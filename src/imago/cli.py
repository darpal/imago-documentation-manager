"""CLI entry point for Imago documentation manager."""

from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.table import Table

from imago.config import get_config

app = typer.Typer(
    name="imago",
    help="AI-powered documentation coach for managing and improving technical documentation.",
    no_args_is_help=True,
)
console = Console()

# Sub-command groups
repo_app = typer.Typer(help="Manage documentation repositories")
config_app = typer.Typer(help="Configure Imago settings")
app.add_typer(repo_app, name="repo")
app.add_typer(config_app, name="config")


# === Repository Commands ===


@repo_app.command("add")
def repo_add(
    url: str = typer.Argument(..., help="Git repository URL"),
    name: Optional[str] = typer.Option(None, "--name", "-n", help="Alias for the repository"),
):
    """Clone and track a documentation repository."""
    from imago.git.repository import RepoManager

    config = get_config()
    config.ensure_directories()

    manager = RepoManager(config.repos_dir)
    repo_name = manager.add(url, name)
    console.print(f"[green]Added repository:[/green] {repo_name}")


@repo_app.command("list")
def repo_list():
    """List all tracked repositories."""
    from imago.git.repository import RepoManager

    config = get_config()
    manager = RepoManager(config.repos_dir)
    repos = manager.list_repos()

    if not repos:
        console.print("[yellow]No repositories tracked yet.[/yellow]")
        console.print("Use [bold]imago repo add <url>[/bold] to add one.")
        return

    table = Table(title="Tracked Repositories")
    table.add_column("Name", style="cyan")
    table.add_column("Path", style="dim")
    table.add_column("Branch", style="green")
    table.add_column("Status", style="yellow")

    for repo in repos:
        table.add_row(repo["name"], repo["path"], repo["branch"], repo["status"])

    console.print(table)


@repo_app.command("pull")
def repo_pull(
    name: Optional[str] = typer.Argument(None, help="Repository name (pulls all if not specified)"),
):
    """Pull latest changes from remote."""
    from imago.git.repository import RepoManager

    config = get_config()
    manager = RepoManager(config.repos_dir)

    if name:
        result = manager.pull(name)
        console.print(f"[green]Pulled:[/green] {name} - {result}")
    else:
        results = manager.pull_all()
        for repo_name, status in results.items():
            console.print(f"[green]Pulled:[/green] {repo_name} - {status}")


@repo_app.command("push")
def repo_push(
    name: Optional[str] = typer.Argument(None, help="Repository name"),
    message: str = typer.Option("Documentation update", "--message", "-m", help="Commit message"),
):
    """Commit and push changes to remote."""
    from imago.git.repository import RepoManager

    config = get_config()
    manager = RepoManager(config.repos_dir)

    if not name:
        console.print("[red]Error:[/red] Repository name required for push")
        raise typer.Exit(1)

    result = manager.push(name, message)
    console.print(f"[green]Pushed:[/green] {name} - {result}")


# === Analysis Commands ===


@app.command("analyze")
def analyze(
    name: Optional[str] = typer.Argument(None, help="Repository name to analyze"),
):
    """Run full documentation analysis on a repository."""
    from imago.git.repository import RepoManager
    from imago.analysis.indexer import DocumentIndexer
    from imago.analysis.validator import DocumentValidator
    from imago.analysis.stats import DocumentStats

    config = get_config()
    manager = RepoManager(config.repos_dir)

    repo_path = manager.get_repo_path(name)
    if not repo_path:
        console.print("[red]Error:[/red] Repository not found")
        raise typer.Exit(1)

    console.print(f"[bold]Analyzing:[/bold] {repo_path}")

    # Run analysis
    with console.status("Indexing documents..."):
        indexer = DocumentIndexer(config.index_path)
        doc_count = indexer.index_repository(repo_path)
        console.print(f"  Indexed [cyan]{doc_count}[/cyan] documents")

    with console.status("Validating structure..."):
        validator = DocumentValidator(repo_path)
        issues = validator.validate()
        if issues:
            console.print(f"  Found [yellow]{len(issues)}[/yellow] issues")
            for issue in issues[:5]:
                console.print(f"    - {issue}")
            if len(issues) > 5:
                console.print(f"    ... and {len(issues) - 5} more")
        else:
            console.print("  [green]No structural issues found[/green]")

    with console.status("Gathering statistics..."):
        stats = DocumentStats(repo_path)
        summary = stats.summary()
        console.print(f"  Total documents: [cyan]{summary['total_documents']}[/cyan]")
        console.print(f"  Total words: [cyan]{summary['total_words']:,}[/cyan]")
        console.print(f"  Avg words/doc: [cyan]{summary['avg_words_per_doc']:.0f}[/cyan]")


@app.command("review")
def review(
    file: Path = typer.Argument(..., help="Path to the document to review"),
):
    """Get AI-powered review of a specific document."""
    from imago.ai.coach import DocumentationCoach

    config = get_config()

    if not file.exists():
        console.print(f"[red]Error:[/red] File not found: {file}")
        raise typer.Exit(1)

    coach = DocumentationCoach(config.anthropic_api_key)

    with console.status("Analyzing document..."):
        content = file.read_text()
        review_result = coach.review_document(content, file.name)

    console.print("\n[bold]Documentation Review[/bold]\n")
    console.print(review_result)


