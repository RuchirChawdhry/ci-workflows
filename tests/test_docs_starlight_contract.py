"""Starlight docs should coexist with the existing Astro landing page.

Contract tests run in the central PR suite before the Pages artifact is built.
"""
from pathlib import Path
import json
import re

import yaml

ROOT = Path(__file__).resolve().parents[1]
SITE = ROOT / "website"
DOCS = SITE / "src/content/docs/docs"
SLUGS = {
    "index",
    "getting-started",
    "concepts/reusable-workflows",
    "concepts/composite-actions",
    "workflows/python-cli",
    "workflows/python-build",
    "workflows/python-compat",
    "workflows/powershell",
    "workflows/powershell-module-pages",
    "workflows/scoop",
    "workflows/homebrew",
    "workflows/astro-pages",
    "troubleshooting",
}
WORKFLOWS = {
    "python-cli": "python-cli.yml",
    "python-build": "python-build.yml",
    "python-compat": "python-compat.yml",
    "powershell": "powershell-ci.yml",
    "powershell-module-pages": "powershell-module-pages.yml",
    "scoop": "scoop-ci.yml",
    "homebrew": "homebrew-ci.yml",
    "astro-pages": "pages-astro.yml",
}


def test_docs_are_integrated_into_current_astro_project():
    config = (SITE / "astro.config.mjs").read_text()
    assert "starlight from '@astrojs/starlight'" in config
    assert "starlight({" in config
    assert "base: '/ci-workflows'" in config
    assert "site: 'https://ruchirchawdhry.github.io'" in config
    assert "output: 'static'" in config
    content = (SITE / "src/content.config.ts").read_text()
    assert "docsLoader()" in content
    assert "docsSchema()" in content
    assert "defineCollection" in content
    package = json.loads((SITE / "package.json").read_text())
    assert "@astrojs/starlight" in package["devDependencies"]
    assert (SITE / "src/pages/index.astro").is_file()


def test_docs_pages_are_complete_and_have_metadata():
    for slug in sorted(SLUGS):
        path = DOCS / f"{slug}.md"
        assert path.is_file(), str(path)
        frontmatter = path.read_text()
        assert frontmatter.startswith("---\n"), str(path)
        assert re.search(r"(?m)^title: .+", frontmatter), str(path)
        assert re.search(r"(?m)^description: .+", frontmatter), str(path)


def test_sidebar_references_real_docs_pages():
    config = (SITE / "astro.config.mjs").read_text()
    for slug in SLUGS:
        assert f"'docs/{slug}'" in config if slug != "index" else "slug: 'docs'" in config
    assert "'./src/styles/starlight.css'" in config
    assert "pagefind: true" in config


def test_workflow_guides_link_to_real_workflows_and_document_caller():
    for slug, name in WORKFLOWS.items():
        source = ROOT / ".github/workflows" / name
        assert source.is_file(), name
        body = (DOCS / "workflows" / f"{slug}.md").read_text()
        assert name in body
        assert "workflow_call" in source.read_text()
        assert "uses:" in body


def test_landings_link_both_directions():
    landing = (SITE / "src/pages/index.astro").read_text()
    assert "Documentation" in landing
    assert "import.meta.env.BASE_URL" in landing
    assert "docs/" in landing
    docs_config = (SITE / "astro.config.mjs").read_text()
    assert "https://ruchirchawdhry.github.io/ci-workflows/" in docs_config


def test_deployment_branch_and_permissions_unchanged():
    wf = yaml.load((ROOT / ".github/workflows/website.yml").read_text(), Loader=yaml.BaseLoader)
    assert wf["on"]["push"]["branches"] == ["main"]
    assert wf["jobs"]["website"]["uses"] == "./.github/workflows/pages-astro.yml"
    assert wf["jobs"]["website"]["with"]["site-path"] == "website"
    assert "github.event_name != 'pull_request'" in wf["jobs"]["website"]["with"]["publish"]


def test_all_internal_documentation_links_resolve_to_real_pages():
    from urllib.parse import urljoin, urlsplit

    expected = {"/ci-workflows/docs/" if name == "index" else
                f"/ci-workflows/docs/{name}/" for name in SLUGS}
    for name in sorted(SLUGS):
        source = (DOCS / f"{name}.md").read_text()
        current = "/ci-workflows/docs/" if name == "index" else f"/ci-workflows/docs/{name}/"
        for href in re.findall(r"\]\(([^)\s]+)(?:\s+[^)]*)?\)", source):
            if href.startswith(("https://", "http://", "mailto:", "#")):
                continue
            target = urlsplit(urljoin("https://example.invalid" + current, href)).path
            assert target in expected, f"{name}: {href} -> {target} is not a docs page"


def test_project_base_is_not_duplicated_in_nav_edit_links_or_favicon():
    config = (SITE / "astro.config.mjs").read_text()
    landing = (SITE / "src/pages/index.astro").read_text()
    assert "favicon: '/favicon.svg'" in config
    assert "baseUrl: 'https://github.com/RuchirChawdhry/ci-workflows/edit/main/website/'" in config
    assert "import.meta.env.BASE_URL.replace(/\\/?$/, '/')" in landing
