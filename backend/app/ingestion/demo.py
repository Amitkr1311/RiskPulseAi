from app.core.config import get_settings
from app.db.session import SessionLocal
from app.ingestion.adapters.demo import DemoAdapter
from app.ingestion.service import IngestionService


def main() -> None:
    settings = get_settings()
    with SessionLocal() as db:
        result = IngestionService(db, {"demo": DemoAdapter()}, settings).run(["demo"], limit=100)
    for run in result:
        print(
            f"source={run.source} status={run.status} fetched={run.fetched} "
            f"inserted={run.inserted} duplicates_skipped={run.duplicates_skipped} failed={run.failed}"
        )


if __name__ == "__main__":
    main()

