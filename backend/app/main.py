from __future__ import annotations

from dotenv import load_dotenv

# Load .env before anything else imports os.environ-reading modules.
load_dotenv()

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .db import init_db
from .routes import icp, leads, outreach, score, system

app = FastAPI(title="Lead Qualifier", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def _startup() -> None:
    init_db()


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


app.include_router(leads.router)
app.include_router(icp.router)
app.include_router(score.router)
app.include_router(outreach.router)
app.include_router(system.router)
