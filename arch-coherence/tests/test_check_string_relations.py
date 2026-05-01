"""Tests for scripts/check_string_relations.py.

Builds a fake project under tmp_path with `[tool.importlinter].root_packages`
and a `layers` DAG contract in pyproject.toml. Each test seeds violations
across LIVE apps (in INSTALLED_APPS) and NOOP apps (on disk but not
registered) and asserts the report sections match exactly.

INSTALLED_APPS is injected via the `STRING_RELATIONS_INSTALLED_APPS` env var
so tests do not require a working `manage.py`.

Run with:
    pytest arch-coherence/tests/test_check_string_relations.py
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "check_string_relations.py"


_PYPROJECT = """\
[tool.importlinter]
root_packages = ["apps", "core"]

[[tool.importlinter.contracts]]
name = "layered DAG"
type = "layers"
layers = [
    "apps.activity",
    "apps.sessions",
    "core",
]
"""

_INSTALLED = "apps.activity.ib,apps.sessions,core.llm"

_CLEAN_MODELS = """\
from django.conf import settings
from django.db import models

from apps.other.models import Other


class Clean(models.Model):
    other = models.ForeignKey(Other, on_delete=models.CASCADE)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
"""

_INTRA_APP = """\
from django.db import models


class Foo(models.Model):
    other = models.ForeignKey("Other", on_delete=models.CASCADE)
"""

_SAME_FILE_FORWARD = """\
from django.db import models


class Front(models.Model):
    later = models.ForeignKey("Back", on_delete=models.CASCADE)


class Back(models.Model):
    pass
"""

_SELF_REF = """\
from django.db import models


class Tree(models.Model):
    parent = models.ForeignKey("self", on_delete=models.CASCADE, null=True)
"""

_UPWARD_CROSS = """\
from django.db import models


class LlmThing(models.Model):
    s = models.ForeignKey("sessions.Session", on_delete=models.CASCADE)
"""

_BROKEN_LABEL = """\
from django.db import models


class LlmThing(models.Model):
    s = models.ForeignKey("xeno_sessions.Session", on_delete=models.CASCADE)
"""

_NOOP_VIOLATION = """\
from django.db import models


class Dead(models.Model):
    other = models.ForeignKey("apps.activity.ib.Other", on_delete=models.CASCADE)
