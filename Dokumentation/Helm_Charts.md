# ECCoSP Helm Charts 5.0.0

## Empfehlung und Geltungsbereich

Neue Installationen mit expliziten Instanz-Values und bereits bereitgestellten
externen Secrets aufbauen. Bestehende Installationen zuerst sichern und gestuft
migrieren, nicht blind mit `helm upgrade` aktualisieren.

Alle vier Standalone-Charts haben unveraendert Version **5.0.0**, `appVersion` **4.17.0** und setzen
Kubernetes >= 1.28 sowie Helm 3 voraus. Die CI verwendet Helm 3.19.0.
Chart-Version und Image-Version sind unterschiedliche Versionsachsen.
Die Default-Image-Tags sind Strings, nicht `latest`; BusyBox ist auf 1.37.0 gesetzt.
Die Images und ihre Laufzeitkompatibilitaet muessen fuer die Zielumgebung
verfuegbar und freigegeben sein. Alternativ ist `image.digest` mit SHA-256
moeglich; bei gesetztem Digest hat dieser Vorrang vor dem Tag.
`image.name` enthaelt das vollstaendige Repository; `image.registry` ist ungueltig.

### Versionierung und Namen

- `Chart.yaml: version` versioniert das Helm-Chart: Paket `ecp-broker-5.0.0.tgz`
   und GitHub-Release/Tag `ecp-broker-5.0.0`. Bei Chart-Aenderungen diese Version
   fuer eine neue Veroeffentlichung erhoehen.
- `Chart.yaml: appVersion` beschreibt die Anwendung. Es darf unabhaengig von der
   Chart-Version wechseln und bestimmt weder Paketnamen noch Dependency-Versionen.
- `instance[].image.tag` bzw. `image.digest` bestimmt das tatsaechliche Containerimage;
   `appVersion` setzt den Tag nicht automatisch.
- Kubernetes-Ressourcennamen bleiben `<release>-<chart>-<instance>` (gegebenenfalls
   gekuerzt/gehasht), ohne Chart- oder App-Version. Eine Version im StatefulSet-Namen
   wuerde bei Upgrades neue Ressourcennamen und andere PVC-Zuordnungen erzeugen.
- Bereits veroeffentlichte Chart-Versionen werden nicht ueberschrieben
   (`skip-existing`). Fuer eine geaenderte Veroeffentlichung eine neue Chart-Version nutzen.

| Chart | Aufgabe | Kanonische Defaults |
| --- | --- | --- |
| [../charts/ecp-endpoint/README.md](../charts/ecp-endpoint/README.md) | Endpoint | [../charts/ecp-endpoint/values.yaml](../charts/ecp-endpoint/values.yaml) |
| [../charts/ecp-directory/README.md](../charts/ecp-directory/README.md) | Component Directory | [../charts/ecp-directory/values.yaml](../charts/ecp-directory/values.yaml) |
| [../charts/ecp-broker/README.md](../charts/ecp-broker/README.md) | ECP Broker | [../charts/ecp-broker/values.yaml](../charts/ecp-broker/values.yaml) |
| [../charts/eccosp-artemis/README.md](../charts/eccosp-artemis/README.md) | Interner Artemis-Broker | [../charts/eccosp-artemis/values.yaml](../charts/eccosp-artemis/values.yaml) |

Die Chart-Quellen liegen ausschliesslich unter `charts/`. Jede Komponente wird
direkt aus ihrem Chart-Verzeichnis als unabhaengiger Helm-Release installiert,
aktualisiert und zurueckgerollt. Es gibt keinen gemeinsamen Plattform-Release
und keinen Dependency-Build fuer diese Charts. Partnerdienste und ihre
Verbindungen muessen separat bereitgestellt und konfiguriert werden.
Die Charts installieren weder Datenbanken noch EDX Toolbox oder Service Catalogue.

## Konfigurationsvertrag: oeffentlich und privat strikt trennen

Jede aktivierte Instanz braucht `instance[].existingSecret` im Release-Namespace.
Die Standalone-Defaults lassen diesen String absichtlich leer: Lint und Rendern
ohne Betreiberkonfiguration sollen scheitern. Die jeweilige Default-Instanz ist
aktiviert; ein leeres Secret-Feld ist keine einsatzbereite Konfiguration.

Helm erzeugt **kein Secret**. Es projiziert eine oeffentliche ConfigMap zusammen
mit ausgewaehlten Keys eines vorhandenen Secrets und bindet die Dateien ein.
Es prueft weder die Existenz des Secrets noch die fachliche Gueltigkeit seines
Inhalts. Fehlende Keys verhindern den Pod-Start; unpassende Inhalte koennen trotz
erfolgreichem Helm-Rendering zu Anwendungsfehlern fuehren.

### Erforderliche Secret-Keys

Jeder Key enthaelt eine **vollstaendige Datei**, nicht nur einen einzelnen
Passwortwert. Es gibt keinen Merge zwischen Values und externer Vollkonfiguration.

| Komponente | Immer erforderlich | Bedingt erforderlich |
| --- | --- | --- |
| EP | `ecp.properties`, `ecp-users.properties`, `ecp-password.properties`, `server.xml`, `users.properties` | Bei nichtleerem `jmxRemoteProperties`: `jmxremote.password`, `jmxremote.ssl` |
| CD | `ecp-directory.properties`, `ecp-users.properties`, `ecp-password.properties`, `server.xml` | Bei nichtleerem `jmxRemoteProperties`: `jmxremote.password`, `jmxremote.ssl` |
| BR | `broker.properties`, `artemis-users.properties` | Single: `broker.xml`; HA: `broker-master.xml` und `broker-slave.xml`; mit Web-Service: `bootstrap.xml` |
| AR | `artemis-users.properties` | Single: `broker.xml`; HA: `broker-master.xml` und `broker-slave.xml`; mit Web-Service: `bootstrap.xml` |

