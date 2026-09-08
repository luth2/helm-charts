"""Synthetic render cases built from charts/, never from operator values files.

Contract for the current templates: existingSecret is a per-instance string and
is required for enabled instances. Raw defaults without it must fail explicitly.
No Secret objects or real credentials are created by this suite.
"""

from copy import deepcopy
from dataclasses import dataclass
from pathlib import Path
import re

import yaml


CHARTS = ("ecp-endpoint", "ecp-directory", "ecp-broker", "eccosp-artemis")
BROKERS = ("ecp-broker", "eccosp-artemis")
PROBES = ("startupProbe", "readinessProbe", "livenessProbe")
SECRET = "review-credentials"
SENSITIVE = {
    "ecp-endpoint": {
        "ecp.properties", "ecp-users.properties", "ecp-password.properties",
        "jmxremote.password", "jmxremote.ssl", "server.xml", "users.properties",
    },
    "ecp-directory": {
        "ecp-directory.properties", "ecp-users.properties", "ecp-password.properties",
        "jmxremote.password", "jmxremote.ssl", "server.xml",
    },
    "ecp-broker": {
        "broker.properties", "broker.xml", "broker-master.xml", "broker-slave.xml",
        "bootstrap.xml", "artemis-users.properties",
    },
    "eccosp-artemis": {
        "broker.xml", "broker-master.xml", "broker-slave.xml", "bootstrap.xml",
        "artemis-users.properties",
    },
}


def read_yaml(path):
    with Path(path).open(encoding="utf-8") as stream:
        return yaml.safe_load(stream) or {}


def merge(base, override):
    """Helm-style map merge; lists replace, never mutate either input."""
    result = deepcopy(base)
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(result.get(key), dict):
            result[key] = merge(result[key], value)
        else:
            result[key] = deepcopy(value)
    return result


def synthetic(value):
    """Replace sample credential scalars while preserving the instance shape."""
    if isinstance(value, list):
        return [synthetic(item) for item in value]
    if isinstance(value, dict):
        return {
            key: (
                "ci-not-a-credential"
                if isinstance(item, str) and re.search(
                    r"password|csrfsecret|encryptor.*key", key, re.IGNORECASE
                )
                else synthetic(item)
            )
            for key, item in value.items()
        }
    return value


@dataclass
class Case:
    name: str
    values: dict
    release: str = "review"
    namespace: str = "review-namespace"
    reject: str | None = None
    schema_reject: bool = False
    schema_keyword: str | None = None


def components(root, target, overrides):
    """Effective per-chart values, including umbrella conditions and globals."""
    if target != "ecco-sp":
        return {target: merge(read_yaml(root / "charts" / target / "values.yaml"), overrides)}
    umbrella = merge(read_yaml(root / "ecco-sp" / "values.yaml"), overrides)
    result = {}
    for chart in CHARTS:
        child = merge(read_yaml(root / "charts" / chart / "values.yaml"), umbrella.get(chart, {}))
        if child.get("enabled", True):
            child["global"] = merge(child.get("global", {}), umbrella.get("global", {}))
            result[chart] = child
    return result


def enabled_instances(values):
    return [item for item in values.get("instance", []) if item.get("enabled", True)]


def secret_keys(chart, item):
    """Full external files, not individual passwords; mirror workload items."""
    if chart in BROKERS:
        keys = {"artemis-users.properties"}
        if chart == "ecp-broker":
            keys.add("broker.properties")
        keys.update({"broker-master.xml", "broker-slave.xml"}
                    if item.get("replicaCount", 1) > 1 else {"broker.xml"})
        service = item.get("service", {})
        if service.get("http") or service.get("https"):
            keys.add("bootstrap.xml")
    else:
        keys = {"ecp-users.properties", "ecp-password.properties", "server.xml"}
        keys.update({"ecp.properties", "users.properties"} if chart == "ecp-endpoint"
                    else {"ecp-directory.properties"})
        if item.get("jmxRemoteProperties"):
            keys.update({"jmxremote.password", "jmxremote.ssl"})
    return keys


