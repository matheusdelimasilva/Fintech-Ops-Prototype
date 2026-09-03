"""Read-only audit trail. Audit events are append-only through the application: this router
intentionally exposes no create, update, or delete operations."""

from fastapi import APIRouter, Query

from app import repositories
from app.api.deps import Actor, DbSession
from app.errors import NotFoundError
from app.models import AuditAction, EntityType
from app.schemas import AuditEventOut

router = APIRouter(prefix="/api/audit-events", tags=["audit"])


@router.get("", response_model=list[AuditEventOut])
def list_audit_events(
    _: Actor,
    session: DbSession,
    entity_type: EntityType | None = None,
    entity_id: str | None = Query(default=None, max_length=64),
    actor: str | None = Query(default=None, max_length=64, description="Actor user ID"),
    action: AuditAction | None = None,
) -> list[AuditEventOut]:
    events = repositories.list_audit_events(
        session,
        entity_type=entity_type,
        entity_id=entity_id,
        actor_user_id=actor,
        action=action,
    )
    return [AuditEventOut.model_validate(event) for event in events]


@router.get("/{event_id}", response_model=AuditEventOut)
def read_audit_event(event_id: str, _: Actor, session: DbSession) -> AuditEventOut:
    event = repositories.get_audit_event(session, event_id)
    if event is None:
        raise NotFoundError("Audit event not found.", details={"event_id": event_id})
    return AuditEventOut.model_validate(event)
