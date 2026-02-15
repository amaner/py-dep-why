import pytest
import json
from unittest.mock import patch, MagicMock
from typer.testing import CliRunner

from py_dep_why.cli import app
from py_dep_why.graph import DependencyGraph, DistNode


runner = CliRunner()


def create_test_graph():
    """Create a simple test graph for command testing."""
    graph = DependencyGraph()
    graph.nodes["myapp"] = DistNode(name="myapp", version="1.0.0", dependencies={"requests"})
    graph.nodes["requests"] = DistNode(name="requests", version="2.28.0", dependencies={"urllib3"})
    graph.nodes["urllib3"] = DistNode(name="urllib3", version="1.26.0")
    return graph


def test_why_command_package_not_found_exit_code():
    """Test that why command exits with code 3 when package is not found."""
    with patch("py_dep_why.cli.build_graph") as mock_build:
        mock_build.return_value = DependencyGraph()
        
        result = runner.invoke(app, ["why", "definitely-not-installed"])
        
        assert result.exit_code == 3
        assert "not installed" in result.stderr.lower()


def test_why_command_json_schema_version():
    """Test that JSON output includes schema_version: 1."""
    graph = create_test_graph()
    
    with patch("py_dep_why.cli.build_graph") as mock_build:
        mock_build.return_value = graph
        
        result = runner.invoke(app, ["--json", "why", "urllib3"])
        
        assert result.exit_code == 0
        output = json.loads(result.stdout)
        assert output["schema_version"] == 1


def test_why_command_json_has_required_keys():
    """Test that JSON output has all required top-level keys."""
    graph = create_test_graph()
    
    with patch("py_dep_why.cli.build_graph") as mock_build:
        mock_build.return_value = graph
        
        result = runner.invoke(app, ["--json", "why", "urllib3"])
        
        assert result.exit_code == 0
        output = json.loads(result.stdout)
        
        # Check required top-level keys
        assert "schema_version" in output
        assert "environment" in output
        assert "target" in output
        assert "warnings" in output
        assert "paths" in output


def test_why_command_json_environment_structure():
    """Test that JSON environment object has correct structure."""
    graph = create_test_graph()
    
    with patch("py_dep_why.cli.build_graph") as mock_build:
        mock_build.return_value = graph
        
        result = runner.invoke(app, ["--json", "why", "urllib3"])
        
        assert result.exit_code == 0
        output = json.loads(result.stdout)
        
        # Check environment structure
        assert "python" in output["environment"]
        assert "python_version" in output["environment"]
        assert isinstance(output["environment"]["python"], str)
        assert isinstance(output["environment"]["python_version"], str)


def test_why_command_json_target_structure():
    """Test that JSON target object has correct structure."""
    graph = create_test_graph()
    
    with patch("py_dep_why.cli.build_graph") as mock_build:
        mock_build.return_value = graph
        
        result = runner.invoke(app, ["--json", "why", "urllib3"])
        
        assert result.exit_code == 0
        output = json.loads(result.stdout)
        
        # Check target structure
        assert "name" in output["target"]
        assert "version" in output["target"]
        assert output["target"]["name"] == "urllib3"
        assert output["target"]["version"] == "1.26.0"


def test_why_command_json_paths_structure():
    """Test that JSON paths array has correct structure."""
    graph = create_test_graph()
    
    with patch("py_dep_why.cli.build_graph") as mock_build:
        mock_build.return_value = graph
        
        result = runner.invoke(app, ["--json", "why", "urllib3"])
        
        assert result.exit_code == 0
        output = json.loads(result.stdout)
        
        # Check paths structure
        assert isinstance(output["paths"], list)
        assert len(output["paths"]) > 0
        
        # Check first path structure
        path = output["paths"][0]
        assert "nodes" in path
        assert isinstance(path["nodes"], list)
        
        # Check node structure (with versions by default)
        if path["nodes"]:
            node = path["nodes"][0]
            assert "name" in node
            assert "version" in node


def test_why_command_json_no_include_versions():
    """Test that --no-include-versions removes version from nodes."""
    graph = create_test_graph()
    
    with patch("py_dep_why.cli.build_graph") as mock_build:
        mock_build.return_value = graph
        
        result = runner.invoke(app, ["--json", "why", "urllib3", "--no-include-versions"])
        
        assert result.exit_code == 0
        output = json.loads(result.stdout)
        
        # Check that nodes only have name, not version
        if output["paths"] and output["paths"][0]["nodes"]:
            node = output["paths"][0]["nodes"][0]
            assert "name" in node
            assert "version" not in node


def test_why_command_human_output_format():
    """Test that human-readable output has expected format."""
    graph = create_test_graph()
    
    with patch("py_dep_why.cli.build_graph") as mock_build:
        mock_build.return_value = graph
        
        result = runner.invoke(app, ["why", "urllib3"])
        
        assert result.exit_code == 0
        assert "Path 1:" in result.stdout
        assert "myapp" in result.stdout
        assert "requests" in result.stdout
        assert "urllib3" in result.stdout


def test_why_command_human_output_with_versions():
    """Test that human output includes versions by default."""
    graph = create_test_graph()
    
    with patch("py_dep_why.cli.build_graph") as mock_build:
        mock_build.return_value = graph
        
        result = runner.invoke(app, ["why", "urllib3"])
        
        assert result.exit_code == 0
        assert "(1.0.0)" in result.stdout or "1.0.0" in result.stdout
        assert "(2.28.0)" in result.stdout or "2.28.0" in result.stdout


def test_why_command_human_output_no_versions():
    """Test that --no-include-versions removes versions from human output."""
    graph = create_test_graph()
    
    with patch("py_dep_why.cli.build_graph") as mock_build:
        mock_build.return_value = graph
        
        result = runner.invoke(app, ["why", "urllib3", "--no-include-versions"])
        
        assert result.exit_code == 0
        # Should have package names but not version numbers in parens
        assert "myapp" in result.stdout
        assert "requests" in result.stdout
        assert "urllib3" in result.stdout
        # Versions should not appear
        assert "(1.0.0)" not in result.stdout
        assert "(2.28.0)" not in result.stdout
        assert "(1.26.0)" not in result.stdout


def test_why_command_max_paths_limit():
    """Test that --max-paths limits the number of paths shown."""
    graph = DependencyGraph()
    # Create multiple paths to target
    for i in range(5):
        graph.nodes[f"app{i}"] = DistNode(name=f"app{i}", version="1.0.0", dependencies={"lib"})
    graph.nodes["lib"] = DistNode(name="lib", version="1.0.0")
    
    with patch("py_dep_why.cli.build_graph") as mock_build:
        mock_build.return_value = graph
        
        result = runner.invoke(app, ["--json", "why", "lib", "--max-paths", "2"])
        
        assert result.exit_code == 0
        output = json.loads(result.stdout)
        assert len(output["paths"]) == 2


def test_why_command_warnings_in_json():
    """Test that warnings appear in JSON output."""
    graph = DependencyGraph()
    # Create a fully cyclic graph to trigger warning
    graph.nodes["a"] = DistNode(name="a", version="1.0.0", dependencies={"b"})
    graph.nodes["b"] = DistNode(name="b", version="1.0.0", dependencies={"a"})
    
    with patch("py_dep_why.cli.build_graph") as mock_build:
        mock_build.return_value = graph
        
        result = runner.invoke(app, ["--json", "why", "a"])
        
        assert result.exit_code == 0
        output = json.loads(result.stdout)
        assert isinstance(output["warnings"], list)
