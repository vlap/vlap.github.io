# AGENTS.md — Agent Operating Instructions & Website Principles

Operating rules, editorial voice, architecture, and workflows for `vlap.github.io` (`/home/volant/code/career/vlap.github.io`).

---

## Agent Instructions on Session Startup

1. **Check Remote Sync:**
   Automated CI pushes commits to `data/` and `static/downloads/` via `.github/workflows/update_data.yml` (monthly OpenAlex) and `vlap/cv/.github/workflows/publish_site.yml` (CV bundle sync). Always run `git fetch origin main` and merge (`git merge origin/main`) before editing.
2. **Editorial Voice (Anti-Buzzword Standard):**
   - Keep Research Log prose **conversational and peer-to-peer**, like talking to a colleague over coffee or writing a lab notebook.
   - **Ban corporate fluff and buzzwords:** never write *"leading technical coordination at the intersection of..."*, *"pioneering schemas"*, or *"spearheading digital transformation"*.
   - **Ground claims in real engineering:** KaTeX equations, benchmark numbers, cluster telemetry, and concrete models (ECMWF OpenIFS CY48R1.1, EC-Earth4, NEMO/PISCES, MareNostrum 5).
   - **Explain the mission directly (do not hide behind citations):** advancing Earth system model fidelity has been slowed by escalating code and physical complexity; at BSC, AI adoption and automated verification make high-fidelity climate prediction affordable to science again.
3. **Verify Build Determinism:** Run `make build` (`hugo --gc --minify` passes with zero warnings or template errors).
4. **Deploy to GitHub Pages:** GitHub Pages deploys via `.github/workflows/hugo.yml` on every **`git push origin main`**. Always verify pushes hit `origin/main`.
5. **Continuous Docs:** Record new site patterns in `AGENTS.md` and personal context in `~/.gemini/antigravity-cli/knowledge/MEMORY.md`.

---

## Site Architecture & Content Standards

### 1. The 5 Core Pillars
- **About (`/about/`):** Personal overview, technical pillars, and tech stack.
- **Log (`/posts/`):** Deep dives (`cover:` diagram, `ShowToc: true`, `TocOpen: false`) and Lab Notes (`tags: ["lab-note"]`, `draft: true`, `150–400` words, optional `.png` via global `publish-note` skill). Never auto-generate empty publication micro-posts.
- **Software (`/software/`):** Curated public tools, CFD solvers, metadata catalogs, and simulation videos.
- **Publications (`/publications/`):** Counter-chronological filterable feed (year, month).
- **CV (`/cv/`):** Direct PDF downloads and dynamic timeline rendered by `layouts/shortcodes/cv_timeline.html` from `data/experience.yaml`.

### 2. Software & Public Footprint
- List only public, consortium-verified repos in `data/curated_software.yaml`: `Climate Commons (cvc-commons)`, `EC-Earth4`, `Prediction Data Workflow`, `ece4-exp`, `baro_tides_fd`, `internal_tides_fd`, and `pisces-inidata` (all featured).
- **Never** expose private BSC GitLab repos (`gitlab.earth.bsc.es`), internal cluster hosts, or personal dotfiles.

### 3. Math, Visuals & UI Patterns
- **KaTeX Math:** `math: true` in frontmatter; preserve `.katex-display { overflow-x: auto; }` horizontal scroll hygiene.
- **Post Media:** Deep-dive articles require `.svg`/`.png` `cover:` diagrams in `static/images/posts/`; Lab Notes may omit or attach a sanitized `.png`.
- **Video Facades:** `/software/` embeds use lightweight `sim-facade` posters with lazy-loaded iframes on click.
- **1-Click Citations & Print Hygiene:** Publications provide instant BibTeX copy (`copyBibTeX`); `@media print` formats `/cv/` and `/publications/` cleanly without site chrome.

---

## Maintenance & Build Workflows

### 1. Data Sync & Local Build
- `make sync`: Runs `$(CV_DIR)/tex/scripts/export_site_bundle.py --site-dir .` (`CV_DIR ?= ../cv`, `/home/volant/code/career/cv`) and `scripts/update_stats.py` to refresh sanitized `data/{publications,trainings,presentations,experience,profile}.yaml` and `static/downloads/*.pdf`.
- `make fetch-web-stats`: Runs `scripts/fetch_openalex.py` and `scripts/update_stats.py` to update `data/scholar_stats.yaml`.
- `make build` / `make serve`: Builds site (`hugo --gc --minify`) or starts local preview at `http://localhost:1313`.

### 2. GitHub Actions Automation
- `.github/workflows/hugo.yml`: Builds and deploys to GitHub Pages on `push` to `main` and via `workflow_call`.
- `.github/workflows/update_data.yml`: Monthly cron (`0 3 1 * *`) running `scripts/fetch_openalex.py` + `scripts/update_stats.py`, staging only `data/scholar_stats.yaml` and `data/stats.yaml`, and triggering `hugo.yml` via `workflow_call`.
- `vlap/cv/.github/workflows/publish_site.yml`: One-way deploy-key sync pushing updated CV YAML and PDFs from `/home/volant/code/career/cv`.
