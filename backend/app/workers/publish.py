"""Publish worker — stub for Task 10."""
import logging
from app.workers.celery_app import celery_app

logger = logging.getLogger(__name__)


@celery_app.task(bind=True, max_retries=3)
def publish_task(self, business_id: str):
    """Deploy the built site to Vercel. Implemented in Task 10."""
    raise NotImplementedError("publish_task is not yet implemented")
