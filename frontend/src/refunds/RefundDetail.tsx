import type { ReactNode } from 'react'
import type { Refund } from '../api/types.ts'
import { Timestamp } from '../shared/DetailsTable.tsx'
import {
  AUDIT_ACTION_LABELS,
  PAYMENT_STATUS_LABELS,
  REFUND_STATUS_LABELS,
  RISK_LABELS,
  formatMoney,
  humanizeKey,
} from '../shared/format.ts'

interface Props {
  refund: Refund
}

function Fact({ label, children }: { label: string; children: ReactNode }) {
  return (
    <div>
      <dt>{label}</dt>
      <dd>{children}</dd>
    </div>
  )
}

function Group({
  id,
  title,
  children,
}: {
  id: string
  title: string
  children: ReactNode
}) {
  return (
    <section className="detail-group" aria-labelledby={id}>
      <h3 id={id}>{title}</h3>
      <dl className="kv">{children}</dl>
    </section>
  )
}

/** Customer, amount, and status badges: the at-a-glance header of a refund. */
export function RefundSummary({ refund }: Props) {
  return (
    <header className="detail-summary">
      <div className="detail-summary-main">
        <p className="detail-customer">{refund.customer_name}</p>
        <p className="detail-amount">{formatMoney(refund.amount_cents, refund.currency)}</p>
      </div>
      <ul className="badge-row" aria-label="Refund status, payment status, and risk">
        <li>
          <span className={`tag tag-${refund.refund_status}`}>
            <span className="visually-hidden">Refund status: </span>
            {REFUND_STATUS_LABELS[refund.refund_status]}
          </span>
        </li>
        <li>
          <span className={`tag tag-${refund.payment_status}`}>
            <span className="visually-hidden">Payment status: </span>
            {PAYMENT_STATUS_LABELS[refund.payment_status]}
          </span>
        </li>
        <li>
          <span className={`tag tag-${refund.risk_level}`}>
            <span className="visually-hidden">Risk: </span>
            {RISK_LABELS[refund.risk_level]} risk
          </span>
        </li>
      </ul>
      <p className="detail-ids">
        <span>
          Transaction <code>{refund.transaction_reference}</code>
        </span>
        <span>
          Customer <code>{refund.customer_reference}</code>
        </span>
        <span>
          Refund <code>{refund.id}</code>
        </span>
      </p>
    </header>
  )
}

/** Remaining metadata grouped into Refund, Transaction, and Activity sections. */
export function RefundFacts({ refund }: Props) {
  return (
    <div className="detail-groups">
      <Group id="detail-group-refund" title="Refund">
        <Fact label="Reason">{humanizeKey(refund.reason_code)}</Fact>
        <Fact label="Status">{REFUND_STATUS_LABELS[refund.refund_status]}</Fact>
        <Fact label="Risk">{RISK_LABELS[refund.risk_level]}</Fact>
        <Fact label="Created">
          <Timestamp value={refund.created_at} />
        </Fact>
        <Fact label="Updated">
          <Timestamp value={refund.updated_at} />
        </Fact>
      </Group>
      <Group id="detail-group-transaction" title="Transaction">
        <Fact label="Reference">
          <code>{refund.transaction_reference}</code>
        </Fact>
        <Fact label="Amount">{formatMoney(refund.amount_cents, refund.currency)}</Fact>
        <Fact label="Currency">{refund.currency}</Fact>
        <Fact label="Payment">{PAYMENT_STATUS_LABELS[refund.payment_status]}</Fact>
        <Fact label="Customer">
          {refund.customer_name} <code>{refund.customer_reference}</code>
        </Fact>
      </Group>
      <Group id="detail-group-activity" title="Activity">
        {refund.last_action ? (
          <>
            <Fact label="Last action">{AUDIT_ACTION_LABELS[refund.last_action]}</Fact>
            <Fact label="By">{refund.last_action_by ?? '—'}</Fact>
            <Fact label="At">
              {refund.last_action_at ? <Timestamp value={refund.last_action_at} /> : '—'}
            </Fact>
            <Fact label="Reason">{refund.last_action_reason ?? '—'}</Fact>
          </>
        ) : (
          <Fact label="Last action">
            <span className="muted">None recorded yet</span>
          </Fact>
        )}
      </Group>
    </div>
  )
}
