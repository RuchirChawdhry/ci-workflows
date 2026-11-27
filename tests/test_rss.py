import importlib.util
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import xml.etree.ElementTree as ET

spec = importlib.util.spec_from_file_location("rss", Path(__file__).resolve().parents[1] / "scripts/rss.py")
rss = importlib.util.module_from_spec(spec)
spec.loader.exec_module(rss)


def release(id, published="2026-01-01T00:00:00Z", **kwargs):
    return dict(id=id, draft=False, prerelease=False, published_at=published, name="Release <&>",
                tag_name=f"v{id}", html_url=f"https://github.com/owner/project/releases/tag/v{id}",
                body="Fix <script>alert(1)</script> & improve\nDocs", **kwargs)


class FeedTests(unittest.TestCase):
    def test_release_filter(self):
        stable = release(1)
        draft = dict(release(2), draft=True)
        preview = dict(release(3), prerelease=True)
        self.assertEqual(len(list(rss.release_items("owner/project", [stable, draft, preview]))), 1)
        self.assertEqual(len(list(rss.release_items("owner/project", [stable, draft, preview], True))), 2)

    def test_round_trip_dedup_and_order(self):
        items = list(rss.release_items("owner/project", [release(1), release(2, "2026-02-01T00:00:00Z")]))
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "feed.rss"
            rss.write_feed(path, "Project", "https://owner.github.io/project/", items + items, 10)
            root = ET.parse(path).getroot()
            self.assertEqual(len(root.findall("channel/item")), 2)
            self.assertEqual(root.find("channel/{http://www.w3.org/2005/Atom}link").get("href"),
                             "https://owner.github.io/project/feed.rss")
            self.assertEqual(root.findtext("channel/item/guid"), "github-release:2")
            self.assertEqual(root.find("channel/item/guid").get("isPermaLink"), "false")
            self.assertIn("&lt;script&gt;", root.findtext("channel/item/description"))
            parsed = list(rss.parse_project(path.read_bytes(), "owner", "project"))
            self.assertEqual(parsed, list(reversed(items)))
            rss.write_feed(path, "All projects", "https://owner.github.io/", parsed, 1)
            self.assertEqual(len(ET.parse(path).findall("channel/item")), 1)

    def test_empty_feed(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "feed.rss"
            rss.write_feed(path, "Empty", "https://owner.github.io/", [], 100)
            self.assertEqual(ET.parse(path).findall("channel/item"), [])

    def test_reject_dtd_and_invalid_link(self):
        with self.assertRaises(ValueError):
            list(rss.parse_project(b'<!DOCTYPE rss><rss/>', "owner", "project"))
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "feed.rss"
            item = next(rss.release_items("owner/project", [release(1)]))
            item["link"] = "https://example.org/release"
            rss.write_feed(path, "Project", "https://owner.github.io/project/", [item], 10)
            with self.assertRaises(ValueError):
                list(rss.parse_project(path.read_bytes(), "owner", "project"))

    def test_pagination(self):
        with patch.object(rss, "get", side_effect=[b"[" + b",".join([b"1"] * 100) + b"]", b"[2]"]) as get:
            self.assertEqual(len(list(rss.api_pages("repos/owner/project/releases", "token"))), 101)
            self.assertIn("page=2", get.call_args.args[0])


if __name__ == "__main__":
    unittest.main()
