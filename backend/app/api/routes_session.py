from fastapi import APIRouter

from app import repositories
from app.api.deps import Actor, DbSession
from app.policy import policy_for
from app.schemas import DemoUserOut, PolicyOut, SessionOut

IDENTITY_NOTE = (
    "Synthetic demo identity: the browser sends only X-Demo-User-Id and the server resolves "
    "role and permissions. There is no real authentication, SSO, or session management."
)

router = APIRouter(prefix="/api/session", tags=["session"])


@router.get("", response_model=SessionOut)
def read_session(actor: Actor, session: DbSession) -> SessionOut:
    policy = policy_for(actor.role)
    return SessionOut(
        user=DemoUserOut(id=actor.id, display_name=actor.display_name, role=actor.role),
        policy=PolicyOut(
            approval_limit_cents=policy.approval_limit_cents,
            can_edit_staging_flags=policy.can_edit_staging_flags,
            can_edit_production_flags=policy.can_edit_production_flags,
            can_escalate_refunds=policy.can_escalate_refunds,
        ),
        available_users=[
            DemoUserOut.model_validate(user) for user in repositories.list_demo_users(session)
        ],
        identity_note=IDENTITY_NOTE,
    )
