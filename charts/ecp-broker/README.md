# ECP Broker - Helm Chart 5.0.0

Standalone-Chart fuer ECP Broker 4.17.0, Helm 3 und Kubernetes >= 1.28.
Oeffentliche Defaults: [values.yaml](values.yaml).

## Pflicht: externe Vollkonfiguration

Jede aktivierte Instanz benoetigt `existingSecret` im Release-Namespace.
Der leere Default laesst Standalone-Lint/Render absichtlich scheitern.
Der Chart erzeugt kein Secret; ein erfolgreicher Render prueft dessen Inhalt nicht.

| Secret-Key | Verwendung |
| --- | --- |
| `broker.properties` | /opt/ecp-broker/config/broker.properties |
| `artemis-users.properties` | /opt/ecp-broker/broker/etc/artemis-users.properties |
| `bootstrap.xml` | Bei HTTP/HTTPS-Service: /opt/ecp-broker/broker/etc/bootstrap.xml |
| `broker.xml` | Single: /opt/ecp-broker/broker/etc/broker.xml |
| `broker-master.xml`, `broker-slave.xml` | HA statt `broker.xml`: Eingaben fuer den nichtprivilegierten HA-Initcontainer |

Die Default-Values haben HTTPS aktiviert; daher ist `bootstrap.xml` hier Pflicht.
Dateien vollstaendig nach offizieller ECP-Konfiguration ausserhalb des Repositorys
erstellen. AMQPS-Port 5671, Web-Port 8161, TLS/Client-Authentifizierung, Benutzer,
Keystore-Pfade, ECP-Code und Directory-/Registrierungsdaten extern abstimmen.
`artemisUsers` enthaelt nur Logins fuer das oeffentliche `amq`-Rollenmapping,
keine Passwoerter und keine automatische Kontoanlage.

Alte `brokerProperties`, private `brokerXml`-Felder, Passwort- und
`prometheusEnabled`-Values aendern die externen Vollfiles nicht. Insbesondere
aktiviert ein Value keine TLS- oder Metrik-Konfiguration im externen XML.
Das benannte `configuration`-Template rendert nur oeffentliche Konfiguration.
Private Vollfiles werden auch intern gar nicht gerendert; private Legacy-
Datensektionen und Dummy-Werte sind entfernt. Die `omit`-Listen in `publicConfig`
und der ConfigMap-Ausgabe bleiben defensiver Schutz fuer reservierte private
Datei-Keys, keine Validierung externer Secret-Inhalte.

## Oeffentliche Defaults

- Eine Replik, ClusterIP, UID/GID/fsGroup 2000; Image-Tag `'4.17.0'`.
- `env.resourcesJvm`: JVM-Heap in der oeffentlichen Artemis-Startkonfiguration.
- Daten- und Journal-PVC je 1Gi; separate Registration-Tool-Logs 64Mi.
  Dieser Logs-PVC bedeutet nicht, dass der Chart eine Registrierung ausfuehrt.
- `keepLogsAfterRestart: false`: Broker-Logs auf `emptyDir`; bei `true` eigener PVC.
- Shared Journal und Shared Configuration sind aus, beide Klassen leer.
  Keine NFS-Annahme. HA-Groessen stehen explizit auf 1Gi.
- `brokerXml.highAvailability.acceptor.port` steuert den HA-Port von Pod und
  Headless-Service; der Wert muss auch im externen XML stimmen.
- Startup/Readiness aktiv, Liveness aus; jeweils 10s/2s, Startup-Schwelle 60.

Single-Probes und HA-Readiness pruefen nur TCP, nicht TLS, Authentifizierung oder
Nachrichtentransport. HA-Startup/Liveness pruefen nur PID 1. Das ist keine robuste
fachliche Gesundheitspruefung; passive Backups koennen absichtlich NotReady sein.

## Standalone pruefen

Aus dem Repository-Root, ohne Clusterzugriff:

```sh
helm lint ./charts/ecp-broker --namespace eccosp -f ./charts/ecp-broker/values.yaml --set 'instance[0].existingSecret=ecp-broker-br-config'
helm template platform ./charts/ecp-broker --namespace eccosp -f ./charts/ecp-broker/values.yaml --set 'instance[0].existingSecret=ecp-broker-br-config'
```

`-f` laedt die vollstaendige Liste vor `--set`; ein isolierter Listenindex-Override
ersetzt sonst die Chart-Default-Liste. Service: `platform-ecp-broker-br-svc`.
`service.amqp` wird abgelehnt; `service.amqps.port` ist der unterstuetzte Port-Key.
Der Key allein aktiviert keine Verschluesselung im externen Broker-XML.

## HA, Rotation und Migration

Mehrere Replikate erfordern Shared Journal, eine explizite geeignete RWX-Klasse,
`ReadWriteMany` und `useSharedStorageForConfiguration: false`.
Keystores bleiben pro Pod auf PVCs; der etc-Arbeitsbereich ist ein `emptyDir`.
Externes Master-/Slave-XML muss Headless-DNS, Ports, Shared-Store-Pfade und die
Platzhalter fuer die HA-Initialisierung korrekt enthalten. Details siehe zentrale Anleitung.

HA verwendet `Parallel` und `OnDelete`. Secret-Aenderung -> `secretRevision`
erhoehen, anschliessend kontrollierte manuelle Pod-Neustarts. Auch oeffentliche
Checksummen loesen bei `OnDelete` keinen automatischen Austausch laufender Pods aus.
Helm prueft externe Secret-Inhalte nicht und registriert keine ECP-Komponenten.

Root-Initcontainer fuer Seed/Ownership sind trotz Least-Capabilities nicht mit
Restricted PSA kompatibel. `root_squash`, Ownership und Journal-Locking vorab
mit dem Storage-Betreiber klaeren. Vor 5.0.0 kein blindes Upgrade und kein
Vertrauen auf `fullnameOverride` allein: Selector-/Headless-/PVC-Aenderungen
verlangen Backup/Restore und gestufte Migration.

[../../Dokumentation/Helm_Charts.md](../../Dokumentation/Helm_Charts.md)
