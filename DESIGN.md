---
name: vlap.github.io
description: Mathematical monograph and lab notebook design system for Dr. Vladimir Lapin's climate modeling, numerical PDEs, and HPC website.
colors:
  accent-pine: "#203931"
  accent-pine-dark: "#6ee7b7"
  accent-pine-mid: "#3E7060"
  accent-pine-mid-dark: "#5aa38b"
  accent-ocean: "#09434e"
  accent-ocean-dark: "#7dd3fc"
  canvas-light: "#ffffff"
  canvas-dark: "#1d1e20"
  ink-primary-light: "#1e1e1e"
  ink-primary-dark: "#dadadb"
  ink-body-light: "#1f1f1f"
  ink-body-dark: "#c4c4c5"
  ink-secondary-light: "#6c6c6c"
  ink-secondary-dark: "#9b9c9d"
  surface-pill-light: "#eef2f0"
  surface-pill-dark: "#2b3033"
  surface-pill-hover-light: "#dfe6e3"
  surface-pill-hover-dark: "#363c40"
  hairline-light: "#e2e6e4"
  hairline-dark: "#303437"
  border-control-light: "#7d8783"
  border-control-dark: "#757d7a"
  code-surface-light: "#f5f5f5"
  code-surface-dark: "#37383e"
typography:
  display:
    fontFamily: 'system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif'
    fontSize: "clamp(1.85rem, 1.4rem + 1.5vw, 2.35rem)"
    fontWeight: 700
    lineHeight: 1.15
    letterSpacing: "-0.025em"
  headline:
    fontFamily: 'system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif'
    fontSize: "clamp(1.3rem, 1.15rem + 0.5vw, 1.55rem)"
    fontWeight: 700
    lineHeight: 1.25
    letterSpacing: "-0.015em"
  title:
    fontFamily: 'system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif'
    fontSize: "1.125rem"
    fontWeight: 650
    lineHeight: 1.35
    letterSpacing: "-0.01em"
  body:
    fontFamily: 'system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif'
    fontSize: "1.0625rem"
    fontWeight: 400
    lineHeight: 1.62
    letterSpacing: "0em"
  label:
    fontFamily: 'ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, "Liberation Mono", "Courier New", monospace'
    fontSize: "0.78rem"
    fontWeight: 600
    lineHeight: 1.3
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
  full: "9999px"
spacing:
  xs: "4px"
  sm: "8px"
  md: "16px"
  lg: "24px"
  xl: "36px"
components:
  pill-action:
    backgroundColor: "{colors.surface-pill-light}"
    textColor: "{colors.ink-primary-light}"
    rounded: "{rounded.xs}"
    padding: "0.25rem 0.6rem"
  pill-action-hover:
    backgroundColor: "{colors.surface-pill-hover-light}"
    textColor: "{colors.accent-pine}"
  pill-action-primary:
    backgroundColor: "{colors.accent-pine}"
    textColor: "{colors.canvas-light}"
    rounded: "{rounded.xs}"
    padding: "0.25rem 0.6rem"
  button-cv-download:
    backgroundColor: "{colors.canvas-light}"
    textColor: "{colors.ink-primary-light}"
    rounded: "{rounded.xs}"
    padding: "0.75rem 0.9rem"
  button-cv-download-hover:
    backgroundColor: "{colors.surface-pill-light}"
    textColor: "{colors.ink-primary-light}"
  row-monograph:
    backgroundColor: "{colors.canvas-light}"
    textColor: "{colors.ink-primary-light}"
    rounded: "{rounded.none}"
    padding: "1rem 0"
  input-filter:
    backgroundColor: "{colors.canvas-light}"
    textColor: "{colors.ink-primary-light}"
    rounded: "{rounded.xs}"
    padding: "10px 38px 10px 42px"
---

# Design System: vlap.github.io

## Overview

**Creative North Star: "The Computational Physicist's Monograph & Lab Notebook"**

This design system treats technical research, numerical PDEs, and high-performance computing engineering as a cohesive monograph rather than a generic blog. Every route shares a single aligned `45rem` (`720px`) reading column anchored by a left-aligned editorial masthead on Home, a spherical-grid & finite-difference stencil emblem derived from `profile-symbol.svg`, hairline section rules, tabular numerals, and compact monospace action pills.

Neutrals hold the full canvas and structural cadence across both light and dark modes, while deep pine and ocean heritage accents mark interactive links, selections, blockquote hairlines, primary calls to action, and spherical-grid linework. We explicitly reject generic WordPress academic blog patterns such as Nick Higham's `nhigham.com` utility sidebar, recent-posts/archive/category widget columns, subscriber widgets, and stacked blog-card boxes.

