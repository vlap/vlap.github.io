"""Unit tests for scripts/check_modern_web.py."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
import check_modern_web  # noqa: E402


def test_extract_and_partition_separates_submodule_findings(tmp_path: Path) -> None:
    """Verify nested legacy-scan findings are partitioned between first-party and PaperMod."""
    scan_data = {
        "activeRuleCount": 52,
        "activeGuideCount": 38,
        "guides": [
            {
                "guideId": "dark-mode",
                "rules": [
                    {
                        "ruleId": "dark-mode",
                        "findings": [
                            {"file": str(tmp_path / "assets/css/extended/main.css"), "line": 31, "message": "x"},
                            {"file": "themes/PaperMod/layouts/_partials/footer.html", "line": 99, "message": "y"},
                        ],
                    }
                ],
            }
        ],
    }

    flattened = check_modern_web.extract_findings(scan_data)
    assert len(flattened) == 2

    first_party, submodule = check_modern_web.partition_findings(flattened, tmp_path)
    assert [item["relativeFile"] for item in first_party] == ["assets/css/extended/main.css"]
    assert [item["relativeFile"] for item in submodule] == ["themes/PaperMod/layouts/_partials/footer.html"]


def test_main_exits_nonzero_when_first_party_finding_present(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Verify CLI exits 1 on first-party finding and 0 when only submodule findings remain."""
    monkeypatch.setattr(
        check_modern_web,
        "run_legacy_scan",
        lambda repo_root, offline=False: {
            "guides": [
                {
                    "guideId": "js",
                    "rules": [
                        {
                            "ruleId": "js/replace-children-innerhtml",
                            "findings": [{"file": "layouts/shortcodes/foo.html", "line": 10, "message": "bad"}],
                        }
                    ],
                }
            ]
        },
    )
    assert check_modern_web.main(["--json"]) == 1
    out = json.loads(capsys.readouterr().out)
    assert out["firstPartyCount"] == 1
    assert out["submoduleCount"] == 0

    monkeypatch.setattr(
        check_modern_web,
        "run_legacy_scan",
        lambda repo_root, offline=False: {
            "guides": [
                {
                    "guideId": "js",
                    "rules": [
                        {
                            "ruleId": "js/replace-children-innerhtml",
                            "findings": [{"file": "themes/PaperMod/assets/js/fastsearch.js", "line": 51, "message": "sub"}],
                        }
                    ],
                }
            ]
        },
    )
    assert check_modern_web.main(["--json"]) == 0
    out_clean = json.loads(capsys.readouterr().out)
    assert out_clean["firstPartyCount"] == 0
    assert out_clean["submoduleCount"] == 1


def test_normalize_finding_path_preserves_dot_prefixed_directories(tmp_path: Path) -> None:
    """Verify leading './' is removed without stripping leading dots on dotfiles/dotdirs."""
    assert (
        check_modern_web.normalize_finding_path("./.github/workflows/hugo.yml", tmp_path)
        == ".github/workflows/hugo.yml"
    )
    assert (
        check_modern_web.normalize_finding_path(r".\.github\workflows\hugo.yml", tmp_path)
        == ".github/workflows/hugo.yml"
    )
    assert (
        check_modern_web.normalize_finding_path("././.github/workflows/hugo.yml", tmp_path)
        == ".github/workflows/hugo.yml"
    )
