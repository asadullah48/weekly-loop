# Weekly Loop — cumulative progress log

One entry per weekly run. Newest first.

## 2026-11-17 — PreflightKit

**Continuity check:** Week 2. Week 1 (2026-11-10, agentscan v0.2.0) is not yet in this repo. The 11-17 run's Gmail search missed it.

**Trending repos this week (top 5, language-agnostic, from github.com/trending):**

| Repo | Language | Stars | Description |
|---|---|---|---|
| sherlock-project/sherlock | Python | 103,430 | Hunt social media accounts by username across networks |
| dsx-ai-factory/nvke | Go | 840 | NVIDIA Kubernetes Engine — management plane for GPU Kubernetes |
| milind-soni/OpenMausBot | TypeScript | 18,228 | Open-source Grok Bot alternative with a VM bots can use |
| anthropics/claude-quickstarts | Python | 19,406 | Starter projects for building with the Claude API |
| vercel-labs/agent-browser | Rust | 47,569 | Browser automation CLI for AI agents |

**Synthesized idea — PreflightKit (`preflight`):** a zero-dependency Python CLI that probes an AI agent sandbox's *real* capabilities before the agent runs — which commands are on PATH, which Python modules import, which env vars are set, which paths are writable, which hosts accept TCP connections — and turns the result into a JSON capability manifest plus an `assert` command with a CI-friendly exit-code contract (0 met / 1 unmet / 2 input error). Why this gap: all five trending repos either assume an environment (quickstarts), provide one (OpenMausBot's VM), manage remote infrastructure (nvke), probe remote sites (sherlock), or give agents a tool (agent-browser) — none checks what the local sandbox can actually do. Stack rule: top 5 were 2× Python, 1× Go, 1× TS, 1× Rust → neither threshold hit → default Python CLI.

**What got built (2026-11-17/scaffold/):** installable package `preflightkit` (setuptools, stdlib only, no data files), console script `preflight` with `scan` / `scan --json` / `scan --strict` / `assert` / `init`, a `preflight.json` cwd config merge, and a 26-test pytest suite. Verified from a real install in a clean venv, run from a different cwd: 25 passed / 1 intentional root-skip; smoke tests confirmed the full exit-code contract (0/1/2) on the installed CLI.

**Checker (independent subagent, fresh read + its own venv install and runs) found, and what was fixed:**
1. Build artifacts committed in the tree (build/, egg-info, __pycache__, .pytest_cache), no .gitignore → all removed; .gitignore added.
2. README claimed `init` writes a "commented example" — JSON can't carry comments → wording fixed.
3. README claimed the exit-code contract is "documented in `preflight assert --help`" but it wasn't → an epilog was added to the assert subcommand so the claim is now true (verified in help output).
4. A misleading sentence in scaffold/README.md about when network probes run → rewritten accurately.
Also picked up from its nitpicks: MIT LICENSE file added (pyproject declared MIT without one), a stale test comment fixed, and the bare-IPv6 parsing limitation documented in Known limits. Remaining nitpicks (inconsistent error prefix for a bad port inside a requirements file, duplicate host specs probing twice, PyPI long_description referencing the repo-level README) are logged here honestly and left for a future pass. The checker verified every documented command, flag, output and exit code against the running code and confirmed originality vs all five source repos (stdlib-only imports, no wrapper).

**Re-verification after fixes:** full suite re-run from a reinstall in the clean venv (25 passed, 1 skipped), `assert --help` now shows the exit codes, `scan` still 17/17 in this sandbox.

**Delivery:** git push to asadullah48/weekly-loop attempted per pipeline; on the known sandbox git-proxy restriction, fell back to emailing the zip to texcotembroiderysourcinghouse@gmail.com with manual push instructions.
