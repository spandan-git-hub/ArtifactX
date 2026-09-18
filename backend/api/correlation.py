"""Correlation API endpoints."""

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field

from backend.app.database import get_db
from backend.services.correlation_service import correlation_service
from backend.models.models import Case

router = APIRouter()


class DeepCorrelationRequest(BaseModel):
    handover_threshold_seconds: Optional[int] = Field(180, description="Max seconds between messages to qualify as platform handover candidate")
    media_hamming_distance: Optional[int] = Field(4, description="Max bitwise Hamming distance for perceptual media link")
    rendezvous_distance_meters: Optional[float] = Field(50.0, description="Max distance in meters between location coordinates")
    rendezvous_time_seconds: Optional[int] = Field(1800, description="Max seconds between timestamped location events")
    custom_keywords: Optional[List[str]] = Field(default_factory=list, description="Analyst-configured codewords or keywords to scan")


@router.post("/cases/{case_id}/correlate", status_code=status.HTTP_202_ACCEPTED)
def correlate_case(
    case_id: int,
    db: Session = Depends(get_db)
):
    """Trigger baseline correlation for a case."""
    case = db.query(Case).filter(Case.id == case_id).first()
    if not case:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Case not found"
        )

    edge_count = correlation_service.correlate_case(db, case_id)
    return {
        "message": "Correlation started",
        "case_id": case_id,
        "edges_created": edge_count
    }


@router.post("/cases/{case_id}/correlation/deep/run", status_code=status.HTTP_200_OK)
def run_deep_correlation(
    case_id: int,
    payload: Optional[DeepCorrelationRequest] = None,
    db: Session = Depends(get_db)
):
    """
    Trigger full R4 Deep Cross-Platform Correlation Engine:
    - Multi-modal identity resolution (Persons, Phones, Handles)
    - Platform handover candidates (with neutral forensic labeling)
    - Perceptual media correlation (dHash / pHash)
    - Deterministic artifact extraction (Crypto, Banking, Logistics, Codewords)
    - Spatiotemporal rendezvous co-occurrence detection
    """
    case = db.query(Case).filter(Case.id == case_id).first()
    if not case:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Case not found"
        )

    params = payload.dict() if payload else {}
    result = correlation_service.run_deep_correlation(db, case_id, params)
    return result


@router.get("/cases/{case_id}/correlation/graph", response_model=Dict[str, Any])
def get_case_correlation_graph(
    case_id: int,
    db: Session = Depends(get_db)
):
    """Get full stable JSON graph of nodes, edges, and provenance metadata."""
    case = db.query(Case).filter(Case.id == case_id).first()
    if not case:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Case not found"
        )

    return correlation_service.get_deep_graph(db, case_id)


@router.get("/cases/{case_id}/correlation/handover", response_model=List[Dict[str, Any]])
def get_platform_handovers(
    case_id: int,
    db: Session = Depends(get_db)
):
    """Get detected platform handover candidates."""
    case = db.query(Case).filter(Case.id == case_id).first()
    if not case:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Case not found"
        )

    return correlation_service.get_platform_handovers(db, case_id)


@router.get("/cases/{case_id}/correlation/media", response_model=List[Dict[str, Any]])
def get_media_correlations(
    case_id: int,
    db: Session = Depends(get_db)
):
    """Get perceptual media matches."""
    case = db.query(Case).filter(Case.id == case_id).first()
    if not case:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Case not found"
        )

    return correlation_service.get_media_correlations(db, case_id)


@router.get("/cases/{case_id}/correlation/artifacts", response_model=List[Dict[str, Any]])
def get_shared_artifacts(
    case_id: int,
    db: Session = Depends(get_db)
):
    """Get extracted and shared deterministic artifacts."""
    case = db.query(Case).filter(Case.id == case_id).first()
    if not case:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Case not found"
        )

    return correlation_service.get_shared_artifacts(db, case_id)


@router.get("/cases/{case_id}/correlation/rendezvous", response_model=List[Dict[str, Any]])
def get_rendezvous_events(
    case_id: int,
    db: Session = Depends(get_db)
):
    """Get spatiotemporal rendezvous candidates."""
    case = db.query(Case).filter(Case.id == case_id).first()
    if not case:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Case not found"
        )

    return correlation_service.get_rendezvous_events(db, case_id)


@router.get("/cases/{case_id}/correlation/persons", response_model=List[Dict[str, Any]])
def get_resolved_persons(
    case_id: int,
    db: Session = Depends(get_db)
):
    """Get resolved person entity clusters."""
    case = db.query(Case).filter(Case.id == case_id).first()
    if not case:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Case not found"
        )

    return correlation_service.get_resolved_persons(db, case_id)


@router.get("/cases/{case_id}/correlation", response_model=List[dict])
def get_case_correlation(
    case_id: int,
    db: Session = Depends(get_db)
):
    """Get correlation edges for a case (backwards compatible)."""
    case = db.query(Case).filter(Case.id == case_id).first()
    if not case:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Case not found"
        )

    return correlation_service.get_edges_for_case(db, case_id)


@router.get("/cases/{case_id}/correlation/entities", response_model=List[dict])
def get_entity_resolutions(
    case_id: int,
    db: Session = Depends(get_db)
):
    """Get resolved cross-app entity contact mappings for a case (backwards compatible)."""
    case = db.query(Case).filter(Case.id == case_id).first()
    if not case:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Case not found"
        )

    return correlation_service.get_entity_resolutions(db, case_id)


@router.get("/cases/{case_id}/correlation/matrix", response_model=List[dict])
def get_message_matrix(
    case_id: int,
    window_seconds: int = 300,
    db: Session = Depends(get_db)
):
    """Get cross-app message correlation matrix for a case within a time window threshold."""
    case = db.query(Case).filter(Case.id == case_id).first()
    if not case:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Case not found"
        )

    return correlation_service.get_cross_app_message_matrix(db, case_id, window_seconds)


@router.get("/cases/{case_id}/correlation/status", response_model=dict)
def get_correlation_status(
    case_id: int,
    db: Session = Depends(get_db)
):
    """Get accurate platform evidence presence status (has_whatsapp, has_telegram, evidence_count) for a case."""
    case = db.query(Case).filter(Case.id == case_id).first()
    if not case:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Case not found"
        )

    return correlation_service.check_case_evidence_platforms(db, case_id)