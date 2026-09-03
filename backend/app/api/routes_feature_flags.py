from fastapi import APIRouter

from app import repositories
from app.api.deps import Actor, DbSession
from app.errors import NotFoundError
from app.models import Environment
from app.schemas import FeatureFlagOut

router = APIRouter(prefix="/api/feature-flags", tags=["feature-flags"])


@router.get("", response_model=list[FeatureFlagOut])
def list_feature_flags(
    _: Actor, session: DbSession, environment: Environment | None = None
) -> list[FeatureFlagOut]:
    flags = repositories.list_feature_flags(session, environment=environment)
    return [FeatureFlagOut.model_validate(flag) for flag in flags]


@router.get("/{flag_id}", response_model=FeatureFlagOut)
def read_feature_flag(flag_id: str, _: Actor, session: DbSession) -> FeatureFlagOut:
    flag = repositories.get_feature_flag(session, flag_id)
    if flag is None:
        raise NotFoundError("Feature flag not found.", details={"flag_id": flag_id})
    return FeatureFlagOut.model_validate(flag)
