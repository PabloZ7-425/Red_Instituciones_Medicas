// Exporta el esquema real de init.js sin conectar ni escribir en MongoDB.
// Usado por las pruebas para aplicar sus validadores a una BD aislada vía PyMongo.
const fs = require('node:fs');
const vm = require('node:vm');
const path = require('node:path');
const schemas = {};
const indexes = {};
const collections = new Set();
let updates = 0;
const lab = new Proxy({
  getCollectionNames: () => [...collections],
  createCollection: (name, options) => { collections.add(name); schemas[name] = options; },
  runCommand: command => {
    updates += 1;
    schemas[command.collMod] = {validator: command.validator};
    return {ok: 1};
  }
}, {get(target, key) {
  if (key in target) return target[key];
  return {createIndex: (keys, options = {}) => {
    indexes[key] ??= [];
    const index = {keys, options};
    if (!indexes[key].some(item => JSON.stringify(item) === JSON.stringify(index))) indexes[key].push(index);
  }};
}});
const source = fs.readFileSync(path.join(__dirname, 'init.js'), 'utf8');
// Contexto nuevo por ejecución, como dos invocaciones independientes de mongosh.
for (let run = 0; run < 2; run++) vm.runInNewContext(source, {db: {getSiblingDB: () => lab}});
process.stdout.write(JSON.stringify({schemas, indexes, updates}));
