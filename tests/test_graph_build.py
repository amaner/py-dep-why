import pytest
from unittest.mock import Mock, patch
from packaging.requirements import Requirement

from py_dep_why.graph import build_graph, get_node, DistNode, DependencyGraph
from py_dep_why.normalize import normalize_name


def create_mock_distribution(name: str, version: str, requires: list = None):
    """Create a mock Distribution object for testing."""
    mock_dist = Mock()
    mock_dist.metadata.get.side_effect = lambda key, default=None: {
        "Name": name,
        "Version": version,
    }.get(key, default)
    mock_dist.metadata.get_all.return_value = requires or []
    return mock_dist


def test_build_graph_empty():
    """Test building a graph with no distributions."""
    with patch("py_dep_why.graph.distributions", return_value=[]):
        graph = build_graph()
        assert len(graph.nodes) == 0
        assert len(graph.missing_deps) == 0
        assert len(graph.unparseable_reqs) == 0


def test_build_graph_single_package_no_deps():
    """Test building a graph with a single package with no dependencies."""
    mock_dist = create_mock_distribution("requests", "2.28.0", [])
    
    with patch("py_dep_why.graph.distributions", return_value=[mock_dist]):
        graph = build_graph()
        
        assert len(graph.nodes) == 1
        assert "requests" in graph.nodes
        assert graph.nodes["requests"].name == "requests"
        assert graph.nodes["requests"].version == "2.28.0"
        assert len(graph.nodes["requests"].dependencies) == 0


def test_build_graph_with_dependencies():
    """Test building a graph with dependencies."""
    mock_requests = create_mock_distribution(
        "requests", "2.28.0",
        ["urllib3>=1.21.1", "certifi>=2017.4.17"]
    )
    mock_urllib3 = create_mock_distribution("urllib3", "1.26.0", [])
    mock_certifi = create_mock_distribution("certifi", "2022.12.7", [])
    
    with patch("py_dep_why.graph.distributions", return_value=[mock_requests, mock_urllib3, mock_certifi]):
        graph = build_graph()
        
        assert len(graph.nodes) == 3
        assert "requests" in graph.nodes
        assert "urllib3" in graph.nodes
        assert "certifi" in graph.nodes
        
        # Check edges
        assert "urllib3" in graph.nodes["requests"].dependencies
        assert "certifi" in graph.nodes["requests"].dependencies


def test_build_graph_marker_false_no_edge():
    """Test that requirements with false markers don't create edges."""
    # Create a requirement with a marker that evaluates to False
    mock_dist = create_mock_distribution(
        "mypackage", "1.0.0",
        ['somepackage; python_version < "2.0"']  # This should be False for Python 3+
    )
    mock_somepackage = create_mock_distribution("somepackage", "1.0.0", [])
    
    with patch("py_dep_why.graph.distributions", return_value=[mock_dist, mock_somepackage]):
        graph = build_graph()
        
        # Both packages should exist as nodes
        assert "mypackage" in graph.nodes
        assert "somepackage" in graph.nodes
        
        # But no edge should exist because marker is False
        assert "somepackage" not in graph.nodes["mypackage"].dependencies


def test_build_graph_marker_true_creates_edge():
    """Test that requirements with true markers do create edges."""
    # Create a requirement with a marker that evaluates to True
    mock_dist = create_mock_distribution(
        "mypackage", "1.0.0",
        ['somepackage; python_version >= "3.0"']  # This should be True for Python 3+
    )
    mock_somepackage = create_mock_distribution("somepackage", "1.0.0", [])
    
    with patch("py_dep_why.graph.distributions", return_value=[mock_dist, mock_somepackage]):
        graph = build_graph()
        
        # Edge should exist because marker is True
        assert "somepackage" in graph.nodes["mypackage"].dependencies


def test_build_graph_missing_dependency():
    """Test that missing dependencies are tracked as warnings."""
    mock_dist = create_mock_distribution(
        "mypackage", "1.0.0",
        ["missing-package>=1.0.0"]
    )
    
    with patch("py_dep_why.graph.distributions", return_value=[mock_dist]):
        graph = build_graph()
        
        assert len(graph.nodes) == 1
        assert "mypackage" in graph.nodes
        
        # Missing dependency should be tracked
        assert "missing-package" in graph.missing_deps
        
        # No edge should be created to missing package
        assert "missing-package" not in graph.nodes["mypackage"].dependencies


