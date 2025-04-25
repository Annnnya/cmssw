# average_dummy_results.py

import os
import json
import pandas as pd
from collections import defaultdict

# Base directory from your bash script
experiment_name = "test_results_thesis/local-remote_t-s-c_different-sockets""
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
                    threads, streams = t_s_part.split("s")

                    with open(os.path.join(root, fname)) as f:
                        data = json.load(f)

                    events = data.get("total", {}).get("events", 1)
                    recv_modules = [m for m in data["modules"] if m.get("type") == "MPIReceiver"]
                    send_modules = [m for m in data["modules"] if m.get("type") == "MPISender"]

                    if not recv_modules and not send_modules:
                        continue  # Skip if neither sender nor receiver is found

                    entry = {}

                    if recv_modules:
                        entry["recv_cpu"] = sum(m.get("time_thread", 0.0) for m in recv_modules) / events
                        entry["recv_real"] = sum(m.get("time_real", 0.0) for m in recv_modules) / events

                    if send_modules:
                        entry["send_cpu"] = sum(m.get("time_thread", 0.0) for m in send_modules) / events
                        entry["send_real"] = sum(m.get("time_real", 0.0) for m in send_modules) / events

                    entry["total_cpu"] = data.get("total", {}).get("time_thread", 0.0) / events
                    entry["total_real"] = data.get("total", {}).get("time_real", 0.0) / events

                    key = (comm_type, int(threads), int(streams))
                    grouped_entries[key].append(entry)

                except Exception as e:
                    print(f"Error in {fname}: {e}")
                    continue
    return grouped_entries

import re
from collections import defaultdict

def parse_throughput_file(filepath):
    throughput_data = defaultdict(list)
    pattern = re.compile(
        r"\[THROUGHPUT\] comm_(\w+)_t(\d+)s(\d+)_r(\d+) \| avg: ([\d.]+) ± ([\d.]+) ev/s"
    )

    with open(filepath) as f:
        for line in f:
            match = pattern.search(line)
            if match:
                comm, threads, streams, run_id, avg_val, _ = match.groups()
                key = (comm, int(threads), int(streams))
                throughput_data[key].append((int(run_id), float(avg_val)))

    # Discard warmup (first run by run_id) and average the rest
    throughput_avg = {}
    for key, values in throughput_data.items():
        values.sort()  # sort by run_id
        valid = values[1:]  # discard first
        if valid:
            avg_throughput = sum(v[1] for v in valid) / len(valid)
            throughput_avg[key] = avg_throughput

    return throughput_avg



def summarize(grouped_entries):
    summary = []
    for (comm, th, st), group in grouped_entries.items():
        if len(group) <= 1:
            continue  # Not enough runs to discard warmup

        df = pd.DataFrame(group[1:])  # Discard first entry (warmup)
        avg = df.mean(numeric_only=True).to_dict()
        avg.update({
            "comm": comm,
            "threads": th,
            "streams": st
        })
        summary.append(avg)

    return pd.DataFrame(summary)

grouped = find_all_json_files(base_dir, f"{mode}_")
summary_df = summarize(grouped)
summary_df.sort_values(by=["comm", "threads", "streams"], inplace=True)

throughput_path = os.path.join(base_dir, "throughputs.txt")
throughput_avg = parse_throughput_file(throughput_path)

# Add throughput to summary
def attach_throughput(summary_df, throughput_avg):
    summary_df["throughput_ev_per_s"] = summary_df.apply(
        lambda row: throughput_avg.get(
            (row["comm"], row["threads"], row["streams"]), None
        ),
        axis=1
    )
    return summary_df

summary_df = attach_throughput(summary_df, throughput_avg)


# Save output
csv_path = os.path.join(base_dir, f"{mode}_summary_table.csv")
json_path = os.path.join(base_dir, f"{mode}_summary_table.json")
summary_df.to_csv(csv_path, index=False)
summary_df.to_json(json_path, orient="records", indent=2)

print(f"Saved summary to:\n- {csv_path}\n- {json_path}")
