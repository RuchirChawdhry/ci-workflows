from pathlib import Path
import yaml

ROOT = Path(__file__).resolve().parent.parent


def load(path):
    return yaml.load((ROOT / path).read_text(), Loader=yaml.BaseLoader)


def test_reusable_build_is_minimally_privileged_and_slim():
    workflow = load('.github/workflows/python-build.yml')
    assert workflow['on']['workflow_call']
    assert workflow['permissions'] == {'contents': 'read'}
    job = workflow['jobs']['build']
    assert job['runs-on'] == '${{ inputs.runs-on }}'
    assert int(job['timeout-minutes']) <= 14
    assert workflow['on']['workflow_call']['inputs']['runs-on']['default'] == 'ubuntu-slim'
    assert workflow['on']['workflow_call']['inputs']['python-version']['default'] == '3.14.7'


def test_build_checks_metadata_and_artifacts():
    workflow = load('.github/workflows/python-build.yml')
    steps = workflow['jobs']['build']['steps']
    blob = '\n'.join(str(s.get('run', '')) for s in steps)
    assert 'uv build' in blob and '--sdist' in blob and '--wheel' in blob
    assert 'twine check --strict' in blob
    assert any('actions/upload-artifact@' in step.get('uses', '') and step['with']['if-no-files-found'] == 'error' for step in steps)
    assert any(step.get('uses') == '$/actions/test-python-cli' for step in steps)


def test_install_smoke_uses_isolated_wheel_not_local_sources():
    action = load('actions/test-python-cli/action.yml')
    assert action['runs']['using'] == 'composite'
    script = '\n'.join(step.get('run', '') for step in action['runs']['steps'])
    assert 'uv venv' in script
    assert 'uv pip install' in script
    assert '--help' in script
    assert 'venv/bin' in script
    assert 'CLI_COMMAND' in script


def test_fixture_is_real_installable_cli():
    from tomllib import loads
    fixture = ROOT / 'tests/fixtures/hello-cli'
    project = loads((fixture / 'pyproject.toml').read_text())
    assert project['project']['scripts']['workflow-hello'] == 'hello_cli.cli:main'
    assert (fixture / 'src/hello_cli/cli.py').is_file()


def test_action_is_top_level_and_old_path_is_gone():
    assert (ROOT / 'actions/test-python-cli/action.yml').is_file()
    assert not (ROOT / '.github/actions/test-python-cli/action.yml').exists()


def test_python_toolchain_is_intentionally_uv_only():
    workflow = load('.github/workflows/python-build.yml')
    action = load('actions/test-python-cli/action.yml')
    steps = workflow['jobs']['build']['steps']
    assert any('astral-sh/setup-uv@' in step.get('uses', '') for step in steps)
    assert any('uv build' in step.get('run', '') for step in steps)
    assert all('uv pip install' in step.get('run', '') for step in action['runs']['steps'])
