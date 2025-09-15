"""Command-line interface for the Dialectus Debate System."""

import asyncio
import json
import re
from pathlib import Path
from typing import Optional, Dict, Any, List, TYPE_CHECKING
import logging

import click
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.prompt import Confirm

from config import AppConfig, get_default_config
from api_client import ApiClient, DebateSetupRequest, DebateStreamHandler

if TYPE_CHECKING:
    pass

console = Console(force_terminal=True, legacy_windows=True)
logger = logging.getLogger(__name__)


def setup_logging(level: str = "INFO") -> None:
    """Configure logging for the application."""
    logging.basicConfig(
        level=getattr(logging, level.upper()),
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        datefmt="%H:%M:%S",
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
    default="INFO",
    type=click.Choice(["DEBUG", "INFO", "WARNING", "ERROR"]),
)
@click.pass_context
def cli(ctx: click.Context, config: Optional[str], log_level: str) -> None:
    """Dialectus - AI-powered debate orchestration via API."""
    setup_logging(log_level)

    # Load configuration
    if config:
        app_config = AppConfig.load_from_file(Path(config))
        console.print(f"[green]OK[/green] Loaded config from {config}")
    else:
        app_config = get_default_config()
        console.print("[green]OK[/green] Loaded default config from debate_config.json")

    ctx.ensure_object(dict)
    ctx.obj["config"] = app_config


@cli.command()
@click.option("--topic", "-t", help="Debate topic")
@click.option(
    "--format",
    "-f",
    type=click.Choice(["parliamentary", "oxford", "socratic"]),
    help="Debate format",
)
@click.option("--rounds", "-r", type=int, help="Number of rounds")
@click.option("--interactive", "-i", is_flag=True, help="Interactive mode with pauses")
@click.pass_context
def debate(
    ctx: click.Context,
    topic: Optional[str],
    format: Optional[str],
    rounds: Optional[int],
    interactive: bool,
) -> None:
    """Start a debate between AI models."""
    config: AppConfig = ctx.obj["config"]

    # Override config with CLI options
    if topic:
        config.debate.topic = topic
    if format:
        # Type checked by click.Choice, safe to cast
        config.debate.format = format  # type: ignore[assignment]

    # Display debate setup
    _display_debate_info(config)

    if interactive and not Confirm.ask("Start the debate?"):
        console.print("[yellow]Debate cancelled[/yellow]")
        return

    # Run the debate with top-level exception handling
    try:
        asyncio.run(_run_debate_async(config, interactive))
    except Exception as e:
        _display_error(e)
        raise SystemExit(1)


@cli.command()
@click.pass_context
def list_models(ctx: click.Context) -> None:
    """List available models from the API."""
    config: AppConfig = ctx.obj["config"]

    async def _list_models() -> None:
        client = ApiClient(config.system.api_base_url)

        try:
            with Progress(
                SpinnerColumn(), TextColumn("[progress.description]{task.description}")
            ) as progress:
                task = progress.add_task("Fetching available models...", total=None)
                models = await client.get_models()
                progress.remove_task(task)

            if not models:
                console.print(
                    "[red]No models available. Make sure the engine API is running.[/red]"
                )
                return

            table = Table(title="Available Models")
            table.add_column("Model Name", style="cyan")
            table.add_column("Size Category", style="magenta")

            for model in sorted(models):
                size_cat = _categorize_model_size(model)
                table.add_row(model, size_cat)

            console.print(table)

        finally:
            await client.close()

    try:
        asyncio.run(_list_models())
    except Exception as e:
        _display_error(e)
        raise SystemExit(1)


