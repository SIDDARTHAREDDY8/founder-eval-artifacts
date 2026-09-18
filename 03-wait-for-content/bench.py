#!/usr/bin/env python3
"""Benchmark harness: score a list of URLs for partial-page extraction.

Reads urls.txt (one URL per line, # comments allowed), runs the
wait-for-content probe on each, and prints a table plus a JSON summary
with the partial-page rate.

Usage:
  python3 bench.py [--urls urls.txt] [--out bench-results.json]
"""
import argparse
import json
import os
import sys
import traceback

BASE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE)
from wait_probe import probe  # noqa: E402

PORT0 = 19410


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--urls", default=os.path.join(BASE, "urls.txt"))
    ap.add_argument("--out", default=os.path.join(BASE, "bench-results.json"))
    args = ap.parse_args()

    with open(args.urls) as f:
        urls = [l.strip() for l in f if l.strip() and not l.startswith("#")]

    results = []
    for i, url in enumerate(urls):
        try:
            res = probe(url, port=PORT0 + i)
        except Exception as e:  # noqa: BLE001 - bench keeps going
            res = {"url": url, "error": f"{type(e).__name__}: {e}",
                   "partial_page": None}
            traceback.print_exc()
        results.append(res)
        status = ("ERROR" if res.get("error") else
                  "PARTIAL" if res["partial_page"] else "ok")
        print(f"[{status:7s}] {url} "
              f"early={res.get('early_chars')} late={res.get('late_chars')} "
              f"growth={res.get('growth_ratio')}")

    scored = [r for r in results if not r.get("error")]
    partials = sum(1 for r in scored if r["partial_page"])
    summary = {
        "urls": len(urls),
        "scored": len(scored),
        "partial_pages": partials,
        "partial_page_rate": round(partials / max(len(scored), 1), 3),
        "results": results,
    }
    print(f"\npartial-page rate: {partials}/{len(scored)} = "
          f"{summary['partial_page_rate']}")
    with open(args.out, "w") as f:
        json.dump(summary, f, indent=2)
    print(f"wrote {args.out}")


if __name__ == "__main__":
    main()
