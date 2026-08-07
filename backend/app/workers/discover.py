import logging

from app.workers.celery_app import celery_app
from app.database import SessionLocal
from app.models.business import Business
from app.models.job import Job
from app.services.google_places import GooglePlacesClient
from app.services.yelp import YelpClient
from app.services.website_scorer import score_website
from app.config import settings

logger = logging.getLogger(__name__)

CATEGORY_MAP = {
    "restaurant": ["restaurant", "cafe"],
    "plumber": ["plumbers"],
    "salon": ["hair", "beauty"],
    "dentist": ["dentists"],
    "landscaping": ["landscaping", "lawn_services"],
    "retail": ["shopping"],
    "trades": ["contractors"],
    "professional": ["professional_services"],
    "auto": ["auto_repair"],
    "cleaning": ["home_cleaning"],
    "gym": ["gyms", "fitness"],
    "photography": ["photographers"],
    "realestate": ["real_estate_agents"],
    "childcare": ["childcare"],
    "petservices": ["pet_groomers", "veterinarians"],
}


@celery_app.task(bind=True, max_retries=3, default_retry_delay=60)
def discover_task(self, region: str, categories: list[str]):
    from app.workers.gather import gather_task

    google = GooglePlacesClient(api_key=settings.google_places_api_key)
    yelp = YelpClient(api_key=settings.yelp_api_key)
    db = SessionLocal()

    try:
        seen_google_ids = set()
        candidates = []

        for category in categories:
            yelp_cats = CATEGORY_MAP.get(category, [category])

            try:
                google_results = google.search_businesses(region, category)
            except Exception as e:
                logger.warning(f"Google Places failed for {category}: {e}")
                google_results = []

            try:
                yelp_results = yelp.search_businesses(region, yelp_cats[0])
            except Exception as e:
                logger.warning(f"Yelp failed for {category}: {e}")
                yelp_results = []

            for result in google_results + yelp_results:
                place_id = result.get("place_id")
                if place_id and place_id in seen_google_ids:
                    continue
                if place_id:
                    seen_google_ids.add(place_id)

                existing_site = result.get("website")
                ws = score_website(existing_site) if existing_site else 0

                if ws <= 4:
                    candidates.append({**result, "website_score": ws, "category": category})

        for c in candidates:
            existing = (
                db.query(Business)
                .filter(Business.google_place_id == c.get("place_id"))
                .first()
                if c.get("place_id")
                else None
            )

            if existing:
                continue

            business = Business(
                name=c["name"],
                address=c.get("address"),
                city=c.get("city", ""),
                state=c.get("state", ""),
                phone=c.get("phone"),
                category=c["category"],
                google_place_id=c.get("place_id"),
                yelp_id=c.get("yelp_id"),
                existing_website=c.get("website"),
                website_score=c["website_score"],
                status="discovered",
            )
            db.add(business)
            db.flush()

            job = Job(business_id=business.id, step="discover", status="success")
            db.add(job)

        db.commit()

        for business in db.query(Business).filter(Business.status == "discovered").all():
            gather_task.delay(str(business.id))

    except Exception as exc:
        db.rollback()
        raise self.retry(exc=exc)
    finally:
        db.close()
