# ECCoSP Helm Charts: Configuration and Operations

To install versioned packages without a Git checkout, see:
[Helm Repository and Quickstart](Helm_Repository.md).
The local examples in this guide are intended for working with chart sources.

## Recommendation and Scope

Set up new installations with explicit instance values and external Secrets
that have already been provisioned. Back up existing installations first and
migrate them in stages; do not blindly update them with `helm upgrade`.

The four standalone charts in the **5.x series** use `appVersion` **4.17.0** and require
Kubernetes >= 1.28 and Helm 3. CI uses Helm 3.19.0.
Chart versions and image versions are separate versioning dimensions.
The default image tags are strings, not `latest`; BusyBox is set to 1.37.0.
The images must be available for the target environment, and their use and
runtime compatibility must be approved. Alternatively, `image.digest` can use
SHA-256; when a digest is set, it takes precedence over the tag.
`image.name` contains the full repository; `image.registry` is invalid.

### Versioning and Names

- `Chart.yaml: version` versions the Helm chart: package `ecp-broker-5.0.0.tgz`
    and GitHub release/tag `ecp-broker-5.0.0`. When changing the chart, increment
    this version for a new publication.
- `Chart.yaml: appVersion` describes the application. It can change independently
    of the chart version and determines neither package names nor dependency versions.
- `instance[].image.tag` or `image.digest` determines the actual container image;
    `appVersion` does not set the tag automatically.
- Kubernetes resource names remain `<release>-<chart>-<instance>` (truncated/hashed
    if necessary), without a chart or application version. Including a version in the
    StatefulSet name would create new resource names and different PVC mappings during upgrades.
- Previously published chart versions are not overwritten
    (`skip-existing`). Use a new chart version for a changed publication.

| Chart | Purpose | Canonical Defaults |
| --- | --- | --- |
| [../charts/ecp-endpoint/README.md](../charts/ecp-endpoint/README.md) | Endpoint | [../charts/ecp-endpoint/values.yaml](../charts/ecp-endpoint/values.yaml) |
| [../charts/ecp-directory/README.md](../charts/ecp-directory/README.md) | Component Directory | [../charts/ecp-directory/values.yaml](../charts/ecp-directory/values.yaml) |
| [../charts/ecp-broker/README.md](../charts/ecp-broker/README.md) | ECP Broker | [../charts/ecp-broker/values.yaml](../charts/ecp-broker/values.yaml) |
| [../charts/eccosp-artemis/README.md](../charts/eccosp-artemis/README.md) | Internal Artemis Broker | [../charts/eccosp-artemis/values.yaml](../charts/eccosp-artemis/values.yaml) |

Chart sources are located exclusively under `charts/`. Each component is
installed, upgraded, and rolled back as an independent Helm release, either
from the Helm repository or locally from its chart directory. These charts have
no shared platform release and no dependency build. Partner services and their
connections must be provisioned and configured separately.
The charts do not install databases, EDX Toolbox, or Service Catalogue.

## Configuration Contract: Strictly Separate Public and Private Configuration

Every enabled instance requires `instance[].existingSecret` in the release namespace.
The standalone defaults deliberately leave this string empty: linting and rendering
without operator configuration are intended to fail. Each default instance is
enabled; an empty Secret field is not a deployment-ready configuration.

Helm creates **no Secret**. It projects a public ConfigMap together with selected
keys from an existing Secret and mounts the files.
It checks neither the existence of the Secret nor the semantic validity of its
contents. Missing keys prevent the Pod from starting; unsuitable contents can
cause application errors even when Helm rendering succeeds.

### Required Secret Keys

Each key contains a **complete file**, not just an individual password value.
There is no merge between values and the external full configuration.

| Component | Always Required | Conditionally Required |
| --- | --- | --- |
| EP | `ecp.properties`, `ecp-users.properties`, `ecp-password.properties`, `server.xml`, `users.properties` | If `jmxRemoteProperties` is non-empty: `jmxremote.password`, `jmxremote.ssl` |
| CD | `ecp-directory.properties`, `ecp-users.properties`, `ecp-password.properties`, `server.xml` | If `jmxRemoteProperties` is non-empty: `jmxremote.password`, `jmxremote.ssl` |
| BR | `broker.properties`, `artemis-users.properties` | Single: `broker.xml`; HA: `broker-master.xml` and `broker-slave.xml`; with a web service: `bootstrap.xml` |
| AR | `artemis-users.properties` | Single: `broker.xml`; HA: `broker-master.xml` and `broker-slave.xml`; with a web service: `bootstrap.xml` |

