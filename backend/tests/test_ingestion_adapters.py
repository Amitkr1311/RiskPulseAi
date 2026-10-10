from datetime import UTC

import httpx
import pytest

from app.core.config import Settings
from app.ingestion.adapters.news import NewsRssAdapter
from app.ingestion.adapters.reddit import RedditAdapter
from app.ingestion.errors import ProviderNotConfiguredError, ProviderValidationError


NEWS_XML = b"""
<rss><channel><item>
  <guid>news-1</guid>
  <title>  Earnings update  </title>
  <description>  Revenue increased.  </description>
  <link>https://example.test/news-1</link>
  <pubDate>Mon, 19 Jan 2026 10:00:00 GMT</pubDate>
</item></channel></rss>
"""


def test_news_record_normalizes_content_and_timestamp():
    adapter = NewsRssAdapter(Settings(news_rss_url="https://example.test/feed"))

    article = adapter.normalize(
        {
            "external_id": "news-1",
            "title": "  Earnings update  ",
            "text": " Revenue increased. ",
            "url": "https://example.test/news-1",
            "published_at": "2026-01-19T10:00:00+05:30",
        }
    )

    assert article.source == "news"
    assert article.title == "Earnings update"
    assert article.text == "Revenue increased."
    assert article.published_at.tzinfo == UTC
    assert article.published_at.hour == 4
    assert article.is_demo is False


def test_news_adapter_parses_rss_with_mocked_http():
    transport = httpx.MockTransport(lambda request: httpx.Response(200, content=NEWS_XML, request=request))
    settings = Settings(news_rss_url="https://example.test/feed")
    with httpx.Client(transport=transport) as client:
        records = NewsRssAdapter(settings, client).fetch(limit=10)

    assert len(records) == 1
    assert records[0]["external_id"] == "news-1"
    assert records[0]["title"] == "Earnings update"


def test_reddit_record_normalizes_same_contract():
    adapter = RedditAdapter(Settings(reddit_access_token="token"))

    article = adapter.normalize(
        {
            "external_id": "post-1",
            "title": "Rate discussion",
            "text": "The central bank held rates steady.",
            "url": "https://reddit.test/post-1",
            "published_at": 1768816800,
        }
    )

    assert article.source == "reddit"
    assert article.external_id == "post-1"
    assert article.published_at.tzinfo == UTC
    assert article.is_demo is False


def test_reddit_adapter_parses_api_response_with_mocked_http():
    payload = {
        "data": {
            "children": [
                {
                    "data": {
                        "id": "post-1",
                        "title": "Rate discussion",
                        "selftext": "The central bank held rates steady.",
                        "url": "https://reddit.test/post-1",
                        "created_utc": 1768816800,
                    }
                }
            ]
        }
    }
    transport = httpx.MockTransport(lambda request: httpx.Response(200, json=payload, request=request))
    settings = Settings(reddit_access_token="token", reddit_subreddits=["finance"])
    with httpx.Client(transport=transport) as client:
        records = RedditAdapter(settings, client).fetch(limit=10)

    assert records[0]["external_id"] == "post-1"
    assert records[0]["text"] == "The central bank held rates steady."


def test_missing_or_malformed_fields_are_rejected():
    adapter = NewsRssAdapter(Settings(news_rss_url="https://example.test/feed"))

    with pytest.raises(ProviderValidationError):
        adapter.normalize({"external_id": "missing-title", "text": "Body"})
    with pytest.raises(ProviderValidationError):
        adapter.normalize({"title": "Title", "text": "Body", "published_at": "not-a-date"})


def test_missing_reddit_credentials_are_reported_without_network_access():
    adapter = RedditAdapter(Settings(reddit_access_token=None))

    with pytest.raises(ProviderNotConfiguredError):
        adapter.fetch(limit=10)

