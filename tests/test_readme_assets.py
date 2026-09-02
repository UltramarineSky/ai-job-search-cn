"""Every local image referenced by README.md must exist in the repo.

A broken header image on the repo landing page is a silent, high-visibility
failure; this guard turns it into a red CI run instead.

Note: this CN fork intentionally dropped the upstream mascot header, so the
README is text-only and may reference zero local images. The guard therefore
only verifies that README exists and that any local image it *does* reference
resolves - it does not force a local image to be present.
"""
import re
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
README = REPO / "README.md"

IMG_SRC = re.compile(r'<img[^>]+src="([^"]+)"')
MD_IMG = re.compile(r"!\[[^\]]*\]\(([^)\s]+)")


class ReadmeImageReferences(unittest.TestCase):
    def _local_refs(self):
        text = README.read_text(encoding="utf-8")
        refs = IMG_SRC.findall(text) + MD_IMG.findall(text)
        return [r for r in refs if not r.startswith(("http://", "https://"))]

    def test_readme_exists_and_is_non_empty(self):
        # The CN fork intentionally dropped the mascot header, so a local image
        # is no longer required; README just has to exist with real content.
        self.assertTrue(README.is_file(), "README.md is missing")
        self.assertTrue(README.read_text(encoding="utf-8").strip(), "README.md is empty")

    def test_all_local_image_references_resolve(self):
        for ref in self._local_refs():
            with self.subTest(ref=ref):
                self.assertTrue((REPO / ref).is_file(), f"README references missing file: {ref}")


if __name__ == "__main__":
    unittest.main()
