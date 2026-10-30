"""Contracts for the uv-only Python CLI composite action and its wrapper."""

from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[1]


def load(path):
    return yaml.load((ROOT / path).read_text(), Loader=yaml.BaseLoader)


def test_python_cli_wrapper_delegates_quality_to_composite_action():
    workflow = load(".github/workflows/python-cli.yml")
    inputs = workflow["on"]["workflow_call"]["inputs"]
    assert inputs["python-version"]["default"] == "3.14.7"
    assert inputs["runs-on"]["default"] == "ubuntu-slim"
    assert "matrix" not in workflow["jobs"]["quality"].get("strategy", {})
    job = workflow["jobs"]["quality"]
    assert job["runs-on"] == "${{ inputs.runs-on }}"
    assert int(job["timeout-minutes"]) <= 14
    assert workflow["permissions"] == {"contents": "read"}

    steps = job["steps"]
    assert len(steps) == 2
    assert steps[0]["uses"].startswith("actions/checkout@")
    assert steps[0]["with"]["persist-credentials"] == "false"
    assert steps[1]["uses"] == "$/actions/python-checks"
    assert steps[1]["with"] == {
        "python-version": "${{ inputs.python-version }}",
        "cli-command": "${{ inputs.cli-command }}",
    }


def test_composite_action_owns_uv_setup_and_quality_checks():
    action = load("actions/python-checks/action.yml")
    assert action["runs"]["using"] == "composite"
    assert action["inputs"]["python-version"]["default"] == "3.14.7"
    assert action["inputs"]["cli-command"]["default"] == ""

    steps = action["runs"]["steps"]
    assert any("astral-sh/setup-uv@" in step.get("uses", "") for step in steps)
    commands = "\n".join(step.get("run", "") for step in steps)
    for command in (
        "uv python install",
        "uv sync",
        "uv run --no-sync python --version",
        "uv run --no-sync ruff check .",
        "uv run --no-sync ruff format --check .",
        "uv run --no-sync pytest -q",
        'uv run --no-sync "$CLI_COMMAND" --help',
    ):
        assert command in commands


def test_composite_action_is_cross_platform_and_optional_smoke_test():
    action = load("actions/python-checks/action.yml")
    steps = action["runs"]["steps"]
    assert all(step.get("shell") == "bash" for step in steps if "run" in step)
    smoke = next(s for s in steps if s.get("name") == "CLI help smoke test")
    assert smoke["if"] == "${{ inputs.cli-command != '' }}"
    assert smoke["env"]["CLI_COMMAND"] == "${{ inputs.cli-command }}"
