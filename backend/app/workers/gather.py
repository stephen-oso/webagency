"""Gather worker — stub for Task 7."""
import logging
from app.workers.celery_app import celery_app

logger = logging.getLogger(__name__)


@celery_app.task(bind=True, max_retries=3, default_retry_delay=60)
def gather_task(self, business_id: str):
    """Gather detailed business data. Implemented in Task 7."""
    raise NotImplementedError("gather_task is not yet implemented")
