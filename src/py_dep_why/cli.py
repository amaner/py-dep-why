import sys
import typer
from typing import Optional

from .target_env import resolve_target_python, TargetEnvError

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
    print(f"Checking why {package} is installed...")

@app.command()
def roots(
    include_build_tools: bool = typer.Option(False, help="Include common build tools"),
    include_versions: bool = typer.Option(True, help="Include versions in output"),
):
    """List root packages."""
    if ctx.verbose:
        print(f"Target Python: {ctx.target_python}", file=sys.stderr)
    print("Listing root packages...")

@app.command()
def graph(
    format: str = typer.Option("json", help="Output format (json, dot, edges)"),
):
    """Export dependency graph."""
    if ctx.verbose:
        print(f"Target Python: {ctx.target_python}", file=sys.stderr)
    print(f"Exporting graph in {format} format...")

@app.command()
def doctor():
    """Light diagnostics about environment parsing quality."""
    if ctx.verbose:
        print(f"Target Python: {ctx.target_python}", file=sys.stderr)
    print("Running diagnostics...")

if __name__ == "__main__":
    app()