Web-Service bedeutet ein konfiguriertes `service.http` oder `service.https`.
Die Broker-Defaults enthalten HTTPS, benoetigen also `bootstrap.xml`.
Bei HA werden die Master-/Slave-Eingaben durch den nichtprivilegierten
Initcontainer verarbeitet; das daraus entstehende Arbeits-XML ist keine von
Helm aus privaten Values gerenderte Vollkonfiguration.

Private Vollfiles ausserhalb des Repositorys anhand der offiziellen, zur
Image-Version passenden ECP-/Artemis-Konfiguration erstellen und ueber den
freigegebenen Secret-Prozess bereitstellen. Keine Secret-Manifeste, privaten
Vollfile-Beispiele, Zugangsdaten oder Keystores in dieses Repository aufnehmen.
Insbesondere nicht alte Template-Defaults als sichere Betriebswerte kopieren.

Vor dem Start muessen in diesen externen Dateien zusammenpassen:

- Tatsaechliche Listener-Ports, Bind-Adressen, Service-/Pod-DNS und externe URLs.
- Datenbank-URL, Treiber, Schema, Credentials, Verbindungsparameter und HA-Profil.
- TLS-Protokolle, Zertifikate, Client-Authentifizierung, Trust-/Keystore-Pfade,
  Aliase und zugehoerige Passwoerter.
- Benutzer, Rollen, ECP-/Audit-Kennungen, Registrierungsdaten und interne
  Broker-Verbindungen; keine festen Beispielkennungen als produktive Identitaet.
- Daten-, Journal-, Logging- und sonstige Dateipfade zu den vorhandenen Mounts.
- Bei HA Shared-Store-Topologie, Connectoren und Cluster-Authentifizierung.

### Was die verbliebenen Values bewirken

| Bereich | Tatsaechliche Wirkung |
| --- | --- |
| `image`, `replicaCount`, `resourcesK8s`, `securityContext`, Storage, Service, Ingress, Gateway, Probes | Kubernetes-Ressourcen und Pod-Konfiguration |
| EP/CD `envConf.resourcesJvm`, `envConf.ecpLogFullStackTrace` | Oeffentliche JVM-Startkonfiguration |
| BR/AR `env.resourcesJvm` | Oeffentliche Artemis-Startkonfiguration |
| EP/CD `dataDirectory`, `loggingFilePath` | Daten-/Logs-PVC-Mountpfade; externe Properties muessen dazu passen |
| EP/CD `springProfilesActive` | HA-Helper-Validierung; das Laufzeit-/Logging-Profil muss zusaetzlich extern gesetzt sein |
| EP/CD `loggingFileName`, `loggingConfig` | Expliziter Pfadabgleich; keine Aenderung der externen Properties |
| EP `ecpProperties.internalBrokerAuthUser` | Benutzername im oeffentlichen Gruppenmapping, keine Kontoanlage |
| EP optional `usersProperties.users[].login` | Weitere oeffentliche Gruppenmitglieder, Passwort nur extern |
| EP/CD `instance[].jmxRemoteUsers` mit `login`/`access` | Oeffentliches JMX-Access-Mapping; passende Passwortdatei extern |
| BR/AR `artemisUsers[].login` | Oeffentliches `amq`-Rollenmapping; Benutzer/Credentials extern |
| EP/CD `sessionReplication` | Oeffentlicher Tomcat-Kontext und DNS-Umgebung; passendes externes Server-XML weiterhin erforderlich |
| BR/AR `brokerXml.highAvailability.acceptor.port` | HA-Port von Pod und Headless-Service, nicht Inhalt externer XML-Dateien |

Die Logback-/Log4j-Konfiguration wird oeffentlich geliefert. `console-logging`
in EP/CD-Values allein aktiviert das Laufzeitprofil nicht; es muss im Secret
ebenfalls stehen. Private Benutzerlisten entfallen aus Values. Beim CD kann eine
leere Rollenzuordnung nach offizieller Konfiguration extern erhalten bleiben;
Helm setzt keine vermeintliche Standardrolle ein.

Das benannte interne `configuration`-Template rendert ausschliesslich
oeffentliche Konfiguration. Private Vollfiles werden auch intern **gar nicht
gerendert**; private Legacy-Datensektionen und Dummy-Werte sind entfernt.
Die `omit`-Listen in `publicConfig` und der ConfigMap-Ausgabe bleiben als
defensiver Schutz fuer reservierte private Datei-Keys erhalten. Alte private
Values steuern keine extern eingebundene Datei. Weder diese Filter noch ein
erfolgreicher Render validieren Secret-Inhalte oder deren Uebereinstimmung mit Values.
`configMap`, Umgebungsvariablen und zusaetzliche Mounts nicht als Umgehung dieses
Vertrags fuer private Inhalte benutzen.

## Beispiele, Listen und globale Einstellungen

