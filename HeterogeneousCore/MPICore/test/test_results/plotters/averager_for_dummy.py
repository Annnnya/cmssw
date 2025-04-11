# average_dummy_results.py

import os
import json
import pandas as pd
from collections import defaultdict

# Base directory from your bash script
experiment_name = "general_dummy_1-1"
base_dir = f"../{experiment_name}"
mode = "local"

def find_all_json_files(base_dir, prefix):
    grouped_entries = defaultdict(list)

    for root, _, files in os.walk(base_dir):
        for fname in sorted(files):  # Ensure sorted for consistent warmup exclusion
            if fname.endswith(".json") and fname.startswith(prefix):
                try:
                    parts = os.path.relpath(root, base_dir).split("_")
                    comm_type = parts[1]
                    t_s_part = parts[2][1:]  # e.g., "8s4"
                    local_numa, remote_numa = parts[3].split("-")
                    threads, streams = t_s_part.split("s")

                    with open(os.path.join(root, fname)) as f:
                        data = json.load(f)

                    events = data.get("total", {}).get("events", 1)
                    recv_cpu = sum(m.get("time_thread", 0.0) for m in data["modules"] if m.get("type") == "MPIReceiver") / events
                    recv_real = sum(m.get("time_real", 0.0) for m in data["modules"] if m.get("type") == "MPIReceiver") / events
                    total_cpu = data.get("total", {}).get("time_thread", 0.0) / events
                    total_real = data.get("total", {}).get("time_real", 0.0) / events

                    key = (comm_type, int(threads), int(streams), local_numa, remote_numa)
                    grouped_entries[key].append({
                        "recv_cpu": recv_cpu,
                        "recv_real": recv_real,
                        "total_cpu": total_cpu,
                        "total_real": total_real,
                    })

                except Exception as e:
                    print(f"Error in {fname}: {e}")
                    continue
    return grouped_entries

def summarize(grouped_entries):
    summary = []
    for (comm, th, st, ln, rn), group in grouped_entries.items():
        if len(group) <= 1:
            continue  # Not enough runs to discard warmup

        df = pd.DataFrame(group[1:])  # Discard first entry (warmup)
        avg = df.mean(numeric_only=True).to_dict()
        avg.update({
            "comm": comm,
            "threads": th,
            "streams": st,
            "local_numa": ln,
            "remote_numa": rn,
        })
        summary.append(avg)

    return pd.DataFrame(summary)

grouped = find_all_json_files(base_dir, f"{mode}_")
summary_df = summarize(grouped)
summary_df.sort_values(by=["comm", "local_numa", "remote_numa", "threads", "streams"], inplace=True)

# Save output
csv_path = os.path.join(base_dir, f"{mode}_summary_table.csv")
json_path = os.path.join(base_dir, f"{mode}_summary_table.json")
summary_df.to_csv(csv_path, index=False)
summary_df.to_json(json_path, orient="records", indent=2)

print(f"Saved summary to:\n- {csv_path}\n- {json_path}")
