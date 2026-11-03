"""Replay recorded agent prompts and time how long reading and writing take."""
import argparse
import csv
import json
import pathlib

import requests

FIELDS = ["tag", "mode", "trace", "step", "prompt_n", "cache_n", "prefill_s",
          "decode_tps", "completion_tokens", "est_decode_s", "est_step_s"]


def load_rows(trace_dir):
    rows = []
    for f in sorted(pathlib.Path(trace_dir).glob("trace_*.jsonl")):
        for line in f.read_text(encoding="utf-8").splitlines():
            if line.strip():
                rows.append(json.loads(line))
    rows.sort(key=lambda r: (r["trace"], r["step"]))
    seen, unique = set(), []
    for r in rows:
        key = (r["trace"], json.dumps(r["request"].get("messages"), sort_keys=True))
        if key not in seen:
            seen.add(key)
            unique.append(r)
    return unique


def pick(rows, n, warm):
    if warm:
        by_trace = {}
        for r in rows:
            by_trace.setdefault(r["trace"], []).append(r)
        longest = max(by_trace.values(), key=len)
        return longest[:n]  # consecutive steps of one task, in order
    if len(rows) <= n:
        return rows
    gap = len(rows) / n
    return [rows[int(i * gap)] for i in range(n)]  # evenly spread samples


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--traces", required=True)
    ap.add_argument("--tag", required=True)
    ap.add_argument("--url", default="http://127.0.0.1:8080")
    ap.add_argument("--samples", type=int, default=12)
    ap.add_argument("--max-out", type=int, default=64)
    ap.add_argument("--warm", action="store_true",
                    help="keep the server's memory of earlier steps, like a live run")
    args = ap.parse_args()

    mode = "warm" if args.warm else "cold"
    rows = pick(load_rows(args.traces), args.samples, args.warm)
    out = pathlib.Path("results/replay")
    out.mkdir(parents=True, exist_ok=True)
    out_file = out / f"{args.tag}_{mode}.csv"

    with open(out_file, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDS)
        writer.writeheader()
        for i, row in enumerate(rows, 1):
            payload = dict(row["request"])
            payload["stream"] = False
            payload.pop("stream_options", None)
            payload.pop("max_completion_tokens", None)
            payload["max_tokens"] = args.max_out
            payload["cache_prompt"] = args.warm
            r = requests.post(f"{args.url}/v1/chat/completions", json=payload, timeout=7200)
            if r.status_code != 200:
                print(f"[{i}/{len(rows)}] failed ({r.status_code}). Is the server -c big enough?")
                continue
            t = r.json().get("timings", {})
            prefill_s = (t.get("prompt_ms") or 0) / 1000
            tps = t.get("predicted_per_second") or 0
            done = row.get("completion_tokens") or 0
            decode_s = done / tps if tps else 0
            record = {
                "tag": args.tag, "mode": mode, "trace": row["trace"], "step": row["step"],
                "prompt_n": t.get("prompt_n"), "cache_n": t.get("cache_n", 0),
                "prefill_s": round(prefill_s, 2), "decode_tps": round(tps, 2),
                "completion_tokens": done, "est_decode_s": round(decode_s, 2),
                "est_step_s": round(prefill_s + decode_s, 2),
            }
            writer.writerow(record)
            f.flush()
            print(f"[{i}/{len(rows)}] read {record['prompt_n']} tokens in {prefill_s:.1f}s, "
                  f"step total about {record['est_step_s']}s")
    print("Saved", out_file)


if __name__ == "__main__":
    main()