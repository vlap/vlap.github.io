---
name: vlap.github.io
description: Editorial monograph and lab notebook design system for Dr. Vladimir Lapin's climate modeling, HPC, and applied mathematics website.
colors:
  accent-pine: "#203931"
  accent-pine-dark: "#6ee7b7"
  accent-pine-mid: "#3E7060"
  accent-ocean: "#09434e"
  accent-ocean-dark: "#7dd3fc"
  canvas-light: "#ffffff"
  canvas-dark: "#1d1e20"
  surface-dark: "#2e2e33"
  ink-primary-light: "#1e1e1e"
  ink-primary-dark: "#dadadb"
  ink-body-light: "#1f1f1f"
  ink-body-dark: "#c4c4c5"
  ink-secondary-light: "#6c6c6c"
  ink-secondary-dark: "#9b9c9d"
  surface-tertiary-light: "#d6d6d6"
  surface-tertiary-dark: "#414244"
  border-hairline-light: "#eeeeee"
  border-hairline-dark: "#333333"
  code-surface-light: "#f5f5f5"
  code-surface-dark: "#37383e"
typography:
  display:
    fontFamily: 'Georgia, "Times New Roman", Times, serif'
    fontSize: "2.2rem"
    fontWeight: 700
    lineHeight: 1.2
    letterSpacing: "0em"
  headline:
    fontFamily: 'Georgia, "Times New Roman", Times, serif'
    fontSize: "1.6rem"
    fontWeight: 700
    lineHeight: 1.2
    letterSpacing: "0em"
  title:
    fontFamily: 'Georgia, "Times New Roman", Times, serif'
    fontSize: "1.25rem"
    fontWeight: 600
    lineHeight: 1.3
    letterSpacing: "0em"
  body:
    fontFamily: '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Oxygen, Ubuntu, Cantarell, "Open Sans", "Helvetica Neue", sans-serif'
    fontSize: "1.125rem"
    fontWeight: 400
    lineHeight: 1.6
    letterSpacing: "0em"
  label:
    fontFamily: '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Oxygen, Ubuntu, Cantarell, "Open Sans", "Helvetica Neue", sans-serif'
    fontSize: "0.75rem"
    fontWeight: 600
    lineHeight: 1.4
    letterSpacing: "0.02em"
  mono:
    fontFamily: 'ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, "Liberation Mono", "Courier New", monospace'
    fontSize: "0.78rem"
    fontWeight: 600
    lineHeight: 1.4
    letterSpacing: "0em"
rounded:
  none: "0px"
  xs: "4px"
  sm: "6px"
  md: "8px"
  pill: "12px"
  full: "9999px"
spacing:
  xs: "4px"
  sm: "8px"
  md: "16px"
  lg: "24px"
  xl: "36px"
components:
  button-primary:
    backgroundColor: "{colors.canvas-light}"
    textColor: "{colors.ink-primary-light}"
    rounded: "{rounded.md}"
    padding: "10px 16px"
  button-primary-hover:
    backgroundColor: "{colors.accent-pine}"
    textColor: "{colors.canvas-light}"
  chip-badge:
    backgroundColor: "{colors.surface-tertiary-light}"
    textColor: "{colors.ink-primary-light}"
    rounded: "{rounded.pill}"
    padding: "2px 10px"
  card-flat:
    backgroundColor: "{colors.canvas-light}"
    textColor: "{colors.ink-primary-light}"
    rounded: "{rounded.md}"
    padding: "20px"
  input-filter:
    backgroundColor: "{colors.canvas-light}"
    textColor: "{colors.ink-primary-light}"
    rounded: "{rounded.md}"
    padding: "10px 38px 10px 42px"
---

# Design System: vlap.github.io

## Overview

**Creative North Star: "The Applied Mathematician's Monograph & Lab Notebook"**

This design system unifies classical applied-mathematics publishing with modern engineering precision. Long-form technical articles, KaTeX derivations, Fortran kernels, and fluid-dynamics visualizations occupy calm, uncluttered columns anchored by crisp serif section headings and hairline pine dividers carried forward from the legacy "Save The Earth" site.

Color and motion stay strictly subordinate to reading comprehension and operational speed. Neutrals carry the canvas and card geometry, while deep pine and ocean accents mark interactive links, selections, active states, and structural rules across both light and dark modes.

**Key Characteristics:**
- **Editorial Authority:** Georgia serif headings paired with hairline mid-pine bottom rules and a strict 68ch prose reading measure.
- **Flat Tactility:** Crisp 1px borders without resting ambient shadows or colored glow halos.
- **Heritage Accents:** Deep pine and ocean ink tokens adapted explicitly for light and dark surfaces at >= 4.5:1 WCAG AA contrast.
- **Operational Restraint:** Progressive `<details>` disclosures, instant CSS Highlights filtering, and lightweight local video facades.

