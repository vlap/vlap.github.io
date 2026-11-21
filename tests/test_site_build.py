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
    "software/index.html",
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
    for rel in ["index.html", "software/index.html", "publications/index.html", "cv/index.html"]:
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

    home_soup = BeautifulSoup((built_site / "index.html").read_text(encoding="utf-8"), "lxml")
    assert home_soup.find(attrs={"href": re.compile(r"katex@")}) is None
    assert home_soup.find(attrs={"src": re.compile(r"katex@")}) is None


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
    sw_text = (built_site / "software/index.html").read_text(encoding="utf-8")
    match = re.search(r"function playSimVideo\([^)]*\)\{[^}]+\}", sw_text)
    assert match is not None, "Missing playSimVideo function in built software page"
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
    soup = BeautifulSoup((built_site / "software/index.html").read_text(encoding="utf-8"), "lxml")
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

    sw_soup = BeautifulSoup((built_site / "software/index.html").read_text(encoding="utf-8"), "lxml")
    gh_links = sw_soup.select("a.software-github-link")
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
    """Verify #pubFilterInput uses :focus-visible outline and does not suppress :focus outline."""
    rules = _parse_css_rules(built_stylesheet)
    bad_focus = _find_qualified_rules(rules, lambda p: p == "#pubFilterInput:focus")
    for _, content in bad_focus:
        assert "outline:none" not in content.replace(" ", "")
        assert "outline:0" not in content.replace(" ", "")

    fv_rules = _find_qualified_rules(rules, lambda p: p == "#pubFilterInput:focus-visible")
    assert fv_rules, "Missing #pubFilterInput:focus-visible rule"
    fv_css = fv_rules[0][1].replace(" ", "")
    assert "outline:2pxsolidvar(--primary)" in fv_css
    assert "outline-offset:2px" in fv_css


def test_r3_images_dimensions_and_lcp_priority(built_site: Path) -> None:
    """Verify avatar fetchpriority/dimensions and simulation poster dimensions."""
    home_soup = BeautifulSoup((built_site / "index.html").read_text(encoding="utf-8"), "lxml")
    avatar = home_soup.select_one(".home-info-image img")
    assert avatar is not None
    assert avatar.get("fetchpriority") == "high"
    assert avatar.get("width") == "150"
    assert avatar.get("height") == "150"

    sw_soup = BeautifulSoup((built_site / "software/index.html").read_text(encoding="utf-8"), "lxml")
    posters = sw_soup.select("img.sim-poster")
    assert len(posters) == 3
    for img in posters:
        assert img.get("width") == "480"
        assert img.get("height") == "360"
        assert img.get("loading") == "lazy"


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


def test_404_excluded_from_index_json_sitemap_and_rss(built_site: Path) -> None:
    """Verify /404/ is excluded from index.json, sitemap.xml, and index.xml while 404 page still builds."""
    index_entries = json.loads((built_site / "index.json").read_text(encoding="utf-8"))
    assert len(index_entries) >= 10
    assert not any(
        "/404" in entry.get("permalink", "") or "404: Page Not Found" in entry.get("title", "")
        for entry in index_entries
    ), "404 page leaked into index.json"

    sitemap_root = ET.fromstring((built_site / "sitemap.xml").read_text(encoding="utf-8"))
    locs = [el.text or "" for el in sitemap_root.iter("{http://www.sitemaps.org/schemas/sitemap/0.9}loc")]
    assert len(locs) >= 10
    assert not any(loc.endswith("/404/") or loc.endswith("/404.html") for loc in locs), (
        "404 page leaked into sitemap.xml"
    )

    rss_root = ET.fromstring((built_site / "index.xml").read_text(encoding="utf-8"))
    rss_links = [el.text or "" for el in rss_root.findall("./channel/item/link")]
    assert len(rss_links) >= 1
    assert not any(link.endswith("/404/") or link.endswith("/404.html") for link in rss_links), (
        "404 page leaked into index.xml"
    )

    page_404 = built_site / "404" / "index.html"
    if not page_404.is_file():
        page_404 = built_site / "404.html"
    assert page_404.is_file(), "404 page should still be rendered"
    soup_404 = BeautifulSoup(page_404.read_text(encoding="utf-8"), "lxml")
    robots = soup_404.find("meta", attrs={"name": "robots"})
    assert robots is not None and robots.get("content") == "noindex, nofollow"