"""


def _write(path: Path, body: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(body, encoding="utf-8")


def _run(cwd: Path, *, installed: str | None = _INSTALLED) -> subprocess.CompletedProcess[str]:
    env = {**os.environ}
    if installed is not None:
        env["STRING_RELATIONS_INSTALLED_APPS"] = installed
    else:
        env.pop("STRING_RELATIONS_INSTALLED_APPS", None)
    return subprocess.run(
        [sys.executable, str(SCRIPT)],
        cwd=cwd,
        capture_output=True,
        text=True,
        env=env,
        check=False,
    )


def test_clean_tree_passes(tmp_path: Path) -> None:
    _write(tmp_path / "pyproject.toml", _PYPROJECT)
    _write(tmp_path / "apps" / "activity" / "ib" / "models.py", _CLEAN_MODELS)
    _write(tmp_path / "core" / "llm" / "models.py", _CLEAN_MODELS)

    result = _run(tmp_path)

    assert result.returncode == 0, result.stdout + result.stderr
    assert result.stdout == ""


def test_intra_app_violation_is_live_no_cross(tmp_path: Path) -> None:
    _write(tmp_path / "pyproject.toml", _PYPROJECT)
    _write(tmp_path / "apps" / "activity" / "ib" / "models.py", _INTRA_APP)

    result = _run(tmp_path)

    assert result.returncode == 1
    assert result.stdout == (
        "LIVE violations (file's app is in INSTALLED_APPS):\n"
        "  apps/activity/ib/models.py:5: ForeignKey string reference forbidden: 'Other' "
        "[file layer: apps.activity]\n"
    )


def test_same_file_forward_ref_is_exempt(tmp_path: Path) -> None:
    _write(tmp_path / "pyproject.toml", _PYPROJECT)
    _write(tmp_path / "apps" / "activity" / "ib" / "models.py", _SAME_FILE_FORWARD)

    result = _run(tmp_path)

    assert result.returncode == 0, result.stdout + result.stderr
    assert result.stdout == ""


def test_migrations_dir_is_skipped(tmp_path: Path) -> None:
    _write(tmp_path / "pyproject.toml", _PYPROJECT)
    _write(tmp_path / "apps" / "activity" / "ib" / "migrations" / "0001_initial.py", _UPWARD_CROSS)

    result = _run(tmp_path)

    assert result.returncode == 0, result.stdout + result.stderr
    assert result.stdout == ""


def test_self_ref_is_exempt(tmp_path: Path) -> None:
    _write(tmp_path / "pyproject.toml", _PYPROJECT)
    _write(tmp_path / "apps" / "activity" / "ib" / "models.py", _SELF_REF)

    result = _run(tmp_path)

    assert result.returncode == 0, result.stdout + result.stderr
    assert result.stdout == ""


def test_upward_cross_is_flagged(tmp_path: Path) -> None:
    _write(tmp_path / "pyproject.toml", _PYPROJECT)
    _write(tmp_path / "core" / "llm" / "models.py", _UPWARD_CROSS)

    result = _run(tmp_path)

    assert result.returncode == 1
    assert "UPWARD DAG cross" in result.stdout
    assert "target layer: apps.sessions" in result.stdout


def test_unknown_app_label_is_flagged(tmp_path: Path) -> None:
    _write(tmp_path / "pyproject.toml", _PYPROJECT)
    _write(tmp_path / "core" / "llm" / "models.py", _BROKEN_LABEL)

    result = _run(tmp_path)

    assert result.returncode == 1
    assert "target app label 'xeno_sessions' not in INSTALLED_APPS" in result.stdout


def test_noop_module_is_separated(tmp_path: Path) -> None:
    _write(tmp_path / "pyproject.toml", _PYPROJECT)
    _write(tmp_path / "apps" / "ghost" / "models.py", _NOOP_VIOLATION)

    result = _run(tmp_path)

    assert result.returncode == 1
    assert result.stdout.startswith("NOOP modules")
    assert "apps/ghost/models.py:5" in result.stdout


def test_live_and_noop_both_reported(tmp_path: Path) -> None:
    _write(tmp_path / "pyproject.toml", _PYPROJECT)
    _write(tmp_path / "apps" / "activity" / "ib" / "models.py", _INTRA_APP)
    _write(tmp_path / "apps" / "ghost" / "models.py", _NOOP_VIOLATION)

    result = _run(tmp_path)

    assert result.returncode == 1
    assert "LIVE violations" in result.stdout
    assert "NOOP modules" in result.stdout
    live_idx = result.stdout.index("LIVE violations")
    noop_idx = result.stdout.index("NOOP modules")
    assert live_idx < noop_idx


def test_missing_root_packages_key_errors(tmp_path: Path) -> None:
    _write(tmp_path / "pyproject.toml", "[tool.other]\nx = 1\n")

    result = _run(tmp_path)

    assert result.returncode == 2
    assert "root_packages missing" in result.stderr


def test_missing_pyproject_errors(tmp_path: Path) -> None:
    result = _run(tmp_path)

    assert result.returncode == 2
    assert "pyproject.toml not found" in result.stderr


def test_missing_installed_apps_source_errors(tmp_path: Path) -> None:
    _write(tmp_path / "pyproject.toml", _PYPROJECT)
    _write(tmp_path / "apps" / "activity" / "ib" / "models.py", _CLEAN_MODELS)

    result = _run(tmp_path, installed=None)

    assert result.returncode == 2
    assert "manage.py not found" in result.stderr
