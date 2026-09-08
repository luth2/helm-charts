"""Run pinned, cluster-free source and packaged-chart checks on Linux CI.

Raw defaults lacking existingSecret are expected to reject with that exact
diagnostic. Positive tests always use generated synthetic Secret references.
Packages and rendered YAML are published only after the entire suite succeeds.
"""

import argparse
from pathlib import Path
import re
import shutil
import subprocess
import tarfile
import tempfile

import yaml

from chart_fixtures import BROKERS, CHARTS, Case, components, enabled_instances, fixtures, read_yaml
from manifest_checks import require, validate_manifest


ROOT = Path(__file__).resolve().parents[2]
KUBERNETES_VERSION = "1.32.0"
SEMVER = re.compile(
    r"(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)"
    r"(?:-((?:0|[1-9][0-9]*|[0-9]*[A-Za-z-][0-9A-Za-z-]*)"
    r"(?:\.(?:0|[1-9][0-9]*|[0-9]*[A-Za-z-][0-9A-Za-z-]*))*))?"
    r"(?:\+[0-9A-Za-z-]+(?:\.[0-9A-Za-z-]+)*)?"
)


def chart_directory(root, name):
    return root / ("ecco-sp" if name == "ecco-sp" else f"charts/{name}")


def run(command, reject=None):
    result = subprocess.run([str(part) for part in command], cwd=ROOT, text=True, capture_output=True, check=False)
    if reject is not None:
        require(result.returncode != 0, "Invalid values were unexpectedly accepted")
        require(re.search(reject, result.stderr, re.IGNORECASE | re.DOTALL),
                f"Render failed for an unrelated reason (expected {reject}):\n{result.stderr}")
    else:
        require(result.returncode == 0, f"{command[0]} failed:\n{result.stdout}\n{result.stderr}")
    return result.stdout


def check_metadata():
    tracked = run(["git", "ls-files", "ecco-sp/charts"])
    require(not tracked.strip(), "Vendored umbrella chart copies must be removed from Git")
    all_metadata = {name: read_yaml(chart_directory(ROOT, name) / "Chart.yaml")
                    for name in (*CHARTS, "ecco-sp")}
    for name, metadata in all_metadata.items():
        directory = chart_directory(ROOT, name)
        for key, expected in {
            "name": name, "apiVersion": "v2", "type": "application",
            "kubeVersion": ">=1.28.0-0",
        }.items():
            require(metadata.get(key) == expected, f"{name}: unexpected {key}")
        require(isinstance(metadata.get("appVersion"), str) and metadata["appVersion"].strip(),
                f"{name}: appVersion must be a non-empty descriptive string")
        require(isinstance(metadata.get("version"), str) and SEMVER.fullmatch(metadata["version"]),
                f"{name}: version must be strict SemVer")
        require((directory / "values.yaml").is_file(), f"{name}: values.yaml is required")
        if name == "ecco-sp":
            expected = [
                {"name": chart, "version": all_metadata[chart]["version"], "repository": f"file://../charts/{chart}",
                 "condition": f"{chart}.enabled"}
                for chart in CHARTS
            ]
            require(metadata.get("dependencies") == expected, "Umbrella dependencies must point only to charts/")
            require(not (directory / "requirements.yaml").exists(), "Legacy requirements.yaml remains")
        else:
            values = read_yaml(directory / "values.yaml")
            require(values.get("global", {}).get("storage", {}).get("class") == "",
                    f"{name}: global.storage.class default must be empty")
            if name in BROKERS:
                require(all(item.get("useSharedStorageForJournal") is False for item in values["instance"]),
                        f"{name}: shared journal must be opt-in")
    return all_metadata


def validation_cases(root, target):
    cases = fixtures(root, target)
    defaults = components(root, target, {})
    missing_secret = any(not item.get("existingSecret") for values in defaults.values()
                         for item in enabled_instances(values))
    cases.insert(0, Case("raw-defaults", {}, reject=r"existingSecret" if missing_secret else None))
    return cases


