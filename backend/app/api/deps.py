from typing import Annotated

from fastapi import Depends
from sqlalchemy.orm import Session

from app.db import get_session
from app.identity import CurrentUser, get_current_user

DbSession = Annotated[Session, Depends(get_session)]
Actor = Annotated[CurrentUser, Depends(get_current_user)]
