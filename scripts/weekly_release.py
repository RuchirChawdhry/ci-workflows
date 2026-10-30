"""Build exact weekly release bundles and compare distributable Git trees.

No network calls, releases or tags are created by this script. GitHub Actions
controls when (and whether) the validated bundle is published.
"""
from __future__ import annotations

import argparse
import hashlib
import re
import subprocess
import zipfile
from datetime import date
from pathlib import Path

INCLUDED = (".github/workflows", "actions", "assets", "README.md", "LICENSE")
TAG_PATTERN = re.compile(r"weekly-(\d{4}-\d{2}-\d{2})\Z")


def git(repo: Path, *args: str, check: bool = True) -> subprocess.CompletedProcess:
    result = subprocess.run(
        ["git", *args], cwd=repo, capture_output=True, text=True, check=False
    )
    if check and result.returncode:
        raise RuntimeError(f"git {' '.join(args)}: {result.stderr.strip()}")
    return result


def has_changes(repo: Path, previous: str, head: str = "HEAD") -> bool:
    """Compare delivered paths against the previous successful release tag."""
    parent = git(repo, "merge-base", "--is-ancestor", previous, head, check=False)
    if parent.returncode != 0:
        raise ValueError("Previous release must be an ancestor of the current commit")
    result = git(
        repo, "diff", "--quiet", "--exit-code", previous, head, "--", *INCLUDED,
        check=False,
    )
    if result.returncode not in (0, 1):
        raise RuntimeError(f"git diff failed: {result.stderr.strip()}")
    return result.returncode == 1


def make_bundle(
    repo: Path, ref: str, tag: str, output_dir: Path
) -> tuple[Path, Path]:
    """Archive exactly the five requested paths from a Git commit."""
    matched = TAG_PATTERN.fullmatch(tag)
    if not matched:
        raise ValueError("Expected a weekly-YYYY-MM-DD release tag")
    try:
        date.fromisoformat(matched.group(1))
    except ValueError as exc:
        raise ValueError("Release tag must contain a valid date") from exc

    repo, output_dir = Path(repo), Path(output_dir)
    expected: set[str] = set()
    for path in INCLUDED:
        result = git(repo, "ls-tree", "-r", "--name-only", ref, "--", path)
        names = {line for line in result.stdout.splitlines() if line}
        if not names:
            raise ValueError(f"Missing required distributable content: {path}")
        expected.update(names)

    output_dir.mkdir(parents=True, exist_ok=True)
    archive = output_dir / f"ci-workflows-{tag}.zip"
    checksum = output_dir / "SHA256SUMS.txt"
    git(repo, "archive", "--format=zip", f"--output={archive.resolve()}", ref, *INCLUDED)
    with zipfile.ZipFile(archive) as package:
        present = {item.filename for item in package.infolist() if not item.is_dir()}
        if present != expected:
            raise RuntimeError(
                f"Archive content mismatch: missing={expected - present}, "
                f"extra={present - expected}"
            )
        if damaged := package.testzip():
            raise RuntimeError(f"Archive integrity check failed: {damaged}")

    with archive.open("rb") as stream:
        digest = hashlib.file_digest(stream, "sha256").hexdigest()
    checksum.write_text(f"{digest}  {archive.name}\n", encoding="utf-8")
    return archive, checksum


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", type=Path, default=Path("."))
    commands = parser.add_subparsers(dest="command", required=True)

    changed = commands.add_parser("changed", help="Compare distributable paths")
    changed.add_argument("--previous", required=True)
    changed.add_argument("--ref", default="HEAD")
    changed.add_argument("--github-output", type=Path)

    build = commands.add_parser("build", help="Create verified release ZIP")
    build.add_argument("--tag", required=True)
    build.add_argument("--ref", default="HEAD")
    build.add_argument("--output-dir", type=Path, default=Path("dist/weekly"))

    args = parser.parse_args()
    if args.command == "changed":
        result = has_changes(args.repo, args.previous, args.ref)
        print(f"Distributable changes since {args.previous}: {result}")
        if args.github_output:
            with args.github_output.open("a", encoding="utf-8") as stream:
                stream.write(f"changed={str(result).lower()}\n")
    else:
        archive, checksum = make_bundle(
            args.repo, args.ref, args.tag, args.output_dir
        )
        print(f"Verified archive: {archive}")
        print(f"SHA-256 checksum: {checksum}")


if __name__ == "__main__":
    main()
