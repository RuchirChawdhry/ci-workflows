"""Generate and verify JSON-LD for portfolio and wiki documentation HTML."""
import argparse
from datetime import datetime
from html.parser import HTMLParser
import json
import os
from pathlib import Path
import subprocess
from urllib.error import HTTPError
from urllib.parse import urljoin, urlsplit
from urllib.request import Request, urlopen

CONTEXT = "https://schema.org"
COMMON = {"name", "url", "description"}
WORK = COMMON | {"publisher", "isPartOf", "about", "mainEntity", "mainEntityOfPage", "dateModified", "inLanguage"}
FIELDS = {
    "Person": COMMON | {"sameAs"},
    "Organization": COMMON | {"sameAs"},
    "WebSite": WORK,
    "WebPage": WORK | {"breadcrumb"},
    "CollectionPage": WORK | {"breadcrumb"},
    "SoftwareSourceCode": WORK | {"codeRepository", "programmingLanguage", "runtimePlatform", "license", "keywords", "version", "maintainer"},
    "SoftwareApplication": WORK | {"applicationCategory", "operatingSystem", "softwareVersion", "softwareRequirements", "downloadUrl", "license"},
    "TechArticle": WORK | {"headline"},
    "APIReference": WORK | {"headline"},
    "BreadcrumbList": {"itemListElement"},
    "ItemList": {"itemListElement", "numberOfItems"},
    "ListItem": {"position", "name", "item"},
}
REF_TYPES = {
    "publisher": {"Person", "Organization"}, "maintainer": {"Person", "Organization"},
    "isPartOf": {"WebSite"}, "mainEntityOfPage": {"WebPage", "CollectionPage"},
    "breadcrumb": {"BreadcrumbList"},
    "mainEntity": {"SoftwareSourceCode", "SoftwareApplication", "TechArticle", "APIReference", "ItemList"},
    "about": {"SoftwareSourceCode", "SoftwareApplication", "Person", "Organization"},
}
URL_FIELDS = {"url", "sameAs", "codeRepository", "license", "downloadUrl"}
TEXT_FIELDS = {"name", "description", "headline", "programmingLanguage", "runtimePlatform", "keywords", "version", "softwareVersion", "applicationCategory", "operatingSystem", "softwareRequirements"}
OVERRIDES = {"description", "programmingLanguage", "runtimePlatform", "application", "pageTypes"}
APP_FIELDS = {"name", "description", "applicationCategory", "operatingSystem", "softwareRequirements", "downloadUrl"}


def api(path, optional=False):
    request = Request("https://api.github.com/" + path, headers={
        "Authorization": "Bearer " + os.environ["GH_TOKEN"],
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    })
    try:
        with urlopen(request, timeout=20) as response:
            return json.load(response)
    except HTTPError as error:
        if optional and error.code == 404:
            return {}
        raise


def repository_metadata(repository):
    data = api("repos/" + repository)
    release = api("repos/" + repository + "/releases/latest", optional=True)
    license_data = api("repos/" + repository + "/license", optional=True)
    return {
        "name": data["name"], "url": data["html_url"], "description": data.get("description") or "",
        "language": data.get("language"), "topics": data.get("topics") or [],
        "license": license_data.get("html_url"),
        "license_name": (license_data.get("license") or {}).get("spdx_id"),
        "release": release.get("tag_name"), "release_url": release.get("html_url"),
    }


def identity(owner, profile):
    origin = f"https://{owner.lower()}.github.io/"
    kind = "Organization" if profile.get("type") == "Organization" else "Person"
    return {"@id": origin + "#identity", "@type": kind,
            "name": profile.get("name") or profile.get("login") or owner,
            "url": profile.get("html_url") or f"https://github.com/{owner}"}


def node(kind, identifier, **values):
    return {"@type": kind, "@id": identifier, **{key: value for key, value in values.items() if value is not None and value != "" and value != []}}


def ref(value):
    return {"@id": value["@id"] if isinstance(value, dict) else value}


