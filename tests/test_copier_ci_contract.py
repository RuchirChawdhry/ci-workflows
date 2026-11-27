from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]


def test_copier_workflow_contract():
    workflow = yaml.load(
        (ROOT / ".github/workflows/copier-ci.yml").read_text(),
        Loader=yaml.BaseLoader,
    )
    assert set(workflow["on"]) == {"workflow_call"}
    inputs = workflow["on"]["workflow_call"]["inputs"]
    assert set(inputs) == {"profile", "copier-data", "artifact-suffix"}
    assert inputs["copier-data"]["default"] == "{}"
    assert inputs["artifact-suffix"]["default"] == ""
    assert inputs["profile"]["default"] == "python"
    assert workflow["permissions"] == {"contents": "read"}
    job = workflow["jobs"]["validate"]
    assert "windows-latest" in job["runs-on"]
    assert "ubuntu-24.04" in job["runs-on"]
    steps = job["steps"]
    assert steps[0]["with"]["persist-credentials"] == "false"
    assert any(s.get("uses") == "$/actions/python-checks" for s in steps)
    assert any(s.get("uses") == "$/actions/test-python-cli" for s in steps)
    commands = "\n".join(s.get("run", "") for s in steps)
    for command in (
        "pytest -q tests",
        "copier copy --defaults --vcs-ref=HEAD",
        'uv build --python "$PYTHON_VERSION" --sdist --wheel',
        "uv pip install",
        "gui_scripts",
        "pnpm typecheck",
        "pnpm lint",
        "pnpm test",
        "pnpm verify:build",
        "pnpm exec playwright test",
    ):
        assert command in commands
    assert "--trust" not in commands
    render = next(s for s in steps if s.get("id") == "render_current_template")
    assert render["env"]["COPIER_DATA"] == "${{ inputs.copier-data }}"
    assert '--data-file "$RUNNER_TEMP/copier-answers.yml"' in render["run"]
    reports = next(s for s in steps if s.get("id") == "reports")
    assert reports["with"]["name"] == "copier-junit${{ inputs.artifact-suffix }}"


def test_version_setup_and_reports():
    workflow = yaml.load(
        (ROOT / ".github/workflows/copier-ci.yml").read_text(), Loader=yaml.BaseLoader
    )
    steps = {s["id"]: s for s in workflow["jobs"]["validate"]["steps"] if "id" in s}
    version = "${{ steps.python_version.outputs.version }}"
    assert ".python-version" in steps["python_version"]["run"]
    quality = steps["check_generated_python_project"]["with"]
    assert quality["python-version"] == version
    assert quality["setup-uv"] == "false"
    assert "generated-python.xml" in quality["test-command"]
    assert steps["build_python_distributions"]["env"]["PYTHON_VERSION"] == version
    assert steps["install_and_verify_winui_wheel"]["env"]["PYTHON_VERSION"] == version
    smoke = steps["smoke_test_installed_cli"]["with"]
    assert smoke["python-version"] == version
    assert smoke["smoke-test"] == "tests/smoke_installed.py"
    assert smoke["junit-path"].endswith("installed-wheel.xml")
    assert steps["reports"]["if"] == "always()"
    summary = next(s for s in workflow["jobs"]["validate"]["steps"] if s["name"] == "Summarize validation stages")
    assert summary["if"] == "always()"
    assert "GITHUB_STEP_SUMMARY" in summary["run"]
    assert all(s["id"].upper() in summary["run"] for s in steps.values())
    assert "3.14.7" not in (ROOT / ".github/workflows/copier-ci.yml").read_text()


def test_composite_actions_keep_standalone_defaults():
    quality = yaml.load((ROOT / "actions/python-checks/action.yml").read_text(), Loader=yaml.BaseLoader)
    assert quality["inputs"]["setup-uv"]["default"] == "true"
    assert quality["runs"]["steps"][0]["if"] == "inputs.setup-uv == 'true'"
    smoke = yaml.load((ROOT / "actions/test-python-cli/action.yml").read_text(), Loader=yaml.BaseLoader)
    assert smoke["inputs"]["smoke-test"]["default"] == ""
    script = smoke["runs"]["steps"][0]["run"]
    assert 'export CLI_EXECUTABLE=' in script
    assert 'cd "$(mktemp -d)"' in script
    assert "-I -m pytest" in script
