import pytest
from py_dep_why.graph import DependencyGraph, DistNode
from py_dep_why.explain import find_paths, find_diverse_roots


def test_find_paths_simple_chain():
    """Test finding a path in a simple chain: A -> B -> C."""
    graph = DependencyGraph()
    graph.nodes["a"] = DistNode(name="a", version="1.0.0", dependencies={"b"})
    graph.nodes["b"] = DistNode(name="b", version="1.0.0", dependencies={"c"})
    graph.nodes["c"] = DistNode(name="c", version="1.0.0")
    
    paths, warnings = find_paths(graph, "c", max_paths=5, max_depth=25)
    
    assert len(paths) == 1
    assert paths[0] == ["a", "b", "c"]
    assert len(warnings) == 0


def test_find_paths_multiple_roots_to_target():
    """Test finding paths when multiple roots lead to the same target."""
    graph = DependencyGraph()
    graph.nodes["app1"] = DistNode(name="app1", version="1.0.0", dependencies={"lib"})
    graph.nodes["app2"] = DistNode(name="app2", version="1.0.0", dependencies={"lib"})
    graph.nodes["lib"] = DistNode(name="lib", version="1.0.0")
    
    paths, warnings = find_paths(graph, "lib", max_paths=5, max_depth=25)
    
    assert len(paths) == 2
    assert ["app1", "lib"] in paths
    assert ["app2", "lib"] in paths
    assert len(warnings) == 0


def test_find_paths_diamond_dependency():
    """Test finding paths in a diamond dependency: A -> B,C -> D."""
    graph = DependencyGraph()
    graph.nodes["a"] = DistNode(name="a", version="1.0.0", dependencies={"b", "c"})
    graph.nodes["b"] = DistNode(name="b", version="1.0.0", dependencies={"d"})
    graph.nodes["c"] = DistNode(name="c", version="1.0.0", dependencies={"d"})
    graph.nodes["d"] = DistNode(name="d", version="1.0.0")
    
    paths, warnings = find_paths(graph, "d", max_paths=5, max_depth=25)
    
    # Should find both paths through b and c
    assert len(paths) == 2
    assert ["a", "b", "d"] in paths
    assert ["a", "c", "d"] in paths


def test_find_paths_with_cycle_still_finds_path():
    """Test that cycles don't prevent finding valid paths."""
    graph = DependencyGraph()
    # Root -> A -> B -> C (valid path)
    # A -> B -> A (creates cycle between a and b)
    graph.nodes["root"] = DistNode(name="root", version="1.0.0", dependencies={"a"})
    graph.nodes["a"] = DistNode(name="a", version="1.0.0", dependencies={"b"})
    graph.nodes["b"] = DistNode(name="b", version="1.0.0", dependencies={"a", "c"})
    graph.nodes["c"] = DistNode(name="c", version="1.0.0")
    
    paths, warnings = find_paths(graph, "c", max_paths=5, max_depth=25)
    
    # Should find paths despite the cycle between a and b
    # c is also a root, so it will have a self-path
    assert len(paths) >= 1
    # The path from root should exist
    assert ["root", "a", "b", "c"] in paths


def test_find_paths_target_not_reachable():
    """Test when target exists but is not reachable from any root."""
    graph = DependencyGraph()
    graph.nodes["a"] = DistNode(name="a", version="1.0.0", dependencies={"b"})
    graph.nodes["b"] = DistNode(name="b", version="1.0.0")
    graph.nodes["isolated"] = DistNode(name="isolated", version="1.0.0")
    
    paths, warnings = find_paths(graph, "isolated", max_paths=5, max_depth=25)
    
    # isolated is a root itself, so it should find itself
    assert len(paths) == 1
    assert paths[0] == ["isolated"]


def test_find_paths_target_not_found():
    """Test when target package doesn't exist in the graph."""
    graph = DependencyGraph()
    graph.nodes["a"] = DistNode(name="a", version="1.0.0")
    
    paths, warnings = find_paths(graph, "nonexistent", max_paths=5, max_depth=25)
    
    assert len(paths) == 0
    assert len(warnings) == 1
    assert "not found" in warnings[0].lower()


def test_find_paths_no_roots_fallback():
    """Test fallback when there are no roots (fully cyclic graph)."""
    graph = DependencyGraph()
    # Create a cycle: A -> B -> C -> A
    graph.nodes["a"] = DistNode(name="a", version="1.0.0", dependencies={"b"})
    graph.nodes["b"] = DistNode(name="b", version="1.0.0", dependencies={"c"})
    graph.nodes["c"] = DistNode(name="c", version="1.0.0", dependencies={"a"})
    
    paths, warnings = find_paths(graph, "b", max_paths=5, max_depth=25)
    
    # Should find paths starting from all nodes
    assert len(paths) > 0
    assert len(warnings) == 1
    assert "no root packages" in warnings[0].lower()


