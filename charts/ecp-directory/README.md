# ECP Component Directory - Helm Chart

Standalone chart for ECP Directory 4.17.1, Helm 3, and Kubernetes >= 1.28.
Public defaults: [values.yaml](values.yaml).

Versioned packages instead of a local checkout:
[Helm Repository and Quickstart](../../Dokumentation/Helm_Repository.md).

## Required: External Secret

Each enabled instance requires `existingSecret` in the release namespace.
`existingSecret: ''` intentionally causes standalone linting/rendering with unchanged defaults
to fail. Helm does not create Secrets or check external Secret contents.

| Secret Key | Mount Target |
| --- | --- |
| `ecp-directory.properties` | /etc/ecp-directory/ecp-directory.properties |
| `ecp-users.properties` | /etc/ecp-directory/ecp-users.properties |
| `ecp-password.properties` | /etc/ecp-directory/ecp-password.properties |
| `server.xml` | /usr/share/ecp-directory/conf/server.xml |
| `jmxremote.password`, `jmxremote.ssl` | Additionally required when `jmxRemoteProperties` is set and nonempty; default location: /etc/ecp-directory/ |

Maintain complete files outside the repository according to the official ECP configuration
and provide them before installation. Ports, database, TLS, users, and CA,
registration, and authentication keystores must match the environment.
Do not create complete private files or Secret manifests in this repository.

For an airgapped cluster, mirror the application and BusyBox images to your
internal registry. Set `instance[].image.name` to the full repository path of
the mirrored `entsoe/ecp-directory` image in the complete instance values, and
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

## Public Values and Their Limits

`envConf` controls JVM startup configuration; Kubernetes values control resources,
Services, storage, and probes. `dataDirectory` and `loggingFilePath` under
`ecpDirectoryProperties` are used as PVC mount paths. `springProfilesActive`
is used for HA validation. Runtime profiles, including `console-logging`,
as well as `loggingFileName` and `loggingConfig`, must be set appropriately in the complete external
configuration. Helm provides the public Logback configuration but does not replace
any properties file in the Secret.

`sessionReplication: true` provides the public context and
`DNS_MEMBERSHIP_SERVICE_NAME`. The required Tomcat cluster configuration must
also be present in the external `server.xml`. The chart does not enable it there.
Users, including roles, are managed exclusively externally; an empty
Directory role mapping can be retained in accordance with the official configuration.
Helm does not add a role.

`instance[].jmxRemoteUsers: [{login: monitor, access: readonly}]` controls only the
public JMX access mapping. The list is directly on the instance, not
under `jmxRemotePassword`; old nested user lists are no longer supported.
The external `jmxremote.password` must match these logins; do not put passwords in
values. When `jmxRemoteProperties` is nonempty, password and SSL files are
required, even if individual switches are set to false. Helm does not check their contents
or whether they match the access list.

Old private `ecpDirectoryProperties`, `ecpUsersProperties`, and
`ecpPasswordProperties` do not modify any external file. The internal named
`configuration` template renders only public configuration.
Complete private files are not rendered at all, even internally; private legacy
data sections and dummy values have been removed. The `omit` lists in `publicConfig`
and the ConfigMap output remain a defensive safeguard for reserved private
file keys, not a validation of external Secret contents.

## Ingress and Gateway API

Ingress remains available; alternatively, `instance[].gateway.enabled: true` creates
an HTTPRoute for the web Service. For HTTPS, a
BackendTLSPolicy v1 with an explicit backend certificate name and CA trust is also created.
The Gateway/controller/CRDs must already exist. AMQP(S) is not routed.
Both access methods are disabled by default and can be used in parallel for migration.
[Gateway Configuration and TLS Prerequisites](../../Dokumentation/Gateway_API.md).

## Defaults and Validation

One replica, HTTPS 8443, UID/GID/fsGroup 2000, data PVC 1Gi, logs PVC 256Mi.
Startup and readiness are enabled, liveness is disabled. Interval 10s, timeout 2s,
startup threshold 60. TCP checks neither the database nor TLS or application-level health.
Set `databaseWait.enabled: true` with a database `host` and `port` on an instance
to wait for TCP reachability before startup. Optional `attempts` (default 30)
and `intervalSeconds` (default 2) bound the wait. This does not authenticate,
execute SQL, or check the schema; keep credentials in the external Secret.
JMX remains disabled by default.

From the repository root, without cluster access:

```sh
helm lint ./charts/ecp-directory --namespace eccosp -f ./charts/ecp-directory/values.yaml --set 'instance[0].existingSecret=ecp-directory-cd-config'
helm template platform ./charts/ecp-directory --namespace eccosp -f ./charts/ecp-directory/values.yaml --set 'instance[0].existingSecret=ecp-directory-cd-config'
```

`-f` is important here: Lists are replaced, not merged with chart defaults
element by element. The subsequent `--set` modifies the already complete
instance. Service: `platform-ecp-directory-cd-svc`.

## Operations, HA, and Migration

Multiple replicas require `ecp-ha`, `springDatasourceDriverClassName`, and an
external `ecpDBUrl` in `ecpDirectoryProperties` for validation.
This configures neither the external database nor the contents of the Secret.
There is no database check by default and no registration hook.
Keystores are initialized from the image onto the PVC; registration and
certificate provisioning remain external.

Secret contents changed -> increment `secretRevision` and plan a restart.
ConfigMap checksums do not cover external Secret contents.
Root init containers for seeding/ownership are not compatible with Restricted PSA;
with `root_squash`, a coordinated storage/ownership solution is required.

Do not blindly install 5.0.0 over old releases: Compare immutable selector
and StatefulSet fields as well as PVC names. `fullnameOverride` alone
is not sufficient. Backup/restore and staged migration are documented in
[../../Dokumentation/Helm_Charts.md](../../Dokumentation/Helm_Charts.md).
