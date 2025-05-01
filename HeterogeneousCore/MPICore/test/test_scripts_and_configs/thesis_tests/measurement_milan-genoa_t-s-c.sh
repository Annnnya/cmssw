#!/bin/bash

# Number of runs per test (first can be treated as warm-up)
runs=6

# Threads/Streams combinations to test
thread_stream_combos=("1:1" "4:4" "8:8" "16:16" "24:24" "32:32")

# Message sizes in bytes
message_sizes=(4 1024 $((1024*1024))) # 4B, 1KB, 1MB

# Scripts to run
script_local="dummy_configs/dummy_local_3send.py"
script_remote="dummy_configs/dummy_remote_3rec.py"

# Base directory for logs
BASE_DIR="../../test_results_thesis/dummy/mpich/sync/remote_different_sockets"
mkdir -p "$BASE_DIR"

# Hostnames
remote_host="gputest-genoa-02.cms"
local_host="gputest-milan-02.cms"

# Interfaces and UCX devices
remote_ucx_dev="mlx5_4:1"
local_ucx_dev="mlx5_3:1"

# Resolve absolute base dir
absolute_base_dir=$(realpath "$BASE_DIR")

# Path to MPICH mpirun
MPIRUN=/nfshome0/apolova/mpich-4.3.0-install/bin/mpirun

for message_size in "${message_sizes[@]}"; do
    echo "=== Testing MESSAGE_SIZE=$message_size ==="
    export MESSAGE_SIZE=$message_size

    for combo in "${thread_stream_combos[@]}"; do
        IFS=':' read -r threads streams <<< "$combo"

        end_core=$((threads - 1))

        TEST_DIR="$BASE_DIR/test_m${message_size}_t${threads}s${streams}"
        absolute_test_dir="$absolute_base_dir/test_m${message_size}_t${threads}s${streams}"

        mkdir -p "$TEST_DIR"
        ssh "$remote_host" "mkdir -p $absolute_test_dir"

        echo "=== Running tests with ${threads} threads, ${streams} streams, message size ${message_size} bytes, CPUs: 0-$end_core ==="

        for i in $(seq 1 $runs); do
            echo "Run #$i for m${message_size}_t${threads}s${streams} on CPU list: 0-$end_core"

            run_id=$i
            exp_threads=$threads
            exp_streams=$streams
            exp_name="dummy_remote_m${message_size}_t${threads}s${streams}_r${i}"
            exp_output_dir="$absolute_test_dir"
            throughput_log_file="$absolute_base_dir/throughputs.txt"

            $MPIRUN \
                -hosts "$remote_host","$local_host" \
                -np 1 \
                -env UCX_TLS rc_x,ud_x,self,shm \
                -env LD_LIBRARY_PATH "$LD_LIBRARY_PATH" \
                -env UCX_NET_DEVICES "$remote_ucx_dev" \
                -env RUN_ID "$run_id" \
                -env EXPERIMENT_THREADS "$exp_threads" \
                -env EXPERIMENT_STREAMS "$exp_streams" \
                -env EXPERIMENT_NAME "$exp_name" \
                -env EXPERIMENT_OUTPUT_DIR "$exp_output_dir" \
                -env THROUGHPUT_LOG_FILE "$throughput_log_file" \
                -env MESSAGE_SIZE "$message_size" \
                numactl --physcpubind=0-"${end_core}" cmsRun "$script_remote" \
                : \
                -np 1 \
                -env UCX_TLS rc_x,ud_x,self,shm \
                -env LD_LIBRARY_PATH "$LD_LIBRARY_PATH" \
                -env UCX_NET_DEVICES "$local_ucx_dev" \
                -env RUN_ID "$run_id" \
                -env EXPERIMENT_THREADS "$exp_threads" \
                -env EXPERIMENT_STREAMS "$exp_streams" \
                -env EXPERIMENT_NAME "$exp_name" \
                -env EXPERIMENT_OUTPUT_DIR "$exp_output_dir" \
                -env THROUGHPUT_LOG_FILE "$throughput_log_file" \
                -env MESSAGE_SIZE "$message_size" \
                numactl --physcpubind=0-"${end_core}" cmsRun "$script_local"
        done

        echo "✅ Completed tests for threads=$threads, streams=$streams, message size=$message_size bytes"
    done
done

echo "✅ All cross-machine dummy tests completed!"
