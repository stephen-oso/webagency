import pytest
from unittest.mock import patch, MagicMock
from app.models.business import Business
from app.models.job import Job


def test_discover_creates_businesses_for_candidates(db):
    google_result = {
        "place_id": "gp-abc", "name": "Budget Plumbing", "address": "1 Water St",
        "city": "Ottawa", "state": "ON", "phone": None, "website": None,
        "rating": 3.8, "review_count": 12, "photos": [], "yelp_id": None,
    }
    yelp_result = {
        "yelp_id": "yelp-xyz", "place_id": None, "name": "Fast Fix Plumbing",
        "address": "2 Pipe Ave", "city": "Ottawa", "state": "ON",
        "phone": "613-555-0101", "website": None, "rating": 4.0, "review_count": 8, "photos": [],
    }

    with patch("app.workers.discover.GooglePlacesClient") as MockGoogle, \
         patch("app.workers.discover.YelpClient") as MockYelp, \
         patch("app.workers.discover.score_website", return_value=0), \
         patch("app.workers.discover.SessionLocal", return_value=db), \
         patch("app.workers.gather.gather_task.delay"):

        MockGoogle.return_value.search_businesses.return_value = [google_result]
        MockYelp.return_value.search_businesses.return_value = [yelp_result]

        from app.workers.discover import discover_task
        discover_task.run("Ottawa, ON", ["plumber"])

    businesses = db.query(Business).all()
    assert len(businesses) == 2
    names = {b.name for b in businesses}
    assert "Budget Plumbing" in names
    assert db.query(Job).filter(Job.step == "discover").count() >= 2


def test_discover_skips_existing_business(db):
    b = Business(name="Budget Plumbing", city="Ottawa", state="ON",
                 category="plumber", google_place_id="gp-abc", status="discovered")
    db.add(b)
    db.flush()

    google_result = {
        "place_id": "gp-abc", "name": "Budget Plumbing", "address": "1 Water St",
        "city": "Ottawa", "state": "ON", "phone": None, "website": None,
        "rating": 3.8, "review_count": 12, "photos": [], "yelp_id": None,
    }

    with patch("app.workers.discover.GooglePlacesClient") as MockGoogle, \
         patch("app.workers.discover.YelpClient") as MockYelp, \
         patch("app.workers.discover.score_website", return_value=0), \
         patch("app.workers.discover.SessionLocal", return_value=db), \
         patch("app.workers.gather.gather_task.delay"):

        MockGoogle.return_value.search_businesses.return_value = [google_result]
        MockYelp.return_value.search_businesses.return_value = []

        from app.workers.discover import discover_task
        discover_task.run("Ottawa, ON", ["plumber"])

    assert db.query(Business).count() == 1
