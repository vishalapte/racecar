# Operational discipline

Accessed via [`../README.md`](../README.md). If you arrived here directly, read that first.

Operational discipline for agent execution — applies during review-lens analysis ([`../arch-coherence/README.md`](../arch-coherence/README.md), [`../doc-coherence/README.md`](../doc-coherence/README.md), [`../eng-review/README.md`](../eng-review/README.md)), where reads, greps, and test runs are expensive, and during general implementation work. Tool calls are not locally cheap; cost compounds across the conversation. State-changing tool calls compound worse — a wrong probe wastes a turn, a wrong mutation wastes recovery.

## Rules

Ordered from independent (universal precondition for any action) to dependent (presumes a workflow already in flight).

1. **Check before mutate.** Before any state-changing action — `pip install`, `mkdir`, `kill`, `createdb`, `git branch -D`, `npm install` — run the cheap non-destructive probe first (`python -c "import X"`, `pip show X`, `ls`, `pgrep`, `psql -l`, `git branch --list`). If the probe says the action is unnecessary or unsafe, skip or ask. Non-destructive intelligence beats destructive intelligence: a probe that returns "already there" costs one turn; a mutation that clobbers a venv, a database, or an in-flight branch costs the rest of the session.

2. **Parallel independent reads.** When checking N unrelated files or symbols, issue all reads and greps in a single assistant turn. Serial only when each lookup informs the next.

3. **Audit before fix.** When tests fail or a refactor breaks call sites, grep for the full set of broken patterns first. Report the inventory before making any change. No fix-the-first-occurrence-then-rerun loops.

4. **Group failure modes before fixing.** On a multi-failure test run, cluster failures by root cause first. Do not fix the first failure and rerun. Five tests failing from one shared cause get fixed once, not five times.

5. **Script mechanical changes.** Three or more identical-shape edits is a script (Python or `sed`), applied once, verified once. Not an `Edit`-tool loop. Identical-shape means the change can be expressed as one pattern; if each edit needs its own judgement or its own commit message, the loop is correct.

6. **The test suite is not a debugger.** Use targeted runs (single test, single file, single module) to iterate. Reserve the full suite for confirming completion, not for searching the failure space. If you find yourself rerunning the full suite to see what changed, you are debugging through it — stop, read the failure, narrow the run.

## Why this matters for review work

The lenses read broadly. Every serial grep, every redundant test run, every unbatched tool call multiplies against the size of the codebase under review. A review that should take one inventory pass and one report becomes a reread loop, and the owner pays in tokens and wall time for nothing.

State-changing actions multiply worse. A probe that returns "already installed" is a one-turn correction; a destructive action against the wrong target is unrecoverable inside the conversation.

## Failure modes to recognize

- Treating each tool call as locally cheap. A 50-second test run feels like one unit; eight of them is the same task done badly.
- Mutating without probing. Reaching for `pip install` or `mkdir` when `pip show` or `ls` would have settled the question in one turn.
- Verifying each step instead of committing to a multi-step plan. Useful for novel work, wasteful for mechanical work.
- Defaulting to serial tool calls when in doubt. If the calls are independent, parallel is the rule.
- Following the smell, not the cause. Five tests failing from one shared cause get fixed once, not five times.
