"""Versioned bilingual skill taxonomy, boundary-safe matching, and bounded typo support."""

import re
import unicodedata
from collections.abc import Iterable, Iterator
from dataclasses import dataclass
from functools import lru_cache

from src.extraction.taxonomy_data import CATEGORY_SPAN_LABELS, TAXONOMY_SPECS

VERSION = "explicit-aliases-single-edit-min5-v5"


def _fold(value: str) -> str:
    if not isinstance(value, str):
        raise TypeError("Skill alias must be text")
    return " ".join(unicodedata.normalize("NFKC", value).casefold().split())


def _fold_ascii(value: str) -> str:
    folded = _fold(value)
    return " ".join(
        "".join(
            ch for ch in unicodedata.normalize("NFKD", folded) if not unicodedata.combining(ch)
        ).split()
    )


CATEGORIES: dict[str, str] = {}
PARENTS: dict[str, str] = {}
SPAN_LABELS: dict[str, str] = {}
_PROSE_ALIASES: dict[str, str] = {}
_LABEL_ALIASES: dict[str, str] = {}
_ALIASES: dict[str, str] = {}

for _spec in TAXONOMY_SPECS:
    CATEGORIES[_spec.canonical_name] = _spec.category
    SPAN_LABELS[_spec.canonical_name] = CATEGORY_SPAN_LABELS.get(_spec.category, "skill")
    if _spec.parent is not None:
        PARENTS[_spec.canonical_name] = _spec.parent

    _canon_folded = _fold(_spec.canonical_name)
    _ALIASES[_canon_folded] = _spec.canonical_name
    if _spec.prose_safe_canonical:
        _PROSE_ALIASES[_canon_folded] = _spec.canonical_name
    else:
        _LABEL_ALIASES[_canon_folded] = _spec.canonical_name

    for _alias in _spec.aliases:
        _fa = _fold(_alias)
        _ALIASES[_fa] = _spec.canonical_name
        _PROSE_ALIASES[_fa] = _spec.canonical_name

    for _alias in _spec.label_only_aliases:
        _fa = _fold(_alias)
        _ALIASES[_fa] = _spec.canonical_name
        _LABEL_ALIASES[_fa] = _spec.canonical_name


def _build_ascii_index(source: dict[str, str]) -> dict[str, str]:
    buckets: dict[str, set[str]] = {}
    for alias, canonical in source.items():
        buckets.setdefault(_fold_ascii(alias), set()).add(canonical)
    return {key: next(iter(vals)) for key, vals in buckets.items() if len(vals) == 1}


_PROSE_ALIASES_ASCII = _build_ascii_index(_PROSE_ALIASES)
_ALIASES_ASCII = _build_ascii_index(_ALIASES)

_PROSE_VARIANTS_BY_CANONICAL: dict[str, frozenset[str]] = {}
_tmp_variants: dict[str, set[str]] = {}
for _alias, _canonical in _PROSE_ALIASES.items():
    _norm = _canonical.casefold()
    _tmp_variants.setdefault(_norm, set()).add(_alias)
    _ascii = _fold_ascii(_alias)
    if _ascii != _alias and _PROSE_ALIASES_ASCII.get(_ascii) == _canonical:
        _tmp_variants[_norm].add(_ascii)
_PROSE_VARIANTS_BY_CANONICAL = {k: frozenset(v) for k, v in _tmp_variants.items()}
_TAXONOMY_CANONICAL_FOLDS: frozenset[str] = frozenset(k.casefold() for k in CATEGORIES)

_PROSE_SPAN_PATTERN = re.compile(
    r"(?<![\w.+#-])(?:"
    + "|".join(
        re.escape(alias).replace(r"\ ", r"\s+")
        for alias in sorted(_PROSE_ALIASES, key=lambda item: (-len(item), item))
    )
    + r")(?![\w+#-])",
    re.I,
)

# Precompiled typo buckets from prose-safe aliases only so common-word label aliases
# (e.g. "shell", "tempo", "sonar") never cause 1-edit false positives in free text.
_DEFAULT_BUCKETS: dict[tuple[int, str], list[tuple[str, str]]] = {}
for _alias, _canonical in _PROSE_ALIASES.items():
    if len(_alias) >= 5:
        _DEFAULT_BUCKETS.setdefault((len(_alias), re.sub(r"\w", "", _alias)), []).append(
            (_alias, _canonical)
        )
