from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

router = APIRouter(prefix="/pipeline", tags=["pipeline"])


class RunBody(BaseModel):
    region: str
    categories: list[str]


@router.post("/run")
def run_pipeline(body: RunBody):
    """Enqueue a discovery run for the given region and categories."""
    from app.workers.discover import discover_task

    if not body.region:
        raise HTTPException(status_code=400, detail="region is required")
    discover_task.delay(body.region, body.categories)
    return {"queued": True, "region": body.region, "categories": body.categories}
