"""Repository for correlation edge, entity resolution, and deep finding data."""

from typing import List, Optional
from sqlalchemy.orm import Session

from backend.models.models import CorrelationEdge, PersonEntity, CorrelationFinding


class CorrelationRepository:
    """Repository for correlation data operations."""

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

    # --- Person Entities ---

    def save_person_entities(self, db: Session, case_id: int, persons: List[dict]):
        """Save resolved person entity clusters."""
        if not persons:
            return
        objs = []
        for p in persons:
            obj = PersonEntity(
                case_id=case_id,
                entity_uuid=p.get("person_id") or p.get("entity_uuid"),
                label=p.get("label", ""),
                entity_type="PERSON",
                confidence_score=p.get("confidence_score", 1.0),
                resolution_method=p.get("resolution_method", ""),
                attributes={
                    "phone_numbers": p.get("phone_numbers", []),
                    "handles": p.get("handles", []),
                    "aliases": p.get("aliases", []),
                    "resolved_accounts": p.get("resolved_accounts", []),
                },
                evidence_links=p.get("evidence_links", []),
                limitations=p.get("limitations", []),
                provenance=p.get("provenance", {}),
                is_ambiguous=p.get("is_ambiguous", False),
            )
            objs.append(obj)
        db.add_all(objs)
        db.commit()

    def get_person_entities_by_case_id(self, db: Session, case_id: int) -> List[PersonEntity]:
        """Get person entities for a case."""
        return db.query(PersonEntity).filter(PersonEntity.case_id == case_id).all()

    def delete_person_entities_by_case_id(self, db: Session, case_id: int) -> None:
        """Delete person entities for a case."""
        db.query(PersonEntity).filter(PersonEntity.case_id == case_id).delete()
        db.commit()

    # --- Correlation Findings ---

    def save_correlation_findings(self, db: Session, case_id: int, findings: List[dict]):
        """Save specialized correlation findings."""
        if not findings:
            return
        objs = []
        for f in findings:
            obj = CorrelationFinding(
                case_id=case_id,
                finding_uuid=f.get("finding_uuid") or f.get("finding_id", ""),
                finding_type=f.get("finding_type", "unknown"),
                sub_type=f.get("sub_type"),
                confidence_score=f.get("confidence_score", 1.0),
                details=f.get("details", {}),
                evidence_ids=f.get("evidence_ids", []),
                limitations=f.get("limitations", []),
                provenance=f.get("provenance", {}),
            )
            objs.append(obj)
        db.add_all(objs)
        db.commit()

    def get_findings_by_type(self, db: Session, case_id: int, finding_type: Optional[str] = None) -> List[CorrelationFinding]:
        """Get correlation findings by case ID and optional type."""
        query = db.query(CorrelationFinding).filter(CorrelationFinding.case_id == case_id)
        if finding_type:
            query = query.filter(CorrelationFinding.finding_type == finding_type)
        return query.all()

    def delete_findings_by_case_id(self, db: Session, case_id: int) -> None:
        """Delete correlation findings for a case."""
        db.query(CorrelationFinding).filter(CorrelationFinding.case_id == case_id).delete()
        db.commit()