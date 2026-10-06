FROM node:22-trixie-slim
# El emulador de Firestore necesita Java.
# Si firebase-tools pide una version mas nueva, cambia a openjdk-21-jre-headless.
RUN apt-get update && apt-get install -y --no-install-recommends openjdk-21-jre-headless \
    && rm -rf /var/lib/apt/lists/*
RUN npm install -g firebase-tools
WORKDIR /firebase
COPY firebase.json .
# El prefijo "demo-" permite correr el emulador sin iniciar sesion en Firebase
CMD ["firebase", "emulators:start", "--only", "firestore", "--project", "demo-historiales"]


