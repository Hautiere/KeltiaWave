import os
from pathlib import Path
import sys

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool


BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

os.environ.setdefault("BOOTSTRAP_CLASS_USERS", "false")
os.environ.setdefault("AUDIO_STORAGE", "local")
os.environ.setdefault("DATABASE_URL", "sqlite://")

from app.auth import create_access_token  # noqa: E402
from app.db import Base, get_db  # noqa: E402
from app.main import app  # noqa: E402
from app.models.user import User  # noqa: E402
from app.learning import storage as learning_storage  # noqa: E402


@pytest.fixture()
def db_session():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    session = sessionmaker(autocommit=False, autoflush=False, bind=engine)()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=engine)


@pytest.fixture()
def client(db_session, tmp_path, monkeypatch):
    media_dir = tmp_path / "learning-media"
    media_dir.mkdir()
    monkeypatch.setattr(learning_storage, "LOCAL_LEARNING_DIR", media_dir)
    monkeypatch.setattr(learning_storage.corpus_storage, "s3_enabled", lambda: False)

    def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    try:
        with TestClient(app) as test_client:
            yield test_client
    finally:
        app.dependency_overrides.clear()


@pytest.fixture()
def users(db_session):
    admin = User(
        email="admin-learning@example.test",
        password_hash="unused",
        display_name="Learning Admin",
        profile_type="admin",
        role="admin",
        auth_status="verified",
        active=True,
    )
    learner = User(
        email="learner-learning@example.test",
        password_hash="unused",
        display_name="Learning Learner",
        profile_type="student",
        role="learner",
        auth_status="verified",
        active=True,
    )
    db_session.add_all([admin, learner])
    db_session.commit()
    db_session.refresh(admin)
    db_session.refresh(learner)
    return admin, learner


@pytest.fixture()
def auth_headers(users):
    admin, learner = users
    return {
        "admin": {"Authorization": f"Bearer {create_access_token(admin)}"},
        "learner": {"Authorization": f"Bearer {create_access_token(learner)}"},
    }
