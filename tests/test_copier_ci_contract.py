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
    assert set(inputs) == {"profile"}
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
        "uv build --sdist --wheel",
        "uv pip install",
        "gui_scripts",
        "pnpm typecheck",
        "pnpm lint",
        "pnpm test",
        "pnpm verify:build",
        "pnpm test:e2e",
    ):
        assert command in commands
    assert "--trust" not in commands