Pro Release die gesamten kanonischen Values des passenden Charts in eine eigene
Betreiberdatei kopieren. Darin alle Instanzeinstellungen pruefen, insbesondere
Name, `existingSecret`, Image, Storage, Ressourcen, Ports und externe Verbindungen.
Die folgenden Secret-Namen sind Platzhalter fuer extern bereitzustellende Objekte,
keine mitgelieferten Secrets.

| Chart | Release | Instanz | `existingSecret` |
| --- | --- | --- | --- |
| Endpoint | `ep1` | `ep1` | `ecp-endpoint-ep1-config` |
| Directory | `cd` | `cd` | `ecp-directory-cd-config` |
| ECP Broker | `br` | `br` | `ecp-broker-br-config` |
| Interner Artemis-Broker | `eptb1` | `artemis-eptb1` | `eccosp-artemis-eptb1-config` |

**Helm ersetzt Listen.** Fuer mehrere Instanzen desselben Charts eine gemeinsame
vollstaendige `instance`-Liste mit allen Eintraegen pflegen oder getrennte Releases
verwenden. Zwei `-f`-Dateien mit je einer Instanz werden nicht zusammengefuehrt:
Die letzte Liste gewinnt. Values verschiedener Charts gehoeren in getrennte
Helm-Aufrufe, nicht in einen gemeinsamen Aufruf. Zwei unabhaengige Instanzen
sind kein HA-Cluster. Eine weitere Endpoint-Instanz aktiviert JMX nicht automatisch.

`global` liegt an der Wurzel jeder Standalone-Values-Datei und gilt nur fuer den
jeweiligen Release. Gemeinsame Betreiberwerte bewusst in allen betroffenen
Dateien pflegen, statt Storage oder Registry-Konfiguration unbeabsichtigt zu
ueberschreiben:

- `global.storage.class: ''`: `storageClassName` wird bei normalen PVCs weggelassen;
  die Default-StorageClass des Clusters wird verwendet.
- `global.storage.class: '-'`: explizit leere StorageClass, keine dynamische
  Default-Provisionierung; passende statische PVs muessen vorhanden sein.
- Ein anderer String benennt die gewuenschte StorageClass. Keine Klasse wird
  vom Chart angelegt; Shared-Storage-Klassen werden separat gesetzt.
- `global.imagePullSecrets: []`: keine Registry-Credentials vorausgesetzt.
  Bei Bedarf vorhandene Pull-Secrets im Zielnamespace referenzieren.
- `global.imageBusybox`: `busybox` mit Tag `'1.37.0'`.

## Deployment in fuenf Schritten

Die folgenden Befehle sind Beispiele fuer den Betreiber, keine hier ausgefuehrten
Aktionen. Alle Pfade gelten ab Repository-Root. Fuer eine neue Installation
verwenden wir die getrennten Releases `cd`, `br`, `eptb1` und `ep1` im Namespace
`eccosp`. Die Betreiberdateien liegen im selbst anzulegenden Verzeichnis
`../eccosp-values` ausserhalb des Repositorys und enthalten keine privaten Vollfiles.

### 1. Zielumgebung und Migrationsbedarf klaeren

Kubernetes-Version, Image-Zugriff, Storage, Kapazitaet, Netzwerk/TLS, Namespace-
Policies und benoetigte externe Datenbanken freigeben. Bei bestehender Installation
zuerst den Migrationsabschnitt abarbeiten. Die Beispielgroessen sind Startwerte,
keine Produktionsdimensionierung. JVM-Heap plus nativer Speicher muessen unter
dem Container-Limit bleiben; Requests nach Lastmessung anpassen.

### 2. Vollkonfiguration und Secrets vorbereiten

Die benoetigten kompletten Dateien nach obigem Vertrag **ausserhalb des Repositorys**
erstellen. Den Zielnamespace und alle benoetigten Secrets durch den freigegebenen
Betriebsprozess bereitstellen lassen. Vor Schritt 5 muessen sie vollstaendig
befuellt sein; ein leerer Secret-Platzhalter genuegt nicht. Die Beispiele legen
keine Benutzer, Datenbanken, TLS-Zertifikate oder ECP-Registrierungen an.

Die externen Dateien fuer die vier eigenstaendigen Releases auf diese Services abstimmen:

| Verbindung | Adresse innerhalb desselben Namespace |
| --- | --- |
| Directory | `https://cd-ecp-directory-cd-svc:8443/ECP_MODULE` |
| ECP Broker | `amqps://br-ecp-broker-br-svc:5671` |
| Endpoint EP1 | `https://ep1-ecp-endpoint-ep1-svc:8443` |
| Interner Broker fuer EP1 | `amqps://eptb1-eccosp-artemis-artemis-eptb1-svc:5672` |

Diese Adressen sind Beispiele fuer die externen Konfigurationen, keine Helm-
Substitution. Andere Release-/Instanznamen oder Namespaces verlangen andere
Adressen und passende Zertifikate. ECP-Komponentencodes extern nach dem
Registrierungsverfahren festlegen, nicht aus Kubernetes-Namen ableiten.

### 3. Vollstaendige Betreiber-Values vorbereiten

