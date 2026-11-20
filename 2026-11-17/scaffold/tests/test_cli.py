import json

import pytest

from preflightkit.cli import main


@pytest.fixture
def offline_cwd(tmp_path, monkeypatch):
    """Run CLI from a temp dir with an offline, tiny probe config.

    An empty-plan scan would still use defaults, so tests that must stay
    offline write a preflight.json and pass requirements that avoid network.
    """
    monkeypatch.chdir(tmp_path)
    return tmp_path


def test_scan_table_output(offline_cwd, capsys, monkeypatch):
    # Shrink the default plan to keep the test fast and offline.
    monkeypatch.setattr(
        "preflightkit.cli.ProbePlan",
        _tiny_probe_plan_cls(),
    )
    assert main(["scan"]) == 0
    out = capsys.readouterr().out
    assert "probes passed" in out
    assert "env" in out


def test_scan_json_is_valid_manifest(offline_cwd, capsys, monkeypatch):
    monkeypatch.setattr("preflightkit.cli.ProbePlan", _tiny_probe_plan_cls())
    assert main(["scan", "--json"]) == 0
    manifest = json.loads(capsys.readouterr().out)
    assert manifest["manifest_version"] == 1
    assert "probes" in manifest and "summary" in manifest
    assert manifest["summary"]["total"] == manifest["summary"]["ok"] + manifest["summary"]["failed"]


def test_scan_strict_fails_on_missing(offline_cwd, capsys, monkeypatch):
    monkeypatch.setattr("preflightkit.cli.ProbePlan", _tiny_probe_plan_cls(bad=True))
    assert main(["scan", "--strict"]) == 1


def test_init_then_assert_roundtrip(offline_cwd, capsys):
    assert main(["init"]) == 0
    req_path = offline_cwd / "preflight-requirements.json"
    assert req_path.exists()
    # Rewrite requirements to an offline subset that must pass anywhere.
    req_path.write_text(json.dumps({"modules": ["json"], "env": ["HOME"], "paths": ["."]}))
    assert main(["assert", str(req_path)]) == 0
    assert "all requirements met" in capsys.readouterr().out


def test_init_refuses_overwrite(offline_cwd):
    assert main(["init"]) == 0
    with pytest.raises(SystemExit) as excinfo:
        main(["init"])
    assert excinfo.value.code == 2
    assert main(["init", "--force"]) == 0


def test_assert_unmet_exits_1(offline_cwd, capsys):
    req = offline_cwd / "req.json"
    req.write_text(json.dumps({"commands": ["definitely-not-a-real-binary-xyz"]}))
    assert main(["assert", str(req)]) == 1
    err = capsys.readouterr().err
    assert "unmet requirements" in err
    assert "definitely-not-a-real-binary-xyz" in err


def test_assert_missing_file_exits_2(offline_cwd):
    with pytest.raises(SystemExit) as excinfo:
        main(["assert", "nope.json"])
    assert excinfo.value.code == 2


def test_assert_bad_json_exits_2(offline_cwd):
    bad = offline_cwd / "bad.json"
    bad.write_text("{not json")
    with pytest.raises(SystemExit) as excinfo:
        main(["assert", str(bad)])
    assert excinfo.value.code == 2


def test_assert_unknown_section_exits_2(offline_cwd):
    bad = offline_cwd / "bad.json"
    bad.write_text(json.dumps({"wheels": ["round"]}))
    with pytest.raises(SystemExit) as excinfo:
        main(["assert", str(bad)])
    assert excinfo.value.code == 2


def test_config_merge_applies(offline_cwd, capsys, monkeypatch):
    monkeypatch.setattr("preflightkit.cli.ProbePlan", _tiny_probe_plan_cls())
    (offline_cwd / "preflight.json").write_text(json.dumps({"env": ["PREFLIGHT_EXTRA"]}))
    monkeypatch.setenv("PREFLIGHT_EXTRA", "1")
    assert main(["scan"]) == 0
    assert "PREFLIGHT_EXTRA" in capsys.readouterr().out


def test_bad_config_exits_2(offline_cwd, monkeypatch):
    monkeypatch.setattr("preflightkit.cli.ProbePlan", _tiny_probe_plan_cls())
    (offline_cwd / "preflight.json").write_text(json.dumps({"bogus": []}))
    with pytest.raises(SystemExit) as excinfo:
        main(["scan"])
    assert excinfo.value.code == 2


def _tiny_probe_plan_cls(bad: bool = False):
    """A ProbePlan replacement whose default() is tiny and offline."""
    from preflightkit.probes import ProbePlan

    class TinyPlan(ProbePlan):
        @classmethod
        def default(cls):
            commands = ["definitely-not-a-real-binary-xyz"] if bad else []
            return cls(commands=commands, modules=["json"], env=["HOME"], paths=["."], network=[])

    return TinyPlan
