// Central B5 infrastructure; never changes validators, seeds or clinical adapters.
let connection;
const deadline = Date.now() + 30000;
while (true) {
  try {
    connection = new Mongo("mongodb://mongo:27017/?directConnection=true&serverSelectionTimeoutMS=1000");
    if (connection.getDB("admin").runCommand({ping: 1}).ok === 1) break;
  } catch (error) {
    if (Date.now() >= deadline) throw new Error("MongoDB no responde");
  }
  sleep(200);
}
const admin = connection.getDB("admin");
let config;
try {
  config = admin.runCommand({replSetGetConfig: 1});
} catch (error) {
  if (error.code !== 94) throw new Error("No se pudo inspeccionar configuracion rs0");
  config = {ok: 0, code: 94};
}
if (config.ok === 1) {
  if (config.config._id !== "rs0" || config.config.members.length !== 1 ||
      config.config.members[0].host !== "mongo:27017") {
    throw new Error("Topologia existente incompatible; no se reconfigura automaticamente");
  }
} else if (config.code === 94) {
  const result = admin.runCommand({replSetInitiate: {_id: "rs0", members: [{_id: 0, host: "mongo:27017"}]}});
  if (result.ok !== 1) throw new Error("No se pudo iniciar rs0");
} else {
  throw new Error("Se requiere mongod --replSet rs0; revisar estado antes de iniciar");
}
while (Date.now() < deadline) {
  const hello = admin.runCommand({hello: 1});
  if (hello.setName === "rs0" && hello.isWritablePrimary === true) {
    print("rs0 PRIMARY listo; configuracion conservada");
    quit(0);
  }
  sleep(200);
}
throw new Error("rs0 no alcanzo PRIMARY en el plazo esperado");
