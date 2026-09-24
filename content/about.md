---
title: "About Me"
layout: "page"
---

### Senior Research Engineer | Climate & Geophysical Models · HPC · Predictions · AI Adoption

I am a Senior Research Engineer and Software Coordinator at the **Barcelona Supercomputing Center (BSC)**.

My day-to-day work sits right at the intersection of atmospheric physics, supercomputing on **MareNostrum 5**, and modern software engineering. With the rapid evolution of machine learning and next-generation prediction systems, our everyday working practices in climate modeling have to change: we need to replace brittle shell scripts and manual steps with automated, schema-driven pipelines, automated verification, and reproducible HPC environments. That is the core mission behind Climate Commons ([`cvc-commons`](https://github.com/vlap/cvc-commons)).

<div class="badge-container">
    <span class="badge badge-hpc">HPC Architecture</span>
    <span class="badge badge-ai">AI Surrogates</span>
    <span class="badge">OpenIFS CY48R1.1</span>
    <span class="badge">EC-Earth4</span>
    <span class="badge">MareNostrum 5</span>
    <span class="badge">cvc-commons</span>
    <span class="badge badge-lead">Consortium Coordination</span>
</div>

---

### What I Focus On

- **Atmospheric Physics & Numerics:** Making sure atmospheric models stay physically realistic when pushed to higher resolutions or lower precision. Right now, that means investigating tracer mass conservation in ECMWF OpenIFS CY48R1.1, diagnosing why single-precision runs drift, and implementing SIMD-friendly stochastic rounding to eliminate numerical truncation errors.
- **HPC Systems & Supercomputing:** Running Earth system models at scale on MareNostrum 5. I focus on optimizing multi-component coupling (OASIS3-MCT), eliminating parallel filesystem bottlenecks (like Lustre metadata contention during job startup), and orchestrating CMIP7 production runs with Autosubmit and Slurm.
- **Modernizing Climate Workflows:** Leading Climate Commons ([`cvc-commons`](https://github.com/vlap/cvc-commons)) and declarative catalog pipelines for ocean initial conditions (`pisces-inidata` / NEMO). The goal is straightforward: make climate preprocessing deterministic, testable in CI, and ready for automated, AI-assisted engineering.
- **AI Surrogates & Fluid Dynamics:** Exploring neural operators as fast surrogates for fluid equations (like 2D Shallow Water Equations on PDEBench), while keeping a solid grounding in classic geophysical fluid solvers for global barotropic and internal ocean tides.

---

### Tech Stack & Tools

- **Languages:** Python (Xarray, Dask, PyTorch, NumPy, Pandas), Modern & Legacy Fortran (MPI, OpenMP), C++, Bash.
- **HPC & Platforms:** MareNostrum 5, Slurm, Autosubmit, LMOD modules, `uv`, CDO, NCO, NetCDF-C, Git/CI/CD.
- **Models:** EC-Earth4, OpenIFS (CY48R1.1), NEMO/PISCES, OASIS3-MCT.