def url_ok(value):
    parts = urlsplit(value)
    return parts.scheme == "https" and bool(parts.netloc) and not parts.username and not parts.password


def strings(value):
    values = value if isinstance(value, list) else [value]
    if not values or any(not isinstance(v, str) or not v.strip() for v in values):
        raise ValueError("Expected nonempty text")
    return values


def read_overrides(path):
    config = json.loads(path.read_text(encoding="utf-8")) if path.is_file() else {}
    if not isinstance(config, dict) or set(config) - OVERRIDES:
        raise ValueError("Unsupported schema.json override")
    for key in ("description", "programmingLanguage", "runtimePlatform"):
        if key in config:
            strings(config[key])
            if key != "programmingLanguage" and not isinstance(config[key], str):
                raise ValueError(f"{key} must be text")
    app = config.get("application")
    if app is not None:
        if not isinstance(app, dict) or set(app) - APP_FIELDS or not {"name", "description"} <= set(app):
            raise ValueError("application requires name and description; unknown keys are rejected")
        for key, value in app.items():
            strings(value)
            if not isinstance(value, str):
                raise ValueError(f"application.{key} must be text")
        if "downloadUrl" in app and not url_ok(app["downloadUrl"]):
            raise ValueError("application.downloadUrl must be HTTPS")
    types = config.get("pageTypes", {})
    if not isinstance(types, dict) or any(v not in {"TechArticle", "APIReference"} for v in types.values()):
        raise ValueError("pageTypes supports TechArticle and APIReference")
    return config


def modified(path, repo):
    result = subprocess.run(
        ["git", "log", "-1", "--follow", "--format=%cI", "--", str(path.relative_to(repo))],
        cwd=repo, check=True, capture_output=True, text=True,
    ).stdout.strip()
    return result or None


def list_items(entries):
    return [{"@type": "ListItem", "position": i, "name": name, "item": url}
            for i, (name, url) in enumerate(entries, 1)]


def project_graph(origin, site_title, title, url, owner, metadata, config, date, page_type="TechArticle"):
    website = node("WebSite", origin + "#website", name=site_title, url=origin, publisher=ref(owner))
    source = node("SoftwareSourceCode", origin + "#source", name=metadata["name"], url=origin,
                  codeRepository=metadata["url"], description=config.get("description", metadata["description"]),
                  programmingLanguage=config.get("programmingLanguage", metadata["language"]),
                  runtimePlatform=config.get("runtimePlatform"), license=metadata["license"],
                  keywords=metadata["topics"], version=metadata["release"], maintainer=ref(owner))
    page = node("WebPage", url + "#page", name=title, url=url, isPartOf=ref(website), dateModified=date)
    nodes = [owner, website, source, page]
    if url == origin:
        page["mainEntity"] = ref(source)
        if config.get("application"):
            app = node("SoftwareApplication", origin + "#application", url=origin,
                       **config["application"], softwareVersion=metadata["release"], license=metadata["license"],
                       publisher=ref(owner))
            source["about"] = ref(app)
            nodes.append(app)
    else:
        crumbs = node("BreadcrumbList", url + "#breadcrumbs", itemListElement=list_items([(site_title, origin), (title, url)]))
        article = node(page_type, url + "#article", headline=title, url=url, mainEntityOfPage=ref(page),
                       about=ref(source), isPartOf=ref(website), dateModified=date)
        page.update(breadcrumb=ref(crumbs), mainEntity=ref(article))
        nodes.extend([crumbs, article])
    return {"@context": CONTEXT, "@graph": nodes}


def portfolio_graph(origin, title, owner, entries):
    website = node("WebSite", origin + "#website", name=title, url=origin, publisher=ref(owner))
    collection = node("CollectionPage", origin + "#page", name=title, url=origin,
                      isPartOf=ref(website), mainEntity=ref(origin + "#projects"), about=ref(owner))
    projects = node("ItemList", origin + "#projects", numberOfItems=len(entries), itemListElement=list_items(entries))
    return {"@context": CONTEXT, "@graph": [owner, website, collection, projects]}


