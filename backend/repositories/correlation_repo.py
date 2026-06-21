"""Repository for correlation edge data."""

from typing import List
from sqlalchemy.orm import Session

from backend.models.models import CorrelationEdge


class CorrelationRepository:
    """Repository for correlation edge data operations."""

    def save_edges(self, db: Session, edges: List[dict]):
        """Save correlation edges to database."""
        for edge_data in edges:
            # Check if edge already exists (by source_id, target_id, relation_type, and case_id)
            # We'll assume that the combination of source_type, source_id, target_type, target_id, relation_type, and case_id is unique.
            existing = db.query(CorrelationEdge).filter(
                CorrelationEdge.case_id == edge_data["case_id"],
                CorrelationEdge.source_type == edge_data["source_type"],
                CorrelationEdge.source_id == edge_data["source_id"],
                CorrelationEdge.target_type == edge_data["target_type"],
                CorrelationEdge.target_id == edge_data["target_id"],
                CorrelationEdge.relation_type == edge_data["relation_type"]
            ).first()

            if not existing:
                edge = CorrelationEdge(**edge_data)
                db.add(edge)

        db.commit()

    def get_edges_by_case_id(self, db: Session, case_id: int) -> List[CorrelationEdge]:
        """Get correlation edges by case ID."""
        return db.query(CorrelationEdge).filter(
            CorrelationEdge.case_id == case_id
        ).all()

    def delete_edges_by_case_id(self, db: Session, case_id: int) -> None:
        """Delete correlation edges for a case."""
        db.query(CorrelationEdge).filter(
            CorrelationEdge.case_id == case_id
        ).delete()
        db.commit()