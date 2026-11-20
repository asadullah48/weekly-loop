import os

import pytest

from preflightkit.probes import (
    ProbePlan,
    _parse_host_port,
    probe_command,
    probe_env,
    probe_module,
    probe_path_writable,
    run_plan,
)


def test_probe_command_found():
    # "env" is POSIX-guaranteed, so this passes on any Unix-like system.
    result = probe_command("env")
    assert result.ok
    assert result.kind == "command"


def test_probe_command_missing():
    result = probe_command("definitely-not-a-real-binary-xyz")
    assert not result.ok
    assert result.detail == "not on PATH"


def test_probe_module_found_and_missing():
    assert probe_module("json").ok
    assert not probe_module("definitely_not_a_module_xyz").ok


def test_probe_env(monkeypatch):
    monkeypatch.setenv("PREFLIGHT_TEST_VAR", "1")
    assert probe_env("PREFLIGHT_TEST_VAR").ok
    monkeypatch.delenv("PREFLIGHT_TEST_VAR")
    assert not probe_env("PREFLIGHT_TEST_VAR").ok
    monkeypatch.setenv("PREFLIGHT_TEST_VAR", "")
    assert not probe_env("PREFLIGHT_TEST_VAR").ok, "empty value counts as unset"


def test_probe_env_never_records_value(monkeypatch):
    monkeypatch.setenv("PREFLIGHT_SECRET", "hunter2")
    result = probe_env("PREFLIGHT_SECRET")
    assert "hunter2" not in result.detail


def test_probe_path_writable(tmp_path):
    assert probe_path_writable(str(tmp_path)).ok
    missing = tmp_path / "does-not-exist"
    result = probe_path_writable(str(missing))
    assert not result.ok
    assert result.detail == "not a directory"


@pytest.mark.skipif(not hasattr(os, "geteuid") or os.geteuid() == 0, reason="needs POSIX non-root user")
def test_probe_path_readonly(tmp_path):
    ro = tmp_path / "ro"
    ro.mkdir()
    ro.chmod(0o555)
    try:
        result = probe_path_writable(str(ro))
        if os.geteuid() == 0:
            pytest.skip("running as root: chmod does not block writes")
        assert not result.ok
    finally:
        ro.chmod(0o755)


def test_parse_host_port():
    assert _parse_host_port("github.com") == ("github.com", 443)
    assert _parse_host_port("db.local:5432") == ("db.local", 5432)
    with pytest.raises(ValueError):
        _parse_host_port("host:notaport")


def test_plan_merge_dedup_and_validation():
    plan = ProbePlan(commands=["git"]).merge({"commands": ["git", "jq"], "env": ["HOME"]})
    assert plan.commands == ["git", "jq"]
    assert plan.env == ["HOME"]
    with pytest.raises(ValueError):
        ProbePlan().merge({"nonsense": []})
    with pytest.raises(ValueError):
        ProbePlan().merge({"commands": "git"})
    with pytest.raises(ValueError):
        ProbePlan().merge({"commands": [1]})


def test_run_plan_offline_sections(tmp_path):
    plan = ProbePlan(
        commands=["env", "no-such-cmd-xyz"],
        modules=["json"],
        env=["HOME"],
        paths=[str(tmp_path)],
        network=[],  # keep this test offline
    )
    results = run_plan(plan)
    assert len(results) == 5
    by_target = {(r.kind, r.target): r.ok for r in results}
    assert by_target[("command", "env")]
    assert not by_target[("command", "no-such-cmd-xyz")]
    assert by_target[("module", "json")]
    assert by_target[("path", str(tmp_path))]
