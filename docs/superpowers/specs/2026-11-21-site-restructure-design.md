# Site Restructure Design (2026-11-21)

Supersedes the IA parts of `2026-09-24-website-redesign-spec.md`.

## 1. Goal
The site serves 3 audiences:
- Collaborators: what I work on, my code, and how to reach me.
- HR and hiring: a fast check of my fit, plus CV PDFs.
- Me: a place to publish thoughts, presentations and papers.

The site is one part of the `career/` system (`cv/`, `job_applications/`, `vlap.github.io/`).

Success criteria:
- Each audience reaches its content from Home in one click.
- Each fact (bio, contacts, career history, stats) is written once, in one owner repo.
- All prose is short and plain. There is no generated filler.
- Talks, notes and paper notes are all Log items, so a later publishing workflow only adds a Markdown file (and optionally a PDF).

Out of scope: the future publishing workflow, changes to `job_applications/`, and visual redesign (DESIGN.md stays).

## 2. Ownership in `career/`
Rule: every fact has one owner. Other repos only read it.

| Fact | Owner | Path to site |
|---|---|---|
| Name, title, social links | `cv/tex/data/metadata.yaml` | `make sync` → `data/profile.yaml` |
| Bio, current focus, public email | `cv/tex/data/metadata.yaml` (new keys `bio`, `focus`, `public_email`) | `make sync` → `data/profile.yaml` |
| Experience, education | `cv/tex/data/experience.yaml` | `make sync` |
| Publications | `cv/tex/my_pubs.bib` | `make sync` |
| Presentations list | `cv/tex/presentations.yaml` | `make sync` |
| CV PDFs | `cv/tex` | `make sync` |
| Citations, h-index | OpenAlex | monthly CI |
| Public software list | site `data/curated_software.yaml` | site only |
| Log items, slide PDFs | site `content/posts/`, `static/slides/` | site only |
| Applications, letters | `job_applications/` (private) | never shown |

- `public_email: vladimir.lapin@bsc.es` is shown on the site. The existing `email:` key (used in CV PDFs) is not changed.
- `export_site_bundle.py` copies `bio`, `focus`, `public_email` into `profile.yaml` (keys `bio`, `current_focus`, `email`). The hand-edited bio in `profile.yaml` is overwritten. This is intended.
- `career/` becomes a git meta-repo with a private GitHub remote `vlap/career` (user creates the empty repo on GitHub first).
  - Submodules added in place: `cv` → https://github.com/vlap/cv.git, `job_applications` → https://github.com/vlap/job-applications.git, `vlap.github.io` → git@github.com:vlap/vlap.github.io.git.
  - `career/README.md` holds the system map: the 3 repos and the ownership table above.
  - Delete the stray Hugo artifacts `career/public/` and `career/resources/`. Add `public/` and `resources/` to `career/.gitignore`.

### LinkedIn mirror (future work, TBD)
- Direction is `cv` → LinkedIn. `cv` stays the owner.
- A later task can use the LinkedIn MCP (`get_my_profile`) to diff the profile against `cv` and report gaps.
- Log posts may carry an optional front-matter key `linkedin:` (URL of the matching LinkedIn post). Templates show it as a link if present. Nothing else depends on it.

## 3. Information architecture
Menu: `Work` · `Log` · `CV`. Footer: email, GitHub, LinkedIn, Scholar, ORCID, RSS.

### Home `/`
- Photo, name, tagline.
- Bio and current focus (from `profile.yaml`). This is the only place the bio appears.
- Three links: Collaborate → `/work/`, Hiring → `/cv/`, Read → `/posts/`.
- "Latest from the Log": up to 3 latest items with their kind label. Render the block only when 2 or more Log items are published.
- Removed: metrics row, research-highlight cards.

### Work `/work/` (new; `/software/` redirects here via `aliases`)
- Intro (1–2 sentences), current projects (one line each).
- Software cards from `curated_software.yaml` (one-sentence descriptions, no equations).
- "Older simulations": the existing `simulation_gallery` shortcode, at the bottom of the page.
- Selected publications: the 5 latest by year and month, from `publications.yaml` (automatic), plus link to `/publications/`.
- The current-projects lines are owned by `content/work.md`. They are short summaries for collaborators. The detailed version stays in the CV bullets. This duplication is accepted.

