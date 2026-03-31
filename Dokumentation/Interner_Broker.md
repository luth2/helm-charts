# Interner Broker

Offizielle Quelle:

- [Internal Broker Manual](https://eccosp-docs.entsoe.eu/s/ecco-sp/m/internal-broker-manual)
- [ECCo SP Documents](https://eccosp-docs.entsoe.eu/k)

## Zweck

Der interne Broker stellt die Messaging-Dienste fuer die interne Nachrichtenverarbeitung innerhalb des Endpoints bereit. Ohne diese Anbindung kann ein Endpoint Nachrichten nicht verarbeiten.

## Rolle im Gesamtsystem

Der interne Broker ist eine Infrastrukturkomponente fuer die interne Kommunikation.

- Er entkoppelt Verarbeitungsschritte innerhalb des Endpoint-Betriebs.
- Mehrere Endpoints koennen an eine gemeinsame Instanz angebunden werden.
- Auch Business-Anwendungen koennen ihn verwenden, wenn die Integration ueber den AMQP-Kanal erfolgt.

## Technischer Aufbau laut Doku

Die offizielle Dokumentation beschreibt zwei Kernbestandteile:

- einen AMQP-Broker auf Basis von ActiveMQ Artemis
- ein ECCo SP Audit Logger Plugin fuer Audit-Logging bei Verbindungen sowie beim Senden und Konsumieren von Nachrichten

## Betriebsrelevante Punkte

- Die Verbindung des Endpoints zum internen Broker ist obligatorisch.
- Mehrere Endpoints koennen sich eine Instanz teilen, wenn Queue-Namen sauber per Prefix getrennt werden.
- Der Fokus liegt weniger auf externer Teilnehmerkommunikation und staerker auf robuster interner Verarbeitung und Nachvollziehbarkeit.

## Bezug zum Helm-Repository

Im Repository wird der interne Broker ueber das Artemis-Chart abgebildet.

- Chart: `charts/eccosp-artemis`
- Beispiel-Values: `ecco-sp/values-eccosp-artemis-eptb1.yaml`, `ecco-sp/values-eccosp-artemis-eptb2.yaml`

## Installationsanleitung auf VM

### Zielbild

Der interne Broker wird als lokale oder zentrale interne Messaging-Komponente auf einer VM betrieben. Er stellt ueblicherweise bereit:

- AMQPS fuer den Endpoint auf Port 5672
- HTTPS fuer Administration bzw. Konsole auf Port 8161

Anders als der externe Broker ist er nicht fuer die netzweite Kommunikation gedacht, sondern fuer interne Verarbeitung und Auditierbarkeit.

### Voraussetzungen

- Linux-VM mit Java-Laufzeit entsprechend dem offiziellen Softwarepaket
- Vorbereiteter Keystore fuer TLS auf der AMQPS-Schnittstelle
- Definierte Benutzer und Rollen fuer Endpoint- oder Toolbox-Zugriffe
- Ausreichender lokaler Speicher fuer Journal, Bindings, Paging und Logs
- Geklaerte Queue-Prefixe, falls mehrere Endpoints dieselbe Instanz nutzen

### Wichtige Verzeichnisse und Dateien

Die Repo-Konfiguration legt fuer eine VM-Sicht vor allem diese Struktur nahe:

- Installationsbasis unter `/usr/share/eccosp-artemis`
- Instanzdaten unter `/opt/eccosp-artemis`
- Konfiguration unter `/opt/eccosp-artemis/etc`
- Laufzeitdaten unter `/opt/eccosp-artemis/data`
- `broker.xml` fuer Artemis- und TLS-Konfiguration
- `artemis.profile` fuer Start- und JVM-Parameter
- `keystore.jks` fuer den TLS-Endpunkt

### Installationsablauf

1. Die VM mit Betriebssystem, Java und Systembenutzer vorbereiten.
2. Das offizielle Internal-Broker- bzw. ECCoSP-Artemis-Paket installieren oder entpacken.
3. Instanz-, Daten-, Log- und Konfigurationsverzeichnisse anlegen.
4. `broker.xml` fuer den AMQPS-Acceptor, TLS, Journal und Speichergrenzen anpassen.
5. `artemis.profile` fuer JVM-Groessen und Startoptionen anpassen.
6. Den Keystore an der konfigurierten Stelle ablegen und Benutzerdateien pflegen.
7. Den Broker als Dienst registrieren und starten.
8. Erst danach die verbundenen Endpoints auf diese Instanz ausrichten.

### Inhaltlich wichtige Parameter

Bei einer VM-Installation sind insbesondere diese Punkte relevant:

- Acceptor-Port und TLS-Parameter in `broker.xml`
- Keystore-Pfad und Passwort
- Journal-, Bindings-, Paging- und Large-Message-Verzeichnisse
- JVM-Werte in `artemis.profile`
- Benutzer und Rollen fuer die zugreifenden Clients
- optional Queue-spezifische Address-Settings

### Validierung nach der Installation

- HTTPS-Konsole auf Port 8161 pruefen
- AMQPS-Schnittstelle auf Port 5672 pruefen
- Benutzeranmeldung und TLS-Handshake testen
- Queue-Erzeugung und Queue-Prefixe mit einem Test-Endpoint pruefen
- Audit-Logging und Journal-Verhalten kontrollieren

### Hinweis fuer die Installationsreihenfolge

Der interne Broker muss auf VMs vor den abhaengigen Endpoints bereitstehen. Wenn mehrere Endpoints dieselbe Instanz nutzen, muessen Queue-Prefixe und Benutzerrechte sauber getrennt werden.

## Kurzfazit

Der interne Broker ist die technische Basis fuer die interne Endpoint-Verarbeitung. In Kubernetes ist er vor allem fuer stabile interne Messaging-Pfade, Auditierbarkeit und eine saubere Trennung mehrerer Endpoint-Instanzen relevant.