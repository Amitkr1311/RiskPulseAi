import hashlib
from datetime import UTC

import httpx
import pytest

from app.core.config import Settings
from app.ingestion.adapters.news import NewsRssAdapter
from app.ingestion.adapters.reddit import RedditAdapter
from app.ingestion.adapters.social import SocialCsvAdapter
from app.ingestion.errors import ProviderNotConfiguredError, ProviderResponseError, ProviderTimeoutError, ProviderValidationError


NEWS_XML = b"""
<rss><channel><item>
  <guid>news-1</guid>
  <title>  Earnings update  </title>
  <description><![CDATA[<p>Revenue increased.</p><a href="https://example.test/read-more">Read more</a>]]></description>
  <link>https://example.test/news-1</link>
  <pubDate>Mon, 19 Jan 2026 10:00:00 GMT</pubDate>
</item></channel></rss>
"""

ATOM_XML = b"""
<feed xmlns="http://www.w3.org/2005/Atom"><entry>
  <id>atom-1</id><title>Market update</title>
  <summary type="html"><![CDATA[<p>Index moved higher.</p>]]></summary>
  <link href="https://example.test/atom-1" />
  <updated>2026-01-19T10:00:00Z</updated>
</entry></feed>
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


def test_news_normalizes_overlong_external_ids_deterministically():
    adapter = NewsRssAdapter(Settings(news_rss_url="https://example.test/feed"))
    long_external_id = "google-news-id-" + ("x" * 500)

    article = adapter.normalize(
        {
            "external_id": long_external_id,
            "title": "Long identifier",
            "text": "A valid article body.",
        }
    )

    assert article.external_id == "sha256:" + hashlib.sha256(long_external_id.encode()).hexdigest()
    assert len(article.external_id) == 71


def test_news_adapter_parses_rss_with_mocked_http():
    transport = httpx.MockTransport(lambda request: httpx.Response(200, content=NEWS_XML, request=request))
    settings = Settings(news_rss_url="https://example.test/feed")
    with httpx.Client(transport=transport) as client:
        records = NewsRssAdapter(settings, client).fetch(limit=10)

    assert len(records) == 1
    assert records[0]["external_id"] == "news-1"
    assert records[0]["title"] == "Earnings update"
    assert records[0]["text"] == "Revenue increased. Read more"


def test_news_adapter_parses_atom_entries_and_link_attributes():
    transport = httpx.MockTransport(lambda request: httpx.Response(200, content=ATOM_XML, request=request))
    settings = Settings(news_rss_url="https://example.test/feed")
    with httpx.Client(transport=transport) as client:
        records = NewsRssAdapter(settings, client).fetch(limit=10)

    assert records == [{
        "external_id": "atom-1",
        "title": "Market update",
        "text": "Index moved higher.",
        "url": "https://example.test/atom-1",
        "published_at": "2026-01-19T10:00:00Z",
    }]


def test_news_adapter_rejects_invalid_xml_and_surfaces_timeout():
    invalid_transport = httpx.MockTransport(lambda request: httpx.Response(200, content=b"not xml", request=request))
    with httpx.Client(transport=invalid_transport) as client:
        with pytest.raises(ProviderResponseError):
            NewsRssAdapter(Settings(news_rss_url="https://example.test/feed"), client).fetch(limit=10)

    def timeout(_request):
        raise httpx.ReadTimeout("timed out")

    with httpx.Client(transport=httpx.MockTransport(timeout)) as client:
        with pytest.raises(ProviderTimeoutError):
            NewsRssAdapter(Settings(news_rss_url="https://example.test/feed"), client).fetch(limit=10)


def test_reddit_record_normalizes_same_contract():
    adapter = RedditAdapter(Settings(reddit_ingestion_enabled=True, reddit_access_token="token"))

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
    settings = Settings(reddit_ingestion_enabled=True, reddit_access_token="token", reddit_subreddits=["finance"])
    with httpx.Client(transport=transport) as client:
        records = RedditAdapter(settings, client).fetch(limit=10)

    assert records[0]["external_id"] == "post-1"
    assert records[0]["text"] == "The central bank held rates steady."


def test_social_csv_replays_tweets_through_the_shared_normalization_contract(tmp_path):
    csv_path = tmp_path / "tweets-vs-stock.csv"
    csv_path.write_text(
        "tweet_id,Tweet,Date,Stock Price\n"
        "tweet-1,\"Bank shares face tariff risk\",2026-01-19,100.5\n",
        encoding="utf-8",
    )
    adapter = SocialCsvAdapter(Settings(social_csv_path=str(csv_path)))

    records = adapter.fetch(limit=10)
    article = adapter.normalize(records[0])

    assert adapter.configured is True
    assert records[0]["external_id"] == "tweet-1"
    assert article.source == "social"
    assert article.text == "Bank shares face tariff risk"
    assert article.published_at.tzinfo == UTC
    assert article.is_demo is False


def test_missing_social_csv_is_reported_as_not_configured(tmp_path):
    adapter = SocialCsvAdapter(Settings(social_csv_path=str(tmp_path / "missing.csv")))

    with pytest.raises(ProviderNotConfiguredError):
        adapter.fetch(limit=10)


def test_missing_or_malformed_fields_are_rejected():
    adapter = NewsRssAdapter(Settings(news_rss_url="https://example.test/feed"))

    with pytest.raises(ProviderValidationError):
        adapter.normalize({"external_id": "missing-title", "text": "Body"})
    with pytest.raises(ProviderValidationError):
        adapter.normalize({"title": "Title", "text": "Body", "published_at": "not-a-date"})


def test_missing_reddit_credentials_are_reported_without_network_access():
    adapter = RedditAdapter(Settings(reddit_ingestion_enabled=True, reddit_access_token=None))

    with pytest.raises(ProviderNotConfiguredError):
        adapter.fetch(limit=10)


def test_reddit_is_disabled_without_explicit_opt_in():
    adapter = RedditAdapter(Settings(reddit_access_token="token"))

    with pytest.raises(ProviderNotConfiguredError):
        adapter.fetch(limit=10)
