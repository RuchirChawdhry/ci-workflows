"""Test sitemap discovery and root generation without live network access."""
from pathlib import Path
import xml.etree.ElementTree as ET

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
    urlset = '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">' + f"<url><loc>{base.rstrip(chr(47))}</loc></url></urlset>"
    responses = {base + "sitemap-index.xml": index, base + "sitemap-0.xml": urlset}
    ns["request"] = lambda url: (url, responses[url].encode())
    projects = ns["discover"]("Example", [
        {"name": "demo", "has_pages": True, "private": False},
        {"name": "hidden", "has_pages": True, "private": True},
        {"name": "example.github.io", "has_pages": True},
    ])
    assert projects == [("demo", base, [base + "sitemap-0.xml"])]
    ns["generate"]("Example", projects, tmp_path)
    root = ET.parse(tmp_path / "sitemap.xml").getroot()
    locs = [entry.findtext(ns["tag"]("loc")) for entry in root]
    assert locs == [base + "sitemap-0.xml", "https://example.github.io/sitemap-root.xml"]
    assert "Sitemap: https://example.github.io/sitemap.xml" in (tmp_path / "robots.txt").read_text()
    assert base in (tmp_path / "index.html").read_text()
