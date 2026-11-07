export default function Timeline({ items, renderItem }) {
  return <ol className="clinical-timeline">{items.map((item, index) =>
    <li key={item.id}>{renderItem(item, index)}</li>
  )}</ol>
}
