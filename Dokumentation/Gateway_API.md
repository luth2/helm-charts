# Gateway API neben Ingress

Alle vier Einzelcharts bieten optional `instance[].gateway.enabled`. Standard ist
`false`; bestehende Ingress-Installationen bleiben unveraendert. Es handelt sich
um **Web-Routing mit HTTPRoute**, nicht um einen Ersatz fuer AMQP(S)-Zugaenge.

Die Einstellung zum Community-Projekt **ingress-nginx** betrifft nicht die
Kubernetes-Ingress-API selbst und nicht pauschal alle NGINX-Produkte. Ein anderer
Controller wird durch diese Charts weder ausgewaehlt noch installiert.

## Verantwortung und Voraussetzungen

| Plattform/Betrieb | Diese Charts |
| --- | --- |
| Gateway-API-CRDs, Gateway-Controller und GatewayClass | Eine `HTTPRoute` pro aktivierter Instanz |
| Bestehendes Gateway und HTTP-/HTTPS-Listener | Referenz auf genau ein Gateway, optional einen Listener |
| Oeffentliche TLS-Zertifikate am HTTPS-Listener | Hostnamen und ein `PathPrefix` auf den normalen Instanz-Service |
| CA-ConfigMap und Backend-Zertifikate | Bei HTTPS eine `BackendTLSPolicy` fuer den HTTPS-Service-Port |
| DNS, Firewall, allowedRoutes und Controller-Betrieb | Keine CRDs, Gateways, Zertifikate oder ReferenceGrants |

`HTTPRoute` und `BackendTLSPolicy` werden als `gateway.networking.k8s.io/v1`
gerendert. Fuer HTTPS ist Gateway API **>= 1.4.0 Standard Channel** erforderlich;
die CI prueft gegen **v1.4.1**. Der gewaehlte Controller muss HTTPRoute und die
verwendeten BackendTLSPolicy-Funktionen unterstuetzen. CRD-Installation allein
garantiert keine Unterstuetzung. Kubernetes-/Controller-Kompatibilitaet der
konkret installierten Gateway-API-Version separat pruefen.

Die Charts fragen beim Rendern keinen Cluster ab. Ohne installierte CRDs scheitert
das Deployment aktivierter Gateway-Ressourcen; bei deaktiviertem Gateway sind
keine Gateway-API-CRDs notwendig.

## HTTPS-Beispiel pro Instanz

Die **vollstaendige Instanzliste** aus den jeweiligen Chart-Values uebernehmen und
im gewuenschten Eintrag den folgenden Ausschnitt einsetzen. Nicht als isolierte
`instance`-Liste uebergeben: Helm ersetzt Listen, statt deren Elemente zu mergen.
Image, vorhandenes Konfigurations-Secret, Storage und alle weiteren benoetigten
Instanzwerte bleiben erforderlich.

```yaml
# Ausschnitt innerhalb einer vollstaendigen instance[]-Konfiguration
ingress:
  enabled: false
gateway:
  enabled: true
  parentRefs:
    - name: shared-web
      namespace: networking
      sectionName: https
  hostnames:
    - broker.example.org
  path: /
  backendProtocol: https
  backendTLS:
    hostname: broker.internal.example.org
    caCertificateRefs:
      - group: ""
        kind: ConfigMap
        name: backend-ca
```

Das Gateway `shared-web` muss existieren. Sein HTTPS-Listener `https` terminiert
Client-TLS und referenziert das oeffentliche Zertifikat fuer `broker.example.org`.
Der Gateway-Namespace ist optional; ohne ihn wird der Release-Namespace verwendet.
Ohne `sectionName` erfolgt die Anbindung an passende Listener des Gateways.
Fuer ein Gateway in einem anderen Namespace muss dessen `allowedRoutes` den
Namespace der HTTPRoute zulassen. **Dafuer ist kein ReferenceGrant erforderlich**;
es wird kein namespace-uebergreifender Service-Backend-Verweis erzeugt.

Der zweite TLS-Abschnitt ist unabhaengig davon: Gateway -> Anwendung.
`backendTLS.hostname` ist der SNI-/Zertifikatsname des Backends, ohne Wildcard.
Die vorhandene ConfigMap `backend-ca` liegt im **Release-Namespace** und enthaelt
die PEM-CA unter `ca.crt`. Hier keine privaten Schluessel ablegen. Zertifikatskette
und SAN muessen stimmen; eine unsichere Abschaltung der Pruefung wird nicht angeboten.

Alternativ zu `caCertificateRefs` kann `wellKnownCACertificates: System` gesetzt
werden. Genau eine Vertrauensquelle ist erlaubt. Welche System-CAs verwendet
werden und ob dieser Modus unterstuetzt wird, haengt vom Controller ab.

Standard fuer `backendProtocol` ist `https`, fuer `path` `/`. Das Chart liest
die Portnummer aus `service.https.port` und erzeugt:

- HTTPRoute `<instanzname>-route` -> Service `<instanzname>-svc`.
- BackendTLSPolicy `<instanzname>-backend-tls` -> denselben Service, `sectionName: https`.

