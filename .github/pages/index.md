---
hide:
  - toc
---

<!-- markdownlint-configure-file {"MD033": {"allowed_elements": ["div"]}} -->

# ECCoSP on Kubernetes

<div class="portal-lead" markdown>
Four standalone Helm charts. One starting point for installing, configuring
and securely operating the Energy Communication Platform.
</div>

[Get started with Helm](Dokumentation/Helm_Repository.md){ .md-button .md-button--primary }
[Explore the charts](charts/index.md){ .md-button }

## One repository for documentation and charts

**Helm repository:** <https://luth2.github.io/helm-charts/>

```sh
helm repo add eccosp https://luth2.github.io/helm-charts/
helm repo update
helm search repo eccosp --versions
```

The website explains operations. At the same address, Helm reads the
[repository index](https://luth2.github.io/helm-charts/index.yaml) and downloads
versioned chart packages. No source code checkout is required.

<div class="grid cards" markdown>

- **Component Directory**

    ---

    Central trust and registration authority for the ECP network.

    [Configure the directory](charts/ecp-directory/README.md)

- **ECP Broker**

    ---

    Message routing between network participants.

    [Configure the broker](charts/ecp-broker/README.md)

- **Internal Artemis broker**

    ---

    Internal message transport for connected components.

    [Configure Artemis](charts/eccosp-artemis/README.md)

- **ECP Endpoint**

    ---

    Connect business applications to the ECP network.

    [Configure the endpoint](charts/ecp-endpoint/README.md)

</div>

## From package to operation

1. **Choose a version:** Check published packages in the [chart catalog](charts/index.md).
2. **Prepare values:** Retrieve the complete defaults for the selected version.
3. **Meet the prerequisites:** Provision the namespace, images, storage, external Secrets and partner services.
4. **Render and install:** Treat each chart as a separate, versioned Helm release.
5. **Perform acceptance testing:** Verify registration, TLS, the database and message flow.

!!! warning "Do not deploy with unchanged defaults"
    The charts do not create private Secrets. Each enabled instance needs
    complete external configuration. Successful Helm rendering replaces
    neither registration nor functional testing. Do not blindly upgrade
    existing releases: [Migration and PVC preservation](Dokumentation/Helm_Charts.md).

## Further reading

- [Operations guide: Secrets, HA, storage and updates](Dokumentation/Helm_Charts.md)
- [Gateway API and TLS](Dokumentation/Gateway_API.md)
- [Components and official ENTSO-E documentation](Dokumentation/README.md)
- [GitHub Releases](https://github.com/luth2/helm-charts/releases)

The legacy umbrella chart **ecco-sp** remains in the repository for existing
users. For new installations, use only the four standalone charts.
These charts do not install EDX Toolbox, Service Catalogue or databases.
