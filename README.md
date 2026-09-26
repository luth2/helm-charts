# Helm Chart Repo for EccoSP Charts

![ECCoSP](https://www.entsoe.eu/assets/graphics/uploads/ecco-sp-logo.png)

ENTSO-E Communication & Connectivity Service Platform (ECCo SP) is a standardized communication platform for the Energy market. It contains ECP (Energy Communication Platform) and EDX (ENTSO-E Data Exchange) as a software solution for establishing communication between TSOs.

## Documentation and Helm repository

**Portal and repository:** <https://luth2.github.io/helm-charts/>

```sh
helm repo add eccosp https://luth2.github.io/helm-charts/
helm repo update
helm search repo eccosp --versions
```

- [Quickstart: versioned packages, values and GitOps](Dokumentation/Helm_Repository.md)
- [Operations: Secrets, storage, HA and migration](Dokumentation/Helm_Charts.md)
- [Enable Pages and publish safely](Dokumentation/GitHub_Pages.md)
- [Published releases](https://github.com/luth2/helm-charts/releases)

Use the four standalone charts for new installations. The legacy umbrella chart
`ecco-sp` remains in the Helm index for existing users only.

## ECCo SP Security Feature

ECCo SP is a software for creating a secure, centrally managed network for data exchange. With ECCo SP, business applications can confidently exchange data with other organizations that are part of the same network. Unlike traditional methods like SFTP, SMTP, and MFT, ECCo SP automatically manages the PKI (Public Key Infrastructure) and allows only authorized participants to communicate. Additionally, ECCo SP stands apart from AS4 by being centrally governed and allowing for endpoints to be placed within a protected network zone, ensuring that they are shielded from external threats.

The key features of ECCo SP:

- All messaging offers Confidentiality, Authentication, Integrity and Non-Repudiation.
- The network can be scaled to support High Availability.
- Access to the network is restricted through a registration process and controlled centrally. Compromised endpoints can be excluded from the network.
- Secure Software Development Lifecycle, which guarantees regular vulnerability scanning, continuous updating of the software and immediate patching if necessary.

## Kubernetes deployment with Helm

The 5.x Helm charts use application images 4.17.0 by default and require Helm 3
and Kubernetes >= 1.28. There are exactly four standalone charts:
[charts/ecp-endpoint/README.md](charts/ecp-endpoint/README.md),
[charts/ecp-directory/README.md](charts/ecp-directory/README.md),
[charts/ecp-broker/README.md](charts/ecp-broker/README.md) and
[charts/eccosp-artemis/README.md](charts/eccosp-artemis/README.md).
Each chart is installed, upgraded and rolled back as an independent Helm release,
either from the Helm repository or locally; partner services are not installed automatically.
Explicitly pin the desired published chart version when installing.

For each release, copy the complete canonical chart values into a separate
operator-managed file and adapt them. Helm replaces instance lists rather than merging entries.
Each enabled instance requires an externally provisioned, populated
`existingSecret`; the unchanged defaults intentionally fail linting/rendering
because the Secret name is empty. Helm does not create Secrets or complete private configurations;
registration and keystore provisioning remain external operational tasks.

All four charts offer optional routing, with `instance[].gateway.enabled: false`
as the default. Prerequisites and examples: [Dokumentation/Gateway_API.md](Dokumentation/Gateway_API.md).

Five-step deployment, Secret key requirements, HA, rotation and safe migration
while preserving PVCs: [Dokumentation/Helm_Charts.md](Dokumentation/Helm_Charts.md).
Do not blindly upgrade existing releases: selectors and PVC names may change;
even `fullnameOverride` does not guarantee a compatible upgrade.
HA requires coordinated external configuration and suitable storage. Root
init containers prevent a blanket claim of Restricted PSA compliance despite
the non-root application, and may fail with NFS `root_squash`.

CI validates the four standalone charts with synthetic fixtures, linting, rendering
and package checks, then uses server-side dry-runs against temporary kind clusters
for every Kubernetes minor from 1.34 through the latest available in stable kind
releases. For Gateway resources, the pinned Gateway API CRD sources
v1.4.1 are downloaded over verified HTTPS and checked using SHA-256 before use.
This does not replace testing on the target cluster or runtime tests.

## ECP - Energy Communication Platform

![ECP](https://www.entsoe.eu/assets/graphics/uploads/thumbnail_0a1abssgsdcolbaj.png)

The purpose of the ECP is to provide message delivery capabilities with the following additional key features: Security, Reliability, Integration, Standard, Transparency, and Portability. ECP supports several integration channels such as AMQP(S), MADES Web Service (IEC 62325-504), and FSSF (File System Shared Folder).

ECP contains three components :

- The client component - ECP Endpoint
- The service provider components - ECP Component Directory and ECP Broker

## EDX - ENTSO-E Data Exchange

![EDX](https://www.entsoe.eu/assets/graphics/uploads/thumbnail_5y7u5lpwyjwcs4rm.png)

EDX is an additional and optional extension of ECP.

EDX is the communication platform for OPDE applications. It creates a distributed service platform where both service providers and consumers are connected via a state-of-the-art communication platform. It allows using additional integration channels for messaging. While ECP uses a fixed set of integration channels, EDX allows using (S)FTP, FSSP, MADES, SCP, or Web Services (e.g.: IEC 62325-504).

EDX also allows the implementation of new integration channels easily. It creates the basis for the OPDE platform and other ENTSO-E applications in the future that require reliable and secure communication.

EDX contains two components :

- The client component - EDX Toolbox
- The service provider component - EDX Service Catalogue