@cli.command()
@click.option("--transcript-dir", "-d", help="Transcript directory path")
def transcripts(transcript_dir: Optional[str]) -> None:
    """List saved debate transcripts."""
    config: AppConfig = click.get_current_context().obj["config"]

    # Use provided directory or default from config
    transcript_path = (
        Path(transcript_dir) if transcript_dir else Path(config.system.transcript_dir)
    )

    if not transcript_path.exists():
        console.print(
            f"[yellow]Transcript directory not found: {transcript_path}[/yellow]"
        )
        return

    transcript_files = list(transcript_path.glob("*.json"))

    if not transcript_files:
        console.print(f"[yellow]No transcripts found in {transcript_path}[/yellow]")
        return

    console.print(f"\n[bold]Found {len(transcript_files)} transcript(s):[/bold]\n")

    table = Table(title="Debate Transcripts")
    table.add_column("File", style="cyan")
    table.add_column("Topic", style="green")
    table.add_column("Format", style="blue")
    table.add_column("Messages", justify="center")
    table.add_column("Date", style="dim")

    for file_path in sorted(
        transcript_files, key=lambda p: p.stat().st_mtime, reverse=True
    ):
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)

            topic = data.get("topic", "Unknown")[:40]
            if len(data.get("topic", "")) > 40:
                topic += "..."

            table.add_row(
                file_path.name,
                topic,
                data.get("format", "Unknown"),
                str(len(data.get("messages", []))),
                file_path.stat().st_mtime.__format__("%Y-%m-%d %H:%M"),
            )
        except (json.JSONDecodeError, KeyError):
            table.add_row(file_path.name, "Error reading", "", "", "")

    console.print(table)


def _categorize_model_size(model_name: str) -> str:
    """Categorize model by size for display."""
    model_lower = model_name.lower()
    if "3b" in model_lower or "mini" in model_lower:
        return "3B (Light)"
    elif "7b" in model_lower:
        return "7B (Medium)"
    elif "13b" in model_lower or "14b" in model_lower:
        return "13B+ (Heavy)"
    else:
        return "Unknown"


def _display_debate_info(config: AppConfig) -> None:
    """Display debate configuration information."""
    judge_info = _format_judge_info(config)

    info_panel = Panel.fit(
        f"""[bold]Topic:[/bold] {config.debate.topic}
[bold]Format:[/bold] {config.debate.format.title()}
[bold]Time per turn:[/bold] {config.debate.time_per_turn}s
[bold]Word limit:[/bold] {config.debate.word_limit}

[bold]Participants:[/bold]
{_format_participants(config)}

[bold]Judging:[/bold] {judge_info}""",
        title="Debate Setup",
        border_style="blue",
    )
    console.print(info_panel)


def _format_participants(config: AppConfig) -> str:
    """Format participant information for display."""
    participants = []
    for model_id, model_config in config.models.items():
        participants.append(
            f"- {model_id}: {model_config.name} ({model_config.personality})"
        )
    return "\n".join(participants)


def _format_judge_info(config: AppConfig) -> str:
    """Format judge information for display."""
    judge_count = len(config.judging.judge_models)

    if judge_count == 0:
        return "No judging"
    elif judge_count == 1:
        judge_info = f"Single judge: {config.judging.judge_models[0]} ({config.judging.judge_provider})"
        logger.info(
            f"Configured single judge: {config.judging.judge_models[0]} via {config.judging.judge_provider}"
        )
        return judge_info
    else:
        judge_info = f"Ensemble: {judge_count} judges ({', '.join(config.judging.judge_models)}) via {config.judging.judge_provider}"
        logger.info(
            f"Configured ensemble judges: {config.judging.judge_models} via {config.judging.judge_provider}"
        )
        return judge_info


def _format_judge_decision_info(judge_decision: Dict[str, Any]) -> str:
    """Format judge decision display info."""
    metadata = judge_decision.get("metadata", {})
    ensemble_size = metadata.get("ensemble_size", 0)

    if ensemble_size and ensemble_size > 1:
        return f"Ensemble Decision ({ensemble_size} judges)"
    else:
        judge_model = metadata.get("judge_model")
        if judge_model:
            return f"Judge: {judge_model}"
        return "AI Judge"


def _get_victory_strength(margin: float) -> str:
    """Get victory strength description based on margin."""
    if margin < 0.5:
        return "Very Close"
    elif margin < 1.0:
        return "Close Victory"
    elif margin < 2.0:
        return "Clear Victory"
    elif margin < 3.0:
        return "Strong Victory"
    else:
        return "Decisive Victory"


def _check_incomplete_scoring(criterion_scores: List[Dict[str, Any]]) -> bool:
    """Check if scoring is incomplete (missing categories for participants)."""
    if not criterion_scores:
        return True

    # Group by participant to check category counts
    participant_counts: Dict[str, int] = {}
    for score in criterion_scores:
        participant_id = score.get("participant_id")
        if participant_id:
            participant_counts[participant_id] = (
                participant_counts.get(participant_id, 0) + 1
            )

    # Check if any participant has fewer than 3 categories (logic, evidence, persuasiveness)
    expected_categories = 3
    return any(count < expected_categories for count in participant_counts.values())


