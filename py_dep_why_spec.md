# py-dep-why — Project Specification

## 1. Summary

`py-dep-why` is a Python CLI tool that explains **why** a package is present in an environment by building a dependency graph and answering questions like:

- What pulled in package `X`?
- What are the root (top-level) packages?
- What dependency paths exist from roots to `X`?
- Export the dependency graph for tooling/visualization.

Primary design constraints:

- Cross-platform: **macOS + Linux** first.
- Works well when installed via **pipx**.
- Primary data source: **installed environment metadata** via `importlib.metadata`.
- Output: human-readable by default, plus **`--json`** for automation.

## 2. Goals

- Provide a fast, deterministic explanation for why a dependency is installed.
- Make the tool safe and easy to use when installed in an isolated pipx environment.
- Support both interactive usage and scripting/CI via `--json` output.
- Provide a small, stable command surface with predictable output.

## 3. Non-Goals (v1)

- Not a vulnerability scanner (not a replacement for `pip-audit`, `safety`, etc.).
- Not a full lockfile analyzer (Poetry/uv/pip-tools lock parsing is a v2 feature).
- Not a resolver. The tool explains the **current** installed environment.
- Not responsible for creating or managing virtual environments.

## 4. Target Users / Use Cases

- Developers debugging “why is `X` installed?”
- Maintainers reducing dependency bloat.
- CI jobs that enforce “no forbidden deps.”
- Tooling authors wanting a lightweight dep graph export.

## 5. Installation & Execution Model (pipx-first)

### 5.1 Installation

- Recommended installation:
  - `pipx install py-dep-why`

### 5.2 Key implication of pipx

When installed via pipx, `py-dep-why` runs in its **own** isolated environment. Therefore, v1 must support targeting an external Python environment to inspect.

### 5.3 Target environment selection

The tool supports three ways to choose the environment being inspected:

1) **Current interpreter** (default)
   - If you run `py-dep-why` from within a venv, it inspects that venv.

2) `--python PATH`
   - Inspect the environment for a specific interpreter (e.g., `.venv/bin/python`).

3) `--venv PATH`
   - Convenience flag where `PATH` is a venv directory; the tool finds the interpreter:
     - POSIX: `${VENV}/bin/python`
     - (Windows is optional in v1; can be added later)

Rules:

- `--python` and `--venv` are mutually exclusive.
- If neither is provided, use `sys.executable`.

Implementation note:

- If `--python` (or resolved `--venv`) points to a different interpreter than the running process, the tool executes its analysis using that interpreter by re-invoking itself:
  - `target_python -m py_dep_why ...` (module execution)
  - This avoids trying to introspect another environment’s `site-packages` from the pipx environment.

## 6. CLI Design

### 6.1 Global options

All commands accept:

- `--python PATH`: target interpreter
- `--venv PATH`: target venv directory
- `--json`: output machine-readable JSON to stdout
- `--no-color`: disable ANSI color
- `--verbose`: include extra diagnostic details (e.g., metadata anomalies)

Behavior:

- If `--json` is set, stdout is JSON only. Human output goes to stderr if needed for warnings.
- Exit codes are consistent across commands (see Section 11).

### 6.2 Commands

#### 6.2.1 `why`

Purpose: explain why a package is present by printing one or more dependency paths from roots to the target.

Usage:

- `py-dep-why why <package>`

Options:

- `--max-paths N` (default: 5)
- `--max-depth N` (default: 25)
- `--all-paths` (overrides `--max-paths`; may be expensive)
- `--include-versions/--no-include-versions` (default: include)

Human output requirements:

- If package is not installed, say so and suggest checking the target env.
- If installed but no path from any root is found (should be rare), explain possible reasons (cycles, metadata issues).

Example (human):

```
$ py-dep-why why anyio

anyio 4.3.0 is installed.

Path 1:
  fastapi 0.110.0
    -> starlette 0.36.3
      -> anyio 4.3.0

Path 2:
  httpx 0.27.0
    -> anyio 4.3.0
```

#### 6.2.2 `roots`

Purpose: list “root” packages (top-level installed distributions).

Definition:

