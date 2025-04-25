# plot_dummy_results.py

import pandas as pd
import matplotlib.pyplot as plt
import os

experiment_name = "synchronous_thread-stream-core"
mode = "local"

df = pd.read_csv(f"../{experiment_name}/{mode}_summary_table.csv")

# Make nicer labels
df["config"] = df["threads"].astype(str) + "x" + df["streams"].astype(str)
df["numa"] = df["local_numa"].astype(str) + "-" + df["remote_numa"].astype(str)

# Metrics to plot
time_metrics = {
    "recv_cpu": "Receiver CPU Time / event",
    "recv_real": "Receiver Real Time / event",
    "total_cpu": "Total CPU Time / event",
    "total_real": "Total Real Time / event"
}

# Output folder
plot_dir = f"../{experiment_name}/plots_{mode}"
os.makedirs(plot_dir, exist_ok=True)

# Loop over comm types and plot one plot per metric
for comm_type in df["comm"].unique():
    df_comm = df[df["comm"] == comm_type]
    for metric, label in time_metrics.items():
        plt.figure(figsize=(10, 6))
        for numa, group in df_comm.groupby("numa"):
            group_sorted = group.sort_values(by=["threads", "streams"])
            plt.plot(group_sorted["config"], group_sorted[metric], label=f"NUMA {numa}", marker='o')
        plt.title(f"{label} vs Threads x Streams [{comm_type}]")
        plt.xlabel("Threads x Streams")
        plt.ylabel(label)
        plt.legend()
        plt.grid(True)
        plt.tight_layout()
        plt.savefig(os.path.join(plot_dir, f"{comm_type}_{metric}.png"))
        plt.close()

print(f"Saved plots to {plot_dir}")
