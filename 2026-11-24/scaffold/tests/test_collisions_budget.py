from skillscope.budget import budget, estimate_tokens
from skillscope.bundle import discover
from skillscope.collisions import find_collisions, jaccard, stopwords, terms


def test_stopwords_ship_as_package_data():
    # Fails on an install that forgot package-data for data/*.txt.
    words = stopwords()
    assert {"the", "use", "user", "skill"} <= words


def test_terms_drop_boilerplate_and_plurals():
    assert terms("Use when the user asks to merge PDF files.") == {"merge", "pdf", "file"}


def test_jaccard_edges():
    assert jaccard(set(), {"a"}) == 0.0
    assert jaccard({"a", "b"}, {"b", "c"}) == 1 / 3


def test_collisions_found_and_sorted(make_skill):
    make_skill("pdf-a", "name: pdf-a\ndescription: Extract text and tables from PDF files.")
    make_skill("pdf-b", "name: pdf-b\ndescription: Extract tables from PDF files quickly.")
    root = make_skill("deploy", "name: deploy\ndescription: Deploy a web service to Kubernetes.")
    pairs = find_collisions(discover(root), threshold=0.3)
    assert len(pairs) == 1
    assert (pairs[0]["a"], pairs[0]["b"]) == ("pdf-a", "pdf-b")
    assert pairs[0]["shared"] == ["extract", "file", "pdf", "table"]
    assert pairs[0]["score"] == 0.667


def test_unparseable_skills_are_ignored_by_collisions(make_skill):
    root = make_skill("ok", "name: ok\ndescription: Extract PDF tables.")
    (root / "bad").mkdir()
    (root / "bad" / "SKILL.md").write_text("Extract PDF tables.", encoding="utf-8")
    assert find_collisions(discover(root), threshold=0.1) == []


def test_budget_totals(make_skill):
    make_skill("aaaa", "name: aaaa\ndescription: " + "d" * 40, "b" * 400)
    root = make_skill("bbbb", "name: bbbb\ndescription: " + "d" * 8, "")
    report = budget(discover(root))
    assert estimate_tokens("abcde") == 2
    assert report["totals"] == {"skills": 2, "startup_tokens": 11 + 3, "body_tokens": 100}


def test_plural_stripping_keeps_ss_us_is_words():
    assert terms("Merge PDFs and docs") == {"merge", "pdf", "doc"}
    assert terms("status analysis class") == {"status", "analysis", "class"}


def test_unicode_words_are_kept_whole():
    assert terms("Résumé café builder") == {"résumé", "café", "builder"}
