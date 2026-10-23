import { useEffect, useRef } from 'react'
export default function TaskDialog({ children, title, onCancel, busy }) {
  const ref=useRef(null)
  useEffect(()=>{ref.current.showModal();ref.current.querySelector('input,select,textarea')?.focus()},[])
  return <dialog ref={ref} className="operation-dialog" aria-label={title} onCancel={e=>{e.preventDefault();if(!busy)onCancel()}}>{children}</dialog>
}
