"""Tests for synthetic Kubernetes fixtures and the kind version matrix."""

from pathlib import Path
import tempfile
import unittest

from chart_fixtures import CHARTS, SECRET, read_yaml
from kubernetes_fixtures import CASES, write_fixtures
from kubernetes_matrix import select_matrix


class KubernetesMatrixTests(unittest.TestCase):
    def test_cluster_fixtures_are_synthetic_positive_cases(self):
        with tempfile.TemporaryDirectory() as temporary:
            destination = Path(temporary)
            write_fixtures(destination)
            for chart in CHARTS:
                with self.subTest(chart=chart):
                    self.assertEqual({path.stem for path in (destination / chart).glob("*.yaml")},
                                     set(CASES))
                    for case in CASES:
                        values = read_yaml(destination / chart / f"{case}.yaml")
                        self.assertEqual(values["instance"][0]["existingSecret"], SECRET)

    def test_contiguous_digest_pinned_versions(self):
        body = "Images pre-built for this release:\n" + "\n".join(
            f"kindest/node:v1.{minor}.1@sha256:{str(minor)[-1] * 64}"
            for minor in range(34, 38)
        )
        matrix = select_matrix([{"tag_name": "v0.33.0", "body": body}])
        self.assertEqual([item["kubernetes_version"] for item in matrix["include"]],
                         ["1.34.1", "1.35.1", "1.36.1", "1.37.1"])
        self.assertTrue(all(item["kind_version"] == "v0.33.0" for item in matrix["include"]))

    def test_missing_or_conflicting_images_fail(self):
        image = lambda minor, digest: f"kindest/node:v1.{minor}.1@sha256:{digest * 64}"
        for body in (
            image(34, "a") + "\n" + image(36, "b"),
            image(34, "a") + "\n" + image(35, "b") + "\n" + image(36, "c") + "\n" + image(36, "d"),
        ):
            with self.subTest(body=body), self.assertRaises(ValueError):
                select_matrix([{"tag_name": "v0.33.0", "body": "Images pre-built for this release:\n" + body}])

    def test_older_release_keeps_minimum_version(self):
        image = lambda minor, digest: f"kindest/node:v1.{minor}.1@sha256:{digest * 64}"
        releases = [
            {"tag_name": "v0.34.0", "body": "Images pre-built for this release:\n" +
             "\n".join(image(minor, "a") for minor in range(35, 39))},
            {"tag_name": "v0.33.0", "body": "Images pre-built for this release:\n" +
             "\n".join(image(minor, "b") for minor in range(34, 38))},
        ]
        matrix = select_matrix(releases)["include"]
        self.assertEqual([item["kubernetes_version"] for item in matrix],
                         [f"1.{minor}.1" for minor in range(34, 39)])
        self.assertEqual([item["kind_version"] for item in matrix],
                         ["v0.33.0"] + ["v0.34.0"] * 4)