"""Publish worker — deploys built sites to Vercel and handles review mode gating."""
import json
import logging
import uuid
from datetime import datetime
from pathlib import Path

from app.workers.celery_app import celery_app
from app.database import SessionLocal
from app.models.business import Business
from app.models.site import Site
from app.models.job import Job
from app.services.publisher import VercelPublisher
from app.config import settings

logger = logging.getLogger(__name__)


@celery_app.task(bind=True, max_retries=3)
def publish_task(self, business_id: str):
    """Deploy the built site to Vercel, update Site record, handle review mode."""
    from app.workers.outreach_worker import outreach_task

    db = SessionLocal()
    try:
        business = db.query(Business).filter(Business.id == uuid.UUID(business_id)).first()
        if not business:
            logger.warning(f"publish_task: business {business_id} not found, skipping")
            return

        site = db.query(Site).filter(Site.business_id == business.id).first()
        if not site:
            logger.warning(f"publish_task: no Site record for business {business_id}, skipping")
            return

        build_dir = Path(settings.base_dir) / "built_sites" / business_id

        # Read site_data.json to get template slug
        site_data_path = build_dir / "site_data.json"
        if site_data_path.exists():
            site_data = json.loads(site_data_path.read_text())
        else:
            site_data = {}

        slug = f"{business.name.lower().replace(' ', '-')}-{str(business.id)[:8]}"

        publisher = VercelPublisher(
            token=settings.vercel_token,
            team_id=settings.vercel_team_id,
            agency_domain=settings.agency_domain,
        )
        vercel_url = publisher.deploy(str(build_dir), slug)

        site.vercel_url = vercel_url
        site.custom_subdomain = f"{slug}.{settings.agency_domain}"
        site.deployed_at = datetime.utcnow()

        business.status = "published"
        job = Job(
            business_id=business.id,
            step="publish",
            status="success",
            last_run_at=datetime.utcnow(),
            attempts=self.request.retries + 1,
        )
        db.add(job)

        if settings.review_mode:
            site.review_status = "pending"
            logger.info(f"Review mode ON — site {business_id} awaiting approval")
        else:
            site.review_status = "approved"
            outreach_task.delay(business_id, str(site.id))

        db.commit()

    except Exception as exc:
        db.rollback()
        logger.error(f"publish_task: failed for {business_id}: {exc}")
        raise self.retry(exc=exc, countdown=60 * (2 ** self.request.retries))
    finally:
        db.close()
