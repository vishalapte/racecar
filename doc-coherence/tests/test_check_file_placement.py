"""Tests for doc-coherence/scripts/check_file_placement.py.

The check is reference-driven: a markdown doc is correctly placed when the resolver
chain (root README.md / CLAUDE.md, and any SKILL.md entry point) reaches it via
links. There is no fixed allowlist of filenames. An orphan no resolver links to is
the defect.

Run with:
    pytest doc-coherence/tests/test_check_file_placement.py
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "check_file_placement.py"


def _run(repo: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(SCRIPT)], cwd=repo, capture_output=True, text=True, check=False
    )


def _seed(tmp_path: Path, files: dict[str, str]) -> Path:
    (tmp_path / ".git").mkdir()
    for rel, content in files.items():
        p = tmp_path / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content, encoding="utf-8")
    return tmp_path


def test_referenced_doc_passes(tmp_path: Path) -> None:
    repo = _seed(
        tmp_path,
        {"README.md": "See the [guide](GUIDE.md).\n", "GUIDE.md": "# Guide\n"},
    )
    assert _run(repo).returncode == 0, _run(repo).stdout


def test_orphan_doc_fails(tmp_path: Path) -> None:
    repo = _seed(
        tmp_path,
        {"README.md": "# Root, links nothing\n", "ORPHAN.md": "# nobody links me\n"},
    )
    result = _run(repo)
    assert result.returncode == 1
    assert "ORPHAN.md" in result.stdout


def test_reachable_through_a_chain_passes(tmp_path: Path) -> None:
    """Reachability is transitive: README -> A -> B, with relative paths resolved."""
    repo = _seed(
        tmp_path,
        {
            "README.md": "[a](sub/A.md)\n",
            "sub/A.md": "[b](B.md)\n",  # relative to sub/ -> sub/B.md
            "sub/B.md": "# end of chain\n",
        },
    )
    assert _run(repo).returncode == 0, _run(repo).stdout


def test_skill_md_is_an_entry_point(tmp_path: Path) -> None:
    """A SKILL.md needs no inbound link (the harness invokes it); the doc it loads is
    reachable through it."""
    repo = _seed(
        tmp_path,
        {
            "README.md": "# Root, links nothing\n",
            "lens/SKILL.md": "Load [the dense doc](DENSE.md) in full.\n",
            "lens/DENSE.md": "# reached via the skill, not a README link\n",
        },
    )
    assert _run(repo).returncode == 0, _run(repo).stdout


def test_docs_dir_is_exempt(tmp_path: Path) -> None:
    repo = _seed(
        tmp_path,
        {"README.md": "# links nothing\n", "docs/ANYTHING.md": "# unreferenced, under docs/\n"},
    )
    assert _run(repo).returncode == 0, _run(repo).stdout


def test_claude_without_readme_fails(tmp_path: Path) -> None:
    # Link sub/CLAUDE.md so it is not also an orphan — isolating the missing-sibling finding.
    repo = _seed(
        tmp_path,
        {"README.md": "[c](sub/CLAUDE.md)\n", "sub/CLAUDE.md": "# agent context, no sibling README\n"},
    )
    result = _run(repo)
    assert result.returncode == 1
    assert "without a sibling README.md" in result.stdout


def test_ignore_paths_excludes_tree(tmp_path: Path) -> None:
    """Markdown scoped out via [tool.pylint.MASTER].ignore-paths is not orphan-checked."""
    repo = _seed(
        tmp_path,
        {"README.md": "# links nothing\n", "data/taxonomy/animals.md": "# orphan unless scoped\n"},
    )
    before = _run(repo)
    assert before.returncode == 1, before.stdout
    assert "data/taxonomy/animals.md" in before.stdout

    (repo / "pyproject.toml").write_text(
        '[tool.pylint.MASTER]\nignore-paths = ["^data/.*"]\n', encoding="utf-8"
    )
    after = _run(repo)
    assert after.returncode == 0, after.stdout
