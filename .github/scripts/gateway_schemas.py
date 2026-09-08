"""Pinned Gateway API v1.4.1 schemas for cluster-free, strict Kubeconform CI.

Only rendered Gateway kinds trigger downloads. The complete upstream source is
verified before parsing; converted schemas live only in the validation workdir.
Kubernetes CEL extensions are retained but are not executed by JSON Schema.
"""

from copy import deepcopy
from hashlib import sha256
import json
from pathlib import Path
import ssl
from urllib.request import urlopen

import yaml


GROUP = "gateway.networking.k8s.io"
VERSION = "v1.4.1"
BASE_URL = f"https://raw.githubusercontent.com/kubernetes-sigs/gateway-api/{VERSION}/config/crd/standard"
# SHA256 of the actual upstream bytes, fetched with verified HTTPS.
SOURCES = {
    "HTTPRoute": ("httproutes", "98c6777c22309d319292e9c288ee632006c9ffdd4272383d6f9dffa3fbccaf14"),
    "BackendTLSPolicy": ("backendtlspolicies", "f94f34b0c19cab6c25b53a6e672d9a684116a4e52193531fe2abcea20b51574f"),
}


def convert_schema(schema):
    """Convert schema nodes, never property names or literal default/enum data.

    Close structured objects only when upstream has not specified openness.
    OpenAPI nullable permits null even with enum; an anyOf preserves that rule.
    """
    if isinstance(schema, bool):
        return schema
    result = deepcopy(schema)
    for key in ("description", "externalDocs", "example"):
        result.pop(key, None)
    for key in ("properties", "patternProperties", "definitions", "$defs"):
        if key in result:
            result[key] = {name: convert_schema(child) for name, child in result[key].items()}
    for key in ("items", "additionalProperties", "additionalItems", "not", "if", "then", "else", "contains"):
        if key in result:
            child = result[key]
            result[key] = ([convert_schema(item) for item in child] if isinstance(child, list)
                           else convert_schema(child))
    for key in ("allOf", "anyOf", "oneOf"):
        if key in result:
            result[key] = [convert_schema(child) for child in result[key]]
    if (result.get("type") == "object" and "properties" in result
            and not result.get("x-kubernetes-preserve-unknown-fields", False)):
        result.setdefault("additionalProperties", False)
    # OpenAPI 3.0 uses boolean exclusive bounds; Draft 7 uses numeric bounds.
    for bound in ("minimum", "maximum"):
        exclusive = "exclusive" + bound.capitalize()
        if isinstance(result.get(exclusive), bool):
            enabled = result.pop(exclusive)
            if enabled and bound in result:
                result[exclusive] = result.pop(bound)
    nullable = result.pop("nullable", False)
    return {"anyOf": [result, {"type": "null"}]} if nullable else result


def schema_from_crd(source, kind):
    crd = yaml.safe_load(source)
    spec = crd.get("spec", {})
    if (crd.get("kind") != "CustomResourceDefinition" or spec.get("group") != GROUP
            or spec.get("names", {}).get("kind") != kind):
        raise ValueError("Unexpected Gateway CRD identity")
    versions = [v for v in spec.get("versions", []) if v.get("name") == "v1" and v.get("served") is True]
    if len(versions) != 1:
        raise ValueError("Gateway CRD must contain exactly one served v1 schema")
    schema = convert_schema(versions[0]["schema"]["openAPIV3Schema"])
    schema["$schema"] = "http://json-schema.org/draft-07/schema#"
    properties = schema.setdefault("properties", {})
    properties["apiVersion"] = {"type": "string", "const": f"{GROUP}/v1"}
    properties["kind"] = {"type": "string", "const": kind}
    # CRDs omit ObjectMeta internals; closing this object would reject valid labels.
    properties["metadata"] = {"type": "object"}
    schema["required"] = sorted(set(schema.get("required", [])) | {"apiVersion", "kind", "metadata"})
    return schema


def download_source(kind):
    plural, digest = SOURCES[kind]
    url = f"{BASE_URL}/{GROUP}_{plural}.yaml"
    with urlopen(url, timeout=30, context=ssl.create_default_context()) as response:
        if not response.geturl().startswith("https://"):
            raise ValueError("Gateway CRD redirect must use HTTPS")
        source = response.read()
    if sha256(source).hexdigest() != digest:
        raise ValueError(f"Gateway CRD SHA256 mismatch: {kind}")
    return source


def ensure_gateway_schemas(work, docs):
    """Return a Kubeconform location, caching each used kind within this workdir."""
    kinds = {doc.get("kind") for doc in docs} & SOURCES.keys()
    if not kinds:
        return None
    directory = Path(work) / "gateway-schemas" / GROUP
    directory.mkdir(parents=True, exist_ok=True)
    for kind in sorted(kinds):
        path = directory / f"{kind.lower()}_v1.json"
        if not path.is_file():
            schema = schema_from_crd(download_source(kind), kind)
            # Atomic publication: interrupted writes must not become cache hits.
            pending = path.with_suffix(".tmp")
            pending.write_text(json.dumps(schema, sort_keys=True), encoding="utf-8")
            pending.replace(path)
    return (Path(work) / "gateway-schemas").as_posix() + "/{{.Group}}/{{.ResourceKind}}_{{.ResourceAPIVersion}}.json"