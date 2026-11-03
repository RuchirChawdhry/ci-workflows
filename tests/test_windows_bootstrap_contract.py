"""Contracts for Windows Taskfile bootstrap provisioning."""
from pathlib import Path
import yaml

ROOT = Path(__file__).resolve().parents[1]


def test_reusable_bootstrap_executes_and_verifies_real_installation():
    wf = yaml.load((ROOT / ".github/workflows/windows-bootstrap.yml").read_text(), Loader=yaml.BaseLoader)
    inputs = wf["on"]["workflow_call"]["inputs"]
    assert inputs["config-path"]["required"] == "true"
    assert inputs["runs-on"]["default"] == "windows-2025"
    assert wf["permissions"] == {"contents": "read"}
    job = wf["jobs"]["bootstrap"]
    assert job["runs-on"] == "${{ inputs.runs-on }}"
    steps = job["steps"]
    assert "actions/checkout@" in steps[0]["uses"]
    assert steps[0]["with"]["persist-credentials"] == "false"
    assert 'Copy-Item' in steps[1]["run"] and '.app-config.yml' in steps[1]["run"]
    assert "bootstrap.ps1" in steps[2]["run"]
    verify = steps[3]["run"]
    assert "Import-Module Yayaml" in verify
    assert "ConvertFrom-Yaml" in verify
    assert "Missing Scoop packages" in verify
    assert "Missing WinGet package" in verify
    assert "task --taskfile ./Taskfile.yml --list-all --silent" in verify
    assert "Task discovery failed" in verify
    assert "task --taskfile ./Taskfile.yml status" in verify