A web service means a configured `service.http` or `service.https`.
The broker defaults include HTTPS, so they require `bootstrap.xml`.
For HA, the master/slave inputs are processed by the unprivileged init container;
the resulting working XML is not a full configuration rendered by Helm from
private values.

Create complete private configuration files outside the repository using the
official ECP/Artemis configuration for the image version, and provision them
through the approved Secret process. Do not add Secret manifests, examples of
complete private configuration files, credentials, or keystores to this repository.
In particular, do not copy old template defaults as safe operational values.

Before startup, the following must be consistent across these external files:

- Actual listener ports, bind addresses, Service/Pod DNS, and external URLs.
- Database URL, driver, schema, credentials, connection parameters, and HA profile.
- TLS protocols, certificates, client authentication, truststore/keystore paths,
   aliases, and associated passwords.
- Users, roles, ECP/audit identifiers, registration data, and internal broker
   connections; do not use fixed example identifiers as production identities.
- Data, journal, logging, and other file paths must match the existing mounts.
- For HA, shared-store topology, connectors, and cluster authentication.

### What the Remaining Values Control

| Area | Actual Effect |
| --- | --- |
| `image`, `replicaCount`, `resourcesK8s`, `securityContext`, Storage, Service, Ingress, Gateway, Probes | Kubernetes resources and Pod configuration |
| EP/CD `envConf.resourcesJvm`, `envConf.ecpLogFullStackTrace` | Public JVM startup configuration |
| BR/AR `env.resourcesJvm` | Public Artemis startup configuration |
| EP/CD `dataDirectory`, `loggingFilePath` | Data/log PVC mount paths; external properties must match |
| EP/CD `springProfilesActive` | HA helper validation; the runtime/logging profile must also be set externally |
| EP/CD `loggingFileName`, `loggingConfig` | Explicit path consistency check; no changes to external properties |
| EP `ecpProperties.internalBrokerAuthUser` | Username in the public group mapping; does not create an account |
| EP optional `usersProperties.users[].login` | Additional public group members; passwords are external only |
| EP/CD `instance[].jmxRemoteUsers` with `login`/`access` | Public JMX access mapping; matching password file is external |
| BR/AR `artemisUsers[].login` | Public `amq` role mapping; users/credentials are external |
| EP/CD `sessionReplication` | Public Tomcat context and DNS environment; matching external server XML is still required |
| BR/AR `brokerXml.highAvailability.acceptor.port` | HA port of the Pod and headless Service, not the contents of external XML files |

The Logback/Log4j configuration is provided as public configuration. Setting
`console-logging` in EP/CD values alone does not enable the runtime profile; it
must also be present in the Secret. Private user lists are no longer part of values.
For CD, an empty role mapping may be retained externally in accordance with the
official configuration; Helm does not insert an assumed default role.

The internal named `configuration` template renders public configuration only.
Complete private configuration files are **not rendered at all**, even internally;
legacy private data sections and dummy values have been removed.
The `omit` lists in `publicConfig` and the ConfigMap output remain as a
defensive safeguard for reserved private file keys. Old private values do not
control any externally mounted file. Neither these filters nor successful rendering
validate Secret contents or their consistency with values.
Do not use `configMap`, environment variables, or additional mounts to bypass
this contract for private contents.

## Examples, Lists, and Global Settings

For each release, copy the complete canonical values of the appropriate chart into
a dedicated operator values file. Check all instance settings in that file, especially
the name, `existingSecret`, image, storage, resources, ports, and external connections.
The following Secret names are placeholders for objects to be provisioned externally,
not Secrets supplied by the charts.

| Chart | Release | Instance | `existingSecret` |
| --- | --- | --- | --- |
| Endpoint | `ep1` | `ep1` | `ecp-endpoint-ep1-config` |
| Directory | `cd` | `cd` | `ecp-directory-cd-config` |
| ECP Broker | `br` | `br` | `ecp-broker-br-config` |
| Internal Artemis Broker | `eptb1` | `artemis-eptb1` | `eccosp-artemis-eptb1-config` |

