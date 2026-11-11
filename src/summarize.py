"""Turn all result files into one table and two charts."""
import glob
import json
import pathlib

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

out = pathlib.Path("results")
out.mkdir(exist_ok=True)
lines = ["# Results", ""]

# 1. Reading time vs prompt length
files = sorted(glob.glob("results/speed/*.csv"))
if files:
    speed = pd.concat([pd.read_csv(f) for f in files])
    s = (speed.groupby(["tag", "target_tokens"])
         .agg(prompt_tokens=("prompt_n", "mean"),
              reading_seconds=("prompt_ms", lambda x: x.mean() / 1000),
              reading_tok_per_s=("prompt_per_second", "mean"),
              writing_tok_per_s=("predicted_per_second", "mean"))
         .round(1).reset_index())
    lines += ["## Reading and writing speed by prompt length", "", s.to_markdown(index=False), ""]
    plt.figure(figsize=(7, 4))
    for tag, g in s.groupby("tag"):
        plt.plot(g["prompt_tokens"], g["reading_seconds"], marker="o", label=tag)
    plt.xlabel("Prompt length (tokens)")
    plt.ylabel("Seconds to read the prompt")
    plt.title("Reading time grows with prompt length")
    plt.legend()
    plt.tight_layout()
    plt.savefig("results/reading_time.png", dpi=150)
    plt.close()

# 2. Replay: time per agent step, split into reading and writing
files = sorted(glob.glob("results/replay/*.csv"))
if files:
    rep = pd.concat([pd.read_csv(f) for f in files])
    rep["setup"] = rep["tag"] + " (" + rep["mode"] + ")"
    r = (rep.groupby("setup")
         .agg(steps=("est_step_s", "count"), avg_prompt_tokens=("prompt_n", "mean"),
              reading_s=("prefill_s", "mean"), writing_s=("est_decode_s", "mean"),
              step_s=("est_step_s", "mean"))
         .round(1))
    r["reading_share_pct"] = (100 * r["reading_s"] / r["step_s"]).round(0)
    lines += ["## Seconds per agent step (replay)", "", r.reset_index().to_markdown(index=False), ""]
    r[["reading_s", "writing_s"]].plot(kind="bar", stacked=True, figsize=(8, 4))
    plt.ylabel("Seconds per agent step")
    plt.title("Where one agent step spends its time")
    plt.tight_layout()
    plt.savefig("results/step_time.png", dpi=150)
    plt.close()

# 3. Live runs: real timings saved by the proxy
rows = []
for f in glob.glob("traces_clean/*/trace_*.jsonl"):
    tag = pathlib.Path(f).parent.name
    for line in open(f, encoding="utf-8"):
        row = json.loads(line)
        t = row.get("timings") or {}
        rows.append({"tag": tag, "trace": row["trace"],
                     "reading_s": (t.get("prompt_ms") or 0) / 1000,
                     "writing_s": (t.get("predicted_ms") or 0) / 1000})
if rows:
    live = pd.DataFrame(rows).groupby(["tag", "trace"]).sum().reset_index()
    live["task_minutes"] = (live["reading_s"] + live["writing_s"]) / 60
    live["reading_share_pct"] = 100 * live["reading_s"] / (live["reading_s"] + live["writing_s"])
    l = live.groupby("tag").agg(tasks=("trace", "count"),
                                avg_task_minutes=("task_minutes", "mean"),
                                reading_share_pct=("reading_share_pct", "mean")).round(1)
    lines += ["## Live agent runs (real time spent per task)", "", l.reset_index().to_markdown(index=False), ""]

pathlib.Path("results/summary.md").write_text("\n".join(lines), encoding="utf-8")
print("Wrote results/summary.md and charts")