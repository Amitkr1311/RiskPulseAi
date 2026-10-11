from collections.abc import Mapping
from typing import Protocol

import httpx

from app.ingestion.errors import (
    ProviderAuthenticationError,
    ProviderRateLimitError,
    ProviderResponseError,
    ProviderTransientError,
)
from app.ingestion.normalization import NormalizedArticle


class SourceAdapter(Protocol):
    source_name: str

    @property
    def configured(self) -> bool: ...

    def fetch(self, limit: int, offset: int = 0) -> list[Mapping[str, object]]: ...

    def normalize(self, record: Mapping[str, object]) -> NormalizedArticle: ...


def validate_http_response(response: httpx.Response) -> None:
    if response.status_code in (401, 403):
        raise ProviderAuthenticationError("provider authentication failed")
    if response.status_code in (408, 429):
        raise ProviderRateLimitError("provider rate limit or timeout response")
    if response.status_code >= 500:
        raise ProviderTransientError("provider returned a server error")
    if response.status_code >= 400:
        raise ProviderResponseError("provider returned an unsuccessful response")
