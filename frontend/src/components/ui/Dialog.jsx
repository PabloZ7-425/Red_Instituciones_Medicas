import { useEffect, useRef } from 'react'

export default function Dialog({ title, onCancel, busy, returnFocusRef, children }) {
  const ref = useRef(null)

  useEffect(() => {
    const dialog = ref.current
    const trigger = document.activeElement
    dialog.showModal()
    dialog.querySelector('input, select, textarea')?.focus()
    return () => {
      dialog.close()
      const target = returnFocusRef?.current ?? trigger
      if (target?.isConnected) target.focus()
    }
  }, [returnFocusRef])

  function cancel(event) {
    event.preventDefault()
    if (!busy) onCancel()
  }

  return <dialog ref={ref} className="operation-dialog ui-dialog" aria-label={title} onCancel={cancel}>
    {children}
  </dialog>
}
