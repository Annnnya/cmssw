import pandas as pd
import matplotlib.pyplot as plt
import os

# ==== INPUT FILES ====

files = [
    {"local-remote_t-s-c_different-sockets": "/data/user/apolova/dev2/CMSSW_15_0_0/src/HeterogeneousCore/MPICore/test/test_results_thesis/local-remote_t-s-c_different-sockets/local_summary_table.csv"},
    {"local-remote_t-s-c_remote_oversub": "/data/user/apolova/dev2/CMSSW_15_0_0/src/HeterogeneousCore/MPICore/test/test_results_thesis/local-remote_t-s-c_remote_oversub/remote_4/local_summary_table.csv"},
    {"local-remote_t-s-c_same_cores": "/data/user/apolova/dev2/CMSSW_15_0_0/src/HeterogeneousCore/MPICore/test/test_results_thesis/local-remote_t-s-c_same_cores/local_summary_table.csv"},
    {"whole_hlt_t-s-c": "/data/user/apolova/dev2/CMSSW_15_0_0/src/HeterogeneousCore/MPICore/test/test_results_thesis/whole_hlt_t-s-c/whole_summary_table.csv"},
    {"milan-genoa_t-s-c_over_ib": "/data/user/apolova/dev2/CMSSW_15_0_0/src/HeterogeneousCore/MPICore/test/test_results_thesis/milan-genoa_ucx_t-s-c/local_summary_table.csv"}
]

output_dir = "./comparative_plots_sync"

# ==== READ & PREPARE DATA ====

dfs = []

for file_info in files:
    type_name, path = next(iter(file_info.items()))
    try:
        df = pd.read_csv(path)
        df["type"] = type_name
        dfs.append(df)
    except Exception as e:
        print(f"❌ Error reading {path}: {e}")

# Combine all available DataFrames
if not dfs:
    print("No valid files found. Exiting.")
    exit(1)

df = pd.concat(dfs)

# Create output directory if it doesn't exist
os.makedirs(output_dir, exist_ok=True)

# ==== PLOTTING FUNCTIONS ====

def make_plot(y_column, ylabel, title, filename, max_threads=None):
    plt.figure()
    for t in df['type'].unique():
        sub = df[df['type'] == t]
        if max_threads is not None:
            sub = sub[sub['threads'] <= max_threads]
        plt.plot(sub['threads'], sub[y_column], marker='o', label=t)

    plt.xlabel("Threads")
    plt.ylabel(ylabel)
    plt.title(title)
    plt.legend()
    plt.grid(True)
    plt.savefig(os.path.join(output_dir, filename))
    plt.close()

# ==== MAKE PLOTS ====

make_plot("throughput_ev_per_s", "Throughput (ev/s)", "Throughput vs Threads", "throughput_vs_threads.png", max_threads=64)
make_plot("total_real", "Total Real Time per Event", "Total Real Time per Event vs Threads", "total_real_vs_threads.png", max_threads=64)
make_plot("total_cpu", "Total CPU Time per Event", "Total CPU Time per Event vs Threads", "total_cpu_vs_threads.png", max_threads=64)

print("✅ Plots saved to:", output_dir)
