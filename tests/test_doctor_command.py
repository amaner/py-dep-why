import pytest
import json
from unittest.mock import patch, Mock
from typer.testing import CliRunner

from py_dep_why.cli import app
from py_dep_why.graph import DependencyGraph, DistNode, MissingDep, UnparseableReq


runner = CliRunner()


def create_test_graph_with_problems():
    """Create a test graph with missing and unparseable requirements."""
    graph = DependencyGraph()
    graph.nodes["a"] = DistNode(name="a", version="1.0.0", dependencies={"b"})
    graph.nodes["b"] = DistNode(name="b", version="2.0.0")
    
    # Add problems
    graph.missing_deps.add("missing-pkg")
    graph.missing_deps_detailed.append(
        MissingDep(from_package="a", requirement="missing-pkg")
    )
    
    graph.unparseable_reqs.append("bad requirement string!!!")
    graph.unparseable_reqs_detailed.append(
        UnparseableReq(from_package="b", requirement="bad requirement string!!!")
    )
    
    return graph


def test_doctor_json_schema_version():
    """Test that doctor JSON output includes schema_version: 1."""
    graph = DependencyGraph()
    graph.nodes["test"] = DistNode(name="test", version="1.0.0")
    
    with patch("py_dep_why.cli.build_graph") as mock_build:
        mock_build.return_value = graph
        
        result = runner.invoke(app, ["--json", "doctor"])
        
        assert result.exit_code == 0
        output = json.loads(result.stdout)
        assert output["schema_version"] == 1


def test_doctor_json_has_required_keys():
    """Test that doctor JSON output has all required top-level keys."""
    graph = DependencyGraph()
    graph.nodes["test"] = DistNode(name="test", version="1.0.0")
    
    with patch("py_dep_why.cli.build_graph") as mock_build:
        mock_build.return_value = graph
        
        result = runner.invoke(app, ["--json", "doctor"])
        
        assert result.exit_code == 0
        output = json.loads(result.stdout)
        
        # Check required top-level keys
        assert "schema_version" in output
        assert "environment" in output
        assert "stats" in output
        assert "problems" in output


def test_doctor_json_environment_structure():
    """Test that doctor JSON environment has correct structure."""
    graph = DependencyGraph()
    graph.nodes["test"] = DistNode(name="test", version="1.0.0")
    
    with patch("py_dep_why.cli.build_graph") as mock_build:
        mock_build.return_value = graph
        
        result = runner.invoke(app, ["--json", "doctor"])
        
        assert result.exit_code == 0
        output = json.loads(result.stdout)
        
        # Check environment structure
        assert "python" in output["environment"]
        assert "python_version" in output["environment"]


def test_doctor_json_stats_structure():
    """Test that doctor JSON stats has all required fields."""
    graph = create_test_graph_with_problems()
    
    with patch("py_dep_why.cli.build_graph") as mock_build:
        mock_build.return_value = graph
        
        result = runner.invoke(app, ["--json", "doctor"])
        
        assert result.exit_code == 0
        output = json.loads(result.stdout)
        
        # Check stats structure
        stats = output["stats"]
        assert "distributions" in stats
        assert "nodes" in stats
        assert "edges" in stats
        assert "missing_requirements" in stats
        assert "unparseable_requirements" in stats
        
        # Check values
        assert stats["distributions"] == 2
        assert stats["nodes"] == 2
        assert stats["edges"] == 1
        assert stats["missing_requirements"] == 1
        assert stats["unparseable_requirements"] == 1


def test_doctor_json_problems_structure():
    """Test that doctor JSON problems has correct structure."""
    graph = create_test_graph_with_problems()
    
    with patch("py_dep_why.cli.build_graph") as mock_build:
        mock_build.return_value = graph
        
        result = runner.invoke(app, ["--json", "doctor"])
        
        assert result.exit_code == 0
        output = json.loads(result.stdout)
        
        # Check problems structure
        problems = output["problems"]
        assert "missing_requirements" in problems
        assert "unparseable_requirements" in problems
        
        # Check missing requirements
        assert isinstance(problems["missing_requirements"], list)
        assert len(problems["missing_requirements"]) == 1
        missing = problems["missing_requirements"][0]
        assert "from" in missing
        assert "requirement" in missing
        assert missing["from"] == "a"
        assert missing["requirement"] == "missing-pkg"
        
        # Check unparseable requirements
        assert isinstance(problems["unparseable_requirements"], list)
        assert len(problems["unparseable_requirements"]) == 1
        unparseable = problems["unparseable_requirements"][0]
        assert "from" in unparseable
        assert "requirement" in unparseable
        assert unparseable["from"] == "b"
        assert unparseable["requirement"] == "bad requirement string!!!"


def test_doctor_json_no_problems():
    """Test doctor JSON output when there are no problems."""
    graph = DependencyGraph()
    graph.nodes["a"] = DistNode(name="a", version="1.0.0", dependencies={"b"})
    graph.nodes["b"] = DistNode(name="b", version="2.0.0")
    
    with patch("py_dep_why.cli.build_graph") as mock_build:
        mock_build.return_value = graph
        
        result = runner.invoke(app, ["--json", "doctor"])
        
        assert result.exit_code == 0
        output = json.loads(result.stdout)
        
        # Should have empty problem lists
        assert len(output["problems"]["missing_requirements"]) == 0
        assert len(output["problems"]["unparseable_requirements"]) == 0
        assert output["stats"]["missing_requirements"] == 0
        assert output["stats"]["unparseable_requirements"] == 0


def test_doctor_human_output():
    """Test doctor human-readable output format."""
    graph = create_test_graph_with_problems()
    
    with patch("py_dep_why.cli.build_graph") as mock_build:
        mock_build.return_value = graph
        
        result = runner.invoke(app, ["doctor"])
        
        assert result.exit_code == 0
        assert "Environment Diagnostics" in result.stdout
        assert "Statistics:" in result.stdout
        assert "Distributions: 2" in result.stdout
        assert "Dependency edges: 1" in result.stdout
        assert "Missing Requirements:" in result.stdout
        assert "a requires missing-pkg" in result.stdout
        assert "Unparseable Requirements:" in result.stdout
        assert "bad requirement string!!!" in result.stdout


def test_doctor_human_output_no_problems():
    """Test doctor human output when there are no problems."""
    graph = DependencyGraph()
    graph.nodes["a"] = DistNode(name="a", version="1.0.0")
    
    with patch("py_dep_why.cli.build_graph") as mock_build:
        mock_build.return_value = graph
        
        result = runner.invoke(app, ["doctor"])
        
        assert result.exit_code == 0
        assert "No problems detected" in result.stdout


def test_doctor_counts_accuracy():
    """Test that doctor accurately counts distributions, nodes, and edges."""
    graph = DependencyGraph()
    # Create a more complex graph
    graph.nodes["a"] = DistNode(name="a", version="1.0.0", dependencies={"b", "c"})
    graph.nodes["b"] = DistNode(name="b", version="2.0.0", dependencies={"d"})
    graph.nodes["c"] = DistNode(name="c", version="3.0.0", dependencies={"d"})
    graph.nodes["d"] = DistNode(name="d", version="4.0.0")
    
    with patch("py_dep_why.cli.build_graph") as mock_build:
        mock_build.return_value = graph
        
        result = runner.invoke(app, ["--json", "doctor"])
        
        assert result.exit_code == 0
        output = json.loads(result.stdout)
        
        # 4 distributions/nodes
        assert output["stats"]["distributions"] == 4
        assert output["stats"]["nodes"] == 4
        # 4 edges: a->b, a->c, b->d, c->d
        assert output["stats"]["edges"] == 4
