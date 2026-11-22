# Website Testing and Evaluation Guidelines

Verification standards, automated checks, and periodic manual audits for `vlap.github.io`.

## 1. Quick Start

Run the full local verification pipeline before pushing to `main`:

```bash
make verify
```

`make verify` runs four independent gates in sequence:

| Target | Command | Scope | Requires Network |
|---|---|---|---|
| `make build-site` | `hugo --gc --minify --cleanDestinationDir` | Production build without mutating `data/` from `../cv` | No |
| `make test` | `python3 -m pytest -q` | OpenAlex script tests, static DOM/CSS/SRI/Speculation Rules, link integrity, `DESIGN.md` sync | No |
| `make test-browser` | `node --test tests/browser_verify.mjs` | Headless Chromium E2E (`color-scheme`, header layout, `tabular-nums`, action pills, WCAG AA contrast, print, CLS, overflow) | No |
| `make scan` | `python3 scripts/check_modern_web.py` | `modern-web-guidance legacy-scan` enforcing 0 first-party findings | Yes (`npx` cache; use `--offline` if cached) |

When updating CV data from `../cv`, run `make build` (`sync` + `hugo --gc --minify --cleanDestinationDir`) before `make verify`.

## 2. Automated Gate Criteria

### 2.1 Hugo Build (`make build` / `make build-site`)
- Exit code must be `0` with zero `WARN` or `ERROR` lines in output.
- Snap confinement note: `/snap/bin/hugo` cannot read or write `/tmp`. Automated tests (`tests/test_site_build.py`, `tests/browser_verify.mjs`, `tests/capture_screenshots.mjs`) create temporary build and profile directories inside the repository root (`_tmp_hugo_*`, `_tmp_chrome_*`) and delete them in `finally` / `after` hooks.

### 2.2 Static DOM, CSS, and Link Suite (`tests/test_site_build.py`)
Parses minified output with `BeautifulSoup(..., "lxml")` and `tinycss2`:
- **External Subresource Security (R1):** On `math: true` pages, `katex@0.16.11` tags (`katex.min.css`, `katex.min.js`, `contrib/auto-render.min.js`) include exact `sha384` `integrity` digests, `crossorigin="anonymous"`, and `referrerpolicy="no-referrer"`. Non-redirect HTML pages include `<meta name="referrer" content="strict-origin-when-cross-origin">`, `<meta name="color-scheme" content="light dark">`, and zero external webfont CDN links.
- **Trusted Types & Dark Mode CSS (R1):** `playSimVideo()` uses `replaceChildren()` instead of `innerHTML`. Built CSS defines `color-scheme: light dark` on `:root`, explicit `:root[data-theme="dark"|"light"]` overrides, fallback `--badge-*` custom properties, and `@supports (color: light-dark(white, black))` tokens.
- **Monograph Typography, Pills & Signature (R1, R2):** CSS enforces `font-variant-numeric: tabular-nums` across dates, metrics, badges, and tables; wrapping pill bars with zero `--secondary` ink; flat `.log-rows .log-row` rules; and one inline $M_2$ `.tidal-field-band > svg.tidal-field-svg` on Home (`aria-hidden="true"`, valid `viewBox`, `>= 4` contour primitives, theme-adaptive colors, zero `profile-symbol.svg` or emoji bars).
- **Accessibility & Semantic Controls (R2):** Video facades render as `<button type="button" class="sim-facade" aria-label="Play ...">` with phrasing children (`<span>`) and `border: 0; padding: 0;` reset. `#pubFilterStatus` exposes `role="status"` and `aria-live="polite"`. Decorative `<svg>` icons carry `aria-hidden="true"`, icon-only GitHub links include `aria-label`, and `#pubFilterInput:focus-visible` plus generic `:focus-visible` controls preserve a `2px` outline.
- **Performance, CV PDFs & Print Hygiene (R3):** Homepage portrait declares `fetchpriority="high"` and compact square dimensions (`72 <= width == height <= 130`, currently `96x96`); `.sim-poster` images declare `width="480" height="360"`. `.pub-year-group:nth-of-type(n+3)` and `.cv-item:nth-of-type(n+6)` apply `content-visibility: auto; contain-intrinsic-size: auto none auto 220px;` with `@media print` visibility resets. Every page includes valid `<script type="speculationrules">` prefetch JSON excluding `/downloads/*` and `[rel~=nofollow]`. CV PDFs are verified via `pypdf` (`pdfinfo`/regex fallback): Industry CV (`2` pages) and Full Research CV (`>= 2` pages).
- **Design Sync, IA & Anti-Reference:** Verifies `DESIGN.md` (frontmatter + 8 canonical sections) and `.impeccable/design.json` (`schemaVersion: 2`) match `main.css`, verifies Section 3 IA / Section 6 prose / redirects, checks zero Nick Higham WordPress sidebars or widgets, and verifies every root-relative `href` / `src` resolves in the built site.

