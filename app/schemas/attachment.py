from datetime import datetime

from pydantic import BaseModel, ConfigDict


class BidAttachmentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    raw_document_id: int | None = None
    source_url: str
    file_url: str
    file_name: str
    file_type: str
    file_size: int | None = None
    local_path: str | None = None
    extracted_text: str | None = None
    parse_status: str
    error_message: str | None = None
    created_at: datetime
    updated_at: datetime


class ParsePendingRequest(BaseModel):
    limit: int = 20
