"""Audit recording. Events are append-only through the application: this module only creates."""

from datetime import datetime
from uuid import uuid4

from sqlalchemy.orm import Session

from app.identity import CurrentUser
from app.models import AuditAction, AuditEvent, EntityType, FeatureFlag, RefundCase
from app.timeutil import to_utc_iso


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


def feature_flag_snapshot(flag: FeatureFlag) -> dict[str, object]:
    """JSON-safe view of the flag fields an update can change, plus what identifies the flag."""
    return {
        "key": flag.key,
        "environment": flag.environment.value,
        "enabled": flag.enabled,
        "rollout_percent": flag.rollout_percent,
        "updated_at": to_utc_iso(flag.updated_at),
    }


def record_event(
    session: Session,
    *,
    actor: CurrentUser,
    action: AuditAction,
    entity_type: EntityType,
    entity_id: str,
    before_state: dict[str, object],
    after_state: dict[str, object],
    reason: str,
    occurred_at: datetime,
) -> AuditEvent:
    """Stage an audit event in the caller's transaction. The caller commits."""
    event = AuditEvent(
        id=f"evt_{uuid4().hex}",
        occurred_at=occurred_at,
        actor_user_id=actor.id,
        actor_display_name=actor.display_name,
        actor_role=actor.role,
        action=action,
        entity_type=entity_type,
        entity_id=entity_id,
        before_state=before_state,
        after_state=after_state,
        reason=reason,
    )
    session.add(event)
    return event
