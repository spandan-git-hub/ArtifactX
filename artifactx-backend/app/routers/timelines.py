from datetime import datetime

from bson import ObjectId
from fastapi import APIRouter, HTTPException, Query

from app.database import db
from app.models import serialize_many


router = APIRouter(tags=["timelines"])


@router.get("/cases/{case_id}/timeline")
async def get_timeline(
    case_id: str,
    sender: str | None = None,
    keyword: str | None = None,
    event_type: str | None = None,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
    limit: int = Query(default=200, ge=1, le=1000),
    offset: int = Query(default=0, ge=0),
):
    if not ObjectId.is_valid(case_id):
        raise HTTPException(status_code=404, detail="Case not found")
    case = await db.cases.find_one({"_id": ObjectId(case_id)})
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")

    query: dict = {"case_id": case_id}
    if sender:
        query["actor"] = {"$regex": sender, "$options": "i"}
    if keyword:
        query["summary"] = {"$regex": keyword, "$options": "i"}
    if event_type:
        query["event_type"] = event_type
    if date_from or date_to:
        query["timestamp"] = {}
        if date_from:
            query["timestamp"]["$gte"] = date_from
        if date_to:
            query["timestamp"]["$lte"] = date_to

    cursor = db.timeline.find(query).sort("timestamp", 1).skip(offset).limit(limit)
    return serialize_many(await cursor.to_list(length=limit))
