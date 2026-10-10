from dataclasses import dataclass


@dataclass(frozen=True)
class EntityMention:
    mention: str
    canonical_name: str
    identifier: str | None
    resolved: bool
    entity_type: str
    extraction_confidence: float | None


@dataclass(frozen=True)
class SentimentResult:
    label: str
    score: float
    probabilities: dict[str, float]
    backend: str
    model_id: str


@dataclass(frozen=True)
class EventResult:
    event_type: str
    confidence: float
    matched_terms: tuple[str, ...]
    classifier: str


@dataclass(frozen=True)
class ImpactResult:
    score: int
    factors: dict[str, float | str]
    rationale: str


@dataclass(frozen=True)
class AnalysisResult:
    text: str
    entities: tuple[EntityMention, ...]
    sentiment: SentimentResult
    event: EventResult
    impact: ImpactResult


@dataclass(frozen=True)
class ProcessingResult:
    article_id: int
    status: str
    signal_id: int | None = None
    error: str | None = None
