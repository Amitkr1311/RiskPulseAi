import argparse

from app.core.config import get_settings
from app.db.session import SessionLocal
from app.nlp.service import NLPService


def main() -> None:
    parser = argparse.ArgumentParser(description="Process pending RiskPulse articles through the NLP pipeline")
    parser.add_argument("--limit", type=int, default=None, help="Maximum number of pending articles")
    parser.add_argument("--article-id", type=int, default=None, help="Process one article instead of a batch")
    args = parser.parse_args()
    db = SessionLocal()
    try:
        service = NLPService(db, get_settings())
        if args.article_id is not None:
            result = service.process_article(args.article_id)
            print(result)
        else:
            print(service.process_pending(args.limit))
    finally:
        db.close()


if __name__ == "__main__":
    main()
