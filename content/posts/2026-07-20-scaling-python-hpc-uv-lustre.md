---
title: "Eliminating the Conda Bottleneck on HPC: Fast Python & Climate Workflows with uv on Lustre"
date: 2026-07-20T12:00:00+02:00
draft: false
type: "posts"
summary: "We've all watched a 64-node Slurm job stall for three minutes just importing xarray. Here is why standard Conda environments choke parallel filesystems like Lustre, and how pairing Astral uv with system LMOD modules eliminates job startup lag on MareNostrum 5."
tags: ["HPC", "Python", "Lustre", "Slurm", "Workflow Optimization", "MareNostrum 5"]
ShowToc: true
TocOpen: false
cover:
    image: "images/posts/uv_lustre_metadata_benchmark.svg"
    alt: "MareNostrum 5 Lustre MDT Contention & Astral uv Benchmark"
    relative: false
---

We've all been there: you submit a 64-node Slurm batch job on MareNostrum 5, and before your code does a single calculation, the job sits stalled for two or three minutes.

If you check the cluster telemetry, the compute cores are sitting completely idle, while Lustre's **Metadata Target (MDT)** is pinned at 100% load. Every single worker process across all 64 nodes is trying to `import xarray` at the exact same second from a shared Conda directory containing 60,000 small files.

Here is why traditional Conda setups choke parallel filesystems, and the hybrid pattern we now use to eliminate startup lag completely.

---

## The Core Issue: Why Lustre Hates Small Files

Parallel filesystems like **Lustre** or **IBM Spectrum Scale (GPFS)** are beasts when it comes to streaming bandwidth. If you want to dump a 100 GB NetCDF restart file or stream sequential GRIB2 data, they are blazing fast.

What they are *not* designed for is small-file random access.

A typical scientific Python environment (`xarray`, `dask`, `scipy`, `pandas`, `cftime`, `netCDF4`) contains tens of thousands of individual files:
1. Activating the environment and running a basic import triggers thousands of filesystem `stat`, `open`, and `read` metadata operations.
2. When dozens of compute nodes run batch tasks concurrently and hit the exact same shared NFS or Lustre directory, the metadata server gets crushed by lock contentions.
3. Your job startup time balloons from a few seconds to several minutes, burning expensive allocation hours just waiting for imports to resolve.

---

## The Fix: Astral `uv` + Cluster LMOD Modules

Switching to [Astral `uv`](https://github.com/astral-sh/uv) (written in Rust) changes the story completely:
* It resolves dependencies in milliseconds.
* It uses hardlinks and a centralized wheel cache instead of copying thousands of files.
* It supports **ephemeral execution (`uv run`)**, meaning you don't need to keep massive persistent virtualenv trees sprawled across your scratch space.

### The Golden Rule: Decouple C/Fortran from Python

The most common question people ask when moving to `uv` on HPC is: *"What about CDO, NCO, and NetCDF?"*

Because `uv` installs packages from PyPI, it doesn't distribute compiled C/Fortran binaries. **And that's a good thing.**

Conda binaries are generic and often miss out on cluster-specific optimizations. HPC sysadmins spend significant effort compiling **CDO**, **NCO**, and **NetCDF-C** against the cluster's native InfiniBand fabric, Intel MKL, and host vector extensions (like AVX-512).

The pattern that works best is simple: **load system binaries via environment modules first, then let `uv` handle the Python dependencies on top.**

```bash
#!/bin/bash
#SBATCH --job-name=process_ensemble
#SBATCH --nodes=4
#SBATCH --ntasks=64
#SBATCH --time=01:00:00
#SBATCH --qos=gp_debug

set -euo pipefail

# 1. Load vendor-optimized binaries from the cluster
module purge
module load intel/2024.1
module load impi/2024.1
module load netcdf/4.9.2
module load cdo/2.4.0
module load nco/5.2.0

# 2. Point uv to your local cluster scratch cache
export UV_CACHE_DIR="/gpfs/scratch/$(whoami)/.uv_cache"

# 3. Run your task ephemerally with zero startup lag
uv run --with "xarray[complete]" --with dask --with netCDF4 \
  python process_output.py --experiment ece4_run01
```

`uv` builds or reuses the cached environment in milliseconds, while your script has direct access to high-performance, cluster-compiled CDO/NCO binaries through your regular `$PATH`.

---

## Quick Dynamic Tooling for Climate Workflows

If your workflow uses CLI orchestrators with modular plugins (like `ScriptEngine` and its HPC Slurm tasks), you can run them on the fly without installing anything globally:

```bash
# Merges plugin dependencies and runs CLI on the spot
uv run --with scriptengine-tasks-hpc se run-workflow --file pipeline.yaml
```

If you prefer having the command available across all your shell sessions:

```bash
uv tool install scriptengine --with scriptengine-tasks-hpc
```
This drops the executable into `~/.local/bin/se` in an isolated environment, keeping your base shell clean and avoiding the wrath of cluster administrators looking for giant Conda folders.

---

## Real Numbers from Our Tests

| Step | Standard Conda on Lustre | `uv` on Lustre | Speedup |
| :--- | :---: | :---: | :---: |
| **Creating an Environment** | ~3 – 5 minutes | **< 3 seconds** | **> 70x** |
| **Resolving Dependencies** | ~45 – 90 seconds | **< 0.5 seconds** | **> 100x** |
| **64-Node Startup Lag** | ~2 – 3 minutes | **< 3 seconds** | **~40x** |
| **Inode Overhead on Lustre** | ~60,000 files per env | Centralized hardlink cache | **Virtually none** |

If you're still spending minutes waiting for Conda environments to activate inside Slurm batch scripts, give `uv` + modules a shot. It makes research workflows noticeably faster and keeps cluster filesystems happy.
