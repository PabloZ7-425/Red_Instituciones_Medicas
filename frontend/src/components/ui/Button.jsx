export default function Button({ variant = 'primary', className = '', ...props }) {
  return <button className={`ui-button ui-button--${variant} ${className}`.trim()} {...props} />
}
