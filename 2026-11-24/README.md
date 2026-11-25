# SkillScope — week of 2026-11-24

**Pitch:** a zero-dependency CLI that checks a whole folder of Agent Skills at once. It finds skills that trigger on the same words, duplicate names, broken file links, and the folder's combined token cost.

The runnable starter is in [`scaffold/`](scaffold/). Its README has install steps, real example output and the rule list.

## Inspiration (GitHub Trending, daily, fetched 2026-11-24)

| # | Repo | Language | Stars | Idea borrowed |
|---|---|---|---|---|
| 1 | [elementalsouls/Claude-BugHunter](https://github.com/elementalsouls/Claude-BugHunter) | Python | 15,897 | Skill bundles are getting big (it ships 82 skills and 15 slash commands). With that many skills, two skills competing for the same request becomes a real risk. That risk is what `collisions` measures. |
| 2 | [obra/superpowers](https://github.com/obra/superpowers) | Shell | 323,660 | Treating skills as an engineering discipline. A skill library deserves the same automated quality checks as code. |
| 3 | [HKUDS/CLI-Anything](https://github.com/HKUDS/CLI-Anything) | Python | 62,021 | Ship it as a plain CLI with `--json` output and stable exit codes, so agents and CI pipelines can call it, not only people. |
| 4 | [jingyaogong/minimind](https://github.com/jingyaogong/minimind) | Python | 68,112 | Build small things from scratch. No PyYAML: a small, strict frontmatter parser written for this job, and only the standard library. |
| 5 | [cursor/plugins](https://github.com/cursor/plugins) | TypeScript | 18,076 | A published spec as the contract. Seven of the eleven `check` rules restate constraints from the Agent Skills specification (marked "spec" in the rules table). |

Stack rule: 3 of the 5 are Python (BugHunter, CLI-Anything, minimind), so the run built a Python CLI.

## Core features

- `skillscope check DIR`: 11 rules (SS001–SS011). Seven come from the Agent Skills spec; duplicate names (SS008) and broken relative links (SS009) are bundle-level; two are size warnings.
- `skillscope collisions DIR`: pairwise word-overlap (Jaccard) score of every two skill descriptions, with the shared words shown.
- `skillscope budget DIR`: estimated tokens loaded at startup for the whole folder, plus each skill's body cost.
- `--json` on every scanning command; exit codes 0 / 1 / 2 (clean / findings / input error).
- 62 pytest tests, run against a real install from a different folder.

## Why it's different from the trending repos

Each claim below can be checked:

1. **It is not a wrapper or a clone.** No file in `scaffold/src/` imports or calls code from any of the five repos. `grep -rn "^import\|^from" --include='*.py' scaffold/src` shows only the standard library and its own modules.
2. **Zero runtime dependencies.** `dependencies = []` in `scaffold/pyproject.toml`.
3. **It compares skills with each other.** Going by the five repos' own descriptions, three of them (BugHunter, superpowers, cursor/plugins) publish skills or plugin specs, CLI-Anything makes software agent-native, and minimind trains a model. None of those descriptions mentions a tool that compares skill descriptions with each other. I did not audit their full source.
4. **Honest about prior art.** The Agent Skills spec has an official single-skill validator (`skills-ref validate`) that "checks that your SKILL.md frontmatter is valid and follows all naming conventions". skillscope overlaps with it on SS002–SS007. What it adds is the bundle view: SS008, SS009, `collisions` and `budget`. I did not check whether newer versions of skills-ref cover links or overlap.

## Status labels

- **VERIFIED (this run, Linux, Python 3.13):** 62 tests passed from a clean venv install, run from a folder outside the source tree. The CLI commands and outputs shown in `scaffold/README.md` were captured from that install. An independent checker also installed it on Python 3.11 (42 tests at the time, before the fixes) and found no crash under adversarial input.
- **PROPOSED:** that the 0.3 collision threshold is useful on real bundles (only tested on small examples), and that the tool works on Windows (written to be cross-platform, not run there).
- **NOT CHECKED:** the star counts are copied from the GitHub Trending page as fetched; they were not re-checked against the GitHub API.
