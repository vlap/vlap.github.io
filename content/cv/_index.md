---
title: "Curriculum Vitae"
draft: false
hideMeta: true
---

<div class="cv-download-bar">
  <a href="/downloads/vladimir-lapin-cv-research-full.pdf" class="cv-download-btn" target="_blank" rel="noopener">
    <svg class="cv-download-icon" aria-hidden="true" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/><line x1="16" y1="13" x2="8" y2="13"/><line x1="16" y1="17" x2="8" y2="17"/></svg>
    <span class="cv-download-text">
      <span class="cv-download-title">Full Research CV (PDF)</span>
      <span class="cv-download-sublabel">Academic track &amp; complete publication record</span>
    </span>
  </a>
  <a href="/downloads/vladimir-lapin-cv-applied-scientist.pdf" class="cv-download-btn" target="_blank" rel="noopener">
    <svg class="cv-download-icon" aria-hidden="true" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="2" y="7" width="20" height="14" rx="2" ry="2"/><path d="M16 21V5a2 2 0 0 0-2-2h-4a2 2 0 0 0-2 2v16"/></svg>
    <span class="cv-download-text">
      <span class="cv-download-title">Applied Scientist CV (PDF)</span>
      <span class="cv-download-sublabel">ML emulation, physics &amp; research engineering</span>
    </span>
  </a>
  <a href="/downloads/vladimir-lapin-cv-industry.pdf" class="cv-download-btn" target="_blank" rel="noopener">
    <svg class="cv-download-icon" aria-hidden="true" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="3" width="18" height="18" rx="2"/><path d="M3 9h18"/><path d="M9 21V9"/></svg>
    <span class="cv-download-text">
      <span class="cv-download-title">Industry CV (PDF)</span>
      <span class="cv-download-sublabel">2-page HPC &amp; AI systems summary</span>
    </span>
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

{{< cv_timeline section="employment" >}}

---

## Education

{{< cv_timeline section="education" >}}

---

## Trainings &amp; Certifications

{{< cv_data file="trainings" collapsible="true" section_id="trainings--certifications" summary_label="trainings &amp; certifications" >}}

<p class="cv-standalone-link"><a href="/cv/trainings/">Open standalone Trainings &amp; Certifications page &rarr;</a></p>

---

## Selected Presentations

{{< cv_data file="presentations" collapsible="true" section_id="selected-presentations" summary_label="selected presentations" >}}

<p class="cv-standalone-link"><a href="/cv/presentations/">Open standalone Selected Presentations page &rarr;</a></p>

<script>
(function () {
  function openCvDetailsForHash(hash) {
    if (!hash || hash.length < 2) return;
    var id = decodeURIComponent(hash.slice(1));
    var bySection = document.querySelector('details.cv-section-details[data-cv-section="' + CSS.escape(id) + '"]');
    if (bySection) {
      bySection.open = true;
      return;
    }
    var target = document.getElementById(id);
    if (!target) return;
    var parentDetails = target.closest('details.cv-section-details');
    if (parentDetails) {
      parentDetails.open = true;
      return;
    }
    var nextEl = target.nextElementSibling;
    while (nextEl && !nextEl.matches('h2, hr')) {
      if (nextEl.matches('details.cv-section-details')) {
        nextEl.open = true;
        break;
      }
      nextEl = nextEl.nextElementSibling;
    }
  }

  if (window.location.hash) {
    openCvDetailsForHash(window.location.hash);
  }

  window.addEventListener('hashchange', function () {
    openCvDetailsForHash(window.location.hash);
  });

  document.querySelectorAll('.cv-nav-link[href^="#"]').forEach(function (link) {
    link.addEventListener('click', function () {
      openCvDetailsForHash(link.getAttribute('href'));
    });
  });

  window.addEventListener('beforeprint', function () {
    document.querySelectorAll('details.cv-section-details').forEach(function (d) {
      d.setAttribute('data-was-open', d.open ? 'true' : 'false');
      d.open = true;
    });
  });

  window.addEventListener('afterprint', function () {
    document.querySelectorAll('details.cv-section-details').forEach(function (d) {
      if (d.getAttribute('data-was-open') === 'false') {
        d.open = false;
      }
      d.removeAttribute('data-was-open');
    });
  });
})();
</script>
