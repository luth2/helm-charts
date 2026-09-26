# ECP Endpoint - Helm Chart

Standalone chart for ECP Endpoint 4.17.1, Helm 3, and Kubernetes >= 1.28.
The canonical public configuration is in [values.yaml](values.yaml).
Versioned packages instead of a local checkout:
[Helm Repository and Quickstart](../../Dokumentation/Helm_Repository.md).
Use this standalone chart for new installations, not the legacy umbrella chart.

## Required: External Secret

Each enabled `instance` requires `existingSecret` in the release namespace.
The empty default is intentional: Standalone linting/rendering with unchanged defaults fails.
The chart creates neither a Secret nor complete private configurations for operation.

| Secret Key | Mount Target |
| --- | --- |
| `ecp.properties` | /etc/ecp-endpoint/ecp.properties |
| `ecp-users.properties` | /etc/ecp-endpoint/ecp-users.properties |
| `ecp-password.properties` | /etc/ecp-endpoint/ecp-password.properties |
| `server.xml` | /usr/share/ecp-endpoint/conf/server.xml |
| `users.properties` | /etc/ecp-endpoint/users.properties |
| `jmxremote.password`, `jmxremote.ssl` | Additionally required when `jmxRemoteProperties` is set and nonempty; default location: /etc/ecp-endpoint/ |

All keys contain complete, externally maintained files that follow the official
ECP configuration. Ports, database, TLS, users, keystores, and the connection to
the internal broker must be configured correctly there. An existing Secret name alone
is not sufficient for a functional startup. Helm checks neither existence nor content.
Do not store Secret files or private configuration examples in this repository.

For an airgapped cluster, mirror the application and BusyBox images to your
internal registry. Set `instance[].image.name` to the full repository path of
the mirrored `entsoe/ecp-endpoint` image in the complete instance values, and
configure the shared images and pull credentials for this release:

```yaml
global:
  imageBusybox:
    name: artifactory.intern.example/docker/busybox
    tag: '1.37.0'
  imagePullSecrets:
    - name: artifactory-pull
```

The pull Secret must exist in the release namespace. The chart does not mirror
images, create registry credentials, or provision the external HA database.

## What Values Actually Control

- Kubernetes: Image, replicas, resources, storage, Services, Ingress, and probes.
- `envConf.resourcesJvm` and `envConf.ecpLogFullStackTrace`: Public JVM startup configuration.
- `ecpProperties.dataDirectory` and `loggingFilePath`: PVC mount paths.
- `springProfilesActive`: HA validation; the actual runtime profile comes
  from the Secret. Also set `console-logging` there.
- `loggingFileName` and `loggingConfig`: Documented path alignment, not an update
  to the external file. The chart provides the public Logback configuration.
- `internalBrokerAuthUser`: Public group mapping for `admins`,
  `tempDestinationAdmins`, and `users`. The corresponding users and credentials
  must exist in the complete external configurations.
- Populate the optional `usersProperties.users` with `login` only if additional
  public group members are needed; never include a password.
- `sessionReplication`: Public Tomcat context and discovery environment;
  the matching cluster configuration in the external `server.xml` remains the operator's responsibility.
- `instance[].jmxRemoteUsers: [{login: monitor, access: readonly}]`: Public
  JMX access mapping directly on the instance, not under `jmxRemotePassword`.
  Old nested user lists are not evaluated. The external
  `jmxremote.password` must match these logins; do not put passwords in values.
  When `jmxRemoteProperties` is nonempty, password and SSL files are required,
  even if individual switches are set to false. Helm does not validate Secret contents.

Other old `ecpProperties`, `ecpUsersProperties`, and `ecpPasswordProperties`
do not modify the mounted private files. The internal named
`configuration` template renders only public configuration; complete private files
are not rendered at all, even internally. Private legacy data sections and
dummy values have been removed. The `omit` lists in `publicConfig` and the
ConfigMap output remain a defensive safeguard for reserved private file keys,
not a validation of external Secret contents.
An additional Artemis bootstrap mount is not part of the basic Endpoint configuration.

## Ingress and Gateway API

Ingress remains available; alternatively, `instance[].gateway.enabled: true` creates
an HTTPRoute for the web Service. For HTTPS, a
BackendTLSPolicy v1 with an explicit backend certificate name and CA trust is also created.
The Gateway/controller/CRDs must already exist. AMQP(S) is not routed.
Both access methods are disabled by default and can be used in parallel for migration.
[Gateway Configuration and TLS Prerequisites](../../Dokumentation/Gateway_API.md).

## Defaults and Validation

One replica, HTTPS 8443, UID/GID/fsGroup 2000, data PVC 1Gi, logs PVC 256Mi.
JMX is not enabled, including in the EP2 example. Startup and readiness are
enabled, liveness is disabled; interval 10s, timeout 2s, startup threshold 60.
TCP probes check only transport reachability, not the TLS handshake, database, or ECP health.
Set `databaseWait.enabled: true` with a database `host` and `port` on an instance
to wait for TCP reachability before startup. Optional `attempts` (default 30)
and `intervalSeconds` (default 2) bound the wait. This does not authenticate,
execute SQL, or check the schema; keep credentials in the external Secret.

From the repository root, without cluster access:

```sh
helm lint ./charts/ecp-endpoint --namespace eccosp -f ./charts/ecp-endpoint/values.yaml --set 'instance[0].existingSecret=ecp-endpoint-ep1-config'
helm template platform ./charts/ecp-endpoint --namespace eccosp -f ./charts/ecp-endpoint/values.yaml --set 'instance[0].existingSecret=ecp-endpoint-ep1-config'
```

The explicit `-f` preserves the complete instance when the subsequent `--set` is applied.
Do not set a Secret name using only a list index: Helm does not merge chart default
and override lists element by element. Include all fields in custom lists.
The Service in this example is named `platform-ecp-endpoint-ep1-svc`.

## Operations, HA, and Migration

More than one replica requires `ecp-ha`, a supported external JDBC driver,
and `ecpDBUrl` in `ecpProperties` for helper validation. The same database
configuration, including credentials, must be set externally; there is
no database check by default. A second standalone Endpoint is not an HA replica.

Secret change -> increment `secretRevision` and plan a Pod restart.
Public ConfigMap checksums do not track external Secret contents.
Root init containers for seeding/ownership are not
compatible with Restricted PSA despite their limited capabilities; check NFS `root_squash` beforehand.
Keystores remain on the PVC initialized from the image; registration is
external and is not performed by Helm hooks.

Do not blindly upgrade from versions before 5.0.0: Selector, headless Service, and PVC names may
change. Even `fullnameOverride` does not guarantee upgrade compatibility.
Procedure, backup/restore, Secret rotation, and complete key migration:
[../../Dokumentation/Helm_Charts.md](../../Dokumentation/Helm_Charts.md).
