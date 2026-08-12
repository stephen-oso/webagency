from pydantic import BaseModel, ConfigDict
from uuid import UUID
import uuid
from datetime import datetime


class BusinessOut(BaseModel):
    model_config = {"from_attributes": True}
    id: UUID
    name: str
    city: str
    state: str
    category: str
    status: str
    website_score: int | None
    created_at: datetime


class AssetOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    photos: list[str] = []
    description: str | None = None
    hours: dict | None = None
    rating: float | None = None
    review_count: int | None = None
    services: list | None = None
    price_range: str | None = None


class SiteOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    vercel_url: str | None = None
    custom_subdomain: str | None = None
    review_status: str | None = None
    deployed_at: datetime | None = None
    template_used: str | None = None


class OutreachSummaryOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    email_to: str | None = None
    email_status: str | None = None
    form_status: str | None = None


class JobSummaryOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    step: str | None = None
    status: str | None = None
    error_msg: str | None = None
    last_run_at: datetime | None = None


class BusinessDetailOut(BusinessOut):
    address: str | None = None
    phone: str | None = None
    email: str | None = None
    existing_website: str | None = None
    google_place_id: str | None = None
    yelp_id: str | None = None
    asset: AssetOut | None = None
    site: SiteOut | None = None
    outreach: OutreachSummaryOut | None = None
    recent_jobs: list[JobSummaryOut] = []
