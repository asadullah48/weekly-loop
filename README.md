# weekly-loop

An automated weekly experiment. Every Tuesday a loop looks at GitHub Trending and builds one small starter project inspired by it. This is a practice log, not a flagship project.

## Weeks

| Week | Project | Folder |
|---|---|---|
| 2026-11-17 | PreflightKit | [2026-11-17/](2026-11-17/) |

## Status

- **VERIFIED** (run by hand on Windows 11, Python via uv, fresh isolated env, tests run from a different folder, 2026-11-20):
  - PreflightKit test suite, Windows 11, Python 3.13.9: 25 passed, 1 skipped. The skip is `test_probe_path_readonly`, which needs a POSIX non-root user. Its skip condition was fixed in this commit; before the fix it failed on Windows because `os.geteuid()` does not exist there.
  - Installed `preflight` CLI exit codes: `assert` gave 0 when all requirements were met, 1 when one was unmet, and 2 for a bad section, bad JSON, or a missing file. `scan --json` exited 0 and printed a valid manifest.
- **REPORTED** (from the run's email, not re-checked): 25 passed and 1 skipped on Linux (skip = root-only test); an independent checker found and fixed 4 issues (see [progress.md](progress.md)).
- **PROPOSED**: the "gap" claim that none of that week's trending repos checks the local sandbox's own capabilities.
- **NOTE**: the 2026-11-17 trending list has the same repos and star counts as the 2026-11-10 run, so it is probably stale data, not a fresh fetch.
