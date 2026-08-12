from pydantic import BaseModel
from uuid import UUID
from datetime import datetime


class OutreachOut(BaseModel):
    model_config = {"from_attributes": True}
    id: UUID
    business_id: UUID
    email_to: str | None = None
    email_sent_at: datetime | None = None
    email_status: str | None = None
    form_submitted_at: datetime | None = None
    form_status: str | None = None
    responded_at: datetime | None = None
