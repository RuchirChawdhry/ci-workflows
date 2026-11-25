"""Test sitemap discovery and root generation without live network access."""
from pathlib import Path
import xml.etree.ElementTree as ET
from urllib.robotparser import RobotFileParser

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / ".github/workflows/sitemap-index.yml"


def load():
    workflow = yaml.load(WORKFLOW.read_text(), Loader=yaml.BaseLoader)
    run = workflow["jobs"]["build"]["steps"][1]["run"]
    namespace = {"__name__": "test_sitemap"}
    exec(compile(run.split("<<'PY'\n", 1)[1].rsplit("\nPY", 1)[0], str(WORKFLOW), "exec"), namespace)
    return workflow, namespace


def test_workflow_contract():
    workflow, _ = load()
    assert set(workflow["on"]) == {"workflow_call"}
    assert ".github.io" in workflow["jobs"]["build"]["if"]
    assert workflow["jobs"]["build"]["permissions"] == {"contents": "read"}
    assert workflow["jobs"]["deploy"]["permissions"] == {"pages": "write", "id-token": "write"}
    assert workflow["jobs"]["deploy"]["needs"] == "build"


def test_discovery_flattens_indexes_and_excludes_other_hosts(tmp_path):
    _, ns = load()
    base = "https://example.github.io/demo/"
    prefix = '<sitemapindex xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'
    index = prefix + f"<sitemap><loc>{base}sitemap-0.xml</loc></sitemap>" + "<sitemap><loc>https://other.example/sitemap.xml</loc></sitemap></sitemapindex>"
    urlset = (
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'
        f"<url><loc>{base.rstrip('/')}</loc></url>"
        f"<url><loc>{base}docs/</loc></url>"
        f"<url><loc>{base}docs/</loc></url></urlset>"
    )
    responses = {base + "sitemap-index.xml": index, base + "sitemap-0.xml": urlset}
    ns["request"] = lambda url: (url, responses[url].encode())
    projects = ns["discover"]("Example", [
        {"name": "demo", "has_pages": True, "private": False},
        {"name": "hidden", "has_pages": True, "private": True},
        {"name": "example.github.io", "has_pages": True},
    ])
    assert projects == [("demo", base, {base + "sitemap-0.xml": {base.rstrip("/"), base + "docs/"}})]
    ns["generate"]("Example", projects, tmp_path)
    root = ET.parse(tmp_path / "sitemap.xml").getroot()
    assert root.tag == ns["tag"]("urlset")
    locs = [entry.findtext(ns["tag"]("loc")) for entry in root]
    assert locs == ["https://example.github.io/", base.rstrip("/"), base + "docs/"]
    index = ET.parse(tmp_path / "sitemaps.xml").getroot()
    assert index.tag == ns["tag"]("sitemapindex")
    assert [entry.findtext(ns["tag"]("loc")) for entry in index] == [
        base + "sitemap-0.xml", "https://example.github.io/sitemap.xml"
    ]
    assert not (tmp_path / "sitemap-root.xml").exists()
    assert "Sitemap: https://example.github.io/sitemaps.xml" in (tmp_path / "robots.txt").read_text()
    assert base in (tmp_path / "index.html").read_text()


def test_empty_portfolio_and_sitemap_limits(tmp_path):
    _, ns = load()
    assert ns["generate"]("Example", [], tmp_path) == (1, 1)
    root = ET.parse(tmp_path / "sitemap.xml").getroot()
    assert [entry.findtext(ns["tag"]("loc")) for entry in root] == ["https://example.github.io/"]
    ns["MAX_ENTRIES"] = 1
    with pytest.raises(ValueError, match="entry sitemap limit"):
        ns["write_xml"](tmp_path / "oversized.xml", "urlset", "url", ["https://example.github.io/", "https://example.github.io/demo/"])
    ns["LIMIT"] = 1
    with pytest.raises(ValueError, match="MB sitemap limit"):
        ns["write_xml"](tmp_path / "oversized.xml", "urlset", "url", ["https://example.github.io/"])


def test_robots_explicitly_allows_crawlers_and_lists_all_sitemaps(tmp_path):
    _, ns = load()
    host = "https://example.github.io/"
    leaves = {host + "demo/sitemap-0.xml", host + "other/sitemap.xml"}
    path = tmp_path / "robots.txt"
    ns["write_robots"](path, host, leaves)
    lines = path.read_text().splitlines()
    agents = [line.split(": ", 1)[1] for line in lines if line.startswith("User-agent: ")]
    assert len(agents) == 78
    assert len({agent.lower() for agent in agents}) == len(agents)
    assert {"GPTBot", "OAI-SearchBot", "ClaudeBot", "Google-Extended", "Applebot-Extended",
            "Googlebot", "bingbot", "AhrefsBot", "SemrushBot", "CCBot",
            "archive.org_bot", "TurnitinBot", "*"} <= set(agents)
    assert not any(line.startswith("Disallow:") for line in lines)
    parser = RobotFileParser()
    parser.parse(lines)
    for agent in [*agents, "UnlistedResearchBot"]:
        assert parser.can_fetch(agent, host + "demo/docs/")
    assert parser.site_maps() == [host + "sitemaps.xml", host + "sitemap.xml", *sorted(leaves)]
