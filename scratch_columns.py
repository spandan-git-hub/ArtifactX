import sqlite3
from backend.app.database import SessionLocal
from backend.models.models import EvidenceFile

db = SessionLocal()
ef = db.query(EvidenceFile).filter(EvidenceFile.id == 1536).first()
b = ef.content_bytes
temp_file = "d:/ArtifactX/scratch_test_1536.db"
with open(temp_file, "wb") as f:
    f.write(b)
conn = sqlite3.connect(temp_file)
c = conn.cursor()

for t in ["message", "message_media", "message_quoted", "message_location", "message_revoked", "message_edit_info"]:
    c.execute(f"PRAGMA table_info({t})")
    print(t, ":", [col[1] for col in c.fetchall()])

conn.close()
import os
os.remove(temp_file)
db.close()
