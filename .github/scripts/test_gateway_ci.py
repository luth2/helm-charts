"""Offline Gateway CI regressions; modeled manifests are not Helm render tests."""

from copy import deepcopy
from hashlib import sha256
import json
from pathlib import Path
import ssl
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import MagicMock, patch

import yaml

from chart_fixtures import BROKERS, CHARTS, Case, SECRET, components, fixtures, secret_keys
import gateway_schemas as schemas
from manifest_checks import documents, instance_name, validate_manifest
import test_chart_ci as chart_tests
import validate_charts as runner


def sample_crd(kind="HTTPRoute"):
    return yaml.safe_dump({
        "apiVersion": "apiextensions.k8s.io/v1", "kind": "CustomResourceDefinition",
        "spec": {"group": schemas.GROUP, "names": {"kind": kind}, "versions": [
            {"name": "v1", "served": True, "schema": {"openAPIV3Schema": {
                "type": "object", "required": ["spec"], "properties": {
                    "apiVersion": {"type": "string"}, "kind": {"type": "string"},
                    "metadata": {"type": "object"},
                    "spec": {"type": "object", "properties": {"hostname": {"type": "string"}}},
                },
            }}},
        ]},
    }).encode()


class GatewayFixtureTests(unittest.TestCase):
    def test_all_targets_cover_gateway_contract_and_keep_probes(self):
        positive = {"gateway-https", "gateway-system-ca", "gateway-http", "gateway-custom",
                    "gateway-ingress-migration", "gateway-multiple-instances", "gateway-disabled",
                    "gateway-instance-disabled"}
        for target in (*CHARTS, "ecco-sp"):
            with self.subTest(target=target):
                cases = fixtures(runner.ROOT, target)
                by_name = {case.name: case for case in cases}
                self.assertEqual(len(cases), len(by_name))
                self.assertTrue(positive <= by_name.keys())
                charts = CHARTS if target == "ecco-sp" else (target,)
                for chart in charts:
                    def item(name):
                        value = by_name[name].values
                        return (value[chart] if target == "ecco-sp" else value)["instance"][0]
                    default = item("gateway-https")
                    self.assertNotIn("backendProtocol", default["gateway"])
                    self.assertNotIn("path", default["gateway"])
                    self.assertEqual(default["gateway"]["parentRefs"], [{"name": "review-gateway"}])
                    http = item("gateway-http")
                    self.assertEqual(http["service"]["https"], default["service"]["https"])
                    self.assertEqual(http["service"]["http"]["port"], 18080)
                    self.assertNotIn("backendTLS", http["gateway"])
                    for probe in ("startupProbe", "readinessProbe", "livenessProbe"):
                        self.assertEqual(http[probe], item("existing-secret")[probe])
                    self.assertEqual(item("gateway-ingress-migration")["ingress"], item("ingress")["ingress"])
                    values = by_name["gateway-multiple-instances"].values
                    child = values[chart] if target == "ecco-sp" else values
                    instances = child["instance"]
                    self.assertEqual(len(instances), 4)
                    self.assertEqual(len({i["gateway"]["hostnames"][0] for i in instances}), 4)
                    self.assertEqual(len(instances[0]["name"]), 63)
                    self.assertEqual(len(by_name["gateway-multiple-instances"].release), 53)
                    self.assertIn("fullnameOverride", instances[2])
                    self.assertFalse(instances[3]["enabled"])
                    for protocol in ("http", "https"):
                        case = by_name[f"{chart}-reject-gateway-missing-{protocol}-port"]
                        self.assertFalse(case.schema_reject)
                        self.assertIn(f"service\\.{protocol}\\.port", case.reject)
                for case in cases:
                    if case.schema_reject:
                        self.assertIn("-reject-gateway-", case.name)
                        self.assertTrue(case.reject)
                        self.assertTrue(case.schema_keyword)
                    elif "-reject-gateway-" not in case.name:
                        self.assertIsNone(case.schema_keyword)

    def test_schema_rejection_guard_rejects_missing_unrelated_or_wrong_category(self):
        case = Case("ecp-endpoint-reject-gateway-absent-parent", {}, reject=r"gateway.*parentRefs",
                    schema_reject=True, schema_keyword="required")
        error = SimpleNamespace(absolute_path=["instance", 0, "gateway"],
                                message="'parentRefs' is a required property", validator="required")
        chart_tests.assert_gateway_schema_rejection(case, [("ecp-endpoint", error)])
        for errors in ([], [("ecp-broker", error)],
                       [("ecp-endpoint", SimpleNamespace(**{**vars(error), "absolute_path": ["instance", 0, "service"]}))],
                       [("ecp-endpoint", SimpleNamespace(**{**vars(error), "validator": "oneOf"}))],
                       [("ecp-endpoint", SimpleNamespace(**{**vars(error), "message": "'other' is required"}))]):
            with self.subTest(errors=bool(errors)), self.assertRaises(ValueError):
                chart_tests.assert_gateway_schema_rejection(case, errors)