## Colors

The palette pairs neutral PaperMod paper and charcoal surfaces with a restrained deep-pine and ocean heritage accent pair derived from the legacy site.

### Primary
- **Deep Pine** (`#203931` light / `#6ee7b7` dark): Used for `::selection` highlights, native `accent-color` controls, interactive hover fills on primary links/play icons, and focus indicators.
- **Mid Pine** (`#3E7060`): Used as the 1px structural hairline rule under section headings, blockquote hairlines, link underline decoration, and interactive card hover borders.

### Secondary
- **Deep Ocean** (`#09434e` light / `#7dd3fc` dark): Used for inline prose hyperlinks and scholarly cross-references so links read distinctly from body copy without harsh neon saturation.

### Neutral
- **Canvas** (`#ffffff` light / `#1d1e20` dark): Primary page background.
- **Elevated Card Surface** (`#ffffff` light / `#2e2e33` dark): Card backgrounds for software, CV entries, publication cards, and simulation tiles.
- **Primary Ink** (`#1e1e1e` light / `#dadadb` dark): Headings, card titles, pill/badge text, and primary controls (`>= 4.5:1` on all surfaces including tertiary pills).
- **Body Ink** (`#1f1f1f` light / `#c4c4c5` dark): Long-form reading prose and technical lists.
- **Secondary Ink** (`#6c6c6c` light / `#9b9c9d` dark): Metadata timestamps, institutions, and non-pill supporting captions.
- **Tertiary Fill** (`#d6d6d6` light / `#414244` dark): Neutral pill, tag, and badge container fill.
- **Hairline Border** (`#eeeeee` light / `#333333` dark): Default 1px structural border around cards, inputs, tables, and timelines.
- **Code Surface** (`#f5f5f5` light / `#37383e` dark): Inline code chips, BibTeX `<pre>` blocks, and code containers.

### Named Rules
**The Heritage Scarcity Rule.** Reserve deep pine and ocean exclusively for section rules, inline links, active selections, and interactive emphasis; never flood card backgrounds with saturated brand fills.
**The Pill Contrast Rule.** Never render small pill, tag, or badge text in `--secondary` over `--tertiary`; always use `--primary` (or dedicated WCAG AA semantic tokens) to maintain >= 4.5:1 contrast.

## Typography

**Display Font:** `Georgia, "Times New Roman", Times, serif` for `h1`, `h2`, and `.post-title`.
**Body Font:** System UI sans (`-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Oxygen, Ubuntu, Cantarell, "Open Sans", "Helvetica Neue", sans-serif`) for body prose, navigation, and dense card titles.
**Label/Mono Font:** System monospace (`ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, "Liberation Mono", "Courier New", monospace`) for Fortran/Python code listings, BibTeX records, and license pills.

**Character:** Serif headings lend monograph gravitas to theoretical sections while crisp system sans keeps multi-column grids, CV dates, and mobile viewports effortless to scan.

### Hierarchy
- **Display** (700, `2.2rem`, `1.2`): Homepage hero heading and page titles with `text-wrap: balance`.
- **Headline** (700, `1.6rem`, `1.2`): Major article and section `h2` headings, underlined with a 1px mid-pine rule (`0.35rem` bottom padding).
- **Title** (600, `1.25rem`, `1.3`): Subsection `h3` headings and card titles (borderless inside cards and `.cv-item-title`).
- **Body** (400, `1.125rem`, `1.6`): Long-form prose capped at `68ch` with `text-wrap: pretty` and `0.18em` link underline offset.
- **Label** (600, `0.75rem`, `1.4`, `0.02em`): Compact metadata pills, skill tags, and `tabular-nums` badges/metrics/table cells.

### Named Rules
**The 68ch Monograph Measure Rule.** Constrain `.post-content p` and `.post-content li` to `68ch` for comfortable reading while exempting image-bearing paragraphs and `<figure>` blocks at `100%` container width.
**The Tabular Numerals Rule.** Apply `font-variant-numeric: tabular-nums` on `.metric-value`, `.pub-year-pill`, `.cv-date-badge`, and `table td` so numeric benchmarks and CV dates align cleanly.

## Layout

Content sits inside a centered single reading column (`720px` `--main-width`) framed by a `1024px` navigation bar (`24px` `--gap` desktop, `14px` mobile). Dense catalogs such as `/software/` use responsive CSS grids (`minmax(min(100%, 300px), 1fr)` for software cards and `minmax(min(100%, 350px), 1fr)` for 4:3 simulation tiles) with `min-width: 0; max-width: 100%` containment so wide tables and KaTeX equations scroll internally without horizontal viewport overflow. Long secondary CV lists (Trainings and Presentations) use progressive `<details class="cv-section-details">` disclosures on `/cv/` while remaining expanded on standalone routes and `@media print`.

## Elevation & Depth

