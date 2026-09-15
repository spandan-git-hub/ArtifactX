"""Forensic Assistant API endpoints for investigative copilot queries and chat sentiment analysis."""

from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from backend.app.database import get_db
from backend.models.models import Case
from backend.services.assistant_service import AssistantService

router = APIRouter()


class CopilotQueryRequest(BaseModel):
    query: str = Field(..., description="Investigator natural language question or keyword search")
    jid: Optional[str] = Field(None, description="Filter search to a specific chat JID or dialog ID")
    limit: Optional[int] = Field(25, ge=1, le=100, description="Max finding records to return")


class SentimentAnalysisRequest(BaseModel):
    jid: Optional[str] = Field(None, description="Optional target chat thread JID to analyze")
    message_ids: Optional[List[str]] = Field(None, description="Optional explicit list of message IDs to analyze")


@router.post("/{case_id}/assistant/query")
def query_assistant(
    case_id: int,
    payload: CopilotQueryRequest,
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    """
    Process investigator natural language questions over case messages and forensic metadata.
    NOTE: Strictly excluded from legal court reports.
    """
    case = db.query(Case).filter(Case.id == case_id).first()
    if not case:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Case not found")

    if not payload.query or not payload.query.strip():
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Query string cannot be empty",
        )

    return AssistantService.query_case_copilot(
        db=db,
        case_id=case_id,
        query=payload.query.strip(),
        jid=payload.jid,
        limit=payload.limit or 25,
    )


@router.post("/{case_id}/assistant/sentiment")
def analyze_sentiment(
    case_id: int,
    payload: Optional[SentimentAnalysisRequest] = None,
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    """
    Execute chat sentiment classification, intention marker detection, and suspicion confidence scoring.
    NOTE: Strictly excluded from legal court reports.
    """
    case = db.query(Case).filter(Case.id == case_id).first()
    if not case:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Case not found")

    jid = payload.jid if payload else None
    message_ids = payload.message_ids if payload else None

    return AssistantService.analyze_case_sentiment(
        db=db,
        case_id=case_id,
        jid=jid,
        message_ids=message_ids,
    )
