import pytest

from skillscope.bundle import BundleError, discover
from skillscope.rules import check


def rules_for(root):
    return sorted((f.skill, f.rule) for f in check(discover(root)))


def test_clean_skill_has_no_findings(make_skill):
    root = make_skill("good-skill", "name: good-skill\ndescription: Does a clear thing.")
    assert rules_for(root) == []


@pytest.mark.parametrize(
    "dirname, frontmatter, rule",
    [
        ("a", "description: x", "SS002"),
        ("Bad-Name", "name: Bad-Name\ndescription: x", "SS003"),
        ("pdf--x", "name: pdf--x\ndescription: x", "SS003"),
        ("other", "name: mismatch\ndescription: x", "SS004"),
        ("empty", "name: empty\ndescription: \"\"", "SS005"),
        ("long", "name: long\ndescription: " + "x" * 1025, "SS006"),
        ("compat", "name: compat\ndescription: x\ncompatibility: " + "y" * 501, "SS007"),
    ],
)
def test_spec_rules(make_skill, dirname, frontmatter, rule):
    root = make_skill(dirname, frontmatter)
    assert (dirname, rule) in rules_for(root)


def test_unparseable_frontmatter_is_ss001(make_skill):
    root = make_skill("ok", "name: ok\ndescription: fine")
    (root / "broken").mkdir()
    (root / "broken" / "SKILL.md").write_text("no frontmatter here\n", encoding="utf-8")
    assert rules_for(root) == [("broken", "SS001")]


def test_duplicate_names_flag_both_skills(make_skill):
    make_skill("one/dup", "name: dup\ndescription: first")
    root = make_skill("two/dup", "name: dup\ndescription: second")
    assert rules_for(root) == [("one/dup", "SS008"), ("two/dup", "SS008")]


def test_broken_and_valid_links(make_skill):
    body = (
        "See [ok](ref.md) and [missing](refs/nope.md#part) and ![img](pic.png).\n"
        "Ignore [web](https://example.com), [anchor](#top), `[code](x.md)`.\n"
        "```\n[fenced](also-missing.md)\n```\n"
    )
    root = make_skill("links", "name: links\ndescription: x", body)
    (root / "links" / "ref.md").write_text("ok", encoding="utf-8")
    findings = [f for f in check(discover(root)) if f.rule == "SS009"]
    assert [f.message for f in findings] == [
        "link target 'refs/nope.md' not found",
        "link target 'pic.png' not found",
    ]
    assert all(f.line == 5 for f in findings)  # body starts on line 5


def test_size_warnings(make_skill):
    body = "line\n" * 501 + "x" * 20001
    root = make_skill("big", "name: big\ndescription: x", body)
    found = {(f.rule, f.severity) for f in check(discover(root))}
    assert found == {("SS010", "warning"), ("SS011", "warning")}


def test_hidden_and_vendor_dirs_are_skipped(make_skill):
    make_skill(".git/hidden", "name: hidden\ndescription: x")
    make_skill("node_modules/dep", "name: dep\ndescription: x")
    root = make_skill("real", "name: real\ndescription: x")
    assert [s.rel for s in discover(root)] == ["real"]


def test_bundle_errors(tmp_path):
    with pytest.raises(BundleError, match="does not exist"):
        discover(tmp_path / "missing")
    with pytest.raises(BundleError, match="no SKILL.md"):
        discover(tmp_path)


def test_null_description_is_ss005(make_skill):
    root = make_skill("nulled", "name: nulled\ndescription: ~")
    assert rules_for(root) == [("nulled", "SS005")]


def test_links_inside_code_and_comments_are_ignored(make_skill):
    body = (
        "Intro.\n"
        "\n"
        "    [indented](gone-indented.md)\n"
        "\n"
        "<!-- [c](gone-comment.md) -->\n"
        "<!--\n[multi](gone-multi.md)\n-->\n"
        "````\n```\n[four](gone-four.md)\n````\n"
        "```python\n~~~\n[mixed](gone-mixed.md)\n```\n"
        "[real](gone-real.md)\n"
    )
    root = make_skill("code", "name: code\ndescription: x", body)
    found = [f.message for f in check(discover(root)) if f.rule == "SS009"]
    assert found == ["link target 'gone-real.md' not found"]


def test_link_target_forms(make_skill):
    body = (
        "[enc](my%20file.md) [paren](file(1).md) [ok](<my file.md>)\n"
        "[a](<gone file.md>) [t](gone1.md (Title)) [q](gone2.md \"it's\")\n"
        "[nested [b]](gone-nested.md) [ref][r]\n"
        "\n"
        "[r]: gone-ref.md\n"
    )
    root = make_skill("forms", "name: forms\ndescription: x", body)
    (root / "forms" / "my file.md").write_text("ok", encoding="utf-8")
    (root / "forms" / "file(1).md").write_text("ok", encoding="utf-8")
    found = [f.message for f in check(discover(root)) if f.rule == "SS009"]
    assert found == [
        "link target 'gone file.md' not found",
        "link target 'gone1.md' not found",
        "link target 'gone2.md' not found",
        "link target 'gone-nested.md' not found",
        "link target 'gone-ref.md' not found",
    ]


def test_hidden_folder_hint(make_skill):
    root = make_skill(".claude/skills/deploy", "name: deploy\ndescription: x")
    with pytest.raises(BundleError, match=r"1 skipped .*\.claude/skills"):
        discover(root)
    assert [s.rel for s in discover(root / ".claude" / "skills")] == ["deploy"]
