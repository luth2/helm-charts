# Helm Repository: Quickstart and GitOps

## Add the Repository

The documentation and Helm repository share one address:
<https://luth2.github.io/helm-charts/>. Helm uses `index.yaml` and the
versioned `.tgz` packages hosted there. No Git checkout or OCI client is required.

```sh
helm repo add eccosp https://luth2.github.io/helm-charts/
helm repo update
helm search repo eccosp --versions
```

| Chart reference | Example release | Purpose |
| --- | --- | --- |
| `eccosp/ecp-directory` | `cd` | Component Directory |
| `eccosp/ecp-broker` | `br` | ECP Broker |
| `eccosp/eccosp-artemis` | `eptb1` | Internal Broker |
| `eccosp/ecp-endpoint` | `ep1` | Endpoint |

The old umbrella chart **ecco-sp** may still appear in search results. It remains
available for existing users but is not recommended for new installations.
The four standalone charts do not install partner services, databases, or EDX components.

## Choose the Version Deliberately

The following shell examples pin the already published chart version
**5.0.1**. They are not instructions to upgrade an existing installation
directly. The chart version, `appVersion`, and container image are versioned
independently. Choose approved versions based on the
[releases](https://github.com/luth2/helm-charts/releases) and the
[operations and migration notes](Helm_Charts.md).

```sh
helm show chart eccosp/ecp-endpoint --version 5.0.1
```

## Retrieve the Complete Values for the Package Version

Create the operator configuration files in a dedicated working directory outside the
source code repository. The following redirections create new files;
do not run them again over operator configuration files that have already been customized.

```sh
mkdir eccosp-values
helm show values eccosp/ecp-directory --version 5.0.1 > eccosp-values/cd.yaml
helm show values eccosp/ecp-broker --version 5.0.1 > eccosp-values/br.yaml
helm show values eccosp/eccosp-artemis --version 5.0.1 > eccosp-values/eptb1.yaml
helm show values eccosp/ecp-endpoint --version 5.0.1 > eccosp-values/ep1.yaml
```

Review every file in full: instance names, `existingSecret`, images, storage,
ports, resources, and external connections. **Helm replaces lists** rather than
merging instance entries. Do not overlay the defaults with a reduced `instance` list
containing only a name and secret.

The website shows values and schemas from the current source state. For deployments,
the **versioned package defaults** just retrieved are authoritative.

## External Prerequisites

Before installation, the `eccosp` namespace, populated secrets, image access,
storage, and external partners must be ready. The chart does not create secrets.
The intentionally empty `existingSecret` defaults cannot be used for installation.

Each secret key contains the required **complete configuration file**.
Secrets, passwords, and keystores belong neither in Git nor in this portal.
The required secret keys, example names, and service addresses are documented in the
[operations guide](Helm_Charts.md). Also observe the pod security, HA, and
storage restrictions described there.

## Render and Install New Releases

First, render each release without a cluster, for example:

```sh
helm template ep1 eccosp/ecp-endpoint --version 5.0.1 --namespace eccosp -f eccosp-values/ep1.yaml
```

Repeat the same checks for Directory, ECP Broker, and Artemis using their
respective release/chart reference and operator configuration file. Check names, PVCs,
selectors, secret references, ports, and SecurityContexts. Optionally, retrieve the
versioned package with `helm pull` and validate it locally with `helm lint`.

Only after approval and once the prerequisites are in place, perform a **new** installation
step by step:

```sh
helm install cd eccosp/ecp-directory --version 5.0.1 --namespace eccosp -f eccosp-values/cd.yaml --wait --timeout 15m
helm install br eccosp/ecp-broker --version 5.0.1 --namespace eccosp -f eccosp-values/br.yaml --wait --timeout 15m
helm install eptb1 eccosp/eccosp-artemis --version 5.0.1 --namespace eccosp -f eccosp-values/eptb1.yaml --wait --timeout 15m
helm install ep1 eccosp/ecp-endpoint --version 5.0.1 --namespace eccosp -f eccosp-values/ep1.yaml --wait --timeout 15m
```

Each component is installed and rolled back independently. After each step,
check PVC binding, initialization, and application health. Finally, perform functional acceptance checks for TLS,
authentication, registration, the database, and message flow.
`--wait` alone is not proof of operational readiness.

## Updates and Reproducibility

- Pin chart versions explicitly; do not automatically select `latest` or open-ended version ranges.
- Keep operator values under version control without including complete private configurations.
- Retrieve new defaults separately and compare them with the existing configuration; do not overwrite existing files.
- Before updates, create backups, compare PVCs/selectors, and perform the [migration](Helm_Charts.md).
- Published chart versions are immutable. Corrections require a new chart version.

## Argo CD and Flux

Both can read the public HTTPS repository without credentials.
The repository URL is the base address, **not** the address of `index.yaml`.

| Tool | Repository | Chart | Version |
| --- | --- | --- | --- |
| Argo CD Application | `spec.source.repoURL: https://luth2.github.io/helm-charts/` | `spec.source.chart: ecp-endpoint` | `spec.source.targetRevision: 5.0.1` |
| Flux HelmRepository + HelmRelease | `HelmRepository.spec.url: https://luth2.github.io/helm-charts/` | `HelmRelease.spec.chart.spec.chart: ecp-endpoint` | `HelmRelease.spec.chart.spec.version: 5.0.1` |

For Flux, also set `sourceRef` to the HelmRepository. For Argo CD, supply the
complete operator values, for example through a separate values repository;
for Flux, use `values` or `valuesFrom`. Manage the target namespace, external secrets, and
deployment order separately. Enter chart names without the local
Helm alias prefix `eccosp/`. Create separate Applications or HelmReleases, respectively,
for each of the other components.

## Troubleshooting

| Symptom | Check |
| --- | --- |
| Repository or package returns 404 | Check Pages publication and the current index; [Pages operations](GitHub_Pages.md) |
| Version not found | `helm repo update` and `helm search repo eccosp --versions`; use the chart version rather than appVersion |
| Empty `existingSecret` or missing values | Retrieve and customize the complete defaults for the pinned version |
| Pod does not start despite successful rendering | Check secret keys, registry, storage, external configuration, and init containers |
| New website, but still an old chart version | Documentation state and release state are separate; wait for a successful chart release |
