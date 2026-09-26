# Gateway API Alongside Ingress

All four standalone charts optionally support `instance[].gateway.enabled`. The default is
`false`; existing Ingress installations remain unchanged. This provides
**web routing with HTTPRoute**, not a replacement for AMQP(S) access.

The discontinuation of the **ingress-nginx** community project does not affect the
Kubernetes Ingress API itself or all NGINX products in general. These charts
neither select nor install a replacement controller.

## Responsibilities and Prerequisites

| Platform/operations | These charts |
| --- | --- |
| Gateway API CRDs, Gateway controller and GatewayClass | One `HTTPRoute` per enabled instance |
| Existing Gateway and HTTP/HTTPS listeners | Reference to exactly one Gateway, optionally a listener |
| Public TLS certificates on the HTTPS listener | Hostnames and a `PathPrefix` targeting the regular instance Service |
| CA ConfigMap and backend certificates | For HTTPS, a `BackendTLSPolicy` for the HTTPS Service port |
| DNS, firewall, allowedRoutes and controller operation | No CRDs, Gateways, certificates or ReferenceGrants |

`HTTPRoute` and `BackendTLSPolicy` are rendered as `gateway.networking.k8s.io/v1`.
HTTPS requires Gateway API **>= 1.4.0 Standard Channel**;
CI checks against **v1.4.1**. The selected controller must support HTTPRoute and the
BackendTLSPolicy features used. Installing CRDs alone
does not guarantee support. Check Kubernetes/controller compatibility for the
specific installed Gateway API version separately.

The charts do not query a cluster during rendering. Without installed CRDs,
deployment of enabled Gateway resources fails; when Gateway is disabled,
no Gateway API CRDs are required.

## HTTPS Example per Instance

Copy the **complete instance list** from the relevant chart values and
insert the following snippet into the desired entry. Do not pass it as an isolated
`instance` list: Helm replaces lists rather than merging their elements.
The image, existing configuration Secret, storage and all other required
instance values are still necessary.

```yaml
# Snippet within a complete instance[] configuration
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

The Gateway `shared-web` must exist. Its HTTPS listener `https` terminates
client TLS and references the public certificate for `broker.example.org`.
The Gateway namespace is optional; if omitted, the release namespace is used.
Without `sectionName`, the route attaches to matching listeners on the Gateway.
For a Gateway in another namespace, its `allowedRoutes` must permit the
HTTPRoute's namespace. **No ReferenceGrant is required for this**;
no cross-namespace Service backend reference is created.

The second TLS segment is independent: Gateway -> application.
`backendTLS.hostname` is the backend's SNI/certificate name, without a wildcard.
The existing ConfigMap `backend-ca` resides in the **release namespace** and contains
the PEM CA certificate under `ca.crt`. Do not store private keys here. The certificate chain
and SAN must be correct; insecure disabling of verification is not offered.

As an alternative to `caCertificateRefs`, you can set `wellKnownCACertificates: System`.
Exactly one trust source is allowed. Which system CAs are used
and whether this mode is supported depend on the controller.

The default for `backendProtocol` is `https`, and for `path` it is `/`. The chart reads
the port number from `service.https.port` and creates:

- HTTPRoute `<instance-name>-route` -> Service `<instance-name>-svc`.
- BackendTLSPolicy `<instance-name>-backend-tls` -> the same Service, `sectionName: https`.

The policy covers only the named HTTPS port, not AMQPS or the headless Service.
HTTP is not automatically assumed based on a port number, and no
TLS mode in the external application configuration is changed.

## HTTP Backend After TLS Termination

With `backendProtocol: http`, no BackendTLSPolicy is created. In this case,
`service.http.port` must be configured and the application must actually serve HTTP
there. `backendTLS` must be removed entirely. The segment between
the Gateway and the Pod is **unencrypted** in this mode, even if the client
accesses the Gateway over HTTPS. Use only after explicit network/security approval.

An HTTP Service value only creates Kubernetes port configuration: also align the listener
in the external server/bootstrap files. An existing
HTTPS port remains unchanged; there is no automatic fallback.

## Scope and Limitations

- One Gateway parent, up to 16 hostnames, one `PathPrefix`, and exactly the local
  instance Service as the backend. Optional string annotations for the HTTPRoute.
- No automatic path rewriting, redirects, authentication
  or adoption of controller-specific Ingress annotations. Plan such features
  separately on the Gateway/controller. `path` is only a match, not a rewrite.
- No TCPRoute/TLSRoute, AMQP passthrough or automatic mTLS configuration.
  If ECP requires the original client certificate identity at the backend,
  TLS termination is not a transparent replacement. Coordinate the mTLS/PKI design separately.
- Application URLs, proxy trust, cookies/redirects and the Jolokia origin policy
  must still be checked in the respective application/operational configuration.
- For HA Brokers, passive Pods may remain NotReady. The HTTPRoute uses
  the regular Service and does not change these existing readiness/HA semantics.

## Staged Migration

1. Provision a supported Gateway controller, CRDs, Gateway and TLS.
2. Initially set `gateway.enabled: true` alongside `ingress.enabled: true`.
   Use a separate hostname or controlled DNS resolution for testing;
   existing Ingress annotations are not converted automatically.
3. Check `HTTPRoute.status.parents` for `Accepted=True` and `ResolvedRefs=True`;
   check the Gateway for `Programmed=True` and check the BackendTLSPolicy status.
   Conditions must apply to the current generation, not to earlier changes.
4. Test frontend TLS, backend SNI/CA, login, business requests and failover.
   Valid manifests prove neither certificate validity nor reachability.
5. Switch DNS/traffic in a controlled manner, then set `ingress.enabled: false`.
   Maintain a rollback path; remove the old controller only after migrating all consumers.

## CI and Release

All four standalone charts are tested from source and from the extracted package with Gateway and
Ingress scenarios: HTTP/HTTPS, CA modes, namespace/listener, custom paths,
long names, multiple/disabled instances and invalid configurations.
Kubeconform receives schemas derived from the official v1.4.1 CRDs;
downloads are verified against fixed SHA256 checksums and are not loaded as executable code.
Missing schemas are not ignored. The schema checks are cluster-free; the independent
[Kubernetes validation workflow](../.github/workflows/kubernetes.yml) installs
the verified CRDs and performs API server dry-runs for HTTP and
HTTPS Gateway fixtures. This still does not verify controller support, certificates,
runtime routing, or the admission policies of the target cluster.

Do not overwrite previously published chart versions. Choose a new chart version
before publishing this new feature;
`appVersion` and container tags do not have to change as a result.

## Further Reading

- [Helm operations guide](Helm_Charts.md)
- [Gateway API: HTTP Routing](https://gateway-api.sigs.k8s.io/guides/http-routing/)
- [Gateway API: TLS Configuration](https://gateway-api.sigs.k8s.io/guides/tls/)
- [Migrating from Ingress-NGINX](https://gateway-api.sigs.k8s.io/guides/getting-started/migrating-from-ingress-nginx/)
