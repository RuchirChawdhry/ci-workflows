"""Contracts for Scoop workflow and reusable actions."""
from pathlib import Path
import importlib.util
import hashlib
import json
import pytest
import yaml

ROOT = Path(__file__).resolve().parents[1]

def parse(path):
    return yaml.load((ROOT / path).read_text(), Loader=yaml.BaseLoader)

def module(path):
    file = ROOT / path
    spec = importlib.util.spec_from_file_location(file.stem, file)
    obj = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(obj)
    return obj

def test_scoop_workflow_contract():
    wf = parse(".github/workflows/scoop-ci.yml")
    inputs = wf["on"]["workflow_call"]["inputs"]
    for name in ("artifact-name", "asset-path", "app-name", "version", "release-url"):
        assert inputs[name]["required"] == "true"
    assert wf["permissions"] == {"contents": "read"}
    job = wf["jobs"]["validate"]
    assert job["runs-on"] == "windows-2025"
    assert any("actions/download-artifact@" in s.get("uses", "") for s in job["steps"])
    assert any(s.get("uses") == "$/actions/scoop-manifest" for s in job["steps"])
    assert any(s.get("uses") == "$/actions/scoop-test" for s in job["steps"])
    assert any("actions/upload-artifact@" in s.get("uses", "") for s in job["steps"])

def test_actions_are_composite_and_uv_only():
    for name in ("scoop-manifest", "scoop-test"):
        action = parse(f"actions/{name}/action.yml")
        assert action["runs"]["using"] == "composite"
        steps = action["runs"]["steps"]
        assert any("astral-sh/setup-uv@" in s.get("uses", "") for s in steps)
        assert any("uv run --no-project --python 3.14.7" in s.get("run", "") for s in steps)

def test_manifest_hash_metadata_and_rejection(tmp_path):
    generator = module("actions/scoop-manifest/generate.py")
    exe = tmp_path / "markbox.exe"
    exe.write_bytes(b"MZfixture")
    data = dict(asset=exe, output=tmp_path / "markbox.json", app_name="markbox",
        version="1.2.3", release_url="https://github.com/example/cli/releases/download/v1.2.3/markbox.exe",
        description="Demo", homepage="https://github.com/example/cli", license_name="MIT",
        binary_name="markbox.exe")
    result = generator.generate_manifest(**data)
    manifest = json.loads(result.read_text())
    assert manifest["hash"] == hashlib.sha256(exe.read_bytes()).hexdigest()
    assert manifest["url"] == data["release_url"]
    assert manifest["bin"] == "markbox.exe"
    assert manifest["checkver"]["github"] == data["homepage"]
    assert "$version" in manifest["autoupdate"]["url"]
    for key, value in (("app_name", "../unsafe"), ("release_url", "http://invalid/a.exe"),
                       ("version", "bad"), ("binary_name", "../../unsafe.exe")):
        with pytest.raises(ValueError):
            generator.generate_manifest(**{**data, key: value})
    exe.write_bytes(b"")
    with pytest.raises(ValueError):
        generator.generate_manifest(**data)

def test_local_install_does_not_mutate_remote_manifest(tmp_path):
    generator = module("actions/scoop-manifest/generate.py")
    smoke = module("actions/scoop-test/smoke.py")
    exe = tmp_path / "markbox.exe"
    exe.write_bytes(b"MZfixture")
    path = generator.generate_manifest(asset=exe, output=tmp_path / "markbox.json",
        app_name="markbox", version="1.2.3",
        release_url="https://github.com/example/cli/releases/download/v1.2.3/markbox.exe",
        description="Demo", homepage="", license_name="", binary_name="markbox.exe")
    local = smoke.prepare_local_manifest(path, exe, tmp_path / "stage", "http://127.0.0.1:3131")
    original, tested = json.loads(path.read_text()), json.loads(local.read_text())
    assert tested["hash"] == original["hash"]
    assert tested["url"] == "http://127.0.0.1:3131/markbox.exe"
    assert original["url"].startswith("https://")