**Helm replaces lists.** For multiple instances of the same chart, maintain one
complete `instance` list containing all entries, or use separate releases.
Two `-f` files with one instance each are not merged:
the last list wins. Values for different charts belong in separate Helm
invocations, not in a single combined invocation. Two independent instances
are not an HA cluster. An additional Endpoint instance does not enable JMX automatically.

`global` is at the root of each standalone values file and applies only to that
release. Deliberately maintain shared operator values in all affected files
rather than unintentionally overwriting storage or registry configuration:

- `global.storage.class: ''`: `storageClassName` is omitted for normal PVCs;
   the cluster's default StorageClass is used.
- `global.storage.class: '-'`: an explicitly empty StorageClass, with no dynamic
   default provisioning; matching static PVs must exist.
- Any other string names the desired StorageClass. The chart does not create
   any class; shared-storage classes are set separately.
- `global.imagePullSecrets: []`: no registry credentials are assumed.
   Reference existing pull Secrets in the target namespace if needed.
- `global.imageBusybox`: `busybox` with tag `'1.37.0'`.

## Deployment in Five Steps

The following commands are examples for the operator, not actions executed here.
All paths are relative to the repository root. For a new installation, we use
the separate releases `cd`, `br`, `eptb1`, and `ep1` in the namespace
`eccosp`. The operator values files reside in the `../eccosp-values` directory,
which you must create outside the repository; they contain no complete private
configuration files.

### 1. Clarify the Target Environment and Migration Requirements

Approve the Kubernetes version, image access, storage, capacity, network/TLS,
namespace policies, and required external databases. For an existing installation,
complete the migration section first. The example sizes are starting points,
not production sizing. JVM heap plus native memory must remain below the
container limit; adjust requests based on load measurements.

### 2. Prepare the Full Configuration and Secrets

Create the required complete files **outside the repository** according to the
contract above. Have the target namespace and all required Secrets provisioned
through the approved operational process. They must be fully populated before
step 5; an empty Secret placeholder is insufficient. The examples do not create
users, databases, TLS certificates, or ECP registrations.

Align the external files for the four independent releases with these Services:

| Connection | Address Within the Same Namespace |
| --- | --- |
| Directory | `https://cd-ecp-directory-cd-svc:8443/ECP_MODULE` |
| ECP Broker | `amqps://br-ecp-broker-br-svc:5671` |
| Endpoint EP1 | `https://ep1-ecp-endpoint-ep1-svc:8443` |
| Internal Broker for EP1 | `amqps://eptb1-eccosp-artemis-artemis-eptb1-svc:5672` |

These addresses are examples for the external configurations, not Helm
substitutions. Different release/instance names or namespaces require different
addresses and matching certificates. Define ECP component codes externally
according to the registration procedure; do not derive them from Kubernetes names.

### 3. Prepare Complete Operator Values

Copy each set of canonical values linked above in full: Directory to
`../eccosp-values/cd.yaml`, ECP Broker to `../eccosp-values/br.yaml`,
Artemis to `../eccosp-values/eptb1.yaml`, and Endpoint to
`../eccosp-values/ep1.yaml`. These files are not supplied.
The default instance names match the table above. In each file, set
`instance[0].existingSecret` to the corresponding provisioned Secret,
and review and adapt the entire configuration for the target environment.
`instance` and `global` remain directly at the values root, without a chart-name prefix.
Do not overlay the defaults with reduced lists containing only a name and Secret.
Maintain a complete entry for each additional instance.
A local Helm installation is required only to run the examples,
not to read or modify the values.

### 4. Lint and Render Without a Cluster

Check each release separately with its complete operator values file:

