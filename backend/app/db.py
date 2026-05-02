from __future__ import annotations

import os
from datetime import datetime

from sqlalchemy import (
    Column,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    JSON,
    String,
    Text,
    create_engine,
)
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

DB_PATH = os.environ.get("LEADGEN_DB", "leadgen.db")
DATABASE_URL = f"sqlite:///{DB_PATH}"

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


class Base(DeclarativeBase):
    pass


class ICP(Base):
    __tablename__ = "icp"
    id = Column(Integer, primary_key=True)
    industry_keywords = Column(String, default="")
    size_min = Column(Integer, default=0)
    size_max = Column(Integer, default=10000)
    value_prop = Column(Text, default="")
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class Lead(Base):
    __tablename__ = "leads"
    id = Column(Integer, primary_key=True)
    company_name = Column(String, nullable=False)
    website = Column(String, default="")
    domain = Column(String, index=True, unique=True)
    industry = Column(String, default="")
    employee_count = Column(Integer, default=0)
    location = Column(String, default="")
    created_at = Column(DateTime, default=datetime.utcnow)


class Enrichment(Base):
    __tablename__ = "enrichment"
    lead_id = Column(Integer, primary_key=True)
    title = Column(String, default="")
    description = Column(Text, default="")
    tech_stack = Column(JSON, default=list)
    contacts = Column(JSON, default=dict)
    signals = Column(JSON, default=dict)
    fetched_at = Column(DateTime, default=datetime.utcnow)
    status = Column(String, default="ok")  # ok | error | skipped


class Score(Base):
    __tablename__ = "scores"
    lead_id = Column(Integer, primary_key=True)
    score = Column(Float, default=0.0)
    tier = Column(String, default="C")
    reasons = Column(JSON, default=list)
    why = Column(Text, default="")
    scored_at = Column(DateTime, default=datetime.utcnow)


class ScoreHistory(Base):
    __tablename__ = "score_history"
    id = Column(Integer, primary_key=True)
    lead_id = Column(Integer, ForeignKey("leads.id"), index=True)
    previous_score = Column(Float, nullable=True)
    previous_tier = Column(String, default="")
    new_score = Column(Float, default=0.0)
    new_tier = Column(String, default="C")
    previous_why = Column(Text, default="")
    new_why = Column(Text, default="")
    version = Column(Integer, default=1)
    changed_at = Column(DateTime, default=datetime.utcnow)


class ScrapeCache(Base):
    __tablename__ = "scrape_cache"
    domain = Column(String, primary_key=True)
    html = Column(Text, default="")
    headers = Column(JSON, default=dict)
    fetched_at = Column(DateTime, default=datetime.utcnow)


class LeadPipeline(Base):
    __tablename__ = "lead_pipeline"
    lead_id = Column(Integer, ForeignKey("leads.id"), primary_key=True)
    stage = Column(String, default="new", index=True)
    reason = Column(Text, default="")
    updated_by = Column(String, default="system")
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class LeadPipelineHistory(Base):
    __tablename__ = "lead_pipeline_history"
    id = Column(Integer, primary_key=True)
    lead_id = Column(Integer, ForeignKey("leads.id"), index=True)
    from_stage = Column(String, default="")
    to_stage = Column(String, default="new")
    reason = Column(Text, default="")
    updated_by = Column(String, default="system")
    updated_at = Column(DateTime, default=datetime.utcnow)


class OutreachDraft(Base):
    __tablename__ = "outreach_drafts"
    id = Column(Integer, primary_key=True)
    lead_id = Column(Integer, ForeignKey("leads.id"), index=True)
    tone = Column(String, default="direct")
    subject = Column(String, default="")
    body = Column(Text, default="")
    created_at = Column(DateTime, default=datetime.utcnow)


class ScoringConfig(Base):
    __tablename__ = "scoring_config"
    id = Column(Integer, primary_key=True)
    template = Column(String, default="Balanced")
    weights = Column(JSON, default=dict)
    version = Column(Integer, default=1)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


DEFAULT_SCORING_WEIGHTS = {
    "industry_match": 30,
    "size_band": 20,
    "tech_relevance": 20,
    "contact_completeness": 15,
    "activity_recency": 15,
}


def init_db() -> None:
    Base.metadata.create_all(engine)
    # Seed singleton ICP row if missing.
    with SessionLocal() as s:
        if s.get(ICP, 1) is None:
            s.add(
                ICP(
                    id=1,
                    industry_keywords="saas, software, b2b",
                    size_min=10,
                    size_max=500,
                    value_prop="AI-powered lead enrichment for B2B sales teams",
                )
            )
            s.commit()
        if s.get(ScoringConfig, 1) is None:
            s.add(
                ScoringConfig(
                    id=1,
                    template="Balanced",
                    weights=DEFAULT_SCORING_WEIGHTS.copy(),
                    version=1,
                )
            )
            s.commit()


def get_session() -> Session:
    return SessionLocal()


def to_dict(obj: Any) -> dict:
    if obj is None:
        return {}
    return {c.name: getattr(obj, c.name) for c in obj.__table__.columns}
