import type { Refund } from '../api/types.ts'
import { DetailsTable, Row, Timestamp } from '../shared/DetailsTable.tsx'
import {
  AUDIT_ACTION_LABELS,
  REFUND_STATUS_LABELS,
  RISK_LABELS,
  formatMoney,
} from '../shared/format.ts'

interface Props {
  refund: Refund
}

export function RefundDetail({ refund }: Props) {
  return (
    <>
      <DetailsTable caption="Refund fields">
        <Row label="Refund id">
          <code>{refund.id}</code>
        </Row>
        <Row label="Transaction">{refund.transaction_reference}</Row>
        <Row label="Customer">
          {refund.customer_name} (<code>{refund.customer_reference}</code>)
        </Row>
        <Row label="Amount">{formatMoney(refund.amount_cents, refund.currency)}</Row>
        <Row label="Payment status">{refund.payment_status}</Row>
        <Row label="Refund status">
          <span className={`tag tag-${refund.refund_status}`}>
            {REFUND_STATUS_LABELS[refund.refund_status]}
          </span>
        </Row>
        <Row label="Risk">
          <span className={`tag tag-${refund.risk_level}`}>{RISK_LABELS[refund.risk_level]}</span>
        </Row>
        <Row label="Reason code">{refund.reason_code}</Row>
        <Row label="Created">
          <Timestamp value={refund.created_at} />
        </Row>
        <Row label="Updated">
          <Timestamp value={refund.updated_at} />
        </Row>
      </DetailsTable>

      <h3>Last action</h3>
      {refund.last_action ? (
        <DetailsTable caption="Last action">
          <Row label="Action">{AUDIT_ACTION_LABELS[refund.last_action]}</Row>
          <Row label="By">{refund.last_action_by ?? '—'}</Row>
          <Row label="At">
            {refund.last_action_at ? <Timestamp value={refund.last_action_at} /> : '—'}
          </Row>
          <Row label="Reason">{refund.last_action_reason ?? '—'}</Row>
        </DetailsTable>
      ) : (
        <p className="muted">No action has been recorded for this refund yet.</p>
      )}
    </>
  )
}
