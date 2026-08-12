from pydantic import BaseModel
from uuid import UUID
from datetime import datetime


class SiteOut(BaseModel):
    model_config = {"from_attributes": True}
    id: UUID
    business_id: UUID
    template_used: str
    vercel_url: str | None = None
    custom_subdomain: str | None = None
    review_status: str
    deployed_at: datetime | None = None