```sh
helm lint ./charts/ecp-directory --namespace eccosp -f ../eccosp-values/cd.yaml
helm template cd ./charts/ecp-directory --namespace eccosp -f ../eccosp-values/cd.yaml
helm lint ./charts/ecp-broker --namespace eccosp -f ../eccosp-values/br.yaml
helm template br ./charts/ecp-broker --namespace eccosp -f ../eccosp-values/br.yaml
helm lint ./charts/eccosp-artemis --namespace eccosp -f ../eccosp-values/eptb1.yaml
helm template eptb1 ./charts/eccosp-artemis --namespace eccosp -f ../eccosp-values/eptb1.yaml
helm lint ./charts/ecp-endpoint --namespace eccosp -f ../eccosp-values/ep1.yaml
helm template ep1 ./charts/ecp-endpoint --namespace eccosp -f ../eccosp-values/ep1.yaml
```

Check names, selectors, PVCs, Secret references, ports, and SecurityContexts.
Successful rendering is not a cluster, registration, or functional test.
To test only one Endpoint, use only its chart and operator values file;
this does not automatically install the external partners it requires.

For a purely local smoke test, with the canonical instance list supplied before `--set`:

```sh
helm lint ./charts/ecp-endpoint --namespace eccosp -f ./charts/ecp-endpoint/values.yaml --set 'instance[0].existingSecret=ecp-endpoint-ep1-config'
helm template ep1 ./charts/ecp-endpoint --namespace eccosp -f ./charts/ecp-endpoint/values.yaml --set 'instance[0].existingSecret=ecp-endpoint-ep1-config'
```

The explicit `-f` prevents an isolated list-index override from replacing the
default instance with only the Secret name. Corresponding standalone commands
are provided in each chart README. This smoke test checks neither the Secret
nor operational readiness; use the reviewed operator values files for deployments.

### 5. New Installation and Subsequent Acceptance Testing

Install only after the namespace has been provisioned, Secrets populated,
storage prepared, and external configuration approved:

```sh
helm install cd ./charts/ecp-directory --namespace eccosp -f ../eccosp-values/cd.yaml --wait --timeout 15m
helm install br ./charts/ecp-broker --namespace eccosp -f ../eccosp-values/br.yaml --wait --timeout 15m
helm install eptb1 ./charts/eccosp-artemis --namespace eccosp -f ../eccosp-values/eptb1.yaml --wait --timeout 15m
helm install ep1 ./charts/ecp-endpoint --namespace eccosp -f ../eccosp-values/ep1.yaml --wait --timeout 15m
```

These commands apply to single instances and a **new** installation.
Check each step individually; there is no cross-release transaction or shared
rollback. Do not use this as an upgrade or migration procedure.
The commands do not register any components.
Afterwards, perform controlled checks of PVC binding, init containers,
TLS/authentication, the external database, ECP registration, and an end-to-end
message flow. Partner approvals and the Registration Tool procedure take place
outside the chart. A successful Helm `--wait` does not replace this acceptance testing.

## Storage, Security, and Probes

### Persistence and Ownership

EP/CD use data PVCs and persistent logs by default (`keepLogsAfterRestart: true`).
BR/AR have data/keystore and journal storage; logs are ephemeral by default
(`false`). BR also has a PVC for Registration Tool logs. Shared storage is
disabled in all single-instance defaults; classes are empty, and shared-storage
sizes are explicitly 1Gi. Neither NFS nor a particular StorageClass is assumed.

Seed init containers copy existing image files to the data PVCs without
overwriting files. Keystores are retained there; this initialization is neither
ECP registration nor secure automatic certificate rotation. Provision or register
missing or incorrect operational keystores externally.
For BR, the etc working directory is initialized as an `emptyDir`, while keystores
reside in the data area. AR uses the data PVC for etc/keystores.

Application containers run by default as UID/GID 2000 (EP/CD/BR) or 2030 (AR),
without privilege escalation, with `RuntimeDefault` seccomp, and without
capabilities. In contrast, the two seed/ownership init containers run as root
with only `CHOWN`, `FOWNER`, and `DAC_OVERRIDE`; they do not mount any projected
private configuration. Review any additional custom containers separately.

**This does not satisfy Restricted Pod Security Admission.** Do not claim that
a non-root main container makes the entire Pod Restricted-compliant.
With NFS `root_squash`, even these root init containers can fail on `chown`/`chmod`.
Therefore, pre-provision ownership and permissions with the storage operator
and test initialization behavior in a test environment. Pre-provisioning alone
does not disable the root init containers, which still run; a strictly
Restricted/root-squash environment requires a separately approved adaptation
of the deployment/storage design, not a blanket increase in permissions.

