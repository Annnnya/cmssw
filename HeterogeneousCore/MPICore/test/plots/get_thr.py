import re
import csv
import statistics
from collections import defaultdict
from math import sqrt


def parse_log(log_file_path: str):
    """
    Returns a list of entries:
    (run_id, threads, streams, throughput)
    """
    entries = []

    current_run = None
    current_threads = None
    current_streams = None

    with open(log_file_path, 'r') as f:
        for line in f:
            # Run line
            if 'Run #' in line:
                m = re.search(r'Run #(\d+) for t(\d+)s(\d+)', line)
                if m:
                    current_run = int(m.group(1))
                    current_threads = int(m.group(2))
                    current_streams = int(m.group(3))

            # Throughput line
            if 'throughput' in line:
                m = re.search(
                    r'throughput[^0-9\-+]*([-+]?\d+(?:\.\d+)?)',
                    line
                )
                if m and current_run is not None:
                    throughput = float(m.group(1))
                    entries.append(
                        (current_run, current_threads, current_streams, throughput)
                    )

    return entries


def summarize(entries):
    """
    Group by (threads, streams),
    discard warmup run,
    compute mean + SEM
    """
    grouped = defaultdict(list)

    for run, th, st, thr in entries:
        grouped[(th, st)].append((run, thr))

    summary = []

    for (th, st), values in grouped.items():
        # sort by run id
        values.sort(key=lambda x: x[0])

        # discard warmup
        valid = [v[1] for v in values[1:]]

        if len(valid) < 2:
            continue

        mean = sum(valid) / len(valid)
        std = statistics.stdev(valid)
        sem = std / sqrt(len(valid))

        summary.append({
            "threads": th,
            "streams": st,
            "throughput_ev_per_s": mean,
            "throughput_error": sem
        })

    return summary


def write_csv(summary, output_path):
    fieldnames = [
        "threads",
        "streams",
        "throughput_ev_per_s",
        "throughput_error"
    ]

    with open(output_path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(sorted(summary, key=lambda x: (x["threads"], x["streams"])))


# === MAIN ===

if __name__ == "__main__":
    log_file = "../test_results/log_multiple_controllers.txt"
    output_csv = "../test_results/summary_mc.csv"

    entries = parse_log(log_file)
    summary = summarize(entries)
    write_csv(summary, output_csv)

    print(f"✅ Saved CSV to {output_csv}")
