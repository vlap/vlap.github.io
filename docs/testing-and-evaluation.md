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
| `make test` | `python3 -m pytest -q` | OpenAlex script tests, static DOM/CSS/SRI/Speculation Rules, link integrity | No |
| `make test-browser` | `node --test tests/browser_verify.mjs` | Headless Chromium E2E (`color-scheme`, keyboard activation, live status, CLS, overflow, Tab order) | No |
| `make scan` | `python3 scripts/check_modern_web.py` | `modern-web-guidance legacy-scan` enforcing 0 first-party findings | Yes (`npx` cache; use `--offline` if cached) |

When updating CV data from `../cv`, run `make build` (`sync` + `hugo --gc --minify --cleanDestinationDir`) before `make verify`.

## 2. Automated Gate Criteria

### 2.1 Hugo Build (`make build` / `make build-site`)
- Exit code must be `0` with zero `WARN` or `ERROR` lines in output.
- Snap confinement note: `/snap/bin/hugo` cannot read or write `/tmp`. Automated tests (`tests/test_site_build.py`, `tests/browser_verify.mjs`) create temporary build directories inside the repository root (`_tmp_hugo_*`) and delete them in `finally` / `after` hooks.

### 2.2 Static DOM, CSS, and Link Suite (`tests/test_site_build.py`)
Parses the minified output with `BeautifulSoup(..., "lxml")` and `tinycss2` (never relying on fragile unminified attribute quotes):
- **External Subresource Security (R1):** On all `math: true` pages, `katex@0.16.11` tags (`katex.min.css`, `katex.min.js`, `contrib/auto-render.min.js`) include exact `sha384` `integrity` digests, `crossorigin="anonymous"`, and `referrerpolicy="no-referrer"`. Every non-redirect HTML page includes `<meta name="referrer" content="strict-origin-when-cross-origin">` and `<meta name="color-scheme" content="light dark">`.
- **Trusted Types & Dark Mode CSS (R1):** `playSimVideo()` uses `replaceChildren()` instead of `innerHTML`. Built CSS defines `color-scheme: light dark` on `:root`, explicit `:root[data-theme="dark"|"light"]` overrides, fallback `--badge-*` custom properties, and `@supports (color: light-dark(white, black))` consolidated `--badge-*` tokens.
- **Accessibility & Semantic Controls (R2):** Video facades render as `<button type="button" class="sim-facade" aria-label="Play ...">` with phrasing children (`<span>`) and `border: 0; padding: 0;` reset. `#pubFilterStatus` exposes `role="status"` and `aria-live="polite"`. Decorative `<svg>` icons carry `aria-hidden="true"`, icon-only GitHub links include `aria-label`, and `#pubFilterInput:focus-visible` preserves a `2px` outline.
- **Performance & Print Hygiene (R3):** Homepage avatar has `fetchpriority="high" width="150" height="150"`; `.sim-poster` images declare `width="480" height="360"`. `.pub-year-group:nth-of-type(n+3)` and `.cv-item:nth-of-type(n+6)` apply `content-visibility: auto; contain-intrinsic-size: auto none auto 220px;` with `@media print` visibility resets. Every page includes valid `<script type="speculationrules">` prefetch JSON excluding `/downloads/*` and `[rel~=nofollow]`.
- **Internal Links:** Every root-relative `href` / `src` resolves to a built file in the output directory.

### 2.3 Headless Browser Suite (`tests/browser_verify.mjs`)
Uses Node 22 (`node:test`, `node:http`, native `WebSocket` CDP) and local headless Chromium (`CHROME_BIN` override supported):
- **Zero runtime errors:** Zero `console.error` or uncaught page exceptions across `/`, `/software/`, `/publications/`, `/cv/`.
- **Theme synchronization:** `#theme-toggle` updates `html.dataset.theme`, `localStorage["pref-theme"]`, `<meta name="color-scheme">.content`, `getComputedStyle(document.documentElement).colorScheme`, and `--badge-hpc-bg` across reloads.
- **Keyboard & interactive widgets:** `Enter` activates `<button class="sim-facade">` into a `youtube-nocookie.com/embed/` `<iframe>`. Typing into `#pubFilterInput` updates `#pubFilterStatus` live counts, `#pubFilterClear` restores all items and focus, and `#pubFilterInput` renders a visible `:focus-visible` outline.
- **Deferred rendering & CWV:** Sequential `Tab` navigation reaches off-screen `content-visibility: auto` `.pub-year-group` and `.cv-item` elements. Layout shift (`CLS`) equals `0`, and `scrollWidth <= innerWidth` holds at both `1280x800` and `375x812`.

### 2.4 `modern-web-guidance` Legacy Scan (`scripts/check_modern_web.py`)
`npx -y modern-web-guidance@latest legacy-scan . --json` exits `0` even when findings exist and scans the read-only `themes/PaperMod/` submodule. `scripts/check_modern_web.py` flattens `guides[].rules[].findings[]`, separates `themes/PaperMod/` findings from first-party files, and exits `1` if any first-party finding exists.

When implementing new HTML/CSS/JS features, consult `modern-web-guidance` first:

```bash
npx -y modern-web-guidance@latest search "<2-5 word capability>"
npx -y modern-web-guidance@latest retrieve "<guide-id>"
```

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
- **WCAG automated scan (target: 0 critical/serious issues):** Run `npx -y @axe-core/cli http://127.0.0.1:1313/` against `make serve` on `/`, `/about/`, `/software/`, `/publications/`, and `/cv/` in both light and dark modes.
- **Print layout check:** Open `/cv/` and `/publications/` in Chromium print preview (`Ctrl+P`) and confirm all `.pub-year-group` and `.cv-item` blocks render without truncation, chrome, or split cards.
- **Lighthouse audit (target: >= 95 across categories):** Run `npx -y lighthouse http://127.0.0.1:1313/ --only-categories=performance,accessibility,best-practices,seo`.
- **CI alignment:** `.github/workflows/hugo.yml` builds with `HUGO_VERSION: 0.165.0`; keep CSS/template syntax compatible with both CI (`0.165.0`) and local Hugo.
