---
title: "Curriculum Vitae"
date: 2026-05-04
draft: false
---

<div class="cv-download-bar">
  <a href="/downloads/vladimir-lapin-cv-research-full.pdf" class="cv-download-btn" target="_blank" rel="noopener">
    <span>📄</span> Full Research CV (PDF)
  </a>
  <a href="/downloads/vladimir-lapin-cv-applied-scientist.pdf" class="cv-download-btn" target="_blank" rel="noopener">
    <span>💼</span> Applied Scientist CV (PDF)
  </a>
  <a href="/downloads/vladimir-lapin-cv-industry.pdf" class="cv-download-btn" target="_blank" rel="noopener">
    <span>📊</span> Industry CV (PDF)
  </a>
</div>

<nav class="cv-nav-bar">
  <a href="#research-experience" class="cv-nav-link">Experience</a>
  <a href="#education" class="cv-nav-link">Education</a>
  <a href="#trainings--certifications" class="cv-nav-link">Trainings &amp; Certifications</a>
  <a href="#selected-presentations" class="cv-nav-link">Selected Presentations</a>
  <a href="/publications/" class="cv-nav-link">Publications &rarr;</a>
</nav>

Senior Research Engineer in Climate Modelling &amp; HPC at the **Barcelona Supercomputing Center (BSC)**. Specialized in atmospheric and oceanic fluid dynamics, Tier-0 supercomputing on MareNostrum 5, data assimilation, and reproducible scientific workflows.

---

## Research Experience

<div class="cv-timeline">

  <div class="cv-entry">
    <div class="cv-entry-header">
      <h3 class="cv-entry-title">Senior Research Engineer</h3>
      <span class="cv-date-badge">2021 – Present</span>
    </div>
    <div class="cv-institution">Barcelona Supercomputing Center (BSC) · Barcelona, Spain</div>
    <ul class="cv-bullets">
      <li><strong>Co-Lead Engineer, Auto-EC-Earth4:</strong> Architecting workflow execution DAGs (Autosubmit / Slurm) scheduling hundreds of concurrent compute jobs on MareNostrum 5 for CMIP7 and WMO decadal production cycles under cluster capacity constraints.</li>
      <li><strong>Atmospheric Numerics &amp; Precision:</strong> Diagnosing tracer mass conservation in ECMWF OpenIFS CY48R1.1; designed a SIMD-friendly stochastic rounding kernel in <code>qmfixer.F90</code> that eliminates secular float32 drift (converging to $+0.00\text{ ppm/cy}$, matching double precision).</li>
      <li><strong>HPC Scalability from First Principles:</strong> Identified MPI halo-exchange (<code>lbc_lnk</code>) as the primary NEMO4 scalability bottleneck from domain-decomposition first principles; tuning the <code>nn_comm</code> communication scheme delivered a $\sim 10\%$ simulated years per day (SYPD) gain with zero code changes.</li>
      <li><strong>Modern Scientific Software Engineering:</strong> Lead developer of Climate Commons (<a href="https://github.com/vlap/cvc-commons"><code>cvc-commons</code></a>); designed declarative workflow schemas (JSON Schema), agent developer contracts, and deterministic CI verification for climate workflows.</li>
    </ul>
  </div>

  <div class="cv-entry">
    <div class="cv-entry-header">
      <h3 class="cv-entry-title">Recognized Researcher (RE2)</h3>
      <span class="cv-date-badge">2017 – 2021</span>
    </div>
    <div class="cv-institution">Barcelona Supercomputing Center (BSC) · Barcelona, Spain</div>
    <ul class="cv-bullets">
      <li><strong>Data Assimilation &amp; State Estimation:</strong> Designed and validated ensemble Kalman filter (EnKF) and nudging schemes for optimal state estimation in EC-Earth3 (atmosphere, ocean, and sea ice), reducing systematic initialization biases across multi-decadal hindcasts.</li>
      <li><strong>High-Throughput Ensemble Infrastructure:</strong> Built and operated scalable ensemble prediction systems (50–100 SYPD, 10s–100s of ensemble members) on HPC clusters for decadal climate variability studies.</li>
      <li><strong>Experimentation at Scale:</strong> Automated parameter sweeps and assimilation sensitivity tests across 60-year coupled climate integrations.</li>
    </ul>
  </div>

  <div class="cv-entry">
    <div class="cv-entry-header">
      <h3 class="cv-entry-title">Research Scientist / Postdoctoral Fellow</h3>
      <span class="cv-date-badge">2014 – 2017</span>
    </div>
    <div class="cv-institution">Max Planck Institute for Meteorology (MPI-M) · Hamburg, Germany</div>
    <ul class="cv-bullets">
      <li><strong>Sea-Ice Dynamics Solver (ICON):</strong> Implemented an iterative Elastic-Viscous-Plastic (EVP) rheology solver for the ICON climate model on icosahedral-unstructured grids, resolving the severe parallel scalability bottleneck inherent to unstructured sea-ice dynamics.</li>
      <li><strong>Dynamical Modeling &amp; Compute Efficiency:</strong> Optimized dynamical solvers within the ICON modeling framework, balancing physical realism, numerical stability, and high-performance computing efficiency.</li>
    </ul>
  </div>

  <div class="cv-entry">
    <div class="cv-entry-header">
      <h3 class="cv-entry-title">Postdoctoral Research Fellow</h3>
      <span class="cv-date-badge">2011 – 2014</span>
    </div>
    <div class="cv-institution">University of Leeds · Leeds, United Kingdom</div>
    <ul class="cv-bullets">
      <li><strong>Global Baroclinic &amp; Barotropic Tide Models:</strong> Developed a high-resolution global spectral finite-difference solver for coupled barotropic and baroclinic tides at 2 arc-minute resolution (8 constituents, Fortran/MPI), resolving internal tide generation over steep underwater topography.</li>
      <li><strong>Novel Numerical Boundary Scheme:</strong> Derived and implemented a second-order accurate C-grid boundary treatment eliminating $O(1)$ staircase errors at irregular coastlines (published in <em>Ocean Modelling</em>, 2014).</li>
      <li><strong>Teaching &amp; Mentoring:</strong> Teaching assistant for Calculus of Variations, Calculus &amp; Mathematical Analysis, and Modelling with Differential Equations.</li>
    </ul>
  </div>

