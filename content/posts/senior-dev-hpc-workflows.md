---
title: "Running Decadal Climate Ensembles on Tier-0 HPC: Autosubmit DAGs, Lustre Striping, and Cluster Telemetry"
date: 2026-05-04T19:00:00+02:00
draft: false
type: "posts"
math: true
summary: "Engineering lessons from managing multi-member Earth system model ensembles on MareNostrum 5: orchestrating DAGs with Autosubmit, tuning Lustre striping for NetCDF outputs, and NUMA-aware MPI rank placement."
tags: ["HPC", "Autosubmit", "MareNostrum 5", "Slurm", "Lustre", "EC-Earth", "Climate Modeling"]
ShowToc: true
TocOpen: false
cover:
    image: "images/posts/hpc_ensemble_dag_architecture.svg"
    alt: "MareNostrum 5 Autosubmit Ensemble DAG Architecture"
    relative: false
---

When running a single coupled Earth System Model experiment (like EC-Earth4 with OpenIFS atmosphere and NEMO4 ocean), the setup is reasonably predictable: you allocate your compute nodes, launch the coupled executable via `srun`, and monitor simulated years per day (SYPD).

The real engineering challenges start when you scale up to **decadal prediction campaigns**: running 30 to 100 ensemble members across 60-year hindcast windows. At this scale, you are not managing a simulation—you are operating a high-throughput factory on a shared supercomputer (in our case, MareNostrum 5 at BSC). Under cluster capacity constraints and aggressive wallclocks, small inefficiencies compound rapidly into lost allocations, deadlocks, and corrupted restart states.

Here are four hard-won engineering patterns from the trenches of Tier-0 ensemble operations.

---

### 1. From Brittle Shell Loops to Directed Acyclic Graphs (DAGs)

In early-stage modeling projects, people frequently automate ensemble sweeps using nested bash loops that fire `sbatch` scripts. While intuitive for 2 or 3 test runs, this pattern breaks disastrously at scale:
- If member `04` encounters an MPI rank hang at time step 4200 due to a single-node memory ECC glitch, the loop either halts completely or blindly launches downstream post-processing jobs against corrupted half-written files.
- Resuming failed runs requires manual inspection of log files, manually adjusting restart date namelists, and re-submitting dependent jobs.

```
       [Atmospheric Init / Preproc]
                   │
                   ▼
       [Oceanic Restart Remap / Nudge]
                   │
                   ▼
     ┌─────────────┴─────────────┐
     ▼                           ▼
[Sim Chunk 1 (Atm)]         [Sim Chunk 1 (Ocean)]
     │                           │
     └─────────────┬─────────────┘
                   ▼
       [Coupled Checkpoint / Sync]
                   │
       ┌───────────┴───────────┐
       ▼                       ▼
 [CMOR / Postproc]        [Sim Chunk 2...]
```

In our production workflows at BSC, we orchestrate these campaigns as **Directed Acyclic Graphs (DAGs)** managed by **Autosubmit**:
1. **Deterministic Leg Chunking:** Long integrations are split into discrete temporal chunks (typically 1 month to 1 year per leg).
2. **Dynamic Dependency Tracking:** Post-processing, diagnostics, and archiving tasks depend strictly on the clean completion and hash verification of the corresponding simulation chunk.
3. **Automatic Wallclock Recovery:** If a chunk hits the Slurm wallclock limit during a slow checkpoint, Autosubmit detects the timeout, rolls back the unfinalized outputs, and resubmits from the last bit-for-bit valid restart without human intervention.

---

### 2. Lustre Storage Contention: Striping vs. Metadata Floods

MareNostrum 5’s GPFS and Lustre parallel filesystems are engineered for extreme aggregate bandwidth (multi-terabyte/s streaming). However, parallel filesystems have an Achilles' heel: **Metadata Operations (MDS contention)**.

When 60 concurrent ensemble members simultaneously open hundreds of small diagnostic NetCDF files, write history logs, and query filesystem attributes at each timestep:
$$\text{Metadata IOPS} \propto N_{\text{members}} \times N_{\text{files}} \times f_{\text{sync}}$$
The Metadata Target (MDT) locks up. Jobs spend 30–45% of their allocation time blocked in `I/O wait` (uninterruptible sleep `D` state), drastically pulling down cluster-wide throughput.

