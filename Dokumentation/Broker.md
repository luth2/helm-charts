# Broker

Offizielle Quelle:

- [Broker Manual](https://eccosp-docs.entsoe.eu/s/ecco-sp/m/broker-manual)
- [ECCo SP Documents](https://eccosp-docs.entsoe.eu/k)

## Zweck

Der Broker ist die zentrale Service-Provider-Komponente fuer den externen Nachrichtenaustausch im ECP-Netz. Er uebernimmt die eigentliche AMQP-basierte Zustellung zwischen Teilnehmern.

## Rolle im Gesamtsystem

Im Unterschied zum internen Broker ist der Broker fuer die netzweite Kommunikation zwischen Komponenten und Organisationen ausgelegt.

- Endpoints verbinden sich fuer den externen Nachrichtenaustausch mit dem Broker.
- Die zulaessigen Kommunikationspartner und Berechtigungen orientieren sich an Informationen aus dem Component Directory.
- Message Paths und Queue-Management sind zentrale Betriebsaspekte.

## Technischer Aufbau laut Doku

Die offizielle Dokumentation nennt zwei Kernkomponenten:

- einen AMQP-Broker auf Basis von ActiveMQ Artemis
- ein benutzerdefiniertes Authentication- und Authorization-Plugin, das Sicherheitsinformationen aus dem Component Directory verwendet

## Betriebsrelevante Punkte

- Der Broker steuert Queue-Management fuer die Nachrichtenvermittlung.
- Authentifizierung und Autorisierung sind integraler Bestandteil des Betriebs.
- Die Doku verweist zusaetzlich auf Themen wie lokale Component-Directory-Daten, Registrierung, Administration und Monitoring.

## Bezug zum Helm-Repository

- Chart: `charts/ecp-broker`
- Beispiel-Values: `ecco-sp/values-ecp-broker-br.yaml`

## Installationsanleitung auf VM

### Zielbild

Der Broker laeuft als eigenstaendige Serverkomponente auf einer VM und stellt zwei wesentliche Schnittstellen bereit:

- AMQPS fuer Endpoints auf Port 5671
- HTTPS fuer Administration bzw. Konsole auf Port 8161

Er verwendet Registrierungs- und Authentisierungsdaten aus dem Component Directory und kombiniert diese mit einer Artemis-Laufzeitinstanz.

### Voraussetzungen

- Linux-VM mit Java-Laufzeit entsprechend dem offiziellen Softwarepaket
- Erreichbares Home Component Directory
- Vorbereitete Registrierungsschluessel und spaeteres Auth-Keystore-Verfahren
- Freigeschaltete Ports 5671 und 8161
- Genug lokaler oder geteilter Speicher fuer Journal, Bindings und Paging

### Wichtige Verzeichnisse und Dateien

Aus der Repo-Konfiguration ergibt sich fuer eine klassische VM-Installation grob diese Struktur:

- Installationsbasis unter `/opt/ecp-broker`
- Laufzeitkonfiguration unter `/opt/ecp-broker/config`
- Artemis-Instanz unter `/opt/ecp-broker/broker`
- Lokaler Directory-Cache unter `/opt/ecp-broker/cd`
- Hauptkonfiguration `broker.properties`
- Artemis-Konfiguration `broker.xml`
- Java-/Startprofil `artemis.profile`
- Registrierungskeystore und Auth-Keystore im Konfigurationsbereich

### Installationsablauf

1. Die VM mit Betriebssystem, Java und Systembenutzer vorbereiten.
2. Das offizielle Broker-Paket installieren oder entpacken.
3. Die Verzeichnisse fuer Konfiguration, Laufzeitdaten, Journal und Logs anlegen.
4. `broker.properties` mit Component-Code, Kontaktinformationen, URLs und Home Component Directory konfigurieren.
5. Registrierungskeystore einspielen und die Erstregistrierung gegen das Home Component Directory durchfuehren.
6. Das dabei erzeugte Auth-Keystore sicher ablegen und in der Konfiguration referenzieren.
7. `broker.xml` und `artemis.profile` fuer Ports, TLS, Journal und Speicherverbrauch anpassen.
8. Den Broker als Systemdienst registrieren und starten.

### Inhaltlich wichtige Parameter

Bei einer VM-Installation sind insbesondere diese Werte entscheidend:

- `ecp.broker.urls`
- `ecp.broker.code`
- `ecp.directory.client.synchronization.homeComponentDirectoryPrimaryCode`
- `ecp.directory.client.synchronization.homeComponentDirectoryPrimaryUrl`
- `ecp.keystore.location` und `ecp.authKeystore.location`
- TLS- und Acceptor-Konfiguration in `broker.xml`
- Journal-, Paging- und Storage-Pfade der Artemis-Instanz

### Validierung nach der Installation

- HTTPS-Konsole auf Port 8161 pruefen
- AMQPS-Erreichbarkeit auf Port 5671 pruefen
- Synchronisation mit dem Component Directory pruefen
- Testverbindung eines Endpoints inklusive Authentifizierung validieren
- Queue-Erzeugung, Journal-Verhalten und Zertifikatsnutzung kontrollieren

### Hinweis fuer die Installationsreihenfolge

Auf VMs sollte der Broker nach dem Component Directory, aber vor den Endpoints in Betrieb gehen. Fuer HA-Szenarien sind Journal-Layout, Storage-Performance und Zertifikatsablage die kritischen Punkte.

## Kurzfazit

Der Broker ist die Schluesselkomponente fuer den gesicherten externen Transport. Wenn es um Queue-Verhalten, Sicherheitsrichtlinien, Teilnehmerzugriffe oder netzweite Kommunikation geht, ist diese Komponente massgeblich.