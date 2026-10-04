from __future__ import annotations

from html.parser import HTMLParser
import json
from pathlib import Path
import re
import shutil
import tempfile
import unittest
from unittest.mock import patch
from xml.etree import ElementTree

import manage
from tools.pages import SITE_URL, build_pages


class AssetParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.assets: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        values = dict(attrs)
        if tag in ("script", "img") and values.get("src"):
            self.assets.append(values["src"])
        if tag == "link" and values.get("rel") in ("icon", "stylesheet"):
            self.assets.append(values["href"])


class PagesTests(unittest.TestCase):
    @patch("manage.build_pages")
    @patch("manage.build_frontend")
    def test_pages_command_compiles_before_packaging(self, compile: object, package: object) -> None:
        with unittest.mock.patch("manage.run_server") as server:
            calls = unittest.mock.Mock()
            calls.attach_mock(compile, "compile")
            calls.attach_mock(package, "package")
            manage.main(("pages",))
        self.assertEqual(calls.mock_calls, [unittest.mock.call.compile(),
                                          unittest.mock.call.package(manage.PROJECT_ROOT)])
        server.assert_not_called()

    def test_deployment_is_complete_and_safe_at_a_repository_subpath(self) -> None:
        # Use the real runtime files to catch new absolute URLs or missing assets.
        with tempfile.TemporaryDirectory(prefix=".pages-test-", dir=manage.PROJECT_ROOT) as directory:
            root = Path(directory)
            for name in ("pages", "src", "public"):
                shutil.copytree(manage.PROJECT_ROOT / name, root / name)
            shutil.copy2(manage.PROJECT_ROOT / "index.html", root / "index.html")
            shutil.copytree(manage.PROJECT_ROOT / "node_modules" / "three" / "build",
                            root / "node_modules" / "three" / "build")
            shutil.copy2(manage.PROJECT_ROOT / "node_modules" / "three" / "LICENSE",
                         root / "node_modules" / "three" / "LICENSE")
            (root / "private.env").write_text("must never be published")
            build_pages(root)
            output = root / ".pages-output"
            (output / "stale.txt").touch()
            build_pages(root)
            self.assertFalse((output / "stale.txt").exists())
            self.assertFalse((output / "private.env").exists())
            self.assertTrue((output / ".nojekyll").exists())
            self.assertFalse(list(output.rglob("*.ts")))
            self.assertFalse(list(output.rglob("*.py")))
            for page in (output / "index.html", output / "play" / "index.html"):
                markup = page.read_text()
                self.assertNotIn("@@", markup)
                parser = AssetParser()
                parser.feed(markup)
                for asset in parser.assets:
                    self.assertFalse(asset.startswith("/"), asset)
                    self.assertTrue((page.parent / asset).is_file(), asset)
            game = (output / "play" / "index.html").read_text()
            import_map = json.loads(re.search(r'<script type="importmap">(.*?)</script>',
                                             game, re.S).group(1))
            self.assertTrue((output / "play" / import_map["imports"]["three"]).is_file())
            self.assertTrue((output / "play/node_modules/three/build/three.core.js").is_file())
            landing = (output / "index.html").read_text()
            data = json.loads(re.search(r'<script type="application/ld\+json">(.*?)</script>',
                                       landing, re.S).group(1))
            self.assertEqual(data["url"], SITE_URL)
            self.assertEqual(data["@type"], "VideoGame")
            self.assertIn(f'<link rel="canonical" href="{SITE_URL}">', landing)
            sitemap = ElementTree.parse(output / "sitemap.xml")
            self.assertEqual(sitemap.find(".//{*}loc").text, SITE_URL)
