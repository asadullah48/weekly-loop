import json
import subprocess
import sys

import pytest

from skillscope.cli import main


def run(*args):
    return main([str(a) for a in args])


def test_check_exit_codes(make_skill, capsys):
    root = make_skill("good", "name: good\ndescription: fine")
    assert run("check", root) == 0
    make_skill("Bad", "name: Bad\ndescription: fine")
    assert run("check", root) == 1
    out = capsys.readouterr().out
    assert "Bad/SKILL.md: error SS003" in out
    assert "2 skill(s) scanned: 1 error(s), 0 warning(s)" in out


def test_check_strict_fails_on_warnings(make_skill):
    root = make_skill("big", "name: big\ndescription: fine", "line\n" * 501)
    assert run("check", root) == 0
    assert run("check", "--strict", root) == 1


def test_check_json(make_skill, capsys):
    root = make_skill("other", "name: mismatch\ndescription: fine")
    assert run("check", "--json", root) == 1
    data = json.loads(capsys.readouterr().out)
    assert data["errors"] == 1 and data["skills_scanned"] == 1
    assert data["findings"][0]["rule"] == "SS004"


def test_collisions_exit_codes_and_json(make_skill, capsys):
    make_skill("a", "name: a\ndescription: Extract PDF tables.")
    root = make_skill("b", "name: b\ndescription: Extract PDF tables now.")
    assert run("collisions", "--json", root) == 1
    data = json.loads(capsys.readouterr().out)
    assert data["pairs"][0]["shared"] == ["extract", "pdf", "table"]
    assert run("collisions", "--threshold", "1", root) == 0


@pytest.mark.parametrize("bad", ["0", "1.5", "abc"])
def test_bad_threshold_is_input_error(make_skill, bad):
    root = make_skill("a", "name: a\ndescription: x")
    with pytest.raises(SystemExit) as exc:
        run("collisions", "--threshold", bad, root)
    assert exc.value.code == 2


def test_budget_text(make_skill, capsys):
    root = make_skill("a", "name: a\ndescription: abcd", "x" * 8)
    assert run("budget", root) == 0
    assert "~2 tokens loaded at startup, ~2 tokens of bodies" in capsys.readouterr().out


def test_input_errors_exit_2(tmp_path, capsys):
    assert run("check", tmp_path / "missing") == 2
    assert run("budget", tmp_path) == 2
    assert "no SKILL.md files found" in capsys.readouterr().err


def test_rules_command_lists_all_ids(capsys):
    assert run("rules") == 0
    out = capsys.readouterr().out
    assert out.count("SS0") == 11


def test_module_entry_point_runs(make_skill):
    root = make_skill("good", "name: good\ndescription: fine")
    proc = subprocess.run([sys.executable, "-m", "skillscope", "check", str(root)],
                          capture_output=True, text=True)
    assert proc.returncode == 0, proc.stderr
    assert "0 error(s)" in proc.stdout


def test_budget_header_aligns_with_short_paths(make_skill, capsys):
    root = make_skill("a", "name: a\ndescription: abcd")
    run("budget", root)
    header, row = capsys.readouterr().out.splitlines()[:2]
    assert header.index("startup") + len("startup") == row.index("2") + 1
