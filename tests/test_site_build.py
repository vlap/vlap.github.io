"""Build, static DOM, CSS, SRI, Speculation Rules, and link checks for vlap.github.io."""

from __future__ import annotations

import json
import re
import shutil
import subprocess
import tempfile
import tomllib
import xml.etree.ElementTree as ET
from pathlib import Path
from urllib.parse import unquote

import pytest
import tinycss2
import yaml
from bs4 import BeautifulSoup


REPO_ROOT = Path(__file__).resolve().parent.parent

KATEX_EXPECTED = {
    "https://cdn.jsdelivr.net/npm/katex@0.16.11/dist/katex.min.css": (
        "sha384-nB0miv6/jRmo5UMMR1wu3Gz6NLsoTkbqJghGIsx//Rlm+ZU03BU6SQNC66uf4l5+"
    ),
    "https://cdn.jsdelivr.net/npm/katex@0.16.11/dist/katex.min.js": (
        "sha384-7zkQWkzuo3B5mTepMUcHkMB5jZaolc2xDwL6VFqjFALcbeS9Ggm/Yr2r3Dy4lfFg"
    ),
    "https://cdn.jsdelivr.net/npm/katex@0.16.11/dist/contrib/auto-render.min.js": (
        "sha384-43gviWU0YVjaDtb/GhzOouOXtZMP/7XUzwPTstBeZFe/+rCMvRwr4yROQP43s0Xk"
    ),
}

KATEX_PAGES = [
    "posts/2026-06-15-neural-surrogates-shallow-water-equations/index.html",
]


def _is_meta_refresh_redirect(html_text: str) -> bool:
    return 'http-equiv="refresh"' in html_text.lower() or "http-equiv=refresh" in html_text.lower()


@pytest.fixture(scope="module")
def built_site() -> Path:
    """Build Hugo site into a snap-safe directory under REPO_ROOT and clean up."""
    out_dir = Path(tempfile.mkdtemp(prefix="_tmp_hugo_test_", dir=REPO_ROOT))
    try:
        proc = subprocess.run(
            ["hugo", "--gc", "--minify", "-d", str(out_dir)],
            cwd=str(REPO_ROOT),
            capture_output=True,
            text=True,
            check=False,
        )
        combined = f"{proc.stdout}\n{proc.stderr}"
        assert proc.returncode == 0, f"Hugo build failed:\n{combined}"
        assert "WARN" not in combined, f"Hugo emitted warnings:\n{combined}"
        assert "ERROR" not in combined, f"Hugo emitted errors:\n{combined}"
        yield out_dir
    finally:
        shutil.rmtree(out_dir, ignore_errors=True)


@pytest.fixture(scope="module")
def non_redirect_html_pages(built_site: Path) -> list[tuple[Path, BeautifulSoup]]:
    """Parse all non-redirect HTML pages in the built site."""
    pages: list[tuple[Path, BeautifulSoup]] = []
    for html_path in sorted(built_site.rglob("*.html")):
        raw = html_path.read_text(encoding="utf-8")
        if _is_meta_refresh_redirect(raw):
            continue
        pages.append((html_path.relative_to(built_site), BeautifulSoup(raw, "lxml")))
    assert len(pages) >= 20, f"Expected >=20 built HTML pages, got {len(pages)}"
    return pages


@pytest.fixture(scope="module")
def built_stylesheet(built_site: Path) -> str:
    """Read the single fingerprinted stylesheet bundle."""
    css_files = list((built_site / "assets" / "css").glob("stylesheet*.css"))
    assert len(css_files) == 1, f"Expected 1 built stylesheet, found {css_files}"
    return css_files[0].read_text(encoding="utf-8")


def _parse_css_rules(css_text: str) -> list:
    return tinycss2.parse_stylesheet(
        css_text,
        skip_comments=True,
        skip_whitespace=True,
    )


def _serialize_prelude(rule) -> str:
    return re.sub(r"/\*.*?\*/", "", tinycss2.serialize(rule.prelude)).strip()


def _serialize_content(rule) -> str:
    return re.sub(r"/\*.*?\*/", "", tinycss2.serialize(rule.content)).strip()


def _find_qualified_rules(rules: list, selector_predicate) -> list:
    matched = []
    for rule in rules:
        if rule.type == "qualified-rule":
            prelude = _serialize_prelude(rule)
            if selector_predicate(prelude):
                matched.append((prelude, _serialize_content(rule)))
        elif rule.type == "at-rule" and rule.content is not None:
            nested = tinycss2.parse_rule_list(
                rule.content,
                skip_comments=True,
                skip_whitespace=True,
            )
            matched.extend(_find_qualified_rules(nested, selector_predicate))
    return matched


def test_hugo_build_succeeds_cleanly(built_site: Path) -> None:
    """Verify core pages and CSS bundle exist after clean Hugo build."""
    for rel in ["index.html", "work/index.html", "posts/index.html", "publications/index.html", "cv/index.html"]:
        assert (built_site / rel).is_file(), f"Missing built page: {rel}"


def test_r1_katex_sri_and_referrerpolicy(built_site: Path) -> None:
    """Verify exact KaTeX 0.16.11 SRI hashes, crossorigin, and referrerpolicy on math pages."""
    for rel in KATEX_PAGES:
        soup = BeautifulSoup((built_site / rel).read_text(encoding="utf-8"), "lxml")
        css_tag = soup.find("link", attrs={"rel": "stylesheet", "href": re.compile(r"katex@0\.16\.11/dist/katex\.min\.css")})
        assert css_tag is not None, f"Missing katex.min.css on {rel}"
        assert css_tag.get("integrity") == KATEX_EXPECTED[css_tag["href"]]
        assert css_tag.get("crossorigin") == "anonymous"
        assert css_tag.get("referrerpolicy") == "no-referrer"

        js_tag = soup.find("script", attrs={"src": re.compile(r"katex@0\.16\.11/dist/katex\.min\.js")})
        assert js_tag is not None, f"Missing katex.min.js on {rel}"
        assert js_tag.get("integrity") == KATEX_EXPECTED[js_tag["src"]]
        assert js_tag.get("crossorigin") == "anonymous"
        assert js_tag.get("referrerpolicy") == "no-referrer"

        auto_tag = soup.find("script", attrs={"src": re.compile(r"katex@0\.16\.11/dist/contrib/auto-render\.min\.js")})
        assert auto_tag is not None, f"Missing auto-render.min.js on {rel}"
        assert auto_tag.get("integrity") == KATEX_EXPECTED[auto_tag["src"]]
        assert auto_tag.get("crossorigin") == "anonymous"
        assert auto_tag.get("referrerpolicy") == "no-referrer"

    for no_math_rel in ("index.html", "work/index.html"):
        no_math_soup = BeautifulSoup((built_site / no_math_rel).read_text(encoding="utf-8"), "lxml")
        assert no_math_soup.find(attrs={"href": re.compile(r"katex@")}) is None, f"Unexpected KaTeX CSS on {no_math_rel}"
        assert no_math_soup.find(attrs={"src": re.compile(r"katex@")}) is None, f"Unexpected KaTeX JS on {no_math_rel}"


def test_r1_meta_referrer_and_color_scheme_all_pages(
    non_redirect_html_pages: list[tuple[Path, BeautifulSoup]],
) -> None:
    """Verify <meta name=referrer> and <meta name=color-scheme> appear on every page."""
    for rel, soup in non_redirect_html_pages:
        ref = soup.find("meta", attrs={"name": "referrer"})
        assert ref is not None and ref.get("content") == "strict-origin-when-cross-origin", (
            f"Missing or invalid meta[name=referrer] on {rel}"
        )
        cs = soup.find("meta", attrs={"name": "color-scheme"})
        assert cs is not None and cs.get("content") == "light dark", (
            f"Missing or invalid meta[name=color-scheme] on {rel}"
        )


def test_r1_head_and_footer_sync_meta_color_scheme(built_site: Path) -> None:
    """Verify built scripts synchronize meta[name=color-scheme] on init and toggle."""
    html_text = (built_site / "index.html").read_text(encoding="utf-8")
    assert 'meta[name="color-scheme"]' in html_text or "meta[name=color-scheme]" in html_text
    assert 'localStorage.getItem("pref-theme")' in html_text or "localStorage.getItem('pref-theme')" in html_text
    assert 'localStorage.setItem("pref-theme"' in html_text or "localStorage.setItem('pref-theme'" in html_text
    # Built footer toggle script must also update meta[name="color-scheme"]
    footer_source = (REPO_ROOT / "layouts" / "_partials" / "footer.html").read_text(encoding="utf-8")
    assert "color-scheme" in footer_source


def test_r1_simulation_gallery_uses_replace_children(built_site: Path) -> None:
    """Verify playSimVideo uses replaceChildren(video) without innerHTML."""
    work_text = (built_site / "work/index.html").read_text(encoding="utf-8")
    match = re.search(r"function playSimVideo\([^)]*\)\{[^}]+\}", work_text)
    assert match is not None, "Missing playSimVideo function in built work page"
    fn_body = match.group(0)
    assert re.search(r"\.replaceChildren\(\w+\)", fn_body) is not None, fn_body
    assert ".innerHTML" not in fn_body
    src_text = (REPO_ROOT / "layouts" / "shortcodes" / "simulation_gallery.html").read_text(encoding="utf-8")
    assert "innerHTML" not in src_text
    assert "container.replaceChildren(video)" in src_text


def test_simulation_assets_exist_in_static_and_built_site(built_site: Path) -> None:
    """Verify every poster and video file in data/simulations.yaml exists in static/ and public/."""
    sims = yaml.safe_load((REPO_ROOT / "data" / "simulations.yaml").read_text(encoding="utf-8"))
    assert isinstance(sims, list) and len(sims) == 3
    max_video_bytes = int(1.5 * 1024 * 1024)
    for sim in sims:
        for key in ("poster", "video_webm", "video_mp4"):
            rel_url = sim.get(key)
            assert rel_url and rel_url.startswith("/"), f"Missing root-relative {key} in {sim}"
            rel_path = rel_url.lstrip("/")
            static_file = REPO_ROOT / "static" / rel_path
            built_file = built_site / rel_path
            assert static_file.is_file(), f"Missing static simulation asset: {static_file}"
            assert built_file.is_file(), f"Missing built simulation asset: {built_file}"
            if key.startswith("video_"):
                assert static_file.stat().st_size < max_video_bytes, (
                    f"Video {rel_url} exceeds 1.5 MB: {static_file.stat().st_size} bytes"
                )


def test_r1_css_color_scheme_and_light_dark_badges(built_stylesheet: str) -> None:
    """Verify :root color-scheme, data-theme overrides, and @supports light-dark() badge tokens."""
    rules = _parse_css_rules(built_stylesheet)
    assert not any(
        r.type == "error" for r in rules
    ), "Built CSS contains parse errors"

    root_rules = _find_qualified_rules(rules, lambda p: p == ":root")
    root_combined = ";".join(content for _, content in root_rules)
    assert re.search(r"color-scheme\s*:\s*light dark", root_combined)

    dark_rules = _find_qualified_rules(rules, lambda p: ":root[data-theme=dark]" in p)
    assert any("color-scheme:dark" in c.replace(" ", "") for _, c in dark_rules)

    light_rules = _find_qualified_rules(rules, lambda p: ":root[data-theme=light]" in p)
    assert any("color-scheme:light" in c.replace(" ", "") for _, c in light_rules)

    supports_blocks = [
        r for r in rules
        if r.type == "at-rule" and r.lower_at_keyword == "supports"
        and "light-dark" in _serialize_prelude(r)
        and not _serialize_prelude(r).lstrip().startswith("not")
    ]
    assert supports_blocks, "Missing @supports (color: light-dark(...)) block"
    supports_text = _serialize_content(supports_blocks[0])
    for token in [
        "--badge-hpc-bg", "--badge-hpc-text", "--badge-hpc-border",
        "--badge-ai-bg", "--badge-ai-text", "--badge-ai-border",
        "--badge-lead-bg", "--badge-lead-text", "--badge-lead-border",
    ]:
        assert token in supports_text, f"Missing {token} inside @supports light-dark block"
        assert "light-dark(" in supports_text

    # Ensure fallback custom properties exist on :root outside @supports
    assert "--badge-hpc-bg:" in root_combined


def test_r2_simulation_gallery_native_button_and_css(built_site: Path, built_stylesheet: str) -> None:
    """Verify .sim-facade is a native <button type=button> with valid phrasing children and CSS reset."""
    soup = BeautifulSoup((built_site / "work/index.html").read_text(encoding="utf-8"), "lxml")
    assert soup.select("div.sim-facade") == [], "Legacy div.sim-facade should be replaced by button"
    buttons = soup.select("button.sim-facade")
    assert len(buttons) == 3, f"Expected 3 button.sim-facade elements, got {len(buttons)}"
    for btn in buttons:
        assert btn.get("type") == "button"
        assert (btn.get("aria-label") or "").startswith("Play ")
        assert btn.find("div") is None, "<button> must not contain flow <div> children"

    rules = _parse_css_rules(built_stylesheet)
    facade_rules = _find_qualified_rules(rules, lambda p: p == ".sim-facade")
    assert facade_rules, "Missing .sim-facade rule in built CSS"
    facade_css = facade_rules[0][1].replace(" ", "")
    assert "border:0" in facade_css
    assert "padding:0" in facade_css