def _is_structured_data(text: str) -> bool:
    """Check if text looks like structured data that shouldn't be displayed as reasoning."""
    if not text or not isinstance(text, str):
        return False

    # Check for JSON-like patterns
    stripped = text.strip()
    if stripped.startswith("{") and stripped.endswith("}"):
        try:
            json.loads(stripped)
            return True
        except json.JSONDecodeError:
            pass

    # Check for dictionary-like patterns
    dict_patterns = [
        r"^\s*\{.*:\s*.*\}\s*$",  # Basic dict pattern
        r"winner_id.*participant_id",  # Judge output pattern
    ]

    return any(re.search(pattern, text, re.DOTALL) for pattern in dict_patterns)


async def _run_debate_async(config: AppConfig, interactive: bool) -> None:
    """Run the debate asynchronously via API."""
    # Pass models config and timeout settings to ApiClient
    models_config = {
        model_id: {"provider": model_config.provider}
        for model_id, model_config in config.models.items()
    }
    client = ApiClient(
        config.system.api_base_url,
        models_config,
        config.system.http_timeout_local,
        config.system.http_timeout_remote,
    )

    try:
        # Create debate setup request
        setup = DebateSetupRequest(
            topic=config.debate.topic,
            format=config.debate.format,
            word_limit=config.debate.word_limit,
            models={
                model_id: {
                    "name": model_config.name,
                    "provider": model_config.provider,
                    "personality": model_config.personality,
                    "max_tokens": model_config.max_tokens,
                    "temperature": model_config.temperature,
                }
                for model_id, model_config in config.models.items()
            },
            judge_models=config.judging.judge_models,
            judge_provider=config.judging.judge_provider,
        )

        # Create debate
        with Progress(
            SpinnerColumn(), TextColumn("[progress.description]{task.description}")
        ) as progress:
            task = progress.add_task("Creating debate...", total=None)
            debate_response = await client.create_debate(setup)
            progress.remove_task(task)

        console.print(f"[green]OK[/green] Debate created: {debate_response.id}")

        # Connect to WebSocket BEFORE starting the debate to catch all messages
        console.print(f"[green]OK[/green] Connecting to debate stream...")

        # Set up the stream handler first
        def on_message_received(message: Dict[str, Any]) -> None:
            """Display message immediately when received."""
            _display_message(message, config)

        def on_judge_decision(decision: Dict[str, Any]) -> None:
            """Display judge decision immediately when received."""
            logger.info(
                f"Judge callback invoked - displaying results. Decision keys: {list(decision.keys()) if decision else 'None'}"
            )
            console.print("\n" + "=" * 50)
            console.print("[bold yellow]🏛️ JUDGE DECISION RECEIVED[/bold yellow]")
            console.print("=" * 50)
            _display_judge_decision(decision, config)

        stream_handler = DebateStreamHandler(
            config.system.api_base_url,
            debate_response.id,
            config.system.websocket_timeout,
            message_callback=on_message_received,
            judge_callback=on_judge_decision,
        )

        # Start WebSocket connection in background
        import asyncio

        websocket_task = asyncio.create_task(stream_handler.connect_and_stream())

        # Give WebSocket time to connect
        await asyncio.sleep(1.0)

        # Now start the debate
        with Progress(
            SpinnerColumn(), TextColumn("[progress.description]{task.description}")
        ) as progress:
            task = progress.add_task("Starting debate...", total=None)
            await client.start_debate(debate_response.id)
            progress.remove_task(task)

        console.print(f"[green]OK[/green] Debate started")
        console.print("\n[bold blue]Live Debate Feed[/bold blue]")

        # Wait for WebSocket to complete
        try:
            await websocket_task
        except Exception as e:
            logger.error(f"WebSocket stream error: {e}")


    except Exception as e:
        console.print(f"[red]Error during debate: {e}[/red]")
        logger.exception("Debate execution failed")

    finally:
        await client.close()




