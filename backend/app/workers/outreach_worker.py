"""Outreach worker — sends email and contact-form outreach for published sites."""

import logging
import urllib.parse
import uuid
from datetime import date, datetime

from app.config import settings
from app.database import SessionLocal
from app.models.business import Business
from app.models.job import Job
from app.models.outreach import Outreach
from app.models.site import Site
from app.services.form_outreach import FormOutreachClient
from app.services.hunter import HunterClient
from app.services.resend import ResendClient
from app.workers.celery_app import celery_app

logger = logging.getLogger(__name__)


def _count_todays_outreach(db) -> int:
    """Return how many Outreach rows have been sent today (by email_sent_at)."""
    today_start = datetime.combine(date.today(), datetime.min.time())
    return (
        db.query(Outreach)
        .filter(Outreach.email_sent_at >= today_start)
        .count()
    )


@celery_app.task(bind=True, max_retries=3)
def outreach_task(self, business_id: str, site_id: str):
    """Send outreach email + contact form for a published site.

    Email lookup order:
      1. Hunter.io domain search from business.existing_website domain.
      2. business.email field from DB.
      3. Skip email if neither available.

    Both email and form outreach are attempted sequentially and logged to a
    single Outreach row for the business.

    The daily cap is checked BEFORE the main try/except so that the Celery
    Retry exception is not swallowed.
    """
    db = SessionLocal()

    # --- Daily cap check (must be OUTSIDE main try/except) ---
    if _count_todays_outreach(db) >= settings.outreach_daily_cap:
        db.close()
        logger.info(f"Daily outreach cap reached — requeueing {business_id} in 1 hour")
        raise self.retry(countdown=3600)

    try:
        business = db.query(Business).filter(
            Business.id == uuid.UUID(business_id)
        ).first()
        site = db.query(Site).filter(Site.id == uuid.UUID(site_id)).first()

        if not business or not site:
            logger.warning(
                f"outreach_task: business {business_id} or site {site_id} not found — skipping"
            )
            return

        site_url = site.vercel_url or site.custom_subdomain or ""

        # Create a single Outreach row (updated as we go).
        record = Outreach(business_id=business.id, site_id=site.id)
        db.add(record)
        db.flush()

        # ------------------------------------------------------------------
        # Email outreach
        # ------------------------------------------------------------------
        email = None

        # 1. Hunter.io lookup from existing website domain.
        if not email and business.existing_website and settings.hunter_api_key:
            domain = urllib.parse.urlparse(business.existing_website).netloc
            if domain:
                hunter = HunterClient(api_key=settings.hunter_api_key)
                email = hunter.find_email(domain, business.name)

        # 2. Fall back to email stored on the business record.
        if not email:
            email = business.email

        if email:
            try:
                resend = ResendClient(api_key=settings.resend_api_key)
                resend.send_email(
                    to=email,
                    subject=f"I built {business.name} a website — take a look",
                    business_name=business.name,
                    city=business.city,
                    site_url=site_url,
                )
                record.email_to = email
                record.email_sent_at = datetime.utcnow()
                record.email_status = "sent"
                logger.info(f"Email sent to {email} for business {business_id}")
            except Exception as e:
                logger.warning(f"Email outreach failed for {business_id}: {e}")
                record.email_status = "failed"
        else:
            logger.info(f"No email found for {business_id} — skipping email outreach")
            record.email_status = "skipped"

        # ------------------------------------------------------------------
        # Contact form outreach
        # ------------------------------------------------------------------
        if business.existing_website:
            try:
                form_client = FormOutreachClient()
                success = form_client.submit_form(
                    website_url=business.existing_website,
                    business_name=business.name,
                    site_url=site_url,
                )
                record.form_submitted_at = datetime.utcnow()
                record.form_status = "submitted" if success else "failed"
                logger.info(
                    f"Form outreach {'succeeded' if success else 'failed'} for {business_id}"
                )
            except Exception as e:
                logger.warning(f"Form outreach error for {business_id}: {e}")
                record.form_status = "failed"
        else:
            record.form_status = "skipped"
            logger.info(f"No existing website for {business_id} — skipping form outreach")

        # Mark business as outreached and log the pipeline step.
        business.status = "outreached"
        job = Job(business_id=business.id, step="outreach", status="success")
        db.add(job)
        db.commit()
        logger.info(f"Outreach complete for business {business_id}")

    except Exception as exc:
        db.rollback()
        logger.error(f"outreach_task failed for {business_id}: {exc}")
        raise self.retry(exc=exc, countdown=60 * (2 ** self.request.retries))
    finally:
        db.close()