def test_r2_pub_filter_status_and_decorative_svgs(
    built_site: Path,
    non_redirect_html_pages: list[tuple[Path, BeautifulSoup]],
) -> None:
    """Verify #pubFilterStatus live region and aria-hidden=true on decorative SVGs."""
    pub_soup = BeautifulSoup((built_site / "publications/index.html").read_text(encoding="utf-8"), "lxml")
    status = pub_soup.select_one("#pubFilterStatus")
    assert status is not None
    assert status.get("role") == "status"
    assert status.get("aria-live") == "polite"

    filter_icon = pub_soup.select_one("svg.pub-filter-icon")
    assert filter_icon is not None and filter_icon.get("aria-hidden") == "true"

    copy_svgs = pub_soup.select(".pub-copy-btn svg")
    assert len(copy_svgs) >= 20
    assert all(svg.get("aria-hidden") == "true" for svg in copy_svgs)

    work_soup = BeautifulSoup((built_site / "work/index.html").read_text(encoding="utf-8"), "lxml")
    gh_links = work_soup.select("a.software-github-link")
    assert len(gh_links) >= 5
    for link in gh_links:
        assert link.get("aria-label"), "Icon-only GitHub link must have aria-label"
        svg = link.find("svg")
        assert svg is not None and svg.get("aria-hidden") == "true"

    for rel, soup in non_redirect_html_pages:
        toggle_svgs = soup.select("#theme-toggle svg")
        assert len(toggle_svgs) == 2, f"Expected 2 theme-toggle SVGs on {rel}"
        assert all(svg.get("aria-hidden") == "true" for svg in toggle_svgs)

    header_src = (REPO_ROOT / "layouts" / "_partials" / "header.html").read_text(encoding="utf-8")
    ext_svg_match = re.search(r"findRE.*?<svg[^>]*>", header_src, re.DOTALL)
    assert ext_svg_match is not None and 'aria-hidden="true"' in ext_svg_match.group(0)


def test_r2_focus_visible_outline_preserved(built_stylesheet: str) -> None:
    """Verify #pubFilterInput and generic controls use :focus-visible outline and do not suppress :focus outline."""
    rules = _parse_css_rules(built_stylesheet)
    bad_focus = _find_qualified_rules(rules, lambda p: p == "#pubFilterInput:focus")
    for _, content in bad_focus:
        assert "outline:none" not in content.replace(" ", "")
        assert "outline:0" not in content.replace(" ", "")

    fv_rules = _find_qualified_rules(rules, lambda p: p == "#pubFilterInput:focus-visible")
    assert fv_rules, "Missing #pubFilterInput:focus-visible rule"
    fv_css = fv_rules[0][1].replace(" ", "")
    assert "outline:2pxsolidvar(--primary)" in fv_css or "outline:2pxsolidvar(--accent-pine)" in fv_css
    assert "outline-offset:2px" in fv_css

    generic_fv = _find_qualified_rules(rules, lambda p: ":focus-visible" in p and "a" in p and "button" in p)
    assert generic_fv, "Missing generic :focus-visible outline rule for interactive controls"
    generic_css = ";".join(c for _, c in generic_fv).replace(" ", "")
    assert "outline:2pxsolidvar(--accent-pine)" in generic_css or "outline:2pxsolidvar(--primary)" in generic_css
    assert "outline-offset:2px" in generic_css


def test_r3_images_dimensions_and_lcp_priority(built_site: Path) -> None:
    """Verify avatar fetchpriority/dimensions, simulation poster dimensions, and cover img dimensions."""
    home_soup = BeautifulSoup((built_site / "index.html").read_text(encoding="utf-8"), "lxml")
    avatar = home_soup.select_one(".home-info-image img")
    assert avatar is not None
    assert avatar.get("fetchpriority") == "high"
    w = int(avatar["width"])
    h = int(avatar["height"])
    assert 72 <= w <= 130, f"Expected compact square avatar width in 72..130, got {w}"
    assert w == h, f"Expected square avatar dimensions, got {w}x{h}"

    work_soup = BeautifulSoup((built_site / "work/index.html").read_text(encoding="utf-8"), "lxml")
    posters = work_soup.select("img.sim-poster")
    assert len(posters) == 3
    for img in posters:
        assert img.get("width") == "480"
        assert img.get("height") == "360"
        assert img.get("loading") == "lazy"

    for rel in (
        "posts/index.html",
        "kinds/note/index.html",
        "posts/2026-06-15-neural-surrogates-shallow-water-equations/index.html",
    ):
        soup = BeautifulSoup((built_site / rel).read_text(encoding="utf-8"), "lxml")
        cover_img = soup.select_one("figure.entry-cover img")
        assert cover_img is not None, f"Missing figure.entry-cover img on {rel}"
        assert cover_img.get("width") and int(cover_img["width"]) > 0, f"Missing width on cover img in {rel}"
        assert cover_img.get("height") and int(cover_img["height"]) > 0, f"Missing height on cover img in {rel}"


def test_r3_content_visibility_and_print_reset(built_stylesheet: str) -> None:
    """Verify content-visibility deferral and @media print reset in built CSS."""
    rules = _parse_css_rules(built_stylesheet)
    cv_rules = _find_qualified_rules(
        rules,
        lambda p: ".pub-year-group:nth-of-type(n+3)" in p and ".cv-item:nth-of-type(n+6)" in p,
    )
    assert cv_rules, "Missing content-visibility rule for .pub-year-group:nth-of-type(n+3), .cv-item:nth-of-type(n+6)"
    cv_css = cv_rules[0][1].replace(" ", "")
    assert "content-visibility:auto" in cv_css
    assert "contain-intrinsic-size:autononeauto220px" in cv_css

    print_blocks = [
        r for r in rules
        if r.type == "at-rule" and r.lower_at_keyword == "media" and "print" in _serialize_prelude(r)
    ]
    assert print_blocks, "Missing @media print block"
    print_nested = tinycss2.parse_rule_list(
        print_blocks[0].content,
        skip_comments=True,
        skip_whitespace=True,
    )
    reset_rules = _find_qualified_rules(
        print_nested,
        lambda p: ".pub-year-group" in p and ".cv-item" in p,
    )
    assert reset_rules, "Missing .pub-year-group, .cv-item reset inside @media print"
    reset_css = ";".join(c for _, c in reset_rules).replace(" ", "")
    assert "content-visibility:visible!important" in reset_css
    assert "contain-intrinsic-size:none!important" in reset_css


def test_r3_speculation_rules_json(
    non_redirect_html_pages: list[tuple[Path, BeautifulSoup]],
) -> None:
    """Verify valid Speculation Rules prefetch block on built HTML pages."""
    for rel, soup in non_redirect_html_pages:
        tag = soup.find("script", attrs={"type": "speculationrules"})
        assert tag is not None, f"Missing speculationrules script on {rel}"
        payload = json.loads(tag.string or "")
        assert "prefetch" in payload and len(payload["prefetch"]) >= 1
        rule = payload["prefetch"][0]
        assert rule.get("eagerness") == "moderate"
        clauses = rule["where"]["and"]
        assert {"href_matches": "/*"} in clauses
        assert {"not": {"href_matches": "/downloads/*"}} in clauses
        assert {"not": {"selector_matches": "[rel~=nofollow]"}} in clauses


def test_internal_links_resolve_in_built_site(
    built_site: Path,
    non_redirect_html_pages: list[tuple[Path, BeautifulSoup]],
) -> None:
    """Verify root-relative internal links and assets resolve to files in built_site."""
    missing: list[str] = []
    for rel, soup in non_redirect_html_pages:
        for el in soup.find_all(["a", "link", "script", "img", "video", "source"]):
            urls: list[str] = []
            if el.name in {"a", "link"} and el.get("href"):
                urls.append(el["href"])
            if el.get("src"):
                urls.append(el["src"])
            if el.get("poster"):
                urls.append(el["poster"])
            if el.get("srcset"):
                for part in el["srcset"].split(","):
                    candidate_url = part.strip().split(" ", 1)[0]
                    if candidate_url:
                        urls.append(candidate_url)
            for url in urls:
                if not url or not url.startswith("/") or url.startswith("//"):
                    continue
                path_part = unquote(url.split("#", 1)[0].split("?", 1)[0])
                if not path_part or path_part == "/":
                    continue
                candidate = built_site / path_part.lstrip("/")
                if candidate.is_file() or (candidate / "index.html").is_file():
                    continue
                missing.append(f"{rel} -> {url}")

    assert not missing, "Broken internal links:\n" + "\n".join(missing[:20])


def test_404_excluded_from_sitemap_and_rss_and_no_index_json(built_site: Path) -> None:
    """Verify /404.html exists cleanly at site root, index.xml only includes Log posts, and /search/ + index.json are absent."""
    assert not (built_site / "index.json").exists(), "index.json should not be generated"
    assert not (built_site / "search").exists(), "/search/ should not be generated"

    sitemap_root = ET.fromstring((built_site / "sitemap.xml").read_text(encoding="utf-8"))
    locs = [el.text or "" for el in sitemap_root.iter("{http://www.sitemaps.org/schemas/sitemap/0.9}loc")]
    assert len(locs) >= 10
    assert not any(loc.endswith("/404/") or loc.endswith("/404.html") for loc in locs), (
        "404 page leaked into sitemap.xml"
    )

    rss_root = ET.fromstring((built_site / "index.xml").read_text(encoding="utf-8"))
    rss_links = [el.text or "" for el in rss_root.findall("./channel/item/link")]
    expected_post_suffixes = {
        "/posts/2026-06-15-neural-surrogates-shallow-water-equations/",
        "/posts/2014-04-28-egu2014-global-modelling-surface-internal-tides/",
        "/posts/2013-06-21-ams19-global-modelling-surface-internal-tides/",
    }
    assert len(rss_links) == 3, f"Expected exact 3 Log items in index.xml, got {len(rss_links)}: {rss_links}"
    assert not any(link.endswith("/404/") or link.endswith("/404.html") for link in rss_links), (
        "404 page leaked into index.xml"
    )
    for link in rss_links:
        assert "/posts/" in link, f"Non-Log link leaked into index.xml: {link}"
        assert not any(bad in link for bad in ("/work/", "/publications/", "/cv/")), (
            f"Non-Log page leaked into index.xml: {link}"
        )
    matched_suffixes = {
        next((s for s in expected_post_suffixes if link.endswith(s)), "")
        for link in rss_links
    }
    assert matched_suffixes == expected_post_suffixes, f"Unexpected RSS post links: {rss_links}"

    page_404 = built_site / "404.html"
    assert page_404.is_file(), "404.html must exist at site root for GitHub Pages"
    assert not (built_site / "404" / "index.html").exists(), "Legacy 404/index.html must not exist"
    soup_404 = BeautifulSoup(page_404.read_text(encoding="utf-8"), "lxml")
    robots = soup_404.find("meta", attrs={"name": "robots"})
    assert robots is not None and robots.get("content") == "noindex, nofollow"
    assert soup_404.select_one(".post-meta") is None, "404.html must not emit author .post-meta"
    assert soup_404.select_one("footer.post-footer") is None, "404.html must not emit empty .post-footer"
    home_link_404 = any(
        (a.get("href") or "").rstrip("/") in {"", "https://vlap.github.io"}
        for a in soup_404.select("main a[href]")
    )
    assert home_link_404, "404.html must provide a link back to homepage"


def test_presentations_yaml_no_urls_typo_and_renders_link(built_site: Path) -> None:
    """Verify data/presentations.yaml uses 'url' (not 'urls') and renders the ClimathNet 2014 link."""
    items = yaml.safe_load((REPO_ROOT / "data" / "presentations.yaml").read_text(encoding="utf-8"))
    assert isinstance(items, list) and len(items) >= 20
    for item in items:
        assert "urls" not in item, f"Unexpected 'urls' key in presentations.yaml: {item}"

    soup = BeautifulSoup((built_site / "cv" / "presentations" / "index.html").read_text(encoding="utf-8"), "lxml")
    link = soup.find("a", class_="cv-link", href="https://climathnet.org/meetingsandevents/conference2014/")
    assert link is not None, "Missing rendered ClimathNet 2014 link on /cv/presentations/"


