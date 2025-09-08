"""Command-line interface for the Dialectus Dialectus."""

import asyncio
import json
from pathlib import Path
from typing import Optional
import logging

import click
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.prompt import Confirm

from config.settings import AppConfig, get_default_config
from models.manager import ModelManager
from debate_engine.core import DebateEngine, DebatePhase
from debate_engine.transcript import TranscriptManager
from judges.factory import create_judge

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
    """Dialectus - Local-first debate orchestration."""
    setup_logging(log_level)

    # Load configuration
    if config:
        app_config = AppConfig.load_from_file(Path(config))
        console.print(f"[green]OK[/green] Loaded config from {config}")
    else:
        try:
            app_config = get_default_config()
            console.print("[green]OK[/green] Loaded default config from debate_config.json")
        except FileNotFoundError as e:
            console.print(f"[red]Error[/red] {e}")
            raise click.Abort()

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
    """List available models from Ollama."""
    config: AppConfig = ctx.obj["config"]

    async def _list_models() -> None:
        model_manager = ModelManager(config.system)

        with Progress(
            SpinnerColumn(), TextColumn("[progress.description]{task.description}")
        ) as progress:
            task = progress.add_task("Fetching available models...", total=None)
            models = await model_manager.get_available_models()
            progress.remove_task(task)

        if not models:
            console.print(
                "[red]No models available. Make sure Ollama is running.[/red]"
            )
            return

        table = Table(title="Available Ollama Models")
        table.add_column("Model Name", style="cyan")
        table.add_column("Size Category", style="magenta")

        for model in sorted(models):
            size_cat = _categorize_model_size(model)
            table.add_row(model, size_cat)

        console.print(table)

    asyncio.run(_list_models())


@cli.command()
@click.option("--transcript-dir", "-d", help="Transcript directory path")
def transcripts(transcript_dir: Optional[str]) -> None:
    """List and view saved debate transcripts."""
    config: AppConfig = click.get_current_context().obj["config"]
    
    # Use provided directory or default from config
    if transcript_dir:
        manager = TranscriptManager(transcript_dir)
    else:
        manager = TranscriptManager(config.system.transcript_dir)
    
    transcripts_list = manager.list_transcripts()
    
    if not transcripts_list:
        console.print(f"[yellow]No transcripts found in {manager.transcript_dir}[/yellow]")
        return
    
    console.print(f"\n[bold]Found {len(transcripts_list)} transcript(s):[/bold]\n")
    
    table = Table(title="Debate Transcripts")
    table.add_column("File", style="cyan")
    table.add_column("Topic", style="green") 
    table.add_column("Format", style="blue")
    table.add_column("Messages", justify="center")
    table.add_column("Date", style="dim")
    
    for transcript_path in sorted(transcripts_list, key=lambda p: p.stat().st_mtime, reverse=True):
        summary = manager.get_transcript_summary(transcript_path)
        if summary:
            topic = summary.get('topic', 'Unknown')[:40] + ('...' if len(summary.get('topic', '')) > 40 else '')
            table.add_row(
                transcript_path.name,
                topic,
                summary.get('format', 'Unknown'),
                str(summary.get('message_count', 0)),
                transcript_path.stat().st_mtime.__format__('%Y-%m-%d %H:%M')
            )
        else:
            table.add_row(transcript_path.name, "Error reading", "", "", "")
    
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
    info_panel = Panel.fit(
        f"""[bold]Topic:[/bold] {config.debate.topic}
[bold]Format:[/bold] {config.debate.format.title()}
[bold]Time per turn:[/bold] {config.debate.time_per_turn}s
[bold]Word limit:[/bold] {config.debate.word_limit}

[bold]Participants:[/bold]
{_format_participants(config)}""",
        title="Debate Setup",
        border_style="blue",
    )
    console.print(info_panel)


def _format_participants(config: AppConfig) -> str:
    """Format participant information for display."""
    participants = []
    for model_id, model_config in config.models.items():
        participants.append(
            f"• {model_id}: {model_config.name} ({model_config.personality})"
        )
    return "\n".join(participants)


async def _run_debate_async(config: AppConfig, interactive: bool) -> None:
    """Run the debate asynchronously."""
    # Initialize components
    model_manager = ModelManager(config.system)
    debate_engine = DebateEngine(config, model_manager)

    try:
        # Initialize debate
        with Progress(
            SpinnerColumn(), TextColumn("[progress.description]{task.description}")
        ) as progress:
            task = progress.add_task("Initializing debate...", total=None)
            context = await debate_engine.initialize_debate()
            progress.remove_task(task)

        console.print(f"[green]OK[/green] Debate initialized: {context.topic}")

        # Run debate rounds
        if interactive:
            await _run_interactive_debate(debate_engine, context, config)
        else:
            await _run_automatic_debate(debate_engine, context, config)

        # Judge the debate if configured
        judge = create_judge(config.judging, config.system, model_manager)
        if judge:
            with Progress(
                SpinnerColumn(), TextColumn("[progress.description]{task.description}")
            ) as progress:
                task = progress.add_task("Judging debate...", total=None)
                try:
                    decision = await debate_engine.judge_debate(judge)
                    progress.remove_task(task)
                    if decision:
                        _display_judge_decision(decision, config)
                except Exception as e:
                    progress.remove_task(task)
                    console.print(f"[red]Judge evaluation failed: {e}[/red]")
        
        # Display results
        _display_debate_results(context, config)
        
        # Show transcript location if saved
        if 'transcript_path' in context.metadata:
            console.print(f"\n[green]✓[/green] Transcript saved to: [cyan]{context.metadata['transcript_path']}[/cyan]")

    except Exception as e:
        console.print(f"[red]Error during debate: {e}[/red]")
        logger.exception("Debate execution failed")


