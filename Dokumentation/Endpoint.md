# Endpoint

Official source:

- [Endpoint Manual](https://eccosp-docs.entsoe.eu/s/ecco-sp/m/endpoint-manual)
- [ECCo SP Documents](https://eccosp-docs.entsoe.eu/k)

## Purpose

The Endpoint is the user-facing component of ECP. It provides the user interface and API through which business applications send and receive messages and integrate them into existing processes.

## Role in the Overall System

The Endpoint sits between business applications and the central communication services of ECCo SP.

- It connects to the Internal Broker for internal processing.
- It uses the Broker for external message exchange.
- It accesses the Component Directory for certificates and information about other components.

## Important Interfaces

- Internal Broker: AMQPS, typical default port 5672
- Broker: AMQPS, typical default port 5671
- Component Directory: HTTPS, typical default port 8443

The official documentation also describes the Endpoint as a central integration component for various channels and processing stages, including pre-processing, post-processing and registration helpers.

## Operational Considerations

- An Endpoint must be registered with a Home Component Directory to participate in the ECP network.
- A continuous connection to the Component Directory is not strictly required for ongoing messaging as long as the cached information remains valid.
- According to the documentation, the default TTL of a CD entry is 28 days.
- The configuration of Message Paths on the recipient side determines which Broker is used for a particular route.

## Relationship to the Helm Repository

- Chart: `charts/ecp-endpoint`
- Example values: `ecco-sp/values-ecp-endpoint-ep1.yaml`, `ecco-sp/values-ecp-endpoint-ep2.yaml`

## VM Installation Guide

### Target Setup

The Endpoint runs on its own VM or on a dedicated application VM and connects from there to three external services:

- Internally to the Internal Broker on port 5672
- Externally to the Broker on port 5671
- Administratively to the Component Directory on port 8443

### Prerequisites

- Linux VM with a Java runtime matching the official software package
- Reachable Component Directory
- Reachable Internal Broker
- Reachable Broker for external message exchange
- Prepared keystores for registration and authentication
- Optional external database if a local data path is not to be used

### Important Directories and Files

The repository configurations identify the following key files and paths for traditional operation:

- Runtime data under `/var/lib/ecp-endpoint`
- Logs under `/var/log/ecp-endpoint`
- Main configuration `ecp.properties`
- Logging configuration `ecp-logback.xml`
- Keystore `keystore.jks`
- Authentication keystore `authKeystore.jks`

For a later container build, these artifacts define the boundary between image content and external runtime configuration.

### Installation Procedure

1. Prepare the VM with an operating system, Java and a system user for the Endpoint.
2. Install or extract the official Endpoint software package on the VM.
3. Create the data, log and configuration directories with stable paths.
4. Configure `ecp.properties` with the data path, Broker connections, Home Component Directory and keystore paths.
5. If HA is required, connect the external database and activate the appropriate HA profile.
6. Place certificates and keystores at the designated paths.
7. Register the Endpoint as a service, typically using systemd or a vendor-specific startup script.
8. Start the service and check the HTTPS user interface.

### Key Configuration Parameters

The following settings in particular must be configured correctly for a VM installation:

- `internalBroker.urls`, `internalBroker.host`, `internalBroker.amqp.port`
- `internalBroker.auth.user`, `internalBroker.auth.password`
- `ecp.keystore.location`, `ecp.authKeystore.location`
- `ecp.directory.client.synchronization.homeComponentDirectoryPrimaryCode`
- `ecp.directory.client.synchronization.homeComponentDirectoryPrimaryUrl`
- If applicable, `ecp.db.*` for an external database connection

### Post-Installation Validation

- Check HTTPS access to the Endpoint
- Check the connection to the Internal Broker
- Check the connection to the Broker
- Check synchronization with the Component Directory
- Complete registration and validate Message Paths

### Installation Order Note

On VMs, the Endpoint should always be brought into operation last because it depends on a working Internal Broker, Broker and Component Directory.

## Conclusion

The Endpoint is the actual entry point for applications. It is the primary starting point for operational questions about integration, routing, obtaining certificates or connections to internal and external messaging services.
