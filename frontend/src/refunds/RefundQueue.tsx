import type { Refund } from '../api/types.ts'
import { navigate, refundHash } from '../router.ts'
import {
  REFUND_STATUS_LABELS,
  RISK_LABELS,
  formatDate,
  formatMoney,
} from '../shared/format.ts'

interface Props {
  refunds: Refund[]
  selectedId: string | null
}

export function RefundQueue({ refunds, selectedId }: Props) {
  return (
    <div className="table-scroll queue-scroll">
      <table className="data-table" aria-label="Refund queue">
        <thead>
          <tr>
            <th scope="col">Transaction</th>
            <th scope="col">Customer</th>
            <th scope="col" className="numeric">
              Amount
            </th>
            <th scope="col">Risk</th>
            <th scope="col">Status</th>
            <th scope="col">Created</th>
          </tr>
        </thead>
        <tbody>
          {refunds.map((refund) => {
            const selected = refund.id === selectedId
            return (
              <tr
                key={refund.id}
                className="selectable"
                aria-selected={selected}
                onClick={() => navigate(refundHash(refund.id))}
              >
                <td>
                  <a
                    className="row-link mono"
                    href={refundHash(refund.id)}
                    aria-current={selected ? 'true' : undefined}
                  >
                    {refund.transaction_reference}
                  </a>
                </td>
                <td>{refund.customer_name}</td>
                <td className="numeric">{formatMoney(refund.amount_cents, refund.currency)}</td>
                <td>
                  <span className={`tag tag-${refund.risk_level}`}>
                    {RISK_LABELS[refund.risk_level]}
                  </span>
                </td>
                <td>
                  <span className={`tag tag-${refund.refund_status}`}>
                    {REFUND_STATUS_LABELS[refund.refund_status]}
                  </span>
                </td>
                <td>
                  <time dateTime={refund.created_at}>{formatDate(refund.created_at)}</time>
                </td>
              </tr>
            )
          })}
        </tbody>
      </table>
    </div>
  )
}
