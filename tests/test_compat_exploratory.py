"""Exploratory probing must leave metadata untouched and never claim official support."""
import subprocess

from scripts.compat_probe import probe
from scripts.compat_report import summarize, markdown


def run(stage, args, cwd):
    return subprocess.CompletedProcess(args, int(stage == "install-with-deps"), "",
                                       "dependency resolution failed" if stage == "install-with-deps" else "")


def test_unsupported_copy_does_not_mutate_original(tmp_path):
    (tmp_path / "pyproject.toml").write_text('[project]\nname="sample"\nversion="0.1"\nrequires-python=">=3.11"\n')
    (tmp_path / "src").mkdir()
    result = probe(tmp_path, "3.9", lambda stage, args, cwd: subprocess.CompletedProcess(args, 0, "", ""),
                   explore_unsupported=True)
    assert result["status"] == "EXPERIMENTAL_PASS"
    assert result["exploratory"] is True
    assert 'requires-python=">=3.11"' in (tmp_path / "pyproject.toml").read_text()


def test_exploratory_resolution_errors_remain_dependency_errors(tmp_path):
    (tmp_path / "pyproject.toml").write_text('[project]\nname="sample"\nversion="0.1"\nrequires-python=">=3.11"\n')
    (tmp_path / "src").mkdir()
    result = probe(tmp_path, "3.9", run, explore_unsupported=True)
    assert result["status"] == "DEPENDENCY"
    assert result["exploratory"] is True


def test_markdown_surfaces_final_traceback_exception(tmp_path):
    import json
    (tmp_path / "3.10.json").write_text(json.dumps({
        "version": "3.10", "status": "CLI", "failed_stage": "cli",
        "reason": "Traceback (most recent call last):\\n  File x\\nImportError: cannot import name UTC"
    }))
    result = markdown(summarize(tmp_path, ["3.10"]))
    assert "ImportError: cannot import name UTC" in result
    assert "| 3.10 | CLI | cli | Traceback" not in result
