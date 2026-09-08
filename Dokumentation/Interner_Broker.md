# Internal Broker

Official source:

- [Internal Broker Manual](https://eccosp-docs.entsoe.eu/s/ecco-sp/m/internal-broker-manual)
- [ECCo SP Documents](https://eccosp-docs.entsoe.eu/k)

## Purpose

The Internal Broker provides the messaging services for internal message processing within the Endpoint. Without this connection, an Endpoint cannot process messages.

## Role in the Overall System

The Internal Broker is an infrastructure component for internal communication.

- It decouples processing steps within Endpoint operation.
- Multiple Endpoints can connect to a shared instance.
- Business applications can also use it when integrating through the AMQP channel.

## Technical Architecture According to the Documentation

The official documentation describes two core components:

- An AMQP broker based on ActiveMQ Artemis
- An ECCo SP Audit Logger Plugin for audit logging of connections and of message sending and consumption

## Operational Considerations

- The Endpoint's connection to the Internal Broker is mandatory.
- Multiple Endpoints can share an instance if queue names are clearly separated by prefixes.
- The focus is less on communication with external participants and more on robust internal processing and traceability.

## Relationship to the Helm Repository

In this repository, the Internal Broker is represented by the Artemis chart.

- Chart: `charts/eccosp-artemis`
- Example values: `ecco-sp/values-eccosp-artemis-eptb1.yaml`, `ecco-sp/values-eccosp-artemis-eptb2.yaml`

## VM Installation Guide

### Target Setup

The Internal Broker runs on a VM as a local or central internal messaging component. It typically provides:

- AMQPS for the Endpoint on port 5672
- HTTPS for administration or the console on port 8161

Unlike the external Broker, it is intended for internal processing and auditability rather than network-wide communication.

### Prerequisites

- Linux VM with a Java runtime matching the official software package
- Prepared keystore for TLS on the AMQPS interface
- Defined users and roles for Endpoint or Toolbox access
- Sufficient local storage for the journal, bindings, paging and logs
- Agreed queue prefixes if multiple Endpoints use the same instance

### Important Directories and Files

From a VM perspective, the repository configuration primarily suggests the following structure:

- Installation base under `/usr/share/eccosp-artemis`
- Instance data under `/opt/eccosp-artemis`
- Configuration under `/opt/eccosp-artemis/etc`
- Runtime data under `/opt/eccosp-artemis/data`
- `broker.xml` for Artemis and TLS configuration
- `artemis.profile` for startup and JVM parameters
- `keystore.jks` for the TLS endpoint

### Installation Procedure

1. Prepare the VM with an operating system, Java and a system user.
2. Install or extract the official Internal Broker or ECCoSP Artemis package.
3. Create the instance, data, log and configuration directories.
4. Adjust `broker.xml` for the AMQPS acceptor, TLS, the journal and memory limits.
5. Adjust `artemis.profile` for JVM sizing and startup options.
6. Place the keystore at the configured location and maintain the user files.
7. Register the Broker as a service and start it.
8. Only then configure the connected Endpoints to use this instance.

### Key Configuration Parameters

The following settings are particularly relevant for a VM installation:

- Acceptor port and TLS parameters in `broker.xml`
- Keystore path and password
- Journal, bindings, paging and large-message directories
- JVM values in `artemis.profile`
- Users and roles for connecting clients
- Optional queue-specific address settings

### Post-Installation Validation

- Check the HTTPS console on port 8161
- Check the AMQPS interface on port 5672
- Test user login and the TLS handshake
- Check queue creation and queue prefixes with a test Endpoint
- Check audit logging and journal behavior

### Installation Order Note

On VMs, the Internal Broker must be available before the Endpoints that depend on it. If multiple Endpoints use the same instance, queue prefixes and user permissions must be clearly separated.

## Conclusion

The Internal Broker is the technical foundation for internal Endpoint processing. In Kubernetes, it is particularly relevant to stable internal messaging paths, auditability and clear separation of multiple Endpoint instances.
