import importlib.util
import math
import re
from collections.abc import Callable

from app.nlp.contracts import SentimentResult


class SentimentInferenceError(RuntimeError):
    pass


class UnavailableSentimentAnalyzer:
    def __init__(self, reason: str) -> None:
        self.reason = reason

    def analyze(self, _text: str) -> SentimentResult:
        raise SentimentInferenceError(self.reason)


class HeuristicSentimentAnalyzer:
    """Deterministic local fallback, explicitly labelled as a heuristic."""

    positive_terms = frozenset({"gain", "gains", "growth", "profit", "strong", "positive", "improved", "record", "beat", "up"})
    negative_terms = frozenset({"loss", "losses", "decline", "weak", "negative", "default", "missed", "downgrade", "crisis", "down", "risk"})

    def __init__(self, model_id: str = "heuristic-v1") -> None:
        self.model_id = model_id

    def analyze(self, text: str) -> SentimentResult:
        tokens = re.findall(r"[a-z]+", text.casefold())
        positive = sum(token in self.positive_terms for token in tokens)
        negative = sum(token in self.negative_terms for token in tokens)
        denominator = max(positive + negative, 1)
        score = max(-1.0, min(1.0, (positive - negative) / denominator))
        label = "positive" if score > 0.1 else "negative" if score < -0.1 else "neutral"
        probabilities = {
            "positive": max(score, 0.0),
            "negative": max(-score, 0.0),
            "neutral": 1.0 - abs(score),
        }
        return SentimentResult(label, score, probabilities, "heuristic", self.model_id)


class FinBertSentimentAnalyzer:
    def __init__(
        self,
        model_id: str = "ProsusAI/finbert",
        device: str = "cpu",
        allow_download: bool = False,
        classifier: Callable[..., object] | None = None,
    ) -> None:
        self.model_id = model_id
        if classifier is not None:
            self._classifier = classifier
            return
        if importlib.util.find_spec("transformers") is None:
            raise SentimentInferenceError("FinBERT requires the optional 'transformers' package")
        try:
            from transformers import pipeline

            kwargs: dict[str, object] = {"task": "text-classification", "model": model_id, "device": device}
            if not allow_download:
                kwargs["local_files_only"] = True
            self._classifier = pipeline(**kwargs)
        except Exception as exc:  # model loading errors must be surfaced, not replaced by guesses
            raise SentimentInferenceError(f"Unable to load FinBERT model '{model_id}'") from exc

    def analyze(self, text: str) -> SentimentResult:
        try:
            raw = self._classifier(text, top_k=None, truncation=True, max_length=512)
        except Exception as exc:
            raise SentimentInferenceError("FinBERT inference failed") from exc
        if raw and isinstance(raw, list) and isinstance(raw[0], list):
            raw = raw[0]
        if not isinstance(raw, list):
            raise SentimentInferenceError("FinBERT returned an invalid result")
        probabilities: dict[str, float] = {}
        for item in raw:
            if not isinstance(item, dict) or "label" not in item or "score" not in item:
                raise SentimentInferenceError("FinBERT returned an invalid label result")
            label = str(item["label"]).strip().casefold()
            if label not in {"positive", "negative", "neutral"}:
                raise SentimentInferenceError(f"Unsupported FinBERT label: {label}")
            score = float(item["score"])
            if not math.isfinite(score) or not 0 <= score <= 1:
                raise SentimentInferenceError("FinBERT returned an invalid probability")
            probabilities[label] = score
        if set(probabilities) != {"positive", "negative", "neutral"}:
            raise SentimentInferenceError("FinBERT did not return all three verified labels")
        total = sum(probabilities.values())
        if total <= 0:
            raise SentimentInferenceError("FinBERT returned zero total probability")
        probabilities = {key: value / total for key, value in probabilities.items()}
        label = max(probabilities, key=probabilities.get)
        score = probabilities["positive"] - probabilities["negative"]
        return SentimentResult(label, score, probabilities, "finbert", self.model_id)
