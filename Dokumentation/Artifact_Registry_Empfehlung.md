# Artifact Registry Empfehlung

## Ziel

Fuer ECCo SP brauchst du mittelfristig nicht nur eine Container-Registry, sondern einen Ort fuer mehrere Artefaktarten:

- RPM-Pakete der Herstellerkomponenten
- generische Dateien wie ZIP, TAR, Konfigurationsvorlagen und Keystores
- spaetere OCI-Images fuer die selbst gebauten Container

## Kurzempfehlung

Wenn du eine freie oder sehr kostenguenstige SaaS-Loesung suchst, ist Cloudsmith fuer den schnellen Start die pragmatischste Option.

Wenn du eine Azure-nahe Enterprise-Loesung mit sauberer Perspektive fuer spaetere Skalierung und Governance willst, ist JFrog Artifactory SaaS auf Azure die bessere Wahl.

Azure Artifacts allein ist fuer diesen Anwendungsfall nicht ausreichend, weil du damit nicht sauber alle benoetigten Artefaktarten, insbesondere RPM und generische Herstellerpakete, in einem konsistenten Modell abbildest.

## Bewertete Optionen

### Option 1: Cloudsmith als freie SaaS-Variante

Geeignet, wenn du schnell starten willst und moeglichst wenig Betriebsaufwand haben moechtest.

Vorteile:

- SaaS ohne eigene Plattformpflege
- gut fuer RPM, Generic Files und OCI-Images geeignet
- einfacher Einstieg fuer kleine Teams und erste Prototypen
- schnell fuer Build-Pipelines nutzbar

Nachteile:

- Free- oder Community-Modelle haben ueblicherweise Limits bei Storage, Traffic oder Retention
- weniger Azure-zentrierte Governance als eine dedizierte Enterprise-Loesung
- spaetere Migration in groessere Betriebsmodelle kann notwendig werden

Empfehlung:

- gut fuer den Proof of Concept und den Start mit eigenen Images
- gut, wenn du zuerst RPMs, generische Dateien und OCI in einem SaaS-Dienst unterbringen willst

### Option 2: JFrog Artifactory SaaS auf Azure

Geeignet, wenn du eine langfristige Zielplattform mit Azure-Naehe willst.

Vorteile:

- einheitliche Plattform fuer RPM, Generic, Maven und OCI
- gute Trennung von lokalen, Remote- und Virtual-Repositories
- solide Basis fuer Build Promotion, Security Scans und Governance
- passt gut in Azure-zentrierte Delivery-Pipelines

Nachteile:

- hoeherer organisatorischer und finanzieller Aufwand als bei einem schlanken SaaS-Start
- fuer einen kleinen Prototypen oft mehr Plattform als unmittelbar noetig

Empfehlung:

- beste Zielarchitektur, wenn du Azure ohnehin als zentrale Plattform verwendest
- besonders sinnvoll, wenn spaeter mehrere Teams, Promotion-Stufen und zentrale Freigabeprozesse dazu kommen

### Option 3: Azure-native Bausteine ohne echtes Artifactory

Moeglicher Aufbau waere etwa:

- Azure Container Registry fuer OCI-Images
- Blob Storage oder statisches Repo fuer RPM-Dateien
- optional Azure Artifacts fuer paketorientierte Entwicklerartefakte

Das ist technisch machbar, aber fuer ECCo SP unguenstig, weil du die Artefakte ueber mehrere Dienste verteilst und kein einheitliches Repository-Modell fuer RPM, Generic und OCI bekommst.

Empfehlung:

- nicht die erste Wahl fuer deinen Fall
- nur sinnvoll, wenn Artifactory organisatorisch ausgeschlossen ist und OCI der Hauptfokus bleibt

## Empfohlene Repository-Struktur

Unabhaengig vom Produkt solltest du die Artefakte logisch trennen:

1. `eccosp-rpm-local` fuer originale Hersteller-RPMs
2. `eccosp-generic-local` fuer entpackte Zusatzdateien, Templates, Skripte und Dokumente
3. `eccosp-docker-local` oder OCI-Repo fuer die finalen Images
4. optional `eccosp-maven-local`, falls spaeter einzelne Java-Artefakte separat gebaut oder gespiegelt werden

## Empfohlener Ablauf

1. Herstellerpakete und Zusatzdateien in die Registry laden
2. Base-Image gegen diese Artefakte bauen
3. Komponentenspezifische Images vom Base-Image ableiten
4. Images in das OCI-Repository pushen
5. Deployment nur noch ueber versionierte Images und externe Laufzeitkonfiguration durchfuehren

## Konkrete Entscheidung

Wenn du heute starten willst:

- nimm Cloudsmith, wenn niedriges Setup und geringe Einstiegshuerde wichtiger sind als maximale Plattformtiefe
- nimm JFrog Artifactory SaaS auf Azure, wenn du direkt auf eine langfristige Azure-Zielplattform gehen willst

Fuer dein Vorhaben mit RPM, generischen Herstellerdateien und spaeteren Container-Images ist JFrog auf Azure die robustere Zielarchitektur. Wenn du zunaechst kostenschonend und schnell experimentieren willst, ist Cloudsmith der bessere Startpunkt.