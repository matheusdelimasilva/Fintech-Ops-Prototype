import type { ReactNode } from 'react'

export function LoadingState({ label }: { label: string }) {
  return (
    <p role="status" className="state state-loading">
      {label}
    </p>
  )
}

export function EmptyState({
  title,
  children,
  compact = false,
}: {
  title: string
  children?: ReactNode
  compact?: boolean
}) {
  return (
    <div className={compact ? 'state state-empty state-compact' : 'state state-empty'}>
      <p>
        <strong>{title}</strong>
      </p>
      {children}
    </div>
  )
}
