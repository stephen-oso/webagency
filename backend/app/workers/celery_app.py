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
