import { useEffect, useRef, useState } from 'react'
import { todayInGuatemala } from './patient-form.js'
import { validateConsultationCreate } from './consultation-form.js'

export default function ConsultationForm({ service, patientId, onCreated, onSessionExpired, onCancel, onBusyChange }) {
  const [fields, setFields] = useState({})
  const [message, setMessage] = useState('')
  const [saving, setSaving] = useState(false)
  const formRef = useRef(null)
  const inFlight = useRef(false)
  useEffect(() => {
    const first = ['fecha', 'notas_evolucion'].find(key => fields[key])
    if (!saving && first) formRef.current.elements[first].focus()
  }, [fields, saving])

  async function submit(event) {
    event.preventDefault()
    if (inFlight.current) return
    const { data, fields: errors } = validateConsultationCreate(Object.fromEntries(new FormData(event.currentTarget)))
    if (Object.keys(errors).length) { setFields(errors); setMessage('Revisa los campos indicados.'); return }
    inFlight.current = true
    setSaving(true); onBusyChange(true); setFields({}); setMessage('')
    try {
      const consultation = await service.createConsultation(patientId, data)
      onCreated(consultation)
    } catch (error) {
      if (error.status === 401) onSessionExpired(error)
      else {
        setFields(error.fields ?? {})
        setMessage(error.status === 409 ? 'No se pudo guardar la consulta: el estado del paciente o de la cita cambió. Actualiza el historial antes de continuar.'
          : error.status === 0 ? 'No se pudo confirmar el registro. Consulta el historial antes de intentar guardarlo otra vez.'
            : error.message)
      }
    } finally { inFlight.current = false; setSaving(false); onBusyChange(false) }
  }

  return <section className="consultation-form" aria-labelledby="consultation-form-title">
    <h3 id="consultation-form-title">Registrar consulta</h3>
    {message && <div role="alert" className="error-message">{message}
      {Object.entries(fields).filter(([key]) => !['fecha', 'notas_evolucion'].includes(key)).map(([key, errors]) => <p key={key}>{Array.isArray(errors) ? errors.join(' ') : ''}</p>)}
    </div>}
    <form ref={formRef} onSubmit={submit} noValidate aria-busy={saving}>
      <label htmlFor="consultation-fecha">Fecha de consulta</label>
      <input id="consultation-fecha" name="fecha" type="date" defaultValue={todayInGuatemala()} max={todayInGuatemala()} required disabled={saving}
        aria-invalid={!!fields.fecha} aria-describedby={fields.fecha ? 'consultation-error-fecha' : undefined} />
      {fields.fecha && <p className="field-error" id="consultation-error-fecha">{fields.fecha.join(' ')}</p>}
      <label htmlFor="consultation-notas">Notas de evolución</label>
      <textarea id="consultation-notas" name="notas_evolucion" rows={5} maxLength={5000} required disabled={saving}
        aria-invalid={!!fields.notas_evolucion} aria-describedby={fields.notas_evolucion ? 'consultation-error-notas' : undefined} />
      {fields.notas_evolucion && <p className="field-error" id="consultation-error-notas">{fields.notas_evolucion.join(' ')}</p>}
      <div className="form-actions"><button disabled={saving}>{saving ? 'Guardando…' : 'Guardar consulta'}</button>
        <button type="button" disabled={saving} onClick={onCancel}>Cancelar consulta</button></div>
    </form>
  </section>
}
