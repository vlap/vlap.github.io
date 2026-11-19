"""Tests for scripts/fetch_openalex.py."""

import json
from pathlib import Path
import sys
import urllib.error

import pytest
import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
import fetch_openalex  # noqa: E402


class _FakeResp:
    """Minimal context-manager mock for urllib.request.urlopen."""

    def __init__(self, payload: bytes) -> None:
        self._payload = payload

    def __enter__(self) -> "_FakeResp":
        return self

    def __exit__(self, *args: object) -> bool:
        return False

    def read(self) -> bytes:
        return self._payload


def test_fetch_openalex_writes_scholar_stats(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Verify update_scholar_stats writes standardized OpenAlex counts and date."""
    payload = json.dumps({
        "cited_by_count": 1420,
        "summary_stats": {"h_index": 10, "i10_index": 11},
    }).encode("utf-8")

    monkeypatch.setattr(
        fetch_openalex.urllib.request,
        "urlopen",
        lambda *a, **k: _FakeResp(payload),
    )
    out_file = tmp_path / "scholar_stats.yaml"
    fetch_openalex.update_scholar_stats(out_file)
    written = yaml.safe_load(out_file.read_text(encoding="utf-8"))
    assert written["citations"] == 1420
    assert written["h_index"] == 10
    assert written["i10_index"] == 11
    assert "last_updated" in written


def test_fetch_openalex_fails_loudly_on_http_error(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Verify URLError propagates instead of being swallowed."""
    def boom(*args: object, **kwargs: object) -> None:
        raise urllib.error.URLError("timeout")

    monkeypatch.setattr(fetch_openalex.urllib.request, "urlopen", boom)
    with pytest.raises(urllib.error.URLError):
        fetch_openalex.update_scholar_stats(tmp_path / "scholar_stats.yaml")


@pytest.mark.parametrize(
    "bad_payload",
    [
        {"summary_stats": {"h_index": 10}},
        {"cited_by_count": 100, "summary_stats": {}},
    ],
)
def test_fetch_openalex_raises_on_unexpected_schema(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    bad_payload: dict,
) -> None:
    """Verify ValueError is raised when required OpenAlex keys are missing."""
    payload = json.dumps(bad_payload).encode("utf-8")
    monkeypatch.setattr(
        fetch_openalex.urllib.request,
        "urlopen",
        lambda *a, **k: _FakeResp(payload),
    )
    with pytest.raises(ValueError):
        fetch_openalex.update_scholar_stats(tmp_path / "scholar_stats.yaml")
