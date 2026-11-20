"""Run modern-web-guidance legacy-scan and enforce zero first-party findings."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parent.parent
SUBMODULE_PREFIX = "themes/PaperMod/"


def normalize_finding_path(raw_path: str, repo_root: Path) -> str:
    """Return a repository-relative POSIX path for a legacy-scan finding."""
    normalized = raw_path.replace("\\", "/")
    candidate = Path(normalized)
    if candidate.is_absolute():
        try:
            return candidate.resolve().relative_to(repo_root.resolve()).as_posix()
        except ValueError:
            return candidate.as_posix()
    while normalized.startswith("./"):
        normalized = normalized.removeprefix("./")
    return normalized


def extract_findings(scan_data: dict[str, Any]) -> list[dict[str, Any]]:
    """Flatten nested guides[].rules[].findings[] records from legacy-scan JSON."""
    flattened: list[dict[str, Any]] = []
    for guide in scan_data.get("guides", []):
        guide_id = guide.get("guideId", "unknown")
        for rule in guide.get("rules", []):
            rule_id = rule.get("ruleId", guide_id)
            for finding in rule.get("findings", []):
                entry = dict(finding)
                entry.setdefault("guideId", guide_id)
                entry.setdefault("ruleId", rule_id)
                flattened.append(entry)
    return flattened


def partition_findings(
    findings: list[dict[str, Any]],
    repo_root: Path,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Split legacy-scan findings into first-party and PaperMod submodule lists."""
    first_party: list[dict[str, Any]] = []
    submodule: list[dict[str, Any]] = []

    for finding in findings:
        rel_path = normalize_finding_path(str(finding.get("file", "")), repo_root)
        enriched = dict(finding)
        enriched["relativeFile"] = rel_path
        if rel_path.startswith(SUBMODULE_PREFIX) or rel_path == "themes/PaperMod":
            submodule.append(enriched)
        else:
            first_party.append(enriched)

    return first_party, submodule


def run_legacy_scan(repo_root: Path, offline: bool = False) -> dict[str, Any]:
    """Execute modern-web-guidance legacy-scan --json and parse its output."""
    cmd = ["npx"]
    if offline:
        cmd.append("--offline")
    else:
        cmd.append("-y")
    cmd.extend(["modern-web-guidance@latest", "legacy-scan", str(repo_root), "--json"])

    result = subprocess.run(
        cmd,
        cwd=str(repo_root),
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        raise RuntimeError(
            f"legacy-scan failed (exit {result.returncode}): {result.stderr.strip()}"
        )
    try:
        return json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"Failed to parse legacy-scan JSON: {exc}") from exc


def format_report(
    first_party: list[dict[str, Any]],
    submodule: list[dict[str, Any]],
    scan_data: dict[str, Any],
) -> str:
    """Build a concise human-readable report of legacy-scan results."""
    lines = [
        "modern-web-guidance legacy-scan summary:",
        f"  Rules active: {scan_data.get('activeRuleCount', 'unknown')} "
        f"(guides: {scan_data.get('activeGuideCount', 'unknown')})",
        f"  First-party findings: {len(first_party)}",
        f"  Submodule findings (themes/PaperMod/): {len(submodule)}",
    ]

    if first_party:
        lines.append("\nFirst-party findings (MUST be 0):")
        for item in first_party:
            guide = item.get("guideId") or item.get("guide") or "unknown"
            rule = item.get("ruleId") or item.get("rule") or ""
            loc = f"{item.get('relativeFile')}:{item.get('line', '?')}"
            msg = item.get("message") or item.get("snippet") or ""
            lines.append(f"  - [{guide}/{rule}] {loc} — {msg}".strip())

    if submodule:
        lines.append("\nSubmodule findings (read-only themes/PaperMod/):")
        for item in submodule:
            guide = item.get("guideId") or item.get("guide") or "unknown"
            loc = f"{item.get('relativeFile')}:{item.get('line', '?')}"
            lines.append(f"  - [{guide}] {loc}")

    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    """CLI entrypoint for scripts/check_modern_web.py."""
    parser = argparse.ArgumentParser(
        description="Run modern-web-guidance legacy-scan and fail on first-party issues."
    )
    parser.add_argument(
        "--offline",
        action="store_true",
        help="Pass --offline to npx when running in offline environments.",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Emit partitioned findings as JSON.",
    )
    args = parser.parse_args(argv)

    scan_data = run_legacy_scan(REPO_ROOT, offline=args.offline)
    findings = extract_findings(scan_data)
    first_party, submodule = partition_findings(findings, REPO_ROOT)

    if args.json:
        print(
            json.dumps(
                {
                    "firstPartyCount": len(first_party),
                    "submoduleCount": len(submodule),
                    "firstParty": first_party,
                    "submodule": submodule,
                },
                indent=2,
            )
        )
    else:
        print(format_report(first_party, submodule, scan_data))

    return 1 if first_party else 0


if __name__ == "__main__":
    sys.exit(main())
