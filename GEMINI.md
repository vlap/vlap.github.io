# Website Project - Context & Agent Rules

For full operating rules, editorial voice, and session startup checklists, see **[`AGENTS.md`](./AGENTS.md)**.

## Architecture
- **Framework:** Hugo Extended (required for PaperMod assets).
- **Theme:** PaperMod (customized via `hugo.toml` and local `layouts/` overrides).
- **Symbol Bar:** Monochromatic technical symbols (`🌐 ∫ ⚙ ⬡ ∞`) in `layouts/_partials/home_info.html`.
- **Data Driven:** CV and publications are generated deterministically via `make sync` (`scripts/bib_to_yaml.py`).

## Core Principles
1. **Peer-to-Peer Voice:** Conversational, colleague-to-colleague tone across all articles. Absolutely zero corporate marketing buzzwords.
2. **Technical Grounding:** Concrete physics, equations, benchmark numbers, and cluster telemetry.
3. **Public Repositories Only:** Only public, consortium-verified tools in `data/curated_software.yaml`.
4. **Counter-Chronological Publications:** Sorted most-recent first by year and month. Never auto-generate publication micro-posts.

## Maintenance Workflows
```bash
# Update and mirror CV data
make sync

# Build site deterministically
make build

# Local live preview
make serve
```

## Deploying
The site deploys automatically to GitHub Pages via GitHub Actions on every push to `main`:
```bash
git push origin main
```
*Note: Always run `git fetch origin main` on session start to cleanly integrate any automated nightly data updates before pushing.*
