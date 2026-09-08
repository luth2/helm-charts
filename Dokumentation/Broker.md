# Broker

Official source:

- [Broker Manual](https://eccosp-docs.entsoe.eu/s/ecco-sp/m/broker-manual)
- [ECCo SP Documents](https://eccosp-docs.entsoe.eu/k)

## Purpose

The Broker is the central service provider component for external message exchange in the ECP network. It handles the actual AMQP-based delivery between participants.

## Role in the Overall System

Unlike the Internal Broker, the Broker is designed for network-wide communication between components and organizations.

- Endpoints connect to the Broker for external message exchange.
- Permitted communication partners and permissions are based on information from the Component Directory.
- Message Paths and queue management are key operational aspects.

## Technical Architecture According to the Documentation

The official documentation lists two core components:

- An AMQP broker based on ActiveMQ Artemis
- A custom authentication and authorization plugin that uses security information from the Component Directory

## Operational Considerations

- The Broker controls queue management for message delivery.
- Authentication and authorization are integral to operation.
- The documentation also covers topics such as local Component Directory data, registration, administration and monitoring.

## Relationship to the Helm Repository

- Chart: `charts/ecp-broker`
- Example values: `ecco-sp/values-ecp-broker-br.yaml`

## VM Installation Guide

### Target Setup

The Broker runs as a standalone server component on a VM and provides two essential interfaces:

- AMQPS for Endpoints on port 5671
- HTTPS for administration or the console on port 8161

It uses registration and authentication data from the Component Directory and combines these with an Artemis runtime instance.

### Prerequisites

- Linux VM with a Java runtime matching the official software package
- Reachable Home Component Directory
- Prepared registration keys and a process for the subsequent authentication keystore
- Open ports 5671 and 8161
- Sufficient local or shared storage for the journal, bindings and paging

### Important Directories and Files

The repository configuration suggests roughly the following structure for a traditional VM installation:

- Installation base under `/opt/ecp-broker`
- Runtime configuration under `/opt/ecp-broker/config`
- Artemis instance under `/opt/ecp-broker/broker`
- Local directory cache under `/opt/ecp-broker/cd`
- Main configuration `broker.properties`
- Artemis configuration `broker.xml`
- Java/startup profile `artemis.profile`
- Registration keystore and authentication keystore in the configuration area

### Installation Procedure

1. Prepare the VM with an operating system, Java and a system user.
2. Install or extract the official Broker package.
3. Create the directories for configuration, runtime data, the journal and logs.
4. Configure `broker.properties` with the component code, contact information, URLs and Home Component Directory.
5. Deploy the registration keystore and perform initial registration with the Home Component Directory.
6. Store the resulting authentication keystore securely and reference it in the configuration.
7. Adjust `broker.xml` and `artemis.profile` for ports, TLS, the journal and memory usage.
8. Register the Broker as a system service and start it.

### Key Configuration Parameters

The following values are particularly important for a VM installation:

- `ecp.broker.urls`
- `ecp.broker.code`
- `ecp.directory.client.synchronization.homeComponentDirectoryPrimaryCode`
- `ecp.directory.client.synchronization.homeComponentDirectoryPrimaryUrl`
- `ecp.keystore.location` and `ecp.authKeystore.location`
- TLS and acceptor configuration in `broker.xml`
- Journal, paging and storage paths of the Artemis instance

### Post-Installation Validation

- Check the HTTPS console on port 8161
- Check AMQPS reachability on port 5671
- Check synchronization with the Component Directory
- Validate a test connection from an Endpoint, including authentication
- Check queue creation, journal behavior and certificate usage

### Installation Order Note

On VMs, the Broker should be brought into operation after the Component Directory but before the Endpoints. For HA scenarios, journal layout, storage performance and certificate storage are the critical factors.

## Conclusion

The Broker is the key component for secure external transport. It is the primary component responsible for queue behavior, security policies, participant access and network-wide communication.