class Page(HTMLParser):
    def __init__(self, document):
        super().__init__(convert_charrefs=True)
        self.text, self.links, self.h1, self.jsonld = [], [], [], []
        self.hidden = None
        self.in_h1 = False
        self.in_main = False
        self.in_li = False
        self.project_links = []
        self.anchor = None
        self.anchor_text = []
        self.canonical = None
        self.feed(document)

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag in {"script", "style", "template"}:
            self.hidden = "jsonld" if tag == "script" and attrs.get("type") == "application/ld+json" else tag
        if tag == "h1":
            self.in_h1 = True
        if tag == "main":
            self.in_main = True
        if tag == "li" and self.in_main:
            self.in_li = True
        if tag == "a" and "href" in attrs:
            self.links.append(attrs["href"])
            if self.in_li:
                self.anchor, self.anchor_text = attrs["href"], []
        if tag == "link" and attrs.get("rel") == "canonical":
            self.canonical = attrs.get("href")

    def handle_endtag(self, tag):
        if tag in {"script", "style", "template"}:
            self.hidden = None
        if tag == "h1":
            self.in_h1 = False
        if tag == "main":
            self.in_main = False
        if tag == "li":
            self.in_li = False
        if tag == "a" and self.anchor:
            self.project_links.append(("".join(self.anchor_text).strip(), self.anchor))
            self.anchor = None

    def handle_data(self, data):
        if self.hidden == "jsonld":
            self.jsonld.append(data)
        if self.hidden:
            return
        self.text.append(data)
        if self.in_h1:
            self.h1.append(data)
        if self.anchor:
            self.anchor_text.append(data)


def validate(graph, page):
    if graph.get("@context") != CONTEXT or not isinstance(graph.get("@graph"), list):
        raise ValueError("Invalid JSON-LD context or graph")
    nodes = graph["@graph"]
    by_id = {item["@id"]: item for item in nodes}
    if len(by_id) != len(nodes):
        raise ValueError("Duplicate entity identifiers")
    visible = " ".join(" ".join(page.text).split())
    heading = " ".join("".join(page.h1).split())
    links = {urljoin(page.canonical or "", link).rstrip("/") for link in page.links}
    canonical = (page.canonical or "").rstrip("/")
    for item in nodes:
        kind = item["@type"]
        if kind not in FIELDS or set(item) - FIELDS[kind] - {"@id", "@type"} or not url_ok(item["@id"]):
            raise ValueError(f"Unsupported schema or property: {item}")
        for key, value in item.items():
            if key in REF_TYPES:
                if not isinstance(value, dict) or set(value) != {"@id"} or value["@id"] not in by_id or by_id[value["@id"]]["@type"] not in REF_TYPES[key]:
                    raise ValueError(f"Invalid relationship: {key} {value}")
            if key in URL_FIELDS:
                for url in strings(value):
                    if not url_ok(url):
                        raise ValueError(f"Invalid URL: {url}")
            if key in TEXT_FIELDS:
                strings(value)
        # Validate page claims against existing content; repository facts are sourced
        # separately from GitHub and explicit configuration, not invented UI.
        if kind in {"WebPage", "CollectionPage"} and " ".join(item["name"].split()) != heading:
            raise ValueError("Page name does not match the visible heading")
        if kind in {"TechArticle", "APIReference"} and " ".join(item["headline"].split()) != heading:
            raise ValueError("Article headline does not match the visible heading")
        if kind == "SoftwareSourceCode" and item["codeRepository"].rstrip("/") not in links:
            raise ValueError("Source repository is not linked from the documentation")
        if kind == "SoftwareApplication":
            for key in ("name", "description"):
                if " ".join(item[key].split()) not in visible:
                    raise ValueError(f"Application {key} must appear in authored content")
            if "downloadUrl" in item and item["downloadUrl"].rstrip("/") not in links:
                raise ValueError("Application download URL is not linked from the page")
        if "dateModified" in item:
            datetime.fromisoformat(item["dateModified"])
        if "itemListElement" in item:
            entries = item["itemListElement"]
            if item.get("numberOfItems", len(entries)) != len(entries) or (kind == "BreadcrumbList" and len(entries) < 2):
                raise ValueError("Invalid list length")
            for i, entry in enumerate(entries, 1):
                if set(entry) != {"@type", "position", "name", "item"} or entry["@type"] != "ListItem" or entry["position"] != i or not url_ok(entry["item"]):
                    raise ValueError("Invalid list entry")
                target = entry["item"].rstrip("/")
                if " ".join(entry["name"].split()) not in visible or (target not in links and target != canonical):
                    raise ValueError("List entry does not match existing navigation")
            if kind == "BreadcrumbList" and entries[-1]["item"].rstrip("/") != canonical:
                raise ValueError("Breadcrumb destination does not match page")
    pages = [n for n in nodes if n["@type"] in {"WebPage", "CollectionPage"}]
    if len(pages) != 1 or pages[0]["url"].rstrip("/") != (page.canonical or "").rstrip("/"):
        raise ValueError("Page entity does not match canonical URL")


