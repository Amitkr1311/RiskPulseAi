import csv
import json
import random
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Iterable

from app.core.config import Settings
from app.nlp.sentiment import SentimentInferenceError
from research.metrics import SENTIMENT_LABELS, evaluate_predictions, normalize_label

DATASET_NAME = "takala/financial_phrasebank"
DATASET_LICENSE = "CC-BY-NC-SA-3.0"
DEFAULT_CONFIG = "sentences_allagree"


class PhraseBankUnavailableError(RuntimeError):
    pass


@dataclass(frozen=True)
class PhraseExample:
    sentence: str
    label: str


def _example_from_record(record: dict[str, Any]) -> PhraseExample:
    sentence = record.get("sentence") or record.get("text")
    if not isinstance(sentence, str) or not sentence.strip():
        raise PhraseBankUnavailableError("PhraseBank record has no sentence text")
    if "label" not in record and "sentiment" not in record:
        raise PhraseBankUnavailableError("PhraseBank record has no label")
    try:
        label = normalize_label(record.get("label", record.get("sentiment")))
    except ValueError as exc:
        raise PhraseBankUnavailableError(str(exc)) from exc
    return PhraseExample(sentence.strip(), label)


def _load_local(path: Path) -> list[PhraseExample]:
    if path.is_dir():
        candidates = [path / "data.csv", path / "train.csv", path / "financial_phrasebank.csv"]
        path = next((candidate for candidate in candidates if candidate.exists()), path)
    if not path.exists() or not path.is_file():
        raise PhraseBankUnavailableError(f"local PhraseBank path does not exist: {path}")
    try:
        if path.suffix.casefold() == ".csv":
            with path.open("r", encoding="utf-8-sig", newline="") as handle:
                return [_example_from_record(row) for row in csv.DictReader(handle)]
        if path.suffix.casefold() in {".json", ".jsonl"}:
            if path.suffix.casefold() == ".jsonl":
                records = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
            else:
                records = json.loads(path.read_text(encoding="utf-8"))
            if isinstance(records, dict) and "data" in records:
                records = records["data"]
            if not isinstance(records, list):
                raise PhraseBankUnavailableError("local PhraseBank JSON must contain a list of records")
            return [_example_from_record(record) for record in records]
    except (OSError, UnicodeError, json.JSONDecodeError, csv.Error) as exc:
        raise PhraseBankUnavailableError(f"unable to read local PhraseBank data: {path}") from exc
    raise PhraseBankUnavailableError("local PhraseBank path must be CSV, JSON, or JSONL")


def load_examples(config: str = DEFAULT_CONFIG, local_path: str | None = None) -> list[PhraseExample]:
    if local_path:
        examples = _load_local(Path(local_path))
    else:
        try:
            from datasets import load_dataset
        except ImportError as exc:
            raise PhraseBankUnavailableError("install the research extras to download Financial PhraseBank: pip install -r requirements-research.txt") from exc
        try:
            dataset = load_dataset(DATASET_NAME, config)
            records: Iterable[dict[str, Any]] = dataset["train"]
            examples = [_example_from_record(dict(record)) for record in records]
        except Exception as exc:
            raise PhraseBankUnavailableError(f"unable to load {DATASET_NAME}/{config}: {exc}") from exc
    if not examples:
        raise PhraseBankUnavailableError("Financial PhraseBank contains no examples")
    return examples


def evaluate_phrasebank(
    settings: Settings,
    *,
    config: str = DEFAULT_CONFIG,
    local_path: str | None = None,
    seed: int = 42,
) -> dict[str, object]:
    random.seed(seed)
    examples = load_examples(config=config, local_path=local_path)
    try:
        from app.nlp.service import build_sentiment_analyzer

        analyzer = build_sentiment_analyzer(settings)
        predictions = [analyzer.analyze(example.sentence).label for example in examples]
    except SentimentInferenceError as exc:
        raise PhraseBankUnavailableError(str(exc)) from exc
    metrics = evaluate_predictions((example.label for example in examples), predictions)
    model_id = getattr(analyzer, "model_id", settings.nlp_sentiment_model_id)
    backend = getattr(analyzer, "model_id", "").casefold() if settings.nlp_sentiment_backend == "heuristic" else settings.nlp_sentiment_backend
    return {
        "schema_version": "1.0",
        "dataset": {
            "name": DATASET_NAME,
            "configuration": config,
            "source": "local path" if local_path else "Hugging Face Hub",
            "license": DATASET_LICENSE,
        },
        "model": {
            "backend": settings.nlp_sentiment_backend,
            "identifier": model_id,
            "label_mapping": {"negative": "negative", "neutral": "neutral", "positive": "positive"},
            "score_definition": "positive_probability - negative_probability for FinBERT; heuristic score for heuristic backend",
            "runtime_marker": backend,
        },
        "evaluation_date": datetime.now(UTC).date().isoformat(),
        "seed": seed,
        "metrics": metrics,
        "limitations": [
            "Financial PhraseBank contains sentence-level examples and does not represent the full structure of long news articles.",
            "This evaluation does not train or fine-tune the production sentiment model.",
            "Metrics are not evidence of investment performance or causal market prediction.",
        ],
    }


def render_summary(report: dict[str, object]) -> str:
    metrics = report["metrics"]
    assert isinstance(metrics, dict)
    per_class = metrics["per_class"]
    assert isinstance(per_class, dict)
    lines = [
        "RiskPulse AI sentiment evaluation",
        f"Dataset: {report['dataset']['name']} / {report['dataset']['configuration']}",
        f"Model: {report['model']['identifier']} ({report['model']['backend']})",
        f"Examples: {metrics['evaluated_examples']}",
        f"Accuracy: {metrics['accuracy']:.4f}",
        f"Macro-F1: {metrics['macro_f1']:.4f}",
        "Per-class metrics:",
    ]
    for label in SENTIMENT_LABELS:
        values = per_class[label]
        lines.append(f"  {label}: precision={values['precision']:.4f} recall={values['recall']:.4f} f1={values['f1']:.4f}")
    lines.append("Confusion matrix (actual -> predicted):")
    for actual in SENTIMENT_LABELS:
        lines.append(f"  {actual}: {metrics['confusion_matrix'][actual]}")
    return "\n".join(lines) + "\n"
