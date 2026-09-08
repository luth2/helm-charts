# Container

This directory contains the shared container base for future ECCo-SP component images.

Current contents:

- `base-image/` as the shared UBI Minimal base image for Java-based ECCo-SP components

Purpose of this structure:

- Maintain the shared Java runtime and basic tools in one place
- Build future component Dockerfiles on a consistent foundation
- Cover the shell and Java requirements of existing ECCo-SP deployments in the base image itself
