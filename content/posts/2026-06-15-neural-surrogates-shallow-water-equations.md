---
title: "Training Neural Surrogates for Geophysical Fluid Dynamics: 2D Shallow Water Equations on PDEBench"
date: 2026-06-15T14:00:00+02:00
draft: false
type: "posts"
math: true
summary: "Single-step validation loss is dangerously misleading when training neural operators on fluid PDEs. Here is what we learned building an end-to-end training pipeline for the 2D Shallow Water Equations on PDEBench, formatting for The Well, and evaluating autoregressive rollouts."
tags: ["AI Surrogates", "Geophysical Fluid Dynamics", "PDEBench", "PyTorch", "HPC", "Machine Learning"]
---

If you're training neural operators or deep learning surrogates on fluid dynamics equations, there is one common trap almost everyone falls into early on: **trusting single-step validation loss.**

A model can show an impressive $L_2$ error of $10^{-4}$ on predicting the next time step ($t \to t + \Delta t$). But the moment you unroll the model autoregressively—feeding its own predictions back into itself for 20 or 30 steps—high-frequency gravity waves quickly blow up into numerical shock waves, total fluid mass drifts, and the simulation goes completely unphysical.

Here is what we learned setting up an automated pipeline to benchmark neural surrogates on the **2D Shallow Water Equations (SWE)** from the [PDEBench](https://github.com/pdebench/PDEBench) suite, converted into *"The Well"* standardized format.

---

## 1. The Benchmark Problem: Why Shallow Water?

The 2D Shallow Water Equations are the classic playground for geophysical fluid dynamics. They capture the essential physics of atmospheric and oceanic flows—gravity wave propagation, geostrophic adjustment, and vortex dynamics—under hydrostatic balance:

$$\frac{\partial h}{\partial t} + \nabla \cdot (h \mathbf{u}) = 0$$

$$\frac{\partial (h \mathbf{u})}{\partial t} + \nabla \cdot \left( h \mathbf{u} \otimes \mathbf{u} + \frac{1}{2} g h^2 \mathbf{I} \right) = - f \mathbf{k} \times (h \mathbf{u}) - g h \nabla b$$

where $h$ is total fluid column depth, $\mathbf{u} = (u, v)$ is horizontal velocity, $g$ is gravity, $f$ is the Coriolis parameter, and $b$ is bottom bathymetry.

If an AI surrogate cannot stably preserve fluid volume and reproduce geostrophic adjustment here, it has no chance of working inside a coupled climate model.

---

## 2. Ingestion & Converting to "The Well" Format

PDEBench provides great raw simulation datasets (~6.2 GB for the 2D SWE configuration), but the raw HDF5 files aren't immediately ready for large-scale model training. 

We automated the entire setup from download to formatted tensor datasets:

```bash
# 1. Grab the raw PDEBench dataset
mkdir -p data/PDEBench
uv run python PDEBench/pdebench/data_download/download_direct.py \
  --root_folder data/PDEBench \
  --pde_name swe

# 2. Convert to 'The Well' format with clean splits
uv run python scripts/convert_pdebench_to_well.py \
  --dataset shallow \
  --create-splits
```

### Why Format Standardization Matters
Converting to *"The Well"* specification gives you:
* **Channel-first tensor layouts** that plug directly into PyTorch Distributed Data Parallel (DDP).
* **Explicit physical metadata:** Conserved physical invariants—like total fluid volume $\iint h \, dx dy$ and momentum components—are indexed so you can compute physical conservation metrics directly inside your validation loop.
* **Deterministic train/val/test splits** across varied initial conditions (radial dam breaks, shear instability waves).

---

## 3. Headless Training on Supercomputers

Supercomputing compute nodes on MareNostrum 5 don't have direct outbound internet access, which means default live dashboards like Weights & Biases will crash your job on startup.

We set up an automated driver script (`run_swe_pipeline.sh`) that handles offline telemetry and verification runs:

```bash
# Quick sanity check: 1 epoch with small validation set
./run_swe_pipeline.sh --test

# Full multi-epoch training run across GPU nodes
./run_swe_pipeline.sh --epochs 40
```

Inside the script, setting `export WANDB_MODE=offline` ensures all metrics, loss curves, and validation snapshots are saved locally to disk and can be synced later from a login node.

```bash
uv run python -m flowers.train \
  --data configs/data/pdebench-shallow_water.yaml \
  --model configs/models/flower_small.yaml \
  --train configs/train_1-to-1.yaml
```

---

## 4. Key Takeaways for PDE Surrogates

1. **Autoregressive Rollouts are the Only True Test:** Never judge a PDE surrogate on 1-step loss alone. Run rollouts to $N = 50$ steps during validation. If the model starts producing high-frequency spatial noise early on, the loss weights need more physical regularization.
2. **Respect the Conservation Laws:** Tracking total mass $\iint h \, dx dy$ over time reveals numerical leaks immediately. If fluid mass steadily drifts, penalizing the divergence $\nabla \cdot (h\mathbf{u})$ in the loss function helps rein it in.
3. **Automate the Pipeline End-to-End:** Having a single reproducible script that pulls the data, creates the splits, and launches training via `uv` saves dozens of hours of manual fiddling when experimenting with new model architectures.
