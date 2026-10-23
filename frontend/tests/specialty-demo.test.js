import assert from 'node:assert/strict'
import { test } from 'node:test'
import { createDemoClinicalService, DEMO_PASSWORD } from '../src/mocks/clinical-service.js'
import { createClinicalClient } from '../src/api/clinical.js'
import { validateSpecialtyDemo, canWriteSpecialtyDemo } from '../src/clinical/specialty-demo.js'

const patient = { identificacion: 'DEMO-SPECIALTY', nombres: 'Persona', apellidos: 'Sintética', fecha_nacimiento: '2000-01-01' }
const tutor = { nombres: 'Tutor', apellidos: 'DEMO', parentesco: 'Familiar' }
const growth = { fecha: '2020-01-01', peso_kg: '15.2', talla_cm: '90' }
const resultFields = [{ nombre: 'Número', tipo: 'numero', valor: '3.5', unidad: 'DEMO' }, { nombre: 'Texto', tipo: 'texto', valor: 'DEMO' }, { nombre: 'Booleano', tipo: 'booleano', valor: 'false' }]
async function login(service, institution) { await service.login({ username: `DEMO-medico-${institution}`, password: DEMO_PASSWORD }) }
async function prepare(institution, role = 'admin') {
  const service = createDemoClinicalService({ role })
  await login(service, institution)
  const p = await service.createPatient(patient)
  return { service, p, specialty: service.specialtyDemo }
}

test('el cliente HTTP no expone el doble specialtyDemo', () => {
  assert.equal(createClinicalClient().specialtyDemo, undefined)
})

test('validación pediátrica conserva fechas civiles y decimales string; rechaza unidades ambiguas', () => {
  assert.deepEqual(validateSpecialtyDemo('growth', growth).data, { fecha: '2020-01-01', peso_kg: '15.20', talla_cm: '90.00' })
  for (const change of [{ peso_kg: '1e2' }, { peso_kg: 1.2 }, { peso_kg: '0' }, { talla_cm: '10000' }, { talla_cm: '1.234' }, { fecha: '2020-02-30' }, { fecha: '9999-01-01' }, { medico_id: 'intruso' }]) assert.ok(Object.keys(validateSpecialtyDemo('growth', { ...growth, ...change }).fields).length)
  assert.ok(validateSpecialtyDemo('growth', growth, { birth: '2021-01-01' }).fields.fecha)
  assert.ok(validateSpecialtyDemo('tutor', { ...tutor, correo: 'inválido' }).fields.correo)
  assert.ok(validateSpecialtyDemo('tutor', { ...tutor, telefono: null }).fields.telefono)
  assert.equal(canWriteSpecialtyDemo({ rol: 'secretaria', institucion: 'pediatrico' }, 'tutor'), true)
  assert.equal(canWriteSpecialtyDemo({ rol: 'laboratorista', institucion: 'laboratorio' }, 'procedure'), false)
})

test('validación UTC y FDI rechaza normalización de fechas imposibles y piezas inexistentes', () => {
  const input = { cama_id: ' ID opaco ', tipo_ingreso: ' DEMO ', fecha_hora_ingreso: '2020-01-01T12:00:00Z' }
  assert.equal(validateSpecialtyDemo('admission', input).data.cama_id, ' ID opaco ')
  for (const timestamp of ['2020-02-30T12:00:00Z', '2020-01-01T24:00:00Z', '2020-01-01T12:00:00-06:00', '9999-01-01T12:00:00Z']) assert.ok(validateSpecialtyDemo('admission', { ...input, fecha_hora_ingreso: timestamp }).fields.fecha_hora_ingreso)
  for (const piece of ['10', '19', '56', '86', '00']) assert.ok(validateSpecialtyDemo('procedure', { tratamiento_id: 'T', pieza: piece, descripcion: 'DEMO', estado: 'realizado' }).fields.pieza)
})

test('DEMO hospital: cama exclusiva, alta cronológica e idempotente, reutilización y archivo', async () => {
  const { service, p, specialty } = await prepare('hospital')
  const bed = (await specialty.catalog('admission', p.id))[0].id
  const input = { cama_id: bed, fecha_hora_ingreso: '2020-01-01T12:00:00Z', tipo_ingreso: 'DEMO' }
  const admission = await specialty.save('admission', p.id, input)
  const p2 = await service.createPatient({ ...patient, identificacion: 'DEMO-SECOND' })
  await assert.rejects(specialty.save('admission', p2.id, input), e => e.status === 409)
  const discharge = { ingreso_id: admission.id, fecha_hora_alta: '2020-01-02T12:00:00Z' }
  await assert.rejects(specialty.save('discharge', p.id, { ...discharge, fecha_hora_alta: '2019-01-01T12:00:00Z' }), e => e.status === 400)
  const saved = await specialty.save('discharge', p.id, discharge)
  assert.deepEqual(await specialty.save('discharge', p.id, discharge), saved)
  await assert.rejects(specialty.save('discharge', p.id, { ...discharge, fecha_hora_alta: '2020-01-03T12:00:00Z' }), e => e.status === 409)
  await specialty.save('admission', p2.id, input)
  assert.equal((await specialty.list(p.id)).discharge.length, 1)
  await service.archivePatient(p.id, { motivo: 'DEMO' })
  await assert.rejects(specialty.save('admission', p.id, input), e => e.status === 409)
  assert.equal((await specialty.list(p.id)).admission.length, 1)
})

