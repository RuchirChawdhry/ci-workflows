"""Test weekly release decisions and exact, verifiable archive contents."""
from __future__ import annotations

import hashlib
import importlib.util
import subprocess
import zipfile
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[1]


def load_script():
    script = ROOT / "scripts/weekly_release.py"
    spec = importlib.util.spec_from_file_location("weekly_release", script)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def git(repo, *args):
    return subprocess.run(
        ["git", *args], cwd=repo, text=True, check=True, capture_output=True
    ).stdout.strip()


def repository(tmp_path):
    git(tmp_path, "init", "-q")
    git(tmp_path, "config", "user.email", "test@example.invalid")
    git(tmp_path, "config", "user.name", "Contract Tests")
    files = {
        ".github/workflows/sample.yml": "name: Sample\n",
        "actions/sample/action.yml": "name: Sample\n",
        "actions/sample/run.py": "print('sample')\n",
        "assets/logo.svg": "<svg></svg>\n",
        "README.md": "# Hello\n",
        "LICENSE": "MIT\n",
        "tests/test_example.py": "assert True\n",
        "website/index.html": "Hello\n",
    }
    for name, body in files.items():
        path = tmp_path / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(body)
    git(tmp_path, "add", ".")
    git(tmp_path, "commit", "-qm", "first")
    git(tmp_path, "tag", "weekly-2026-10-25")
    return files


def test_release_workflow_schedule_and_security():
    file = ROOT / ".github/workflows/weekly-release.yml"
    workflow = yaml.load(file.read_text(), Loader=yaml.BaseLoader)
    assert workflow["on"]["schedule"][0]["cron"] == "30 3 * * 0"
    assert "workflow_dispatch" in workflow["on"]
    assert workflow["permissions"] == {"contents": "read"}
    job = workflow["jobs"]["release"]
    assert job["runs-on"] == "ubuntu-slim"
    assert job["permissions"]["contents"] == "write"
    assert job["if"] == "github.ref == 'refs/heads/main'"
    assert int(job["timeout-minutes"]) <= 14
    steps = job["steps"]
    assert any("fetch-depth" in s.get("with", {}) and str(s["with"]["fetch-depth"]) == "0" for s in steps)
    scripts = "\n".join(s.get("run", "") for s in steps)
    assert "gh release create" in scripts
    assert "scripts/weekly_release.py" in scripts
    assert "weekly-$(date -u +%F)" in scripts
    assert "gh release view" in scripts
    assert "gh release list" in scripts


def test_bundle_file_selection_is_exact(tmp_path):
    mod = load_script()
    repository(tmp_path)
    assert mod.INCLUDED == (
        ".github/workflows", "actions", "assets", "README.md", "LICENSE"
    )
    archive, checksum = mod.make_bundle(tmp_path, "HEAD", "weekly-2026-11-01", tmp_path / "dist")
    assert archive.name == "ci-workflows-weekly-2026-11-01.zip"
    assert checksum.name == "SHA256SUMS.txt"
    with zipfile.ZipFile(archive) as z:
        names = {i.filename for i in z.infolist() if not i.is_dir()}
        assert names == {
            ".github/workflows/sample.yml",
            "actions/sample/action.yml",
            "actions/sample/run.py",
            "assets/logo.svg",
            "README.md", "LICENSE",
        }
        assert z.read("README.md") == b"# Hello\n"
    digest = hashlib.sha256(archive.read_bytes()).hexdigest()
    assert checksum.read_text().strip() == f"{digest}  {archive.name}"


def test_only_distributable_changes_trigger_release(tmp_path):
    mod = load_script()
    files = repository(tmp_path)
    base = "weekly-2026-10-25"
    assert not mod.has_changes(tmp_path, base, "HEAD")

    (tmp_path / "tests/test_example.py").write_text("assert False\n")
    (tmp_path / "website/index.html").write_text("Changed\n")
    git(tmp_path, "add", ".")
    git(tmp_path, "commit", "-qm", "tests and website")
    assert not mod.has_changes(tmp_path, base, "HEAD")

    (tmp_path / "assets/logo.svg").write_text("<svg>new</svg>\n")
    git(tmp_path, "add", ".")
    git(tmp_path, "commit", "-qm", "new logo")
    assert mod.has_changes(tmp_path, base, "HEAD")

    (tmp_path / "assets/logo.svg").write_text(files["assets/logo.svg"])
    git(tmp_path, "add", ".")
    git(tmp_path, "commit", "-qm", "revert logo")
    assert not mod.has_changes(tmp_path, base, "HEAD")

    (tmp_path / ".github/workflows/sample.yml").write_text("name: Updated\n")
    git(tmp_path, "add", ".")
    git(tmp_path, "commit", "-qm", "workflow changed")
    assert mod.has_changes(tmp_path, base, "HEAD")


def test_rejects_missing_paths_and_invalid_snapshot_tag(tmp_path):
    mod = load_script()
    repository(tmp_path)
    with pytest.raises(ValueError, match="weekly"):
        mod.make_bundle(tmp_path, "HEAD", "v1.0.0", tmp_path / "dist")
    (tmp_path / "LICENSE").unlink()
    git(tmp_path, "add", "-A")
    git(tmp_path, "commit", "-qm", "remove license")
    with pytest.raises(ValueError, match="LICENSE"):
        mod.make_bundle(tmp_path, "HEAD", "weekly-2026-11-01", tmp_path / "dist")


def test_previous_release_must_be_ancestor(tmp_path):
    mod = load_script()
    repository(tmp_path)
    assert not mod.has_changes(tmp_path, "weekly-2026-10-25", "HEAD")
    with pytest.raises(ValueError, match="ancestor"):
        mod.has_changes(tmp_path, "HEAD", "weekly-2026-10-25")

def test_smoke_workflow_only_builds_not_publishes():
    wf = yaml.load(
        (ROOT / ".github/workflows/weekly-release-smoke.yml").read_text(),
        Loader=yaml.BaseLoader,
    )
    assert "pull_request" in wf["on"]
    assert wf["permissions"] == {"contents": "read"}
    steps = wf["jobs"]["archive"]["steps"]
    script = "\n".join(step.get("run", "") for step in steps)
    assert "scripts/weekly_release.py" in script
    assert "sha256sum --check SHA256SUMS.txt" in script
    assert "gh release create" not in script
    assert any("actions/upload-artifact@" in step.get("uses", "") for step in steps)
