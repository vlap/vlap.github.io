#!/usr/bin/env python3
"""@file fetch_openalex.py
@brief Fetch author citation metrics from OpenAlex using ORCID and write data/scholar_stats.yaml.
"""

from datetime import date
import json
from pathlib import Path
import urllib.request

import yaml

ORCID_ID = "0000-0001-7302-8539"
OPENALEX_URL = f"https://api.openalex.org/authors/https://orcid.org/{ORCID_ID}"


def fetch_metrics(url: str = OPENALEX_URL) -> dict:
    """Query OpenAlex author endpoint and return standardized metric counts.

    @param url OpenAlex author API URL.
    @return Dictionary with citations, h_index, i10_index, and last_updated.
    @raises ValueError When required OpenAlex fields are missing.
    """
    req = urllib.request.Request(url, headers={"User-Agent": "vlap-site-metrics/1.0"})
    with urllib.request.urlopen(req, timeout=20) as resp:
        data = json.loads(resp.read().decode("utf-8"))
    summary = data.get("summary_stats")
    if (
        not isinstance(data, dict)
        or not isinstance(summary, dict)
        or "cited_by_count" not in data
        or "h_index" not in summary
    ):
        keys = list(data.keys()) if isinstance(data, dict) else type(data).__name__
        raise ValueError(f"Unexpected OpenAlex response schema: {keys}")
    return {
        "citations": int(data["cited_by_count"]),
        "h_index": int(summary["h_index"]),
        "i10_index": int(summary.get("i10_index", 0)),
        "last_updated": date.today().isoformat(),
    }


def update_scholar_stats(output_path: Path) -> None:
    """Fetch OpenAlex metrics and write them to output_path as YAML.

    @param output_path Destination YAML file path.
    """
    metrics = fetch_metrics()
    output_path.write_text(yaml.safe_dump(metrics, sort_keys=False), encoding="utf-8")


def main() -> int:
    """CLI entrypoint to refresh data/scholar_stats.yaml.

    @return Exit code (0 on success).
    """
    root = Path(__file__).resolve().parent.parent
    out = root / "data" / "scholar_stats.yaml"
    update_scholar_stats(out)
    print(f"Updated {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