class GatewayManifestTests(unittest.TestCase):
    setUp = chart_tests.ManifestTests.setUp
    check = chart_tests.ManifestTests.check

    def add_gateway(self, protocol="https", system=False, custom=False):
        item = self.effective["ecp-endpoint"]["instance"][0]
        gateway = {"enabled": True, "parentRefs": [{"name": "edge"}],
                   "hostnames": ["console.example.invalid"]}
        if protocol == "https":
            gateway["backendTLS"] = {"hostname": "backend.example.invalid"}
            gateway["backendTLS"].update({"wellKnownCACertificates": "System"} if system else {
                "caCertificateRefs": [{"group": "", "kind": "ConfigMap", "name": "review-ca"}],
            })
        else:
            gateway["backendProtocol"] = "http"
            item["service"]["http"] = {"port": 18080}
        if custom:
            gateway.update(path="/console/api", annotations={"example.invalid/owner": "ci", "flag": "false"},
                           hostnames=["console.example.invalid", "*.example.invalid"],
                           parentRefs=[{"name": "edge", "namespace": "networking", "sectionName": "web",
                                        "group": schemas.GROUP, "kind": "Gateway"}])
            item["service"][protocol]["port"] = 18443
        item["gateway"] = gateway
        port = item["service"][protocol]["port"]
        self.docs.append({"apiVersion": "v1", "kind": "Service", "metadata": {"name": self.name + "-svc"},
                          "spec": {"selector": {"app": self.name}, "ports": [{"name": protocol, "port": port}]}})
        self.docs.append({"apiVersion": schemas.GROUP + "/v1", "kind": "HTTPRoute",
                          "metadata": {"name": self.name + "-route", "annotations": deepcopy(gateway.get("annotations", {}))},
                          "spec": {"parentRefs": deepcopy(gateway["parentRefs"]), "hostnames": deepcopy(gateway["hostnames"]),
                                   "rules": [{"matches": [{"path": {"type": "PathPrefix", "value": gateway.get("path", "/")}}],
                                              "backendRefs": [{"group": "", "kind": "Service", "name": self.name + "-svc",
                                                               "port": port, "weight": 1}]}]}})
        if protocol == "https":
            self.docs.append({"apiVersion": schemas.GROUP + "/v1", "kind": "BackendTLSPolicy",
                              "metadata": {"name": self.name + "-backend-tls"},
                              "spec": {"targetRefs": [{"group": "", "kind": "Service", "name": self.name + "-svc",
                                                       "sectionName": "https"}], "validation": deepcopy(gateway["backendTLS"])}})

    def test_https_system_http_custom_success_all_charts(self):
        for chart in CHARTS:
            for protocol, system, custom in (("https", False, False), ("https", True, True), ("http", False, True)):
                with self.subTest(chart=chart, protocol=protocol, system=system):
                    self.setUp()
                    self.add_gateway(protocol, system, custom)
                    item = self.effective["ecp-endpoint"]["instance"][0]
                    name = instance_name(self.case.release, chart, item)
                    docs = documents(yaml.safe_dump_all(self.docs).replace(self.name, name))
                    pod = docs[0]["spec"]["template"]["spec"]
                    keys = sorted(secret_keys(chart, item))
                    pod["volumes"][0]["projected"]["sources"][1]["secret"]["items"] = [{"key": k, "path": k} for k in keys]
                    pod["containers"][0]["volumeMounts"] = [
                        {"name": "config", "subPath": k, "mountPath": f"/etc/{k}", "readOnly": True} for k in keys]
                    if chart in BROKERS:
                        pod["containers"][0]["ports"].append({"name": "amqps", "containerPort": 5671})
                        for probe in ("startupProbe", "readinessProbe"):
                            pod["containers"][0][probe]["tcpSocket"]["port"] = "amqps"
                    validate_manifest(yaml.safe_dump_all(docs), self.case, {chart: {"instance": [item]}})

    def test_route_every_mapping_is_checked(self):
        self.add_gateway(custom=True)
        route_index = 4
        changes = [
            (("apiVersion",), schemas.GROUP + "/v1beta1"),
            (("metadata", "name"), self.name + "-wrong"),
            (("metadata", "namespace"), "wrong"),
            (("metadata", "annotations"), {"wrong": "annotation"}),
            (("spec", "hostnames"), ["wrong.example.invalid"]),
            (("spec", "parentRefs"), []),
            (("spec", "rules"), []),
            (("spec", "rules", 0, "matches", 0, "path", "type"), "Exact"),
            (("spec", "rules", 0, "matches", 0, "path", "value"), "/wrong"),
        ]
        for field in ("name", "namespace", "sectionName", "group", "kind"):
            changes.append((("spec", "parentRefs", 0, field), "wrong"))
        for field, value in (("name", self.name + "-headless"), ("port", 443), ("group", "other"),
                             ("kind", "ExternalService"), ("weight", 2), ("namespace", "other")):
            changes.append((("spec", "rules", 0, "backendRefs", 0, field), value))
        for path, value in changes:
            with self.subTest(path=path):
                docs = deepcopy(self.docs)
                node = docs[route_index]
                for part in path[:-1]:
                    node = node[part]
                node[path[-1]] = value
                with self.assertRaises(ValueError):
                    self.check(docs)
        for field in ("parentRefs", "hostnames", "rules"):
            docs = deepcopy(self.docs)
            docs[route_index]["spec"].pop(field)
            with self.subTest(missing=field), self.assertRaisesRegex(ValueError, "Gateway HTTPRoute spec"):
                self.check(docs)
        for field in ("matches", "backendRefs"):
            docs = deepcopy(self.docs)
            rule = docs[route_index]["spec"]["rules"][0]
            rule[field].append(deepcopy(rule[field][0]))
            with self.subTest(extra=field), self.assertRaisesRegex(ValueError, "Gateway HTTPRoute spec"):
                self.check(docs)
        docs = deepcopy(self.docs)
        docs[route_index]["spec"]["rules"].append(deepcopy(docs[route_index]["spec"]["rules"][0]))
        with self.assertRaisesRegex(ValueError, "Gateway HTTPRoute spec"):
            self.check(docs)

    def test_tls_every_mapping_is_checked(self):
        self.add_gateway()
        changes = [(("apiVersion",), schemas.GROUP + "/v1alpha3"),
                   (("metadata", "name"), self.name + "-wrong-tls"),
                   (("spec", "validation", "hostname"), "wrong.example.invalid"),
                   (("spec", "validation", "wellKnownCACertificates"), "System")]
        for field in ("group", "kind", "name", "sectionName", "namespace"):
            changes.append((("spec", "targetRefs", 0, field), "wrong"))
        for field in ("group", "kind", "name", "namespace"):
            changes.append((("spec", "validation", "caCertificateRefs", 0, field), "wrong"))
        for path, value in changes:
            with self.subTest(path=path):
                docs = deepcopy(self.docs)
                node = docs[-1]
                for part in path[:-1]:
                    node = node[part]
                node[path[-1]] = value
                with self.assertRaisesRegex(ValueError, "Gateway"):
                    self.check(docs)
        for field in ("targetRefs", "validation"):
            docs = deepcopy(self.docs)
            docs[-1]["spec"].pop(field)
            with self.subTest(missing=field), self.assertRaisesRegex(ValueError, "Gateway BackendTLSPolicy spec"):
                self.check(docs)
        for field in ("targetRefs", "caCertificateRefs"):
            docs = deepcopy(self.docs)
            node = docs[-1]["spec"] if field == "targetRefs" else docs[-1]["spec"]["validation"]
            node[field].append(deepcopy(node[field][0]))
            with self.subTest(extra=field), self.assertRaisesRegex(ValueError, "Gateway BackendTLSPolicy spec"):
                self.check(docs)
        self.setUp()
        self.add_gateway(system=True)
        self.docs[-1]["spec"]["validation"]["wellKnownCACertificates"] = "Other"
        with self.assertRaisesRegex(ValueError, "Gateway BackendTLSPolicy spec"):
            self.check(self.docs)

    def test_missing_extra_disabled_and_forbidden_resources(self):
        self.add_gateway()
        for index in (4, 5):
            docs = deepcopy(self.docs)
            docs.pop(index)
            with self.subTest(missing=index), self.assertRaisesRegex(ValueError, "Gateway resources"):
                self.check(docs)
        for kind in ("Gateway", "GatewayClass", "CustomResourceDefinition", "ReferenceGrant", "TCPRoute"):
            extra = {"apiVersion": schemas.GROUP + "/v1", "kind": kind, "metadata": {"name": self.name + "-extra"}}
            with self.subTest(kind=kind), self.assertRaisesRegex(ValueError, "Gateway"):
                self.check(self.docs + [extra])
        item = self.effective["ecp-endpoint"]["instance"][0]
        item["gateway"]["enabled"] = False
        self.check(self.docs[:4])
        with self.assertRaisesRegex(ValueError, "Gateway resources"):
            self.check(self.docs)
        item["enabled"] = False
        self.check([])
        with self.assertRaisesRegex(ValueError, "Gateway resources"):
            self.check(self.docs[4:])
        self.setUp()
        self.add_gateway("http")
        extra = {"apiVersion": schemas.GROUP + "/v1", "kind": "BackendTLSPolicy",
                 "metadata": {"name": self.name + "-backend-tls"}, "spec": {}}
        with self.assertRaisesRegex(ValueError, "Gateway resources"):
            self.check(self.docs + [extra])

    def test_backend_service_identity_port_and_selector(self):
        self.add_gateway()
        for field, value in (("name", "http"), ("port", 443), ("port", "8443")):
            docs = deepcopy(self.docs)
            docs[3]["spec"]["ports"][0][field] = value
            with self.subTest(field=field, value=value), self.assertRaisesRegex(ValueError, "Service port mismatch"):
                self.check(docs)
        docs = deepcopy(self.docs)
        docs[3]["metadata"]["name"] = self.name + "-other"
        with self.assertRaisesRegex(ValueError, "backend Service missing"):
            self.check(docs)
        docs = deepcopy(self.docs)
        docs[3]["spec"]["selector"] = {"app": "other"}
        with self.assertRaisesRegex(ValueError, "selects another instance"):
            self.check(docs)

    def test_long_names_override_multiple_and_disabled_instances(self):
        self.add_gateway()
        baseline = deepcopy(self.docs)
        base_item = deepcopy(self.effective["ecp-endpoint"]["instance"][0])
        self.case.release = "release-" + "r" * 45
        items, docs = [], []
        for index in range(4):
            item = deepcopy(base_item)
            item["name"] = "i" * 62 + str(index)
            item["gateway"]["hostnames"] = [f"instance-{index}.example.invalid"]
            if index == 2:
                item["fullnameOverride"] = "fixed-endpoint"
            if index == 3:
                item["enabled"] = False
            items.append(item)
            if item.get("enabled", True):
                name = instance_name(self.case.release, "ecp-endpoint", item)
                instance_docs = documents(yaml.safe_dump_all(baseline).replace(self.name, name))
                instance_docs[4]["spec"]["hostnames"] = deepcopy(item["gateway"]["hostnames"])
                docs.extend(instance_docs)
        self.effective["ecp-endpoint"]["instance"] = items
        self.check(docs)
        docs[4]["spec"]["rules"][0]["backendRefs"][0]["name"] = docs[9]["metadata"]["name"]
        with self.assertRaisesRegex(ValueError, "Gateway HTTPRoute spec"):
            self.check(docs)

    def test_ingress_gateway_migration(self):
        self.add_gateway()
        item = self.effective["ecp-endpoint"]["instance"][0]
        item["ingress"] = {"enabled": True, "host": "console.example.invalid", "ingressClassName": "review-ingress"}
        self.docs.append({"apiVersion": "networking.k8s.io/v1", "kind": "Ingress", "metadata": {"name": self.name + "-ingress"},
                          "spec": {"ingressClassName": "review-ingress", "tls": [{"secretName": "review-tls"}],
                                   "rules": [{"host": "console.example.invalid", "http": {"paths": [{
                                       "path": "/", "pathType": "Prefix", "backend": {"service": {
                                           "name": self.name + "-svc", "port": {"number": 8443}}}}]}}]}})
        self.check(self.docs)
        self.docs[-1]["spec"]["rules"][0]["host"] = "wrong.example.invalid"
        with self.assertRaisesRegex(ValueError, "Ingress host ignored"):
            self.check(self.docs)


