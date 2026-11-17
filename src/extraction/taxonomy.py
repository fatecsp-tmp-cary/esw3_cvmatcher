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
    r"\s+(?:intermedi[aá]ri[oa]\s*(?:/|ou)\s*avan[cç]ad[oa]|"
    r"avan[cç]ad[oa]\s*(?:/|ou)\s*fluente|"
    r"avan[cç]ad[oa]s?|intermedi[aá]ri[oa]s?|b[aá]sic[oa]s?|fluente|t[eé]cnic[oa]|"
    r"profissional|advanced|intermediate|basic|fluent|fluency|proficiency)$",
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
        for pattern in (_TRAILING_PAREN_TAG, _TRAILING_LEVEL, _LEADING_WRAPPER):
            updated = pattern.sub("", cleaned).strip()
            if updated != cleaned:
                cleaned = updated
                if _exact_lookup(cleaned) is not None:
                    return cleaned
                break
        else:
            break
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
    last_cnh = False

    def _add(name: str) -> None:
        nonlocal last_cnh
        last_cnh = name.startswith("CNH ")
        if name not in seen:
            seen.add(name)
            resolved.append(name)

    def _resolve_cnh_letter(value: str) -> str | None:
        if last_cnh and len(value) == 1 and value.upper() in {"A", "B", "C", "D", "E"}:
            return canonical_skill(f"CNH {value.upper()}")
        return None

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
            if (hit := _resolve_cnh_letter(token) or canonical_skill(token)) is not None:
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
                    if not sub:
                        continue
                    if (sub_hit := _resolve_cnh_letter(sub) or canonical_skill(sub)) is not None:
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


_URL_TLD_PREFIX = re.compile(
    r"^(?:https?://|www\.|[a-z0-9-]+(?:\.[a-z0-9-]+)*\.(?:com|org|net|io|dev|br|gov|edu|co|app|ai)(?:\.[a-z]{2})?(?:/|$))",
    re.I,
)
_URL_DOMAIN_SUFFIX = re.compile(
    r"^\.(?:com|org|net|io|dev|br|gov|edu|co|app|ai)(?:\.[a-z]{2})?(?:/|\b)",
    re.I,
)


def alias_spans(text: str) -> Iterator[tuple[int, int, str]]:
    """Supplement model detection with exact explicit prose-safe vocabulary occurrences.

    Match original Unicode directly; no fuzzy-generated offsets or strength.
    """
    for match in _PROSE_SPAN_PATTERN.finditer(text):
        token_start = max(
            text.rfind(" ", 0, match.start()),
            text.rfind("\n", 0, match.start()),
            text.rfind("\t", 0, match.start()),
            text.rfind("(", 0, match.start()),
            -1,
        )
        token_prefix = text[token_start + 1 : match.start()]
        if (
            text[match.end() : match.end() + 3] == "://"
            or _URL_TLD_PREFIX.match(token_prefix)
            or _URL_DOMAIN_SUFFIX.match(text[match.end() :])
        ):
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


_TOKEN_REGEX = re.compile(r"\w+(?:[.+#/-]+\w+)*[+#]*")


