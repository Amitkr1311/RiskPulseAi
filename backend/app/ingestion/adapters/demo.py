import json
from collections.abc import Mapping
from pathlib import Path

from app.ingestion.errors import ProviderValidationError
from app.ingestion.normalization import NormalizedArticle


class DemoAdapter:
    source_name = "demo"

    def __init__(self, data_path: Path | None = None) -> None:
        self.data_path = data_path or Path(__file__).resolve().parents[3] / "data" / "demo_articles.json"

    @property
    def configured(self) -> bool:
        return self.data_path.exists()

    def fetch(self, limit: int) -> list[Mapping[str, object]]:
        if not self.configured:
            raise ProviderValidationError("demo fixture file is unavailable")
        with self.data_path.open(encoding="utf-8") as fixture_file:
            records = json.load(fixture_file)
        if not isinstance(records, list):
            raise ProviderValidationError("demo fixture file must contain a list")
        return records[:limit]

    def normalize(self, record: Mapping[str, object]) -> NormalizedArticle:
        try:
            return NormalizedArticle(
                source=record.get("source"),
                external_id=record.get("external_id"),
                title=record.get("title"),
                text=record.get("text"),
                url=record.get("url"),
                published_at=record.get("published_at"),
                is_demo=True,
            )
        except ProviderValidationError:
            raise
        except Exception as exc:
            raise ProviderValidationError("demo record is malformed") from exc

