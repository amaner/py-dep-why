import typer

app = typer.Typer(
    name="py-dep-why",
    help="Explain why a package is present in an environment",
    no_args_is_help=True,
)

@app.callback()
def main(
    python: str = typer.Option(None, help="Target interpreter path"),
    venv: str = typer.Option(None, help="Target venv directory"),
    json: bool = typer.Option(False, "--json", help="Output machine-readable JSON"),
    no_color: bool = typer.Option(False, "--no-color", help="Disable ANSI color"),
    verbose: bool = typer.Option(False, "--verbose", help="Include extra diagnostic details"),
):
    pass

@app.command()
def why(
    package: str,
    max_paths: int = typer.Option(5, help="Maximum paths to show"),
    max_depth: int = typer.Option(25, help="Maximum depth to search"),
    all_paths: bool = typer.Option(False, help="Show all paths (overrides --max-paths)"),
    include_versions: bool = typer.Option(True, help="Include versions in output"),
):
    """Explain why a package is present by printing dependency paths."""
    print(f"Checking why {package} is installed...")

@app.command()
def roots(
    include_build_tools: bool = typer.Option(False, help="Include common build tools"),
    include_versions: bool = typer.Option(True, help="Include versions in output"),
):
    """List root packages."""
    print("Listing root packages...")

@app.command()
def graph(
    format: str = typer.Option("json", help="Output format (json, dot, edges)"),
):
    """Export dependency graph."""
    print(f"Exporting graph in {format} format...")

@app.command()
def doctor():
    """Light diagnostics about environment parsing quality."""
    print("Running diagnostics...")

if __name__ == "__main__":
    app()