def test_hugo_toml_nav_social_and_post_chrome(
    non_redirect_html_pages: list[tuple[Path, BeautifulSoup]],
) -> None:
    """Verify hugo.toml outputs, 3-item menu, 6 footer social links, and post chrome settings."""
    raw_toml = (REPO_ROOT / "hugo.toml").read_text(encoding="utf-8")
    assert len(re.findall(r"(?im)^\s*showCodeCopyButtons\s*=", raw_toml)) == 1

    cfg = tomllib.loads(raw_toml)
    assert cfg.get("taxonomies") == {
        "tag": "tags",
        "category": "categories",
        "kind": "kinds",
    }, f"Unexpected [taxonomies] in hugo.toml: {cfg.get('taxonomies')}"
    assert cfg.get("outputs", {}).get("home") == ["HTML", "RSS"], (
        f"Expected outputs.home == ['HTML', 'RSS'], got {cfg.get('outputs')}"
    )

    params = cfg.get("params", {})
    for key in ("ShowReadingTime", "ShowShareButtons", "ShowBreadCrumbs", "ShowToc"):
        assert params.get(key) is False, f"params.{key} must be False directly under [params]"
    for key in ("ShowPostNavLinks", "ShowCodeCopyButtons", "ShowScrollToTop"):
        assert params.get(key) is True, f"params.{key} must be True directly under [params]"
    assert params.get("mainSections") == ["posts"], "params.mainSections must live directly under [params]"

    minify_cfg = params.get("minify", {})
    assert set(minify_cfg.keys()) == {"disableHTML", "disableJS", "disableCSS"}, (
        f"Unexpected keys trapped under [params.minify]: {minify_cfg}"
    )

    buttons = params.get("profileMode", {}).get("buttons", [])
    assert not any(btn.get("url") in {"/tools/", "/software/"} for btn in buttons), (
        f"Obsolete button URL in hugo.toml: {buttons}"
    )

    menu_main = sorted(cfg.get("menu", {}).get("main", []), key=lambda m: m.get("weight", 0))
    assert [(m.get("name"), m.get("url")) for m in menu_main] == [
        ("Work", "/work/"),
        ("Log", "/posts/"),
        ("CV", "/cv/"),
    ], f"Expected exact 3-item menu (Work, Log, CV), got {menu_main}"
    weights = [m.get("weight") for m in menu_main]
    assert len(weights) == len(set(weights)), f"Duplicate menu.main weights: {weights}"

    social_icons = params.get("socialIcons", [])
    assert [(s.get("name"), s.get("url")) for s in social_icons] == [
        ("email", "mailto:vladimir.lapin@bsc.es"),
        ("github", "https://github.com/vlap"),
        ("linkedin", "https://linkedin.com/in/vladimir-lapin"),
        ("googlescholar", "https://scholar.google.com/citations?user=ZVQF-ggAAAAJ&hl=en"),
        ("orcid", "https://orcid.org/0000-0001-7302-8539"),
        ("rss", "/index.xml"),
    ], f"Unexpected socialIcons config: {social_icons}"

    post_pages = [
        (rel, soup)
        for rel, soup in non_redirect_html_pages
        if len(rel.parts) == 3 and rel.parts[0] == "posts" and rel.parts[2] == "index.html"
    ]
    assert len(post_pages) == 3, f"Expected 3 built post pages, got {len(post_pages)}"

    code_posts = 0
    for rel, soup in post_pages:
        assert soup.select_one("nav.breadcrumbs") is None, f"Unexpected breadcrumbs on {rel}"
        assert soup.select_one("ul.share-buttons") is None, f"Unexpected share-buttons on {rel}"
        assert soup.select_one("nav.paginav") is not None, f"Missing post nav links on {rel}"
        meta = soup.select_one(".post-meta")
        assert meta is not None and not re.search(r"\b\d+\s+min\b", meta.get_text()), (
            f"Unexpected reading time in .post-meta on {rel}"
        )
        if "2026-06-15" in rel.as_posix():
            assert soup.select_one("details.toc") is not None, f"Expected per-post ToC on {rel}"
        else:
            assert soup.select_one("details.toc") is None, f"Unexpected ToC on {rel} when ShowToc=false"
        if soup.select("pre > code"):
            code_posts += 1
            scripts = "\n".join(s.get_text() for s in soup.find_all("script"))
            assert "copy-code" in scripts, f"Missing copy-code script on post with <pre><code>: {rel}"
    assert code_posts >= 1, f"Expected >= 1 post with <pre><code>, found {code_posts}"

    for rel, soup in non_redirect_html_pages:
        assert soup.find("a", href=re.compile(r"/tools/")) is None, f"Dead /tools/ link found on {rel}"
        nav_items = [(a.get_text(strip=True), a.get("href")) for a in soup.select("#menu a")]
        assert len(nav_items) == 3, f"Expected 3 nav items on {rel}, got {nav_items}"
        assert [name for name, _ in nav_items] == ["Work", "Log", "CV"], (
            f"Unexpected nav names on {rel}: {nav_items}"
        )
        assert nav_items[0][1].endswith("/work/")
        assert nav_items[1][1].endswith("/posts/")
        assert nav_items[2][1].endswith("/cv/")

        footer_links = soup.select("footer.footer .social-icons a")
        assert len(footer_links) == 6, f"Expected 6 footer social icons on {rel}, got {len(footer_links)}"
        footer_hrefs = [a.get("href") or "" for a in footer_links]
        assert footer_hrefs[0] == "mailto:vladimir.lapin@bsc.es"
        assert "github.com/vlap" in footer_hrefs[1]
        assert "linkedin.com/in/vladimir-lapin" in footer_hrefs[2]
        assert "scholar.google.com" in footer_hrefs[3]
        assert "orcid.org" in footer_hrefs[4]
        assert footer_hrefs[5].endswith("/index.xml")
        assert all(a.get("aria-label") for a in footer_links), f"Missing aria-label on footer social link in {rel}"


def test_svg_favicons_declare_svg_mime_type(
    non_redirect_html_pages: list[tuple[Path, BeautifulSoup]],
) -> None:
    """Verify SVG favicon <link rel=icon> tags declare type=image/svg+xml instead of image/png."""
    for rel, soup in non_redirect_html_pages:
        icons = soup.select('link[rel="icon"]')
        svg_icons = [el for el in icons if "favicon.svg" in (el.get("href") or "")]
        assert svg_icons, f"Missing favicon.svg <link rel=icon> on {rel}"
        for el in svg_icons:
            assert el.get("type") != "image/png", f"Misdeclared image/png on SVG favicon in {rel}"
            if el.get("sizes"):
                assert el.get("type") == "image/svg+xml", (
                    f"Sized SVG favicon must declare image/svg+xml on {rel}, got {el.get('type')}"
                )


def test_makefile_clean_destination_dir() -> None:
    """Verify Makefile uses --cleanDestinationDir and Hugo deletes stale fingerprinted CSS bundles."""
    makefile_text = (REPO_ROOT / "Makefile").read_text(encoding="utf-8")
    for target in ("build:", "build-site:"):
        match = re.search(rf"^{re.escape(target)}[^\n]*\n(?:\t[^\n]*\n)+", makefile_text, re.MULTILINE)
        assert match is not None, f"Missing {target} target in Makefile"
        assert "--cleanDestinationDir" in match.group(0), f"Missing --cleanDestinationDir in {target}"

    out_dir = Path(tempfile.mkdtemp(prefix="_tmp_hugo_clean_", dir=REPO_ROOT))
    try:
        stale_css = out_dir / "assets" / "css" / "stylesheet.stale000.css"
        stale_css.parent.mkdir(parents=True, exist_ok=True)
        stale_css.write_text("/* stale */", encoding="utf-8")

        proc = subprocess.run(
            ["hugo", "--gc", "--minify", "--cleanDestinationDir", "-d", str(out_dir)],
            cwd=str(REPO_ROOT),
            capture_output=True,
            text=True,
            check=False,
        )
        assert proc.returncode == 0, f"Hugo clean build failed:\n{proc.stdout}\n{proc.stderr}"
        assert not stale_css.exists(), "Stale CSS file survived --cleanDestinationDir"
        bundles = list((out_dir / "assets" / "css").glob("stylesheet*.css"))
        assert len(bundles) == 1, f"Expected exactly 1 CSS bundle, got {bundles}"
    finally:
        shutil.rmtree(out_dir, ignore_errors=True)


def test_pub_list_bibtex_and_error_empty_state(built_site: Path) -> None:
    """Verify undated BibTeX omits year & trailing commas, copyBibTeX handles failures, and 0-match empty state exists."""
    pub_html = (built_site / "publications" / "index.html").read_text(encoding="utf-8")
    soup = BeautifulSoup(pub_html, "lxml")

    bib_blocks = [el.get_text() for el in soup.select(".pub-bibtex-block code")]
    assert len(bib_blocks) >= 24

    lapin_blocks = [
        b for b in bib_blocks
        if "Improved accuracy of finite difference ocean models with irregular boundaries" in b
    ]
    assert len(lapin_blocks) == 1
    assert "year =" not in lapin_blocks[0]
    assert "2026" not in lapin_blocks[0]
    assert "note = {Manuscript in preparation}" in lapin_blocks[0]

    for block in bib_blocks:
        assert re.search(r",\s*\}", block) is None, f"Trailing comma before closing brace in BibTeX:\n{block}"

    assert ".catch(" in pub_html
    assert "Copy failed" in pub_html

    copy_status = soup.select_one("#pubCopyStatus")
    assert copy_status is not None
    assert copy_status.get("role") == "status"
    assert copy_status.get("aria-live") == "polite"
    assert copy_status.find_parent("button") is None

    feed = soup.select_one(".publication-feed")
    assert feed is not None
    empty_state = feed.select_one("#pubEmptyState")
    assert empty_state is not None
    assert empty_state.has_attr("hidden")
    reset_btn = empty_state.select_one('button[type="button"]')
    assert reset_btn is not None and "clearPubFilter" in (reset_btn.get("onclick") or "")


def test_css_focus_touch_target_and_sim_polish(built_stylesheet: str) -> None:
    """Verify 44px #theme-toggle, non-bounce .sim-play-icon, and flat .sim-physics."""
    rules = _parse_css_rules(built_stylesheet)

    toggle_rules = _find_qualified_rules(rules, lambda p: p == "#theme-toggle")
    assert toggle_rules, "Missing #theme-toggle rule"
    toggle_css = ";".join(c for _, c in toggle_rules).replace(" ", "")
    assert "min-width:44px" in toggle_css
    assert "min-height:44px" in toggle_css

    play_rules = _find_qualified_rules(rules, lambda p: p == ".sim-play-icon")
    assert play_rules, "Missing .sim-play-icon rule"
    play_css = play_rules[0][1].replace(" ", "")
    assert re.search(r"cubic-bezier\(0?\.22,1,0?\.36,1\)", play_css) is not None
    assert "1.56" not in built_stylesheet

    physics_rules = _find_qualified_rules(rules, lambda p: p == ".sim-physics")
    assert physics_rules, "Missing .sim-physics rule"
    physics_css = physics_rules[0][1].replace(" ", "")
    assert "background:transparent" in physics_css or "background:00" in physics_css
    assert "border-top:1pxsolidvar(--border)" in physics_css
    assert "border-left:0" in physics_css or "border-left:none" in physics_css
    assert "border-radius:0" in physics_css
    assert "var(--tertiary)" not in physics_css

    assert _find_qualified_rules(rules, lambda p: ".pub-copy-btn.copy-failed" in p)
    assert _find_qualified_rules(rules, lambda p: ".pub-empty-state" in p)

    base_poster_idx = None
    base_play_idx = None
    reduced_motion_idx = None
    for idx, rule in enumerate(rules):
        if rule.type == "qualified-rule":
            prelude = _serialize_prelude(rule)
            content_nospace = _serialize_content(rule).replace(" ", "")
            if ".sim-facade:hover .sim-poster" in prelude and "scale(1.04)" in content_nospace:
                base_poster_idx = idx
            if ".sim-facade:hover .sim-play-icon" in prelude and "scale(1.12)" in content_nospace:
                base_play_idx = idx
        elif (
            rule.type == "at-rule"
            and rule.lower_at_keyword == "media"
            and "prefers-reduced-motion" in _serialize_prelude(rule)
            and "reduce" in _serialize_prelude(rule)
            and rule.content is not None
        ):
            nested = tinycss2.parse_rule_list(rule.content, skip_comments=True, skip_whitespace=True)
            rm_rules = _find_qualified_rules(
                nested,
                lambda p: ".sim-facade:hover .sim-play-icon" in p and ".sim-facade:hover .sim-poster" in p,
            )
            if any("transform:none" in c.replace(" ", "") for _, c in rm_rules):
                reduced_motion_idx = idx

    assert base_poster_idx is not None, "Missing base .sim-facade:hover .sim-poster rule"
    assert base_play_idx is not None, "Missing base .sim-facade:hover .sim-play-icon rule"
    assert reduced_motion_idx is not None, "Missing @media (prefers-reduced-motion: reduce) transform:none rule"
    assert reduced_motion_idx > max(base_poster_idx, base_play_idx), (
        "@media (prefers-reduced-motion: reduce) must appear AFTER base .sim-facade hover/focus rules"
    )

    light_fail = _find_qualified_rules(rules, lambda p: p == ".pub-copy-btn.copy-failed")
    dark_fail = _find_qualified_rules(
        rules,
        lambda p: "[data-theme=dark]" in p and ".pub-copy-btn.copy-failed" in p,
    )
    assert light_fail and "color:" in light_fail[0][1].replace(" ", "")
    assert dark_fail and "color:" in dark_fail[0][1].replace(" ", "")


def test_post_svgs_no_raw_latex_and_label_bounds(built_site: Path) -> None:
    """Verify post SVGs contain no raw $...$ LaTeX and neural_surrogate_swe_rollout labels stay within card bounds."""
    svg_dir = REPO_ROOT / "static" / "images" / "posts"
    svg_files = sorted(svg_dir.glob("*.svg"))
    assert len(svg_files) >= 4
    for svg_path in svg_files:
        raw = svg_path.read_text(encoding="utf-8")
        assert re.search(r"\$[^$]+\$", raw) is None, f"Raw LaTeX found in {svg_path.name}"
        ET.fromstring(raw)
        assert (built_site / "images" / "posts" / svg_path.name).is_file()

    swe_root = ET.fromstring((svg_dir / "neural_surrogate_swe_rollout.svg").read_text(encoding="utf-8"))
    ns_uri = "http://www.w3.org/2000/svg"
    labels_checked = 0
    for text_el in swe_root.iter(f"{{{ns_uri}}}text"):
        txt = (text_el.text or "").strip()
        if txt in {"FNO: Dispersion Blowup", "Flowers: Stable Rollout"}:
            labels_checked += 1
            assert text_el.get("text-anchor") == "end", f"{txt} must use text-anchor='end'"
            assert float(text_el.get("x", "999")) <= 300, f"{txt} x coordinate too large"
    assert labels_checked == 2


def test_readme_synced_with_agents_md() -> None:
    """Verify README.md documents the 3-item IA, workflows, and verification commands without obsolete claims."""
    readme = (REPO_ROOT / "README.md").read_text(encoding="utf-8")
    for required in (
        "AGENTS.md",
        "Work",
        "Log",
        "CV",
        "/work/",
        "/posts/",
        "/kinds/",
        "/publications/",
        "/cv/",
        "make sync",
        "make fetch-web-stats",
        "make build",
        "make build-site",
        "make serve",
        "make verify",
        "docs/testing-and-evaluation.md",
    ):
        assert required in readme, f"README.md missing expected reference: {required}"

    for obsolete in (
        "5 Core Pillars",
        "About (`/about/`)",
        "Software (`/software/`)",
        "Utilities (`/contact/`, `/search/`)",
        "Fuse.js",
        "for `/software/`",
        "every night at midnight",
        "Micro-post",
        "--kind micro",
        "github_activity.yaml",
        "git push origin main --force",
        "(requests, pyyaml)",
    ):
        assert obsolete not in readme, f"README.md still contains obsolete content: {obsolete}"


