import textwrap
from pathlib import Path

import pytest


@pytest.fixture
def make_skill(tmp_path: Path):
    """Create <tmp>/bundle/<dirname>/SKILL.md and return the bundle root."""
    root = tmp_path / "bundle"
    root.mkdir()

    def _make(dirname: str, frontmatter: str, body: str = "# Title\n") -> Path:
        skill_dir = root / dirname
        skill_dir.mkdir(parents=True, exist_ok=True)
        text = "---\n" + textwrap.dedent(frontmatter).strip("\n") + "\n---\n" + body
        (skill_dir / "SKILL.md").write_text(text, encoding="utf-8")
        return root

    return _make
