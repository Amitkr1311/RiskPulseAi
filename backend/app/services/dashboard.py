from datetime import UTC, datetime, timedelta

from sqlalchemy import case, func, select
from sqlalchemy.orm import Session

from app.db.models import Article, IngestionRun, RiskSignal

HIGH_IMPACT_THRESHOLD = 7


def dashboard_summary(db: Session) -> dict[str, object]:
    now = datetime.now(UTC)
    day_ago = now - timedelta(days=1)
    week_ago = now - timedelta(days=7)
    month_ago = now - timedelta(days=30)

    total_articles = _count(db, select(func.count()).select_from(Article))
    processed_articles = _count(db, select(func.count()).select_from(Article).where(Article.processing_status == "processed"))
    pending_articles = _count(db, select(func.count()).select_from(Article).where(Article.processing_status == "pending"))
    failed_articles = _count(db, select(func.count()).select_from(Article).where(Article.processing_status == "failed"))
    total_signals = _count(db, select(func.count()).select_from(RiskSignal))
    high_impact_signals = _count(
        db,
        select(func.count()).select_from(RiskSignal).where(RiskSignal.impact_score >= HIGH_IMPACT_THRESHOLD),
    )
    signal_counts = db.execute(
        select(
            func.count(case((RiskSignal.created_at >= day_ago, 1))).label("last_24_hours"),
            func.count(case((RiskSignal.created_at >= week_ago, 1))).label("last_7_days"),
            func.count(case((RiskSignal.created_at >= month_ago, 1))).label("last_30_days"),
        )
    ).one()

    return {
        "total_articles": total_articles,
        "processed_articles": processed_articles,
        "pending_articles": pending_articles,
        "failed_articles": failed_articles,
        "total_signals": total_signals,
        "high_impact_signals": high_impact_signals,
        "high_impact_threshold": HIGH_IMPACT_THRESHOLD,
        "recent_signal_counts": {
            "last_24_hours": int(signal_counts.last_24_hours or 0),
            "last_7_days": int(signal_counts.last_7_days or 0),
            "last_30_days": int(signal_counts.last_30_days or 0),
        },
        "live_articles": _count(db, select(func.count()).select_from(Article).where(Article.is_demo.is_(False))),
        "demo_articles": _count(db, select(func.count()).select_from(Article).where(Article.is_demo.is_(True))),
        "latest_ingestion_at": db.scalar(select(func.max(IngestionRun.completed_at))),
        "latest_processed_at": db.scalar(select(func.max(Article.processed_at))),
    }


def _count(db: Session, query) -> int:
    return int(db.scalar(query) or 0)
