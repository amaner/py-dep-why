import sys
import json
import typer
from typing import Optional

from .target_env import resolve_target_python, re_exec_if_needed, TargetEnvError
from .graph import build_graph, compute_roots, get_node
from .explain import find_paths

app = typer.Typer(
    name="py-dep-why",
    help="Explain why a package is present in an environment",
    no_args_is_help=True,
)

# Global state to pass options from callback to commands
class GlobalContext:
    def __init__(self):
        self.target_python: Optional[str] = None
        self.json_output: bool = False
        self.no_color: bool = False
        self.verbose: bool = False

ctx = GlobalContext()

@app.callback()
def main(
    python: Optional[str] = typer.Option(None, "--python", help="Target interpreter path"),
    venv: Optional[str] = typer.Option(None, "--venv", help="Target venv directory"),
    json: bool = typer.Option(False, "--json", help="Output machine-readable JSON"),
    no_color: bool = typer.Option(False, "--no-color", help="Disable ANSI color"),
    verbose: bool = typer.Option(False, "--verbose", help="Include extra diagnostic details"),
):
    """Global options for py-dep-why."""
    try:
        ctx.target_python = resolve_target_python(python_path=python, venv_path=venv)
        ctx.json_output = json
        ctx.no_color = no_color
        ctx.verbose = verbose
        
        # Re-exec under target interpreter if needed (before any command logic runs)
        re_exec_if_needed(ctx.target_python, sys.argv)
    except TargetEnvError as e:
        typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(code=e.exit_code)

@app.command()
def why(
    package: str,
    max_paths: int = typer.Option(5, help="Maximum paths to show"),
    max_depth: int = typer.Option(25, help="Maximum depth to search"),
    all_paths: bool = typer.Option(False, help="Show all paths (overrides --max-paths)"),
    include_versions: bool = typer.Option(True, help="Include versions in output"),
):
    """Explain why a package is present by printing dependency paths."""
    if ctx.verbose:
        print(f"Target Python: {ctx.target_python}", file=sys.stderr)
    
    # Build the dependency graph
    graph = build_graph()
    
    # Check if package exists
    target_node = get_node(graph, package)
    if not target_node:
        if not ctx.json_output:
            print(f"Package '{package}' is not installed in this environment.", file=sys.stderr)
        raise typer.Exit(code=3)
    
    # Find paths
    paths, warnings = find_paths(
        graph,
        package,
        max_paths=max_paths,
        max_depth=max_depth,
        all_paths=all_paths
    )
    
    # Output
    if ctx.json_output:
        # JSON output per spec
        output = {
            "schema_version": 1,
            "environment": {
                "python": ctx.target_python,
                "python_version": f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
            },
            "target": {
                "name": target_node.name,
                "version": target_node.version
            },
            "warnings": warnings,
            "paths": []
        }
        
        for path in paths:
            path_nodes = []
            for pkg_name in path:
                node = graph.nodes.get(pkg_name)
                if node:
                    if include_versions:
                        path_nodes.append({"name": node.name, "version": node.version})
                    else:
                        path_nodes.append({"name": node.name})
            output["paths"].append({"nodes": path_nodes})
        
        print(json.dumps(output, indent=2))
    else:
        # Human-readable output
        if warnings:
            for warning in warnings:
                print(f"Warning: {warning}", file=sys.stderr)
        
        if not paths:
            print(f"No dependency paths found to '{package}'.")
        else:
            print(f"Found {len(paths)} path(s) to '{package}':\n")
            
            for i, path in enumerate(paths, start=1):
                print(f"Path {i}:")
                for depth, pkg_name in enumerate(path):
                    node = graph.nodes.get(pkg_name)
                    if node:
                        indent = "  " * depth
                        if include_versions:
                            print(f"{indent}{node.name} ({node.version})")
                        else:
                            print(f"{indent}{node.name}")
                print()  # Blank line between paths

@app.command()
def roots(
    include_build_tools: bool = typer.Option(False, help="Include common build tools"),
    include_versions: bool = typer.Option(True, help="Include versions in output"),
):
    """List root packages."""
    if ctx.verbose:
        print(f"Target Python: {ctx.target_python}", file=sys.stderr)
    
    # Build the dependency graph
    graph = build_graph()
    
    # Compute roots
    root_nodes = compute_roots(graph, include_build_tools=include_build_tools)
    
    # Output
    if ctx.json_output:
        # JSON output per spec
        output = {
            "schema_version": 1,
            "roots": [
                {"name": node.name, "version": node.version} if include_versions
                else {"name": node.name}
                for node in root_nodes
            ]
        }
        print(json.dumps(output, indent=2))
    else:
        # Human-readable output
        if not root_nodes:
            print("No root packages found.")
        else:
            for node in root_nodes:
                if include_versions:
                    print(f"{node.name} ({node.version})")
                else:
                    print(node.name)

@app.command()
def graph(
    format: str = typer.Option("json", help="Output format (json, dot, edges)"),
):
    """Export dependency graph."""
    if ctx.verbose:
        print(f"Target Python: {ctx.target_python}", file=sys.stderr)
    
    # If --json global flag is set, force json format
    if ctx.json_output:
        format = "json"
        
    # Build graph
    dep_graph = build_graph()
    
    if format == "json":
        # JSON output per spec
        output = {
            "schema_version": 1,
            "environment": {
                "python": ctx.target_python,
                "python_version": f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
            },
            "nodes": [
                {"name": node.name, "version": node.version}
                for node in dep_graph.nodes.values()
            ],
            "edges": [],
            "warnings": list(dep_graph.missing_deps) + dep_graph.unparseable_reqs
        }
        
        # Collect edges
        for source_name, node in dep_graph.nodes.items():
            for target_name in node.dependencies:
                output["edges"].append({"from": source_name, "to": target_name})
                
        print(json.dumps(output, indent=2))
        
    elif format == "dot":
        # DOT format
        print('digraph "dependency-graph" {')
        print('  rankdir=LR;')
        print('  node [shape=box, style=filled, fillcolor="#ffffff"];')
        
        # Nodes
        for node in dep_graph.nodes.values():
            label = f"{node.name}\\n{node.version}"
            print(f'  "{node.name}" [label="{label}"];')
            
        # Edges
        for source_name, node in dep_graph.nodes.items():
            for target_name in node.dependencies:
                print(f'  "{source_name}" -> "{target_name}";')
                
        print('}')
        
    elif format == "edges":
        # Simple edges format
        for source_name, node in dep_graph.nodes.items():
            for target_name in node.dependencies:
                print(f"{source_name} -> {target_name}")
    
    else:
        print(f"Unknown format: {format}", file=sys.stderr)
        raise typer.Exit(code=1)

@app.command()
def doctor():
    """Light diagnostics about environment parsing quality."""
    if ctx.verbose:
        print(f"Target Python: {ctx.target_python}", file=sys.stderr)
    print("Running diagnostics...")

if __name__ == "__main__":
    app()
