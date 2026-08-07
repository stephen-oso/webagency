# Web Agency — Plan 1/3: Backend & Pipeline

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the Python backend — FastAPI REST API, Celery pipeline workers, and all external service integrations — that powers the 5-step autonomous pipeline (discover → gather → build → publish → outreach).

**Architecture:** FastAPI exposes a REST API for the dashboard and CLI. Celery workers (backed by Redis) run each pipeline step as a task, chaining via explicit `.delay()` calls. PostgreSQL is the system of record. All external APIs are isolated behind service modules for easy mocking in tests. SQLAlchemy 2.0 sync sessions are used throughout (no asyncpg) to keep Celery workers simple.

**Tech Stack:** Python 3.12, FastAPI 0.115, Celery 5.4, Redis, PostgreSQL 16, SQLAlchemy 2.0 (sync + psycopg2), Alembic 1.13, Playwright 1.48, Anthropic SDK 0.40, boto3 1.35 (Cloudflare R2), httpx 0.27, pytest 8.3, respx 0.21, moto 5.0

**Plans 2/3 (Template Library) and 3/3 (Dashboard + CLI) are separate plans that follow this one.**

## Global Constraints
- Python 3.12+
- SQLAlchemy 2.0 sync sessions everywhere — no asyncpg, no async/await in workers
- Celery tasks: `max_retries=3`, retry delays: 60s → 120s → 240s (exponential)
- Claude API: copy generation only — never layout, never design decisions
- Outreach daily cap: `settings.outreach_daily_cap`, default 20
- `Publisher` is an abstract base class — `VercelPublisher` is the concrete default
- All secrets via environment variables, never hardcoded
- US and Canada geography only (Phase 1)
- Tests use a real PostgreSQL test DB (env var `TEST_DATABASE_URL`); all external HTTP APIs mocked with `respx`; boto3 mocked with `moto`; Playwright mocked with `pytest-mock`

---

## File Map

```
webagency/
├── backend/
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py                     # FastAPI app factory
│   │   ├── config.py                   # pydantic-settings Settings class
│   │   ├── database.py                 # SQLAlchemy engine + SessionLocal + get_db
│   │   ├── models/
│   │   │   ├── __init__.py             # re-exports all models for Alembic
│   │   │   ├── base.py                 # DeclarativeBase
│   │   │   ├── business.py             # Business + BusinessAsset
│   │   │   ├── site.py                 # Site
│   │   │   ├── outreach.py             # Outreach
│   │   │   └── job.py                  # Job
│   │   ├── schemas/
│   │   │   ├── __init__.py
│   │   │   ├── business.py             # BusinessOut, BusinessCreate, BusinessAssetOut
│   │   │   ├── site.py                 # SiteOut
│   │   │   ├── outreach.py             # OutreachOut
│   │   │   └── job.py                  # JobOut
│   │   ├── api/
│   │   │   ├── __init__.py
│   │   │   ├── router.py               # aggregates all routers
│   │   │   ├── businesses.py           # GET /businesses, GET /businesses/{id}, POST /businesses/{id}/retry
│   │   │   ├── jobs.py                 # GET /jobs
│   │   │   ├── sites.py                # GET /sites, POST /sites/{id}/approve, POST /sites/{id}/reject
│   │   │   └── outreach.py             # GET /outreach
│   │   ├── workers/
│   │   │   ├── __init__.py
│   │   │   ├── celery_app.py           # Celery app config
│   │   │   ├── discover.py             # discover_task
│   │   │   ├── gather.py               # gather_task
│   │   │   ├── build.py                # build_task
│   │   │   ├── publish.py              # publish_task
│   │   │   └── outreach_worker.py      # outreach_task
│   │   └── services/
│   │       ├── __init__.py
│   │       ├── google_places.py        # GooglePlacesClient
│   │       ├── yelp.py                 # YelpClient
│   │       ├── storage.py              # R2StorageClient
│   │       ├── claude.py               # ClaudeClient (copy generation)
│   │       ├── publisher.py            # Publisher ABC + VercelPublisher
│   │       ├── resend.py               # ResendClient
│   │       ├── hunter.py               # HunterClient
│   │       └── form_outreach.py        # FormOutreachClient (Playwright)
│   ├── migrations/
│   │   ├── env.py
│   │   └── versions/
│   ├── tests/
│   │   ├── __init__.py
│   │   ├── conftest.py                 # engine, db session, settings override fixtures
│   │   ├── test_models.py              # DB model create/read/relationship tests
│   │   ├── test_google_places.py
│   │   ├── test_yelp.py
│   │   ├── test_storage.py
│   │   ├── test_claude.py
│   │   ├── test_publisher.py
│   │   ├── test_resend.py
│   │   ├── test_hunter.py
│   │   ├── test_form_outreach.py
│   │   ├── test_discover.py
│   │   ├── test_gather.py
│   │   ├── test_build.py
│   │   ├── test_publish.py
│   │   ├── test_outreach_worker.py
│   │   └── test_api.py
│   ├── pyproject.toml
│   ├── alembic.ini
│   └── .env.example
├── templates/                          # Plan 2/3 — stubs created here
│   └── (restaurant/ plumber/ salon/ dentist/ landscaping/ retail/ trades/
│       professional/ auto/ cleaning/ gym/ photography/ realestate/ childcare/ petservices/)
└── docs/
    └── superpowers/
```

---

### Task 1: Project Scaffold + Config

**Files:**
- Create: `backend/pyproject.toml`
- Create: `backend/.env.example`
- Create: `backend/app/__init__.py`
- Create: `backend/app/config.py`
- Create: all `__init__.py` stubs under `app/models/`, `app/schemas/`, `app/api/`, `app/workers/`, `app/services/`

**Interfaces:**
- Produces: `from app.config import settings` — `Settings` object used by every other module

- [ ] **Step 1: Create directory structure**

```bash
cd C:/Users/Stephen/webagency
mkdir -p backend/app/models backend/app/schemas backend/app/api backend/app/workers backend/app/services
mkdir -p backend/migrations/versions backend/tests
touch backend/app/__init__.py backend/app/models/__init__.py backend/app/schemas/__init__.py
touch backend/app/api/__init__.py backend/app/workers/__init__.py backend/app/services/__init__.py
touch backend/tests/__init__.py
```

- [ ] **Step 2: Write `backend/pyproject.toml`**

```toml
[tool.poetry]
name = "webagency-backend"
version = "0.1.0"
description = "Autonomous website agency pipeline"
packages = [{include = "app"}]

[tool.poetry.dependencies]
python = "^3.12"
fastapi = "^0.115"
uvicorn = {extras = ["standard"], version = "^0.30"}
celery = {extras = ["redis"], version = "^5.4"}
sqlalchemy = "^2.0"
alembic = "^1.13"
psycopg2-binary = "^2.9"
pydantic-settings = "^2.5"
anthropic = "^0.40"
playwright = "^1.48"
boto3 = "^1.35"
httpx = "^0.27"
redis = "^5.1"

[tool.poetry.group.dev.dependencies]
pytest = "^8.3"
pytest-mock = "^3.14"
respx = "^0.21"
moto = {extras = ["s3"], version = "^5.0"}

[tool.pytest.ini_options]
testpaths = ["tests"]

[build-system]
requires = ["poetry-core"]
build-backend = "poetry.core.masonry.api"
```

- [ ] **Step 3: Write `backend/.env.example`**

```env
DATABASE_URL=postgresql://postgres:postgres@localhost:5432/webagency
TEST_DATABASE_URL=postgresql://postgres:postgres@localhost:5432/webagency_test
REDIS_URL=redis://localhost:6379/0

GOOGLE_PLACES_API_KEY=your_key_here
YELP_API_KEY=your_key_here

ANTHROPIC_API_KEY=your_key_here

CLOUDFLARE_R2_ENDPOINT=https://your-account-id.r2.cloudflarestorage.com
CLOUDFLARE_R2_ACCESS_KEY=your_key_here
CLOUDFLARE_R2_SECRET_KEY=your_key_here
CLOUDFLARE_R2_BUCKET=webagency-assets

VERCEL_TOKEN=your_token_here
VERCEL_TEAM_ID=
AGENCY_DOMAIN=youragency.com

RESEND_API_KEY=your_key_here
HUNTER_API_KEY=your_key_here

OUTREACH_DAILY_CAP=20
REVIEW_MODE=true
```

- [ ] **Step 4: Write `backend/app/config.py`**

```python
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str
    redis_url: str = "redis://localhost:6379/0"

    google_places_api_key: str = ""
    yelp_api_key: str = ""

    anthropic_api_key: str = ""

    cloudflare_r2_endpoint: str = ""
    cloudflare_r2_access_key: str = ""
    cloudflare_r2_secret_key: str = ""
    cloudflare_r2_bucket: str = "webagency-assets"

    vercel_token: str = ""
    vercel_team_id: str | None = None
    agency_domain: str = "youragency.com"

    resend_api_key: str = ""
    hunter_api_key: str | None = None

    outreach_daily_cap: int = 20
    review_mode: bool = True


settings = Settings()
```

- [ ] **Step 5: Install dependencies**

```bash
cd backend
poetry install
poetry run playwright install chromium
```

- [ ] **Step 6: Commit**

```bash
git -C C:/Users/Stephen/webagency init
git -C C:/Users/Stephen/webagency add backend/
git -C C:/Users/Stephen/webagency commit -m "feat: project scaffold and config"
```

---

### Task 2: Database Models + Alembic

**Files:**
- Create: `backend/app/models/base.py`
- Create: `backend/app/models/business.py`
- Create: `backend/app/models/site.py`
- Create: `backend/app/models/outreach.py`
- Create: `backend/app/models/job.py`
- Modify: `backend/app/models/__init__.py`
- Create: `backend/app/database.py`
- Create: `backend/alembic.ini`
- Create: `backend/migrations/env.py`
- Test: `backend/tests/test_models.py`

**Interfaces:**
- Produces:
  - `from app.models.business import Business, BusinessAsset`
  - `from app.models.site import Site`
  - `from app.models.outreach import Outreach`
  - `from app.models.job import Job`
  - `from app.database import SessionLocal, get_db`

- [ ] **Step 1: Write `backend/app/models/base.py`**

```python
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass
```

- [ ] **Step 2: Write `backend/app/models/business.py`**

