#!/usr/bin/env python3
"""Wait-for-content heuristic probe.

For one URL:
  early snapshot = raw HTML fetched over HTTP with no JS execution
                   (what a naive scraper sees).
  late snapshot  = the same page rendered by headless Chromium via CDP
                   (what the page becomes after JS runs).

Both snapshots are reduced to visible text and compared. A large growth in
visible text between early and late means content loaded after extraction:
the page is JS-heavy and a naive scrape returns a partial page.

Usage:
  python3 wait_probe.py <url> [--wait-ms 4000] [--out result.json]

Requires: websocket-client (pip install websocket-client)
"""
import argparse
import html as htmlmod
import json
import os
import re
import sys
import urllib.request

BASE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE)
from render import render  # noqa: E402


def fetch_early(url, timeout=30):
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        raw = resp.read()
    charset = resp.headers.get_content_charset() or "utf-8"
    return raw.decode(charset, errors="replace")


def visible_text(html):
    # drop scripts, styles, and comments, then strip tags
    no_script = re.sub(r"(?is)<(script|style|noscript)[^>]*>.*?</\1>", " ", html)
    no_comments = re.sub(r"(?s)<!--.*?-->", " ", no_script)
    text = re.sub(r"<[^>]+>", " ", no_comments)
    text = htmlmod.unescape(text)
    return re.sub(r"\s+", " ", text).strip()


def probe(url, wait_ms=4000, port=19399):
    if url.startswith("file://"):
        with open(url[7:], "r", encoding="utf-8", errors="replace") as f:
            early_html = f.read()
    else:
        early_html = fetch_early(url)
    late_html = render(url, wait_ms=wait_ms, port=port)

    early = visible_text(early_html)
    late = visible_text(late_html)
    early_n, late_n = len(early), len(late)
    growth = late_n / max(early_n, 1)
    # fraction of late text that was already present early
    overlap = len(set(early.split()) & set(late.split())) / max(len(set(late.split())), 1)

    partial = growth >= 2.0 and late_n - early_n >= 200
    return {
        "url": url,
        "early_chars": early_n,
        "late_chars": late_n,
        "growth_ratio": round(growth, 2),
        "vocab_overlap": round(overlap, 2),
        "partial_page": partial,
        "verdict": ("PARTIAL: naive scrape misses late-loaded content"
                    if partial else "OK: early snapshot captured the page"),
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("url")
    ap.add_argument("--wait-ms", type=int, default=4000)
    ap.add_argument("--out", default=None)
    ap.add_argument("--port", type=int, default=19399)
    args = ap.parse_args()
    res = probe(args.url, wait_ms=args.wait_ms, port=args.port)
    print(json.dumps(res, indent=2))
    if args.out:
        with open(args.out, "w") as f:
            json.dump(res, f, indent=2)


if __name__ == "__main__":
    main()
