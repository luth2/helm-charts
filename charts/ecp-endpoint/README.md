# ECP Endpoint - Helm Chart 5.0.0

Standalone-Chart fuer ECP Endpoint 4.17.0, Helm 3 und Kubernetes >= 1.28.
Die kanonische oeffentliche Konfiguration steht in [values.yaml](values.yaml).
Der Umbrella verwendet denselben Chart, keine separat gepflegte Kopie.

## Pflicht: externes Secret

Jede aktivierte `instance` benoetigt `existingSecret` im Release-Namespace.
Der leere Default ist Absicht: Ein unveraenderter Standalone-Lint/Render scheitert.
Der Chart erzeugt kein Secret und keine privaten Vollkonfigurationen fuer den Betrieb.

| Secret-Key | Mountziel |
| --- | --- |
| `ecp.properties` | /etc/ecp-endpoint/ecp.properties |
| `ecp-users.properties` | /etc/ecp-endpoint/ecp-users.properties |
| `ecp-password.properties` | /etc/ecp-endpoint/ecp-password.properties |
| `server.xml` | /usr/share/ecp-endpoint/conf/server.xml |
| `users.properties` | /etc/ecp-endpoint/users.properties |
| `jmxremote.password`, `jmxremote.ssl` | Zusaetzlich bei gesetztem, nichtleerem `jmxRemoteProperties`; standardmaessig /etc/ecp-endpoint/ |

Alle Keys enthalten vollstaendige, extern gepflegte Dateien nach der offiziellen
ECP-Konfiguration. Ports, Datenbank, TLS, Benutzer, Keystores und die Verbindung zum
internen Broker muessen dort stimmen. Ein vorhandener Secret-Name allein reicht
nicht fuer einen funktionsfaehigen Start. Helm prueft weder Existenz noch Inhalt.
Keine Secret-Dateien oder privaten Konfigurationsbeispiele in diesem Repository ablegen.

## Was Values tatsaechlich steuern

- Kubernetes: Image, Replikate, Ressourcen, Storage, Services, Ingress und Probes.
- `envConf.resourcesJvm` und `envConf.ecpLogFullStackTrace`: oeffentliche JVM-Startkonfiguration.
- `ecpProperties.dataDirectory` und `loggingFilePath`: PVC-Mountpfade.
- `springProfilesActive`: HA-Validierung; das tatsaechliche Laufzeitprofil kommt
  aus dem Secret. `console-logging` dort ebenfalls setzen.
- `loggingFileName` und `loggingConfig`: dokumentierter Pfadabgleich, kein Update
  der externen Datei. Der Chart liefert die oeffentliche Logback-Konfiguration.
- `internalBrokerAuthUser`: oeffentliches Gruppenmapping fuer `admins`,
  `tempDestinationAdmins` und `users`. Die zugehoerigen Benutzer und Zugangsdaten
  muessen in den externen Vollkonfigurationen vorhanden sein.
- Optionale `usersProperties.users` nur mit `login` pflegen, wenn weitere
  oeffentliche Gruppenmitglieder benoetigt werden; niemals mit Passwort.
- `sessionReplication`: oeffentlicher Tomcat-Kontext und Discovery-Umgebung;
  die passende Cluster-Konfiguration im externen `server.xml` bleibt Betreiberaufgabe.
- `instance[].jmxRemoteUsers: [{login: monitor, access: readonly}]`: oeffentliches
  JMX-Access-Mapping direkt an der Instanz, nicht unter `jmxRemotePassword`.
  Alte verschachtelte Benutzerlisten werden nicht ausgewertet. Die externe
  `jmxremote.password` muss zu diesen Logins passen; kein Passwort in Values.
  Bei nichtleerem `jmxRemoteProperties` sind Passwort- und SSL-Datei erforderlich,
  auch bei einzelnen Schaltern auf false. Helm validiert keine Secret-Inhalte.

