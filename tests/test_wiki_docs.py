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
