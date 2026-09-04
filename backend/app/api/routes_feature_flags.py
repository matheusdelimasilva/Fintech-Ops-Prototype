from fastapi import APIRouter

from app import feature_flag_service, repositories
from app.api.deps import Actor, DbSession
from app.errors import NotFoundError
from app.feature_flag_service import FlagChanges
from app.identity import CurrentUser
from app.models import Environment, FeatureFlag
from app.schemas import FeatureFlagOut, FeatureFlagPatch

router = APIRouter(prefix="/api/feature-flags", tags=["feature-flags"])


def _flag_out(actor: CurrentUser, flag: FeatureFlag) -> FeatureFlagOut:
    return FeatureFlagOut(
        id=flag.id,
        key=flag.key,
        description=flag.description,
        environment=flag.environment,
        enabled=flag.enabled,
        rollout_percent=flag.rollout_percent,
        updated_at=flag.updated_at,
        can_edit=feature_flag_service.can_edit(actor, flag),
        requires_confirmation=feature_flag_service.requires_confirmation(flag),
    )


@router.get("", response_model=list[FeatureFlagOut])
def list_feature_flags(
    actor: Actor, session: DbSession, environment: Environment | None = None
) -> list[FeatureFlagOut]:
    flags = repositories.list_feature_flags(session, environment=environment)
    return [_flag_out(actor, flag) for flag in flags]


@router.get("/{flag_id}", response_model=FeatureFlagOut)
def read_feature_flag(flag_id: str, actor: Actor, session: DbSession) -> FeatureFlagOut:
    flag = repositories.get_feature_flag(session, flag_id)
    if flag is None:
        raise NotFoundError("Feature flag not found.", details={"flag_id": flag_id})
    return _flag_out(actor, flag)


@router.patch("/{flag_id}", response_model=FeatureFlagOut)
def update_feature_flag(
    flag_id: str, body: FeatureFlagPatch, actor: Actor, session: DbSession
) -> FeatureFlagOut:
    flag = feature_flag_service.update_feature_flag(
        session,
        actor,
        flag_id,
        FlagChanges(enabled=body.enabled, rollout_percent=body.rollout_percent),
        body.reason,
        confirm_production=body.confirm_production,
    )
    return _flag_out(actor, flag)
