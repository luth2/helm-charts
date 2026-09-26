# ECP Broker - Helm Chart

Standalone chart for ECP Broker 4.17.1, Helm 3, and Kubernetes >= 1.28.
Public defaults: [values.yaml](values.yaml).

Versioned packages instead of a local checkout:
[Helm Repository and Quickstart](../../Dokumentation/Helm_Repository.md).

## Required: Complete External Configuration

Each enabled instance requires `existingSecret` in the release namespace.
The empty default intentionally causes standalone linting/rendering to fail.
The chart does not create a Secret; successful rendering does not validate its contents.

| Secret Key | Usage |
| --- | --- |
| `broker.properties` | /opt/ecp-broker/config/broker.properties |
| `artemis-users.properties` | /opt/ecp-broker/broker/etc/artemis-users.properties |
| `bootstrap.xml` | With an HTTP/HTTPS Service: /opt/ecp-broker/broker/etc/bootstrap.xml |
| `broker.xml` | Single: /opt/ecp-broker/broker/etc/broker.xml |
| `broker-master.xml`, `broker-slave.xml` | HA instead of `broker.xml`: Inputs for the unprivileged HA init container |

The default values enable HTTPS, so `bootstrap.xml` is required here.
Create complete files outside the repository according to the official ECP configuration.
Coordinate AMQPS port 5671, web port 8161, TLS/client authentication, users,
keystore paths, ECP code, and Directory/registration data externally.
`artemisUsers` contains only logins for the public `amq` role mapping,
not passwords, and does not create accounts automatically.

Old `brokerProperties`, private `brokerXml` fields, and password values do not
modify the complete external files. Set `instance[].prometheusEnabled: true` to
add `eu.entsoe.ecp.artemis.plugin.prometheus.EcpPrometheusMetricsPlugin` with
`ecpBrokerPropertiesLocation=/opt/ecp-broker/config/broker.properties` to the
effective broker XML, and `metrics.war` to each web binding in `bootstrap.xml`.
The external Secret remains unchanged: an unprivileged Python init container
copies and updates its XML in the broker's writable configuration volume, after
HA configuration when applicable. An HTTP/HTTPS service and its `bootstrap.xml`
Secret key are required. Existing matching plugin and web-app entries are not
duplicated. Verify the broker image contains the plugin and WAR before rollout;
the metrics endpoint still needs appropriate web access controls.

For airgapped clusters, mirror every required image into an internal Artifactory
Docker repository and configure the full image paths in your deployment values:

```yaml
global:
  imageBusybox:
    name: artifactory.intern.example/docker/busybox
    tag: '1.37.0'
  imageMetricsPython:
    name: artifactory.intern.example/docker/python
    tag: '3.12-alpine'
  imagePullSecrets:
    - name: artifactory-pull
```

Set `instance[].image.name` to the mirrored `entsoe/ecp-broker` image's full
Artifactory path in the complete instance values. `imageMetricsPython` is pulled
only when `prometheusEnabled` is true; the mirrored image must provide `python3`.
The pull Secret must already exist in the release namespace. No chart downloads
or mirrors images automatically. Do not place registry credentials in values.

The named `configuration` template renders only public configuration.
Complete private files are not rendered at all, even internally; private legacy
data sections and dummy values have been removed. The `omit` lists in `publicConfig`
and the ConfigMap output remain a defensive safeguard for reserved private
file keys, not a validation of external Secret contents.

## Public Defaults

- One replica, ClusterIP, UID/GID/fsGroup 2000; image tag `'4.17.1'`.
- `env.resourcesJvm`: JVM heap in the public Artemis startup configuration.
- Data and journal PVCs: 1Gi each; separate registration tool logs: 64Mi.
  This logs PVC does not mean that the chart performs registration.
- `keepLogsAfterRestart: false`: Broker logs on `emptyDir`; a dedicated PVC when `true`.
- Shared journal and shared configuration are disabled; both storage classes are empty.
  No NFS assumption. HA sizes are explicitly set to 1Gi.
- `brokerXml.highAvailability.acceptor.port` controls the HA port of the Pod and
  headless Service; the value must also be correct in the external XML.
- Startup/readiness enabled, liveness disabled; interval 10s/timeout 2s for each, startup threshold 60.

Single-instance probes and HA readiness check only TCP, not TLS, authentication, or
message transport. HA startup/liveness check only PID 1. This is not a robust
application-level health check; passive backups may intentionally be NotReady.

## Ingress and Gateway API

Ingress remains available; alternatively, `instance[].gateway.enabled: true` creates
an HTTPRoute for the web Service. For HTTPS, a
BackendTLSPolicy v1 with an explicit backend certificate name and CA trust is also created.
The Gateway/controller/CRDs must already exist. AMQP(S) is not routed.
Both access methods are disabled by default and can be used in parallel for migration.
[Gateway Configuration and TLS Prerequisites](../../Dokumentation/Gateway_API.md).

## Standalone Validation

From the repository root, without cluster access:

```sh
helm lint ./charts/ecp-broker --namespace eccosp -f ./charts/ecp-broker/values.yaml --set 'instance[0].existingSecret=ecp-broker-br-config'
helm template platform ./charts/ecp-broker --namespace eccosp -f ./charts/ecp-broker/values.yaml --set 'instance[0].existingSecret=ecp-broker-br-config'
```

`-f` loads the complete list before `--set`; otherwise, an isolated list-index override
replaces the chart default list. Service: `platform-ecp-broker-br-svc`.
`service.amqp` is rejected; `service.amqps.port` is the supported port key.
The key alone does not enable encryption in the external broker XML.

## HA, Rotation, and Migration

Multiple replicas require a shared journal, an explicit suitable RWX storage class,
`ReadWriteMany`, and `useSharedStorageForConfiguration: false`.
Keystores remain on per-Pod PVCs; the etc working directory is an `emptyDir`.
External master/slave XML must correctly specify headless DNS, ports, shared-store paths, and
the placeholders for HA initialization. See the central guide for details.

HA uses `Parallel` and `OnDelete`. Secret change -> increment `secretRevision`,
then perform controlled manual Pod restarts. Even public
checksums do not trigger automatic replacement of running Pods with `OnDelete`.
Helm does not check external Secret contents or register ECP components.

Root init containers for seeding/ownership are not compatible with
Restricted PSA despite using minimal capabilities. Clarify `root_squash`, ownership, and journal locking
with the storage operator beforehand. Do not blindly upgrade from versions before 5.0.0 or
rely on `fullnameOverride` alone: Selector/headless Service/PVC changes
require backup/restore and staged migration.

[../../Dokumentation/Helm_Charts.md](../../Dokumentation/Helm_Charts.md)
