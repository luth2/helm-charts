# ECCo SP Base Image

Dieses Base-Image ist als gemeinsamer Startpunkt fuer spaetere ECCo-SP-Komponentenimages gedacht.

## Ziel

Das Image bildet nur die gemeinsamen Voraussetzungen ab:

- UBI Minimal als gemeinsame Red-Hat-nahe Basis
- Java 21 ueber `java-21-openjdk`
- Bash und grundlegende Shell-Werkzeuge
- TLS- und Zertifikatsbasis ueber `ca-certificates` und `openssl`
- keine vorab erzeugten ECCo-SP-Laufzeitverzeichnisse

## Warum nicht Distroless

Die aktuelle ECCo-SP-Struktur erwartet an mehreren Stellen Shell-, Bash- und Startskript-Verhalten. Dazu kommen Tomcat- und Artemis-nahe Konfigurationen. Deshalb ist ein kleines, aber nicht distroless Base-Image fuer den ersten Schritt die robustere Wahl.


## Warum kein Tini mehr

Tini ist ein sehr kleiner Init-Prozess fuer Container. Er kuemmert sich darum, Signale sauber weiterzugeben und beendete Kindprozesse aufzuraeumen.

Fuer dieses erste Base-Image habe ich es wieder entfernt, weil du aktuell nur eine schlanke gemeinsame UBI-Java-Basis willst und die eigentliche Startlogik spaeter komponentspezifisch ueber die RPM-Installation kommen soll.

Wenn spaeter eine Komponente als PID 1 unsauber mit Signalen oder Zombie-Prozessen umgeht, kann Tini immer noch gezielt im finalen Komponentendockerfile wieder aufgenommen werden.

## Java-Sicherheitsanpassung

Nach der Installation wird die Java-Sicherheitskonfiguration angepasst.

Die Datei `java.security` wird unterhalb von `/usr/lib/jvm` gesucht, und folgende Zeile wird ersetzt:

- von `securerandom.source=file:/dev/random`
- auf `securerandom.source=file:/dev/urandom`

Das entspricht genau deiner Vorgabe und vermeidet Blockierungen durch `dev/random`.

## Build-Beispiel

```bash
docker build \
  -t eccosp/base:0.1.0 \
  ./Container/base-image
```

## GitHub- und GHCR-Zuordnung

Im Dockerfile sind OCI-Labels hinterlegt, damit das Image spaeter sauber einem GitHub-Repository zugeordnet werden kann.

Besonders wichtig ist:

- `org.opencontainers.image.source`

Diesen Wert solltest du beim Build auf die echte Repository-URL setzen, zum Beispiel:

```bash
docker build \
  --build-arg IMAGE_SOURCE=https://github.com/ORG/REPO \
  --build-arg IMAGE_URL=https://github.com/ORG/REPO \
  --build-arg IMAGE_DOCUMENTATION=https://github.com/ORG/REPO/tree/main/Container/base-image \
  -t ghcr.io/ORG/REPO/eccosp-base:0.1.0 \
  ./Container/base-image
```

Wenn du spaeter nach GHCR pushst, ist genau diese Kombination aus Image-Name und OCI-Source-Label die saubere Grundlage fuer die Zuordnung zum GitHub-Repository.

## Anpassbare Build-Argumente

- `UBI_BASE_IMAGE` fuer das konkrete UBI-Minimal-Image
- `IMAGE_SOURCE` fuer die GitHub-Repository-URL
- `IMAGE_URL` fuer die Projekt-URL
- `IMAGE_DOCUMENTATION` fuer die Doku-URL
- `IMAGE_VERSION` fuer die fachliche Image-Version

## Wichtiger Hinweis zur Java-Version

Das Image installiert bewusst `java-21-openjdk`, weil das jetzt deine Vorgabe fuer die gemeinsame Basis ist.

Vor produktivem Einsatz solltest du trotzdem noch pruefen, ob die gelieferten ECCo-SP-RPMs exakt mit dieser Java-Variante freigegeben sind.

## Wichtiger Hinweis zu Verzeichnissen

Das Base-Image legt bewusst keine ECCo-SP-spezifischen Laufzeitverzeichnisse an.

Die Annahme ist jetzt:

- RPM-Installation erzeugt die benoetigte Zielstruktur
- komponentenspezifische Dockerfiles uebernehmen nur noch RPM-Installation und Konfigurationsanpassung
- keine kuenstliche Vorstruktur im Base-Image

## Netzwerk- und Firewall-Hinweise

Diese Ports werden nicht im Image geoeffnet, sondern muessen auf VM-, Host-, Netzwerk- oder Kubernetes-Ebene freigegeben werden.

Moegliche ausgehende Datenbankports:

- Oracle Database: 1521
- Microsoft SQL Server: 1433
- MySQL: 3306
- PostgreSQL: 5432

Kommunikation mit anderen ECP-Komponenten:

Default Ports laut Vorgabe:

| Komponente | Inbound | Outbound | Both |
| --- | --- | --- | --- |
| Endpoint | - | - | 8443 |
| Component Directory | 8443 | - | - |
| Broker | 5671, 8161 | - | - |
| Internal Broker | 5672, 8161 | - | 5671* |

`5671*` beim Internal Broker bedeutet in der Praxis den moeglichen Kommunikationspfad zu weiteren ECP-Komponenten oder speziellen Routing-Szenarien. Diese Freigabe ist also keine Image-Eigenschaft, sondern eine Betriebs- und Netzwerkanforderung.

## Empfohlene Weiterentwicklung

Die naechsten Dockerfiles sollten dieses Image als Basis verwenden und anschliessend nur noch komponentspezifisch ergaenzen:

- RPM installieren und nur die benoetigten Anpassungen vornehmen
- benoetigte Konfigurationen und Startkommandos ergaenzen
- Startkommando der jeweiligen Komponente definieren