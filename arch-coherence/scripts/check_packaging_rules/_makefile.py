"""Makefile (and its included racecar.mk) validation against the §7 contract."""

from __future__ import annotations

import re
from pathlib import Path

from ._constants import FORBIDDEN_MAKEFILE_TOOLS, REQUIRED_MAKEFILE_TARGETS
from ._findings import Finding

_MAKEFILE_TARGET_RE = re.compile(r"^([a-zA-Z_][\w-]*)\s*:", re.MULTILINE)


def _target_body(text: str, target: str) -> str:
    """Return the recipe lines (tab-indented) for a named target, or '' if absent."""
    m = re.search(
        rf"^{re.escape(target)}\s*:[^\n]*\n((?:[\t][^\n]*\n?)*)",
        text,
        re.MULTILINE,
    )
    return m.group(1) if m else ""


def _resolve_makefile_text(
    root: Path, mk_text: str
) -> tuple[str | None, list[Finding]]:
    """Combine the owned Makefile with racecar.mk for validation.

    The Makefile fold (PACKAGING.md §7): canonical targets live in racecar.mk, which
    the owned Makefile includes. Returns (combined_text, findings). combined_text is
    None when the repo declares the fold (includes racecar.mk) but the file is absent
    — a Blocker that supersedes per-target validation. A repo with neither racecar.mk
    nor an include predates the fold and is nudged, not blocked. racecar.mk is
    identical in every repo and self-detects the shape, so there is no per-repo stamp
    to validate.
    """
    rcmk = root / "racecar.mk"
    includes_rcmk = bool(
        re.search(r"^\s*-?include\s+racecar\.mk\b", mk_text, re.MULTILINE)
    )
    if rcmk.exists():
        return mk_text + "\n" + rcmk.read_text(encoding="utf-8"), []
    if includes_rcmk:
        return None, [
            Finding(
                "Blocker",
                "racecar.mk",
                "missing-file",
                "Makefile includes racecar.mk but it is absent; run `make sync` to regenerate it",
            )
        ]
    return mk_text, [
        Finding(
            "Finding",
            "Makefile",
            "no-racecar-mk",
            "no racecar.mk: this repo predates the Makefile fold; run `make sync` "
            "to adopt it (PACKAGING.md §7)",
        )
    ]


def check_makefile(root: Path) -> list[Finding]:
    """Validate the Makefile (and its included racecar.mk) against the §7 contract."""
    path = root / "Makefile"
    if not path.exists():
        return [Finding("Blocker", "Makefile", "missing-file", "Makefile is required")]
    text, findings = _resolve_makefile_text(root, path.read_text(encoding="utf-8"))
    if text is None:
        return findings

    found = set(_MAKEFILE_TARGET_RE.findall(text))
    missing = REQUIRED_MAKEFILE_TARGETS - found
    for target in sorted(missing):
        findings.append(
            Finding(
                "Blocker",
                "Makefile",
                f"missing-target:{target}",
                "required canonical target absent; see PACKAGING.md §7",
            )
        )

    for tool in FORBIDDEN_MAKEFILE_TOOLS:
        if re.search(rf"(^|[\s\t])({re.escape(tool)})(\s|$)", text, re.MULTILINE):
            findings.append(
                Finding(
                    "Blocker",
                    "Makefile",
                    f"non-canon-tool:{tool}",
                    f"invocation of {tool!r} is non-canon (PACKAGING.md §1 §2)",
                )
            )

    # Fast `check` = fmt-check + lint + test (pre-commit cadence).
    check_line = re.search(r"^check\s*:\s*(.*?)(?:##|$)", text, re.MULTILINE)
    if check_line is not None:
        deps = set(check_line.group(1).split())
        for required in ("fmt-check", "lint", "test"):
            if required not in deps:
                findings.append(
                    Finding(
                        "Finding",
                        "Makefile",
                        f"check-chain:{required}",
                        f"fast `check` should depend on {required!r} (PACKAGING.md §7)",
                    )
                )

    # install-dev: must depend on install, install the dev group, wire pre-commit.
    decl = re.search(r"^install-dev\s*:\s*(.*?)(?:##|$)", text, re.MULTILINE)
    if decl and "install" not in decl.group(1).split():
        findings.append(
            Finding(
                "Blocker",
                "Makefile",
                "install-dev:missing-install-dep",
                "install-dev must depend on 'install' (PACKAGING.md §7)",
            )
        )
    body = _target_body(text, "install-dev")
    if body and "--group" not in body:
        findings.append(
            Finding(
                "Blocker",
                "Makefile",
                "install-dev:pip-group",
                "install-dev must run 'pip install --group' for the PEP 735 "
                "dev group (PACKAGING.md §7)",
            )
        )
    if body and "pre-commit install" not in body:
        findings.append(
            Finding(
                "Blocker",
                "Makefile",
                "install-dev:pre-commit-install",
                "install-dev must run 'pre-commit install' (PACKAGING.md §7)",
            )
        )

    # fmt: isort must precede black (DRIFT.md / memory: isort before black).
    body = _target_body(text, "fmt")
    if body:
        isort_pos = body.find("isort")
        black_pos = body.find("black")
        if isort_pos == -1 or black_pos == -1 or isort_pos > black_pos:
            findings.append(
                Finding(
                    "Blocker",
                    "Makefile",
                    "fmt:isort-before-black",
                    "fmt must invoke isort before black (PACKAGING.md §7)",
                )
            )

    # arch must invoke the canonical check scripts.
    body = _target_body(text, "arch")
    for script in ("check_upward_imports.py", "check_packaging.py"):
        if body and script not in body:
            findings.append(
                Finding(
                    "Blocker",
                    "Makefile",
                    f"arch:{script}",
                    f"arch must invoke scripts/{script} (PACKAGING.md §7)",
                )
            )

    # docs must invoke all four doc-coherence scripts.
    body = _target_body(text, "docs")
    for script in (
        "check_docs.py",
        "check_todo_format.py",
        "check_file_placement.py",
    ):
        if body and script not in body:
            findings.append(
                Finding(
                    "Blocker",
                    "Makefile",
                    f"docs:{script}",
                    f"docs must invoke scripts/{script} (PACKAGING.md §7)",
                )
            )

    # help must use ##@ section markers.
    body = _target_body(text, "help")
    if body and "##@" not in body:
        findings.append(
            Finding(
                "Finding",
                "Makefile",
                "help:no-section-markers",
                "help should use ##@ section markers to group non-canon targets (PACKAGING.md §7)",
            )
        )

    return findings
