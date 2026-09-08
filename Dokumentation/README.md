# ECCo SP Component Documentation

This directory provides a concise summary of the official ECCo SP documentation for the Helm charts maintained in this repository.

Official documentation home page:

- [ECCo SP Documents](https://eccosp-docs.entsoe.eu/k)

Components in this repository:

| Component | Repository chart | Summary | Official source |
| --- | --- | --- | --- |
| Endpoint | `charts/ecp-endpoint` | [Endpoint](./Endpoint.md) | [Endpoint Manual](https://eccosp-docs.entsoe.eu/s/ecco-sp/m/endpoint-manual) |
| Internal Broker | `charts/eccosp-artemis` | [Internal Broker](./Interner_Broker.md) | [Internal Broker Manual](https://eccosp-docs.entsoe.eu/s/ecco-sp/m/internal-broker-manual) |
| Broker | `charts/ecp-broker` | [Broker](./Broker.md) | [Broker Manual](https://eccosp-docs.entsoe.eu/s/ecco-sp/m/broker-manual) |
| Component Directory | `charts/ecp-directory` | [Component Directory](./Component_Directory.md) | [Component Directory Manual](https://eccosp-docs.entsoe.eu/s/ecco-sp/m/component-directory-manual) |

Summary as of: March 31, 2026.

## Kubernetes and Helm

- [Helm repository, quickstart and GitOps](./Helm_Repository.md)
- [Configuration, external Secrets, HA and migration](./Helm_Charts.md)
- [Gateway API and TLS](./Gateway_API.md)
- [GitHub Pages and publishing](./GitHub_Pages.md)

## Recommended Order on VMs

For traditional component installations on VMs, the following order makes sense from both a functional and an operational perspective:

1. Component Directory
2. Broker
3. Internal Broker
4. Endpoint

Rationale:

- The Component Directory is the trust and registration authority.
- The Broker requires the Component Directory for registration and synchronization.
- The Internal Broker must be available before an Endpoint can process messages internally.
- The Endpoint should be installed and registered last, once the services it depends on are reachable.

## Implications for Custom Container Builds

If you plan to build the containers yourself later, the VM perspective is helpful because it shows the actual runtime structure:

- Binary artifacts and startup scripts reside in the component's installation directories.
- Configuration, keystores and user files must be clearly separated from the image.
- Persistent data, journals and logs should be planned as separate directories or volumes.
- Certificates and registration-related keystores should never be baked into the image.
