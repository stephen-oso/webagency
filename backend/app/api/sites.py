from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.site import Site
from app.models.outreach import Outreach
from app.schemas.site import SiteOut

router = APIRouter(prefix="/sites", tags=["sites"])


@router.get("", response_model=list[SiteOut])
def list_sites(db: Session = Depends(get_db)):
    return db.query(Site).order_by(Site.deployed_at.desc()).all()


@router.post("/{site_id}/approve")
def approve_site(site_id: UUID, db: Session = Depends(get_db)):
    from app.workers.outreach_worker import outreach_task

    site = db.query(Site).filter(Site.id == site_id).first()
    if not site:
        raise HTTPException(status_code=404, detail="Site not found")
    site.review_status = "approved"
    db.commit()

    # Only enqueue outreach if not already sent
    existing_outreach = db.query(Outreach).filter(
        Outreach.business_id == site.business_id,
        Outreach.email_sent_at.isnot(None)
    ).first()
    if not existing_outreach:
        outreach_task.delay(str(site.business_id), str(site.id))
    return {"approved": True}


@router.post("/{site_id}/reject")
def reject_site(site_id: UUID, db: Session = Depends(get_db)):
    site = db.query(Site).filter(Site.id == site_id).first()
    if not site:
        raise HTTPException(status_code=404, detail="Site not found")
    site.review_status = "rejected"
    db.commit()
    return {"rejected": True}
