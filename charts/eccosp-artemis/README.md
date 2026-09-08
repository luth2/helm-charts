# ECCoSP Artemis - Helm Chart

Standalone chart for the internal broker 4.17.0, Helm 3, and Kubernetes >= 1.28.
Public defaults: [values.yaml](values.yaml).

Versioned packages instead of a local checkout:
[Helm Repository and Quickstart](../../Dokumentation/Helm_Repository.md).

## Required: Complete External Configuration

Each enabled instance requires `existingSecret` in the release namespace.
The empty default is intentional: Standalone linting/rendering with unchanged defaults fails.
The chart does not create Secrets or check their existence or contents.

| Secret Key | Usage |
| --- | --- |
| `artemis-users.properties` | /opt/eccosp-artemis/etc/artemis-users.properties |
| `bootstrap.xml` | With an HTTP/HTTPS Service: /opt/eccosp-artemis/etc/bootstrap.xml |
| `broker.xml` | Single: /opt/eccosp-artemis/etc/broker.xml |
| `broker-master.xml`, `broker-slave.xml` | HA instead of `broker.xml`: Inputs for the unprivileged HA init container |

Because the defaults include HTTPS, `bootstrap.xml` is required. Create all files
externally and in full according to the official configuration. Set AMQPS port 5672,
web port 8161, TLS, users, keystores, and the audit/ECP identifier correctly.
Do not store Secret manifests or complete private file examples in the repository.

`artemisUsers` contains only `login` for the public `amq` role mapping;
this does not create the `endpoint` and `toolbox` accounts. The external
user files and client configurations must match.
Private `brokerXml` values, `artemisKeystoreLocation`, `artemisKeystorePassword`,
or `prometheusEnabled` do not modify any external files. The named
`configuration` template renders only public configuration. Complete private files
are not rendered at all, even internally; private legacy data sections and
dummy values have been removed. The `omit` lists in `publicConfig` and the
ConfigMap output remain a defensive safeguard for reserved private file keys,
not a validation of external Secret contents.

## Public Defaults

- One replica, ClusterIP, UID/GID/fsGroup 2030; image tag `'4.17.0'`.
- `env.resourcesJvm`: Heap in the public Artemis startup configuration.
- Data/keystore PVC and journal PVC: 1Gi each. Logs use `emptyDir` by default,
  with a dedicated logs PVC when `keepLogsAfterRestart: true`.
- Shared configuration and shared journal are disabled; both storage classes are empty, with no
  NFS assumption. Shared storage sizes are 1Gi each when explicitly enabled.
- `brokerXml.highAvailability.acceptor.port`: HA port of the Pod/headless Service,
  not a modification of the external XML configuration.
- Startup/readiness enabled, liveness disabled; interval 10s, timeout 2s,
  startup threshold 60. This does not enable JMX.

Single-instance probes and HA readiness check only TCP reachability. HA startup/liveness
check only PID 1 so that passive backups are not restarted because of a missing
AMQP listener. Neither variant checks overall broker health,
TLS, or successful message processing.

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
helm lint ./charts/eccosp-artemis --namespace eccosp -f ./charts/eccosp-artemis/values.yaml --set 'instance[0].existingSecret=eccosp-artemis-eptb1-config'
helm template platform ./charts/eccosp-artemis --namespace eccosp -f ./charts/eccosp-artemis/values.yaml --set 'instance[0].existingSecret=eccosp-artemis-eptb1-config'
```

The complete list is loaded with `-f` and only then modified with `--set`.
Helm does not merge lists with chart defaults element by element.
Service: `platform-eccosp-artemis-artemis-eptb1-svc`.
`service.amqp` is rejected; `service.amqps.port` remains the port key even
when a different transport configuration is selected externally. Configure TLS externally.

## HA, Rotation, and Migration

Multiple replicas require a shared journal on an explicit suitable
RWX storage class, `ReadWriteMany`, and no shared configuration storage.
Keystores and the generated HA working XML reside on the respective data PVC.
The external HA input files must be fully prepared; Helm
does not invent cluster credentials or a suitable topology.

HA uses `Parallel`/`OnDelete`: After Secret changes, increment `secretRevision`
and perform controlled manual Pod restarts. Public checksums
do not track external Secret contents or bypass `OnDelete`.
Registration and certificate provisioning are external, not bundled as hooks.

Root init containers for seeding/ownership remain incompatible with Restricted PSA;
`root_squash` and ownership require a coordinated storage solution.
When migrating from versions before 5.0.0, handle selector, headless Service, and PVC changes with backup/restore.
`fullnameOverride` does not guarantee an in-place upgrade.

[../../Dokumentation/Helm_Charts.md](../../Dokumentation/Helm_Charts.md)
