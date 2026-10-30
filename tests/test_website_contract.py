"""Contracts for the first real Astro site powered by our own Pages workflow."""
from pathlib import Path
import json
import yaml

ROOT = Path(__file__).resolve().parents[1]
SITE = ROOT / "website"


def workflow(path):
    return yaml.load((ROOT / path).read_text(), Loader=yaml.BaseLoader)


def test_site_is_astro_and_uses_project_pages_base():
    package = json.loads((SITE / "package.json").read_text())
    assert package["scripts"]["build"] == "astro build"
    assert "astro" in package["devDependencies"]
    assert (SITE / "package-lock.json").exists()
    config = (SITE / "astro.config.mjs").read_text()
    assert "output: 'static'" in config
    assert "base: '/ci-workflows'" in config
    assert "site: 'https://ruchirchawdhry.github.io'" in config


def test_site_caller_uses_our_own_reusable_workflow():
    wf = workflow(".github/workflows/website.yml")
    assert "pull_request" in wf["on"]
    assert wf["on"]["push"]["branches"] == ["main"]
    assert "workflow_dispatch" in wf["on"]
    assert wf["permissions"] == {
        "contents": "read",
        "pages": "write",
        "id-token": "write",
    }
    job = wf["jobs"]["website"]
    assert job["uses"] == "./.github/workflows/pages-astro.yml"
    assert job["with"]["site-path"] == "website"
    assert job["with"]["publish"] == (
        "${{ github.event_name != 'pull_request' && github.ref == 'refs/heads/main' }}"
    )


def test_site_does_not_invent_release_features():
    page = (SITE / "src/pages/index.astro").read_text()
    cards = (SITE / "src/data/workflows.ts").read_text()
    for name in ("Python CLI", "Python Build", "Compatibility Explorer",
                 "PowerShell", "Scoop", "Homebrew", "Astro Pages"):
        assert name in cards
    for path in ("python-cli.yml", "python-build.yml", "python-compat.yml",
                 "powershell-ci.yml", "scoop-ci.yml", "homebrew-ci.yml",
                 "pages-astro.yml"):
        assert (ROOT / ".github/workflows" / path).exists()
        assert path in cards
    assert "workflows" in page.lower()
    assert "pypi publishing" not in page.lower()


def test_site_has_share_metadata_and_accessible_navigation():
    layout = (SITE / "src/layouts/BaseLayout.astro").read_text()
    page = (SITE / "src/pages/index.astro").read_text()
    assert 'name="description"' in layout
    assert 'property="og:title"' in layout
    assert 'property="og:image"' in layout
    assert 'name="twitter:card"' in layout
    assert 'aria-label="Primary navigation"' in page
    assert 'id="workflows"' in page
    assert 'id="how-it-works"' in page
    assert 'id="principles"' in page
    assert 'prefers-reduced-motion' in (SITE / "src/styles/global.css").read_text()
