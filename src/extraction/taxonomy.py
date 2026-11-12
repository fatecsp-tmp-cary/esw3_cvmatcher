"""Small explicit aliases; unknown skill strings remain unknown supporting evidence."""

import unicodedata
from collections.abc import Iterable

_ALIASES = {
    "python": "Python",
    "python3": "Python",
    "python 3": "Python",
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
}


def canonical_skill(value: str) -> str | None:
    """Exact case/whitespace aliases only; no fuzzy or mandatory inference."""
    if not isinstance(value, str):
        raise TypeError("Skill alias must be text")
    return _ALIASES.get(" ".join(unicodedata.normalize("NFKC", value).casefold().split()))


def normalize_skill(name: str) -> str:
    """Normalize explicit skill text; unknown input is not classified as a requirement."""
    if not isinstance(name, str):
        raise TypeError("Skill alias must be text")
    value = " ".join(unicodedata.normalize("NFKC", name).casefold().split())
    return _ALIASES.get(value, value).casefold()


def find_skills(texts: Iterable[str], vocabulary: Iterable[str]) -> set[str]:
    """Return normalized vocabulary skills explicitly mentioned in supplied text.

    No substring/fuzzy inference: aliases must match bounded whole tokens/phrases.
    Punctuation inside technology names is preserved, including C++, C# and Node.js.
    """
    import re

    normalized_texts = [
        " ".join(unicodedata.normalize("NFKC", text).casefold().split()) for text in texts
    ]
    known = {normalize_skill(name) for name in vocabulary if name.strip()}
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
    return found
