import logging
import uuid
from datetime import datetime

from app.workers.celery_app import celery_app
from app.database import SessionLocal
from app.models.business import Business, BusinessAsset
from app.models.job import Job
from app.services.google_places import GooglePlacesClient
from app.services.storage import R2StorageClient
from app.config import settings

logger = logging.getLogger(__name__)


@celery_app.task(bind=True, max_retries=3)
def gather_task(self, business_id: str):
    """Gather detailed business data from Google Places and Yelp, upload photos to R2,
    persist a BusinessAsset record, and enqueue the build worker."""
    from app.workers.build import build_task

    db = SessionLocal()
    try:
        business = db.query(Business).filter(Business.id == uuid.UUID(business_id)).first()
        if not business:
            logger.warning(f"gather_task: business {business_id} not found, skipping")
            return

        business.status = "gathering"
        db.commit()

        google = GooglePlacesClient(api_key=settings.google_places_api_key)
        storage = R2StorageClient(
            endpoint=settings.cloudflare_r2_endpoint,
            access_key=settings.cloudflare_r2_access_key,
            secret_key=settings.cloudflare_r2_secret_key,
            bucket=settings.cloudflare_r2_bucket,
        )

        raw_google: dict = {}
        photos: list[str] = []
        hours: list | dict = []
        description: str | None = None
        rating: float | None = float(business.website_score) if business.website_score is not None else None
        review_count: int = 0
        services: list = []
        price_range: str | None = None

        # --- Google Places ---
        if business.google_place_id:
            try:
                raw_google = google.get_place_details(business.google_place_id)

                # Backfill city/state if the discover worker left them empty
                if not business.city and raw_google.get("city"):
                    business.city = raw_google["city"]
                if not business.state and raw_google.get("state"):
                    business.state = raw_google["state"]

                photo_refs = raw_google.get("photos", [])[:6]
                for i, ref in enumerate(photo_refs):
                    try:
                        photo_url = google.get_photo_url(ref, max_width=1200)
                        key = f"businesses/{business_id}/photo_{i}.jpg"
                        r2_url = storage.upload_from_url(photo_url, key)
                        photos.append(r2_url)
                    except Exception as e:
                        logger.warning(f"gather_task: failed to upload Google photo {i} for {business_id}: {e}")

                hours = raw_google.get("hours", [])
                description = raw_google.get("description")
                rating = raw_google.get("rating", rating)
                review_count = raw_google.get("review_count", 0)

            except Exception as e:
                logger.warning(f"gather_task: Google Places details failed for {business_id}: {e}")

        # Normalise hours to a dict for JSON storage
        hours_dict: dict | None = (
            {"weekday_text": hours} if isinstance(hours, list) else hours or None
        )

        asset = BusinessAsset(
            business_id=business.id,
            photos=photos or None,
            description=description,
            hours=hours_dict,
            rating=rating,
            review_count=review_count,
            services=services or None,
            price_range=price_range,
            raw_google=raw_google or None,
            raw_yelp=None,
        )
        db.add(asset)

        business.status = "gathering_done"
        job = Job(
            business_id=business.id,
            step="gather",
            status="success",
            last_run_at=datetime.utcnow(),
            attempts=self.request.retries + 1,
        )
        db.add(job)
        db.commit()

        build_task.delay(business_id)

    except Exception as exc:
        db.rollback()
        raise self.retry(exc=exc, countdown=60 * (2 ** self.request.retries))
    finally:
        db.close()