def test_build_graph_unparseable_requirement():
    """Test that unparseable requirements are tracked as warnings."""
    mock_dist = create_mock_distribution(
        "mypackage", "1.0.0",
        ["this is not a valid requirement string!!!"]
    )
    
    with patch("py_dep_why.graph.distributions", return_value=[mock_dist]):
        graph = build_graph()
        
        assert len(graph.nodes) == 1
        assert len(graph.unparseable_reqs) == 1
        assert "this is not a valid requirement string!!!" in graph.unparseable_reqs


def test_build_graph_extras_stripped():
    """Test that extras are stripped from package names when creating edges."""
    mock_dist = create_mock_distribution(
        "mypackage", "1.0.0",
        ["requests[security]>=2.0.0"]
    )
    mock_requests = create_mock_distribution("requests", "2.28.0", [])
    
    with patch("py_dep_why.graph.distributions", return_value=[mock_dist, mock_requests]):
        graph = build_graph()
        
        # Edge should point to 'requests', not 'requests[security]'
        assert "requests" in graph.nodes["mypackage"].dependencies


def test_build_graph_name_normalization():
    """Test that package names are normalized according to PEP 503."""
    mock_dist1 = create_mock_distribution("My_Package", "1.0.0", ["Other.Package>=1.0"])
    mock_dist2 = create_mock_distribution("other-package", "2.0.0", [])
    
    with patch("py_dep_why.graph.distributions", return_value=[mock_dist1, mock_dist2]):
        graph = build_graph()
        
        # Both should be normalized
        assert "my-package" in graph.nodes
        assert "other-package" in graph.nodes
        
        # Edge should use normalized name
        assert "other-package" in graph.nodes["my-package"].dependencies


def test_get_node():
    """Test the get_node helper function."""
    graph = DependencyGraph()
    graph.nodes["my-package"] = DistNode(name="my-package", version="1.0.0")
    
    # Should normalize the input name
    node = get_node(graph, "My_Package")
    assert node is not None
    assert node.name == "my-package"
    
    # Non-existent package
    node = get_node(graph, "does-not-exist")
    assert node is None


def test_build_graph_complex_scenario():
    """Test a more complex graph with multiple dependencies and edge cases."""
    mock_app = create_mock_distribution(
        "myapp", "1.0.0",
        [
            "requests>=2.0.0",
            "flask>=2.0.0",
            "dev-only-package; extra == 'dev'",  # Should be filtered by marker
        ]
    )
    mock_requests = create_mock_distribution(
        "requests", "2.28.0",
        ["urllib3>=1.21.1", "certifi>=2017.4.17"]
    )
    mock_flask = create_mock_distribution(
        "flask", "2.3.0",
        ["werkzeug>=2.0.0", "jinja2>=3.0.0"]
    )
    mock_urllib3 = create_mock_distribution("urllib3", "1.26.0", [])
    mock_certifi = create_mock_distribution("certifi", "2022.12.7", [])
    mock_werkzeug = create_mock_distribution("werkzeug", "2.3.0", [])
    mock_jinja2 = create_mock_distribution("jinja2", "3.1.0", [])
    
    with patch("py_dep_why.graph.distributions", return_value=[
        mock_app, mock_requests, mock_flask, mock_urllib3, 
        mock_certifi, mock_werkzeug, mock_jinja2
    ]):
        graph = build_graph()
        
        assert len(graph.nodes) == 7
        
        # Check myapp dependencies
        assert "requests" in graph.nodes["myapp"].dependencies
        assert "flask" in graph.nodes["myapp"].dependencies
        assert "dev-only-package" not in graph.nodes["myapp"].dependencies
        
        # Check requests dependencies
        assert "urllib3" in graph.nodes["requests"].dependencies
        assert "certifi" in graph.nodes["requests"].dependencies
        
        # Check flask dependencies
        assert "werkzeug" in graph.nodes["flask"].dependencies
        assert "jinja2" in graph.nodes["flask"].dependencies
