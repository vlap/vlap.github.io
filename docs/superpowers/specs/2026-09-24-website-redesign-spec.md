# Architectural Specification: Minimal-Maintenance Personal Website & Living Research Log

- **Author:** Dr. Vladimir Lapin & Assistant
- **Date:** 2026-09-24
- **Status:** Approved (Post-Adversarial Review)
- **Target Repository:** `vlap/vlap.github.io` (`/home/volant/vlap.github.io`)

---

## 1. Executive Summary & Narrative Realignment

### 1.1 The Shift: From Generic "MLOps" to Grounded AI & Agentic Adoption
The website previously used generic phrases (*"Interested in MLOps to bridge models with modern machine learning frameworks"*), which underrepresented Vladimir's actual technical role and contributions.

We pivot the site to articulate his authentic leadership and engineering profile: **AI & Agentic Workflow Adoption in Earth System Science & Supercomputing**, grounded in concrete proof:
1. **Climate Commons ([`cvc-commons`](https://github.com/vlap/cvc-commons)):** Developing curated repositories of scientific workflows, deterministic CI verification, and agentic software engineering (`gh-aw` + Gemini) that augment human climate scientists.
2. **Transforming Weather & Climate Working Practices ([arXiv:2606.25076](https://arxiv.org/abs/2606.25076)):** Redefining the forecasting value chain—connecting Tier-0 supercomputing (MareNostrum 5) with shared verification workflows, interactive computing, and agentic software tooling.
3. **Core Climate & HPC Engineering:** Deep domain mastery in EC-Earth4, ICON sea-ice dynamics, ocean tides, Autosubmit, and high-throughput CMIP7 data pipelines.

### 1.2 Core Design Principles (Pragmatic Scientist / Post-Adversarial Review)
- **Zero-Maintenance Overhead:** Avoid brittle custom parsers, regex scanners, or complex in-place YAML re-writers.
- **Deterministic, Offline-First Builds:** The website build must never fail because an external scraper (Google Scholar, GitHub API) hit a rate limit. Local TeX CV in Dropbox and Git are the single sources of truth.
- **Native PaperMod Alignment:** Stop fighting the theme with 500 lines of brittle custom CSS. Embrace PaperMod’s native minimalism, theme variables, and responsive layout primitives.
- **No Empty Placeholders:** Do not create top-level sections for assets that do not exist. Fold small or emerging topics (like simulations) into existing rich sections.

---

## 2. Streamlined Information Architecture

The top navigation is consolidated from 9 cluttered links down to **4 focused pillars**:

```
[ Vladimir Lapin ]  🌐 ∫ ⚙             [ About ] [ Log ] [ Software ] [ Publications ] [ CV ]  [ 🌓 ]
```

| Route | Pillar | Content & Function |
| :--- | :--- | :--- |
| `/` | **Home** | Monochromatic hero header, authentic bio, current focus, impact metrics, featured projects (`cvc-commons`, `EC-Earth4`), and recent log entries. |
| `/about/` | **About** | Professional profile, technical philosophy (deterministic CI, agentic workflows, HPC architecture), and technical stack. |
| `/posts/` | **Research & Engineering Log** | High-signal technical notes, benchmark analyses, and guides published directly from development sessions. |
| `/software/` | **Software & Work** | Unified portfolio: Flagship initiatives (`cvc-commons`, `EC-Earth4`, `auto-ecearth4`, `prediction-data-workflow`, `dotfiles`) + Embedded HPC Simulation Showcase. |
| `/publications/` | **Publications** | Structured bibliography synced from local TeX BibTeX, grouped by year with clean external links. |
| `/cv/` | **Curriculum Vitae** | Professional history, education, target PDF downloads, and unified jump-link sections for Trainings and Presentations. |

*Utility routes (`/search/`, `/archives/`, `/contact/`) are consolidated into subtle footer or header icon links.*

---

## 3. Subsystem Specifications

### 3.1 Content Ingestion: In-Session Agentic Publishing (Replaces Fragile Scanner)
- **Elimination of `publish_artifact.py`:** We do not build an automated script to parse `~/.gemini/antigravity-cli/brain/`. Automated regex sanitization risks leaking confidential BSC paths, tokens, or raw scratchpad clutter.
- **The Agent-Assisted Workflow:**
  - Whenever an ongoing Antigravity session produces a valuable technical finding, benchmark, or guide (e.g. single- vs double-precision analysis, UV HPC setup, PDEBench guide), the user simply instructs the agent:
    > *"Format this finding into a public technical note for my website log."*
  - The agent sanitizes internal paths, adds standard Hugo frontmatter (`title`, `date`, `tags: ["HPC", "Climate", "AgenticAI"]`), and commits the clean Markdown directly to `content/posts/<slug>.md`.
  - **Result:** Zero maintenance code, zero risk of credentials leaking, high editorial quality.

### 3.2 Homepage & Layout Streamlining
- **No Redundant News Ticker:** Rather than maintaining a fragile `data/news.yaml` that merely duplicates publication titles and blog posts, the homepage directly surfaces:
  1. **Profile Hero**: Centered name, avatar, and monochromatic symbol bar (`🌐 ∞ ∫ ⬡ ⚙`).
  2. **Bio & Current Focus**: Left-aligned, readable text container (`max-width: 720px`).
  3. **Impact Metrics**: Papers, Citations, h-index, Core Tools.
  4. **Flagship Work**: High-visibility cards for `cvc-commons` and `EC-Earth4`.
  5. **Recent Log Entries**: The 3 most recent technical notes.

### 3.3 Unified Software & Simulation Showcase (`/software/`)
- Eliminate `/simulations/` as an underpopulated top-level page.
- On `/software/`:
  - **Section 1: Open Science & Agentic Workflows** (featuring `cvc-commons`, Autosubmit tools, and data workflows).
  - **Section 2: Earth System Models & Supercomputing** (EC-Earth4 on MareNostrum 5, OpenIFS integration).
  - **Section 3: Numerical Simulation Highlights** (embedded videos of ICON sea-ice dynamics, ocean tides, with technical HPC context: resolution, partition, physical phenomena).
  - **Section 4: Developer Infrastructure** (modular shell, dotfiles, scientific python utilities).

### 3.4 Decoupled, Robust Build Pipeline (`Makefile`)
- **Deterministic Core (`make build` / `make sync`)**:
  - `scripts/bib_to_yaml.py`: Parses local `orcid_works.bib` from Dropbox TeX CV.
  - `rsync`: Mirrors YAML and PDFs from `DROPBOX_CV_PATH`.
  - `update_stats.py`: Calculates publication and software counts.
  - `hugo --gc --minify`: Builds static site.
- **Decoupled Web Scrapers (`make fetch-web-stats`)**:
  - `fetch_scholar.py` and `fetch_github.py` are isolated from the critical build path.
  - They are only executed on-demand or via scheduled jobs, updating cached YAML. If Google Scholar blocks scraping or GitHub rate-limits, `make build` and `hugo` still succeed deterministically.
- **Bug Fix for `fetch_orcid.py`**:
  - Disable automated generation of daily timestamped micro-posts in `content/posts/`. Publications live strictly in `data/publications.yaml` and the `/publications/` page.
  - Purge existing duplicate post files (`2026-05-06-...`, `2026-05-08-...`).

### 3.5 Native CSS Sanitation (`assets/css/extended/main.css`)
- Remove the syntax error fragment at line 136 (`lay: none !important; ...`).
- Remove hardcoded inline `#666` colors in shortcodes (`publications.html`, `cv_data.html`), adopting CSS variables `var(--secondary)` and `var(--primary)` for clean light/dark mode contrast.
- Remove redundant CSS bloat, relying on PaperMod's built-in flexbox and grid utilities.
- Fix `.home-info` body text alignment to `text-align: left` for professional legibility.

---

## 4. Implementation Plan Stages

1. **Stage 1: Code Cleanup & Bug Fixes**
   - Repair `assets/css/extended/main.css` syntax errors and dark mode variables.
   - Patch `fetch_orcid.py` and remove duplicate micro-posts in `content/posts/`.
   - Update `Makefile` to decouple fragile scrapers from `make build`.

2. **Stage 2: Narrative & Positioning Overhaul**
   - Rewrite `data/profile.yaml`, `content/about.md`, and `content/tools.md` to reflect AI & Agentic Adoption, `cvc-commons`, and arXiv:2606.25076.
   - Deprecate separate `content/tools.md` by consolidating its content into `About` and `Software`.

3. **Stage 3: Information Architecture & Navigation**
   - Update `hugo.toml` menu configuration to 4 core pillars (`About`, `Log`, `Software`, `Publications`, `CV`).
   - Relocate `/simulations` into a rich section within `content/software.md`.
   - Embed Trainings & Presentations cleanly on `content/cv/_index.md`.

4. **Stage 4: Homepage & Layout Polish**
   - Refactor `layouts/_partials/home_info.html` and `layouts/index.html` for clean hero presentation, left-aligned bio, and featured project cards.
   - Verify layout and contrast across mobile, desktop, light, and dark modes.

5. **Stage 5: Verification & Sync Run**
   - Execute local `make build` and `hugo server` verification.
   - Verify all links, PDFs, and responsive layouts.
