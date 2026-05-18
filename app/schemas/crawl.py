from datetime import datetime

from pydantic import BaseModel, ConfigDict


class CrawlRunRequest(BaseModel):
    keyword: str = "脚手架"
    source_type: str = "mock"


class CrawlTaskOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    source_id: int | None = None
    keyword: str
    status: str
    started_at: datetime | None = None
    finished_at: datetime | None = None
    total_found: int
    total_saved: int
    error_message: str | None = None


class CrawlRunResponse(BaseModel):
    task: CrawlTaskOut
