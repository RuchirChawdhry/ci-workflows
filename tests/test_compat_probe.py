"""Pure mocked execution tests: no Python downloads are needed."""
import subprocess
from scripts.compat_probe import probe

def project(tmp_path, requirement=">=3.8"):
    (tmp_path / "pyproject.toml").write_text(
        f'[project]\nname = "sample"\nversion = "0.1.0"\nrequires-python = "{requirement}"\n')
    (tmp_path / "src").mkdir(exist_ok=True)
    (tmp_path / "tests").mkdir(exist_ok=True)
    return tmp_path

def executor(fail=None, calls=None):
    def execute(stage, args, cwd):
        if calls is not None:
            calls.append((stage, args))
        return subprocess.CompletedProcess(args, int(stage == fail), "",
                                           f"deliberate {stage} failure" if stage == fail else "")
    return execute

def test_syntax_failure_is_not_dependency_failure(tmp_path):
    result = probe(project(tmp_path), "3.8", executor("syntax"))
    assert result["status"] == "SYNTAX"
    assert result["failed_stage"] == "syntax"

def test_metadata_is_not_a_source_incompatibility(tmp_path):
    calls = []
    result = probe(project(tmp_path, ">=3.11"), "3.8", executor(calls=calls))
    assert result["status"] == "UNSUPPORTED"
    assert "requires-python" in result["reason"]
    assert "install-no-deps" not in [stage for stage, _ in calls]

def test_build_and_runtime_dependencies_are_distinct(tmp_path):
    p = project(tmp_path)
    assert probe(p, "3.12", executor("install-no-deps"))["status"] == "BUILD"
    failure = probe(p, "3.12", executor("install-with-deps"))
    assert failure["status"] == "DEPENDENCY"
    assert "deliberate install-with-deps" in failure["reason"]

def test_import_cli_and_test_failures_are_distinct(tmp_path):
    p = project(tmp_path)
    for stage, expected in [("import", "IMPORT"), ("cli", "CLI"), ("tests", "TEST")]:
        assert probe(p, "3.12", executor(stage), import_name="sample", cli_command="sample")["status"] == expected

def test_success_and_optional_steps(tmp_path):
    calls = []
    result = probe(project(tmp_path), "3.13", executor(calls=calls))
    assert result["status"] == "PASS"
    assert all(check["ok"] for check in result["checks"])
    assert "cli" not in [s for s, _ in calls]

def test_provisioning_errors_are_infrastructure(tmp_path):
    result = probe(project(tmp_path), "3.6", executor("provision"))
    assert result["status"] == "INFRA"

def test_cli_exec_uses_args_not_a_shell(tmp_path):
    calls = []
    probe(project(tmp_path), "3.12", executor(calls=calls), cli_command="my-tool")
    assert all(isinstance(args, list) for _, args in calls)
    assert any(args[-1:] == ["--help"] and args[0].endswith("/my-tool") for _, args in calls)