test('DEMO pediatría: tutores independientes, vacunas de catálogo y medidas explícitas', async () => {
  const { p, specialty } = await prepare('pediatrico')
  const first = await specialty.save('tutor', p.id, tutor)
  const second = await specialty.save('tutor', p.id, tutor)
  assert.notEqual(first.id, second.id)
  assert.notEqual(first.tutor_id, second.tutor_id)
  assert.equal(first.correo, null)
  const vaccine = (await specialty.catalog('vaccine', p.id))[0].id
  await specialty.save('vaccine', p.id, { vacuna_id: vaccine, fecha: '2020-01-01', dosis: '1' })
  await assert.rejects(specialty.save('vaccine', p.id, { vacuna_id: 'ajena', fecha: '2020-01-01', dosis: '1' }), e => e.status === 404)
  const saved = await specialty.save('growth', p.id, growth)
  assert.equal(saved.peso_kg, '15.20')
  assert.equal(saved.talla_cm, '90.00')
  const rows = await specialty.list(p.id)
  assert.equal(rows.tutor.length, 2)
  assert.equal(rows.vaccine.length, 1)
  assert.equal(rows.growth.length, 1)
})

test('DEMO laboratorio: tipos numérico/texto/booleano, sin rangos clínicos inferidos', async () => {
  const { p, specialty } = await prepare('laboratorio', 'laboratorista')
  const exam = (await specialty.catalog('result', p.id))[0].id
  const input = { tipo_examen: exam, fecha: '2020-01-01T12:00:00Z', estado: 'finalizado', campos: resultFields }
  const row = await specialty.save('result', p.id, input)
  assert.equal(row.campos[0].valor, 3.5)
  assert.equal(row.campos[1].valor, 'DEMO')
  assert.equal(row.campos[2].valor, false)
  for (const fields of [[{ nombre: 'N', tipo: 'numero', valor: 'NaN' }], [resultFields[0], resultFields[0]], [{ nombre: 'B', tipo: 'booleano', valor: 'sí' }], []]) await assert.rejects(specialty.save('result', p.id, { ...input, campos: fields }), e => e.status === 400)
  assert.equal((await specialty.list(p.id)).result.length, 1)
})

test('DEMO odontología: tratamiento de la misma historia y pieza FDI', async () => {
  const { service, p, specialty } = await prepare('odontologica')
  assert.deepEqual(await specialty.catalog('procedure', p.id), [])
  const c = await service.createConsultation(p.id, { fecha: '2020-01-01', notas_evolucion: 'DEMO' })
  const d = await service.createDiagnosis(c.id, { codigo_cie10: 'DEMO', descripcion: 'DEMO' })
  const t = await service.createTreatment(d.id, { indicaciones_generales: 'DEMO' })
  const row = await specialty.save('procedure', p.id, { tratamiento_id: t.id, pieza: '16', descripcion: 'DEMO', estado: 'realizado' })
  assert.equal(row.consulta_id, c.id)
  const second = await service.createPatient({ ...patient, identificacion: 'DEMO-SECOND' })
  await assert.rejects(specialty.save('procedure', second.id, { tratamiento_id: t.id, pieza: '16', descripcion: 'DEMO', estado: 'realizado' }), e => e.status === 404)
})

test('DEMO: secretaria pediátrica solo recibe tutores; rol y profesional se revalidan', async () => {
  const { p, specialty } = await prepare('pediatrico', 'secretaria')
  await specialty.save('tutor', p.id, tutor)
  assert.deepEqual(Object.keys(await specialty.list(p.id)), ['tutor'])
  await assert.rejects(specialty.save('growth', p.id, growth), e => e.status === 403)
  const service = createDemoClinicalService({ professionalEnabled: false })
  await login(service, 'pediatrico')
  await assert.rejects(service.specialtyDemo.save('growth', 'missing', growth), e => e.status === 403)
  const nurse = createDemoClinicalService({ role: 'enfermero' })
  await login(nurse, 'pediatrico')
  await assert.rejects(nurse.specialtyDemo.save('tutor', 'missing', tutor), e => e.status === 403)
})

test('DEMO: separación de instituciones, copia de lecturas y rechazo tras logout', async () => {
  const { service, p, specialty } = await prepare('pediatrico')
  await specialty.save('growth', p.id, growth)
  const copy = await specialty.list(p.id)
  copy.growth.length = 0
  assert.equal((await specialty.list(p.id)).growth.length, 1)
  await service.logout()
  await assert.rejects(specialty.list(p.id), e => e.status === 401)
  await login(service, 'hospital')
  await assert.rejects(specialty.list(p.id), e => e.status === 404)
  await assert.rejects(specialty.save('growth', p.id, growth), e => e.status === 403)
})