Surfaces are flat by default (`box-shadow: none`) and establish separation through 1px `--border` hairlines and subtle light/dark surface contrast (`--theme` vs `--entry`). Hover states shift border color to `--accent-pine-mid` and apply gentle 1–3px vertical lift without drop shadows or chromatic glow halos.

### Named Rules
**The Flat-By-Default Rule.** Cards, inputs, covers, and play buttons carry zero resting `box-shadow` and zero colored glow halos; depth is expressed solely through 1px borders and clean surface hierarchy.

## Shapes

The system favors clean rectangular geometry anchored by an `8px` (`--radius`) default corner radius on cards, download buttons, and disclosures, tightening to `4px`–`6px` on compact technical pills and BibTeX code blocks, `12px` on skill/year pills, `0px` on structural hairline blockquotes, and circular `50%` masks on the author portrait and play icon.

## Components

Controls feel tactile, keyboard-obvious, and strictly utilitarian without decorative clutter.

### Buttons
- **Shape:** Gently rounded (`8px`) for `.cv-download-btn`, `.view-all-link`, `.pub-empty-reset-btn`, and `.cv-details-summary`; `44px` minimum touch target height on primary/mobile controls.
- **Primary:** `--entry` surface, `1px solid var(--border)` hairline, `--primary` label text, `10px 16px` padding.
- **Hover / Focus:** Transitions border to `--accent-pine-mid` (or solid `--accent-pine` fill with `--theme` text on `.view-all-link` and `.sim-play-icon`); preserves visible `2px` `:focus-visible` outline with `2px` offset.

### Chips
- **Style:** `--tertiary` background, `--primary` text (`>= 4.5:1` contrast), `2px 10px` padding (`12px` pill radius for badges/years, `4px` for technical tags/BibTeX actions).
- **State:** Hover deepens background to `--border` without dropping contrast; semantic `.badge-hpc`, `.badge-ai`, `.badge-lead` pair distinct hue-matched borders with accessible light/dark text.

### Cards / Containers
- **Corner Style:** `8px` (`--radius`).
- **Background:** `--entry` (`#ffffff` light / `#2e2e33` dark).
- **Shadow Strategy:** `box-shadow: none` at rest and on hover (see Elevation & Depth).
- **Border:** `1px solid var(--border)` at rest; `var(--accent-pine-mid)` on hover.
- **Internal Padding:** `20px` (software cards), `14px 18px` (CV items), `1.1rem 1.25rem` (publication cards).

### Inputs / Fields
- **Style:** `--entry` surface, `1px solid var(--border)`, `8px` radius, `10px 38px 10px 42px` padding on `#pubFilterInput`.
- **Focus:** `2px solid var(--primary)` outline with `2px` offset on `:focus-visible`.

### Navigation
- Horizontal header bar (`#menu`) with active bottom indicator, `44x44px` `#theme-toggle` button, and pill-style `.cv-nav-bar` / `.pub-year-nav` jump links (`4px 12px`, `14px` radius).

### Simulation Facade & Disclosure
- Self-hosted 4:3 `.sim-video` containers render crisp `480x360` WebP posters inside a native `<button class="sim-facade">` that swaps cleanly via `replaceChildren(video)` into a muted/controls `<video>` element (`cubic-bezier(0.22, 1, 0.36, 1)` hover scale on the play badge, disabled under `prefers-reduced-motion: reduce`).
- `.cv-section-details` uses native `<details>`/`<summary>` with an inline SVG chevron and automatic expansion on `@media print` and anchor navigation.

## Do's and Don'ts

### Do:
- **Do** use `--accent-pine` (`#203931` / `#6ee7b7`) and `--accent-ocean` (`#09434e` / `#7dd3fc`) for structural hairlines, prose links, selections, and interactive emphasis.
- **Do** keep all cards flat (`1px solid var(--border)`, `box-shadow: none`) and use `var(--primary)` for text on `--tertiary` pills.
- **Do** preserve `Georgia` serif display headings with `1px solid var(--accent-pine-mid)` bottom hairlines on section `h2`s while keeping card titles borderless.
- **Do** declare explicit dimensions (`width`/`height`) on media, `tabular-nums` on numeric badges/tables, and `beforeprint`/`@media print` expansion on `<details>`.

### Don't:
- **Don't** add colored blurred shadows (`dark-glow`), bounce easing (`1.56`), thick colored `border-left` side-tabs on cards, or nested cards inside cards.
- **Don't** use `var(--secondary)` text inside `.post-tag`, `.software-tag`, `.sim-spec-pill`, `.cv-date-badge`, `.cv-skills-tag`, or `.pub-year-pill`.
- **Don't** replace native `<button>`/`<details>` controls with `<div>` click handlers or inject raw HTML via `innerHTML`.
- **Don't** modify anything inside the read-only `themes/PaperMod/` submodule.
