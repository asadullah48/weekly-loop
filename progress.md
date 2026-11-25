# Weekly Loop — cumulative progress log

One entry per weekly run. Newest first.

## 2026-11-24 — SkillScope

**Continuity check:** Week 3. The Gmail search for `subject:"Weekly Loop Project"` found one earlier run, 2026-11-17 (PreflightKit, main inspiration sherlock-project/sherlock). This repo's log also records a week 1 run on 2026-11-10 (agentscan v0.2.0), which has no matching email. None of this week's trending repos were used in earlier weeks, and this week's idea is not a repeat. The repo README noted that the 11-17 trending list was probably stale. This week's fetch was fresh: the page showed "stars today" counts and a completely different top 5.

**Trending repos this week (top 5, language-agnostic, from github.com/trending, fetched 2026-11-24):**

| Repo | Language | Stars | Description |
|---|---|---|---|
| elementalsouls/Claude-BugHunter | Python | 15,897 | Claude Code skill bundle for bug hunting and red-team work: 82 skills, 15 slash commands |
| obra/superpowers | Shell | 323,660 | An agentic skills framework and software development methodology |
| HKUDS/CLI-Anything | Python | 62,021 | Making all software agent-native through CLIs |
| jingyaogong/minimind | Python | 68,112 | Train your own 64M LLM from scratch in 2 hours |
| cursor/plugins | TypeScript | 18,076 | Cursor plugin specification and official plugins |

**Synthesized idea: SkillScope (`skillscope`).** A zero-dependency Python CLI that checks a whole folder of Agent Skills (SKILL.md) at once:
- `collisions`: pairs of skills whose descriptions overlap enough that an agent may pick the wrong one;
- `check`: 11 rules, covering spec frontmatter rules plus duplicate names and broken relative links;
- `budget`: estimated tokens loaded at startup for the whole folder, and each skill's body cost.

Why this gap: three of the five repos ship skills, skill frameworks or plugin specs, and skill bundles are getting big (82 skills in one repo). Going by their descriptions, none of them compares skills with each other. Prior art, stated honestly: the Agent Skills spec has an official single-skill validator, `skills-ref validate`. SkillScope overlaps with it on frontmatter rules. What it adds is the bundle view. Stack rule: 3 of the 5 are Python, so it is a Python CLI.

**What got built (2026-11-24/scaffold/):**
- Installable package `skillscope`: setuptools, src layout, standard library only, MIT.
- The stopword list ships as package data (`data/stopwords.txt`), and the installed wheel was checked to contain it. This guards against the earlier "data file not packaged" crash.
- A strict frontmatter parser for the YAML subset that SKILL.md files use, written for this project.
- A demo bundle with deliberate mistakes.
- 62 pytest tests.

**VERIFIED:** clean venv, tests copied outside the source tree and run against the installed package: 62 passed (Linux, Python 3.13). Every command and output shown in the scaffold README was re-captured from the installed CLI, run from another folder. Exit codes: check 1, collisions 1, budget 0, and 2 for a bad path or a bad threshold.

**Checker (independent subagent, fresh read, its own venv on Python 3.13 and 3.11, adversarial inputs):** it confirmed the original packaging, the 42 tests passing at the time, character-exact README output, and no crashes. It also found real bugs, all fixed with a regression test each:
1. An indented `---` inside a block scalar ended the frontmatter early, so the description was cut off without any error. The closing delimiter now has to start at column 0.
2. A quoted value followed by a `# comment` was wrongly flagged as SS001. Fixed.
3. `description: ~` / `null` passed as valid. These are now read as missing, so SS005 fires.
4. SS009 false errors on `my%20file.md` and `file(1).md`. Targets are now URL-decoded, and parentheses in paths are handled.
5. SS009 flagged links inside indented code, HTML comments, ```` ```` ```` fences, and fences of mixed type. Fence character and length are now tracked; indented code and comments are skipped.
6. SS009 missed `<angle bracket>` targets, `(title)` and `"it's"` titles, nested link text, and reference-style links. All are now detected.
7. `str.splitlines()` also splits on form feeds and Unicode separators, which shifted line numbers and counts. Splitting now uses only `\n`, `\r\n` and `\r`.
8. Block scalars lost paragraph breaks (`>`) and relative indentation (`|`). Now dedented correctly.
9. The parser silently accepted uneven nested indentation, duplicate nested keys and `| text`. These now raise errors.
10. Plural stripping missed `pdfs` and `docs` and cut `analysis` to `analysi`. Fixed: `-ss`, `-us` and `-is` words are kept.
11. The tokenizer only understood ASCII. It now keeps Unicode words; the README notes that it works best for space-separated languages.
12. The `budget` table header was misaligned when all paths were short. Fixed.
13. A repo with skills under `.claude/skills/` reported "no SKILL.md files" with no explanation. The error now says how many files were skipped and to pass `.claude/skills`.
Also from its list:
- the SS002/SS005 messages now say "missing or empty";
- the scaffold README no longer claims Windows works (written to be cross-platform, tested on Linux only);
- the main README no longer claims a line-by-line spec mapping;
- the grep in the originality claim now uses `--include='*.py'`;
- dead code removed from conftest;
- a `__main__` guard added;
- `\n`/`\t` escapes decoded;
- symlink skipping and the remaining limits documented.

**Left for a future pass (logged, not fixed):** quoted keys are rejected (documented); a plain value containing `: ` is accepted although strict YAML rejects it (documented); links that leave the skill folder (`../`) are not flagged; `C:/` paths are skipped; collision scores show 2 decimals in text and 3 in JSON; the checker could not confirm star counts through the GitHub API.

**Delivery:** a git push to asadullah48/weekly-loop was tried once. On failure, the fallback was to email the zip to texcotembroiderysourcinghouse@gmail.com with manual push steps.

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
