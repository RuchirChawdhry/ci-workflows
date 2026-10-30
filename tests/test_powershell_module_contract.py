"""Contracts for the reusable PowerShell module build pipeline."""
from pathlib import Path
import yaml

ROOT = Path(__file__).resolve().parents[1]

def read(path):
    return yaml.load((ROOT / path).read_text(), Loader=yaml.BaseLoader)

def test_module_workflow_has_read_only_inputs_and_artifacts():
    wf = read(".github/workflows/powershell-module.yml")
    inputs = wf["on"]["workflow_call"]["inputs"]
    assert inputs["manifest-path"]["required"] == "true"
    assert inputs["runs-on"]["default"] == "windows-2025"
    assert inputs["minimum-powershell-version"]["default"] == "7.6.9"
    assert wf["permissions"] == {"contents": "read"}
    steps = wf["jobs"]["build"]["steps"]
    assert any(s.get("uses") == "$/actions/powershell-checks" for s in steps)
    assert any(s.get("uses") == "$/actions/powershell-module-build" for s in steps)
    assert any("actions/upload-artifact@" in s.get("uses", "") and s.get("if") == "always()" for s in steps)
    assert any("actions/upload-artifact@" in s.get("uses", "") and "module-zip" in str(s.get("with", {})) for s in steps)
    assert not any("Publish-" in s.get("run", "") for s in steps)

def test_checks_are_reused_by_old_script_ci():
    wf = read(".github/workflows/powershell-ci.yml")
    assert any(s.get("uses") == "$/actions/powershell-checks" for s in wf["jobs"]["quality"]["steps"])
    action = read("actions/powershell-checks/action.yml")
    assert action["runs"]["using"] == "composite"
    assert action["inputs"]["require-tests"]["default"] == "false"
    script = ROOT / "actions/powershell-checks/check.ps1"
    source = script.read_text()
    pester = (ROOT / "actions/powershell-checks/pester.ps1").read_text()
    assert "TestResult.OutputFormat" in pester
    assert "JUnitXml" in pester
    assert "PSScriptAnalyzer" in source
    assert "Pester" in (ROOT / "actions/powershell-checks/pester.ps1").read_text()
    assert "$env:REQUIRE_TESTS" in pester
    assert "7.6.9" in source

def test_module_build_does_isolated_import_and_checks_exports():
    action = read("actions/powershell-module-build/action.yml")
    assert action["runs"]["using"] == "composite"
    code = (ROOT / "actions/powershell-module-build/build.ps1").read_text()
    verifier = (ROOT / "actions/powershell-module-build/verify.ps1").read_text()
    assert "Test-ModuleManifest" in code
    assert "Compress-Archive" in code
    assert "Expand-Archive" in code
    assert "PSModulePath" in code
    assert "pwsh" in code
    assert "Import-Module" in verifier
    assert "FunctionsToExport" in verifier
    assert "Get-Command" in verifier

def test_sample_is_real_module_with_tests():
    folder = ROOT / "tests/fixtures/SampleModule"
    manifest = (folder / "SampleModule.psd1").read_text()
    assert "ModuleVersion" in manifest
    assert "FunctionsToExport" in manifest
    assert (folder / "SampleModule.psm1").is_file()
    assert (ROOT / "tests/fixtures/SampleModule.Tests/SampleModule.Tests.ps1").is_file()
    smoke = read(".github/workflows/powershell-module-smoke.yml")
    assert "pull_request" in smoke["on"]
    assert any(".github/workflows/powershell-module.yml" in s.get("uses", "")
               for s in smoke["jobs"].values())

def test_minimum_runtime_is_actually_provisioned():
    setup = read("actions/powershell-checks/action.yml")
    commands = "\n".join(s.get("run", "") for s in setup["runs"]["steps"])
    assert "PowerShell-7.6.9-win-x64.zip" in commands
    assert "CE7484804C0F0AD4DDA10C958E71ACDAF7EEBFB22505C1B480F89E0E9F1DA94D" in commands
    assert "GITHUB_PATH" in commands
    assert "pwsh -NoProfile -NonInteractive -File" in commands
    build = read("actions/powershell-module-build/action.yml")
    build_steps = "\n".join(s.get("run", "") for s in build["runs"]["steps"])
    assert "pwsh -NoProfile -NonInteractive -File" in build_steps

def test_static_analysis_and_pester_run_in_separate_processes():
    action = read("actions/powershell-checks/action.yml")
    runs = "\n".join(s.get("run","") for s in action["runs"]["steps"])
    assert "pwsh -NoProfile -NonInteractive -File" in runs
    assert "pester.ps1" in runs and "check.ps1" in runs
    static = (ROOT / "actions/powershell-checks/check.ps1").read_text()
    assert "Import-Module Pester" not in static
