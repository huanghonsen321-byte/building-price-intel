from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.schemas.quote import ScaffoldQuoteRequest, ScaffoldQuoteResponse
from app.services.quote_service import calculate_scaffold_quote

router = APIRouter(prefix="/api/quote", tags=["quote"])


@router.post("/scaffold/calculate", response_model=ScaffoldQuoteResponse)
def calculate_quote(payload: ScaffoldQuoteRequest, db: Session = Depends(get_db)):
    return calculate_scaffold_quote(db, payload)
