"""Contracts for reusable personal-tap Homebrew CI."""
from __future__ import annotations
import hashlib
import importlib.util
import io
import tarfile
from pathlib import Path
import pytest
import yaml

ROOT = Path(__file__).resolve().parents[1]

def load_yaml(path):
    return yaml.load((ROOT / path).read_text(), Loader=yaml.BaseLoader)

def load_module(path):
    file = ROOT / path
    spec = importlib.util.spec_from_file_location(file.stem, file)
    obj = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(obj)
    return obj

def make_archive(path, filename="markbox", mode=0o755):
    body = b"#!/bin/sh\necho markbox\n"
    with tarfile.open(path, "w:gz") as tar:
        member = tarfile.TarInfo(filename)
        member.mode = mode
        member.size = len(body)
        tar.addfile(member, io.BytesIO(body))

def options(tmp_path):
    archive = tmp_path / "markbox-macos-x64.tar.gz"
    make_archive(archive)
    return dict(archive=archive, output=tmp_path/"Formula"/"markbox.rb",
        app_name="markbox", version="0.1.0",
        release_url="https://github.com/demo/markbox/releases/download/v0.1.0/markbox-macos-x64.tar.gz",
        description="A CLI demo", homepage="https://github.com/demo/markbox",
        license_name="MIT", binary_name="markbox", architecture="x86_64")

def test_workflow_orchestrates_existing_artifact_read_only():
    wf = load_yaml(".github/workflows/homebrew-ci.yml")
    inputs = wf["on"]["workflow_call"]["inputs"]
    for name in ("artifact-name","archive-path","app-name","version","release-url","homepage"):
        assert inputs[name]["required"] == "true"
    assert inputs["runs-on"]["default"] == "macos-15-intel"
    assert inputs["architecture"]["default"] == "x86_64"
    assert wf["permissions"] == {"contents":"read"}
    job = wf["jobs"]["validate"]
    assert job["runs-on"] == "${{ inputs.runs-on }}"
    steps = job["steps"]
    assert any("actions/download-artifact@" in s.get("uses","") for s in steps)
    assert any(s.get("uses") == "$/actions/homebrew-formula" for s in steps)
    assert any(s.get("uses") == "$/actions/homebrew-test" for s in steps)
    assert any("actions/upload-artifact@" in s.get("uses","") for s in steps)
    assert not any("git push" in s.get("run","") for s in steps)

def test_composite_actions_use_uv_3147():
    for name in ("homebrew-formula","homebrew-test"):
        action = load_yaml(f"actions/{name}/action.yml")
        assert action["runs"]["using"] == "composite"
        assert any("astral-sh/setup-uv@" in s.get("uses","") for s in action["runs"]["steps"])
        assert any("uv run --no-project --python 3.14.7" in s.get("run","") for s in action["runs"]["steps"])

def test_formula_hash_and_installed_test(tmp_path):
    generator = load_module("actions/homebrew-formula/generate.py")
    args = options(tmp_path)
    formula = generator.generate_formula(**args).read_text()
    assert "class Markbox < Formula" in formula
    assert hashlib.sha256(args["archive"].read_bytes()).hexdigest() in formula
    assert args["release_url"] in formula
    assert "depends_on arch: :x86_64" in formula
    assert 'bin.install "markbox"' in formula
    assert 'system "#{bin}/markbox", "--help"' in formula
    assert 'license "MIT"' in formula

def test_generator_rejects_malformed_metadata_and_unsafe_archives(tmp_path):
    generator = load_module("actions/homebrew-formula/generate.py")
    args = options(tmp_path)
    for key,value in (("app_name","../bad"),("version","v0.1"),
                      ("release_url","http://bad/markbox-macos-x64.tar.gz"),
                      ("binary_name","../evil"),("architecture","other"),
                      ("license_name",'MIT"; system("evil")')):
        with pytest.raises(ValueError):
            generator.generate_formula(**{**args,key:value})
    make_archive(args["archive"],filename="../bad")
    with pytest.raises(ValueError,match="exactly one executable"):
        generator.generate_formula(**args)
    make_archive(args["archive"],mode=0o644)
    with pytest.raises(ValueError,match="executable"):
        generator.generate_formula(**args)

def test_local_test_keeps_public_formula_unchanged(tmp_path):
    generator = load_module("actions/homebrew-formula/generate.py")
    smoke = load_module("actions/homebrew-test/smoke.py")
    args = options(tmp_path)
    original = generator.generate_formula(**args)
    prior = original.read_text()
    local = smoke.make_test_formula(original,args["archive"],tmp_path/"stage","http://127.0.0.1:43210")
    data = local.read_text()
    assert "http://127.0.0.1:43210/markbox-macos-x64.tar.gz" in data
    assert hashlib.sha256(args["archive"].read_bytes()).hexdigest() in data
    assert original.read_text() == prior
    with pytest.raises(ValueError,match="checksum"):
        smoke.make_test_formula(original,tmp_path/"missing",tmp_path/"other","http://127.0.0.1:43210")
