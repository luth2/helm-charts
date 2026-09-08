"""Tests for the CI code itself; these do not substitute for Helm rendering."""

from copy import deepcopy
from pathlib import Path
import re
import subprocess
import tempfile
import unittest
from unittest.mock import patch

import yaml

from chart_fixtures import BROKERS, CHARTS, PROBES, Case, SECRET, SENSITIVE, components, fixtures, merge, read_yaml, secret_keys
from manifest_checks import check_public_file, documents, instance_name, validate_manifest, volume_keys
import validate_charts as runner


class FixtureTests(unittest.TestCase):
    def test_shipped_probe_values_only_expose_enabled(self):
        expected = {probe: {"enabled": probe != "livenessProbe"} for probe in PROBES}
        sources = [runner.ROOT / "charts" / chart / "values.yaml" for chart in CHARTS]
        self.assertEqual(len(sources), 4)
        for path in sources:
            with self.subTest(path=path):
                values = read_yaml(path)
                instances = values.get("instance", [])
                self.assertTrue(instances)
                for item in instances:
                    self.assertEqual({probe: item[probe] for probe in PROBES}, expected)

    def test_merge_preserves_inputs_and_replaces_lists(self):
        original = {"instance": [{"name": "one"}], "global": {"storage": {"class": ""}}}
        result = merge(original, {"instance": [{"name": "two"}]})
        self.assertEqual(result["instance"], [{"name": "two"}])
        result["global"]["storage"]["class"] = "changed"
        self.assertEqual(original["global"]["storage"]["class"], "")

    def test_fixtures_copy_complete_instance_without_mutating_source(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            original = {
                "global": {"storage": {"class": ""}},
                "instance": [{"name": "original", "replicaCount": 1,
                              "ecpProperties": {"ecpKeystorePassword": "sample"},
                              "resourcesK8s": {"requests": {"cpu": "500m"}},
                              "useSharedStorageForJournal": False}],
            }
            for chart in CHARTS:
                directory = root / "charts" / chart
                directory.mkdir(parents=True)
                (directory / "values.yaml").write_text(yaml.safe_dump(original), encoding="utf-8")
            for chart in CHARTS:
                with self.subTest(chart=chart):
                    cases = {case.name: case for case in fixtures(root, chart)}
                    baseline = cases["existing-secret"].values["instance"][0]
                    self.assertEqual(baseline["resourcesK8s"], original["instance"][0]["resourcesK8s"])
                    self.assertEqual(baseline["existingSecret"], SECRET)
                    self.assertEqual(cases["replicas-zero"].values["instance"][0]["replicaCount"], 0)
                    self.assertFalse(cases["probes-disabled"].values["instance"][0]["readinessProbe"]["enabled"])
                    multiple = cases["multiple-instances"].values["instance"]
                    multiple[1]["resourcesK8s"]["requests"]["cpu"] = "1"
                    self.assertEqual(baseline["resourcesK8s"]["requests"]["cpu"], "500m")
                    self.assertEqual(read_yaml(root / "charts" / chart / "values.yaml"), original)
                    self.assertTrue(cases[f"{chart}-reject-invalid-ha"].reject)
                    disabled = components(root, chart, cases["all-instances-disabled"].values)
                    self.assertEqual(validate_manifest("", cases["all-instances-disabled"], disabled), [])

    def test_repo_fixtures_cover_new_contract(self):
        # Source-contract guard, not a Helm render.
        for chart in CHARTS:
            with self.subTest(chart=chart):
                cases = {case.name: case for case in fixtures(runner.ROOT, chart)}
                self.assertIn("config-false-and-zero", cases)
                self.assertIn("startup-disabled", cases)
                self.assertIn("probe-defaults", cases)
                self.assertIn("probe-empty-maps", cases)
                self.assertIn("probes-enabled-only", cases)
                enabled_only = cases["probes-enabled-only"].values
                self.assertEqual({p: enabled_only["instance"][0][p] for p in PROBES},
                                 {p: {"enabled": True} for p in PROBES})
                self.assertTrue(cases[f"{chart}-reject-duplicate-name"].reject)
                self.assertTrue(cases[f"{chart}-reject-duplicate-fullnameOverride"].reject)
                child = cases["probes-zero-delay"].values
                for probe in PROBES:
                    self.assertIs(child["instance"][0][probe]["enabled"], True)
                    self.assertEqual(child["instance"][0][probe]["initialDelaySeconds"], 0)
                long_case = cases["long-release-and-instances"]
                self.assertEqual(len(long_case.release), 53)
                self.assertTrue(all(len(i["name"]) == 63 for i in long_case.values["instance"]))
                item = cases["config-false-and-zero"].values["instance"][0]
                self.assertIn({"subPath": "review-scalars.properties",
                               "content": "feature.enabled=false\nretry.count=0"}, item["configMap"])
                # Legacy private fixture fields are inert and do not prove scalar preservation.
                source = (runner.ROOT / "charts" / chart / "templates/configMap.yaml").read_text(encoding="utf-8")
                public_keys = set(re.findall(r"^  ([\w.-]+):", source, re.MULTILINE))
                self.assertFalse(public_keys & SENSITIVE[chart])
                if chart not in BROKERS:
                    self.assertIs(item["envConf"]["ecpLogFullStackTrace"], False)
                    self.assertIs(item["jmxRemoteProperties"]["comSunManagementJmxRemoteAuthenticate"], False)
                    self.assertIn("ecpLogFullStackTrace", source)
                    self.assertIn("range $instance.jmxRemoteUsers", source)
                    self.assertNotIn("$instance.jmxRemotePassword", source)
                    child = cases["session-true-custom-env"].values
                    self.assertIs(child["instance"][0]["sessionReplication"], True)
                    self.assertEqual(len(child["instance"][0]["env"]), 2)


def probe_settings(kind, port="https"):
    return {"tcpSocket": {"port": port}, "initialDelaySeconds": 0, "periodSeconds": 10,
            "timeoutSeconds": 2, "failureThreshold": 60 if kind == "startupProbe" else 3,
            "successThreshold": 1}


class ManifestTests(unittest.TestCase):
    def setUp(self):
        self.name = "review-ecp-endpoint-review-one"
        self.case = Case("unit", {})
        self.effective = {"ecp-endpoint": {
            "global": {"storage": {"class": ""}},
            "instance": [{"name": "review-one", "replicaCount": 0, "existingSecret": SECRET,
                          "service": {"https": {"port": 8443}}}],
        }}
        labels = {"app": self.name}
        self.docs = [
            {"apiVersion": "apps/v1", "kind": "StatefulSet", "metadata": {"name": self.name},
             "spec": {"replicas": 0, "serviceName": self.name + "-headless",
                      "selector": {"matchLabels": labels},
                      "template": {"metadata": {"labels": labels}, "spec": {
                          "containers": [{"name": "app", "image": "example.invalid/review:1",
                                          "ports": [{"name": "https", "containerPort": 8443}],
                                          "startupProbe": probe_settings("startupProbe"),
                                          "readinessProbe": probe_settings("readinessProbe"),
                                          "volumeMounts": [{"name": "config", "subPath": key,
                                                            "mountPath": f"/etc/{key}", "readOnly": True}
                                                           for key in sorted(secret_keys("ecp-endpoint", {}))]}],
                          "volumes": [{"name": "config", "projected": {"sources": [
                              {"configMap": {"name": self.name + "-cm"}},
                              {"secret": {"name": SECRET, "items": [
                                  {"key": key, "path": key} for key in sorted(secret_keys("ecp-endpoint", {}))]}},
                          ]}}],
                      }}}},
            {"apiVersion": "v1", "kind": "Service", "metadata": {"name": self.name + "-headless"},
             "spec": {"clusterIP": "None", "selector": labels, "ports": [{"port": 8443}]}},
            {"apiVersion": "v1", "kind": "ConfigMap", "metadata": {"name": self.name + "-cm"},
             "data": {"env.conf": "SYNTHETIC=1"}},
        ]

    def check(self, docs):
        return validate_manifest(yaml.safe_dump_all(docs), self.case, self.effective)

    def test_valid_fixture(self):
        self.assertEqual(len(self.check(self.docs)), 3)

    def test_duplicate_yaml_key_rejected(self):
        with self.assertRaisesRegex(ValueError, "Duplicate YAML"):
            documents("kind: Service\nkind: Secret\n")

    def test_duplicate_resource_rejected(self):
        with self.assertRaisesRegex(ValueError, "Duplicate resource"):
            self.check(self.docs + [deepcopy(self.docs[-1])])

    def test_secret_key_leak_rejected(self):
        self.docs[-1]["data"]["ecp.properties"] = "synthetic=true"
        with self.assertRaisesRegex(ValueError, "Sensitive file keys"):
            self.check(self.docs)

    def test_zero_replicas_and_false_probe_regressions_rejected(self):
        for field, value, message in (
            ("replicas", 1, "replicaCount lost"),
            ("probe", {"tcpSocket": {"port": 8443}}, "Disabled livenessProbe"),
        ):
            with self.subTest(field=field):
                docs = deepcopy(self.docs)
                if field == "replicas":
                    docs[0]["spec"][field] = value
                else:
                    docs[0]["spec"]["template"]["spec"]["containers"][0]["livenessProbe"] = value
                with self.assertRaisesRegex(ValueError, message):
                    self.check(docs)

    def test_service_selector_rejected(self):
        self.docs[1]["spec"]["selector"] = {"app": "other"}
        with self.assertRaisesRegex(ValueError, "Headless selector mismatch"):
            self.check(self.docs)

    def test_custom_probe_delay_checked(self):
        item = self.effective["ecp-endpoint"]["instance"][0]
        item["livenessProbe"] = {"enabled": True, "initialDelaySeconds": 7, "periodSeconds": 11}
        probe = {**probe_settings("livenessProbe"), "initialDelaySeconds": 7, "periodSeconds": 11}
        self.docs[0]["spec"]["template"]["spec"]["containers"][0]["livenessProbe"] = probe
        self.check(self.docs)
        probe["initialDelaySeconds"] = 120
        with self.assertRaisesRegex(ValueError, "initialDelaySeconds ignored"):
            self.check(self.docs)

    def test_empty_storage_class_must_be_omitted(self):
        self.docs[0]["spec"]["volumeClaimTemplates"] = [
            {"metadata": {"name": "data"}, "spec": {"storageClassName": ""}}
        ]
        with self.assertRaisesRegex(ValueError, "Empty storage class must be omitted"):
            self.check(self.docs)

    def test_missing_mounted_key_rejected(self):
        self.docs[0]["spec"]["template"]["spec"]["containers"][0]["volumeMounts"][0]["subPath"] = "missing.conf"
        with self.assertRaisesRegex(ValueError, "Missing mounted configuration key"):
            self.check(self.docs)

    def test_missing_configmap_and_wrong_secret_rejected(self):
        with self.assertRaisesRegex(ValueError, "Missing ConfigMap"):
            volume_keys({"configMap": {"name": "missing"}}, {}, set(), SECRET)
        with self.assertRaisesRegex(ValueError, "Unexpected configuration Secret"):
            volume_keys({"secret": {"secretName": "wrong"}}, {}, set(), SECRET)

    def test_disabled_chart_has_no_resources(self):
        self.assertEqual(validate_manifest("", self.case, {}), [])
        with self.assertRaisesRegex(ValueError, "Missing, extra"):
            validate_manifest(yaml.safe_dump_all(self.docs), self.case, {})

    def test_all_probe_enabled_flags_and_defaults(self):
        for kind in PROBES:
            for enabled in (False, True):
                with self.subTest(kind=kind, enabled=enabled):
                    docs = deepcopy(self.docs)
                    item = self.effective["ecp-endpoint"]["instance"][0]
                    item[kind] = {"enabled": enabled}
                    main = docs[0]["spec"]["template"]["spec"]["containers"][0]
                    if enabled:
                        main[kind] = probe_settings(kind)
                        self.check(docs)
                        main.pop(kind)
                        with self.assertRaisesRegex(ValueError, f"Enabled {kind} missing"):
                            self.check(docs)
                    else:
                        main.pop(kind, None)
                        self.check(docs)
                        main[kind] = probe_settings(kind)
                        with self.assertRaisesRegex(ValueError, f"Disabled {kind}"):
                            self.check(docs)
                    item.pop(kind)

    def test_readiness_is_required_without_db_init(self):
        item = self.effective["ecp-endpoint"]["instance"][0]
        item["ecpProperties"] = {"springDatasourceDriverClassName": "org.postgresql.Driver"}
        self.check(self.docs)
        main = self.docs[0]["spec"]["template"]["spec"]["containers"][0]
        main.pop("readinessProbe")
        with self.assertRaisesRegex(ValueError, "Enabled readinessProbe missing"):
            self.check(self.docs)

    def test_probe_tcp_action_and_all_timings_checked(self):
        for kind in ("startupProbe", "readinessProbe"):
            for field in ("initialDelaySeconds", "periodSeconds", "timeoutSeconds", "failureThreshold", "successThreshold"):
                with self.subTest(kind=kind, field=field):
                    docs = deepcopy(self.docs)
                    docs[0]["spec"]["template"]["spec"]["containers"][0][kind][field] += 1
                    with self.assertRaisesRegex(ValueError, f"{field} ignored"):
                        self.check(docs)
        main = self.docs[0]["spec"]["template"]["spec"]["containers"][0]
        main["readinessProbe"]["tcpSocket"] = {"port": "database"}
        with self.assertRaisesRegex(ValueError, "application TCP listener"):
            self.check(self.docs)

    def test_string_enabled_is_not_boolean(self):
        self.effective["ecp-endpoint"]["instance"][0]["readinessProbe"] = {"enabled": "false"}
        with self.assertRaisesRegex(ValueError, "enabled must be boolean"):
            self.check(self.docs)

    def test_no_log_persistence_rejects_init_mount(self):
        pod = self.docs[0]["spec"]["template"]["spec"]
        pod["initContainers"] = [{"name": "permissions", "volumeMounts": [{"name": "logs", "mountPath": "/logs"}]}]
        with self.assertRaisesRegex(ValueError, "Disabled logs still mounted"):
            self.check(self.docs)

    def test_session_replication_and_custom_env(self):
        item = self.effective["ecp-endpoint"]["instance"][0]
        item.update(sessionReplication=True, env=[{"name": "CUSTOM", "value": "0"}])
        main = self.docs[0]["spec"]["template"]["spec"]["containers"][0]
        main["env"] = item["env"] + [{"name": "DNS_MEMBERSHIP_SERVICE_NAME", "value": self.name + "-headless"}]
        main["volumeMounts"].append({"name": "config", "subPath": "context.xml", "mountPath": "/etc/context.xml"})
        self.docs[-1]["data"]["context.xml"] = "<Context/>"
        self.check(self.docs)
        main["env"].append(deepcopy(main["env"][0]))
        with self.assertRaisesRegex(ValueError, "Duplicate env"):
            self.check(self.docs)
        main["env"].pop()
        main["env"].pop(0)
        with self.assertRaisesRegex(ValueError, "Custom env lost"):
            self.check(self.docs)

    def test_explicit_secret_contract_and_readonly(self):
        pod = self.docs[0]["spec"]["template"]["spec"]
        secret = pod["volumes"][0]["projected"]["sources"][1]["secret"]
        items = secret.pop("items")
        with self.assertRaisesRegex(ValueError, "explicit items"):
            self.check(self.docs)
        secret["items"] = items
        items[0]["key"] = "wrong"
        with self.assertRaisesRegex(ValueError, "key/path contract"):
            self.check(self.docs)
        items[0]["key"] = items[0]["path"]
        items.append(deepcopy(items[0]))
        with self.assertRaisesRegex(ValueError, "Duplicate Secret"):
            self.check(self.docs)
        items.pop()
        mounts = pod["containers"][0]["volumeMounts"]
        mounts[0]["readOnly"] = False
        with self.assertRaisesRegex(ValueError, "read-only"):
            self.check(self.docs)
        mounts.pop(0)
        with self.assertRaisesRegex(ValueError, "Required Secret files not mounted"):
            self.check(self.docs)

    def test_override_and_long_names_match_resources(self):
        for release, change in (("review", {"fullnameOverride": "external-name"}),
                                ("r" * 53, {"name": "i" * 63})):
            with self.subTest(release=release):
                item = self.effective["ecp-endpoint"]["instance"][0]
                item.pop("fullnameOverride", None)
                item.update(change)
                self.case.release = release
                expected = instance_name(release, "ecp-endpoint", item)
                docs = documents(yaml.safe_dump_all(self.docs).replace(self.name, expected))
                self.check(docs)
                docs[0]["metadata"]["name"] = "wrong-name"
                with self.assertRaisesRegex(ValueError, "incorrectly named"):
                    self.check(docs)

    def test_duplicate_instance_inputs_rejected(self):
        items = self.effective["ecp-endpoint"]["instance"]
        items.append(deepcopy(items[0]))
        with self.assertRaisesRegex(ValueError, "Duplicate instance.name"):
            self.check(self.docs)

    def test_non_string_configmap_and_custom_scalar_content(self):
        item = self.effective["ecp-endpoint"]["instance"][0]
        content = "feature.enabled=false\nretry.count=0"
        item["configMap"] = [{"subPath": "scalars.properties", "content": content}]
        self.docs[-1]["data"]["scalars.properties"] = content
        self.check(self.docs)
        self.docs[-1]["data"]["scalars.properties"] = content.replace("count=0", "count=10")
        with self.assertRaisesRegex(ValueError, "Custom public configuration lost"):
            self.check(self.docs)
        for value in (False, 0):
            self.docs[-1]["data"]["scalars.properties"] = value
            with self.assertRaisesRegex(ValueError, "Non-string ConfigMap"):
                self.check(self.docs)
        self.docs[-1]["data"]["scalars.properties"] = content
        # Exercise the public JMX assertion, not private full-file contents.
        item["jmxRemoteProperties"] = {"comSunManagementJmxRemoteAuthenticate": False}
        pod = self.docs[0]["spec"]["template"]["spec"]
        for key in ("jmxremote.password", "jmxremote.ssl"):
            pod["volumes"][0]["projected"]["sources"][1]["secret"]["items"].append({"key": key, "path": key})
            pod["containers"][0]["volumeMounts"].append({
                "name": "config", "subPath": key, "mountPath": f"/etc/{key}", "readOnly": True,
            })
        for enabled in (False, True):
            item["jmxRemoteProperties"]["comSunManagementJmxRemoteAuthenticate"] = enabled
            self.docs[-1]["data"]["jmxremote.properties"] = (
                f"com.sun.management.jmxremote.authenticate={str(enabled).lower()}"
            )
            self.check(self.docs)
            self.docs[-1]["data"]["jmxremote.properties"] = (
                f"com.sun.management.jmxremote.authenticate={str(not enabled).lower()}"
            )
            with self.assertRaisesRegex(ValueError, "Public JMX boolean ignored"):
                self.check(self.docs)

    def test_all_charts_readiness_and_passive_broker_probes(self):
        for chart in CHARTS:
            for replicas in (1, 2):
                with self.subTest(chart=chart, replicas=replicas):
                    item = {"name": "review-one", "replicaCount": replicas, "existingSecret": SECRET,
                            "service": {"https": {"port": 8443}}}
                    name = instance_name("review", chart, item)
                    docs = documents(yaml.safe_dump_all(self.docs).replace(self.name, name))
                    spec = docs[0]["spec"]
                    spec["replicas"] = replicas
                    pod = spec["template"]["spec"]
                    main = pod["containers"][0]
                    keys = secret_keys(chart, item)
                    main["volumeMounts"] = [{"name": "config", "subPath": key,
                                             "mountPath": f"/etc/{key}", "readOnly": True}
                                            for key in sorted(keys)]
                    pod["volumes"][0]["projected"]["sources"][1]["secret"]["items"] = [
                        {"key": key, "path": key} for key in sorted(keys)]
                    if chart in BROKERS:
                        main["ports"].append({"name": "amqps", "containerPort": 5671})
                        main["readinessProbe"]["tcpSocket"]["port"] = "amqps"
                        main["startupProbe"]["tcpSocket"]["port"] = "amqps"
                        if replicas > 1:
                            item.update(useSharedStorageForJournal=True, sharedStorageClassJournal="rwx")
                            main["startupProbe"].pop("tcpSocket")
                            main["startupProbe"]["exec"] = {"command": ["/bin/sh", "-ec", "kill -0 1"]}
                            pod["volumes"].append({"name": "journal", "persistentVolumeClaim": {"claimName": name + "-journal-claim"}})
                            docs.append({"apiVersion": "v1", "kind": "PersistentVolumeClaim",
                                         "metadata": {"name": name + "-journal-claim"},
                                         "spec": {"accessModes": ["ReadWriteMany"], "storageClassName": "rwx"}})
                    effective = {chart: {"instance": [item]}}
                    validate_manifest(yaml.safe_dump_all(docs), self.case, effective)
                    main.pop("readinessProbe")
                    with self.assertRaisesRegex(ValueError, "Enabled readinessProbe missing"):
                        validate_manifest(yaml.safe_dump_all(docs), self.case, effective)


class PublicConfigurationTests(unittest.TestCase):
    def test_xml_syntax_not_just_yaml(self):
        for text in ("<Context><Manager/></Context>", "<r><!-- password=sample --></r>"):
            check_public_file("context.xml", text)
        for text in ("<Context><Manager></Context>", '<r a="one" a="two"/>', "<r>a & b</r>"):
            with self.subTest(text=text), self.assertRaisesRegex(ValueError, "Malformed public XML"):
                check_public_file("context.xml", text)

    def test_active_literal_credentials_rejected(self):
        for filename, text in (
            ("public.properties", "ecp.keystore.password=password"),
            ("public.properties", "ecp.csrf.secret=sample"),
            ("public.properties", "jasypt.encryptor.key=sample"),
            ("setenv.sh", 'export JAVA_OPTS="-Ddb.password=sample"'),
            ("extra.xml", '<r certificateKeystorePassword="sample"/>'),
            ("extra.xml", '<r><property key="clusterPassword" value="sample"/></r>'),
            ("extra.xml", '<r><password>sample</password></r>'),
        ):
            with self.subTest(filename=filename), self.assertRaisesRegex(ValueError, "Static credential"):
                check_public_file(filename, text)

    def test_comments_references_and_noncredential_settings_allowed(self):
        check_public_file("public.properties", "\n".join([
            "# db.password=password", "! password=sample", "; password=sample",
            "com.sun.management.jmxremote.password.file=/etc/jmxremote.password",
            "ecp.password.location=/etc/ecp-password.properties", "maskPassword=true",
            "db.password=${DB_PASSWORD}", "keyStorePassword=$PASSWORD", "db.password=",
            "feature.enabled=false", "retry.count=0",
        ]))
        check_public_file("extra.xml", '<r><!-- password=sample --><p key="password" value="${PASSWORD}"/></r>')


class ContractTests(unittest.TestCase):
    def test_secret_file_matrix(self):
        for chart in CHARTS:
            for replicas in (0, 1, 2):
                item = {"replicaCount": replicas}
                keys = secret_keys(chart, item)
                if chart in BROKERS:
                    self.assertEqual("broker.xml" in keys, replicas < 2)
                    self.assertEqual("broker-master.xml" in keys, replicas > 1)
                    self.assertEqual("broker.properties" in keys, chart == "ecp-broker")
                    self.assertNotIn("bootstrap.xml", keys)
                    item["service"] = {"https": {"port": 8162}}
                    self.assertIn("bootstrap.xml", secret_keys(chart, item))
                else:
                    self.assertIn("server.xml", keys)
                    self.assertNotIn("jmxremote.password", keys)
                    item["jmxRemoteProperties"] = {"comSunManagementJmxRemoteAuthenticate": False}
                    self.assertTrue({"jmxremote.password", "jmxremote.ssl"} <= secret_keys(chart, item))

    def test_name_hash_boundary_and_collision_resistance(self):
        import hashlib
        prefix = "r" * 33 + "-" + "r" * 19
        names = []
        for chart in CHARTS:
            for last in ("a", "b"):
                item = {"name": "i" * 62 + last}
                raw = f"{prefix}-{chart}-{item['name']}"
                expected = "r" * 33 + "-" + hashlib.sha256(raw.encode()).hexdigest()[:10]
                self.assertEqual(instance_name(prefix, chart, item), expected)
                names.append(expected)
        self.assertEqual(len(set(names)), len(names))
        self.assertEqual(instance_name("r", "c", {"name": "i" * 41}), "r-c-" + "i" * 41)
        self.assertEqual(len(instance_name("r", "c", {"name": "i" * 42})), 45)


class TemplateBoundaryTests(unittest.TestCase):
    def test_broker_statefulsets_keep_document_separator_newline(self):
        # Regression for run 34252754761: the second instance's leading ---
        # was joined to the previous PVC scalar by the $mounts right trim.
        # Model only this literal boundary, not Go evaluation or Helm rendering.
        for chart in BROKERS:
            with self.subTest(chart=chart):
                source = (runner.ROOT / "charts" / chart / "templates/statefulset.yaml").read_text(encoding="utf-8")
                prefix = source.split("apiVersion: apps/v1", 1)[0]
                boundary = re.search(r"(\{\{- \$mounts[^\n]*\}\})(\s*---\s*)$", prefix)
                self.assertIsNotNone(boundary)
                action, separator = boundary.groups()
                self.assertFalse(action.endswith("-}}"), "Keep the newline before the next StatefulSet")
                previous = "apiVersion: apps/v1\nkind: StatefulSet\nspec:\n  storage: 1Gi"
                following = "apiVersion: apps/v1\nkind: StatefulSet\nspec:\n  storage: 1Gi\n"
                self.assertEqual(len(documents(previous + separator + following)), 2)
                # Restoring the old right trim must reproduce the reported error.
                with self.assertRaisesRegex(ValueError, "Duplicate YAML mapping key: apiVersion"):
                    documents(previous + separator.lstrip() + following)


class RunnerTests(unittest.TestCase):
    def test_metadata_validates_each_standalone_chart(self):
        with tempfile.TemporaryDirectory() as temporary, patch.object(runner, "ROOT", Path(temporary)):
            metadata = {}
            for index, name in enumerate(CHARTS):
                directory = runner.chart_directory(runner.ROOT, name)
                directory.mkdir(parents=True)
                metadata[name] = {"name": name, "apiVersion": "v2", "type": "application",
                                  "version": f"6.{index}.0", "appVersion": f"4.{20 + index}.0-vendor", "kubeVersion": ">=1.28.0-0"}
                (directory / "values.yaml").write_text(yaml.safe_dump({
                    "global": {"storage": {"class": ""}}, "instance": [{"useSharedStorageForJournal": False}],
                }), encoding="utf-8")
            for name, data in metadata.items():
                (runner.chart_directory(runner.ROOT, name) / "Chart.yaml").write_text(yaml.safe_dump(data), encoding="utf-8")
            self.assertEqual(runner.check_metadata(), metadata)
            self.assertEqual(len(metadata), 4)
            for name, data in metadata.items():
                path = runner.chart_directory(runner.ROOT, name) / "Chart.yaml"
                for key, bad in (("name", "other"), ("apiVersion", "v1"), ("type", "library"),
                                 ("kubeVersion", ">=1.20.0"), ("appVersion", ""), ("version", "05.0.0")):
                    with self.subTest(chart=name, field=key):
                        path.write_text(yaml.safe_dump({**data, key: bad}), encoding="utf-8")
                        with self.assertRaisesRegex(ValueError, key):
                            runner.check_metadata()
                        path.write_text(yaml.safe_dump(data), encoding="utf-8")

    def test_unsupported_targets_rejected_before_io_or_tools(self):
        for target in ("ecco-sp", "unknown", "../ecp-endpoint"):
            for operation in (
                lambda: components(runner.ROOT, target, {}),
                lambda: fixtures(runner.ROOT, target),
                lambda: runner.validation_cases(runner.ROOT, target),
                lambda: runner.chart_directory(runner.ROOT, target),
                lambda: runner.validate(target),
            ):
                with self.subTest(target=target), patch.object(Path, "open") as opened, patch.object(runner, "run") as run:
                    with self.assertRaisesRegex(ValueError, "Unsupported chart target"):
                        operation()
                    opened.assert_not_called()
                    run.assert_not_called()

    def test_raw_default_contract_and_disabled_standalone(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            for chart in CHARTS:
                with self.subTest(chart=chart):
                    directory = root / "charts" / chart
                    directory.mkdir(parents=True)
                    path = directory / "values.yaml"
                    path.write_text(yaml.safe_dump({"instance": [{"name": "sample"}]}), encoding="utf-8")
                    cases = runner.validation_cases(root, chart)
                    self.assertEqual(cases[0].name, "raw-defaults")
                    self.assertEqual(cases[0].reject, "existingSecret")
                    disabled = next(case for case in cases if case.name == "all-instances-disabled")
                    effective = components(root, chart, disabled.values)
                    self.assertEqual(set(effective), {chart})
                    self.assertEqual(validate_manifest("", disabled, effective), [])
                    path.write_text(yaml.safe_dump(disabled.values), encoding="utf-8")
                    self.assertIsNone(runner.validation_cases(root, chart)[0].reject)

    def test_strict_semver(self):
        for version in ("5.0.0", "6.12.3", "6.0.0-rc.1", "6.0.0+build.5"):
            self.assertIsNotNone(runner.SEMVER.fullmatch(version))
        for version in ("v5.0.0", "5.0", "05.0.0", "5.0.0-01", "5.0.0-", "5.0.0/../x"):
            self.assertIsNone(runner.SEMVER.fullmatch(version))

    def test_package_uses_metadata_and_requires_exactly_one(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            metadata = {"version": "6.1.0-rc.2+build.7", "appVersion": "4.99.0"}
            path = root / "ecp-endpoint-6.1.0-rc.2+build.7.tgz"
            with self.assertRaisesRegex(ValueError, "exactly one"):
                runner.package_path(root, "ecp-endpoint", metadata)
            path.touch()
            self.assertEqual(runner.package_path(root, "ecp-endpoint", metadata), path)
            (root / "ecp-endpoint-5.0.0.tgz").touch()
            with self.assertRaisesRegex(ValueError, "exactly one"):
                runner.package_path(root, "ecp-endpoint", metadata)

    def test_run_rejection_must_match_diagnostic(self):
        for code, error, success in ((1, "existingSecret is required", True),
                                     (1, "bad template syntax", False), (0, "", False)):
            with self.subTest(code=code, error=error), patch.object(
                runner.subprocess, "run", return_value=subprocess.CompletedProcess([], code, "", error)
            ):
                if success:
                    runner.run(["helm", "template"], reject="existingSecret")
                else:
                    with self.assertRaises(ValueError):
                        runner.run(["helm", "template"], reject="existingSecret")

    def test_empty_render_still_runs_lint_and_kubeconform(self):
        for chart in CHARTS:
            case = next(case for case in fixtures(runner.ROOT, chart) if case.name == "all-instances-disabled")
            with self.subTest(chart=chart), tempfile.TemporaryDirectory() as temporary, patch.object(
                runner, "run", side_effect=["# empty\n", "", "Summary: 0 resources found"]
            ) as run:
                docs = runner.render(runner.chart_directory(runner.ROOT, chart), chart, case, Path(temporary), "source")
                self.assertEqual(docs, [])
                self.assertEqual([call.args[0][0] for call in run.call_args_list], ["helm", "helm", "kubeconform"])
                self.assertEqual(run.call_args_list[-1].args[0][-1].read_text(encoding="utf-8"), "# empty\n")

    def test_raw_defaults_error_stops_before_lint(self):
        case = Case("raw-defaults", {}, reject="existingSecret")
        for chart in CHARTS:
            with self.subTest(chart=chart), tempfile.TemporaryDirectory() as temporary, patch.object(
                runner, "run", return_value=""
            ) as run:
                self.assertIsNone(runner.render(runner.chart_directory(runner.ROOT, chart), chart, case, Path(temporary), "source"))
                run.assert_called_once()
                self.assertEqual(run.call_args.kwargs["reject"], "existingSecret")

    def test_pipeline_rechecks_packages_and_blocks_manifest_drift(self):
        cases = [Case("raw-defaults", {}, reject="existingSecret"), Case("existing-secret", {}),
                 Case("custom-release", {}, release="canary"), Case("all-disabled", {})]
        metadata = {"version": "6.1.0"}
        for drift in (False, True):
            with self.subTest(drift=drift), tempfile.TemporaryDirectory() as temporary:
                root = Path(temporary)

                def fake_render(chart, target, case, work, stage):
                    if case.reject:
                        return None
                    if case.name == "all-disabled":
                        return []
                    return [{"kind": "StatefulSet", "metadata": {"name": case.release},
                             "spec": {"replicas": 2 if drift and stage == "packaged" else 1}}]

                with (
                    patch.object(runner, "ROOT", root),
                    patch.object(runner, "check_metadata", return_value={"ecp-endpoint": metadata}),
                    patch.object(runner, "validation_cases", return_value=cases),
                    patch.object(runner, "run", side_effect=["v3.19.0", "v0.7.0", ""]),
                    patch.object(runner, "package_path", return_value=root / "ecp-endpoint-6.1.0.tgz") as package,
                    patch.object(runner, "unpack"),
                    patch.object(runner, "read_yaml", return_value=metadata),
                    patch.object(runner, "render", side_effect=fake_render) as render,
                    patch.object(runner.shutil, "copy2") as copy,
                ):
                    if drift:
                        with self.assertRaisesRegex(ValueError, "Packaged/source manifests differ"):
                            runner.validate("ecp-endpoint")
                        copy.assert_not_called()
                        self.assertFalse((root / ".ci-artifacts/ecp-endpoint/publish").exists())
                    else:
                        runner.validate("ecp-endpoint")
                        self.assertEqual(render.call_count, len(cases) * 2)
                        self.assertEqual([call.args[4] for call in render.call_args_list],
                                         ["source"] * len(cases) + ["packaged"] * len(cases))
                        self.assertEqual(copy.call_args_list[0].args[0].name, "ecp-endpoint-6.1.0.tgz")
                    self.assertEqual(package.call_args.args[2], metadata)


def validate_local_schemas():
    """Opt-in local check using existing jsonschema; no Helm or Secret contents.

    Kept separate from unittest: Linux CI only needs PyYAML for the unit
    tests and uses Helm for schema/renderer/HA-helper integration validation.
    """
    import json
    from collections import Counter
    from jsonschema import Draft7Validator

    validators = {}
    for chart in CHARTS:
        path = runner.ROOT / "charts" / chart / "values.schema.json"
        schema = json.loads(path.read_text(encoding="utf-8"))
        Draft7Validator.check_schema(schema)
        validators[chart] = Draft7Validator(schema)

    counts = Counter()
    for target in CHARTS:
        local = Counter()
        for case in runner.validation_cases(runner.ROOT, target):
            errors = [(chart, error)
                      for chart, values in components(runner.ROOT, target, case.values).items()
                      for error in validators[chart].iter_errors(values)]
            if case.name == "raw-defaults" and case.reject:
                if not errors or any(list(error.absolute_path)[-1:] != ["existingSecret"]
                                     or error.instance != "" for _, error in errors):
                    raise ValueError(f"{target}: expected only empty existingSecret rejection: {errors}")
                category = "expected empty existingSecret rejection"
            elif case.schema_reject:
                assert_gateway_schema_rejection(case, errors)
                category = "expected gateway schema rejection"
            else:
                if errors:
                    details = [(chart, list(error.absolute_path), error.message) for chart, error in errors]
                    raise ValueError(f"{target}/{case.name}: {details}")
                category = "helper-only negative (not executed)" if case.reject else "positive schema validation"
            local[category] += 1
            counts[category] += 1
        print(f"{target}: {dict(local)}")

    print(f"Schemas: {len(validators)}; scenarios: {dict(counts)}")


def assert_gateway_schema_rejection(case, errors):
    """Do not let a Gateway-negative fixture excuse unrelated values errors."""
    if not case.schema_reject or not errors or not case.reject or not case.schema_keyword:
        raise ValueError("Expected categorized Gateway schema rejection")
    for chart, error in errors:
        path = list(error.absolute_path)
        diagnostic = ".".join(map(str, path)) + ": " + error.message
        if (not case.name.startswith(chart + "-reject-gateway-")
                or len(path) < 3 or path[:3] != ["instance", 0, "gateway"]
                or error.validator != case.schema_keyword
                or not re.search(case.reject, diagnostic, re.IGNORECASE | re.DOTALL)):
            raise ValueError(f"Unexpected Gateway schema rejection category: {chart}/{path}/{error.validator}")


if __name__ == "__main__":
    unittest.main()