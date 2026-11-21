# AGENTS.md — `vlap.github.io`

Operating rules, voice, IA, and workflows for `vlap.github.io`.

## Sync, Deploy, and Docs

1. **Sync:** CI pushes to `data/` and `static/downloads/` (`.github/workflows/update_data.yml`, `vlap/cv/.github/workflows/publish_site.yml`). Run `git fetch origin main && git merge origin/main` first.
2. **Deploy:** `.github/workflows/hugo.yml` deploys on `git push origin main`.
3. **Boundary:** Site rules go in `AGENTS.md`; personal context goes in `~/.gemini/antigravity-cli/knowledge/MEMORY.md` (`< 8,000` chars combined).

## Editorial Voice

- Write Research Log prose in a conversational, peer-to-peer lab-notebook voice.
- Ban corporate buzzwords: never write *"leading technical coordination at the intersection of..."*, *"pioneering schemas"*, or *"spearheading digital transformation"*.
- Ground claims in KaTeX math, benchmarks, telemetry, `OpenIFS CY48R1.1`, `EC-Earth4`, `NEMO/PISCES`, `MareNostrum 5`.
- State the mission directly: model complexity slowed progress; AI tools and automated verification make climate prediction affordable again.

## Site IA and Chrome

- **Nav & Footer:** Menu: `Work`, `Log`, `CV`. Footer: email, GitHub, LinkedIn, Scholar, ORCID, RSS.
- **Home (`/`):** Photo, name, tagline, `profile.yaml` bio + focus (bio only here), 3 links (`Collaborate`->`/work/`, `Hiring`->`/cv/`, `Read`->`/posts/`), `Latest from the Log` (<= 3 items with kind labels when `>= 2` published).
- **Work (`/work/`):** Intro, current projects, `curated_software.yaml` cards (1 sentence, no equations), `simulation_gallery` at bottom, 5 latest publications + `/publications/` link.
- **Log (`/posts/`):** `kinds` (`note`, `talk`, `paper`) at `/kinds/<kind>/`, optional `linkedin:` link, `static/slides/` for new talks (external URLs for backfilled talks). Lab Notes: `tags: ["lab-note"]`, `draft: true`, `150–400` words, optional `.png` (`publish-note`). Never auto-generate empty publication micro-posts.
- **CV (`/cv/`):** 2 PDF buttons (`vladimir-lapin-cv-research-full.pdf`, `vladimir-lapin-cv-industry.pdf`), tools line, `cv_timeline`, `cv_data` linking presentations to published `talk` posts matching `event` and `year`.
- **Publications (`/publications/`):** Linked from Work/CV; OpenAlex metrics intro + counter-chronological filterable feed.
- **Redirects & Chrome:** `/about/`->`/`, `/contact/`->`/`, `/software/`->`/work/`, `/archives/`->`/posts/`; `/search/` and home `JSON` removed. `ShowShareButtons=false`, `ShowReadingTime=false`, `ShowBreadCrumbs=false`, `ShowToc=false` (opt-in `ShowToc: true`), RSS on.

## Public Code, Math, and UI

- Only public consortium-verified repos in `data/curated_software.yaml`: `cvc-commons`, `EC-Earth4`, `Prediction Data Workflow`, `ece4-exp`, `baro_tides_fd`, `internal_tides_fd`, `pisces-inidata`. Never expose `gitlab.earth.bsc.es`, internal hosts, or dotfiles.
- Keep `math: true` KaTeX scroll, `static/images/posts/` `cover:` diagrams, `button.sim-facade` `<video>` (`replaceChildren`), `copyBibTeX`, and `@media print` on `/cv/` and `/publications/`.

## Build, Verify, and CI

- `make sync`: `$(CV_DIR)/tex/scripts/export_site_bundle.py --site-dir .` (`CV_DIR ?= ../cv`) + `scripts/update_stats.py` (`data/{publications,trainings,presentations,experience,profile}.yaml`, `static/downloads/*.pdf`).
- `make fetch-web-stats`: updates `data/scholar_stats.yaml`, `data/stats.yaml`.
- `make build` / `make build-site`: `hugo --gc --minify --cleanDestinationDir` (zero warnings). `make serve`: `http://localhost:1313`.
- `make verify`: `build-site`, `test`, `test-browser`, `scan` (`docs/testing-and-evaluation.md`).
- CI: `.github/workflows/hugo.yml`, `.github/workflows/update_data.yml`, `vlap/cv/.github/workflows/publish_site.yml`.
