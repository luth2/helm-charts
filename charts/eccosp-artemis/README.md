# ECCoSP Artemis - Helm Chart 5.0.0

Standalone-Chart fuer den internen Broker 4.17.0, Helm 3 und Kubernetes >= 1.28.
Oeffentliche Defaults: [values.yaml](values.yaml).

## Pflicht: externe Vollkonfiguration

Jede aktivierte Instanz benoetigt `existingSecret` im Release-Namespace.
Der leere Default ist Absicht: Unveraenderter Standalone-Lint/Render scheitert.
Der Chart erzeugt keine Secrets und prueft weder deren Existenz noch Inhalte.

| Secret-Key | Verwendung |
| --- | --- |
| `artemis-users.properties` | /opt/eccosp-artemis/etc/artemis-users.properties |
| `bootstrap.xml` | Bei HTTP/HTTPS-Service: /opt/eccosp-artemis/etc/bootstrap.xml |
| `broker.xml` | Single: /opt/eccosp-artemis/etc/broker.xml |
| `broker-master.xml`, `broker-slave.xml` | HA statt `broker.xml`: Eingaben fuer den nichtprivilegierten HA-Initcontainer |

Da die Defaults HTTPS enthalten, ist `bootstrap.xml` erforderlich. Alle Dateien
extern vollstaendig nach offizieller Konfiguration erstellen. AMQPS-Port 5672,
Web-Port 8161, TLS, Benutzer, Keystores und Audit-/ECP-Kennung korrekt setzen.
Keine Secret-Manifeste oder privaten Vollfile-Beispiele im Repository ablegen.

`artemisUsers` enthaelt nur `login` fuer das oeffentliche `amq`-Rollenmapping;
die Konten `endpoint` und `toolbox` werden dadurch nicht angelegt. Die externen
Benutzerdateien und die Client-Konfigurationen muessen dazu passen.
Private `brokerXml`-Values, `artemisKeystoreLocation`, `artemisKeystorePassword`
oder `prometheusEnabled` aendern keine externen Dateien. Das benannte
`configuration`-Template rendert nur oeffentliche Konfiguration. Private Vollfiles
werden auch intern gar nicht gerendert; private Legacy-Datensektionen und
Dummy-Werte sind entfernt. Die `omit`-Listen in `publicConfig` und der
ConfigMap-Ausgabe bleiben defensiver Schutz fuer reservierte private Datei-Keys,
keine Validierung externer Secret-Inhalte.

## Oeffentliche Defaults

- Eine Replik, ClusterIP, UID/GID/fsGroup 2030; Image-Tag `'4.17.0'`.
- `env.resourcesJvm`: Heap in der oeffentlichen Artemis-Startkonfiguration.
- Daten-/Keystore-PVC und Journal-PVC je 1Gi. Logs standardmaessig `emptyDir`,
  mit `keepLogsAfterRestart: true` eigener Logs-PVC.
- Shared Configuration und Shared Journal aus; beide Klassen leer, keine
  NFS-Annahme. Shared-Groessen fuer explizite Aktivierung je 1Gi.
- `brokerXml.highAvailability.acceptor.port`: HA-Port von Pod/Headless-Service,
  keine Aenderung der externen XML-Konfiguration.
- Startup/Readiness aktiv, Liveness aus; 10s Intervall, 2s Timeout,
  Startup-Schwelle 60. JMX wird hierdurch nicht aktiviert.

Single-Probes und HA-Readiness pruefen nur TCP-Erreichbarkeit. HA-Startup/Liveness
pruefen nur PID 1, damit passive Backups nicht wegen fehlendem AMQP-Listener
neu gestartet werden. Weder Variante prueft umfassende Broker-Gesundheit,
TLS oder erfolgreiche Nachrichtenverarbeitung.

## Ingress und Gateway API

Ingress bleibt verfuegbar; alternativ erzeugt `instance[].gateway.enabled: true`
eine HTTPRoute fuer den Web-Service. Bei HTTPS wird zusaetzlich eine
BackendTLSPolicy v1 mit explizitem Backend-Zertifikatsnamen und CA-Vertrauen erzeugt.
Gateway/Controller/CRDs muessen bereits existieren. AMQP(S) wird nicht geroutet.
Beide Zugangswege sind standardmaessig aus und fuer Migration parallel nutzbar.
[Gateway-Konfiguration und TLS-Voraussetzungen](../../Dokumentation/Gateway_API.md).

## Standalone pruefen

Aus dem Repository-Root, ohne Clusterzugriff:

```sh
helm lint ./charts/eccosp-artemis --namespace eccosp -f ./charts/eccosp-artemis/values.yaml --set 'instance[0].existingSecret=eccosp-artemis-eptb1-config'
helm template platform ./charts/eccosp-artemis --namespace eccosp -f ./charts/eccosp-artemis/values.yaml --set 'instance[0].existingSecret=eccosp-artemis-eptb1-config'
```

Die komplette Liste wird mit `-f` geladen, erst danach per `--set` angepasst.
Helm mischt Listen nicht elementweise mit Chart-Defaults.
Service: `platform-eccosp-artemis-artemis-eptb1-svc`.
`service.amqp` wird abgelehnt; `service.amqps.port` bleibt der Port-Key auch dann,
wenn extern eine andere Transportkonfiguration gewaehlt wird. TLS extern setzen.

## HA, Rotation und Migration

Mehrere Replikate verlangen Shared Journal auf einer expliziten geeigneten
RWX-Klasse, `ReadWriteMany` und keine gemeinsame Konfigurationsablage.
Keystores und das erzeugte HA-Arbeits-XML liegen auf dem jeweiligen Daten-PVC.
Die externen HA-Eingabedateien muessen vollstaendig vorbereitet sein; Helm
erfindet weder Cluster-Zugangsdaten noch eine passende Topologie.

HA verwendet `Parallel`/`OnDelete`: Nach Secret-Aenderungen `secretRevision`
erhoehen und Pods manuell kontrolliert neu starten. Oeffentliche Checksummen
verfolgen keine externen Secret-Inhalte und umgehen `OnDelete` nicht.
Registrierung und Zertifikatsversorgung sind extern, nicht als Hooks gebuendelt.

Root-Initcontainer fuer Seed/Ownership bleiben inkompatibel mit Restricted PSA;
`root_squash` und Ownership erfordern eine abgestimmte Storage-Loesung.
Vor 5.0.0 Selector-, Headless-Service- und PVC-Aenderungen mit Backup/Restore
migrieren. `fullnameOverride` ist keine Garantie fuer ein In-place-Upgrade.

[../../Dokumentation/Helm_Charts.md](../../Dokumentation/Helm_Charts.md)
