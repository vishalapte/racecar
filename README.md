# Standards — Resolver

This is a routing table. Load the file that applies to the task at hand. Do not load all files.

Topic: Architectural coherence — four checks (acyclicity, direction, layer integrity, depth-plus-one isolation) with sub-axioms (environment-layer exception, domain boundaries), plus review lens
Load: [arch-coherence/README.md](arch-coherence/README.md)

Topic: Python architectural coherence — module structure, imports, CLI, enforcement
Load: [arch-coherence/PYTHON.md](arch-coherence/PYTHON.md)

Topic: Django architectural coherence — service layer, view layering
Load: [arch-coherence/DJANGO.md](arch-coherence/DJANGO.md)

Topic: Engineering review — wrapper around gstack `plan-eng-review` with racecar-specific pre/post passes
Load: [eng-review/README.md](eng-review/README.md)

Topic: Python engineering hygiene — mindset, naming, formatting, testing, linting, Definition of Done
Load: [eng-review/PYTHON.md](eng-review/PYTHON.md)

Topic: Django engineering hygiene — database/performance, security
Load: [eng-review/DJANGO.md](eng-review/DJANGO.md)

Topic: Documentation coherence — update protocol + review lens (links, section numbers, file naming, cogency, scope honesty, rule testability, one-home-per-rule)
Load: [doc-coherence/README.md](doc-coherence/README.md)

Topic: Ownership — tooling enables design and confirms correctness; responsibility stays with the owner
Load: [shared/OWNERSHIP.md](shared/OWNERSHIP.md)

Topic: Voice — shared conventions for prescriptive writing (standards and review outputs)
Load: [shared/VOICE.md](shared/VOICE.md)

Topic: TODO list rendering format
Load: [shared/TODO_FORMAT.md](shared/TODO_FORMAT.md)

Topic: Glossary — DAG, coherence, cogency, resolver, depth-plus-one, outward-downward, one-home-per-rule, scope honesty, drift
Load: [GLOSSARY.md](GLOSSARY.md)

## Enforcement

Reference this file from your project's `CLAUDE.md` or equivalent agent-instruction file. Read it first to find which component applies. Do not load component files speculatively — read only what the current task requires. If you arrived at a component file directly, return here first.
