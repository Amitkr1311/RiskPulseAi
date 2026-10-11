from collections import Counter
from typing import Iterable

SENTIMENT_LABELS = ("negative", "neutral", "positive")


class MetricInputError(ValueError):
    pass


def normalize_label(value: object) -> str:
    if isinstance(value, bool):
        raise MetricInputError("boolean labels are invalid")
    if isinstance(value, int):
        mapping = {-1: "negative", 0: "neutral", 1: "positive"}
        if value in mapping:
            return mapping[value]
    label = str(value).strip().casefold()
    if label in {"-1", "0", "1"}:
        return {"-1": "negative", "0": "neutral", "1": "positive"}[label]
    aliases = {"neg": "negative", "neu": "neutral", "pos": "positive"}
    label = aliases.get(label, label)
    if label not in SENTIMENT_LABELS:
        raise MetricInputError(f"unsupported sentiment label: {value}")
    return label


def evaluate_predictions(references: Iterable[object], predictions: Iterable[object]) -> dict[str, object]:
    reference_labels = [normalize_label(value) for value in references]
    prediction_labels = [normalize_label(value) for value in predictions]
    if not reference_labels:
        raise MetricInputError("evaluation dataset is empty")
    if len(reference_labels) != len(prediction_labels):
        raise MetricInputError("reference and prediction lengths differ")

    confusion = {actual: {predicted: 0 for predicted in SENTIMENT_LABELS} for actual in SENTIMENT_LABELS}
    for actual, predicted in zip(reference_labels, prediction_labels, strict=True):
        confusion[actual][predicted] += 1

    total = len(reference_labels)
    accuracy = sum(actual == predicted for actual, predicted in zip(reference_labels, prediction_labels, strict=True)) / total
    per_class: dict[str, dict[str, float]] = {}
    f1_values: list[float] = []
    for label in SENTIMENT_LABELS:
        true_positive = confusion[label][label]
        predicted_total = sum(confusion[actual][label] for actual in SENTIMENT_LABELS)
        actual_total = sum(confusion[label].values())
        precision = true_positive / predicted_total if predicted_total else 0.0
        recall = true_positive / actual_total if actual_total else 0.0
        f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
        per_class[label] = {"precision": precision, "recall": recall, "f1": f1}
        f1_values.append(f1)

    return {
        "accuracy": accuracy,
        "macro_f1": sum(f1_values) / len(f1_values),
        "per_class": per_class,
        "confusion_matrix": confusion,
        "class_distribution": dict(Counter(reference_labels)),
        "evaluated_examples": total,
    }
