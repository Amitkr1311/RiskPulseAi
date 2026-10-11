import html
import logging
import xml.etree.ElementTree as ET
from collections.abc import Mapping
from html.parser import HTMLParser

import httpx

from app.core.config import Settings
from app.ingestion.adapters.base import validate_http_response
from app.ingestion.errors import ProviderResponseError, ProviderTimeoutError, ProviderValidationError
from app.ingestion.normalization import NormalizedArticle, normalize_whitespace

logger = logging.getLogger("riskpulse.ingestion.news")


class _FeedTextParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.parts: list[str] = []

    def handle_data(self, data: str) -> None:
        self.parts.append(data)


def _local_name(tag: str) -> str:
    return tag.rsplit("}", 1)[-1].lower()


def _clean_feed_text(value: object) -> str | None:
    if not isinstance(value, str):
        return None
    parser = _FeedTextParser()
    parser.feed(html.unescape(value))
    parser.close()
    cleaned = normalize_whitespace(" ".join(parser.parts))
    return cleaned or None


class NewsRssAdapter:
    source_name = "news"

    def __init__(self, settings: Settings, client: httpx.Client | None = None) -> None:
        self.settings = settings
        self.client = client or httpx.Client()

    @property
    def configured(self) -> bool:
        return bool(self.settings.news_rss_url and self.settings.news_rss_url.strip())

    def fetch(self, limit: int, offset: int = 0) -> list[Mapping[str, object]]:
        del offset  # RSS pagination is provider-controlled; offset is for local replay sources.
        if not self.configured:
            from app.ingestion.errors import ProviderNotConfiguredError

            raise ProviderNotConfiguredError("financial news RSS URL is not configured")
        try:
            response = self.client.get(
                self.settings.news_rss_url,
                timeout=self.settings.ingestion_request_timeout_seconds,
                headers={"Accept": "application/rss+xml, application/atom+xml, application/xml"},
            )
            validate_http_response(response)
        except httpx.TimeoutException as exc:
            raise ProviderTimeoutError("financial news provider timed out") from exc
        except httpx.RequestError as exc:
            raise ProviderTimeoutError("financial news provider request failed") from exc

        try:
            root = ET.fromstring(response.content)
        except ET.ParseError as exc:
            raise ProviderResponseError("financial news feed was not valid XML") from exc

        records: list[Mapping[str, object]] = []
        for item in root.iter():
            if _local_name(item.tag) not in {"item", "entry"}:
                continue
            values: dict[str, object] = {}
            for child in item:
                name = _local_name(child.tag)
                text_value = _clean_feed_text(child.text)
                if name == "link" and child.attrib.get("href"):
                    text_value = child.attrib["href"]
                if text_value is not None:
                    values[name] = text_value
            if values:
                records.append(
                    {
                        "external_id": values.get("guid") or values.get("id") or values.get("link"),
                        "title": values.get("title"),
                        "text": values.get("description") or values.get("content") or values.get("summary"),
                        "url": values.get("link"),
                        "published_at": values.get("pubdate") or values.get("published") or values.get("updated"),
                    }
                )
            if len(records) >= limit:
                break
        return records

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
                is_historical=False,
            )
        except ProviderValidationError:
            raise
        except Exception as exc:
            raise ProviderValidationError("financial news record is malformed") from exc
