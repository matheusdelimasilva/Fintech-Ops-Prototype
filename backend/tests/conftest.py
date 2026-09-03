from collections.abc import Iterator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import Engine

from app import db, seed
from app.main import app

SAM = {"X-Demo-User-Id": "user_sam_support"}
OLIVIA = {"X-Demo-User-Id": "user_olivia_ops"}
AVERY = {"X-Demo-User-Id": "user_avery_admin"}


@pytest.fixture
def engine(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Iterator[Engine]:
    url = f"sqlite:///{tmp_path / 'test.db'}"
    monkeypatch.setenv("DATABASE_URL", url)
    db.get_engine.cache_clear()
    engine = db.make_engine(url)
    yield engine
    engine.dispose()
    db.get_engine.cache_clear()


@pytest.fixture
def seeded_engine(engine: Engine) -> Engine:
    seed.reset(engine)
    return engine


@pytest.fixture
def client(seeded_engine: Engine) -> Iterator[TestClient]:
    factory = db.make_session_factory(seeded_engine)

    def override_get_session() -> Iterator[db.Session]:
        with factory() as session:
            yield session

    app.dependency_overrides[db.get_session] = override_get_session
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()