**The Fix:**
1. **Pre-allocating Lustre Striping:** For multi-gigabyte coupled restart files (`restart_openifs.nc`, `restart_nemo.nc`), we stripe across multiple Object Storage Targets (OSTs) before writing:
   ```bash
   # Stripe large restart directories across 8 OSTs with 4MB chunk size
   lfs setstripe -c 8 -S 4M ./output/restarts/
   ```
   For small diagnostic files and logs, we enforce single-stripe (`-c 1`) to eliminate OST lock negotiation.
2. **Node-Local Scratch Buffering:** We route all high-frequency runtime logs (`fort.4`, `stdout`, `output.txt`) to local NVMe node scratch (`$TMPDIR`) during execution, tarring and streaming them to shared storage only upon chunk completion.

---

### 3. NUMA-Aware Rank Placement on Sapphire Rapids

MareNostrum 5 General Purpose Partition (GPP) nodes feature dual-socket Intel Xeon Platinum 8480+ processors (112 physical cores per node, split across multiple Sub-NUMA Clustering (SNC) domains).

In hybrid OpenMP/MPI models like OpenIFS, default Slurm CPU affinity often spreads MPI ranks carelessly across socket boundaries. This results in heavy inter-socket UPI traffic during the spectral transform phase (`trans` library), where Legendre transforms and Fast Fourier Transforms (FFTs) hammer memory bandwidth.

By profiling with Darshan and perf, we identified that improper NUMA affinity was penalizing our OpenIFS SYPD by nearly 14%.

**Production Slurm Pinning Recipe:**
```bash
#SBATCH --nodes=8
#SBATCH --ntasks-per-node=56
#SBATCH --cpus-per-task=2
#SBATCH --distribution=block:cyclic

export OMP_NUM_THREADS=2
export OMP_PLACES=cores
export OMP_PROC_BIND=close
export I_MPI_PIN_DOMAIN=auto
```
Binding threads closely to local NUMA cores and distributing MPI tasks cyclically across sockets ensures memory buffers for halo exchanges and matrix operations stay strictly within the local memory controller domain.

---

### 4. High-Throughput Edge Transfers without Crashing Gateways

At the conclusion of a 60-year ensemble campaign, we typically have 40–80 TB of raw NetCDF output that must be transferred from fast Tier-0 scratch to long-term storage or institutional data repositories (e.g., EUDAT or BSC archive).

Using a simple `scp` or naive `rsync -av` over cluster login nodes is forbidden on production HPC: it chokes shared network gateways and drops silently if the SSH session disconnects after 12 hours.

**The Production Transfer Protocol:**
1. **Dedicated Data Transfer Nodes (DTNs):** Never sync from a login node. Dispatch edge transfers as batch jobs onto dedicated DTNs with high-bandwidth 100GbE / InfiniBand uplinks.
2. **Resumable Partial Staging:** Use an isolated partial directory to prevent half-copied files from polluting destination directories:
   ```bash
   rsync -av --partial-dir=.rsync-partial \
         --bwlimit=500000 \
         --exclude="*.tmp" \
         --exclude="core.*" \
         ./scratch/ensemble_data/ \
         archive-host:/gdata/projects/cmip7/
   ```
3. **Streaming Manifest Verification:** Before deleting data from cluster scratch, we compute SHA-256 manifests on both ends in parallel:
   ```bash
   find . -type f -name "*.nc" -print0 | xargs -0 -P 16 sha256sum > local_manifest.sha256
   ```
   Only when the remote verification script confirms a 100% hash match is local scratch cleaned.

---

### Summary: Architecture over Ad-hoc Scripting

Managing Earth system model ensembles is fundamentally a distributed systems engineering challenge. Moving from ad-hoc shell scripts to declarative workflow DAGs, tuning parallel filesystem striping, and respecting hardware NUMA topologies transforms a temperamental research run into a deterministic scientific pipeline.
