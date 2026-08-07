from fastapi import APIRouter
from app.api.businesses import router as businesses_router
from app.api.sites import router as sites_router
from app.api.jobs import router as jobs_router
from app.api.outreach import router as outreach_router
from app.api.pipeline import router as pipeline_router
from app.api.settings_api import router as settings_router

router = APIRouter()
router.include_router(businesses_router)
router.include_router(sites_router)
router.include_router(jobs_router)
router.include_router(outreach_router)
router.include_router(pipeline_router)
router.include_router(settings_router)
