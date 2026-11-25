"""Command-line interface: `skillscope check | collisions | budget | rules`."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from . import __version__
from .budget import budget
from .bundle import BundleError, discover
from .collisions import DEFAULT_THRESHOLD, find_collisions
from .rules import RULES, check

EXIT_OK, EXIT_FINDINGS, EXIT_INPUT = 0, 1, 2

EXIT_HELP = """exit codes:
  0  nothing to report
  1  findings reported (see command help)
  2  input error (bad path, no SKILL.md found, bad option)"""


def _threshold(value: str) -> float:
    try:
        number = float(value)
    except ValueError:
        raise argparse.ArgumentTypeError(f"not a number: {value!r}") from None
    if not 0 < number <= 1:
        raise argparse.ArgumentTypeError("threshold must be > 0 and <= 1")
    return number


class _Parser(argparse.ArgumentParser):
    """ArgumentParser that exits with code 2 and our own prefix on bad input."""

    def error(self, message: str):
        self.print_usage(sys.stderr)
        self.exit(EXIT_INPUT, f"skillscope: error: {message}\n")


def build_parser() -> argparse.ArgumentParser:
    parser = _Parser(
        prog="skillscope",
        description="Bundle-level checks for folders of Agent Skills (SKILL.md).",
        epilog=EXIT_HELP,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--version", action="version", version=f"skillscope {__version__}")
    sub = parser.add_subparsers(dest="command", required=True, parser_class=_Parser)

    def add(name: str, help_text: str, epilog: str) -> argparse.ArgumentParser:
        p = sub.add_parser(name, help=help_text, description=help_text, epilog=epilog,
                           formatter_class=argparse.RawDescriptionHelpFormatter)
        p.add_argument("path", type=Path, help="bundle directory to scan")
        p.add_argument("--json", action="store_true", help="print JSON instead of text")
        return p

    p_check = add("check", "Run spec and bundle rules on every skill.",
                  "exit codes: 0 no errors (warnings allowed), 1 errors found "
                  "(or any warning with --strict), 2 input error")
    p_check.add_argument("--strict", action="store_true", help="treat warnings as failures")

    p_col = add("collisions", "List skill pairs whose descriptions overlap.",
                "exit codes: 0 no pair at or above the threshold, 1 pairs found, 2 input error")
    p_col.add_argument("--threshold", type=_threshold, default=DEFAULT_THRESHOLD,
                       help=f"Jaccard similarity to report, 0-1 (default {DEFAULT_THRESHOLD})")

    add("budget", "Estimate the token cost of the bundle.",
        "exit codes: 0 success, 2 input error")

    sub.add_parser("rules", help="List rule IDs and what they check.")
    return parser


def _cmd_check(skills, args) -> int:
    findings = check(skills)
    errors = sum(f.severity == "error" for f in findings)
    warnings = len(findings) - errors
    if args.json:
        print(json.dumps({"skills_scanned": len(skills), "errors": errors,
                          "warnings": warnings,
                          "findings": [f.to_dict() for f in findings]}, indent=2))
    else:
        for f in findings:
            where = f"{f.skill}/SKILL.md" + (f":{f.line}" if f.line else "")
            print(f"{where}: {f.severity} {f.rule} {f.message}")
        print(f"{len(skills)} skill(s) scanned: {errors} error(s), {warnings} warning(s)")
    failed = errors > 0 or (args.strict and warnings > 0)
    return EXIT_FINDINGS if failed else EXIT_OK


def _cmd_collisions(skills, args) -> int:
    pairs = find_collisions(skills, args.threshold)
    if args.json:
        print(json.dumps({"threshold": args.threshold, "pairs": pairs}, indent=2))
    else:
        for p in pairs:
            print(f"{p['score']:.2f}  {p['a']}  <->  {p['b']}")
            print(f"      shared: {', '.join(p['shared'])}")
        print(f"{len(pairs)} overlapping pair(s) at threshold {args.threshold}")
    return EXIT_FINDINGS if pairs else EXIT_OK


def _cmd_budget(skills, args) -> int:
    report = budget(skills)
    if args.json:
        print(json.dumps(report, indent=2))
        return EXIT_OK
    width = max(len("skill"), *(len(r["skill"]) for r in report["skills"]))
    print(f"{'skill':<{width}}  startup  body  lines")
    for r in report["skills"]:
        note = "  (unparseable)" if r["parse_error"] else ""
        print(f"{r['skill']:<{width}}  {r['metadata_tokens']:>7}  {r['body_tokens']:>4}"
              f"  {r['body_lines']:>5}{note}")
    t = report["totals"]
    print(f"total: {t['skills']} skill(s), ~{t['startup_tokens']} tokens loaded at startup, "
          f"~{t['body_tokens']} tokens of bodies (estimate: {report['estimate']})")
    return EXIT_OK


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.command == "rules":
        for rule_id, text in RULES.items():
            print(f"{rule_id}  {text}")
        return EXIT_OK
    try:
        skills = discover(args.path)
    except BundleError as exc:
        print(f"skillscope: error: {exc}", file=sys.stderr)
        return EXIT_INPUT
    handlers = {"check": _cmd_check, "collisions": _cmd_collisions, "budget": _cmd_budget}
    return handlers[args.command](skills, args)

