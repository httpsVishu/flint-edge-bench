"""Measure how long Flint takes to READ prompts of different lengths."""
import argparse
import csv
import pathlib
import time

import requests

CODE_BLOCK = (
    "def add_item(cart, item, qty=1):\n"
    "    if item in cart:\n"
    "        cart[item] += qty\n"
    "    else:\n"
    "        cart[item] = qty\n"
    "    return cart\n\n"
)
QUESTION = "\nIn one sentence, what does the code above do?"
FIELDS = ["tag", "run", "target_tokens", "prompt_n", "prompt_ms", "prompt_per_second",
          "predicted_n", "predicted_ms", "predicted_per_second", "wall_s"]


def make_prompt(n_tokens):
    chars = int(n_tokens * 3.5)  # rough guess: 3.5 characters per token
    text = (CODE_BLOCK * (chars // len(CODE_BLOCK) + 1))[:chars]
    return text + QUESTION


def ask(url, prompt, max_out, timeout):
    payload = {
        "model": "flint",
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": max_out,
        "cache_prompt": False,  # force a fresh read every time
    }
    start = time.time()
    r = requests.post(f"{url}/v1/chat/completions", json=payload, timeout=timeout)
    wall = time.time() - start
    r.raise_for_status()
    return r.json().get("timings", {}), wall


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--tag", required=True, help="a label like laptop-Q2")
    ap.add_argument("--url", default="http://127.0.0.1:8080")
    ap.add_argument("--sizes", default="2000,8000,16000")
    ap.add_argument("--runs", type=int, default=2)
    ap.add_argument("--max-out", type=int, default=64)
    ap.add_argument("--timeout", type=int, default=3600)
    args = ap.parse_args()

    out = pathlib.Path("results/speed")
    out.mkdir(parents=True, exist_ok=True)
    out_file = out / f"{args.tag}.csv"

    print("Warm-up request (not recorded)...")
    ask(args.url, make_prompt(500), 16, args.timeout)

    with open(out_file, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDS)
        writer.writeheader()
        for size in [int(s) for s in args.sizes.split(",")]:
            for run in range(1, args.runs + 1):
                t, wall = ask(args.url, make_prompt(size), args.max_out, args.timeout)
                row = {
                    "tag": args.tag, "run": run, "target_tokens": size,
                    "prompt_n": t.get("prompt_n"), "prompt_ms": t.get("prompt_ms"),
                    "prompt_per_second": t.get("prompt_per_second"),
                    "predicted_n": t.get("predicted_n"), "predicted_ms": t.get("predicted_ms"),
                    "predicted_per_second": t.get("predicted_per_second"),
                    "wall_s": round(wall, 1),
                }
                writer.writerow(row)
                f.flush()
                print(f"size {size} run {run}: read {row['prompt_n']} tokens in "
                      f"{(row['prompt_ms'] or 0) / 1000:.1f}s, "
                      f"write speed {row['predicted_per_second']}")
    print("Saved", out_file)


if __name__ == "__main__":
    main()