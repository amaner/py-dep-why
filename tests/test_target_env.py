import sys
import pytest
from pathlib import Path
from py_dep_why.target_env import (
    resolve_target_python,
    InvalidUsageError,
    TargetNotFoundError,
)


def test_resolve_default():
    """Test that default returns sys.executable."""
    result = resolve_target_python()
    assert result == sys.executable


def test_resolve_python_path_valid():
    """Test resolving with --python pointing to current interpreter."""
    result = resolve_target_python(python_path=sys.executable)
    assert result == str(Path(sys.executable).resolve())


def test_resolve_python_path_not_found():
    """Test that missing --python path raises TargetNotFoundError with exit code 4."""
    with pytest.raises(TargetNotFoundError) as exc_info:
        resolve_target_python(python_path="/does/not/exist/python")
    assert exc_info.value.exit_code == 4


def test_resolve_venv_not_found():
    """Test that missing --venv path raises TargetNotFoundError with exit code 4."""
    with pytest.raises(TargetNotFoundError) as exc_info:
        resolve_target_python(venv_path="/does/not/exist")
    assert exc_info.value.exit_code == 4


def test_resolve_both_python_and_venv():
    """Test that providing both --python and --venv raises InvalidUsageError with exit code 2."""
    with pytest.raises(InvalidUsageError) as exc_info:
        resolve_target_python(python_path="/some/python", venv_path="/some/venv")
    assert exc_info.value.exit_code == 2
    assert "both" in str(exc_info.value).lower()


def test_resolve_venv_valid(tmp_path):
    """Test resolving with --venv pointing to a valid venv structure."""
    # Create a mock venv structure
    venv_dir = tmp_path / "test_venv"
    bin_dir = venv_dir / "bin"
    bin_dir.mkdir(parents=True)
    
    # Create a mock python executable (just copy current interpreter)
    python_path = bin_dir / "python"
    python_path.symlink_to(sys.executable)
    
    result = resolve_target_python(venv_path=str(venv_dir))
    assert result == str(python_path)


def test_resolve_python_not_executable(tmp_path):
    """Test that non-executable file raises TargetNotFoundError."""
    # Create a non-executable file
    fake_python = tmp_path / "fake_python"
    fake_python.write_text("#!/bin/sh\necho fake")
    fake_python.chmod(0o644)  # readable but not executable
    
    with pytest.raises(TargetNotFoundError) as exc_info:
        resolve_target_python(python_path=str(fake_python))
    assert exc_info.value.exit_code == 4
    assert "not executable" in str(exc_info.value).lower()
