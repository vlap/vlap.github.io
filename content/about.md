---
title: "About Me"
layout: "page"
---

### Senior Research Engineer | Climate & Geophysical Models · HPC · Predictions · AI Adoption

I am a Senior Research Engineer at the **Barcelona Supercomputing Center (BSC)**, where I work on Earth system models (EC-Earth4, OpenIFS, NEMO), co-lead Auto-EC-Earth4 ensemble workflows on **MareNostrum 5**, and lead AI adoption across the research group.

For years, advancing the fidelity of climate models has been hindered by escalating physical and software complexity—multi-million line legacy Fortran codes, fragile multi-component coupling layers, and intractable debugging across supercomputing tiers. The promise of modern AI is making high-fidelity Earth system prediction affordable to science again: coupling fast neural emulators with physical dynamical cores, and replacing brittle manual scripts with schema-validated, deterministic workflows like Climate Commons ([`cvc-commons`](https://github.com/vlap/cvc-commons)).

<div class="badge-container">
    <span class="badge badge-hpc">HPC Architecture</span>
    <span class="badge badge-ai">AI Adoption</span>
    <span class="badge">OpenIFS CY48R1.1</span>
    <span class="badge">EC-Earth4</span>
    <span class="badge">MareNostrum 5</span>
    <span class="badge">cvc-commons</span>
    <span class="badge badge-lead">Consortium Coordination</span>
</div>

---

### What I Focus On

- **HPC Systems & Ensemble Workflows:** Co-leading Auto-EC-Earth4 ensemble workflows on MareNostrum 5. I focus on optimizing multi-component coupling (OASIS3-MCT), eliminating parallel filesystem bottlenecks (Lustre OST striping and metadata contention), and orchestrating CMIP7 and WMO decadal production cycles under strict capacity constraints.
- **AI Adoption & Model Emulation:** Leading group-wide AI adoption to transform scientific workflow development, evaluate neural emulators for coupled Earth system components, and implement automated validation harnesses.
- **Atmospheric Physics & Numerics:** Making sure atmospheric models stay physically realistic when pushed to higher resolutions or lower precision. Right now, that means investigating tracer mass conservation in ECMWF OpenIFS CY48R1.1, diagnosing why single-precision runs drift, and implementing SIMD-friendly stochastic rounding to eliminate numerical truncation errors.
- **Declarative Scientific Pipelines:** Author of Climate Commons ([`cvc-commons`](https://github.com/vlap/cvc-commons)) and declarative catalog pipelines for ocean initial conditions (`pisces-inidata` / NEMO). Transforming scientific software into schema-validated, testable components.
- **Physical Modeling & Fluid Dynamics:** Grounded in classical geophysical fluid dynamics—from high-resolution ICON sea-ice rheology solvers (mEVP) to global barotropic and internal ocean tide spectral solvers (`baro_tides_fd`, `internal_tides_fd`).

---

### Tech Stack & Tools

- **Languages:** Python (Xarray, Dask, PyTorch, NumPy, Pandas), Modern & Legacy Fortran (MPI, OpenMP), C++, Bash.
- **HPC & Platforms:** MareNostrum 5, Slurm, Autosubmit, LMOD modules, `uv`, CDO, NCO, NetCDF-C, Git/CI/CD.
- **Models:** EC-Earth4, OpenIFS (CY48R1.1), NEMO/PISCES, OASIS3-MCT.
