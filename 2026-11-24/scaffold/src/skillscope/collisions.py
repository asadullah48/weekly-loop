"""Find skills whose descriptions overlap so much an agent may pick the wrong one.

Each description becomes a set of content words (lowercased Unicode words of
3+ characters, stopwords removed, a plural 's' stripped except after
ss/us/is). Every pair of skills is
scored with Jaccard similarity: shared words / all distinct words.
"""

from __future__ import annotations

import re
from functools import lru_cache
from importlib.resources import files
from itertools import combinations

from .bundle import Skill

WORD_RE = re.compile(r"[^\W_]+")  # Unicode letters and digits
DEFAULT_THRESHOLD = 0.3


@lru_cache(maxsize=1)
def stopwords() -> frozenset[str]:
    """Load the stopword list shipped as package data."""
    text = files("skillscope").joinpath("data/stopwords.txt").read_text(encoding="utf-8")
    return frozenset(
        w.strip() for w in text.splitlines() if w.strip() and not w.startswith("#")
    )


def _normalize(word: str) -> str:
    """Strip a plural 's' ("pdfs" -> "pdf"), but keep -ss, -us, -is words
    ("class", "status", "analysis")."""
    if len(word) >= 4 and word.endswith("s") and not word.endswith(("ss", "us", "is")):
        return word[:-1]
    return word


def terms(description: str) -> set[str]:
    stop = stopwords()
    words = (w for w in WORD_RE.findall(description.lower()) if len(w) >= 3)
    return {_normalize(w) for w in words if w not in stop} - stop


def jaccard(a: set[str], b: set[str]) -> float:
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)


def find_collisions(skills: list[Skill], threshold: float = DEFAULT_THRESHOLD) -> list[dict]:
    """Return pairs with similarity >= threshold, highest first."""
    usable = [(s, terms(s.description)) for s in skills if not s.parse_error and s.description]
    pairs = []
    for (sa, ta), (sb, tb) in combinations(usable, 2):
        score = jaccard(ta, tb)
        if score >= threshold:
            pairs.append(
                {
                    "a": sa.rel,
                    "b": sb.rel,
                    "score": round(score, 3),
                    "shared": sorted(ta & tb),
                }
            )
    pairs.sort(key=lambda p: (-p["score"], p["a"], p["b"]))
    return pairs
