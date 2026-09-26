"""Update only the chart version, preserving the rest of Chart.yaml."""

import argparse
from pathlib import Path
import re

import yaml


def bump(path, version):
    source = path.read_text(encoding="utf-8")
    metadata = yaml.safe_load(source)
    if not re.fullmatch(r"\d+\.\d+\.\d+(?:-[0-9A-Za-z.-]+)?", version):
        raise ValueError("Invalid chart version")
    if not isinstance(metadata, dict) or not isinstance(metadata.get("version"), (str, int, float)):
        raise ValueError("Chart.yaml has no version")
    updated, count = re.subn(r"^version: [^\n]+$", f"version: {version}", source, flags=re.MULTILINE)
    if count != 1:
        raise ValueError("Expected exactly one top-level version field")
    if yaml.safe_load(updated)["version"] != version:
        raise ValueError("Version update did not produce the expected chart metadata")
    path.write_text(updated, encoding="utf-8")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("chart", choices=("ecp-endpoint", "ecp-directory", "ecp-broker", "eccosp-artemis"))
    parser.add_argument("version")
    args = parser.parse_args()
    bump(Path(__file__).resolve().parents[2] / "charts" / args.chart / "Chart.yaml", args.version)