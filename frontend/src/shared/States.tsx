import type { ReactNode } from 'react'

export function LoadingState({ label }: { label: string }) {
  return (
    <p role="status" className="state state-loading">
      {label}
    </p>
  )
}

export function EmptyState({ title, children }: { title: string; children?: ReactNode }) {
  return (
    <div className="state state-empty">
      <p>
        <strong>{title}</strong>
      </p>
      {children}
    </div>
  )
}
