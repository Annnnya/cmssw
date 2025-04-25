

single node, single process:
  - milan
  - hlt_single.py
  - 1, 2, 4, 8, 16, 24, 32, 64 threads and streams
    - 0             #  1 physical core
    - 0-1
    - 0-3
    - 0-7
    - 0-15
    - 0-23
    - 0-31          # 32 physical cores


single node, two processes, on the same cores
  - milan
  - hlt_local.py / hlt_remote.py
  - 1, 2, 4, 8, 16, 24, 32, 64 threads and streams
    - 0             #  1 physical core
    - 0-1
    - 0-3
    - 0-7
    - 0-15
    - 0-23
    - 0-31          # 32 physical cores


single node, two processes, on different sockets
  - milan
  - hlt_local.py / hlt_remote.py
  - 1, 2, 4, 8, 16, 24, 32, 64 threads and streams
    - 0 / 64        #  1 physical core
    - 0-1 / 64-65
    - 0-3 / ...
    - 0-7
    - 0-15
    - 0-23
    - 0-31 / 64-95  # 32 physical cores

  - for 32, investigate overcommit
    - local:  32 cores / 32 threads / 32 streams
    - remote:  8 cores / 32 threads / 32 streams


two nodes, two processes, on different nodes
  - milan / genoa
  - hlt_local.py / hlt_remote.py
  - 1, 2, 4, 8, 16, 24, 32, 64 threads and streams
    - 0             #  1 physical core
    - 0-1
    - 0-3
    - 0-7
    - 0-15
    - 0-23
    - 0-31          # 32 physical cores

  - for 32, investigate overcommit
    - local:  32 cores / 32 threads / 32 streams
    - remote:  8 cores / 32 threads / 32 streams

---

types of links

  - infiniband
    - milan: mlx5_3
    - genoa: mlx5_4
    - pml ucx

  - slow ethernet
    - milan: eno8303
    - genoa: enp34s0f0
    - pml ob1, btl tcp

*** reconfigure cards in RoCE mode ***

  - roce
    - milan: mlx5_3
    - genoa: mlx5_4
    - pml ucx

  - tcp
    - milan: mlx5_3
    - genoa: mlx5_4
    - pml ob1, btl tcp


---

software implementations

  - synchronous
  - asynchronous v1
  - asynchronous v2
