from datetime import datetime
from enum import Enum

from sqlalchemy import JSON, DateTime, Integer, String, Text
from sqlalchemy import Enum as SqlEnum
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class Role(str, Enum):
    SUPPORT_AGENT = "support_agent"
    OPERATIONS_MANAGER = "operations_manager"
    ADMIN = "admin"


class RefundStatus(str, Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    ESCALATED = "escalated"


class RiskLevel(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class PaymentStatus(str, Enum):
    CAPTURED = "captured"
    SETTLED = "settled"
    DISPUTED = "disputed"


class Environment(str, Enum):
    STAGING = "staging"
    PRODUCTION = "production"


class AuditAction(str, Enum):
    REFUND_APPROVED = "refund.approved"
    REFUND_REJECTED = "refund.rejected"
    REFUND_ESCALATED = "refund.escalated"
    FEATURE_FLAG_UPDATED = "feature_flag.updated"


class EntityType(str, Enum):
    REFUND = "refund"
    FEATURE_FLAG = "feature_flag"


def _enum(enum_cls: type[Enum]) -> SqlEnum:
    return SqlEnum(
        enum_cls,
        native_enum=False,
        create_constraint=True,
        values_callable=lambda cls: [member.value for member in cls],
        length=64,
    )


class DemoUser(Base):
    __tablename__ = "demo_users"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    display_name: Mapped[str] = mapped_column(String(120), nullable=False)
    role: Mapped[Role] = mapped_column(_enum(Role), nullable=False)


class RefundCase(Base):
    __tablename__ = "refund_cases"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    customer_name: Mapped[str] = mapped_column(String(120), nullable=False)
    customer_reference: Mapped[str] = mapped_column(String(64), nullable=False)
    transaction_reference: Mapped[str] = mapped_column(String(64), nullable=False)
    amount_cents: Mapped[int] = mapped_column(Integer, nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False)
    payment_status: Mapped[PaymentStatus] = mapped_column(_enum(PaymentStatus), nullable=False)
    refund_status: Mapped[RefundStatus] = mapped_column(_enum(RefundStatus), nullable=False)
    risk_level: Mapped[RiskLevel] = mapped_column(_enum(RiskLevel), nullable=False)
    reason_code: Mapped[str] = mapped_column(String(64), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    last_action: Mapped[AuditAction | None] = mapped_column(_enum(AuditAction), nullable=True)
    last_action_by: Mapped[str | None] = mapped_column(String(120), nullable=True)
    last_action_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    last_action_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)


class FeatureFlag(Base):
    __tablename__ = "feature_flags"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    key: Mapped[str] = mapped_column(String(120), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    environment: Mapped[Environment] = mapped_column(_enum(Environment), nullable=False)
    enabled: Mapped[bool] = mapped_column(nullable=False)
    rollout_percent: Mapped[int] = mapped_column(Integer, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)


class AuditEvent(Base):
    __tablename__ = "audit_events"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    occurred_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, index=True)
    actor_user_id: Mapped[str] = mapped_column(String(64), nullable=False)
    actor_display_name: Mapped[str] = mapped_column(String(120), nullable=False)
    actor_role: Mapped[Role] = mapped_column(_enum(Role), nullable=False)
    action: Mapped[AuditAction] = mapped_column(_enum(AuditAction), nullable=False)
    entity_type: Mapped[EntityType] = mapped_column(_enum(EntityType), nullable=False, index=True)
    entity_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    before_state: Mapped[dict[str, object]] = mapped_column(JSON, nullable=False)
    after_state: Mapped[dict[str, object]] = mapped_column(JSON, nullable=False)
    reason: Mapped[str] = mapped_column(Text, nullable=False)
