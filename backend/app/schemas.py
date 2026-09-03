from datetime import datetime, timezone
from typing import Any

from pydantic import BaseModel, ConfigDict, field_serializer

from app.models import (
    AuditAction,
    EntityType,
    Environment,
    PaymentStatus,
    RefundStatus,
    RiskLevel,
    Role,
)


def to_utc_iso(value: datetime) -> str:
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


class ApiModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    @field_serializer("*", when_used="json", check_fields=False)
    def _serialize_datetimes(self, value: Any) -> Any:
        if isinstance(value, datetime):
            return to_utc_iso(value)
        return value


class DemoUserOut(ApiModel):
    id: str
    display_name: str
    role: Role


class PolicyOut(ApiModel):
    approval_limit_cents: int | None
    can_edit_staging_flags: bool
    can_edit_production_flags: bool


class SessionOut(ApiModel):
    user: DemoUserOut
    policy: PolicyOut
    available_users: list[DemoUserOut]
    identity_note: str


class RefundOut(ApiModel):
    id: str
    customer_name: str
    customer_reference: str
    transaction_reference: str
    amount_cents: int
    currency: str
    payment_status: PaymentStatus
    refund_status: RefundStatus
    risk_level: RiskLevel
    reason_code: str
    created_at: datetime
    updated_at: datetime
    last_action: AuditAction | None
    last_action_by: str | None
    last_action_reason: str | None
    last_action_at: datetime | None


class FeatureFlagOut(ApiModel):
    id: str
    key: str
    description: str
    environment: Environment
    enabled: bool
    rollout_percent: int
    updated_at: datetime


class AuditEventOut(ApiModel):
    id: str
    occurred_at: datetime
    actor_user_id: str
    actor_display_name: str
    actor_role: Role
    action: AuditAction
    entity_type: EntityType
    entity_id: str
    before_state: dict[str, Any]
    after_state: dict[str, Any]
    reason: str