def test_presentations_yaml_no_urls_typo_and_renders_link(built_site: Path) -> None:
    """Verify data/presentations.yaml uses 'url' (not 'urls') and renders the ClimathNet 2014 link."""
    items = yaml.safe_load((REPO_ROOT / "data" / "presentations.yaml").read_text(encoding="utf-8"))
    assert isinstance(items, list) and len(items) >= 20
    for item in items:
        assert "urls" not in item, f"Unexpected 'urls' key in presentations.yaml: {item}"

    soup = BeautifulSoup((built_site / "cv" / "presentations" / "index.html").read_text(encoding="utf-8"), "lxml")
    link = soup.find("a", class_="cv-link", href="https://climathnet.org/meetingsandevents/conference2014/")
    assert link is not None, "Missing rendered ClimathNet 2014 link on /cv/presentations/"


def test_hugo_toml_clean_and_contact_nav(
    non_redirect_html_pages: list[tuple[Path, BeautifulSoup]],
) -> None:
    """Verify hugo.toml scoping, nav/buttons cleanup, and rendered post features."""
    raw_toml = (REPO_ROOT / "hugo.toml").read_text(encoding="utf-8")
    assert len(re.findall(r"(?im)^\s*showCodeCopyButtons\s*=", raw_toml)) == 1

    cfg = tomllib.loads(raw_toml)
    assert cfg.get("taxonomies") == {
        "tag": "tags",
        "category": "categories",
        "kind": "kinds",
    }, f"Unexpected [taxonomies] in hugo.toml: {cfg.get('taxonomies')}"
    params = cfg.get("params", {})
    for key in (
        "ShowReadingTime",
        "ShowShareButtons",
        "ShowPostNavLinks",
        "ShowBreadCrumbs",
        "ShowCodeCopyButtons",
        "ShowScrollToTop",
    ):
        assert params.get(key) is True, f"params.{key} must be True directly under [params]"
    assert params.get("ShowToc") is False, "params.ShowToc must live directly under [params]"
    assert params.get("mainSections") == ["posts"], "params.mainSections must live directly under [params]"

    minify_cfg = params.get("minify", {})
    assert set(minify_cfg.keys()) == {"disableHTML", "disableJS", "disableCSS"}, (
        f"Unexpected keys trapped under [params.minify]: {minify_cfg}"
    )

    buttons = params.get("profileMode", {}).get("buttons", [])
    assert not any(btn.get("url") == "/tools/" for btn in buttons), "Dead /tools/ button still in hugo.toml"

    menu_main = cfg.get("menu", {}).get("main", [])
    assert any(m.get("url") == "/contact/" and m.get("name") == "Contact" for m in menu_main), (
        "Missing /contact/ in menu.main"
    )
    weights = [m.get("weight") for m in menu_main]
    assert len(weights) == len(set(weights)), f"Duplicate menu.main weights: {weights}"

    post_pages = [
        (rel, soup)
        for rel, soup in non_redirect_html_pages
        if len(rel.parts) == 3 and rel.parts[0] == "posts" and rel.parts[2] == "index.html"
    ]
    assert len(post_pages) == 3, f"Expected 3 built post pages, got {len(post_pages)}"

    code_posts = 0
    for rel, soup in post_pages:
        assert soup.select_one("nav.breadcrumbs") is not None, f"Missing breadcrumbs on {rel}"
        assert soup.select_one("ul.share-buttons") is not None, f"Missing share-buttons on {rel}"
        assert soup.select_one("nav.paginav") is not None, f"Missing post nav links on {rel}"
        meta = soup.select_one(".post-meta")
        assert meta is not None and re.search(r"\b\d+\s+min\b", meta.get_text()), (
            f"Missing reading time in .post-meta on {rel}"
        )
        if soup.select("pre > code"):
            code_posts += 1
            scripts = "\n".join(s.get_text() for s in soup.find_all("script"))
            assert "copy-code" in scripts, f"Missing copy-code script on post with <pre><code>: {rel}"
    assert code_posts >= 1, f"Expected >= 1 post with <pre><code>, found {code_posts}"

    for rel, soup in non_redirect_html_pages:
        assert soup.find("a", href=re.compile(r"/tools/")) is None, f"Dead /tools/ link found on {rel}"
        assert soup.select_one('#menu a[href$="/contact/"]') is not None, f"Missing /contact/ nav link on {rel}"


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
    """Verify #searchInput:focus-visible, 44px #theme-toggle, non-bounce .sim-play-icon, and flat .sim-physics."""
    rules = _parse_css_rules(built_stylesheet)

    bad_search_focus = _find_qualified_rules(rules, lambda p: p == "#searchInput:focus")
    for _, content in bad_search_focus:
        assert "outline:none" not in content.replace(" ", "")
        assert "outline:0" not in content.replace(" ", "")

    search_fv = _find_qualified_rules(rules, lambda p: p == "#searchInput:focus-visible")
    assert search_fv, "Missing #searchInput:focus-visible rule"
    search_css = search_fv[0][1].replace(" ", "")
    assert "outline:2pxsolidvar(--primary)" in search_css
    assert "outline-offset:2px" in search_css

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
    """Verify README.md documents current 5 pillars, workflows, and verification commands without obsolete claims."""
    readme = (REPO_ROOT / "README.md").read_text(encoding="utf-8")
    for required in (
        "/about/",
        "/posts/",
        "/software/",
        "/publications/",
        "/cv/",
        "/contact/",
        "/search/",
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
        "every night at midnight",
        "Micro-post",
        "--kind micro",
        "github_activity.yaml",
        "git push origin main --force",
        "(requests, pyyaml)",
    ):
        assert obsolete not in readme, f"README.md still contains obsolete content: {obsolete}"


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
        "about/index.html",
        "software/index.html",
        "publications/index.html",
        "cv/index.html",
        "cv/presentations/index.html",
        "cv/trainings/index.html",
        "contact/index.html",
        "kinds/index.html",
        "kinds/note/index.html",
        "kinds/talk/index.html",
        "posts/2026-06-15-neural-surrogates-shallow-water-equations/index.html",
        "posts/2014-04-28-egu2014-global-modelling-surface-internal-tides/index.html",
        "posts/2013-06-21-ams19-global-modelling-surface-internal-tides/index.html",
    ):
        assert expected in checked_routes, f"Expected route missing from heading audit: {expected}"