- A package is a **root** if **no other installed distribution depends on it** (after evaluating markers for the current environment).

Usage:

- `py-dep-why roots`

Options:

- `--include-build-tools` (default: false)
  - When false, attempt to hide common tooling roots if they are detected as global noise (e.g., `pip`, `setuptools`, `wheel`). This is heuristic-based and must be documented as such.

Output:

- Print roots sorted by normalized name.
- If `--include-versions` (default true), show versions.

#### 6.2.3 `graph`

Purpose: export dependency graph.

Usage:

- `py-dep-why graph`

Options:

- `--format json` (default when `--json` set)
- `--format dot` (Graphviz DOT)
- `--format edges` (plain `A -> B` lines)

Notes:

- `--json` forces JSON output and ignores `--format` unless `--format json`.

#### 6.2.4 `doctor`

Purpose: light diagnostics about environment parsing quality.

Usage:

- `py-dep-why doctor`

Output:

- Interpreter path, Python version
- Distribution count
- Count of edges
- List of distributions with problematic metadata (unparseable requirements, missing name/version, etc.)

Rationale: helps users understand why some edges/paths are missing.

## 7. Dependency Graph Construction

### 7.1 Data source

Primary: `importlib.metadata.distributions()` under the **target interpreter**.

For each distribution:

- `name`: distribution name
- `version`: distribution version
- `requires`: list of requirement strings (from `dist.requires`)

### 7.2 Name normalization

To match dependencies to installed distributions, normalize names using the same logic as PEP 503:

- Lowercase
- Replace runs of `[-_.]` with `-`

Store:

- `normalized_name`
- `display_name` (original)

### 7.3 Requirement parsing

Parse `Requires-Dist` entries with `packaging.requirements.Requirement`.

- Evaluate environment markers using `Requirement.marker.evaluate()` with default environment for the interpreter.
- If marker evaluates false, ignore that dependency edge.

Extras handling:

- v1 does not attempt to determine which extras were requested by dependers.
- If the requirement is of the form `pkg[extra]`, still record a dependency edge to `pkg`.

### 7.4 Graph model

Let each node represent a distribution.

- Node key: `normalized_name`
- Node attributes:
  - `name` (display)
  - `normalized_name`
  - `version`

Edges represent dependency relationships:

- Directed edge: `A -> B` means “A requires B”.

Edge attributes (optional in v1 JSON):

- `requirement`: original requirement string (useful for debugging)

### 7.5 Missing nodes

If a requirement refers to a package not installed, do not create a node by default.

- Record as a warning in `doctor` and optionally in verbose JSON metadata.

### 7.6 Cycles

Cycles can exist (rare but possible via extras / environment markers / metadata). The path search must avoid infinite loops.

Strategy:

- During path search, track visited nodes in the current path.

## 8. Algorithms

### 8.1 Roots computation

Compute incoming edge count for each installed node.

- Roots = nodes with `in_degree == 0`.
- If `--include-build-tools` is false, optionally filter out a small allowlist of “build tools” **only if they are roots**. This should be configurable and conservative.

### 8.2 Path finding for `why`

Goal: find up to `max_paths` simple paths from any root to target.

Approach:

- Perform BFS (or iterative deepening DFS) from roots to target to find shortest-ish explanations.
- Keep `max_depth` guard.
- Stop after `max_paths` unless `--all-paths`.

Path ranking:

- Prefer shorter paths.
- If multiple roots lead to target, include diverse roots.

Edge case:

- If there are no roots (e.g., fully cyclic), fall back to using all nodes as potential starts and explain the condition in output.

## 9. Output Specifications

### 9.1 Human output conventions

- Keep output compact and copy-paste friendly.
- Show versions by default.
- Indent dependencies as a tree path.

Color (unless `--no-color`):

- Package names: bold
- Warnings: yellow
- Errors: red

### 9.2 JSON output

JSON output must be stable and versioned.

- Include `schema_version` in all JSON outputs.
- v1 schema version: `1`.

#### 9.2.1 JSON for `why`

