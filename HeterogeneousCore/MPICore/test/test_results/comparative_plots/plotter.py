import pandas as pd
import matplotlib.pyplot as plt
import os

# Paths to input CSVs and output directory
file1 = "/data/user/apolova/dev2/CMSSW_15_0_0/src/HeterogeneousCore/MPICore/test/test_results/synchronous_thread-stream-core/local_summary_table.csv"
file2 = "/data/user/apolova/dev2/CMSSW_15_0_0/src/HeterogeneousCore/MPICore/test/test_results/plain_hlt_dependence_within_socket_thread-stream-core/local_summary_table.csv"
file3 = "/data/user/apolova/dev2/CMSSW_15_0_0/src/HeterogeneousCore/MPICore/test/test_results/plain_hlt_thread-stream-core/local_summary_table.csv"
file4 = "/data/user/apolova/dev2/CMSSW_15_0_0/src/HeterogeneousCore/MPICore/test/test_results/synchronous_thread-stream-core_1_socket_oversub/local_summary_table.csv"
output_dir = "/data/user/apolova/dev2/CMSSW_15_0_0/src/HeterogeneousCore/MPICore/test/test_results/comparative_plots"

# Read the CSVs
df1 = pd.read_csv(file1)
df2 = pd.read_csv(file2)
df3 = pd.read_csv(file3)
df4 = pd.read_csv(file4)


# Add a column to distinguish them
df1["type"] = "synchronous mpi adding hardware threads first"
df2["type"] = "original pipeline adding separate cpus first"
df3["type"] = "original pipeline adding hardware threads first"
df4["type"] = "synchronous mpi adding separate cpus first"

# Combine
df = pd.concat([df1, df2, df3, df4])

# Create output directory if it doesn't exist
os.makedirs(output_dir, exist_ok=True)

# Plot throughput vs threads
def make_plot(y_column, ylabel, title, filename):
    plt.figure()
    for t in df['type'].unique():
        sub = df[df['type'] == t]
        plt.plot(sub['threads'], sub[y_column], marker='o', label=t)
    # plt.axvline(x=64, color='gray', linestyle='--', linewidth=1)  # Vertical line at 64
    plt.xlabel("Threads")
    plt.ylabel(ylabel)
    plt.title(title)
    plt.legend()
    plt.grid(True)
    plt.savefig(os.path.join(output_dir, filename))
    plt.close()

def make_plot_64(y_column, ylabel, title, filename):
    plt.figure()
    for t in df['type'].unique():
        sub = df[(df['type'] == t) & (df['threads'] <= 64)]  # filter out threads > 64
        plt.plot(sub['threads'], sub[y_column], marker='o', label=t)
    plt.xlabel("Threads")
    plt.ylabel(ylabel)
    plt.title(title)
    plt.legend()
    plt.grid(True)
    plt.savefig(os.path.join(output_dir, filename))
    plt.close()

# Create plots
make_plot_64("throughput_ev_per_s", "Throughput (ev/s)", "Throughput vs Threads", "throughput_vs_threads.png")
make_plot_64("total_real", "Total Real Time per Event", "Total Real Time per Event vs Threads", "total_real_vs_threads.png")
make_plot_64("total_cpu", "Total CPU Time per Event", "Total CPU Time per Event vs Threads", "total_cpu_vs_threads.png")