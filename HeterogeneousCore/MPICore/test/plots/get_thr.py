#!/usr/bin/env python3

import re
import csv
import statistics
import argparse
from collections import defaultdict
from math import sqrt
from pathlib import Path


def parse_log(log_file_path: Path):
    """
    Returns a list of entries:
    (run_id, threads, streams, throughput)
    """
    entries = []

    current_run = None
    current_threads = None
    current_streams = None

    with log_file_path.open("r") as f:
        for line in f:
            # Run line
            if "Run #" in line:
                m = re.search(r"Run #(\d+) for t(\d+)s(\d+)", line)
                if m:
                    current_run = int(m.group(1))
                    current_threads = int(m.group(2))
                    current_streams = int(m.group(3))

            # Throughput line
            if "throughput" in line:
                m = re.search(
                    r"throughput[^0-9\-+]*([-+]?\d+(?:\.\d+)?)",
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
        values.sort(key=lambda x: x[0])  # sort by run id

        # discard warmup run
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


def write_csv(summary, output_path: Path):
    fieldnames = [
        "threads",
        "streams",
        "throughput_ev_per_s",
        "throughput_error"
    ]

    with output_path.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(
            sorted(summary, key=lambda x: (x["threads"], x["streams"]))
        )


# === MAIN ===

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Parse CMSSW throughput logs and produce CSV summary"
    )
    parser.add_argument(
        "logfile",
        type=Path,
        help="Path to the input log file"
    )

    args = parser.parse_args()

    log_file = args.logfile
    if not log_file.exists():
        raise FileNotFoundError(f"Input file does not exist: {log_file}")

    # output path: test_results/<input_name>.csv
    output_dir = Path("../../test_results")
    output_dir.mkdir(parents=True, exist_ok=True)

    output_csv = output_dir / (log_file.stem + ".csv")

    entries = parse_log(log_file)
    summary = summarize(entries)
    write_csv(summary, output_csv)

    print(f"✅ Saved CSV to {output_csv}")
