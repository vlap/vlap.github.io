# Product

<!-- impeccable:product-schema 1 -->

## Platform

web

## Users

Three audiences, in this order:

1. **Collaborators** (Earth system modelers, HPC and ML engineers, EC-Earth/BSC/ECMWF partners). They want to know what I work on now, see my public code, and find how to reach me.
2. **HR and hiring committees.** They want a fast check of my fit, my career history, and a CV PDF.
3. **Me.** I use the site to publish notes, talks (with slides) and short notes on my papers.

## Product Purpose

A personal research site that answers each audience in one click from Home: Collaborate → `/work/`, Hiring → `/cv/`, Read → `/posts/`. It is one part of the `career/` system (`cv/`, `job_applications/`, `vlap.github.io/`). The site displays facts that other repos own. It does not own the bio, career history or publications.

## Positioning

An applied mathematician and research engineer's site, written in plain first-person prose. The claims are checkable: public repos, papers, slides and CV entries. It is not a portfolio with marketing copy.

## Operating Context

- Pages: Home, Work, Log, CV. Publications is linked from Work and CV. There are no About, Contact, Search or Archives pages. Their old URLs redirect.
- Log is one feed with a `kinds` taxonomy (`note`, `talk`, `paper`). A talk page has an abstract, venue, date and a slide link.
- Data ownership (single source per fact):
  - `cv/tex/data/metadata.yaml`: name, title, bio, focus, public email, social links.
  - `cv/tex`: experience, publications, presentations, trainings and CV PDFs. These reach the site through `make sync`.
  - OpenAlex: citations and h-index (monthly CI).
  - Site-owned: `data/curated_software.yaml`, `content/work.md` project lines, `content/posts/`, `static/slides/`.
- A LinkedIn mirror (`cv` → LinkedIn) is future work.

## Capabilities and Constraints

- Static Hugo site on GitHub Pages. No backend.
- `themes/PaperMod/` is a read-only submodule.
- `make sync` overwrites `data/profile.yaml`, `data/experience.yaml` and the `vladimir-lapin-cv*.pdf` files. Thesis PDFs and other downloads must survive it.
- Never expose private BSC GitLab repos, internal hostnames or credentials. Only public repos go in `curated_software.yaml`.
- Snap-confined Hugo cannot use `/tmp`. Temporary builds use `_tmp_*` in the repo root.

## Brand Commitments

- **Plain voice:** short sentences, first person, no filler and no buzzwords. Each fact appears once.
- **Restraint:** three menu items, no metric banners, no decorative cards.
- **Visual continuity:** the visual system lives in `DESIGN.md`.

## Evidence on Hand

- `data/experience.yaml`: MSU, Limerick, Leeds, MPI-M, BSC.
- `data/publications.yaml`, `data/presentations.yaml`, `data/trainings.yaml` (synced from `cv`). `data/scholar_stats.yaml` (OpenAlex).
- `data/curated_software.yaml`: 7 public repositories.
- `static/downloads/`: CV PDFs (Research full and Industry have buttons), PhD and MSc theses.
- `static/videos/simulations/`, `static/images/simulations/`: older tide, wave and rimming-flow simulations.
- Log: one published note (neural surrogates) and backfilled talks (EGU2014, AMS 2013).

## Product Principles

1. **One click per audience:** Home routes collaborators, hiring and readers directly.
2. **One owner per fact:** text lives in one repo. Other places render it.
3. **Evidence before assertion:** link a repo, paper, slide or CV entry for each claim.
4. **Own words only:** no AI-written prose is published without the author's review.
5. **Reproducible builds:** `make sync` and `make verify` stay deterministic.

## Accessibility & Inclusion

- WCAG 2.1 AA contrast in light and dark modes.
- Full keyboard navigation, visible focus, 44×44 px touch targets, `prefers-reduced-motion` support.
- Semantic headings, print-ready CV and publications, core reading without JavaScript.
