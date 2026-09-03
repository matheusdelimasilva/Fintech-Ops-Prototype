"""Refund workflow: load -> authorize -> guarded state transition -> audit -> one commit.

Nothing is persisted unless every step succeeds; a failure at any point leaves the refund
and the audit table untouched.
"""

from dataclasses import dataclass

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
from app.timeutil import utcnow


@dataclass(frozen=True)
class Transition:
    allowed_from: frozenset[RefundStatus]
    target: RefundStatus
    audit_action: AuditAction


_DECIDABLE = frozenset({RefundStatus.PENDING, RefundStatus.ESCALATED})

TRANSITIONS: dict[RefundAction, Transition] = {
    RefundAction.APPROVE: Transition(
        allowed_from=_DECIDABLE,
        target=RefundStatus.APPROVED,
        audit_action=AuditAction.REFUND_APPROVED,
    ),
    RefundAction.REJECT: Transition(
        allowed_from=_DECIDABLE,
        target=RefundStatus.REJECTED,
        audit_action=AuditAction.REFUND_REJECTED,
    ),
    RefundAction.ESCALATE: Transition(
        allowed_from=frozenset({RefundStatus.PENDING}),
        target=RefundStatus.ESCALATED,
        audit_action=AuditAction.REFUND_ESCALATED,
    ),
}

DENIAL_ERRORS: dict[str, tuple[type[AppError], str]] = {
    APPROVAL_LIMIT_EXCEEDED: (
        ApprovalLimitExceededError,
        "Refund amount exceeds this role's approval limit.",
    ),
    ACTION_NOT_PERMITTED_FOR_ROLE: (
        ActionNotPermittedForRoleError,
        "This role may not perform this refund action.",
    ),
    UNSUPPORTED_CURRENCY: (
        UnsupportedCurrencyError,
        "Only USD refunds are supported.",
    ),
}


def _denial_for(actor: CurrentUser, action: RefundAction, refund: RefundCase) -> Denial | None:
    return refund_action_denial(actor.role, action, refund.amount_cents, refund.currency)


def _denial_error(denial: Denial) -> AppError:
    error_type, message = DENIAL_ERRORS[denial.code]
    return error_type(message, details=denial.details)


def _transition_error(
    action: RefundAction, current_status: RefundStatus, message: str
) -> InvalidStateTransitionError:
    return InvalidStateTransitionError(
        message,
        details={
            "action": action.value,
            "current_status": current_status.value,
            "allowed_from": sorted(s.value for s in TRANSITIONS[action].allowed_from),
        },
    )


def allowed_actions(actor: CurrentUser, refund: RefundCase) -> list[RefundAction]:
    """UI hint only: the same checks run again inside `perform_refund_action`."""
    return [
        action
        for action in RefundAction
        if _denial_for(actor, action, refund) is None
        and refund.refund_status in TRANSITIONS[action].allowed_from
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
        raise _denial_error(denial)

    transition = TRANSITIONS[action]
    observed_status = refund.refund_status
    if observed_status not in transition.allowed_from:
        raise _transition_error(
            action,
            observed_status,
            f"Cannot {action.value} a refund that is {observed_status.value}.",
        )

    before_state = refund_snapshot(refund)
    now = utcnow()
    try:
        # The UPDATE only applies if the row still has exactly the status captured in
        # `before_state`, so the audit event always records the true immediate transition.
        # Any concurrent change, even to another allowed status, leaves zero rows updated.
        result = session.execute(
            update(RefundCase)
            .where(
                RefundCase.id == refund.id,
                RefundCase.refund_status == observed_status,
            )
            .values(
                refund_status=transition.target,
                updated_at=now,
                last_action=transition.audit_action,
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
                f"Refund changed from {observed_status.value} to {refund.refund_status.value} "
                f"before this {action.value} could be applied.",
            )
        record_refund_event(
            session,
            actor=actor,
            action=transition.audit_action,
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