```json
{
  "schema_version": 1,
  "command": "why",
  "target": {
    "name": "anyio",
    "normalized_name": "anyio",
    "installed": true,
    "version": "4.3.0"
  },
  "environment": {
    "python": "/path/to/python",
    "python_version": "3.12.2"
  },
  "paths": [
    {
      "nodes": [
        {"name": "fastapi", "normalized_name": "fastapi", "version": "0.110.0"},
        {"name": "starlette", "normalized_name": "starlette", "version": "0.36.3"},
        {"name": "anyio", "normalized_name": "anyio", "version": "4.3.0"}
      ]
    }
  ],
  "warnings": []
}
```

Notes:

- `paths[].nodes` is an ordered list from root -> target.

#### 9.2.2 JSON for `roots`

```json
{
  "schema_version": 1,
  "command": "roots",
  "environment": {
    "python": "/path/to/python",
    "python_version": "3.12.2"
  },
  "roots": [
    {"name": "fastapi", "normalized_name": "fastapi", "version": "0.110.0"}
  ],
  "warnings": []
}
```

#### 9.2.3 JSON for `graph`

```json
{
  "schema_version": 1,
  "command": "graph",
  "environment": {
    "python": "/path/to/python",
    "python_version": "3.12.2"
  },
  "nodes": [
    {"name": "fastapi", "normalized_name": "fastapi", "version": "0.110.0"}
  ],
  "edges": [
    {"from": "fastapi", "to": "starlette", "requirement": "starlette>=0.36.3"}
  ],
  "warnings": []
}
```

#### 9.2.4 JSON for `doctor`

```json
{
  "schema_version": 1,
  "command": "doctor",
  "environment": {
    "python": "/path/to/python",
    "python_version": "3.12.2"
  },
  "stats": {
    "distributions": 123,
    "nodes": 120,
    "edges": 540,
    "missing_requirements": 7,
    "unparseable_requirements": 2
  },
  "problems": {
    "missing": [
      {"from": "somepkg", "requirement": "nonexistent>=1.0"}
    ],
    "unparseable": [
      {"from": "weirdpkg", "requirement": "???"}
    ]
  }
}
```

## 10. Project Structure (recommended)

```
py-dep-why/
  pyproject.toml
  src/
    py_dep_why/
      __init__.py
      __main__.py
      cli.py
      target_env.py
      graph.py
      normalize.py
      explain.py
      output.py
  tests/
    test_normalize.py
    test_graph_build.py
    test_why_paths.py
```

Notes:

- Use the `src/` layout.
- `__main__.py` enables `python -m py_dep_why ...` for target-interpreter execution.

## 11. Exit Codes

- `0`: success
- `1`: general error (unexpected)
- `2`: invalid usage (bad args)
- `3`: target package not installed (for `why`)
- `4`: unable to execute target interpreter / target env not found

## 12. Dependencies

Runtime (v1):

- `typer`
- `packaging`

Dev/test:

- `pytest`

Optional (nice-to-have but not required for MVP):

- `rich` (if desired for output; can also use Click styling)

## 13. Testing & CI

### 13.1 Unit tests

- Name normalization tests (PEP 503 behavior)
- Requirement parsing and marker evaluation tests
- Graph building tests with mocked distribution metadata
- Path finding tests including:
  - multiple roots
  - cycles
  - missing nodes

### 13.2 Integration tests

- Create a small fixture environment (or use `venv` in CI) with known packages and validate:
  - `roots` includes expected roots
  - `why` returns expected paths
  - JSON schema presence

### 13.3 GitHub Actions matrix

- OS: ubuntu-latest, macos-latest
- Python: 3.10, 3.11, 3.12

## 14. Performance Expectations

- Target: handle environments with ~500 distributions in < 1s to build graph on typical dev laptop.
- Avoid quadratic behavior where possible (use dicts keyed by normalized name).

## 15. Security / Safety

- No network access required.
- No mutation by default.
- Avoid executing arbitrary code from inspected environment; only read metadata.

## 16. Initial Milestones & Backlog

### Milestone 1: Core graph + CLI skeleton

- Implement `--python/--venv` targeting with re-exec via `python -m py_dep_why`.
- Implement graph build from `importlib.metadata`.
- Implement `roots` (human + JSON).

