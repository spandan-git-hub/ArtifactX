"""Integration tests for Correlation API endpoints."""

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from unittest.mock import patch

from backend.app.main import app
from backend.models.models import Case

client = TestClient(app)


def test_correlate_case_endpoint(db_session: Session):
    """Test correlation endpoint."""
    # Create test case
    case = Case(name="Test Case", description="Test for correlation")
    db_session.add(case)
    db_session.commit()
    db_session.refresh(case)

    # Mock the correlation service in the API module
    with patch('backend.api.correlation.correlation_service') as mock_service:
        mock_service.correlate_case.return_value = 5

        response = client.post(
            f"/api/correlation/cases/{case.id}/correlate",
        )

        assert response.status_code == 202
        data = response.json()
        assert data["message"] == "Correlation started"
        assert data["case_id"] == case.id
        assert data["edges_created"] == 5
        mock_service.correlate_case.assert_called_once()


def test_correlate_case_endpoint_not_found(db_session: Session):
    """Test correlation endpoint with non-existent case."""
    with patch('backend.api.correlation.correlation_service') as mock_service:
        mock_service.correlate_case.return_value = 0

        response = client.post(
            f"/api/correlation/cases/999/correlate",
        )

        # The API checks for case existence before calling service
        assert response.status_code == 404
        data = response.json()
        assert data["detail"] == "Case not found"


def test_get_correlation_endpoint(db_session: Session):
    """Test getting correlation edges endpoint."""
    # Create test case
    case = Case(name="Test Case", description="Test for correlation")
    db_session.add(case)
    db_session.commit()
    db_session.refresh(case)

    # Mock the correlation service
    with patch('backend.api.correlation.correlation_service') as mock_service:
        mock_service.get_edges_for_case.return_value = [
            {
                "id": 1,
                "case_id": case.id,
                "source_type": "wa_message",
                "source_id": "msg1",
                "target_type": "wa_contact",
                "target_id": "user1@example.com",
                "relation_type": "sent_by",
                "metadata": {"evidence_id": 1},
            },
            {
                "id": 2,
                "case_id": case.id,
                "source_type": "wa_contact",
                "source_id": "user1@example.com",
                "target_type": "tg_contact",
                "target_id": "12345",
                "relation_type": "matches_contact",
                "metadata": {"phone_number": "1111111111"},
            },
        ]

        response = client.get(
            f"/api/correlation/cases/{case.id}/correlation",
        )

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) == 2

        # Check first edge
        assert data[0]["source_type"] == "wa_message"
        assert data[0]["source_id"] == "msg1"
        assert data[0]["target_type"] == "wa_contact"
        assert data[0]["relation_type"] == "sent_by"

        # Check second edge
        assert data[1]["source_type"] == "wa_contact"
        assert data[1]["target_id"] == "12345"
        assert data[1]["relation_type"] == "matches_contact"

        mock_service.get_edges_for_case.assert_called_once()


def test_get_correlation_endpoint_not_found(db_session: Session):
    """Test getting correlation edges with non-existent case."""
    response = client.get("/api/correlation/cases/999/correlation")

    assert response.status_code == 404
    data = response.json()
    assert data["detail"] == "Case not found"


# Clean up overrides
def tear_down():
    app.dependency_overrides.clear()
