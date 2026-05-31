# Adopting racecar in a project

Three paths: **new project** (scaffold from scratch), **existing project with a local racecar clone** (sync scripts locally), and **existing project without a local clone** (sync scripts remotely via curl).

## Picking a shape

Pick the shape that matches your project's layout:

| Shape | When to pick it |
|---|---|
| `src` | Plain installable Python package; no Django |
| `pypkg` | Installable package nested for future expansion; no Django yet |
| `pypkg+djapp` | Shared installable library plus a Django app that imports it |
| `djapp` | Straight Django, no separately-installable package |

Full shape reference: [`arch-coherence/PACKAGING.md`](arch-coherence/PACKAGING.md) §"Scope".

## Path A: new project

**1. Scaffold**

From the racecar repo root:

    make init ARGS="--shape pypkg+djapp --name myproject --package myproject --dest /path/to/new/repo"

Substitute `pypkg+djapp`, `myproject`, and the dest path for your project. Optional flags: `--version`, `--description`, `--author`, `--email`. See `python scripts/init_project.py --help`.

The scaffolder writes: the Makefile (shape vars set), library pyproject (placeholders filled), djapp pyproject (Shape `pypkg+djapp` only), `.pre-commit-config.yaml`, `.gitignore`, a skeleton `__init__.py`, and all eight check scripts under `scripts/`.

**2. Edit the importlinter contract**

Open the library pyproject (`pypkg/src/pyproject.toml` for Shape `pypkg+djapp`, `pyproject.toml` for others). Find `[[tool.importlinter.contracts]]` and replace the placeholder layer list with your real package layout. A fresh project with one package is fine as a starting point; add layers as the package grows.

**3. Install dev dependencies**

    cd /path/to/new/repo
    make install-dev

This creates `.venv/`, upgrades pip to 25.1+, and installs the library in editable mode plus the full dev tool set.

**4. Enable git hooks**

    .venv/bin/pre-commit install

Run from the repo root. This wires the pre-commit hooks declared in `.pre-commit-config.yaml` so they run on every `git commit`.

**5. Verify**

    make check-full

All checks should pass on a fresh scaffold. If any fail, they are real findings in the skeleton code or config — fix before proceeding.

## Path B: existing project

For a repo already set up with racecar conventions but whose check scripts are behind the current racecar version.

**Sync the scripts** (from the racecar repo root):

    make sync-scripts DEST=/path/to/existing/repo

Preview without writing first:

    make sync-scripts DEST=/path/to/existing/repo DRY_RUN=--dry-run

The sync copies only the eight canonical check scripts into `<dest>/scripts/`. It leaves any project-specific scripts in that directory untouched. Unchanged scripts are reported but not rewritten.

After syncing, run `make check-full` in the target repo and commit the updated scripts.

## Path C: remote sync (no local racecar clone)

For a repo that wants to update its check scripts without having racecar checked out locally. Fetches scripts directly from GitHub using only the Python stdlib.

**Run in one step from the adopter repo root:**

    curl -fsSL https://raw.githubusercontent.com/vishalapte/racecar/main/scripts/sync_remote.py \
      | python3 - --dest .

**Pin to a specific release:**

    curl -fsSL https://raw.githubusercontent.com/vishalapte/racecar/main/scripts/sync_remote.py \
      | python3 - --dest . --ref v0.6.0

**Preview without writing:**

    curl -fsSL https://raw.githubusercontent.com/vishalapte/racecar/main/scripts/sync_remote.py \
      | python3 - --dest . --dry-run

The `--ref` argument accepts any branch name, tag, or full commit SHA. Default is `main` (latest). Pin to a tag for reproducible updates.

After syncing, run `make check-full` and commit the updated scripts.

## Makefile help grouping convention

The canonical `help` target sorts targets alphabetically within each group. Racecar canon targets (install, check, fmt, lint, arch, docs, test, clean, etc.) appear ungrouped at the top. Project-specific targets are grouped under `##@` section markers:

    ##@ Django
    run: ## runserver on http://localhost:8000
    ...

    ##@ Project
    my-custom-target: ## description
    ...

Add `##@` markers only for targets that are not racecar canon. Leave canon targets ungrouped.

## Keeping in sync

The eight check scripts are the canonical source. When racecar updates them, update each adopter repo using Path B or Path C and commit the results. Path B requires a local racecar clone; Path C works from any machine with Python and curl.

The Makefile and pyproject templates do not have an automated sync path — review `diff -u templates/classic/Makefile <repo>/Makefile` manually when the template changes and merge intentionally.
