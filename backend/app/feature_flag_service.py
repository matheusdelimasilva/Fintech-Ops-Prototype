"""Feature-flag workflow: load -> authorize -> confirm production -> reject no-op ->
guarded update -> audit -> one commit.

Same shape and guarantees as `refund_service`: nothing is persisted unless every step
succeeds, and the audit event always records the true immediate before/after states.
"""

from dataclasses import dataclass

from sqlalchemy import update
from sqlalchemy.orm import Session

from app import repositories
from app.audit import feature_flag_snapshot, record_event
from app.errors import (
    ActionNotPermittedForRoleError,
    NoChangeError,
    NotFoundError,
    ProductionConfirmationRequiredError,
    StaleUpdateError,
)
from app.identity import CurrentUser
from app.models import AuditAction, EntityType, Environment, FeatureFlag
from app.policy import feature_flag_edit_denial
from app.timeutil import utcnow

ROLLOUT_MIN = 0
ROLLOUT_MAX = 100


@dataclass(frozen=True)
class FlagChanges:
    """Fields the caller wants to set; `None` means "leave as is". At least one must be set."""

    enabled: bool | None = None
    rollout_percent: int | None = None

    def __post_init__(self) -> None:
        if self.enabled is None and self.rollout_percent is None:
            raise ValueError("FlagChanges must set at least one field")
        if self.rollout_percent is not None and not (
            ROLLOUT_MIN <= self.rollout_percent <= ROLLOUT_MAX
        ):
            raise ValueError("rollout_percent must be between 0 and 100")


def can_edit(actor: CurrentUser, flag: FeatureFlag) -> bool:
    """UI hint only: `update_feature_flag` re-runs the same policy check."""
    return feature_flag_edit_denial(actor.role, flag.environment) is None


def requires_confirmation(flag: FeatureFlag) -> bool:
    """UI hint only: `update_feature_flag` enforces the confirmation itself."""
    return flag.environment is Environment.PRODUCTION


def update_feature_flag(
    session: Session,
    actor: CurrentUser,
    flag_id: str,
    changes: FlagChanges,
    reason: str,
    confirm_production: bool,
) -> FeatureFlag:
    flag = repositories.get_feature_flag(session, flag_id)
    if flag is None:
        raise NotFoundError("Feature flag not found.", details={"flag_id": flag_id})

    denial = feature_flag_edit_denial(actor.role, flag.environment)
    if denial is not None:
        raise ActionNotPermittedForRoleError(
            "This role may not edit feature flags in this environment.", details=denial.details
        )

    if requires_confirmation(flag) and confirm_production is not True:
        raise ProductionConfirmationRequiredError(
            "Changing a production flag requires confirm_production to be true.",
            details={"flag_id": flag.id, "environment": flag.environment.value},
        )

    observed_enabled = flag.enabled
    observed_rollout = flag.rollout_percent
    observed_updated_at = flag.updated_at
    new_enabled = observed_enabled if changes.enabled is None else changes.enabled
    new_rollout = observed_rollout if changes.rollout_percent is None else changes.rollout_percent
    if new_enabled == observed_enabled and new_rollout == observed_rollout:
        raise NoChangeError(
            "The requested values match the flag's current values.",
            details={
                "flag_id": flag.id,
                "current": {"enabled": observed_enabled, "rollout_percent": observed_rollout},
            },
        )

    before_state = feature_flag_snapshot(flag)
    now = utcnow()
    try:
        # Guard on every observed mutable value, not just the clock, so a concurrent change
        # that happens to land in the same instant still leaves zero rows updated.
        result = session.execute(
            update(FeatureFlag)
            .where(
                FeatureFlag.id == flag.id,
                FeatureFlag.enabled == observed_enabled,
                FeatureFlag.rollout_percent == observed_rollout,
                FeatureFlag.updated_at == observed_updated_at,
            )
            .values(enabled=new_enabled, rollout_percent=new_rollout, updated_at=now)
        )
        session.refresh(flag)
        if result.rowcount != 1:
            raise StaleUpdateError(
                "The feature flag changed before this update could be applied.",
                details={
                    "flag_id": flag.id,
                    "current": {"enabled": flag.enabled, "rollout_percent": flag.rollout_percent},
                },
            )
        record_event(
            session,
            actor=actor,
            action=AuditAction.FEATURE_FLAG_UPDATED,
            entity_type=EntityType.FEATURE_FLAG,
            entity_id=flag.id,
            before_state=before_state,
            after_state=feature_flag_snapshot(flag),
            reason=reason,
            occurred_at=now,
        )
        session.commit()
    except Exception:
        session.rollback()
        raise
    return flag
