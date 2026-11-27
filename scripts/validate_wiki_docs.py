"""Check generated agent files, HTML link relations, and HTML-only sitemap coverage."""
from html.parser import HTMLParser
from pathlib import Path
import re
import sys
import xml.etree.ElementTree as ET

NS = {"s": "http://www.sitemaps.org/schemas/sitemap/0.9"}


class Links(HTMLParser):
    def __init__(self):
        super().__init__()
        self.links = []

    def handle_starttag(self, tag, attrs):
        if tag == "link":
            self.links.append(dict(attrs))


def validate(dist, origin):
    index = (dist / "llms.txt").read_text()
    full = (dist / "llms-full.txt").read_text()
    assert index.startswith("# ") and "\n> " in index
    pages = set()
    for url in re.findall(r"\]\((https://[^)]+/index\.md)\)", index):
        assert url.startswith(origin), url
        mirror = dist / url.removeprefix(origin)
        raw = mirror.read_text()
        assert raw.startswith("# ") and raw in full, mirror
        page = mirror.with_suffix(".html")
        links = Links()
        links.feed(page.read_text())
        assert any(link.get("rel") == "alternate" and link.get("type") == "text/markdown" and link.get("href") == url for link in links.links), page
        assert any(link.get("rel") == "describedby" and link.get("href") == origin + "llms.txt" for link in links.links), page
        pages.add(url.removesuffix("index.md").rstrip("/"))
    assert pages
    index_xml = ET.parse(dist / "sitemap-index.xml")
    sitemap_urls = set()
    for entry in index_xml.findall("s:sitemap/s:loc", NS):
        assert entry.text.startswith(origin)
        tree = ET.parse(dist / entry.text.removeprefix(origin))
        sitemap_urls.update(loc.text.rstrip("/") for loc in tree.findall("s:url/s:loc", NS))
    assert sitemap_urls == pages, (sitemap_urls, pages)
    # Keep Astro's sitemap index and expose a flat, project-local sitemap as well.
    ET.register_namespace("", NS["s"])
    root = ET.Element(f"{{{NS['s']}}}urlset")
    for url in sorted(sitemap_urls):
        ET.SubElement(ET.SubElement(root, f"{{{NS['s']}}}url"), f"{{{NS['s']}}}loc").text = url + "/"
    ET.ElementTree(root).write(dist / "sitemap.xml", encoding="utf-8", xml_declaration=True)
    assert {loc.text.rstrip("/") for loc in ET.parse(dist / "sitemap.xml").findall("s:url/s:loc", NS)} == pages
    print(f"Validated {len(pages)} Markdown mirrors, HTML pages and sitemap URLs; wrote sitemap.xml")


if __name__ == "__main__":
    validate(Path(sys.argv[1]), sys.argv[2])
