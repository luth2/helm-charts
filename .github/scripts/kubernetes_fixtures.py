"""Write only the synthetic chart values needed for API server dry-runs."""

import argparse
from pathlib import Path

import yaml

from chart_fixtures import CHARTS, fixtures


CASES = ("existing-secret", "ingress", "gateway-https", "gateway-http")
ROOT = Path(__file__).resolve().parents[2]


def write_fixtures(destination):
    for chart in CHARTS:
        cases = {case.name: case for case in fixtures(ROOT, chart)}
        directory = destination / chart
        directory.mkdir(parents=True, exist_ok=True)
        for name in CASES:
            case = cases[name]
            if case.reject is not None or case.schema_reject:
                raise ValueError(f"{chart}/{name} must be a positive fixture")
            (directory / f"{name}.yaml").write_text(
                yaml.safe_dump(case.values, sort_keys=False), encoding="utf-8"
            )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("destination", type=Path)
    args = parser.parse_args()
    write_fixtures(args.destination)