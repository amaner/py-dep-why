import sys
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock
from py_dep_why.target_env import (
    resolve_target_python,
    re_exec_if_needed,
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


def test_re_exec_no_op_when_same_interpreter():
    """Test that re_exec_if_needed does nothing when target matches current interpreter."""
    # Should return without calling subprocess
    with patch("py_dep_why.target_env.subprocess.run") as mock_run:
        re_exec_if_needed(sys.executable, ["py-dep-why", "roots"])
        mock_run.assert_not_called()


def test_re_exec_filters_python_arg():
    """Test that --python and its value are filtered from re-exec args."""
    fake_target = "/some/other/python"
    original_args = ["py-dep-why", "--python", "/some/other/python", "roots", "--json"]
    
    with patch("py_dep_why.target_env.subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(returncode=0)
        
        with pytest.raises(SystemExit) as exc_info:
            re_exec_if_needed(fake_target, original_args)
        
        # Verify subprocess was called with filtered args
        mock_run.assert_called_once()
        cmd = mock_run.call_args[0][0]
        assert cmd[0] == fake_target
        assert cmd[1:3] == ["-m", "py_dep_why"]
        assert "--python" not in cmd
        assert "roots" in cmd
        assert "--json" in cmd
        assert exc_info.value.code == 0


def test_re_exec_filters_venv_arg():
    """Test that --venv and its value are filtered from re-exec args."""
    fake_target = "/some/venv/bin/python"
    original_args = ["py-dep-why", "--venv", "/some/venv", "why", "requests"]
    
    with patch("py_dep_why.target_env.subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(returncode=0)
        
        with pytest.raises(SystemExit) as exc_info:
            re_exec_if_needed(fake_target, original_args)
        
        cmd = mock_run.call_args[0][0]
        assert "--venv" not in cmd
        assert "/some/venv" not in cmd
        assert "why" in cmd
        assert "requests" in cmd


def test_re_exec_filters_equals_syntax():
    """Test that --python=VALUE syntax is also filtered."""
    fake_target = "/other/python"
    original_args = ["py-dep-why", "--python=/other/python", "doctor"]
    
    with patch("py_dep_why.target_env.subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(returncode=0)
        
        with pytest.raises(SystemExit):
            re_exec_if_needed(fake_target, original_args)
        
        cmd = mock_run.call_args[0][0]
        assert not any("--python" in arg for arg in cmd)
        assert "doctor" in cmd


def test_re_exec_subprocess_error():
    """Test that subprocess errors raise TargetNotFoundError with exit code 4."""
    fake_target = "/nonexistent/python"
    original_args = ["py-dep-why", "--python", fake_target, "roots"]
    
    with patch("py_dep_why.target_env.subprocess.run") as mock_run:
        mock_run.side_effect = OSError("No such file")
        
        with pytest.raises(TargetNotFoundError) as exc_info:
            re_exec_if_needed(fake_target, original_args)
        
        assert exc_info.value.exit_code == 4
