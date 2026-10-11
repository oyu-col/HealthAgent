"""Validate local delivery links, phase sections, and the read-only reference baseline."""

import hashlib
import json
import re
from pathlib import Path
from urllib.parse import unquote, urlsplit


def main():
    root = Path(__file__).resolve().parents[2]
    snapshot = json.loads((root / "docs/reference-snapshot.json").read_text(encoding="utf-8"))
    reference = Path(snapshot["reference_root"])
    changed = []
    for entry in snapshot["files"]:
        path = reference / entry["path"]
        if not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest() != entry["sha256"]:
            changed.append(entry["path"])
    benchmark_reference = json.loads(
        (root / "docs/phase-11-12-deerflow-reference.json").read_text(encoding="utf-8")
    )
    for entry in benchmark_reference["files"]:
        path = reference / entry["path"]
        if not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest() != entry["sha256"]:
            changed.append(entry["path"])
    links = 0
    broken = []
    markdown = [
        root / "README.md",
        root / "AGENTS.md",
        root / "benchmark/README.md",
        root / "benchmark/results/README.md",
        *sorted((root / "docs").glob("*.md")),
    ]
    for path in markdown:
        for target in re.findall(r"\[[^\]]*\]\(([^)]+)\)", path.read_text(encoding="utf-8")):
            target = target.strip("<>")
            if urlsplit(target).scheme or target.startswith("#"):
                continue
            target = unquote(target.split("#")[0])
            links += 1
            if not (path.parent / target).exists():
                broken.append({"file": str(path.relative_to(root)), "target": target})
    sections = (
        "Completed",
        "Files Changed",
        "Design",
        "DeerFlow Reference",
        "Tests",
        "Known Issues",
        "Next Phase",
    )
    missing = []
    for phase in range(13):
        path = root / f"docs/phase-{phase}-delivery.md"
        content = path.read_text(encoding="utf-8") if path.is_file() else ""
        missing.extend(
            f"Phase {phase}: {section}" for section in sections if f"## {section}" not in content
        )
    identical = (root / "HEALTH_AGENT_SPEC.md").read_bytes() == (
        reference / "HEALTH_AGENT_SPEC.md"
    ).read_bytes()
    report = {
        "reference_files_checked": len(snapshot["files"]) + len(benchmark_reference["files"]),
        "delivery_phases_checked": 13,
        "reference_files_changed": changed,
        "spec_byte_identical": identical,
        "local_markdown_links": links,
        "broken_links": broken,
        "missing_delivery_sections": missing,
    }
    print(json.dumps(report, ensure_ascii=False))
    if changed or not identical or broken or missing:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