def _display_message(message: Dict[str, Any], config: AppConfig) -> None:
    """Display a debate message with formatting."""
    style_map = {"pro": "green", "con": "red", "neutral": "blue"}

    position = message.get("position", "neutral")
    speaker_style = style_map.get(position, "white")

    # Get actual model name from config, fallback to speaker_id if not found
    speaker_id = message.get("speaker_id", "unknown")
    display_name = speaker_id
    if speaker_id in config.models:
        display_name = config.models[speaker_id].name

    phase = message.get("phase", "unknown")
    content = message.get("content", "")

    panel = Panel(
        content,
        title=f"[{speaker_style}]{display_name}[/{speaker_style}] ({position.upper()})",
        border_style=speaker_style,
        subtitle=f"{phase.title()}",
    )

    console.print(panel)
    console.print()  # Add spacing


def _display_judge_decision(decision: Dict[str, Any], config: AppConfig) -> None:
    """Display AI judge decision with detailed scoring."""
    if not decision:
        console.print("[red]No judge decision data received[/red]")
        return

    # Get side label mapping from decision metadata if available
    side_label_mapping = {}
    display_labels = decision.get("metadata", {}).get("display_labels", {})
    if display_labels:
        # Reverse the display_labels mapping to get side_label -> participant_id
        for participant_id, display_label in display_labels.items():
            parts = display_label.split(" - ")
            if len(parts) == 2:
                side_label = parts[1]  # e.g., "Proposition", "Opposition"
                side_label_mapping[side_label] = participant_id

    def get_display_name(participant_identifier: str) -> str:
        """Get display name for participant, handling both old and new formats."""
        # First check if it's a side label that needs mapping
        if participant_identifier in side_label_mapping:
            actual_participant_id = side_label_mapping[participant_identifier]
            if actual_participant_id in config.models:
                model_name = config.models[actual_participant_id].name
                return f"{model_name} ({participant_identifier})"
            return f"{actual_participant_id} ({participant_identifier})"

        # Check if it's directly a participant ID
        if participant_identifier in config.models:
            return config.models[participant_identifier].name

        # Fallback to the identifier itself
        return participant_identifier

    # Winner announcement with proper display name
    winner_id = decision.get("winner_id", "unknown")
    winner_display_name = get_display_name(winner_id)

    winner_margin = decision.get("winner_margin", 0.0)

    console.print(f"\n[bold green]🏆 WINNER: {winner_display_name}[/bold green]")

    # Show margin (now calculated by engine)
    if winner_margin > 0:
        victory_strength = _get_victory_strength(winner_margin)
        console.print(
            f"[dim]Victory Margin: {winner_margin:.1f} points ({victory_strength})[/dim]"
        )

    # Show judge type info
    judge_info = _format_judge_decision_info(decision)
    console.print(f"[dim]{judge_info}[/dim]")

    # Overall feedback
    overall_feedback = decision.get("overall_feedback")
    if overall_feedback:
        console.print(f"\n[bold blue]Judge's Summary:[/bold blue]")
        console.print(f"[italic]{overall_feedback}[/italic]")

    # Extract criterion scores from the decision
    criterion_scores = decision.get("criterion_scores", [])

    # Detailed scoring table
    if criterion_scores:
        console.print(f"\n[bold blue]Detailed Scoring:[/bold blue]")

        # Check for incomplete scoring
        has_incomplete_scoring = _check_incomplete_scoring(criterion_scores)
        if has_incomplete_scoring:
            console.print(
                "[yellow]⚠️ Warning: Some scoring categories may be incomplete[/yellow]"
            )

        scoring_table = Table(title="Judge Scoring Breakdown")
        scoring_table.add_column("Participant", style="magenta", width=25)
        scoring_table.add_column("Criterion", style="cyan", width=15)
        scoring_table.add_column("Score", justify="center", style="yellow", width=8)
        scoring_table.add_column("Feedback", style="dim", width=50)

        for score in criterion_scores:
            # Get display name for participant (handles side labels)
            participant_id = score.get("participant_id", "unknown")
            participant_display_name = get_display_name(participant_id)

            criterion = score.get("criterion", "unknown")
            if isinstance(criterion, dict) and "value" in criterion:
                criterion = criterion["value"]

            score_value = score.get("score", 0.0)
            feedback = score.get("feedback", "")

            scoring_table.add_row(
                participant_display_name,
                str(criterion).title(),
                f"{score_value:.1f}/10" if score_value is not None else "N/A",
                feedback[:47] + "..." if len(feedback) > 50 else feedback,
            )

        console.print(scoring_table)

    # Judge's reasoning (skip if it looks like structured data)
    reasoning = decision.get("reasoning")
    if reasoning and not _is_structured_data(reasoning):
        console.print(f"\n[bold blue]Judge's Reasoning:[/bold blue]")
        # Simple word wrap for long lines
        reasoning_lines = reasoning.split("\n")
        for line in reasoning_lines:
            if len(line) > 100:
                words = line.split()
                current_line: List[str] = []
                for word in words:
                    if len(" ".join(current_line + [word])) <= 100:
                        current_line.append(word)
                    else:
                        if current_line:
                            console.print(" ".join(current_line))
                            current_line = [word]
                        else:
                            console.print(word)
                if current_line:
                    console.print(" ".join(current_line))
            else:
                console.print(line)

    # Show individual judge decisions for ensemble judging
    metadata = decision.get("metadata", {})
    individual_decisions = metadata.get("individual_decisions", [])
    ensemble_size = metadata.get("ensemble_size", 0)

    if ensemble_size > 1 and individual_decisions:
        console.print(f"\n[bold blue]Individual Judge Decisions:[/bold blue]")
        for i, individual_decision in enumerate(individual_decisions, 1):
            _display_individual_judge_decision(individual_decision, i, get_display_name, config)

    # Debug information
    if metadata.get("judge_model"):
        console.print(f"\n[dim]Judge Model: {metadata['judge_model']}[/dim]")


