from bson import ObjectId
from fastapi import APIRouter, HTTPException, Query

from app.database import db
from app.models import CaseCreate, now_utc, serialize_doc, serialize_many


router = APIRouter(prefix="/cases", tags=["cases"])


@router.post("")
async def create_case(payload: CaseCreate):
    now = now_utc()
    document = {
        "title": payload.title.strip(),
        "description": payload.description.strip(),
        "investigator": payload.investigator.strip() or "Investigator",
        "created_at": now,
        "status": "open",
    }
    result = await db.cases.insert_one(document)
    case_id = str(result.inserted_id)
    await db.audit.insert_one(
        {
            "case_id": case_id,
            "action": "case_created",
            "actor": document["investigator"],
            "timestamp": now,
            "details": {"title": document["title"]},
        }
    )
    document["_id"] = result.inserted_id
    return serialize_doc(document)


@router.get("")
async def list_cases(limit: int = Query(default=50, ge=1, le=200)):
    cursor = db.cases.find().sort("created_at", -1).limit(limit)
    return serialize_many(await cursor.to_list(length=limit))


@router.get("/{case_id}")
async def get_case(case_id: str):
    case = await _get_case(case_id)
    return serialize_doc(case)


async def _get_case(case_id: str):
    if not ObjectId.is_valid(case_id):
        raise HTTPException(status_code=404, detail="Case not found")
    case = await db.cases.find_one({"_id": ObjectId(case_id)})
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")
    return case