Die oben verlinkten kanonischen Values jeweils vollstaendig kopieren: Directory
nach `../eccosp-values/cd.yaml`, ECP Broker nach `../eccosp-values/br.yaml`,
Artemis nach `../eccosp-values/eptb1.yaml` und Endpoint nach
`../eccosp-values/ep1.yaml`. Diese Dateien werden nicht mitgeliefert.
Die Default-Instanznamen entsprechen der obigen Tabelle. In jeder Datei
`instance[0].existingSecret` auf das zugehoerige bereitgestellte Secret setzen
und die gesamte Konfiguration fuer die Zielumgebung pruefen und anpassen.
`instance` und `global` bleiben direkt an der Values-Wurzel, ohne Chart-Namenspraefix.
Keine reduzierten Listen mit nur Name und Secret ueber die Defaults legen.
Fuer zusaetzliche Instanzen jeweils einen vollstaendigen Eintrag pflegen.
Eine lokale Helm-Installation ist nur fuer die Ausfuehrung der Beispiele noetig,
nicht fuer das Lesen oder Anpassen der Values.

### 4. Ohne Cluster linten und rendern

Jeden Release separat mit seiner vollstaendigen Betreiberdatei pruefen:

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

Namen, Selector, PVCs, Secret-Referenzen, Ports und SecurityContexts pruefen.
Ein erfolgreicher Render ist keine Cluster-, Registrierungs- oder Funktionspruefung.
Nur einen Endpoint testen: ausschliesslich dessen Chart und Betreiberdatei verwenden;
dadurch werden seine extern benoetigten Partner nicht automatisch installiert.

Fuer einen reinen lokalen Smoke-Test mit kanonischer Instanzliste vor `--set`:

```sh
helm lint ./charts/ecp-endpoint --namespace eccosp -f ./charts/ecp-endpoint/values.yaml --set 'instance[0].existingSecret=ecp-endpoint-ep1-config'
helm template ep1 ./charts/ecp-endpoint --namespace eccosp -f ./charts/ecp-endpoint/values.yaml --set 'instance[0].existingSecret=ecp-endpoint-ep1-config'
```

Das explizite `-f` verhindert, dass ein isolierter Listenindex-Override die
Default-Instanz bis auf den Secret-Namen ersetzt. Entsprechende Standalone-
Befehle stehen in jedem Chart-README. Dieser Smoke-Test prueft weder das Secret
noch die Betriebsfaehigkeit; fuer Deployments die geprueften Betreiberdateien nutzen.

### 5. Neue Installation und anschliessende Abnahme

Erst nach bereitgestelltem Namespace, befuellten Secrets, vorbereitetem Storage
und freigegebener externer Konfiguration installieren:

```sh
helm install cd ./charts/ecp-directory --namespace eccosp -f ../eccosp-values/cd.yaml --wait --timeout 15m
helm install br ./charts/ecp-broker --namespace eccosp -f ../eccosp-values/br.yaml --wait --timeout 15m
helm install eptb1 ./charts/eccosp-artemis --namespace eccosp -f ../eccosp-values/eptb1.yaml --wait --timeout 15m
helm install ep1 ./charts/ecp-endpoint --namespace eccosp -f ../eccosp-values/ep1.yaml --wait --timeout 15m
```

Diese Befehle gelten fuer Single-Instanzen und eine **neue** Installation.
Jeden Schritt einzeln pruefen; es gibt keine releaseuebergreifende Transaktion
oder gemeinsamen Rollback. Nicht als Upgrade-/Migrationsrezept verwenden.
Die Befehle registrieren keine Komponenten.
Danach kontrolliert PVC-Bindung, Initcontainer, TLS/Authentifizierung, externe
Datenbank, ECP-Registrierung und einen vollstaendigen Nachrichtenfluss pruefen.
Partnerfreigaben und Registration-Tool-Ablauf erfolgen ausserhalb des Charts.
Ein positives Helm-`--wait` ersetzt diese Abnahme nicht.

## Storage, Sicherheit und Probes

### Persistenz und Ownership

EP/CD nutzen Daten-PVCs und standardmaessig persistente Logs (`keepLogsAfterRestart: true`).
BR/AR haben Daten-/Keystore- und Journal-Storage; Logs sind standardmaessig fluechtig
(`false`). BR hat zusaetzlich einen PVC fuer Registration-Tool-Logs. Shared Storage
ist in allen Single-Defaults aus; Klassen sind leer, Shared-Groessen explizit 1Gi.
NFS oder eine bestimmte StorageClass wird nicht vorausgesetzt.

Seed-Initcontainer kopieren vorhandene Image-Dateien ohne Ueberschreiben auf die
Daten-PVCs. Keystores bleiben dort erhalten; diese Initialisierung ist keine
ECP-Registrierung und keine sichere automatische Zertifikatsrotation. Nicht
vorhandene bzw. falsche Betriebskeystores extern bereitstellen oder registrieren.
Beim BR wird der etc-Arbeitsbereich als `emptyDir` initialisiert, die Keystores
liegen im Datenbereich. AR nutzt fuer etc/Keystores den Daten-PVC.

Anwendungscontainer laufen standardmaessig als UID/GID 2000 (EP/CD/BR) bzw.
2030 (AR), ohne Privilege Escalation, mit `RuntimeDefault`-Seccomp und ohne
Capabilities. Die beiden Seed-/Ownership-Initcontainer laufen dagegen als Root
mit ausschliesslich `CHOWN`, `FOWNER`, `DAC_OVERRIDE`; sie mounten keine projizierte
private Konfiguration. Zusaetzliche eigene Container gesondert pruefen.