def test_m5_agents_memory_budget_and_gemini_pointer() -> None:
    """Verify AGENTS.md + MEMORY.md < 8,000 chars (CI-safe) and GEMINI.md is a 1-line pointer."""
    agents_text = (REPO_ROOT / "AGENTS.md").read_text(encoding="utf-8")
    assert len(agents_text) <= 4500, (
        f"AGENTS.md exceeds standalone 4500-char CI cap: {len(agents_text)} chars"
    )

    memory_path = Path.home() / ".gemini" / "antigravity-cli" / "knowledge" / "MEMORY.md"
    if memory_path.is_file():
        memory_text = memory_path.read_text(encoding="utf-8")
        total_chars = len(agents_text) + len(memory_text)
        assert total_chars < 8000, (
            f"AGENTS.md ({len(agents_text)}) + MEMORY.md ({len(memory_text)}) = {total_chars} >= 8000 chars"
        )

    gemini_text = (REPO_ROOT / "GEMINI.md").read_text(encoding="utf-8")
    lines = gemini_text.splitlines()
    assert len(lines) == 1, f"GEMINI.md must be a single line, got {len(lines)} lines"
    assert lines[0].strip() != "", "GEMINI.md single line must not be blank"
    assert "AGENTS.md" in lines[0], f"GEMINI.md must point to AGENTS.md, got: {lines[0]!r}"


def test_m5_agents_md_ia_and_core_rules() -> None:
    """Verify AGENTS.md documents the new IA and retains core workflow, voice, and safety rules."""
    agents_text = (REPO_ROOT / "AGENTS.md").read_text(encoding="utf-8")
    for required in (
        "Work",
        "Log",
        "CV",
        "/work/",
        "/posts/",
        "/kinds/",
        "/cv/",
        "/publications/",
        "git fetch origin main",
        "curated_software.yaml",
        "gitlab.earth.bsc.es",
        "make sync",
        "make build",
        "make verify",
        "git push origin main",
    ):
        assert required in agents_text, f"AGENTS.md missing required reference/rule: {required}"

    assert "buzzword" in agents_text.lower(), "AGENTS.md missing anti-buzzword editorial voice rule"

    for obsolete in (
        "5 Core Pillars",
        "About (`/about/`)",
        "Software (`/software/`)",
        "lazy-loaded iframes",
    ):
        assert obsolete not in agents_text, f"AGENTS.md still contains obsolete claim: {obsolete}"


def _hex_to_rgb(hex_str: str) -> tuple[float, float, float]:
    h = hex_str.lstrip("#")
    return tuple(int(h[i : i + 2], 16) for i in (0, 2, 4))  # type: ignore[return-value]


def _wcag_contrast(fg: tuple[float, float, float], bg: tuple[float, float, float]) -> float:
    def _lum(rgb: tuple[float, float, float]) -> float:
        ch = []
        for v in rgb:
            s = v / 255.0
            ch.append(s / 12.92 if s <= 0.04045 else ((s + 0.055) / 1.055) ** 2.4)
        return 0.2126 * ch[0] + 0.7152 * ch[1] + 0.0722 * ch[2]

    l1, l2 = _lum(fg), _lum(bg)
    return (max(l1, l2) + 0.05) / (min(l1, l2) + 0.05)


def test_heading_hierarchy_no_skipped_levels(
    non_redirect_html_pages: list[tuple[Path, BeautifulSoup]],
) -> None:
    """Verify every non-redirect HTML page has a single h1 and zero skipped heading levels."""
    checked_routes: set[str] = set()
    for rel, soup in non_redirect_html_pages:
        checked_routes.add(rel.as_posix())
        levels = [int(h.name[1]) for h in soup.find_all(["h1", "h2", "h3", "h4", "h5", "h6"])]
        assert levels, f"No headings found on {rel}"
        assert levels[0] == 1, f"First heading on {rel} must be h1, got h{levels[0]} ({levels})"
        assert levels.count(1) == 1, f"Expected exactly 1 h1 on {rel}, got {levels.count(1)} ({levels})"
        for prev, curr in zip(levels, levels[1:]):
            assert curr <= prev + 1, f"Skipped heading level h{prev} -> h{curr} on {rel}: {levels}"

    for expected in (
        "index.html",
        "work/index.html",
        "posts/index.html",
        "publications/index.html",
        "cv/index.html",
        "cv/presentations/index.html",
        "cv/trainings/index.html",
        "kinds/index.html",
        "kinds/note/index.html",
        "kinds/talk/index.html",
        "posts/2026-06-15-neural-surrogates-shallow-water-equations/index.html",
        "posts/2014-04-28-egu2014-global-modelling-surface-internal-tides/index.html",
        "posts/2013-06-21-ams19-global-modelling-surface-internal-tides/index.html",
    ):
        assert expected in checked_routes, f"Expected route missing from heading audit: {expected}"


def test_home_physical_field_graphic_and_no_emoji_bar(built_site: Path, built_stylesheet: str) -> None:
    """Verify Home renders the authentic M2 tidal physical-field SVG without legacy profile-symbol.svg or emoji bars."""
    home_raw = (built_site / "index.html").read_text(encoding="utf-8")
    assert "profile-symbol.svg" not in home_raw, "Legacy profile-symbol.svg must not be referenced in built index.html"
    home_info_src = (REPO_ROOT / "layouts" / "_partials" / "home_info.html").read_text(encoding="utf-8")
    assert "profile-symbol.svg" not in home_info_src, "Legacy profile-symbol.svg must not remain in home_info.html"

    home_soup = BeautifulSoup(home_raw, "lxml")
    assert home_soup.select_one("img.home-symbol-icon") is None, "Legacy img.home-symbol-icon must be removed"

    h1 = home_soup.select_one(".home-info h1")
    assert h1 is not None
    assert h1.select_one(".symbol-bar") is None
    h1_text = h1.get_text()
    for glyph in ("🌐", "♾", "🤖", "🌍"):
        assert glyph not in h1_text, f"Raw emoji {glyph!r} found in home <h1>"
        assert glyph not in home_info_src, f"Raw emoji {glyph!r} found in home_info.html"

    bands = home_soup.select(".home-info .tidal-field-band")
    assert len(bands) == 1, f"Expected exactly 1 .tidal-field-band inside .home-info, got {len(bands)}"
    assert bands[0].get("aria-hidden") == "true"

    svgs = home_soup.select(".home-info .tidal-field-band svg.tidal-field-svg")
    assert len(svgs) == 1, f"Expected exactly 1 svg.tidal-field-svg inside .tidal-field-band, got {len(svgs)}"
    svg_el = svgs[0]
    assert svg_el.get("aria-hidden") == "true"

    svg_root = ET.fromstring(str(svg_el))
    vb_raw = svg_root.get("viewBox") or svg_root.get("viewbox") or ""
    vb_parts = [float(p) for p in vb_raw.split()]
    assert len(vb_parts) == 4 and vb_parts[2] > 0 and vb_parts[3] > 0, (
        f"Invalid viewBox on tidal-field-svg: {vb_raw!r}"
    )

    tidal_src = (REPO_ROOT / "layouts" / "_partials" / "tidal_field.html").read_text(encoding="utf-8")
    tidal_src_root = ET.fromstring(tidal_src)
    assert tidal_src_root.get("viewBox") is not None, "tidal_field.html must declare camelCase viewBox"

    primitive_tags = {"path", "circle", "ellipse", "polyline", "polygon"}
    primitives = [
        el for el in svg_root.iter()
        if el.tag.split("}")[-1] in primitive_tags
    ]
    assert len(primitives) >= 4, f"Expected >= 4 contour primitives in tidal-field-svg, got {len(primitives)}"

    # Inspect both root <svg> and child <g>/<path>/<circle> nodes for theme-adaptive strokes/fills
    has_current_color_or_var = False
    for node in svg_root.iter():
        stroke = (node.get("stroke") or "").strip()
        fill = (node.get("fill") or "").strip()
        style = (node.get("style") or "").strip()
        if stroke == "currentColor" or "var(" in stroke or "var(" in fill or "var(" in style:
            has_current_color_or_var = True
        for attr_val in (stroke, fill):
            assert attr_val.lower() not in {"#000", "#000000", "#fff", "#ffffff"}, (
                f"Hardcoded non-adaptive color {attr_val!r} found in tidal-field-svg"
            )
    assert has_current_color_or_var, "Expected stroke='currentColor' or CSS var(...) on tidal-field-svg nodes"

    rules = _parse_css_rules(built_stylesheet)
    coamp_css = ";".join(c for _, c in _find_qualified_rules(rules, lambda p: p == ".tidal-coamplitude")).replace(" ", "")
    cotid_css = ";".join(c for _, c in _find_qualified_rules(rules, lambda p: p == ".tidal-cotidal")).replace(" ", "")
    amphi_css = ";".join(c for _, c in _find_qualified_rules(rules, lambda p: p == ".tidal-amphidromes circle")).replace(" ", "")
    assert "color:var(--accent-ocean)" in coamp_css
    assert "color:var(--accent-pine-mid)" in cotid_css
    assert "fill:var(--theme)" in amphi_css and "stroke:var(--accent-pine)" in amphi_css
    assert _find_qualified_rules(rules, lambda p: "[data-theme=dark]" in p and ".tidal-coamplitude" in p)
    assert _find_qualified_rules(rules, lambda p: "[data-theme=dark]" in p and ".tidal-cotidal" in p)


def test_cv_two_pdf_buttons_tools_and_talk_links(built_site: Path) -> None:
    """Verify /cv/ suppresses trailing post-entry cards, renders 2 PDF buttons, tools line, and talk links."""
    cv_raw = (built_site / "cv" / "index.html").read_text(encoding="utf-8")
    cv_soup = BeautifulSoup(cv_raw, "lxml")
    assert cv_soup.select("article.post-entry") == [], "Duplicate trailing post-entry cards found on /cv/"

    buttons = cv_soup.select(".cv-download-bar a.cv-download-btn")
    assert len(buttons) == 2, f"Expected 2 CV download buttons, got {len(buttons)}"
    hrefs = [btn.get("href") or "" for btn in buttons]
    assert hrefs == [
        "/downloads/vladimir-lapin-cv-research-full.pdf",
        "/downloads/vladimir-lapin-cv-industry.pdf",
    ], f"Unexpected CV button hrefs: {hrefs}"
    assert "applied-scientist" not in cv_raw, "Obsolete applied-scientist CV button found on /cv/"
    sublabels: list[str] = []
    for btn in buttons:
        href = btn.get("href") or ""
        assert (built_site / href.lstrip("/")).is_file(), f"Missing PDF asset: {href}"
        title = btn.select_one(".cv-download-title")
        sub = btn.select_one(".cv-download-sublabel")
        assert title is not None and title.get_text(strip=True)
        assert sub is not None and sub.get_text(strip=True)
        sublabels.append(sub.get_text(strip=True))
    assert len(set(sublabels)) == 2, f"CV button sublabels must be distinct: {sublabels}"

    cv_text = cv_soup.get_text(" ", strip=True)
    assert "Specialized in atmospheric and oceanic fluid dynamics" not in cv_text, (
        "Old CV intro paragraph should be removed"
    )
    assert "Tools:" in cv_text and "Models:" in cv_text and "EC-Earth4" in cv_text and "OpenIFS" in cv_text, (
        "Missing Tools & Models line on /cv/"
    )

    assert (built_site / "cv" / "presentations" / "index.html").is_file()
    assert (built_site / "cv" / "trainings" / "index.html").is_file()

    # Verify legacy PhD/MSc thesis PDFs are copied, built, and linked from Education
    for pdf_name in ("phd-thesis-vlapin.pdf", "msc-thesis-vlapin.pdf"):
        assert (built_site / "downloads" / pdf_name).is_file(), f"Missing built thesis PDF: {pdf_name}"
        assert cv_soup.find("a", href=f"/downloads/{pdf_name}") is not None, (
            f"Missing /downloads/{pdf_name} link on /cv/"
        )

    # Verify /cv/ collapses Trainings & Presentations inside details.cv-section-details while keeping standalone pages open
    cv_details = cv_soup.select("details.cv-section-details")
    assert len(cv_details) == 2, f"Expected 2 details.cv-section-details on /cv/, got {len(cv_details)}"
    assert all(not d.has_attr("open") for d in cv_details), "CV details disclosures should start collapsed"

    trainings_soup = BeautifulSoup((built_site / "cv" / "trainings" / "index.html").read_text(encoding="utf-8"), "lxml")
    assert trainings_soup.select("details.cv-section-details") == []
    assert len(trainings_soup.select(".cv-item")) == 28

    pres_soup = BeautifulSoup((built_site / "cv" / "presentations" / "index.html").read_text(encoding="utf-8"), "lxml")
    assert pres_soup.select("details.cv-section-details") == []
    assert len(pres_soup.select(".cv-item")) == 21

    # Verify EGU2014 (2014) and AMS 19th (2013) link to their Log talk pages on both /cv/ and /cv/presentations/
    for target_name, target_soup in (("cv", cv_soup), ("cv/presentations", pres_soup)):
        for event_name, expected_slug in (
            ("EGU2014", "/posts/2014-04-28-egu2014-global-modelling-surface-internal-tides/"),
            ("19th Conference on Atmospheric and Oceanic Fluid Dynamics of the AMS", "/posts/2013-06-21-ams19-global-modelling-surface-internal-tides/"),
        ):
            matching_items = [
                item for item in target_soup.select(".cv-item")
                if event_name in item.get_text(" ", strip=True)
            ]
            assert len(matching_items) == 1, f"Expected 1 {event_name} item on {target_name}, got {len(matching_items)}"
            talk_link = matching_items[0].find("a", href=re.compile(re.escape(expected_slug)))
            assert talk_link is not None, f"Missing Log talk link {expected_slug} on {event_name} in {target_name}"

    # Verify compact timeline styling for institution/bullet-less entries (Career Break)
    assert len(cv_soup.select(".cv-entry-compact")) == 1

    # Verify static portfolio pages omit blog date/reading-time .post-meta
    for rel in (
        "work/index.html",
        "publications/index.html",
        "cv/index.html",
    ):
        page_soup = BeautifulSoup((built_site / rel).read_text(encoding="utf-8"), "lxml")
        assert page_soup.select_one(".post-meta") is None, f"Unexpected .post-meta on static page {rel}"


