"""Build a Starlight documentation site and agent-readable files from wiki Markdown."""
import argparse
import html
import json
from pathlib import Path
import re
from urllib.parse import urlsplit

from markdown_it import MarkdownIt
from mdformat.renderer import MDRenderer
from mdformat_gfm import plugin as gfm

PAGE_NAME = re.compile(r"[A-Za-z0-9]+(?:-[A-Za-z0-9]+)*")


def parser():
    md = MarkdownIt(renderer_cls=MDRenderer)
    md.options.update(mdformat={"wrap": "keep"}, store_labels=True,
                      parser_extension=[gfm], codeformatters={})
    gfm.update_mdit(md)
    return md


def link_tokens(tokens):
    for token in tokens:
        if token.type == "link_open":
            yield token
        if token.children:
            yield from link_tokens(token.children)


def wiki_target(href):
    url = urlsplit(href)
    name = url.path.removesuffix(".md")
    if not (url.scheme or url.netloc or url.query) and PAGE_NAME.fullmatch(name):
        return name, ("#" + url.fragment if url.fragment else "")
    return None


def rewrite(text, paths, origin, markdown):
    md = parser()
    env = {}
    tokens = md.parse(text, env)
    for token in link_tokens(tokens):
        target = wiki_target(token.attrGet("href"))
        if target is None:
            continue
        name, fragment = target
        if name not in paths:
            raise ValueError(f"Unknown wiki page: {name}")
        token.attrSet("href", f"{origin}{paths[name]}{'index.md' if markdown else ''}{fragment}")
        # Rewritten reference links become inline links; image references remain untouched.
        token.meta.pop("label", None)
    return md.renderer.render(tokens, md.options, env)


def site_settings(wiki):
    path = wiki / "_Site.json"
    return json.loads(path.read_text(encoding="utf-8")) if path.is_file() else {}


def landing_cards(body):
    """Render the authored Highlights list as cards, leaving Markdown mirrors unchanged."""
    pattern = r"(?m)^## Highlights[ \t]*\n\n((?:- \*\*[^\n]+\*\*: [^\n]+\n?)+)"
    match = re.search(pattern, body)
    if not match:
        raise ValueError("Landing page requires a Highlights list of '**Title**: Description' entries")
    cards = []
    for title, description in re.findall(r"(?m)^- \*\*(.+?)\*\*: (.+)$", match.group(1)):
        cards.append(f"<li><strong>{html.escape(title)}</strong><span>{html.escape(description)}</span></li>")
    grid = '<ul class="project-highlights" aria-label="Highlights">' + "".join(cards) + "</ul>\n\n"
    return body[:match.start()] + "## Highlights\n\n" + grid + body[match.end():]


def prepare(wiki, site, origin, repo_url, description):
    origin = origin.rstrip("/") + "/"
    settings = site_settings(wiki)
    files = {p.stem: p for p in sorted(wiki.glob("*.md")) if not p.name.startswith("_")}
    if "Home" not in files:
        raise ValueError("wiki/Home.md is required")
    if any(p.is_symlink() or not PAGE_NAME.fullmatch(name) for name, p in files.items()):
        raise ValueError("Wiki pages must be regular Markdown files with hyphenated ASCII names")
    paths = {name: "" if name == "Home" else name.lower() + "/" for name in files}
    if len(set(paths.values())) != len(paths):
        raise ValueError("Wiki page routes collide")
    sidebar = wiki / "_Sidebar.md"
    order = ["Home"]
    if sidebar.is_file():
        for token in link_tokens(parser().parse(sidebar.read_text(encoding="utf-8"))):
            target = wiki_target(token.attrGet("href"))
            if target and target[0] in files:
                order.append(target[0])
    order = list(dict.fromkeys([*order, *files]))
    content = site / "src/content/docs"
    public = site / "public"
    content.mkdir(parents=True, exist_ok=True)
    public.mkdir(parents=True, exist_ok=True)
    entries, full, navigation = [], [], []
    for name in order:
        text = files[name].read_text(encoding="utf-8").strip()
        heading, sep, body = text.partition("\n")
        if not heading.startswith("# "):
            raise ValueError(f"{name} must begin with an H1")
        title = heading[2:].strip()
        route = paths[name]
        mirror = public / route / "index.md"
        mirror.parent.mkdir(parents=True, exist_ok=True)
        raw = rewrite(text, paths, origin, True)
        mirror.write_text(raw, encoding="utf-8")
        full.append(raw)
        entries.append(f"- [{title}]({origin}{route}index.md)")
        navigation.append({"label": title, "link": origin + route})
        head = [
            {"tag": "link", "attrs": {"rel": "alternate", "type": "text/markdown", "href": origin + route + "index.md"}},
            {"tag": "link", "attrs": {"rel": "describedby", "href": origin + "llms.txt"}},
        ]
        landing = name == "Home" and settings.get("landing", False)
        document = f"---\ntitle: {json.dumps(title)}\nhead: {json.dumps(head)}\n---\n\n"
        rendered = rewrite(body, paths, origin, False)
        if landing:
            rendered = landing_cards(rendered)
        (content / ("index.md" if not route else route.rstrip("/") + ".md")).write_text(
            document + rendered, encoding="utf-8")
    title = files["Home"].read_text(encoding="utf-8").splitlines()[0][2:].strip()
    summary = " ".join(description.split())
    index = f"# {title}\n\n> {summary}\n\nSource: {repo_url}\n\n## Documentation\n\n"
    (public / "llms.txt").write_text(index + "\n".join(entries) + f"\n\n## Complete documentation\n\n- [All pages]({origin}llms-full.txt)\n", encoding="utf-8")
    (public / "llms-full.txt").write_text("\n\n---\n\n".join(full), encoding="utf-8")
    (site / "docs-meta.json").write_text(json.dumps({"title": settings.get("title", title), "description": summary, "repo": repo_url, "sidebar": navigation}), encoding="utf-8")
    print(f"Prepared {len(files)} wiki pages and Markdown mirrors")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--wiki", type=Path, required=True)
    parser.add_argument("--site", type=Path, required=True)
    parser.add_argument("--origin", required=True)
    parser.add_argument("--repo", required=True)
    parser.add_argument("--description", required=True)
    args = parser.parse_args()
    prepare(args.wiki, args.site, args.origin, args.repo, args.description)