### 2.3 Headless Browser Suite (`tests/browser_verify.mjs`)
Uses Node 22 (`node:test`, `node:http`, native `WebSocket` CDP) and local headless Chromium (`CHROME_BIN` override supported):
- **Zero runtime errors:** Zero `console.error` or uncaught page exceptions across all 11 built routes (`/`, `/work/`, `/publications/`, `/cv/`, `/posts/`, `/kinds/`, `/kinds/note/`, `/kinds/talk/`, and 3 published posts), plus 4 meta-refresh redirects (`/about/`, `/contact/`, `/software/`, `/archives/`) and 404s (`/search/`, `/index.json`).
- **Theme synchronization & WCAG AA contrast:** `#theme-toggle` updates `html.dataset.theme`, `localStorage["pref-theme"]`, `<meta name="color-scheme">.content`, `getComputedStyle(document.documentElement).colorScheme`, and `.post-content a` computed color (`--accent-ocean`) across reloads. Alpha-composited WCAG AA contrast (`>= 4.5:1`) is verified in light and dark modes across `1280x800` and `375x812` for all monograph pills (including `.log-kind-pill.active` and `.log-kind-pill:not(.active)`), links, badges, and `.chroma .c1`.
- **Keyboard, video facades & publication filter:** `Enter` activates `<button class="sim-facade">` via `replaceChildren(video)` into a self-hosted `<video controls muted>` (`.webm` + `.mp4` `<source>`). Typing into `#pubFilterInput` updates `#pubFilterStatus`, `CSS.highlights` (`0` `<mark>` DOM mutations), and `?q=` URL state; `/` focuses `#pubFilterInput`; `Escape` clears (guarded by `e.isComposing`); `#pubEmptyState` handles zero matches; `copyBibTeX` isolates timers across buttons and meets `>= 4.5:1` contrast on `.copy-failed` in both themes.
- **Monograph geometry, `tabular-nums`, print & CWV:** Verifies left-aligned Home header and compact non-overlapping headshot on `1280x800` and `375x812`; strict `.log-rows .log-row` flat styling; `tabular-nums` glyph width invariance (`|w("1111") - w("8888")| <= 0.25px`) and mobile CV wrapping; `>= 3.5px` action pill spacing without clipping; `/cv/` PDF `fetch()` (`%PDF-`) and `beforeprint`/`afterprint` `<details>` expansion; isolated `--buildDrafts` wide `<table>` and KaTeX mobile scroll; zero Nick Higham live DOM patterns; `CLS === 0`; and `scrollWidth <= innerWidth` across all 6 viewport configurations (`1280x800`, `320x568`, `375x812`, `390x844` desktop + `375x812`, `390x844` mobile) plus `>= 44x44px` mobile `#theme-toggle`.

### 2.4 `modern-web-guidance` Legacy Scan (`scripts/check_modern_web.py`)
`npx -y modern-web-guidance@latest legacy-scan . --json` exits `0` even when findings exist and scans the read-only `themes/PaperMod/` submodule. `scripts/check_modern_web.py` flattens `guides[].rules[].findings[]`, separates `themes/PaperMod/` findings from first-party files, and exits `1` if any first-party finding exists.

When implementing new HTML/CSS/JS features, consult `modern-web-guidance` first:

```bash
npx -y modern-web-guidance@latest search "<2-5 word capability>"
npx -y modern-web-guidance@latest retrieve "<guide-id>"
```

