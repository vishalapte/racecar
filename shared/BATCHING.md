# Batching

Accessed via [`../README.md`](../README.md). If you arrived here directly, read that first.

Operational discipline for agent execution — applies during review-lens analysis ([`../arch-coherence/README.md`](../arch-coherence/README.md), [`../doc-coherence/README.md`](../doc-coherence/README.md), [`../eng-review/README.md`](../eng-review/README.md)), where reads, greps, and test runs are expensive, and during general implementation work. Tool calls are not locally cheap; cost compounds across the conversation.

## Rules

1. **Audit before fix.** When tests fail or a refactor breaks call sites, grep for the full set of broken patterns first. Report the inventory before making any change. No fix-the-first-occurrence-then-rerun loops.

2. **Script mechanical changes.** Three or more similar edits is a script (Python or `sed`), applied once, verified once. Not an `Edit`-tool loop.

3. **One verification cycle per task.** Run the full test suite at most twice — once to baseline if needed, once to confirm completion. Targeted single-test runs in between are fine.

4. **Parallel independent reads.** When checking N unrelated files or symbols, issue all reads and greps in a single assistant turn. Serial only when each lookup informs the next.

5. **Group failure modes before fixing.** On a multi-failure test run, cluster failures by root cause first. Do not fix the first failure and rerun.

## Why this matters for review work

The lenses read broadly. Every serial grep, every redundant test run, every unbatched tool call multiplies against the size of the codebase under review. A review that should take one inventory pass and one report becomes a reread loop, and the owner pays in tokens and wall time for nothing.

## Failure modes to recognize

- Treating each tool call as locally cheap. A 50-second test run feels like one unit; eight of them is the same task done badly.
- Verifying each step instead of committing to a multi-step plan. Useful for novel work, wasteful for mechanical work.
- Defaulting to serial tool calls when in doubt. If the calls are independent, parallel is the rule.
- Following the smell, not the cause. Five tests failing from one shared cause get fixed once, not five times.
