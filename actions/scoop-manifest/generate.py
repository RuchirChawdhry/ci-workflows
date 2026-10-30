"""Generate a portable Windows exe Scoop manifest from the exact tested bytes."""
from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path
from urllib.parse import urlsplit

APP_RE = re.compile(r"^[a-z][a-z0-9-]{0,63}$")
VERSION_RE = re.compile(r"^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)(?:[-.+][a-zA-Z0-9.-]+)?$")
BIN_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]*\.exe$", re.I)

def generate_manifest(*, asset: Path, output: Path, app_name: str, version: str,
                      release_url: str, description: str, homepage: str,
                      license_name: str, binary_name: str) -> Path:
    asset, output = Path(asset), Path(output)
    if not APP_RE.fullmatch(app_name):
        raise ValueError("app-name must be lowercase alphanumeric/hyphen")
    if not VERSION_RE.fullmatch(version):
        raise ValueError("version must be numeric dotted semver")
    if not BIN_RE.fullmatch(binary_name):
        raise ValueError("binary-name must be one .exe filename")
    if not asset.is_file() or asset.stat().st_size == 0:
        raise ValueError(f"missing or empty release asset: {asset}")
    if asset.suffix.lower() != ".exe":
        raise ValueError("first implementation supports portable .exe assets only")
    url = urlsplit(release_url)
    if url.scheme != "https" or not url.netloc or url.username or url.password or url.fragment:
        raise ValueError("release-url must be HTTPS without credentials or fragments")
    if not url.path.endswith("/" + asset.name):
        raise ValueError("release URL must end with exact asset filename")
    homepage_url = urlsplit(homepage)
    if homepage and (homepage_url.scheme != "https" or not homepage_url.netloc):
        raise ValueError("homepage must use HTTPS")

    with asset.open("rb") as stream:
        sha256 = hashlib.file_digest(stream, "sha256").hexdigest()
    manifest = {"version": version, "description": description, "url": release_url,
                "hash": sha256, "bin": binary_name}
    if homepage:
        manifest["homepage"] = homepage
    if license_name:
        manifest["license"] = license_name
    release_part = f"/v{version}/"
    if release_part in release_url:
        manifest["autoupdate"] = {"url": release_url.replace(release_part, "/v$version/", 1)}
    elif f"/{version}/" in release_url:
        manifest["autoupdate"] = {"url": release_url.replace(f"/{version}/", "/$version/", 1)}
    if homepage_url.hostname and homepage_url.hostname.lower() == "github.com" and re.fullmatch(r"/[^/]+/[^/]+/?", homepage_url.path):
        manifest["checkver"] = {"github": homepage.rstrip("/")}
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return output

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for key in ("asset", "output", "app-name", "version", "release-url"):
        parser.add_argument("--" + key, required=True)
    for key in ("description", "homepage", "license", "binary-name"):
        parser.add_argument("--" + key, default="")
    args = parser.parse_args()
    asset = Path(args.asset)
    result = generate_manifest(asset=asset, output=Path(args.output),
        app_name=args.app_name, version=args.version, release_url=args.release_url,
        description=args.description, homepage=args.homepage,
        license_name=args.license, binary_name=args.binary_name or asset.name)
    print(result)

if __name__ == "__main__":
    main()
