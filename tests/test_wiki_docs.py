from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from wiki_docs import prepare, rewrite, parser, link_tokens


def test_wiki_docs(tmp_path):
    wiki = tmp_path / "wiki"
    wiki.mkdir()
    (wiki / "Home.md").write_text("# Example\n\n[Start](Getting-Started)\n")
    (wiki / "Getting-Started.md").write_text("# Start\n\n[Home](Home)\n\n~~~sh\n[not a link](Unknown)\n~~~\n")
    (wiki / "_Sidebar.md").write_text("[Start](Getting-Started)\n")
    site = tmp_path / "site"
    base = "https://example.github.io/demo/"
    prepare(wiki, site, base, "https://github.com/example/demo", "Example docs")
    public = site / "public"
    assert f"[Start]({base}getting-started/index.md)" in (public / "index.md").read_text()
    assert f"[Start]({base}getting-started/)" in (site / "src/content/docs/index.md").read_text()
    assert "[not a link](Unknown)" in (public / "getting-started/index.md").read_text()
    assert f"[Start]({base}getting-started/index.md)" in (public / "llms.txt").read_text()
    assert (public / "getting-started/index.md").read_text() in (public / "llms-full.txt").read_text()
    assert not (public / "_sidebar").exists()



def test_optional_landing_preserves_markdown_mirror(tmp_path):
    import json

    wiki = tmp_path / "wiki"
    wiki.mkdir()
    (wiki / "_Site.json").write_text('{"title":"demo-cli","landing":true}')
    (wiki / "Home.md").write_text("# Build CLIs\n\nIntro\n\n## Highlights\n\n- **Minimal core**: Start with essentials.\n- **Agent-ready**: Predictable interfaces.\n\n## Documentation\n\n[Start](Getting-Started)\n")
    (wiki / "Getting-Started.md").write_text("# Start\n")
    site = tmp_path / "site"
    prepare(wiki, site, "https://example.github.io/demo/", "https://github.com/example/demo", "Example")
    homepage = (site / "src/content/docs/index.md").read_text()
    assert "template: splash" not in homepage
    assert "## Highlights" in homepage
    assert '<ul class="project-highlights"' in homepage
    assert "<strong>Agent-ready</strong><span>Predictable interfaces.</span>" in homepage
    assert "## Documentation" in homepage
    mirror = (site / "public/index.md").read_text()
    assert "- **Minimal core**: Start with essentials." in mirror
    assert "project-highlights" not in mirror
    assert json.loads((site / "docs-meta.json").read_text())["title"] == "demo-cli"
    assert "template: splash" not in (site / "src/content/docs/getting-started.md").read_text()


def test_markdown_links_and_gfm():
    base = "https://example.github.io/demo/"
    text = """[**Nested** label](Guide.md#section "Title")

[Reference][page]

[page]: Guide

`[code](Unknown)`

![image](logo.png)

- [x] Done

| A | B |
|---|---|
| 1 | 2 |

~~~markdown
[not a link](Unknown)
~~~
"""
    result = rewrite(text, {"Guide": "guide/"}, base, True)
    links = [token.attrGet("href") for token in link_tokens(parser().parse(result))]
    assert links == [base + "guide/index.md#section", base + "guide/index.md"]
    assert "[code](Unknown)" in result
    assert "[not a link](Unknown)" in result
    assert "![image](logo.png)" in result
    assert "[x] Done" in result
    assert any(token.type == "table_open" for token in parser().parse(result))


def test_unknown_wiki_page():
    import pytest
    with pytest.raises(ValueError, match="Unknown wiki page: Missing"):
        rewrite("[Missing](Missing)", {}, "https://example.github.io/", False)
