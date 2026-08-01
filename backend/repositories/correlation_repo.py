"""Repository for correlation edge data."""

from typing import List
from sqlalchemy.orm import Session

from backend.models.models import CorrelationEdge


class CorrelationRepository:
    """Repository for correlation edge data operations."""

    def save_edges(self, db: Session, edges: List[dict]):
        """Save correlation edges to database in a single batch."""
        if not edges:
            return
        edge_objects = []
        for edge_data in edges:
            data = edge_data.copy()
            if "metadata" in data and "metadata_" not in data:
                data["metadata_"] = data.pop("metadata")
            edge_objects.append(CorrelationEdge(**data))
        db.add_all(edge_objects)
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