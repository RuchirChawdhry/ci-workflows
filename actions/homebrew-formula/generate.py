"""Generate a personal-tap formula from exact release-archive bytes."""
from __future__ import annotations
import argparse
import hashlib
import json
import re
import tarfile
from pathlib import Path
from urllib.parse import urlsplit

APP = re.compile(r"[a-z][a-z0-9-]{0,63}\Z")
VERSION = re.compile(r"(?:0|[1-9]\d*)\.(?:0|[1-9]\d*)\.(?:0|[1-9]\d*)(?:[-.+][A-Za-z0-9.-]+)?\Z")
BINARY = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.-]*\Z")
LICENSE = re.compile(r"[A-Za-z0-9][A-Za-z0-9.+-]*\Z")
ARCH = {"x86_64", "arm64"}

def check_https(url: str, suffix: str | None = None) -> None:
    parsed = urlsplit(url)
    if parsed.scheme != "https" or not parsed.hostname or parsed.username or parsed.password or parsed.fragment:
        raise ValueError("URL must use HTTPS without credentials or fragments")
    if suffix and not parsed.path.endswith("/" + suffix):
        raise ValueError("release URL must end with the exact archive filename")

def generate_formula(*, archive: Path, output: Path, app_name: str, version: str,
                     release_url: str, description: str, homepage: str, license_name: str,
                     binary_name: str, architecture: str) -> Path:
    archive, output = Path(archive), Path(output)
    if not APP.fullmatch(app_name):
        raise ValueError("app-name must use lowercase letters, digits, and hyphens")
    if not VERSION.fullmatch(version):
        raise ValueError("version must be numeric dotted semver")
    if not BINARY.fullmatch(binary_name) or binary_name.startswith("-"):
        raise ValueError("binary-name must be a safe filename")
    if architecture not in ARCH:
        raise ValueError("architecture must be x86_64 or arm64")
    if license_name and not LICENSE.fullmatch(license_name):
        raise ValueError("license-name must be an SPDX identifier")
    if not archive.is_file() or archive.stat().st_size == 0 or not archive.name.endswith(".tar.gz"):
        raise ValueError("non-empty .tar.gz archive required")
    check_https(release_url, archive.name)
    check_https(homepage)
    if not description.strip():
        raise ValueError("description is required")
    with tarfile.open(archive, "r:gz") as tar:
        members = tar.getmembers()
        if len(members) != 1 or members[0].name != binary_name or not members[0].isfile():
            raise ValueError("archive must contain exactly one executable at its root")
        if not members[0].mode & 0o111 or members[0].size == 0:
            raise ValueError("archive member must be nonempty and executable")
    with archive.open("rb") as stream:
        sha = hashlib.file_digest(stream, "sha256").hexdigest()
    klass = "".join(word.capitalize() for word in app_name.split("-"))
    license_value = json.dumps(license_name) if license_name else ":cannot_represent"
    formula = (
        f"class {klass} < Formula\n"
        f"  desc {json.dumps(description)}\n"
        f"  homepage {json.dumps(homepage)}\n"
        f"  url {json.dumps(release_url)}\n"
        f"  version {json.dumps(version)}\n"
        f"  sha256 {json.dumps(sha)}\n"
        f"  license {license_value}\n\n"
        f"  depends_on :macos\n"
        f"  depends_on arch: :{architecture}\n\n"
        f"  def install\n"
        f"    bin.install {json.dumps(binary_name)}\n"
        f"  end\n\n"
        f"  test do\n"
        f'    system "#{{bin}}/{binary_name}", "--help"\n'
        f"  end\nend\n"
    )
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(formula, encoding="utf-8")
    return output

def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    for name in ("archive","output","app-name","version","release-url","homepage","description"):
        p.add_argument("--" + name, required=True)
    for name in ("license","binary-name"):
        p.add_argument("--" + name, default="")
    p.add_argument("--architecture", choices=sorted(ARCH), default="x86_64")
    a = p.parse_args()
    print(generate_formula(archive=Path(a.archive), output=Path(a.output),
        app_name=a.app_name, version=a.version, release_url=a.release_url,
        description=a.description, homepage=a.homepage, license_name=a.license,
        binary_name=a.binary_name or a.app_name, architecture=a.architecture))

if __name__ == "__main__":
    main()
