# Endpoint

Offizielle Quelle:

- [Endpoint Manual](https://eccosp-docs.entsoe.eu/s/ecco-sp/m/endpoint-manual)
- [ECCo SP Documents](https://eccosp-docs.entsoe.eu/k)

## Zweck

Der Endpoint ist die nutzernahe Komponente von ECP. Er stellt die Oberfläche und die API bereit, über die Business-Anwendungen Nachrichten senden, empfangen und in bestehende Prozesse integrieren.

## Rolle im Gesamtsystem

Der Endpoint sitzt zwischen den fachlichen Anwendungen und den zentralen Kommunikationsdiensten von ECCo SP.

- Für die interne Verarbeitung ist er an den internen Broker angebunden.
- Für den externen Nachrichtenaustausch nutzt er den Broker.
- Für Zertifikate und Informationen über andere Komponenten greift er auf das Component Directory zu.

## Wichtige Schnittstellen

- Interner Broker: AMQPS, typischer Default-Port 5672
- Broker: AMQPS, typischer Default-Port 5671
- Component Directory: HTTPS, typischer Default-Port 8443

Die offizielle Doku beschreibt den Endpoint außerdem als zentrale Integrationskomponente für verschiedene Kanäle und Verarbeitungsstufen, darunter Vor- und Nachverarbeitung sowie Registrierungshilfen.

## Betriebsrelevante Punkte

- Ein Endpoint muss in einem Home Component Directory registriert sein, um am ECP-Netz teilzunehmen.
- Die Verbindung zum Component Directory ist für laufendes Messaging nicht permanent zwingend, solange die zwischengespeicherten Informationen gueltig sind.
- Laut Dokumentation liegt die Default-TTL eines CD-Eintrags bei 28 Tagen.
- Die Konfiguration der Message Paths auf Empfängerseite bestimmt, welcher Broker für ein bestimmtes Routing verwendet wird.

## Bezug zum Helm-Repository

- Chart: `charts/ecp-endpoint`
- Beispiel-Values: `ecco-sp/values-ecp-endpoint-ep1.yaml`, `ecco-sp/values-ecp-endpoint-ep2.yaml`

## Installationsanleitung auf VM

### Zielbild

Der Endpoint wird auf einer eigenen VM oder auf einer dedizierten Applikations-VM betrieben und verbindet sich von dort aus mit drei externen Diensten:

- intern mit dem internen Broker auf Port 5672
- extern mit dem Broker auf Port 5671
- administrativ mit dem Component Directory auf Port 8443

### Voraussetzungen

- Linux-VM mit Java-Laufzeit entsprechend dem offiziellen Softwarepaket
- Ein erreichbares Component Directory
- Ein erreichbarer interner Broker
- Ein erreichbarer Broker fuer den externen Nachrichtenaustausch
- Vorbereitete Keystores fuer Registrierung und Authentisierung
- Optional eine externe Datenbank, falls kein lokaler Datenpfad genutzt werden soll

### Wichtige Verzeichnisse und Dateien

Aus den Repo-Konfigurationen lassen sich fuer den klassischen Betrieb vor allem diese Dateien und Pfade ableiten:

- Laufzeitdaten unter `/var/lib/ecp-endpoint`
- Logs unter `/var/log/ecp-endpoint`
- Hauptkonfiguration `ecp.properties`
- Logging-Konfiguration `ecp-logback.xml`
- Keystore `keystore.jks`
- Authentifizierungs-Keystore `authKeystore.jks`

Für einen späteren Container-Build sind genau diese Artefakte die Trennlinie zwischen Image-Inhalt und externer Laufzeitkonfiguration.

### Installationsablauf

1. Die VM mit Betriebssystem, Java und Systembenutzer fuer den Endpoint vorbereiten.
2. Das offizielle Endpoint-Softwarepaket auf die VM installieren oder entpacken.
3. Daten-, Log- und Konfigurationsverzeichnisse anlegen und mit stabilen Pfaden versehen.
4. `ecp.properties` mit Datenpfad, Broker-Verbindungen, Home Component Directory und Keystore-Pfaden konfigurieren.
5. Falls HA benoetigt wird, die externe Datenbank anbinden und das passende HA-Profil aktivieren.
6. Zertifikate und Keystores in die vorgesehenen Pfade ablegen.
7. Den Endpoint als Dienst, typischerweise via systemd oder herstellerspezifischem Startskript, registrieren.
8. Den Dienst starten und die HTTPS-Oberflaeche pruefen.

### Inhaltlich wichtige Parameter

Bei einer VM-Installation muessen insbesondere diese Punkte korrekt gesetzt sein:

- `internalBroker.urls`, `internalBroker.host`, `internalBroker.amqp.port`
- `internalBroker.auth.user`, `internalBroker.auth.password`
- `ecp.keystore.location`, `ecp.authKeystore.location`
- `ecp.directory.client.synchronization.homeComponentDirectoryPrimaryCode`
- `ecp.directory.client.synchronization.homeComponentDirectoryPrimaryUrl`
- gegebenenfalls `ecp.db.*` fuer externe Datenbankanbindung

### Validierung nach der Installation

- HTTPS-Zugriff auf den Endpoint pruefen
- Verbindung zum internen Broker pruefen
- Verbindung zum Broker pruefen
- Synchronisation mit dem Component Directory pruefen
- Registrierung abschliessen und Message Paths validieren

### Hinweis fuer die Installationsreihenfolge

Der Endpoint sollte auf VMs immer zuletzt in Betrieb gehen, weil er auf den funktionierenden internen Broker, den Broker und das Component Directory angewiesen ist.

## Kurzfazit

Der Endpoint ist der eigentliche Einstiegspunkt für Anwendungen. Wenn im Betrieb Integrationsfragen, Routing, Zertifikatsbezug oder die Anbindung an interne und externe Messaging-Dienste relevant sind, ist diese Komponente der primäre Ansatzpunkt.