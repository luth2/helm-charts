"""Version metadata changes must not rewrite other chart fields."""

from pathlib import Path
import tempfile
import unittest

from bump_chart_version import bump


class BumpTests(unittest.TestCase):
    def test_only_version_changes(self):
        source = 'apiVersion: v2\nversion: 5.0.1\nappVersion: "4.17.0"\n'
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "Chart.yaml"
            path.write_text(source, encoding="utf-8")
            bump(path, "5.1.0")
            self.assertEqual(path.read_text(encoding="utf-8"), source.replace("5.0.1", "5.1.0"))
            with self.assertRaisesRegex(ValueError, "Invalid chart version"):
                bump(path, "invalid")
            self.assertEqual(path.read_text(encoding="utf-8"), source.replace("5.0.1", "5.1.0"))


if __name__ == "__main__":
    unittest.main()