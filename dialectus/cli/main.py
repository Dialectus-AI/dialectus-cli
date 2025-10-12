"""Command-line interface for the Dialectus Debate System."""

import asyncio
import logging
import os
from pathlib import Path
from typing import Mapping, Protocol, cast

# Ensure UTF-8 encoding for cross-platform compatibility (Windows console, Git Bash, etc.)
os.environ["PYTHONIOENCODING"] = "utf-8"

import click
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.prompt import Confirm
from rich.table import Table

from dialectus.cli.config import AppConfig, get_default_config
from dialectus.cli.runner import DebateRunner
from dialectus.cli.database import DatabaseManager
from models.manager import ModelManager
from dialectus.cli.presentation import display_debate_info, display_error


class ModelInfo(Protocol):
    provider: str
    description: str


console = Console(force_terminal=True, legacy_windows=False)


def setup_logging(level: str = "WARNING") -> None:
    """Configure logging for the application with colored output."""

    # Custom formatter with colors for severity levels
    class ColoredFormatter(logging.Formatter):
        """Formatter that adds colors to log levels."""

        COLORS = {
            "DEBUG": "\033[90m",  # Gray/dim
            "INFO": "",  # Default (no color)
            "WARNING": "\033[33m",  # Yellow/orange
            "ERROR": "\033[31m",  # Red
            "CRITICAL": "\033[1;31m",  # Bold red
        }
        RESET = "\033[0m"

        def format(self, record: logging.LogRecord) -> str:
            color = self.COLORS.get(record.levelname, "")
            record.levelname = f"{color}{record.levelname}{self.RESET}"
            return super().format(record)

    # Configure basic logging
    handler = logging.StreamHandler()
    handler.setFormatter(
        ColoredFormatter(
            fmt="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            datefmt="%H:%M:%S",
        )
    )

    logging.basicConfig(
        level=getattr(logging, level.upper()),
        handlers=[handler],
    )

    # Suppress noisy third-party loggers
    logging.getLogger("openai").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("openai._base_client").setLevel(logging.WARNING)
    logging.getLogger("urllib3").setLevel(logging.WARNING)


@click.group()
@click.option(
    "--config",
    "-c",
    type=click.Path(exists=True),
    help="Configuration file path (default: debate_config.json)",
)
@click.option(
    "--log-level",
    default=None,
    type=click.Choice(["DEBUG", "INFO", "WARNING", "ERROR"]),
    help="Override log level from config file",
)
@click.pass_context
def cli(ctx: click.Context, config: str | None, log_level: str | None) -> None:
    """Dialectus - AI-powered debate orchestration using dialectus-engine."""
    # Load configuration first
    if config:
        app_config = AppConfig.load_from_file(Path(config))
        console.print(f"[green]OK[/green] Loaded config from {config}")
    else:
        app_config = get_default_config()
        console.print("[green]OK[/green] Loaded default config from debate_config.json")

    # Use CLI log level if provided, otherwise use config file value
    effective_log_level = (
        log_level if log_level is not None else app_config.system.log_level
    )
    setup_logging(effective_log_level)

    ctx.ensure_object(dict)
    ctx.obj["config"] = app_config


@cli.command()
@click.option("--topic", "-t", help="Debate topic")
@click.option(
    "--format",
    "-f",
    type=click.Choice(["parliamentary", "oxford", "socratic", "public_forum"]),
    help="Debate format",
)
@click.option("--interactive", "-i", is_flag=True, help="Interactive mode with pauses")
@click.pass_context
def debate(
    ctx: click.Context,
    topic: str | None,
    format: str | None,
    interactive: bool,
) -> None:
    """Start a debate between AI models using the engine directly."""
    config: AppConfig = ctx.obj["config"]

    # Override config with CLI options
    if topic:
        config.debate.topic = topic
    if format:
        config.debate.format = format  # type: ignore[assignment]

    # Display debate setup
    display_debate_info(console, config)

    if interactive and not Confirm.ask("Start the debate?"):
        console.print("[yellow]Debate cancelled[/yellow]")
        return

    # Run the debate with direct engine integration
    try:
        runner = DebateRunner(config, console)
        asyncio.run(runner.run_debate())
    except Exception as e:
        display_error(console, e)
        raise SystemExit(1)


@cli.command()
@click.pass_context
def list_models(ctx: click.Context) -> None:
    """List available models from Ollama and OpenRouter."""
    config: AppConfig = ctx.obj["config"]

    async def _list_models() -> None:
        model_manager = ModelManager(config.system)

        try:
            with Progress(
                SpinnerColumn(), TextColumn("[progress.description]{task.description}")
            ) as progress:
                task = progress.add_task("Fetching available models...", total=None)
                raw_models = await model_manager.get_available_models()

                # Type guard for model catalog structure
                if not raw_models:
                    raise TypeError("Empty model listing received")

                models = cast(Mapping[str, ModelInfo], raw_models)
                progress.remove_task(task)

            if not models:
                console.print(
                    "[red]No models available. Make sure Ollama is running or OpenRouter is configured.[/red]"
                )
                return

            table = Table(title="Available Models")
            table.add_column("Model ID", style="cyan")
            table.add_column("Provider", style="magenta")
            table.add_column("Description", style="dim")

            for model_id, model_info in sorted(models.items()):
                table.add_row(
                    model_id,
                    model_info.provider,
                    (
                        model_info.description[:60] + "..."
                        if len(model_info.description) > 60
                        else model_info.description
                    ),
                )

            console.print(table)

        except Exception as e:
            console.print(f"[red]Failed to fetch models: {e}[/red]")
            raise

    try:
        asyncio.run(_list_models())
    except Exception as e:
        display_error(console, e)
        raise SystemExit(1)


@cli.command()
@click.option(
    "--limit", "-l", default=20, help="Number of transcripts to show (default: 20)"
)
def transcripts(limit: int) -> None:
    """List saved debate transcripts from local database."""
    try:
        db = DatabaseManager()
        transcript_list = db.list_transcripts(limit=limit)

        if not transcript_list:
            console.print("[yellow]No transcripts found[/yellow]")
            return

        console.print(f"\n[bold]Found {len(transcript_list)} transcript(s):[/bold]\n")

        table = Table(title="Debate Transcripts")
        table.add_column("ID", style="cyan", justify="center")
        table.add_column("Topic", style="green")
        table.add_column("Format", style="blue")
        table.add_column("Messages", justify="center")
        table.add_column("Date", style="dim")

        for transcript in transcript_list:
            topic = transcript.get("topic", "Unknown")[:50]
            if len(transcript.get("topic", "")) > 50:
                topic += "..."

            table.add_row(
                str(transcript["id"]),
                topic,
                transcript.get("format", "Unknown"),
                str(transcript.get("message_count", 0)),
                transcript.get("created_at", "Unknown"),
            )

        console.print(table)

    except Exception as e:
        display_error(console, e)
        raise SystemExit(1)


if __name__ == "__main__":
    cli()
