from collections.abc import Sequence

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.models import (
    AuditAction,
    AuditEvent,
    DemoUser,
    EntityType,
    Environment,
    FeatureFlag,
    RefundCase,
    RefundStatus,
    RiskLevel,
)


def get_demo_user(session: Session, user_id: str) -> DemoUser | None:
    return session.get(DemoUser, user_id)


def list_demo_users(session: Session) -> Sequence[DemoUser]:
    return session.scalars(select(DemoUser).order_by(DemoUser.id)).all()


def count_demo_users(session: Session) -> int:
    return session.scalar(select(func.count()).select_from(DemoUser)) or 0


def list_refunds(
    session: Session,
    *,
    search: str | None = None,
    status: RefundStatus | None = None,
    risk_level: RiskLevel | None = None,
) -> Sequence[RefundCase]:
    stmt = select(RefundCase)
    if search:
        pattern = f"%{search.strip().lower()}%"
        stmt = stmt.where(
            or_(
                func.lower(RefundCase.customer_name).like(pattern),
                func.lower(RefundCase.customer_reference).like(pattern),
                func.lower(RefundCase.transaction_reference).like(pattern),
            )
        )
    if status is not None:
        stmt = stmt.where(RefundCase.refund_status == status)
    if risk_level is not None:
        stmt = stmt.where(RefundCase.risk_level == risk_level)
    stmt = stmt.order_by(RefundCase.created_at.desc(), RefundCase.id.asc())
    return session.scalars(stmt).all()


def get_refund(session: Session, refund_id: str) -> RefundCase | None:
    return session.get(RefundCase, refund_id)


def list_feature_flags(
    session: Session, *, environment: Environment | None = None
) -> Sequence[FeatureFlag]:
    stmt = select(FeatureFlag)
    if environment is not None:
        stmt = stmt.where(FeatureFlag.environment == environment)
    stmt = stmt.order_by(FeatureFlag.key.asc(), FeatureFlag.environment.asc())
    return session.scalars(stmt).all()


def get_feature_flag(session: Session, flag_id: str) -> FeatureFlag | None:
    return session.get(FeatureFlag, flag_id)


def list_audit_events(
    session: Session,
    *,
    entity_type: EntityType | None = None,
    entity_id: str | None = None,
    actor_user_id: str | None = None,
    action: AuditAction | None = None,
) -> Sequence[AuditEvent]:
    stmt = select(AuditEvent)
    if entity_type is not None:
        stmt = stmt.where(AuditEvent.entity_type == entity_type)
    if entity_id:
        stmt = stmt.where(AuditEvent.entity_id == entity_id)
    if actor_user_id:
        stmt = stmt.where(AuditEvent.actor_user_id == actor_user_id)
    if action is not None:
        stmt = stmt.where(AuditEvent.action == action)
    stmt = stmt.order_by(AuditEvent.occurred_at.desc(), AuditEvent.id.asc())
    return session.scalars(stmt).all()


def get_audit_event(session: Session, event_id: str) -> AuditEvent | None:
    return session.get(AuditEvent, event_id)
