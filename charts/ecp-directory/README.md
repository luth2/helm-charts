# ECP Component Directory - Helm Chart 5.0.0

Standalone-Chart fuer ECP Directory 4.17.0, Helm 3 und Kubernetes >= 1.28.
Oeffentliche Defaults: [values.yaml](values.yaml).

## Pflicht: externes Secret

Jede aktivierte Instanz benoetigt `existingSecret` im Release-Namespace.
`existingSecret: ''` laesst einen unveraenderten Standalone-Lint/Render absichtlich
fehlschlagen. Helm erzeugt keine Secrets und prueft keine externen Secret-Inhalte.

| Secret-Key | Mountziel |
| --- | --- |
| `ecp-directory.properties` | /etc/ecp-directory/ecp-directory.properties |
| `ecp-users.properties` | /etc/ecp-directory/ecp-users.properties |
| `ecp-password.properties` | /etc/ecp-directory/ecp-password.properties |
| `server.xml` | /usr/share/ecp-directory/conf/server.xml |
| `jmxremote.password`, `jmxremote.ssl` | Zusaetzlich bei gesetztem, nichtleerem `jmxRemoteProperties`; standardmaessig /etc/ecp-directory/ |

Vollstaendige Dateien ausserhalb des Repositorys nach offizieller ECP-Konfiguration
pflegen und vor Installation bereitstellen. Ports, DB, TLS, Benutzer, CA-,
Registrierungs- und Authentifizierungs-Keystores muessen zur Umgebung passen.
Keine privaten Vollfiles oder Secret-Manifeste in diesem Repository erzeugen.

## Oeffentliche Values und ihre Grenzen

`envConf` steuert JVM-Startkonfiguration, Kubernetes-Values steuern Ressourcen,
Services, Storage und Probes. `dataDirectory` und `loggingFilePath` unter
`ecpDirectoryProperties` werden als PVC-Mountpfade verwendet. `springProfilesActive`
dient der HA-Validierung. Laufzeitprofile inklusive `console-logging`,
`loggingFileName` und `loggingConfig` muessen in der externen Vollkonfiguration
passend gesetzt sein. Helm liefert die oeffentliche Logback-Konfiguration, ersetzt
aber keine Properties-Datei des Secrets.

`sessionReplication: true` liefert den oeffentlichen Kontext und
`DNS_MEMBERSHIP_SERVICE_NAME`. Die benoetigte Tomcat-Cluster-Konfiguration muss
auch im externen `server.xml` stehen. Der Chart aktiviert sie dort nicht.
Benutzer inklusive Rollen werden ausschliesslich extern verwaltet; eine leere
Directory-Rollenzuordnung kann entsprechend der offiziellen Konfiguration
beibehalten werden, Helm ergaenzt keine Rolle.

`instance[].jmxRemoteUsers: [{login: monitor, access: readonly}]` steuert nur das
oeffentliche JMX-Access-Mapping. Die Liste steht direkt an der Instanz, nicht
unter `jmxRemotePassword`; alte verschachtelte Benutzerlisten entfallen.
Die externe `jmxremote.password` muss zu diesen Logins passen; kein Passwort in
Values. Bei nichtleerem `jmxRemoteProperties` sind Passwort- und SSL-Datei
erforderlich, auch bei einzelnen Schaltern auf false. Helm prueft deren Inhalt
und die Uebereinstimmung mit der Access-Liste nicht.

Alte private `ecpDirectoryProperties`, `ecpUsersProperties` und
`ecpPasswordProperties` aendern keine externe Datei. Das interne benannte
`configuration`-Template rendert ausschliesslich oeffentliche Konfiguration.
Private Vollfiles werden auch intern gar nicht gerendert; private Legacy-
Datensektionen und Dummy-Werte sind entfernt. Die `omit`-Listen in `publicConfig`
und der ConfigMap-Ausgabe bleiben defensiver Schutz fuer reservierte private
Datei-Keys, keine Validierung externer Secret-Inhalte.

## Ingress und Gateway API

Ingress bleibt verfuegbar; alternativ erzeugt `instance[].gateway.enabled: true`
eine HTTPRoute fuer den Web-Service. Bei HTTPS wird zusaetzlich eine
BackendTLSPolicy v1 mit explizitem Backend-Zertifikatsnamen und CA-Vertrauen erzeugt.
Gateway/Controller/CRDs muessen bereits existieren. AMQP(S) wird nicht geroutet.
Beide Zugangswege sind standardmaessig aus und fuer Migration parallel nutzbar.
[Gateway-Konfiguration und TLS-Voraussetzungen](../../Dokumentation/Gateway_API.md).

## Defaults und Pruefung

Eine Replik, HTTPS 8443, UID/GID/fsGroup 2000, Daten-PVC 1Gi, Logs-PVC 256Mi.
Startup und Readiness sind aktiv, Liveness ist aus. Intervall 10s, Timeout 2s,
Startup-Schwelle 60. TCP prueft weder Datenbank noch TLS oder fachliche Gesundheit.
JMX bleibt standardmaessig aus.

Aus dem Repository-Root, ohne Clusterzugriff:

```sh
helm lint ./charts/ecp-directory --namespace eccosp -f ./charts/ecp-directory/values.yaml --set 'instance[0].existingSecret=ecp-directory-cd-config'
helm template platform ./charts/ecp-directory --namespace eccosp -f ./charts/ecp-directory/values.yaml --set 'instance[0].existingSecret=ecp-directory-cd-config'
```

`-f` ist hier wichtig: Listen werden ersetzt, nicht mit Chart-Defaults
elementweise gemischt. Der anschliessende `--set` veraendert die bereits vollstaendige
Instanz. Service: `platform-ecp-directory-cd-svc`.

## Betrieb, HA und Migration

Fuer mehrere Replikate sind `ecp-ha`, `springDatasourceDriverClassName` und eine
externe `ecpDBUrl` in `ecpDirectoryProperties` zur Validierung erforderlich.
Dies konfiguriert weder die externe Datenbank noch den Inhalt des Secrets.
Es gibt keine DB-Wartecontainer und keine Registrierungs-Hooks.
Keystores werden aus dem Image auf das PVC initialisiert; Registrierung und
Zertifikatsversorgung bleiben extern.

Secret-Inhalt geaendert -> `secretRevision` erhoehen und Neustart einplanen.
ConfigMap-Checksummen decken keine externen Secret-Inhalte ab.
Die Root-Initcontainer fuer Seed/Ownership sind nicht Restricted-PSA-kompatibel;
bei `root_squash` ist eine abgestimmte Storage-/Ownership-Loesung erforderlich.

5.0.0 nicht blind ueber alte Releases installieren: unveraenderliche Selector-
und StatefulSet-Felder sowie PVC-Namen vergleichen. `fullnameOverride` allein
reicht nicht. Backup/Restore und gestufte Migration stehen in
[../../Dokumentation/Helm_Charts.md](../../Dokumentation/Helm_Charts.md).
