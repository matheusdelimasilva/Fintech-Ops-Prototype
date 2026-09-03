import type { Refund } from '../api/types.ts'
import {
  AUDIT_ACTION_LABELS,
  REFUND_STATUS_LABELS,
  RISK_LABELS,
  formatMoney,
  formatTimestamp,
} from '../shared/format.ts'

interface Props {
  refund: Refund
}

function Timestamp({ value }: { value: string }) {
  return <time dateTime={value}>{formatTimestamp(value)}</time>
}

export function RefundDetail({ refund }: Props) {
  return (
    <>
      <dl className="details-list">
        <div>
          <dt>Refund id</dt>
          <dd>
            <code>{refund.id}</code>
          </dd>
        </div>
        <div>
          <dt>Transaction</dt>
          <dd>{refund.transaction_reference}</dd>
        </div>
        <div>
          <dt>Customer</dt>
          <dd>
            {refund.customer_name} (<code>{refund.customer_reference}</code>)
          </dd>
        </div>
        <div>
          <dt>Amount</dt>
          <dd>{formatMoney(refund.amount_cents, refund.currency)}</dd>
        </div>
        <div>
          <dt>Payment status</dt>
          <dd>{refund.payment_status}</dd>
        </div>
        <div>
          <dt>Refund status</dt>
          <dd>
            <span className={`tag tag-${refund.refund_status}`}>
              {REFUND_STATUS_LABELS[refund.refund_status]}
            </span>
          </dd>
        </div>
        <div>
          <dt>Risk</dt>
          <dd>
            <span className={`tag tag-${refund.risk_level}`}>{RISK_LABELS[refund.risk_level]}</span>
          </dd>
        </div>
        <div>
          <dt>Reason code</dt>
          <dd>{refund.reason_code}</dd>
        </div>
        <div>
          <dt>Created</dt>
          <dd>
            <Timestamp value={refund.created_at} />
          </dd>
        </div>
        <div>
          <dt>Updated</dt>
          <dd>
            <Timestamp value={refund.updated_at} />
          </dd>
        </div>
      </dl>

      <h3>Last action</h3>
      {refund.last_action ? (
        <dl className="details-list">
          <div>
            <dt>Action</dt>
            <dd>{AUDIT_ACTION_LABELS[refund.last_action]}</dd>
          </div>
          <div>
            <dt>By</dt>
            <dd>{refund.last_action_by ?? '—'}</dd>
          </div>
          <div>
            <dt>At</dt>
            <dd>{refund.last_action_at ? <Timestamp value={refund.last_action_at} /> : '—'}</dd>
          </div>
          <div>
            <dt>Reason</dt>
            <dd>{refund.last_action_reason ?? '—'}</dd>
          </div>
        </dl>
      ) : (
        <p className="muted">No action has been recorded for this refund yet.</p>
      )}
    </>
  )
}
