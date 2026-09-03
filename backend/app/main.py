from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import routes_audit, routes_feature_flags, routes_refunds, routes_session
from app.db import get_engine
from app.errors import register_exception_handlers
from app.seed import seed_if_empty


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    seed_if_empty(get_engine())
    yield


app = FastAPI(
    title="Fintech Ops Console API",
    version="0.2.0",
    description=(
        "Local evaluation prototype. All data and identities are synthetic; "
        "identity is a demo user ID header resolved server-side, not real authentication."
    ),
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

register_exception_handlers(app)

app.include_router(routes_session.router)
app.include_router(routes_refunds.router)
app.include_router(routes_feature_flags.router)
app.include_router(routes_audit.router)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "service": "fintech-ops-console-api"}
