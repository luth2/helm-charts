# Component Directory

Official source:

- [Component Directory Manual](https://eccosp-docs.entsoe.eu/s/ecco-sp/m/component-directory-manual)
- [ECCo SP Documents](https://eccosp-docs.entsoe.eu/k)

## Purpose

The Component Directory is the central directory and registration authority in the ECP network. It maintains the relevant public information about components and provides interfaces for registration, configuration changes and synchronization.

## Role in the Overall System

Each component must first register with a Home Component Directory to participate in the network.

- Registration of new components
- Updates to existing configurations
- Synchronization of local directories with a Component Directory

The official documentation also covers topics such as certification authority updates, centralized management of Message Paths and groups of ECP networks.

## Technical Architecture According to the Documentation

According to the manual, the Component Directory consists of two parts:

- A directory application with a REST interface
- An associated Directory Store

## Operational Considerations

- The Component Directory is the trust anchor for master data and security-related information in the network.
- Other components access these data for registration, certificates and partner information.
- Stable synchronization and consistent maintenance of entries are essential for uninterrupted operation.

## Relationship to the Helm Repository

- Chart: `charts/ecp-directory`
- Example values: `ecco-sp/values-ecp-directory-cd.yaml`

## VM Installation Guide

### Target Setup

The Component Directory runs on a VM as the central trust and registration authority. It typically provides an HTTPS user interface or REST interface on port 8443 and stores directory and certificate information locally or in an external database.

### Prerequisites

- Linux VM with a Java runtime matching the official software package
- Prepared keystores, CA-related passwords and registration data
- Optional external database for HA or centralized persistence
- Open HTTPS port 8443
- Administrative access for initial configuration and user creation

### Important Directories and Files

The repository configuration identifies the following key artifacts for traditional VM operation:

- Runtime data under `/var/lib/ecp-directory`
- Logs under `/var/log/ecp-directory`
- Main configuration `ecp-directory.properties`
- Logging configuration `ecp-logback.xml`
- Keystore `keystore.jks`
- Authentication keystore `authKeystore.jks`
- User file for Directory accounts

### Installation Procedure

1. Prepare the VM with an operating system, Java and a system user.
2. Install or extract the official Component Directory package.
3. Create the data, log and configuration directories.
4. Adjust `ecp-directory.properties` for the data path, HTTPS, certificates, synchronization and, if applicable, an external database.
5. Store keystores and CA-related passwords appropriately.
6. Set up administrative users.
7. Register the Directory as a service and start it.
8. After successful initialization, register downstream components with this Directory.

### Key Configuration Parameters

The following values are particularly critical for a VM installation:

- `spring.profiles.active` for non-HA or HA operation
- `ecp.keystore.location`, `ecp.authKeystore.location`
- `ecp.directory.regKeystore.password`, `ecp.directory.caKeystore.password`
- `ecp.automaticUpdate.*` for certificate renewal
- `ecp.directory.client.synchronization.directorySynchronizationInterval`
- If applicable, `ecp.db.*` for an external database

### Post-Installation Validation

- Check HTTPS access on port 8443
- Check administrator login
- Check certificate functions and automatic updates
- Check synchronization with other Directories, if used
- Successfully complete registration of a test component

### Installation Order Note

On VMs, the Component Directory is usually the first component brought into production. Brokers and Endpoints should only be installed and registered afterward.

## Conclusion

The Component Directory is the administration and trust authority of the ECP network. It is operationally critical to keeping components available for onboarding, discoverable and securely configurable.
