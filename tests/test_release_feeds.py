import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
from urllib.error import HTTPError
import xml.etree.ElementTree as ET

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import release_feeds as feeds

ATOM = b'''<feed xmlns="http://www.w3.org/2005/Atom">
<title>Releases</title><id>urn:feed</id><updated>2026-11-22T16:37:40+05:30</updated>
<entry><id>tag:github.com,2008:Repository/123/v1</id><title>v1 &amp; fixes</title>
<updated>2026-11-22T17:15:15+05:30</updated>
<link rel="alternate" href="https://github.com/owner/project/releases/tag/v1"/>
<content type="html">&lt;p&gt;Hello &amp;amp; fixes&lt;/p&gt;</content>
<author><name>bot</name></author></entry></feed>'''


class NativeFeedTests(unittest.TestCase):
    def test_formats_and_alias(self):
        items = feeds.parse(ATOM, "owner", "project")
        project = dict(name="project", url="https://github.com/owner/project", description="<unsafe>", items=items + items)
        with tempfile.TemporaryDirectory() as temp:
            out = Path(temp)
            feeds.generate(out, "owner", [project], 200)
            rss = ET.parse(out / "feed.rss")
            self.assertEqual(rss.findtext("channel/item/description"), "<p>Hello &amp; fixes</p>")
            self.assertEqual(rss.findtext("channel/item/pubDate"), "Sun, 22 Nov 2026 11:45:15 GMT")
            self.assertEqual(len(rss.findall("channel/item")), 1)
            self.assertEqual((out / "rss.xml").read_bytes(), (out / "feed.rss").read_bytes())
            atom = ET.parse(out / "feed.atom")
            self.assertEqual(atom.findtext(feeds.A + "entry/" + feeds.A + "id"), items[0]["id"])
            self.assertIsNone(atom.find(feeds.A + "entry/" + feeds.A + "published"))
            data = json.loads((out / "feed.json").read_text())
            self.assertEqual(data["items"][0]["date_modified"], "2026-11-22T11:45:15Z")
            self.assertNotIn("date_published", data["items"][0])
            self.assertEqual(ET.parse(out / "feeds.opml").find("body/outline").get("xmlUrl"),
                             "https://github.com/owner/project/releases.atom")
            self.assertIn("&lt;unsafe&gt;", (out / "feeds/index.html").read_text())

    def test_no_pages_required_and_private_excluded(self):
        repos = [dict(name="project", private=False, has_pages=False, owner=dict(login="owner")),
                 dict(name="private", private=True, has_pages=True, owner=dict(login="owner"))]
        with patch.object(feeds, "api_pages", return_value=repos), patch.object(feeds, "get", return_value=ATOM) as get:
            projects = feeds.discover("owner", "token")
            self.assertEqual([p["name"] for p in projects], ["project"])
            get.assert_called_once_with("https://github.com/owner/project/releases.atom")

    def test_invalid_input(self):
        for data in (b"<!DOCTYPE feed><feed/>", ATOM.replace(b"github.com/owner/project", b"example.com/owner/project")):
            with self.assertRaises(ValueError):
                feeds.parse(data, "owner", "project")

    def test_missing_vs_network_failure(self):
        for status in (404, 503):
            with patch.object(feeds, "get", side_effect=HTTPError("https://github.com", status, "", {}, None)):
                if status == 404:
                    self.assertIsNone(feeds.fetch_project("owner", dict(name="project")))
                else:
                    with self.assertRaises(HTTPError):
                        feeds.fetch_project("owner", dict(name="project"))

    def test_empty_collection(self):
        with tempfile.TemporaryDirectory() as temp:
            out = Path(temp)
            feeds.generate(out, "owner", [], 200)
            self.assertEqual(json.loads((out / "feed.json").read_text())["items"], [])
            self.assertEqual(ET.parse(out / "feeds.opml").findall("body/outline"), [])


if __name__ == "__main__":
    unittest.main()
