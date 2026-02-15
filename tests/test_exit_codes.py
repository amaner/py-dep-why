"""
Tests for exit codes to ensure they match the specification.

Exit codes:
- 0: success
- 1: unexpected error
- 2: invalid usage
- 3: target package not installed (why command)
- 4: unable to execute target interpreter / target env not found
"""

import subprocess
import sys
from pathlib import Path
import tempfile


def run_cli(*args):
    """Run py-dep-why CLI and return the result."""
    return subprocess.run(
        [sys.executable, "-m", "py_dep_why"] + list(args),
        capture_output=True,
        text=True
    )


def test_exit_code_0_success():
    """Test that successful commands exit with code 0."""
    result = run_cli("--json", "roots")
    assert result.returncode == 0, f"Expected exit code 0, got {result.returncode}"


def test_exit_code_2_invalid_usage_mutual_exclusivity():
    """Test that --python and --venv together exit with code 2."""
    result = run_cli("--python", sys.executable, "--venv", "/tmp/fake", "roots")
    assert result.returncode == 2, f"Expected exit code 2 for invalid usage, got {result.returncode}"
    assert "mutually exclusive" in result.stderr.lower() or "cannot" in result.stderr.lower()


def test_exit_code_3_package_not_installed():
    """Test that 'why' command exits with code 3 for missing package."""
    result = run_cli("why", "definitely-not-installed-package-xyz")
    assert result.returncode == 3, f"Expected exit code 3 for missing package, got {result.returncode}"
    assert "not installed" in result.stderr.lower()


def test_exit_code_4_python_not_found():
    """Test that invalid --python path exits with code 4."""
    result = run_cli("--python", "/nonexistent/python", "roots")
    assert result.returncode == 4, f"Expected exit code 4 for missing interpreter, got {result.returncode}"


def test_exit_code_4_venv_not_found():
    """Test that invalid --venv path exits with code 4."""
    result = run_cli("--venv", "/nonexistent/venv", "roots")
    assert result.returncode == 4, f"Expected exit code 4 for missing venv, got {result.returncode}"


def test_exit_code_4_python_not_executable():
    """Test that non-executable file as --python exits with code 4."""
    with tempfile.NamedTemporaryFile(mode='w', delete=False) as f:
        f.write("not a python interpreter")
        temp_file = f.name
    
    try:
        result = run_cli("--python", temp_file, "roots")
        assert result.returncode == 4, f"Expected exit code 4 for non-executable, got {result.returncode}"
    finally:
        Path(temp_file).unlink()


def test_exit_code_0_doctor():
    """Test that doctor command exits with code 0."""
    result = run_cli("doctor")
    assert result.returncode == 0, f"Expected exit code 0, got {result.returncode}"


def test_exit_code_0_graph():
    """Test that graph command exits with code 0."""
    result = run_cli("graph", "--format", "edges")
    assert result.returncode == 0, f"Expected exit code 0, got {result.returncode}"


def test_exit_code_0_why_existing_package():
    """Test that 'why' command exits with code 0 for existing package."""
    # Use a package we know exists (pytest is installed in test environment)
    result = run_cli("why", "pytest")
    assert result.returncode == 0, f"Expected exit code 0 for existing package, got {result.returncode}"


def test_exit_code_1_unknown_format():
    """Test that unknown graph format exits with code 1."""
    result = run_cli("graph", "--format", "unknown-format")
    assert result.returncode == 1, f"Expected exit code 1 for unknown format, got {result.returncode}"
