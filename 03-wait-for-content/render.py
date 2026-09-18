#!/usr/bin/env python3
"""Headless render via Chrome DevTools Protocol.

Launches headless Chromium with a remote-debugging port, navigates to the
URL, waits for network/rendering to settle, then returns the rendered
document HTML. Used as the 'late snapshot' for the wait-for-content probe.

Works with file:// URLs and http(s) URLs (the browser must be able to reach
the network; proxy config is out of scope here).

Usage:
  python3 render.py <url> [--wait-ms 4000] [--out rendered.html]
"""
import argparse
import json
import subprocess
import sys
import time
import urllib.request

CHROME = "/opt/meta-chromium/chrome"


def launch_chrome(port):
    proc = subprocess.Popen(
        [CHROME, "--headless=new", "--no-sandbox", "--disable-gpu",
         "--disable-dev-shm-usage", f"--remote-debugging-port={port}",
         "--remote-allow-origins=*", "about:blank"],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    # wait for the DevTools endpoint to come up
    for _ in range(60):
        try:
            with urllib.request.urlopen(
                    f"http://127.0.0.1:{port}/json/list",
                    timeout=2) as resp:
                targets = json.load(resp)
            for t in targets:
                if t.get("type") == "page":
                    return proc, t["webSocketDebuggerUrl"]
        except Exception:
            pass
        time.sleep(0.5)
    proc.terminate()
    raise RuntimeError("chrome DevTools endpoint did not come up")


def render(url, wait_ms=4000, port=19399):
    import websocket  # pip install websocket-client
    proc, ws_url = launch_chrome(port)
    try:
        ws = websocket.create_connection(ws_url, timeout=30)
        msg_id = [0]

        def send(method, params=None):
            msg_id[0] += 1
            ws.send(json.dumps({"id": msg_id[0], "method": method,
                                "params": params or {}}))
            return msg_id[0]

        def recv(mid, timeout=30):
            deadline = time.time() + timeout
            while time.time() < deadline:
                msg = json.loads(ws.recv())
                if msg.get("id") == mid:
                    return msg.get("result", {})
            raise RuntimeError(f"no reply for {mid}")

        send("Page.enable")
        send("Runtime.enable")
        mid = send("Page.navigate", {"url": url})
        recv(mid)
        # let JS run and late content load
        time.sleep(wait_ms / 1000.0)
        mid = send("Runtime.evaluate", {
            "expression": "document.documentElement.outerHTML",
            "returnByValue": True})
        html = recv(mid)["result"]["value"]
        ws.close()
        return html
    finally:
        proc.terminate()
        proc.wait()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("url")
    ap.add_argument("--wait-ms", type=int, default=4000)
    ap.add_argument("--out", default=None)
    ap.add_argument("--port", type=int, default=19399)
    args = ap.parse_args()
    html = render(args.url, wait_ms=args.wait_ms, port=args.port)
    if args.out:
        with open(args.out, "w") as f:
            f.write(html)
        print(f"wrote {args.out} ({len(html)} chars)")
    else:
        print(html)


if __name__ == "__main__":
    main()
