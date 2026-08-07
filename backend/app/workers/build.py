"""Build worker — stub for Task 9."""
import logging
from app.workers.celery_app import celery_app

logger = logging.getLogger(__name__)


@celery_app.task(bind=True, max_retries=3)
def build_task(self, business_id: str):
    """Build the website for a business. Implemented in Task 9."""
    raise NotImplementedError("build_task is not yet implemented")
