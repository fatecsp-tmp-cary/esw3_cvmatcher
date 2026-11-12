"""Conservative contextual classification of local-model spans, never exclusion."""

import re

from src.domain.requirements import key
from src.extraction.taxonomy import canonical_skill

VERSION = "explicit-context-required-preferred-optional-v1"
CUES = {
    "REQUIRED": (
        r"\b(?:requisitos?|obrigatorios?|obrigatorias?|exigid[oa]s?|required|"
        r"requirements?|must|required skills)\b"
    ),
    "PREFERRED": r"\b(?:desejaveis|desejavel|preferencial|preferencia|preferred|desirable)\b",
    "NICE_TO_HAVE": (
        r"\b(?:diferencia(?:l|is)|opciona(?:l|is)|bonus|"
        r"nice[\s_–—-]+to[\s_–—-]+have|optional)\b"
    ),
}
UNCERTAIN = re.compile(r"\b(?:nao|sem|not|no|without|uncertain|talvez|incerto|unclear)\b")


def classify(text: str, start: int, end: int) -> str | None:
    """Use explicit sentence/section cues; any negation/conflict stays unknown."""
    before = text[:start]
    line_start = before.rfind("\n") + 1
    line_end = text.find("\n", end)
    if line_end < 0:
        line_end = len(text)
    line = key(text[line_start:line_end])
    if UNCERTAIN.search(line):
        return None
    found = {name for name, pattern in CUES.items() if re.search(pattern, line)}
    if not found:
        previous = before[:line_start].splitlines()
        for heading in reversed(previous):
            heading = heading.strip().lstrip("# ").rstrip(":")
            if not heading:
                continue
            # An unrelated line breaks heading attribution instead of leaking
            # mandatory scope across arbitrary sections.
            if len(heading.split()) <= 4 and not UNCERTAIN.search(key(heading)):
                found = {
                    name for name, pattern in CUES.items() if re.fullmatch(pattern, key(heading))
                }
            break
    return next(iter(found)) if len(found) == 1 else None


def annotate_spans(text, evidence):
    """One pure classification policy shared by storage and offline evaluation."""
    strengths: dict[str, set[str]] = {}
    negated = set()
    rows = []
    for item in evidence:
        value = text[item["start"] : item["end"]]
        name = canonical_skill(value)
        concept = name or key(value)
        strength = classify(text, item["start"], item["end"])
        line_start = text.rfind("\n", 0, item["start"]) + 1
        line_end = text.find("\n", item["end"])
        line = text[line_start : line_end if line_end >= 0 else len(text)]
        if UNCERTAIN.search(key(line)):
            negated.add(concept)
        if strength is not None:
            strengths.setdefault(concept, set()).add(strength)
        rows.append((item, name, concept, strength))
    for item, name, concept, strength in rows:
        if len(strengths.get(concept, set())) > 1 or concept in negated:
            strength = None
        item["requirement_class"] = strength
        if name:
            item["canonical_skill"] = name
    return evidence
