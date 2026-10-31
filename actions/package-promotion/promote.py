"""Promote public GitHub Release assets to a personal Scoop bucket or Homebrew tap.

No pushes or pull requests are performed here; the reusable workflow owns those
operations and keeps the package repositories as the only mutation targets.
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import re
import shutil
import tempfile
from pathlib import Path
from urllib.request import Request, urlopen

REPOSITORY = re.compile(r"(?!.*\.\.)[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+\Z")
NAME = re.compile(r"[a-z][a-z0-9-]{0,63}\Z")
FILE = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.-]+\Z")
VERSION = re.compile(r"(?:0|[1-9]\d*)\.(?:0|[1-9]\d*)\.(?:0|[1-9]\d*)(?:[-.+][A-Za-z0-9.-]+)?\Z")
MAX_BYTES = 200 * 1024 * 1024


def _module(relative: str):
    script = Path(__file__).resolve().parents[1] / relative
    spec = importlib.util.spec_from_file_location(script.stem, script)
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


def latest_release(repository: str) -> dict:
    url = f"https://api.github.com/repos/{repository}/releases/latest"
    request = Request(url, headers={
        "Accept": "application/vnd.github+json",
        "User-Agent": "ci-workflows-personal-package-promotion",
        "X-GitHub-Api-Version": "2022-11-28",
    })
    with urlopen(request, timeout=25) as response:
        return json.load(response)


def download_release_asset(url: str, destination: Path) -> None:
    request = Request(url, headers={"User-Agent": "ci-workflows-package-promotion"})
    with urlopen(request, timeout=90) as response, destination.open("wb") as output:
        total = 0
        while chunk := response.read(1024 * 1024):
            total += len(chunk)
            if total > MAX_BYTES:
                raise ValueError("Release asset exceeds 200 MiB safety limit")
            output.write(chunk)
    if not destination.stat().st_size:
        raise ValueError("Release asset is empty")


def validate_catalog(catalog: dict, ecosystem: str) -> list[dict]:
    if ecosystem not in ("scoop", "homebrew"):
        raise ValueError("ecosystem must be scoop or homebrew")
    if set(catalog) != {"schema", "packages"} or catalog["schema"] != 1:
        raise ValueError("Expected schema 1 package catalog")
    items = catalog["packages"]
    if not isinstance(items, list):
        raise ValueError("Catalog packages must be a list")
    names = set()
    for item in items:
        if not isinstance(item, dict):
            raise ValueError("Catalog package must be an object")
        required = ("name", "repository", "asset", "binary", "description", "homepage", "license")
        if any(not isinstance(item.get(key), str) for key in required):
            raise ValueError("Package metadata must contain string fields")
        name, repo, asset = item["name"], item["repository"], item["asset"]
        if not NAME.fullmatch(name) or name in names:
            raise ValueError("Invalid or duplicate package name")
        names.add(name)
        if not REPOSITORY.fullmatch(repo):
            raise ValueError("Invalid GitHub repository identifier")
        if not FILE.fullmatch(asset) or not FILE.fullmatch(item["binary"]):
            raise ValueError("Invalid asset or binary filename")
        if not item["homepage"].startswith("https://github.com/"):
            raise ValueError("Package homepage must use HTTPS GitHub")
        if not item["description"].strip():
            raise ValueError("Package description is required")
        if ecosystem == "scoop":
            if not asset.lower().endswith(".exe"):
                raise ValueError("Scoop promotion currently supports portable .exe")
        else:
            if not asset.endswith(".tar.gz"):
                raise ValueError("Homebrew promotion currently supports .tar.gz")
            if item.get("architecture") not in ("x86_64", "arm64"):
                raise ValueError("Homebrew architecture must be x86_64 or arm64")
    return items


def promote(catalog: dict, ecosystem: str, root: Path,
            resolver=latest_release, downloader=download_release_asset) -> list[Path]:
    """Return files actually changed; safely reject invalid catalogs before downloads."""
    packages = validate_catalog(catalog, ecosystem)
    root = Path(root)
    updated = []
    for item in packages:
        release = resolver(item["repository"])
        tag = release.get("tag_name", "")
        version = tag[1:] if tag.startswith("v") else tag
        if release.get("draft") or release.get("prerelease") or not VERSION.fullmatch(version):
            raise ValueError(f"Invalid stable release for {item['repository']}: {tag}")
        matching = [a for a in release.get("assets", []) if a.get("name") == item["asset"]]
        if len(matching) != 1:
            raise ValueError(f"Required release asset missing: {item['repository']} / {item['asset']}")
        url = matching[0].get("browser_download_url", "")
        expected = (f"https://github.com/{item['repository']}/releases/download/"
                    f"{tag}/{item['asset']}")
        if url != expected:
            raise ValueError(f"Unexpected or untrusted release asset URL: {url}")

        extension = "json" if ecosystem == "scoop" else "rb"
        folder = "bucket" if ecosystem == "scoop" else "Formula"
        target = root / folder / f"{item['name']}.{extension}"
        with tempfile.TemporaryDirectory(prefix="package-promotion-") as temp:
            staging = Path(temp)
            asset = staging / item["asset"]
            downloader(url, asset)
            candidate = staging / f"{item['name']}.{extension}"
            if ecosystem == "scoop":
                _module("scoop-manifest/generate.py").generate_manifest(
                    asset=asset, output=candidate,
                    app_name=item["name"], version=version,
                    release_url=url, description=item["description"],
                    homepage=item["homepage"], license_name=item["license"],
                    binary_name=item["binary"],
                )
            else:
                _module("homebrew-formula/generate.py").generate_formula(
                    archive=asset, output=candidate,
                    app_name=item["name"], version=version,
                    release_url=url, description=item["description"],
                    homepage=item["homepage"], license_name=item["license"],
                    binary_name=item["binary"],
                    architecture=item["architecture"],
                )
            new_content = candidate.read_bytes()
            if target.is_file() and target.read_bytes() == new_content:
                continue
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(candidate, target)
            updated.append(target)
            print(f"Prepared {target}: {version}")
    return updated


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--catalog", required=True, type=Path)
    parser.add_argument("--ecosystem", choices=("scoop", "homebrew"), required=True)
    parser.add_argument("--root", default=".", type=Path)
    parser.add_argument("--github-output", type=Path)
    args = parser.parse_args()
    catalog = json.loads(args.catalog.read_text(encoding="utf-8"))
    result = promote(catalog, args.ecosystem, args.root)
    print(f"Proposed {len(result)} package update(s)")
    if args.github_output:
        with args.github_output.open("a", encoding="utf-8") as output:
            output.write(f"changed={str(bool(result)).lower()}\n")
            output.write(f"updated-count={len(result)}\n")


if __name__ == "__main__":
    main()
