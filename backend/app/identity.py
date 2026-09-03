"""Synthetic demo identity. The browser sends only a demo user ID; role and permissions
are resolved from server-side data and never trusted from the request."""

from dataclasses import dataclass
from typing import Annotated

from fastapi import Depends
from fastapi.security import APIKeyHeader
from sqlalchemy.orm import Session

from app import repositories
from app.db import get_session
from app.errors import MissingIdentityError, UnknownIdentityError
from app.models import Role

DEMO_USER_HEADER = "X-Demo-User-Id"

demo_user_header = APIKeyHeader(
    name=DEMO_USER_HEADER,
    auto_error=False,
    scheme_name="DemoUserId",
    description="ID of a server-defined synthetic demo user. Roles are never sent by the client.",
)


@dataclass(frozen=True)
class CurrentUser:
    id: str
    display_name: str
    role: Role


def get_current_user(
    demo_user_id: Annotated[str | None, Depends(demo_user_header)],
    session: Annotated[Session, Depends(get_session)],
) -> CurrentUser:
    if demo_user_id is None or not demo_user_id.strip():
        raise MissingIdentityError(f"Missing required {DEMO_USER_HEADER} header.")
    user = repositories.get_demo_user(session, demo_user_id.strip())
    if user is None:
        raise UnknownIdentityError(
            "Unknown demo user.", details={"demo_user_id": demo_user_id.strip()}
        )
    return CurrentUser(id=user.id, display_name=user.display_name, role=user.role)
