from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv
import os

load_dotenv()

mongo_uri = os.getenv("MONGO_URI", "mongodb://localhost:27017")
database_name = os.getenv("DATABASE_NAME", "artifactx")

client = AsyncIOMotorClient(mongo_uri)
db = client[database_name]


async def ensure_indexes():
    await db.cases.create_index("created_at")
    await db.evidence.create_index("case_id")
    await db.artifacts.create_index([("case_id", 1), ("timestamp", 1)])
    await db.timeline.create_index([("case_id", 1), ("timestamp", 1)])
    await db.audit.create_index([("case_id", 1), ("timestamp", 1)])
