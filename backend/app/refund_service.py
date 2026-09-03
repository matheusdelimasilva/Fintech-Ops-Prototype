"""Refund workflow: load -> authorize -> guarded state transition -> audit -> one commit.

Nothing is persisted unless every step succeeds; a failure at any point leaves the refund
and the audit table untouched.
"""

from datetime import datetime, timezone

from sqlalchemy import update
from sqlalchemy.orm import Session

from app import repositories
from app.audit import record_refund_event, refund_snapshot
from app.errors import (
    ActionNotPermittedForRoleError,
    AppError,
    ApprovalLimitExceededError,
    InvalidStateTransitionError,
    NotFoundError,
    UnsupportedCurrencyError,
)
from app.identity import CurrentUser
from app.models import AuditAction, RefundCase, RefundStatus
from app.policy import (
    ACTION_NOT_PERMITTED_FOR_ROLE,
    APPROVAL_LIMIT_EXCEEDED,
    UNSUPPORTED_CURRENCY,
    Denial,
    RefundAction,
    refund_action_denial,
)

ALLOWED_FROM: dict[RefundAction, frozenset[RefundStatus]] = {
    RefundAction.APPROVE: frozenset({RefundStatus.PENDING, RefundStatus.ESCALATED}),
    RefundAction.REJECT: frozenset({RefundStatus.PENDING, RefundStatus.ESCALATED}),
    RefundAction.ESCALATE: frozenset({RefundStatus.PENDING}),
}

TARGET_STATUS: dict[RefundAction, RefundStatus] = {
    RefundAction.APPROVE: RefundStatus.APPROVED,
    RefundAction.REJECT: RefundStatus.REJECTED,
    RefundAction.ESCALATE: RefundStatus.ESCALATED,
}

AUDIT_ACTION: dict[RefundAction, AuditAction] = {
    RefundAction.APPROVE: AuditAction.REFUND_APPROVED,
    RefundAction.REJECT: AuditAction.REFUND_REJECTED,
    RefundAction.ESCALATE: AuditAction.REFUND_ESCALATED,
}

DENIAL_ERRORS: dict[str, type[AppError]] = {
    APPROVAL_LIMIT_EXCEEDED: ApprovalLimitExceededError,
    ACTION_NOT_PERMITTED_FOR_ROLE: ActionNotPermittedForRoleError,
    UNSUPPORTED_CURRENCY: UnsupportedCurrencyError,
}


def _utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def _denial_for(actor: CurrentUser, action: RefundAction, refund: RefundCase) -> Denial | None:
    return refund_action_denial(actor.role, action, refund.amount_cents, refund.currency)


def _transition_error(
    action: RefundAction, current_status: RefundStatus, message: str
) -> InvalidStateTransitionError:
    return InvalidStateTransitionError(
        message,
        details={
            "action": action.value,
            "current_status": current_status.value,
            "allowed_from": sorted(status.value for status in ALLOWED_FROM[action]),
        },
    )


def allowed_actions(actor: CurrentUser, refund: RefundCase) -> list[RefundAction]:
    """UI hint only: the same checks run again inside `perform_refund_action`."""
    return [
        action
        for action in RefundAction
        if _denial_for(actor, action, refund) is None
        and refund.refund_status in ALLOWED_FROM[action]
    ]


def perform_refund_action(
    session: Session,
    actor: CurrentUser,
    refund_id: str,
    action: RefundAction,
    reason: str,
) -> RefundCase:
    refund = repositories.get_refund(session, refund_id)
    if refund is None:
        raise NotFoundError("Refund not found.", details={"refund_id": refund_id})

    denial = _denial_for(actor, action, refund)
    if denial is not None:
        raise DENIAL_ERRORS[denial.code](denial.message, details=denial.details)

    if refund.refund_status not in ALLOWED_FROM[action]:
        raise _transition_error(
            action,
            refund.refund_status,
            f"Cannot {action.value} a refund that is {refund.refund_status.value}.",
        )

    before_state = refund_snapshot(refund)
    now = _utcnow()
    try:
        # The status predicate makes the transition check atomic at the database: a
        # concurrent action that already moved this refund leaves zero rows to update.
        result = session.execute(
            update(RefundCase)
            .where(
                RefundCase.id == refund.id,
                RefundCase.refund_status.in_(ALLOWED_FROM[action]),
            )
            .values(
                refund_status=TARGET_STATUS[action],
                updated_at=now,
                last_action=AUDIT_ACTION[action],
                last_action_by=actor.display_name,
                last_action_reason=reason,
                last_action_at=now,
            )
        )
        session.refresh(refund)
        if result.rowcount != 1:
            raise _transition_error(
                action,
                refund.refund_status,
                f"Refund changed to {refund.refund_status.value} before this {action.value} "
                "could be applied.",
            )
        record_refund_event(
            session,
            actor=actor,
            action=AUDIT_ACTION[action],
            refund=refund,
            before_state=before_state,
            reason=reason,
            occurred_at=now,
        )
        session.commit()
    except Exception:
        session.rollback()
        raise
    return refund
