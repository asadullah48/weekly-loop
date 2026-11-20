# preflightkit (scaffold)

Probe an AI agent sandbox's real capabilities — commands, Python modules, env vars, writable paths, network reachability — and assert a requirements file against them. Standard library only.

See the top-level `README.md` (one folder up) for the idea, the inspiration table, and the full pitch.

## Install

```bash
pip install .
```

## Use

```bash
preflight scan                       # human-readable report of the default probe set
preflight scan --json                # JSON capability manifest
preflight scan --strict              # exit 1 if any probe fails
preflight init                       # write an example preflight-requirements.json
preflight assert preflight-requirements.json   # exit 0 all met / 1 unmet / 2 input error
```

Add a `preflight.json` in your working directory to extend the scan:

```json
{ "commands": ["docker"], "env": ["OPENAI_API_KEY"], "network": ["api.github.com:443"] }
```

`preflight assert` probes exactly what the requirements file names (plus any
`preflight.json`), so results are deterministic for CI.

## Tests

```bash
pip install pytest
pytest
```

The test suite runs fully offline: network probing is unit-tested only at the
parsing level, and every CLI test uses an empty network list. The tool itself
does run real network probes whenever `scan`'s default host list or an
`assert` requirements file names hosts.

## Known limits (starter scaffold)

- Network probe is a TCP connect, not an HTTP request — a proxy that accepts
  connections but blocks requests will look reachable.
- No version constraints yet (e.g. "node >= 20"); probes are presence-only.
- No concurrency for non-network probes (they are fast enough locally).
- Bare IPv6 addresses (e.g. `::1`) are mis-parsed as `host:port` specs; use
  hostnames for now.
