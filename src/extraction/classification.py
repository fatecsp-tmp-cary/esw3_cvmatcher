"""Explicit clause classification and score-only requirement projection."""

import re
from typing import Any

from src.domain.requirements import key
from src.extraction.context import BACKGROUND_PREFIX, local_bounds, sections
from src.extraction.contracts import SpanEvidence
from src.extraction.spans import entity_bounds
from src.extraction.taxonomy import alias_spans, match_skill

VERSION = "clause-strongest-negation-hedge-conflict-v4"
STRENGTH = {None: 0, "NICE_TO_HAVE": 1, "PREFERRED": 2, "REQUIRED": 3}
CUES = {
    "REQUIRED": (
        r"\b(?:requisitos?|obrigatori[oa]s?|exigid[oa]s?|exigimos|exigir|necessari[oa]s?|"
        r"indispensave(?:l|is)|essencia(?:l|is)|minim[oa]s?|required|requirements?|must|"
        r"mandatory|essential|minimum|need(?:ed|s)?|necessary)\b"
    ),
    "PREFERRED": (
        r"\b(?:desejave(?:l|is)|preferencia(?:l|is)|preferencia|preferencialmente|"
        r"diferencia(?:l|is)|valorizad[oa]s?|preferred|preferably|desirable)\b"
    ),
    "NICE_TO_HAVE": (
        r"\b(?:opciona(?:l|is)|bonus|plus|pontos? extras?|"
        r"nice[\s_–—-]+to[\s_–—-]+have|optional)\b"
    ),
}
HEDGE = re.compile(
    r"\b(?:maybe|perhaps|might|may|could|would|talvez|pode|podem|poderia[m]?|seria[m]?)\b"
    r"[^.;!?\n]{0,65}?\b(?:useful|needed|required|necessary|helpful|plus|need|"
    r"util|uteis|necessari[oa]s?|precisar|bom|boa|diferencial)\b"
)
NEGATION = re.compile(r"\b(?:not|no|never|without|nao|sem|dispensad[oa])\b")
AMBIGUOUS = re.compile(r"\b(?:unclear|uncertain|ambiguous|incert[oa]|ambigu[oa])\b")
ANY_CUE = re.compile("|".join(f"(?:{p})" for p in (*CUES.values(), HEDGE.pattern)), re.I)


def _cue(text: str):
    return ANY_CUE.search(key(text))


def _local(text: str, start: int, end: int):
    left, right = local_bounds(text, start, end, _cue)
    context = key(text[left:right])
    hedges = list(HEDGE.finditer(context))
    strengths = []
    negated = False
    for name, pattern in CUES.items():
        for cue in re.finditer(pattern, context):
            if any(h.start() <= cue.start() < h.end() for h in hedges):
                continue
            prefix = context[: cue.start()]
            # Attach negation to this predicate, never every entity on a line.
            prefix = re.split(r"\b(?:but|and|mas)\b|,", prefix)[-1]
            negations = list(NEGATION.finditer(prefix))
            if negations and not re.search(r"\b(?:not only|nao (?:so|somente|apenas))\b", prefix):
                negated = True
            else:
                strengths.append(name)
    mention = key(text[start:end])
    if re.search(r"\b(?:without|no|sem|not|nao)\s+" + re.escape(mention) + r"\b", context):
        negated = True
        strengths = []
    strengths.extend("NICE_TO_HAVE" for h in hedges if not NEGATION.search(context[: h.start()]))
    if AMBIGUOUS.search(context):
        return None, negated, bool(strengths), context
    strength = max(strengths, key=STRENGTH.__getitem__, default=None)
    conflict = len(set(strengths)) > 1 or (negated and bool(strengths))
    return strength, negated, conflict, context


def classify(text: str, start: int, end: int) -> str | None:
    """Classify a mention with local precedence and section fallback only."""
    strength, negated, _, context = _local(text, start, end)
    if strength is not None or negated or AMBIGUOUS.search(context):
        return strength
    section = next((s for s in sections(text) if s.start <= start < s.end), None)
    if section and section.kind == "requirements":
        return _local(section.heading, 0, len(section.heading))[0]
    return None


def _cue_only(value):
    remaining = key(value)
    for pattern in CUES.values():
        remaining = re.sub(pattern, "", remaining)
    remaining = re.sub(r"\b(?:is|are|be|e|sao|a|an|um|uma|not|no|nao)\b", "", remaining)
    return not remaining.strip(" :-,./")


def annotate_spans(text, evidence):
    """Annotate detections in place; return selected, consolidated requirements.

    Suppressed occurrences remain in the original evidence list. Projection keeps
    the strongest actual occurrence, never promotes a negated span. Approximation
    and conflict flags cannot authorize mandatory satisfaction or exclusion.
    """
    section_rows = sections(text)
    existing = {entity_bounds(text, row["start"], row["end"]) for row in evidence}
    for start, end, label in alias_spans(text):
        if (start, end) not in existing:
            row = SpanEvidence(start, end, label, 1.0).serialize(text)
            row["detection_source"] = "exact_alias"
            evidence.append(row)
            existing.add((start, end))
    groups: dict[str, list[dict[str, Any]]] = {}
    for item in evidence:
        item.setdefault("detection_source", "model")
        item.setdefault("detected_start", item["start"])
        item.setdefault("detected_end", item["end"])
        start, end = entity_bounds(text, item["start"], item["end"])
        item["start"], item["end"] = start, end
        value = text[start:end]
        match = match_skill(value)
        concept = key(match.name if match else value)
        strength, negated, conflict, context = _local(text, start, end)
        section = next((s for s in section_rows if s.start <= start < s.end), None)
        ignored = bool(
            not value
            or _cue_only(value)
            or (section and section.kind in {"background", "heading"})
            or BACKGROUND_PREFIX.search(context)
            or key(value)
            in {"experience", "experiencia", "skill", "skills", "requisito", "requisitos"}
        )
        if (
            strength is None
            and not negated
            and not AMBIGUOUS.search(context)
            and section
            and section.kind == "requirements"
        ):
            strength = _local(section.heading, 0, len(section.heading))[0]
        selected = not ignored and bool(
            strength
            or negated
            or AMBIGUOUS.search(context)
            or (section and section.kind == "requirements")
        )
        item.update(
            requirement_class=None if ignored else strength,
            negated=negated,
            conflicting=conflict,
            approximate_match=bool(match and match.approximate),
            requirement_selected=False,
            exclusion_safe=False,
        )
        if match:
            item["matched_skill"] = match.name
            if not match.approximate:
                item["canonical_skill"] = match.name
        if selected:
            groups.setdefault(concept, []).append(item)
    output = []
    for rows in groups.values():
        strengths = {r["requirement_class"] for r in rows if not r["negated"]}
        conflicting = (
            any(r["conflicting"] for r in rows)
            or len(strengths - {None}) > 1
            or (any(r["negated"] for r in rows) and bool(strengths - {None}))
        )
        for row in rows:
            row["conflicting"] = conflicting
        winner = min(
            rows,
            key=lambda r: (-STRENGTH[r["requirement_class"]], r["start"], r["end"], r["label"]),
        )
        winner["requirement_selected"] = True
        output.append(winner)
    return sorted(output, key=lambda r: (r["start"], r["end"]))