def test_home_profile_symbol_svg_and_no_emoji_bar(built_site: Path) -> None:
    """Verify home <h1> uses decorative profile-symbol.svg instead of raw emoji bars."""
    home_soup = BeautifulSoup((built_site / "index.html").read_text(encoding="utf-8"), "lxml")
    h1 = home_soup.select_one(".home-info h1")
    assert h1 is not None
    img = h1.select_one("img.home-symbol-icon")
    assert img is not None, "Missing img.home-symbol-icon inside home <h1>"
    assert img.get("src") == "/images/decor/profile-symbol.svg"
    assert img.get("alt") == ""
    assert img.get("aria-hidden") == "true"
    assert img.get("width") == "28"
    assert img.get("height") == "28"
    assert (built_site / "images" / "decor" / "profile-symbol.svg").is_file()

    assert h1.select_one(".symbol-bar") is None
    h1_text = h1.get_text()
    for glyph in ("🌐", "♾", "🤖"):
        assert glyph not in h1_text, f"Raw emoji {glyph!r} found in home <h1>"

    profile_partial = (REPO_ROOT / "layouts" / "_partials" / "index_profile.html").read_text(encoding="utf-8")
    assert "/images/decor/profile-symbol.svg" in profile_partial
    assert "🌍" not in profile_partial


def test_cv_no_duplicate_post_entries_and_three_pdf_buttons(built_site: Path) -> None:
    """Verify /cv/ suppresses trailing post-entry cards and renders 3 PDF buttons with audience sublabels."""
    cv_soup = BeautifulSoup((built_site / "cv" / "index.html").read_text(encoding="utf-8"), "lxml")
    assert cv_soup.select("article.post-entry") == [], "Duplicate trailing post-entry cards found on /cv/"

    buttons = cv_soup.select(".cv-download-bar a.cv-download-btn")
    assert len(buttons) == 3, f"Expected 3 CV download buttons, got {len(buttons)}"
    sublabels: list[str] = []
    for btn in buttons:
        href = btn.get("href") or ""
        assert href.startswith("/downloads/") and href.endswith(".pdf"), f"Unexpected CV href: {href}"
        assert (built_site / href.lstrip("/")).is_file(), f"Missing PDF asset: {href}"
        title = btn.select_one(".cv-download-title")
        sub = btn.select_one(".cv-download-sublabel")
        assert title is not None and title.get_text(strip=True)
        assert sub is not None and sub.get_text(strip=True)
        sublabels.append(sub.get_text(strip=True))
    assert len(set(sublabels)) == 3, f"CV button sublabels must be distinct: {sublabels}"

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

    # Verify compact timeline styling for institution/bullet-less entries (Career Break)
    assert len(cv_soup.select(".cv-entry-compact")) == 1

    # Verify static portfolio pages omit blog date/reading-time .post-meta
    for rel in (
        "about/index.html",
        "software/index.html",
        "publications/index.html",
        "cv/index.html",
        "contact/index.html",
    ):
        page_soup = BeautifulSoup((built_site / rel).read_text(encoding="utf-8"), "lxml")
        assert page_soup.select_one(".post-meta") is None, f"Unexpected .post-meta on static page {rel}"


