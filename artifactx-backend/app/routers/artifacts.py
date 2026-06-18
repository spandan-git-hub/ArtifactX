from bson import ObjectId
from fastapi import APIRouter, HTTPException, Query

from app.database import db
from app.models import serialize_many


router = APIRouter(prefix="/evidence", tags=["artifacts"])


@router.get("/{evidence_id}/artifacts")
async def get_artifacts(
    evidence_id: str,
    limit: int = Query(default=200, ge=1, le=1000),
    offset: int = Query(default=0, ge=0),
):
    if not ObjectId.is_valid(evidence_id):
        raise HTTPException(status_code=404, detail="Evidence not found")
    evidence = await db.evidence.find_one({"_id": ObjectId(evidence_id)})
    if not evidence:
        raise HTTPException(status_code=404, detail="Evidence not found")

    cursor = (
        db.artifacts.find({"evidence_id": evidence_id})
        .sort("timestamp", 1)
        .skip(offset)
        .limit(limit)
    )
    return serialize_many(await cursor.to_list(length=limit))
