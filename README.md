# ArtifactX

ArtifactX is an academic digital-forensics prototype for WhatsApp `.txt` chat export analysis. It provides a FastAPI backend and a React dashboard for case creation, evidence upload, timeline review, filtering, and `.docx` report generation.

## Run the Backend

```powershell
cd artifactx-backend
.\venv\Scripts\
python.exe -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

Backend docs are available at `http://127.0.0.1:8000/docs`.

## Run the Dashboard

```powershell
cd artifactx-dashboard
npm install
npm run dev
```

Open `http://127.0.0.1:5173`.

## MVP Workflow

1. Create a case with title, investigator, and description.
2. Upload a WhatsApp `.txt` export.
3. Review evidence hash, parser status, participants, and message counts.
4. Search and filter the timeline by keyword, sender, or event type.
5. Download the academic `.docx` report.

## Notes

- This is an academic prototype, not a court-validated forensic suite.
- MongoDB is required through `artifactx-backend/.env`.
- Uploaded originals are stored under `artifactx-backend/storage/evidence`.
- The MVP supports WhatsApp text exports only.