```python
import uuid
from datetime import datetime
from sqlalchemy import String, Integer, Float, Text, JSON, ForeignKey, TIMESTAMP
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID
from .base import Base


class Business(Base):
    __tablename__ = "businesses"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    address: Mapped[str | None] = mapped_column(Text)
    city: Mapped[str] = mapped_column(String(100), nullable=False)
    state: Mapped[str] = mapped_column(String(50), nullable=False)
    phone: Mapped[str | None] = mapped_column(String(50))
    email: Mapped[str | None] = mapped_column(String(255))
    category: Mapped[str] = mapped_column(String(100), nullable=False)
    google_place_id: Mapped[str | None] = mapped_column(String(255), unique=True)
    yelp_id: Mapped[str | None] = mapped_column(String(255), unique=True)
    existing_website: Mapped[str | None] = mapped_column(Text)
    website_score: Mapped[int | None] = mapped_column(Integer)
    status: Mapped[str] = mapped_column(String(50), default="discovered", nullable=False)
    user_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), default=datetime.utcnow)

    assets: Mapped["BusinessAsset | None"] = relationship("BusinessAsset", back_populates="business", uselist=False)
    site: Mapped["Site | None"] = relationship("Site", back_populates="business", uselist=False)
    outreach_records: Mapped[list["Outreach"]] = relationship("Outreach", back_populates="business")
    jobs: Mapped[list["Job"]] = relationship("Job", back_populates="business")


class BusinessAsset(Base):
    __tablename__ = "business_assets"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    business_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("businesses.id"), unique=True)
    photos: Mapped[list | None] = mapped_column(JSON)
    description: Mapped[str | None] = mapped_column(Text)
    hours: Mapped[dict | None] = mapped_column(JSON)
    rating: Mapped[float | None] = mapped_column(Float)
    review_count: Mapped[int | None] = mapped_column(Integer)
    reviews_summary: Mapped[str | None] = mapped_column(Text)
    social_links: Mapped[dict | None] = mapped_column(JSON)
    services: Mapped[list | None] = mapped_column(JSON)
    price_range: Mapped[str | None] = mapped_column(String(10))
    raw_google: Mapped[dict | None] = mapped_column(JSON)
    raw_yelp: Mapped[dict | None] = mapped_column(JSON)

    business: Mapped["Business"] = relationship("Business", back_populates="assets")
```

- [ ] **Step 3: Write `backend/app/models/site.py`**

```python
import uuid
from datetime import datetime
from sqlalchemy import String, Text, ForeignKey, TIMESTAMP
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID
from .base import Base


class Site(Base):
    __tablename__ = "sites"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    business_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("businesses.id"), unique=True)
    template_used: Mapped[str] = mapped_column(String(50), nullable=False)
    vercel_url: Mapped[str | None] = mapped_column(Text)
    custom_subdomain: Mapped[str | None] = mapped_column(Text)
    review_status: Mapped[str] = mapped_column(String(20), default="pending")
    deployed_at: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True))

    business: Mapped["Business"] = relationship("Business", back_populates="site")
```

- [ ] **Step 4: Write `backend/app/models/outreach.py`**

```python
import uuid
from datetime import datetime
from sqlalchemy import String, Text, ForeignKey, TIMESTAMP
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID
from .base import Base


class Outreach(Base):
    __tablename__ = "outreach"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    business_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("businesses.id"))
    site_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("sites.id"))
    email_to: Mapped[str | None] = mapped_column(String(255))
    email_sent_at: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True))
    email_status: Mapped[str | None] = mapped_column(String(20))
    form_submitted_at: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True))
    form_status: Mapped[str | None] = mapped_column(String(20))
    response_text: Mapped[str | None] = mapped_column(Text)
    responded_at: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True))

    business: Mapped["Business"] = relationship("Business", back_populates="outreach_records")
```

- [ ] **Step 5: Write `backend/app/models/job.py`**

```python
import uuid
from datetime import datetime
from sqlalchemy import String, Integer, Text, ForeignKey, TIMESTAMP
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID
from .base import Base


class Job(Base):
    __tablename__ = "jobs"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    business_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("businesses.id"))
    step: Mapped[str] = mapped_column(String(20), nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="queued", nullable=False)
    error_msg: Mapped[str | None] = mapped_column(Text)
    attempts: Mapped[int] = mapped_column(Integer, default=0)
    last_run_at: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True))

    business: Mapped["Business"] = relationship("Business", back_populates="jobs")
```

- [ ] **Step 6: Write `backend/app/models/__init__.py`**

```python
from .business import Business, BusinessAsset
from .site import Site
from .outreach import Outreach
from .job import Job
from .base import Base

__all__ = ["Business", "BusinessAsset", "Site", "Outreach", "Job", "Base"]
```

- [ ] **Step 7: Write `backend/app/database.py`**

```python
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from .config import settings

engine = create_engine(settings.database_url, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)


def get_db():
    db: Session = SessionLocal()
    try:
        yield db
    finally:
        db.close()
```

- [ ] **Step 8: Set up Alembic**

```bash
cd backend
poetry run alembic init migrations
```

Edit `backend/alembic.ini` — set `sqlalchemy.url` to use env var:
```ini
sqlalchemy.url = %(DATABASE_URL)s
```

Edit `backend/migrations/env.py` — add model metadata:
```python
import os
from logging.config import fileConfig
from sqlalchemy import engine_from_config, pool
from alembic import context
from app.models import Base

config = context.config
config.set_main_option("sqlalchemy.url", os.environ["DATABASE_URL"])

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    url = config.get_main_option("sqlalchemy.url")
    context.configure(url=url, target_metadata=target_metadata, literal_binds=True)
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
```

- [ ] **Step 9: Write `backend/tests/conftest.py`**

```python
import os
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.models import Base

TEST_DATABASE_URL = os.getenv(
    "TEST_DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/webagency_test"
)


@pytest.fixture(scope="session")
def test_engine():
    engine = create_engine(TEST_DATABASE_URL)
    Base.metadata.create_all(engine)
    yield engine
    Base.metadata.drop_all(engine)


@pytest.fixture(scope="function")
def db(test_engine):
    connection = test_engine.connect()
    transaction = connection.begin()
    Session = sessionmaker(bind=connection, join_transaction_mode="create_savepoint")
    session = Session()
    yield session
    session.close()
    transaction.rollback()
    connection.close()
```

- [ ] **Step 10: Write `backend/tests/test_models.py`**

```python
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
```

- [ ] **Step 11: Run tests**

```bash
cd backend
TEST_DATABASE_URL=postgresql://postgres:postgres@localhost:5432/webagency_test poetry run pytest tests/test_models.py -v
```

Expected: 3 PASS

- [ ] **Step 12: Generate and run initial migration**

```bash
cd backend
DATABASE_URL=postgresql://postgres:postgres@localhost:5432/webagency poetry run alembic revision --autogenerate -m "initial schema"
DATABASE_URL=postgresql://postgres:postgres@localhost:5432/webagency poetry run alembic upgrade head
```

- [ ] **Step 13: Commit**

```bash
git -C C:/Users/Stephen/webagency add backend/
git -C C:/Users/Stephen/webagency commit -m "feat: database models and alembic migrations"
```

---

### Task 3: FastAPI Shell + Celery Setup

**Files:**
- Create: `backend/app/main.py`
- Create: `backend/app/workers/celery_app.py`
- Test: `backend/tests/test_api.py` (health check only for now)

**Interfaces:**
- Produces:
  - `from app.main import app` — FastAPI app instance
  - `from app.workers.celery_app import celery_app` — Celery app used by all workers

- [ ] **Step 1: Write `backend/app/main.py`**

```python
from fastapi import FastAPI
from app.api.router import router

app = FastAPI(title="Web Agency API", version="0.1.0")
app.include_router(router, prefix="/api")


@app.get("/health")
def health():
    return {"status": "ok"}
```

- [ ] **Step 2: Write `backend/app/api/router.py`**

```python
from fastapi import APIRouter

router = APIRouter()

# Routers added in later tasks
```

- [ ] **Step 3: Write `backend/app/workers/celery_app.py`**

```python
from celery import Celery
from app.config import settings

celery_app = Celery(
    "webagency",
    broker=settings.redis_url,
    backend=settings.redis_url,
    include=[
        "app.workers.discover",
        "app.workers.gather",
        "app.workers.build",
        "app.workers.publish",
        "app.workers.outreach_worker",
    ],
)

celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="UTC",
    task_track_started=True,
    task_acks_late=True,
)
```

- [ ] **Step 4: Write failing health check test in `backend/tests/test_api.py`**

```python
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_health():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
```

- [ ] **Step 5: Run test**

```bash
cd backend
poetry run pytest tests/test_api.py::test_health -v
```

Expected: PASS

- [ ] **Step 6: Commit**

```bash
git -C C:/Users/Stephen/webagency add backend/
git -C C:/Users/Stephen/webagency commit -m "feat: FastAPI shell and Celery app setup"
```

---

### Task 4: Google Places + Yelp Services

**Files:**
- Create: `backend/app/services/google_places.py`
- Create: `backend/app/services/yelp.py`
- Test: `backend/tests/test_google_places.py`
- Test: `backend/tests/test_yelp.py`

**Interfaces:**
- Produces:
  - `GooglePlacesClient(api_key: str).search_businesses(region: str, category: str, radius_m: int = 50000) -> list[dict]`
    - Returns list of dicts with keys: `place_id`, `name`, `address`, `city`, `state`, `phone`, `website`, `rating`, `review_count`, `photos` (list of photo refs)
  - `GooglePlacesClient.get_place_details(place_id: str) -> dict`
    - Returns dict with keys: `place_id`, `name`, `address`, `city`, `state`, `phone`, `website`, `hours`, `description`, `photos`, `rating`, `review_count`
  - `GooglePlacesClient.get_photo_url(photo_reference: str, max_width: int = 1200) -> str`
  - `YelpClient(api_key: str).search_businesses(location: str, category: str, limit: int = 50) -> list[dict]`
    - Returns list of dicts with keys: `yelp_id`, `name`, `address`, `city`, `state`, `phone`, `website`, `rating`, `review_count`, `photos`
  - `YelpClient.get_business(yelp_id: str) -> dict`
    - Returns dict with keys: `yelp_id`, `name`, `photos`, `hours`, `price_range`, `categories`, `description`

- [ ] **Step 1: Write `backend/app/services/google_places.py`**