def test_css_contrast_tokens_and_modern_polish(
    built_stylesheet: str,
    non_redirect_html_pages: list[tuple[Path, BeautifulSoup]],
) -> None:
    """Verify contrast tokens, zero remote font CDNs, overflow rules, and modern CSS polish."""
    rules = _parse_css_rules(built_stylesheet)
    assert not any(r.type == "error" for r in rules), "Built CSS contains parse errors"

    root_combined = ";".join(c for _, c in _find_qualified_rules(rules, lambda p: p == ":root"))
    lead_match = re.search(r"--badge-lead-text-light:\s*(#[0-9a-fA-F]{6})", root_combined)
    assert lead_match is not None, "Missing --badge-lead-text-light token"
    lead_fg = _hex_to_rgb(lead_match.group(1))
    # --badge-lead-bg-light: rgba(0, 153, 76, 0.1) composited over #ffffff -> (230, 245, 237)
    lead_bg = (0.1 * 0 + 0.9 * 255, 0.1 * 153 + 0.9 * 255, 0.1 * 76 + 0.9 * 255)
    assert _wcag_contrast(lead_fg, lead_bg) >= 4.5

    for token in ("--pub-highlight-bg", "--pub-highlight-text"):
        assert f"{token}:" in root_combined, f"Missing fallback {token} on :root"

    supports_blocks = [
        r for r in rules
        if r.type == "at-rule" and r.lower_at_keyword == "supports"
        and "light-dark" in _serialize_prelude(r)
        and not _serialize_prelude(r).lstrip().startswith("not")
    ]
    assert supports_blocks
    supports_text = _serialize_content(supports_blocks[0])
    assert "--pub-highlight-bg" in supports_text and "--pub-highlight-text" in supports_text

    hl_rules = _find_qualified_rules(rules, lambda p: "::highlight(pub-search-match)" in p)
    assert hl_rules, "Missing ::highlight(pub-search-match) rule"
    hl_css = hl_rules[0][1].replace(" ", "")
    assert "background-color:var(--pub-highlight-bg)" in hl_css
    assert "color:var(--pub-highlight-text)" in hl_css
    assert "text-decoration:underline" in hl_css

    chroma_rules = _find_qualified_rules(rules, lambda p: ".chroma .c" in p and ".chroma .c1" in p)
    assert chroma_rules, "Missing .chroma comment contrast override"
    chroma_color_match = re.search(r"color:\s*(#[0-9a-fA-F]{6})", chroma_rules[-1][1])
    assert chroma_color_match is not None
    chroma_fg = _hex_to_rgb(chroma_color_match.group(1))
    assert _wcag_contrast(chroma_fg, (28, 29, 33)) >= 4.5
    assert _wcag_contrast(chroma_fg, (46, 46, 51)) >= 4.5

    for sel in (
        ".post-tag",
        ".software-tag",
        ".sim-spec-pill",
        ".sim-physics",
        ".cv-nav-link",
        ".cv-date-badge",
        ".cv-skills-tag",
        ".pub-year-pill",
        ".pub-bibtex-summary",
        ".pub-copy-btn",
    ):
        matched = _find_qualified_rules(rules, lambda p, s=sel: p == s)
        assert matched, f"Missing rule for {sel}"
        combined_sel_css = ";".join(c for _, c in matched).replace(" ", "")
        assert "color:var(--secondary)" not in combined_sel_css, f"{sel} still uses low-contrast --secondary"

    post_tags_rules = _find_qualified_rules(rules, lambda p: ".post-tags a" in p)
    assert any("color:var(--primary)" in c.replace(" ", "") for _, c in post_tags_rules)

    # Typography & zero third-party webfont CDN requests (exempting pinned KaTeX CSS on math pages)
    assert "system-ui" in root_combined and "--font-sans:" in root_combined
    assert "ui-monospace" in root_combined and "--font-mono:" in root_combined
    for cdn in ("fonts.googleapis.com", "fonts.gstatic.com", "use.typekit.net"):
        assert cdn not in built_stylesheet, f"Unexpected external font CDN {cdn} in stylesheet"
    assert not re.search(r"@font-face\s*\{[^}]*https?://", built_stylesheet, re.IGNORECASE), (
        "Unexpected remote @font-face font URL in stylesheet"
    )
    for rel, soup in non_redirect_html_pages:
        for link_tag in soup.find_all("link", href=True):
            href = link_tag["href"]
            if href.startswith(("http://", "https://")):
                if rel.as_posix() in KATEX_PAGES and href.startswith("https://cdn.jsdelivr.net/npm/katex@0.16.11/"):
                    continue
                if "stylesheet" in (link_tag.get("rel") or []):
                    pytest.fail(f"Unexpected external stylesheet {href!r} on {rel}")
    assert "max-width:68ch" not in built_stylesheet.replace(" ", ""), "Remove lopsided 68ch cap inside 720px column"

    main_rules = _find_qualified_rules(rules, lambda p: p == ".main")
    assert main_rules, "Missing .main containment rule"
    main_css = ";".join(c for _, c in main_rules).replace(" ", "")
    assert "min-width:0" in main_css
    assert "width:100%" in main_css or "box-sizing:border-box" in main_css
    assert "max-width:100%" not in main_css, ".main must keep PaperMod centered max-width"

    overflow_container_rules = _find_qualified_rules(
        rules,
        lambda p: ".post-single" in p and ".post-content" in p and ".main" not in p,
    )
    assert overflow_container_rules, "Missing .post-single, .post-content overflow containment rule"
    oc_css = ";".join(c for _, c in overflow_container_rules).replace(" ", "")
    assert "min-width:0" in oc_css
    assert "max-width:100%" in oc_css
    assert "overflow-wrap:break-word" in oc_css

    timeline_rules = _find_qualified_rules(rules, lambda p: p == ".cv-timeline")
    assert timeline_rules
    timeline_css = ";".join(c for _, c in timeline_rules).replace(" ", "")
    assert any(
        tok in timeline_css
        for tok in (
            "border-left:1pxsolidvar(--tertiary)",
            "border-left:1pxsolidvar(--border)",
            "border-left:1pxsolidvar(--hairline)",
        )
    ), f"Missing hairline border-left on .cv-timeline: {timeline_css}"

    assert _find_qualified_rules(rules, lambda p: p == ".cv-entry-compact")
    pill_reset_rules = _find_qualified_rules(
        rules,
        lambda p: ".post-content a.pub-year-pill" in p and ".post-content a.pub-badge-btn" in p,
    )
    assert pill_reset_rules
    assert "box-shadow:none" in pill_reset_rules[0][1].replace(" ", "")

    table_rules = _find_qualified_rules(rules, lambda p: p == ".post-content table")
    assert table_rules
    table_css = ";".join(c for _, c in table_rules).replace(" ", "")
    assert "position:relative" in table_css
    assert "display:block" in table_css
    assert "max-width:100%" in table_css
    assert "overflow-x:auto" in table_css

    katex_rules = _find_qualified_rules(rules, lambda p: p == ".katex-display")
    assert katex_rules
    katex_css = ";".join(c for _, c in katex_rules).replace(" ", "")
    assert "position:relative" in katex_css
    assert "overflow-x:auto" in katex_css

    # Idea 3B: @view-transition + scroll progress gated in prefers-reduced-motion: no-preference
    no_pref_blocks = [
        r for r in rules
        if r.type == "at-rule"
        and r.lower_at_keyword == "media"
        and "prefers-reduced-motion" in _serialize_prelude(r)
        and "no-preference" in _serialize_prelude(r)
    ]
    assert no_pref_blocks, "Missing @media (prefers-reduced-motion: no-preference) block"
    no_pref_nested = tinycss2.parse_rule_list(no_pref_blocks[0].content, skip_comments=True, skip_whitespace=True)

    vt_blocks = [r for r in no_pref_nested if r.type == "at-rule" and r.lower_at_keyword == "view-transition"]
    assert vt_blocks and "navigation:auto" in _serialize_content(vt_blocks[0]).replace(" ", "")

    scroll_supports = [
        r for r in no_pref_nested
        if r.type == "at-rule" and r.lower_at_keyword == "supports"
        and "animation-timeline" in _serialize_prelude(r)
    ]
    assert scroll_supports, "Missing @supports (animation-timeline: scroll()) inside no-preference"
    scroll_nested = tinycss2.parse_rule_list(scroll_supports[0].content, skip_comments=True, skip_whitespace=True)
    progress_rules = _find_qualified_rules(scroll_nested, lambda p: ".post-single::before" in p)
    assert progress_rules
    progress_css = progress_rules[0][1].replace(" ", "")
    assert "animation:" in progress_css and "animation-timeline:scroll(rootblock)" in progress_css
    assert progress_css.index("animation:") < progress_css.index("animation-timeline:")

    balance_rules = _find_qualified_rules(rules, lambda p: "h1" in p and ".post-title" in p and ".pub-card-title" in p)
    assert any("text-wrap:balance" in c.replace(" ", "") for _, c in balance_rules)

    pretty_rules = _find_qualified_rules(rules, lambda p: ".post-content p" in p and ".pub-card-authors" in p)
    assert any("text-wrap:pretty" in c.replace(" ", "") for _, c in pretty_rules)

    sw_grid_rules = _find_qualified_rules(rules, lambda p: p == ".software-container")
    assert sw_grid_rules and any(
        "min(100%," in c.replace(" ", "") or "min-width:0" in c.replace(" ", "")
        for _, c in sw_grid_rules
    ), f"Expected responsive .software-container track or min-width:0, got {sw_grid_rules}"

    sim_grid_rules = _find_qualified_rules(rules, lambda p: p == ".simulation-gallery")
    assert sim_grid_rules and any(
        "minmax(min(100%,350px),1fr)" in c.replace(" ", "") or "min(100%," in c.replace(" ", "")
        for _, c in sim_grid_rules
    ), f"Expected .simulation-gallery responsive min(100%, ...) grid track, got {sim_grid_rules}"

    empty_msg_rules = _find_qualified_rules(rules, lambda p: p == ".pub-empty-message")
    assert empty_msg_rules and any(
        "margin-inline:auto" in c.replace(" ", "") for _, c in empty_msg_rules
    ), f"Expected margin-inline: auto on .pub-empty-message, got {empty_msg_rules}"


def test_pub_list_highlights_url_sync_and_shortcuts_markup(built_site: Path) -> None:
    """Verify /publications/ script includes CSS.highlights, TreeWalker, ?q= sync, and / + Escape shortcuts."""
    pub_html = (built_site / "publications" / "index.html").read_text(encoding="utf-8")
    for token in (
        "CSS.highlights",
        "Highlight",
        "createTreeWalker",
        "NodeFilter.SHOW_TEXT",
        "pub-search-match",
        "replaceState",
        "URLSearchParams",
        "Escape",
    ):
        assert token in pub_html, f"Missing {token!r} in built publications page"

    pub_src = (REPO_ROOT / "layouts" / "shortcodes" / "pub_list.html").read_text(encoding="utf-8")
    assert "innerHTML" not in pub_src
    assert re.search(r"e\.key\s*===\s*['\"]Escape['\"].*?e\.isComposing", pub_src, re.DOTALL), (
        "Escape keydown handler in pub_list.html must guard e.isComposing"
    )


def _parse_front_matter(md_path: Path) -> tuple[dict, str]:
    raw = md_path.read_text(encoding="utf-8")
    parts = raw.split("---", 2)
    assert len(parts) == 3, f"Expected YAML front matter in {md_path}"
    return yaml.safe_load(parts[1]) or {}, parts[2]


