"""Audit recording. Events are append-only through the application: this module only creates."""

from app.models import RefundCase
from app.schemas import to_utc_iso


def refund_snapshot(refund: RefundCase) -> dict[str, object]:
    """JSON-safe view of the refund fields an action can change, plus the money it concerns.

    Used for both seeded and live audit events so the two never differ in shape.
    """
    return {
        "refund_status": refund.refund_status.value,
        "amount_cents": refund.amount_cents,
        "currency": refund.currency,
        "risk_level": refund.risk_level.value,
        "last_action": refund.last_action.value if refund.last_action else None,
        "last_action_by": refund.last_action_by,
        "last_action_reason": refund.last_action_reason,
        "last_action_at": to_utc_iso(refund.last_action_at) if refund.last_action_at else None,
    }
