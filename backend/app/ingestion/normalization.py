import hashlib
import re
from datetime import UTC, datetime
from email.utils import parsedate_to_datetime
from typing import Any

from pydantic import BaseModel, Field, ValidationInfo, field_validator, model_validator

from app.ingestion.errors import ProviderValidationError

_WHITESPACE = re.compile(r"\s+")


def normalize_whitespace(value: str) -> str:
    return _WHITESPACE.sub(" ", value).strip()


def parse_timestamp(value: Any) -> datetime | None:
    if value is None or value == "":
        return None
    try:
        if isinstance(value, (int, float)):
            parsed = datetime.fromtimestamp(value, tz=UTC)
        elif isinstance(value, datetime):
            parsed = value
        elif isinstance(value, str):
            raw_value = value.strip()
            try:
                parsed = datetime.fromisoformat(raw_value.replace("Z", "+00:00"))
            except ValueError:
                parsed = parsedate_to_datetime(raw_value)
        else:
            raise ValueError("unsupported timestamp type")
    except (TypeError, ValueError, OverflowError) as exc:
        raise ProviderValidationError("publication timestamp is malformed") from exc

    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC)


def content_hash_for(title: str, text: str) -> str:
    canonical = f"{normalize_whitespace(title).lower()}\n{normalize_whitespace(text).lower()}"
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


class NormalizedArticle(BaseModel):
    source: str = Field(min_length=1, max_length=32)
    external_id: str | None = Field(default=None, max_length=255)
    title: str = Field(min_length=1, max_length=500)
    text: str = Field(min_length=1)
    url: str | None = Field(default=None, max_length=1000)
    published_at: datetime | None = None
    ingested_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    content_hash: str = ""
    is_demo: bool = False
    is_historical: bool = False
    source_metadata: dict[str, object] | None = None
    processing_status: str = "pending"

    @field_validator("source", "title", "text", mode="before")
    @classmethod
    def clean_required_text(cls, value: Any) -> str:
        if not isinstance(value, str):
            raise ProviderValidationError("required text field is missing")
        cleaned = normalize_whitespace(value)
        if not cleaned:
            raise ProviderValidationError("required text field is empty")
        return cleaned

    @field_validator("external_id", "url", mode="before")
    @classmethod
    def clean_optional_text(cls, value: Any, info: ValidationInfo) -> str | None:
        if value is None:
            return None
        if not isinstance(value, str):
            raise ProviderValidationError("optional text field is malformed")
        cleaned = normalize_whitespace(value)
        if info.field_name == "external_id" and len(cleaned) > 255:
            return f"sha256:{hashlib.sha256(cleaned.encode('utf-8')).hexdigest()}"
        return cleaned or None

    @field_validator("published_at", "ingested_at", mode="before")
    @classmethod
    def normalize_datetime(cls, value: Any) -> datetime | None:
        return parse_timestamp(value)

    @model_validator(mode="after")
    def set_content_hash(self) -> "NormalizedArticle":
        if not self.content_hash:
            self.content_hash = content_hash_for(self.title, self.text)
        return self
