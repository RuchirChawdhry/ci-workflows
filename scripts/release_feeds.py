"""Aggregate native public GitHub release feeds into portable syndication formats."""
import argparse
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from email.utils import format_datetime
from html import escape
import json
import os
from pathlib import Path
from urllib.error import HTTPError
from urllib.parse import quote, urlsplit
import xml.etree.ElementTree as ET

from rss import api_pages, get, MAX_BYTES

ATOM = "http://www.w3.org/2005/Atom"
A = f"{{{ATOM}}}"
JSON_VERSION = "https://jsonfeed.org/version/1.1"


def timestamp(value):
    result = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if result.tzinfo is None:
        raise ValueError("Atom timestamp has no timezone")
    return result.astimezone(timezone.utc)


def iso(value):
    return value.isoformat().replace("+00:00", "Z")


def project_url(owner, name):
    return f"https://github.com/{quote(owner, safe='')}/{quote(name, safe='')}"


def parse(data, owner, name):
    source = project_url(owner, name)
    text = data.decode("utf-8-sig")
    if "<!DOCTYPE" in text.upper() or "<!ENTITY" in text.upper():
        raise ValueError("DTD/entity declarations are forbidden")
    root = ET.fromstring(text)
    if root.tag != A + "feed":
        raise ValueError(f"Expected Atom feed: {source}")
    items = []
    for entry in root.findall(A + "entry"):
        id_ = entry.findtext(A + "id", "").strip()
        title = entry.findtext(A + "title", "").strip()
        updated = timestamp(entry.findtext(A + "updated", ""))
        published = entry.findtext(A + "published")
        alternate = next((link.get("href", "") for link in entry.findall(A + "link")
                          if link.get("rel", "alternate") == "alternate"), "")
        link = urlsplit(alternate)
        prefix = f"/{owner}/{name}/releases/tag/".lower()
        if (not id_ or not title or link.scheme != "https" or link.netloc != "github.com"
                or not link.path.lower().startswith(prefix)):
            raise ValueError(f"Invalid release entry: {source}")
        content = entry.find(A + "content")
        if content is None:
            content = entry.find(A + "summary")
        kind = content.get("type", "text") if content is not None else "text"
        body = content.text or "" if content is not None else ""
        # GitHub renders/sanitizes release HTML; no arbitrary external feed URLs are fetched.
        if kind != "html":
            body = escape(body)
        author = entry.findtext(A + "author/" + A + "name") or root.findtext(A + "author/" + A + "name") or owner
        items.append(dict(id=id_, title=f"{name}: {title}", url=alternate, content_html=body,
                          author=author, project=name, updated=updated,
                          published=timestamp(published) if published else None))
    return items


def fetch_project(owner, repo):
    name = repo["name"]
    source = project_url(owner, name)
    try:
        items = parse(get(source + "/releases.atom"), owner, name)
    except HTTPError as error:
        if error.code in {404, 410}:
            print(f"No native feed: {name}")
            return None
        raise
    if not items:
        return None
    print(f"Discovered {name}: {len(items)} release entries")
    return dict(name=name, url=source, description=repo.get("description") or "", items=items)


def discover(owner, token):
    repos = sorted((repo for repo in api_pages(f"users/{quote(owner)}/repos", token)
                    if not repo["private"] and repo["owner"]["login"].casefold() == owner.casefold()),
                   key=lambda repo: repo["name"].casefold())
    with ThreadPoolExecutor(max_workers=4) as pool:
        projects = pool.map(lambda repo: fetch_project(owner, repo), repos)
        return [project for project in projects if project is not None]


def sort_items(items, limit):
    unique = {}
    for item in items:
        previous = unique.get(item["id"])
        if previous is None or item["updated"] > previous["updated"]:
            unique[item["id"]] = item
    return sorted(unique.values(), key=lambda item: (item["published"] or item["updated"], item["id"]),
                  reverse=True)[:limit]


def write_xml(path, root):
    ET.indent(root)
    data = ET.tostring(root, encoding="utf-8", xml_declaration=True)
    if len(data) > MAX_BYTES:
        raise ValueError(f"Feed exceeds size limit: {path}")
    ET.fromstring(data)
    path.write_bytes(data)


def fields(node, values):
    for tag, value in values.items():
        ET.SubElement(node, tag).text = value


def rss_feed(path, base, title, items):
    root = ET.Element("rss", {"version": "2.0", "xmlns:atom": ATOM})
    channel = ET.SubElement(root, "channel")
    fields(channel, dict(title=title, link=base, description="Public GitHub project release updates"))
    ET.SubElement(channel, "atom:link", href=base + "feed.rss", rel="self", type="application/rss+xml")
    if items:
        fields(channel, dict(lastBuildDate=format_datetime(max(item["updated"] for item in items), usegmt=True)))
    for item in items:
        node = ET.SubElement(channel, "item")
        fields(node, dict(title=item["title"], link=item["url"], description=item["content_html"],
                          category=item["project"], pubDate=format_datetime(item["published"] or item["updated"], usegmt=True)))
        ET.SubElement(node, "guid", isPermaLink="false").text = item["id"]
    write_xml(path, root)


