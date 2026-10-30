"""Consolidate version-specific JSON evidence into a readable Actions summary."""
import argparse
import json
from collections import Counter
from pathlib import Path

from packaging.version import Version


def summarize(directory, versions):
    directory = Path(directory)
    results = []
    for version in sorted(set(versions), key=Version):
        file = directory / f"{version}.json"
        try:
            value = json.loads(file.read_text(encoding="utf-8"))
            if value.get("version") != version or not isinstance(value.get("status"), str):
                raise ValueError("Malformed probe result")
        except (OSError, ValueError) as exc:
            value = {"version": version, "status": "INFRA",
                     "failed_stage": "collect",
                     "reason": f"Missing/invalid result: {exc}", "checks": []}
        results.append(value)
    passed = [r["version"] for r in results if r["status"] == "PASS"]
    experimental = [r["version"] for r in results if r["status"] == "EXPERIMENTAL_PASS"]
    return {"results": results,
            "counts": dict(sorted(Counter(r["status"] for r in results).items())),
            "lowest_passing": min(passed, key=Version) if passed else None,
            "lowest_experimental": min(experimental, key=Version) if experimental else None}


def markdown(report):
    lines = ["## 🐍 Python compatibility explorer", "",
             "| Python | Result | Failed stage | Diagnostic |",
             "|---|---|---|---|"]
    for entry in report["results"]:
        diagnostic = str(entry.get("reason", "")).strip().splitlines()
        # The final traceback line contains the exception; the first is only a heading.
        message = diagnostic[-1] if diagnostic and diagnostic[0].startswith("Traceback") else (diagnostic[0] if diagnostic else "")
        reason = message.strip().replace("|", "\\|")[:150]
        lines.append(f"| {entry['version']} | {entry['status']} | {entry.get('failed_stage') or '—'} | {reason} |")
    lines.extend(["",
                  f"**Lowest tested passing version:** {report['lowest_passing'] or 'None'}",
                  f"**Lowest exploratory passing version:** {report.get('lowest_experimental') or 'None'}",
                  "", "EXPERIMENTAL_PASS indicates the package was tested with requires-python relaxed "
                  "only in a disposable copy; it does not certify the original distribution.",
                  "", "Passing is not an official support guarantee. Only the tested interpreter, "
                  "dependencies, operating system, and checks are covered. "
                  "Missing results are INFRA, not incompatibility."])
    return "\n".join(lines) + "\n"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--versions-json", required=True)
    parser.add_argument("--json-output", type=Path, required=True)
    parser.add_argument("--markdown-output", type=Path, required=True)
    args = parser.parse_args()
    versions = json.loads(args.versions_json)
    if (not isinstance(versions, list) or not versions
            or not all(isinstance(v, str) for v in versions)):
        parser.error("versions-json must be a nonempty JSON array of version strings")
    report = summarize(args.input, versions)
    args.json_output.parent.mkdir(parents=True, exist_ok=True)
    args.json_output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    args.markdown_output.write_text(markdown(report), encoding="utf-8")
    print(markdown(report))


if __name__ == "__main__":
    main()