def package_path(directory, target, metadata):
    expected = directory / f"{target}-{metadata['version']}.tgz"
    require(list(directory.glob(f"{target}-*.tgz")) == [expected],
            f"Expected exactly one package matching metadata: {expected.name}")
    return expected


def render(chart, target, case, work, stage):
    print(f"{target}/{stage}/{case.name}: starting lint/render/schema checks", flush=True)
    effective = components(ROOT, target, case.values)
    fixture = work / f"{case.name}.values.yaml"
    fixture.write_text(yaml.safe_dump(case.values, sort_keys=False), encoding="utf-8")
    flags = ["--namespace", case.namespace, "--kube-version", KUBERNETES_VERSION]
    # No --debug: even failing cases must not dump configuration contents to logs.
    command = ["helm", "template", case.release, chart, *flags, "--values", fixture]
    text = run(command, reject=case.reject)
    if case.reject:
        print(f"{stage}/{case.name}: rejected for the expected reason", flush=True)
        return None
    run(["helm", "lint", "--strict", chart, *flags, "--values", fixture])
    docs = validate_manifest(text, case, effective)
    manifest = work / f"{case.name}.{stage}.yaml"
    manifest.write_text(text, encoding="utf-8")
    # Do not skip the empty manifest: disabled fixtures must validate too.
    # Kubeconform v0.7.0 processResults starts with success=true (zero is valid).
    summary = run(["kubeconform", "-strict", "-summary", "-kubernetes-version", KUBERNETES_VERSION, manifest])
    print(f"{stage}/{case.name}: {summary.strip()}", flush=True)
    return docs


def unpack(package, destination):
    with tarfile.open(package, "r:gz") as archive:
        require(all(not member.issym() and not member.islnk() for member in archive.getmembers()),
                "Chart archive contains links")
        archive.extractall(destination, filter="data")


def validate(target):
    metadata = check_metadata()
    version = run(["helm", "version", "--template", "{{.Version}}"])
    require(version.strip() == "v3.19.0", "CI requires Helm 3.19.0")
    require("0.7.0" in run(["kubeconform", "-v"]), "CI requires Kubeconform 0.7.0")
    chart = chart_directory(ROOT, target)
    cases = validation_cases(ROOT, target)
    output = ROOT / ".ci-artifacts" / target / "publish"
    require(not output.exists(), f"Refusing to overwrite previous results: {output}")
    with tempfile.TemporaryDirectory(prefix=f"chart-ci-{target}-") as temporary:
        work = Path(temporary)
        source_results = {case.name: render(chart, target, case, work, "source") for case in cases}
        # A second release in the same namespace must have no colliding resource identities.
        def identities(docs):
            return {(doc["kind"], doc["metadata"]["name"]) for doc in docs}

        require(not identities(source_results["existing-secret"]).intersection(identities(source_results["custom-release"])),
                "Two releases in the same namespace have colliding resource names")
        run(["helm", "package", chart, "--destination", work])
        package = package_path(work, target, metadata[target])
        extracted = work / "unpacked"
        unpack(package, extracted)
        packaged_chart = extracted / target
        require(read_yaml(packaged_chart / "Chart.yaml") == metadata[target], "Packaged/source metadata differ")
        # Intentionally no dependency update/build here: the package must be self-contained.
        for case in cases:
            packaged = render(packaged_chart, target, case, work, "packaged")
            require(packaged == source_results[case.name], f"Packaged/source manifests differ: {case.name}")
        output.mkdir(parents=True)
        shutil.copy2(package, output / package.name)
        for case in cases:
            if case.reject is None:
                for suffix in ("values.yaml", "source.yaml", "packaged.yaml"):
                    path = work / f"{case.name}.{suffix}"
                    shutil.copy2(path, output / path.name)
    print(f"{target}: {len(cases)} source/package scenarios passed (no cluster tests)", flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--chart", choices=(*CHARTS, "ecco-sp"), required=True)
    arguments = parser.parse_args()
    validate(arguments.chart)