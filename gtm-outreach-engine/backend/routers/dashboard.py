"""
Dashboard API routes for pipeline metrics and analytics.
"""

from datetime import datetime, timezone, timedelta
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func

from database import get_db, Prospect, ProspectStatus
from schemas import DashboardStats

router = APIRouter(prefix="/api/dashboard", tags=["Dashboard"])


@router.get("/stats", response_model=DashboardStats)
def get_stats(db: Session = Depends(get_db)):
    """
    Returns aggregate pipeline metrics:
    - Total prospects in the system
    - Breakdown by status (new, enriched, email_generated, etc.)
    - Emails generated in the last 24 hours
    """
    
    total = db.query(func.count(Prospect.id)).scalar() or 0
    
    # Count by status
    status_counts = (
        db.query(Prospect.status, func.count(Prospect.id))
        .group_by(Prospect.status)
        .all()
    )
    by_status = {status.value: count for status, count in status_counts}
    
    # Emails generated today
    today_start = datetime.now(timezone.utc) - timedelta(hours=24)
    emails_today = (
        db.query(func.count(Prospect.id))
        .filter(
            Prospect.email_generated_at.isnot(None),
            Prospect.email_generated_at >= today_start,
        )
        .scalar() or 0
    )
    
    return DashboardStats(
        total_prospects=total,
        by_status=by_status,
        emails_generated_today=emails_today,
    )
