# arch-coherence/lib/_cli.py — OPTIONAL. Copy to your package's source root as
# `<pkg>/_cli.py` (e.g. src/athena/_cli.py) only if you want the dispatcher-
# listing render factored out of your __main__.py files.
#
# Not mandated. Inlining the render body in each __main__.py (see CLI.md,
# Pattern 1) is equally valid and is the documented baseline. The payoff lands
# once a package has several __main__.py nodes: the inlined body is then
# duplicated across them, and pylint's duplicate-code (R0801) flags it on the
# path to a clean lint. This module is the one-home alternative — each node's
# `_print_commands()` becomes a thin call instead of a copy. Modifying this
# file is a standards-change conversation, not a per-project decision.
"""Optional shared renderer for a package's `__main__.py` discovery listing.

Per arch-coherence/CLI.md, each package's `__main__.py` exposes `commands()`
— a list of `(name, description)` pairs naming its immediate `python -m
<pkg>.<name>` children. A Pattern 1 or Pattern 2 node renders that list when
run with no arguments. Drop this file in and have `_print_commands()` delegate:

    from <pkg>._cli import print_commands

    def _print_commands() -> None:
        print_commands(__package__, commands())

The listing is flat by default. A dispatcher with many verbs of mixed effect
can group them — so destructive commands are distinguishable from safe ones at
a glance — by classifying each verb and passing `kinds`:

    _KINDS = {"calendar": "read", "catalog": "write", "spider": "placeholder"}

    def _print_commands() -> None:
        print_commands(__package__, commands(), kinds=_KINDS)
"""

from __future__ import annotations

# Default section order + heading for the grouped layout. A caller's `kinds`
# maps each verb name to one of these keys; pass a different `sections` tuple
# to use another vocabulary. The default surfaces command effect (read-only vs
# writes vs not-yet-built), which is the common reason to group.
SECTIONS: tuple[tuple[str, str], ...] = (
    ("read", "Read-only (no writes):"),
    ("write", "Writes (idempotent; --force / --dry-run):"),
    ("placeholder", "Placeholders:"),
)


def print_commands(
    package: str,
    entries: list[tuple[str, str]],
    *,
    kinds: dict[str, str] | None = None,
    sections: tuple[tuple[str, str], ...] = SECTIONS,
) -> None:
    """Render the discovery listing for `python -m {package}`.

    `entries` is the node's `commands()` output; child names are relative and
    the full `python -m {package}.{name}` paths are built here.

    With `kinds` omitted the listing is flat. With `kinds` — a `name -> key`
    map covering every entry — the verbs are grouped under `sections`, in
    `sections` order, empty groups skipped. A verb whose `kinds` key is not in
    `sections`, or that is missing from `kinds` entirely, raises: a new verb
    that forgets its classification fails loudly instead of silently vanishing
    from the listing.
    """
    if kinds is not None:
        section_keys = {key for key, _ in sections}
        unclassified = [name for name, _ in entries if kinds.get(name) not in section_keys]
        if unclassified:
            raise ValueError(
                f"kinds missing or out-of-vocabulary for: {unclassified} "
                f"(known section keys: {sorted(section_keys)})"
            )

    paths = {name: f"python -m {package}.{name}" for name, _ in entries}
    descs = dict(entries)
    width = max((len(p) for p in paths.values()), default=0)
    print(f"python -m {package}\n")

    if kinds is None:
        for name, _ in entries:
            print(f"  {paths[name].ljust(width)}   {descs[name]}")
        print("\nAppend --help to any command for its options.")
        return

    for key, label in sections:
        names = [name for name, _ in entries if kinds[name] == key]
        if not names:
            continue
        print(f"  {label}")
        for name in names:
            print(f"    {paths[name].ljust(width)}   {descs[name]}")
        print()
    print("Append --help to any command for its options.")
