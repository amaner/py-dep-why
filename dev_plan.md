# Development Plan: Low-Blast-Radius Agent Prompts
 
 Use the following prompts sequentially. Each prompt is intentionally scoped so your agent can complete it in one small PR-sized change.
 
 ---
 
 ## Prompt 0 — Create and activate a local dev venv
 
 **Model recommendation:** Gemini 3 Flash
 
 **Prompt:**
 
 Create a fresh local development virtual environment in the repo and activate it.
 
 - Use Python 3.11.5.
 - Create the venv in `.venv/`.
 - Activation (macOS/Linux): `source .venv/bin/activate`.
 - Upgrade packaging tooling: `python -m pip install -U pip setuptools wheel`.
 
 Do not implement any project code yet.
 
 **Acceptance checks:**
 
 - `python -V` shows the expected interpreter.
 - `which python` points inside `.venv`.
 - `python -m pip --version` points at `.venv`.
 
 ---
 
 ## Prompt 1 — Repo inventory + bootstrap checklist
 
 **Model recommendation:** Gemini 3 Flash
 
 **Prompt:**
 
 Read `py_dep_why_spec.md` and the current repository tree. Then:
 
 - Confirm whether the repo already has `pyproject.toml`, `src/py_dep_why/*`, and `tests/*` as suggested by the spec.
 - If anything is missing, create only the minimal scaffolding files/folders needed to run `python -m py_dep_why --help` (empty modules are fine for now).
 - Add runtime deps (`typer`, `packaging`) and test dep (`pytest`) to `pyproject.toml` (use a standard modern layout).
 - Ensure `py-dep-why` console script entry point points to `py_dep_why.cli:app`.
 
 **Acceptance checks:**
 
 - `python -m py_dep_why --help` works.
 - `python -c "import py_dep_why"` works.
 
 ---
 
 ## Prompt 2 — Implement name normalization helper + unit tests
 
 **Model recommendation:** Claude Sonnet 4.5
 
 **Prompt:**
 
 Implement PEP 503 normalization in `src/py_dep_why/normalize.py`:
 
 - Function `normalize_name(name: str) -> str` that:
   - lowercases
   - replaces runs of `[-_.]` with `-`
 
 Add unit tests in `tests/test_normalize.py` to cover:
 
 - `Foo_Bar` -> `foo-bar`
 - `foo.bar` -> `foo-bar`
 - `foo--bar` -> `foo-bar` (run collapse)
 - Decide and test whitespace handling (strip or preserve) consistently
 
 **Acceptance checks:**
 
 - `pytest -q` passes.
 
 ---
 
 ## Prompt 3 — Create CLI skeleton (Typer) with global options + subcommands
 
 **Model recommendation:** Claude Sonnet 4.5
 
 **Prompt:**
 
 Implement a Typer app in `src/py_dep_why/cli.py` with commands (no real logic yet):
 
 - Global options on the app:
   - `--python PATH`
   - `--venv PATH`
   - `--json`
   - `--no-color`
   - `--verbose`
 - Subcommands:
   - `why <package>` with options `--max-paths`, `--max-depth`, `--all-paths`, `--include-versions/--no-include-versions`
   - `roots` with `--include-build-tools`, `--include-versions/--no-include-versions`
   - `graph` with `--format` (`json|dot|edges`)
   - `doctor`
 
 Ensure `src/py_dep_why/__main__.py` runs the app so `python -m py_dep_why ...` works.
 
 Do not implement functionality yet—only argument parsing and help text.
 
 **Acceptance checks:**
 
 - `python -m py_dep_why --help` shows global options and commands.
 - `python -m py_dep_why why --help` shows the `why` options.
 
 ---
 
 ## Prompt 4 — Target environment resolution (`--venv` -> interpreter) and argument validation
 
 **Model recommendation:** Claude Sonnet 4.5
 
 **Prompt:**
 
 Implement `src/py_dep_why/target_env.py` with:
 
 - A function to resolve the target interpreter path based on:
   - default: `sys.executable`
   - `--python PATH`
   - `--venv PATH` resolving to `${VENV}/bin/python` (POSIX)
 - Enforce `--python` and `--venv` mutually exclusive.
 - Raise/return a structured error that CLI can map to exit code `2` (invalid usage) for bad args, and `4` for missing/unexecutable interpreter.
 
 Wire this into the CLI so every command computes a `target_python` string (even if it equals `sys.executable`).
 
 **Acceptance checks:**
 
 *Note: these will be run manually by user - do not run automatically. User will tell agent if they work or fail.*
 - `python -m py_dep_why --venv /does/not/exist roots` exits with code `4`.
 - `python -m py_dep_why --python x --venv y roots` exits with code `2`.
 
 ---
 
 ## Prompt 5 — Implement re-exec into target interpreter (`python -m py_dep_why ...`)
 
 **Model recommendation:** Claude Sonnet 4.5
 
 **Prompt:**
 
 Implement the spec’s pipx-safe behavior:
 
 - If `target_python != sys.executable`, re-invoke the tool as:
   - `target_python -m py_dep_why <original args minus the --python/--venv selectors>`
 - Preserve all other args exactly.
 - Ensure `--json` remains honored.
 - Ensure errors executing the subprocess map to exit code `4`.
 
 Keep the re-exec logic centralized (e.g., a helper in `target_env.py`), and keep `cli.py` thin.
 
