from app.core.config import Settings
from app.ingestion.adapters.news import NewsRssAdapter
from app.ingestion.adapters.reddit import RedditAdapter
from app.ingestion.adapters.social import SocialCsvAdapter


def build_adapters(settings: Settings) -> dict[str, object]:
    return {
        "news": NewsRssAdapter(settings),
        "social": SocialCsvAdapter(settings),
        "reddit": RedditAdapter(settings),
    }