**Restricted Pod Security Admission ist damit nicht erfuellt.** Nicht behaupten,
ein Non-Root-Hauptcontainer mache den gesamten Pod Restricted-kompatibel.
Bei NFS `root_squash` koennen auch diese Root-Initcontainer an `chown`/`chmod`
scheitern. Ownership und Rechte deshalb mit dem Storage-Betreiber vorprovisionieren
und das Init-Verhalten in einer Testumgebung pruefen. Vorprovisionierung allein
deaktiviert die weiterhin ausgefuehrten Root-Initcontainer nicht; eine strikt
Restricted-/Root-Squash-Umgebung benoetigt eine separat freigegebene Anpassung
des Deployment-/Storage-Konzepts, nicht pauschal mehr Rechte.

### Aussagekraft der Probes

Die ausgelieferten Values enthalten pro Probe nur
`enabled`: Startup und Readiness sind an, Liveness ist aus. Aktionen, Ports und
Timing-Defaults liegen im jeweiligen `*.probes`-Template-Helper, den das
StatefulSet einbindet. Die Standardwerte muessen nicht in Values wiederholt werden.
Bestehende explizite Timing-Overrides bleiben optional unterstuetzt; das
Standardverhalten aendert sich durch die vereinfachten Values nicht.

| Probe | Default | Bedeutung |
| --- | --- | --- |
| Startup | an, 10s Intervall, 2s Timeout, 60 Fehlversuche | EP/CD und Single-Broker: TCP; HA-Broker: nur `kill -0 1` |
| Readiness | an, 10s Intervall, 2s Timeout, 3 Fehlversuche | TCP auf Web-Port bei EP/CD bzw. AMQP-Port bei BR/AR |
| Liveness | aus, bei Aktivierung 10s/2s, 3 Fehlversuche | TCP bzw. bei HA-Brokern nur PID-1-Existenz |

Initialverzoegerung ist 0, Erfolgsschwelle 1. Ein erreichbarer TCP-Port beweist
weder TLS noch Authentifizierung, DB-Verbindung, Registrierung oder fachliche
Gesundheit. PID 1 kann existieren, obwohl der Broker blockiert ist. Kein robustes
Full-Health-Monitoring behaupten. `databaseWait` ist nicht unterstuetzt;
DB-Initialisierung und Wiederverbindung liegen bei Anwendung und Betrieb.

## High Availability explizit konfigurieren

### EP und CD

`replicaCount > 1` verlangt unter `ecpProperties` bzw. `ecpDirectoryProperties`
ein `springProfilesActive` mit `ecp-ha`, `springDatasourceDriverClassName` und
eine externe JDBC-URL in `ecpDBUrl`. Diese drei Angaben sind oeffentliche
Topologie-/Validierungswerte, keine DB-Credentials. URL ohne Zugangsdaten pflegen.
Treiber werden fuer PostgreSQL, MariaDB/MySQL, SQL Server und Oracle akzeptiert;
die tatsaechliche Image-/DB-Kombination muss offiziell unterstuetzt sein.

Die zugehoerige externe Vollkonfiguration muss dasselbe HA-Profil und dieselbe
DB-Verbindung mit vollstaendigen Credentials enthalten. Keine eingebettete DB
ueber mehrere Replikate teilen. Session-Replikation verlangt zusaetzlich die
korrekte Tomcat-Cluster-Konfiguration im externen Server-XML und erreichbares
Discovery-Netzwerk. Helm rendert diese privaten Einstellungen nicht.

### BR und AR: Shared Store

Fuer eine neue HA-Instanz die **vollstaendige** Instanzliste anpassen:

| Value | HA-Beispiel / Pflicht |
| --- | --- |
| `replicaCount` | `2` |
| `useSharedStorageForJournal` | `true` |
| `useSharedStorageForConfiguration` | `false` |
| `sharedStorageAccessMode` | `ReadWriteMany` |
| `sharedStorageClassJournal` | z.B. `rwx-journal`, nur falls diese geeignete Klasse tatsaechlich bereitgestellt wurde |
| `sharedStorageSizeJournal` | `1Gi` als Startwert, betrieblich dimensionieren |
| `brokerXml.highAvailability.acceptor.port` | `61616`, muss mit externer Konfiguration uebereinstimmen |

`rwx-journal` ist ein Beispielname, keine mitgelieferte Klasse. RWX allein
beweist keine Artemis-Eignung: Dateisperren, Konsistenz, Latenz, Ausfallverhalten
und Rechte des konkreten Backends pruefen. Nur das Journal wird gemeinsam benutzt;
Konfiguration und Keystores bleiben pro Pod getrennt. Keine Single-Instanz durch
blosses Hochskalieren ohne externe HA-Dateien und Storage-Plan in HA umwandeln.

Im Secret statt des Single-Keys beide HA-Keys bereitstellen. Die externen XML-
Dateien benoetigen Shared-Store-Policy, passende Journal-/Paging-/Binding-/Large-
Message-Pfade, Listener, Credentials und vollstaendige Connectoren. Das oeffentliche
HA-Skript ersetzt lediglich `MASTER`, `SLAVE1` bis `SLAVE<n>` und im Slave-Dokument
`SLAVE-REF` durch Pod-Namen und kopiert das ausgewaehlte XML ins Arbeitsverzeichnis.
Ordinal 0 erhaelt die Master-Konfiguration, weitere Ordinals die Slave-Konfiguration;
das ist keine Aussage darueber, welcher Broker nach einem Failover aktuell aktiv ist.
Keine Helm-Ausdruecke in externen Dateien erwarten; Namespace und DNS-Suffixe
werden dort nicht automatisch eingesetzt. Die reservierten Ersetzungstokens
nicht in anderen XML-Inhalten verwenden.

