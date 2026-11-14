"""Small explicit aliases; unknown skill strings remain unknown supporting evidence."""

import re
import unicodedata
from collections.abc import Iterable
from dataclasses import dataclass

VERSION = "explicit-aliases-single-edit-min5-v3"

_ALIASES = {
    "python": "Python",
    "python3": "Python",
    "python 3": "Python",
    "cpython": "CPython",
    "cython": "Cython",
    "postgres": "PostgreSQL",
    "postgresql": "PostgreSQL",
    "kubernetes": "Kubernetes",
    "k8s": "Kubernetes",
    "javascript": "JavaScript",
    "js": "JavaScript",
    "typescript": "TypeScript",
    "ts": "TypeScript",
    "docker": "Docker",
    "sql": "SQL",
    "fastapi": "FastAPI",
    "react": "React",
    "react.js": "React",
    "reactjs": "React",
    "node.js": "Node.js",
    "nodejs": "Node.js",
    "aws": "AWS",
    "amazon web services": "AWS",
    "git": "Git",
    "java": "Java",
    "c#": "C#",
    "c++": "C++",
    "c": "C",
    "c sharp": "C#",
    "r": "R",
    "go": "Go",
    "golang": "Go",
    "ruby": "Ruby",
    "rails": "Rails",
    "ruby on rails": "Rails",
    "php": "PHP",
    "wordpress": "WordPress",
    "coren": "COREN",
    "oab": "OAB",
    "crc": "CRC",
    "crf": "CRF",
    "cnh a": "CNH A",
    "cnh b": "CNH B",
    "cnh c": "CNH C",
    "cnh d": "CNH D",
    "cnh e": "CNH E",
    "pmp": "PMP",
    "cissp": "CISSP",
    "ingles": "English",
    "inglês": "English",
    "english": "English",
    "portugues": "Portuguese",
    "português": "Portuguese",
    "portuguese": "Portuguese",
    "espanhol": "Spanish",
    "spanish": "Spanish",
    "frances": "French",
    "francês": "French",
    "french": "French",
    "alemao": "German",
    "alemão": "German",
    "german": "German",
}

CATEGORIES = {
    **dict.fromkeys(
        ("COREN", "OAB", "CRC", "CRF", "CNH A", "CNH B", "CNH C", "CNH D", "CNH E"),
        "professional license",
    ),
    **dict.fromkeys(("PMP", "CISSP"), "certification"),
    **dict.fromkeys(("English", "Portuguese", "Spanish", "French", "German"), "language"),
}


def _fold(value: str) -> str:
    if not isinstance(value, str):
        raise TypeError("Skill alias must be text")
    return " ".join(unicodedata.normalize("NFKC", value).casefold().split())


def canonical_skill(value: str) -> str | None:
    """Exact case/whitespace aliases only; no fuzzy or mandatory inference."""
    return _ALIASES.get(_fold(value))


def alias_spans(text: str):
    """Supplement model detection with exact explicit vocabulary occurrences.

    Match original Unicode directly; no fuzzy-generated offsets or strength.
    """
    pattern = re.compile(
        r"(?<![\w.+#])(?:"
        + "|".join(
            re.escape(a).replace(r"\ ", r"\s+")
            for a in sorted(_ALIASES, key=lambda a: (-len(a), a))
        )
        + r")(?![\w+#])",
        re.I,
    )
    for match in pattern.finditer(text):
        name = canonical_skill(match.group())
        if name:
            yield match.start(), match.end(), CATEGORIES.get(name, "skill")


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
    aliases, buckets = _alias_index(vocabulary)
    return _lookup(_fold(value), aliases, buckets)


def _alias_index(vocabulary):
    aliases = dict(_ALIASES)
    for name in vocabulary:
        aliases.setdefault(_fold(name), canonical_skill(name) or name)
    buckets: dict[tuple[int, str], list[tuple[str, str]]] = {}
    for alias, name in aliases.items():
        if len(alias) >= 5:
            buckets.setdefault((len(alias), re.sub(r"\w", "", alias)), []).append((alias, name))
    return aliases, buckets


def _lookup(folded, aliases, buckets):
    if folded in aliases:
        return AliasMatch(aliases[folded], False)
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
    value = _fold(name)
    return _ALIASES.get(value, value).casefold()


def find_skills(texts: Iterable[str], vocabulary: Iterable[str]) -> set[str]:
    """Return normalized vocabulary skills explicitly mentioned in supplied text.

    Exact aliases plus bounded score-only typo support. This result is never
    sufficient evidence for mandatory satisfaction or candidate exclusion.
    """
    normalized_texts = [
        " ".join(unicodedata.normalize("NFKC", text).casefold().split()) for text in texts
    ]
    vocabulary = tuple(name for name in vocabulary if name.strip())
    known = {normalize_skill(name) for name in vocabulary}
    found = set()
    for canonical in known:
        variants = {canonical}
        variants.update(
            alias for alias, display in _ALIASES.items() if normalize_skill(display) == canonical
        )
        pattern = re.compile(
            r"(?<![\w.+#])(?:"
            + "|".join(re.escape(name) for name in sorted(variants))
            + r")(?![\w+#])"
        )
        if any(pattern.search(text) for text in normalized_texts):
            found.add(canonical)
    # Tokenize full names, retaining internal punctuation. Sentence-final full
    # stops are separators, while Node.js and C++ remain single distinct tokens.
    aliases, buckets = _alias_index(vocabulary)
    widths = sorted({len(name.split()) for name in aliases})
    seen = set()
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
