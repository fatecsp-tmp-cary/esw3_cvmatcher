"""Local extraction boundary and exact character offsets into cleaned job text."""

import math
from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True, slots=True)
class TextChunk:
    start: int
    end: int
    text: str


def chunks(text: str, *, size: int = 1200, overlap: int = 200) -> tuple[TextChunk, ...]:
    """Cover all characters with bounded, overlapping windows, without truncation."""
    if size <= 0 or overlap < 0 or overlap >= size:
        raise ValueError("Invalid chunk policy")
    result = []
    start = 0
    while start < len(text):
        end = min(start + size, len(text))
        result.append(TextChunk(start, end, text[start:end]))
        if end == len(text):
            break
        start = end - overlap
    return tuple(result)


@dataclass(frozen=True, slots=True)
class SpanEvidence:
    start: int
    end: int
    label: str
    confidence: float

    def serialize(self, text: str) -> dict[str, object]:
        if (
            type(self.start) is not int
            or type(self.end) is not int
            or not 0 <= self.start < self.end <= len(text)
            or not isinstance(self.label, str)
            or not self.label.strip()
            or len(self.label) > 100
            or isinstance(self.confidence, bool)
            or not isinstance(self.confidence, (int, float))
            or not math.isfinite(self.confidence)
            or not 0 <= self.confidence <= 1
        ):
            raise ValueError("Invalid span evidence")
        # Span labels/confidence never establish mandatory classification.
        return {
            "start": self.start,
            "end": self.end,
            "label": self.label,
            "confidence": self.confidence,
            "requirement_class": None,
        }


class LocalExtractor(Protocol):
    def extract(self, text: str) -> list[SpanEvidence]:
        """Extract from cleaned title + newline + description using a pinned local model."""
