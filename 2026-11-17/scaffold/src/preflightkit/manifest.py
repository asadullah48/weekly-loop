"""Build and serialize the capability manifest from probe results."""

from __future__ import annotations

import datetime
import json
import platform

from .probes import ProbeResult

MANIFEST_VERSION = 1


def build_manifest(results: list[ProbeResult]) -> dict:
    """Group probe results into a JSON-serializable capability manifest."""
    grouped: dict[str, dict[str, dict]] = {}
    for r in results:
        grouped.setdefault(r.kind, {})[r.target] = {"ok": r.ok, "detail": r.detail}
    return {
        "manifest_version": MANIFEST_VERSION,
        "generated_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "platform": {
            "system": platform.system(),
            "python": platform.python_version(),
        },
        "probes": grouped,
        "summary": {
            "total": len(results),
            "ok": sum(1 for r in results if r.ok),
            "failed": sum(1 for r in results if not r.ok),
        },
    }


def to_json(manifest: dict) -> str:
    return json.dumps(manifest, indent=2, sort_keys=True)


def to_table(results: list[ProbeResult]) -> str:
    """Plain-text report, aligned for humans, stable for logs."""
    if not results:
        return "no probes ran"
    width_kind = max(len(r.kind) for r in results)
    width_target = max(len(r.target) for r in results)
    lines = []
    for r in results:
        mark = "ok " if r.ok else "FAIL"
        lines.append(
            f"[{mark}] {r.kind.ljust(width_kind)}  {r.target.ljust(width_target)}  {r.detail}"
        )
    ok = sum(1 for r in results if r.ok)
    lines.append(f"\n{ok}/{len(results)} probes passed")
    return "\n".join(lines)