async def _run_interactive_debate(debate_engine: DebateEngine, context, config: AppConfig) -> None:
    """Run debate with interactive pauses."""
    phases = [
        DebatePhase.OPENING,
        DebatePhase.REBUTTAL,
        DebatePhase.CROSS_EXAM,
        DebatePhase.CLOSING,
    ]

    for round_num in range(1, context.participants.__len__()):
        if round_num <= len(phases):
            phase = phases[round_num - 1]

            console.print(
                f"\n[bold blue]Round {round_num}: {phase.value.title()} Statements[/bold blue]"
            )

            if not Confirm.ask(f"Continue to {phase.value}?"):
                console.print("[yellow]Debate stopped by user[/yellow]")
                return

            round_messages = await debate_engine.conduct_round(phase)

            # Display round results
            for message in round_messages:
                _display_message(message, config)


async def _run_automatic_debate(debate_engine: DebateEngine, context, config: AppConfig) -> None:
    """Run debate automatically without pauses."""
    console.print("\n[bold]Starting debate...[/bold]")

    # Run the full debate and display messages as they come
    await debate_engine.run_full_debate()

    # Display all messages from the completed debate
    console.print("\n[bold blue]Debate Transcript[/bold blue]")
    for message in context.messages:
        _display_message(message, config)

    console.print("[green]OK[/green] Debate completed")


def _display_message(message, config: AppConfig) -> None:
    """Display a debate message with formatting."""
    style_map = {"pro": "green", "con": "red", "neutral": "blue"}

    speaker_style = style_map.get(message.position.value, "white")
    
    # Get actual model name from config, fallback to speaker_id if not found
    display_name = message.speaker_id
    if message.speaker_id in config.models:
        display_name = config.models[message.speaker_id].name

    panel = Panel(
        message.content,
        title=f"[{speaker_style}]{display_name}[/{speaker_style}] ({message.position.value.upper()})",
        border_style=speaker_style,
        subtitle=f"{message.phase.value.title()}",
    )

    console.print(panel)
    console.print()  # Add spacing


def _display_debate_results(context, config: AppConfig) -> None:
    """Display final debate results."""
    console.print("\n[bold blue]Debate Summary[/bold blue]")

    # Message count by speaker
    message_counts = {}
    total_words = 0

    for message in context.messages:
        if message.speaker_id not in message_counts:
            message_counts[message.speaker_id] = 0
        message_counts[message.speaker_id] += 1
        total_words += len(message.content.split())

    results_table = Table(title="Debate Statistics")
    results_table.add_column("Speaker", style="cyan")
    results_table.add_column("Messages", justify="center")
    results_table.add_column("Avg Words", justify="center")

    for speaker_id, count in message_counts.items():
        speaker_messages = [m for m in context.messages if m.speaker_id == speaker_id]
        avg_words = sum(len(m.content.split()) for m in speaker_messages) / len(
            speaker_messages
        )
        
        # Get actual model name from config, fallback to speaker_id if not found
        display_name = speaker_id
        if speaker_id in config.models:
            display_name = config.models[speaker_id].name
        
        results_table.add_row(display_name, str(count), f"{avg_words:.1f}")

    console.print(results_table)
    console.print(
        f"\n[dim]Total messages: {len(context.messages)} | Total words: {total_words}[/dim]"
    )


def _display_judge_decision(decision, config: AppConfig) -> None:
    """Display AI judge decision with detailed scoring."""
    from judges.base import JudgeDecision
    
    judge_decision: JudgeDecision = decision
    
    # Winner announcement with actual model name
    winner_display_name = judge_decision.winner_id
    if judge_decision.winner_id in config.models:
        winner_display_name = config.models[judge_decision.winner_id].name
    
    console.print(f"\n[bold green]🏆 WINNER: {winner_display_name}[/bold green]")
    console.print(f"[dim]Margin: {judge_decision.winner_margin:.1f}/10.0[/dim]")
    
    # Overall feedback
    if judge_decision.overall_feedback:
        console.print(f"\n[bold blue]Judge's Summary:[/bold blue]")
        console.print(f"[italic]{judge_decision.overall_feedback}[/italic]")
    
    # Detailed scoring table
    scoring_table = Table(title="Judge Scoring Breakdown")
    scoring_table.add_column("Criterion", style="cyan")
    scoring_table.add_column("Participant", style="magenta") 
    scoring_table.add_column("Score", justify="center", style="yellow")
    scoring_table.add_column("Feedback", style="dim")
    
    for score in judge_decision.criterion_scores:
        # Get actual model name for participant
        participant_display_name = score.participant_id
        if score.participant_id in config.models:
            participant_display_name = config.models[score.participant_id].name
            
        scoring_table.add_row(
            score.criterion.value.title(),
            participant_display_name,
            f"{score.score:.1f}/10",
            score.feedback[:60] + "..." if len(score.feedback) > 60 else score.feedback
        )
    
    console.print(scoring_table)
    
    # Judge's reasoning
    if judge_decision.reasoning:
        console.print(f"\n[bold blue]Judge's Reasoning:[/bold blue]")
        # Wrap long text for better display
        reasoning_lines = judge_decision.reasoning.split('\n')
        for line in reasoning_lines:
            if len(line) > 100:
                # Simple word wrap
                words = line.split()
                current_line = []
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
    
    # Show judge metadata if available
    judge_model = judge_decision.metadata.get('judge_model')
    if judge_model:
        console.print(f"\n[dim]Evaluated by: {judge_model}[/dim]")


if __name__ == "__main__":
    cli()
