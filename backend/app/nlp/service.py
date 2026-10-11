from datetime import UTC, datetime
from dataclasses import dataclass
import importlib.util
import logging

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.db.models import Article, ArticleEntity, Entity, RiskSignal
from app.nlp.contracts import AnalysisResult, ProcessingResult
from app.nlp.entities import AliasEntityExtractor, load_aliases
from app.nlp.events import RuleBasedEventClassifier
from app.nlp.impact import ImpactScorer
from app.nlp.preprocessing import TextProcessingError, preprocess_text
from app.nlp.sentiment import (
    FinBertSentimentAnalyzer,
    HeuristicSentimentAnalyzer,
    SentimentInferenceError,
    UnavailableSentimentAnalyzer,
)
from app.stress_testing.service import StressTestingService

logger = logging.getLogger("riskpulse.nlp")


@dataclass(frozen=True)
class BatchResult:
    requested: int
    processed: int
    skipped: int
    failed: int
    results: tuple[ProcessingResult, ...]


class ArticleNotFoundError(LookupError):
    pass


def build_sentiment_analyzer(settings: Settings):
    backend = settings.nlp_sentiment_backend.casefold()
    if backend == "heuristic":
        return HeuristicSentimentAnalyzer()
    if backend == "finbert":
        return FinBertSentimentAnalyzer(
            model_id=settings.nlp_sentiment_model_id,
            device=settings.nlp_model_device,
            allow_download=settings.nlp_allow_model_download,
        )
    raise ValueError("NLP_SENTIMENT_BACKEND must be 'heuristic' or 'finbert'")


