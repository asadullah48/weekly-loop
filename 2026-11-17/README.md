# PreflightKit

**One-line pitch:** A zero-dependency Python CLI that probes an AI agent's sandbox *before* the agent runs — which commands exist, which hosts are reachable, which paths are writable, which env vars are set — and turns the result into a machine-readable capability manifest that a harness can `assert` against, so agents fail fast with a clear report instead of failing mid-task.

Built for the Weekly Loop (2026-11-17), inspired by the day's GitHub Trending repos.

## Inspiration table

| # | Trending repo | Language | Stars (at fetch) | Idea borrowed |
|---|---|---|---|---|
| 1 | [sherlock-project/sherlock](https://github.com/sherlock-project/sherlock) | Python | 103,430 | Fan out many small presence/absence probes in parallel and report hits and misses in one pass |
| 2 | [dsx-ai-factory/nvke](https://github.com/dsx-ai-factory/nvke) | Go | 840 | A "management plane" mindset: inventory what the infrastructure actually offers instead of assuming it |
| 3 | [milind-soni/OpenMausBot](https://github.com/milind-soni/OpenMausBot) | TypeScript | 18,228 | Bots get a VM to work in — which means the VM's real capabilities, not its advertised ones, decide what the bot can do |
| 4 | [anthropics/claude-quickstarts](https://github.com/anthropics/claude-quickstarts) | Python | 19,406 | Starter templates silently assume an environment (keys set, network open); those assumptions should be checkable |
| 5 | [vercel-labs/agent-browser](https://github.com/vercel-labs/agent-browser) | Rust | 47,569 | CLI tools built *for* agents: plain-text/JSON output, non-interactive, exit codes a harness can branch on |

## Core features

- `preflight scan` — run the built-in probe set (commands, Python modules, env vars, path writability, network reachability) and print a human-readable table.
- `preflight scan --json` — same scan, but emit a JSON **capability manifest** for a harness or agent to consume.
- `preflight assert <requirements.json>` — check a JSON requirements file against a fresh scan; exit `0` if every requirement is met, exit `1` and list each unmet requirement otherwise.
- `preflight init` — write an example `preflight-requirements.json` into the current directory to start from.
- Custom probes: a `preflight.json` config in the working directory can add extra commands, modules, env vars, paths, and hosts to the scan — no packaged data files, plain JSON read at runtime.
- Zero third-party dependencies: standard library only (`argparse`, `shutil`, `socket`, `importlib`, `json`, `concurrent.futures`).

## Why it's different from the trending repos

Specific, checkable claims:

1. **None of the five repos probes the local execution environment.** sherlock probes *remote* social sites for usernames; agent-browser automates a browser; OpenMausBot provides a VM; nvke manages GPU Kubernetes; claude-quickstarts are app templates. PreflightKit's subject is the sandbox itself — `shutil.which`, `importlib.util.find_spec`, socket connects, and `os.access`/tempfile write checks against the local machine. You can verify this by reading `src/preflightkit/probes.py`: there is no browser driver, no social-site list, and no Kubernetes client.
2. **It is not a wrapper around any of them.** The package imports only the Python standard library (check `pyproject.toml`: the `dependencies` list is empty).
3. **It adds an `assert` contract none of them have:** a requirements JSON → exit-code contract (`0` met / `1` unmet / `2` usage error) designed for CI steps and agent harnesses, documented in `preflight assert --help` and tested in `tests/test_assertions.py`.
4. **Scope is deliberately narrow:** it answers "what can this environment do right now?" and nothing else — no task execution, no browsing, no account hunting.

## Quick start

```bash
pip install ./scaffold          # from this folder
preflight scan                  # human-readable report
preflight scan --json           # capability manifest
preflight init                  # writes preflight-requirements.json
preflight assert preflight-requirements.json
```

## Status

Week-of-2026-11-17 starter scaffold: working CLI, probe engine, assert contract, and a pytest suite. Not yet a finished product — see `scaffold/README.md` for limits and next steps.