class SkillTextMatcher:
    """Request-local precompiled skill matcher over fixed candidate text."""

    def __init__(self, texts: Iterable[str]) -> None:
        self.normalized_texts = [
            " ".join(unicodedata.normalize("NFKC", text).casefold().split()) for text in texts
        ]
        self.ascii_texts = [_fold_ascii(text) for text in self.normalized_texts]
        self._prose_taxonomy_found: set[str] = set()
        self._approx_taxonomy_found: set[str] = set()
        self._tokenized_texts: list[tuple[str, list[re.Match[str]], list[str]]] = []
        self._phrases_by_width: dict[int, set[str]] = {}
        self._phrases_by_shape: dict[tuple[int, int, str], list[str]] = {}

        if not self.normalized_texts:
            return

        for source_text in (*self.normalized_texts, *self.ascii_texts):
            for match in _PROSE_SPAN_PATTERN.finditer(source_text):
                matched_folded = _fold(match.group())
                name = _PROSE_ALIASES.get(matched_folded) or _PROSE_ALIASES_ASCII.get(
                    _fold_ascii(matched_folded)
                )
                if name is not None:
                    self._prose_taxonomy_found.add(name.casefold())

        for text in self.normalized_texts:
            matches = list(_TOKEN_REGEX.finditer(text))
            tokens = [m.group() for m in matches]
            self._tokenized_texts.append((text, matches, tokens))

        self._collect_phrases(_DEFAULT_WIDTHS)
        for width in _DEFAULT_WIDTHS:
            for phrase in self._phrases_by_width.get(width, ()):
                exact_prose = _PROSE_ALIASES.get(phrase) or _PROSE_ALIASES_ASCII.get(
                    _fold_ascii(phrase)
                )
                if exact_prose is not None:
                    self._prose_taxonomy_found.add(exact_prose.casefold())
                approx_match = _lookup(phrase, _ALIASES, _DEFAULT_BUCKETS)
                if approx_match and approx_match.approximate:
                    self._approx_taxonomy_found.add(normalize_skill(approx_match.name))

    def _collect_phrases(self, widths: Iterable[int]) -> None:
        missing = tuple(sorted({w for w in widths if w > 0 and w not in self._phrases_by_width}))
        if not missing:
            return
        for w in missing:
            self._phrases_by_width[w] = set()
        for text, matches, tokens in self._tokenized_texts:
            for start in range(len(tokens)):
                for size in missing:
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
                    bucket = self._phrases_by_width[size]
                    if phrase not in bucket:
                        bucket.add(phrase)
                        if len(phrase) >= 4:
                            shape = (size, len(phrase), re.sub(r"\w", "", phrase))
                            self._phrases_by_shape.setdefault(shape, []).append(phrase)

    def match(self, vocabulary: Iterable[str]) -> set[str]:
        """Match pre-extracted candidate text against a target job vocabulary."""
        if not self.normalized_texts:
            return set()
        known = {normalize_skill(name) for name in vocabulary if name.strip()}
        if not known:
            return set()

        known_taxonomy = known & _TAXONOMY_CANONICAL_FOLDS
        found = (self._prose_taxonomy_found | self._approx_taxonomy_found) & known_taxonomy

        extras = known - _TAXONOMY_CANONICAL_FOLDS
        if not extras:
            return found

        extra_widths = {len(skill.split()) for skill in extras if len(skill) >= 5}
        if extra_widths:
            self._collect_phrases(extra_widths)

        for extra in extras:
            if any(extra in text for text in (*self.normalized_texts, *self.ascii_texts)):
                pattern = _skill_find_pattern(extra)
                if any(pattern.search(text) for text in self.normalized_texts) or any(
                    pattern.search(text) for text in self.ascii_texts
                ):
                    found.add(extra)
                    continue
            if len(extra) >= 5:
                width = len(extra.split())
                punct = re.sub(r"\w", "", extra)
                for size in (len(extra) - 1, len(extra), len(extra) + 1):
                    for phrase in self._phrases_by_shape.get((width, size, punct), ()):
                        if phrase not in _ALIASES and len(phrase) >= 5 and one_edit(phrase, extra):
                            found.add(extra)
                            break
                    else:
                        continue
                    break
        return found


def compile_skill_matcher(texts: Iterable[str]) -> SkillTextMatcher:
    """Build a request-local matcher for repeated per-job intersections."""
    return SkillTextMatcher(texts)


def find_skills(texts: Iterable[str], vocabulary: Iterable[str]) -> set[str]:
    """Return normalized vocabulary skills explicitly mentioned in supplied text.

    Exact aliases plus bounded score-only typo support. This result is never
    sufficient evidence for mandatory satisfaction or candidate exclusion.
    """
    return SkillTextMatcher(texts).match(vocabulary)
