#!/usr/bin/env python3
"""Notebook-to-app conversion eval: marimo notebook vs Streamlit app.

Both apps implement the same data-app task (load sales.csv, filter by a
category widget, show totals + revenue bar chart + table). The harness
scores:

  1. lines of code (non-blank, non-comment)
  2. conversion correctness: static checks that both apps wire the same
     widget, the same shared data logic, and the same outputs
  3. functional check: runs the shared data logic per category and verifies
     sane numbers
  4. time to interactive: launches each app server and times until the first
     HTTP 200 (skipped honestly if the runtime is not installed)

Usage:
  python3 eval.py [--skip-servers]
"""
import argparse
import ast
import os
import shutil
import subprocess
import sys
import time
import urllib.request

BASE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE)


def loc(path):
    n = 0
    with open(path) as f:
        for line in f:
            s = line.strip()
            if s and not s.startswith("#") and not s.startswith('"""'):
                n += 1
    return n


def static_checks(path, kind):
    with open(path) as f:
        src = f.read()
    tree = ast.parse(src)
    names = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Attribute):
            names.add(node.attr)
        if isinstance(node, ast.Name):
            names.add(node.id)
    checks = {
        "imports shared data_logic": "data_logic" in src,
        "loads sales.csv via load_sales": "load_sales" in src,
        "category widget present": ("dropdown" in names if kind == "marimo"
                                    else "selectbox" in names),
        "widget options from categories()": "categories(df)" in src,
        "applies filter_and_summarize": "filter_and_summarize" in src,
        "bar chart of revenue": ("ax.bar" in src and 'summary["revenue"]' in src),
        "shows summary table": ("mo.ui.table" in src if kind == "marimo"
                                else "st.dataframe" in src),
    }
    return checks


def functional_check():
    from data_logic import load_sales, categories, filter_and_summarize
    df = load_sales()
    assert len(df) == 12, f"expected 12 rows, got {len(df)}"
    results = {}
    for cat in categories(df):
        summary, totals = filter_and_summarize(df, cat)
        assert totals["revenue"] == int(summary["revenue"].sum())
        assert totals["units"] > 0 and totals["products"] > 0
        results[cat] = totals
    return results


def time_to_interactive(cmd, port, timeout=90):
    """Launch an app server; return seconds until first HTTP 200."""
    exe = shutil.which(cmd[0])
    if exe is None:
        return None, f"{cmd[0]} not installed"
    proc = subprocess.Popen(cmd, stdout=subprocess.DEVNULL,
                            stderr=subprocess.DEVNULL)
    try:
        deadline = time.time() + timeout
        start = time.time()
        while time.time() < deadline:
            try:
                with urllib.request.urlopen(
                        f"http://127.0.0.1:{port}", timeout=3) as resp:
                    if resp.status == 200:
                        return time.time() - start, None
            except Exception:
                pass
            if proc.poll() is not None:
                return None, f"{cmd[0]} exited early (code {proc.returncode})"
            time.sleep(0.5)
        return None, "timed out waiting for HTTP 200"
    finally:
        proc.terminate()
        proc.wait()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--skip-servers", action="store_true")
    args = ap.parse_args()

    apps = {"marimo": "app_marimo.py", "streamlit": "app_streamlit.py"}
    print("== lines of code (non-blank, non-comment) ==")
    for kind, fn in apps.items():
        print(f"  {kind:<10} {loc(os.path.join(BASE, fn))}")

    print("\n== conversion correctness checks ==")
    all_ok = True
    for kind, fn in apps.items():
        print(f"  [{kind}]")
        for name, ok in static_checks(os.path.join(BASE, fn), kind).items():
            print(f"    {'PASS' if ok else 'FAIL'}  {name}")
            all_ok &= ok

    print("\n== functional check (shared data logic) ==")
    try:
        results = functional_check()
        for cat, totals in results.items():
            print(f"  {cat:<8} products={totals['products']} "
                  f"units={totals['units']} revenue=${totals['revenue']:,}")
        print("  PASS: totals consistent across categories")
    except AssertionError as e:
        all_ok = False
        print(f"  FAIL: {e}")
    except ImportError as e:
        all_ok = False
        print(f"  SKIP: pandas not installed ({e})")

    print("\n== time to interactive app ==")
    if args.skip_servers:
        print("  skipped (--skip-servers)")
    else:
        for kind, cmd, port in [
                ("marimo", ["marimo", "run", "app_marimo.py",
                            "--port", "18771", "--headless"], 18771),
                ("streamlit", ["streamlit", "run", "app_streamlit.py",
                               "--server.port", "18772",
                               "--server.headless", "true"], 18772)]:
            secs, err = time_to_interactive(cmd, port)
            if secs is None:
                print(f"  {kind:<10} not measured ({err})")
            else:
                print(f"  {kind:<10} {secs:.1f}s to first HTTP 200")

    print(f"\nconversion correctness: {'ALL PASS' if all_ok else 'FAILURES'}")


if __name__ == "__main__":
    main()
