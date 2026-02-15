import pytest
import json
from unittest.mock import patch
from typer.testing import CliRunner

from py_dep_why.cli import app
from py_dep_why.graph import DependencyGraph, DistNode

runner = CliRunner()


def create_test_graph():
    """Create a simple test graph for command testing."""
    graph = DependencyGraph()
    graph.nodes["a"] = DistNode(name="a", version="1.0.0", dependencies={"b"})
    graph.nodes["b"] = DistNode(name="b", version="2.0.0", dependencies={"c"})
    graph.nodes["c"] = DistNode(name="c", version="3.0.0")
    return graph


def test_graph_command_edges_format():
    """Test graph command with edges format."""
    graph = create_test_graph()
    
    with patch("py_dep_why.cli.build_graph") as mock_build:
        mock_build.return_value = graph
        
        result = runner.invoke(app, ["graph", "--format", "edges"])
        
        assert result.exit_code == 0
        assert "a -> b" in result.stdout
        assert "b -> c" in result.stdout


def test_graph_command_dot_format():
    """Test graph command with dot format."""
    graph = create_test_graph()
    
    with patch("py_dep_why.cli.build_graph") as mock_build:
        mock_build.return_value = graph
        
        result = runner.invoke(app, ["graph", "--format", "dot"])
        
        assert result.exit_code == 0
        assert "digraph" in result.stdout
        assert '"a" -> "b";' in result.stdout
        assert '"b" -> "c";' in result.stdout
        assert 'label="a\\n1.0.0"' in result.stdout


def test_graph_command_json_format():
    """Test graph command with json format."""
    graph = create_test_graph()
    graph.missing_deps.add("missing")
    
    with patch("py_dep_why.cli.build_graph") as mock_build:
        mock_build.return_value = graph
        
        result = runner.invoke(app, ["graph", "--format", "json"])
        
        assert result.exit_code == 0
        output = json.loads(result.stdout)
        
        # Check structure
        assert output["schema_version"] == 1
        assert "environment" in output
        assert len(output["nodes"]) == 3
        assert len(output["edges"]) == 2
        
        # Check content
        node_names = {n["name"] for n in output["nodes"]}
        assert node_names == {"a", "b", "c"}
        
        edges = {(e["from"], e["to"]) for e in output["edges"]}
        assert ("a", "b") in edges
        assert ("b", "c") in edges
        
        assert "missing" in output["warnings"]


def test_graph_command_global_json_forces_json_format():
    """Test that global --json flag overrides --format argument."""
    graph = create_test_graph()
    
    with patch("py_dep_why.cli.build_graph") as mock_build:
        mock_build.return_value = graph
        
        # Request edges format but with global --json flag
        result = runner.invoke(app, ["--json", "graph", "--format", "edges"])
        
        assert result.exit_code == 0
        # Should be valid JSON
        output = json.loads(result.stdout)
        assert output["schema_version"] == 1


def test_graph_command_unknown_format():
    """Test that unknown format raises error."""
    with patch("py_dep_why.cli.build_graph") as mock_build:
        mock_build.return_value = DependencyGraph()
        
        result = runner.invoke(app, ["graph", "--format", "unknown"])
        
        assert result.exit_code == 1
        assert "Unknown format" in result.stderr