### What the Probes Establish

The supplied values contain only `enabled` for each probe:
startup and readiness are enabled; liveness is disabled. Actions, ports, and
timing defaults reside in the respective `*.probes` template helper included by
the StatefulSet. The defaults do not need to be repeated in values.
Existing explicit timing overrides remain optionally supported; the simplified
values do not change the default behavior.

| Probe | Default | Meaning |
| --- | --- | --- |
| Startup | enabled, 10s interval, 2s timeout, 60 failures | EP/CD and single brokers: TCP; HA brokers: only `kill -0 1` |
| Readiness | enabled, 10s interval, 2s timeout, 3 failures | TCP on the web port for EP/CD or the AMQP port for BR/AR |
| Liveness | disabled; when enabled, 10s/2s, 3 failures | TCP, or only the existence of PID 1 for HA brokers |

The initial delay is 0, and the success threshold is 1. A reachable TCP port
proves neither TLS, authentication, database connectivity, registration, nor
application-level health. PID 1 can exist even when the broker is blocked. Do not
claim robust, comprehensive health monitoring. `databaseWait` is not supported;
database initialization and reconnection are the responsibility of the application
and operations team.

## Configure High Availability Explicitly

### EP and CD

`replicaCount > 1` requires `springProfilesActive` containing `ecp-ha`,
`springDatasourceDriverClassName`, and an external JDBC URL in `ecpDBUrl`
under `ecpProperties` or `ecpDirectoryProperties`, respectively. These three
settings are public topology/validation values, not database credentials. Keep
credentials out of the URL. Drivers for PostgreSQL, MariaDB/MySQL, SQL Server,
and Oracle are accepted; the actual image/database combination must be officially supported.

The corresponding external full configuration must contain the same HA profile
and database connection with complete credentials. Do not share an embedded
database across multiple replicas. Session replication additionally requires the
correct Tomcat cluster configuration in the external server XML and a reachable
discovery network. Helm does not render these private settings.

### BR and AR: Shared Store

For a new HA instance, modify the **complete** instance list:

| Value | HA Example / Requirement |
| --- | --- |
| `replicaCount` | `2` |
| `useSharedStorageForJournal` | `true` |
| `useSharedStorageForConfiguration` | `false` |
| `sharedStorageAccessMode` | `ReadWriteMany` |
| `sharedStorageClassJournal` | e.g. `rwx-journal`, only if this suitable class has actually been provisioned |
| `sharedStorageSizeJournal` | `1Gi` as a starting point; size for operational requirements |
| `brokerXml.highAvailability.acceptor.port` | `61616`; must match the external configuration |

`rwx-journal` is an example name, not a supplied class. RWX alone does not
prove suitability for Artemis: check file locking, consistency, latency, failure
behavior, and permissions of the specific backend. Only the journal is shared;
configuration and keystores remain separate for each Pod. Do not convert a single
instance to HA merely by scaling up without external HA files and a storage plan.

Provide both HA keys in the Secret instead of the single-instance key. The external
XML files require a shared-store policy, matching journal/paging/binding/large-message
paths, listeners, credentials, and complete connectors. The public HA script only
replaces `MASTER`, `SLAVE1` through `SLAVE<n>`, and, in the slave document,
`SLAVE-REF` with Pod names, then copies the selected XML to the working directory.
Ordinal 0 receives the master configuration; subsequent ordinals receive the slave
configuration. This does not indicate which broker is currently active after a failover.
Do not expect Helm expressions to be evaluated in external files; namespaces and
DNS suffixes are not inserted automatically. Do not use the reserved replacement
tokens in other XML content.

For release `br`, namespace `eccosp`, and instance `br`, an example HA Pod DNS name is
`br-ecp-broker-br-0.br-ecp-broker-br-headless-svc.eccosp.svc.cluster.local`.
Adjust this externally if the cluster domain differs. The headless Service also
publishes NotReady addresses for discovery; clients use the normal `-svc`.
`service.amqp` is rejected for BR/AR. `service.amqps.port` is the port key;
an optional `brokerXml.acceptor.port` must match it. Neither this value
nor `brokerXml.acceptor.sslEnabled` changes the external broker XML.

