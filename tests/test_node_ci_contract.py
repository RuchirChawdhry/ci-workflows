"""Node CI interface, reproducibility, and consumer smoke contracts."""
import json
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]


def load(path):
    return yaml.load((ROOT / path).read_text(), Loader=yaml.BaseLoader)


def test_node_workflow_is_reusable_and_read_only():
    workflow = load(".github/workflows/node-ci.yml")
    inputs = workflow["on"]["workflow_call"]["inputs"]
    assert workflow["permissions"] == {"contents": "read"}
    assert inputs["runs-on"]["default"] == "ubuntu-latest"
    assert inputs["node-version"]["default"] == "24"
    assert inputs["project-path"]["default"] == "."
    assert inputs["package-manager"]["default"] == "auto"
    job = workflow["jobs"]["quality"]
    assert job["runs-on"] == "${{ inputs.runs-on }}"
    assert job["timeout-minutes"] == "${{ inputs.timeout-minutes }}"
    assert job["defaults"]["run"]["working-directory"] == "${{ inputs.project-path }}"
    steps = job["steps"]
    assert steps[0]["uses"].startswith("actions/checkout@")
    assert steps[0]["with"]["persist-credentials"] == "false"
    assert steps[1]["uses"].startswith("actions/setup-node@")


def test_manager_detection_and_frozen_installs():
    steps = load(".github/workflows/node-ci.yml")["jobs"]["quality"]["steps"]
    manager = next(s for s in steps if s.get("id") == "manager")
    for token in ("package-lock.json", "npm-shrinkwrap.json", "pnpm-lock.yaml",
                  "yarn.lock", "packageManager", "Exactly one"):
        assert token in manager["run"]
    install = next(s for s in steps if s["name"] == "Install dependencies from lockfile")
    for token in ("npm ci", "corepack pnpm install --frozen-lockfile",
                  "corepack yarn install --frozen-lockfile",
                  "corepack yarn install --immutable"):
        assert token in install["run"]
    assert install["env"]["INSTALL_COMMAND"] == "${{ inputs.install-command }}"


def test_check_stages_are_configurable_and_do_not_interpolate_untrusted_code():
    workflow = load(".github/workflows/node-ci.yml")
    inputs = workflow["on"]["workflow_call"]["inputs"]
    steps = workflow["jobs"]["quality"]["steps"]
    for name, title in (("typecheck", "Typecheck"), ("lint", "Lint"),
                        ("test", "Unit tests"), ("build", "Build application")):
        assert inputs[name + "-command"]["default"] == "auto"
        step = next(s for s in steps if s["name"] == title)
        assert step["if"] == "${{ inputs." + name + "-command != '' }}"
        assert step["env"]["STAGE_COMMAND"] == "${{ inputs." + name + "-command }}"
        assert "npm run " + name in step["run"]
        assert 'bash -e -o pipefail -c "$STAGE_COMMAND"' in step["run"]
        assert "${{" not in step["run"]


def test_optional_artifact_strict_and_exposed_as_output():
    workflow = load(".github/workflows/node-ci.yml")
    upload = next(s for s in workflow["jobs"]["quality"]["steps"] if s.get("id") == "upload")
    assert "inputs.artifact-path != ''" in upload["if"]
    assert "inputs.build-command != ''" in upload["if"]
    assert upload["with"]["if-no-files-found"] == "error"
    assert workflow["on"]["workflow_call"]["outputs"]["artifact-id"]["value"] == (
        "${{ jobs.quality.outputs.artifact-id }}"
    )


def test_smoke_runs_real_caller_jobs_on_linux_and_windows():
    smoke = load(".github/workflows/node-ci-smoke.yml")
    assert "pull_request" in smoke["on"]
    assert smoke["permissions"] == {"contents": "read"}
    assert len(smoke["jobs"]) == 2
    for job in smoke["jobs"].values():
        assert job["uses"] == "./.github/workflows/node-ci.yml"
        assert job["with"]["project-path"] == "tests/fixtures/node-app"
    assert smoke["jobs"]["npm-windows"]["with"]["runs-on"] == "windows-2025"
    assert smoke["jobs"]["npm-windows"]["with"]["typecheck-command"] == "node --check src/index.js"
    assert smoke["jobs"]["npm-linux"]["with"]["artifact-path"].endswith("dist/index.js")


def test_fixture_contains_reproducible_install_and_real_tests():
    fixture = ROOT / "tests/fixtures/node-app"
    package = json.loads((fixture / "package.json").read_text())
    lock = json.loads((fixture / "package-lock.json").read_text())
    assert lock["lockfileVersion"] == 3
    assert lock["name"] == package["name"]
    assert set(("typecheck", "lint", "test", "build")) <= set(package["scripts"])
    for relative in ("src/index.js", "test/index.test.js", "scripts/build.mjs"):
        assert (fixture / relative).is_file()