**Key Characteristics:**
- **Left-Aligned Monograph Authority:** Home opens with a left-aligned portrait-and-identity masthead featuring the spherical-grid stencil emblem, a ruled Current Focus line, and a three-column audience index rather than a centered social-profile card.
- **Hairline-Ruled Hierarchy:** Log entries, CV presentations/trainings, and publication records use `1px` structural hairlines on a unified canvas (`#ffffff` light / `#1d1e20` dark) instead of elevated card boxes.
- **Tabular Precision & Compact Action Pills:** Dates, publication metrics, CV badges, and filter controls align with `tabular-nums` monospace typography and `4px`-radius action pills (`PDF`, `Code`, `Slides`, `DOI`, `Copy BibTeX`, `View BibTeX`) meeting WCAG 2.1 AA contrast (`>= 4.5:1`).
- **Zero-Overhead Performance:** Native system sans-serif and monospace stacks eliminate webfont network latency and layout shift (`CLS === 0`), while progressive `<details>` disclosures, `CSS.highlights` filtering, and local video facades keep interaction instant.

## Colors

The palette pairs neutral paper and charcoal surfaces with a restrained deep-pine and ocean heritage accent system resolved automatically via `light-dark()` with explicit light/dark fallbacks.

### Primary
- **Deep Pine** (`accent-pine` light / `accent-pine-dark` dark): Used for `::selection` fills, native `accent-color` controls, active navigation/filter indicators, primary action pill backgrounds, featured CV badges, and hover accents.
- **Mid Pine** (`accent-pine-mid` light / `accent-pine-mid-dark` dark): Used for the `1px` left blockquote rule, prose underline decoration, hairline hover highlights, and the finite-difference stencil lines (calibrated for `>= 4.5:1` / UI-control contrast on dark surfaces).

### Secondary
- **Deep Ocean** (`accent-ocean` light / `accent-ocean-dark` dark): Used for inline prose hyperlinks, scholarly cross-references, and spherical-grid meridians so links read distinctly from body copy without harsh neon saturation.

### Neutral
- **Canvas** (`canvas-light` / `canvas-dark`): Unified page background across single articles, list feeds, and grids.
- **Primary Ink** (`ink-primary-light` / `ink-primary-dark`): Headings, titles, bold scan leads, and action-pill text (`>= 9.55:1` on pill surfaces).
- **Body Ink** (`ink-body-light` / `ink-body-dark`): Long-form reading prose, summaries, and simulation descriptions.
- **Secondary Ink** (`ink-secondary-light` / `ink-secondary-dark`): Non-pill metadata timestamps, dates, author lists, and filter placeholders (`>= 5.25:1`).
- **Pill Surface & Hover** (`surface-pill-light` / `surface-pill-dark` and hover variants): Low-chroma tinted backgrounds for action pills, kind badges, tags, and compact navigation chips.
- **Control Border** (`border-control-light` / `border-control-dark`): High-contrast `1px` border (`>= 3.0:1` UI contrast) around pills, buttons, and filter inputs.
- **Structural Hairline** (`hairline-light` / `hairline-dark`): Subtle `1px` row dividers, section rules, header/footer boundaries, and code frame borders.
- **Code Surface** (`code-surface-light` / `code-surface-dark`): Inline code spans, BibTeX `<pre>` blocks, and syntax-highlighted listings.

### Named Rules
**The Heritage Scarcity Rule.** Reserve deep pine and ocean exclusively for structural rules, inline prose links, selections, primary actions, and the spherical-grid emblem; never flood general page cards with saturated brand fills.
**The Pill Contrast Rule.** Always pair small pills, tags, and action badges with primary ink over tinted pill surfaces (or canvas ink over deep pine for primary pills) to sustain `>= 4.5:1` WCAG AA contrast in both light and dark modes.
**The Control Border Rule.** Give interactive pills, inputs, and disclosure controls a visible `border-control` stroke (`>= 3.0:1` against canvas) so buttons remain unmistakable without relying on drop shadows.

## Typography

**Display Font:** System UI sans (`system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif`) for `h1`, page headers, and monograph titles.
**Body Font:** System UI sans (identical stack) for long-form prose, project descriptions, and publication abstracts (`CLS === 0`).
**Label/Mono Font:** System monospace (`ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, "Liberation Mono", "Courier New", monospace`) for dates, action pills, kind badges, CV tools/badges, BibTeX records, and code listings.

**Character:** Fluid `clamp()` display/headline scaling pairs with crisp `650`/`700` sans weights and `tabular-nums` monospace metadata, letting readers scan dates, metrics, and equations cleanly without decorative serif or webfont overhead.