_DEFAULT_WIDTHS: tuple[int, ...] = tuple(sorted({len(alias.split()) for alias in _PROSE_ALIASES}))

_LEADING_WRAPPER = re.compile(
    r"^(?:flu[eê]ncia\s+em|conhecimentos?\s+(?:em|de|no|na)|dom[ií]nio\s+(?:de|em)|"
    r"experi[eê]ncia\s+(?:com|em)|no[cç][oõ]es\s+(?:de|em)|comunica[cç][aã]o\s+em)\s+",
    re.I,
)
_TRAILING_PAREN_TAG = re.compile(
    r"\s*\((?:desej[aá]ve(?:l|is)|diferencia(?:l|is)|obrigat[oó]ri[oa]s?|opcional|"
    r"b[aá]sic[oa]|intermedi[aá]ri[oa](?:\s*/\s*avan[cç]ad[oa])?|avan[cç]ad[oa](?:\s*/\s*fluente)?|"
    r"fluente|t[eé]cnic[oa]|basic|intermediate|advanced|fluent|required|preferred|optional)\)\s*$",
    re.I,
)
_TRAILING_LEVEL = re.compile(
    r"(?:\s+(?:intermedi[aá]ri[oa]\s*(?:/|ou)\s*avan[cç]ad[oa]|"
    r"avan[cç]ad[oa]\s*(?:/|ou)\s*fluente|"
    r"avan[cç]ad[oa]s?|intermedi[aá]ri[oa]s?|b[aá]sic[oa]s?|fluente|t[eé]cnic[oa]|"
    r"profissional|advanced|intermediate|basic|fluent|fluency|proficiency))+$",
    re.I,
)
_ATOMIC_SLASH_SKILLS = frozenset(_ALIASES)


def _exact_lookup(folded: str) -> str | None:
    if (hit := _ALIASES.get(folded)) is not None:
        return hit
    return _ALIASES_ASCII.get(_fold_ascii(folded))


def _strip_qualifiers(value: str) -> str:
    cleaned = _fold(value).rstrip(" .;,:")
    # Preserve canonical dotted names like .NET if trailing dot was stripped accidentally.
    if not cleaned:
        return ""
    while True:
        updated = _TRAILING_PAREN_TAG.sub("", cleaned).strip()
        updated = _TRAILING_LEVEL.sub("", updated).strip()
        updated = _LEADING_WRAPPER.sub("", updated).strip()
        if updated == cleaned:
            break
        cleaned = updated
    return cleaned


def canonical_skill(value: str) -> str | None:
    """Exact/bilingual alias lookup with safe proficiency-wrapper normalization."""
    folded = _fold(value)
    if (hit := _exact_lookup(folded)) is not None:
        return hit
    stripped = _strip_qualifiers(folded)
    if stripped and stripped != folded:
        return _exact_lookup(stripped)
    return None


def resolve_skills(value: str) -> tuple[str, ...]:
    """Resolve a single or compound skill label into deduplicated canonical skill names."""
    if not isinstance(value, str):
        raise TypeError("Skill alias must be text")
    stripped_input = value.strip()
    if not stripped_input:
        return ()
    if (single := canonical_skill(stripped_input)) is not None:
        return (single,)

    # Expand parenthesized groups and compound lists without splitting atomic slash skills.
    parts: list[str] = []
    if "(" in stripped_input or ")" in stripped_input:
        outer = re.sub(r"\([^)]*\)", " ", stripped_input)
        parts.append(outer)
        for inner in re.findall(r"\(([^)]+)\)", stripped_input):
            parts.append(inner)
        # Recover broken semicolon-split fragments such as "Observabilidade (Datadog" or "GCP)".
        if "(" in stripped_input and ")" not in stripped_input:
            head, tail = stripped_input.split("(", 1)
            parts.extend((head, tail))
        elif ")" in stripped_input and "(" not in stripped_input:
            parts.append(stripped_input.rstrip(")"))
    else:
        parts.append(stripped_input)

    resolved: list[str] = []
    seen: set[str] = set()

    def _add(name: str) -> None:
        if name not in seen:
            seen.add(name)
            resolved.append(name)

    for chunk in parts:
        chunk_clean = chunk.strip(" ()[]{};,.")
        if not chunk_clean:
            continue
        if (direct := canonical_skill(chunk_clean)) is not None:
            _add(direct)
            continue
        # Split on comma, conjunctions, and slashes only when the chunk isn't an atomic skill.
        tokens = re.split(r"\s*(?:,|;|\be\b|\band\b|\bou\b|\bor\b)\s*", chunk_clean, flags=re.I)
        for token in tokens:
            token = token.strip(" ()[]{};,.")
            if not token:
                continue
            if (hit := canonical_skill(token)) is not None:
                _add(hit)
                continue
            if (
                _fold_ascii(token) in {"nao relacionais", "nao-relacionais"}
                and "Relational Databases" in seen
            ):
                _add("NoSQL")
                continue
            if "/" in token and _fold(token) not in _ATOMIC_SLASH_SKILLS:
                for sub in token.split("/"):
                    sub = sub.strip(" ()[]{};,.")
                    if sub and (sub_hit := canonical_skill(sub)) is not None:
                        _add(sub_hit)
    return tuple(resolved)