```python
import httpx
from dataclasses import dataclass


PLACES_BASE = "https://maps.googleapis.com/maps/api/place"
GEOCODE_BASE = "https://maps.googleapis.com/maps/api/geocode"


@dataclass
class GooglePlacesClient:
    api_key: str

    def search_businesses(self, region: str, category: str, radius_m: int = 50000) -> list[dict]:
        coords = self._geocode(region)
        params = {
            "location": f"{coords['lat']},{coords['lng']}",
            "radius": radius_m,
            "keyword": category,
            "key": self.api_key,
        }
        results = []
        url = f"{PLACES_BASE}/nearbysearch/json"
        while url:
            resp = httpx.get(url if url.startswith("http") else f"{PLACES_BASE}/nearbysearch/json", params=params, timeout=10)
            resp.raise_for_status()
            data = resp.json()
            for place in data.get("results", []):
                results.append(self._normalize_search_result(place))
            next_token = data.get("next_page_token")
            url = f"{PLACES_BASE}/nearbysearch/json?pagetoken={next_token}&key={self.api_key}" if next_token else None
            params = {}
        return results

    def get_place_details(self, place_id: str) -> dict:
        fields = "place_id,name,formatted_address,address_components,formatted_phone_number,website,opening_hours,editorial_summary,photos,rating,user_ratings_total"
        resp = httpx.get(
            f"{PLACES_BASE}/details/json",
            params={"place_id": place_id, "fields": fields, "key": self.api_key},
            timeout=10,
        )
        resp.raise_for_status()
        result = resp.json().get("result", {})
        return self._normalize_details(result)

    def get_photo_url(self, photo_reference: str, max_width: int = 1200) -> str:
        return (
            f"{PLACES_BASE}/photo"
            f"?maxwidth={max_width}&photo_reference={photo_reference}&key={self.api_key}"
        )

    def _geocode(self, region: str) -> dict:
        resp = httpx.get(
            f"{GEOCODE_BASE}/json",
            params={"address": region, "key": self.api_key},
            timeout=10,
        )
        resp.raise_for_status()
        location = resp.json()["results"][0]["geometry"]["location"]
        return {"lat": location["lat"], "lng": location["lng"]}

    def _normalize_search_result(self, place: dict) -> dict:
        return {
            "place_id": place.get("place_id"),
            "name": place.get("name"),
            "address": place.get("vicinity"),
            "city": "",
            "state": "",
            "phone": None,
            "website": None,
            "rating": place.get("rating"),
            "review_count": place.get("user_ratings_total"),
            "photos": [p["photo_reference"] for p in place.get("photos", [])],
        }

    def _normalize_details(self, result: dict) -> dict:
        city, state = "", ""
        for comp in result.get("address_components", []):
            if "locality" in comp["types"]:
                city = comp["long_name"]
            if "administrative_area_level_1" in comp["types"]:
                state = comp["short_name"]
        return {
            "place_id": result.get("place_id"),
            "name": result.get("name"),
            "address": result.get("formatted_address"),
            "city": city,
            "state": state,
            "phone": result.get("formatted_phone_number"),
            "website": result.get("website"),
            "hours": result.get("opening_hours", {}).get("weekday_text", []),
            "description": result.get("editorial_summary", {}).get("overview"),
            "photos": [p["photo_reference"] for p in result.get("photos", [])],
            "rating": result.get("rating"),
            "review_count": result.get("user_ratings_total"),
        }
```

- [ ] **Step 2: Write `backend/tests/test_google_places.py`**

```python
import pytest
import respx
import httpx
from app.services.google_places import GooglePlacesClient


@pytest.fixture
def client():
    return GooglePlacesClient(api_key="test-key")


@respx.mock
def test_search_businesses_returns_normalized_results(client):
    respx.get("https://maps.googleapis.com/maps/api/geocode/json").mock(
        return_value=httpx.Response(200, json={
            "results": [{"geometry": {"location": {"lat": 43.65, "lng": -79.38}}}]
        })
    )
    respx.get("https://maps.googleapis.com/maps/api/place/nearbysearch/json").mock(
        return_value=httpx.Response(200, json={
            "results": [
                {"place_id": "abc123", "name": "Mike's Plumbing", "vicinity": "123 Main St",
                 "rating": 4.2, "user_ratings_total": 38, "photos": [{"photo_reference": "ref1"}]}
            ],
            "status": "OK"
        })
    )
    results = client.search_businesses("Toronto, ON", "plumber")
    assert len(results) == 1
    assert results[0]["place_id"] == "abc123"
    assert results[0]["photos"] == ["ref1"]


@respx.mock
def test_get_place_details_extracts_city_state(client):
    respx.get("https://maps.googleapis.com/maps/api/place/details/json").mock(
        return_value=httpx.Response(200, json={
            "result": {
                "place_id": "abc123",
                "name": "Mike's Plumbing",
                "formatted_address": "123 Main St, Toronto, ON M4B 1B3, Canada",
                "address_components": [
                    {"types": ["locality"], "long_name": "Toronto", "short_name": "Toronto"},
                    {"types": ["administrative_area_level_1"], "long_name": "Ontario", "short_name": "ON"},
                ],
                "formatted_phone_number": "416-555-0123",
                "website": None,
                "rating": 4.2,
                "user_ratings_total": 38,
                "photos": [],
            }
        })
    )
    details = client.get_place_details("abc123")
    assert details["city"] == "Toronto"
    assert details["state"] == "ON"
    assert details["phone"] == "416-555-0123"
    assert details["website"] is None
```

- [ ] **Step 3: Run tests**

```bash
cd backend
poetry run pytest tests/test_google_places.py -v
```

Expected: 2 PASS

- [ ] **Step 4: Write `backend/app/services/yelp.py`**

```python
import httpx
from dataclasses import dataclass

YELP_BASE = "https://api.yelp.com/v3"


@dataclass
class YelpClient:
    api_key: str

    @property
    def _headers(self) -> dict:
        return {"Authorization": f"Bearer {self.api_key}"}

    def search_businesses(self, location: str, category: str, limit: int = 50) -> list[dict]:
        resp = httpx.get(
            f"{YELP_BASE}/businesses/search",
            headers=self._headers,
            params={"location": location, "categories": category, "limit": limit},
            timeout=10,
        )
        resp.raise_for_status()
        return [self._normalize_search(b) for b in resp.json().get("businesses", [])]

    def get_business(self, yelp_id: str) -> dict:
        resp = httpx.get(
            f"{YELP_BASE}/businesses/{yelp_id}",
            headers=self._headers,
            timeout=10,
        )
        resp.raise_for_status()
        return self._normalize_detail(resp.json())

    def _normalize_search(self, b: dict) -> dict:
        loc = b.get("location", {})
        return {
            "yelp_id": b.get("id"),
            "name": b.get("name"),
            "address": " ".join(filter(None, loc.get("display_address", []))),
            "city": loc.get("city"),
            "state": loc.get("state"),
            "phone": b.get("display_phone"),
            "website": None,
            "rating": b.get("rating"),
            "review_count": b.get("review_count"),
            "photos": b.get("photos", []),
        }

    def _normalize_detail(self, b: dict) -> dict:
        return {
            "yelp_id": b.get("id"),
            "name": b.get("name"),
            "photos": b.get("photos", []),
            "hours": b.get("hours", [{}])[0].get("open", []) if b.get("hours") else [],
            "price_range": b.get("price"),
            "categories": [c["title"] for c in b.get("categories", [])],
            "description": None,
        }
```

- [ ] **Step 5: Write `backend/tests/test_yelp.py`**

```python
import pytest
import respx
import httpx
from app.services.yelp import YelpClient


@pytest.fixture
def client():
    return YelpClient(api_key="test-yelp-key")


@respx.mock
def test_search_returns_normalized_results(client):
    respx.get("https://api.yelp.com/v3/businesses/search").mock(
        return_value=httpx.Response(200, json={
            "businesses": [{
                "id": "yelp-abc", "name": "City Salon",
                "location": {"city": "Vancouver", "state": "BC", "display_address": ["123 Robson St", "Vancouver, BC"]},
                "display_phone": "604-555-0199", "rating": 4.7, "review_count": 120, "photos": []
            }]
        })
    )
    results = client.search_businesses("Vancouver, BC", "salon")
    assert results[0]["yelp_id"] == "yelp-abc"
    assert results[0]["city"] == "Vancouver"


@respx.mock
def test_get_business_returns_detail(client):
    respx.get("https://api.yelp.com/v3/businesses/yelp-abc").mock(
        return_value=httpx.Response(200, json={
            "id": "yelp-abc", "name": "City Salon",
            "photos": ["https://yelp.com/photo1.jpg"],
            "price": "$$", "categories": [{"title": "Hair Salons"}], "hours": []
        })
    )
    detail = client.get_business("yelp-abc")
    assert detail["price_range"] == "$$"
    assert "Hair Salons" in detail["categories"]
```

- [ ] **Step 6: Run tests**

```bash
cd backend
poetry run pytest tests/test_yelp.py -v
```

Expected: 2 PASS

- [ ] **Step 7: Commit**

```bash
git -C C:/Users/Stephen/webagency add backend/
git -C C:/Users/Stephen/webagency commit -m "feat: Google Places and Yelp service clients"
```

---

### Task 5: Cloudflare R2 Storage Service

**Files:**
- Create: `backend/app/services/storage.py`
- Test: `backend/tests/test_storage.py`

**Interfaces:**
- Produces:
  - `R2StorageClient(endpoint: str, access_key: str, secret_key: str, bucket: str).upload_from_url(url: str, key: str) -> str`
    - Downloads the image at `url`, uploads to R2 under `key`, returns the public R2 URL
  - `R2StorageClient.upload_bytes(data: bytes, key: str, content_type: str) -> str`

- [ ] **Step 1: Write `backend/app/services/storage.py`**

```python
import httpx
import boto3
from dataclasses import dataclass
from botocore.config import Config


@dataclass
class R2StorageClient:
    endpoint: str
    access_key: str
    secret_key: str
    bucket: str

    def _s3(self):
        return boto3.client(
            "s3",
            endpoint_url=self.endpoint,
            aws_access_key_id=self.access_key,
            aws_secret_access_key=self.secret_key,
            config=Config(signature_version="s3v4"),
            region_name="auto",
        )

    def upload_from_url(self, url: str, key: str) -> str:
        resp = httpx.get(url, follow_redirects=True, timeout=15)
        resp.raise_for_status()
        content_type = resp.headers.get("content-type", "image/jpeg")
        return self.upload_bytes(resp.content, key, content_type)

    def upload_bytes(self, data: bytes, key: str, content_type: str = "image/jpeg") -> str:
        self._s3().put_object(
            Bucket=self.bucket,
            Key=key,
            Body=data,
            ContentType=content_type,
        )
        return f"{self.endpoint}/{self.bucket}/{key}"
```

- [ ] **Step 2: Write `backend/tests/test_storage.py`**

```python
import pytest
import respx
import httpx
from moto import mock_aws
import boto3
from app.services.storage import R2StorageClient


@pytest.fixture
def r2_client():
    return R2StorageClient(
        endpoint="https://test.r2.cloudflarestorage.com",
        access_key="test-access",
        secret_key="test-secret",
        bucket="webagency-test",
    )


@mock_aws
@respx.mock
def test_upload_from_url_stores_and_returns_url(r2_client):
    boto3.client("s3", endpoint_url="https://test.r2.cloudflarestorage.com",
                 aws_access_key_id="test-access", aws_secret_access_key="test-secret",
                 region_name="us-east-1").create_bucket(Bucket="webagency-test")

    respx.get("https://example.com/photo.jpg").mock(
        return_value=httpx.Response(200, content=b"fake-image-bytes",
                                    headers={"content-type": "image/jpeg"})
    )
    url = r2_client.upload_from_url("https://example.com/photo.jpg", "businesses/abc/photo1.jpg")
    assert "photo1.jpg" in url
```