Die Policy erfasst nur den benannten HTTPS-Port, nicht AMQPS oder den Headless-Service.
Es wird kein HTTP aufgrund einer Portnummer automatisch angenommen und kein
TLS-Modus in der externen Anwendungs-Konfiguration geaendert.

## HTTP-Backend nach TLS-Terminierung

Mit `backendProtocol: http` wird keine BackendTLSPolicy erzeugt. Dann muss
`service.http.port` konfiguriert sein und die Anwendung dort tatsaechlich HTTP
anbieten. `backendTLS` muss vollstaendig entfernt werden. Der Abschnitt zwischen
Gateway und Pod ist in diesem Modus **unverschluesselt**, auch wenn der Client
das Gateway per HTTPS erreicht. Nur nach bewusster Netzwerk-/Sicherheitsfreigabe nutzen.

Ein HTTP-Service-Value erzeugt lediglich Kubernetes-Portkonfiguration: Den Listener
in den externen Server-/Bootstrap-Dateien ebenfalls abstimmen. Ein vorhandener
HTTPS-Port bleibt unveraendert; es gibt keinen automatischen Fallback.

## Umfang und Grenzen

- Ein Gateway-Parent, bis zu 16 Hostnamen, ein `PathPrefix`, genau der lokale
  Instanz-Service als Backend. Optional String-Annotations fuer die HTTPRoute.
- Kein automatisches Umschreiben des Pfads, kein Redirect, keine Authentifizierung
  und keine Uebernahme controllerspezifischer Ingress-Annotations. Solche Funktionen
  separat am Gateway/Controller planen. `path` ist nur ein Match, kein Rewrite.
- Kein TCPRoute/TLSRoute, kein AMQP-Passthrough und keine automatische mTLS-Konfiguration.
  Benoetigt ECP die urspruengliche Client-Zertifikatsidentitaet am Backend, ist die
  TLS-Terminierung kein transparenter Ersatz. mTLS-/PKI-Konzept separat abstimmen.
- Application-URLs, Proxy-Vertrauen, Cookies/Redirects und Jolokia-Origin-Policy
  bleiben in der jeweiligen Anwendungs-/Betriebskonfiguration zu pruefen.
- Bei HA-Brokern bleiben passive Pods gegebenenfalls NotReady. Die HTTPRoute nutzt
  den normalen Service und aendert diese bestehende Readiness-/HA-Semantik nicht.

## Gestufte Migration

1. Unterstuetzten Gateway-Controller, CRDs, Gateway und TLS bereitstellen.
2. `gateway.enabled: true` zunaechst parallel zu `ingress.enabled: true` setzen.
   Fuer Tests einen separaten Hostnamen oder kontrollierte DNS-Aufloesung nutzen;
   bestehende Ingress-Annotations werden nicht automatisch konvertiert.
3. `HTTPRoute.status.parents` auf `Accepted=True` und `ResolvedRefs=True` pruefen;
   Gateway auf `Programmed=True` sowie BackendTLSPolicy-Status kontrollieren.
   Conditions muessen zur aktuellen Generation gehoeren, nicht zu alten Aenderungen.
4. Frontend-TLS, Backend-SNI/CA, Anmeldung, fachliche Requests und Failover testen.
   Gueltige Manifeste beweisen weder Zertifikatsgueltigkeit noch Erreichbarkeit.
5. DNS/Traffic kontrolliert umstellen, anschliessend `ingress.enabled: false` setzen.
   Rueckweg vorhalten; alten Controller erst nach Migration aller Verbraucher entfernen.

## CI und Release

Alle vier Einzelcharts werden aus Quelle und entpacktem Paket mit Gateway- und
Ingress-Szenarien geprueft: HTTP/HTTPS, CA-Modi, Namespace/Listener, eigene Pfade,
lange Namen, mehrere/deaktivierte Instanzen und ungueltige Konfigurationen.
Kubeconform erhaelt aus den offiziellen v1.4.1-CRDs abgeleitete Schemas; die
Downloads werden per festem SHA256 geprueft und nicht als ausfuehrbarer Code geladen.
Fehlende Schemas werden nicht ignoriert. Die Pruefung ist clusterfrei: Kubernetes-
CEL-Regeln, Controller-Unterstuetzung, Zertifikate und Routing-Laufzeit sind damit
nicht nachgewiesen und muessen im Zielcluster abgenommen werden.

Bereits veroeffentlichte Chart-Versionen nicht ueberschreiben. Vor der
Veroeffentlichung dieser neuen Funktion eine neue Chart-Version waehlen;
`appVersion` und Container-Tags muessen sich dadurch nicht aendern.

## Weiterfuehrend

- [Helm-Betriebsanleitung](Helm_Charts.md)
- [Gateway API: HTTP Routing](https://gateway-api.sigs.k8s.io/guides/http-routing/)
- [Gateway API: TLS-Konfiguration](https://gateway-api.sigs.k8s.io/guides/tls/)
- [Migration von Ingress-NGINX](https://gateway-api.sigs.k8s.io/guides/getting-started/migrating-from-ingress-nginx/)
