"""A small, strict parser for the YAML subset used in SKILL.md frontmatter.

Supported:
  * top-level ``key: value`` pairs (plain, 'single' or "double" quoted)
  * plain values that wrap onto indented continuation lines (joined with spaces)
  * block scalars ``key: |`` and ``key: >`` (with optional ``-`` / ``+``)
  * one level of nested mapping (``metadata:`` followed by indented ``k: v``)
  * full-line ``#`` comments and `` # comment`` after a value
  * ``~`` / ``null`` read as a missing value (None)

Anything else (flow mappings, lists, anchors, quoted keys, tabs for
indentation, uneven nesting) raises FrontmatterError, so it is reported
instead of silently misread.
"""

from __future__ import annotations

import re
import textwrap

_KEY_RE = re.compile(r"^([A-Za-z0-9_-]+):(?:[ \t]+(.*))?$")
_BLOCK_RE = re.compile(r"^[|>][-+]?$")
_NEWLINE_RE = re.compile(r"\r\n|\r|\n")
_NULLS = {"~", "null", "Null", "NULL"}


class FrontmatterError(ValueError):
    """Raised when frontmatter is missing, unterminated or unsupported."""


def split_lines(text: str) -> list[str]:
    """Split on \\n, \\r\\n and \\r only (unlike str.splitlines, which also
    splits on form feeds and Unicode separators and so shifts line numbers)."""
    lines = _NEWLINE_RE.split(text)
    if lines and lines[-1] == "":
        lines.pop()
    return lines


def split(text: str) -> tuple[list[str], str, int]:
    """Return (frontmatter lines, body text, 1-based line where body starts)."""
    lines = split_lines(text)
    if not lines or lines[0].rstrip() != "---":
        raise FrontmatterError("file does not start with a '---' frontmatter block")
    for i in range(1, len(lines)):
        if lines[i].rstrip() == "---":  # column 0 only: indented '---' is content
            body = "\n".join(lines[i + 1 :])
            return lines[1:i], body, i + 2
    raise FrontmatterError("frontmatter block is not closed with '---'")


def _quoted(raw: str, lineno: int) -> str:
    """Decode a quoted scalar; only whitespace or a # comment may follow it."""
    quote, i, out = raw[0], 1, []
    while i < len(raw):
        ch = raw[i]
        if quote == "'" and ch == "'":
            if raw[i + 1 : i + 2] == "'":
                out.append("'")
                i += 2
                continue
            break
        if quote == '"' and ch == "\\" and i + 1 < len(raw):
            nxt = raw[i + 1]
            out.append({"n": "\n", "t": "\t", '"': '"', "\\": "\\"}.get(nxt, "\\" + nxt))
            i += 2
            continue
        if quote == '"' and ch == '"':
            break
        out.append(ch)
        i += 1
    else:
        raise FrontmatterError(f"line {lineno}: unterminated quoted value")
    rest = raw[i + 1 :].strip()
    if rest and not rest.startswith("#"):
        raise FrontmatterError(f"line {lineno}: unexpected text after quoted value")
    return "".join(out)


def _scalar(raw: str, lineno: int) -> str | None:
    raw = raw.strip()
    if raw[:1] in ("'", '"'):
        return _quoted(raw, lineno)
    if raw[:1] in ("[", "{", "&", "*", "!", "|", ">", "@", "`"):
        raise FrontmatterError(f"line {lineno}: unsupported YAML construct {raw[:1]!r}")
    if " #" in raw:
        raw = raw.split(" #", 1)[0].rstrip()
    return None if raw in _NULLS else raw


def _indent(line: str) -> int:
    return len(line) - len(line.lstrip(" "))


def _block(style: str, child: list[str]) -> str:
    text = textwrap.dedent("\n".join(child)).strip("\n")
    if style == "|":
        return text
    folded, para = [], []
    for line in text.split("\n"):
        if line.strip():
            para.append(line.strip())
        else:
            folded.append(" ".join(para))
            para = []
    folded.append(" ".join(para))
    return "\n".join(p for p in folded if p)


def _nested(child: list[str], first_lineno: int) -> dict[str, str | None]:
    nested: dict[str, str | None] = {}
    width = None
    for offset, c in enumerate(child):
        lineno = first_lineno + offset
        if not c.strip() or c.lstrip().startswith("#"):
            continue
        if width is None:
            width = _indent(c)
        if _indent(c) != width:
            raise FrontmatterError(f"line {lineno}: uneven indentation in nested mapping")
        m = _KEY_RE.match(c.strip())
        if not m:
            raise FrontmatterError(
                f"line {lineno}: only one level of 'key: value' nesting is supported"
            )
        if m.group(1) in nested:
            raise FrontmatterError(f"line {lineno}: duplicate key {m.group(1)!r}")
        nested[m.group(1)] = _scalar(m.group(2) or "", lineno)
    return nested


def parse_lines(fm: list[str]) -> dict[str, object]:
    """Parse frontmatter lines into a dict of str -> str | None | dict."""
    data: dict[str, object] = {}
    i = 0
    while i < len(fm):
        line = fm[i]
        lineno = i + 2  # +1 for 1-based, +1 for the opening '---'
        if line.strip() and "\t" in line[: _indent(line) + 1]:
            raise FrontmatterError(f"line {lineno}: tabs are not allowed for indentation")
        if not line.strip() or line.lstrip().startswith("#"):
            i += 1
            continue
        if _indent(line) != 0:
            raise FrontmatterError(f"line {lineno}: unexpected indentation")
        match = _KEY_RE.match(line.rstrip())
        if not match:
            raise FrontmatterError(f"line {lineno}: expected 'key: value'")
        key, value = match.group(1), (match.group(2) or "").strip()
        if key in data:
            raise FrontmatterError(f"line {lineno}: duplicate key {key!r}")

        # Collect the indented (or blank) lines that belong to this key.
        j = i + 1
        child: list[str] = []
        while j < len(fm) and (not fm[j].strip() or _indent(fm[j]) > 0):
            child.append(fm[j])
            j += 1
        while child and not child[-1].strip():
            child.pop()

        if _BLOCK_RE.match(value):
            data[key] = _block(value[0], child)
        elif value == "" and child:
            data[key] = _nested(child, lineno + 1)
        elif value == "":
            data[key] = None
        else:
            parts = [value] + [c.strip() for c in child if c.strip()]
            data[key] = _scalar(" ".join(parts), lineno)
        i = j
    return data


def parse(text: str) -> tuple[dict[str, object], str, int]:
    """Parse a whole SKILL.md: returns (frontmatter dict, body, body start line)."""
    fm, body, start = split(text)
    return parse_lines(fm), body, start
