export default function DataTable({ caption, columns, rows }) {
  return <div className="table-scroll"><table>
    <caption>{caption}</caption>
    <thead><tr>{columns.map(column => <th key={column.label} scope="col">{column.label}</th>)}</tr></thead>
    <tbody>{rows.map(row => <tr key={row.id}>{columns.map(column => <td key={column.label}>{column.value(row)}</td>)}</tr>)}</tbody>
  </table></div>
}