def skill_category(name: str) -> str | None:
    """Return the curated domain category for a canonical skill or alias."""
    canonical = canonical_skill(name) or name
    return CATEGORIES.get(canonical)


def parent_skill(name: str) -> str | None:
    """Return the curated parent canonical skill name if defined."""
    canonical = canonical_skill(name) or name
    return PARENTS.get(canonical)


def alias_spans(text: str) -> Iterator[tuple[int, int, str]]:
    """Supplement model detection with exact explicit prose-safe vocabulary occurrences.

    Match original Unicode directly; no fuzzy-generated offsets or strength.
    """
    for match in _PROSE_SPAN_PATTERN.finditer(text):
        if text[match.end() : match.end() + 3] == "://":
            continue
        prefix = text[max(0, match.start() - 40) : match.start()]
        if re.search(r"https?://\S*$", prefix, re.I):
            continue
        matched_folded = _fold(match.group())
        name = _PROSE_ALIASES.get(matched_folded) or _PROSE_ALIASES_ASCII.get(
            _fold_ascii(matched_folded)
        )
        if name:
            yield match.start(), match.end(), SPAN_LABELS.get(name, "skill")


def one_edit(left: str, right: str) -> bool:
    """At most one insertion/deletion/substitution/adjacent transposition."""
    if left == right:
        return True
    if abs(len(left) - len(right)) > 1:
        return False
    if len(left) == len(right):
        changed = [i for i, (a, b) in enumerate(zip(left, right, strict=True)) if a != b]
        return len(changed) == 1 or (
            len(changed) == 2
            and changed[1] == changed[0] + 1
            and left[changed[0]] == right[changed[1]]
            and left[changed[1]] == right[changed[0]]
        )
    shorter, longer = sorted((left, right), key=len)
    first = next(
        (i for i, (a, b) in enumerate(zip(shorter, longer, strict=False)) if a != b), len(shorter)
    )
    return shorter[first:] == longer[first + 1 :]


@dataclass(frozen=True)
class AliasMatch:
    name: str
    approximate: bool


def match_skill(value: str, *, vocabulary: Iterable[str] = ()) -> AliasMatch | None:
    """Approximation is score-only support, never a new authoritative alias.

    Search the entire project vocabulary before a caller's subset, so a known
    different name or a tie cannot become a typo merely due to retrieval scope.
    Punctuation/word boundaries must agree and both names have at least 5 chars.
    """
    folded = _fold(value)
    if (exact := canonical_skill(folded)) is not None:
        return AliasMatch(exact, False)

    aliases, buckets = _alias_index(vocabulary)
    return _lookup(folded, aliases, buckets)


def _alias_index(
    vocabulary: Iterable[str],
) -> tuple[dict[str, str], dict[tuple[int, str], list[tuple[str, str]]]]:
    extra = [name for name in vocabulary if _fold(name) not in _ALIASES]
    if not extra:
        return _ALIASES, _DEFAULT_BUCKETS
    aliases = dict(_ALIASES)
    buckets = {key: list(items) for key, items in _DEFAULT_BUCKETS.items()}
    for name in extra:
        key = _fold(name)
        resolved = canonical_skill(name) or name
        aliases[key] = resolved
        if len(key) >= 5:
            buckets.setdefault((len(key), re.sub(r"\w", "", key)), []).append((key, resolved))
    return aliases, buckets


