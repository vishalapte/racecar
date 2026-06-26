"""check_changelog: the newest CHANGELOG.md entry must match VERSION."""

from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(REPO_ROOT / "scripts"))
import check_changelog  # noqa: E402


def test_racecar_repo_satisfies_its_own_check():
    # racecar itself must lead the changelog with its current VERSION.
    assert check_changelog.problem(REPO_ROOT) is None


def _write(root: Path, version: str, changelog: str) -> None:
    (root / "VERSION").write_text(version + "\n", encoding="utf-8")
    (root / "CHANGELOG.md").write_text(changelog, encoding="utf-8")


def test_matching_top_entry_passes(tmp_path):
    _write(tmp_path, "1.2.3", "# Changelog\n\n## 1.2.3 - 2026-01-01\n\n### Added\n- x\n")
    assert check_changelog.problem(tmp_path) is None


def test_drift_is_flagged_with_both_versions(tmp_path):
    _write(tmp_path, "1.3.0", "# Changelog\n\n## 1.2.3 - 2026-01-01\n\n### Added\n- x\n")
    err = check_changelog.problem(tmp_path)
    assert err is not None and "1.3.0" in err and "1.2.3" in err


def test_missing_changelog_is_flagged(tmp_path):
    (tmp_path / "VERSION").write_text("1.0.0\n", encoding="utf-8")
    assert "missing" in (check_changelog.problem(tmp_path) or "")


def test_unreleased_only_is_flagged(tmp_path):
    _write(tmp_path, "1.0.0", "# Changelog\n\n## [Unreleased]\n\n### Added\n- x\n")
    err = check_changelog.problem(tmp_path)
    assert err is not None and "no released" in err


def test_prerelease_version_matches(tmp_path):
    _write(tmp_path, "1.0.0-rc1", "# Changelog\n\n## 1.0.0-rc1 - 2026-01-01\n\n### Added\n- x\n")
    assert check_changelog.problem(tmp_path) is None