Fuer Release `br`, Namespace `eccosp` und Instanz `br` lautet etwa der HA-Pod-DNS-Name
`br-ecp-broker-br-0.br-ecp-broker-br-headless-svc.eccosp.svc.cluster.local`.
Bei abweichender Cluster-Domain extern anpassen. Der Headless-Service publiziert
auch NotReady-Adressen fuer Discovery; Clients verwenden den normalen `-svc`.
`service.amqp` wird bei BR/AR abgelehnt. `service.amqps.port` ist der Port-Key;
ein optionaler `brokerXml.acceptor.port` muss dazu passen. Weder dieser Value
noch `brokerXml.acceptor.sslEnabled` aendern das externe Broker-XML.

HA-StatefulSets verwenden `podManagementPolicy: Parallel` und `OnDelete`.
Passive Backups oeffnen gegebenenfalls keinen AMQP-Listener und bleiben daher
NotReady. Ein pauschales `helm --wait` kann bei HA bis zum Timeout warten;
`--atomic` kann daraufhin zurueckrollen. Fuer HA eine separate, rollenbewusste
Abnahme und einen kontrollierten Wartungsablauf verwenden, nicht die Readiness
deaktivieren, nur um einen gruenen Rollout zu erzwingen.

## Secret-Rotation, JMX und Netzwerk

1. Neue externe Konfiguration und gegebenenfalls Keystores/Credentials abgestimmt
   vorbereiten; Rueckweg und Sicherung fuer die alte Version festlegen.
2. Vorhandenes Secret ueber den freigegebenen Prozess aktualisieren oder ein neues
   Secret referenzieren. Keine Inhalte in Helm-Values oder Release-Artefakte kopieren.
3. `secretRevision` der betroffenen Instanz als String erhoehen, z.B. von `'1'`
   auf `'2'`, und die oeffentliche Release-Konfiguration aktualisieren.
4. Pods kontrolliert neu starten und die neue Konfiguration fachlich abnehmen.
   EP/CD und Single-Broker verwenden regulaere StatefulSet-RollingUpdates.
   HA-Broker mit `OnDelete` verlangen manuelle, einzelne Pod-Ersetzungen.
   Aktive/passive Rolle zuerst feststellen, Backup-Bereitschaft und Failover
   pruefen; niemals pauschal alle Pods gleichzeitig loeschen.

`checksumConfig: true` erfasst nur die oeffentliche ConfigMap. Die Checksumme
verfolgt weder Inhalte referenzierter Secrets noch Secrets aus `env`/`extraEnv`
oder zusaetzlichen Volumes. Secret-`subPath`-Mounts aktualisieren laufende Container
nicht automatisch; bei HA wird das Arbeits-XML nur im Initcontainer aufbereitet.
Auch eine geaenderte Checksumme oder `secretRevision` hebt `OnDelete` nicht auf.

JMX bleibt bei EP/CD standardmaessig unkonfiguriert. Bei nichtleerem
`jmxRemoteProperties` sind **beide** zusaetzlichen privaten Keys erforderlich,
auch wenn einzelne JMX-Schalter false sind. Nur oeffentliche JMX-Optionen und
`instance[].jmxRemoteUsers: [{login: monitor, access: readonly}]` fuer das
oeffentliche Access-Mapping in Values pflegen; kein `password`. Die Liste liegt
direkt an der Instanz, nicht unter `jmxRemotePassword`. Alte verschachtelte
Benutzerlisten werden nicht mehr ausgewertet. Die externe `jmxremote.password`
muss zu den Logins dieser Access-Liste passen; Helm prueft diese Zuordnung nicht.
Passwort-/SSL-Inhalte vollstaendig extern halten.
Authentifizierung, SSL und Registry-SSL bewusst konfigurieren; separate
JMX-Netzwerkfreigabe und die Java-Anforderungen an Dateirechte testen.

Ingress ist standardmaessig aus. Bei Aktivierung sind Host, Controller und TLS-
Secret bewusst zu setzen. Bei `ingressClassName: nginx` und HTTPS-Backend wird
die Backend-Protokoll-Annotation ergaenzt, sofern nicht vorgegeben. Das ersetzt
keine TLS-/mTLS-Konfiguration der Anwendung. Web-Ingress transportiert nicht
automatisch AMQP; dafuer einen geeigneten TCP-Zugang planen. Bei BR/AR beeinflusst
`service.https.host` bzw. `service.http.host` die oeffentliche Jolokia-Origin-Policy;
diese pruefen, statt sich auf den weit gefassten leeren Default zu verlassen.

Alle vier Charts bieten ausserdem optionales Gateway-API-Routing; pro Instanz
ist `gateway.enabled: false` der Default. Voraussetzungen, Routing und TLS-
Beispiele stehen in [Gateway_API.md](Gateway_API.md). Die Charts ersetzen damit
weder die externe Anwendungskonfiguration noch die betriebliche TLS-Abnahme.

## Migration von bisherigen Charts auf 5.0.0

### Bisherigen Umbrella in unabhaengige Releases ueberfuehren

Der fruehere `ecco-sp`-Umbrella wurde entfernt. Alte verschachtelte Komponenten-
Values nicht unveraendert weiterreichen: Pro Zielrelease die aktuellen
Standalone-Defaults vollstaendig uebernehmen und die benoetigten Einstellungen
an deren Wurzel migrieren. Ein Helm-Release laesst sich nicht durch einen normalen
Upgrade-Aufruf in mehrere Releases aufteilen. Release-Ownership, Ressourcen-
und PVC-Namen sowie externe DNS-/TLS-Bezuege nach dem gestuften Ablauf pruefen.
Keine automatische Ressourcenuebernahme oder gefahrlose Deinstallation des
alten Releases voraussetzen.

