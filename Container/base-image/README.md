# ECCo SP Base Image

This base image is intended as a shared starting point for future ECCo-SP component images.

## Purpose

The image provides only the shared prerequisites:

- UBI Minimal as a shared Red Hat-based foundation
- Java 21 via `java-21-openjdk`
- Bash and basic shell tools
- TLS and certificate support via `ca-certificates` and `openssl`
- No pre-created ECCo-SP runtime directories

## Built-in Basic Hardening

The base image is intentionally kept simple but already includes several useful basic hardening measures:

- Package installation without weak dependencies
- Package installation without documentation overhead
- Cleanup of package and temporary caches after the build
- Update of the CA trust store
- Adjustment of the Java `securerandom` source to `urandom`

Stricter restrictions, such as a final non-root user or read-only runtime assumptions, are intentionally not included because subsequent RPM installations and component scripts may have different requirements depending on the component.

## Why Not Distroless

The current ECCo-SP structure relies on shell, Bash, and startup script behavior in several places. It also includes Tomcat- and Artemis-related configurations. A small but non-distroless base image is therefore the more robust choice for this first step.

## Why Tini Was Removed

Tini is a very small init process for containers. It handles proper signal forwarding and reaping of terminated child processes.

It was removed again from this initial base image because the current requirement is only for a lean, shared UBI Java base, with the actual startup logic to be supplied later for each component through RPM installation.

If a component later fails to handle signals or zombie processes correctly when running as PID 1, Tini can still be selectively reintroduced in the final component Dockerfile.

## Java Security Adjustment

The Java security configuration is adjusted after installation.

The `java.security` file is located under `/usr/lib/jvm`, and the following line is replaced:

- From `securerandom.source=file:/dev/random`
- To `securerandom.source=file:/dev/urandom`

This exactly matches the specified requirement and avoids blocking caused by `dev/random`.

## Build Example

```bash
docker build \
  -t eccosp/base:0.1.0 \
  ./Container/base-image
```

## GitHub and GHCR Association

The Dockerfile includes OCI labels so that the image can later be properly associated with a GitHub repository.

Especially important:

- `org.opencontainers.image.source`

Set this value to the actual repository URL at build time, for example:

```bash
docker build \
  --build-arg IMAGE_SOURCE=https://github.com/ORG/REPO \
  --build-arg IMAGE_URL=https://github.com/ORG/REPO \
  --build-arg IMAGE_DOCUMENTATION=https://github.com/ORG/REPO/tree/main/Container/base-image \
  -t ghcr.io/ORG/REPO/eccosp-base:0.1.0 \
  ./Container/base-image
```

When pushing to GHCR later, this exact combination of image name and OCI source label provides a sound basis for association with the GitHub repository.

## Configurable Build Arguments

- `UBI_BASE_IMAGE` for the specific UBI Minimal image
- `IMAGE_SOURCE` for the GitHub repository URL
- `IMAGE_URL` for the project URL
- `IMAGE_DOCUMENTATION` for the documentation URL
- `IMAGE_VERSION` for the application-level image version

## Important Note on the Java Version

The image intentionally installs `java-21-openjdk` because this is the current requirement for the shared base.

Before production use, still verify whether the supplied ECCo-SP RPMs are explicitly approved for this exact Java variant.

## Important Note on Directories

The base image intentionally does not create any ECCo-SP-specific runtime directories.

The current assumptions are:

- RPM installation creates the required target structure
- Component-specific Dockerfiles only handle RPM installation and configuration adjustments
- No artificial directory structure is pre-created in the base image

## Network and Firewall Notes

These ports are not opened in the image; they must be allowed at the VM, host, network, or Kubernetes level.

Possible outbound database ports:

- Oracle Database: 1521
- Microsoft SQL Server: 1433
- MySQL: 3306
- PostgreSQL: 5432

Communication with other ECP components:

Default ports according to the specification:

| Component | Inbound | Outbound | Both |
| --- | --- | --- | --- |
| Endpoint | - | - | 8443 |
| Component Directory | 8443 | - | - |
| Broker | 5671, 8161 | - | - |
| Internal Broker | 5672, 8161 | - | 5671* |

For the Internal Broker, `5671*` indicates a possible communication path to additional ECP components or specific routing scenarios in practice. Allowing this traffic is therefore an operational and network requirement, not an image property.

## Recommended Next Steps

Future Dockerfiles should use this image as their base and then add only component-specific elements:

- Install the RPM and make only the required adjustments
- Add the required configurations and startup commands
- Define the startup command for the respective component
