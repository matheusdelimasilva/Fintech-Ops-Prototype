import type { ReactNode } from 'react'
import { formatTimestamp } from './format.ts'

export function Timestamp({ value }: { value: string }) {
  return <time dateTime={value}>{formatTimestamp(value)}</time>
}

export function Row({ label, children }: { label: string; children: ReactNode }) {
  return (
    <tr>
      <th scope="row">{label}</th>
      <td>{children}</td>
    </tr>
  )
}

/** Label/value table for one record. The caption is for screen readers only. */
export function DetailsTable({ caption, children }: { caption: string; children: ReactNode }) {
  return (
    <table className="details-table">
      <caption className="visually-hidden">{caption}</caption>
      <tbody>{children}</tbody>
    </table>
  )
}