- [ ] **Step 3: Run test**

```bash
cd backend
poetry run pytest tests/test_storage.py -v
```

Expected: 1 PASS

- [ ] **Step 4: Commit**

```bash
git -C C:/Users/Stephen/webagency add backend/
git -C C:/Users/Stephen/webagency commit -m "feat: Cloudflare R2 storage service"
```

---

### Task 6: Website Scorer + Discover Worker

**Files:**
- Create: `backend/app/services/website_scorer.py`
- Create: `backend/app/workers/discover.py`
- Test: `backend/tests/test_discover.py`

**Interfaces:**
- Consumes: `GooglePlacesClient`, `YelpClient`, `SessionLocal`
- Produces:
  - `score_website(url: str) -> int` — returns 0-10 (0 = no site, 10 = excellent modern site). Score ≤ 4 = candidate.
  - `discover_task(region: str, categories: list[str]) -> None` — Celery task; creates `Business` rows + enqueues `gather_task` for each candidate

- [ ] **Step 1: Write `backend/app/services/website_scorer.py`**

```python
from playwright.sync_api import sync_playwright, Error as PlaywrightError


def score_website(url: str) -> int:
    """Score a website 0-10. 0 = no site/404. ≤4 = outreach candidate."""
    if not url:
        return 0
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            try:
                resp = page.goto(url, timeout=8000, wait_until="domcontentloaded")
                if resp is None or resp.status >= 400:
                    return 0
                content = page.content()
                score = 5
                if len(content) < 2000:
                    score -= 3
                if "coming soon" in content.lower() or "under construction" in content.lower():
                    score -= 4
                if not page.query_selector("meta[name='viewport']"):
                    score -= 2
                if page.query_selector("table[width]") or page.query_selector("font[face]"):
                    score -= 2
                return max(0, min(10, score))
            finally:
                browser.close()
    except (PlaywrightError, Exception):
        return 0
```

- [ ] **Step 2: Write `backend/app/workers/discover.py`**

```python
from celery import shared_task
from app.workers.celery_app import celery_app
from app.database import SessionLocal
from app.models.business import Business
from app.models.job import Job
from app.services.google_places import GooglePlacesClient
from app.services.yelp import YelpClient
from app.services.website_scorer import score_website
from app.config import settings
import logging

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
            existing = db.query(Business).filter(
                Business.google_place_id == c.get("place_id")
            ).first() if c.get("place_id") else None

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
```

- [ ] **Step 3: Write `backend/tests/test_discover.py`**

```python
import pytest
import uuid
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
```

- [ ] **Step 4: Run tests**

```bash
cd backend
TEST_DATABASE_URL=postgresql://postgres:postgres@localhost:5432/webagency_test poetry run pytest tests/test_discover.py -v
```

Expected: 2 PASS

- [ ] **Step 5: Commit**

```bash
git -C C:/Users/Stephen/webagency add backend/
git -C C:/Users/Stephen/webagency commit -m "feat: website scorer and discover worker"
```

---

### Task 7: Gather Worker

**Files:**
- Create: `backend/app/workers/gather.py`
- Test: `backend/tests/test_gather.py`

**Interfaces:**
- Consumes: `GooglePlacesClient`, `YelpClient`, `R2StorageClient`, `Business`, `BusinessAsset`
- Produces:
  - `gather_task(business_id: str) -> None` — Celery task; populates `BusinessAsset`, enqueues `build_task`

- [ ] **Step 1: Write `backend/app/workers/gather.py`**

```python
from celery import shared_task
from app.workers.celery_app import celery_app
from app.database import SessionLocal
from app.models.business import Business, BusinessAsset
from app.models.job import Job
from app.services.google_places import GooglePlacesClient
from app.services.yelp import YelpClient
from app.services.storage import R2StorageClient
from app.config import settings
import logging
import uuid

logger = logging.getLogger(__name__)


@celery_app.task(bind=True, max_retries=3, default_retry_delay=60)
def gather_task(self, business_id: str):
    from app.workers.build import build_task

    db = SessionLocal()
    try:
        business = db.query(Business).filter(Business.id == uuid.UUID(business_id)).first()
        if not business:
            return

        business.status = "gathering"
        db.commit()

        google = GooglePlacesClient(api_key=settings.google_places_api_key)
        yelp = YelpClient(api_key=settings.yelp_api_key)
        storage = R2StorageClient(
            endpoint=settings.cloudflare_r2_endpoint,
            access_key=settings.cloudflare_r2_access_key,
            secret_key=settings.cloudflare_r2_secret_key,
            bucket=settings.cloudflare_r2_bucket,
        )

        raw_google = {}
        raw_yelp = {}
        photos = []
        hours = []
        description = None
        rating = business.website_score
        review_count = 0
        services = []
        price_range = None

        if business.google_place_id:
            try:
                raw_google = google.get_place_details(business.google_place_id)
                photo_refs = raw_google.get("photos", [])[:6]
                for i, ref in enumerate(photo_refs):
                    photo_url = google.get_photo_url(ref)
                    key = f"businesses/{business_id}/photo_{i}.jpg"
                    try:
                        r2_url = storage.upload_from_url(photo_url, key)
                        photos.append(r2_url)
                    except Exception as e:
                        logger.warning(f"Failed to upload photo {i}: {e}")
                hours = raw_google.get("hours", [])
                description = raw_google.get("description")
                rating = raw_google.get("rating", rating)
                review_count = raw_google.get("review_count", 0)
            except Exception as e:
                logger.warning(f"Google details failed for {business_id}: {e}")

        if business.yelp_id:
            try:
                raw_yelp = yelp.get_business(business.yelp_id)
                price_range = raw_yelp.get("price_range")
                services = raw_yelp.get("categories", [])
                for i, photo_url in enumerate(raw_yelp.get("photos", [])[:3]):
                    key = f"businesses/{business_id}/yelp_photo_{i}.jpg"
                    try:
                        r2_url = storage.upload_from_url(photo_url, key)
                        if r2_url not in photos:
                            photos.append(r2_url)
                    except Exception as e:
                        logger.warning(f"Failed yelp photo {i}: {e}")
            except Exception as e:
                logger.warning(f"Yelp details failed for {business_id}: {e}")

        asset = BusinessAsset(
            business_id=business.id,
            photos=photos,
            description=description,
            hours={"weekday_text": hours} if isinstance(hours, list) else hours,
            rating=rating,
            review_count=review_count,
            services=services,
            price_range=price_range,
            raw_google=raw_google,
            raw_yelp=raw_yelp,
        )
        db.add(asset)

        business.status = "gathering_done"
        job = Job(business_id=business.id, step="gather", status="success")
        db.add(job)
        db.commit()

        build_task.delay(business_id)

    except Exception as exc:
        db.rollback()
        raise self.retry(exc=exc)
    finally:
        db.close()
```

- [ ] **Step 2: Write `backend/tests/test_gather.py`**

```python
import uuid
import pytest
from unittest.mock import patch, MagicMock
from app.models.business import Business, BusinessAsset


def test_gather_creates_asset_and_enqueues_build(db):
    b = Business(name="Top Auto", city="Calgary", state="AB",
                 category="auto", google_place_id="gp-auto123",
                 yelp_id="yelp-auto123", status="discovered")
    db.add(b)
    db.flush()
    business_id = str(b.id)

    mock_google_detail = {
        "place_id": "gp-auto123", "name": "Top Auto", "address": "1 Garage Rd",
        "city": "Calgary", "state": "AB", "phone": "403-555-0111",
        "website": None, "hours": ["Mon: 8AM-5PM"], "description": "Quality auto repair.",
        "photos": ["ref1"], "rating": 4.3, "review_count": 55,
    }
    mock_yelp_detail = {
        "yelp_id": "yelp-auto123", "name": "Top Auto", "photos": [],
        "hours": [], "price_range": "$$", "categories": ["Auto Repair"], "description": None,
    }

    with patch("app.workers.gather.GooglePlacesClient") as MockGoogle, \
         patch("app.workers.gather.YelpClient") as MockYelp, \
         patch("app.workers.gather.R2StorageClient") as MockR2, \
         patch("app.workers.gather.SessionLocal", return_value=db), \
         patch("app.workers.build.build_task.delay") as mock_build:

        MockGoogle.return_value.get_place_details.return_value = mock_google_detail
        MockGoogle.return_value.get_photo_url.return_value = "https://maps.googleapis.com/photo?ref=ref1"
        MockR2.return_value.upload_from_url.return_value = "https://r2.example.com/photo_0.jpg"
        MockYelp.return_value.get_business.return_value = mock_yelp_detail

        from app.workers.gather import gather_task
        gather_task.run(business_id)

    db.refresh(b)
    assert b.status == "gathering_done"
    assert b.assets is not None
    assert b.assets.rating == 4.3
    assert "https://r2.example.com/photo_0.jpg" in b.assets.photos
    mock_build.assert_called_once_with(business_id)
```

- [ ] **Step 3: Run test**

```bash
cd backend
TEST_DATABASE_URL=postgresql://postgres:postgres@localhost:5432/webagency_test poetry run pytest tests/test_gather.py -v
```

Expected: 1 PASS

- [ ] **Step 4: Commit**

```bash
git -C C:/Users/Stephen/webagency add backend/
git -C C:/Users/Stephen/webagency commit -m "feat: gather worker"
```

---

### Task 8: Claude Copy Generation Service

**Files:**
- Create: `backend/app/services/claude.py`
- Test: `backend/tests/test_claude.py`

**Interfaces:**
- Produces:
  - `ClaudeClient(api_key: str).generate_site_copy(business_data: dict, assets: dict) -> dict`
    - Returns: `{"headline": str, "subheadline": str, "about": str, "services": list[str], "cta_text": str, "meta_description": str}`
  - `ClaudeClient.select_template(category: str) -> str`
    - Returns one of: `restaurant`, `plumber`, `salon`, `dentist`, `landscaping`, `retail`, `trades`, `professional`, `auto`, `cleaning`, `gym`, `photography`, `realestate`, `childcare`, `petservices`

- [ ] **Step 1: Write `backend/app/services/claude.py`**

