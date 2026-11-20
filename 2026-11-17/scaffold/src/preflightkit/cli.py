"""Command-line interface for PreflightKit.

Exit codes:
  0  success / all requirements met
  1  one or more requirements unmet (assert) or probe failures (scan --strict)
  2  usage or input error (bad JSON, unknown keys, missing file)
"""

from __future__ import annotations

import argparse
import json
import os
import sys

from . import __version__
from .assertions import REQUIREMENT_KINDS, check, validate_requirements
from .manifest import build_manifest, to_json, to_table
from .probes import ProbePlan, run_plan

CONFIG_FILENAME = "preflight.json"


def _fail(message: str) -> "SystemExit":
    """Input/usage error: print to stderr and exit 2."""
    print(message, file=sys.stderr)
    return SystemExit(2)

EXAMPLE_REQUIREMENTS = {
    "commands": ["git", "python3"],
    "modules": ["json"],
    "env": ["HOME"],
    "paths": ["."],
    "network": ["github.com"],
}


def _load_json_file(path: str) -> dict:
    try:
        with open(path, "r", encoding="utf-8") as fh:
            data = json.load(fh)
    except FileNotFoundError:
        raise _fail(f"preflight: file not found: {path}") from None
    except json.JSONDecodeError as exc:
        raise _fail(f"preflight: invalid JSON in {path}: {exc}") from None
    if not isinstance(data, dict):
        raise _fail(f"preflight: {path} must contain a JSON object")
    return data


def _build_plan(config_dir: str, no_default: bool = False) -> ProbePlan:
    plan = ProbePlan() if no_default else ProbePlan.default()
    config_path = os.path.join(config_dir, CONFIG_FILENAME)
    if os.path.isfile(config_path):
        extra = _load_json_file(config_path)
        try:
            plan = plan.merge(extra)
        except ValueError as exc:
            raise _fail(f"preflight: bad {CONFIG_FILENAME}: {exc}") from None
    return plan


def cmd_scan(args: argparse.Namespace) -> int:
    plan = _build_plan(os.getcwd())
    results = run_plan(plan, network_timeout=args.timeout)
    if args.json:
        print(to_json(build_manifest(results)))
    else:
        print(to_table(results))
    if args.strict and any(not r.ok for r in results):
        return 1
    return 0


def cmd_assert(args: argparse.Namespace) -> int:
    requirements = _load_json_file(args.requirements)
    try:
        validate_requirements(requirements)
    except ValueError as exc:
        raise _fail(f"preflight: bad requirements file: {exc}") from None

    # Probe exactly what the requirements name (plus any local preflight.json),
    # so nothing comes back "not probed" unless the file itself is odd.
    plan = _build_plan(os.getcwd(), no_default=True)
    try:
        plan = plan.merge({k: requirements.get(k, []) for k in REQUIREMENT_KINDS})
    except ValueError as exc:  # pragma: no cover - validate_requirements catches first
        raise _fail(f"preflight: bad requirements file: {exc}") from None

    manifest = build_manifest(run_plan(plan, network_timeout=args.timeout))
    unmet = check(requirements, manifest)
    if unmet:
        print("unmet requirements:", file=sys.stderr)
        for u in unmet:
            print(f"  - {u.section}: {u.target} ({u.reason})", file=sys.stderr)
        return 1
    print("all requirements met")
    return 0


def cmd_init(args: argparse.Namespace) -> int:
    path = os.path.join(os.getcwd(), "preflight-requirements.json")
    if os.path.exists(path) and not args.force:
        raise _fail(f"preflight: {path} already exists (use --force to overwrite)")
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(EXAMPLE_REQUIREMENTS, fh, indent=2)
        fh.write("\n")
    print(f"wrote {path}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="preflight",
        description="Probe this environment's real capabilities and assert requirements.",
    )
    parser.add_argument("--version", action="version", version=f"preflightkit {__version__}")
    sub = parser.add_subparsers(dest="command", required=True)

    p_scan = sub.add_parser("scan", help="run probes and print a report")
    p_scan.add_argument("--json", action="store_true", help="emit a JSON capability manifest")
    p_scan.add_argument("--strict", action="store_true", help="exit 1 if any probe fails")
    p_scan.add_argument("--timeout", type=float, default=3.0, help="network probe timeout (s)")
    p_scan.set_defaults(func=cmd_scan)

    p_assert = sub.add_parser(
        "assert",
        help="check a requirements JSON file; exit 1 on unmet",
        epilog="exit codes: 0 all requirements met; 1 one or more unmet; 2 input/usage error",
    )
    p_assert.add_argument("requirements", help="path to requirements JSON file")
    p_assert.add_argument("--timeout", type=float, default=3.0, help="network probe timeout (s)")
    p_assert.set_defaults(func=cmd_assert)

    p_init = sub.add_parser("init", help="write an example preflight-requirements.json here")
    p_init.add_argument("--force", action="store_true", help="overwrite an existing file")
    p_init.set_defaults(func=cmd_init)

    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        return args.func(args)
    except SystemExit:
        raise
    except Exception as exc:  # defensive: never show a bare traceback to a harness
        print(f"preflight: error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
