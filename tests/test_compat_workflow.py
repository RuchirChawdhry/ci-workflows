"""Contracts for read-only reusable workflow and PR smoke test."""
from pathlib import Path
import yaml
ROOT = Path(__file__).resolve().parents[1]

def load(path):
    return yaml.load((ROOT / path).read_text(), Loader=yaml.BaseLoader)

def test_only_reusable_no_publish_permissions():
    d = load(".github/workflows/python-compat.yml")
    assert "workflow_call" in d["on"] and "push" not in d["on"]
    assert d["permissions"] == {"contents":"read"}
    assert d["jobs"]["probe"]["strategy"]["fail-fast"] == "false"
    assert "fromJSON(inputs.versions-json)" in d["jobs"]["probe"]["strategy"]["matrix"]["python"]

def test_implementation_pinned_to_called_workflow_commit():
    d = load(".github/workflows/python-compat.yml")
    steps = d["jobs"]["probe"]["steps"]
    assert steps[0]["with"]["persist-credentials"] == "false"
    assert steps[1]["with"]["repository"] == "${{ job.workflow_repository }}"
    assert steps[1]["with"]["ref"] == "${{ job.workflow_sha }}"
    assert any("compat_probe.py" in s.get("run","") for s in steps)
    assert any("upload-artifact@" in s.get("uses","") and s.get("if") == "always()" for s in steps)

def test_report_after_any_probe_result():
    d = load(".github/workflows/python-compat.yml")
    job = d["jobs"]["report"]
    assert job["if"] == "always()" and job["needs"] == ["probe"]
    assert any("GITHUB_STEP_SUMMARY" in s.get("run","") for s in job["steps"])

def test_smoke_uses_local_reusable_workflow():
    d = load(".github/workflows/python-compat-smoke.yml")
    assert d["jobs"]["smoke"]["uses"] == "$/.github/workflows/python-compat.yml"
    assert d["jobs"]["smoke"]["with"]["package-path"] == "tests/fixtures/hello-cli"
