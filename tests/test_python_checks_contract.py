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
    assert inputs["project-path"]["default"] == "."
    assert inputs["dev-group"]["default"] == "dev"
    assert inputs["test-command"]["default"] == "pytest -q"
    assert inputs["workspace-package"]["default"] == ""
    assert "matrix" not in workflow["jobs"]["quality"].get("strategy", {})
    job = workflow["jobs"]["quality"]
    assert job["runs-on"] == "${{ inputs.runs-on }}"
    assert int(job["timeout-minutes"]) <= 14
    assert workflow["permissions"] == {"contents": "read"}

    steps = job["steps"]
    assert len(steps) == 2
    assert steps[0]["uses"].startswith("actions/checkout@")
    assert steps[0]["with"]["persist-credentials"] == "false"
    # Self-repository syntax pins the action to the called workflow's own commit.
    assert steps[1]["uses"] == "$/actions/python-checks"
    assert steps[1]["with"] == {
        "python-version": "${{ inputs.python-version }}",
        "project-path": "${{ inputs.project-path }}",
        "dev-group": "${{ inputs.dev-group }}",
        "test-command": "${{ inputs.test-command }}",
        "workspace-package": "${{ inputs.workspace-package }}",
        "cli-command": "${{ inputs.cli-command }}",
    }


def test_composite_action_owns_uv_setup_and_quality_checks():
    action = load("actions/python-checks/action.yml")
    assert action["runs"]["using"] == "composite"
    assert action["inputs"]["python-version"]["default"] == "3.14.7"
    assert action["inputs"]["cli-command"]["default"] == ""
    assert action["inputs"]["project-path"]["default"] == "."
    assert action["inputs"]["dev-group"]["default"] == "dev"
    assert action["inputs"]["test-command"]["default"] == "pytest -q"
    assert action["inputs"]["workspace-package"]["default"] == ""

    steps = action["runs"]["steps"]
    assert any("astral-sh/setup-uv@" in step.get("uses", "") for step in steps)
    commands = "\n".join(step.get("run", "") for step in steps)
    for command in (
        "uv python install",
        "uv sync",
        "uv run --no-sync python --version",
        "uv run --no-sync ruff check .",
        "uv run --no-sync ruff format --check .",
        'uv run --no-sync bash -e -o pipefail -c "$TEST_COMMAND"',
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

def test_python_monorepo_scoping_custom_group_and_test_command():
    action = load("actions/python-checks/action.yml")
    steps = action["runs"]["steps"]
    for step in steps:
        if "run" in step:
            assert step["working-directory"] == "${{ inputs.project-path }}"
    install = next(step for step in steps if step["name"] == "Install Python and project dependencies")
    assert install["env"]["DEV_GROUP"] == "${{ inputs.dev-group }}"
    assert install["env"]["WORKSPACE_PACKAGE"] == "${{ inputs.workspace-package }}"
    assert 'sync_args+=(--group "$DEV_GROUP")' in install["run"]
    assert 'sync_args+=(--package "$WORKSPACE_PACKAGE")' in install["run"]
    assert 'uv sync "${sync_args[@]}"' in install["run"]
    test = next(step for step in steps if step["name"] == "Test")
    assert test["if"] == "${{ inputs.test-command != '' }}"
    assert test["env"]["TEST_COMMAND"] == "${{ inputs.test-command }}"
    assert '"$TEST_COMMAND"' in test["run"]
    assert "${{" not in test["run"]


def test_real_workspace_fixture_and_consumer_smoke():
    from pathlib import Path
    import tomllib

    workspace = ROOT / "tests/fixtures/python-monorepo"
    root = tomllib.loads((workspace / "pyproject.toml").read_text())
    member = workspace / "packages/widget"
    child = tomllib.loads((member / "pyproject.toml").read_text())
    assert root["tool"]["uv"]["workspace"]["members"] == ["packages/*"]
    assert child["project"]["name"] == "ci-workflows-widget"
    assert "quality" in child["dependency-groups"]
    assert "dev" not in child["dependency-groups"]
    assert (member / "tests/test_greeting.py").exists()
    smoke = load(".github/workflows/python-monorepo-smoke.yml")
    assert "pull_request" in smoke["on"]
    assert smoke["permissions"] == {"contents": "read"}
    job = smoke["jobs"]["uv-workspace-member"]
    assert job["uses"] == "./.github/workflows/python-cli.yml"
    assert job["with"]["project-path"] == "tests/fixtures/python-monorepo/packages/widget"
    assert job["with"]["dev-group"] == "quality"
    assert job["with"]["workspace-package"] == "ci-workflows-widget"
    assert job["with"]["test-command"] == "pytest -q tests -k greeting"
