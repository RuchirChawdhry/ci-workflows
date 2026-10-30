"""Contracts and behavior tests for documentation-only PowerShell module Pages."""
import json
from pathlib import Path

import pytest
import yaml

from scripts.module_docs_render import build_site

ROOT = Path(__file__).resolve().parents[1]
TEMPLATE = ROOT / "templates" / "powershell-module-docs"


def workflow():
    return yaml.load((ROOT / ".github/workflows/powershell-module-pages.yml").read_text(),
                     Loader=yaml.BaseLoader)


def sample(helpful=True):
    return {
        "schema_version": 1,
        "module": {"name": "SampleModule", "version": "0.1.0", "description": "Sample module"},
        "commands": [
            {"name": "Get-Greeting", "kind": "Function", "synopsis": "Greets someone",
             "description": "Produces a friendly greeting." if helpful else "",
             "syntax": "Get-Greeting [-Name] <String>",
             "parameters": [{"name": "Name", "type": "String", "required": True,
                             "description": "Person to greet." if helpful else ""}],
             "examples": [{"title": "Example 1", "code": "Get-Greeting -Name World",
                           "description": "Returns a greeting."}] if helpful else []}
        ]
    }


def test_three_distinct_jobs_and_no_release_publishing():
    wf = workflow()
    assert set(wf["on"]) == {"workflow_call"}
    assert wf["permissions"] == {"contents": "read"}
    assert {"extract", "build", "deploy"} == set(wf["jobs"])
    assert wf["jobs"]["extract"]["runs-on"] == "windows-2025"
    assert wf["jobs"]["build"]["needs"] == "extract"
    assert wf["jobs"]["deploy"]["needs"] == "build"
    assert wf["on"]["workflow_call"]["inputs"]["publish"]["default"] == "false"
    assert wf["on"]["workflow_call"]["inputs"]["strict-help"]["default"] == "true"
    assert wf["jobs"]["deploy"]["permissions"] == {"pages": "write", "id-token": "write"}
    assert wf["jobs"]["deploy"]["environment"]["name"] == "github-pages"
    guard = wf["jobs"]["deploy"]["if"]
    assert "inputs.publish" in guard and "pull_request" in guard and "inputs.deploy-branch" in guard


def test_extract_produces_json_artifact_and_build_consumes_it():
    wf = workflow()
    extraction = wf["jobs"]["extract"]["steps"]
    build = wf["jobs"]["build"]["steps"]
    assert any("module_docs_extract.ps1" in s.get("run", "") for s in extraction)
    assert any("actions/upload-artifact@" in s.get("uses", "") for s in extraction)
    assert any("actions/download-artifact@" in s.get("uses", "") for s in build)
    assert any("module_docs_render.py" in s.get("run", "") for s in build)
    assert any("upload-pages-artifact@" in s.get("uses", "") for s in build)
    assert any("actions/deploy-pages@" in s.get("uses", "") for s in wf["jobs"]["deploy"]["steps"])
    assert all("publish" not in s.get("name", "").lower() for s in extraction)


def test_template_is_docs_only_starlight_and_reuses_lockfile():
    config = (TEMPLATE / "astro.config.mjs").read_text()
    assert "starlight(" in config and "DOCS_BASE" in config
    assert "autogenerate: { directory: 'reference' }" in config
    assert "\n  base,\n" in config
    assert (TEMPLATE / "src/content.config.ts").exists()
    assert (TEMPLATE / "src/styles/custom.css").exists()
    assert "astro" in json.loads((ROOT / "website/package.json").read_text())["devDependencies"]


def test_renderer_generates_root_home_and_command_reference(tmp_path):
    input_file = tmp_path / "reference.json"
    input_file.write_text(json.dumps(sample()))
    site = tmp_path / "site"
    generated = build_site(input_file, site, strict=True)
    assert generated == ["Get-Greeting"]
    home = (site / "src/content/docs/index.md").read_text()
    ref = (site / "src/content/docs/reference/get-greeting.md").read_text()
    assert "SampleModule" in home
    assert "Get-Greeting" in home
    assert "Greets someone" in ref
    assert "Get-Greeting -Name World" in ref
    assert "Person to greet." in ref
    assert "## Parameters" in ref


def test_strict_mode_rejects_missing_help_without_ignoring_partial_metadata(tmp_path):
    input_file = tmp_path / "reference.json"
    input_file.write_text(json.dumps(sample(helpful=False)))
    with pytest.raises(ValueError, match="Get-Greeting"):
        build_site(input_file, tmp_path / "site", strict=True)
    build_site(input_file, tmp_path / "site", strict=False)
    assert "Get-Greeting" in (tmp_path / "site/src/content/docs/reference/get-greeting.md").read_text()


def test_existing_platyps_markdown_can_supply_authored_help(tmp_path):
    data = sample(helpful=False)
    input_file = tmp_path / "reference.json"
    input_file.write_text(json.dumps(data))
    authored = tmp_path / "docs"
    authored.mkdir()
    (authored / "Get-Greeting.md").write_text(
        "# Get-Greeting\n\n## SYNOPSIS\n\nGreets somebody.\n\n"
        "## DESCRIPTION\n\nA detailed, authored explanation.\n\n"
        "## EXAMPLES\n\n### Example 1\n\n```powershell\nGet-Greeting -Name World\n```\n"
    )
    build_site(input_file, tmp_path / "site", authored=authored, strict=True)
    ref = (tmp_path / "site/src/content/docs/reference/get-greeting.md").read_text()
    assert "A detailed, authored explanation" in ref


def test_renderer_rejects_unsafe_command_names(tmp_path):
    d = sample()
    d["commands"][0]["name"] = "../../unsafe"
    p = tmp_path / "reference.json"
    p.write_text(json.dumps(d))
    with pytest.raises(ValueError):
        build_site(p, tmp_path / "site", strict=False)