### Log `/posts/`
- One feed. New taxonomy `kinds` with values `note`, `talk`, `paper`. Filter pages at `/kinds/<kind>/`.
- `hugo.toml` must declare all taxonomies explicitly: `tag = "tags"`, `category = "categories"`, `kind = "kinds"`.
- Talk page: abstract, venue and date, slide PDF in `static/slides/`, optional video link.
- Paper page: short note in my own words, link to DOI.
- Published now: `2026-06-15-neural-surrogates-shallow-water-equations.md` (`kinds: [note]`), plus 2 backfilled talk pages (below).
- Post 2 text review: before launch, list unverifiable claims and AI-sounding phrases in the post (file + line + reason) for the user. The user decides what to cut. No AI rewrite.
- Backfilled talks (`kinds: [talk]`, `date` = original talk date, front matter `event` and `year` equal to the matching entry in `data/presentations.yaml`):
  - EGU2014, "Global modelling of surface and internal tides" (2014-04, Vienna). Slides: link to https://presentations.copernicus.org/EGU2014/EGU2014-14442_presentation.pdf.
  - AMS 19th Conference on Atmospheric and Oceanic Fluid Dynamics, "Global modelling of surface and internal tides" (2013-06). Link: https://ams.confex.com/ams/19Fluid17Middle/webprogram/Paper227193.html.
  - Abstract text is copied from the official abstract page, quoted and attributed. It is not written by AI. If the official abstract cannot be fetched, the page has venue, date and link only.
- Slide PDFs: backfilled talks link to the external URL only. `static/slides/` holds copies only for new talks by the user.
- Set `draft: true` on: `2026-05-04-senior-dev-hpc-workflows.md`, `2026-07-20-scaling-python-hpc-uv-lustre.md`, `2026-09-22-pragmatic-scientist-audit-climate-workflows.md`, `2026-09-24-openifs-mass-conservation-stochastic-rounding.md`. Files stay in the repo.

### CV `/cv/`
- Two PDF buttons: Research (full) `vladimir-lapin-cv-research-full.pdf` and Industry `vladimir-lapin-cv-industry.pdf`. Other variants remain in `static/downloads/` without buttons.
- Remove the intro paragraph. Add one "Tools and models" line (section 6).
- Timeline, trainings, presentations unchanged. The `cv_data` shortcode links a presentation entry to a Log page when a published post has `kinds` containing `talk` and the same `event` and `year`. No change to `cv/tex/presentations.yaml`.

### Publications `/publications/`
- Unchanged list. Linked from Work and CV, not from the menu.
- Intro line shows paper count, citations and h-index (moved from Home).

### Removed pages (redirect aliases added to a surviving page)
- `/about/` → `/` (tech stack moves to CV line).
- `/contact/` → `/` (footer has contacts).
- `/search/` removed (also remove `JSON` from home outputs if nothing else uses it).
- `/archives/` → `/posts/`.

### Post chrome (`hugo.toml`)
- `ShowShareButtons = false`, `ShowReadingTime = false`, `ShowBreadCrumbs = false`.
- ToC only on long posts (front matter `ShowToc: true` per post; global `ShowToc = false`).
- RSS stays on.

## 4. Docs
- `AGENTS.md`: shorten. Keep rules (voice, public-only repos, build/deploy, sync). Update architecture to this IA. `AGENTS.md` + `MEMORY.md` together < 8,000 characters.
- `GEMINI.md`: one line pointing to `AGENTS.md`.
- `PRODUCT.md`: shorten to users, purpose, constraints. Keep the `impeccable:product-schema` marker. Remove text that repeats AGENTS.md.
- `DESIGN.md`: unchanged.

## 5. Order of work and verification
Rollout:
- Site work happens on branch `restructure` in `vlap.github.io`. Commit once per step. `make verify` passes after each step.
- cv work happens on branch `site-bio` in `cv`. Run `make sync` locally from that branch.
- After the user's manual review in `make serve`: merge `restructure` into site `main` and push. Then merge `site-bio` into cv `main` and push. Reason: a cv push to `main` that touches `tex/data/**` triggers `publish_site.yml`, which pushes to the live site `main`. With this order, that CI sync is a no-op.

