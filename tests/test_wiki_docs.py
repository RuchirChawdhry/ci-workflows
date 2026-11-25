from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from wiki_docs import prepare


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
    assert "template: splash" in homepage
    assert '<ul class="project-highlights"' in homepage
    assert "<strong>Agent-ready</strong><span>Predictable interfaces.</span>" in homepage
    assert "## Documentation" in homepage
    mirror = (site / "public/index.md").read_text()
    assert "- **Minimal core**: Start with essentials." in mirror
    assert "project-highlights" not in mirror
    assert json.loads((site / "docs-meta.json").read_text())["title"] == "demo-cli"
    assert "template: splash" not in (site / "src/content/docs/getting-started.md").read_text()
