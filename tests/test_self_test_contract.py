"""Contracts for the central repository's own PR validation workflow."""

from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / ".github/workflows/self-test.yml"


def test_every_pull_request_runs_contract_tests():
    workflow = yaml.load(WORKFLOW.read_text(), Loader=yaml.BaseLoader)
    assert "pull_request" in workflow["on"]
    assert workflow["permissions"] == {"contents": "read"}

    job = workflow["jobs"]["contracts"]
    assert job["runs-on"] == "ubuntu-slim"
    assert int(job["timeout-minutes"]) <= 14


def test_contract_checks_use_uv_with_python_3147():
    workflow = yaml.load(WORKFLOW.read_text(), Loader=yaml.BaseLoader)
    steps = workflow["jobs"]["contracts"]["steps"]
    assert any("astral-sh/setup-uv@" in step.get("uses", "") for step in steps)
    scripts = "\n".join(step.get("run", "") for step in steps)
    assert "uv python install 3.14.7" in scripts
    assert "uv run --no-project --python 3.14.7" in scripts
    assert "--with pytest" in scripts
    assert "--with PyYAML" in scripts
    assert "pytest -q tests" in scripts
