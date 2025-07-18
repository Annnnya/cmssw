import pandas as pd
import matplotlib.pyplot as plt
import os

# ==== INPUT FILES ====

files = [
    # {"demo": "/data/user/apolova/dev1/CMSSW_15_0_0/src/HeterogeneousCore/MPICore/test/test_results_thesis/sync/milan-genoa_ucx_t-s-c/local_summary_table.csv"},
    # {"async": "/data/user/apolova/dev1/CMSSW_15_0_0/src/HeterogeneousCore/MPICore/test/test_results_thesis/simple_async/milan-genoa_ucx_t-s-c/local_summary_table.csv"},
    # {"one-sided": "/data/user/apolova/dev1/CMSSW_15_0_0/src/HeterogeneousCore/MPICore/test/test_results_thesis/one-sided/milan-genoa_ucx_t-s-c/local_summary_table.csv"},
    {"whole": "/data/user/apolova/dev1/CMSSW_15_0_0/src/HeterogeneousCore/MPICore/test/test_results_thesis/whole_hlt_t-s-c/whole_summary_table.csv"},
    {"metadata": "/data/user/apolova/dev1/CMSSW_15_1_0_pre3/src/HeterogeneousCore/MPICore/test/test_results/mpich/metadata_initilization/milan-genoa_ucx_t-s-c/local_summary_table.csv"},
    {"sync": "/data/user/apolova/dev1/CMSSW_15_1_0_pre3/src/HeterogeneousCore/MPICore/test/test_results/mpich/simple_sync_rebased/milan-genoa_ucx_t-s-c/local_summary_table.csv"},
    # {"number of products mpich": "/data/user/apolova/dev1/CMSSW_15_0_0/src/HeterogeneousCore/MPICore/test/test_results_thesis/mpich/async_number_of_products/local-remote_t-s-c_different-sockets/local_summary_table.csv"},
    # {"mpich async number of products": "/data/user/apolova/dev1/CMSSW_15_0_0/src/HeterogeneousCore/MPICore/test/test_results_thesis/mpich/async_number_of_products/milan-genoa_ucx_t-s-c/local_summary_table.csv"},
    {"number of products with ssend": "/data/user/apolova/dev1/CMSSW_15_1_0_pre3/src/HeterogeneousCore/MPICore/test/test_results/mpich/number_of_products_rebased/milan-genoa_ucx_t-s-c/local_summary_table.csv"},
    {"one_buffer_serialize": "/data/user/apolova/dev1/CMSSW_15_1_0_pre3/src/HeterogeneousCore/MPICore/test/test_results/mpich/one_buffer_serialize/milan-genoa_ucx_t-s-c/local_summary_table.csv"}
]

output_dir = "./milan-genoa-comparative_plots"

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

import numpy as np

def make_histogram_throughput(df, output_path):
    import matplotlib.pyplot as plt
    import numpy as np

    grouped = df.groupby('threads')
    types = df['type'].unique()
    threads = sorted(df['threads'].unique())

    bar_width = 0.1
    num_types = len(types)
    x = np.arange(len(threads))  # Base x locations for thread groups

    plt.figure(figsize=(max(12, num_types), 6))

    for i, t in enumerate(types):
        sub = df[df['type'] == t]
        sub = sub.set_index('threads')  # for easy lookup

        heights = []
        errors = []
        for th in threads:
            if th in sub.index:
                row = sub.loc[th]
                heights.append(row['throughput_ev_per_s'])
                errors.append(row['throughput_error'] if 'throughput_error' in row and not pd.isna(row['throughput_error']) else 0)
            else:
                heights.append(0)
                errors.append(0)

        # Bar positions: shift each type's bar within the group
        x_pos = x + i * bar_width
        if any(errors):
            plt.bar(x_pos, heights, bar_width, label=t, yerr=errors, capsize=3)
        else:
            plt.bar(x_pos, heights, bar_width, label=t)

    # X-ticks in the middle of each group
    plt.xticks(x + (num_types - 1) * bar_width / 2, threads)
    plt.xlabel("Threads")
    plt.ylabel("Throughput (ev/s)")
    plt.title("Throughput per Thread Count (Grouped by Approach)")
    plt.legend(bbox_to_anchor=(1.02, 1), loc='upper left', fontsize='small')
    plt.tight_layout()

    plt.savefig(os.path.join(output_path, "throughput_histogram.png"))
    plt.close()


def make_plot(y_column, ylabel, title, filename, max_threads=None):
    plt.figure(figsize=(10, 8))  # Slightly taller to fit legend
    for t in df['type'].unique():
        sub = df[df['type'] == t]
        if max_threads is not None:
            sub = sub[sub['threads'] <= max_threads]

        x = sub['threads']
        y = sub[y_column]

        # Use error bars if plotting throughput with available error
        if y_column == "throughput_ev_per_s" and "throughput_error" in sub:
            yerr = sub['throughput_error']
            plt.errorbar(x, y, yerr=yerr, marker='o', label=t, capsize=3)
        else:
            plt.plot(x, y, marker='o', label=t)

    plt.xlabel("Threads")
    plt.ylabel(ylabel)
    plt.title(title)
    plt.grid(True)

    # Move legend below
    plt.legend(loc='upper center', bbox_to_anchor=(0.5, -0.2), ncol=2, fontsize='small', frameon=False)

    # Adjust layout so everything fits
    plt.tight_layout(rect=[0, 0.2, 1, 1])

    plt.savefig(os.path.join(output_dir, filename), bbox_inches='tight')
    plt.close()


# ==== MAKE PLOTS ====
make_histogram_throughput(df, output_dir)



print("✅ Plots saved to:", output_dir)