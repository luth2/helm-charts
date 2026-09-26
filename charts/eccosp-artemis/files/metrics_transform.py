import os
from pathlib import Path
import sys
import xml.etree.ElementTree as ET


def local_name(element):
    return element.tag.rsplit("}", 1)[-1]


def child(parent, name):
    prefix = parent.tag.split("}", 1)[0] + "}" if parent.tag.startswith("{") else ""
    return ET.Element(prefix + name)


def write_xml(tree, destination):
    target = Path(destination)
    temporary = target.with_name(target.name + ".metrics-tmp")
    try:
        tree.write(temporary, encoding="utf-8", xml_declaration=True)
        os.chmod(temporary, 0o600)
        os.replace(temporary, target)
    finally:
        temporary.unlink(missing_ok=True)


def configure_broker(source, destination, plugin_class, properties):
    tree = ET.parse(source)
    cores = [element for element in tree.iter() if local_name(element) == "core"]
    if len(cores) != 1:
        raise ValueError("Expected exactly one broker core element")
    core = cores[0]
    metrics = next((element for element in core if local_name(element) == "metrics"), None)
    if metrics is None:
        metrics = child(core, "metrics")
        plugins = next((index for index, element in enumerate(core) if local_name(element) == "broker-plugins"), len(core))
        core.insert(plugins, metrics)
    if not any(local_name(element) == "plugin" and element.get("class-name") == plugin_class for element in metrics):
        plugin = child(metrics, "plugin")
        plugin.set("class-name", plugin_class)
        if properties:
            location = child(plugin, "property")
            location.set("key", "ecpBrokerPropertiesLocation")
            location.set("value", properties)
            plugin.append(location)
        metrics.append(plugin)
    write_xml(tree, destination)


def configure_bootstrap(source, destination):
    tree = ET.parse(source)
    bindings = [binding for web in tree.iter() if local_name(web) == "web"
                for binding in web if local_name(binding) == "binding"]
    if not bindings:
        raise ValueError("Expected at least one web binding")
    for binding in bindings:
        if not any(local_name(app) == "app" and app.get("url") == "metrics" for app in binding):
            app = child(binding, "app")
            app.set("url", "metrics")
            app.set("war", "metrics.war")
            binding.append(app)
    write_xml(tree, destination)


if __name__ == "__main__":
    configure_broker(sys.argv[1], sys.argv[3], sys.argv[5], sys.argv[6] if len(sys.argv) > 6 else None)
    configure_bootstrap(sys.argv[2], sys.argv[4])