# Website Redesign & Living Research Log Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Transform personal website into a clean, minimal-maintenance academic & research portfolio, reframing the narrative around AI & Agentic Workflow Adoption in Earth System Science & HPC, eliminating theme/CSS bugs, decoupling build scrapers, and consolidating navigation.

**Architecture:** Hugo (Extended) static site with PaperMod theme. Streamlines information architecture to 4–5 core pillars (`About`, `Log`, `Software`, `Publications`, `CV`), folds simulations into a rich software showcase, fixes dark mode contrast and corrupted CSS, and decouples fragile web scrapers from the deterministic `make build` pipeline.

**Tech Stack:** Hugo, PaperMod, CSS3 Variables, Python 3, YAML, BibTeX, Make, Bash.

**Spec:** [`docs/superpowers/specs/2026-09-24-website-redesign-spec.md`](file:///home/volant/vlap.github.io/docs/superpowers/specs/2026-09-24-website-redesign-spec.md)

## Global Constraints

- Never use raw Ruby or Jekyll dependencies; maintain pure Hugo static build.
- Offline-first builds: `make build` must never fail due to external API or rate-limiting failures.
- No confidential BSC paths (`/gpfs/projects/bsc32/...`) or credentials in public content or templates.
- Strict adherence to PaperMod design tokens (`var(--primary)`, `var(--secondary)`, `var(--tertiary)`, `var(--border)`, `var(--entry)`, `var(--radius)`).
- Preserve all existing comments and docstrings unrelated to changed code.

## Review Focus

1. **Dark mode contrast failure**: Elements styled with hardcoded hex colors (e.g. `#666`, `#0066cc`) becoming unreadable on dark background.
2. **Broken internal links**: Removing `/simulations/` or `/tools/` routes breaking internal hyperlinks or bookmarks.
3. **Build failure on fresh environment**: External API scrapers failing and halting `make build`.
4. **Mobile layout overflow**: Multi-column grids or symbol bars causing horizontal scrolling on narrow screens (< 600px).
5. **Loss of CV content**: Consolidating trainings and presentations into `/cv/` causing missing data or unrendered shortcodes.

---

### Task 1: CSS & Template Dark Mode Sanitation

**Files:**
- Modify: `assets/css/extended/main.css`
- Modify: `layouts/shortcodes/publications.html`
- Modify: `layouts/shortcodes/cv_data.html`

**Requirements:**
- Eliminate the truncated CSS syntax error at lines 136-143 in `main.css`.
- Replace hardcoded `color: #666;` with `var(--secondary)` in shortcodes to ensure clean dark mode legibility.
- Left-align editorial body copy in `.home-info` while keeping hero avatar and metrics centered.

- [ ] Inspect lines 130-150 in `assets/css/extended/main.css` and delete the malformed CSS block (`lay: none !important; ...`).
- [ ] In `layouts/shortcodes/publications.html`, replace all inline `color: #666;` styles with `color: var(--secondary);` or class-based styling.
- [ ] In `layouts/shortcodes/cv_data.html`, replace all inline `color: #666;` styles with `color: var(--secondary);`.
- [ ] In `assets/css/extended/main.css`, update `.home-info .entry-content` to `text-align: left; max-width: 720px; margin: 0 auto; line-height: 1.6;`.
- [ ] Run `hugo --gc` to verify that templates and CSS parse cleanly without warnings or errors.
- [ ] Commit changes: `git commit -am "fix(style): sanitize main.css syntax errors and dark mode contrast variables"`

---

### Task 2: Decouple Build Pipeline & Purge Duplicate Micro-Posts

**Files:**
- Modify: `scripts/fetch_orcid.py`
- Modify: `Makefile`
- Delete: `content/posts/2026-05-06-*.md` and `content/posts/2026-05-08-*.md` (duplicate publication micro-posts)

**Requirements:**
- Stop `fetch_orcid.py` from auto-generating timestamped micro-posts in `content/posts/`.
- Decouple `fetch_scholar.py` and `fetch_github.py` from the standard `make build` / `make sync` targets so builds never fail from rate-limiting.
- Clean out the redundant micro-posts that flooded `content/posts/`.

- [ ] In `scripts/fetch_orcid.py`, disable `create_micro_post(work)` invocation in `main()`, so it only updates `data/publications.yaml`.
- [ ] Delete all duplicate publication micro-posts from `content/posts/` (`2026-05-06-*.md` and `2026-05-08-*.md`), retaining genuine articles (`migrating-to-hugo.md`, `senior-dev-hpc-workflows.md`).
- [ ] In `Makefile`, update `sync:` so it only runs deterministic local scripts: `bib_to_yaml.py`, `rsync` from Dropbox, and `update_stats.py`.
- [ ] In `Makefile`, create a separate non-blocking target `fetch-web-stats:` for `fetch_scholar.py` and `fetch_github.py`.
- [ ] Run `make build` and verify that the build succeeds deterministically and quickly without network latency or scraper failures.
- [ ] Commit changes: `git commit -am "fix(build): decouple scrapers from critical path and purge duplicate micro-posts"`

---

### Task 3: Narrative & Profile Realignment (AI & Agentic Adoption + HPC)

**Files:**
- Modify: `data/profile.yaml`
- Modify: `content/about.md`
- Delete: `content/tools.md`

**Requirements:**
- Update `data/profile.yaml` to reframe bio from "Interested in MLOps..." to AI & Agentic Workflow Adoption in Earth System Science, MareNostrum 5, `cvc-commons`, and arXiv:2606.25076.
- Update `content/about.md` to articulate the technical philosophy: deterministic CI, agentic software engineering, reproducible climate pipelines, and high-performance computing.
- Remove redundant `content/tools.md` (folding its key technical stack elements into `content/about.md`).

- [ ] Edit `data/profile.yaml` to set `bio` and `current_focus` focusing on AI & Agentic Workflow Adoption in Earth System Science, highlighting `cvc-commons` and MareNostrum 5.
- [ ] Edit `content/about.md` to highlight:
  - Technical Coordination & Scientific Software Engineering at BSC.
  - Climate Commons (`cvc-commons`) & Agentic Workflows (`gh-aw` + AI pair programming).
  - Alignment with arXiv:2606.25076 on modernizing weather/climate digital practices.
  - HPC Architecture on MareNostrum 5 (MN5) and CMIP7 readiness.
  - Technical stack badges (Python, Fortran, Xarray, Autosubmit, Slurm, Git/Agile).
- [ ] Remove `content/tools.md`.
- [ ] Run `hugo` to confirm all pages build without broken references.
- [ ] Commit changes: `git commit -am "feat(narrative): reframe profile and about page around AI and agentic climate workflows"`

---

### Task 4: Navigation & Information Architecture Consolidation

**Files:**
- Modify: `hugo.toml`
- Modify: `content/software.md`
- Delete: `content/simulations.md`
- Modify: `content/cv/_index.md`

**Requirements:**
- Streamline top navbar to 5 core pillars: `About`, `Log`, `Software`, `Publications`, `CV`.
- Fold the simulations showcase into `content/software.md` under a dedicated "Numerical Simulations & HPC Showcase" section.
- Embed `trainings` and `presentations` shortcodes directly on `content/cv/_index.md` with quick anchor links, removing them from the top navbar.

- [ ] In `hugo.toml`, update `[menu]` so `menu.main` contains only:
  - `about` (weight 10, `/about/`)
  - `posts` / `log` (weight 20, name "Log", url `/posts/`)
  - `software` (weight 30, `/software/`)
  - `publications` (weight 40, `/publications/`)
  - `cv` (weight 50, `/cv/`)
- [ ] In `content/software.md`:
  - Feature `cvc-commons` (Climate Commons) as the leading open-science project.
  - Feature `EC-Earth4`, `auto-ecearth4`, and `prediction-data-workflow`.
  - Add a dedicated section `## Numerical Simulations & HPC Highlights` incorporating the `{{< simulation_gallery >}}` shortcode and case study descriptions.
- [ ] Delete `content/simulations.md`.
- [ ] In `content/cv/_index.md`, embed sections for `## Trainings & Certifications` (`{{< cv_data file="trainings" >}}`) and `## Selected Presentations` (`{{< cv_data file="presentations" >}}`) with top jump-links.
- [ ] Run `hugo` to verify no dangling routes or broken menu links exist.
- [ ] Commit changes: `git commit -am "feat(nav): consolidate navbar to 5 core pillars and fold simulations into software showcase"`

---

### Task 5: Homepage Layout & PaperMod Polish

**Files:**
- Modify: `layouts/_partials/home_info.html`
- Modify: `layouts/index.html`
- Modify: `assets/css/extended/main.css`

**Requirements:**
- Homepage hero displays avatar, name, and normalized symbol bar (`🌐 ∞ ∫ ⬡ ⚙`).
- Left-aligned editorial bio with clear visual hierarchy.
- Homepage spotlights `cvc-commons` and `EC-Earth4` as flagship initiatives.
- Recent research log entries shown below hero with reading times and topic badges.

- [ ] In `layouts/_partials/home_info.html`:
  - Ensure clean symbol bar formatting and alignment.
  - Render bio with left-alignment inside a centered container.
  - Display impact metrics (Papers, Citations, h-index, Tools).
  - Add a featured card spotlight for `cvc-commons` and `EC-Earth4`.
- [ ] In `layouts/index.html`, ensure the "Recent Log Entries" section lists the latest technical notes cleanly.
- [ ] In `assets/css/extended/main.css`, refine card styles, badge padding, hover transitions, and dark-mode contrast.
- [ ] Run `hugo` and inspect generated HTML files in `public/`.
- [ ] Commit changes: `git commit -am "feat(home): polish homepage hero, featured cards, and log feed"`

---

### Task 6: End-to-End Verification & Deploy Readiness

**Files:**
- Verify all modified files across the repo.

**Requirements:**
- Run full `make build` without errors.
- Verify light and dark mode styling.
- Verify responsive layout on mobile viewport.
- Verify all external and internal links.

- [ ] Execute `make build` and confirm exit code 0.
- [ ] Run a test server with `hugo server -D` in background or check generated output in `public/`.
- [ ] Verify that `/about/`, `/posts/`, `/software/`, `/publications/`, and `/cv/` render as expected.
- [ ] Check git diff and log to confirm clean, descriptive commits.
- [ ] Present completed work and summary to user.