def test_css_contrast_tokens_and_modern_polish(built_stylesheet: str) -> None:
    """Verify Idea 2A contrast tokens/overrides, Idea 2B overflow rules, and Idea 3B modern CSS polish."""
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

    # Centered column preservation + mobile overflow containment rules
    assert "Georgia" not in built_stylesheet, "Display headings should keep system sans-serif stack"
    assert "max-width:68ch" not in built_stylesheet.replace(" ", ""), "Remove lopsided 68ch cap inside 720px column"

    main_rules = _find_qualified_rules(rules, lambda p: p == ".main")
    assert main_rules, "Missing .main containment rule"
    main_css = ";".join(c for _, c in main_rules).replace(" ", "")
    assert "width:100%" in main_css
    assert "min-width:0" in main_css
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
    assert "border-left:1pxsolidvar(--tertiary)" in ";".join(c for _, c in timeline_rules).replace(" ", "")

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
        "minmax(min(100%,300px),1fr)" in c.replace(" ", "") for _, c in sw_grid_rules
    ), f"Expected .software-container min(100%, 300px) grid track, got {sw_grid_rules}"

    sim_grid_rules = _find_qualified_rules(rules, lambda p: p == ".simulation-gallery")
    assert sim_grid_rules and any(
        "minmax(min(100%,350px),1fr)" in c.replace(" ", "") for _, c in sim_grid_rules
    ), f"Expected .simulation-gallery min(100%, 350px) grid track, got {sim_grid_rules}"

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


def test_index_json_enriched_with_publications_and_software(built_site: Path) -> None:
    """Verify index.json includes all publications (/publications/?q=) and software (/software/) without /404/."""
    entries = json.loads((built_site / "index.json").read_text(encoding="utf-8"))
    pubs = yaml.safe_load((REPO_ROOT / "data" / "publications.yaml").read_text(encoding="utf-8"))
    software = yaml.safe_load((REPO_ROOT / "data" / "curated_software.yaml").read_text(encoding="utf-8"))

    assert len(entries) >= 9 + len(pubs) + len(software)
    assert not any("/404" in e.get("permalink", "") for e in entries)

    by_title = {e.get("title"): e for e in entries}
    for pub in pubs:
        title = pub["title"]
        assert title in by_title, f"Publication missing from index.json: {title}"
        entry = by_title[title]
        assert "/publications/?q=" in entry["permalink"], f"Bad pub permalink: {entry['permalink']}"
        if pub.get("journal"):
            assert pub["journal"] in entry["content"]

    for sw in software:
        name = sw["name"]
        assert name in by_title, f"Software missing from index.json: {name}"
        entry = by_title[name]
        assert entry["permalink"].endswith("/software/"), f"Bad software permalink: {entry['permalink']}"
        for tag in sw.get("tags", []):
            assert tag in entry["content"]


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
        "index.json",
    ):
        built_file = built_site / rel
        assert built_file.is_file(), f"Missing expected built file: {rel}"
        content = built_file.read_text(encoding="utf-8")
        for slug in forbidden_slugs:
            assert slug not in content, f"Drafted slug {slug!r} leaked into {rel}"

    for html_path in built_site.rglob("*.html"):
        soup = BeautifulSoup(html_path.read_text(encoding="utf-8"), "lxml")
        for a in soup.find_all("a", href=True):
            href = a["href"]
            if href.startswith("/") and not href.startswith("//"):
                for slug in forbidden_slugs:
                    assert slug not in href, f"Relative internal link {href!r} in {html_path.relative_to(built_site)} points to drafted post"

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
