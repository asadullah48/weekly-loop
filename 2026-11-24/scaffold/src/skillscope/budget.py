"""Rough context-cost accounting for a skill bundle.

Token counts are an ESTIMATE (characters / 4, rounded up). Real tokenizers
differ, so treat the numbers as a budget guide, not an exact count.
"""

from __future__ import annotations

import math

from .bundle import Skill
from .frontmatter import split_lines

CHARS_PER_TOKEN = 4


def estimate_tokens(text: str) -> int:
    return math.ceil(len(text) / CHARS_PER_TOKEN) if text else 0


def budget(skills: list[Skill]) -> dict[str, object]:
    """Per-skill and total estimated tokens.

    startup_tokens: name + description of every skill - what an agent loads
    up front for the whole bundle. body_tokens: what each skill costs once
    activated.
    """
    rows = []
    for skill in skills:
        metadata = estimate_tokens(skill.name) + estimate_tokens(skill.description)
        rows.append(
            {
                "skill": skill.rel,
                "name": skill.name,
                "metadata_tokens": metadata,
                "body_tokens": estimate_tokens(skill.body),
                "body_lines": len(split_lines(skill.body)),
                "parse_error": skill.parse_error,
            }
        )
    return {
        "estimate": f"characters / {CHARS_PER_TOKEN}",
        "skills": rows,
        "totals": {
            "skills": len(rows),
            "startup_tokens": sum(r["metadata_tokens"] for r in rows),
            "body_tokens": sum(r["body_tokens"] for r in rows),
        },
    }
