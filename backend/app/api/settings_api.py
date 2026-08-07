from fastapi import APIRouter
from pydantic import BaseModel
from typing import Optional

from app.config import settings

router = APIRouter(prefix="/settings", tags=["settings"])


class SettingsOut(BaseModel):
    review_mode: bool
    outreach_daily_cap: int
    agency_domain: str


class SettingsPatch(BaseModel):
    review_mode: Optional[bool] = None
    outreach_daily_cap: Optional[int] = None


@router.get("", response_model=SettingsOut)
def get_settings():
    return SettingsOut(
        review_mode=settings.review_mode,
        outreach_daily_cap=settings.outreach_daily_cap,
        agency_domain=settings.agency_domain,
    )


@router.patch("", response_model=SettingsOut)
def patch_settings(body: SettingsPatch):
    """Update settings in memory only — does not persist to .env."""
    if body.review_mode is not None:
        settings.review_mode = body.review_mode
    if body.outreach_daily_cap is not None:
        settings.outreach_daily_cap = body.outreach_daily_cap
    return SettingsOut(
        review_mode=settings.review_mode,
        outreach_daily_cap=settings.outreach_daily_cap,
        agency_domain=settings.agency_domain,
    )
