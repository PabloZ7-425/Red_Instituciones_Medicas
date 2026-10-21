import { useEffect, useRef, useState } from 'react'
import { todayInGuatemala, validatePatientCreate } from './patient-form.js'

const inputs = [
  ['identificacion', 'Identificación', 'text', 20],
  ['nombres', 'Nombres', 'text', 100],
  ['apellidos', 'Apellidos', 'text', 100],
  ['fecha_nacimiento', 'Fecha de nacimiento', 'date'],
]

export default function PatientForm({ service, onCreated, onSessionExpired, onCancel, onBusyChange }) {
  const [fields, setFields] = useState({})
  const [message, setMessage] = useState('')
  const [saving, setSaving] = useState(false)
  const inFlight = useRef(false)
  const formRef = useRef(null)

  useEffect(() => {
    const first = inputs.find(([name]) => fields[name])?.[0]
    if (!saving && first) formRef.current.elements[first].focus()
  }, [fields, saving])

  function showErrors(errors, text) {
    setFields(errors); setMessage(text)
  }

  async function submit(event) {
    event.preventDefault()
    if (inFlight.current) return
    const values = Object.fromEntries(new FormData(event.currentTarget))
    const result = validatePatientCreate(values)
    if (Object.keys(result.fields).length) {
      showErrors(result.fields, 'Revisa los campos indicados antes de guardar.')
      return
    }
    inFlight.current = true
    onBusyChange(true)
    setSaving(true); setMessage(''); setFields({})
    try {
      const patient = await service.createPatient(result.data)
      onCreated(patient)
    } catch (error) {
      if (error.status === 401) onSessionExpired(error)
      else showErrors(error.fields ?? {}, error.status === 409
        ? 'No se pudo registrar: la identificación ya existe en esta institución.'
        : error.status === 0
          ? 'No se pudo confirmar el registro. Busca la identificación antes de volver a guardarlo.'
          : error.message)
    } finally {
      inFlight.current = false
      onBusyChange(false)
      setSaving(false)
    }
  }

  return <section className="clinical-panel patient-form" aria-labelledby="patient-form-title">
    <h2 id="patient-form-title">Registrar paciente</h2>
    {message && <div role="alert" className="error-message">{message}
      {Object.entries(fields).filter(([name]) => !inputs.some(([key]) => key === name)).map(([name, errors]) => <p key={name}>{Array.isArray(errors) ? errors.join(' ') : ''}</p>)}
    </div>}
    <form ref={formRef} onSubmit={submit} noValidate aria-busy={saving}>
      {inputs.map(([name, label, type, maxLength]) => <div key={name}>
        <label htmlFor={`patient-${name}`}>{label}</label>
        <input id={`patient-${name}`} name={name} type={type} maxLength={maxLength}
          max={type === 'date' ? todayInGuatemala() : undefined} required disabled={saving}
          aria-invalid={!!fields[name]} aria-describedby={fields[name] ? `error-${name}` : undefined} />
        {fields[name] && <p className="field-error" id={`error-${name}`}>{fields[name].join(' ')}</p>}
      </div>)}
      <div className="form-actions">
        <button disabled={saving}>{saving ? 'Guardando…' : 'Guardar paciente'}</button>
        <button type="button" disabled={saving} onClick={onCancel}>Cancelar</button>
      </div>
    </form>
  </section>
}
