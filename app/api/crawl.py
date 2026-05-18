from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.schemas.crawl import CrawlRunRequest, CrawlRunResponse, CrawlTaskOut
from app.services.crawl_service import list_crawl_tasks, run_mock_crawl, run_public_crawl

router = APIRouter(prefix="/api/crawl", tags=["crawl"])


@router.post("/run", response_model=CrawlRunResponse)
def run_crawl(payload: CrawlRunRequest, db: Session = Depends(get_db)):
    task = run_public_crawl(db, payload.keyword) if payload.source_type == "public" else run_mock_crawl(db, payload.keyword)
    return {"task": task}


@router.get("/tasks", response_model=list[CrawlTaskOut])
def get_crawl_tasks(db: Session = Depends(get_db)):
    return list_crawl_tasks(db)
