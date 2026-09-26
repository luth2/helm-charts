"""Select digest-pinned Kubernetes node images from stable kind releases."""

import json
import os
import re
import sys
from urllib.request import Request, urlopen


RELEASE_URL = "https://api.github.com/repos/kubernetes-sigs/kind/releases?per_page=100"
IMAGE = re.compile(r"kindest/node:v1\.(\d+)\.(\d+)@sha256:([0-9a-f]{64})")


def select_matrix(releases):
    if not isinstance(releases, list):
        raise ValueError("Expected a list of kind releases")
    images = {}
    stable = sorted(
        (release for release in releases if not release.get("draft") and not release.get("prerelease")
         and re.fullmatch(r"v0\.\d+\.\d+", release.get("tag_name", ""))),
        key=lambda release: tuple(map(int, release["tag_name"][1:].split("."))),
        reverse=True,
    )
    for release in stable:
        body = release.get("body") or ""
        if "Images pre-built for this release:" not in body:
            continue
        current = {}
        for match in IMAGE.finditer(body.split("Images pre-built for this release:", 1)[1]):
            minor, patch, digest = match.groups()
            minor = int(minor)
            if minor < 34:
                continue
            entry = {
                "kubernetes_version": f"1.{minor}.{patch}",
                "kind_version": release["tag_name"],
                "node_image": match.group(),
            }
            if minor in current and current[minor] != entry:
                raise ValueError(f"Conflicting kind images for Kubernetes 1.{minor}")
            current[minor] = entry
        for minor, entry in current.items():
            images.setdefault(minor, entry)
    if not images or set(images) != set(range(34, max(images) + 1)) or max(images) < 36:
        raise ValueError("kind releases must provide every Kubernetes minor from 1.34 to latest")
    return {"include": [images[minor] for minor in sorted(images)]}


def main():
    headers = {"Accept": "application/vnd.github+json", "User-Agent": "eccosp-chart-ci"}
    if token := os.environ.get("GITHUB_TOKEN"):
        headers["Authorization"] = f"Bearer {token}"
    with urlopen(Request(RELEASE_URL, headers=headers), timeout=30) as response:
        releases = json.load(response)
    print("matrix=" + json.dumps(select_matrix(releases), separators=(",", ":")))


if __name__ == "__main__":
    try:
        main()
    except (ValueError, OSError) as error:
        print(error, file=sys.stderr)
        sys.exit(1)