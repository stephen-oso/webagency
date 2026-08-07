from pydantic import BaseModel
from uuid import UUID
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


class BusinessDetailOut(BusinessOut):
    address: str | None = None
    phone: str | None = None
    email: str | None = None
    existing_website: str | None = None
    google_place_id: str | None = None
    yelp_id: str | None = None
