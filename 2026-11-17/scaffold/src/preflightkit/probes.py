"""Probe implementations.

Each probe answers one yes/no question about the local environment and
returns a ProbeResult. All probes use only the Python standard library.
"""

from __future__ import annotations

import importlib.util
import os
import shutil
import socket
import tempfile
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field


@dataclass(frozen=True)
class ProbeResult:
    """Outcome of a single probe."""

    kind: str  # "command" | "module" | "env" | "path" | "network"
    target: str
    ok: bool
    detail: str = ""

    def as_dict(self) -> dict:
        return {
            "kind": self.kind,
            "target": self.target,
            "ok": self.ok,
            "detail": self.detail,
        }


def probe_command(name: str) -> ProbeResult:
    """Is an executable with this name on PATH?"""
    path = shutil.which(name)
    return ProbeResult("command", name, path is not None, detail=path or "not on PATH")


def probe_module(name: str) -> ProbeResult:
    """Is this Python module importable in the current interpreter?"""
    try:
        spec = importlib.util.find_spec(name)
    except (ImportError, ValueError):
        spec = None
    return ProbeResult(
        "module", name, spec is not None,
        detail=(spec.origin or "built-in") if spec else "not importable",
    )


def probe_env(name: str) -> ProbeResult:
    """Is this environment variable set to a non-empty value?

    The value itself is never recorded, so secrets don't leak into reports.
    """
    ok = bool(os.environ.get(name))
    return ProbeResult("env", name, ok, detail="set" if ok else "unset or empty")


def probe_path_writable(path: str) -> ProbeResult:
    """Can we actually create a file under this directory?"""
    expanded = os.path.expanduser(path)
    if not os.path.isdir(expanded):
        return ProbeResult("path", path, False, detail="not a directory")
    try:
        with tempfile.NamedTemporaryFile(dir=expanded, prefix=".preflight-", delete=True):
            pass
    except OSError as exc:
        return ProbeResult("path", path, False, detail=f"write failed: {exc.strerror or exc}")
    return ProbeResult("path", path, True, detail="writable")


def probe_network(host: str, port: int = 443, timeout: float = 3.0) -> ProbeResult:
    """Can we open a TCP connection to host:port?

    Note: in proxied sandboxes this tests the proxy route, which is exactly
    what an agent's own HTTP calls would use.
    """
    target = f"{host}:{port}"
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return ProbeResult("network", target, True, detail="tcp connect ok")
    except OSError as exc:
        return ProbeResult("network", target, False, detail=str(exc))


#: Default probe set: a small, opinionated baseline for agent sandboxes.
DEFAULT_PROBES: dict[str, list] = {
    "commands": ["git", "python3", "node", "npm", "pip", "curl"],
    "modules": ["json", "sqlite3", "ssl", "venv"],
    "env": ["HOME", "PATH"],
    "paths": [tempfile.gettempdir(), "."],
    "network": ["pypi.org", "github.com", "registry.npmjs.org"],
}


@dataclass
class ProbePlan:
    """A concrete set of probes to run."""

    commands: list[str] = field(default_factory=list)
    modules: list[str] = field(default_factory=list)
    env: list[str] = field(default_factory=list)
    paths: list[str] = field(default_factory=list)
    network: list[str] = field(default_factory=list)  # "host" or "host:port"

    @classmethod
    def default(cls) -> "ProbePlan":
        return cls(
            commands=list(DEFAULT_PROBES["commands"]),
            modules=list(DEFAULT_PROBES["modules"]),
            env=list(DEFAULT_PROBES["env"]),
            paths=list(DEFAULT_PROBES["paths"]),
            network=list(DEFAULT_PROBES["network"]),
        )

    def merge(self, extra: dict) -> "ProbePlan":
        """Return a new plan with items from a config dict appended (deduplicated)."""

        def merged(current: list[str], added) -> list[str]:
            if not isinstance(added, list):
                raise ValueError(f"config values must be lists, got {type(added).__name__}")
            out = list(current)
            for item in added:
                if not isinstance(item, str):
                    raise ValueError("config list items must be strings")
                if item not in out:
                    out.append(item)
            return out

        known = {"commands", "modules", "env", "paths", "network"}
        unknown = set(extra) - known
        if unknown:
            raise ValueError(f"unknown config keys: {', '.join(sorted(unknown))}")
        return ProbePlan(
            commands=merged(self.commands, extra.get("commands", [])),
            modules=merged(self.modules, extra.get("modules", [])),
            env=merged(self.env, extra.get("env", [])),
            paths=merged(self.paths, extra.get("paths", [])),
            network=merged(self.network, extra.get("network", [])),
        )


def _parse_host_port(spec: str) -> tuple[str, int]:
    if ":" in spec:
        host, _, port_text = spec.rpartition(":")
        try:
            return host, int(port_text)
        except ValueError as exc:
            raise ValueError(f"bad network spec {spec!r}: port must be an integer") from exc
    return spec, 443


def run_plan(plan: ProbePlan, network_timeout: float = 3.0) -> list[ProbeResult]:
    """Run every probe in the plan; network probes run in parallel."""
    results: list[ProbeResult] = []
    results.extend(probe_command(c) for c in plan.commands)
    results.extend(probe_module(m) for m in plan.modules)
    results.extend(probe_env(e) for e in plan.env)
    results.extend(probe_path_writable(p) for p in plan.paths)

    if plan.network:
        host_ports = [_parse_host_port(spec) for spec in plan.network]
        with ThreadPoolExecutor(max_workers=min(8, len(host_ports))) as pool:
            futures = [
                pool.submit(probe_network, host, port, network_timeout)
                for host, port in host_ports
            ]
            results.extend(f.result() for f in futures)
    return results