### Alte private Values migrieren, nicht weiterreichen

Die folgende Liste beschreibt alte Schluesselgruppen, keinen neuen Values-
Katalog. Nicht mehr benoetigte private Schluessel aus Betreiber-Values entfernen;
ihre vollstaendige Laufzeitkonfiguration extern verwalten. Auch scheinbar
oeffentliche Einzelwerte innerhalb einer privaten Vollfile werden nicht mehr
in die extern eingebundene Datei uebertragen.

| Alte Values / Gruppen | Neues Ziel und Besonderheit |
| --- | --- |
| EP `ecpProperties`, CD `ecpDirectoryProperties` | Vollstaendige jeweilige Properties-Datei im Secret; nur oben genannte Pfad-/Profil-/HA-/Gruppenwerte in Values behalten |
| `ecpKeystorePassword`, `ecpAuthKeystorePassword`, `ecpDBKeystorePassword`, CD `ecpDirectoryRegKeystorePassword`, `ecpDirectoryCAKeystorePassword` und zugehoerige Locations | Externe Properties und Server-/Broker-XML konsistent zu PVC-Keystores setzen |
| `ecpDBUsername`, `ecpDBPassword`, Datasource-/DBCP2-Optionen, Validation Query | Externe DB-Konfiguration; bei HA nur URL ohne Credentials und Treiber zusaetzlich fuer die Validierung behalten |
| `ecpDBHostname`, `ecpDBName`, `databaseWait` und globale MySQL-/MsSQL-/Postgres-/Oracle-Client-Images | Keine DB-Wartecontainer mehr; keine Readiness-Garantie fuer Datenbanken |
| `internalBrokerHost`, `internalBrokerUrls`, Ports, Authentifizierung, Keystore-, Queue- und Verbindungsparameter | EP-Vollkonfiguration extern; nur `internalBrokerAuthUser` fuer das oeffentliche Gruppenmapping bleibt |
| `ecpCsrfSecret`, Jasypt-Algorithmus, `ecpPasswordProperties.encryptionPassword` | Extern generierte/verwaltete Werte; alten festen CSRF-Wert und bekannte Default-Passwoerter ersetzen |
| `ecpUsersProperties.ecpEndpointUsers`, `ecpUsersProperties.ecpDirectoryUsers`, `usersProperties.users[].password` | Externe Benutzerdateien; EP-Gruppenmitglieder bei Bedarf nur mit Login oeffentlich; CD-Rolle darf gemaess offizieller Konfiguration leer bleiben |
| `jmxRemotePassword`, `jmxRemoteSsl` inklusive Benutzerpasswoertern und Keystore-/Truststore-Passwoertern | Externe JMX-Vollfiles; nur Login-/Access-Zuordnung nach `instance[].jmxRemoteUsers` migrieren, passende externe Passwortdatei bereitstellen |
| LDAP, SOCKS-Proxy, NAT, AMQP-API/SendHandler, FSSF, Prioritaeten, Brokerparameter, Parallelitaet, Content-Storage, Synchronisations-/Registrierungs-/Cleaning-Jobs, Directory-Zugriff/TTL, UI-Theme | Externe EP-/CD-Properties; keine Wirkung alter Values auf die gemounteten Vollfiles |
| Actuator-/Prometheus-/Health-Threshold-Properties, `springJmxEnabled`, Automatic-Update-Optionen | Externe Laufzeitkonfiguration; nicht mit Kubernetes-Probes verwechseln |
| BR `brokerProperties` einschliesslich Kontaktdaten, Netzwerken, Filtern, ECP-Code, Directory-URL/-Code und Registrierungs-ID | Vollstaendige externe Broker-Properties; Registrierung und Aktualisierung der Ergebnisse ausserhalb von Helm |
| BR/AR `artemisUsers[].password`, Default-User/-Password | Externe Artemis-Benutzerdatei; `artemisUsers` nur Login fuer Rollenmapping |
| AR `artemisKeystoreLocation`, `artemisKeystorePassword` | Externes Bootstrap-/Broker-XML und passende PVC-Keystores |
| BR/AR `brokerXml.default`, Journal, CriticalAnalyzer, AddressSettings, Acceptor-TLS/Properties, Audit-/ECP-Kennung, `maskPassword`, Codec/Key, Cluster-User/-Password | Externes Single- oder Master-/Slave-XML; in Values nur benoetigte Port-/Topologiepruefungen behalten |
| BR/AR `prometheusEnabled` und Web-Bootstrap-Optionen | Externes Broker-/Bootstrap-XML; der Value schaltet im externen Dokument nichts um |
| Alter EP-Bootstrap-Custom-Mount auf einen fremden Artemis-Pfad | Entfernen; nicht Bestandteil der Endpoint-Grundkonfiguration |

Alte Defaults koennen in bisherigen Helm-Release-Secrets, ConfigMaps, Backups oder
Git-Historie verbleiben. Die Migration loescht diese Historie nicht automatisch.
Zugriff, Aufbewahrung und notwendige Rotation kompromittierter/bekannter Werte
mit dem Sicherheitsbetrieb abstimmen, ohne fuer einen Rollback benoetigte
Backups unkontrolliert zu vernichten. Kein `--reuse-values` fuer diese Migration.