def external_db(chart, item):
    key = "ecpProperties" if chart == "ecp-endpoint" else "ecpDirectoryProperties"
    item.setdefault(key, {}).update({
        "springProfilesActive": "ecp-ha, console-logging",
        "springDatasourceDriverClassName": "org.postgresql.Driver",
        "ecpDBUrl": "jdbc:postgresql://database.example.invalid:5432/review",
        "ecpDBHostname": "database.example.invalid",
        "ecpDBName": "review",
        "ecpDBUsername": "review",
        "ecpDBPassword": "ci-not-a-credential",
    })


def fixtures(root, target):
    charts = CHARTS if target == "ecco-sp" else (target,)
    baseline = {}
    for chart in charts:
        values = synthetic(read_yaml(root / "charts" / chart / "values.yaml"))
        if not values.get("instance"):
            raise ValueError(f"{chart}: a sample instance is required to generate fixtures")
        # Copy the complete first instance: replacing Helm lists by hand loses defaults.
        item = deepcopy(values["instance"][0])
        item.update(name="review-one", enabled=True, existingSecret=SECRET)
        values["instance"] = [item]
        values["enabled"] = True
        baseline[chart] = values
    base = baseline if target == "ecco-sp" else baseline[target]
    if target == "ecco-sp":
        base["global"] = {"storage": {"class": ""}}

    def edit(name, change):
        value = deepcopy(base)
        for chart in charts:
            child = value[chart] if target == "ecco-sp" else value
            change(chart, child, child["instance"][0])
        return Case(name, value)

    result = [Case("existing-secret", deepcopy(base))]

    def probes_off(chart, values, item):
        for probe in PROBES:
            item[probe] = {"enabled": False}
        # Exercise the old truthy-map bug even when an external DB is configured.
        if chart not in BROKERS:
            external_db(chart, item)

    result.append(edit("probes-disabled", probes_off))
    result.append(edit("startup-disabled", lambda c, v, i: i.update(startupProbe={"enabled": False})))

    def probe_defaults(chart, values, item):
        for probe in PROBES:
            item.pop(probe, None)

    result.append(edit("probe-defaults", probe_defaults))
    result.append(edit("probe-empty-maps", lambda c, v, i: i.update({p: {} for p in PROBES})))
    # Public Values expose only enabled; exercise default timings for all probes,
    # including liveness, which is off in the shipped defaults.
    result.append(edit("probes-enabled-only", lambda c, v, i: i.update({
        p: {"enabled": True} for p in PROBES
    })))

    def probes_on(chart, values, item):
        for probe in PROBES:
            item[probe] = {"enabled": True, "initialDelaySeconds": 7, "periodSeconds": 11,
                           "timeoutSeconds": 4, "failureThreshold": 9, "successThreshold": 1}
        if chart not in BROKERS:
            external_db(chart, item)

    result.append(edit("probes-custom-delays", probes_on))
    result.append(edit("probes-zero-delay", lambda c, v, i: i.update({
        p: {"enabled": True, "initialDelaySeconds": 0} for p in PROBES
    })))
    result.append(edit("replicas-zero", lambda c, v, i: i.update(replicaCount=0)))
    result.append(edit("all-instances-disabled", lambda c, v, i: i.update(enabled=False, existingSecret="")))
    result.append(edit("instance-enabled-default", lambda c, v, i: i.pop("enabled", None)))
    result.append(edit("fullname-override", lambda c, v, i: i.update(fullnameOverride=f"fixed-{c}")))

    def long_names(chart, values, item):
        item["name"] = "instance-" + "x" * 53 + "a"
        second = deepcopy(item)
        second["name"] = item["name"][:-1] + "b"
        values["instance"].append(second)

    long_case = edit("long-release-and-instances", long_names)
    long_case.release = "release-" + "r" * 45  # Helm release maximum: 53.
    result.append(long_case)

    def public_scalars(chart, values, item):
        # Sensitive configuration is external: exercise false/0 inputs without
        # pretending to inspect broker XML or application properties in a Secret.
        if chart in BROKERS:
            broker = item.setdefault("brokerXml", {})
            broker.setdefault("journal", {}).update(persistenceEnabled=False, bufferTimeout=0)
            broker.setdefault("default", {}).update(ecpCacheDisabled=False, ecpCacheReloadInterval=0)
        else:
            key = "ecpProperties" if chart == "ecp-endpoint" else "ecpDirectoryProperties"
            item.setdefault(key, {}).update(ecpAutomaticUpdateEnabled=False, ecpMetricsSyncThreshold=0)
            item.setdefault("jmxRemoteProperties", {})["comSunManagementJmxRemoteAuthenticate"] = False
        # Public custom file must preserve the literal false/0, not lose data
        # through a truthy default. All ConfigMap data remains string-valued.
        item.setdefault("configMap", []).append({
            "subPath": "review-scalars.properties", "content": "feature.enabled=false\nretry.count=0",
        })

    result.append(edit("config-false-and-zero", public_scalars))

    if any(chart not in BROKERS for chart in charts):
        result.append(edit("no-log-persistence", lambda c, v, i: i.update(keepLogsAfterRestart=False)
                           if c not in BROKERS else None))
        for enabled in (False, True):
            def session_env(chart, values, item):
                if chart not in BROKERS:
                    item.update(sessionReplication=enabled, env=[
                        {"name": "REVIEW_CUSTOM", "value": "false-0"},
                        {"name": "REVIEW_POD", "valueFrom": {"fieldRef": {"fieldPath": "metadata.name"}}},
                    ])
            result.append(edit(f"session-{str(enabled).lower()}-custom-env", session_env))

    def multiple(chart, values, item):
        second = deepcopy(item)
        second["name"] = "review-two"
        disabled = deepcopy(item)
        disabled.update(name="review-disabled", enabled=False, existingSecret="")
        values["instance"] += [second, disabled]

    result.append(edit("multiple-instances", multiple))
    result.append(Case("custom-release", deepcopy(base), release="canary"))
    result.append(Case("custom-namespace", deepcopy(base), namespace="tenant-canary"))

    def ingress(chart, values, item):
        item["ingress"] = {
            "enabled": True, "host": f"{chart}.example.invalid", "contextPath": "/",
            "ingressClassName": "review-ingress", "tls": {"secretName": "review-tls"},
        }

    result.append(edit("ingress", ingress))

    def gateway(chart, values, item):
        # Keep HTTPS present even for HTTP fixtures: probe selection must not change.
        item.setdefault("service", {}).setdefault("https", {"port": 8443})
        item["gateway"] = {
            "enabled": True,
            "parentRefs": [{"name": "review-gateway"}],
            "hostnames": [f"{chart}.example.invalid"],
            "backendTLS": {
                "hostname": f"{chart}.backend.example.invalid",
                "caCertificateRefs": [{"group": "", "kind": "ConfigMap", "name": "review-ca"}],
            },
        }

    def gateway_case(name, change=None):
        def configure(chart, values, item):
            gateway(chart, values, item)
            if change:
                change(chart, values, item)
        return edit(name, configure)

    result.append(gateway_case("gateway-https"))  # Protocol and path deliberately absent.
    result.append(gateway_case("gateway-system-ca", lambda c, v, i: i["gateway"].update(
        backendProtocol="https", backendTLS={"hostname": f"{c}.backend.example.invalid",
                                             "wellKnownCACertificates": "System"})))

    def gateway_http(chart, values, item):
        item["gateway"]["backendProtocol"] = "http"
        item["gateway"].pop("backendTLS")
        item["service"]["http"] = {"port": 18080}

    result.append(gateway_case("gateway-http", gateway_http))

    def gateway_custom(chart, values, item):
        item["gateway"].update(
            path="/console/api", hostnames=[f"{chart}.example.invalid", f"*.{chart}.example.invalid"],
            parentRefs=[{"name": "shared-gateway", "namespace": "networking", "sectionName": "web",
                         "group": "gateway.networking.k8s.io", "kind": "Gateway"}],
            annotations={"review.example.invalid/owner": "chart-ci", "review.example.invalid/flag": "false"},
        )
        item["service"]["https"]["port"] = 18443

    custom = gateway_case("gateway-custom", gateway_custom)
    custom.namespace = "tenant-gateway"
    result.append(custom)
    result.append(gateway_case("gateway-ingress-migration", ingress))

    def gateway_multiple(chart, values, item):
        long_names(chart, values, item)
        values["instance"][1]["gateway"]["hostnames"] = [f"second.{chart}.example.invalid"]
        fixed = deepcopy(item)
        fixed.update(name="fixed-instance", fullnameOverride=f"fixed-{chart}")
        fixed["gateway"]["hostnames"] = [f"fixed.{chart}.example.invalid"]
        disabled = deepcopy(item)
        disabled.update(name="disabled-instance", enabled=False, existingSecret="")
        disabled["gateway"]["hostnames"] = [f"disabled.{chart}.example.invalid"]
        values["instance"] += [fixed, disabled]

    multiple_gateway = gateway_case("gateway-multiple-instances", gateway_multiple)
    multiple_gateway.release = "release-" + "r" * 45
    result.append(multiple_gateway)
    result.append(gateway_case("gateway-disabled", lambda c, v, i: i["gateway"].update(enabled=False)))
    result.append(gateway_case("gateway-instance-disabled", lambda c, v, i: i.update(enabled=False, existingSecret="")))

    # Each negative changes exactly one chart, so unrelated schema errors cannot hide.
    invalid_gateway = (
        ("absent-parent", lambda g: g.pop("parentRefs"), "required", r"gateway.*parentRefs"),
        ("empty-parent", lambda g: g.update(parentRefs=[]), "minItems", r"gateway.*parentRefs"),
        ("multiple-parents", lambda g: g["parentRefs"].append({"name": "other"}), "maxItems", r"gateway.*parentRefs"),
        ("parent-name", lambda g: g["parentRefs"][0].pop("name"), "required", r"gateway.*parentRefs.*name"),
        ("parent-kind", lambda g: g["parentRefs"][0].update(kind="Service"), "const", r"gateway.*parentRefs.*kind"),
        ("parent-group", lambda g: g["parentRefs"][0].update(group=""), "const", r"gateway.*parentRefs.*group"),
        ("absent-host", lambda g: g.pop("hostnames"), "required", r"gateway.*hostnames"),
        ("empty-host", lambda g: g.update(hostnames=[]), "minItems", r"gateway.*hostnames"),
        ("absent-tls", lambda g: g.pop("backendTLS"), "required", r"gateway.*backendTLS"),
        ("tls-hostname", lambda g: g["backendTLS"].pop("hostname"), "required", r"gateway.*backendTLS.*hostname"),
        ("tls-trust", lambda g: g["backendTLS"].pop("caCertificateRefs"), "oneOf", r"gateway.*backendTLS"),
        ("tls-dual-trust", lambda g: g["backendTLS"].update(wellKnownCACertificates="System"), "oneOf", r"gateway.*backendTLS"),
        ("tls-wildcard", lambda g: g["backendTLS"].update(hostname="*.example.invalid"), "pattern", r"gateway.*backendTLS.*hostname"),
        ("tls-ca-kind", lambda g: g["backendTLS"]["caCertificateRefs"][0].update(kind="Secret"), "const", r"gateway.*caCertificateRefs.*kind"),
        ("tls-ca-group", lambda g: g["backendTLS"]["caCertificateRefs"][0].update(group="other"), "const", r"gateway.*caCertificateRefs.*group"),
        ("tls-ca-name", lambda g: g["backendTLS"]["caCertificateRefs"][0].pop("name"), "required", r"gateway.*caCertificateRefs.*name"),
        ("tls-empty-ca", lambda g: g["backendTLS"].update(caCertificateRefs=[]), "minItems", r"gateway.*caCertificateRefs"),
        ("tls-multiple-ca", lambda g: g["backendTLS"]["caCertificateRefs"].append({"group": "", "kind": "ConfigMap", "name": "other-ca"}), "maxItems", r"gateway.*caCertificateRefs"),
        ("tls-system", lambda g: g.update(backendTLS={"hostname": "backend.example.invalid", "wellKnownCACertificates": "Other"}), "const", r"gateway.*wellKnownCACertificates"),
        ("http-tls", lambda g: g.update(backendProtocol="http"), "not", r"gateway"),
        ("protocol", lambda g: g.update(backendProtocol="tcp"), "enum", r"gateway.*backendProtocol"),
        ("path", lambda g: g.update(path="no-leading-slash"), "pattern", r"gateway.*path"),
    )
    for chart in charts:
        for suffix, mutate, keyword, reason in invalid_gateway:
            case = gateway_case(f"{chart}-reject-gateway-{suffix}")
            child = case.values[chart] if target == "ecco-sp" else case.values
            mutate(child["instance"][0]["gateway"])
            case.reject, case.schema_reject, case.schema_keyword = reason, True, keyword
            result.append(case)
        for protocol in ("http", "https"):
            case = gateway_case(f"{chart}-reject-gateway-missing-{protocol}-port")
            child = case.values[chart] if target == "ecco-sp" else case.values
            item = child["instance"][0]
            if protocol == "http":
                gateway_http(chart, child, item)
            else:
                item["service"]["http"] = {"port": 18080}
            # Removing the selected map keeps values schema-valid. The template
            # helper must reject the absent selected port, not a Service schema.
            item["service"].pop(protocol)
            case.reject = rf"gateway.backendProtocol={protocol} requires service\.{protocol}\.port"
            result.append(case)

    def ha(chart, values, item):
        item["replicaCount"] = 2
        if chart in BROKERS:
            item.update(
                useSharedStorageForJournal=True, useSharedStorageForConfiguration=False,
                sharedStorageClassJournal="review-rwx", sharedStorageSizeJournal="100Mi",
                sharedStorageAccessMode="ReadWriteMany",
            )
        else:
            external_db(chart, item)

    result.append(edit("ha-valid", ha))

    def storage(chart, values, item):
        values.setdefault("global", {}).setdefault("storage", {})["class"] = "review-rwo"

    explicit_storage = edit("explicit-storage-class", storage)
    if target == "ecco-sp":
        explicit_storage.values["global"]["storage"]["class"] = "review-rwo"
    result.append(explicit_storage)

    for chart in charts:
        for collision in ("name", "fullnameOverride"):
            values = deepcopy(base)
            child = values[chart] if target == "ecco-sp" else values
            second = deepcopy(child["instance"][0])
            if collision == "fullnameOverride":
                child["instance"][0][collision] = second[collision] = "duplicate-resource"
                second["name"] = "different-instance"
            child["instance"].append(second)
            result.append(Case(f"{chart}-reject-duplicate-{collision}", values,
                               reject=r"duplicate instance[. ](name|resource name)"))
        if chart not in BROKERS:
            case = edit(f"{chart}-external-db", lambda c, v, i: external_db(c, i) if c == chart else None)
            result.append(case)
        invalid = deepcopy(base)
        item = (invalid[chart] if target == "ecco-sp" else invalid)["instance"][0]
        item["replicaCount"] = 2
        if chart in BROKERS:
            item["useSharedStorageForJournal"] = False
            reject = r"useSharedStorageForJournal|shared.*journal|journal.*shared"
        else:
            key = "ecpProperties" if chart == "ecp-endpoint" else "ecpDirectoryProperties"
            props = item.setdefault(key, {})
            for field in ("springDatasourceDriverClassName", "ecpDBUrl", "ecpDBHostname"):
                props.pop(field, None)
            props["springProfilesActive"] = "ecp-nonha, console-logging"
            reject = r"external.*(database|db)|ecp-ha|springDatasourceDriverClassName"
        result.append(Case(f"{chart}-reject-invalid-ha", invalid, reject=reject))
        if chart in BROKERS:
            valid = next(case for case in result if case.name == "ha-valid")
            for field, bad, reason in (
                ("sharedStorageAccessMode", "ReadWriteOnce", r"ReadWriteMany|sharedStorageAccessMode"),
                ("sharedStorageClassJournal", "", r"sharedStorageClassJournal|storage.class"),
                ("useSharedStorageForConfiguration", True, r"useSharedStorageForConfiguration|shared.*configuration"),
            ):
                values = deepcopy(valid.values)
                child = values[chart] if target == "ecco-sp" else values
                child["instance"][0][field] = bad
                result.append(Case(f"{chart}-reject-{field.lower()}", values, reject=reason))

    if target == "ecco-sp":
        result.append(Case("all-dependencies-disabled", {c: {"enabled": False} for c in CHARTS}))
        for selected in CHARTS:
            values = deepcopy(base)
            for chart in CHARTS:
                values[chart]["enabled"] = chart == selected
            result.append(Case(f"only-{selected}", values))
    return result