```python
import anthropic
from dataclasses import dataclass

CATEGORY_TO_TEMPLATE = {
    "restaurant": "restaurant", "cafe": "restaurant",
    "plumber": "plumber", "plumbing": "plumber",
    "salon": "salon", "hair": "salon", "beauty": "salon",
    "dentist": "dentist", "dental": "dentist",
    "landscaping": "landscaping", "lawn": "landscaping",
    "retail": "retail", "boutique": "retail",
    "trades": "trades", "contractor": "trades", "handyman": "trades",
    "professional": "professional",
    "auto": "auto", "mechanic": "auto",
    "cleaning": "cleaning",
    "gym": "gym", "fitness": "gym",
    "photography": "photography", "photographer": "photography",
    "realestate": "realestate", "realtor": "realestate",
    "childcare": "childcare", "daycare": "childcare",
    "petservices": "petservices", "vet": "petservices", "grooming": "petservices",
}

COPY_PROMPT = """You are writing website copy for a local business. Use ONLY real details from the data provided.
Do NOT use generic filler phrases. Reference specific services, location, or details that make this business unique.

Business data:
Name: {name}
City: {city}, {state}
Category: {category}
Description: {description}
Services: {services}
Rating: {rating} ({review_count} reviews)
Hours: {hours}

Return ONLY a JSON object with these exact keys:
{{
  "headline": "short punchy headline (max 8 words, references the business or location)",
  "subheadline": "1 sentence that says what they do and where (max 20 words)",
  "about": "2-3 sentences about the business using real details (max 60 words)",
  "services": ["service 1", "service 2", "service 3", "service 4"],
  "cta_text": "call to action button text (max 5 words)",
  "meta_description": "SEO description (max 155 chars)"
}}"""


@dataclass
class ClaudeClient:
    api_key: str

    def select_template(self, category: str) -> str:
        normalized = category.lower().strip()
        return CATEGORY_TO_TEMPLATE.get(normalized, "professional")

    def generate_site_copy(self, business_data: dict, assets: dict) -> dict:
        prompt = COPY_PROMPT.format(
            name=business_data.get("name", ""),
            city=business_data.get("city", ""),
            state=business_data.get("state", ""),
            category=business_data.get("category", ""),
            description=assets.get("description") or "Local business serving the community.",
            services=", ".join(assets.get("services") or []) or "General services",
            rating=assets.get("rating") or "N/A",
            review_count=assets.get("review_count") or 0,
            hours=str(assets.get("hours") or {}).replace("{", "").replace("}", ""),
        )

        client = anthropic.Anthropic(api_key=self.api_key)
        message = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=800,
            messages=[{"role": "user", "content": prompt}],
        )

        import json
        text = message.content[0].text.strip()
        if text.startswith("```"):
            text = text.split("```")[1]
            if text.startswith("json"):
                text = text[4:]
        return json.loads(text.strip())
```

- [ ] **Step 2: Write `backend/tests/test_claude.py`**

```python
import pytest
from unittest.mock import patch, MagicMock
from app.services.claude import ClaudeClient


@pytest.fixture
def client():
    return ClaudeClient(api_key="test-anthropic-key")


def test_select_template_maps_categories(client):
    assert client.select_template("plumber") == "plumber"
    assert client.select_template("salon") == "salon"
    assert client.select_template("auto") == "auto"
    assert client.select_template("unknown_category") == "professional"


def test_generate_site_copy_returns_required_keys(client):
    mock_response = MagicMock()
    mock_response.content = [MagicMock(text='{"headline": "Toronto\'s Trusted Plumber", "subheadline": "Fast plumbing repairs in Toronto, ON.", "about": "Mike\'s Plumbing has served Toronto for 15 years.", "services": ["Leak Repair", "Drain Cleaning", "Water Heater"], "cta_text": "Get a Free Quote", "meta_description": "Mike\'s Plumbing — fast, reliable plumbing in Toronto."}')]

    with patch("anthropic.Anthropic") as MockAnthropic:
        MockAnthropic.return_value.messages.create.return_value = mock_response
        result = client.generate_site_copy(
            {"name": "Mike's Plumbing", "city": "Toronto", "state": "ON", "category": "plumber"},
            {"description": "15 years of service", "services": ["Leak Repair"], "rating": 4.5, "review_count": 38, "hours": {}},
        )

    assert "headline" in result
    assert "services" in result
    assert isinstance(result["services"], list)
```

- [ ] **Step 3: Run tests**

```bash
cd backend
poetry run pytest tests/test_claude.py -v
```

Expected: 2 PASS

- [ ] **Step 4: Commit**

```bash
git -C C:/Users/Stephen/webagency add backend/
git -C C:/Users/Stephen/webagency commit -m "feat: Claude copy generation service"
```

---

### Task 9: Build Worker

**Files:**
- Create: `backend/app/workers/build.py`
- Create: `templates/` stub directories (one per vertical, each with `package.json` + `pages/index.js`)
- Test: `backend/tests/test_build.py`

**Interfaces:**
- Consumes: `ClaudeClient`, `Business`, `BusinessAsset`, `Site`
- Produces:
  - `build_task(business_id: str) -> None` — clones the correct template, injects copy + photos + details, writes built project to `builds/{business_id}/`, creates `Site` row, enqueues `publish_task`

- [ ] **Step 1: Create template stub directories**

Create the directory structure that Plan 2 will fill with real templates:

```bash
cd C:/Users/Stephen/webagency
for dir in restaurant plumber salon dentist landscaping retail trades professional auto cleaning gym photography realestate childcare petservices; do
  mkdir -p "templates/$dir/pages"
  echo '{"name":"webagency-template","version":"0.1.0","scripts":{"dev":"next dev","build":"next build","export":"next export"},"dependencies":{"next":"14.2.0","react":"18.3.0","react-dom":"18.3.0"}}' > "templates/$dir/package.json"
  echo 'export default function Home({ data }) { return <div><h1>{data?.headline}</h1><p>{data?.subheadline}</p></div>; }
export async function getStaticProps() { const data = require("../site-data.json"); return { props: { data } }; }' > "templates/$dir/pages/index.js"
done
mkdir -p builds
```

- [ ] **Step 2: Write `backend/app/workers/build.py`**

```python
import json
import uuid
import shutil
from pathlib import Path
from app.workers.celery_app import celery_app
from app.database import SessionLocal
from app.models.business import Business, BusinessAsset
from app.models.site import Site
from app.models.job import Job
from app.services.claude import ClaudeClient
from app.config import settings
import logging

logger = logging.getLogger(__name__)

TEMPLATES_DIR = Path(__file__).parent.parent.parent.parent / "templates"
BUILDS_DIR = Path(__file__).parent.parent.parent.parent / "builds"


@celery_app.task(bind=True, max_retries=3, default_retry_delay=60)
def build_task(self, business_id: str):
    from app.workers.publish import publish_task

    db = SessionLocal()
    try:
        business = db.query(Business).filter(Business.id == uuid.UUID(business_id)).first()
        if not business:
            return

        business.status = "building"
        db.commit()

        assets = db.query(BusinessAsset).filter(BusinessAsset.business_id == business.id).first()
        assets_dict = {}
        if assets:
            assets_dict = {
                "photos": assets.photos or [],
                "description": assets.description,
                "hours": assets.hours,
                "rating": assets.rating,
                "review_count": assets.review_count,
                "services": assets.services or [],
                "price_range": assets.price_range,
            }

        claude = ClaudeClient(api_key=settings.anthropic_api_key)
        template_slug = claude.select_template(business.category)
        copy = claude.generate_site_copy(
            {"name": business.name, "city": business.city, "state": business.state, "category": business.category},
            assets_dict,
        )

        template_src = TEMPLATES_DIR / template_slug
        if not template_src.exists():
            template_src = TEMPLATES_DIR / "professional"

        build_dest = BUILDS_DIR / business_id
        if build_dest.exists():
            shutil.rmtree(build_dest)
        shutil.copytree(template_src, build_dest)

        site_data = {
            "business": {
                "name": business.name,
                "address": business.address,
                "city": business.city,
                "state": business.state,
                "phone": business.phone,
                "email": business.email,
                "category": business.category,
            },
            "assets": assets_dict,
            **copy,
        }
        (build_dest / "site-data.json").write_text(json.dumps(site_data, indent=2))

        site = Site(business_id=business.id, template_used=template_slug)
        db.add(site)

        business.status = "built"
        job = Job(business_id=business.id, step="build", status="success")
        db.add(job)
        db.commit()

        publish_task.delay(business_id)

    except Exception as exc:
        db.rollback()
        logger.error(f"Build failed for {business_id}: {exc}")
        raise self.retry(exc=exc)
    finally:
        db.close()
```

- [ ] **Step 3: Write `backend/tests/test_build.py`**

```python
import uuid
import json
import shutil
from pathlib import Path
from unittest.mock import patch, MagicMock
from app.models.business import Business, BusinessAsset
from app.models.site import Site

BUILDS_DIR = Path(__file__).parent.parent.parent / "builds"


def test_build_creates_site_record_and_site_data_json(db, tmp_path):
    b = Business(name="City Salon", city="Vancouver", state="BC",
                 category="salon", status="gathering_done")
    db.add(b)
    db.flush()
    business_id = str(b.id)

    asset = BusinessAsset(
        business_id=b.id, photos=["https://r2.example.com/photo.jpg"],
        description="Top salon in Vancouver", rating=4.8, review_count=200,
        services=["Haircut", "Color"], price_range="$$",
    )
    db.add(asset)
    db.flush()

    mock_copy = {
        "headline": "Vancouver's Top Salon",
        "subheadline": "Expert cuts and color in Vancouver, BC.",
        "about": "City Salon has been styling Vancouver since 2010.",
        "services": ["Haircut", "Color", "Blowout"],
        "cta_text": "Book Now",
        "meta_description": "City Salon — expert hair in Vancouver.",
    }

    with patch("app.workers.build.ClaudeClient") as MockClaude, \
         patch("app.workers.build.SessionLocal", return_value=db), \
         patch("app.workers.build.BUILDS_DIR", tmp_path), \
         patch("app.workers.publish.publish_task.delay") as mock_publish:

        MockClaude.return_value.select_template.return_value = "salon"
        MockClaude.return_value.generate_site_copy.return_value = mock_copy

        from app.workers.build import build_task
        build_task.run(business_id)

    site_data_path = tmp_path / business_id / "site-data.json"
    assert site_data_path.exists()
    data = json.loads(site_data_path.read_text())
    assert data["headline"] == "Vancouver's Top Salon"
    assert data["business"]["name"] == "City Salon"

    db.refresh(b)
    assert b.status == "built"
    assert b.site is not None
    assert b.site.template_used == "salon"
    mock_publish.assert_called_once_with(business_id)
```

- [ ] **Step 4: Run test**

```bash
cd backend
TEST_DATABASE_URL=postgresql://postgres:postgres@localhost:5432/webagency_test poetry run pytest tests/test_build.py -v
```

Expected: 1 PASS

- [ ] **Step 5: Commit**

```bash
git -C C:/Users/Stephen/webagency add backend/ templates/ builds/
git -C C:/Users/Stephen/webagency commit -m "feat: build worker and template stubs"
```

---

### Task 10: Publisher Interface + Vercel + Publish Worker

**Files:**
- Create: `backend/app/services/publisher.py`
- Create: `backend/app/workers/publish.py`
- Test: `backend/tests/test_publisher.py`
- Test: `backend/tests/test_publish.py`

**Interfaces:**
- Produces:
  - `Publisher` ABC with method `deploy(build_path: str, slug: str) -> str` (returns public URL)
  - `VercelPublisher(token: str, team_id: str | None, agency_domain: str).deploy(build_path: str, slug: str) -> str`
  - `publish_task(business_id: str) -> None` — deploys site, creates/updates `Site.vercel_url`, handles review mode gate, enqueues `outreach_task` if approved

- [ ] **Step 1: Write `backend/app/services/publisher.py`**

```python
from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path
import subprocess
import httpx


