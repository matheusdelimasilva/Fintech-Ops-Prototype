"""Deterministic synthetic seed data. All identities, customers, and transactions are fake.

Usage:
    python -m app.seed           # create tables and seed only if the database is empty
    python -m app.seed --reset   # drop everything and reseed
"""

import argparse
from datetime import datetime

from sqlalchemy import Engine
from sqlalchemy.orm import Session

from app import repositories
from app.db import create_tables, database_url, drop_tables, get_engine, make_session_factory
from app.models import (
    AuditAction,
    AuditEvent,
    DemoUser,
    EntityType,
    Environment,
    FeatureFlag,
    PaymentStatus,
    RefundCase,
    RefundStatus,
    RiskLevel,
    Role,
)

USER_SAM = "user_sam_support"
USER_OLIVIA = "user_olivia_ops"
USER_AVERY = "user_avery_admin"

SUPPORT_LIMIT_CENTS = 50_000
OPS_LIMIT_CENTS = 500_000


def _at(day: int, hour: int, minute: int = 0) -> datetime:
    return datetime(2026, 1, day, hour, minute, 0)


def demo_users() -> list[DemoUser]:
    return [
        DemoUser(id=USER_SAM, display_name="Sam Support", role=Role.SUPPORT_AGENT),
        DemoUser(id=USER_OLIVIA, display_name="Olivia Ops", role=Role.OPERATIONS_MANAGER),
        DemoUser(id=USER_AVERY, display_name="Avery Admin", role=Role.ADMIN),
    ]


def _refund(
    number: int,
    *,
    customer_name: str,
    amount_cents: int,
    risk_level: RiskLevel,
    reason_code: str,
    created_at: datetime,
    refund_status: RefundStatus = RefundStatus.PENDING,
    payment_status: PaymentStatus = PaymentStatus.SETTLED,
    updated_at: datetime | None = None,
    last_action: AuditAction | None = None,
    last_action_by: str | None = None,
    last_action_reason: str | None = None,
    last_action_at: datetime | None = None,
) -> RefundCase:
    return RefundCase(
        id=f"rfnd_{number:03d}",
        customer_name=customer_name,
        customer_reference=f"CUST-{1000 + number}",
        transaction_reference=f"TXN-2026-{number:04d}",
        amount_cents=amount_cents,
        currency="USD",
        payment_status=payment_status,
        refund_status=refund_status,
        risk_level=risk_level,
        reason_code=reason_code,
        created_at=created_at,
        updated_at=updated_at or created_at,
        last_action=last_action,
        last_action_by=last_action_by,
        last_action_reason=last_action_reason,
        last_action_at=last_action_at,
    )


def refund_cases() -> list[RefundCase]:
    return [
        _refund(
            1,
            customer_name="Priya Natarajan",
            amount_cents=31_240,
            risk_level=RiskLevel.LOW,
            reason_code="duplicate_charge",
            created_at=_at(5, 9, 15),
        ),
        _refund(
            2,
            customer_name="Marcus Bell",
            amount_cents=SUPPORT_LIMIT_CENTS,
            risk_level=RiskLevel.LOW,
            reason_code="item_not_received",
            created_at=_at(5, 10, 40),
        ),
        _refund(
            3,
            customer_name="Chen Wei",
            amount_cents=SUPPORT_LIMIT_CENTS + 1,
            risk_level=RiskLevel.MEDIUM,
            reason_code="item_not_received",
            created_at=_at(5, 14, 5),
        ),
        _refund(
            4,
            customer_name="Fatima Al-Sayed",
            amount_cents=245_000,
            risk_level=RiskLevel.MEDIUM,
            reason_code="service_cancelled",
            created_at=_at(6, 8, 30),
        ),
        _refund(
            5,
            customer_name="Diego Ramirez",
            amount_cents=OPS_LIMIT_CENTS,
            risk_level=RiskLevel.MEDIUM,
            reason_code="billing_error",
            created_at=_at(6, 11, 0),
        ),
        _refund(
            6,
            customer_name="Hannah Fischer",
            amount_cents=OPS_LIMIT_CENTS + 1,
            risk_level=RiskLevel.HIGH,
            reason_code="billing_error",
            created_at=_at(6, 16, 45),
        ),
        _refund(
            7,
            customer_name="Northwind Traders LLC",
            amount_cents=1_230_000,
            risk_level=RiskLevel.HIGH,
            reason_code="contract_termination",
            payment_status=PaymentStatus.DISPUTED,
            created_at=_at(7, 9, 0),
        ),
        _refund(
            8,
            customer_name="Aiko Tanaka",
            amount_cents=12_999,
            risk_level=RiskLevel.LOW,
            reason_code="duplicate_charge",
            created_at=_at(4, 13, 20),
            refund_status=RefundStatus.APPROVED,
            updated_at=_at(4, 15, 2),
            last_action=AuditAction.REFUND_APPROVED,
            last_action_by="Sam Support",
            last_action_reason="Duplicate charge confirmed against transaction history.",
            last_action_at=_at(4, 15, 2),
        ),
        _refund(
            9,
            customer_name="Liam O'Connor",
            amount_cents=89_900,
            risk_level=RiskLevel.HIGH,
            reason_code="suspected_fraud",
            payment_status=PaymentStatus.DISPUTED,
            created_at=_at(4, 9, 45),
            refund_status=RefundStatus.REJECTED,
            updated_at=_at(4, 17, 30),
            last_action=AuditAction.REFUND_REJECTED,
            last_action_by="Olivia Ops",
            last_action_reason="Chargeback already filed by the card issuer.",
            last_action_at=_at(4, 17, 30),
        ),
        _refund(
            10,
            customer_name="Grace Okafor",
            amount_cents=76_500,
            risk_level=RiskLevel.MEDIUM,
            reason_code="quality_complaint",
            created_at=_at(7, 10, 10),
            refund_status=RefundStatus.ESCALATED,
            updated_at=_at(7, 10, 55),
            last_action=AuditAction.REFUND_ESCALATED,
            last_action_by="Sam Support",
            last_action_reason="Amount exceeds support approval limit; needs manager review.",
            last_action_at=_at(7, 10, 55),
        ),
        _refund(
            11,
            customer_name="Sofia Rossi",
            amount_cents=4_575,
            risk_level=RiskLevel.LOW,
            reason_code="accidental_purchase",
            payment_status=PaymentStatus.CAPTURED,
            created_at=_at(8, 8, 5),
        ),
        _refund(
            12,
            customer_name="Ethan Walker",
            amount_cents=150_000,
            risk_level=RiskLevel.HIGH,
            reason_code="suspected_fraud",
            payment_status=PaymentStatus.DISPUTED,
            created_at=_at(9, 12, 30),
        ),
    ]


