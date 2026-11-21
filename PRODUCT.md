# Product

<!-- impeccable:product-schema 1 -->

## Platform

web

## Users

Primary visitors are HPC, climate modeling, and AI engineering leads, Principal Investigators (PIs), and technical or academic hiring committees evaluating Dr. Vladimir Lapin's numerical modeling rigor, workflow engineering, and research leadership.

Secondary visitors are fellow Earth system modelers and consortium collaborators (EC-Earth, BSC, ECMWF) reading Research Log notes, checking software repositories, exporting BibTeX citations, or downloading CV and thesis artifacts.

## Product Purpose

Present Vladimir Lapin's career trajectory, mathematical and HPC engineering depth, peer-reviewed publications, and technical log clearly so evaluators can verify research and engineering fit within minutes, supporting career growth across BSC leadership, international climate/AI collaborations, and senior research or applied science roles.

## Positioning

An authentic applied mathematician's technical monograph and lab notebook grounded in verifiable Tier-0 supercomputing work (MareNostrum 5, OpenIFS CY48R1.1, EC-Earth4, NEMO/PISCES, `cvc-commons`) and a continuous physical-modeling lineage (`MSU 2003–2008 -> Limerick 2008–2011 -> Leeds 2011–2014 -> MPI-M 2015–2017 -> BSC 2019–present`), contrasting directly with generic executive summaries and corporate buzzword portfolios.

## Operating Context

Visitors operate primarily in Read and Operate modes: reading long-form Research Log essays with KaTeX equations and Fortran/Python code, filtering 24+ publications with instant BibTeX copy, playing self-hosted geophysical and fluid-dynamics simulation clips, scanning or printing the CV, and downloading audience-specific CV PDFs or historical MSc and PhD theses.

CV data (`data/experience.yaml`, `data/publications.yaml`, `data/presentations.yaml`, `data/trainings.yaml`) and PDF CV variants sync from `../cv` via `make sync`; bibliometric counts (`data/scholar_stats.yaml`) sync monthly from OpenAlex via GitHub Actions.

## Capabilities and Constraints

- Static Hugo site deployed to GitHub Pages; zero runtime backend or server-side database.
- `themes/PaperMod/` is a read-only git submodule and must remain unmodified.
- `make sync` overwrites `data/experience.yaml` and deletes `static/downloads/vladimir-lapin-cv*.pdf`, so non-`vladimir-lapin-cv*.pdf` assets (such as `phd-thesis-vlapin.pdf` and `msc-thesis-vlapin.pdf`) and template-level thesis links in `layouts/shortcodes/cv_timeline.html` must survive `make sync`.
- Strict anti-buzzword prose policy (`AGENTS.md`): peer-to-peer clarity backed by equations, cluster telemetry, and verifiable public repositories; never expose private BSC GitLab hosts, internal cluster hostnames, or credentials.
- Snap-confined Hugo (`v0.170.1`) cannot read or write `/tmp`; temporary test builds use `_tmp_*` inside the repository root.

## Brand Commitments

- **Candid Applied-Mathematician Voice:** Carry forward the direct mathematical and practical engineering voice of the legacy site (*"Frankly speaking, as an applied mathematician, I would give a go at modelling of any physical process with a rich mathematical structure"*; tools that *"save researchers from banging their heads against the wall for too long"*).
- **Minimalist Read/Operate Restraint:** Keep navigation, filtering, and reading surfaces free of filler copy, nested ornament, or artificial celebration.
- **Heritage Continuity:** Preserve continuity with the legacy `"Save The Earth"` site through its pine and ocean editorial accents, serif monograph headings, and authentic fluid/ocean simulation artifacts.

## Evidence on Hand

- `data/experience.yaml`: Verified career lineage across MSU (2003–2008), University of Limerick / MACSI (2008–2011), University of Leeds (2011–2014), Max Planck Institute for Meteorology (2015–2017), and Barcelona Supercomputing Center (2019–present).
- `data/publications.yaml` (24 entries), `data/curated_software.yaml` (7 public repositories), `data/presentations.yaml` (21 entries), `data/trainings.yaml` (28 entries), and `data/scholar_stats.yaml` (OpenAlex citations and h-index).
- `static/downloads/`: 5 role-tailored CV PDFs synced from `../cv`, plus `phd-thesis-vlapin.pdf` and `msc-thesis-vlapin.pdf` from `/home/volant/vlap.github.io.legacy`.
- `static/videos/simulations/` & `static/images/simulations/`: Self-hosted legacy simulations (`global-ocean-tides`, `overturning-wave`, `rimming-flow`) replacing dead third-party video embeds.
- `content/posts/`: 5 peer-to-peer technical deep dives with KaTeX derivations, Fortran/Python listings, and diagnostic figures.

## Product Principles

1. **Evidence before assertion:** Anchor every capability claim in equations, cluster benchmarks, public repositories, or downloadable PDFs.
2. **Progressive disclosure for busy reviewers:** Surface primary decision artifacts (CV PDFs, Research Experience, Education, featured software, recent posts) first while keeping full trainings, presentations, and BibTeX records one click away.
3. **Peer-to-peer candor:** Write like an engineer talking to a colleague in a lab notebook; never use corporate fluff.
4. **Deterministic reproducibility:** Keep data sync, Hugo builds, DOM/CSS tests, Chromium E2E checks, and `modern-web-guidance` scans reproducible via `make sync` and `make verify`.
5. **Universal access:** Deliver full keyboard navigability, print-ready CV/publication layouts, and light/dark readability without requiring JavaScript for core reading.

## Accessibility & Inclusion

- WCAG 2.1 AA computed contrast (`>= 4.5:1` for text, `>= 3:1` for controls, icons, and focus indicators) in both light and dark modes.
- Full keyboard navigation, visible `:focus-visible` outlines, minimum `44x44px` mobile touch targets, and `prefers-reduced-motion` compliance.
- Semantic heading hierarchy without skipped levels, print-expanded `<details>` disclosures (`@media print`), and descriptive labels for icon-only controls and media facades.
