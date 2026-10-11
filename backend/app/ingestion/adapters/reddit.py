import logging
from collections.abc import Mapping

import httpx

from app.core.config import Settings
from app.ingestion.adapters.base import validate_http_response
from app.ingestion.errors import ProviderNotConfiguredError, ProviderResponseError, ProviderTimeoutError, ProviderValidationError
from app.ingestion.normalization import NormalizedArticle

logger = logging.getLogger("riskpulse.ingestion.reddit")


class RedditAdapter:
    source_name = "reddit"

    def __init__(self, settings: Settings, client: httpx.Client | None = None) -> None:
        self.settings = settings
        self.client = client or httpx.Client()

    @property
    def configured(self) -> bool:
        return bool(
            self.settings.reddit_ingestion_enabled
            and self.settings.reddit_access_token
            and self.settings.reddit_subreddits
        )

    def fetch(self, limit: int, offset: int = 0) -> list[Mapping[str, object]]:
        del offset  # Reddit pagination uses provider cursors, not row offsets.
        if not self.configured:
            raise ProviderNotConfiguredError("Reddit access token or subreddit configuration is missing")
        token = self.settings.reddit_access_token.get_secret_value()
        records: list[Mapping[str, object]] = []
        for subreddit in self.settings.reddit_subreddits:
            if len(records) >= limit:
                break
            params: dict[str, object] = {"limit": min(limit - len(records), 100), "sort": "new", "raw_json": 1}
            if self.settings.reddit_search_terms:
                params["q"] = " OR ".join(self.settings.reddit_search_terms)
                params["restrict_sr"] = "on"
            try:
                response = self.client.get(
                    f"{self.settings.reddit_api_base_url.rstrip('/')}/r/{subreddit}/search.json",
                    params=params,
                    timeout=self.settings.ingestion_request_timeout_seconds,
                    headers={
                        "Authorization": f"Bearer {token}",
                        "User-Agent": self.settings.reddit_user_agent,
                    },
                )
                validate_http_response(response)
            except httpx.TimeoutException as exc:
                raise ProviderTimeoutError("Reddit provider timed out") from exc
            except httpx.RequestError as exc:
                raise ProviderTimeoutError("Reddit provider request failed") from exc

            try:
                payload = response.json()
                children = payload["data"]["children"]
                if not isinstance(children, list):
                    raise TypeError("children was not a list")
            except (ValueError, KeyError, TypeError) as exc:
                raise ProviderResponseError("Reddit response was malformed") from exc

            for child in children:
                data = child.get("data") if isinstance(child, dict) else None
                if not isinstance(data, dict):
                    continue
                text = data.get("selftext")
                if not isinstance(text, str) or text.strip() in {"", "[deleted]", "[removed]"}:
                    logger.info("Skipping Reddit post with deleted or empty content", extra={"source": "reddit"})
                    continue
                url = data.get("url") or data.get("permalink")
                if isinstance(url, str) and url.startswith("/"):
                    url = f"{self.settings.reddit_api_base_url.rstrip('/')}{url}"
                records.append(
                    {
                        "external_id": data.get("id"),
                        "title": data.get("title"),
                        "text": text,
                        "url": url,
                        "published_at": data.get("created_utc"),
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
            raise ProviderValidationError("Reddit record is malformed") from exc