re-exec should happen in the callback immediately (before any command logic runs).

 **Acceptance checks:**
 
 - When run with `--python SOME_OTHER_PY`, it executes under that interpreter (prove via `--verbose` output only; never in JSON mode).
 
 ---
 
 ## Prompt 6 — Graph data model + graph construction from `importlib.metadata`
 
 **Model recommendation:** Claude Sonnet 4.5
 
 **Prompt:**
 
 Implement `src/py_dep_why/graph.py` to build an in-memory dependency graph under the *current* interpreter (re-exec already ensures this is the target env):
 
 - Enumerate installed distributions via `importlib.metadata.distributions()`.
 - Build a node index keyed by normalized name.
 - Parse requirements using `packaging.requirements.Requirement`.
 - Evaluate markers; ignore edges whose markers evaluate to false.
 - For requirements with extras (`pkg[extra]`), still edge to `pkg`.
 - Do not create nodes for missing dependencies; track them as warnings for `doctor`.
 - Also track unparseable requirement strings.
 
 Add unit tests in `tests/test_graph_build.py` using mocked distributions (do not depend on the developer machine’s installed packages).
 
 **Acceptance checks:**
 
 *Note: user will run tests manually - do not run automatically. Just output commands to run.*

 - `pytest -q` passes.
 - Tests cover marker false -> no edge.
 - Tests cover missing dependency -> warning captured.
 
 ---
 
 ## Prompt 7 — Roots computation + `roots` command output (human + JSON)
 
 **Model recommendation:** Claude Sonnet 4.5
 
 **Prompt:**
 
 Implement roots:
 
 - Compute `in_degree` from edges.
 - Roots are nodes with `in_degree == 0`.
 - Add `--include-build-tools` filtering that *only* removes build tools if they are roots (conservative allowlist: `pip`, `setuptools`, `wheel`).
 - Sort roots by normalized name.
 - Output:
   - Human-readable list to stdout when not `--json`.
   - JSON schema per spec when `--json`.
 
 Add tests for roots computation using a small synthetic graph.
 
 **Acceptance checks:**
 
 *Note: user will run tests manually - do not run automatically. Just output commands to run.*
 
 - `python -m py_dep_why roots --json` emits JSON with `schema_version: 1`.
 - `pytest -q` passes.
 
 ---
 
 ## Prompt 8 — Path finding algorithm for `why` (BFS/iterative) + cycle avoidance
 
 **Model recommendation:** Claude Sonnet 4.5
 
 **Prompt:**
 
 Implement path search in `src/py_dep_why/explain.py`:
 
 - Find up to `max_paths` simple paths from any root to `target`.
 - Honor `max_depth`.
 - If `--all-paths`, return all found paths (bounded by `max_depth`).
 - Avoid infinite loops by tracking visited nodes per-path.
 - If there are no roots, fall back to treating all nodes as potential starts and record a warning.
 - Prefer shorter paths.
 
 Add tests in `tests/test_why_paths.py` covering:
 
 - Multiple roots to same target (diverse roots)
 - Cycle present but still finds path
 - Target not reachable
 - No roots (fully cyclic) fallback
 
 **Acceptance checks:**
 
 *Note: user will run tests manually - do not run automatically. Just output commands to run.*
 
 - `pytest -q` passes.
 
 ---
 
 ## Prompt 9 — Implement `why` command behavior + exit code 3 when not installed
 
 **Model recommendation:** Claude Sonnet 4.5
 
 **Prompt:**
 
 Wire `why` command end-to-end:
 
 - Normalize input package name.
 - If target package not installed in node index, print human message and exit code `3`.
 - Otherwise compute paths and print:
   - Human output with “Path 1/2/…” format and indentation as in spec.
   - JSON output per spec when `--json` (include environment python path/version, `warnings`, and `paths[].nodes`).
 - Include versions by default; honor `--no-include-versions`.
 
 Add tests for JSON structure stability (schema_version, keys present).
 
 **Acceptance checks:**
 
 - `python -m py_dep_why why definitely-not-installed` exits `3`.
 - `pytest -q` passes.
 
 ---
 
 ## Prompt 10 — Implement `graph` export (`json`, `dot`, `edges`)
 
 **Model recommendation:** Gemini 3 Pro
 
 **Prompt:**
 
 Implement `graph` command exporters:
 
 - JSON output matches spec (nodes, edges, warnings, environment, schema_version).
 - DOT output: directed graph, quote node ids safely.
 - `edges` output: plain lines `A -> B` using normalized names.
 
 Behavior rules:
 
 - If `--json` is set, force JSON output regardless of `--format`.
 
 Add tests for each format with a small synthetic graph.
 
 **Acceptance checks:**
 
 - `python -m py_dep_why graph --format edges` prints `A -> B` lines.
 - `pytest -q` passes.
 
 ---
 
 ## Prompt 11 — Implement `doctor` diagnostics + JSON schema
 
 **Model recommendation:** Gemini 3 Pro
 
 **Prompt:**
 
 Implement `doctor`:
 
 - Print / emit JSON containing:
   - environment python path/version
   - stats: distributions, nodes, edges, missing_requirements, unparseable_requirements
   - problems: lists of missing and unparseable requirements (with `from` and `requirement`)
 - Honor `--json` (stdout JSON only).
 - Honor `--verbose` to include extra detail, but keep stable keys.
 
 Add tests verifying counts and structure using mocked distributions.
 
 **Acceptance checks:**
 
 - `python -m py_dep_why doctor --json` matches the spec’s shape.
 - `pytest -q` passes.
 
 ---
 
 ## Prompt 12 — Output handling (`--no-color`, stderr warnings, JSON purity)
 
 **Model recommendation:** Gemini 3 Flash
 
 **Prompt:**
 
 Create `src/py_dep_why/output.py` that centralizes printing:
 
 - Ensure when `--json` is enabled:
   - stdout is JSON only
   - any warnings go to stderr
 - Add optional color formatting, disabled by `--no-color`.
 
 Refactor commands to use this output helper with minimal behavior change.
 
 **Acceptance checks:**
 
 - A deliberately triggered warning does not pollute JSON stdout.
 - `pytest -q` passes.
 
 ---
 
 ## Prompt 13 — Integration test: create a temporary venv and run CLI against it
 
 **Model recommendation:** Claude Opus 4.6
 
 **Prompt:**
 
 Add an integration test that:
 
 - Creates a temporary venv
 - Installs a small set of packages with known relationships
 - Executes `python -m py_dep_why --python <venv_python> roots --json`
 - Executes `python -m py_dep_why --python <venv_python> why <known-transitive-dep> --json`
 - Asserts JSON parses, `schema_version` is present, and at least one path exists
 
 Keep network usage optional:
 
 - Gate the test behind `PY_DEP_WHY_INTEGRATION=1` and skip by default.
 
 **Acceptance checks:**
 
 - `pytest -q` passes with integration test skipped.
 - With `PY_DEP_WHY_INTEGRATION=1`, the integration test passes locally.
 
 ---
 
 ## Prompt 14 — Exit code audit and consistent error mapping
 
 **Model recommendation:** Gemini 3 Flash
 
 **Prompt:**
 
 Audit all commands and ensure exit codes match spec:
 
 - `0` success
 - `1` unexpected error
 - `2` invalid usage
 - `3` target package not installed (why)
 - `4` unable to execute target interpreter / target env not found
 
 Add tests for the key exit codes using subprocess invocation.
 
 **Acceptance checks:**
 
 - `pytest -q` passes.
 
 ---
 
 ## Prompt 15 — CI (GitHub Actions) matrix: ubuntu + macos, Python 3.10–3.12
 
 **Model recommendation:** Gemini 3 Pro
 
 **Prompt:**
 
 Add GitHub Actions workflow:
 
 - Runs `pytest -q`
 - Matrix:
   - OS: ubuntu-latest, macos-latest
   - Python: 3.10, 3.11, 3.12
 - Uses caching
 - Installs package in editable mode with test dependencies
 
 Keep it minimal and stable.
 
 **Acceptance checks:**
 
 - Workflow YAML is valid.
 - Local tests still pass.