from pydantic import BaseModel
from uuid import UUID
from datetime import datetime


class JobOut(BaseModel):
    model_config = {"from_attributes": True}
    id: UUID
    business_id: UUID
    step: str
    status: str
    error_msg: str | None = None
    attempts: int
    last_run_at: datetime | None = None
