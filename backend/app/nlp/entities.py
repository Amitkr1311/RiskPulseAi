import json
import re
from pathlib import Path

from app.nlp.contracts import EntityMention


DEFAULT_ENTITY_ALIASES = [
    {"canonical_name": "Apple", "aliases": ["Apple", "Apple Inc"], "entity_type": "organization"},
    {"canonical_name": "Microsoft", "aliases": ["Microsoft", "Microsoft Corporation"], "entity_type": "organization"},
    {"canonical_name": "Tesla", "aliases": ["Tesla", "Tesla Inc"], "entity_type": "organization"},
    {
        "canonical_name": "Reserve Bank of India",
        "aliases": ["RBI", "Reserve Bank of India"],
        "entity_type": "organization",
    },
    {"canonical_name": "Federal Reserve", "aliases": ["Federal Reserve", "Fed"], "entity_type": "organization"},
    {"canonical_name": "Government of India", "aliases": ["Government of India"], "entity_type": "organization"},
]


def load_aliases(path: str | None = None) -> list[dict[str, object]]:
    if path:
        alias_path = Path(path)
        if not alias_path.is_absolute():
            alias_path = Path(__file__).resolve().parents[2] / alias_path
        if alias_path.exists():
            try:
                value = json.loads(alias_path.read_text(encoding="utf-8"))
                if isinstance(value, list):
                    return value
            except (OSError, json.JSONDecodeError):
                pass
    return DEFAULT_ENTITY_ALIASES


class AliasEntityExtractor:
    """Conservative alias extraction; unknown identifiers are never inferred."""

    _generic_pattern = re.compile(
        r"\b(?:[A-Z][A-Za-z&.-]+(?:\s+[A-Z][A-Za-z&.-]+){0,3}\s+)"
        r"(?:Bank|Corporation|Corp|Inc|Ltd|Holdings|Group)\b"
    )

    def __init__(self, aliases: list[dict[str, object]] | None = None) -> None:
        self.aliases = aliases or DEFAULT_ENTITY_ALIASES
        self._patterns = []
        for item in self.aliases:
            canonical = str(item.get("canonical_name", "")).strip()
            if not canonical:
                continue
            for alias in item.get("aliases", []):
                alias_text = str(alias).strip()
                if alias_text:
                    self._patterns.append(
                        (
                            re.compile(rf"(?<!\w){re.escape(alias_text)}(?!\w)", re.IGNORECASE),
                            canonical,
                            str(item.get("entity_type", "organization")),
                        )
                    )
        self._patterns.sort(key=lambda item: len(item[0].pattern), reverse=True)

    def extract(self, text: str) -> tuple[EntityMention, ...]:
        matches: list[tuple[int, int, EntityMention]] = []
        for pattern, canonical, entity_type in self._patterns:
            for match in pattern.finditer(text):
                matches.append(
                    (
                        match.start(),
                        match.end(),
                        EntityMention(
                            mention=match.group(0),
                            canonical_name=canonical,
                            identifier=None,
                            resolved=True,
                            entity_type=entity_type,
                            extraction_confidence=1.0,
                        ),
                    )
                )
        for match in self._generic_pattern.finditer(text):
            matches.append(
                (
                    match.start(),
                    match.end(),
                    EntityMention(
                        mention=match.group(0),
                        canonical_name=match.group(0),
                        identifier=None,
                        resolved=False,
                        entity_type="organization",
                        extraction_confidence=None,
                    ),
                )
            )

        selected: list[EntityMention] = []
        occupied: list[tuple[int, int]] = []
        seen: set[tuple[str, str]] = set()
        for start, end, entity in sorted(matches, key=lambda item: (item[0], -(item[1] - item[0]))):
            if any(start < other_end and end > other_start for other_start, other_end in occupied):
                continue
            key = (entity.canonical_name.casefold(), entity.mention.casefold())
            if key in seen:
                continue
            seen.add(key)
            occupied.append((start, end))
            selected.append(entity)
        return tuple(selected)