### Hierarchy
- **Display** (700, `clamp(1.85rem, 1.4rem + 1.5vw, 2.35rem)`, `1.15`): Page titles and Home masthead name with `-0.025em` tracking and `text-wrap: balance`.
- **Headline** (700, `clamp(1.3rem, 1.15rem + 0.5vw, 1.55rem)`, `1.25`): Section `h2` headings with a `1px` structural hairline bottom rule.
- **Title** (650, `1.125rem`, `1.35`): Subsection `h3` headings, software card titles, simulation titles, and publication titles.
- **Body** (400, `1.0625rem`, `1.62`): Long-form reading prose filling the `45rem` (`720px`, `~68–75ch`) measure with `text-wrap: pretty` and `0.18em` underline offset.
- **Label / Mono** (600, `0.78rem`, `1.3`): Action pills, kind badges, ISO dates (`0.8125rem`), CV date badges, and `tabular-nums` metrics.

### Named Rules
**The Unified Column Measure Rule.** Align `.header-nav` and `.main` to `45rem` (`720px`) so mastheads, prose, tables, KaTeX blocks, ruled lists, and footer chrome share exact left and right edges on desktop.
**The Tabular Numerals Rule.** Apply `font-variant-numeric: tabular-nums` across ISO Log dates, publication years/metrics, CV date badges, simulation spec pills, and table cells so numeric columns align vertically.

## Layout

All routes inhabit a single centered `45rem` (`720px`) column with `24px` desktop (`14px` mobile) gutter padding and `min-width: 0` containment down to `320px`. On Home, the `.home-masthead` pairs a compact square portrait (`96px` desktop, `clamp(4.5rem, 18vw, 6rem)`), left-aligned `h1`/tagline, and inline spherical-grid emblem (`home-domain-emblem`), followed by the single-occurrence bio, ruled Current Focus, and 3-column `.home-audience-links` strip (collapsing to 1 column at `<= 600px`). Both Home and `/posts/` / `/kinds/*` render a 2-column `.log-rows` grid (`10.5rem minmax(0, 1fr)` on desktop, `1fr` below `600px`) with stretched-link title navigation. `/work/` uses responsive `minmax(min(100%, 300px), 1fr)` software grids and `minmax(min(100%, 350px), 1fr)` 4:3 simulation tiles. `/cv/` leads with a 2-column `.cv-download-bar` (stacking below `600px`), `.cv-nav-bar` jumping to Experience/Education or linking directly to `/cv/trainings/`, `/cv/presentations/`, and `/publications/`, and left-ruled `.cv-timeline`. `/publications/` pairs `#pubFilterInput` and `.pub-year-nav` with `content-visibility: auto` year groups (reset for print) and full-width wrapping `<details class="pub-bibtex-details">` drawers.

## Elevation & Depth

Surfaces are flat by default (`box-shadow: none`) and establish hierarchy exclusively through `1px` hairline borders, subtle pill-surface tinting, and typography weight contrast. Hover and focus states shift borders to `--accent-pine` / `--accent-pine-mid` or darken `--surface-pill` to `--surface-pill-hover` without drop shadows, transform lifts, or colored glow halos.

### Named Rules
**The Flat-By-Default Rule.** Cards, ruled rows, inputs, cover frames, and play controls carry zero resting `box-shadow` and zero hover translate lifts; spatial separation comes strictly from `1px` hairlines and calibrated whitespace.

## Shapes

Rectangular editorial geometry dominates: `0px` radius on ruled Log/CV/Publication rows, blockquotes, and the 3-column audience strip; `4px` (`xs`) radius on action pills, filter inputs, software/simulation cards, BibTeX `<pre>` blocks, and pagination boxes; `6px` (`sm`) radius on the Home portrait frame; and `50%` (`full`) circular geometry strictly on the simulation play badge and CV timeline nodes.

## Components

Controls are compact, keyboard-obvious, `>= 44px` accessible on touch/primary targets (`>= 2.25rem` on coarse pointers), and built on native HTML primitives (`<a>`, `<button>`, `<details>`/`<summary>`).

### Action Pills & CV Download Buttons
- **Shape:** `4px` radius (`min-block-size: 1.85rem` desktop, `2.25rem` coarse pointer).
- **Default (`action-pill`):** `--surface-pill` fill, `--primary` monospace `600` text, `1px solid var(--border-control)`, `0.25rem 0.6rem` padding; used for `DOI ↗`, `URL ↗`, `Copy BibTeX`, `View BibTeX`, `Slides (PDF) ↗`, `Thesis PDF ↗`, `Site ↗`, and `Discuss on LinkedIn →`.
- **Primary (`action-pill--primary`):** Solid `--accent-pine` fill with `--theme` text for primary actions such as `Talk page →` and featured `2-page · PDF` CV badges.
- **CV Download Bar:** 2-column grid of bordered `4px` buttons (`vladimir-lapin-cv-research-full.pdf` then `vladimir-lapin-cv-industry.pdf`) featuring explicit monospace format badges (`Full · PDF` and primary `2-page · PDF`).