def atom_feed(path, base, title, items):
    # Scope the default namespace to this document, not the process.
    root = ET.Element("feed", xmlns=ATOM)
    updated = max((item["updated"] for item in items), default=datetime(1970, 1, 1, tzinfo=timezone.utc))
    fields(root, dict(id=base + "feed.atom", title=title, updated=iso(updated)))
    ET.SubElement(root, "link", rel="self", href=base + "feed.atom", type="application/atom+xml")
    ET.SubElement(root, "link", rel="alternate", href=base + "feeds/")
    fields(ET.SubElement(root, "author"), dict(name=title))
    for item in items:
        node = ET.SubElement(root, "entry")
        fields(node, dict(id=item["id"], title=item["title"], updated=iso(item["updated"])))
        if item["published"]:
            fields(node, dict(published=iso(item["published"])))
        ET.SubElement(node, "link", rel="alternate", href=item["url"])
        ET.SubElement(node, "category", term=item["project"])
        fields(ET.SubElement(node, "author"), dict(name=item["author"]))
        ET.SubElement(node, "content", type="html").text = item["content_html"]
    write_xml(path, root)


def json_feed(path, base, title, items):
    entries = []
    for item in items:
        entry = dict(id=item["id"], title=item["title"], url=item["url"], content_html=item["content_html"],
                     date_modified=iso(item["updated"]), authors=[dict(name=item["author"])], tags=[item["project"]])
        if item["published"]:
            entry["date_published"] = iso(item["published"])
        entries.append(entry)
    data = json.dumps(dict(version=JSON_VERSION, title=title, home_page_url=base + "feeds/",
                           feed_url=base + "feed.json", items=entries), ensure_ascii=False, indent=2)
    if len(data.encode("utf-8")) > MAX_BYTES:
        raise ValueError("JSON feed exceeds size limit")
    path.write_text(data + "\n", encoding="utf-8")


def opml(path, title, projects):
    root = ET.Element("opml", version="2.0")
    fields(ET.SubElement(root, "head"), dict(title=title))
    body = ET.SubElement(root, "body")
    for project in projects:
        ET.SubElement(body, "outline", type="rss", text=project["name"], title=project["name"],
                      xmlUrl=project["url"] + "/releases.atom", htmlUrl=project["url"] + "/releases")
    write_xml(path, root)


def directory(path, title, projects):
    rows = []
    for project in projects:
        name, url = escape(project["name"]), escape(project["url"], quote=True)
        description = escape(project["description"])
        latest = sort_items(project["items"], 1)[0]
        rows.append(f'<article><h2><a href="{url}">{name}</a></h2><p>{description}</p>'
                    f'<p><a href="{escape(latest["url"], quote=True)}">{escape(latest["title"])}</a> '
                    f'<time>{(latest["published"] or latest["updated"]).date()}</time></p>'
                    f'<a href="{url}/releases.atom">Subscribe (Atom)</a></article>')
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{escape(title)} — feeds</title>
<link rel="alternate" type="application/rss+xml" href="../feed.rss">
<link rel="alternate" type="application/atom+xml" href="../feed.atom">
<link rel="alternate" type="application/feed+json" href="../feed.json">
<style>
:root{{color-scheme:light dark;font:16px/1.6 system-ui,sans-serif}}body{{max-width:840px;margin:3rem auto;padding:0 1.25rem}}h1{{line-height:1.1}}a{{color:LinkText}}nav{{display:flex;flex-wrap:wrap;gap:1rem}}article{{border-top:1px solid gray;padding:1rem 0}}h2{{margin:0;font-size:1.25rem}}input{{box-sizing:border-box;width:100%;padding:.7rem;margin:1rem 0;font:inherit}}time{{opacity:.75;white-space:nowrap}}
</style></head><body><main><a href="../">Portfolio</a><h1>Project subscriptions</h1>
<p>Follow all releases or subscribe to individual projects. Import OPML into your feed reader to follow each project separately.</p>
<nav><a href="../feed.rss">RSS 2.0</a><a href="../feed.atom">Atom</a><a href="../feed.json">JSON Feed</a><a href="../feeds.opml">Import OPML</a></nav>
<label for="search">Search {len(projects)} projects</label><input id="search" type="search" placeholder="Project name or description">
<section>{''.join(rows)}</section></main>
<script>document.querySelector('#search').addEventListener('input',event=>{{const query=event.target.value.toLowerCase();document.querySelectorAll('article').forEach(card=>card.hidden=!card.textContent.toLowerCase().includes(query));}});</script>
</body></html>""", encoding="utf-8")


def generate(output, owner, projects, limit):
    output.mkdir(parents=True, exist_ok=True)
    base = f"https://{owner.lower()}.github.io/"
    title = f"{owner} — project releases"
    items = sort_items((item for project in projects for item in project["items"]), limit)
    rss_feed(output / "feed.rss", base, title, items)
    (output / "rss.xml").unlink(missing_ok=True)
    atom_feed(output / "feed.atom", base, title, items)
    json_feed(output / "feed.json", base, title, items)
    opml(output / "feeds.opml", title, projects)
    directory(output / "feeds/index.html", title, projects)
    print(f"Generated four feed files and directory: {len(projects)} projects, {len(items)} entries")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--limit", type=int, default=200)
    args = parser.parse_args()
    if not 1 <= args.limit <= 1000:
        parser.error("--limit must be between 1 and 1000")
    owner, repo = os.environ["GITHUB_REPOSITORY"].split("/")
    if repo.casefold() != f"{owner}.github.io".casefold():
        parser.error("Run portfolio mode only from OWNER.github.io")
    generate(args.output, owner, discover(owner, os.environ["GH_TOKEN"]), args.limit)


if __name__ == "__main__":
    main()