Steps:
1. `cv` (branch `site-bio`): add `bio`, `focus`, `public_email` to `metadata.yaml`; extend `export_site_bundle.py`; add a test in `cv/tex/tests`.
2. Content: draft the 4 posts; add `kinds` taxonomy; tag the kept post; add the 2 backfilled talk pages; produce the post 2 claim list for the user.
3. Pages and menu: add `/work/`; strip Home, CV, Publications; remove About, Contact, Search, Archives; add aliases; CV-to-talk linking in `cv_data`; post chrome settings.
4. Prose: apply section 6 text to Home, Work, CV, `curated_software.yaml`, `hugo.toml`.
5. Docs: section 4 changes.
6. `career/` meta-repo: init, submodules, README, .gitignore, cleanup, push to `vlap/career`.

Tests (TDD: update tests in `tests/test_site_build.py` and `tests/browser_verify.mjs` before templates):
- Existing checks for metrics row, highlight cards, About/Contact/Search pages are replaced by checks for the new structure.
- Every old URL (`/about/`, `/contact/`, `/software/`, `/archives/`) is a redirect in `public/`. `/search/` and the 4 drafted posts produce no page, and no internal link points to them.
- The bio string appears exactly once in `public/`, in `public/index.html`.
- Menu has exactly 3 items: Work, Log, CV.
- Home has no "Latest from the Log" block when fewer than 2 Log items are published.
- The EGU2014 entry on /cv/ links to its Log talk page.
- Manual: user reads Home, Work, CV in `make serve` before `git push origin main`.

Risks:
- Drafted posts return 404. Accepted: recent, few backlinks.
- `make sync` overwrites `profile.yaml` bio from `cv`. Intended.

## 6. Draft text (approved 2026-11-21)

**Tagline:** Senior Research Engineer, BSC · Climate models, HPC, ML emulators

**Bio (`cv` metadata `bio`):**
I am a Senior Research Engineer at the Barcelona Supercomputing Center. I work on the EC-Earth4 climate model: coupling, performance on MareNostrum 5, and the ensemble workflows behind our decadal predictions for CMIP7. Before BSC, I wrote sea-ice and ocean-tide solvers at MPI-M and the University of Leeds. Climate models have become too expensive to improve, and I think AI tools and automated verification can make that work affordable again.

**Focus (`cv` metadata `focus`):**
Preparing EC-Earth4 for CMIP7 on MareNostrum 5, tracer mass conservation in OpenIFS, and coupling neural emulators to EC-Earth4.

**Home links:**
- Collaborate — what I work on, the code, and how to reach me.
- Hiring — CV, career history and PDF downloads.
- Read — notes, talks and papers.

**Work intro:**
Projects I am on now, the public code, and some older simulations. If something here overlaps with your work, email me.

**Work: current projects:**
- Auto-EC-Earth4 — I co-lead the Autosubmit workflow for 50–100 member decadal ensembles (CMIP7, WMO/DCPP).
- EC-Earth4 performance — single precision, load balancing and MPI tuning; coupled runs are 2–3× faster.
- Emulators in EC-Earth4 — interfaces to couple neural emulators, and a GNN ocean biogeochemistry emulator with mass-conservation checks.
- OpenIFS tracer mass conservation in CY48R1.1.

**Software descriptions (`curated_software.yaml`):**
- cvc-commons — Shared workflow tasks and preprocessing scripts for climate computing at BSC, with schema checks and CI.
- EC-Earth4 — The European community Earth system model. I work on OpenIFS integration, OASIS3-MCT coupling and CMIP7 runs.
- Prediction Data Workflow — Preprocessing and interpolation of EN4, ERA5 and ORAS5 data for climate predictions.
- ece4-exp — Manages EC-Earth4 experiment configuration with layered YAML files.
- baro_tides_fd — Global finite-difference solver for barotropic ocean tides (Fortran).
- internal_tides_fd — Global solver for barotropic and internal tides with vertical mode decomposition (Fortran).
- pisces-inidata — Builds PISCES biogeochemistry initial conditions for NEMO and EC-Earth4 from a data catalog.

**CV tools line:**
Tools: Python (xarray, Dask, PyTorch), Fortran (MPI, OpenMP), Bash, Slurm, Autosubmit, CDO, NCO. Models: EC-Earth4, OpenIFS, NEMO/PISCES, OASIS3-MCT, ICON.

**Publications intro:**
{N} papers · {citations} citations · h-index {h} (OpenAlex).

**`hugo.toml` description:**
Vladimir Lapin, Senior Research Engineer at BSC. Climate models, HPC and ML emulators.
