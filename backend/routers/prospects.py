"""
Prospect management API routes.

Handles the full prospect lifecycle:
- Upload (CSV or single entry)
- Enrichment (external API calls)
- Email generation (LLM-powered)
- Status tracking
"""

import io
import csv
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Query
from sqlalchemy.orm import Session
from sqlalchemy import func

from database import get_db, Prospect, ProspectStatus
from schemas import (
    ProspectCreate, ProspectResponse, ProspectListItem,
    EmailGenerateRequest, UploadResponse
)
from services.enrichment import enrich_prospect
from services.llm_service import generate_email

router = APIRouter(prefix="/api/prospects", tags=["Prospects"])


@router.post("/upload", response_model=UploadResponse)
async def upload_csv(file: UploadFile = File(...), db: Session = Depends(get_db)):
    """
    Bulk-upload prospects from a CSV file.
    
    Expected CSV columns: company_name (required), domain, contact_name,
    contact_role, contact_email. Extra columns are ignored.
    
    Returns count of uploaded, skipped (duplicates), and any errors.
    """
    
    if not file.filename or not file.filename.endswith(".csv"):
        raise HTTPException(status_code=400, detail="File must be a .csv")
    
    content = await file.read()
    
    try:
        text = content.decode("utf-8")
    except UnicodeDecodeError:
        text = content.decode("latin-1")
    
    reader = csv.DictReader(io.StringIO(text))
    
    uploaded = 0
    skipped = 0
    errors = []
    
    for i, row in enumerate(reader, start=2):  # start=2 because row 1 is headers
        company_name = row.get("company_name", "").strip()
        
        if not company_name:
            errors.append(f"Row {i}: missing company_name, skipped")
            continue
        
        # Skip duplicates (same company name already in DB)
        existing = db.query(Prospect).filter(
            func.lower(Prospect.company_name) == company_name.lower()
        ).first()
        
        if existing:
            skipped += 1
            continue
        
        prospect = Prospect(
            company_name=company_name,
            domain=row.get("domain", "").strip() or None,
            contact_name=row.get("contact_name", "").strip() or None,
            contact_role=row.get("contact_role", "").strip() or None,
            contact_email=row.get("contact_email", "").strip() or None,
            status=ProspectStatus.NEW,
        )
        db.add(prospect)
        uploaded += 1
    
    db.commit()
    
    return UploadResponse(uploaded=uploaded, skipped=skipped, errors=errors)


@router.post("/", response_model=ProspectResponse)
def create_prospect(data: ProspectCreate, db: Session = Depends(get_db)):
    """Add a single prospect manually."""
    
    prospect = Prospect(
        company_name=data.company_name,
        domain=data.domain,
        contact_name=data.contact_name,
        contact_role=data.contact_role,
        contact_email=data.contact_email,
        status=ProspectStatus.NEW,
    )
    db.add(prospect)
    db.commit()
    db.refresh(prospect)
    
    return prospect