def feature_flags() -> list[FeatureFlag]:
    return [
        FeatureFlag(
            id="flag_instant_refunds_staging",
            key="instant_refunds",
            description="Issue refunds under $50 without manual review.",
            environment=Environment.STAGING,
            enabled=True,
            rollout_percent=100,
            updated_at=_at(3, 10, 0),
        ),
        FeatureFlag(
            id="flag_instant_refunds_production",
            key="instant_refunds",
            description="Issue refunds under $50 without manual review.",
            environment=Environment.PRODUCTION,
            enabled=False,
            rollout_percent=0,
            updated_at=_at(3, 10, 5),
        ),
        FeatureFlag(
            id="flag_bulk_export_staging",
            key="bulk_export",
            description="Allow CSV export of the refund queue.",
            environment=Environment.STAGING,
            enabled=True,
            rollout_percent=50,
            updated_at=_at(5, 16, 20),
        ),
        FeatureFlag(
            id="flag_new_risk_scoring_production",
            key="new_risk_scoring",
            description="Use the v2 risk model when labelling refund cases.",
            environment=Environment.PRODUCTION,
            enabled=True,
            rollout_percent=10,
            updated_at=_at(8, 9, 0),
        ),
    ]


def _refund_snapshot(refund: RefundCase, status: RefundStatus) -> dict[str, object]:
    return {
        "refund_status": status.value,
        "amount_cents": refund.amount_cents,
        "currency": refund.currency,
        "risk_level": refund.risk_level.value,
    }


def audit_events(refunds: list[RefundCase]) -> list[AuditEvent]:
    by_id = {refund.id: refund for refund in refunds}
    approved = by_id["rfnd_008"]
    rejected = by_id["rfnd_009"]
    escalated = by_id["rfnd_010"]
    return [
        AuditEvent(
            id="evt_seed_001",
            occurred_at=approved.last_action_at,
            actor_user_id=USER_SAM,
            actor_display_name="Sam Support",
            actor_role=Role.SUPPORT_AGENT,
            action=AuditAction.REFUND_APPROVED,
            entity_type=EntityType.REFUND,
            entity_id=approved.id,
            before_state=_refund_snapshot(approved, RefundStatus.PENDING),
            after_state=_refund_snapshot(approved, RefundStatus.APPROVED),
            reason=approved.last_action_reason or "",
        ),
        AuditEvent(
            id="evt_seed_002",
            occurred_at=rejected.last_action_at,
            actor_user_id=USER_OLIVIA,
            actor_display_name="Olivia Ops",
            actor_role=Role.OPERATIONS_MANAGER,
            action=AuditAction.REFUND_REJECTED,
            entity_type=EntityType.REFUND,
            entity_id=rejected.id,
            before_state=_refund_snapshot(rejected, RefundStatus.PENDING),
            after_state=_refund_snapshot(rejected, RefundStatus.REJECTED),
            reason=rejected.last_action_reason or "",
        ),
        AuditEvent(
            id="evt_seed_003",
            occurred_at=escalated.last_action_at,
            actor_user_id=USER_SAM,
            actor_display_name="Sam Support",
            actor_role=Role.SUPPORT_AGENT,
            action=AuditAction.REFUND_ESCALATED,
            entity_type=EntityType.REFUND,
            entity_id=escalated.id,
            before_state=_refund_snapshot(escalated, RefundStatus.PENDING),
            after_state=_refund_snapshot(escalated, RefundStatus.ESCALATED),
            reason=escalated.last_action_reason or "",
        ),
    ]


def is_seeded(session: Session) -> bool:
    return repositories.count_demo_users(session) > 0


def seed(session: Session) -> None:
    refunds = refund_cases()
    session.add_all(demo_users())
    session.add_all(refunds)
    session.add_all(feature_flags())
    session.add_all(audit_events(refunds))
    session.commit()


def seed_if_empty(engine: Engine) -> bool:
    create_tables(engine)
    with make_session_factory(engine)() as session:
        if is_seeded(session):
            return False
        seed(session)
        return True


def reset(engine: Engine) -> None:
    drop_tables(engine)
    create_tables(engine)
    with make_session_factory(engine)() as session:
        seed(session)


def main() -> None:
    parser = argparse.ArgumentParser(description="Seed the Fintech Ops Console demo database.")
    parser.add_argument("--reset", action="store_true", help="Drop all tables and reseed.")
    args = parser.parse_args()

    engine = get_engine()
    if args.reset:
        reset(engine)
        print(f"Reset and reseeded {database_url()}")
    elif seed_if_empty(engine):
        print(f"Seeded empty database {database_url()}")
    else:
        print(f"Database {database_url()} already seeded; use --reset to start over.")


if __name__ == "__main__":
    main()
