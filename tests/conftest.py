"""Pytest fixtures."""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from backend.app.database import Base, get_db
from backend.app.main import app
from backend import models

# In-memory shared database for testing to persist across connections
TEST_DATABASE_URL = "sqlite:///file::memory:?cache=shared"

engine = create_engine(
    TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture(scope="function", autouse=True)
def setup_database():
    print("Tables before create_all:", list(Base.metadata.tables.keys()))
    Base.metadata.create_all(bind=engine)
    print("Tables after create_all:", list(Base.metadata.tables.keys()))
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture()
def client():
    return TestClient(app)


@pytest.fixture()
def db_session():
    session = TestingSessionLocal()
    yield session
    session.rollback()
    session.close()


def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = override_get_db


# Clean up overrides
def tear_down():
    app.dependency_overrides.clear()