def inject(path, graph):
    document = path.read_text(encoding="utf-8")
    if Page(document).jsonld:
        raise ValueError(f"Existing JSON-LD in {path}")
    if "</head>" not in document:
        raise ValueError(f"Cannot locate HTML head: {path}")
    payload = json.dumps(graph, ensure_ascii=True, allow_nan=False).replace("<", "\\u003c").replace(">", "\\u003e").replace("&", "\\u0026")
    document = document.replace("</head>", '<script type="application/ld+json">' + payload + "</script></head>", 1)
    page = Page(document)
    parsed = json.loads("".join(page.jsonld))
    if parsed != graph:
        raise ValueError("JSON-LD round-trip mismatch")
    validate(parsed, page)
    path.write_text(document, encoding="utf-8")


def wiki_site(dist, origin, repo, owner, metadata, config):
    wiki = repo / "wiki"
    sources = sorted(p for p in wiki.glob("*.md") if not p.name.startswith("_"))
    titles = {p.stem: p.read_text(encoding="utf-8").splitlines()[0].removeprefix("# ") for p in sources}
    if set(config.get("pageTypes", {})) - (set(titles) - {"Home"}):
        raise ValueError("pageTypes contains an unknown or homepage source")
    for path in sources:
        route = "" if path.stem == "Home" else path.stem.lower() + "/"
        url = origin + route
        graph = project_graph(origin, titles["Home"], titles[path.stem], url, owner, metadata, config,
                              modified(path, repo), config.get("pageTypes", {}).get(path.stem, "TechArticle"))
        inject(dist / route / "index.html", graph)
    print(f"Validated JSON-LD on {len(sources)} documentation pages")


def portfolio_site(dist, origin, owner):
    path = dist / "index.html"
    page = Page(path.read_text(encoding="utf-8"))
    entries = [(name, url) for name, url in page.project_links if url.startswith(origin) and url != origin]
    graph = portfolio_graph(origin, "".join(page.h1).strip(), owner, entries)
    inject(path, graph)
    print(f"Validated portfolio JSON-LD with {len(entries)} project entries")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("mode", choices=["wiki", "portfolio"])
    parser.add_argument("--dist", type=Path, required=True)
    parser.add_argument("--origin", required=True)
    parser.add_argument("--repo", type=Path, default=Path.cwd())
    args = parser.parse_args()
    repository = os.environ["GITHUB_REPOSITORY"]
    owner_name = repository.split("/")[0]
    owner = identity(owner_name, api("users/" + owner_name))
    origin = args.origin.rstrip("/") + "/"
    if args.mode == "wiki":
        wiki_site(args.dist, origin, args.repo.resolve(), owner, repository_metadata(repository),
                  read_overrides(args.repo / "schema.json"))
    else:
        portfolio_site(args.dist, origin, owner)
