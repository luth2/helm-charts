"""Stage public Markdown once and merge the built site with a Helm snapshot.

Never writes to gh-pages. Publication uses a Pages artifact containing the
complete branch snapshot plus HTML, with Helm payload bytes preserved.
"""

import argparse
from pathlib import Path
import re
import shutil
from urllib.parse import quote

import yaml


ROOT = Path(__file__).resolve().parents[2]
CHARTS = ("ecp-directory", "ecp-broker", "eccosp-artemis", "ecp-endpoint")
REPOSITORY = "https://github.com/luth2/helm-charts"


def write_text(path, text):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def source_links(text):
    """Workflow files are source links, not public documentation downloads."""
    return re.sub(
        r"\]\(\.\./\.github/([^)]*)\)",
        lambda match: f"]({REPOSITORY}/blob/main/.github/{match[1]})",
        text,
    )


def stage(root, destination, helm_repository=None):
    # Refuse stale input rather than silently retaining removed documentation.
    destination.mkdir(parents=True, exist_ok=False)
    for source in sorted((root / "Dokumentation").glob("*.md")):
        write_text(destination / "Dokumentation" / source.name,
                   source_links(source.read_text(encoding="utf-8")))
    write_text(destination / "about.md", (root / "README.md").read_text(encoding="utf-8"))
    write_text(destination / "index.md",
               (root / ".github/pages/index.md").read_text(encoding="utf-8"))
    write_text(destination / "assets/portal.css",
               (root / ".github/pages/portal.css").read_text(encoding="utf-8"))

    entries = {}
    if helm_repository is not None:
        index = yaml.safe_load((helm_repository / "index.yaml").read_text(encoding="utf-8"))
        entries = index["entries"]

    catalog = [
        "# Chart catalog and versions", "",
        "Four standalone charts, four independent releases. Partner services are not installed automatically.",
        "", "## Source versions and published packages", "",
        "The source version comes from `Chart.yaml` on main. The published version",
        "is the first entry for each chart in the Helm index at build time.",
        "These versions may differ while a release is being published.", "",
        "| Chart | Source version | appVersion | Kubernetes | In the Helm index |",
        "| --- | --- | --- | --- | --- |",
    ]
    for name in CHARTS:
        source = root / "charts" / name
        target = destination / "charts" / name
        target.mkdir(parents=True)
        for filename in ("README.md", "Chart.yaml", "values.yaml", "values.schema.json"):
            shutil.copyfile(source / filename, target / filename)
        metadata = yaml.safe_load((source / "Chart.yaml").read_text(encoding="utf-8"))
        published = entries.get(name, [])
        version = str(published[0]["version"]) if published else "not available in this build"
        release = f"[{version}]({REPOSITORY}/releases/tag/{quote(name + '-' + version, safe='')})" if published else version
        catalog.append(
            f"| [{name}]({name}/README.md) | {metadata['version']} | "
            f"{metadata['appVersion']} | `{metadata['kubeVersion']}` | {release} |"
        )
    catalog += [
        "", "The linked chart READMEs, values and schemas describe the source version.",
        "For installation, retrieve the defaults **of the pinned package version** using",
        "`helm show values`; do not use files from main without checking them.",
        "", "## Installation and upgrades", "",
        "[Helm quickstart and GitOps](../Dokumentation/Helm_Repository.md)", "",
        "[All GitHub releases](https://github.com/luth2/helm-charts/releases)", "",
        "## Legacy: ecco-sp", "",
        "The legacy umbrella chart remains in the index for existing users.",
        "It is no longer a recommended installation target. Use the four standalone",
        "charts for new installations; first back up and migrate existing deployments",
        "according to the [migration guide](../Dokumentation/Helm_Charts.md).", "",
    ]
    write_text(destination / "charts/index.md", "\n".join(catalog))


def merge(site, helm_repository, destination):
    """Overlay only website output; fail before copying if Helm files collide."""
    if not (helm_repository / "index.yaml").is_file():
        raise ValueError("Helm snapshot must contain index.yaml")
    if destination.exists():
        raise ValueError("Publication destination must not exist")
    for directory in (site, helm_repository):
        if any(path.is_symlink() for path in directory.rglob("*")):
            raise ValueError("Symlinks are not allowed in Pages artifacts")
    for path in site.rglob("*"):
        if path.name == "index.yaml" or path.suffix == ".tgz":
            raise ValueError(f"Website must not supply Helm payload: {path}")
    shutil.copytree(helm_repository, destination, ignore=shutil.ignore_patterns(".git"))
    shutil.copytree(site, destination, dirs_exist_ok=True)
    write_text(destination / ".nojekyll", "")
    # Prove preservation of every index and package, including nested archives.
    for source in helm_repository.rglob("*"):
        if source.is_file() and (source.name == "index.yaml" or source.suffix == ".tgz"):
            if source.read_bytes() != (destination / source.relative_to(helm_repository)).read_bytes():
                raise ValueError(f"Helm payload changed: {source}")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=("stage", "merge"))
    parser.add_argument("--helm-repository", type=Path)
    args = parser.parse_args()
    output = ROOT / ".ci-artifacts/pages"
    if args.mode == "stage":
        stage(ROOT, output / "docs", args.helm_repository)
    else:
        if args.helm_repository is None:
            parser.error("merge requires --helm-repository")
        merge(output / "site", args.helm_repository, output / "publish")


if __name__ == "__main__":
    main()