HA StatefulSets use `podManagementPolicy: Parallel` and `OnDelete`.
Passive backups may not open an AMQP listener and therefore remain NotReady.
Indiscriminate use of `helm --wait` for HA can wait until the timeout;
`--atomic` may then roll back. For HA, use separate, role-aware acceptance
testing and a controlled maintenance procedure; do not disable readiness
just to force a green rollout.

## Secret Rotation, JMX, and Networking

1. Coordinate preparation of the new external configuration and, if needed,
   keystores/credentials; define a rollback path and backup for the old version.
2. Update the existing Secret through the approved process or reference a new
   Secret. Do not copy contents into Helm values or release artifacts.
3. Increment `secretRevision` for the affected instance as a string, e.g. from `'1'`
   to `'2'`, and update the public release configuration.
4. Restart Pods in a controlled manner and perform application-level acceptance
   testing of the new configuration. EP/CD and single brokers use regular
   StatefulSet RollingUpdates. HA brokers with `OnDelete` require manual Pod
   replacements, one at a time. Identify the active/passive roles first, and check
   backup readiness and failover; never indiscriminately delete all Pods at once.

`checksumConfig: true` covers only the public ConfigMap. The checksum tracks
neither the contents of referenced Secrets nor Secrets from `env`/`extraEnv`
or additional volumes. Secret `subPath` mounts do not automatically update running
containers; for HA, the working XML is prepared only in the init container.
Even a changed checksum or `secretRevision` does not override `OnDelete`.

JMX remains unconfigured by default for EP/CD. If `jmxRemoteProperties` is
non-empty, **both** additional private keys are required, even if individual
JMX switches are false. Keep only public JMX options and
`instance[].jmxRemoteUsers: [{login: monitor, access: readonly}]` for the public
access mapping in values; no `password`. The list belongs directly to the instance,
not under `jmxRemotePassword`. Old nested user lists are no longer evaluated.
The external `jmxremote.password` must match the logins in this access list;
Helm does not check this mapping.
Keep password/SSL contents entirely external.
Deliberately configure authentication, SSL, and registry SSL; test separate
JMX network access and compliance with Java's file-permission requirements.

Ingress is disabled by default. When enabling it, explicitly set the host,
controller, and TLS Secret. With `ingressClassName: nginx` and an HTTPS backend,
the backend protocol annotation is added unless already specified. This does not
replace application TLS/mTLS configuration. Web ingress does not automatically
carry AMQP; plan suitable TCP access for it. For BR/AR, `service.https.host` or
`service.http.host` affects the public Jolokia origin policy; review this policy
rather than relying on the permissive empty default.

All four charts also offer optional Gateway API routing; the default for each
instance is `gateway.enabled: false`. Prerequisites, routing, and TLS examples
are provided in [Gateway_API.md](Gateway_API.md). This does not mean the charts
replace external application configuration or operational TLS acceptance testing.

## Migration from Previous Charts to 5.0.0

### Convert the Previous Umbrella Chart into Independent Releases

The former `ecco-sp` umbrella chart has been removed. Do not pass old nested
component values through unchanged: for each target release, adopt the complete
current standalone defaults and migrate the required settings to their root.
A Helm release cannot be split into multiple releases through a normal upgrade
invocation. Check release ownership, resource and PVC names, and external DNS/TLS
references using the staged procedure. Do not assume automatic adoption of
resources or that the old release can be safely uninstalled.

### Migrate Old Private Values; Do Not Pass Them Through

The following list describes old key groups, not a new values catalog.
Remove private keys that are no longer needed from operator values;
manage their full runtime configuration externally. Even apparently public
individual values within a complete private configuration file are no longer
transferred to the externally mounted file.

