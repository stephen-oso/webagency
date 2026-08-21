import uuid
import pytest
from unittest.mock import patch, MagicMock
from app.models.business import Business, BusinessAsset
from app.models.job import Job


def test_gather_creates_asset_and_enqueues_build(db):
    b = Business(
        name="Top Auto",
        city="Calgary",
        state="AB",
        category="auto",
        google_place_id="gp-auto123",
        status="discovered",
    )
    db.add(b)
    db.flush()
    business_id = str(b.id)

    mock_google_detail = {
        "place_id": "gp-auto123",
        "name": "Top Auto",
        "address": "1 Garage Rd",
        "city": "Calgary",
        "state": "AB",
        "phone": "403-555-0111",
        "website": None,
        "hours": ["Mon: 8AM-5PM"],
        "description": "Quality auto repair.",
        "photos": ["ref1"],
        "rating": 4.3,
        "review_count": 55,
    }

    with patch("app.workers.gather.GooglePlacesClient") as MockGoogle, \
         patch("app.workers.gather.R2StorageClient") as MockR2, \
         patch("app.workers.gather.SessionLocal", return_value=db), \
         patch("app.workers.build.build_task") as mock_build:

        MockGoogle.return_value.get_place_details.return_value = mock_google_detail
        MockGoogle.return_value.get_photo_url.return_value = "https://maps.googleapis.com/photo?ref=ref1"
        MockR2.return_value.upload_from_url.return_value = "https://r2.example.com/photo_0.jpg"

        from app.workers.gather import gather_task
        gather_task.run(business_id)

    db.refresh(b)
    assert b.status == "gathering_done"
    assert b.assets is not None
    assert b.assets.rating == 4.3
    assert "https://r2.example.com/photo_0.jpg" in b.assets.photos
    mock_build.delay.assert_called_once_with(business_id)


def test_gather_creates_job_record(db):
    b = Business(
        name="Clean Homes",
        city="Vancouver",
        state="BC",
        category="cleaning",
        google_place_id="gp-clean456",
        status="discovered",
    )
    db.add(b)
    db.flush()
    business_id = str(b.id)

    mock_google_detail = {
        "place_id": "gp-clean456",
        "name": "Clean Homes",
        "address": "10 Broom St",
        "city": "Vancouver",
        "state": "BC",
        "phone": "604-555-0200",
        "website": None,
        "hours": [],
        "description": "Professional cleaning.",
        "photos": [],
        "rating": 4.6,
        "review_count": 30,
    }

    with patch("app.workers.gather.GooglePlacesClient") as MockGoogle, \
         patch("app.workers.gather.R2StorageClient") as MockR2, \
         patch("app.workers.gather.SessionLocal", return_value=db), \
         patch("app.workers.build.build_task"):

        MockGoogle.return_value.get_place_details.return_value = mock_google_detail
        MockGoogle.return_value.get_photo_url.return_value = "https://maps.googleapis.com/photo?ref=x"
        MockR2.return_value.upload_from_url.return_value = "https://r2.example.com/x.jpg"

        from app.workers.gather import gather_task
        gather_task.run(business_id)

    jobs = db.query(Job).filter(Job.business_id == b.id, Job.step == "gather").all()
    assert len(jobs) == 1
    assert jobs[0].status == "success"


def test_gather_backfills_city_state_when_empty(db):
    """Discover worker may leave city/state blank; gather should populate them."""
    b = Business(
        name="Sparse Biz",
        city="",
        state="",
        category="retail",
        google_place_id="gp-sparse789",
        status="discovered",
    )
    db.add(b)
    db.flush()
    business_id = str(b.id)

    mock_google_detail = {
        "place_id": "gp-sparse789",
        "name": "Sparse Biz",
        "address": "5 Main St",
        "city": "Toronto",
        "state": "ON",
        "phone": None,
        "website": None,
        "hours": [],
        "description": None,
        "photos": [],
        "rating": 3.5,
        "review_count": 10,
    }

    with patch("app.workers.gather.GooglePlacesClient") as MockGoogle, \
         patch("app.workers.gather.R2StorageClient") as MockR2, \
         patch("app.workers.gather.SessionLocal", return_value=db), \
         patch("app.workers.build.build_task"):

        MockGoogle.return_value.get_place_details.return_value = mock_google_detail
        MockGoogle.return_value.get_photo_url.return_value = "https://maps.googleapis.com/photo?ref=y"
        MockR2.return_value.upload_from_url.return_value = "https://r2.example.com/y.jpg"

        from app.workers.gather import gather_task
        gather_task.run(business_id)

    db.refresh(b)
    assert b.city == "Toronto"
    assert b.state == "ON"


def test_gather_skips_missing_business(db):
    """Should return silently if business_id does not exist."""
    missing_id = str(uuid.uuid4())

    with patch("app.workers.gather.GooglePlacesClient"), \
         patch("app.workers.gather.R2StorageClient"), \
         patch("app.workers.gather.SessionLocal", return_value=db), \
         patch("app.workers.build.build_task") as mock_build:

        from app.workers.gather import gather_task
        gather_task.run(missing_id)

    mock_build.delay.assert_not_called()
    assert db.query(BusinessAsset).count() == 0


def test_gather_succeeds_when_google_fails(db):
    """Worker should complete and enqueue build even when Google Places raises."""
    b = Business(
        name="Offline Biz",
        city="Toronto",
        state="ON",
        category="retail",
        google_place_id="gp-offline999",
        status="discovered",
    )
    db.add(b)
    db.flush()
    business_id = str(b.id)

    with patch("app.workers.gather.GooglePlacesClient") as MockGoogle, \
         patch("app.workers.gather.R2StorageClient"), \
         patch("app.workers.gather.SessionLocal", return_value=db), \
         patch("app.workers.build.build_task") as mock_build:

        MockGoogle.return_value.get_place_details.side_effect = Exception("API down")

        from app.workers.gather import gather_task
        gather_task.run(business_id)

    db.refresh(b)
    assert b.status == "gathering_done"
    asset = db.query(BusinessAsset).filter(BusinessAsset.business_id == b.id).first()
    assert asset is not None
    mock_build.delay.assert_called_once_with(business_id)


def test_gather_uses_exponential_backoff_on_retry():
    """Verify retry uses countdown= not default_retry_delay."""
    import inspect
    import os

    os.environ.setdefault("DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/webagency_test")

    from app.workers import gather

    source = inspect.getsource(gather.gather_task)
    assert "default_retry_delay" not in source, (
        "gather_task must NOT use default_retry_delay; use countdown= in self.retry()"
    )
    assert "countdown=60 * (2 ** self.request.retries)" in source, (
        "gather_task must use exponential backoff: countdown=60 * (2 ** self.request.retries)"
    )
