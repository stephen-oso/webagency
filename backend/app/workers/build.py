"""Build worker — selects a template, generates copy via Claude, and writes a site_data.json manifest."""
import json
import logging
import os
import shutil
import uuid
from datetime import datetime
from pathlib import Path

from app.workers.celery_app import celery_app
from app.database import SessionLocal
from app.models.business import Business, BusinessAsset
from app.models.site import Site
from app.models.job import Job
from app.services.claude import ClaudeClient
from app.config import settings

logger = logging.getLogger(__name__)


@celery_app.task(bind=True, max_retries=3)
def build_task(self, business_id: str):
    """Select template, generate copy, write site_data.json, update status, enqueue publish."""
    from app.workers.publish import publish_task

    db = SessionLocal()
    try:
        business = db.query(Business).filter(Business.id == uuid.UUID(business_id)).first()
        if not business:
            logger.warning(f"build_task: business {business_id} not found, skipping")
            return

        business.status = "building"
        db.commit()

        asset = db.query(BusinessAsset).filter(BusinessAsset.business_id == business.id).first()
        assets_dict: dict = {}
        if asset:
            assets_dict = {
                "photos": asset.photos or [],
                "description": asset.description,
                "hours": asset.hours,
                "rating": asset.rating,
                "review_count": asset.review_count,
                "services": asset.services or [],
                "price_range": asset.price_range,
            }

        business_data = {
            "name": business.name,
            "city": business.city,
            "state": business.state,
            "category": business.category,
        }

        claude = ClaudeClient(api_key=settings.anthropic_api_key)
        template = claude.select_template(business.category)
        copy = claude.generate_site_copy(business_data, assets_dict)

        site_data = {
            "business_id": business_id,
            "template": template,
            "copy": copy,
            "photos": assets_dict.get("photos", []),
            "business_data": {
                "name": business.name,
                "city": business.city,
                "state": business.state,
                "phone": business.phone,
                "email": business.email,
                "category": business.category,
                "hours": assets_dict.get("hours"),
                "rating": assets_dict.get("rating"),
                "review_count": assets_dict.get("review_count"),
            },
        }

        template_src = os.path.join(settings.base_dir, "templates", template)
        build_dest = os.path.join(settings.base_dir, "built_sites", business_id)
        os.makedirs(build_dest, exist_ok=True)
        if os.path.exists(template_src):
            shutil.copytree(template_src, build_dest, dirs_exist_ok=True)

        output_dir = Path(build_dest)
        (output_dir / "site_data.json").write_text(json.dumps(site_data, indent=2))

        site = Site(business_id=business.id, template_used=template)
        db.add(site)

        business.status = "built"
        job = Job(
            business_id=business.id,
            step="build",
            status="success",
            last_run_at=datetime.utcnow(),
            attempts=self.request.retries + 1,
        )
        db.add(job)
        db.commit()

        publish_task.delay(business_id)

    except Exception as exc:
        db.rollback()
        logger.error(f"build_task: failed for {business_id}: {exc}")
        raise self.retry(exc=exc, countdown=60 * (2 ** self.request.retries))
    finally:
        db.close()