| Old Values / Groups | New Destination and Specific Considerations |
| --- | --- |
| EP `ecpProperties`, CD `ecpDirectoryProperties` | Complete corresponding properties file in the Secret; retain only the path/profile/HA/group values listed above in values |
| `ecpKeystorePassword`, `ecpAuthKeystorePassword`, `ecpDBKeystorePassword`, CD `ecpDirectoryRegKeystorePassword`, `ecpDirectoryCAKeystorePassword` and associated locations | Configure external properties and server/broker XML consistently with PVC keystores |
| `ecpDBUsername`, `ecpDBPassword`, datasource/DBCP2 options, validation query | External database configuration; for HA, additionally retain only the credential-free URL and driver for validation |
| `ecpDBHostname`, `ecpDBName`, `databaseWait` and global MySQL/MsSQL/Postgres/Oracle client images | No more database-wait containers; no database readiness guarantee |
| `internalBrokerHost`, `internalBrokerUrls`, ports, authentication, keystore, queue, and connection parameters | Full EP configuration is external; only `internalBrokerAuthUser` remains for public group mapping |
| `ecpCsrfSecret`, Jasypt algorithm, `ecpPasswordProperties.encryptionPassword` | Externally generated/managed values; replace the old fixed CSRF value and known default passwords |
| `ecpUsersProperties.ecpEndpointUsers`, `ecpUsersProperties.ecpDirectoryUsers`, `usersProperties.users[].password` | External user files; if needed, expose only logins for EP group members; the CD role may remain empty in accordance with the official configuration |
| `jmxRemotePassword`, `jmxRemoteSsl`, including user passwords and keystore/truststore passwords | Complete external JMX files; migrate only the login/access mapping to `instance[].jmxRemoteUsers`, and provide a matching external password file |
| LDAP, SOCKS proxy, NAT, AMQP API/SendHandler, FSSF, priorities, broker parameters, parallelism, content storage, synchronization/registration/cleaning jobs, Directory access/TTL, UI theme | External EP/CD properties; old values have no effect on the mounted complete configuration files |
| Actuator/Prometheus/health-threshold properties, `springJmxEnabled`, automatic-update options | External runtime configuration; do not confuse with Kubernetes probes |
| BR `brokerProperties`, including contact details, networks, filters, ECP code, Directory URL/code, and registration ID | Complete external broker properties; registration and updates to its results take place outside Helm |
| BR/AR `artemisUsers[].password`, default user/password | External Artemis user file; `artemisUsers` contains only logins for role mapping |
| AR `artemisKeystoreLocation`, `artemisKeystorePassword` | External bootstrap/broker XML and matching PVC keystores |
| BR/AR `brokerXml.default`, Journal, CriticalAnalyzer, AddressSettings, acceptor TLS/properties, audit/ECP identifier, `maskPassword`, codec/key, cluster user/password | External single-instance or master/slave XML; retain only required port/topology checks in values |
| BR/AR `prometheusEnabled` and web bootstrap options | External broker/bootstrap XML; the value does not toggle anything in the external document |
| Old EP bootstrap custom mount targeting an unrelated Artemis path | Remove; not part of the base Endpoint configuration |

Old defaults may remain in previous Helm release Secrets, ConfigMaps, backups,
or Git history. Migration does not automatically delete this history.
Coordinate access, retention, and any necessary rotation of compromised/known
values with security operations, without indiscriminately destroying backups
needed for rollback. Do not use `--reuse-values` for this migration.

### Staged Procedure with PVC Preservation

1. **Take inventory:** securely record the old release name, namespace, chart/image
   versions, complete values, live manifests, selectors, StatefulSet ServiceName,
   ClaimTemplate names, PVC/PV bindings, StorageClass/ReclaimPolicy, and
   registration identities. Do not put private exports in the repository.
2. **Create consistent backups:** back up databases, data PVCs, the journal, keystores,
   registration data, and required logs. Establish snapshot/backup consistency
   while writers are active; test restoration on separate volumes.
3. **Render and compare the target:** names are derived from the release, chart,
   and instance. Base names longer than 45 characters are truncated and given a hash.
   `fullnameOverride` accepts a maximum of 45 characters but does **not** guarantee
   a compatible upgrade. Selectors now also include `app.kubernetes.io/instance`;
   the headless Service and StatefulSet `serviceName`, as well as ClaimTemplate/PVC
   names, may have changed. Some of these fields are immutable.
