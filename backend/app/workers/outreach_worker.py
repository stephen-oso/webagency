"""Outreach worker stub — fully implemented in Task 11."""
import logging
from app.workers.celery_app import celery_app

logger = logging.getLogger(__name__)


@celery_app.task(bind=True, max_retries=3)
def outreach_task(self, business_id: str, site_id: str):
    """Send outreach email/message for a published site. Implemented in Task 11."""
    raise NotImplementedError("outreach_task is not yet implemented")