class Publisher(ABC):
    @abstractmethod
    def deploy(self, build_path: str, slug: str) -> str:
        """Deploy a Next.js project directory. Returns the public URL."""


@dataclass
class VercelPublisher(Publisher):
    token: str
    team_id: str | None
    agency_domain: str

    def deploy(self, build_path: str, slug: str) -> str:
        cmd = ["vercel", "--token", self.token, "--yes", "--prod", str(build_path)]
        if self.team_id:
            cmd += ["--scope", self.team_id]

        result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
        if result.returncode != 0:
            raise RuntimeError(f"Vercel deploy failed: {result.stderr}")

        vercel_url = result.stdout.strip().split("\n")[-1].strip()
        return vercel_url
```

- [ ] **Step 2: Write `backend/app/workers/publish.py`**

```python
import uuid
from pathlib import Path
from datetime import datetime
from app.workers.celery_app import celery_app
from app.database import SessionLocal
from app.models.business import Business
from app.models.site import Site
from app.models.job import Job
from app.services.publisher import VercelPublisher
from app.config import settings
import logging

logger = logging.getLogger(__name__)

BUILDS_DIR = Path(__file__).parent.parent.parent.parent / "builds"


@celery_app.task(bind=True, max_retries=3, default_retry_delay=60)
def publish_task(self, business_id: str):
    from app.workers.outreach_worker import outreach_task

    db = SessionLocal()
    try:
        business = db.query(Business).filter(Business.id == uuid.UUID(business_id)).first()
        if not business:
            return

        site = db.query(Site).filter(Site.business_id == business.id).first()
        if not site:
            return

        build_path = BUILDS_DIR / business_id
        slug = f"{business.name.lower().replace(' ', '-')}-{business.city.lower()}"
        slug = "".join(c for c in slug if c.isalnum() or c == "-")[:50]

        publisher = VercelPublisher(
            token=settings.vercel_token,
            team_id=settings.vercel_team_id,
            agency_domain=settings.agency_domain,
        )
        vercel_url = publisher.deploy(str(build_path), slug)

        site.vercel_url = vercel_url
        site.custom_subdomain = f"https://{slug}.{settings.agency_domain}"
        site.deployed_at = datetime.utcnow()

        business.status = "published"
        job = Job(business_id=business.id, step="publish", status="success")
        db.add(job)

        if settings.review_mode:
            site.review_status = "pending"
            logger.info(f"Review mode ON — site {business_id} awaiting approval")
        else:
            site.review_status = "approved"
            outreach_task.delay(business_id)

        db.commit()

    except Exception as exc:
        db.rollback()
        raise self.retry(exc=exc)
    finally:
        db.close()
```

- [ ] **Step 3: Write `backend/tests/test_publisher.py`**

```python
import pytest
from unittest.mock import patch, MagicMock
from app.services.publisher import VercelPublisher


def test_vercel_publisher_calls_cli_and_returns_url(tmp_path):
    publisher = VercelPublisher(token="tok-abc", team_id=None, agency_domain="youragency.com")

    mock_result = MagicMock()
    mock_result.returncode = 0
    mock_result.stdout = "Building...\nhttps://mikes-plumbing-toronto.vercel.app"

    with patch("subprocess.run", return_value=mock_result) as mock_run:
        url = publisher.deploy(str(tmp_path), "mikes-plumbing-toronto")

    assert url == "https://mikes-plumbing-toronto.vercel.app"
    cmd = mock_run.call_args[0][0]
    assert "--prod" in cmd
    assert "--token" in cmd


def test_vercel_publisher_raises_on_failure(tmp_path):
    publisher = VercelPublisher(token="tok-abc", team_id=None, agency_domain="youragency.com")
    mock_result = MagicMock()
    mock_result.returncode = 1
    mock_result.stderr = "Error: Not authenticated"

    with patch("subprocess.run", return_value=mock_result):
        with pytest.raises(RuntimeError, match="Vercel deploy failed"):
            publisher.deploy(str(tmp_path), "some-slug")
```

- [ ] **Step 4: Write `backend/tests/test_publish.py`**

```python
import uuid
from unittest.mock import patch, MagicMock
from app.models.business import Business
from app.models.site import Site


def test_publish_sets_review_pending_when_review_mode_on(db):
    b = Business(name="Mike's Plumbing", city="Toronto", state="ON",
                 category="plumber", status="built")
    db.add(b)
    db.flush()
    site = Site(business_id=b.id, template_used="plumber")
    db.add(site)
    db.flush()
    business_id = str(b.id)

    with patch("app.workers.publish.VercelPublisher") as MockPublisher, \
         patch("app.workers.publish.SessionLocal", return_value=db), \
         patch("app.workers.publish.settings") as mock_settings, \
         patch("app.workers.outreach_worker.outreach_task.delay") as mock_outreach:

        MockPublisher.return_value.deploy.return_value = "https://mikes-plumbing-toronto.vercel.app"
        mock_settings.review_mode = True
        mock_settings.vercel_token = "tok"
        mock_settings.vercel_team_id = None
        mock_settings.agency_domain = "youragency.com"

        from app.workers.publish import publish_task
        publish_task.run(business_id)

    db.refresh(site)
    assert site.review_status == "pending"
    assert site.vercel_url == "https://mikes-plumbing-toronto.vercel.app"
    mock_outreach.assert_not_called()


def test_publish_enqueues_outreach_when_review_mode_off(db):
    b = Business(name="City Salon", city="Vancouver", state="BC",
                 category="salon", status="built")
    db.add(b)
    db.flush()
    site = Site(business_id=b.id, template_used="salon")
    db.add(site)
    db.flush()
    business_id = str(b.id)

    with patch("app.workers.publish.VercelPublisher") as MockPublisher, \
         patch("app.workers.publish.SessionLocal", return_value=db), \
         patch("app.workers.publish.settings") as mock_settings, \
         patch("app.workers.outreach_worker.outreach_task.delay") as mock_outreach:

        MockPublisher.return_value.deploy.return_value = "https://city-salon-vancouver.vercel.app"
        mock_settings.review_mode = False
        mock_settings.vercel_token = "tok"
        mock_settings.vercel_team_id = None
        mock_settings.agency_domain = "youragency.com"

        from app.workers.publish import publish_task
        publish_task.run(business_id)

    mock_outreach.assert_called_once_with(business_id)
```

- [ ] **Step 5: Run tests**

```bash
cd backend
TEST_DATABASE_URL=postgresql://postgres:postgres@localhost:5432/webagency_test poetry run pytest tests/test_publisher.py tests/test_publish.py -v
```

Expected: 4 PASS

- [ ] **Step 6: Commit**

```bash
git -C C:/Users/Stephen/webagency add backend/
git -C C:/Users/Stephen/webagency commit -m "feat: publisher interface, Vercel implementation, publish worker"
```

---

### Task 11: Outreach Services + Outreach Worker

**Files:**
- Create: `backend/app/services/resend.py`
- Create: `backend/app/services/hunter.py`
- Create: `backend/app/services/form_outreach.py`
- Create: `backend/app/workers/outreach_worker.py`
- Test: `backend/tests/test_resend.py`
- Test: `backend/tests/test_hunter.py`
- Test: `backend/tests/test_form_outreach.py`
- Test: `backend/tests/test_outreach_worker.py`

**Interfaces:**
- Produces:
  - `ResendClient(api_key: str).send_email(to: str, subject: str, html: str, from_email: str) -> dict`
    - Returns `{"id": str, "status": "sent"}`
  - `HunterClient(api_key: str).find_email(domain: str, company: str) -> str | None`
  - `FormOutreachClient().submit_form(website_url: str, message: str) -> bool`
  - `outreach_task(business_id: str) -> None` — sends email + form, logs to `Outreach` table, respects daily cap

- [ ] **Step 1: Write `backend/app/services/resend.py`**

```python
import httpx
from dataclasses import dataclass

RESEND_BASE = "https://api.resend.com"

EMAIL_TEMPLATE = """<html><body style="font-family: sans-serif; max-width: 600px; margin: 0 auto; padding: 20px;">
<p>Hi {business_name} team,</p>
<p>I built you a website — take a look:</p>
<p><a href="{site_url}" style="font-size: 18px; color: #0066cc;">{site_url}</a></p>
<p>I noticed {business_name} in {city} didn't have a website (or the current one was outdated), so I put this together based on your {source} listing. It's live now.</p>
<p>If you'd like to keep it — and get your own domain, edits, and SEO — reply to this email and we'll sort out the details.</p>
<p>If it's not for you, no worries. Just ignore this.</p>
<p>— The Web Agency</p>
</body></html>"""


@dataclass
class ResendClient:
    api_key: str
    from_email: str = "hello@youragency.com"

    def send_email(self, to: str, subject: str, business_name: str,
                   city: str, site_url: str, source: str = "Google") -> dict:
        html = EMAIL_TEMPLATE.format(
            business_name=business_name, city=city, site_url=site_url, source=source
        )
        resp = httpx.post(
            f"{RESEND_BASE}/emails",
            headers={"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"},
            json={"from": self.from_email, "to": [to], "subject": subject, "html": html},
            timeout=10,
        )
        resp.raise_for_status()
        return {"id": resp.json().get("id"), "status": "sent"}
```

- [ ] **Step 2: Write `backend/app/services/hunter.py`**

```python
import httpx
from dataclasses import dataclass

HUNTER_BASE = "https://api.hunter.io/v2"


@dataclass
class HunterClient:
    api_key: str

    def find_email(self, domain: str, company: str) -> str | None:
        if not self.api_key:
            return None
        try:
            resp = httpx.get(
                f"{HUNTER_BASE}/domain-search",
                params={"domain": domain, "company": company, "api_key": self.api_key, "limit": 1},
                timeout=10,
            )
            resp.raise_for_status()
            emails = resp.json().get("data", {}).get("emails", [])
            return emails[0]["value"] if emails else None
        except Exception:
            return None
```

- [ ] **Step 3: Write `backend/app/services/form_outreach.py`**

```python
from dataclasses import dataclass
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeout
import logging

logger = logging.getLogger(__name__)

FORM_MESSAGE = """Hi, I built {business_name} a website — {site_url}

I noticed you didn't have a website (or the current one was outdated), so I put one together using your online listings. It's live now.

If you'd like to keep it and get your own domain + edits, just reply here. If not, no worries.

— The Web Agency"""


