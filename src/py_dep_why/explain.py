from typing import List, Set, Optional
from collections import deque

from .graph import DependencyGraph, DistNode, compute_roots, get_node
from .normalize import normalize_name


def find_paths(
    graph: DependencyGraph,
    target: str,
    max_paths: int = 5,
    max_depth: int = 25,
    all_paths: bool = False,
) -> tuple[List[List[str]], List[str]]:
    """
    Find dependency paths from root packages to a target package.
    
    Uses BFS to find simple paths (no cycles) from roots to the target.
    Prefers shorter paths.
    
    Args:
        graph: The dependency graph
        target: Target package name (will be normalized)
        max_paths: Maximum number of paths to return (ignored if all_paths=True)
        max_depth: Maximum depth to search
        all_paths: If True, return all paths found (bounded by max_depth)
        
    Returns:
        Tuple of (paths, warnings) where:
        - paths: List of paths, each path is a list of package names from root to target
        - warnings: List of warning messages
    """
    target_normalized = normalize_name(target)
    warnings = []
    
    # Check if target exists in graph
    if target_normalized not in graph.nodes:
        return [], [f"Package '{target}' not found in environment"]
    
    # Get roots
    roots = compute_roots(graph, include_build_tools=True)
    
    # If no roots, fall back to all nodes as potential starts
    if not roots:
        warnings.append("No root packages found (possibly cyclic dependencies). Searching from all packages.")
        roots = list(graph.nodes.values())
    
    # BFS to find paths
    paths = []
    limit = None if all_paths else max_paths
    
    for root in roots:
        if limit is not None and len(paths) >= limit:
            break
        
        # BFS from this root
        # Queue contains: (current_node_name, path_so_far)
        queue = deque([(root.name, [root.name])])
        
        while queue:
            if limit is not None and len(paths) >= limit:
                break
            
            current, path = queue.popleft()
            
            # Check depth limit
            if len(path) > max_depth:
                continue
            
            # Found target?
            if current == target_normalized:
                paths.append(path)
                continue
            
            # Explore dependencies
            current_node = graph.nodes.get(current)
            if not current_node:
                continue
            
            for dep in current_node.dependencies:
                # Avoid cycles: don't revisit nodes already in this path
                if dep not in path:
                    queue.append((dep, path + [dep]))
    
    # Sort paths by length (prefer shorter paths)
    paths.sort(key=len)
    
    # Apply limit if not all_paths
    if not all_paths and max_paths > 0:
        paths = paths[:max_paths]
    
    return paths, warnings


def find_diverse_roots(
    graph: DependencyGraph,
    target: str,
    max_paths: int = 5,
    max_depth: int = 25,
) -> Set[str]:
    """
    Find diverse root packages that lead to the target.
    
    Returns the set of unique root package names that have paths to the target.
    
    Args:
        graph: The dependency graph
        target: Target package name (will be normalized)
        max_paths: Maximum number of paths to find
        max_depth: Maximum depth to search
        
    Returns:
        Set of root package names
    """
    paths, _ = find_paths(graph, target, max_paths=max_paths, max_depth=max_depth, all_paths=True)
    
    # Extract unique roots (first element of each path)
    roots = {path[0] for path in paths if path}
    
    return roots
