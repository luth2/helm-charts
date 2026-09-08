"""Structural assertions only; no claim about image, shell or cluster behavior."""

from hashlib import sha256
import re
from xml.etree import ElementTree

import yaml

from chart_fixtures import BROKERS, PROBES, SECRET, SENSITIVE, enabled_instances, secret_keys


class UniqueKeyLoader(yaml.SafeLoader):
    """Do not silently accept overwritten YAML mapping keys."""


def unique_mapping(loader, node, deep=False):
    loader.flatten_mapping(node)
    mapping = {}
    for key_node, value_node in node.value:
        key = loader.construct_object(key_node, deep=deep)
        if key in mapping:
            raise ValueError(f"Duplicate YAML mapping key: {key} (rendered line {key_node.start_mark.line + 1}); "
                             "check YAML document separators and template whitespace trimming")
        mapping[key] = loader.construct_object(value_node, deep=deep)
    return mapping


UniqueKeyLoader.add_constructor(yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, unique_mapping)


def require(condition, message):
    if not condition:
        raise ValueError(message)


def documents(text):
    return [doc for doc in yaml.load_all(text, Loader=UniqueKeyLoader) if doc is not None]


def selected(selector, labels):
    return bool(selector) and all(labels.get(key) == value for key, value in selector.items())


def instance_name(release, chart, item):
    """Match instanceName: 45 chars, trunc 34/trimSuffix + SHA256[:10]."""
    base = item.get("fullnameOverride") or f"{release}-{chart}-{item['name']}"
    if len(base) > 45:
        return f"{base[:34].removesuffix('-')}-{sha256(base.encode()).hexdigest()[:10]}"
    return base


def credential_key(key):
    # File paths and algorithm switches are public, password values are not.
    normalized = re.sub(r"[^a-z0-9]", "", key.lower())
    if normalized == "maskpassword":
        return False
    return bool(re.search(r"(?:password|passwd|secret)$|(?:encryptor|sensitiveStringCodec)key$",
                          normalized, re.IGNORECASE))


def check_public_file(filename, content):
    """Inspect actual public data, never template comments or external files.

    This is a targeted literal-credential check, not a general secret scanner.
    XML parsing only proves well-formedness, not application schema validity.
    """
    def check(key, value):
        value = str(value).strip().strip("\"'")
        reference = re.fullmatch(r"\$\{[^{}]+\}|\$[A-Za-z_][A-Za-z0-9_]*", value)
        require(not (credential_key(key) and value and not reference),
                f"Static credential value in public configuration: {filename}/{key}")

    if filename.lower().endswith(".xml"):
        try:
            root = ElementTree.fromstring(content)
        except ElementTree.ParseError as error:
            raise ValueError(f"Malformed public XML: {filename}") from error
        for element in root.iter():
            check(element.tag.rsplit("}", 1)[-1], element.text or "")
            for key, value in element.attrib.items():
                check(key, value)
            if "value" in element.attrib:
                check(element.get("name", element.get("key", "")), element.attrib["value"])
    else:
        # Anchored assignments and JVM -D options; skip whole comment lines.
        for line in content.splitlines():
            if line.lstrip().startswith(("#", "!", ";")):
                continue
            assignment = re.match(r"^\s*(?:export\s+)?([\w.-]+)\s*[:=]\s*(.*?)\s*$", line)
            if assignment:
                check(*assignment.groups())
            for key, value in re.findall(r"-D([\w.-]+)=([^\s\\\"']+)", line):
                check(key, value)


def volume_keys(volume, configmaps, sensitive, existing_secret):
    """Resolve projected paths, including Secret keys that exist outside this render.

    Secret content/existence is intentionally not checked. Explicit items must
    match the workload's full-file key contract; no implicit all-keys mounts.
    """
    sources = volume.get("projected", {}).get("sources", [volume])
    keys = set()
    secrets = set()
    config_backed = False
    for source in sources:
        if "configMap" in source:
            config_backed = True
            reference = source["configMap"]
            name = reference["name"]
            require(name in configmaps, f"Missing ConfigMap: {name}")
            data = configmaps[name].get("data", {})
            if "items" in reference:
                for item in reference["items"]:
                    require(item["key"] in data, f"Missing ConfigMap key: {name}/{item['key']}")
                    require(item["path"] not in keys, "Duplicate projected configuration path")
                    keys.add(item["path"])
            else:
                require(not keys.intersection(data), "Colliding projected ConfigMap keys")
                keys.update(data)
        if "secret" in source:
            config_backed = True
            reference = source["secret"]
            name = reference.get("secretName", reference.get("name"))
            require(name == existing_secret == SECRET, "Unexpected configuration Secret reference")
            secrets.add(name)
            items = reference.get("items")
            require(isinstance(items, list) and bool(items), "Secret requires explicit items contract")
            require(reference.get("optional", False) is False, "Configuration Secret must not be optional")
            require(all(item.get("key") == item.get("path") for item in items), "Secret key/path contract mismatch")
            paths = {item["path"] for item in items}
            require(len(paths) == len(items), "Duplicate Secret projection keys")
            require(paths == sensitive, "Secret items do not match required file-key contract")
            require(not keys.intersection(paths), "Colliding ConfigMap/Secret projection keys")
            keys.update(paths)
    return (keys if config_backed else None), secrets


