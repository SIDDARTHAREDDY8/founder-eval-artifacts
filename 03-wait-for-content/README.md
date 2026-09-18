# Wait-for-content heuristic

Detects JS-heavy pages where a naive scrape returns only part of the page.

## How it works

`wait_probe.py` takes two snapshots of a URL:

- **early**: raw HTML fetched over HTTP with no JS execution (what a naive
  scraper sees).
- **late**: the page rendered by headless Chromium via the DevTools Protocol
  (`render.py`), after JS has run.

Both are reduced to visible text and compared. `growth_ratio =
late_chars / early_chars`. A page is flagged PARTIAL when the ratio is >= 2.0
and at least 200 new characters appeared.

`bench.py` scores a list of URLs from `urls.txt` and reports the
partial-page rate plus per-URL JSON.

## Run

```bash
pip install websocket-client
python3 wait_probe.py <url>
python3 bench.py
```

## Measured result

On the two local fixtures (deterministic, no network needed):

| page | early chars | late chars | growth | verdict |
|---|---|---|---|---|
| static.html | 281 | 281 | 1.00 | OK |
| js-heavy.html | 57 | 396 | 6.95 | PARTIAL |

Partial-page rate: **1/2 = 0.5**. The JS fixture's real content only appears
after a 1.2s `setTimeout`, exactly the failure mode the heuristic targets.

To score live URLs, add them to `urls.txt`. Note the bundled `urls.txt`
uses `file://` fixtures so the demo is reproducible anywhere; live sites
need the machine's browser to reach the network.