def test_step2_drafts_kinds_and_backfilled_talks(built_site: Path) -> None:
    """Verify drafted posts are excluded, kinds taxonomy works, and backfilled talks are valid."""
    posts_dir = REPO_ROOT / "content" / "posts"
    drafted_slugs = [
        "2026-05-04-senior-dev-hpc-workflows",
        "2026-07-20-scaling-python-hpc-uv-lustre",
        "2026-09-22-pragmatic-scientist-audit-climate-workflows",
        "2026-09-24-openifs-mass-conservation-stochastic-rounding",
    ]
    forbidden_slugs = [*drafted_slugs, "senior-dev-hpc-workflows"]

    for slug in drafted_slugs:
        md_path = posts_dir / f"{slug}.md"
        assert md_path.is_file(), f"Drafted post file must remain on disk: {md_path}"
        fm, _ = _parse_front_matter(md_path)
        assert fm.get("draft") is True, f"Expected draft: true in {md_path.name}"
        assert not (built_site / "posts" / slug).exists(), f"Drafted post leaked to public/posts/{slug}"

    assert not (built_site / "posts" / "senior-dev-hpc-workflows").exists(), (
        "Alias /posts/senior-dev-hpc-workflows/ leaked from drafted post"
    )

    for rel in (
        "posts/index.html",
        "archives/index.html",
        "kinds/index.html",
        "kinds/note/index.html",
        "kinds/talk/index.html",
        "index.xml",
        "sitemap.xml",
    ):
        built_file = built_site / rel
        assert built_file.is_file(), f"Missing expected built file: {rel}"
        content = built_file.read_text(encoding="utf-8")
        for slug in forbidden_slugs:
            assert slug not in content, f"Drafted slug {slug!r} leaked into {rel}"

    forbidden_paths = [*forbidden_slugs, "/search/", "/search"]
    for html_path in built_site.rglob("*.html"):
        rel_html = html_path.relative_to(built_site)
        soup = BeautifulSoup(html_path.read_text(encoding="utf-8"), "lxml")
        for a in soup.find_all("a", href=True):
            href = a["href"]
            is_internal = (href.startswith("/") and not href.startswith("//")) or href.startswith("https://vlap.github.io/")
            if is_internal:
                for slug in forbidden_slugs:
                    assert slug not in href, f"Internal link {href!r} in {rel_html} points to drafted post"
                assert "/search/" not in href and not href.endswith("/search"), (
                    f"Internal link {href!r} in {rel_html} points to removed /search/"
                )

    for xml_rel in ("sitemap.xml", "index.xml"):
        xml_text = (built_site / xml_rel).read_text(encoding="utf-8")
        for slug in forbidden_slugs:
            assert slug not in xml_text, f"Drafted slug {slug!r} leaked into {xml_rel}"
        assert "/search/" not in xml_text, f"/search/ leaked into {xml_rel}"

    kept_slug = "2026-06-15-neural-surrogates-shallow-water-equations"
    kept_fm, _ = _parse_front_matter(posts_dir / f"{kept_slug}.md")
    assert kept_fm.get("draft") is False
    assert kept_fm.get("kinds") == ["note"], f"Expected kinds: ['note'] on {kept_slug}, got {kept_fm.get('kinds')}"
    assert (built_site / "posts" / kept_slug / "index.html").is_file()
    note_html = (built_site / "kinds" / "note" / "index.html").read_text(encoding="utf-8")
    assert kept_slug in note_html, f"{kept_slug} missing from /kinds/note/"

    slides_dir = REPO_ROOT / "static" / "slides"
    assert not slides_dir.exists() or not any(slides_dir.iterdir()), (
        "Backfilled talks must use external URLs only, nothing in static/slides/"
    )

    presentations = yaml.safe_load((REPO_ROOT / "data" / "presentations.yaml").read_text(encoding="utf-8"))
    pres_pairs = {(p.get("event"), p.get("year")) for p in presentations}

    talk_specs = [
        ("2014-04-28-egu2014-global-modelling-surface-internal-tides", "EGU2014", 2014),
        (
            "2013-06-21-ams19-global-modelling-surface-internal-tides",
            "19th Conference on Atmospheric and Oceanic Fluid Dynamics of the AMS",
            2013,
        ),
    ]
    talk_index_html = (built_site / "kinds" / "talk" / "index.html").read_text(encoding="utf-8")
    for slug, expected_event, expected_year in talk_specs:
        md_path = posts_dir / f"{slug}.md"
        assert md_path.is_file(), f"Missing backfilled talk file: {md_path}"
        fm, body = _parse_front_matter(md_path)
        assert fm.get("draft") is False, f"Expected draft: false in {md_path.name}"
        assert fm.get("kinds") == ["talk"], f"Expected kinds: ['talk'] in {md_path.name}"
        assert fm.get("event") == expected_event
        assert fm.get("year") == expected_year
        assert (fm.get("event"), fm.get("year")) in pres_pairs, (
            f"Talk {(fm.get('event'), fm.get('year'))} missing from data/presentations.yaml"
        )
        assert "\n> " in body or body.lstrip().startswith("> "), f"Expected quoted abstract in {md_path.name}"
        assert "From the official" in body, f"Expected abstract attribution in {md_path.name}"

        assert slug in talk_index_html, f"{slug} missing from /kinds/talk/"
        built_talk = built_site / "posts" / slug / "index.html"
        assert built_talk.is_file(), f"Missing built talk page: {built_talk}"
        talk_soup = BeautifulSoup(built_talk.read_text(encoding="utf-8"), "lxml")
        assert talk_soup.select_one(".post-content blockquote") is not None, (
            f"Missing rendered <blockquote> abstract on {slug}"
        )
        ext_links = [
            a["href"] for a in talk_soup.select(".post-content a[href]") if a["href"].startswith("https://")
        ]
        assert ext_links, f"Expected external HTTPS link(s) in {slug}"
        assert not any(
            "/slides/" in (a.get("href") or "") for a in talk_soup.select(".post-content a[href]")
        ), f"Unexpected local /slides/ link in {slug}"


def _extract_meta_refresh_target(html_text: str) -> str | None:
    soup = BeautifulSoup(html_text, "lxml")
    meta = soup.find("meta", attrs={"http-equiv": re.compile(r"^refresh$", re.I)})
    if meta is None:
        return None
    content = meta.get("content") or ""
    match = re.search(r"url=(.+)$", content, re.I)
    return match.group(1).strip() if match else None


def test_m3_redirects_and_removed_pages(built_site: Path) -> None:
    """Verify removed pages redirect cleanly via Hugo aliases and /search/ + index.json are absent."""
    expected_redirects = {
        "about/index.html": ("https://vlap.github.io/", "/"),
        "contact/index.html": ("https://vlap.github.io/", "/"),
        "software/index.html": ("https://vlap.github.io/work/", "/work/"),
        "archives/index.html": ("https://vlap.github.io/posts/", "/posts/"),
    }
    for rel, targets in expected_redirects.items():
        html_path = built_site / rel
        assert html_path.is_file(), f"Missing redirect file: {rel}"
        raw = html_path.read_text(encoding="utf-8")
        assert _is_meta_refresh_redirect(raw), f"Expected meta-refresh redirect in {rel}, got non-redirect page"
        target = _extract_meta_refresh_target(raw)
        assert target in targets, f"Redirect {rel} points to {target!r}, expected one of {targets}"

    assert not (built_site / "search").exists(), "/search/ directory must not exist in public/"
    assert not (built_site / "index.json").exists(), "index.json must not exist in public/"


def test_m3_bio_appears_once_on_home(built_site: Path) -> None:
    """Verify profile.yaml bio appears exactly once in public/, inside public/index.html."""
    profile = yaml.safe_load((REPO_ROOT / "data" / "profile.yaml").read_text(encoding="utf-8"))
    bio_norm = " ".join((profile.get("bio") or "").split())
    assert len(bio_norm) > 40, "profile.yaml bio missing or unexpectedly short"

    home_raw = (built_site / "index.html").read_text(encoding="utf-8")
    home_soup = BeautifulSoup(home_raw, "lxml")
    home_text = " ".join(home_soup.get_text(" ").split())
    assert bio_norm in home_text, "profile.yaml bio missing from public/index.html"
    assert home_text.count(bio_norm) == 1, "profile.yaml bio appears multiple times on public/index.html"

    for html_path in built_site.rglob("*.html"):
        rel = html_path.relative_to(built_site).as_posix()
        if rel == "index.html":
            continue
        other_text = " ".join(BeautifulSoup(html_path.read_text(encoding="utf-8"), "lxml").get_text(" ").split())
        assert bio_norm not in other_text, f"Bio leaked into {rel}"
        assert "Climate models have become too expensive to improve" not in other_text, (
            f"Bio prose leaked into {rel}"
        )


def test_m3_home_audience_links_and_log_threshold(built_site: Path) -> None:
    """Verify Home audience links, removed dashboard blocks, and >=2 vs <2 Log threshold."""
    home_soup = BeautifulSoup((built_site / "index.html").read_text(encoding="utf-8"), "lxml")
    assert home_soup.select_one(".impact-metrics") is None, "Obsolete .impact-metrics still on Home"
    assert home_soup.select_one(".research-highlights") is None, "Obsolete .research-highlights still on Home"
    assert home_soup.select_one(".home-info .social-icons") is None, "Duplicate social icons still inside .home-info"

    audience_links = home_soup.select(".home-audience-links a")
    assert len(audience_links) == 3, f"Expected 3 audience links on Home, got {len(audience_links)}"
    actual_cta = [(a.select_one(".home-audience-title").get_text(strip=True), a.get("href")) for a in audience_links]
    assert actual_cta[0][0] == "Collaborate" and actual_cta[0][1].endswith("/work/")
    assert actual_cta[1][0] == "Hiring" and actual_cta[1][1].endswith("/cv/")
    assert actual_cta[2][0] == "Read" and actual_cta[2][1].endswith("/posts/")

    # With 3 published Log items (>= 2), "Latest from the Log" must render up to 3 monograph rows with kind badges and ISO dates
    home_posts = home_soup.select_one(".home-posts")
    assert home_posts is not None, "Expected .home-posts on Home when >= 2 Log items are published"
    heading = home_posts.select_one("h2")
    assert heading is not None and heading.get_text(strip=True) == "Latest from the Log"
    rows = home_posts.select(".log-rows .log-row")
    assert 2 <= len(rows) <= 3, f"Expected 2..3 monograph rows in Latest from the Log, got {len(rows)}"
    for row in rows:
        badges = row.select(".kind-badge")
        assert badges, "Expected kind badge on Home Log row"
        assert all(b.get_text(strip=True) in {"note", "talk", "paper"} for b in badges)
        title_link = row.select_one("a.log-row-title-link")
        assert title_link is not None and (title_link.get("href") or "").strip(), "Expected a.log-row-title-link on Home Log row"
        date_el = row.select_one("time.log-row-date")
        assert date_el is not None and re.match(r"^\d{4}-\d{2}-\d{2}$", date_el.get_text(strip=True)), (
            "Expected ISO date in time.log-row-date on Home Log row"
        )

    # Probe < 2 published Log items using snap-safe temporary directories under REPO_ROOT
    probe_src = Path(tempfile.mkdtemp(prefix="_tmp_hugo_probe_src_", dir=REPO_ROOT))
    probe_out = Path(tempfile.mkdtemp(prefix="_tmp_hugo_probe_out_", dir=REPO_ROOT))
    try:
        shutil.copytree(REPO_ROOT / "content", probe_src / "content", dirs_exist_ok=True)
        for talk_name in (
            "2014-04-28-egu2014-global-modelling-surface-internal-tides.md",
            "2013-06-21-ams19-global-modelling-surface-internal-tides.md",
        ):
            talk_path = probe_src / "content" / "posts" / talk_name
            raw = talk_path.read_text(encoding="utf-8")
            talk_path.write_text(raw.replace("draft: false", "draft: true", 1), encoding="utf-8")

        proc = subprocess.run(
            ["hugo", "--gc", "--minify", "--contentDir", str(probe_src / "content"), "-d", str(probe_out)],
            cwd=str(REPO_ROOT),
            capture_output=True,
            text=True,
            check=False,
        )
        assert proc.returncode == 0, f"Probe Hugo build (<2 posts) failed:\n{proc.stdout}\n{proc.stderr}"
        probe_home = BeautifulSoup((probe_out / "index.html").read_text(encoding="utf-8"), "lxml")
        assert probe_home.select_one(".home-posts") is None, (
            "Home must NOT render .home-posts when < 2 Log items are published"
        )
        assert "Latest from the Log" not in probe_home.get_text()
    finally:
        shutil.rmtree(probe_src, ignore_errors=True)
        shutil.rmtree(probe_out, ignore_errors=True)


def test_m3_work_page_structure(built_site: Path) -> None:
    """Verify /work/ has intro, projects, 7 software cards (no equations), 5 latest pubs, and simulations at bottom."""
    work_raw = (built_site / "work" / "index.html").read_text(encoding="utf-8")
    work_soup = BeautifulSoup(work_raw, "lxml")
    content = work_soup.select_one(".post-content")
    assert content is not None

    work_text = content.get_text(" ", strip=True)
    assert "Projects I am on now" in work_text
    assert "Current Projects" in work_text
    assert len(content.select(".software-card")) == 7
    assert "$$" not in work_raw and "\\frac" not in work_raw, "Equations must not appear on /work/"

    pub_items = content.select(".selected-pub-item")
    assert len(pub_items) == 5, f"Expected 5 selected publications on /work/, got {len(pub_items)}"
    pubs_link = content.find("a", href=re.compile(r"/publications/?$"))
    assert pubs_link is not None, "Missing link to /publications/ on /work/"

    # Verify latest 5 dated entries from data/publications.yaml appear in order
    expected_titles = [
        "Multi-model reconstructions and predictions of the CO2 fluxes and atmospheric CO2 variations",
        "Dissecting mesopelagic particulate organic carbon budgets in the North Atlantic",
        "Convection injects labile particulate organic carbon to the deep ocean",
        "The key role of Mediterranean and North Atlantic sea surface temperatures",
        "Comparing the seasonal predictability of the Tropical Pacific variability",
    ]
    rendered_titles = [el.get_text(" ", strip=True) for el in content.select(".selected-pub-item h3")]
    for exp, got in zip(expected_titles, rendered_titles):
        assert exp in got, f"Expected selected pub {exp!r}, got {got!r}"

    # Simulation gallery must appear AFTER Selected Publications
    pos_pubs = work_raw.find("selected-pub-list")
    pos_sim = work_raw.find("simulation-gallery")
    assert pos_pubs != -1 and pos_sim != -1 and pos_sim > pos_pubs, (
        "simulation_gallery must appear after selected publications on /work/"
    )


def test_m3_publications_metrics_intro(built_site: Path) -> None:
    """Verify /publications/ intro line displays paper count, citations, and h-index from data/*.yaml."""
    stats = yaml.safe_load((REPO_ROOT / "data" / "stats.yaml").read_text(encoding="utf-8"))
    scholar = yaml.safe_load((REPO_ROOT / "data" / "scholar_stats.yaml").read_text(encoding="utf-8"))
    pub_soup = BeautifulSoup((built_site / "publications" / "index.html").read_text(encoding="utf-8"), "lxml")
    intro = pub_soup.select_one(".pub-metrics-intro")
    assert intro is not None, "Missing .pub-metrics-intro on /publications/"
    intro_text = re.sub(r"\s+", " ", intro.get_text()).strip()

    expected = f"{stats['publications']} papers · {scholar['citations']} citations · h-index {scholar['h_index']} (OpenAlex)."
    assert intro_text == expected, f"Expected {expected!r} in .pub-metrics-intro, got: {intro_text!r}"


