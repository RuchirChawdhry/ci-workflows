"""Probe one Python interpreter against source checkout using uv.

A no-dependencies install isolates build failures from dependency-resolution failures.
Each result records stage evidence without treating every red job as code incompatibility.
"""
import argparse
import json
import re
import shutil
import shlex
import subprocess
import sys
import tempfile
import tomllib
from pathlib import Path

from packaging.specifiers import SpecifierSet
from packaging.version import Version

STATUS_BY_STAGE = {
    "provision": "INFRA", "venv": "INFRA", "interpreter": "INFRA",
    "syntax": "SYNTAX", "install-no-deps": "BUILD",
    "install-with-deps": "DEPENDENCY", "test-deps": "TEST_DEPENDENCY",
    "import": "IMPORT", "cli": "CLI", "tests": "TEST",
}


def execute_command(stage, argv, cwd):
    try:
        return subprocess.run(argv, cwd=cwd, text=True, capture_output=True,
                              timeout=300, check=False)
    except (OSError, subprocess.TimeoutExpired) as exc:
        return subprocess.CompletedProcess(argv, 124, "", str(exc))


def python_requirement(project):
    data = tomllib.loads((project / "pyproject.toml").read_text(encoding="utf-8"))
    return data.get("project", {}).get("requires-python", "")


def exploratory_copy(project, destination):
    """Relax only project.requires-python in a disposable copy of the package."""
    shutil.copytree(project, destination, ignore=shutil.ignore_patterns(
        ".git", ".venv", ".ci-workflows", "__pycache__", "dist", "build"))
    pyproject = destination / "pyproject.toml"
    lines = pyproject.read_text(encoding="utf-8").splitlines(keepends=True)
    in_project = False
    for index, line in enumerate(lines):
        if line.lstrip().startswith("["):
            in_project = line.strip() == "[project]"
        elif in_project and re.match(r"^\s*requires-python\s*=", line):
            lines[index] = 'requires-python = ">=3.6"\n'
            pyproject.write_text("".join(lines), encoding="utf-8")
            return destination
    raise ValueError("Cannot locate project.requires-python in copy")


def probe(project, version, execute=execute_command, *, import_name="",
          cli_command="", test_requirements="pytest", explore_unsupported=False):
    """Return a complete, machine-readable diagnosis for one requested version."""
    project = Path(project).resolve()
    result = {"version": version, "actual_version": "", "status": "PASS",
              "failed_stage": None, "reason": "Checks passed", "checks": [],
              "exploratory": False}

    def check(stage, argv, cwd=project):
        completed = execute(stage, list(map(str, argv)), cwd)
        output = (completed.stderr or completed.stdout or "").strip()[-5000:]
        ok = completed.returncode == 0
        result["checks"].append({"stage": stage, "ok": ok,
                                 "returncode": completed.returncode,
                                 "command": list(map(str, argv)), "detail": output})
        if not ok:
            result.update(status=STATUS_BY_STAGE[stage], failed_stage=stage,
                          reason=output or f"{stage} exited with {completed.returncode}")
        return ok

    with tempfile.TemporaryDirectory(prefix="compat-") as temporary:
        envdir = Path(temporary) / "venv"
        python = envdir / "bin" / "python"
        if not check("provision", ["uv", "python", "install", version]):
            return result
        if not check("venv", ["uv", "venv", "--python", version, "--managed-python", envdir]):
            return result
        if not check("interpreter", [python, "--version"]):
            return result
        result["actual_version"] = result["checks"][-1]["detail"].removeprefix("Python ") or version

        source = project / "src" if (project / "src").is_dir() else project
        exclude = r"(^|/)(\.git|\.venv|\.ci-workflows|\.tox|dist|build|__pycache__)(/|$)"
        if not check("syntax", [python, "-m", "compileall", "-q", "-x", exclude, source]):
            return result

        try:
            requirement = python_requirement(project)
            install_project = project
            if requirement and Version(version) not in SpecifierSet(requirement):
                message = f"requires-python {requirement} excludes Python {version}"
                if not explore_unsupported:
                    result.update(status="UNSUPPORTED", failed_stage="metadata", reason=message)
                    result["checks"].append({"stage": "metadata", "ok": False,
                                             "detail": message})
                    return result
                install_project = exploratory_copy(project, Path(temporary) / "project")
                result["exploratory"] = True
                result["checks"].append({"stage": "metadata", "ok": True,
                                         "detail": f"EXPLORATORY: relaxed {message} in disposable copy"})
            else:
                result["checks"].append({"stage": "metadata", "ok": True,
                                         "detail": requirement or "No requires-python declaration"})
        except (OSError, ValueError, KeyError) as exc:
            result.update(status="METADATA", failed_stage="metadata", reason=str(exc))
            return result

        if not check("install-no-deps", ["uv", "pip", "install", "--python", python,
                                          "--no-deps", install_project]):
            return result
        if not check("install-with-deps", ["uv", "pip", "install", "--python", python,
                                            install_project]):
            return result
        requirements = shlex.split(test_requirements)
        if requirements and not check("test-deps", ["uv", "pip", "install",
                                                   "--python", python, *requirements]):
            return result
        if import_name and not check("import", [python, "-c",
                                               "import importlib,sys; importlib.import_module(sys.argv[1])",
                                               import_name]):
            return result
        if cli_command:
            if not re.fullmatch(r"[a-zA-Z0-9_.-]+", cli_command):
                result.update(status="CONFIG", failed_stage="cli",
                              reason="CLI must be one executable name")
                return result
            if not check("cli", [envdir / "bin" / cli_command, "--help"]):
                return result
        if (project / "tests").is_dir():
            if not check("tests", [python, "-m", "pytest", "-q", "tests"]):
                return result
        else:
            result["checks"].append({"stage": "tests", "ok": True,
                                     "detail": "SKIPPED: no tests directory"})
        if result["exploratory"]:
            result.update(status="EXPERIMENTAL_PASS",
                          reason="Exploratory checks passed against relaxed metadata copy")
        return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project", type=Path, required=True)
    parser.add_argument("--version", required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--import-name", default="")
    parser.add_argument("--cli-command", default="")
    parser.add_argument("--test-requirements", default="pytest")
    parser.add_argument("--explore-unsupported", action="store_true")
    args = parser.parse_args()
    try:
        result = probe(args.project, args.version, import_name=args.import_name,
                       cli_command=args.cli_command,
                       test_requirements=args.test_requirements,
                       explore_unsupported=args.explore_unsupported)
    except Exception as exc:
        result = {"version": args.version, "status": "INFRA",
                  "failed_stage": "runner",
                  "reason": f"{type(exc).__name__}: {exc}", "checks": []}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(f"Python {args.version}: {result['status']} ({result['reason'][:180]})")
    return 0  # An incompatibility is a finding, not a failed Actions job.


if __name__ == "__main__":
    sys.exit(main())
