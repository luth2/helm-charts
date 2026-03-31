ARG UBI_BASE_IMAGE=registry.access.redhat.com/ubi10/ubi-minimal
FROM ${UBI_BASE_IMAGE}

ARG IMAGE_TITLE="ECCo SP Base Image"
ARG IMAGE_DESCRIPTION="Gemeinsames UBI Minimal Base-Image fuer spaetere ECCo-SP Komponenten"
ARG IMAGE_SOURCE="https://github.com/OWNER/REPO"
ARG IMAGE_URL="https://github.com/OWNER/REPO"
ARG IMAGE_DOCUMENTATION="https://github.com/OWNER/REPO/tree/main/Container/base-image"
ARG IMAGE_VENDOR="Amprion"
ARG IMAGE_LICENSES="Proprietary"
ARG IMAGE_VERSION="0.1.0"

LABEL org.opencontainers.image.title="${IMAGE_TITLE}" \
    org.opencontainers.image.description="${IMAGE_DESCRIPTION}" \
    org.opencontainers.image.source="${IMAGE_SOURCE}" \
    org.opencontainers.image.url="${IMAGE_URL}" \
    org.opencontainers.image.documentation="${IMAGE_DOCUMENTATION}" \
    org.opencontainers.image.vendor="${IMAGE_VENDOR}" \
    org.opencontainers.image.licenses="${IMAGE_LICENSES}" \
    org.opencontainers.image.version="${IMAGE_VERSION}"

ENV LANG=C.UTF-8 \
    LC_ALL=C.UTF-8 \
    TZ=Etc/UTC

RUN microdnf update -y \
    && microdnf install -y \
        bash \
        ca-certificates \
        coreutils \
        findutils \
        grep \
        hostname \
        java-21-openjdk \
        openssl \
        procps-ng \
        sed \
        shadow-utils \
        tzdata \
    && find /usr/lib/jvm -path '*/conf/security/java.security' -exec \
        sed -i 's|^securerandom\.source=file:/dev/random|securerandom.source=file:/dev/urandom|' {} \; \
    && microdnf clean all

CMD ["/bin/bash"]