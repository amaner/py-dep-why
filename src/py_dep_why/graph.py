import sys
from importlib.metadata import distributions, Distribution
from typing import Dict, Set, List, Optional
from dataclasses import dataclass, field

from packaging.requirements import Requirement, InvalidRequirement

from .normalize import normalize_name


@dataclass
class DistNode:
    """Represents a distribution node in the dependency graph."""
    name: str  # normalized
    version: str
    dependencies: Set[str] = field(default_factory=set)  # normalized names


@dataclass
class DependencyGraph:
    """In-memory dependency graph for the current environment."""
    nodes: Dict[str, DistNode] = field(default_factory=dict)  # normalized_name -> DistNode
    missing_deps: Set[str] = field(default_factory=set)  # normalized names
    unparseable_reqs: List[str] = field(default_factory=list)  # raw requirement strings


def build_graph() -> DependencyGraph:
    """
    Build a dependency graph from the current interpreter's installed packages.
    
    Uses importlib.metadata to enumerate distributions and parse requirements.
    Evaluates markers and filters out edges whose markers evaluate to false.
    Tracks missing dependencies and unparseable requirements as warnings.
    
    Returns:
        DependencyGraph with nodes, missing_deps, and unparseable_reqs
    """
    graph = DependencyGraph()
    
    # First pass: create nodes for all installed distributions
    for dist in distributions():
        name = normalize_name(dist.metadata.get("Name", "unknown"))
        version = dist.metadata.get("Version", "0.0.0")
        
        graph.nodes[name] = DistNode(name=name, version=version)
    
    # Second pass: parse requirements and build edges
    for dist in distributions():
        source_name = normalize_name(dist.metadata.get("Name", "unknown"))
        source_node = graph.nodes[source_name]
        
        # Get requires from metadata
        requires = dist.metadata.get_all("Requires-Dist") or []
        
        for req_str in requires:
            try:
                req = Requirement(req_str)
            except InvalidRequirement:
                graph.unparseable_reqs.append(req_str)
                continue
            
            # Evaluate marker - skip if marker evaluates to False
            if req.marker and not req.marker.evaluate():
                continue
            
            # Normalize the target package name (strip extras)
            target_name = normalize_name(req.name)
            
            # Check if target exists in our graph
            if target_name not in graph.nodes:
                graph.missing_deps.add(target_name)
                continue
            
            # Add edge from source to target
            source_node.dependencies.add(target_name)
    
    return graph


def get_node(graph: DependencyGraph, package_name: str) -> Optional[DistNode]:
    """
    Get a node from the graph by package name (normalizes the name).
    
    Args:
        graph: The dependency graph
        package_name: Package name (will be normalized)
        
    Returns:
        DistNode if found, None otherwise
    """
    normalized = normalize_name(package_name)
    return graph.nodes.get(normalized)


def compute_roots(graph: DependencyGraph, include_build_tools: bool = False) -> List[DistNode]:
    """
    Compute root packages (packages with in-degree == 0).
    
    Root packages are those that are not dependencies of any other package.
    
    Args:
        graph: The dependency graph
        include_build_tools: If False, filters out common build tools (pip, setuptools, wheel)
                           only if they are roots
        
    Returns:
        Sorted list of root DistNodes (sorted by normalized name)
    """
    # Conservative allowlist of build tools to filter
    BUILD_TOOLS = {"pip", "setuptools", "wheel"}
    
    # Calculate in-degree for each node
    in_degree = {name: 0 for name in graph.nodes}
    
    for node in graph.nodes.values():
        for dep in node.dependencies:
            if dep in in_degree:
                in_degree[dep] += 1
    
    # Find roots (in-degree == 0)
    roots = []
    for name, degree in in_degree.items():
        if degree == 0:
            node = graph.nodes[name]
            
            # Filter build tools if requested
            if not include_build_tools and name in BUILD_TOOLS:
                continue
            
            roots.append(node)
    
    # Sort by normalized name
    roots.sort(key=lambda n: n.name)
    
    return roots
