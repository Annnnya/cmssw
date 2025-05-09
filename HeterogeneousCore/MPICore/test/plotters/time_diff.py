import pandas as pd

path_mpich_as = "/data/user/apolova/dev1/CMSSW_15_0_0/src/HeterogeneousCore/MPICore/test/test_results_thesis/mpich/simple_async/milan-genoa_ucx_t-s-c/local_summary_table.csv"
path_mpich_s = "/data/user/apolova/dev1/CMSSW_15_0_0/src/HeterogeneousCore/MPICore/test/test_results_thesis/mpich/sync/milan-genoa_ucx_t-s-c/local_summary_table.csv"
path_openmpi_s = "/data/user/apolova/dev1/CMSSW_15_0_0/src/HeterogeneousCore/MPICore/test/test_results_thesis/milan-genoa_ucx_t-s-c/local_summary_table.csv"
path_openmpi_as = "/data/user/apolova/dev1/CMSSW_15_0_0/src/HeterogeneousCore/MPICore/test/test_results_thesis/simple_async/milan-genoa_ucx_t-s-c/local_summary_table.csv"
path_whole = "/data/user/apolova/dev1/CMSSW_15_0_0/src/HeterogeneousCore/MPICore/test/test_results_thesis/whole_hlt_t-s-c/whole_summary_table.csv"

df_mpich_as = pd.read_csv(path_mpich_as)
df_mpich_s = pd.read_csv(path_mpich_s)
df_openmpi_s = pd.read_csv(path_openmpi_s)
df_openmpi_as = pd.read_csv(path_openmpi_as)
df_whole = pd.read_csv(path_whole)

dfs = {
    "MPICH Async": df_mpich_as[['threads', 'total_real']],
    "MPICH Sync": df_mpich_s[['threads', 'total_real']],
    "OpenMPI Sync": df_openmpi_s[['threads', 'total_real']],
    "OpenMPI Async": df_openmpi_as[['threads', 'total_real']],
    "Whole HLT": df_whole[['threads', 'total_real']]
}

merged = dfs['Whole HLT'].rename(columns={'total_real': 'Whole HLT'})

for label, df in dfs.items():
    if label == "Whole HLT":
        continue
    merged = pd.merge(merged, df.rename(columns={'total_real': label}), on='threads', how='inner')

for label in ["MPICH Async", "MPICH Sync", "OpenMPI Sync", "OpenMPI Async"]:
    merged[f"{label} Diff"] = merged[label] - merged['Whole HLT']

output_cols = ['threads'] + [f"{label} Diff" for label in ["MPICH Async", "MPICH Sync", "OpenMPI Sync", "OpenMPI Async"]]
table = merged[output_cols]

table = table.round(2)

lines = []
lines.append("\\begin{tabular}{lrrrr}")
lines.append("\\toprule")
lines.append("Threads & MPICH Async & MPICH Sync & OpenMPI Sync & OpenMPI Async \\\\ \\midrule")

for _, row in table.iterrows():
    line = f"{int(row['threads'])} & {row['MPICH Async Diff']:.2f} & {row['MPICH Sync Diff']:.2f} & {row['OpenMPI Sync Diff']:.2f} & {row['OpenMPI Async Diff']:.2f} \\\\"
    lines.append(line)

lines.append("\\bottomrule")
lines.append("\\end{tabular}")

latex_output = "\n".join(lines)

with open("comparison_real_time_differences.tex", "w") as f:
    f.write(latex_output)