from fastapi import APIRouter, Query

from app import repositories
from app.api.deps import Actor, DbSession
from app.errors import NotFoundError
from app.models import RefundStatus, RiskLevel
from app.schemas import RefundOut

router = APIRouter(prefix="/api/refunds", tags=["refunds"])


@router.get("", response_model=list[RefundOut])
def list_refunds(
    _: Actor,
    session: DbSession,
    search: str | None = Query(default=None, max_length=120),
    status: RefundStatus | None = None,
    risk_level: RiskLevel | None = None,
) -> list[RefundOut]:
    refunds = repositories.list_refunds(
        session, search=search, status=status, risk_level=risk_level
    )
    return [RefundOut.model_validate(refund) for refund in refunds]


@router.get("/{refund_id}", response_model=RefundOut)
def read_refund(refund_id: str, _: Actor, session: DbSession) -> RefundOut:
    refund = repositories.get_refund(session, refund_id)
    if refund is None:
        raise NotFoundError("Refund not found.", details={"refund_id": refund_id})
    return RefundOut.model_validate(refund)
