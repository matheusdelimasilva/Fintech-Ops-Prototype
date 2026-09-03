import type { AuditAction, RefundAction, RefundStatus, RiskLevel, Role } from '../api/types.ts'

const moneyFormatters = new Map<string, Intl.NumberFormat>()

/** Integer minor units in, display string out. Never converts to a float before formatting. */
export function formatMoney(amountCents: number, currency: string): string {
  let formatter = moneyFormatters.get(currency)
  if (!formatter) {
    formatter = new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency,
      minimumFractionDigits: 0,
      maximumFractionDigits: 0,
    })
    moneyFormatters.set(currency, formatter)
  }
  const sign = amountCents < 0 ? '-' : ''
  const absolute = Math.abs(amountCents)
  const major = Math.floor(absolute / 100)
  const minor = String(absolute % 100).padStart(2, '0')
  // Format only the integer part with Intl, then append the exact minor digits, so the
  // amount is never converted to a float.
  const parts = formatter.formatToParts(major)
  const lastInteger = parts.map((p) => p.type).lastIndexOf('integer')
  const text = parts
    .map((part, index) => (index === lastInteger ? `${part.value}.${minor}` : part.value))
    .join('')
  return `${sign}${text}`
}

export function formatApprovalLimit(limitCents: number | null, currency = 'USD'): string {
  return limitCents === null ? 'Unlimited' : formatMoney(limitCents, currency)
}

const pad = (n: number) => String(n).padStart(2, '0')

/** Backend timestamps are UTC; render them as UTC so evidence is reproducible anywhere. */
export function formatTimestamp(iso: string): string {
  const date = new Date(iso)
  if (Number.isNaN(date.getTime())) return iso
  return (
    `${date.getUTCFullYear()}-${pad(date.getUTCMonth() + 1)}-${pad(date.getUTCDate())} ` +
    `${pad(date.getUTCHours())}:${pad(date.getUTCMinutes())}:${pad(date.getUTCSeconds())} UTC`
  )
}

export function formatDate(iso: string): string {
  const date = new Date(iso)
  if (Number.isNaN(date.getTime())) return iso
  return `${date.getUTCFullYear()}-${pad(date.getUTCMonth() + 1)}-${pad(date.getUTCDate())}`
}

export const ROLE_LABELS: Record<Role, string> = {
  support_agent: 'Support Agent',
  operations_manager: 'Operations Manager',
  admin: 'Admin',
}

export const REFUND_STATUS_LABELS: Record<RefundStatus, string> = {
  pending: 'Pending',
  approved: 'Approved',
  rejected: 'Rejected',
  escalated: 'Escalated',
}

export const RISK_LABELS: Record<RiskLevel, string> = {
  low: 'Low',
  medium: 'Medium',
  high: 'High',
}

export const REFUND_ACTION_LABELS: Record<RefundAction, string> = {
  approve: 'Approve',
  reject: 'Reject',
  escalate: 'Escalate',
}

export const AUDIT_ACTION_LABELS: Record<AuditAction, string> = {
  'refund.approved': 'Refund approved',
  'refund.rejected': 'Refund rejected',
  'refund.escalated': 'Refund escalated',
  'feature_flag.updated': 'Feature flag updated',
}

/** Turns a snapshot key like `last_action_by` into `Last action by`. */
export function humanizeKey(key: string): string {
  const words = key.replace(/_/g, ' ')
  return words.charAt(0).toUpperCase() + words.slice(1)
}
