---
title: "Software & Projects"
date: 2026-05-04
draft: false
cover:
    image: "images/decor/photos/photo4.jpg"
    alt: "Software Header"
    relative: false
---

I maintain and contribute to several key software projects in the climate modelling and HPC ecosystem.

## [EC-Earth4](https://ec-earth.org/ec-earth/ec-earth4/)
**Core Technical Contributions & Maintenance**  
*Key Tech: Fortran, C++, OASIS3-MCT, OpenIFS, System Integration*

EC-Earth is a state-of-the-art European Earth System Model (ESM). My work on version 4 focuses on the large-scale integration and modularity of the system.

- **Technical Challenges:** Managing the transition to **OpenIFS 48r1** as the atmospheric component and ensuring seamless coupling with NEMO 4.2.2 via OASIS3-MCT.
- **Engineering Impact:** Improved the deployment and configuration workflows, making the model more accessible for academic research and CMIP7 readiness.
- **Skills:** System integration, Fortran/C++ debugging, large-scale software maintenance.

---

## [Prediction Data Workflow](https://gitlab.earth.bsc.es/es/prediction-data-workflow)
**Lead Developer**  
*Key Tech: Python, Bash, CDO, NCO, SOSIE, Data Engineering*

A modular, Autosubmit-ready framework for preprocessing and interpolating climate datasets (EN4, ERA5, ORAS5).

- **Focus:** Automation, reproducibility, and high-performance data manipulation using CDO, NCO, and SOSIE.
- **Impact:** Streamlines the generation of initial conditions for climate prediction experiments.

---

## [auto-ecearth4](https://earth.bsc.es/gitlab/es/auto-ecearth4)
**Contributor**  
*Key Tech: YAML, Python, Slurm, HPC Orchestration, Autosubmit*

The official Autosubmit-based runtime environment for EC-Earth4.

- **Focus:** Developing robust job templates and configuration schemas for large-scale ESM deployments on HPC systems like Marenostrum 5.

---

*For a full list of my code contributions, visit my [GitHub profile](https://github.com/vlap).*
