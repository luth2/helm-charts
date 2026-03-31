ARG UBI_BASE_IMAGE=registry.access.redhat.com/ubi10/ubi-minimal
FROM ${UBI_BASE_IMAGE}

ARG IMAGE_TITLE="ECCo SP Base Image"
ARG IMAGE_DESCRIPTION="Gemeinsames UBI Minimal Base-Image fuer ECCo-SP Komponenten"
ARG IMAGE_SOURCE="https://github.com/luth2/helm-charts"
ARG IMAGE_AUTHOR="ecp-maintenance@amprion.net"
ARG IMAGE_LICENSES="GPL-3.0-or-later"
ARG IMAGE_VERSION="0.1.0"
ARG IMAGE_VENDOR="luth2"

LABEL org.opencontainers.image.title="${IMAGE_TITLE}" \
    org.opencontainers.image.description="${IMAGE_DESCRIPTION}" \
    org.opencontainers.image.source="${IMAGE_SOURCE}" \
    org.opencontainers.image.authors="${IMAGE_AUTHOR}" \
    org.opencontainers.image.licenses="${IMAGE_LICENSES}" \
    org.opencontainers.image.version="${IMAGE_VERSION}" \
    org.opencontainers.image.vendor="${IMAGE_VENDOR}"

ENV LANG=C.UTF-8 \
    LC_ALL=C.UTF-8 \
    TZ=Etc/UTC

RUN microdnf install -y --setopt=install_weak_deps=0 --nodocs \
        bash \
        ca-certificates \
        coreutils \
        findutils \
        grep \
        hostname \
        java-21-openjdk-headless \
        openssl \
        procps-ng \
        sed \
        tzdata \
    && update-ca-trust \
    && find /usr/lib/jvm -path '*/conf/security/java.security' -print0 | xargs -0 -r sed -i 's|^securerandom\.source=file:/dev/random|securerandom.source=file:/dev/urandom|' \
    && chmod 0644 /etc/passwd /etc/group \
    && rm -rf /var/cache/dnf /var/cache/yum /tmp/* /var/tmp/* \
    && microdnf clean all

CMD ["/bin/bash"]