@router.get("/", response_model=list[ProspectListItem])
def list_prospects(
    status: str | None = Query(None, description="Filter by status"),
    search: str | None = Query(None, description="Search by company name"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
):
    """
    List all prospects with optional filtering.
    
    Supports pagination (limit/offset), status filtering,
    and basic company name search.
    """
    
    query = db.query(Prospect)
    
    if status:
        try:
            status_enum = ProspectStatus(status)
            query = query.filter(Prospect.status == status_enum)
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid status: {status}")
    
    if search:
        query = query.filter(Prospect.company_name.ilike(f"%{search}%"))
    
    query = query.order_by(Prospect.created_at.desc())
    prospects = query.offset(offset).limit(limit).all()
    
    return prospects


@router.get("/{prospect_id}", response_model=ProspectResponse)
def get_prospect(prospect_id: int, db: Session = Depends(get_db)):
    """Get full details for a single prospect, including generated email."""
    
    prospect = db.query(Prospect).filter(Prospect.id == prospect_id).first()
    if not prospect:
        raise HTTPException(status_code=404, detail="Prospect not found")
    
    return prospect


@router.post("/{prospect_id}/enrich", response_model=ProspectResponse)
async def enrich(prospect_id: int, db: Session = Depends(get_db)):
    """
    Trigger enrichment for a prospect.
    
    Calls external APIs (Hunter.io, etc.) to fetch company data,
    contact information, and other metadata. Updates the prospect
    record with enriched data and moves status to ENRICHED.
    """
    
    prospect = db.query(Prospect).filter(Prospect.id == prospect_id).first()
    if not prospect:
        raise HTTPException(status_code=404, detail="Prospect not found")
    
    prospect.status = ProspectStatus.ENRICHING
    db.commit()
    
    try:
        enrichment_data = await enrich_prospect(prospect.domain, prospect.company_name)
        
        # Update prospect with enriched fields
        for field, value in enrichment_data.items():
            if hasattr(prospect, field) and value:
                setattr(prospect, field, value)
        
        prospect.status = ProspectStatus.ENRICHED
        prospect.enriched_at = datetime.now(timezone.utc)
        
    except Exception as e:
        prospect.status = ProspectStatus.FAILED
        db.commit()
        raise HTTPException(status_code=500, detail=f"Enrichment failed: {str(e)}")
    
    db.commit()
    db.refresh(prospect)
    
    return prospect


@router.post("/{prospect_id}/generate-email", response_model=ProspectResponse)
async def generate_outreach_email(
    prospect_id: int,
    params: EmailGenerateRequest | None = None,
    db: Session = Depends(get_db),
):
    """
    Generate a personalized outreach email for a prospect using an LLM.
    
    Uses all available prospect data (basic + enriched) to generate
    a relevant, personalized cold email. The email references specific
    details about the prospect's company to avoid sounding generic.
    """
    
    if params is None:
        params = EmailGenerateRequest()
    
    prospect = db.query(Prospect).filter(Prospect.id == prospect_id).first()
    if not prospect:
        raise HTTPException(status_code=404, detail="Prospect not found")
    
    prospect.status = ProspectStatus.GENERATING
    db.commit()
    
    # Build prospect data dict for the LLM
    prospect_data = {
        "company_name": prospect.company_name,
        "domain": prospect.domain,
        "contact_name": prospect.contact_name,
        "contact_role": prospect.contact_role,
        "company_description": prospect.company_description,
        "industry": prospect.industry,
        "employee_count": prospect.employee_count,
        "location": prospect.location,
        "funding_stage": prospect.funding_stage,
        "technologies": prospect.technologies,
    }
    
    try:
        email_result = await generate_email(
            prospect_data=prospect_data,
            tone=params.tone,
            context=params.context,
            our_product=params.our_product,
        )
        
        prospect.generated_email_subject = email_result["subject"]
        prospect.generated_email_body = email_result["body"]
        prospect.email_tone = params.tone
        prospect.status = ProspectStatus.EMAIL_GENERATED
        prospect.email_generated_at = datetime.now(timezone.utc)
        
    except (ValueError, RuntimeError) as e:
        prospect.status = ProspectStatus.FAILED
        db.commit()
        raise HTTPException(status_code=500, detail=f"Email generation failed: {str(e)}")
    
    db.commit()
    db.refresh(prospect)
    
    return prospect


@router.post("/{prospect_id}/regenerate-email", response_model=ProspectResponse)
async def regenerate_email(
    prospect_id: int,
    params: EmailGenerateRequest,
    db: Session = Depends(get_db),
):
    """
    Regenerate email with different parameters (tone, context, etc.).
    
    Useful when the first generated email doesn't hit the right note.
    Overwrites the previous email.
    """
    
    return await generate_outreach_email(prospect_id, params, db)


@router.delete("/{prospect_id}")
def delete_prospect(prospect_id: int, db: Session = Depends(get_db)):
    """Delete a prospect from the pipeline."""
    
    prospect = db.query(Prospect).filter(Prospect.id == prospect_id).first()
    if not prospect:
        raise HTTPException(status_code=404, detail="Prospect not found")
    
    db.delete(prospect)
    db.commit()
    
    return {"detail": "Prospect deleted"}
