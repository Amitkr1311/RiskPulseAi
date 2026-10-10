import pytest

from app.nlp.entities import AliasEntityExtractor
from app.nlp.events import RuleBasedEventClassifier
from app.nlp.impact import ImpactScorer
from app.nlp.preprocessing import TextProcessingError, preprocess_text
from app.nlp.sentiment import FinBertSentimentAnalyzer, HeuristicSentimentAnalyzer, SentimentInferenceError


def test_heuristic_sentiment_covers_positive_negative_and_neutral() -> None:
    analyzer = HeuristicSentimentAnalyzer()
    assert analyzer.analyze("strong profit growth").label == "positive"
    assert analyzer.analyze("default and severe losses").label == "negative"
    neutral = analyzer.analyze("the company held a meeting")
    assert neutral.label == "neutral"
    assert neutral.score == 0
    assert sum(neutral.probabilities.values()) == pytest.approx(1)


def test_finbert_mapping_uses_verified_three_class_formula() -> None:
    def fake_classifier(*args, **kwargs):
        return [
            {"label": "positive", "score": 0.70},
            {"label": "negative", "score": 0.20},
            {"label": "neutral", "score": 0.10},
        ]

    result = FinBertSentimentAnalyzer(classifier=fake_classifier).analyze("earnings improved")
    assert result.label == "positive"
    assert result.score == pytest.approx(0.5)
    assert result.probabilities["positive"] == pytest.approx(0.7)


def test_finbert_rejects_unverified_or_incomplete_output() -> None:
    analyzer = FinBertSentimentAnalyzer(classifier=lambda *_args, **_kwargs: [{"label": "LABEL_0", "score": 1}])
    with pytest.raises(SentimentInferenceError):
        analyzer.analyze("text")


def test_preprocessing_rejects_empty_and_excessively_long_text() -> None:
    with pytest.raises(TextProcessingError, match="no analyzable"):
        preprocess_text("", "")
    with pytest.raises(TextProcessingError, match="exceeds"):
        preprocess_text("title", "a" * 20, max_chars=10)


def test_entities_preserve_mentions_without_inventing_identifiers() -> None:
    entities = AliasEntityExtractor().extract("RBI reviewed Tesla and Acme Corporation.")
    assert [entity.canonical_name for entity in entities] == ["Reserve Bank of India", "Tesla", "Acme Corporation"]
    assert all(entity.identifier is None for entity in entities)
    assert entities[-1].resolved is False


def test_event_categories_and_fallback_are_deterministic() -> None:
    classifier = RuleBasedEventClassifier()
    assert classifier.classify("The central bank changed interest rate policy").event_type == "macroeconomic"
    assert classifier.classify("The borrower missed payment and entered default").event_type == "credit_event"
    assert classifier.classify("A merger and acquisition was announced").event_type == "merger_acquisition"
    assert classifier.classify("A quiet administrative notice").event_type == "other"


def test_impact_score_is_bounded_and_explainable() -> None:
    sentiment = HeuristicSentimentAnalyzer().analyze("default and losses")
    event = RuleBasedEventClassifier().classify("borrower default and missed payment")
    scorer = ImpactScorer()
    first = scorer.score("news", event, sentiment)
    second = scorer.score("news", event, sentiment)
    assert first == second
    assert 1 <= first.score <= 10
    assert "severity" in first.factors
    assert "portfolio_relevance" in first.factors