def test_m3_log_kind_filters_badges_and_linkedin_probe(built_site: Path) -> None:
    """Verify /posts/ Log heading, kind filter pills, kind badges, and optional linkedin: front matter."""
    log_soup = BeautifulSoup((built_site / "posts" / "index.html").read_text(encoding="utf-8"), "lxml")
    h1 = log_soup.select_one("header.page-header h1")
    assert h1 is not None and h1.get_text(strip=True) == "Log"

    filter_links = log_soup.select(".log-kind-filter a")
    assert len(filter_links) >= 3, f"Expected kind filter links on /posts/, got {filter_links}"
    filter_hrefs = [a.get("href") or "" for a in filter_links]
    assert any(h.endswith("/posts/") for h in filter_hrefs)
    assert any(h.endswith("/kinds/note/") for h in filter_hrefs)
    assert any(h.endswith("/kinds/talk/") for h in filter_hrefs)

    entries = log_soup.select(".log-rows .log-row")
    assert len(entries) == 3, f"Expected 3 published Log entries on /posts/, got {len(entries)}"
    for entry in entries:
        assert entry.select(".kind-badge"), "Expected .kind-badge on Log list entry"
        title_link = entry.select_one("a.log-row-title-link")
        assert title_link is not None and (title_link.get("href") or "").strip(), (
            "Expected a.log-row-title-link on Log list entry"
        )
        date_el = entry.select_one("time.log-row-date")
        assert date_el is not None and re.match(r"^\d{4}-\d{2}-\d{2}$", date_el.get_text(strip=True)), (
            "Expected ISO date in time.log-row-date on Log list entry"
        )

    # Single post without linkedin: must not render .post-linkedin-link, and must show .kind-badge
    note_soup = BeautifulSoup(
        (built_site / "posts" / "2026-06-15-neural-surrogates-shallow-water-equations" / "index.html").read_text(encoding="utf-8"),
        "lxml",
    )
    assert note_soup.select_one(".post-header .kind-badge") is not None
    assert note_soup.select_one(".post-linkedin-link") is None

    # Probe optional linkedin: front-matter key in an isolated temporary contentDir
    probe_src = Path(tempfile.mkdtemp(prefix="_tmp_hugo_probe_src_", dir=REPO_ROOT))
    probe_out = Path(tempfile.mkdtemp(prefix="_tmp_hugo_probe_out_", dir=REPO_ROOT))
    try:
        shutil.copytree(REPO_ROOT / "content", probe_src / "content", dirs_exist_ok=True)
        talk_path = probe_src / "content" / "posts" / "2014-04-28-egu2014-global-modelling-surface-internal-tides.md"
        raw = talk_path.read_text(encoding="utf-8")
        talk_path.write_text(
            raw.replace('year: 2014\n', 'year: 2014\nlinkedin: "https://www.linkedin.com/posts/example-talk"\n', 1),
            encoding="utf-8",
        )

        proc = subprocess.run(
            ["hugo", "--gc", "--minify", "--contentDir", str(probe_src / "content"), "-d", str(probe_out)],
            cwd=str(REPO_ROOT),
            capture_output=True,
            text=True,
            check=False,
        )
        assert proc.returncode == 0, f"Probe Hugo build (linkedin) failed:\n{proc.stdout}\n{proc.stderr}"
        talk_probe_soup = BeautifulSoup(
            (probe_out / "posts" / "2014-04-28-egu2014-global-modelling-surface-internal-tides" / "index.html").read_text(encoding="utf-8"),
            "lxml",
        )
        li_link = talk_probe_soup.select_one('.post-linkedin-link a[href="https://www.linkedin.com/posts/example-talk"]')
        assert li_link is not None, "Expected .post-linkedin-link when linkedin: front-matter is set"

        note_probe_soup = BeautifulSoup(
            (probe_out / "posts" / "2026-06-15-neural-surrogates-shallow-water-equations" / "index.html").read_text(encoding="utf-8"),
            "lxml",
        )
        assert note_probe_soup.select_one(".post-linkedin-link") is None
    finally:
        shutil.rmtree(probe_src, ignore_errors=True)
        shutil.rmtree(probe_out, ignore_errors=True)


def test_m4_section6_verbatim_prose(
    built_site: Path,
    non_redirect_html_pages: list[tuple[Path, BeautifulSoup]],
) -> None:
    """Verify all 10 Spec Section 6 prose items verbatim across config, data, and built HTML."""
    expected_tagline = "Senior Research Engineer, BSC · Climate models, HPC, ML emulators"
    expected_bio = (
        "I am a Senior Research Engineer at the Barcelona Supercomputing Center. I work on the "
        "EC-Earth4 climate model: coupling, performance on MareNostrum 5, and the ensemble "
        "workflows behind our decadal predictions for CMIP7. Before BSC, I wrote sea-ice and "
        "ocean-tide solvers at MPI-M and the University of Leeds. Climate models have become "
        "too expensive to improve, and I think AI tools and automated verification can make "
        "that work affordable again."
    )
    expected_focus = (
        "Preparing EC-Earth4 for CMIP7 on MareNostrum 5, tracer mass conservation in OpenIFS, "
        "and coupling neural emulators to EC-Earth4."
    )
    expected_home_links = [
        ("Collaborate", "/work/", "what I work on, the code, and how to reach me."),
        ("Hiring", "/cv/", "CV, career history and PDF downloads."),
        ("Read", "/posts/", "notes, talks and papers."),
    ]
    expected_work_intro = (
        "Projects I am on now, the public code, and some older simulations. "
        "If something here overlaps with your work, email me."
    )
    expected_work_projects = [
        "Auto-EC-Earth4 — I co-lead the Autosubmit workflow for 50–100 member decadal ensembles (CMIP7, WMO/DCPP).",
        "EC-Earth4 performance — single precision, load balancing and MPI tuning; coupled runs are 2–3× faster.",
        "Emulators in EC-Earth4 — interfaces to couple neural emulators, and a GNN ocean biogeochemistry emulator with mass-conservation checks.",
        "OpenIFS tracer mass conservation in CY48R1.1.",
    ]
    expected_software = [
        (
            "Climate Commons (cvc-commons)",
            "Shared workflow tasks and preprocessing scripts for climate computing at BSC, with schema checks and CI.",
        ),
        (
            "EC-Earth4",
            "The European community Earth system model. I work on OpenIFS integration, OASIS3-MCT coupling and CMIP7 runs.",
        ),
        (
            "Prediction Data Workflow",
            "Preprocessing and interpolation of EN4, ERA5 and ORAS5 data for climate predictions.",
        ),
        (
            "ece4-exp",
            "Manages EC-Earth4 experiment configuration with layered YAML files.",
        ),
        (
            "baro_tides_fd",
            "Global finite-difference solver for barotropic ocean tides (Fortran).",
        ),
        (
            "internal_tides_fd",
            "Global solver for barotropic and internal tides with vertical mode decomposition (Fortran).",
        ),
        (
            "pisces-inidata",
            "Builds PISCES biogeochemistry initial conditions for NEMO and EC-Earth4 from a data catalog.",
        ),
    ]
    expected_cv_tools = (
        "Tools: Python (xarray, Dask, PyTorch), Fortran (MPI, OpenMP), Bash, Slurm, Autosubmit, CDO, NCO. "
        "Models: EC-Earth4, OpenIFS, NEMO/PISCES, OASIS3-MCT, ICON."
    )
    expected_site_desc = "Vladimir Lapin, Senior Research Engineer at BSC. Climate models, HPC and ML emulators."

    profile = yaml.safe_load((REPO_ROOT / "data" / "profile.yaml").read_text(encoding="utf-8"))
    hugo_cfg = tomllib.loads((REPO_ROOT / "hugo.toml").read_text(encoding="utf-8"))
    home_soup = BeautifulSoup((built_site / "index.html").read_text(encoding="utf-8"), "lxml")

    # 1. Tagline
    assert re.sub(r"\s+", " ", profile.get("tagline") or "").strip() == expected_tagline
    assert re.sub(r"\s+", " ", profile.get("description") or "").strip() == expected_tagline
    assert hugo_cfg["params"]["profileMode"]["subtitle"] == expected_tagline
    home_subtitle = home_soup.select_one(".home-subtitle")
    assert home_subtitle is not None
    assert re.sub(r"\s+", " ", home_subtitle.get_text()).strip() == expected_tagline

    # 2. Bio
    assert re.sub(r"\s+", " ", profile.get("bio") or "").strip() == expected_bio
    home_bio = home_soup.select_one(".home-info .entry-content")
    assert home_bio is not None
    assert re.sub(r"\s+", " ", home_bio.get_text()).strip() == expected_bio

    # 3. Focus
    assert re.sub(r"\s+", " ", profile.get("current_focus") or "").strip() == expected_focus
    home_focus = home_soup.select_one(".home-info .current-focus")
    assert home_focus is not None
    assert re.sub(r"\s+", " ", home_focus.get_text()).strip() == f"Current Focus: {expected_focus}"

    # 4. Home links
    audience_links = home_soup.select(".home-audience-links a")
    actual_links = [
        (
            re.sub(r"\s+", " ", a.select_one(".home-audience-title").get_text()).strip(),
            a.get("href") or "",
            re.sub(r"\s+", " ", a.select_one(".home-audience-desc").get_text()).strip(),
        )
        for a in audience_links
    ]
    assert len(actual_links) == len(expected_home_links)
    for (got_title, got_href, got_desc), (exp_title, exp_path, exp_desc) in zip(actual_links, expected_home_links):
        assert got_title == exp_title
        assert got_href.endswith(exp_path), f"Expected href ending in {exp_path}, got {got_href!r}"
        assert got_desc == exp_desc

    # 5 & 6. Work intro and current projects
    work_soup = BeautifulSoup((built_site / "work" / "index.html").read_text(encoding="utf-8"), "lxml")
    work_content = work_soup.select_one(".post-content")
    assert work_content is not None
    first_p = work_content.select_one(":scope > p")
    assert first_p is not None
    assert re.sub(r"\s+", " ", first_p.get_text()).strip() == expected_work_intro
    email_link = first_p.find("a", string="email me")
    assert email_link is not None and email_link.get("href") == "mailto:vladimir.lapin@bsc.es"

    project_lis = work_content.select(":scope > ul:first-of-type > li")
    actual_projects = [re.sub(r"\s+", " ", li.get_text()).strip() for li in project_lis]
    assert actual_projects == expected_work_projects

    # 7. Software descriptions (YAML and rendered /work/)
    software_yaml = yaml.safe_load((REPO_ROOT / "data" / "curated_software.yaml").read_text(encoding="utf-8"))
    yaml_pairs = [(item["name"], item["description"]) for item in software_yaml]
    assert yaml_pairs == expected_software
    for _, desc in yaml_pairs:
        assert "$" not in desc, f"Unexpected math markup in software description: {desc!r}"

    rendered_cards = [
        (
            re.sub(r"\s+", " ", card.select_one("h3").get_text()).strip(),
            re.sub(r"\s+", " ", card.select_one(".software-desc").get_text()).strip(),
        )
        for card in work_content.select(".software-card")
    ]
    assert rendered_cards == expected_software

    # 8. CV tools line
    cv_soup = BeautifulSoup((built_site / "cv" / "index.html").read_text(encoding="utf-8"), "lxml")
    cv_tools = cv_soup.select_one(".cv-tools-line")
    assert cv_tools is not None
    assert re.sub(r"\s+", " ", cv_tools.get_text()).strip() == expected_cv_tools

    # 9. Publications intro
    stats = yaml.safe_load((REPO_ROOT / "data" / "stats.yaml").read_text(encoding="utf-8"))
    scholar = yaml.safe_load((REPO_ROOT / "data" / "scholar_stats.yaml").read_text(encoding="utf-8"))
    pub_soup = BeautifulSoup((built_site / "publications" / "index.html").read_text(encoding="utf-8"), "lxml")
    pub_intro = pub_soup.select_one(".pub-metrics-intro")
    assert pub_intro is not None
    assert re.sub(r"\s+", " ", pub_intro.get_text()).strip() == (
        f"{stats['publications']} papers · {scholar['citations']} citations · h-index {scholar['h_index']} (OpenAlex)."
    )

    # 10. hugo.toml description, meta description, and JSON-LD description on every page
    assert hugo_cfg["description"] == expected_site_desc
    assert hugo_cfg["params"]["description"] == expected_site_desc
    meta_desc = home_soup.find("meta", attrs={"name": "description"})
    assert meta_desc is not None and meta_desc.get("content") == expected_site_desc

    for rel, page_soup in non_redirect_html_pages:
        ld_scripts = page_soup.find_all("script", attrs={"type": "application/ld+json"})
        assert ld_scripts, f"Missing JSON-LD script on {rel}"
        found_person = False
        for sc in ld_scripts:
            payload = json.loads(sc.string or "")
            if payload.get("@type") == "Person":
                found_person = True
                assert payload.get("description") == expected_site_desc, f"Person JSON-LD mismatch on {rel}"
            elif payload.get("@type") == "Organization":
                assert payload.get("description") == expected_site_desc, f"Organization JSON-LD mismatch on {rel}"
        assert found_person, f"Missing Person JSON-LD on {rel}"


def test_monograph_tabular_nums_coverage(built_stylesheet: str) -> None:
    """Verify font-variant-numeric: tabular-nums is declared across dates, metrics, badges, and tables."""
    rules = _parse_css_rules(built_stylesheet)
    tabular_selectors: set[str] = set()
    for rule in rules:
        if rule.type == "qualified-rule":
            content = _serialize_content(rule).replace(" ", "")
            if "font-variant-numeric:tabular-nums" in content:
                for part in _serialize_prelude(rule).split(","):
                    tabular_selectors.add(part.strip())

    required = {
        ".log-row-date",
        ".cv-date-badge",
        ".cv-download-badge",
        ".pub-year-pill",
        ".pub-card-year",
        ".pub-year-heading",
        ".pub-metrics-intro",
        ".log-kind-pill",
        ".sim-spec-pill",
        ".action-pill",
        "table th",
        "table td",
    }
    missing = sorted(required - tabular_selectors)
    assert not missing, f"Selectors missing font-variant-numeric: tabular-nums: {missing}"