def test_find_paths_max_paths_limit():
    """Test that max_paths limits the number of returned paths."""
    graph = DependencyGraph()
    # Create multiple paths to target
    for i in range(10):
        graph.nodes[f"app{i}"] = DistNode(name=f"app{i}", version="1.0.0", dependencies={"lib"})
    graph.nodes["lib"] = DistNode(name="lib", version="1.0.0")
    
    paths, warnings = find_paths(graph, "lib", max_paths=3, max_depth=25)
    
    assert len(paths) == 3


def test_find_paths_all_paths_ignores_limit():
    """Test that all_paths=True returns all paths regardless of max_paths."""
    graph = DependencyGraph()
    # Create multiple paths to target
    for i in range(5):
        graph.nodes[f"app{i}"] = DistNode(name=f"app{i}", version="1.0.0", dependencies={"lib"})
    graph.nodes["lib"] = DistNode(name="lib", version="1.0.0")
    
    paths, warnings = find_paths(graph, "lib", max_paths=2, max_depth=25, all_paths=True)
    
    # Should return all 5 paths, not just 2
    assert len(paths) == 5


def test_find_paths_max_depth_limit():
    """Test that max_depth limits the search depth."""
    graph = DependencyGraph()
    # Create a long chain: A -> B -> C -> D -> E -> F
    graph.nodes["a"] = DistNode(name="a", version="1.0.0", dependencies={"b"})
    graph.nodes["b"] = DistNode(name="b", version="1.0.0", dependencies={"c"})
    graph.nodes["c"] = DistNode(name="c", version="1.0.0", dependencies={"d"})
    graph.nodes["d"] = DistNode(name="d", version="1.0.0", dependencies={"e"})
    graph.nodes["e"] = DistNode(name="e", version="1.0.0", dependencies={"f"})
    graph.nodes["f"] = DistNode(name="f", version="1.0.0")
    
    # Search with max_depth=3 (should not reach f)
    paths, warnings = find_paths(graph, "f", max_paths=5, max_depth=3)
    
    assert len(paths) == 0  # Path is too deep


def test_find_paths_prefers_shorter_paths():
    """Test that shorter paths are returned first."""
    graph = DependencyGraph()
    # Create two paths: A -> B -> C (length 3) and A -> C (length 2)
    graph.nodes["a"] = DistNode(name="a", version="1.0.0", dependencies={"b", "c"})
    graph.nodes["b"] = DistNode(name="b", version="1.0.0", dependencies={"c"})
    graph.nodes["c"] = DistNode(name="c", version="1.0.0")
    
    paths, warnings = find_paths(graph, "c", max_paths=5, max_depth=25)
    
    assert len(paths) == 2
    # Shorter path should come first
    assert paths[0] == ["a", "c"]
    assert paths[1] == ["a", "b", "c"]


def test_find_paths_complex_graph():
    """Test path finding in a more complex realistic graph."""
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
    
    # Find paths to urllib3
    paths, warnings = find_paths(graph, "urllib3", max_paths=5, max_depth=25)
    
    assert len(paths) == 1
    assert paths[0] == ["myapp", "requests", "urllib3"]


def test_find_diverse_roots():
    """Test finding diverse roots that lead to a target."""
    graph = DependencyGraph()
    graph.nodes["app1"] = DistNode(name="app1", version="1.0.0", dependencies={"lib"})
    graph.nodes["app2"] = DistNode(name="app2", version="1.0.0", dependencies={"lib"})
    graph.nodes["app3"] = DistNode(name="app3", version="1.0.0", dependencies={"other"})
    graph.nodes["lib"] = DistNode(name="lib", version="1.0.0")
    graph.nodes["other"] = DistNode(name="other", version="1.0.0")
    
    roots = find_diverse_roots(graph, "lib", max_paths=5, max_depth=25)
    
    assert len(roots) == 2
    assert "app1" in roots
    assert "app2" in roots
    assert "app3" not in roots


def test_find_paths_name_normalization():
    """Test that package names are normalized when searching."""
    graph = DependencyGraph()
    graph.nodes["my-app"] = DistNode(name="my-app", version="1.0.0", dependencies={"my-lib"})
    graph.nodes["my-lib"] = DistNode(name="my-lib", version="1.0.0")
    
    # Search using non-normalized name
    paths, warnings = find_paths(graph, "My_Lib", max_paths=5, max_depth=25)
    
    assert len(paths) == 1
    assert paths[0] == ["my-app", "my-lib"]