Andere alte `ecpProperties`, `ecpUsersProperties` und `ecpPasswordProperties`
aendern die eingebundenen privaten Dateien nicht. Das benannte interne
`configuration`-Template rendert nur oeffentliche Konfiguration; private Vollfiles
werden auch intern gar nicht gerendert. Private Legacy-Datensektionen und
Dummy-Werte sind entfernt. Die `omit`-Listen in `publicConfig` und der
ConfigMap-Ausgabe bleiben defensiver Schutz fuer reservierte private Datei-Keys,
keine Validierung externer Secret-Inhalte.
Ein zusaetzlicher Artemis-Bootstrap-Mount gehoert nicht zur Endpoint-Grundkonfiguration.

## Ingress und Gateway API

Ingress bleibt verfuegbar; alternativ erzeugt `instance[].gateway.enabled: true`
eine HTTPRoute fuer den Web-Service. Bei HTTPS wird zusaetzlich eine
BackendTLSPolicy v1 mit explizitem Backend-Zertifikatsnamen und CA-Vertrauen erzeugt.
Gateway/Controller/CRDs muessen bereits existieren. AMQP(S) wird nicht geroutet.
Beide Zugangswege sind standardmaessig aus und fuer Migration parallel nutzbar.
[Gateway-Konfiguration und TLS-Voraussetzungen](../../Dokumentation/Gateway_API.md).

## Defaults und Pruefung

Eine Replik, HTTPS 8443, UID/GID/fsGroup 2000, Daten-PVC 1Gi, Logs-PVC 256Mi.
JMX ist nicht aktiviert, auch nicht im EP2-Beispiel. Startup und Readiness sind
aktiv, Liveness ist aus; Intervall 10s, Timeout 2s, Startup-Schwelle 60.
TCP-Probes pruefen nur Transport-Erreichbarkeit, weder TLS-Handshake noch DB oder ECP-Gesundheit.

Aus dem Repository-Root, ohne Clusterzugriff:

```sh
helm lint ./charts/ecp-endpoint --namespace eccosp -f ./charts/ecp-endpoint/values.yaml --set 'instance[0].existingSecret=ecp-endpoint-ep1-config'
helm template platform ./charts/ecp-endpoint --namespace eccosp -f ./charts/ecp-endpoint/values.yaml --set 'instance[0].existingSecret=ecp-endpoint-ep1-config'
```

Das explizite `-f` erhaelt die vollstaendige Instanz beim anschliessenden `--set`.
Nicht allein per Listenindex einen Secret-Namen setzen: Helm fuegt Chart-Default-
und Override-Listen nicht elementweise zusammen. Fuer eigene Listen alle Felder uebernehmen.
Der Service dieses Beispiels heisst `platform-ecp-endpoint-ep1-svc`.

## Betrieb, HA und Migration

Mehr als eine Replik verlangt `ecp-ha`, einen unterstuetzten externen JDBC-Treiber
und `ecpDBUrl` in `ecpProperties` fuer die Helper-Validierung. Die gleiche DB-
Konfiguration einschliesslich Zugangsdaten muss extern gesetzt sein; es gibt
keinen DB-Wartecontainer. Ein zweiter eigenstaendiger Endpoint ist keine HA-Replik.

Secret-Aenderung -> `secretRevision` erhoehen und Pod-Neustart einplanen.
Oeffentliche ConfigMap-Checksummen verfolgen keine externen Secret-Inhalte.
Root-Initcontainer fuer Seed/Ownership sind trotz begrenzter Capabilities nicht
mit Restricted PSA kompatibel; NFS `root_squash` vorab pruefen.
Keystores bleiben auf dem aus dem Image initialisierten PVC; Registrierung ist
extern und wird nicht durch Helm-Hooks ausgefuehrt.

Vor 5.0.0 kein blindes Upgrade: Selector-, Headless-Service- und PVC-Namen koennen
sich aendern. Auch `fullnameOverride` garantiert keine Upgrade-Kompatibilitaet.
Vorgehen, Backup/Restore, Secret-Rotation und vollstaendige Key-Migration:
[../../Dokumentation/Helm_Charts.md](../../Dokumentation/Helm_Charts.md).
