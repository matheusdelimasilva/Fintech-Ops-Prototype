from datetime import datetime
from typing import Annotated, Any

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    StrictBool,
    StrictInt,
    StringConstraints,
    field_serializer,
    field_validator,
    model_validator,
)

from app.models import (
    AuditAction,
    EntityType,
    Environment,
    PaymentStatus,
    RefundStatus,
    RiskLevel,
    Role,
)
from app.policy import ROLLOUT_MAX, ROLLOUT_MIN, RefundAction
from app.timeutil import to_utc_iso


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
    can_escalate_refunds: bool


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
    allowed_actions: list[RefundAction]


ActionReason = Annotated[
    str, StringConstraints(strip_whitespace=True, min_length=1, max_length=1000)
]


class RefundActionRequest(BaseModel):
    reason: ActionReason


class FeatureFlagOut(ApiModel):
    id: str
    key: str
    description: str
    environment: Environment
    enabled: bool
    rollout_percent: int
    updated_at: datetime
    # Server-computed hints for the requesting user. PATCH re-checks both independently.
    can_edit: bool
    requires_confirmation: bool


class FeatureFlagPatch(BaseModel):
    """Partial update. Omitted fields are left unchanged; explicit `null` is rejected.

    Strict types: "true", 1, or "50" are not accepted in place of real JSON booleans/integers,
    so the production confirmation in particular must be a literal `true`.
    """

    enabled: StrictBool | None = None
    rollout_percent: StrictInt | None = Field(default=None, ge=ROLLOUT_MIN, le=ROLLOUT_MAX)
    reason: ActionReason
    confirm_production: StrictBool = False

    @field_validator("enabled", "rollout_percent", mode="before")
    @classmethod
    def _reject_explicit_null(cls, value: Any) -> Any:
        if value is None:
            raise ValueError("Field may be omitted but not null.")
        return value

    @model_validator(mode="after")
    def _require_a_change_field(self) -> "FeatureFlagPatch":
        if self.enabled is None and self.rollout_percent is None:
            raise ValueError("Provide at least one of 'enabled' or 'rollout_percent'.")
        return self


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
