"""Contracts for Astro-only reusable GitHub Pages deployment."""
from pathlib import Path
import json
import yaml

ROOT = Path(__file__).resolve().parents[1]


def load(name):
    return yaml.load((ROOT / name).read_text(), Loader=yaml.BaseLoader)


def test_reusable_workflow_has_explicit_opt_in_to_publication():
    wf = load('.github/workflows/pages-astro.yml')
    assert set(wf['on']) == {'workflow_call'}
    inputs = wf['on']['workflow_call']['inputs']
    assert inputs['publish'] == {'description': 'Deploy to GitHub Pages after building', 'type': 'boolean', 'default': 'false'}
    assert inputs['site-path']['default'] == '.'
    assert inputs['node-version']['default'] == '24'
    assert inputs['deploy-branch']['default'] == 'main'
    assert wf['permissions'] == {'contents': 'read'}


def test_build_uses_pinned_official_astro_action_and_read_only_checkout():
    wf = load('.github/workflows/pages-astro.yml')
    build = wf['jobs']['build']
    assert build['permissions'] == {'contents': 'read'}
    steps = build['steps']
    assert steps[0]['uses'].startswith('actions/checkout@')
    assert steps[0]['with']['persist-credentials'] == 'false'
    astro = next(s for s in steps if s.get('name') == 'Build Astro and upload Pages artifact')
    assert astro['uses'].startswith('withastro/action@')
    assert astro['with']['path'] == '${{ inputs.site-path }}'
    assert astro['with']['node-version'] == '${{ inputs.node-version }}'
    assert astro['with']['package-manager'] == '${{ inputs.package-manager }}'
    assert astro['with']['out-dir'] == '${{ inputs.out-dir }}'


def test_deploy_is_separate_protected_job_with_least_privilege():
    wf = load('.github/workflows/pages-astro.yml')
    job = wf['jobs']['deploy']
    assert job['needs'] == 'build'
    assert "inputs.publish" in job['if']
    assert "github.event_name != 'pull_request'" in job['if']
    assert "inputs.deploy-branch" in job['if']
    assert job['environment']['name'] == 'github-pages'
    assert job['permissions'] == {'pages': 'write', 'id-token': 'write'}
    deploy = next(s for s in job['steps'] if s['id'] == 'deployment')
    assert deploy['uses'].startswith('actions/deploy-pages@')
    assert job['environment']['url'] == '${{ steps.deployment.outputs.page_url }}'


def test_smoke_builds_real_astro_fixture_on_pr_without_deploying():
    wf = load('.github/workflows/pages-astro-smoke.yml')
    assert 'pull_request' in wf['on']
    job = wf['jobs']['astro-smoke']
    assert job['uses'] == './.github/workflows/pages-astro.yml'
    assert job['with']['publish'] == 'false'
    assert job['with']['site-path'] == 'tests/fixtures/astro-site'
    assert job['with']['package-manager'] == 'npm'
    assert (ROOT / 'tests/fixtures/astro-site/src/pages/index.astro').exists()
    pkg = json.loads((ROOT / 'tests/fixtures/astro-site/package.json').read_text())
    assert 'astro' in pkg['devDependencies']
    assert pkg['scripts']['build'] == 'astro build'
    config = (ROOT / 'tests/fixtures/astro-site/astro.config.mjs').read_text()
    assert 'output: "static"' in config
    assert 'base: "/ci-workflows"' in config


def test_guide_has_caller_and_pages_settings():
    doc = (ROOT / 'docs/pages-astro.md').read_text()
    for needle in ('pages-astro.yml@', 'Settings', 'GitHub Actions', 'github-pages', 'site-path', 'publish:', 'base:', 'lockfile'):
        assert needle in doc
