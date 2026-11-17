"""Trim grammatical wrappers while retaining exact original Unicode offsets."""

import re

VERSION = "smallest-meaningful-entity-v4"
PREFIX = re.compile(
    r"^(?:(?:registro(?:\s+profissional)?|certifica[cç][aã]o|certification)\s+(?:em\s+|in\s+)?|"
    r"(?:(?:s[oó]lid[oa]s?|bons?|boas?|fortes?|importante|ampla|forte|avan[cç]ad[oa]s?|"
    r"b[aá]sic[oa]s?|good|strong|solid|entry[\s-]+level)\s+)?"
    r"(?:experi[eê]ncias?|experience|conhecimentos?|knowledge|dom[ií]nio|profici[eê]ncia|"
    r"proficiency|familiaridade|familiarity|viv[eê]ncia|habilidades?|skills?)\s+"
    r"(?:(?:avan[cç]ad[oa]s?|b[aá]sic[oa]s?|s[oó]lid[oa]s?|pr[aá]tic[oa]s?|comprovad[oa]s?)\s+)?"
    r"(?:(?:em|com|de|na|no|nas|nos|in|with|of|on)\s+)?|"
    r"(?:senioridade|seniority)\s+)",
    re.I,
)
SUFFIX = re.compile(r"\s+(?:experience|skills?|speaker)$", re.I)


def entity_bounds(text: str, start: int, end: int) -> tuple[int, int]:
    # Never normalize or search a different string to obtain original offsets.
    while start < end and text[start].isspace():
        start += 1
    while end > start and (text[end - 1].isspace() or text[end - 1] in ",;:"):
        end -= 1
    value = text[start:end]
    prefix = PREFIX.match(value)
    if prefix and prefix.end() < len(value):
        start += prefix.end()
    suffix = SUFFIX.search(text[start:end])
    if suffix and suffix.start() > 0:
        end = start + suffix.start()
    return start, end
