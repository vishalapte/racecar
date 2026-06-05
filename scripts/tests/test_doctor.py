"""Tests for scripts/doctor.py — the layer-by-layer load verifier."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

SCRIPTS_DIR = Path(__file__).resolve().parent.parent
RACECAR_ROOT = SCRIPTS_DIR.parent
sys.path.insert(0, str(SCRIPTS_DIR))
sys.path.insert(0, str(RACECAR_ROOT / "hooks"))

import session_load_standards  # noqa: E402

import doctor  # noqa: E402


class CollectingReport(doctor.Report):
    """Capture finding lines instead of printing them."""

    def __init__(self) -> None:
        super().__init__()
        self.lines: list[str] = []

    def ok(self, layer: str, message: str) -> None:
        self.lines.append(f"ok {layer} {message}")

    def fail(self, layer: str, message: str) -> None:
        self.failures += 1
        self.lines.append(f"FAIL {layer} {message}")

    def warn(self, layer: str, message: str) -> None:
        self.warnings += 1
        self.lines.append(f"warn {layer} {message}")


def write_settings(path: Path, drop: tuple[str, str, str] | None = None) -> None:
    """Write a settings.json carrying all expected wiring, minus `drop`."""
    settings: dict = {"hooks": {}}
    for event, matcher, basename in doctor.EXPECTED_WIRING:
        if (event, matcher, basename) == drop:
            continue
        entries = settings["hooks"].setdefault(event, [])
        entry = next((e for e in entries if e["matcher"] == matcher), None)
        if entry is None:
            entry = {"matcher": matcher, "hooks": []}
            entries.append(entry)
        entry["hooks"].append(
            {"type": "command", "command": str(RACECAR_ROOT / "hooks" / basename)}
        )
    path.write_text(json.dumps(settings))


# --- expected_skills ---------------------------------------------------------


def test_expected_skills_derived_from_skill_md_dirs():
    skills = doctor.expected_skills()
    assert skills["racecar"] == RACECAR_ROOT
    assert skills["racecar-doctor"] == RACECAR_ROOT / "doctor"
    assert skills["racecar-normalize"] == RACECAR_ROOT / "normalize"
    # expert/ is an optional overlay, installed separately — never expected.
    assert "racecar-expert" not in skills


# --- layer 1: files ----------------------------------------------------------


def test_check_files_passes_with_full_symlink_set(tmp_path):
    skills_dir = tmp_path / "skills"
    skills_dir.mkdir()
    for name, target in doctor.expected_skills().items():
        (skills_dir / name).symlink_to(target)
    report = CollectingReport()
    doctor.check_files(report, skills_dir)
    assert report.failures == 0


def test_check_files_flags_missing_symlink(tmp_path):
    skills_dir = tmp_path / "skills"
    skills_dir.mkdir()
    report = CollectingReport()
    doctor.check_files(report, skills_dir)
    missing = [
        l for l in report.lines if "FAIL" in l and "missing (run ./install)" in l
    ]
    assert len(missing) == len(doctor.expected_skills())


def test_check_files_flags_wrong_symlink_target(tmp_path):
    skills_dir = tmp_path / "skills"
    skills_dir.mkdir()
    elsewhere = tmp_path / "elsewhere"
    elsewhere.mkdir()
    for name, target in doctor.expected_skills().items():
        (skills_dir / name).symlink_to(target)
    link = skills_dir / "racecar-doctor"
    link.unlink()
    link.symlink_to(elsewhere)
    report = CollectingReport()
    doctor.check_files(report, skills_dir)
    assert report.failures == 1
    assert any("expected" in l for l in report.lines if "FAIL" in l)


def test_check_files_refuses_non_symlink(tmp_path):
    skills_dir = tmp_path / "skills"
    skills_dir.mkdir()
    for name, target in doctor.expected_skills().items():
        (skills_dir / name).symlink_to(target)
    link = skills_dir / "racecar-doctor"
    link.unlink()
    link.mkdir()
    report = CollectingReport()
    doctor.check_files(report, skills_dir)
    assert any("not a symlink" in l for l in report.lines)


# --- layer 2: wiring ---------------------------------------------------------


def test_check_wiring_passes_on_complete_settings(tmp_path):
    settings = tmp_path / "settings.json"
    write_settings(settings)
    report = CollectingReport()
    doctor.check_wiring(report, settings)
    assert report.failures == 0
    assert len(report.lines) == len(doctor.EXPECTED_WIRING)


@pytest.mark.parametrize(
    "drop",
    [
        ("SessionStart", "clear", "session_load_standards.py"),
        ("PreToolUse", "Bash", "compound-command-allow.sh"),
        ("PreCompact", "", "precompact_history.py"),
    ],
)
def test_check_wiring_flags_missing_entry(tmp_path, drop):
    settings = tmp_path / "settings.json"
    write_settings(settings, drop=drop)
    report = CollectingReport()
    doctor.check_wiring(report, settings)
    assert report.failures == 1
    assert any("not wired" in l for l in report.lines if "FAIL" in l)


def test_check_wiring_flags_stale_path(tmp_path):
    settings_path = tmp_path / "settings.json"
    write_settings(settings_path)
    settings = json.loads(settings_path.read_text())
    # Point one wired command at a path outside this checkout.
    entry = settings["hooks"]["PostToolUse"][0]["hooks"][0]
    entry["command"] = str(tmp_path / "old-checkout" / "claude_racecar_hook.sh")
    settings_path.write_text(json.dumps(settings))
    report = CollectingReport()
    doctor.check_wiring(report, settings_path)
    assert report.failures == 1
    assert any("missing file" in l for l in report.lines)


def test_check_wiring_flags_absent_settings(tmp_path):
    report = CollectingReport()
    doctor.check_wiring(report, tmp_path / "settings.json")
    assert report.failures == 1


def test_check_wiring_flags_invalid_json(tmp_path):
    settings = tmp_path / "settings.json"
    settings.write_text("{not json")
    report = CollectingReport()
    doctor.check_wiring(report, settings)
    assert report.failures == 1
    assert any("not valid JSON" in l for l in report.lines)


# --- layer 3: execution ------------------------------------------------------


def test_check_execution_runs_real_hook_and_matches_token():
    report = CollectingReport()
    token = doctor.check_execution(report)
    assert report.failures == 0
    items = session_load_standards.collect_baseline()
    assert token == session_load_standards.load_token(items)
    assert any(f"load token planted: {token}" in l for l in report.lines)


def test_load_token_is_content_derived_and_deterministic():
    items = [(Path("a.md"), "alpha"), (Path("b.md"), "beta")]
    t1 = session_load_standards.load_token(items)
    t2 = session_load_standards.load_token(items)
    assert t1 == t2
    assert len(t1) == 12
    changed = [(Path("a.md"), "alpha"), (Path("b.md"), "beta!")]
    assert session_load_standards.load_token(changed) != t1


# --- layer 4: context --------------------------------------------------------


def test_check_context_unavailable_without_transcript_dir(tmp_path):
    report = CollectingReport()
    doctor.check_context(report, "deadbeef0000", tmp_path)
    assert report.failures == 0
    assert report.warnings == 1
    assert any("UNAVAILABLE" in l for l in report.lines)


def test_check_context_finds_token(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    tdir = doctor.transcript_dir_for(tmp_path, tmp_path / ".claude")
    tdir.mkdir(parents=True)
    (tdir / "session.jsonl").write_text('{"text": "Load token: deadbeef0000"}\n')
    report = CollectingReport()
    doctor.check_context(report, "deadbeef0000", tmp_path / ".claude")
    assert report.warnings == 0
    assert any("found" in l for l in report.lines)


def test_check_context_warns_on_absent_token(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    tdir = doctor.transcript_dir_for(tmp_path, tmp_path / ".claude")
    tdir.mkdir(parents=True)
    (tdir / "session.jsonl").write_text('{"text": "no token here"}\n')
    report = CollectingReport()
    doctor.check_context(report, "deadbeef0000", tmp_path / ".claude")
    assert report.warnings == 1
    assert any("NOT in newest transcript" in l for l in report.lines)
