# AGENTS.md — Agent Operating Instructions & Website Principles

This document defines the operating rules, editorial voice, architecture, and maintenance workflows for `vlap.github.io`.

---

## ⚡ Agent Instructions on Session Startup

Every time an agent session begins in this repository, the agent **MUST** perform the following startup checklist:

1. **Check Remote Sync:**
   GitHub Actions runs a nightly cron job (`update_data.yml`) that commits automated updates to `data/*.yaml`.
   Always run:
   ```bash
   git fetch origin main
   ```
   If local `main` is behind or diverged, cleanly merge remote data updates (`git merge origin/main`) before making new changes.
2. **Enforce the Editorial Voice (Anti-Buzzword Standard):**
   * The tone of the site—especially the Research Log—is **conversational and peer-to-peer**, as if talking to a close colleague over coffee or sharing insights in a lab notebook.
   * **Strictly prohibit marketing buzzwords and corporate fluff:** Never use phrases like *"leading technical coordination at the intersection of..."*, *"pioneering schemas"*, or *"spearheading digital transformation"*.
   * **Ground everything in real engineering:** Use actual equations (KaTeX), benchmark numbers, cluster telemetry, and specific models (ECMWF OpenIFS CY48R1.1, EC-Earth4, NEMO/PISCES, MareNostrum 5).
   * **Do not cite papers as a substitute for explaining the mission:** The mission at BSC is to *modernize how we build, verify, and run Earth system prediction workflows on supercomputers—replacing fragile scripts with automated schemas, deterministic tests, and AI-assisted engineering*.
3. **Verify Build Determinism:**
   Always verify changes locally with:
   ```bash
   make build
   ```
   Confirm Hugo compiles with zero warnings and zero template errors.
4. **Deploy to GitHub Pages:**
   The site is hosted on GitHub Pages and deploys automatically via `.github/workflows/hugo.yml` on every **`git push origin main`**.
   Never assume local commits are live—always verify they have been pushed to `origin/main`.
5. **Continuous Documentation Updates:**
   If new architectural patterns, tools, or editorial rules are established during a session, update `AGENTS.md` (for repository rules) and `~/.gemini/antigravity-cli/knowledge/MEMORY.md` (for personal context/mission).

---

## 🏛️ Site Architecture & Content Standards

### 1. The 5 Core Pillars
Navigation is consolidated into five distinct sections:
* **About (`/about/`):** Personal overview, core technical pillars, and tech stack.
* **Log (`/posts/`):** Conversational research notes and technical deep-dives. **Never** auto-generate empty publication micro-posts.
* **Software (`/software/`):** Curated public software tools, computational fluid dynamics solvers, declarative metadata catalogs, and simulation videos.
* **Publications (`/publications/`):** Filterable publications sorted **counter-chronologically** (most recent first) by year and month.
* **CV (`/cv/`):** Direct PDF download links and quick anchors to Experience, Education, Trainings, and Presentations.

### 2. Software & Public Footprint
* Only public, consortium-verified repositories are listed in `data/curated_software.yaml`:
  * `Climate Commons (cvc-commons)` (featured)
  * `EC-Earth4` (featured)
  * `Prediction Data Workflow` (featured)
  * `ece4-exp` (featured)
  * `baro_tides_fd` (featured)
  * `internal_tides_fd` (featured)
  * `pisces-inidata` (featured)
* **Never** list private BSC GitLab repositories (`gitlab.earth.bsc.es`) or personal dotfiles repositories.

### 3. Mathematics & Visuals
* Math equations are rendered via **KaTeX** using `math: true` in page frontmatter.
* Images must be stored in `static/images/` or `static/images/posts/`.

---

## 🛠️ Maintenance & Build Workflows

### 1. Data Sync & Build
* `make sync`: Deterministic, offline-first data sync. Converts BibTeX from Dropbox CV into `data/publications.yaml` (sorted counter-chronologically) and updates site stats.
* `make build`: Runs data sync and compiles the site using Hugo Extended.
* `make serve`: Starts local development server on `http://localhost:1313`.

### 2. GitHub Actions Automation
* `.github/workflows/hugo.yml`: Builds and deploys the Hugo site to GitHub Pages on every push to `main`.
* `.github/workflows/update_data.yml`: Nightly cron job fetching external statistics. **Configured to only stage `data/*.yaml`** so it will never pollute `content/posts/`.
