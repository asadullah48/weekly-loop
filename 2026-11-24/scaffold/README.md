# skillscope

Bundle-level checks for a folder of [Agent Skills](https://agentskills.io/specification) (`SKILL.md` files).

Validators usually look at one skill at a time. skillscope looks at the whole folder and answers three questions:

1. **Will the agent pick the right skill?** `collisions` finds pairs of skills whose descriptions overlap so much that an agent may activate the wrong one.
2. **Is anything broken?** `check` finds duplicate names, relative links to files that don't exist, and frontmatter that breaks the spec.
3. **What does the folder cost?** `budget` estimates the tokens loaded at startup (every skill's name and description) and the tokens each body adds once a skill is activated.

No runtime dependencies. Python 3.10+. Written to be cross-platform (standard library and `pathlib` only), but so far tested on Linux only.

## Install

```bash
pip install .            # from this folder
pip install ".[test]"    # also installs pytest
```

## Usage

The commands below run against the demo bundle in `examples/demo-bundle/`, which has mistakes in it on purpose. The output shown is real output from version 0.1.0.

```console
$ skillscope check examples/demo-bundle
Changelog-Writer/SKILL.md: error SS003 name 'Changelog-Writer' must be 1-64 chars of a-z, 0-9 and single hyphens, not starting or ending with a hyphen
pdf-forms/SKILL.md:9: error SS009 link target 'references/fields.md' not found
release-notes/SKILL.md: error SS005 'description' is missing or empty
4 skill(s) scanned: 3 error(s), 0 warning(s)
$ echo $?
1
```

```console
$ skillscope collisions examples/demo-bundle
0.44  pdf-extract  <->  pdf-forms
      shared: document, extract, file, pdf
1 overlapping pair(s) at threshold 0.3
```

```console
$ skillscope budget examples/demo-bundle
skill             startup  body  lines
Changelog-Writer       17     5      1
pdf-extract            29    19      3
pdf-forms              33    18      3
release-notes           4     4      1
total: 4 skill(s), ~83 tokens loaded at startup, ~46 tokens of bodies (estimate: characters / 4)
```

Every scanning command takes `--json` for machine-readable output. `skillscope rules` lists the rule IDs.

| Command | Options | Exit 0 | Exit 1 | Exit 2 |
|---|---|---|---|---|
| `check PATH` | `--json`, `--strict` | no errors (warnings allowed) | any error, or any warning with `--strict` | bad path / no `SKILL.md` found |
| `collisions PATH` | `--json`, `--threshold 0-1` (default 0.3) | no pair at or above the threshold | one or more pairs | bad path, or threshold not in (0, 1] |
| `budget PATH` | `--json` | report printed | — | bad path / no `SKILL.md` found |

`PATH` is the folder that holds your skills. Hidden folders inside it (such as `.claude/`) are skipped, so for a repo that keeps skills in `.claude/skills/`, run `skillscope check .claude/skills`. If every `SKILL.md` was skipped, the error message says so.

`python -m skillscope ...` works too.

## Rules

| ID | Severity | Checks | Source |
|---|---|---|---|
| SS001 | error | frontmatter missing, unclosed, or uses YAML this parser does not support | spec |
| SS002 | error | `name` missing, empty or null (`~`) | spec |
| SS003 | error | `name` is not 1-64 chars of `a-z`, `0-9` and single hyphens (no leading or trailing hyphen) | spec |
| SS004 | error | `name` differs from the skill's directory name | spec |
| SS005 | error | `description` missing, empty or null (`~`) | spec |
| SS006 | error | `description` over 1024 chars | spec |
| SS007 | error | `compatibility` over 500 chars | spec |
| SS008 | error | two or more skills in the folder use the same `name` | bundle |
| SS009 | error | a relative inline link, image or reference definition (`[r]: path`) in the body points to a missing file. Links in fenced or indented code, code spans and HTML comments are ignored; `%20`-style encoding is decoded | bundle |
| SS010 | warning | body over 500 lines | spec recommendation |
| SS011 | warning | body estimated over 5000 tokens | spec recommendation |

"Spec" means the Agent Skills specification at agentskills.io, as read on 2026-11-24. The official `skills-ref validate` tool is the reference validator for single skills. Use it alongside skillscope.

## How collisions are scored

Each description becomes a set of content words: lowercased, at least 3 characters, a plural `s` removed (`pdfs` → `pdf`, but `status`, `analysis` and `class` are kept as they are), and stopwords dropped. The stopword list ships as package data in `skillscope/data/stopwords.txt` and includes boilerplate such as "use", "when", "user" and "skill". Each pair of skills gets a Jaccard score: shared words divided by all distinct words. Pairs at or above the threshold are reported, highest first.

## Known limits

- The frontmatter parser handles the YAML subset that SKILL.md files use in practice: plain or quoted values (with `\n`, `\t`, `\"` and `\\` escapes), wrapped values, `|` and `>` block scalars, one level of nesting, comments, and `~`/`null`. Lists, flow mappings, anchors and quoted keys are reported as SS001 instead of being guessed at. One leniency: a plain value containing `: ` (for example `description: Use when: x`) is accepted, although strict YAML loaders reject it.
- Token counts are estimates (characters / 4). Real tokenizers differ.
- Collision scoring compares words, not meaning. Synonyms ("PDF" vs "Acrobat") are missed. Words are split on spaces and punctuation, so it works best for English and other space-separated languages, not Chinese or Japanese. The 0.3 default was picked on small test bundles and has not been tuned on real-world bundles yet.
- Links: link text may hold one level of nested brackets; deeper nesting is not parsed. Links that leave the skill folder (`../x.md`) are only checked for existence, not flagged.
- Hidden directories (names starting with `.`), `node_modules`, `__pycache__` and `venv` inside `PATH` are skipped. Symlinked skill folders are not followed.

## Tests

```bash
pip install ".[test]"
pytest
```

## License

MIT
