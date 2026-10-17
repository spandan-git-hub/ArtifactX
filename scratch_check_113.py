import sqlite3, os
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
c.execute("SELECT name FROM sqlite_master WHERE type='table'")
tables = [r[0] for r in c.fetchall()]
for t in tables:
    try:
        c.execute(f'SELECT count(*) FROM "{t}"')
        cnt = c.fetchone()[0]
        if cnt > 0:
            print(f"{t}: {cnt} rows")
    except Exception:
        pass
conn.close()
os.remove(temp_file)
db.close()