### Chips & Taxonomy Badges
- **Style:** `4px` radius monospace chips (`--surface-pill` background, `--primary` ink, `1px solid var(--border-control)`) for `.kind-badge`, `.log-kind-pill`, `.post-tag`, `.terms-tags a`, `.software-tag`, `.sim-spec-pill`, `.cv-date-badge`, `.cv-skills-tag`, and `.pub-year-pill`.
- **State:** Active `.log-kind-pill.active` uses solid `--accent-pine` with `--theme` text; semantic `.badge-hpc` / `.badge-ai` / `.badge-lead` keep hue-matched borders at `>= 4.5:1` contrast.

### Ruled Monograph Rows & Grid Cards
- **Log Rows (`.log-row`):** Hairline-separated two-column rows (`YYYY-MM-DD` + `.kind-badge` left; title, 2-line summary, tags, and action pills right) using stretched-link `::after` overlay on `.log-row-title-link.entry-link` with `z-index: 2` on independent nested links.
- **Publication & CV Rows (`.pub-card`, `.cv-item`):** Full-width hairline rows (`1.1rem 0` / `1.05rem 0` padding) with top border shifting to `--accent-pine-mid` on hover; `.pub-card-actions` aligns at `flex-start` so open `<details class="pub-bibtex-details">` wraps cleanly onto its own `100%` row without shifting adjacent buttons.
- **Software & Simulation Cards:** `4px` bordered flat cards on `--theme` canvas with `min-width: 0` containment, bordered GitHub icon pill / `Site ↗` pill in `.software-card-header`, and flat `border-top: 1px solid var(--border)` `.sim-physics` notes.

### Inputs / Fields
- **Filter Input (`#pubFilterInput`):** `--theme` background, `1px solid var(--border-control)`, `4px` radius, `10px 38px 10px 42px` padding, accessible `--secondary` placeholder (`>= 5.25:1`), `32x32px` `#pubFilterClear`, `/` and `Escape` keyboard shortcuts (`isComposing`-guarded), and `::highlight(pub-search-match)` matches.

### Navigation
- **Primary Header & Footer:** Single-row `45rem` nav bar (`Work`, `Log`, `CV` + `44x44px` `#theme-toggle`), hairline footer with 6 labeled icon links, `.log-kind-filter` / `.cv-nav-bar` / `.pub-year-nav` pill strips, and `.paginav` prev/next boxes stacking vertically below `600px`.

### Signature Components
- **Editorial Masthead & Spherical-Grid Emblem:** Left-aligned `96px` portrait (`fetchpriority="high"`), display name, tagline, and an inline `64x64` spherical-grid & finite-difference stencil emblem (`home-domain-emblem`, `aria-hidden="true"`) themed via `--accent-ocean`, `--accent-pine-mid`, and `--accent-pine`.
- **Simulation Facade & Progressive Disclosure:** 4:3 `<button type="button" class="sim-facade">` (`480x360` WebP poster, `cubic-bezier(0.22, 1, 0.36, 1)` play-badge scale disabled under `prefers-reduced-motion: reduce`, `replaceChildren(video)` swap) and native `<details class="cv-section-details">` expanding automatically on anchor click, `beforeprint`, and `@media print`.

## Do's and Don'ts

### Do:
- **Do** align all site routes inside the unified `45rem` (`720px`) monograph column with `1px solid var(--hairline)` section and row dividers.
- **Do** use `--surface-pill`, `--border-control`, and `--primary` (or `--accent-pine` / `--theme` for primary actions) so every badge, pill, and button maintains `>= 4.5:1` contrast in both light and dark modes.
- **Do** keep `font-variant-numeric: tabular-nums` on ISO dates, metrics, publication years, CV badges, and tables, and `min-width: 0` on all grid/flex containers down to `320px`.
- **Do** preserve native `<button>`, `<details>`, `beforeprint`/`@media print` expansion, explicit media dimensions, and `prefers-reduced-motion` guards.

### Don't:
- **Don't** imitate Nick Higham (`nhigham.com`) or generic WordPress academic sites: never add a right/left utility sidebar, recent-posts/archive/category widget column, subscriber widget, or stacked card-box blog feeds.
- **Don't** restore a centered social-profile stack on Home, eyebrow kickers above `<h1>` headings, resting `box-shadow`s, `transform` hover lifts, `"Georgia"` serifs, or bounce easing (`1.56`).
- **Don't** set `color: var(--secondary)` on pill/tag surfaces, apply `max-width: 68ch` inside the `45rem` column, inject HTML via `innerHTML`, or modify `themes/PaperMod/`.