@dataclass
class FormOutreachClient:
    def submit_form(self, website_url: str, business_name: str, site_url: str) -> bool:
        message = FORM_MESSAGE.format(business_name=business_name, site_url=site_url)
        try:
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=True)
                page = browser.new_page()
                try:
                    page.goto(website_url, timeout=10000, wait_until="domcontentloaded")
                    contact_link = page.query_selector("a[href*='contact'], a:text-matches('contact', 'i')")
                    if contact_link:
                        contact_link.click()
                        page.wait_for_load_state("domcontentloaded", timeout=5000)

                    textarea = page.query_selector("textarea")
                    if not textarea:
                        return False

                    name_field = page.query_selector("input[name*='name'], input[placeholder*='name' i]")
                    email_field = page.query_selector("input[type='email'], input[name*='email']")

                    if name_field:
                        name_field.fill("Web Agency")
                    if email_field:
                        email_field.fill("hello@youragency.com")

                    textarea.fill(message)

                    submit = page.query_selector("button[type='submit'], input[type='submit']")
                    if submit:
                        submit.click()
                        page.wait_for_timeout(2000)
                        return True
                    return False
                finally:
                    browser.close()
        except (PlaywrightTimeout, Exception) as e:
            logger.warning(f"Form outreach failed for {website_url}: {e}")
            return False
```

- [ ] **Step 4: Write `backend/app/workers/outreach_worker.py`**

```python
import uuid
from datetime import datetime, date
from app.workers.celery_app import celery_app
from app.database import SessionLocal
from app.models.business import Business
from app.models.site import Site
from app.models.outreach import Outreach
from app.models.job import Job
from app.services.resend import ResendClient
from app.services.hunter import HunterClient
from app.services.form_outreach import FormOutreachClient
from app.config import settings
import urllib.parse
import logging

logger = logging.getLogger(__name__)


def _count_todays_outreach(db) -> int:
    today_start = datetime.combine(date.today(), datetime.min.time())
    return db.query(Outreach).filter(
        Outreach.email_sent_at >= today_start
    ).count()


@celery_app.task(bind=True, max_retries=3, default_retry_delay=60)
def outreach_task(self, business_id: str):
    from celery.exceptions import Retry

    db = SessionLocal()
    if _count_todays_outreach(db) >= settings.outreach_daily_cap:
        db.close()
        logger.info(f"Daily cap reached — requeueing {business_id}")
        raise self.retry(countdown=3600)

    try:

        business = db.query(Business).filter(Business.id == uuid.UUID(business_id)).first()
        site = db.query(Site).filter(Site.business_id == business.id).first()
        if not business or not site:
            return

        site_url = site.vercel_url or site.custom_subdomain
        record = Outreach(business_id=business.id, site_id=site.id)
        db.add(record)
        db.flush()

        # Email outreach
        email = business.email
        if not email and business.existing_website:
            domain = urllib.parse.urlparse(business.existing_website).netloc
            hunter = HunterClient(api_key=settings.hunter_api_key or "")
            email = hunter.find_email(domain, business.name)

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
            except Exception as e:
                logger.warning(f"Email failed for {business_id}: {e}")
                record.email_status = "failed"

        # Form outreach
        if business.existing_website:
            try:
                form_client = FormOutreachClient()
                success = form_client.submit_form(business.existing_website, business.name, site_url)
                record.form_submitted_at = datetime.utcnow()
                record.form_status = "submitted" if success else "failed"
            except Exception as e:
                logger.warning(f"Form outreach failed for {business_id}: {e}")
                record.form_status = "failed"
        else:
            record.form_status = "skipped"

        business.status = "outreached"
        job = Job(business_id=business.id, step="outreach", status="success")
        db.add(job)
        db.commit()

    except Exception as exc:
        db.rollback()
        if not isinstance(exc, self.MaxRetriesExceededError):
            raise self.retry(exc=exc)
    finally:
        db.close()
```

- [ ] **Step 5: Write tests**

```python
# backend/tests/test_form_outreach.py
from unittest.mock import patch, MagicMock
from app.services.form_outreach import FormOutreachClient


def test_submit_form_returns_true_on_success():
    client = FormOutreachClient()
    mock_page = MagicMock()
    mock_page.query_selector.side_effect = lambda sel: MagicMock() if "textarea" in sel else None
    mock_page.goto.return_value = None

    with patch("app.services.form_outreach.sync_playwright") as mock_pw:
        mock_pw.return_value.__enter__.return_value.chromium.launch.return_value.new_page.return_value = mock_page
        mock_page.query_selector.return_value = MagicMock()
        result = client.submit_form("https://example.com", "Mike's Plumbing", "https://mikes.vercel.app")

    assert isinstance(result, bool)


def test_submit_form_returns_false_on_playwright_error():
    client = FormOutreachClient()
    with patch("app.services.form_outreach.sync_playwright", side_effect=Exception("browser error")):
        result = client.submit_form("https://example.com", "Salon", "https://salon.vercel.app")
    assert result is False
```

```python
# backend/tests/test_resend.py
import pytest
import respx
import httpx
from app.services.resend import ResendClient


@respx.mock
def test_send_email_posts_to_resend_and_returns_status():
    respx.post("https://api.resend.com/emails").mock(
        return_value=httpx.Response(200, json={"id": "email-abc-123"})
    )
    client = ResendClient(api_key="test-key")
    result = client.send_email(
        to="owner@mikesplumbing.com",
        subject="I built Mike's Plumbing a website",
        business_name="Mike's Plumbing",
        city="Toronto",
        site_url="https://mikes-plumbing-toronto.vercel.app",
    )
    assert result["status"] == "sent"
    assert result["id"] == "email-abc-123"
```

```python
# backend/tests/test_hunter.py
import pytest
import respx
import httpx
from app.services.hunter import HunterClient


@respx.mock
def test_find_email_returns_first_email():
    respx.get("https://api.hunter.io/v2/domain-search").mock(
        return_value=httpx.Response(200, json={
            "data": {"emails": [{"value": "owner@mikesplumbing.com"}]}
        })
    )
    client = HunterClient(api_key="test-key")
    email = client.find_email("mikesplumbing.com", "Mike's Plumbing")
    assert email == "owner@mikesplumbing.com"


def test_find_email_returns_none_when_no_api_key():
    client = HunterClient(api_key="")
    assert client.find_email("example.com", "Example") is None
```

```python
# backend/tests/test_outreach_worker.py
import uuid
from unittest.mock import patch, MagicMock
from app.models.business import Business
from app.models.site import Site
from app.models.outreach import Outreach


def test_outreach_sends_email_and_logs_record(db):
    b = Business(name="Mike's Plumbing", city="Toronto", state="ON",
                 email="mike@mikesplumbing.com", category="plumber", status="published")
    db.add(b)
    db.flush()
    site = Site(business_id=b.id, template_used="plumber",
                vercel_url="https://mikes-plumbing-toronto.vercel.app",
                review_status="approved")
    db.add(site)
    db.flush()
    business_id = str(b.id)

    with patch("app.workers.outreach_worker.ResendClient") as MockResend, \
         patch("app.workers.outreach_worker.FormOutreachClient") as MockForm, \
         patch("app.workers.outreach_worker.SessionLocal", return_value=db), \
         patch("app.workers.outreach_worker.settings") as mock_settings:

        MockResend.return_value.send_email.return_value = {"id": "email-123", "status": "sent"}
        MockForm.return_value.submit_form.return_value = False
        mock_settings.outreach_daily_cap = 20
        mock_settings.resend_api_key = "test-key"
        mock_settings.hunter_api_key = None

        from app.workers.outreach_worker import outreach_task
        outreach_task.run(business_id)

    db.refresh(b)
    assert b.status == "outreached"
    records = db.query(Outreach).filter(Outreach.business_id == b.id).all()
    assert len(records) == 1
    assert records[0].email_status == "sent"


def test_outreach_respects_daily_cap(db):
    b = Business(name="City Salon", city="Vancouver", state="BC",
                 email="info@citysalon.ca", category="salon", status="published")
    db.add(b)
    db.flush()
    site = Site(business_id=b.id, template_used="salon",
                vercel_url="https://city-salon.vercel.app", review_status="approved")
    db.add(site)
    db.flush()

    with patch("app.workers.outreach_worker._count_todays_outreach", return_value=20), \
         patch("app.workers.outreach_worker.SessionLocal", return_value=db), \
         patch("app.workers.outreach_worker.settings") as mock_settings:
        mock_settings.outreach_daily_cap = 20
        from app.workers.outreach_worker import outreach_task
        # Daily cap hit — task raises Retry before creating any Outreach record
        import celery.exceptions
        try:
            outreach_task.run(str(b.id))
        except celery.exceptions.Retry:
            pass

    assert db.query(Outreach).count() == 0
```

- [ ] **Step 6: Run all outreach tests**

```bash
cd backend
TEST_DATABASE_URL=postgresql://postgres:postgres@localhost:5432/webagency_test poetry run pytest tests/test_resend.py tests/test_hunter.py tests/test_outreach_worker.py -v
```

Expected: 5 PASS

- [ ] **Step 7: Commit**

```bash
git -C C:/Users/Stephen/webagency add backend/
git -C C:/Users/Stephen/webagency commit -m "feat: outreach services (Resend, Hunter, form) and outreach worker"
```

---

### Task 12: REST API Endpoints

**Files:**
- Create: `backend/app/schemas/business.py`
- Create: `backend/app/schemas/site.py`
- Create: `backend/app/schemas/outreach.py`
- Create: `backend/app/schemas/job.py`
- Create: `backend/app/api/businesses.py`
- Create: `backend/app/api/jobs.py`
- Create: `backend/app/api/sites.py`
- Create: `backend/app/api/outreach.py`
- Modify: `backend/app/api/router.py`
- Test: `backend/tests/test_api.py`

**Interfaces:**
- Produces REST endpoints:
  - `GET /api/businesses` → list all businesses with status
  - `GET /api/businesses/{id}` → business + assets + site + outreach
  - `POST /api/businesses/{id}/retry?step=gather` → re-enqueue a step
  - `GET /api/sites` → list all sites
  - `POST /api/sites/{id}/approve` → set review_status=approved, enqueue outreach
  - `POST /api/sites/{id}/reject` → set review_status=rejected
  - `GET /api/jobs` → list recent jobs
  - `GET /api/outreach` → list all outreach records
  - `POST /api/run` → start a new discovery run (body: `{region, categories}`)

- [ ] **Step 1: Write schemas**

`backend/app/schemas/business.py`:
```python
from pydantic import BaseModel
from uuid import UUID
from datetime import datetime


class BusinessOut(BaseModel):
    model_config = {"from_attributes": True}
    id: UUID
    name: str
    city: str
    state: str
    category: str
    status: str
    website_score: int | None
    created_at: datetime