### Gestufter Ablauf mit PVC-Erhalt

1. **Inventarisieren:** alten Release-Namen, Namespace, Chart-/Image-Versionen,
   komplette Values, Live-Manifeste, Selector, StatefulSet-ServiceName,
   ClaimTemplate-Namen, PVC-/PV-Bindungen, StorageClass/ReclaimPolicy und
   Registrierungsidentitaeten gesichert erfassen. Private Exporte nicht ins Repo.
2. **Konsistent sichern:** Datenbanken, Daten-PVCs, Journal, Keystores,
   Registrierungsdaten und benoetigte Logs sichern. Snapshot-/Backup-Konsistenz
   bei aktiven Schreibern klaeren; Restore auf getrennten Volumes testen.
3. **Ziel rendern und vergleichen:** Namen entstehen aus Release, Chart und
   Instanz. Basen mit mehr als 45 Zeichen werden gekuerzt und mit Hash ergaenzt.
   `fullnameOverride` akzeptiert maximal 45 Zeichen, garantiert aber **kein**
   kompatibles Upgrade. Selector enthalten nun auch `app.kubernetes.io/instance`;
   Headless-Service und StatefulSet-`serviceName` sowie ClaimTemplate-/PVC-Namen
   koennen sich geaendert haben. Diese Felder sind teilweise unveraenderlich.
4. **PVC-Zuordnung planen:** Ein Claim heisst z.B.
   `data-ep1-ecp-endpoint-ep1-0`, ein Shared-Journal-Claim z.B.
   `br-ecp-broker-br-journal-claim`. Alte PVCs werden nicht anhand ihres
   Inhalts automatisch gefunden. Neue Namen nicht einfach auf leere Volumes
   zeigen lassen. Kontrolliertes Restore oder explizite PV/PVC-Neuzuordnung mit
   dem Storage-Betreiber planen; Daten-PVCs und Shared-PVCs separat behandeln.
5. **Getrennt erproben:** neue Ressourcen auf isolierten Test-/Restore-Volumes
   mit externen Secrets starten. Keine parallelen produktiven Schreiber auf
   demselben Journal/DB-Zustand und keine doppelt aktiven ECP-Identitaeten erzeugen.
   Registrierung, TLS, DB, Benutzer, Neustart, Nachrichtenfluss und bei HA
   Failover/Failback pruefen. Name-/Topologieaenderungen auch extern nachziehen.
6. **Kontrollierter Cutover:** Wartungsfenster, Nachrichten-/Schreibstopp,
   finales konsistentes Backup und Abnahmekriterien festlegen. Falls ein
   StatefulSet neu erstellt werden muss, Erhalt der PVCs/PVs vorab sicherstellen.
   Kein pauschales `helm uninstall`, `--force` oder Loeschen aller PVCs als
   vermeintliche Reparatur. Erst nach Restore und Pruefung Verkehr umschalten.
7. **Rueckweg erhalten:** alte Ressourcen/Backups bis zur Abnahme aufbewahren.
   Bei Fehlern Schreibzugriffe stoppen und abgestimmten Restore/Routing-Rollback
   durchfuehren. Ein `helm rollback` macht DB-/Journal-/Keystore-Aenderungen
   nicht automatisch rueckgaengig. Aufraeumen erst nach erfolgreicher Abnahme.

Auch der Wechsel von Single zu HA kann unveraenderliche StatefulSet-Felder und
PVC-Layouts betreffen. Diesen Wechsel wie eine Topologiemigration planen, nicht
nur als Aenderung von `replicaCount`.

## CI und Grenzen der Nachweise

Die [../.github/workflows/lint.yml](../.github/workflows/lint.yml) prueft alle vier
Standalone-Charts ohne Cluster: Fixture-/Assertion-Tests,
Lint, Rendern, Manifestvalidierung sowie Source- und Paket-Tests.
Uploads enthalten synthetische Testartefakte und
validierte Pakete, keine realen Secrets. Keine produktiven Konfigurationen in
Fixtures, Render-Ausgaben oder CI-Uploads einschleusen.

Fuer gerenderte `HTTPRoute`- und `BackendTLSPolicy`-Ressourcen werden die benoetigten
Gateway-API-CRD-Quellen der gepinnten Version **v1.4.1** ueber verifiziertes HTTPS
geladen und vor dem Parsen gegen fest hinterlegte SHA-256-Pruefsummen geprueft.
Daraus erzeugte strikte Schemas dienen der clusterfreien Manifestvalidierung.
Kubernetes-CEL-Regeln werden dabei nicht ausgefuehrt; dies ist weder ein
Controller-/Laufzeittest noch ein Test gegen einen Cluster.

Die [../.github/workflows/Release Charts.yml](../.github/workflows/Release%20Charts.yml)
veroeffentlicht erst nach erfolgreicher Validierung die vier validierten Pakete.
Die aktuellen Chart-Versionen bleiben 5.0.0; eine gemeinsame Dependency-Version
ist fuer die unabhaengigen Charts nicht erforderlich.
CI beweist keine Image-Verfuegbarkeit, Cluster-Admission, Storage-Eignung,
Registrierung, TLS-/DB-Funktion oder HA-Ausfallsicherheit. Diese Nachweise
bleiben Aufgabe der anschliessenden Test- und Betriebsabnahme.