@app.command("gaps")
def gaps(
    name: Optional[str] = typer.Argument(None, help="Repository name"),
    output: Optional[Path] = typer.Option(None, "--output", "-o", help="Output file path"),
):
    """Identify documentation gaps and missing content."""
    from datetime import datetime
    from imago.git.repository import RepoManager
    from imago.ai.coach import DocumentationCoach
    from imago.analysis.stats import DocumentStats

    config = get_config()
    manager = RepoManager(config.repos_dir)

    repo_path = manager.get_repo_path(name)
    if not repo_path:
        console.print("[red]Error:[/red] Repository not found")
        raise typer.Exit(1)

    coach = DocumentationCoach(config.anthropic_api_key)
    stats = DocumentStats(repo_path)

    with console.status("Analyzing documentation structure..."):
        structure = stats.get_structure()
        gap_analysis = coach.analyze_gaps(structure)

    console.print("\n[bold]Gap Analysis[/bold]\n")
    console.print(gap_analysis)

    # Auto-save to file
    if output:
        output_path = output
    else:
        # Create _Gap_Analysis folder in the repo
        gap_folder = repo_path / "_Gap_Analysis"
        gap_folder.mkdir(exist_ok=True)
        # Generate filename with ISO datetime
        timestamp = datetime.now().strftime("%Y-%m-%dT%H-%M-%S")
        output_path = gap_folder / f"Gap Analysis {timestamp}.md"

    output_path.write_text(gap_analysis)
    console.print(f"\n[green]Saved to:[/green] {output_path}")


@app.command("search")
def search(
    query: str = typer.Argument(..., help="Search query"),
    limit: int = typer.Option(10, "--limit", "-l", help="Maximum results"),
):
    """Search across all indexed documentation."""
    from imago.analysis.indexer import DocumentIndexer

    config = get_config()
    indexer = DocumentIndexer(config.index_path)

    results = indexer.search(query, limit=limit)

    if not results:
        console.print(f"[yellow]No results found for:[/yellow] {query}")
        return

    console.print(f"\n[bold]Search results for:[/bold] {query}\n")
    for result in results:
        console.print(f"[cyan]{result['file']}[/cyan]")
        console.print(f"  {result['snippet']}")
        console.print()


# === Interactive Commands ===


@app.command("chat")
def chat(
    name: Optional[str] = typer.Argument(None, help="Repository name for context"),
):
    """Start an interactive session with the documentation coach."""
    from imago.git.repository import RepoManager
    from imago.ai.coach import DocumentationCoach
    from imago.analysis.stats import DocumentStats

    config = get_config()

    if not config.anthropic_api_key:
        console.print("[red]Error:[/red] Anthropic API key not configured")
        console.print("Set it with: [bold]imago config set anthropic_api_key <key>[/bold]")
        console.print("Or set the ANTHROPIC_API_KEY environment variable")
        raise typer.Exit(1)

    manager = RepoManager(config.repos_dir)
    repo_path = manager.get_repo_path(name) if name else None

    context = None
    if repo_path:
        stats = DocumentStats(repo_path)
        context = stats.get_structure()

    coach = DocumentationCoach(config.anthropic_api_key)

    console.print("\n[bold]Documentation Coach[/bold]")
    console.print("Type [cyan]quit[/cyan] or [cyan]exit[/cyan] to end the session.\n")

    coach.start_session(context)

    while True:
        try:
            user_input = console.input("[bold green]You:[/bold green] ")
        except (KeyboardInterrupt, EOFError):
            break

        if user_input.lower() in ("quit", "exit", "q"):
            break

        if not user_input.strip():
            continue

        with console.status("Thinking..."):
            response = coach.chat(user_input)

        console.print(f"\n[bold blue]Coach:[/bold blue] {response}\n")

    console.print("\n[dim]Session ended.[/dim]")


# === Report Commands ===


@app.command("report")
def report(
    name: Optional[str] = typer.Argument(None, help="Repository name"),
    format: str = typer.Option("md", "--format", "-f", help="Output format (md or html)"),
    output: Optional[Path] = typer.Option(None, "--output", "-o", help="Output file path"),
):
    """Generate a documentation health report."""
    from imago.git.repository import RepoManager
    from imago.reports.generator import ReportGenerator

    config = get_config()
    manager = RepoManager(config.repos_dir)

    repo_path = manager.get_repo_path(name)
    if not repo_path:
        console.print("[red]Error:[/red] Repository not found")
        raise typer.Exit(1)

    generator = ReportGenerator(repo_path, config)

    with console.status("Generating report..."):
        report_content = generator.generate(format=format)

    if output:
        output.write_text(report_content)
        console.print(f"[green]Report saved to:[/green] {output}")
    else:
        console.print(report_content)


# === Config Commands ===


@config_app.command("set")
def config_set(
    key: str = typer.Argument(..., help="Configuration key"),
    value: str = typer.Argument(..., help="Configuration value"),
):
    """Set a configuration value."""
    config = get_config()
    config.set(key, value)
    console.print(f"[green]Set:[/green] {key} = {value}")


@config_app.command("show")
def config_show():
    """Show current configuration."""
    config = get_config()
    all_config = config.all()

    table = Table(title="Configuration")
    table.add_column("Key", style="cyan")
    table.add_column("Value", style="green")

    for key, value in sorted(all_config.items()):
        display_value = "***" if "api_key" in key and value else str(value)
        table.add_row(key, display_value)

    console.print(table)


@config_app.command("path")
def config_path():
    """Show configuration file path."""
    config = get_config()
    console.print(f"Config file: {config.config_path}")


if __name__ == "__main__":
    app()