### 2.5 Multi-Viewport Screenshot Capture (`tests/capture_screenshots.mjs`)
Run `SCREENSHOT_OUT_DIR="/path/outside/repo" node tests/capture_screenshots.mjs` to capture the 20-state matrix (`5` routes: `/`, `/work/`, `/posts/`, `/cv/`, `/publications/` x `2` viewports: `1280x800` and `375x812` x `2` themes: `light` and `dark`).
- **Output isolation:** Writes 40 PNGs (`*_fold.png` and `*_full.png`) plus `manifest.json` to `process.env.SCREENSHOT_OUT_DIR` (falling back strictly to `os.tmpdir()` when unset). Throws an error if the output path resolves inside the repository.
- **Deterministic priming:** Sets `prefers-color-scheme` and `localStorage["pref-theme"]`, waits for `document.fonts.ready`, step-scrolls the page to decode lazy images and `content-visibility: auto` sections, resets scroll to `(0, 0)`, and exits non-zero if any state reports `cls > 0`, `scrollWidth > innerWidth`, failed images, console errors, or page exceptions.

## 3. Dependency & SRI Maintenance

To upgrade KaTeX beyond `0.16.11` in `layouts/partials/extend_head.html`:
1. Pin the exact immutable version URL on `cdn.jsdelivr.net`.
2. Recompute each `sha384` digest directly from the downloaded distribution files:

```bash
curl -fsSL https://cdn.jsdelivr.net/npm/katex@0.16.11/dist/katex.min.css | openssl dgst -sha384 -binary | openssl base64 -A
```

3. Update `KATEX_EXPECTED` in `tests/test_site_build.py` to match the new version and digests. Run `make verify`.

## 4. Periodic Manual & External Audits

Run these checks after major layout, CSS, or content changes:
- **WCAG automated scan (target: 0 critical/serious issues):** Run `npx -y @axe-core/cli http://127.0.0.1:1313/` against `make serve` on `/`, `/work/`, `/posts/`, `/kinds/note/`, `/kinds/talk/`, `/cv/`, and `/publications/` in both light and dark modes.
- **Print layout check:** Open `/cv/` and `/publications/` in Chromium print preview (`Ctrl+P`) and confirm all `.pub-year-group` and `.cv-item` blocks render without truncation, chrome, or split cards.
- **Lighthouse audit (target: >= 95 across categories):** Run `npx -y lighthouse http://127.0.0.1:1313/ --only-categories=performance,accessibility,best-practices,seo`.
- **CI alignment:** `.github/workflows/hugo.yml` builds with `HUGO_VERSION: 0.165.0`; keep CSS/template syntax compatible with both CI (`0.165.0`) and local Hugo.

## 5. 15-Second Scan Rubric (`S1`–`S6`)

Inspect the 40 light/dark PNGs (`1280x800` desktop and `375x812` mobile) generated by `tests/capture_screenshots.mjs` against these binary MUST-PASS gates:

| Window | Gate | Binary Pass Criteria |
|---|---|---|
| **0–1s** | **S1: First-Second Domain Signal** | `/` above the fold immediately signals computational physics / ocean-climate PDE & HPC work via the single authentic $M_2$ physical-field SVG and monograph type; zero emoji bars or `profile-symbol.svg`. |
| **0–2s** | **S2: Left-Aligned Editorial Header** | `/` uses a left-aligned editorial header with compact headshot integrated cleanly without overlap, clipping, or centered social-profile card stacking on desktop and mobile. |
| **2–5s** | **S3: Identity & 1-Click Routing** | `/` fold clearly shows `Dr. Vladimir Lapin`, tagline (`Senior Research Engineer, BSC · Climate models, HPC, ML emulators`), `Current Focus`, and 3 links (`Collaborate`, `Hiring`, `Read`). |
| **5–10s** | **S4: HR 2-Page CV & Timeline Scan** | `/cv/` fold displays both `Industry CV (PDF)` (`2-page`) and `Full Research CV (PDF)` prominently, legible `Tools`/`Models` line, and `tabular-nums` career timeline (`BSC`, `MPI-M`, `Leeds`, `Limerick`, `MSU`) with secondary sections collapsed. |
| **10–13s** | **S5: Site-Wide Monograph Craft** | `/work/`, `/posts/`, and `/publications/` share hairline rules, `tabular-nums` aligned dates/years, compact non-clipped action pills (`>= 3.5px` gap), pine/ocean accents, and AA legibility in light and dark modes. |
| **13–15s** | **S6: Zero Nick Higham Anti-Reference** | Zero WordPress utility sidebars, recent-posts/categories/archives columns, subscriber widgets, `"What Is"` series, or stacked blog-card box clutter anywhere on the site. |
