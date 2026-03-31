# ECCo SP Komponenten-Dokumentation

Diese Ablage fasst die offizielle ECCo SP Dokumentation für die im Repository verwalteten Helm-Charts kompakt zusammen.

Offizielle Doku-Startseite:

- [ECCo SP Documents](https://eccosp-docs.entsoe.eu/k)

Komponenten in diesem Repository:

| Komponente | Repo-Chart | Zusammenfassung | Offizielle Quelle |
| --- | --- | --- | --- |
| Endpoint | `charts/ecp-endpoint` | [Endpoint](./Endpoint.md) | [Endpoint Manual](https://eccosp-docs.entsoe.eu/s/ecco-sp/m/endpoint-manual) |
| Interner Broker | `charts/eccosp-artemis` | [Interner Broker](./Interner_Broker.md) | [Internal Broker Manual](https://eccosp-docs.entsoe.eu/s/ecco-sp/m/internal-broker-manual) |
| Broker | `charts/ecp-broker` | [Broker](./Broker.md) | [Broker Manual](https://eccosp-docs.entsoe.eu/s/ecco-sp/m/broker-manual) |
| Component Directory | `charts/ecp-directory` | [Component Directory](./Component_Directory.md) | [Component Directory Manual](https://eccosp-docs.entsoe.eu/s/ecco-sp/m/component-directory-manual) |

Stand der Zusammenfassung: 31.03.2026.

Weitere technische Notizen:

- [Artifact Registry Empfehlung](./Artifact_Registry_Empfehlung.md)

## Empfohlene Reihenfolge auf VMs

Wenn die Komponenten klassisch auf VMs installiert werden, ist diese Reihenfolge fachlich und betrieblich sinnvoll:

1. Component Directory
2. Broker
3. Interner Broker
4. Endpoint

Begründung:

- Das Component Directory ist die Vertrauens- und Registrierungsinstanz.
- Der Broker benötigt das Component Directory für Registrierung und Synchronisation.
- Der interne Broker muss stehen, bevor ein Endpoint intern Nachrichten verarbeiten kann.
- Der Endpoint sollte erst zuletzt installiert und registriert werden, wenn die abhängigen Dienste bereits erreichbar sind.

## Ableitung für eigene Container-Builds

Wenn du die Container später selbst bauen willst, ist die VM-Sicht hilfreich, weil sie die eigentliche Laufzeitstruktur zeigt:

- Binärartefakte und Startskripte liegen in den Installationsverzeichnissen der Komponente.
- Konfiguration, Keystores und Benutzerdateien müssen sauber vom Image entkoppelt werden.
- Persistente Daten, Journale und Logs sollten als getrennte Verzeichnisse oder Volumes geplant werden.
- Zertifikate und registrierungsbezogene Keystores sollten nie fest ins Image gebaut werden.