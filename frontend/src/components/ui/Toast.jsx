import { useEffect } from 'react'

export default function Toast({ message, onClose }) {
  useEffect(() => {
    if (!message) return
    const timer = setTimeout(onClose, 7500)
    return () => clearTimeout(timer)
  }, [message, onClose])
  return message && <div className="rim-toast">
    <p role="status">{message}</p>
    <button className="text-button" type="button" aria-label="Cerrar aviso" onClick={onClose}>×</button>
  </div>
}
