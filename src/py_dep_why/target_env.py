import os
import sys
import subprocess
from pathlib import Path
from typing import Optional, List


class TargetEnvError(Exception):
    """Base exception for target environment errors."""
    def __init__(self, message: str, exit_code: int):
        super().__init__(message)
        self.exit_code = exit_code


class InvalidUsageError(TargetEnvError):
    """Invalid usage (exit code 2)."""
    def __init__(self, message: str):
        super().__init__(message, exit_code=2)


class TargetNotFoundError(TargetEnvError):
    """Target environment not found or not executable (exit code 4)."""
    def __init__(self, message: str):
        super().__init__(message, exit_code=4)


def resolve_target_python(
    python_path: Optional[str] = None,
    venv_path: Optional[str] = None,
) -> str:
    """
    Resolve the target Python interpreter path.
    
    Args:
        python_path: Explicit path to Python interpreter (--python)
        venv_path: Path to venv directory (--venv)
        
    Returns:
        Absolute path to the target Python interpreter
        
    Raises:
        InvalidUsageError: If both python_path and venv_path are provided
        TargetNotFoundError: If the resolved interpreter doesn't exist or isn't executable
    """
    # Enforce mutual exclusivity
    if python_path and venv_path:
        raise InvalidUsageError(
            "Cannot specify both --python and --venv. Choose one."
        )
    
    # Resolve the target interpreter
    if python_path:
        target = Path(python_path).resolve()
    elif venv_path:
        # POSIX: ${VENV}/bin/python
        venv = Path(venv_path).resolve()
        target = venv / "bin" / "python"
    else:
        # Default: current interpreter
        return sys.executable
    
    # Validate the target exists and is executable
    if not target.exists():
        raise TargetNotFoundError(
            f"Target Python interpreter not found: {target}"
        )
    
    if not os.access(target, os.X_OK):
        raise TargetNotFoundError(
            f"Target Python interpreter is not executable: {target}"
        )
    
    return str(target)


def re_exec_if_needed(target_python: str, original_args: List[str]) -> None:
    """
    Re-execute the tool under the target interpreter if needed.
    
    If target_python differs from sys.executable, this function will:
    - Strip --python/--venv from the original args
    - Re-invoke as: target_python -m py_dep_why <filtered_args>
    - Exit with the subprocess exit code
    
    Args:
        target_python: Resolved target interpreter path
        original_args: Original sys.argv (including script name)
        
    Raises:
        SystemExit: Always exits if re-exec happens (with subprocess exit code)
        TargetNotFoundError: If subprocess execution fails (exit code 4)
    """
    # If we're already running under the target interpreter, do nothing
    if target_python == sys.executable:
        return
    
    # Filter out --python/--venv and their values from args
    filtered_args = []
    skip_next = False
    
    for i, arg in enumerate(original_args[1:], start=1):  # Skip argv[0] (script name)
        if skip_next:
            skip_next = False
            continue
        
        if arg in ("--python", "--venv"):
            skip_next = True  # Skip the next arg (the value)
            continue
        
        # Handle --python=VALUE or --venv=VALUE
        if arg.startswith("--python=") or arg.startswith("--venv="):
            continue
        
        filtered_args.append(arg)
    
    # Build the re-exec command: target_python -m py_dep_why <filtered_args>
    cmd = [target_python, "-m", "py_dep_why"] + filtered_args
    
    try:
        result = subprocess.run(cmd)
        sys.exit(result.returncode)
    except (OSError, subprocess.SubprocessError) as e:
        raise TargetNotFoundError(
            f"Failed to execute target interpreter {target_python}: {e}"
        )