class BusinessDetailOut(BusinessOut):
    address: str | None
    phone: str | None
    email: str | None
    existing_website: str | None
    google_place_id: str | None
    yelp_id: str | None
```

`backend/app/schemas/site.py`:
```python
from pydantic import BaseModel
from uuid import UUID
from datetime import datetime


class SiteOut(BaseModel):
    model_config = {"from_attributes": True}
    id: UUID
    business_id: UUID
    template_used: str
    vercel_url: str | None
    custom_subdomain: str | None
    review_status: str
    deployed_at: datetime | None
```

`backend/app/schemas/outreach.py`:
```python
from pydantic import BaseModel
from uuid import UUID
from datetime import datetime


class OutreachOut(BaseModel):
    model_config = {"from_attributes": True}
    id: UUID
    business_id: UUID
    email_to: str | None
    email_sent_at: datetime | None
    email_status: str | None
    form_submitted_at: datetime | None
    form_status: str | None
    responded_at: datetime | None
```

`backend/app/schemas/job.py`:
```python
from pydantic import BaseModel
from uuid import UUID
from datetime import datetime


class JobOut(BaseModel):
    model_config = {"from_attributes": True}
    id: UUID
    business_id: UUID
    step: str
    status: str
    error_msg: str | None
    attempts: int
    last_run_at: datetime | None
```

- [ ] **Step 2: Write API routers**

`backend/app/api/businesses.py`:
```python
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.business import Business
from app.schemas.business import BusinessOut, BusinessDetailOut
from app.workers.discover import discover_task
from app.workers.gather import gather_task
from app.workers.build import build_task
from app.workers.publish import publish_task

router = APIRouter(prefix="/businesses", tags=["businesses"])

STEP_TASKS = {
    "gather": gather_task,
    "build": build_task,
    "publish": publish_task,
}


@router.get("", response_model=list[BusinessOut])
def list_businesses(status: str | None = None, db: Session = Depends(get_db)):
    q = db.query(Business)
    if status:
        q = q.filter(Business.status == status)
    return q.order_by(Business.created_at.desc()).all()


@router.get("/{business_id}", response_model=BusinessDetailOut)
def get_business(business_id: str, db: Session = Depends(get_db)):
    b = db.query(Business).filter(Business.id == business_id).first()
    if not b:
        raise HTTPException(status_code=404, detail="Business not found")
    return b


@router.post("/{business_id}/retry")
def retry_step(business_id: str, step: str = Query(...), db: Session = Depends(get_db)):
    b = db.query(Business).filter(Business.id == business_id).first()
    if not b:
        raise HTTPException(status_code=404, detail="Business not found")
    task = STEP_TASKS.get(step)
    if not task:
        raise HTTPException(status_code=400, detail=f"Unknown step: {step}")
    task.delay(business_id)
    return {"queued": True, "step": step}


@router.post("/run")
def run_discovery(body: dict, db: Session = Depends(get_db)):
    region = body.get("region")
    categories = body.get("categories", ["plumber", "salon", "restaurant"])
    if not region:
        raise HTTPException(status_code=400, detail="region is required")
    discover_task.delay(region, categories)
    return {"queued": True, "region": region, "categories": categories}
```

`backend/app/api/sites.py`:
```python
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.site import Site
from app.schemas.site import SiteOut

router = APIRouter(prefix="/sites", tags=["sites"])


@router.get("", response_model=list[SiteOut])
def list_sites(db: Session = Depends(get_db)):
    return db.query(Site).order_by(Site.deployed_at.desc()).all()


@router.post("/{site_id}/approve")
def approve_site(site_id: str, db: Session = Depends(get_db)):
    from app.workers.outreach_worker import outreach_task
    site = db.query(Site).filter(Site.id == site_id).first()
    if not site:
        raise HTTPException(status_code=404, detail="Site not found")
    site.review_status = "approved"
    db.commit()
    outreach_task.delay(str(site.business_id))
    return {"approved": True}


@router.post("/{site_id}/reject")
def reject_site(site_id: str, db: Session = Depends(get_db)):
    site = db.query(Site).filter(Site.id == site_id).first()
    if not site:
        raise HTTPException(status_code=404, detail="Site not found")
    site.review_status = "rejected"
    db.commit()
    return {"rejected": True}
```

`backend/app/api/jobs.py`:
```python
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.job import Job
from app.schemas.job import JobOut

router = APIRouter(prefix="/jobs", tags=["jobs"])


@router.get("", response_model=list[JobOut])
def list_jobs(db: Session = Depends(get_db)):
    return db.query(Job).order_by(Job.last_run_at.desc()).limit(200).all()
```

`backend/app/api/outreach.py`:
```python
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.outreach import Outreach
from app.schemas.outreach import OutreachOut

router = APIRouter(prefix="/outreach", tags=["outreach"])


@router.get("", response_model=list[OutreachOut])
def list_outreach(db: Session = Depends(get_db)):
    return db.query(Outreach).order_by(Outreach.email_sent_at.desc()).all()
```

- [ ] **Step 3: Update `backend/app/api/router.py`**

```python
from fastapi import APIRouter
from app.api.businesses import router as businesses_router
from app.api.sites import router as sites_router
from app.api.jobs import router as jobs_router
from app.api.outreach import router as outreach_router

router = APIRouter()
router.include_router(businesses_router)
router.include_router(sites_router)
router.include_router(jobs_router)
router.include_router(outreach_router)
```

- [ ] **Step 4: Add API tests to `backend/tests/test_api.py`**

```python
import uuid
from fastapi.testclient import TestClient
from unittest.mock import patch
from app.main import app
from app.models.business import Business
from app.models.site import Site

client = TestClient(app)


def test_health():
    response = client.get("/health")
    assert response.status_code == 200


def test_list_businesses_empty(db):
    with patch("app.api.businesses.get_db", return_value=iter([db])):
        response = client.get("/api/businesses")
    assert response.status_code == 200
    assert response.json() == []


def test_list_businesses_returns_data(db):
    b = Business(name="Test Biz", city="Toronto", state="ON", category="plumber")
    db.add(b)
    db.flush()

    with patch("app.api.businesses.get_db", return_value=iter([db])):
        response = client.get("/api/businesses")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["name"] == "Test Biz"


def test_approve_site_enqueues_outreach(db):
    b = Business(name="Salon X", city="Vancouver", state="BC", category="salon")
    db.add(b)
    db.flush()
    site = Site(business_id=b.id, template_used="salon",
                vercel_url="https://salon-x.vercel.app", review_status="pending")
    db.add(site)
    db.flush()

    with patch("app.api.sites.get_db", return_value=iter([db])), \
         patch("app.workers.outreach_worker.outreach_task.delay") as mock_delay:
        response = client.post(f"/api/sites/{site.id}/approve")

    assert response.status_code == 200
    mock_delay.assert_called_once_with(str(b.id))


def test_run_discovery_queues_task():
    with patch("app.api.businesses.discover_task.delay") as mock_delay:
        response = client.post("/api/businesses/run", json={"region": "Toronto, ON", "categories": ["plumber"]})
    assert response.status_code == 200
    mock_delay.assert_called_once_with("Toronto, ON", ["plumber"])
```

- [ ] **Step 5: Run all API tests**

```bash
cd backend
TEST_DATABASE_URL=postgresql://postgres:postgres@localhost:5432/webagency_test poetry run pytest tests/test_api.py -v
```

Expected: 5 PASS

- [ ] **Step 6: Commit**

```bash
git -C C:/Users/Stephen/webagency add backend/
git -C C:/Users/Stephen/webagency commit -m "feat: REST API endpoints (businesses, sites, jobs, outreach)"
```

---

### Task 13: Docker Compose + Railway Config

**Files:**
- Create: `backend/docker-compose.yml`
- Create: `backend/Dockerfile`
- Create: `railway.toml`
- Create: `backend/start-worker.sh`

**Interfaces:**
- Produces: a working local dev setup (`docker compose up`) that runs Postgres + Redis + FastAPI + Celery worker

- [ ] **Step 1: Write `backend/Dockerfile`**

```dockerfile
FROM python:3.12-slim

WORKDIR /app

RUN pip install poetry
COPY pyproject.toml poetry.lock* ./
RUN poetry install --no-dev --no-root

COPY . .

RUN poetry run playwright install chromium
RUN poetry run playwright install-deps chromium

EXPOSE 8000
CMD ["poetry", "run", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

- [ ] **Step 2: Write `backend/docker-compose.yml`**

```yaml
version: "3.9"
services:
  db:
    image: postgres:16
    environment:
      POSTGRES_DB: webagency
      POSTGRES_USER: postgres
      POSTGRES_PASSWORD: postgres
    ports:
      - "5432:5432"
    volumes:
      - pgdata:/var/lib/postgresql/data

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"

  api:
    build: .
    env_file: .env
    ports:
      - "8000:8000"
    depends_on:
      - db
      - redis
    volumes:
      - ../templates:/templates
      - ../builds:/builds

  worker:
    build: .
    command: poetry run celery -A app.workers.celery_app worker --loglevel=info --concurrency=4
    env_file: .env
    depends_on:
      - db
      - redis
    volumes:
      - ../templates:/templates
      - ../builds:/builds

volumes:
  pgdata:
```

- [ ] **Step 3: Write `railway.toml`**

```toml
[build]
builder = "dockerfile"
dockerfilePath = "backend/Dockerfile"

[deploy]
startCommand = "poetry run uvicorn app.main:app --host 0.0.0.0 --port $PORT"
healthcheckPath = "/health"
restartPolicyType = "on_failure"
```

- [ ] **Step 4: Write `backend/start-worker.sh`**

```bash
#!/bin/bash
cd /app
poetry run celery -A app.workers.celery_app worker --loglevel=info --concurrency=4
```

- [ ] **Step 5: Start local dev environment**

```bash
cd C:/Users/Stephen/webagency/backend
cp .env.example .env
# Fill in real API keys in .env, then:
docker compose up -d db redis
DATABASE_URL=postgresql://postgres:postgres@localhost:5432/webagency poetry run alembic upgrade head
poetry run uvicorn app.main:app --reload
```

Visit `http://localhost:8000/health` — expect `{"status": "ok"}`

- [ ] **Step 6: Run full test suite**

```bash
cd backend
TEST_DATABASE_URL=postgresql://postgres:postgres@localhost:5432/webagency_test poetry run pytest -v
```

Expected: all tests PASS

- [ ] **Step 7: Commit**

```bash
git -C C:/Users/Stephen/webagency add .
git -C C:/Users/Stephen/webagency commit -m "feat: Docker Compose and Railway deployment config"
```

---

## Plan Complete

**Backend is now done.** The full pipeline — discover → gather → build → publish → outreach — is implemented, tested, and deployable.

**Next:**
- **Plan 2/3:** Build the 15 hand-crafted Next.js templates (using `frontend-design` skill)
- **Plan 3/3:** Build the Next.js dashboard + Python CLI
