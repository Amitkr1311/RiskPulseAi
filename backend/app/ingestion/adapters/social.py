import csv
from collections.abc import Mapping
from pathlib import Path

from app.core.config import Settings
from app.ingestion.errors import ProviderNotConfiguredError, ProviderResponseError, ProviderValidationError
from app.ingestion.normalization import NormalizedArticle


class SocialCsvAdapter:
    """Replay historical tweet/stock records through the normal article flow."""

    source_name = "social"
    text_columns = ("tweet", "text", "content", "message", "body", "headline")
    id_columns = ("id", "tweet_id", "tweetid", "uuid")
    title_columns = ("title", "headline", "subject")
    date_columns = ("date", "datetime", "timestamp", "created_at", "published_at")
    url_columns = ("url", "link", "permalink")
    stock_columns = ("stock name", "stock_name", "stock", "ticker", "symbol")
    company_columns = ("company name", "company_name", "company", "issuer")

    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    @property
    def path(self) -> Path:
        configured_path = Path(self.settings.social_csv_path)
        if configured_path.is_absolute():
            return configured_path
        candidates = (Path.cwd() / configured_path, Path(__file__).resolve().parents[3] / configured_path)
        return next((candidate for candidate in candidates if candidate.exists()), candidates[0])

    @property
    def configured(self) -> bool:
        return self.path.is_file()

    def fetch(self, limit: int, offset: int = 0) -> list[Mapping[str, object]]:
        if not self.configured:
            raise ProviderNotConfiguredError(
                f"social CSV not found; place the Kaggle export at {self.settings.social_csv_path}"
            )
        try:
            with self.path.open("r", encoding="utf-8-sig", newline="") as csv_file:
                reader = csv.DictReader(csv_file)
                field_map = {
                    field.strip().casefold(): field
                    for field in (reader.fieldnames or [])
                    if isinstance(field, str) and field.strip()
                }
                text_key = self._find_column(field_map, self.text_columns)
                if text_key is None:
                    raise ProviderResponseError(
                        "social CSV must contain one of: Tweet, Text, Content, Message, or Body"
                    )

                records: list[Mapping[str, object]] = []
                for row_number, row in enumerate(reader, start=2):
                    if row_number - 2 < offset:
                        continue
                    values = {
                        key.casefold(): value.strip() if isinstance(value, str) else value
                        for key, value in row.items()
                        if isinstance(key, str)
                    }
                    text = values.get(text_key.casefold())
                    if not isinstance(text, str) or not text:
                        # Let the shared normalize/store flow count malformed rows.
                        text = ""
                    external_id = self._value(values, field_map, self.id_columns)
                    stock_name = self._value(values, field_map, self.stock_columns)
                    company_name = self._value(values, field_map, self.company_columns)
                    stock_label = " / ".join(
                        value for value in (str(stock_name).strip() if stock_name else "", str(company_name).strip() if company_name else "") if value
                    )
                    records.append(
                        {
                            "external_id": external_id,
                            "title": self._value(values, field_map, self.title_columns)
                            or f"Historical social post{f' · {stock_label}' if stock_label else ''}",
                            "text": text,
                            "url": self._value(values, field_map, self.url_columns),
                            "published_at": self._value(values, field_map, self.date_columns),
                            "stock_name": stock_name,
                            "company_name": company_name,
                        }
                    )
                    if len(records) >= limit:
                        break
                return records
        except ProviderResponseError:
            raise
        except (OSError, csv.Error) as exc:
            raise ProviderResponseError("social CSV could not be read") from exc

    def normalize(self, record: Mapping[str, object]) -> NormalizedArticle:
        try:
            return NormalizedArticle(
                source=self.source_name,
                external_id=record.get("external_id"),
                title=record.get("title"),
                text=record.get("text"),
                url=record.get("url"),
                published_at=record.get("published_at"),
                is_demo=False,
                is_historical=True,
                source_metadata={
                    "dataset": "Tweet Sentiment's Impact on Stock Returns",
                    "replay": True,
                    "stock_name": record.get("stock_name"),
                    "company_name": record.get("company_name"),
                },
            )
        except ProviderValidationError:
            raise
        except Exception as exc:
            raise ProviderValidationError("social CSV record is malformed") from exc

    @staticmethod
    def _find_column(field_map: dict[str, str], candidates: tuple[str, ...]) -> str | None:
        return next((field_map[candidate] for candidate in candidates if candidate in field_map), None)

    @classmethod
    def _value(
        cls,
        values: dict[str, object],
        field_map: dict[str, str],
        candidates: tuple[str, ...],
    ) -> object | None:
        field = cls._find_column(field_map, candidates)
        return values.get(field.casefold()) if field is not None else None
