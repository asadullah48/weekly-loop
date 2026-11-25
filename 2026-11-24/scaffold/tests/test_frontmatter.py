import pytest

from skillscope.frontmatter import FrontmatterError, parse


def test_plain_and_quoted_values():
    meta, body, start = parse("---\nname: demo\ndescription: \"Say \\\"hi\\\"\"\nlicense: 'It''s MIT'\n---\nBody\n")
    assert meta == {"name": "demo", "description": 'Say "hi"', "license": "It's MIT"}
    assert body == "Body"
    assert start == 6


def test_folded_and_literal_block_scalars():
    text = "---\ndescription: >\n  one\n  two\nnotes: |\n  a\n  b\n---\n"
    meta, _, _ = parse(text)
    assert meta["description"] == "one two"
    assert meta["notes"] == "a\nb"


def test_plain_value_wrapping_onto_next_line():
    meta, _, _ = parse("---\ndescription: first part\n  second part\n---\n")
    assert meta["description"] == "first part second part"


def test_nested_mapping_and_comments():
    text = "---\n# comment\nname: demo  # trailing\nmetadata:\n  author: me\n  version: \"1.0\"\n---\n"
    meta, _, _ = parse(text)
    assert meta["name"] == "demo"
    assert meta["metadata"] == {"author": "me", "version": "1.0"}


@pytest.mark.parametrize(
    "text, message",
    [
        ("# no frontmatter\n", "does not start"),
        ("---\nname: x\n", "not closed"),
        ("---\nname: [a, b]\n---\n", "unsupported"),
        ("---\nname: a\nname: b\n---\n", "duplicate key"),
        ("---\njust text\n---\n", "expected 'key: value'"),
        ("---\n\tname: x\n---\n", "tabs"),
        ("---\nname: \"open\n---\n", "unterminated"),
    ],
)
def test_errors(text, message):
    with pytest.raises(FrontmatterError, match=message):
        parse(text)


def test_indented_dashes_inside_block_scalar_are_content():
    meta, body, _ = parse("---\ndescription: |\n  before\n  ---\n  after\n---\nBody\n")
    assert meta["description"] == "before\n---\nafter"
    assert body == "Body"


def test_quoted_value_with_trailing_comment():
    meta, _, _ = parse("---\ndescription: \"Valid YAML\"  # note\nname: 'a'  # x\n---\n")
    assert meta == {"description": "Valid YAML", "name": "a"}


def test_double_quoted_escapes():
    meta, _, _ = parse('---\nd: "a\\nb \\\\ c"\n---\n')
    assert meta["d"] == "a\nb \\ c"


@pytest.mark.parametrize("value", ["~", "null", "NULL", ""])
def test_null_values_are_none(value):
    meta, _, _ = parse(f"---\ndescription: {value}\n---\n")
    assert meta["description"] is None


def test_block_scalars_keep_paragraphs_and_relative_indent():
    text = "---\nf: >\n  para one\n  still one\n\n  para two\nl: |\n  def f():\n      return 1\n---\n"
    meta, _, _ = parse(text)
    assert meta["f"] == "para one still one\npara two"
    assert meta["l"] == "def f():\n    return 1"


def test_line_numbers_ignore_form_feed_and_unicode_separators():
    _, body, start = parse("---\nname: a\n---\nx\x0cy z\nlast\n")
    assert start == 4
    assert body == "x\x0cy z\nlast"


@pytest.mark.parametrize(
    "text, message",
    [
        ("---\nmetadata:\n  a: b\n    c: d\n---\n", "uneven indentation"),
        ("---\nmetadata:\n  a: b\n  a: c\n---\n", "duplicate key"),
        ("---\ndescription: | not a block\n---\n", "unsupported"),
        ("---\nname: \"a\" trailing\n---\n", "unexpected text"),
    ],
)
def test_strict_errors(text, message):
    with pytest.raises(FrontmatterError, match=message):
        parse(text)
