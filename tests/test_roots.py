import pytest
from py_dep_why.graph import DependencyGraph, DistNode, compute_roots


def test_compute_roots_empty_graph():
    """Test computing roots on an empty graph."""
    graph = DependencyGraph()
    roots = compute_roots(graph)
    assert len(roots) == 0


def test_compute_roots_single_package():
    """Test computing roots with a single package (should be a root)."""
    graph = DependencyGraph()
    graph.nodes["myapp"] = DistNode(name="myapp", version="1.0.0")
    
    roots = compute_roots(graph)
    assert len(roots) == 1
    assert roots[0].name == "myapp"


def test_compute_roots_simple_chain():
    """Test computing roots with a simple dependency chain: A -> B -> C."""
    graph = DependencyGraph()
    graph.nodes["a"] = DistNode(name="a", version="1.0.0", dependencies={"b"})
    graph.nodes["b"] = DistNode(name="b", version="1.0.0", dependencies={"c"})
    graph.nodes["c"] = DistNode(name="c", version="1.0.0")
    
    roots = compute_roots(graph)
    assert len(roots) == 1
    assert roots[0].name == "a"


def test_compute_roots_multiple_roots():
    """Test computing roots with multiple independent packages."""
    graph = DependencyGraph()
    graph.nodes["app1"] = DistNode(name="app1", version="1.0.0", dependencies={"lib1"})
    graph.nodes["app2"] = DistNode(name="app2", version="1.0.0", dependencies={"lib2"})
    graph.nodes["lib1"] = DistNode(name="lib1", version="1.0.0")
    graph.nodes["lib2"] = DistNode(name="lib2", version="1.0.0")
    
    roots = compute_roots(graph)
    assert len(roots) == 2
    # Should be sorted by name
    assert roots[0].name == "app1"
    assert roots[1].name == "app2"


def test_compute_roots_diamond_dependency():
    """Test computing roots with diamond dependency: A -> B,C -> D."""
    graph = DependencyGraph()
    graph.nodes["a"] = DistNode(name="a", version="1.0.0", dependencies={"b", "c"})
    graph.nodes["b"] = DistNode(name="b", version="1.0.0", dependencies={"d"})
    graph.nodes["c"] = DistNode(name="c", version="1.0.0", dependencies={"d"})
    graph.nodes["d"] = DistNode(name="d", version="1.0.0")
    
    roots = compute_roots(graph)
    assert len(roots) == 1
    assert roots[0].name == "a"


def test_compute_roots_filters_build_tools_by_default():
    """Test that build tools (pip, setuptools, wheel) are filtered out by default."""
    graph = DependencyGraph()
    graph.nodes["myapp"] = DistNode(name="myapp", version="1.0.0", dependencies={"requests"})
    graph.nodes["requests"] = DistNode(name="requests", version="2.28.0")
    graph.nodes["pip"] = DistNode(name="pip", version="22.0.0")
    graph.nodes["setuptools"] = DistNode(name="setuptools", version="65.0.0")
    graph.nodes["wheel"] = DistNode(name="wheel", version="0.38.0")
    
    roots = compute_roots(graph, include_build_tools=False)
    
    # Only myapp should be in roots (build tools filtered)
    assert len(roots) == 1
    assert roots[0].name == "myapp"


def test_compute_roots_includes_build_tools_when_requested():
    """Test that build tools are included when include_build_tools=True."""
    graph = DependencyGraph()
    graph.nodes["myapp"] = DistNode(name="myapp", version="1.0.0", dependencies={"requests"})
    graph.nodes["requests"] = DistNode(name="requests", version="2.28.0")
    graph.nodes["pip"] = DistNode(name="pip", version="22.0.0")
    graph.nodes["setuptools"] = DistNode(name="setuptools", version="65.0.0")
    graph.nodes["wheel"] = DistNode(name="wheel", version="0.38.0")
    
    roots = compute_roots(graph, include_build_tools=True)
    
    # All roots should be included
    assert len(roots) == 4
    root_names = {r.name for r in roots}
    assert root_names == {"myapp", "pip", "setuptools", "wheel"}


def test_compute_roots_build_tools_not_filtered_if_dependencies():
    """Test that build tools are NOT filtered if they have dependencies (not roots)."""
    graph = DependencyGraph()
    graph.nodes["myapp"] = DistNode(name="myapp", version="1.0.0", dependencies={"pip"})
    graph.nodes["pip"] = DistNode(name="pip", version="22.0.0", dependencies={"setuptools"})
    graph.nodes["setuptools"] = DistNode(name="setuptools", version="65.0.0")
    
    roots = compute_roots(graph, include_build_tools=False)
    
    # myapp is the only root (pip and setuptools are dependencies, not roots)
    assert len(roots) == 1
    assert roots[0].name == "myapp"


def test_compute_roots_sorted_by_name():
    """Test that roots are sorted alphabetically by normalized name."""
    graph = DependencyGraph()
    graph.nodes["zebra"] = DistNode(name="zebra", version="1.0.0")
    graph.nodes["alpha"] = DistNode(name="alpha", version="1.0.0")
    graph.nodes["beta"] = DistNode(name="beta", version="1.0.0")
    
    roots = compute_roots(graph)
    
    assert len(roots) == 3
    assert roots[0].name == "alpha"
    assert roots[1].name == "beta"
    assert roots[2].name == "zebra"


def test_compute_roots_complex_graph():
    """Test computing roots on a more complex realistic graph."""
    graph = DependencyGraph()
    
    # Application layer
    graph.nodes["myapp"] = DistNode(name="myapp", version="1.0.0", dependencies={"requests", "flask"})
    
    # Web frameworks
    graph.nodes["flask"] = DistNode(name="flask", version="2.3.0", dependencies={"werkzeug", "jinja2"})
    graph.nodes["requests"] = DistNode(name="requests", version="2.28.0", dependencies={"urllib3", "certifi"})
    
    # Lower-level libraries
    graph.nodes["werkzeug"] = DistNode(name="werkzeug", version="2.3.0")
    graph.nodes["jinja2"] = DistNode(name="jinja2", version="3.1.0")
    graph.nodes["urllib3"] = DistNode(name="urllib3", version="1.26.0")
    graph.nodes["certifi"] = DistNode(name="certifi", version="2022.12.7")
    
    # Build tools (should be filtered by default)
    graph.nodes["pip"] = DistNode(name="pip", version="22.0.0")
    graph.nodes["setuptools"] = DistNode(name="setuptools", version="65.0.0")
    
    roots = compute_roots(graph, include_build_tools=False)
    
    # Only myapp should be a root
    assert len(roots) == 1
    assert roots[0].name == "myapp"
    
    # With build tools included
    roots_with_build = compute_roots(graph, include_build_tools=True)
    assert len(roots_with_build) == 3
    root_names = {r.name for r in roots_with_build}
    assert root_names == {"myapp", "pip", "setuptools"}
