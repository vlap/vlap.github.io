---
title: "Software & Projects"
date: 2026-05-04
draft: false
math: true
cover:
    image: "images/decor/photos/photo4.jpg"
    alt: "Software Header"
    relative: false
---

I develop, optimize, and maintain scientific software spanning Earth System Models (EC-Earth4, OpenIFS, NEMO/PISCES), HPC orchestration on MareNostrum 5, and reproducible computational workflows. My work focuses on numerical precision, declarative metadata schemas, and deterministic CI verification for climate science.

{{< software_cards >}}

---

## Computational Methods & Mathematical Solvers

### Global Barotropic & Internal Tide Solvers (`baro_tides_fd` & `internal_tides_fd`)

In geophysical fluid dynamics, tidal energy dissipation plays a governing role in deep ocean mixing and thermohaline circulation. Our Fortran solvers discretize the governing shallow-water wave equations and stratified internal wave dynamics on global spherical grids:

* **Barotropic Global Tides:** Solves the 2D depth-integrated shallow-water equations with astronomical equilibrium tide forcing $\bar{\eta}$ and bottom friction:
  $$\frac{\partial \mathbf{u}}{\partial t} + f \mathbf{k} \times \mathbf{u} = -g \nabla (\eta - \bar{\eta}) - \frac{r}{h}\mathbf{u}$$
  $$\frac{\partial \eta}{\partial t} + \nabla \cdot (h \mathbf{u}) = 0$$
  where $\eta$ is sea-surface elevation, $h$ is bathymetric depth, $f = 2\Omega \sin\theta$ is the Coriolis parameter, and $\bar{\eta}$ represents tidal generating potential.

* **Internal Baroclinic Wave Modal Decomposition:** Resolves the vertical structure of internal waves generated as barotropic tides flow across steep underwater topography. Vertical normal modes $\Phi_n(z)$ satisfy the Sturm-Liouville eigenvalue problem under continuous Brunt-Väisälä buoyancy frequency $N^2(z) = -\frac{g}{\rho_0}\frac{d\rho_0}{dz}$:
  $$\frac{d}{dz}\left( \frac{1}{N^2(z)} \frac{d\Phi_n}{dz} \right) + \frac{1}{c_n^2} \Phi_n = 0, \quad \left.\frac{d\Phi_n}{dz}\right|_{z=0} = \left.\frac{d\Phi_n}{dz}\right|_{z=-H} = 0$$
  yielding modal phase speeds $c_n$ and vertical shear profiles that dictate energy transfer to turbulent mixing.

---

### Declarative Metadata Catalogs for Biogeochemical Models (`pisces-inidata`)

Traditional ocean and biogeochemical initialization pipelines rely on fragile, hard-coded shell scripts and NetCDF variable paths that break when upstream observational providers rename variables or when targeting different model releases.

In [`pisces-inidata`](https://github.com/vlap/pisces-inidata), we decoupled the pipeline using a **declarative metadata catalog schema**:
* **Source Catalog (`catalog.yaml`):** Declaratively specifies observational packages (GLODAP, WOA, benchmark outputs), file naming conventions, coordinate systems, and unit conversions.
* **Target Model Conventions:** Dynamically maps fields to differing target model standards (e.g., `nemo4_ece4` vs. `nemo5`) using pure Python resolvers (`pisces_inidata.catalog`), eliminating hard-coded filenames and variable name overrides from bash execution scripts.
* **Deterministic Verification:** Validates grid coordinates and spatial conservation invariants before writing final initial state NetCDF fields for EC-Earth4.

---

## Numerical Simulations & HPC Highlights

A visual collection of high-resolution climate, sea-ice, and fluid dynamics simulations executed on Tier-0 supercomputing systems including MareNostrum 5.

{{< simulation_gallery >}}

{{< github_feed >}}

*For a full list of my code contributions, visit my [GitHub profile](https://github.com/vlap).*
