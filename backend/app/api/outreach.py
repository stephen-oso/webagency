from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.outreach import Outreach
from app.schemas.outreach import OutreachOut

router = APIRouter(prefix="/outreach", tags=["outreach"])


@router.get("", response_model=list[OutreachOut])
def list_outreach(db: Session = Depends(get_db)):
    return db.query(Outreach).order_by(Outreach.email_sent_at.desc()).all()
