---
title: "Flowers: Multihead Coordinate Warps as a Neural Fluid Solver"
date: 2026-06-15T14:00:00+02:00
draft: false
type: "posts"
kinds: ["note"]
math: true
summary: "Why Till Muser's Flowers architecture (arXiv:2603.04430) caught my attention: learned coordinate warps mirror semi-Lagrangian advection at linear cost without FNO Gibbs ringing or quadratic attention."
tags: ["Flowers", "Neural Operators", "HPC"]
ShowToc: true
TocOpen: false
cover:
    image: "images/posts/flowers_banner.png"
    alt: "Flowers: A Warp Drive for Neural PDE Solvers"
    relative: false
---

Till Muser and co-authors recently released [**Flowers: A Warp Drive for Neural PDE Solvers**](https://arxiv.org/abs/2603.04430) ([project page](https://t-muser.github.io/flowers), [code](https://github.com/t-muser/flowers)). Unlike Fourier Neural Operators (which suffer from Gibbs ringing near sharp fronts and non-periodic boundaries) or Vision Transformers (with quadratic attention overhead), Flowers uses **learned multihead coordinate warps**—no Fourier multipliers, no dot-product attention, and no spatial convolutions.

## 1. Coordinate Warps as Semi-Lagrangian Transport

For anyone working on atmospheric transport schemes (such as semi-Lagrangian advection in OpenIFS), the mechanism is immediately familiar. Under scalar advection, the field is conserved along characteristic trajectories, and each head warps features at displaced coordinates:

$$\partial_t \phi + \mathbf{u} \cdot \nabla \phi = 0, \qquad \phi(t + \Delta t, \mathbf{x}) = \phi(t, \mathbf{x} - \mathbf{u} \Delta t), \qquad \tilde{\mathbf{x}}_k = \mathbf{x} + \mathbf{v}_k(\mathbf{x})$$

Flowers turns backward trajectory lookup into a differentiable layer:
1. Each head predicts a continuous 2D displacement field pointwise from local feature channels.
2. Features are interpolated at the warped coordinates via `torch.nn.functional.grid_sample`.
3. Stacking multihead warps across multiscale residual blocks yields global spatial coupling at linear cost in grid points.

<img src="/images/posts/flowers_warpfield.png" alt="Learned coordinate displacement fields overlaid on fluid shear flow" width="1500" height="750" loading="lazy">
*Figure from [`t-muser/flowers`](https://github.com/t-muser/flowers): learned coordinate displacement fields overlaid on fluid shear flow.*

## 2. Core PyTorch Primitive

The core warp operation reduces to pointwise displacement prediction followed by bilinear grid sampling:

```python
# Predict pointwise 2D coordinate displacements per head and sample via grid_sample
v = head_proj(x)  # (B, H, 2, Nx, Ny)
warped = F.grid_sample(x_heads, base_grid + v, mode="bilinear", align_corners=False)
```

For Earth system models, the open question is extending coordinate warps from 2D Cartesian grids to spherical geometry without polar singularities while preserving tracer mass conservation.