</div>

---

## Education

<div class="cv-timeline">

  <div class="cv-entry">
    <div class="cv-entry-header">
      <h3 class="cv-entry-title">Ph.D. in Applied Mathematics</h3>
      <span class="cv-date-badge">2008 – 2011</span>
    </div>
    <div class="cv-institution">University of Limerick · Limerick, Ireland</div>
    <ul class="cv-bullets">
      <li><strong>Thesis:</strong> <em>Resonant over-reflection of waves by jets in a rotating ocean</em></li>
      <li><strong>Focus:</strong> Geophysical fluid dynamics, wave-current interactions, shear flow instability, Stokes drift, and asymptotic methods.</li>
    </ul>
  </div>

  <div class="cv-entry">
    <div class="cv-entry-header">
      <h3 class="cv-entry-title">Diploma in Mechanics (Equivalent to M.Sc. + B.Sc.)</h3>
      <span class="cv-date-badge">2003 – 2008</span>
    </div>
    <div class="cv-institution">Lomonosov Moscow State University · Moscow, Russia</div>
    <ul class="cv-bullets">
      <li><strong>Thesis:</strong> <em>On stability of plane flows of visco-plastic fluids</em></li>
      <li><strong>Focus:</strong> Continuum mechanics, fluid mechanics, non-Newtonian fluids, asymptotic analysis, and partial differential equations.</li>
    </ul>
  </div>

</div>

---

## Trainings &amp; Certifications

{{< cv_data file="trainings" >}}

---

## Selected Presentations

{{< cv_data file="presentations" >}}
