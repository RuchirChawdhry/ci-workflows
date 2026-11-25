import json
from pathlib import Path
import subprocess
import sys

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from structured_data import (Page, identity, inject, modified, portfolio_graph, project_graph,
                             read_overrides, validate)

ORIGIN = "https://example.github.io/demo/"
OWNER = identity("Example", {"login": "Example", "name": "Example Developer", "type": "User"})
META = {"name": "demo", "url": "https://github.com/Example/demo", "description": "A Python tool",
        "language": "Python", "topics": ["cli"], "license": "https://github.com/Example/demo/blob/main/LICENSE",
        "license_name": "MIT", "release": "v1.0", "release_url": "https://github.com/Example/demo/releases/tag/v1.0"}


def page(tmp_path, url, title):
    path = tmp_path / "index.html"
    path.write_text(f'<html><head><link rel="canonical" href="{url}"></head><body><nav><a href="{ORIGIN}">Demo</a><a href="{META["url"]}">GitHub</a></nav><main><h1>{title}</h1><p>Demo app: A CLI application</p></main></body></html>')
    return path


def test_project_metadata_and_application_opt_in(tmp_path):
    path = page(tmp_path, ORIGIN, "Demo")
    graph = project_graph(ORIGIN, "Demo", "Demo", ORIGIN, OWNER, META, {}, "2026-01-01T12:00:00+00:00")
    assert "SoftwareApplication" not in [n["@type"] for n in graph["@graph"]]
    original_body = path.read_text().split("</head>", 1)[1]
    inject(path, graph)
    assert path.read_text().split("</head>", 1)[1] == original_body
    assert json.loads("".join(Page(path.read_text()).jsonld)) == graph
    assert "v1.0" in path.read_text()
    assert "Project metadata" not in path.read_text()
    path = page(tmp_path, ORIGIN, "Demo")
    config = {"application": {"name": "Demo app", "description": "A CLI application", "operatingSystem": "Linux"}}
    graph = project_graph(ORIGIN, "Demo", "Demo", ORIGIN, OWNER, META, config, None)
    inject(path, graph)
    assert "SoftwareApplication" in path.read_text()


def test_document_breadcrumbs_and_relationships(tmp_path):
    url = ORIGIN + "start/"
    path = page(tmp_path, url, "Start")
    graph = project_graph(ORIGIN, "Demo", "Start", url, OWNER, META, {}, None)
    inject(path, graph)
    rendered = Page(path.read_text())
    assert "BreadcrumbList" in path.read_text()
    assert 'aria-label="Breadcrumb"' not in path.read_text()
    graph["@graph"][-1]["about"] = {"@id": ORIGIN + "#missing"}
    with pytest.raises(ValueError, match="Invalid relationship"):
        validate(graph, rendered)


def test_portfolio_and_escaping(tmp_path):
    url = "https://example.github.io/"
    path = page(tmp_path, url, "Projects")
    path.write_text(path.read_text().replace("</main>", f'<ul><li><a href="{ORIGIN}">demo</a></li></ul></main>'))
    graph = portfolio_graph(url, "Projects", OWNER, [("demo", ORIGIN)])
    inject(path, graph)
    assert '"numberOfItems": 1' in path.read_text()
    path = page(tmp_path, ORIGIN, "Demo")
    graph = project_graph(ORIGIN, "Demo", "Demo", ORIGIN, OWNER, META,
                          {"description": "</script><script>bad</script>"}, None)
    inject(path, graph)
    assert "</script><script>bad" not in path.read_text()


def test_overrides_and_git_history(tmp_path):
    config = tmp_path / "schema.json"
    config.write_text('{"runtimePlatform":"Python 3.14"}')
    assert read_overrides(config)["runtimePlatform"] == "Python 3.14"
    config.write_text('{"invented":true}')
    with pytest.raises(ValueError, match="Unsupported"):
        read_overrides(config)
    subprocess.run(["git", "init", "-q", str(tmp_path)], check=True)
    source = tmp_path / "Home.md"
    source.write_text("# Home")
    subprocess.run(["git", "add", "Home.md"], cwd=tmp_path, check=True)
    subprocess.run(["git", "-c", "user.name=Test", "-c", "user.email=test@example.com", "commit", "-qm", "docs"], cwd=tmp_path, check=True)
    assert modified(source, tmp_path)


def test_mismatched_existing_content_is_rejected(tmp_path):
    path = page(tmp_path, ORIGIN, "Actual title")
    graph = project_graph(ORIGIN, "Demo", "Invented title", ORIGIN, OWNER, META, {}, None)
    original = path.read_text()
    with pytest.raises(ValueError, match="visible heading"):
        inject(path, graph)
    assert path.read_text() == original
