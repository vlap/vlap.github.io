# Website Project - Gemini Context

## Architecture
- **Framework:** Hugo (Extended version required for PaperMod).
- **Theme:** PaperMod (Customized via `hugo.toml` and local `layouts/` overrides).
- **Custom Home Page:** The home page uses a custom `layouts/_partials/home_info.html` to display a monochromatic "Symbol Bar" (🌐 ∞ ∫ ⬡ ⚙) instead of emojis.
- **Data Driven:** The CV and Publication sections are generated from your TeX CV directory in Dropbox.

## Maintenance Workflows

### 1. Updating Data (CV & Pubs)
Whenever you update your TeX CV or ORCID BibTeX, run:
```bash
python3 ~/vlap.github.io/scripts/bib_to_yaml.py && cd ~/vlap.github.io && hugo
```

### 2. Branding & Symbols
To adjust the technical symbols on the home page, edit `layouts/_partials/home_info.html`.

### 3. Deploying
The site deploys automatically to GitHub Pages via GitHub Actions on every push to `main`.

## AI Guidelines
- When adding new data templates, prefer using `hugo.Data` over `.Site.Data`.
- Maintain the minimalist aesthetic of PaperMod.
- Ensure all images are placed in `static/images/`.
