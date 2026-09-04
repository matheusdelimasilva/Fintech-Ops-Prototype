import type { ReactNode } from 'react'

interface Props {
  children: ReactNode
  onDismiss?: () => void
}

/** Non-urgent confirmation (e.g. "Refund approved"). Announced politely, never as an alert. */
export function StatusBanner({ children, onDismiss }: Props) {
  return (
    <div role="status" className="notice notice-success">
      <div className="notice-body">{children}</div>
      {onDismiss && (
        <div className="notice-actions">
          <button type="button" className="secondary" onClick={onDismiss}>
            Dismiss
          </button>
        </div>
      )}
    </div>
  )
}
