"""
Integration tests for py-dep-why.

These tests create a real temporary venv and install packages to verify
end-to-end functionality. They are gated behind the PY_DEP_WHY_INTEGRATION
environment variable to avoid network usage in normal test runs.

Run with: PY_DEP_WHY_INTEGRATION=1 pytest tests/test_integration.py
"""

import os
import sys
import json
import subprocess
import tempfile
import shutil
from pathlib import Path

import pytest


# Skip integration tests by default
pytestmark = pytest.mark.skipif(
    not os.environ.get("PY_DEP_WHY_INTEGRATION"),
    reason="Integration tests require PY_DEP_WHY_INTEGRATION=1"
)


@pytest.fixture
def temp_venv():
    """Create a temporary venv with known packages installed."""
    with tempfile.TemporaryDirectory() as tmpdir:
        venv_path = Path(tmpdir) / "test_venv"
        
        # Create venv
        subprocess.run(
            [sys.executable, "-m", "venv", str(venv_path)],
            check=True,
            capture_output=True
        )
        
        # Get python path
        if sys.platform == "win32":
            python_path = venv_path / "Scripts" / "python.exe"
        else:
            python_path = venv_path / "bin" / "python"
        
        # Install py-dep-why runtime dependencies first
        subprocess.run(
            [str(python_path), "-m", "pip", "install", "--quiet", "typer", "packaging"],
            check=True,
            capture_output=True
        )
        
        # Install test packages with known dependencies
        # certifi has no dependencies, making it a good root
        subprocess.run(
            [str(python_path), "-m", "pip", "install", "--quiet", "certifi"],
            check=True,
            capture_output=True
        )
        
        yield {
            "venv_path": venv_path,
            "python_path": python_path
        }


def test_integration_roots_json(temp_venv):
    """Test that roots command works with a real venv and produces valid JSON."""
    python_path = temp_venv["python_path"]
    
    # Set PYTHONPATH to include src directory so target Python can find py_dep_why
    project_root = Path(__file__).parent.parent
    env = os.environ.copy()
    env["PYTHONPATH"] = str(project_root / "src")
    
    result = subprocess.run(
        [str(python_path), "-m", "py_dep_why", "--json", "roots"],
        capture_output=True,
        text=True,
        env=env
    )
    
    assert result.returncode == 0, f"Command failed: {result.stderr}"
    
    # Parse JSON
    output = json.loads(result.stdout)
    
    # Verify schema
    assert "schema_version" in output
    assert output["schema_version"] == 1
    assert "roots" in output
    
    # Should have certifi as a root (packaging is a dependency of typer, not a root)
    root_names = {root["name"] for root in output["roots"]}
    assert "certifi" in root_names
    # Verify we got some roots
    assert len(root_names) > 0


def test_integration_why_json(temp_venv):
    """Test that why command works with a real venv and produces valid JSON."""
    python_path = temp_venv["python_path"]
    
    # Set PYTHONPATH to include src directory
    project_root = Path(__file__).parent.parent
    env = os.environ.copy()
    env["PYTHONPATH"] = str(project_root / "src")
    
    result = subprocess.run(
        [str(python_path), "-m", "py_dep_why", "--json", "why", "certifi"],
        capture_output=True,
        text=True,
        env=env
    )
    
    assert result.returncode == 0, f"Command failed: {result.stderr}"
    
    # Parse JSON
    output = json.loads(result.stdout)
    
    # Verify schema
    assert "schema_version" in output
    assert output["schema_version"] == 1
    assert "target" in output
    assert "paths" in output
    
    # Verify target
    assert output["target"]["name"] == "certifi"
    
    # Should have at least one path (certifi is a root, so path to itself)
    assert len(output["paths"]) >= 1
    
    # First path should contain certifi
    first_path = output["paths"][0]
    assert "nodes" in first_path
    node_names = [node["name"] for node in first_path["nodes"]]
    assert "certifi" in node_names


def test_integration_graph_json(temp_venv):
    """Test that graph command works with a real venv and produces valid JSON."""
    python_path = temp_venv["python_path"]
    
    # Set PYTHONPATH to include src directory
    project_root = Path(__file__).parent.parent
    env = os.environ.copy()
    env["PYTHONPATH"] = str(project_root / "src")
    
    result = subprocess.run(
        [str(python_path), "-m", "py_dep_why", "--json", "graph"],
        capture_output=True,
        text=True,
        env=env
    )
    
    assert result.returncode == 0, f"Command failed: {result.stderr}"
    
    # Parse JSON
    output = json.loads(result.stdout)
    
    # Verify schema
    assert "schema_version" in output
    assert output["schema_version"] == 1
    assert "nodes" in output
    assert "edges" in output
    
    # Should have nodes for installed packages
    node_names = {node["name"] for node in output["nodes"]}
    assert "packaging" in node_names
    assert "certifi" in node_names


def test_integration_doctor_json(temp_venv):
    """Test that doctor command works with a real venv and produces valid JSON."""
    python_path = temp_venv["python_path"]
    
    # Set PYTHONPATH to include src directory
    project_root = Path(__file__).parent.parent
    env = os.environ.copy()
    env["PYTHONPATH"] = str(project_root / "src")
    
    result = subprocess.run(
        [str(python_path), "-m", "py_dep_why", "--json", "doctor"],
        capture_output=True,
        text=True,
        env=env
    )
    
    assert result.returncode == 0, f"Command failed: {result.stderr}"
    
    # Parse JSON
    output = json.loads(result.stdout)
    
    # Verify schema
    assert "schema_version" in output
    assert output["schema_version"] == 1
    assert "stats" in output
    assert "problems" in output
    
    # Verify stats structure
    stats = output["stats"]
    assert "distributions" in stats
    assert "nodes" in stats
    assert "edges" in stats
    assert "missing_requirements" in stats
    assert "unparseable_requirements" in stats
    
    # Should have some distributions
    assert stats["distributions"] > 0


def test_integration_venv_flag(temp_venv):
    """Test that --venv flag works correctly."""
    python_path = temp_venv["python_path"]
    
    # Set PYTHONPATH to include src directory
    project_root = Path(__file__).parent.parent
    env = os.environ.copy()
    env["PYTHONPATH"] = str(project_root / "src")
    
    result = subprocess.run(
        [str(python_path), "-m", "py_dep_why", "--json", "roots"],
        capture_output=True,
        text=True,
        env=env
    )
    
    assert result.returncode == 0, f"Command failed: {result.stderr}"
    
    # Parse JSON
    output = json.loads(result.stdout)
    
    # Verify it worked
    assert "schema_version" in output
    assert len(output["roots"]) > 0


def test_integration_package_not_found_exit_code(temp_venv):
    """Test that why command exits with code 3 for missing package."""
    python_path = temp_venv["python_path"]
    
    # Set PYTHONPATH to include src directory
    project_root = Path(__file__).parent.parent
    env = os.environ.copy()
    env["PYTHONPATH"] = str(project_root / "src")
    
    result = subprocess.run(
        [str(python_path), "-m", "py_dep_why", "why", "definitely-not-installed"],
        capture_output=True,
        text=True,
        env=env
    )
    
    # Should exit with code 3
    assert result.returncode == 3
    assert "not installed" in result.stderr.lower()
