"""Build RSS 2.0 feeds from public GitHub releases."""
import argparse
from datetime import datetime, timezone
from email.utils import format_datetime, parsedate_to_datetime
import html
import json
import os
from pathlib import Path
import re
from urllib.parse import quote, urlsplit
from urllib.request import HTTPRedirectHandler, Request, build_opener
import xml.etree.ElementTree as ET

ATOM = "http://www.w3.org/2005/Atom"
ET.register_namespace("atom", ATOM)
MAX_BYTES = 10_000_000


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def get(url, token=None):
    headers = {"User-Agent": "ci-workflows-rss"}
    if token:
        headers.update(Authorization=f"Bearer {token}", Accept="application/vnd.github+json")
    with build_opener(NoRedirect()).open(Request(url, headers=headers), timeout=30) as response:
        data = response.read(MAX_BYTES + 1)
    if len(data) > MAX_BYTES:
        raise ValueError(f"Response too large: {url}")
    return data


def api_pages(path, token):
    page = 1
    while True:
        values = json.loads(get(f"https://api.github.com/{path}?per_page=100&page={page}", token))
        yield from values
        if len(values) < 100:
            return
        page += 1


def pages_base(owner, name):
    base = f"https://{owner.lower()}.github.io/"
    return base if name.lower() == f"{owner.lower()}.github.io" else base + quote(name, safe="") + "/"


def clean(value):
    return re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f\ufffe\uffff]", "", value or "")


def release_items(repository, releases, prereleases=False):
    for release in releases:
        if release["draft"] or (release["prerelease"] and not prereleases) or not release.get("published_at"):
            continue
        yield {
            "title": f"{repository.split('/')[-1]}: {release.get('name') or release['tag_name']}",
            "link": release["html_url"],
            "guid": f"github-release:{release['id']}",
            "description": html.escape(clean(release.get("body"))).replace("\n", "<br>"),
            "pubDate": format_datetime(datetime.fromisoformat(release["published_at"].replace("Z", "+00:00")), usegmt=True),
            "category": repository.split("/")[-1],
        }


def date(item):
    result = parsedate_to_datetime(item["pubDate"])
    if result.tzinfo is None:
        raise ValueError("RSS date must contain a timezone")
    return result.astimezone(timezone.utc)


def select(items, limit):
    unique = {}
    for item in items:
        key = item["guid"]
        if key not in unique or date(item) > date(unique[key]):
            unique[key] = item
    return sorted(unique.values(), key=lambda item: (date(item), item["guid"]), reverse=True)[:limit]


def write_feed(output, title, base, items, limit):
    root = ET.Element("rss", version="2.0")
    channel = ET.SubElement(root, "channel")
    for name, value in {"title": title, "link": base, "description": f"Published updates for {title}"}.items():
        ET.SubElement(channel, name).text = clean(value)
    ET.SubElement(channel, "generator").text = "ci-workflows RSS"
    ET.SubElement(channel, f"{{{ATOM}}}link", href=base + "rss.xml", rel="self", type="application/rss+xml")
    selected = select(items, limit)
    if selected:
        ET.SubElement(channel, "lastBuildDate").text = format_datetime(date(selected[0]), usegmt=True)
    for item in selected:
        node = ET.SubElement(channel, "item")
        for field in ("title", "link", "description", "pubDate", "category", "guid"):
            attrs = {"isPermaLink": "false"} if field == "guid" else {}
            ET.SubElement(node, field, attrs).text = clean(item[field])
    ET.indent(root)
    output.parent.mkdir(parents=True, exist_ok=True)
    data = ET.tostring(root, encoding="utf-8", xml_declaration=True)
    if len(data) > MAX_BYTES:
        raise ValueError("Generated feed exceeds size limit")
    ET.fromstring(data)
    output.write_bytes(data)
    print(f"Generated {output}: {len(selected)} items")


def parse_project(data, owner, name):
    data = data.decode("utf-8-sig")
    if "<!DOCTYPE" in data.upper() or "<!ENTITY" in data.upper():
        raise ValueError("DTD/entity declarations are not allowed")
    root = ET.fromstring(data)
    if root.tag != "rss" or root.get("version") != "2.0" or root.find("channel") is None:
        raise ValueError("Expected RSS 2.0 channel")
    if root.findtext("channel/generator") != "ci-workflows RSS":
        print(f"Skipping unrelated RSS feed: {name}")
        return
    for node in root.findall("channel/item"):
        item = {field: node.findtext(field, "").strip() for field in ("title", "link", "description", "pubDate", "guid")}
        prefix = f"/{owner}/{name}/releases/tag/".lower()
        link = urlsplit(item["link"])
        if link.scheme != "https" or link.netloc != "github.com" or not link.path.lower().startswith(prefix):
            raise ValueError(f"Unexpected release link: {item['link']}")
        if not item["title"] or not re.fullmatch(r"github-release:\d+", item["guid"]):
            raise ValueError("Missing title or invalid release GUID")
        date(item)
        # Treat third-party feed descriptions as text; preserve safe HTML from our own generator.
        item["description"] = html.escape(html.unescape(item["description"].replace("<br>", "\n"))).replace("\n", "<br>")
        item["category"] = name
        yield item


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=("project", "portfolio"))
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--limit", type=int, default=100)
    parser.add_argument("--include-prereleases", action="store_true")
    args = parser.parse_args()
    if not 1 <= args.limit <= 1000:
        parser.error("--limit must be between 1 and 1000")
    repository = os.environ["GITHUB_REPOSITORY"]
    owner, name = repository.split("/")
    token = os.environ["GH_TOKEN"]
    metadata = json.loads(get(f"https://api.github.com/repos/{repository}", token))
    if metadata["private"] or metadata.get("visibility") != "public":
        raise ValueError("RSS publication is supported only for public repositories")
    base = pages_base(owner, name)
    if args.mode == "portfolio":
        if name.lower() != f"{owner.lower()}.github.io":
            raise ValueError("Portfolio mode must run in the owner's GitHub Pages user-site repository")
        from release_feeds import discover, rss_feed, sort_items
        projects = discover(owner, token)
        items = sort_items((item for project in projects for item in project["items"]), args.limit)
        args.output.parent.mkdir(parents=True, exist_ok=True)
        rss_feed(args.output, base, f"{owner} — project releases", items)
        return
    else:
        items = release_items(repository, api_pages(f"repos/{repository}/releases", token), args.include_prereleases)
        title = f"{name} releases"
    write_feed(args.output, title, base, items, args.limit)


if __name__ == "__main__":
    main()
