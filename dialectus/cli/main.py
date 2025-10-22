"""Command-line interface for the Dialectus Debate System."""

import asyncio
import logging
import os
import sys
from pathlib import Path

# Allow running this module either as ``python -m dialectus.cli`` or
# ``python dialectus/cli/main.py`` by ensuring the project root is on sys.path.
if __package__ in {None, ""}:
    project_root = Path(__file__).resolve().parents[2]
    if str(project_root) not in sys.path:
        sys.path.insert(0, str(project_root))
    __package__ = "dialectus.cli"

# Ensure UTF-8 encoding for cross-platform compatibility (Windows console, Git Bash, etc.)
os.environ["PYTHONIOENCODING"] = "utf-8"

# Force UTF-8 encoding on Windows for Rich Console to handle Unicode characters
# This fixes Git Bash/Windows console cp1252 encoding issues with box-drawing chars
# Skip this when running under pytest to avoid conflicts with pytest's capture mechanism
if sys.platform == "win32" and "pytest" not in sys.modules:
    import io

    # Wrap stdout with UTF-8 encoding, ignoring errors for incompatible chars
    sys.stdout = io.TextIOWrapper(
        sys.stdout.buffer, encoding="utf-8", errors="replace", line_buffering=True
    )
    sys.stderr = io.TextIOWrapper(
        sys.stderr.buffer, encoding="utf-8", errors="replace", line_buffering=True
    )

import click
from rich.console import Console
from rich.prompt import Confirm
from rich.table import Table

from dialectus.cli.config import AppConfig, ConfigurationError, get_default_config
from dialectus.cli.runner import DebateRunner
from dialectus.cli.database import DatabaseManager
from dialectus.cli.presentation import display_debate_info, display_error


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
    try:
        if config:
            app_config = AppConfig.load_from_file(Path(config))
            console.print(f"[green]OK[/green] Loaded config from {config}")
        else:
            app_config = get_default_config()
            console.print(
                "[green]OK[/green] Loaded default config from debate_config.json"
            )
    except ConfigurationError:
        # Error message already printed by config module
        raise SystemExit(1)

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
    "debate_format",
    type=click.Choice(["parliamentary", "oxford", "socratic", "public_forum"]),
    help="Debate format",
)
@click.option("--interactive", "-i", is_flag=True, help="Interactive mode with pauses")
@click.pass_context
def debate(
    ctx: click.Context,
    topic: str | None,
    debate_format: str | None,
    interactive: bool,
) -> None:
    """Start a debate between AI models using the engine directly."""
    config: AppConfig = ctx.obj["config"]

    # Override config with CLI options
    if topic:
        config.debate.topic = topic
    if debate_format:
        config.debate.format = debate_format

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
    """List available models from configured providers."""
    config: AppConfig = ctx.obj["config"]

    async def _list_models() -> None:
        # Import provider modules and types at the top of the function
        from typing import cast
        from dialectus.engine.models.providers.ollama_provider import OllamaProvider
        from dialectus.engine.models.providers.open_router_provider import (
            OpenRouterProvider,
        )
        from dialectus.engine.models.providers.anthropic_provider import (
            AnthropicProvider,
        )
        from dialectus.engine.models.providers.openai_provider import OpenAIProvider
        from dialectus.engine.models.base_types import BaseEnhancedModelInfo

        # Detect which providers are actually in use from the config
        providers_in_use: set[str] = set()

        # Check debate models
        for model_config in config.models.values():
            providers_in_use.add(model_config.provider)

        # Check judge models if configured
        if config.judging.judge_provider:
            providers_in_use.add(config.judging.judge_provider)

        # Check topic generation model
        providers_in_use.add(config.system.debate_topic_source)

        if not providers_in_use:
            console.print(
                "[red]No providers configured in debate_config.json. "
                "Please configure at least one model.[/red]"
            )
            return

        all_models: list[BaseEnhancedModelInfo] = []
        provider_classes = {
            "ollama": OllamaProvider,
            "openrouter": OpenRouterProvider,
            "anthropic": AnthropicProvider,
            "openai": OpenAIProvider,
        }

        # Query each provider that's in use
        for provider_name in sorted(providers_in_use):
            if provider_name not in provider_classes:
                console.print(
                    f"[yellow]Warning: Unknown provider '{provider_name}'[/yellow]"
                )
                continue

            console.print(f"Fetching models from {provider_name}...")

            try:
                provider_class = provider_classes[provider_name]
                provider = provider_class(config.system)

                # Get enhanced models from this provider directly (bypassing ModelManager)
                # to avoid the engine's blacklist filtering. The engine blacklists models
                # that aren't language-focused or optimal for debates (e.g., vision models,
                # coding models). The CLI allows users to experiment with any model they want.
                provider_models = cast(
                    list[BaseEnhancedModelInfo],
                    await provider.get_enhanced_models(),  # type: ignore[misc]
                )
                all_models.extend(provider_models)

                console.print(
                    f"[green]OK[/green] Found {len(provider_models)} models from {provider_name}"
                )

            except Exception as e:
                console.print(
                    f"[yellow]SKIP[/yellow] Could not fetch models from {provider_name}: {e}"
                )
                # Continue to next provider instead of failing completely

        if not all_models:
            console.print(
                "\n[red]No models available from any configured provider.[/red]"
            )
            console.print("\nTroubleshooting:")
            if "ollama" in providers_in_use:
                console.print(
                    "  • Ollama: Make sure Ollama is running at "
                    f"{config.system.ollama_base_url}"
                )
            if "openrouter" in providers_in_use:
                console.print("  • OpenRouter: Verify your API key is set correctly")
            return

        # Display results in a table
        table = Table(title="Available Models")
        table.add_column("Model ID", style="cyan")
        table.add_column("Provider", style="magenta")
        table.add_column("Description", style="dim")

        for model in sorted(all_models, key=lambda m: m.id):
            table.add_row(
                model.id,
                model.provider,
                (
                    model.description[:60] + "..."
                    if len(model.description) > 60
                    else model.description
                ),
            )

        console.print()
        console.print(table)

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
            topic = transcript.topic[:50]
            if len(transcript.topic) > 50:
                topic += "..."

            table.add_row(
                str(transcript.id),
                topic,
                transcript.format,
                str(transcript.message_count),
                transcript.created_at,
            )

        console.print(table)

    except Exception as e:
        display_error(console, e)
        raise SystemExit(1)


if __name__ == "__main__":
    cli()
