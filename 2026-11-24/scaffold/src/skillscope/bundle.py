"""Discover the skills in a bundle directory and load each SKILL.md."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from .frontmatter import FrontmatterError, parse

SKIP_DIRS = {"node_modules", "__pycache__", "venv"}


@dataclass
class Skill:
    """One skill directory and what could be read from its SKILL.md."""

    dir: Path
    rel: str  # skill directory relative to the bundle root, POSIX style
    meta: dict[str, object] = field(default_factory=dict)
    body: str = ""
    body_start: int = 1
    parse_error: str | None = None

    @property
    def name(self) -> str:
        value = self.meta.get("name")
        return value if isinstance(value, str) else ""

    @property
    def description(self) -> str:
        value = self.meta.get("description")
        return value if isinstance(value, str) else ""

    @property
    def label(self) -> str:
        """Name if usable, else the directory path - used in reports."""
        return self.name or self.rel


class BundleError(Exception):
    """The given path cannot be scanned as a bundle."""


def _skipped(path: Path, root: Path) -> bool:
    parts = path.relative_to(root).parts[:-1]
    return any(p.startswith(".") or p in SKIP_DIRS for p in parts)


def discover(root: Path) -> list[Skill]:
    """Find every SKILL.md under root, sorted.

    Hidden folders (".git", ".claude", ...) and vendor folders inside root are
    skipped; pass such a folder as root to scan it. Symlinked folders are not
    followed.
    """
    if not root.exists():
        raise BundleError(f"path does not exist: {root}")
    if not root.is_dir():
        raise BundleError(f"not a directory: {root}")
    root = root.resolve()
    skills: list[Skill] = []
    skipped = 0
    for md in sorted(root.rglob("SKILL.md")):
        if not md.is_file():
            continue
        if _skipped(md, root):
            skipped += 1
            continue
        rel = md.parent.relative_to(root).as_posix() or "."
        skill = Skill(dir=md.parent, rel=rel)
        try:
            text = md.read_text(encoding="utf-8-sig")
            skill.meta, skill.body, skill.body_start = parse(text)
        except UnicodeDecodeError:
            skill.parse_error = "SKILL.md is not valid UTF-8"
        except FrontmatterError as exc:
            skill.parse_error = str(exc)
        skills.append(skill)
    if not skills:
        hint = ""
        if skipped:
            hint = (f" ({skipped} skipped inside hidden or vendor folders such as .claude/;"
                    " pass that folder directly, e.g. .claude/skills)")
        raise BundleError(f"no SKILL.md files found under {root}{hint}")
    return skills
