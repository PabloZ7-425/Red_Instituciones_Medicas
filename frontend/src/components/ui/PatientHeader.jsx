import Badge from './Badge.jsx'
import { age } from '../../operations/helpers.js'

export default function PatientHeader({ patient, children }) {
  return <div className="patient-header">
    <header className="history-heading">
      <div><p className="shell-overline">Expediente clínico</p><h2>{patient.nombres} {patient.apellidos}</h2></div>
      <Badge tone={patient.estado === 'activo' ? 'success' : 'neutral'}>{patient.estado}</Badge>
    </header>
    <dl className="patient-details">
      <div><dt>Identificación</dt><dd>{patient.identificacion}</dd></div>
      <div><dt>Nacimiento</dt><dd>{patient.fecha_nacimiento}</dd></div>
      <div><dt>Edad</dt><dd>{age(patient.fecha_nacimiento)} años</dd></div>
    </dl>
    {patient.estado === 'archivado' && <p className="notice">Archivado el {patient.fecha_archivo ?? 'fecha no disponible'}.
      Motivo: {patient.motivo_archivo ?? 'no disponible'}. El historial se conserva.</p>}
    {children}
  </div>
}