class GatewaySchemaTests(unittest.TestCase):
    def test_structural_conversion_openness_literals_nullable_and_bounds(self):
        source = {"type": "object", "description": "drop", "properties": {
            "closed": {"type": "object", "properties": {"description": {"type": "string"}}},
            "open": {"type": "object", "additionalProperties": True, "properties": {"a": {"type": "string"}}},
            "preserved": {"type": "object", "x-kubernetes-preserve-unknown-fields": True, "properties": {}},
            "map": {"type": "object", "additionalProperties": {"type": "object", "properties": {"a": {"type": "integer"}}}},
            "empty": {"type": "object"},
            "nullable": {"type": "string", "enum": ["one"], "nullable": True},
            "array": {"type": "array", "items": {"type": "object", "properties": {}}},
            "literal": {"default": {"nullable": True, "type": "object", "description": "retain"}},
            "bound": {"type": "number", "minimum": 0, "exclusiveMinimum": True,
                      "maximum": 10, "exclusiveMaximum": False},
            "composition": {"allOf": [{"type": "object", "properties": {"a": {"type": "string"}}}]},
        }}
        original = deepcopy(source)
        converted = schemas.convert_schema(source)
        self.assertEqual(source, original)
        self.assertNotIn("description", converted)
        self.assertFalse(converted["additionalProperties"])
        props = converted["properties"]
        self.assertFalse(props["closed"]["additionalProperties"])
        self.assertIn("description", props["closed"]["properties"])
        self.assertTrue(props["open"]["additionalProperties"])
        self.assertNotIn("additionalProperties", props["preserved"])
        self.assertNotIn("additionalProperties", props["empty"])
        self.assertFalse(props["map"]["additionalProperties"]["additionalProperties"])
        self.assertFalse(props["array"]["items"]["additionalProperties"])
        self.assertEqual(props["nullable"], {"anyOf": [{"type": "string", "enum": ["one"]}, {"type": "null"}]})
        self.assertEqual(props["literal"], original["properties"]["literal"])
        self.assertEqual(props["bound"], {"type": "number", "exclusiveMinimum": 0, "maximum": 10})
        self.assertFalse(props["composition"]["allOf"][0]["additionalProperties"])
        self.assertIs(schemas.convert_schema(False), False)

    def test_crd_selects_served_v1_and_enforces_identity(self):
        for kind in schemas.SOURCES:
            converted = schemas.schema_from_crd(sample_crd(kind), kind)
            self.assertEqual(converted["properties"]["apiVersion"]["const"], schemas.GROUP + "/v1")
            self.assertEqual(converted["properties"]["kind"]["const"], kind)
            self.assertEqual(converted["properties"]["metadata"], {"type": "object"})
            self.assertEqual(set(converted["required"]), {"apiVersion", "kind", "metadata", "spec"})
        for change in ("kind", "group", "version", "unserved", "duplicate"):
            crd = yaml.safe_load(sample_crd())
            if change == "kind":
                crd["spec"]["names"]["kind"] = "Gateway"
            elif change == "group":
                crd["spec"]["group"] = "other"
            elif change == "version":
                crd["spec"]["versions"][0]["name"] = "v1beta1"
            elif change == "unserved":
                crd["spec"]["versions"][0]["served"] = False
            else:
                crd["spec"]["versions"].append(deepcopy(crd["spec"]["versions"][0]))
            with self.subTest(change=change), self.assertRaises(ValueError):
                schemas.schema_from_crd(yaml.safe_dump(crd), "HTTPRoute")

    def test_download_checksum_timeout_https_and_failure(self):
        source = sample_crd()
        response = MagicMock()
        response.__enter__.return_value = response
        response.geturl.return_value = schemas.BASE_URL + "/test.yaml"
        response.read.return_value = source
        with patch.object(schemas, "urlopen", return_value=response) as download:
            with self.assertRaisesRegex(ValueError, "SHA256 mismatch"):
                schemas.download_source("HTTPRoute")
            with patch.dict(schemas.SOURCES, {"HTTPRoute": ("httproutes", sha256(source).hexdigest())}):
                self.assertEqual(schemas.download_source("HTTPRoute"), source)
                args, kwargs = download.call_args
                self.assertEqual(args[0], schemas.BASE_URL + "/gateway.networking.k8s.io_httproutes.yaml")
                self.assertEqual(kwargs["timeout"], 30)
                self.assertEqual(kwargs["context"].verify_mode, ssl.CERT_REQUIRED)
                self.assertTrue(kwargs["context"].check_hostname)
                response.geturl.return_value = "http://example.invalid/test.yaml"
                with self.assertRaisesRegex(ValueError, "HTTPS"):
                    schemas.download_source("HTTPRoute")

    def test_lazy_cache_per_kind_and_work_directory(self):
        with tempfile.TemporaryDirectory() as temporary, patch.object(schemas, "download_source", side_effect=sample_crd) as download:
            work = Path(temporary)
            self.assertIsNone(schemas.ensure_gateway_schemas(work, [{"kind": "Service"}]))
            download.assert_not_called()
            self.assertFalse((work / "gateway-schemas").exists())
            location = schemas.ensure_gateway_schemas(work, [{"kind": "HTTPRoute"}])
            self.assertEqual(location, work.as_posix() + "/gateway-schemas/{{.Group}}/{{.ResourceKind}}_{{.ResourceAPIVersion}}.json")
            path = work / "gateway-schemas" / schemas.GROUP / "httproute_v1.json"
            self.assertEqual(json.loads(path.read_text())["properties"]["kind"]["const"], "HTTPRoute")
            original = path.read_bytes()
            schemas.ensure_gateway_schemas(work, [{"kind": "HTTPRoute"}, {"kind": "BackendTLSPolicy"}])
            schemas.ensure_gateway_schemas(work, [{"kind": "HTTPRoute"}, {"kind": "BackendTLSPolicy"}])
            self.assertEqual(download.call_count, 2)
            self.assertEqual(path.read_bytes(), original)
            self.assertTrue(path.with_name("backendtlspolicy_v1.json").is_file())
            schemas.ensure_gateway_schemas(work / "second", [{"kind": "HTTPRoute"}])
            self.assertEqual(download.call_count, 3)

    def test_checksum_failure_does_not_publish_cache(self):
        with tempfile.TemporaryDirectory() as temporary, patch.object(schemas, "download_source", side_effect=ValueError("SHA256 mismatch")):
            work = Path(temporary)
            with self.assertRaisesRegex(ValueError, "SHA256 mismatch"):
                schemas.ensure_gateway_schemas(work, [{"kind": "HTTPRoute"}])
            self.assertFalse(list(work.rglob("*.json")))


