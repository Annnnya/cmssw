import os
import json
import pandas as pd
import re
from collections import defaultdict

# Base directory setup
experiment_name = "plain_hlt_dependence_within_socket_thread-stream-core"
base_dir = f"../{experiment_name}"
mode = "local"

def find_all_json_files(base_dir, prefix):
    grouped_entries = defaultdict(list)

    for root, _, files in os.walk(base_dir):
        for fname in sorted(files):
            if fname.endswith(".json") and fname.startswith(prefix):
                try:
                    full_path = os.path.join(root, fname)
                    filename = os.path.splitext(fname)[0]

                    # Match local_t4s4_n6_r1 or local_comm_xpmem_t4s4_r1
                    match = re.search(r"_t(\d+)s(\d+)", filename)
                    if not match:
                        continue
                    threads, streams = match.groups()

                    with open(full_path) as f:
                        data = json.load(f)

                    events = data.get("total", {}).get("events", 1)

                    entry = {
                        "total_cpu": data.get("total", {}).get("time_thread", 0.0) / events,
                        "total_real": data.get("total", {}).get("time_real", 0.0) / events,
                    }

                    key = (int(threads), int(streams))
                    grouped_entries[key].append(entry)

                except Exception as e:
                    print(f"Error in {fname}: {e}")
                    continue

    return grouped_entries

def parse_throughput_file(filepath):
    throughput_data = defaultdict(list)
    pattern = re.compile(
        r"\[THROUGHPUT\] local_t(\d+)s(\d+)_n\d+_r(\d+) \| avg: ([\d.]+)"
    )

    with open(filepath) as f:
        for line in f:
            match = pattern.search(line)
            if match:
                threads, streams, run_id, avg_val = match.groups()
                key = (int(threads), int(streams))
                throughput_data[key].append((int(run_id), float(avg_val)))

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
    for (th, st), group in grouped_entries.items():
        if len(group) <= 1:
            continue  # Not enough runs to discard warmup

        df = pd.DataFrame(group[1:])  # Discard warmup
        avg = df.mean(numeric_only=True).to_dict()
        avg.update({
            "threads": th,
            "streams": st
        })
        summary.append(avg)

    return pd.DataFrame(summary)

def attach_throughput(summary_df, throughput_avg):
    summary_df["throughput_ev_per_s"] = summary_df.apply(
        lambda row: throughput_avg.get((row["threads"], row["streams"]), None),
        axis=1
    )
    return summary_df

# Run everything
grouped = find_all_json_files(base_dir, f"{mode}_")
summary_df = summarize(grouped)

throughput_path = os.path.join(base_dir, "throughputs.txt")
throughput_avg = parse_throughput_file(throughput_path)

summary_df = attach_throughput(summary_df, throughput_avg)
summary_df.sort_values(by=["threads", "streams"], inplace=True)

# Save output
csv_path = os.path.join(base_dir, f"{mode}_summary_table.csv")
json_path = os.path.join(base_dir, f"{mode}_summary_table.json")
summary_df.to_csv(csv_path, index=False)
summary_df.to_json(json_path, orient="records", indent=2)

print(f"Saved summary to:\n- {csv_path}\n- {json_path}")
