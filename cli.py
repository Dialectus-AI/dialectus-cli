"""Command-line interface for the Dialectus Debate System."""

import asyncio
import json
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
    "--config", "-c", type=click.Path(exists=True), help="Configuration file path (default: debate_config.json)"
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

    # Run the debate
    asyncio.run(_run_debate_async(config, interactive))



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

    asyncio.run(_list_models())


@cli.command()
@click.option("--transcript-dir", "-d", help="Transcript directory path")
def transcripts(transcript_dir: Optional[str]) -> None:
    """List saved debate transcripts."""
    config: AppConfig = click.get_current_context().obj["config"]

    # Use provided directory or default from config
    transcript_path = Path(transcript_dir) if transcript_dir else Path(config.system.transcript_dir)

    if not transcript_path.exists():
        console.print(f"[yellow]Transcript directory not found: {transcript_path}[/yellow]")
        return

    transcript_files = list(transcript_path.glob('*.json'))

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

    for file_path in sorted(transcript_files, key=lambda p: p.stat().st_mtime, reverse=True):
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)

            topic = data.get('topic', 'Unknown')[:40]
            if len(data.get('topic', '')) > 40:
                topic += '...'

            table.add_row(
                file_path.name,
                topic,
                data.get('format', 'Unknown'),
                str(len(data.get('messages', []))),
                file_path.stat().st_mtime.__format__('%Y-%m-%d %H:%M')
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
        logger.info(f"Configured single judge: {config.judging.judge_models[0]} via {config.judging.judge_provider}")
        return judge_info
    else:
        judge_info = f"Ensemble: {judge_count} judges ({', '.join(config.judging.judge_models)}) via {config.judging.judge_provider}"
        logger.info(f"Configured ensemble judges: {config.judging.judge_models} via {config.judging.judge_provider}")
        return judge_info


def _format_judge_decision_info(judge_decision: Dict[str, Any]) -> str:
    """Format judge decision display info."""
    metadata = judge_decision.get('metadata', {})
    ensemble_size = metadata.get('ensemble_size', 0)

    if ensemble_size and ensemble_size > 1:
        return f"Ensemble Decision ({ensemble_size} judges)"
    else:
        judge_model = metadata.get('judge_model')
        if judge_model:
            return f"Judge: {judge_model}"
        return "AI Judge"


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
        config.system.http_timeout_remote
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
                    "temperature": model_config.temperature
                }
                for model_id, model_config in config.models.items()
            },
            judge_models=config.judging.judge_models,
            judge_provider=config.judging.judge_provider
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
            logger.info("Judge callback invoked - displaying results")
            console.print("\n" + "="*50)
            _display_judge_decision(decision, config)

        stream_handler = DebateStreamHandler(
            config.system.api_base_url,
            debate_response.id,
            config.system.websocket_timeout,
            message_callback=on_message_received,
            judge_callback=on_judge_decision
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

        # Display final summary
        await _display_final_summary(stream_handler)

    except Exception as e:
        console.print(f"[red]Error during debate: {e}[/red]")
        logger.exception("Debate execution failed")

    finally:
        await client.close()


async def _display_final_summary(stream_handler: DebateStreamHandler) -> None:
    """Display final debate summary statistics."""
    total_messages = len(stream_handler.messages)
    if total_messages > 0:
        console.print(f"\n[bold blue]Debate Summary[/bold blue]")

        # Calculate statistics
        message_counts: Dict[str, int] = {}
        total_words = 0

        for message in stream_handler.messages:
            speaker_id = message.get("speaker_id", "unknown")
            if speaker_id not in message_counts:
                message_counts[speaker_id] = 0
            message_counts[speaker_id] += 1
            content = message.get("content", "")
            total_words += len(content.split())

        from rich.table import Table
        results_table = Table(title="Final Statistics")
        results_table.add_column("Speaker", style="cyan")
        results_table.add_column("Messages", justify="center")
        results_table.add_column("Avg Words", justify="center")

        for speaker_id, count in message_counts.items():
            speaker_messages = [m for m in stream_handler.messages if m.get("speaker_id") == speaker_id]
            if speaker_messages:
                avg_words = sum(len(m.get("content", "").split()) for m in speaker_messages) / len(speaker_messages)
            else:
                avg_words = 0.0
            results_table.add_row(speaker_id, str(count), f"{avg_words:.1f}")

        console.print(results_table)
        console.print(f"\n[dim]Total: {total_messages} messages, {total_words} words[/dim]")


async def _run_interactive_stream(client: ApiClient, debate_id: str, config: AppConfig) -> None:
    """Stream debate with interactive pauses between phases."""
    console.print("\n[bold]Interactive streaming not yet implemented - running automatically...[/bold]")
    # This is now handled inline in _run_debate_async



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
    # Winner announcement with actual model name
    winner_id = decision.get("winner_id", "unknown")
    winner_display_name = winner_id
    if winner_id in config.models:
        winner_display_name = config.models[winner_id].name

    winner_margin = decision.get("winner_margin", 0.0)

    console.print(f"\n[bold green]🏆 WINNER: {winner_display_name}[/bold green]")
    console.print(f"[dim]Margin: {winner_margin:.1f}/10.0[/dim]")

    # Show judge type info
    judge_info = _format_judge_decision_info(decision)
    console.print(f"[dim]{judge_info}[/dim]")

    # Overall feedback
    overall_feedback = decision.get("overall_feedback")
    if overall_feedback:
        console.print(f"\n[bold blue]Judge's Summary:[/bold blue]")
        console.print(f"[italic]{overall_feedback}[/italic]")

    # Detailed scoring table
    criterion_scores = decision.get("criterion_scores", [])
    if criterion_scores:
        scoring_table = Table(title="Judge Scoring Breakdown")
        scoring_table.add_column("Criterion", style="cyan")
        scoring_table.add_column("Participant", style="magenta")
        scoring_table.add_column("Score", justify="center", style="yellow")
        scoring_table.add_column("Feedback", style="dim")

        for score in criterion_scores:
            # Get actual model name for participant
            participant_id = score.get("participant_id", "unknown")
            participant_display_name = participant_id
            if participant_id in config.models:
                participant_display_name = config.models[participant_id].name

            criterion = score.get("criterion", "unknown")
            score_value = score.get("score", 0.0)
            feedback = score.get("feedback", "")

            scoring_table.add_row(
                criterion.title(),
                participant_display_name,
                f"{score_value:.1f}/10",
                feedback[:60] + "..." if len(feedback) > 60 else feedback
            )

        console.print(scoring_table)

    # Judge's reasoning
    reasoning = decision.get("reasoning")
    if reasoning:
        console.print(f"\n[bold blue]Judge's Reasoning:[/bold blue]")
        # Simple word wrap for long lines
        reasoning_lines = reasoning.split('\n')
        for line in reasoning_lines:
            if len(line) > 100:
                words = line.split()
                current_line: List[str] = []
                for word in words:
                    if len(' '.join(current_line + [word])) <= 100:
                        current_line.append(word)
                    else:
                        if current_line:
                            console.print(' '.join(current_line))
                            current_line = [word]
                        else:
                            console.print(word)
                if current_line:
                    console.print(' '.join(current_line))
            else:
                console.print(line)


if __name__ == "__main__":
    cli()
