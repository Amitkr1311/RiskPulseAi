from app.core.config import Settings
from app.ingestion.adapters.news import NewsRssAdapter
from app.ingestion.adapters.reddit import RedditAdapter


def build_adapters(settings: Settings) -> dict[str, object]:
    return {
        "news": NewsRssAdapter(settings),
        "reddit": RedditAdapter(settings),
    }

