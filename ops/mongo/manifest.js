// Hashes + counts + metadata, never print documents. Output is stored privately.
const connection = new Mongo(process.env.MONGO_VERIFY_URI || "mongodb://mongo:27017/?directConnection=true");
const databases = connection.getDB("admin").runCommand({listDatabases: 1, nameOnly: true}).databases
  .map(d => d.name).filter(n => !["admin", "config", "local"].includes(n)).sort();
const result = {};
for (const name of databases) {
  const database = connection.getDB(name);
  const hashes = database.runCommand({dbHash: 1});
  if (hashes.ok !== 1) throw new Error("No se pudo verificar dbHash");
  result[name] = database.getCollectionInfos().sort((a,b) => a.name.localeCompare(b.name)).map(info => ({
    name: info.name, type: info.type, options: info.options,
    // Compound index field order is semantic; encode key as ordered pairs before
    // canonical sorting of metadata object keys.
    indexes: info.type === "view" ? [] : database.getCollection(info.name).getIndexes()
      .sort((a,b) => a.name.localeCompare(b.name)).map(index => ({...index, key: Object.entries(index.key)})),
    count: info.type === "view" ? null : database.getCollection(info.name).countDocuments({}),
    hash: hashes.collections[info.name] || null,
  }));
}
function ordered(value) {
  if (Array.isArray(value)) return value.map(ordered);
  if (value && typeof value === "object") return Object.fromEntries(Object.keys(value).sort().map(k => [k, ordered(value[k])]));
  return value;
}
print(JSON.stringify(ordered(EJSON.serialize(result, {relaxed: false}))));
