import asyncio
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.db.session import get_db
from app.api.articles import router as articles_router
from app.api.ingestion import router as ingestion_router
from app.api.nlp import router as nlp_router
from app.api.signals import router as signals_router
from app.api.dashboard import router as dashboard_router
from app.api.portfolio import router as portfolio_router
from app.api.stress_testing import router as stress_testing_router
from app.api.research import router as research_router
from app.api.replay import replay_manager, router as replay_router
from app.ingestion.scheduler import LiveIngestionScheduler
from app.schemas.health import DependencyHealth, HealthResponse

settings = get_settings()


@asynccontextmanager
async def lifespan(_app: FastAPI):
    stop_event = asyncio.Event()
    task = None
    replay_manager.recover_after_restart()
    if settings.ingestion_live_enabled:
        task = asyncio.create_task(LiveIngestionScheduler(settings).run(stop_event))
    try:
        yield
    finally:
        if task is not None:
            stop_event.set()
            await task
        await asyncio.to_thread(replay_manager.shutdown)


app = FastAPI(
    title=settings.app_name,
    version="0.1.0",
    description="RiskPulse AI foundation API",
    lifespan=lifespan,
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.backend_cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(articles_router)
app.include_router(ingestion_router)
app.include_router(nlp_router)
app.include_router(signals_router)
app.include_router(dashboard_router)
app.include_router(portfolio_router)
app.include_router(stress_testing_router)
app.include_router(research_router)
app.include_router(replay_router)


@app.exception_handler(SQLAlchemyError)
async def database_error_handler(_request, _exc: SQLAlchemyError) -> JSONResponse:
    return JSONResponse(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        content={"detail": "Database service is unavailable"},
    )


@app.get("/health", response_model=HealthResponse, tags=["system"])
def health(db: Session = Depends(get_db)) -> HealthResponse | JSONResponse:
    try:
        db.execute(text("SELECT 1"))
    except SQLAlchemyError:
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={
                "status": "degraded",
                "service": settings.app_name,
                "version": app.version,
                "database": {"status": "unavailable"},
            },
        )

    return HealthResponse(
        status="healthy",
        service=settings.app_name,
        version=app.version,
        database=DependencyHealth(status="healthy"),
    )