def _display_error(error: Exception) -> None:
    """Display a formatted error message using Rich."""
    import traceback

    error_panel = Panel.fit(
        f"""[bold red]Exception Type:[/bold red] {type(error).__name__}

[bold red]Message:[/bold red] {str(error)}

[bold red]Call Stack:[/bold red]
{traceback.format_exc()}""",
        title="[red]⚠️  Debate Failed[/red]",
        border_style="red",
        padding=(1, 2),
    )
    console.print("\n")
    console.print(error_panel)
    console.print()


def _display_individual_judge_decision(
    decision: Dict[str, Any], judge_number: int, get_display_name_func, config: AppConfig
) -> None:
    """Display an individual judge's decision in ensemble judging."""
    judge_model = decision.get("metadata", {}).get("judge_model", f"Judge {judge_number}")
    winner_id = decision.get("winner_id", "unknown")
    winner_display_name = get_display_name_func(winner_id)
    winner_margin = decision.get("winner_margin", 0.0)

    console.print(f"\n[bold cyan]🤖 Judge {judge_number} ({judge_model})[/bold cyan]")
    console.print(f"[green]Winner: {winner_display_name}[/green]")

    if winner_margin > 0:
        victory_strength = _get_victory_strength(winner_margin)
        console.print(f"[dim]Margin: {winner_margin:.1f} points ({victory_strength})[/dim]")

    # Individual judge's overall feedback
    overall_feedback = decision.get("overall_feedback")
    if overall_feedback:
        console.print(f"[italic]{overall_feedback}[/italic]")

    # Individual judge's detailed scores
    criterion_scores = decision.get("criterion_scores", [])
    if criterion_scores:
        # Create a compact table for individual judge scores
        individual_table = Table(title=f"Judge {judge_number} Detailed Scoring", width=80)
        individual_table.add_column("Participant", style="magenta", width=20)
        individual_table.add_column("Criterion", style="cyan", width=12)
        individual_table.add_column("Score", justify="center", style="yellow", width=6)
        individual_table.add_column("Feedback", style="dim", width=35)

        for score in criterion_scores:
            participant_id = score.get("participant_id", "unknown")
            participant_display_name = get_display_name_func(participant_id)

            criterion = score.get("criterion", "unknown")
            if isinstance(criterion, str):
                criterion_display = criterion.title()
            else:
                criterion_display = str(criterion)

            score_value = score.get("score", 0.0)
            feedback = score.get("feedback", "")

            individual_table.add_row(
                participant_display_name,
                criterion_display,
                f"{score_value:.1f}/10" if score_value is not None else "N/A",
                feedback[:32] + "..." if len(feedback) > 35 else feedback,
            )

        console.print(individual_table)

    # Individual judge's reasoning (if not structured data)
    reasoning = decision.get("reasoning")
    if reasoning and not _is_structured_data(reasoning):
        console.print(f"[dim]Reasoning: {reasoning[:150]}{'...' if len(reasoning) > 150 else ''}[/dim]")


if __name__ == "__main__":
    cli()
