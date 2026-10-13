"""Integration tests for database models and session on test database (DEC-003)."""

import pytest
from backend.app.database import Base, engine, SessionLocal
from backend.models import Case


@pytest.mark.integration
def test_create_tables_and_query_case():
    """Verify models create cleanly on test DB and support CRUD."""
    Base.metadata.create_all(bind=engine)
    session = SessionLocal()
    try:
        case = Case(name="Test Case Alpha", description="Unit test verification", investigator="Analyst A")
        session.add(case)
        session.commit()
        session.refresh(case)

        assert case.id is not None
        assert case.name == "Test Case Alpha"

        fetched = session.query(Case).filter(Case.id == case.id).first()
        assert fetched is not None
        assert fetched.investigator == "Analyst A"
    finally:
        session.close()