class GatewayRunnerTests(unittest.TestCase):
    def test_render_source_and_packaged_use_strict_custom_schemas_and_cache(self):
        docs = [{"kind": "HTTPRoute"}, {"kind": "BackendTLSPolicy"}]
        with (tempfile.TemporaryDirectory() as temporary,
              patch.object(runner, "components", return_value={}),
              patch.object(runner, "validate_manifest", return_value=docs),
              patch.object(runner, "run", return_value="") as run,
              patch.object(schemas, "download_source", side_effect=sample_crd) as download):
            work = Path(temporary)
            for stage in ("source", "packaged"):
                self.assertEqual(runner.render(Path("chart"), "ecp-endpoint", Case("gateway", {}), work, stage), docs)
            self.assertEqual(download.call_count, 2)
            commands = [call.args[0] for call in run.call_args_list if call.args[0][0] == "kubeconform"]
            self.assertEqual(len(commands), 2)
            for command in commands:
                self.assertIn("-strict", command)
                locations = [command[i + 1] for i, part in enumerate(command) if part == "-schema-location"]
                self.assertEqual(locations, ["default", work.as_posix() + "/gateway-schemas/{{.Group}}/{{.ResourceKind}}_{{.ResourceAPIVersion}}.json"])
                self.assertFalse(any("skip" in str(part) or "ignore" in str(part) for part in command))

    def test_nongateway_render_never_downloads(self):
        with (tempfile.TemporaryDirectory() as temporary,
              patch.object(runner, "components", return_value={}),
              patch.object(runner, "run", return_value="") as run,
              patch.object(schemas, "urlopen", side_effect=AssertionError("Unexpected network")) as download):
            runner.render(Path("chart"), "ecp-endpoint", Case("empty", {}), Path(temporary), "source")
            download.assert_not_called()
            command = run.call_args_list[-1].args[0]
            self.assertEqual(command.count("-schema-location"), 1)
            self.assertIn("default", command)


if __name__ == "__main__":
    unittest.main()