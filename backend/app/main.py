from fastapi import Depends, FastAPI, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.db.session import get_db
from app.schemas.health import DependencyHealth, HealthResponse

settings = get_settings()
app = FastAPI(title=settings.app_name, version="0.1.0", description="RiskPulse AI foundation API")
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.backend_cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
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

