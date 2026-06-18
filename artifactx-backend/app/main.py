from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.database import ensure_indexes
from app.routers import artifacts, cases, evidence, reports, timelines

app = FastAPI(
    title="ArtifactX API",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
async def startup():
    await ensure_indexes()


@app.get("/")
async def root():
    return {"message": "ArtifactX API Running"}


@app.get("/health")
async def health():
    return {"status": "ok"}


app.include_router(cases.router)
app.include_router(evidence.router)
app.include_router(artifacts.router)
app.include_router(timelines.router)
app.include_router(reports.router)
