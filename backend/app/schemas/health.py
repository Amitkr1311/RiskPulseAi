from typing import Literal

from pydantic import BaseModel


class DependencyHealth(BaseModel):
    status: Literal["healthy", "unavailable"]


class HealthResponse(BaseModel):
    status: Literal["healthy", "degraded"]
    service: str
    version: str
    database: DependencyHealth

