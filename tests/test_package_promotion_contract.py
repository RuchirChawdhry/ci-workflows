"""Contracts for release-to-personal-bucket/tap promotion."""
from __future__ import annotations

import importlib.util
import io
import json
import tarfile
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[1]


def module():
    path = ROOT / "actions/package-promotion/promote.py"
    spec = importlib.util.spec_from_file_location("package_promotion", path)
    item = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(item)
    return item


def archive(path):
    with tarfile.open(path, "w:gz") as tar:
        body = b"#!/bin/sh\necho Hello\n"
        info = tarfile.TarInfo("demo")
        info.mode = 0o755
        info.size = len(body)
        tar.addfile(info, io.BytesIO(body))


def sample(platform):
    filename = "demo.exe" if platform == "scoop" else "demo-macos-x64.tar.gz"
    return {"schema": 1, "packages": [{
        "name": "demo", "repository": "example/demo", "asset": filename,
        "binary": "demo.exe" if platform == "scoop" else "demo",
        "description": "Demo CLI", "homepage": "https://github.com/example/demo",
        "license": "MIT", **({"architecture": "x86_64"} if platform == "homebrew" else {})
    }]}


def test_workflow_reusable_and_permission_scoped():
    wf = yaml.load(
        (ROOT / ".github/workflows/package-promotion.yml").read_text(),
        Loader=yaml.BaseLoader
    )
    assert wf["on"]["workflow_call"]["inputs"]["ecosystem"]["required"] == "true"
    job = wf["jobs"]["promote"]
    assert job["permissions"] == {"contents": "write", "pull-requests": "write"}
    assert job["runs-on"] == "ubuntu-latest"
    steps = job["steps"]
    assert any(s.get("uses") == "$/actions/package-promotion" for s in steps)
    commands = "\n".join(s.get("run", "") for s in steps)
    assert "gh pr create" in commands
    assert "gh pr list" in commands
    assert "git push" in commands
    assert "git diff --cached --quiet" in commands


@pytest.mark.parametrize("ecosystem", ["scoop", "homebrew"])
def test_generate_from_public_release_and_skip_identical(tmp_path, ecosystem):
    mod = module()
    package = sample(ecosystem)
    binary = tmp_path / package["packages"][0]["asset"]
    if ecosystem == "scoop":
        binary.write_bytes(b"MZtest-executable")
    else:
        archive(binary)
    url = f"https://github.com/example/demo/releases/download/v1.2.3/{binary.name}"
    calls = []

    def resolver(repo):
        calls.append(repo)
        return {"tag_name": "v1.2.3", "draft": False, "prerelease": False,
                "assets": [{"name": binary.name, "browser_download_url": url}]}

    def downloader(expected, destination):
        assert expected == url
        destination.write_bytes(binary.read_bytes())

    paths = mod.promote(package, ecosystem, tmp_path / "target", resolver, downloader)
    assert calls == ["example/demo"]
    assert len(paths) == 1
    generated = paths[0]
    assert generated.name == ("demo.json" if ecosystem == "scoop" else "demo.rb")
    body = generated.read_text()
    assert "1.2.3" in body
    assert url in body
    if ecosystem == "scoop":
        assert json.loads(body)["bin"] == "demo.exe"
    else:
        assert "class Demo < Formula" in body
    assert mod.promote(package, ecosystem, tmp_path / "target", resolver, downloader) == []


@pytest.mark.parametrize("bad", [
    {"repository": "bad../other"},
    {"asset": "../private"},
    {"name": "../../escape"},
    {"homepage": "http://insecure"},
])
def test_rejects_bad_catalog_without_writes(tmp_path, bad):
    mod = module()
    packages = sample("scoop")
    packages["packages"][0].update(bad)
    with pytest.raises(ValueError):
        mod.promote(packages, "scoop", tmp_path,
                    lambda repo: (_ for _ in ()).throw(AssertionError("network called")),
                    lambda url, output: None)
    assert not (tmp_path / "bucket").exists()


def test_rejects_unpublished_and_wrong_release_assets(tmp_path):
    mod = module()
    for response in [
        {"tag_name": "v1.2.3", "draft": False, "prerelease": False, "assets": []},
        {"tag_name": "v1.2.3", "draft": True, "prerelease": False, "assets": []},
        {"tag_name": "not-a-version", "draft": False, "prerelease": False, "assets": []},
    ]:
        with pytest.raises(ValueError):
            mod.promote(sample("scoop"), "scoop", tmp_path,
                        lambda repo: response, lambda url, output: None)


def test_action_uses_only_public_release_artifacts():
    action = yaml.load(
        (ROOT / "actions/package-promotion/action.yml").read_text(),
        Loader=yaml.BaseLoader
    )
    assert action["runs"]["using"] == "composite"
    assert all(step.get("shell") == "bash" for step in action["runs"]["steps"] if "run" in step)
    body = (ROOT / "actions/package-promotion/promote.py").read_text()
    assert "api.github.com/repos" in body
    assert "/releases/latest" in body
    assert "browser_download_url" in body
    assert "https://github.com/" in body
