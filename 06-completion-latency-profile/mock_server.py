#!/usr/bin/env python3
"""Minimal mock completion server with a timed pipeline.

This is a MOCK, not a real model server. It exists so the profiling harness
measures a real HTTP + pipeline path on this machine. Every stage is timed
with perf_counter and exposed via GET /metrics.

Pipeline stages per request:
  parse      JSON body parse and validation
  tokenize   prompt tokenization (whitespace split + per-token hash work)
  queue      simulated scheduler wait (models queue contention)
  generate   simulated autoregressive decode: a calibrated CPU busy-loop per
             token (the designed bottleneck, like real decode)
  stream     SSE serialization of the token stream

Endpoints:
  POST /v1/completions {"prompt": str, "max_tokens": int} -> SSE token stream
  GET  /metrics -> JSON list of per-request stage timings (ms)

Usage:
  python3 mock_server.py [--port 18765]
"""
import argparse
import hashlib
import json
import random
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

REQUESTS = []
LOCK = threading.Lock()

# calibrated so one fake token costs roughly 3 ms of CPU on this machine
BUSY_LOOP_ITERS = 60000


def busy_token():
    h = hashlib.sha256()
    for i in range(BUSY_LOOP_ITERS):
        h.update(str(i).encode())
    return h.hexdigest()[:8]


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def _send_json(self, obj, code=200):
        body = json.dumps(obj).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        if self.path == "/metrics":
            with LOCK:
                self._send_json({"requests": REQUESTS})
        elif self.path == "/health":
            self._send_json({"ok": True})
        else:
            self._send_json({"error": "not found"}, 404)

    def do_POST(self):
        if self.path != "/v1/completions":
            self._send_json({"error": "not found"}, 404)
            return
        stages = {}
        t0 = time.perf_counter()

        length = int(self.headers.get("Content-Length", 0))
        body = json.loads(self.rfile.read(length) or b"{}")
        prompt = body.get("prompt", "")
        max_tokens = int(body.get("max_tokens", 32))
        stages["parse_ms"] = (time.perf_counter() - t0) * 1000

        t0 = time.perf_counter()
        tokens_in = prompt.split()
        for tok in tokens_in:  # per-token hash work, like BPE merges
            hashlib.sha256(tok.encode()).hexdigest()
        stages["tokenize_ms"] = (time.perf_counter() - t0) * 1000

        t0 = time.perf_counter()
        time.sleep(random.uniform(0.002, 0.008))  # scheduler queue wait
        stages["queue_ms"] = (time.perf_counter() - t0) * 1000

        t0 = time.perf_counter()
        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream")
        self.send_header("Cache-Control", "no-cache")
        self.end_headers()
        token_times = []
        try:
            for _ in range(max_tokens):
                tg0 = time.perf_counter()
                tok = busy_token()
                token_times.append((time.perf_counter() - tg0) * 1000)
                chunk = json.dumps({"token": tok}).encode()
                self.wfile.write(b"data: " + chunk + b"\n\n")
                self.wfile.flush()
            self.wfile.write(b"data: [DONE]\n\n")
            self.wfile.flush()
        except (BrokenPipeError, ConnectionResetError):
            pass
        stages["generate_ms"] = (time.perf_counter() - t0) * 1000
        stages["stream_ms"] = 0.0  # frames flush inline during generate
        stages["decode_ms_per_token"] = (
            sum(token_times) / max(len(token_times), 1))

        stages["total_ms"] = sum(stages.values())
        with LOCK:
            REQUESTS.append(stages)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", type=int, default=18765)
    args = ap.parse_args()
    srv = ThreadingHTTPServer(("127.0.0.1", args.port), Handler)
    print(f"mock completion server on 127.0.0.1:{args.port} "
          f"(MOCK: no real model behind it)")
    srv.serve_forever()


if __name__ == "__main__":
    main()
