"""
Pydantic models for API request/response validation.

These schemas enforce data contracts between the frontend and backend,
and auto-generate the OpenAPI (Swagger) documentation.
"""

from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


# ── Request Schemas ──

class ProspectCreate(BaseModel):
    """Schema for manually adding a single prospect."""
    company_name: str = Field(..., min_length=1, max_length=255, examples=["Stripe"])
    domain: Optional[str] = Field(None, max_length=255, examples=["stripe.com"])
    contact_name: Optional[str] = Field(None, max_length=255, examples=["John Doe"])
    contact_role: Optional[str] = Field(None, max_length=255, examples=["Head of Engineering"])
    contact_email: Optional[str] = Field(None, max_length=255, examples=["john@stripe.com"])


class EmailGenerateRequest(BaseModel):
    """Parameters for LLM email generation."""
    tone: str = Field(
        default="professional", 
        description="Email tone: professional, casual, or direct",
        examples=["professional"]
    )
    context: Optional[str] = Field(
        None,
        description="Additional context to include in the email (e.g., mutual connection, recent news)",
        examples=["They just raised Series B funding"]
    )
    our_product: str = Field(
        default="CodeRound AI - AI-powered technical interview platform",
        description="Brief description of what we're selling"
    )


# ── Response Schemas ──

class ProspectResponse(BaseModel):
    """Full prospect data returned by the API."""
    id: int
    company_name: str
    domain: Optional[str] = None
    contact_name: Optional[str] = None
    contact_role: Optional[str] = None
    contact_email: Optional[str] = None
    
    # Enrichment
    company_description: Optional[str] = None
    industry: Optional[str] = None
    employee_count: Optional[str] = None
    location: Optional[str] = None
    funding_stage: Optional[str] = None
    technologies: Optional[str] = None
    
    # Generated email
    generated_email_subject: Optional[str] = None
    generated_email_body: Optional[str] = None
    email_tone: Optional[str] = None
    
    # Status
    status: str
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    enriched_at: Optional[datetime] = None
    email_generated_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class ProspectListItem(BaseModel):
    """Lightweight prospect data for list/table views."""
    id: int
    company_name: str
    domain: Optional[str] = None
    contact_name: Optional[str] = None
    contact_role: Optional[str] = None
    status: str
    created_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class DashboardStats(BaseModel):
    """Aggregate metrics for the dashboard."""
    total_prospects: int
    by_status: dict[str, int]
    emails_generated_today: int
    avg_processing_time_seconds: Optional[float] = None


class UploadResponse(BaseModel):
    """Response after CSV upload."""
    uploaded: int
    skipped: int
    errors: list[str]
