# py-dep-why

A Python CLI tool that explains **why** a package is present in your environment by building a dependency graph and answering questions like:

- What pulled in package `X`?
- What are the root (top-level) packages?
- What dependency paths exist from roots to `X`?
- Export the dependency graph for visualization or tooling

## Features

- 🔍 **Explain dependencies** - Find all paths from root packages to any installed package
- 📊 **List root packages** - Identify top-level packages in your environment
- 🗺️ **Export dependency graphs** - Output in JSON, DOT (Graphviz), or plain edges format
- 🩺 **Environment diagnostics** - Check for missing dependencies and parsing issues
- 🎯 **Target any environment** - Inspect other venvs or Python installations
- 📦 **pipx-friendly** - Works great when installed via pipx
- 🔄 **JSON output** - Machine-readable output for automation and CI

## Installation

### Recommended: pipx

```bash
pipx install py-dep-why
```

### Alternative: pip

```bash
pip install py-dep-why
```

### From source

```bash
git clone https://github.com/yourusername/py-dep-why.git
cd py-dep-why
pip install -e .
```

## Usage

### Basic Commands

#### `why` - Explain why a package is installed

```bash
# Find out why 'urllib3' is in your environment
py-dep-why why urllib3

# Output:
# Found 2 path(s) to 'urllib3':
#
# Path 1:
#   requests (2.28.0)
#     urllib3 (1.26.0)
#
# Path 2:
#   httpx (0.27.0)
#     urllib3 (1.26.0)
```

**Options:**
- `--max-paths N` - Limit number of paths shown (default: 5)
- `--max-depth N` - Maximum search depth (default: 25)
- `--all-paths` - Show all paths (overrides --max-paths)
- `--no-include-versions` - Hide version numbers

#### `roots` - List root packages

```bash
# Show all root packages (packages nothing else depends on)
py-dep-why roots

# Output:
# fastapi (0.110.0)
# pytest (9.0.2)
# myapp (1.0.0)
```

**Options:**
- `--include-build-tools` - Include pip, setuptools, wheel if they are roots
- `--no-include-versions` - Hide version numbers

#### `graph` - Export dependency graph

```bash
# Export as JSON
py-dep-why graph --format json

# Export as Graphviz DOT
py-dep-why graph --format dot > deps.dot
dot -Tpng deps.dot -o deps.png

# Export as plain edges
py-dep-why graph --format edges
```

**Formats:**
- `json` - Structured JSON with nodes and edges (default)
- `dot` - Graphviz DOT format for visualization
- `edges` - Plain text `A -> B` format

#### `doctor` - Environment diagnostics

```bash
# Check for dependency issues
py-dep-why doctor

# Output:
# Environment Diagnostics
# ==================================================
# Python: /path/to/python
# Python Version: 3.11.5
#
# Statistics:
#   Distributions: 45
#   Dependency edges: 123
#   Missing requirements: 0
#   Unparseable requirements: 0
#
# ✓ No problems detected!
```

### Global Options

All commands support these global options:

#### Target Environment Selection

```bash
# Inspect a specific Python interpreter
py-dep-why --python /path/to/python why requests

# Inspect a virtual environment
py-dep-why --venv /path/to/venv why requests

# Default: uses current Python (sys.executable)
py-dep-why why requests
```

**Note:** `--python` and `--venv` are mutually exclusive.

#### Output Format

```bash
# JSON output (machine-readable)
py-dep-why --json roots

# Output:
# {
#   "schema_version": 1,
#   "roots": [
#     {"name": "fastapi", "version": "0.110.0"}
#   ]
# }
```

#### Other Options

```bash
# Disable ANSI colors
py-dep-why --no-color roots

# Verbose output (extra diagnostics)
py-dep-why --verbose doctor
```

### JSON Output Schema

All commands support `--json` for machine-readable output with a stable schema:

#### `why` command

```json
{
  "schema_version": 1,
  "environment": {
    "python": "/path/to/python",
    "python_version": "3.11.5"
  },
  "target": {
    "name": "urllib3",
    "version": "1.26.0"
  },
  "paths": [
    {
      "nodes": [
        {"name": "requests", "version": "2.28.0"},
        {"name": "urllib3", "version": "1.26.0"}
      ]
    }
  ],
  "warnings": []
}
```

#### `roots` command

```json
{
  "schema_version": 1,
  "roots": [
    {"name": "fastapi", "version": "0.110.0"}
  ]
}
```

#### `graph` command

```json
{
  "schema_version": 1,
  "environment": {
    "python": "/path/to/python",
    "python_version": "3.11.5"
  },
  "nodes": [
    {"name": "requests", "version": "2.28.0"}
  ],
  "edges": [
    {"from": "requests", "to": "urllib3"}
  ],
  "warnings": []
}
```

#### `doctor` command

```json
{
  "schema_version": 1,
  "environment": {
    "python": "/path/to/python",
    "python_version": "3.11.5"
  },
  "stats": {
    "distributions": 45,
    "nodes": 45,
    "edges": 123,
    "missing_requirements": 0,
    "unparseable_requirements": 0
  },
  "problems": {
    "missing_requirements": [],
    "unparseable_requirements": []
  }
}
```

## Exit Codes

`py-dep-why` uses consistent exit codes for automation and CI:

