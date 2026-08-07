from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session
from typing import Optional

from app.database import get_db
from app.models.business import Business
from app.models.site import Site
from app.models.outreach import Outreach
from app.models.job import Job
from app.schemas.business import BusinessOut, BusinessDetailOut, AssetOut, SiteOut, OutreachSummaryOut, JobSummaryOut

router = APIRouter(prefix="/businesses", tags=["businesses"])


class RetryBody(BaseModel):
    step: str


@router.get("", response_model=list[BusinessOut])
def list_businesses(
    status: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
):
    q = db.query(Business)
    if status:
        q = q.filter(Business.status == status)
    return q.order_by(Business.created_at.desc()).offset(offset).limit(limit).all()


@router.get("/{business_id}", response_model=BusinessDetailOut)
def get_business(business_id: UUID, db: Session = Depends(get_db)):
    from app.models.business import BusinessAsset
    from app.models.outreach import Outreach as OutreachModel

    business = db.query(Business).filter(Business.id == business_id).first()
    if not business:
        raise HTTPException(status_code=404, detail="Business not found")

    result = BusinessDetailOut.model_validate(business)

    asset = db.query(BusinessAsset).filter(BusinessAsset.business_id == business.id).first()
    if asset:
        result.asset = AssetOut.model_validate(asset)

    site = db.query(Site).filter(Site.business_id == business.id).first()
    if site:
        result.site = SiteOut.model_validate(site)

    outreach = db.query(OutreachModel).filter(OutreachModel.business_id == business.id).first()
    if outreach:
        result.outreach = OutreachSummaryOut.model_validate(outreach)

    jobs = db.query(Job).filter(Job.business_id == business.id).order_by(Job.last_run_at.desc()).limit(5).all()
    result.recent_jobs = [JobSummaryOut.model_validate(j) for j in jobs]

    return result


@router.post("/{business_id}/approve")
def approve_business(business_id: UUID, db: Session = Depends(get_db)):
    """Set site.review_status='approved'; enqueue outreach if site exists and outreach not sent."""
    from app.workers.outreach_worker import outreach_task

    b = db.query(Business).filter(Business.id == business_id).first()
    if not b:
        raise HTTPException(status_code=404, detail="Business not found")

    site = db.query(Site).filter(Site.business_id == business_id).first()
    if not site:
        raise HTTPException(status_code=404, detail="No site found for this business")

    site.review_status = "approved"
    db.commit()

    # Only enqueue outreach if it hasn't been sent yet
    outreach_sent = (
        db.query(Outreach)
        .filter(Outreach.business_id == business_id, Outreach.email_sent_at.isnot(None))
        .first()
    )
    if not outreach_sent:
        outreach_task.delay(str(business_id), str(site.id))

    return {"approved": True, "site_id": str(site.id)}


@router.post("/{business_id}/reject")
def reject_business(business_id: UUID, db: Session = Depends(get_db)):
    """Set site.review_status='rejected'."""
    b = db.query(Business).filter(Business.id == business_id).first()
    if not b:
        raise HTTPException(status_code=404, detail="Business not found")

    site = db.query(Site).filter(Site.business_id == business_id).first()
    if not site:
        raise HTTPException(status_code=404, detail="No site found for this business")

    site.review_status = "rejected"
    db.commit()
    return {"rejected": True}


@router.post("/{business_id}/retry")
def retry_step(business_id: UUID, body: RetryBody, db: Session = Depends(get_db)):
    """Re-enqueue a pipeline step for a business."""
    b = db.query(Business).filter(Business.id == business_id).first()
    if not b:
        raise HTTPException(status_code=404, detail="Business not found")

    step = body.step
    if step == "gather":
        from app.workers.gather import gather_task
        gather_task.delay(str(business_id))
    elif step == "build":
        from app.workers.build import build_task
        build_task.delay(str(business_id))
    elif step == "publish":
        from app.workers.publish import publish_task
        publish_task.delay(str(business_id))
    elif step == "outreach":
        from app.workers.outreach_worker import outreach_task
        site = db.query(Site).filter(Site.business_id == business_id).first()
        if not site:
            raise HTTPException(status_code=404, detail="No site found for this business")
        outreach_task.delay(str(business_id), str(site.id))
    else:
        raise HTTPException(status_code=400, detail=f"Unknown step: {step}. Must be one of: gather, build, publish, outreach")

    return {"queued": True, "step": step, "business_id": str(business_id)}
