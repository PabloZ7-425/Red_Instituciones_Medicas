FROM docker:27-cli AS docker
FROM red_instituciones_medicas-firestore:latest AS node
FROM red_instituciones_medicas-backend:latest
COPY --from=docker /usr/local/bin/docker /usr/local/bin/docker
COPY --from=node /usr/local/bin/node /usr/local/bin/node
COPY --from=node /usr/local/lib/node_modules/npm /usr/local/lib/node_modules/npm
RUN ln -s /usr/local/lib/node_modules/npm/bin/npm-cli.js /usr/local/bin/npm \
    && apt-get update && apt-get install -y --no-install-recommends git chromium openjdk-21-jre-headless \
    && rm -rf /var/lib/apt/lists/*
WORKDIR /workspace
ENV GIT_CONFIG_COUNT=1 GIT_CONFIG_KEY_0=safe.directory GIT_CONFIG_VALUE_0=/workspace
CMD ["sleep", "infinity"]