- **0** - Success
- **1** - Unexpected error
- **2** - Invalid usage (e.g., conflicting options)
- **3** - Target package not installed (for `why` command)
- **4** - Unable to execute target interpreter / target environment not found

### Examples

```bash
# Success
py-dep-why roots
echo $?  # 0

# Package not found
py-dep-why why nonexistent-package
echo $?  # 3

# Invalid usage
py-dep-why --python /usr/bin/python --venv /path/to/venv roots
echo $?  # 2

# Target not found
py-dep-why --python /nonexistent/python roots
echo $?  # 4
```

## Use Cases

### Debugging "Why is this installed?"

```bash
# You notice an unexpected package
py-dep-why why some-unexpected-package

# Find out which of your dependencies pulled it in
```

### Reducing Dependency Bloat

```bash
# List all root packages
py-dep-why roots

# Identify which roots you actually need
# Remove unnecessary roots to reduce transitive dependencies
```

### CI/CD Enforcement

```bash
# Fail CI if a forbidden package is present
py-dep-why why forbidden-package && exit 1 || exit 0

# Export dependency graph for analysis
py-dep-why --json graph > deps.json
```

### Visualizing Dependencies

```bash
# Generate a dependency graph visualization
py-dep-why graph --format dot > deps.dot
dot -Tpng deps.dot -o deps.png
open deps.png
```

### Environment Health Check

```bash
# Check for dependency issues before deployment
py-dep-why --json doctor > health.json

# Parse health.json in your deployment pipeline
```

## How It Works

`py-dep-why` uses Python's built-in `importlib.metadata` to:

1. Enumerate all installed distributions in the target environment
2. Parse `Requires-Dist` metadata using `packaging.requirements`
3. Evaluate environment markers to determine active dependencies
4. Build an in-memory dependency graph
5. Perform BFS (breadth-first search) to find paths between packages

**Key features:**
- Handles cycles gracefully (tracks visited nodes per path)
- Evaluates markers for the target environment
- Normalizes package names per PEP 503
- Tracks missing dependencies and unparseable requirements

## Development

### Clone and Setup

```bash
# Clone the repository
git clone https://github.com/yourusername/py-dep-why.git
cd py-dep-why

# Create a virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install in editable mode with test dependencies
pip install -e ".[test]"
```

### Running Tests

```bash
# Run all tests
pytest -q

# Run with verbose output
pytest -v

# Run specific test file
pytest tests/test_graph_build.py -v

# Run integration tests (requires network)
PY_DEP_WHY_INTEGRATION=1 pytest tests/test_integration.py -v
```

### Code Structure

```
py-dep-why/
├── src/py_dep_why/
│   ├── __init__.py
│   ├── __main__.py       # Module entry point
│   ├── cli.py            # Typer CLI application
│   ├── target_env.py     # Environment resolution and re-exec
│   ├── graph.py          # Dependency graph construction
│   ├── explain.py        # Path finding algorithms
│   ├── normalize.py      # PEP 503 name normalization
│   └── output.py         # Output formatting helpers
├── tests/
│   ├── test_normalize.py
│   ├── test_target_env.py
│   ├── test_graph_build.py
│   ├── test_roots.py
│   ├── test_why_paths.py
│   ├── test_why_command.py
│   ├── test_graph_command.py
│   ├── test_doctor_command.py
│   ├── test_output.py
│   ├── test_exit_codes.py
│   └── test_integration.py
└── pyproject.toml
```

### Contributing

Contributions are welcome! Please:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Make your changes
4. Add tests for new functionality
5. Ensure all tests pass (`pytest -q`)
6. Commit your changes (`git commit -m 'Add amazing feature'`)
7. Push to the branch (`git push origin feature/amazing-feature`)
8. Open a Pull Request

### Running CI Locally

The GitHub Actions workflow runs on:
- **OS:** ubuntu-latest, macos-latest
- **Python:** 3.10, 3.11, 3.12

To test locally:

```bash
# Test on your current Python version
pytest -q

# Test with different Python versions (using pyenv or similar)
pyenv install 3.10 3.11 3.12
pyenv local 3.10
pip install -e ".[test]"
pytest -q
```

## Limitations

### v1 Scope

- **No lockfile parsing** - Analyzes installed packages only (not Poetry/uv/pip-tools lockfiles)
- **No vulnerability scanning** - Use `pip-audit` or `safety` for security checks
- **No resolver** - Explains current state, doesn't resolve dependencies
- **Extras handling** - Doesn't track which extras were requested, only that a dependency exists

### Platform Support

- **Tested:** macOS, Linux (Ubuntu)
- **Windows:** Should work but not extensively tested in v1

## License

MIT License - see [LICENSE](LICENSE) file for details.

## Acknowledgments

Built with:
- [typer](https://typer.tiangolo.com/) - CLI framework
- [packaging](https://packaging.pypa.io/) - Requirement parsing and marker evaluation

Inspired by tools like `pipdeptree` and `pip-audit`.

## Support

- **Issues:** [GitHub Issues](https://github.com/yourusername/py-dep-why/issues)
- **Discussions:** [GitHub Discussions](https://github.com/yourusername/py-dep-why/discussions)

---

**Made with ❤️ for Python developers who want to understand their dependencies.**
