#!/usr/bin/env bash
# Linux CI only. No kubectl, cluster creation or installation of releases.
set -euo pipefail

helm_version=3.19.0
kubeconform_version=0.7.0
test "$(uname -s)" = Linux
test "$(uname -m)" = x86_64
work=$(mktemp -d)
trap 'rm -rf "$work"' EXIT
bin="$HOME/.local/bin"
mkdir -p "$bin"
cd "$work"

archive="helm-v${helm_version}-linux-amd64.tar.gz"
curl --fail --silent --show-error --location --retry 3 \
  -o "$archive" "https://get.helm.sh/$archive"
curl --fail --silent --show-error --location --retry 3 \
  -o helm.sha256 "https://get.helm.sh/$archive.sha256sum"
sha256sum --check helm.sha256
tar -xzf "$archive" linux-amd64/helm
install -m 0755 linux-amd64/helm "$bin/helm"
export PATH="$bin:$PATH"
test "$(helm version --template '{{.Version}}')" = "v${helm_version}"

if [[ ${1:-all} != helm-only ]]; then
  base="https://github.com/yannh/kubeconform/releases/download/v${kubeconform_version}"
  archive=kubeconform-linux-amd64.tar.gz
  curl --fail --silent --show-error --location --retry 3 -o "$archive" "$base/$archive"
  curl --fail --silent --show-error --location --retry 3 -o CHECKSUMS "$base/CHECKSUMS"
  # Verify the one downloaded archive; missing/changed checksums fail closed.
  grep -E '^[0-9a-fA-F]{64} [ *]kubeconform-linux-amd64\.tar\.gz$' CHECKSUMS > selected.sha256
  test "$(wc -l < selected.sha256)" -eq 1
  sha256sum --check selected.sha256
  tar -xzf "$archive" kubeconform
  install -m 0755 kubeconform "$bin/kubeconform"
  kubeconform -v
fi

if [[ -n ${GITHUB_PATH:-} ]]; then
  printf '%s\n' "$bin" >> "$GITHUB_PATH"
fi