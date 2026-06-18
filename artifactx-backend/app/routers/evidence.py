from bson import ObjectId
from fastapi import APIRouter, File, HTTPException, UploadFile

from app.database import db
from app.forensic.timeline_builder import build_timeline_events
from app.forensic.whatsapp_parser import parse_whatsapp_export
from app.models import now_utc, serialize_doc, serialize_many
from app.storage import save_upload


router = APIRouter(tags=["evidence"])


@router.post("/cases/{case_id}/evidence")
async def upload_evidence(case_id: str, file: UploadFile = File(...)):
    case = await _get_case(case_id)
    if not (file.filename or "").lower().endswith(".txt"):
        raise HTTPException(status_code=400, detail="ArtifactX MVP accepts WhatsApp .txt exports only.")

    path, file_hash, size = await save_upload(file, case_id)
    raw_bytes = path.read_bytes()
    text = raw_bytes.decode("utf-8-sig", errors="replace")
    parse_result = parse_whatsapp_export(text)
    now = now_utc()

    evidence_doc = {
        "case_id": case_id,
        "filename": file.filename or "whatsapp_export.txt",
        "content_type": file.content_type or "text/plain",
        "size_bytes": size,
        "sha256": file_hash,
        "uploaded_at": now,
        "parser_type": "whatsapp_txt",
        "parse_status": "parsed_with_warnings" if parse_result.warnings or not parse_result.messages else "parsed",
        "storage_path": str(path),
        "statistics": parse_result.statistics,
        "warnings": parse_result.warnings,
    }
    evidence_result = await db.evidence.insert_one(evidence_doc)
    evidence_id = str(evidence_result.inserted_id)

    artifact_docs = []
    for message in parse_result.messages:
        artifact_docs.append(
            {
                "case_id": case_id,
                "evidence_id": evidence_id,
                "timestamp": message.timestamp,
                "sender": message.sender,
                "content": message.content,
                "message_type": message.message_type,
                "raw_text": message.raw_text,
                "flags": message.flags,
            }
        )

    inserted_artifacts = []
    if artifact_docs:
        artifact_result = await db.artifacts.insert_many(artifact_docs)
        for doc, inserted_id in zip(artifact_docs, artifact_result.inserted_ids):
            doc["_id"] = inserted_id
            inserted_artifacts.append(serialize_doc(doc))

    timeline_docs = build_timeline_events(inserted_artifacts)
    if timeline_docs:
        await db.timeline.insert_many(timeline_docs)

    await db.audit.insert_one(
        {
            "case_id": case_id,
            "action": "evidence_uploaded",
            "actor": case.get("investigator", "Investigator"),
            "timestamp": now,
            "details": {
                "filename": evidence_doc["filename"],
                "sha256": file_hash,
                "message_count": parse_result.statistics.get("message_count", 0),
            },
        }
    )

    evidence_doc["_id"] = evidence_result.inserted_id
    return serialize_doc(evidence_doc)


@router.get("/cases/{case_id}/evidence")
async def list_case_evidence(case_id: str):
    await _get_case(case_id)
    cursor = db.evidence.find({"case_id": case_id}).sort("uploaded_at", -1)
    return serialize_many(await cursor.to_list(length=200))


async def _get_case(case_id: str):
    if not ObjectId.is_valid(case_id):
        raise HTTPException(status_code=404, detail="Case not found")
    case = await db.cases.find_one({"_id": ObjectId(case_id)})
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")
    return case
