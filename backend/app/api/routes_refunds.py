from fastapi import APIRouter, Query
from sqlalchemy.orm import Session

from app import refund_service, repositories
from app.api.deps import Actor, DbSession
from app.errors import NotFoundError
from app.identity import CurrentUser
from app.models import RefundCase, RefundStatus, RiskLevel
from app.policy import RefundAction
from app.schemas import RefundActionRequest, RefundOut

router = APIRouter(prefix="/api/refunds", tags=["refunds"])


def _refund_out(actor: CurrentUser, refund: RefundCase) -> RefundOut:
    columns = {
        name: getattr(refund, name) for name in RefundOut.model_fields if name != "allowed_actions"
    }
    return RefundOut(**columns, allowed_actions=refund_service.allowed_actions(actor, refund))


@router.get("", response_model=list[RefundOut])
def list_refunds(
    actor: Actor,
    session: DbSession,
    search: str | None = Query(default=None, max_length=120),
    status: RefundStatus | None = None,
    risk_level: RiskLevel | None = None,
) -> list[RefundOut]:
    refunds = repositories.list_refunds(
        session, search=search, status=status, risk_level=risk_level
    )
    return [_refund_out(actor, refund) for refund in refunds]


@router.get("/{refund_id}", response_model=RefundOut)
def read_refund(refund_id: str, actor: Actor, session: DbSession) -> RefundOut:
    refund = repositories.get_refund(session, refund_id)
    if refund is None:
        raise NotFoundError("Refund not found.", details={"refund_id": refund_id})
    return _refund_out(actor, refund)


def _perform(
    action: RefundAction,
    refund_id: str,
    body: RefundActionRequest,
    actor: CurrentUser,
    session: Session,
) -> RefundOut:
    refund = refund_service.perform_refund_action(session, actor, refund_id, action, body.reason)
    return _refund_out(actor, refund)


@router.post("/{refund_id}/approve", response_model=RefundOut)
def approve_refund(
    refund_id: str, body: RefundActionRequest, actor: Actor, session: DbSession
) -> RefundOut:
    return _perform(RefundAction.APPROVE, refund_id, body, actor, session)


@router.post("/{refund_id}/reject", response_model=RefundOut)
def reject_refund(
    refund_id: str, body: RefundActionRequest, actor: Actor, session: DbSession
) -> RefundOut:
    return _perform(RefundAction.REJECT, refund_id, body, actor, session)


@router.post("/{refund_id}/escalate", response_model=RefundOut)
def escalate_refund(
    refund_id: str, body: RefundActionRequest, actor: Actor, session: DbSession
) -> RefundOut:
    return _perform(RefundAction.ESCALATE, refund_id, body, actor, session)
