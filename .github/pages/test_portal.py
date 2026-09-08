"""Offline regression checks for documentation staging and Helm preservation."""

from pathlib import Path
import tempfile
import unittest

from build_portal import CHARTS, ROOT, merge, source_links, stage


class PortalTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.site = self.root / "site"
        self.helm = self.root / "helm"
        self.site.mkdir()
        self.helm.mkdir()
        (self.site / "index.html").write_text("portal", encoding="utf-8")
        (self.helm / "index.yaml").write_bytes(b"apiVersion: v1\nentries: {}\n")
        (self.helm / "legacy.tgz").write_bytes(b"\x00\xfflegacy")
        (self.helm / "packages").mkdir()
        (self.helm / "packages/chart.tgz").write_bytes(b"\x00\xffchart")

    def test_merge_preserves_index_packages_and_other_files(self):
        (self.helm / "CNAME").write_text("charts.example.org", encoding="utf-8")
        destination = self.root / "publish"
        merge(self.site, self.helm, destination)
        for source in self.helm.rglob("*"):
            if source.is_file():
                self.assertEqual(source.read_bytes(), (destination / source.relative_to(self.helm)).read_bytes())
        self.assertEqual((destination / "index.html").read_text(), "portal")
        self.assertTrue((destination / ".nojekyll").is_file())

    def test_rejects_website_helm_collision_before_copying(self):
        for filename in ("index.yaml", "replacement.tgz"):
            with self.subTest(filename=filename):
                path = self.site / filename
                path.write_text("wrong", encoding="utf-8")
                destination = self.root / "publish"
                with self.assertRaisesRegex(ValueError, "Helm payload"):
                    merge(self.site, self.helm, destination)
                self.assertFalse(destination.exists())
                path.unlink()

    def test_rejects_missing_index(self):
        (self.helm / "index.yaml").unlink()
        with self.assertRaisesRegex(ValueError, "index.yaml"):
            merge(self.site, self.helm, self.root / "publish")

    def test_rejects_existing_destination(self):
        with self.assertRaisesRegex(ValueError, "must not exist"):
            merge(self.site, self.helm, self.site)

    def test_stages_existing_sources_and_metadata_without_private_files(self):
        destination = self.root / "docs"
        stage(ROOT, destination, self.helm)
        for name in CHARTS:
            self.assertEqual((ROOT / "charts" / name / "README.md").read_bytes(),
                             (destination / "charts" / name / "README.md").read_bytes())
            self.assertFalse((destination / "charts" / name / "templates").exists())
        catalog = (destination / "charts/index.md").read_text(encoding="utf-8")
        self.assertIn("not available in this build", catalog)
        self.assertIn("# Chart catalog and versions", catalog)
        self.assertFalse((destination / ".github").exists())

    def test_catalog_distinguishes_published_version_from_main(self):
        (self.helm / "index.yaml").write_text(
            "entries:\n  ecp-endpoint:\n    - version: 1.2.3\n", encoding="utf-8")
        destination = self.root / "docs"
        stage(ROOT, destination, self.helm)
        self.assertIn("releases/tag/ecp-endpoint-1.2.3", (destination / "charts/index.md").read_text(encoding="utf-8"))

    def test_workflow_links_point_to_source(self):
        self.assertEqual(
            source_links("[CI](../.github/workflows/Release%20Charts.yml)"),
            "[CI](https://github.com/luth2/helm-charts/blob/main/.github/workflows/Release%20Charts.yml)",
        )


if __name__ == "__main__":
    unittest.main()