def test_action_pills_css_and_html_contracts(built_site: Path, built_stylesheet: str) -> None:
    """Verify action pill containers wrap cleanly, pills avoid --secondary, rows are flat, and /publications/ renders action pills."""
    rules = _parse_css_rules(built_stylesheet)

    # All standalone pill/tag strip containers must allow wrapping
    for container_sel in (
        ".action-pill-row",
        ".pub-card-actions",
        ".log-kind-filter",
        ".cv-nav-bar",
        ".pub-year-nav",
        ".software-tags",
        ".cv-skills",
        ".sim-specs",
        ".entry-tags",
        ".entry-kinds",
        ".post-kinds",
    ):
        matched = _find_qualified_rules(rules, lambda p, s=container_sel: s in [part.strip() for part in p.split(",")])
        assert matched, f"Missing CSS rule for pill container {container_sel}"
        combined = ";".join(c for _, c in matched).replace(" ", "")
        assert "flex-wrap:wrap" in combined, f"Pill container {container_sel} must declare flex-wrap: wrap"

    # Pills & badges must never regress to low-contrast --secondary ink and must have flat elevation
    for pill_sel in (
        ".action-pill",
        ".pub-badge-btn",
        ".pub-copy-btn",
        ".pub-bibtex-summary",
        ".cv-nav-link",
        ".log-kind-pill",
        ".kind-badge",
        ".post-tag",
        ".software-tag",
        ".sim-spec-pill",
        ".cv-skills-tag",
        ".cv-date-badge",
        ".pub-year-pill",
        ".cv-download-badge",
    ):
        matched = _find_qualified_rules(rules, lambda p, s=pill_sel: p == s)
        assert matched, f"Missing CSS rule for pill selector {pill_sel}"
        combined = ";".join(c for _, c in matched).replace(" ", "")
        assert "color:var(--secondary)" not in combined, f"{pill_sel} must not use low-contrast --secondary"
        shadow_matches = re.findall(r"box-shadow:([^;]+)", combined)
        assert all(val == "none" for val in shadow_matches), f"{pill_sel} has non-flat box-shadow: {shadow_matches}"

    # Monograph Log rows must neutralize PaperMod card box-shadow and border-radius clutter
    post_entry_rules = _find_qualified_rules(rules, lambda p: p == ".post-entry")
    assert post_entry_rules
    pe_css = ";".join(c for _, c in post_entry_rules).replace(" ", "")
    assert "box-shadow:none" in pe_css
    assert "border-radius:0" in pe_css

    log_row_rules = _find_qualified_rules(rules, lambda p: p == ".log-rows .log-row")
    assert log_row_rules
    lr_css = ";".join(c for _, c in log_row_rules).replace(" ", "")
    assert "border-radius:0" in lr_css
    assert "background:transparent" in lr_css or "background:00" in lr_css

    # /publications/ HTML action pill contract
    pubs_data = yaml.safe_load((REPO_ROOT / "data" / "publications.yaml").read_text(encoding="utf-8"))
    expected_doi_count = sum(1 for item in pubs_data if item.get("doi"))
    expected_url_count = sum(
        1 for item in pubs_data
        if item.get("url") and not re.match(r"^https?://(dx\.)?doi\.org", str(item.get("url")))
    )
    pub_soup = BeautifulSoup((built_site / "publications" / "index.html").read_text(encoding="utf-8"), "lxml")
    pub_cards = pub_soup.select(".pub-card")
    assert len(pub_cards) == len(pubs_data) and len(pub_cards) >= 24
    assert len(pub_soup.select(".pub-card a.pub-doi-btn")) == expected_doi_count
    assert len(pub_soup.select(".pub-card a.pub-link-btn")) == expected_url_count
    for card in pub_cards:
        assert card.select_one("button.pub-copy-btn") is not None
        assert card.select_one("details.pub-bibtex-details > summary.pub-bibtex-summary") is not None


def _pdf_page_count(pdf_path: Path) -> int:
    """Return PDF page count preferring pypdf, then pdfinfo, then pure-Python fallback."""
    try:
        from pypdf import PdfReader

        return len(PdfReader(str(pdf_path)).pages)
    except ImportError:
        pass

    pdfinfo_bin = shutil.which("pdfinfo")
    if pdfinfo_bin:
        proc = subprocess.run([pdfinfo_bin, str(pdf_path)], capture_output=True, text=True, check=False)
        if proc.returncode == 0:
            match = re.search(r"^Pages:\s*(\d+)", proc.stdout, re.MULTILINE)
            if match:
                return int(match.group(1))

    raw = pdf_path.read_bytes()
    return len(re.findall(rb"/Type\s*/Page\b(?!s)", raw))


def test_cv_pdfs_and_timeline_structure(built_site: Path) -> None:
    """Verify 2-page Industry PDF, Full Research PDF, above-the-fold download bar order, and timeline structure."""
    industry_pdf = built_site / "downloads" / "vladimir-lapin-cv-industry.pdf"
    research_pdf = built_site / "downloads" / "vladimir-lapin-cv-research-full.pdf"
    assert industry_pdf.is_file() and industry_pdf.read_bytes().startswith(b"%PDF-")
    assert research_pdf.is_file() and research_pdf.read_bytes().startswith(b"%PDF-")

    industry_pages = _pdf_page_count(industry_pdf)
    research_pages = _pdf_page_count(research_pdf)
    assert industry_pages == 2, f"Expected Industry CV PDF to be 2 pages, got {industry_pages}"
    assert research_pages >= 2, f"Expected Full Research CV PDF >= 2 pages, got {research_pages}"

    cv_raw = (built_site / "cv" / "index.html").read_text(encoding="utf-8")
    cv_soup = BeautifulSoup(cv_raw, "lxml")
    assert cv_soup.select("article.post-entry, .log-row, .post-meta") == []
    assert "applied-scientist" not in cv_raw

    pos_bar = cv_raw.find("cv-download-bar")
    pos_tl = cv_raw.find("cv-timeline")
    assert pos_bar != -1 and pos_tl != -1 and pos_bar < pos_tl, (
        ".cv-download-bar must precede .cv-timeline on /cv/"
    )

    industry_btn = cv_soup.select_one('a.cv-download-btn[href="/downloads/vladimir-lapin-cv-industry.pdf"]')
    assert industry_btn is not None
    sublabel = industry_btn.select_one(".cv-download-sublabel")
    badge = industry_btn.select_one(".cv-download-badge.cv-download-badge--primary")
    assert sublabel is not None and "2-page" in sublabel.get_text()
    assert badge is not None and "2-page" in badge.get_text()

    timelines = cv_soup.select(".cv-timeline")
    assert len(timelines) == 2, f"Expected 2 .cv-timeline blocks (employment + education), got {len(timelines)}"

    emp_entries = timelines[0].select(".cv-entry")
    assert len(emp_entries) == 5, f"Expected 5 employment entries, got {len(emp_entries)}"
    assert "Barcelona Supercomputing Center" in emp_entries[0].get_text(" ", strip=True)
    assert len(timelines[0].select(".cv-entry-compact")) == 1
    assert "Career Break" in timelines[0].select_one(".cv-entry-compact").get_text(" ", strip=True)

    edu_entries = timelines[1].select(".cv-entry")
    assert len(edu_entries) == 2, f"Expected 2 education entries, got {len(edu_entries)}"
    edu_text = timelines[1].get_text(" ", strip=True)
    assert "University of Limerick" in edu_text and "Lomonosov Moscow State University" in edu_text


def test_design_docs_sync(built_stylesheet: str) -> None:
    """Verify DESIGN.md (8 canonical sections + frontmatter) and .impeccable/design.json stay synced with main.css."""
    design_md = (REPO_ROOT / "DESIGN.md").read_text(encoding="utf-8")
    parts = design_md.split("---", 2)
    assert len(parts) == 3, "DESIGN.md must start with YAML frontmatter"
    fm = yaml.safe_load(parts[1]) or {}
    body = parts[2]

    expected_headings = [
        "Overview",
        "Colors",
        "Typography",
        "Layout",
        "Elevation & Depth",
        "Shapes",
        "Components",
        "Do's and Don'ts",
    ]
    found_headings = re.findall(r"^##\s+(.+)$", body, re.MULTILINE)
    assert found_headings == expected_headings, (
        f"DESIGN.md H2 sections mismatch: got {found_headings}, expected {expected_headings}"
    )

    design_json = json.loads((REPO_ROOT / ".impeccable" / "design.json").read_text(encoding="utf-8"))
    assert design_json.get("schemaVersion") == 2
    color_meta = design_json.get("extensions", {}).get("colorMeta", {})
    fm_colors = fm.get("colors", {})
    assert set(fm_colors.keys()) == set(color_meta.keys()), "Color keys differ between DESIGN.md and design.json"
    for key, hex_val in fm_colors.items():
        assert color_meta[key]["canonical"].lower() == str(hex_val).lower(), (
            f"Color {key} mismatch: DESIGN.md={hex_val} vs design.json={color_meta[key]['canonical']}"
        )

    rules = _parse_css_rules(built_stylesheet)
    root_combined = ";".join(c for _, c in _find_qualified_rules(rules, lambda p: p == ":root")).lower()
    for css_var, design_key in (
        ("--accent-pine-light", "accent-pine"),
        ("--accent-pine-dark", "accent-pine-dark"),
        ("--accent-pine-mid-light", "accent-pine-mid"),
        ("--accent-pine-mid-dark", "accent-pine-mid-dark"),
        ("--accent-ocean-light", "accent-ocean"),
        ("--accent-ocean-dark", "accent-ocean-dark"),
        ("--hairline-light", "hairline-light"),
        ("--hairline-dark", "hairline-dark"),
        ("--border-control-light", "border-control-light"),
        ("--border-control-dark", "border-control-dark"),
        ("--surface-pill-light", "surface-pill-light"),
        ("--surface-pill-dark", "surface-pill-dark"),
        ("--surface-pill-hover-light", "surface-pill-hover-light"),
        ("--surface-pill-hover-dark", "surface-pill-hover-dark"),
    ):
        expected_hex = fm_colors[design_key].lower()
        assert f"{css_var}:{expected_hex}" in root_combined.replace(" ", ""), (
            f"Built CSS {css_var} out of sync with DESIGN.md {design_key}={expected_hex}"
        )

    body_lower = body.lower()
    for token in ("left-aligned", "tidal", "tabular-nums", "action pill", "nhigham.com"):
        assert token in body_lower, f"DESIGN.md missing required concept {token!r}"
    assert "profile-symbol.svg" not in design_md


def test_zero_nick_higham_and_no_teamwork_metadata(
    non_redirect_html_pages: list[tuple[Path, BeautifulSoup]],
) -> None:
    """Verify zero Nick Higham WordPress patterns in built HTML and zero Teamwork metadata files in REPO_ROOT."""
    for forbidden_file in ("PROJECT.md", "BRIEFING.md", "TEST_INFRA.md", "TEST_READY.md", "DISPATCH.md", "handoff.md"):
        assert not (REPO_ROOT / forbidden_file).exists(), f"Teamwork file leaked into repo root: {forbidden_file}"
    assert not (REPO_ROOT / ".agents" / "teamwork").exists(), ".agents/teamwork/ must not exist inside repo"

    for rel, soup in non_redirect_html_pages:
        assert soup.select("aside, #secondary, .widget-area, .sidebar") == [], f"Sidebar widget found on {rel}"
        assert soup.select(".widget_recent_entries, .widget_archive, .widget_categories") == [], (
            f"WordPress widget class found on {rel}"
        )
        assert soup.select('input[type="email"]') == [], f"Email subscriber input found on {rel}"
        for inp in soup.find_all("input"):
            if rel.as_posix() == "publications/index.html" and inp.get("id") == "pubFilterInput":
                continue
            pytest.fail(f"Unexpected <input> element on {rel}: {inp}")

        gen = soup.find("meta", attrs={"name": "generator"})
        if gen is not None:
            assert "wordpress" not in (gen.get("content") or "").lower(), f"WordPress generator meta on {rel}"

        for sc in soup.find_all("script", src=True):
            assert "mathjax" not in sc["src"].lower(), f"MathJax script found on {rel}"

        for a in soup.find_all("a", href=True):
            assert "What Is" not in a.get_text(" ", strip=True), f"Forbidden 'What Is' series link on {rel}"


def test_tier5_skip_link_copy_code_sim_focus_and_bibtex_css(
    built_site: Path,
    built_stylesheet: str,
    non_redirect_html_pages: list[tuple[Path, BeautifulSoup]],
) -> None:
    """Verify skip-link + #main-content, copy-code hardening, sim-facade focus, and BibTeX code CSS."""
    for rel, soup in non_redirect_html_pages:
        skip = soup.select_one("a.skip-link")
        main = soup.select_one("main#main-content")
        assert skip is not None and skip.get("href") == "#main-content", f"Missing skip-link on {rel}"
        assert main is not None and main.get("tabindex") == "-1", f"Missing main#main-content[tabindex=-1] on {rel}"

    footer_src = (REPO_ROOT / "layouts" / "_partials" / "footer.html").read_text(encoding="utf-8")
    assert "copybutton.type" in footer_src
    assert ".pub-bibtex-block" in footer_src
    assert ".catch(" in footer_src

    sim_src = (REPO_ROOT / "layouts" / "shortcodes" / "simulation_gallery.html").read_text(encoding="utf-8")
    assert "video.tabIndex = 0" in sim_src
    assert "video.focus(" in sim_src

    pub_src = (REPO_ROOT / "layouts" / "shortcodes" / "pub_list.html").read_text(encoding="utf-8")
    assert ".trim()" in pub_src

    rules = _parse_css_rules(built_stylesheet)
    copy_rules = _find_qualified_rules(rules, lambda p: p == ".copy-code")
    assert len(copy_rules) >= 2, "Missing .copy-code override in built CSS"
    assert any(
        "display:inline-flex" in c.replace(" ", "") and "display:none" not in c.replace(" ", "")
        for _, c in copy_rules
    ), ".copy-code must override PaperMod display: none with inline-flex"

    bib_code_rules = _find_qualified_rules(rules, lambda p: p == ".pub-bibtex-block pre code")
    assert bib_code_rules, "Missing .pub-bibtex-block pre code rule"
    bib_code_css = ";".join(c for _, c in bib_code_rules).replace(" ", "")
    assert "background:transparent!important" in bib_code_css or "background:00!important" in bib_code_css


