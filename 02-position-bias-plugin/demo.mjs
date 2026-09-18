#!/usr/bin/env node
/**
 * demo.mjs - runs the position-bias plugin against a toy dataset.
 *
 * The judge here is a SIMULATED stand-in (clearly labeled): a deterministic
 * function that scores higher when the key chunk sits near the start of the
 * context, modeling primacy bias. It exists so the plugin runs with no API
 * cost. Swap in a real judge, e.g.:
 *
 *   const judge = async (context, question) =>
 *     (await callYourJudgeLLM(context, question)).score;
 */
import { readFileSync } from 'fs';
import { measurePositionBias } from './positionBias.js';

// SIMULATED judge. Not a real LLM. Scores the chunk with the best keyword
// overlap, then discounts it by how far down the context that chunk sits,
// modeling primacy bias: score = overlap * (1 - 0.3 * position/n).
function simulatedJudge(questionKeywords) {
  return async (context, question) => {
    const chunks = context.split('\n');
    let best = 0;
    chunks.forEach((chunkText, i) => {
      const lower = chunkText.toLowerCase();
      const hits = questionKeywords.filter((k) => lower.includes(k)).length;
      const overlap = Math.min(1, hits / questionKeywords.length);
      const positionDiscount = 1 - 0.3 * (i / chunks.length);
      best = Math.max(best, overlap * positionDiscount);
    });
    return Math.round(best * 100) / 100;
  };
}

const dataset = JSON.parse(readFileSync('./dataset.json', 'utf8'));

const caseKeywords = [
  ['1889', 'completed', 'eiffel'],
  ['stroma', 'chloroplasts', 'calvin'],
  ['15', 'merge', 'postgresql'],
];

let totalSpread = 0;
for (let i = 0; i < dataset.cases.length; i++) {
  const c = dataset.cases[i];
  const res = await measurePositionBias({
    judge: simulatedJudge(caseKeywords[i]),
    chunks: c.chunks,
    keyId: c.keyId,
    question: c.question,
  });
  totalSpread += res.maxSpread;
  console.log(`case ${i + 1}: ${c.question}`);
  console.log(`  scores by key-chunk position: ${JSON.stringify(res.scores)}`);
  console.log(`  max spread: ${res.maxSpread} -> ${res.verdict}`);
}
console.log(`\nmean max spread across ${dataset.cases.length} cases: ` +
  `${(totalSpread / dataset.cases.length).toFixed(2)}`);
console.log('(judge is SIMULATED with baked-in primacy bias; ' +
  'a real judge would produce its own numbers)');
