from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.db.session import get_db
from app.nlp.service import ArticleNotFoundError, NLPService, nlp_status
from app.schemas.signals import NLPStatus, ProcessRequest, ProcessResponse

router = APIRouter(prefix="/nlp", tags=["nlp"])


@router.get("/status", response_model=NLPStatus)
def get_nlp_status(db: Session = Depends(get_db)) -> NLPStatus:
    return NLPStatus.model_validate(nlp_status(db, get_settings()))


@router.post("/process-pending", response_model=ProcessResponse)
def process_pending(payload: ProcessRequest | None = None, db: Session = Depends(get_db)) -> ProcessResponse:
    service = NLPService(db, get_settings())
    result = service.process_pending(payload.limit if payload else None)
    return ProcessResponse(
        requested=result.requested,
        processed=result.processed,
        skipped=result.skipped,
        failed=result.failed,
        results=[item.__dict__ for item in result.results],
    )


@router.post("/process/{article_id}", response_model=ProcessResponse)
def process_article(article_id: int, db: Session = Depends(get_db)) -> ProcessResponse:
    service = NLPService(db, get_settings())
    try:
        result = service.process_article(article_id)
    except ArticleNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    return ProcessResponse(
        requested=1,
        processed=int(result.status == "processed"),
        skipped=int(result.status == "skipped"),
        failed=int(result.status == "failed"),
        results=[result.__dict__],
    )
