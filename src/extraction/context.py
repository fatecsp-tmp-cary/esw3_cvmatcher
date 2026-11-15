"""Offset-preserving sentence/clause and section context; no text rewriting."""

import re
from dataclasses import dataclass

from src.domain.requirements import key

VERSION = "sentence-clause-sections-v3"
REQUIREMENT_HEADINGS = {
    "requirements",
    "requirement",
    "required",
    "required skills",
    "minimum requirements",
    "qualifications",
    "minimum qualifications",
    "requisitos",
    "requisitos obrigatorios",
    "qualificacoes",
    "o que buscamos",
    "o que esperamos",
    "perfil desejado",
    "what you'll need",
    "what you’ll need",
    "what we're looking for",
    "what we’re looking for",
    "preferred",
    "preferred qualifications",
    "desirable",
    "desejavel",
    "desejaveis",
    "diferencial",
    "diferenciais",
    "nice to have",
    "nice-to-have",
    "bonus",
    "bonus points",
    "optional",
    "opcional",
    "opcionais",
}
BACKGROUND_HEADINGS = {
    "benefits",
    "beneficios",
    "what we offer",
    "o que oferecemos",
    "we offer",
    "about us",
    "about the company",
    "company",
    "company background",
    "our story",
    "sobre nos",
    "sobre a empresa",
    "a empresa",
    "responsibilities",
    "responsabilidades",
    "atividades",
    "atribuicoes",
    "how to apply",
    "apply",
    "application instructions",
    "como se candidatar",
    "candidatura",
    "team context",
    "contexto da equipe",
    "other section",
    "outra secao",
}
BACKGROUND_PREFIX = re.compile(
    r"^(?:team context|contexto da equipe|about us|sobre nos|our story|benefits|beneficios|"
    r"how to apply|como se candidatar|application instructions)\s*:"
)
SENTENCE_BREAK = re.compile(r"[.!?](?=\s|$)|[\n;]")
CLAUSE_BREAK = re.compile(r",\s*|\s+(?:and|but|whereas|while|e|mas|por[eé]m|enquanto)\s+", re.I)


@dataclass(frozen=True)
class Section:
    start: int
    end: int
    kind: str
    heading: str


def sections(text: str) -> tuple[Section, ...]:
    """Unknown marked headings terminate scope; missing sections allow local cues."""
    output = []
    offset = 0
    kind, heading = "unsectioned", ""
    has_requirements = any(
        key(line.split(":", 1)[0].strip().strip("#*_ :\t")) in REQUIREMENT_HEADINGS
        for line in text.splitlines()
    )
    for line in text.splitlines(keepends=True):
        stripped = line.strip()
        plain = key(stripped.strip("#*_ :\t"))
        prefix = key(stripped.split(":", 1)[0].strip("#*_ \t"))
        # Sentence-local context labels are handled by BACKGROUND_PREFIX; they
        # must not suppress a later explicit requirement on the same line.
        sentence_label = prefix in {"team context", "contexto da equipe"}
        inline_heading = (
            ":" in stripped
            and not sentence_label
            and (
                prefix in REQUIREMENT_HEADINGS | BACKGROUND_HEADINGS
                or (
                    has_requirements
                    and len(prefix) < 120
                    and bool(re.fullmatch(r"[\w \-]+", prefix))
                )
            )
        )
        if inline_heading:
            plain = prefix
        marked = inline_heading or bool(re.match(r"^#{1,6}\s+", stripped)) or stripped.endswith(":")
        marked |= any(
            stripped.startswith(mark) and stripped.endswith(mark) for mark in ("**", "__")
        )
        is_heading = plain in REQUIREMENT_HEADINGS | BACKGROUND_HEADINGS
        if is_heading or (marked and len(plain) < 120):
            if plain in REQUIREMENT_HEADINGS:
                kind = "requirements"
            elif plain in BACKGROUND_HEADINGS or has_requirements:
                kind = "background"
            else:
                kind = "unsectioned"
            heading = plain
            heading_end = offset + line.index(":") + 1 if inline_heading else offset + len(line)
            output.append(Section(offset, heading_end, "heading", heading))
            if heading_end < offset + len(line):
                output.append(Section(heading_end, offset + len(line), kind, heading))
        else:
            output.append(Section(offset, offset + len(line), kind, heading))
        offset += len(line)
    return tuple(output)


def sentence_bounds(text: str, start: int, end: int) -> tuple[int, int]:
    left, right = 0, len(text)
    for match in SENTENCE_BREAK.finditer(text):
        if match.end() <= start:
            left = match.end()
        elif match.start() >= end:
            right = match.start()
            break
    return left, right


def local_bounds(text: str, start: int, end: int, has_cue) -> tuple[int, int]:
    """Split subject/predicate pairs; keep lists with a shared predicate together."""
    left, right = sentence_bounds(text, start, end)
    for separator in CLAUSE_BREAK.finditer(text, left, right):
        if separator.start() < end and separator.end() > start:
            continue
        before, after = text[left : separator.start()], text[separator.end() : right]
        cue_after = has_cue(after)
        omitted_negation = re.match(
            r"^(?:(?:but|mas|and|e)\s+)?(?:not|nao)\s+(?!(?:only|so|somente|apenas)\b)",
            key(after).strip(),
        )
        subject = key(after)[: cue_after.start()].strip(" :-") if cue_after else ""
        subject = re.sub(
            r"\b(?:is|are|be|e|sao|a|an|um|uma|not|no|nao|foi|definido|como)\b", "", subject
        ).strip()
        if not has_cue(before) or (not omitted_negation and (not cue_after or not subject)):
            continue
        if separator.end() <= start:
            left = separator.end()
        elif separator.start() >= end:
            right = separator.start()
            break
    return left, right
