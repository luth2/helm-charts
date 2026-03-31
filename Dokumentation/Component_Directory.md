# Component Directory

Offizielle Quelle:

- [Component Directory Manual](https://eccosp-docs.entsoe.eu/s/ecco-sp/m/component-directory-manual)
- [ECCo SP Documents](https://eccosp-docs.entsoe.eu/k)

## Zweck

Das Component Directory ist die zentrale Verzeichnis- und Registrierungsinstanz im ECP-Netz. Es haelt die oeffentlich relevanten Informationen ueber Komponenten vor und stellt Schnittstellen fuer Registrierung, Konfigurationsaenderungen und Synchronisation bereit.

## Rolle im Gesamtsystem

Jede Komponente muss sich zunaechst bei einem Home Component Directory registrieren, um am Netz teilzunehmen.

- Registrierung neuer Komponenten
- Aktualisierung bestehender Konfigurationen
- Synchronisation lokaler Verzeichnisse mit einem Component Directory

Darueber hinaus behandelt die offizielle Doku Themen wie Zertifizierungsstellen-Updates, zentrale Verwaltung von Message Paths und Gruppen von ECP-Netzen.

## Technischer Aufbau laut Doku

Das Component Directory besteht laut Manual aus zwei Teilen:

- einer Directory-Anwendung mit REST-Schnittstelle
- einem zugehoerigen Directory Store

## Betriebsrelevante Punkte

- Das Component Directory ist der Vertrauensanker fuer Stammdaten und Sicherheitsbezug im Netz.
- Andere Komponenten greifen auf diese Daten fuer Registrierung, Zertifikate und Partnerinformationen zu.
- Eine stabile Synchronisation und konsistente Pflege der Eintraege sind fuer einen stoerungsfreien Betrieb zentral.

## Bezug zum Helm-Repository

- Chart: `charts/ecp-directory`
- Beispiel-Values: `ecco-sp/values-ecp-directory-cd.yaml`

## Installationsanleitung auf VM

### Zielbild

Das Component Directory wird als zentrale Vertrauens- und Registrierungsinstanz auf einer VM betrieben. Es stellt typischerweise eine HTTPS-Oberflaeche bzw. REST-Schnittstelle auf Port 8443 bereit und speichert Verzeichnis- und Zertifikatsinformationen lokal oder in einer externen Datenbank.

### Voraussetzungen

- Linux-VM mit Java-Laufzeit entsprechend dem offiziellen Softwarepaket
- Vorbereitete Keystores, CA-bezogene Passwoerter und Registrierungsdaten
- Optional eine externe Datenbank fuer HA- oder zentrale Persistenz
- Freigeschalteter HTTPS-Port 8443
- Administrativer Zugriff fuer Erstkonfiguration und Nutzeranlage

### Wichtige Verzeichnisse und Dateien

Aus der Repo-Konfiguration ergeben sich fuer den klassischen VM-Betrieb vor allem diese Artefakte:

- Laufzeitdaten unter `/var/lib/ecp-directory`
- Logs unter `/var/log/ecp-directory`
- Hauptkonfiguration `ecp-directory.properties`
- Logging-Konfiguration `ecp-logback.xml`
- Keystore `keystore.jks`
- Authentifizierungs-Keystore `authKeystore.jks`
- Benutzerdatei fuer Directory-Accounts

### Installationsablauf

1. Die VM mit Betriebssystem, Java und Systembenutzer vorbereiten.
2. Das offizielle Component-Directory-Paket installieren oder entpacken.
3. Daten-, Log- und Konfigurationsverzeichnisse anlegen.
4. `ecp-directory.properties` fuer Datenpfad, HTTPS, Zertifikate, Synchronisation und gegebenenfalls externe Datenbank anpassen.
5. Keystores und CA-bezogene Passwoerter sauber hinterlegen.
6. Administrative Benutzer einrichten.
7. Das Directory als Dienst registrieren und starten.
8. Nach erfolgreicher Initialisierung nachgelagerte Komponenten gegen dieses Directory registrieren.

### Inhaltlich wichtige Parameter

Bei einer VM-Installation sind insbesondere diese Werte kritisch:

- `spring.profiles.active` fuer non-HA oder HA-Betrieb
- `ecp.keystore.location`, `ecp.authKeystore.location`
- `ecp.directory.regKeystore.password`, `ecp.directory.caKeystore.password`
- `ecp.automaticUpdate.*` fuer Zertifikatserneuerung
- `ecp.directory.client.synchronization.directorySynchronizationInterval`
- gegebenenfalls `ecp.db.*` fuer externe Datenbank

### Validierung nach der Installation

- HTTPS-Zugriff auf Port 8443 pruefen
- Admin-Login pruefen
- Zertifikatsfunktionen und automatische Updates pruefen
- Synchronisation mit weiteren Directories pruefen, falls genutzt
- Registrierung einer Testkomponente erfolgreich durchspielen

### Hinweis fuer die Installationsreihenfolge

Das Component Directory ist auf VMs in der Regel die erste produktive Komponente. Broker und Endpoints sollten erst danach installiert und registriert werden.

## Kurzfazit

Das Component Directory ist die Verwaltungs- und Vertrauensinstanz des ECP-Netzes. Wenn Komponenten onboardingfaehig, auffindbar und sicher konfigurierbar bleiben sollen, ist diese Komponente betriebsentscheidend.