def _lookup(
    folded: str,
    aliases: dict[str, str],
    buckets: dict[tuple[int, str], list[tuple[str, str]]],
) -> AliasMatch | None:
    if folded in aliases:
        return AliasMatch(aliases[folded], False)
    if (ascii_hit := _ALIASES_ASCII.get(_fold_ascii(folded))) is not None:
        return AliasMatch(ascii_hit, False)
    stripped = _strip_qualifiers(folded)
    if stripped and stripped != folded:
        if stripped in aliases:
            return AliasMatch(aliases[stripped], False)
        if (stripped_ascii := _ALIASES_ASCII.get(_fold_ascii(stripped))) is not None:
            return AliasMatch(stripped_ascii, False)
    if len(folded) < 5:
        return None
    punctuation = re.sub(r"\w", "", folded)
    candidates = {
        name
        for size in (len(folded) - 1, len(folded), len(folded) + 1)
        for alias, name in buckets.get((size, punctuation), ())
        if one_edit(folded, alias)
    }
    return AliasMatch(candidates.pop(), True) if len(candidates) == 1 else None


def normalize_skill(name: str) -> str:
    """Normalize explicit skill text; unknown input is not classified as a requirement."""
    canonical = canonical_skill(name)
    return canonical.casefold() if canonical is not None else _fold(name)


@lru_cache(maxsize=2048)
def _skill_find_pattern(canonical: str) -> re.Pattern[str]:
    variants = _PROSE_VARIANTS_BY_CANONICAL.get(canonical)
    if variants is None:
        variants = frozenset({canonical})
    return re.compile(
        r"(?<![\w.+#])(?:"
        + "|".join(re.escape(variant) for variant in sorted(variants, key=lambda v: (-len(v), v)))
        + r")(?![\w+#])"
    )


def find_skills(texts: Iterable[str], vocabulary: Iterable[str]) -> set[str]:
    """Return normalized vocabulary skills explicitly mentioned in supplied text.

    Exact aliases plus bounded score-only typo support. This result is never
    sufficient evidence for mandatory satisfaction or candidate exclusion.
    """
    normalized_texts = [
        " ".join(unicodedata.normalize("NFKC", text).casefold().split()) for text in texts
    ]
    if not normalized_texts:
        return set()
    ascii_texts = [_fold_ascii(text) for text in normalized_texts]
    vocab_tuple = tuple(name for name in vocabulary if name.strip())
    known = {normalize_skill(name) for name in vocab_tuple}
    if not known:
        return set()

    found: set[str] = set()
    for canonical in known:
        if canonical in _TAXONOMY_CANONICAL_FOLDS:
            variants = _PROSE_VARIANTS_BY_CANONICAL.get(canonical, frozenset())
        else:
            variants = frozenset({canonical})
        if not variants:
            continue
        # Fast C-level substring prefilter before regex boundary verification.
        if not any(
            variant in text for variant in variants for text in (*normalized_texts, *ascii_texts)
        ):
            continue
        pattern = _skill_find_pattern(canonical)
        if any(pattern.search(text) for text in normalized_texts) or any(
            pattern.search(text) for text in ascii_texts
        ):
            found.add(canonical)

    # Tokenize full names, retaining internal punctuation. Sentence-final full
    # stops are separators, while Node.js and C++ remain single distinct tokens.
    aliases, buckets = _alias_index(vocab_tuple)
    widths = (
        _DEFAULT_WIDTHS
        if aliases is _ALIASES
        else tuple(sorted({len(name.split()) for name in aliases}))
    )
    seen: set[str] = set()
    for text in normalized_texts:
        matches = list(re.finditer(r"\w+(?:[.+#/-]+\w+)*[+#]*", text))
        tokens = [m.group() for m in matches]
        for start in range(len(tokens)):
            for size in widths:
                if start + size > len(tokens):
                    break
                if any(
                    not text[a.end() : b.start()].isspace()
                    for a, b in zip(
                        matches[start : start + size],
                        matches[start + 1 : start + size],
                        strict=False,
                    )
                ):
                    continue
                phrase = " ".join(tokens[start : start + size])
                if phrase in seen:
                    continue
                seen.add(phrase)
                match = _lookup(phrase, aliases, buckets)
                if match and match.approximate and normalize_skill(match.name) in known:
                    found.add(normalize_skill(match.name))
    return found
