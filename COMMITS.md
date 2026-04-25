# Commits

Accessed via [`README.md`](README.md). If you arrived here directly, read that first.

Rules for commit messages in this repo. Apply without deviation when authoring or suggesting a commit.

## Format

Conventional Commits: `<type>(<optional scope>): <description>`

- Lowercase type and description.
- No trailing period on the subject.
- Imperative mood. "add", not "added".
- Allowed types: `feat`, `fix`, `docs`, `style`, `refactor`, `perf`, `test`, `build`, `ci`, `chore`, `revert`.
- Breaking changes: append `!` after the type or scope (`feat(api)!: …`) and include a `BREAKING CHANGE:` footer.
- A change that does not fit a conventional type is a signal to stop and ask, not to invent one.

## Valid VERSION increments

Compare new vs. old `VERSION`, parsed as `major.minor.patch`. Exactly one of:

| Bump  | Delta    | Result                                                  |
| ----- | -------- | ------------------------------------------------------- |
| Patch | `+0.0.1` | major and minor unchanged; patch increases by 1         |
| Minor | `+0.1.0` | major unchanged; minor increases by 1; patch resets to 0 |
| Major | `+1.0.0` | major increases by 1; minor and patch reset to 0        |

Any other delta is invalid. Refuse to write the commit message and name the valid bump that was likely intended.

## VERSION bumps in commits

When `VERSION` is part of the diff:

- Do not use a separate `chore(bump)` commit. The subject describes the actual change.
- Append a trailing line to the body: `Bump VERSION to X.Y.Z.` — with the period.

## References

- Git `SubmittingPatches` (canonical for many open-source projects): <https://git-scm.com/docs/SubmittingPatches/2.41.0>
- Conventional Commits v1.0.0: <https://www.conventionalcommits.org/en/v1.0.0/>