def validate_manifest(text, case, effective):
    docs = documents(text)
    resources = {}
    for doc in docs:
        require(isinstance(doc, dict), "Manifest document must be a mapping")
        kind = doc.get("kind")
        metadata = doc.get("metadata", {})
        name = metadata.get("name", "")
        namespace = metadata.get("namespace", case.namespace)
        require(namespace == case.namespace, f"Wrong namespace on {kind}/{name}")
        require(len(name) <= 63 and re.fullmatch(r"[a-z0-9](?:[-a-z0-9]*[a-z0-9])?", name),
                f"Unsafe Kubernetes resource name: {kind}/{name}")
        key = (kind, namespace, name)
        require(key not in resources, f"Duplicate resource: {key}")
        resources[key] = doc
        require(kind != "Secret", "existingSecret mode must not emit Secret resources")

    def by_kind(kind):
        return {doc["metadata"]["name"]: doc for doc in docs if doc["kind"] == kind}

    workloads = by_kind("StatefulSet")
    services = by_kind("Service")
    configmaps = by_kind("ConfigMap")
    claims = by_kind("PersistentVolumeClaim")
    ingresses = by_kind("Ingress")
    for chart, values in effective.items():
        instances = values.get("instance", [])
        require(len({item["name"] for item in instances}) == len(instances), "Duplicate instance.name")
        names = [instance_name(case.release, chart, item) for item in instances]
        require(len(set(names)) == len(names), "Duplicate instance resource name")
    expected = {
        instance_name(case.release, chart, item): (chart, values, item)
        for chart, values in effective.items()
        for item in enabled_instances(values)
    }
    require(len(expected) == sum(len(enabled_instances(v)) for v in effective.values()),
            "Duplicate cross-chart resource name")
    require(set(workloads) == set(expected), "Missing, extra or incorrectly named StatefulSets")
    if not expected:
        require(not docs, "Disabled components must not emit resources")
        return docs
    for doc in docs:
        name = doc["metadata"]["name"]
        require(any(name == prefix or name.startswith(prefix + "-") for prefix in expected),
                f"Resource does not match instance naming helper: {name}")

    for name, configmap in configmaps.items():
        owners = [prefix for prefix in expected if name.startswith(prefix + "-")]
        require(len(owners) == 1, f"Orphan/ambiguous ConfigMap: {name}")
        chart = expected[owners[0]][0]
        require(not SENSITIVE[chart].intersection(configmap.get("data", {})),
                f"Sensitive file keys leaked into ConfigMap: {name}")
        require(all(isinstance(value, str) for value in configmap.get("data", {}).values()),
                f"Non-string ConfigMap data: {name}")
        require(not configmap.get("binaryData"), f"Unexpected binary public configuration: {name}")
        for filename, content in configmap.get("data", {}).items():
            check_public_file(filename, content)
        item = expected[owners[0]][2]
        for extra in item.get("configMap", []):
            if extra["subPath"] not in SENSITIVE[chart]:
                require(configmap["data"].get(extra["subPath"]) == extra["content"].rstrip("\n"),
                        f"Custom public configuration lost: {extra['subPath']}")
        if chart not in BROKERS and item.get("jmxRemoteProperties"):
            authenticate = item["jmxRemoteProperties"].get("comSunManagementJmxRemoteAuthenticate")
            if isinstance(authenticate, bool):
                require(f"com.sun.management.jmxremote.authenticate={str(authenticate).lower()}"
                        in configmap["data"].get("jmxremote.properties", "").splitlines(),
                        "Public JMX boolean ignored")

    for name, (chart, values, item) in expected.items():
        spec = workloads[name]["spec"]
        labels = spec["template"]["metadata"]["labels"]
        selector = spec["selector"].get("matchLabels", {})
        require(selected(selector, labels), f"StatefulSet selector mismatch: {name}")
        require(not spec["selector"].get("matchExpressions"), "Unexpected selector expressions")
        require(spec.get("replicas") == item.get("replicaCount", 1), f"replicaCount lost: {name}")
        for other_name, other in workloads.items():
            if other_name != name:
                require(not selected(selector, other["spec"]["template"]["metadata"]["labels"]),
                        f"StatefulSet selector selects another instance: {name}")
        service = services.get(spec["serviceName"])
        require(service is not None, f"Missing governing Service: {name}")
        require(service["spec"].get("clusterIP") == "None", f"Governing Service not headless: {name}")
        require(selected(service["spec"].get("selector", {}), labels), f"Headless selector mismatch: {name}")

        pod = spec["template"]["spec"]
        containers = pod["containers"]
        init_containers = pod.get("initContainers", [])
        main = containers[0]
        require(len({c["name"] for c in containers + init_containers}) == len(containers + init_containers),
                f"Duplicate container names: {name}")
        for probe in PROBES:
            settings = item.get(probe) or {}
            require(isinstance(settings, dict), f"{probe} settings must be a mapping")
            enabled = settings.get("enabled", probe != "livenessProbe")
            require(isinstance(enabled, bool), f"{probe}.enabled must be boolean")
            actual = main.get(probe)
            if not enabled:
                require(actual is None, f"Disabled {probe} still rendered: {name}")
            else:
                require(actual is not None, f"Enabled {probe} missing: {name}")
            if actual is not None:
                defaults = {"initialDelaySeconds": 0, "periodSeconds": 10, "timeoutSeconds": 2,
                            "failureThreshold": 60 if probe == "startupProbe" else 3, "successThreshold": 1}
                for field, default in defaults.items():
                    require(actual.get(field) == settings.get(field, default), f"{probe}.{field} ignored: {name}")
                actions = set(actual).intersection({"tcpSocket", "exec", "httpGet", "grpc"})
                if chart in BROKERS and item.get("replicaCount", 1) > 1 and probe != "readinessProbe":
                    require(actions == {"exec"} and actual["exec"].get("command") == ["/bin/sh", "-ec", "kill -0 1"],
                            f"HA {probe} must allow passive broker: {name}")
                else:
                    port = "amqps" if chart in BROKERS else ("https" if "https" in item.get("service", {}) else "http")
                    require(actions == {"tcpSocket"} and actual["tcpSocket"].get("port") == port,
                            f"{probe} must check application TCP listener: {name}")
                    require(any(p.get("name") == port for p in main.get("ports", [])), "Probe port not exposed")

        templates = spec.get("volumeClaimTemplates") or []
        template_names = {claim["metadata"]["name"] for claim in templates}
        volumes = pod.get("volumes", [])
        volume_names = {volume["name"] for volume in volumes}
        require(len(template_names) == len(templates), f"Duplicate claim templates: {name}")
        require(len(volume_names) == len(volumes), f"Duplicate volumes: {name}")
        require(not template_names.intersection(volume_names), f"Volume/claim name collision: {name}")
        if chart not in BROKERS:
            keep_logs = bool(item.get("keepLogsAfterRestart"))
            require(("logs" in template_names) == keep_logs, f"Log persistence flag ignored: {name}")
            if not keep_logs:
                require(all(m.get("name") != "logs" for c in containers + init_containers
                            for m in c.get("volumeMounts", [])), f"Disabled logs still mounted: {name}")
            env = main.get("env", [])
            require(len({entry["name"] for entry in env}) == len(env), f"Duplicate env names: {name}")
            require(all(entry in env for entry in item.get("env", [])), f"Custom env lost: {name}")
            session = bool(item.get("sessionReplication"))
            dns = [entry for entry in env if entry["name"] == "DNS_MEMBERSHIP_SERVICE_NAME"]
            require(dns == ([{"name": "DNS_MEMBERSHIP_SERVICE_NAME", "value": spec["serviceName"]}] if session else []),
                    f"Session membership env mismatch: {name}")
            context = [m for m in main.get("volumeMounts", []) if m.get("subPath") == "context.xml"]
            require(bool(context) == session, f"Session context mount mismatch: {name}")
        storage_class = values.get("global", {}).get("storage", {}).get("class", "")
        for claim in templates:
            if storage_class:
                require(claim["spec"].get("storageClassName") == ("" if storage_class == "-" else storage_class),
                    f"Storage class ignored: {name}")
            else:
                require("storageClassName" not in claim["spec"], f"Empty storage class must be omitted: {name}")

        known_paths = {}
        secret_references = set()
        secret_volumes = set()
        shared_claims = []
        required_keys = secret_keys(chart, item)
        for volume in volumes:
            paths, references = volume_keys(volume, configmaps, required_keys, item.get("existingSecret"))
            known_paths[volume["name"]] = paths
            secret_references.update(references)
            if references:
                secret_volumes.add(volume["name"])
            if "persistentVolumeClaim" in volume:
                claim_name = volume["persistentVolumeClaim"]["claimName"]
                require(claim_name in claims, f"Missing generated shared PVC: {claim_name}")
                shared_claims.append(claims[claim_name])
        require(secret_references == {SECRET}, f"Existing configuration Secret not mounted: {name}")
        used_config_volumes = set()
        mounted_secret_keys = set()
        for container in containers + init_containers:
            mounts = container.get("volumeMounts", [])
            require(len({mount["mountPath"] for mount in mounts}) == len(mounts), f"Duplicate mount paths: {name}")
            for mount in mounts:
                require(mount["name"] in volume_names | template_names, f"Undefined volume mount: {name}/{mount['name']}")
                paths = known_paths.get(mount["name"])
                if paths is not None:
                    used_config_volumes.add(mount["name"])
                    if "subPath" in mount:
                        require(mount["subPath"] in paths, f"Missing mounted configuration key: {name}/{mount['subPath']}")
                        if mount["name"] in secret_volumes and mount["subPath"] in required_keys:
                            mounted_secret_keys.add(mount["subPath"])
                            require(mount.get("readOnly") is True, f"Secret file mount must be read-only: {name}")
            for env in container.get("env", []):
                reference = env.get("valueFrom", {}).get("secretKeyRef")
                if reference:
                    require(reference.get("name") == SECRET, f"Unexpected environment Secret: {name}")
        require(used_config_volumes, f"No configuration volumes used: {name}")
        require(secret_volumes.intersection(used_config_volumes), f"Configuration Secret volume is never mounted: {name}")
        require(mounted_secret_keys == required_keys, f"Required Secret files not mounted: {name}")
        if chart in BROKERS:
            if item.get("replicaCount", 1) > 1:
                require(shared_claims, f"HA has no shared journal PVC: {name}")
                for claim in shared_claims:
                    require(claim["spec"].get("accessModes") == ["ReadWriteMany"], "HA PVC must use ReadWriteMany")
                    require(claim["spec"].get("storageClassName") == item["sharedStorageClassJournal"],
                            "Shared journal storage class ignored")
            elif not item.get("useSharedStorageForJournal") and not item.get("useSharedStorageForConfiguration"):
                require(not shared_claims, f"Non-HA defaults unexpectedly create shared storage: {name}")

    for name, service in services.items():
        selector = service["spec"].get("selector", {})
        matches = [workload for workload in workloads.values()
                   if selected(selector, workload["spec"]["template"]["metadata"]["labels"])]
        require(len(matches) == 1, f"Service must select exactly one instance: {name}")
        ports = {p["name"] for c in matches[0]["spec"]["template"]["spec"]["containers"] for p in c.get("ports", [])}
        for port in service["spec"]["ports"]:
            if isinstance(port.get("targetPort"), str):
                require(port["targetPort"] in ports, f"Unknown Service targetPort: {name}")

    requested_ingress = sum(bool(item.get("ingress", {}).get("enabled")) for _, _, item in expected.values())
    require(len(ingresses) == requested_ingress, "Ingress enabled flag ignored")
    for name, ingress in ingresses.items():
        owners = [prefix for prefix in expected if name == prefix or name.startswith(prefix + "-")]
        require(len(owners) == 1, f"Orphan Ingress: {name}")
        settings = expected[owners[0]][2]["ingress"]
        require(ingress["spec"].get("ingressClassName") == settings["ingressClassName"], "Ingress class ignored")
        require(any(tls.get("secretName") == "review-tls" for tls in ingress["spec"].get("tls", [])), "Ingress TLS reference missing")
        for rule in ingress["spec"]["rules"]:
            require(rule.get("host") == settings["host"], "Ingress host ignored")
            for path in rule["http"]["paths"]:
                backend = path["backend"]["service"]
                service = services.get(backend["name"])
                require(service is not None, f"Missing Ingress backend Service: {name}")
                require(selected(service["spec"].get("selector", {}), workloads[owners[0]]["spec"]["template"]["metadata"]["labels"]),
                        f"Ingress selects another instance: {name}")
                key, value = next(iter(backend["port"].items()))
                field = "port" if key == "number" else "name"
                require(any(port.get(field) == value for port in service["spec"]["ports"]), "Ingress backend port mismatch")
    return docs