### Milestone 2: `why` explanations

- Implement `why` path finding with `--max-paths`, `--max-depth`, `--all-paths`.
- Produce clean human output and stable JSON.

### Milestone 3: Export + diagnostics

- Implement `graph` export formats (json/dot/edges).
- Implement `doctor` command and stats.

### Milestone 4: Packaging + CI

- `pyproject.toml` with console script entry point `py-dep-why`.
- Basic README (install via pipx, examples).
- CI matrix for ubuntu/macos and Python 3.10-3.12.

### Issue-sized backlog (starter)

1) Implement PEP 503 normalization helper.
2) Implement target interpreter resolution for `--venv`.
3) Implement re-exec logic preserving args for target python.
4) Build distribution index keyed by normalized name.
5) Parse `Requires-Dist` with `packaging` and evaluate markers.
6) Build edges with original requirement strings retained.
7) Compute roots and add `--include-build-tools` filter.
8) Implement BFS path search with cycle avoidance.
9) Add JSON serializers for nodes/edges/paths.
10) Add DOT exporter.
11) Add `doctor` stats and problem lists.
12) Add integration tests that create a temporary venv with known deps.
13) Add `--no-color` and consistent stderr warnings.
14) Add `--verbose` details in `doctor`.
15) Document limitations (extras, lockfiles) clearly.

## 17. Acceptance Criteria (v1)

- `py-dep-why roots` works on macOS and Linux and returns consistent roots for a given env.
- `py-dep-why why <pkg>` returns at least one correct path for common packages in real-world envs.
- `--python` and `--venv` correctly inspect that environment even when tool is installed via pipx.
- `--json` outputs include `schema_version` and conform to the structures above.
- CI passes on ubuntu + macos across Python 3.10-3.12.

## 18. Repo Bootstrap (copy this spec into the new repo folder)

This section is a practical checklist for turning this spec into a working repository.

### 18.1 Recommended repository name

- Repo: `py-dep-why`
- Package (import): `py_dep_why`
- CLI command: `py-dep-why`

### 18.2 Minimal file/folder layout (v1)

Create this structure:

```
py-dep-why/
  pyproject.toml
  README.md
  LICENSE
  src/
    py_dep_why/
      __init__.py
      __main__.py
      cli.py
      target_env.py
      graph.py
      explain.py
      normalize.py
      output.py
  tests/
    test_normalize.py
    test_graph_build.py
    test_why_paths.py
```

Notes:

- Keep logic out of `cli.py` as much as possible; use it as a thin interface.
- `__main__.py` should call the Typer app so that `python -m py_dep_why ...` works.

### 18.3 `pyproject.toml` requirements (high level)

The `pyproject.toml` should:

- Declare `typer` and `packaging` as runtime dependencies.
- Use a `src/` layout.
- Define a console script entry point:
  - `py-dep-why = py_dep_why.cli:app`
- Include an optional test dependency group with `pytest`.

Python version support:

- Recommend `>=3.10`.

### 18.4 Development workflow (local)

Suggested workflow commands (exact tooling up to you):

- Create a dev venv.
- Editable install.
- Run tests.

The project should support running as:

- `py-dep-why ...` (console script)
- `python -m py_dep_why ...` (module execution)

### 18.5 pipx workflow (what to test early)

Since pipx is a core target, validate these scenarios early:

- Install tool via pipx.
- Run it against a separate project venv using:
  - `py-dep-why --venv .venv roots`
  - `py-dep-why --python .venv/bin/python why <pkg>`

Expected behavior:

- The results should reflect the target env, not the pipx env.

### 18.6 First-commit checklist

- Add `typer` app skeleton and a working `--help`.
- Implement environment targeting/re-exec (`--python` / `--venv`).
- Implement name normalization and unit tests.
- Implement graph build from `importlib.metadata`.
- Implement `roots` with human + `--json`.
- Add CI for ubuntu + macos (Python 3.10-3.12).

### 18.7 Suggested “hello world” acceptance test

Once your CLI skeleton exists, this should work in any venv:

- `py-dep-why doctor`
- `py-dep-why roots`
- `py-dep-why why pip` (or another common installed package)