class NLPService:
    def __init__(
        self,
        db: Session,
        settings: Settings,
        sentiment=None,
        entity_extractor: AliasEntityExtractor | None = None,
        event_classifier: RuleBasedEventClassifier | None = None,
        impact_scorer: ImpactScorer | None = None,
    ) -> None:
        self.db = db
        self.settings = settings
        if sentiment is not None:
            self.sentiment = sentiment
        else:
            try:
                self.sentiment = build_sentiment_analyzer(settings)
            except SentimentInferenceError as exc:
                self.sentiment = UnavailableSentimentAnalyzer(str(exc))
        self.entity_extractor = entity_extractor or AliasEntityExtractor(load_aliases(settings.nlp_entity_aliases_path))
        self.event_classifier = event_classifier or RuleBasedEventClassifier()
        self.impact_scorer = impact_scorer or ImpactScorer()

    def process_pending(self, limit: int | None = None) -> BatchResult:
        batch_limit = limit or self.settings.nlp_batch_size
        signal_exists = select(RiskSignal.id).where(RiskSignal.article_id == Article.id).exists()
        article_ids = self.db.scalars(
            select(Article.id)
            .where(Article.processing_status.in_(["pending", "failed"]))
            .where(~signal_exists)
            .order_by(Article.id)
            .limit(batch_limit)
        ).all()
        results = tuple(self.process_article(article_id) for article_id in article_ids)
        return BatchResult(
            requested=len(article_ids),
            processed=sum(result.status == "processed" for result in results),
            skipped=sum(result.status == "skipped" for result in results),
            failed=sum(result.status == "failed" for result in results),
            results=results,
        )

    def process_articles(self, article_ids: tuple[int, ...]) -> BatchResult:
        """Process exactly the articles inserted by one ingestion batch."""
        results = tuple(self.process_article(article_id) for article_id in article_ids)
        return BatchResult(
            requested=len(article_ids),
            processed=sum(result.status == "processed" for result in results),
            skipped=sum(result.status == "skipped" for result in results),
            failed=sum(result.status == "failed" for result in results),
            results=results,
        )

    def process_article(self, article_id: int) -> ProcessingResult:
        article = self.db.get(Article, article_id)
        if article is None:
            raise ArticleNotFoundError(f"Article {article_id} was not found")
        if self.db.scalar(select(RiskSignal.id).where(RiskSignal.article_id == article_id)) is not None:
            if article.processing_status != "processed":
                article.processing_status = "processed"
                article.processed_at = datetime.now(UTC)
                self.db.commit()
            return ProcessingResult(article_id, "skipped")

        article.processing_status = "processing"
        article.processing_attempts = (article.processing_attempts or 0) + 1
        self.db.commit()
        try:
            analysis = self._analyze(article)
            signal = self._persist(article_id, analysis)
            return ProcessingResult(article_id, "processed", signal_id=signal.id)
        except (TextProcessingError, SentimentInferenceError, ValueError) as exc:
            fallback_code = "model_unavailable" if isinstance(exc, SentimentInferenceError) else "analysis_failed"
            return self._record_failure(article_id, getattr(exc, "code", fallback_code))
        except IntegrityError:
            self.db.rollback()
            if self.db.scalar(select(RiskSignal.id).where(RiskSignal.article_id == article_id)) is not None:
                return ProcessingResult(article_id, "skipped")
            return self._record_failure(article_id, "database_error")
        except Exception:
            self.db.rollback()
            return self._record_failure(article_id, "processing_failed")

    def _analyze(self, article: Article) -> AnalysisResult:
        preprocessed = preprocess_text(article.title, article.text, self.settings.nlp_max_text_chars)
        entities = self.entity_extractor.extract(preprocessed.text)
        sentiment = self.sentiment.analyze(preprocessed.text)
        event = self.event_classifier.classify(preprocessed.text)
        impact = self.impact_scorer.score(article.source, event, sentiment, len(entities) / 3)
        return AnalysisResult(preprocessed.text, entities, sentiment, event, impact)

    def _persist(self, article_id: int, analysis: AnalysisResult) -> RiskSignal:
        article = self.db.get(Article, article_id)
        if article is None:
            raise ArticleNotFoundError(f"Article {article_id} was not found")
        self.db.query(ArticleEntity).filter(ArticleEntity.article_id == article_id).delete(synchronize_session=False)
        self.db.flush()

        entity_payloads: list[dict[str, object]] = []
        primary_entity: Entity | None = None
        linked_entity_ids: set[int] = set()
        for mention in analysis.entities:
            entity = self.db.scalar(select(Entity).where(Entity.canonical_name == mention.canonical_name))
            if entity is None:
                entity = Entity(
                    canonical_name=mention.canonical_name,
                    identifier=mention.identifier,
                    aliases=[mention.mention],
                    entity_type=mention.entity_type,
                )
                self.db.add(entity)
                self.db.flush()
            elif mention.mention not in (entity.aliases or []):
                entity.aliases = [*(entity.aliases or []), mention.mention]
            if entity.id not in linked_entity_ids:
                self.db.add(
                    ArticleEntity(
                        article_id=article_id,
                        entity_id=entity.id,
                        raw_mention=mention.mention,
                        extraction_confidence=mention.extraction_confidence,
                    )
                )
                linked_entity_ids.add(entity.id)
            primary_entity = primary_entity or entity
            entity_payloads.append(
                {
                    "mention": mention.mention,
                    "canonical_name": mention.canonical_name,
                    "identifier": mention.identifier,
                    "resolved": mention.resolved,
                    "entity_type": mention.entity_type,
                }
            )

        sentiment = analysis.sentiment
        event = analysis.event
        signal = RiskSignal(
            article_id=article_id,
            entity_id=primary_entity.id if primary_entity else None,
            entity_name=primary_entity.canonical_name if primary_entity else None,
            sentiment_score=sentiment.score,
            sentiment_label=sentiment.label,
            sentiment_probabilities=sentiment.probabilities,
            event_type=event.event_type,
            event_confidence=event.confidence,
            impact_score=analysis.impact.score,
            impact_factors=analysis.impact.factors,
            entities=entity_payloads,
            confidence=event.confidence,
            explanation=analysis.impact.rationale,
            model_version=f"{sentiment.model_id}+{event.classifier}",
            model_metadata={
                "sentiment_backend": sentiment.backend,
                "sentiment_model_id": sentiment.model_id,
                "event_classifier": event.classifier,
                "event_terms": list(event.matched_terms),
                "inference_note": "Heuristic output is deterministic and is not a substitute for FinBERT.",
            },
            scoring_config_version=self.impact_scorer.version,
        )
        self.db.add(signal)
        article.processing_status = "processed"
        article.processing_error = None
        article.processed_at = datetime.now(UTC)
        self.db.commit()
        self.db.refresh(signal)
        try:
            StressTestingService(self.db, self.settings).auto_trigger_for_signal(signal.id)
        except Exception:
            # The signal is already durable; a missing portfolio or scenario must
            # not turn successful NLP persistence into a failed article process.
            logger.exception("Automatic stress trigger failed", extra={"signal_id": signal.id})
        return signal

    def _record_failure(self, article_id: int, error_code: str) -> ProcessingResult:
        self.db.rollback()
        article = self.db.get(Article, article_id)
        if article is not None:
            article.processing_status = "failed"
            article.processing_error = error_code[:128]
            self.db.commit()
        return ProcessingResult(article_id, "failed", error=error_code)


def nlp_status(db: Session, settings: Settings) -> dict[str, object]:
    counts = dict(db.execute(select(Article.processing_status, func.count()).group_by(Article.processing_status)).all())
    backend = settings.nlp_sentiment_backend.casefold()
    available = backend == "heuristic" or importlib.util.find_spec("transformers") is not None
    return {
        "sentiment_backend": backend,
        "sentiment_model_id": settings.nlp_sentiment_model_id,
        "model_available": available,
        "model_download_allowed": settings.nlp_allow_model_download,
        "pending_articles": int(counts.get("pending", 0)),
        "failed_articles": int(counts.get("failed", 0)),
        "processed_articles": int(counts.get("processed", 0)),
        "signal_count": int(db.scalar(select(func.count()).select_from(RiskSignal)) or 0),
    }
