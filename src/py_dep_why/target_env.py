import os
import sys
from pathlib import Path
from typing import Optional


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
