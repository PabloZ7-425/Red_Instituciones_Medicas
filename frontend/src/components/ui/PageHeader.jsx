export default function PageHeader({ title, eyebrow, context }) {
  return <header className="shell-header">
    <div>{eyebrow && <p className="shell-overline">{eyebrow}</p>}<h1>{title}</h1></div>
    {context}
  </header>
}
