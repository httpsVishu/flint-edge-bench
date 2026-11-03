"""Clean raw traces. One raw file can hold several runs, so split by conversation first."""
import argparse
import datetime
import hashlib
import json
import pathlib

# first-message fingerprint -> task name (from the agent's exit-status list)
NAMES = {
    "8ca11773": "django__django-14672",
    "3817f2f3": "sphinx-doc__sphinx-10449",
    "acc00807": "django__django-11299",
}


def task_key(row):
    for m in row["request"].get("messages", []):
        if m.get("role") == "user":
            c = m.get("content")
            c = c if isinstance(c, str) else json.dumps(c)
            return hashlib.md5(c.encode()).hexdigest()[:8]
    return ""


def split_runs(rows):
    """A new run starts when the message list shrinks or the task text changes."""
    runs, cur, prev_n, prev_k = [], [], None, None
    for r in rows:
        n, k = len(r["request"].get("messages", [])), task_key(r)
        if cur and (n < prev_n or k != prev_k):
            runs.append(cur)
            cur = []
        cur.append(r)
        prev_n, prev_k = n, k
    if cur:
        runs.append(cur)
    return runs


def stamp(ts):
    return datetime.datetime.fromtimestamp(ts).strftime("%Y-%m-%d %H:%M")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--raw", default="traces/laptop-Q2")
    ap.add_argument("--out", default="traces_clean/laptop-Q2")
    args = ap.parse_args()
    raw, out = pathlib.Path(args.raw), pathlib.Path(args.out)
    out.mkdir(parents=True, exist_ok=True)

    runs = []
    for f in sorted(raw.glob("trace_*.jsonl")):
        rows = [json.loads(l) for l in f.read_text(encoding="utf-8").splitlines() if l.strip()]
        for r in split_runs(rows):
            runs.append({"file": f.name, "rows": r, "key": task_key(r[0])})

    # keep the longest run for each task; shorter runs of the same task were stopped early
    best = {}
    for run in runs:
        k = run["key"]
        if k not in best or len(run["rows"]) > len(best[k]["rows"]):
            best[k] = run

    report = {"kept": [], "dropped": [], "duplicates_removed": 0, "rows_without_timings_removed": 0}
    kept_runs = []
    for run in runs:
        info = {"task": NAMES.get(run["key"], run["key"]), "from_file": run["file"],
                "steps_raw": len(run["rows"]), "first_seen": stamp(run["rows"][0]["saved_at"])}
        if best[run["key"]] is not run:
            info["reason"] = "shorter run of the same task (stopped early); the longest run is kept"
            report["dropped"].append(info)
            continue
        seen, clean = set(), []
        for r in run["rows"]:
            key = json.dumps(r["request"].get("messages"), sort_keys=True)
            if key in seen:
                report["duplicates_removed"] += 1  # the agent retried after a timeout
                continue
            seen.add(key)
            t = r.get("timings") or {}
            if not t.get("prompt_n") or not t.get("predicted_n"):
                report["rows_without_timings_removed"] += 1
                continue
            clean.append(r)
        info["steps_kept"] = len(clean)
        kept_runs.append((run["rows"][0]["saved_at"], info, clean))

    for new_id, (_, info, clean) in enumerate(sorted(kept_runs, key=lambda x: x[0]), 1):
        for step, r in enumerate(clean, 1):
            r["trace"], r["step"] = new_id, step
        name = f"trace_{new_id:04d}.jsonl"
        (out / name).write_text("\n".join(json.dumps(r) for r in clean) + "\n", encoding="utf-8")
        info["written_as"] = name
        report["kept"].append(info)

    (out / "cleaning_report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()