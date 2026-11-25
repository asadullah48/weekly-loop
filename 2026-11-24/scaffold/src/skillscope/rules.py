"""The `check` rules: per-skill spec rules plus bundle-wide rules."""

from __future__ import annotations

import re
from collections import defaultdict
from dataclasses import asdict, dataclass
from urllib.parse import unquote

from .budget import estimate_tokens
from .bundle import Skill
from .frontmatter import split_lines

NAME_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
# Inline link or image: [text](target "title"). The text may hold one level of
# [brackets]; the target may be <wrapped in angle brackets> or hold balanced ().
LINK_RE = re.compile(
    r"!?\[(?:[^\[\]]|\[[^\[\]]*\])*\]"
    r"\(\s*(?:<([^>\n]+)>|((?:[^()\s]|\([^()\s]*\))+))"
    r"(?:\s+(?:\"[^\"]*\"|'[^']*'|\([^()]*\)))?\s*\)"
)
# Reference definition: [label]: target
REF_DEF_RE = re.compile(r"^ {0,3}\[[^\]]+\]:\s*(?:<([^>]+)>|(\S+))")
CODE_SPAN_RE = re.compile(r"`[^`]*`")
COMMENT_RE = re.compile(r"<!--.*?-->")
FENCE_RE = re.compile(r"^ {0,3}(`{3,}|~{3,})")
SCHEME_RE = re.compile(r"^[A-Za-z][A-Za-z0-9+.-]+:")
DRIVE_RE = re.compile(r"^[A-Za-z]:[\\/]")

MAX_NAME = 64
MAX_DESCRIPTION = 1024
MAX_COMPATIBILITY = 500
MAX_BODY_LINES = 500
MAX_BODY_TOKENS = 5000

RULES = {
    "SS001": "SKILL.md frontmatter missing or unparseable",
    "SS002": "name missing or empty",
    "SS003": "name breaks the spec format",
    "SS004": "name does not match the skill directory",
    "SS005": "description missing or empty",
    "SS006": f"description longer than {MAX_DESCRIPTION} characters",
    "SS007": f"compatibility longer than {MAX_COMPATIBILITY} characters",
    "SS008": "same name used by more than one skill",
    "SS009": "relative link points to a file that does not exist",
    "SS010": f"body longer than {MAX_BODY_LINES} lines",
    "SS011": f"body estimated above {MAX_BODY_TOKENS} tokens",
}


@dataclass
class Finding:
    rule: str
    severity: str  # "error" or "warning"
    skill: str  # skill directory, relative to bundle root
    message: str
    line: int | None = None

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


def _name_findings(skill: Skill) -> list[Finding]:
    name = skill.meta.get("name")
    if not isinstance(name, str) or not name:
        return [Finding("SS002", "error", skill.rel, "'name' is missing or empty")]
    out = []
    if len(name) > MAX_NAME or not NAME_RE.match(name):
        out.append(
            Finding(
                "SS003", "error", skill.rel,
                f"name {name!r} must be 1-{MAX_NAME} chars of a-z, 0-9 and single hyphens, "
                "not starting or ending with a hyphen",
            )
        )
    if name != skill.dir.name:
        out.append(
            Finding("SS004", "error", skill.rel,
                    f"name {name!r} does not match directory {skill.dir.name!r}")
        )
    return out


def _text_findings(skill: Skill) -> list[Finding]:
    out = []
    desc = skill.meta.get("description")
    if not isinstance(desc, str) or not desc.strip():
        out.append(Finding("SS005", "error", skill.rel, "'description' is missing or empty"))
    elif len(desc) > MAX_DESCRIPTION:
        out.append(Finding("SS006", "error", skill.rel,
                           f"description is {len(desc)} chars (max {MAX_DESCRIPTION})"))
    compat = skill.meta.get("compatibility")
    if isinstance(compat, str) and len(compat) > MAX_COMPATIBILITY:
        out.append(Finding("SS007", "error", skill.rel,
                           f"compatibility is {len(compat)} chars (max {MAX_COMPATIBILITY})"))
    return out


def _link_targets(body: str, start: int):
    """Yield (line number, target) for links outside code blocks, code spans
    and HTML comments."""
    fence = None  # (character, length) of the open fence
    in_comment = in_indented = False
    prev_blank = True
    for offset, line in enumerate(split_lines(body)):
        lineno = start + offset
        if fence:
            m = FENCE_RE.match(line)
            if m and m.group(1)[0] == fence[0] and len(m.group(1)) >= fence[1] \
                    and not line.strip()[len(m.group(1)):].strip():
                fence = None
            continue
        if not line.strip():
            prev_blank = True
            continue
        if line.startswith(("    ", "\t")) and (prev_blank or in_indented) and not in_comment:
            in_indented, prev_blank = True, False
            continue
        in_indented = prev_blank = False
        text = line
        if in_comment:
            close = text.find("-->")
            if close == -1:
                continue
            text, in_comment = text[close + 3 :], False
        m = FENCE_RE.match(text)
        if m:
            fence = (m.group(1)[0], len(m.group(1)))
            continue
        text = COMMENT_RE.sub("", text)
        if "<!--" in text:
            text, in_comment = text.split("<!--", 1)[0], True
        text = CODE_SPAN_RE.sub("", text)
        for m in LINK_RE.finditer(text):
            yield lineno, m.group(1) or m.group(2)
        m = REF_DEF_RE.match(text)
        if m:
            yield lineno, m.group(1) or m.group(2)


def _link_findings(skill: Skill) -> list[Finding]:
    out = []
    for lineno, target in _link_targets(skill.body, skill.body_start):
        target = target.strip()
        if (not target or target.startswith(("#", "/", "\\")) or SCHEME_RE.match(target)
                or DRIVE_RE.match(target)):
            continue
        path_part = unquote(target.split("#", 1)[0].split("?", 1)[0])
        if path_part and not (skill.dir / path_part).exists():
            out.append(Finding("SS009", "error", skill.rel,
                               f"link target {path_part!r} not found", lineno))
    return out


def _size_findings(skill: Skill) -> list[Finding]:
    out = []
    lines = len(split_lines(skill.body))
    if lines > MAX_BODY_LINES:
        out.append(Finding("SS010", "warning", skill.rel,
                           f"body has {lines} lines (recommended max {MAX_BODY_LINES})"))
    tokens = estimate_tokens(skill.body)
    if tokens > MAX_BODY_TOKENS:
        out.append(Finding("SS011", "warning", skill.rel,
                           f"body is ~{tokens} tokens (recommended max {MAX_BODY_TOKENS})"))
    return out


def check(skills: list[Skill]) -> list[Finding]:
    """Run every rule over the bundle and return findings in a stable order."""
    findings: list[Finding] = []
    by_name: dict[str, list[str]] = defaultdict(list)
    for skill in skills:
        if skill.parse_error:
            findings.append(Finding("SS001", "error", skill.rel, skill.parse_error))
            continue
        findings += _name_findings(skill)
        findings += _text_findings(skill)
        findings += _link_findings(skill)
        findings += _size_findings(skill)
        if skill.name:
            by_name[skill.name].append(skill.rel)
    for name, dirs in sorted(by_name.items()):
        if len(dirs) > 1:
            for rel in dirs:
                others = ", ".join(d for d in dirs if d != rel)
                findings.append(Finding("SS008", "error", rel,
                                        f"name {name!r} is also used by {others}"))
    findings.sort(key=lambda f: (f.skill, f.rule, f.line or 0))
    return findings
