import html
import re
from dataclasses import dataclass


class TextProcessingError(ValueError):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code


@dataclass(frozen=True)
class PreprocessedText:
    text: str


def preprocess_text(title: str, text: str, max_chars: int = 12_000) -> PreprocessedText:
    combined = f"{title}. {text}" if title else text
    cleaned = html.unescape(re.sub(r"<[^>]+>", " ", combined or ""))
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    if not cleaned:
        raise TextProcessingError("empty_text", "Article has no analyzable text")
    if len(cleaned) > max_chars:
        raise TextProcessingError("text_too_long", f"Article exceeds the {max_chars}-character limit")
    alphabetic = sum(character.isascii() and character.isalpha() for character in cleaned)
    if alphabetic < 3 or alphabetic / max(len(cleaned), 1) < 0.15:
        raise TextProcessingError("unsupported_language", "Article language is not supported by this pipeline")
    return PreprocessedText(text=cleaned)
