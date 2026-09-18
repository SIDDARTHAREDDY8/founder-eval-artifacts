#!/usr/bin/env python3
"""Latency profiler for the mock completion pipeline.

Starts mock_server.py, fires N completion requests (sequential or with
--concurrency C), and measures real latencies on this machine:

  client side: time to first token (TTFT), per-token inter-arrival times
  server side: per-stage timings from GET /metrics

Reports p50/p95 per-token latency and names the bottleneck stage.

Usage:
  python3 profile.py [--requests 20] [--max-tokens 32] [--concurrency 1]
                     [--port 18765]

All numbers are measured on the machine that runs this script.
"""
import argparse
import json
import statistics
import subprocess
import sys
import threading
import time
import urllib.request

BASE_PORT_DEFAULT = 18765


def percentile(xs, p):
    if not xs:
        return 0.0
    s = sorted(xs)
    k = (len(s) - 1) * p / 100
    f, c = int(k), min(int(k) + 1, len(s) - 1)
    return s[f] + (s[c] - s[f]) * (k - f)


def one_request(port, prompt, max_tokens):
    """Returns (ttft_ms, [inter_token_ms...])."""
    body = json.dumps({"prompt": prompt, "max_tokens": max_tokens}).encode()
    req = urllib.request.Request(
        f"http://127.0.0.1:{port}/v1/completions", data=body,
        headers={"Content-Type": "application/json"})
    t_start = time.perf_counter()
    arrivals = []
    with urllib.request.urlopen(req, timeout=120) as resp:
        buf = b""
        for raw in resp:
            buf += raw
            while b"\n\n" in buf:
                frame, buf = buf.split(b"\n\n", 1)
                line = frame.strip()
                if not line:
                    continue
                arrivals.append(time.perf_counter())
                if line == b"data: [DONE]":
                    buf = b""
                    break
    ttft = (arrivals[0] - t_start) * 1000 if arrivals else 0.0
    gaps = [(b - a) * 1000 for a, b in zip(arrivals, arrivals[1:])
            if b - a > 0]
    # last arrival is [DONE]; drop the gap into it
    gaps = gaps[:-1] if gaps else []
    return ttft, gaps


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--requests", type=int, default=20)
    ap.add_argument("--max-tokens", type=int, default=32)
    ap.add_argument("--concurrency", type=int, default=1)
    ap.add_argument("--port", type=int, default=BASE_PORT_DEFAULT)
    args = ap.parse_args()

    srv = subprocess.Popen(
        [sys.executable, "mock_server.py", "--port", str(args.port)],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        for _ in range(50):  # wait for health
            try:
                urllib.request.urlopen(
                    f"http://127.0.0.1:{args.port}/health", timeout=2).read()
                break
            except Exception:
                time.sleep(0.2)
        else:
            raise SystemExit("mock server did not start")

        prompt = ("Explain in simple terms how a binary search tree stays "
                  "balanced after insertions and deletions.")
        ttfts, token_gaps = [], []
        lock = threading.Lock()

        def worker(n):
            local_ttft, local_gaps = [], []
            for _ in range(n):
                ttft, gaps = one_request(args.port, prompt, args.max_tokens)
                local_ttft.append(ttft)
                local_gaps.extend(gaps)
            with lock:
                ttfts.extend(local_ttft)
                token_gaps.extend(local_gaps)

        per_thread = args.requests // args.concurrency
        threads = [threading.Thread(target=worker, args=(per_thread,))
                   for _ in range(args.concurrency)]
        t_all = time.perf_counter()
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        wall = time.perf_counter() - t_all

        with urllib.request.urlopen(
                f"http://127.0.0.1:{args.port}/metrics",
                timeout=10) as resp:
            metrics = json.load(resp)["requests"]

        stage_names = ["parse_ms", "tokenize_ms", "queue_ms",
                       "generate_ms"]
        stage_mean = {s: statistics.mean([m[s] for m in metrics])
                      for s in stage_names}
        decode_mean = statistics.mean(
            [m["decode_ms_per_token"] for m in metrics])
        bottleneck = max(stage_mean, key=stage_mean.get)

        n_tok = len(token_gaps)
        print(f"requests: {len(ttfts)}  tokens/request: {args.max_tokens}  "
              f"concurrency: {args.concurrency}  wall: {wall:.1f}s")
        print(f"client TTFT:            p50={percentile(ttfts, 50):7.1f} ms   "
              f"p95={percentile(ttfts, 95):7.1f} ms")
        print(f"client per-token (n={n_tok}): p50={percentile(token_gaps, 50):7.1f} ms   "
              f"p95={percentile(token_gaps, 95):7.1f} ms")
        print(f"server decode/token:    mean={decode_mean:.1f} ms")
        print("server stage means (ms): " +
              "  ".join(f"{s}={stage_mean[s]:.1f}" for s in stage_names))
        print(f"bottleneck stage: {bottleneck} "
              f"({stage_mean[bottleneck]:.1f} ms mean, "
              f"{stage_mean[bottleneck] / max(sum(stage_mean.values()), 1e-9) * 100:.0f}% of server time)")
    finally:
        srv.terminate()
        srv.wait()


if __name__ == "__main__":
    main()
