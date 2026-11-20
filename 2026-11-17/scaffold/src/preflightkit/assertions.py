"""Check a requirements file against a capability manifest.

Requirements file format (JSON):

{
  "commands": ["git"],
  "modules": ["json"],
  "env": ["HOME"],
  "paths": ["."],
  "network": ["github.com"]
}

Every listed item must have a passing probe of the matching kind.
Network items may be "host" (port 443 implied) or "host:port"; the manifest
records them as "host:port", so "github.com" matches "github.com:443".
"""

from __future__ import annotations

from dataclasses import dataclass

REQUIREMENT_KINDS = ("commands", "modules", "env", "paths", "network")

_KIND_BY_SECTION = {
    "commands": "command",
    "modules": "module",
    "env": "env",
    "paths": "path",
    "network": "network",
}


@dataclass(frozen=True)
class UnmetRequirement:
    section: str
    target: str
    reason: str


def validate_requirements(requirements: dict) -> None:
    """Raise ValueError when the requirements document is malformed."""
    if not isinstance(requirements, dict):
        raise ValueError("requirements must be a JSON object")
    unknown = set(requirements) - set(REQUIREMENT_KINDS)
    if unknown:
        raise ValueError(f"unknown requirement sections: {', '.join(sorted(unknown))}")
    for section, items in requirements.items():
        if not isinstance(items, list) or not all(isinstance(i, str) for i in items):
            raise ValueError(f"section {section!r} must be a list of strings")


def check(requirements: dict, manifest: dict) -> list[UnmetRequirement]:
    """Return the list of unmet requirements (empty means all met)."""
    validate_requirements(requirements)
    probes: dict = manifest.get("probes", {})
    unmet: list[UnmetRequirement] = []
    for section in REQUIREMENT_KINDS:
        kind = _KIND_BY_SECTION[section]
        recorded: dict = probes.get(kind, {})
        for target in requirements.get(section, []):
            lookup = target
            if section == "network" and ":" not in target:
                lookup = f"{target}:443"
            entry = recorded.get(lookup)
            if entry is None:
                unmet.append(UnmetRequirement(section, target, "not probed"))
            elif not entry.get("ok"):
                unmet.append(
                    UnmetRequirement(section, target, entry.get("detail") or "probe failed")
                )
    return unmet
