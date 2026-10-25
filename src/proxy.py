"""A small middleman. It saves every request the agent sends to Flint."""
import argparse
import json
import pathlib
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import requests


class State:
    lock = threading.Lock()
    trace_id = 0
    step = 0


def make_handler(upstream, out_dir):
    class Handler(BaseHTTPRequestHandler):
        def _send(self, code, body, ctype="application/json"):
            self.send_response(code)
            self.send_header("Content-Type", ctype)
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def do_GET(self):
            r = requests.get(upstream + self.path, timeout=60)
            self._send(r.status_code, r.content, r.headers.get("Content-Type", "application/json"))

        def do_POST(self):
            length = int(self.headers.get("Content-Length", 0))
            raw = self.rfile.read(length)
            try:
                payload = json.loads(raw)
            except ValueError:
                payload = None
            r = requests.post(upstream + self.path, data=raw,
                              headers={"Content-Type": "application/json"}, timeout=3600)
            if (payload is not None and self.path.endswith("/chat/completions")
                    and r.status_code == 200 and not payload.get("stream")):
                self.save(payload, r.json())
            self._send(r.status_code, r.content, r.headers.get("Content-Type", "application/json"))

        def save(self, payload, reply):
            with State.lock:
                # A new task starts when the conversation has only 2 messages.
                if len(payload.get("messages", [])) <= 2:
                    State.trace_id += 1
                    State.step = 0
                State.step += 1
                trace_id, step = State.trace_id, State.step
            usage = reply.get("usage", {})
            row = {
                "trace": trace_id, "step": step, "saved_at": time.time(),
                "prompt_tokens": usage.get("prompt_tokens"),
                "completion_tokens": usage.get("completion_tokens"),
                "timings": reply.get("timings"),
                "request": payload,
            }
            path = out_dir / f"trace_{trace_id:04d}.jsonl"
            with open(path, "a", encoding="utf-8") as f:
                f.write(json.dumps(row) + "\n")
            print(f"saved trace {trace_id} step {step}")

        def log_message(self, *args):
            pass

    return Handler


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--upstream", default="http://127.0.0.1:8080")
    ap.add_argument("--port", type=int, default=9000)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()
    out_dir = pathlib.Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)
    server = ThreadingHTTPServer(("127.0.0.1", args.port), make_handler(args.upstream, out_dir))
    print(f"Proxy on port {args.port}, saving to {out_dir}")
    server.serve_forever()


if __name__ == "__main__":
    main()