4. **Plan PVC mappings:** an example claim name is
   `data-ep1-ecp-endpoint-ep1-0`; an example shared-journal claim is
   `br-ecp-broker-br-journal-claim`. Old PVCs are not discovered automatically
   based on their contents. Do not simply let new names point to empty volumes.
   Plan a controlled restore or explicit PV/PVC reassignment with the storage
   operator; handle data PVCs and shared PVCs separately.
5. **Test in isolation:** start new resources on isolated test/restore volumes
   with external Secrets. Do not create parallel production writers against the
   same journal/database state or duplicate active ECP identities. Test registration,
   TLS, the database, users, restarts, message flow, and, for HA, failover/failback.
   Apply name/topology changes to external configurations as well.
6. **Controlled cutover:** define the maintenance window, message/write suspension,
   final consistent backup, and acceptance criteria. If a StatefulSet must be
   recreated, ensure PVC/PV preservation beforehand. Do not indiscriminately use
   `helm uninstall`, `--force`, or deletion of all PVCs as a supposed fix.
   Switch traffic only after restoration and verification.
7. **Preserve a rollback path:** retain old resources/backups until acceptance.
   If errors occur, stop writes and perform the agreed restore/routing rollback.
   A `helm rollback` does not automatically undo database/journal/keystore changes.
   Clean up only after successful acceptance testing.

Switching from single-instance operation to HA can also affect immutable
StatefulSet fields and PVC layouts. Plan this switch as a topology migration,
not merely a change to `replicaCount`.

## CI and Limits of Validation

The [../.github/workflows/lint.yml](../.github/workflows/lint.yml) workflow checks
all four standalone charts: fixture/assertion tests, linting, rendering, manifest
validation, and source and package tests. The independent
[Kubernetes validation workflow](../.github/workflows/kubernetes.yml) packages
the charts with synthetic fixtures and checks them against every Kubernetes minor
from 1.34 through the latest with a pre-built image in official stable kind releases.
Images are selected
from their published SHA-256 digests; missing minor versions fail CI
instead of silently reducing coverage. Each cluster performs server-side dry-runs
for the default, Ingress, and Gateway HTTP/HTTPS fixtures. It installs only the
verified Gateway API v1.4.1 CRDs, not a Gateway controller or application Pods.
Uploads contain synthetic test artifacts and validated packages, not real
Secrets. Do not introduce production configurations into fixtures, rendered
output, or CI uploads.

For rendered `HTTPRoute` and `BackendTLSPolicy` resources, the required
Gateway API CRD sources for the pinned version **v1.4.1** are downloaded over
verified HTTPS and checked against hard-coded SHA-256 checksums before parsing.
Strict schemas generated from these sources are used for the cluster-free
manifest checks; those checks do not execute Kubernetes CEL rules. The separate
Kubernetes workflow runs API server validation with the CRDs installed, but does
not test controller behavior, external Secrets, storage, or application readiness.

The [../.github/workflows/Release Charts.yml](../.github/workflows/Release%20Charts.yml)
workflow publishes the four validated packages only after the independent lint,
Kubernetes, and release-rule checks succeed.
Chart versions are independently determined from conventional commits that change
their respective `charts/<name>/` directory. `feat:` increments the minor version,
`fix:` and `perf:` increment the patch version, and a `!` or `BREAKING CHANGE:`
footer increments the major version. Other commits do not trigger a chart release.
For example, `fix(ecp-endpoint): correct service selector` releases only the
Endpoint chart when its files change. A single commit changing multiple charts
may release each changed chart independently. Use a new `feat:`/`fix:` commit for
a correction to an already published chart version: released tags and packages
are immutable.

On main, semantic-release validates the versioned package, commits the updated
`Chart.yaml`, creates the chart-specific tag `<chart>-<version>` and publishes
the tested `.tgz` as a GitHub Release asset. Chart-releaser then updates the
Helm index from these releases, after the same validated packages have been
copied to `gh-pages`; Pages deploys the refreshed index and portal.
This requires permission for GitHub Actions to write repository contents and
for the release bot to push the version commits to main (including any branch
protection rules). Do not create or retag chart releases by hand alongside this
workflow. `appVersion` and application image tags remain independent.
CI does not prove image availability, admission policies in the target cluster,
storage suitability, registration, TLS/database functionality, or HA resilience.
These checks remain the responsibility of subsequent testing and operational acceptance.
