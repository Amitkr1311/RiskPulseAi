import re

from app.nlp.contracts import EventResult

EVENT_TYPES = (
    "geopolitical",
    "macroeconomic",
    "credit_event",
    "merger_acquisition",
    "earnings",
    "regulatory",
    "product_launch",
    "market_crash",
    "company_performance",
    "other",
)

EVENT_PATTERNS: dict[str, tuple[str, ...]] = {
    "geopolitical": ("geopolitical", "sanctions", "conflict", "war", "supply-chain disruption"),
    "macroeconomic": ("central bank", "interest rate", "inflation", "recession", "monetary policy"),
    "credit_event": ("default", "missed payment", "debt restructuring", "credit downgrade", "bankruptcy"),
    "merger_acquisition": ("merger", "acquisition", "takeover", "buyout"),
    "earnings": ("earnings", "quarterly results", "financial results", "guidance"),
    "regulatory": ("regulator", "regulatory", "fine", "compliance", "new rule"),
    "product_launch": ("product launch", "new product", "launches", "unveiled"),
    "market_crash": ("market crash", "market collapse", "sell-off", "plunge", "crash"),
    "company_performance": ("revenue", "profit", "operating income", "sales growth", "performance"),
}


class RuleBasedEventClassifier:
    def classify(self, text: str) -> EventResult:
        normalized = text.casefold()
        candidates: list[tuple[int, str, tuple[str, ...]]] = []
        for event_type, patterns in EVENT_PATTERNS.items():
            matched = tuple(term for term in patterns if re.search(rf"(?<!\w){re.escape(term)}(?!\w)", normalized))
            if matched:
                candidates.append((len(matched), event_type, matched))
        if not candidates:
            return EventResult("other", 0.15, (), "rules-v1")
        count, event_type, matched = max(candidates, key=lambda item: (item[0], item[1]))
        confidence = min(0.99, 0.35 + count * 0.15)
        return EventResult(event_type, confidence, matched, "rules-v1")
