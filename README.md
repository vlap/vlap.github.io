# Vladimir Lapin — Research Portfolio (`vlap.github.io`)

Personal website and research portfolio built with Hugo Extended and PaperMod.
See [`AGENTS.md`](AGENTS.md) for editorial voice and operating rules, and [`docs/testing-and-evaluation.md`](docs/testing-and-evaluation.md) for verification gates.

---

## Site Architecture (5 Core Pillars + Utilities)

- **About (`/about/`):** Background, research pillars, and technical stack.
- **Log (`/posts/`):** Deep-dive engineering articles (`cover:` diagram, `ShowToc: true`) and Lab Notes (`tags: ["lab-note"]`, `draft: true`, `150–400` words). Empty publication micro-posts are never auto-generated.
- **Software (`/software/`):** Curated public repositories, climate solvers, and simulation video facades.
- **Publications (`/publications/`):** Counter-chronological publication feed with live keyword filtering and 1-click BibTeX copy.
- **CV (`/cv/`):** Direct PDF downloads and dynamic career timeline.
- **Utilities (`/contact/`, `/search/`):** Contact details and client-side Fuse.js search.

---

## Data & Content Layout

| Content Type | Location | Source / Purpose |
| :--- | :--- | :--- |
| **Profile & Focus** | `data/profile.yaml` | Synced from `../cv`; title, bio, and current focus. |
| **Experience Timeline** | `data/experience.yaml` | Synced from `../cv`; career history for `/cv/`. |
| **Publications** | `data/publications.yaml` | Synced from `../cv`; peer-reviewed and preprint entries. |
| **Presentations** | `data/presentations.yaml` | Synced from `../cv`; talks and posters. |
| **Trainings** | `data/trainings.yaml` | Synced from `../cv`; courses and certifications. |
| **CV PDFs** | `static/downloads/*.pdf` | Synced from `../cv`; downloadable CV variants. |
| **Software Portfolio** | `data/curated_software.yaml` | Manually curated public repositories (`cvc-commons`, `EC-Earth4`, etc.). |
| **Simulation Videos** | `data/simulations.yaml` | Video metadata and poster specs for `/software/`. |
| **Scholar & Site Stats** | `data/scholar_stats.yaml`, `data/stats.yaml` | OpenAlex metrics and computed homepage counters. |
| **Articles & Lab Notes** | `content/posts/*.md` | Deep-dive technical posts and Lab Notes (`static/images/posts/` media). |

---

## Workflows & Commands

| Command | Purpose |
| :--- | :--- |
| `make sync` | Export sanitized CV data and PDFs from `../cv` (`CV_DIR ?= ../cv`) and run `scripts/update_stats.py`. |
| `make fetch-web-stats` | Run `scripts/fetch_openalex.py` and `scripts/update_stats.py` to refresh `data/scholar_stats.yaml` and `data/stats.yaml`. |
| `make build` | Run `make sync` followed by `hugo --gc --minify --cleanDestinationDir`. |
| `make build-site` | Build Hugo site (`hugo --gc --minify --cleanDestinationDir`) without syncing `../cv`. |
| `make serve` | Start local Hugo preview server (`hugo server -D`) at `http://localhost:1313`. |
| `make verify` | Run `build-site`, `test` (`pytest`), `test-browser` (headless Chromium CDP), and `scan` (`modern-web-guidance`). |

---

## GitHub Actions Automation

- **Site Deployment (`.github/workflows/hugo.yml`):** Builds (`HUGO_VERSION: 0.165.0`) and deploys to GitHub Pages on `push` to `main` and via `workflow_call`.
- **Monthly Metrics (`.github/workflows/update_data.yml`):** Runs monthly (`0 3 1 * *`) to fetch OpenAlex metrics, recalculate `data/scholar_stats.yaml` and `data/stats.yaml`, commit changes, and trigger `hugo.yml`.
- **CV Bundle Sync (`vlap/cv/.github/workflows/publish_site.yml`):** Pushes updated CV YAML files and PDFs from `vlap/cv` into `data/` and `static/downloads/`.

---

## Authoring & Git Workflow

### Creating a New Post
- **Deep dive:** Create `content/posts/YYYY-MM-DD-slug.md` with a diagram in `static/images/posts/` (`cover:`), `ShowToc: true`, and `math: true` when rendering KaTeX.
- **Lab Note:** Create a short `150–400` word note (`tags: ["lab-note"]`, `draft: true`, optional `.png`) via the `publish-note` workflow.

### Remote Sync Before Editing
Automated CI commits to `data/` and `static/downloads/` on `main`. Always sync before making local edits or pushing:
```bash
git fetch origin main
git merge origin/main
```

---

## Technical Stack

- **Static Site Engine:** Hugo Extended + PaperMod (`themes/PaperMod/` read-only submodule)
- **Data Ingestion:** Python (`pyyaml`, standard library `urllib.request`)
- **Verification & Testing:** `pytest`, `beautifulsoup4`, `lxml`, `tinycss2`, Node 22 + headless Chromium CDP, and `modern-web-guidance` (`docs/testing-and-evaluation.md`)
- **Deployment:** GitHub Actions & GitHub Pages
