import uuid
from app.models.business import Business, BusinessAsset
from app.models.site import Site
from app.models.job import Job


def test_create_business(db):
    b = Business(name="Mike's Plumbing", city="Toronto", state="ON", category="plumber")
    db.add(b)
    db.flush()
    assert b.id is not None
    assert b.status == "discovered"


def test_business_with_asset(db):
    b = Business(name="City Salon", city="Vancouver", state="BC", category="salon")
    db.add(b)
    db.flush()

    asset = BusinessAsset(business_id=b.id, photos=["https://r2.example.com/photo1.jpg"], rating=4.5)
    db.add(asset)
    db.flush()

    db.refresh(b)
    assert b.assets.rating == 4.5


def test_business_with_job(db):
    b = Business(name="Top Auto", city="Calgary", state="AB", category="auto")
    db.add(b)
    db.flush()

    job = Job(business_id=b.id, step="discover", status="success")
    db.add(job)
    db.flush()

    db.refresh(b)
    assert b.jobs[0].step == "discover"
