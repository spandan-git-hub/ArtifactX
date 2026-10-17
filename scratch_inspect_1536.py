import sqlite3
from backend.app.database import SessionLocal
from backend.models.models import EvidenceFile

db = SessionLocal()
ef = db.query(EvidenceFile).filter(EvidenceFile.id == 1536).first()
b = ef.content_bytes
print("EF 1536 size:", len(b))
temp_file = "d:/ArtifactX/scratch_test_1536.db"
with open(temp_file, "wb") as f:
    f.write(b)
conn = sqlite3.connect(temp_file)
c = conn.cursor()
c.execute("SELECT name FROM sqlite_master WHERE type='table'")
tables = [r[0] for r in c.fetchall()]
print("Matching tables in 1536:", [t for t in tables if "group" in t or "participant" in t])
for t in tables:
    if "participant" in t or "group" in t:
        c.execute(f"PRAGMA table_info({t})")
        print(t, "columns:", [col[1] for col in c.fetchall()])
conn.close()
import os
os.remove(temp_file)
db.close()
