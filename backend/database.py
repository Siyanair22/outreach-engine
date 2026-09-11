"""
Database models and session management for the GTM Outreach Engine.

Uses SQLAlchemy ORM with SQLite. The Prospect model tracks each company
through the pipeline: new → enriched → email_generated → sent.
"""

from datetime import datetime, timezone
from sqlalchemy import create_engine, Column, Integer, String, Text, DateTime, Enum as SQLEnum
from sqlalchemy.orm import sessionmaker, declarative_base
from dotenv import load_dotenv
import enum
import os

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./gtm_outreach.db")

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


class ProspectStatus(str, enum.Enum):
    """Pipeline stages a prospect moves through."""
    NEW = "new"
    ENRICHING = "enriching"
    ENRICHED = "enriched"
    GENERATING = "generating"
    EMAIL_GENERATED = "email_generated"
    SENT = "sent"
    FAILED = "failed"


class Prospect(Base):
    """
    Core model representing a company/prospect in the outreach pipeline.
    
    Each prospect starts as NEW when uploaded via CSV or manual entry,
    moves to ENRICHED after external API data is fetched, and then to
    EMAIL_GENERATED once the LLM produces a personalized outreach email.
    """
    __tablename__ = "prospects"

    id = Column(Integer, primary_key=True, index=True)
    
    # Basic info (from CSV upload or manual entry)
    company_name = Column(String(255), nullable=False, index=True)
    domain = Column(String(255), nullable=True)
    contact_name = Column(String(255), nullable=True)
    contact_role = Column(String(255), nullable=True)
    contact_email = Column(String(255), nullable=True)
    
    # Enrichment data (populated by external APIs)
    company_description = Column(Text, nullable=True)
    industry = Column(String(255), nullable=True)
    employee_count = Column(String(50), nullable=True)
    location = Column(String(255), nullable=True)
    funding_stage = Column(String(100), nullable=True)
    technologies = Column(Text, nullable=True)  # comma-separated
    
    # LLM-generated content
    generated_email_subject = Column(Text, nullable=True)
    generated_email_body = Column(Text, nullable=True)
    email_tone = Column(String(50), default="professional")  # professional, casual, direct
    
    # Pipeline tracking
    status = Column(
        SQLEnum(ProspectStatus), 
        default=ProspectStatus.NEW, 
        nullable=False,
        index=True
    )
    
    # Metadata
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    enriched_at = Column(DateTime, nullable=True)
    email_generated_at = Column(DateTime, nullable=True)


def init_db():
    """Create all tables. Called on app startup."""
    Base.metadata.create_all(bind=engine)


def get_db():
    """FastAPI dependency that provides a database session per request."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
