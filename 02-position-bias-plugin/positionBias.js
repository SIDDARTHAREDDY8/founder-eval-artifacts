/**
 * positionBias.js - position-bias eval plugin for RAG judges.
 *
 * Given a set of context chunks and the id of the chunk that actually
 * answers the question, this module re-orders the context so the key chunk
 * sits at different positions (start / middle / end) and calls a judge
 * function on each ordering. If the judge's score swings with position
 * rather than content, the judge has position bias.
 *
 * Usage as a promptfoo custom assertion wrapper:
 *   const { makePromptfooAssertion } = require('./positionBias');
 *   // in promptfoo config: defaultTest with `assert: [{ type: 'javascript', value: 'file://./positionBias.assert.js' }]`
 *
 * The core function is judge-agnostic: pass any async (context, question) => score.
 */

function buildContext(chunks, keyId, position) {
  const key = chunks.find((c) => c.id === keyId);
  const rest = chunks.filter((c) => c.id !== keyId);
  if (!key) throw new Error(`key chunk not found: ${keyId}`);
  let ordered;
  if (position === 'start') ordered = [key, ...rest];
  else if (position === 'end') ordered = [...rest, key];
  else {
    const mid = Math.floor(rest.length / 2);
    ordered = [...rest.slice(0, mid), key, ...rest.slice(mid)];
  }
  return ordered.map((c, i) => `[chunk ${i + 1}] ${c.text}`).join('\n');
}

/**
 * @param {Object} opts
 * @param {(context: string, question: string) => Promise<number>} opts.judge
 * @param {Array<{id: string, text: string}>} opts.chunks
 * @param {string} opts.keyId
 * @param {string} opts.question
 * @param {string[]} [opts.positions]
 * @returns {Promise<Object>} scores per position plus bias summary
 */
async function measurePositionBias({ judge, chunks, keyId, question,
  positions = ['start', 'middle', 'end'] }) {
  const scores = {};
  for (const pos of positions) {
    const context = buildContext(chunks, keyId, pos);
    scores[pos] = await judge(context, question);
  }
  const vals = Object.values(scores);
  const mean = vals.reduce((a, b) => a + b, 0) / vals.length;
  const std = Math.sqrt(vals.reduce((a, b) => a + (b - mean) ** 2, 0) / vals.length);
  const maxSpread = Math.max(...vals) - Math.min(...vals);
  return {
    scores,
    mean: round2(mean),
    stddev: round2(std),
    maxSpread: round2(maxSpread),
    // position-sensitivity: spread relative to the score scale
    positionSensitivity: round2(maxSpread / Math.max(mean, 1e-9)),
    verdict: maxSpread > 0.15
      ? 'BIASED: score swings with key-chunk position'
      : 'OK: score is stable across positions',
  };
}

function round2(x) { return Math.round(x * 100) / 100; }

/**
 * promptfoo-compatible assertion factory.
 * judge and dataset come from the promptfoo test context.
 */
function makePromptfooAssertion({ judge, chunks, keyId, positions }) {
  return async (output, testCase) => {
    const question = testCase?.vars?.question || '';
    const res = await measurePositionBias({ judge, chunks, keyId, question, positions });
    return {
      pass: res.maxSpread <= 0.15,
      score: 1 - Math.min(res.positionSensitivity, 1),
      reason: `${res.verdict} (scores: ${JSON.stringify(res.scores)})`,
      namedScores: { positionBiasSpread: res.maxSpread },
    };
  };
}

module.exports = { measurePositionBias, buildContext, makePromptfooAssertion };
