"""Rich console presentation helpers for Dialectus CLI output."""

from __future__ import annotations

import json
import logging
import re
from typing import Callable

from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from dialectus.cli.config import AppConfig
from dialectus.cli.db_types import (
    CriterionScoreRow,
    DisplayJudgeDecision,
    JudgeDecisionWithScores,
)
from dialectus.engine.models.providers import ProviderRateLimitError

from textwrap import dedent

logger = logging.getLogger(__name__)

# Display configuration constants for UI layout
MAX_REASONING_PREVIEW_LENGTH = (
    150  # Characters to show in individual judge reasoning preview
)
FEEDBACK_COLUMN_WIDTH = 50  # Width of feedback column in scoring tables
FEEDBACK_TRUNCATE_LENGTH = 47  # Truncate feedback at this length (with "..." = 50)
LINE_WRAP_LENGTH = 100  # Maximum line length before wrapping in reasoning display


def display_debate_info(console: Console, config: AppConfig) -> None:
    """Render the core debate configuration details."""
    judge_info = _format_judge_info(config)

    info_panel = Panel.fit(
        dedent(
            f"""[bold]Topic:[/bold] {config.debate.topic}
            [bold]Format:[/bold] {config.debate.format.title()}
            [bold]Time per turn:[/bold] {config.debate.time_per_turn}s
            [bold]Word limit:[/bold] {config.debate.word_limit}

            [bold]Participants:[/bold]
            {_format_participants(config)}

            [bold]Judging:[/bold] {judge_info}"""
        ),
        title="Debate Setup",
        border_style="blue",
    )
    console.print(info_panel)


def display_judge_decision(
    console: Console,
    config: AppConfig,
    decision: DisplayJudgeDecision,
) -> None:
    """Render a judge decision, handling both single and ensemble cases.

    Args:
        console: Rich console for output
        config: App configuration with model details
        decision: Structured judge decision (Pydantic model)
    """
    # side_label_mapping = _build_side_label_mapping(decision)

    def get_display_name(participant_identifier: str) -> str:
        """Resolve display name for participant ID."""
        # TODO: Re-implement side label mapping if needed for display labels
        if participant_identifier in config.models:
            return config.models[participant_identifier].name
        return participant_identifier

    winner_id = decision.winner_id
    winner_display_name = get_display_name(winner_id)
    winner_margin = decision.winner_margin

    console.print(f"\n[bold green]🏆 WINNER: {winner_display_name}[/bold green]")

    if winner_margin > 0:
        victory_strength = _get_victory_strength(winner_margin)
        console.print(
            f"[dim]Victory Margin: {winner_margin:.1f} points"
            f" ({victory_strength})[/dim]"
        )

    judge_info = _format_judge_decision_info(decision)
    console.print(f"[dim]{judge_info}[/dim]")

    if decision.overall_feedback:
        console.print("\n[bold blue]Judge's Summary:[/bold blue]")
        console.print(f"[italic]{decision.overall_feedback}[/italic]")

    _display_detailed_scoring(console, decision.criterion_scores, get_display_name)
    _display_reasoning(console, decision.reasoning)

    metadata = decision.metadata
    individual_decisions = metadata.individual_decisions
    ensemble_size = metadata.ensemble_size

    if ensemble_size > 1 and individual_decisions:
        console.print("\n[bold blue]Individual Judge Decisions:[/bold blue]")
        for index, individual_decision in enumerate(individual_decisions, start=1):
            display_individual_judge_decision(
                console, individual_decision, index, get_display_name
            )

    if metadata.judge_model:
        console.print(f"\n[dim]Judge Model: {metadata.judge_model}[/dim]")


def display_error(console: Console, error: Exception) -> None:
    """Render a Rich panel for exceptions, with provider-specific guidance."""
    import traceback

    if isinstance(error, ProviderRateLimitError):
        provider = error.provider.capitalize()
        lines: list[str] = [
            (
                f"[bold]{provider}[/bold] rejected the request with HTTP"
                f" {error.status_code} (rate limited)."
            ),
        ]

        if error.model:
            lines.append(f"[bold]Model:[/bold] {error.model}")

        if error.detail:
            lines.append("")
            lines.append(error.detail)

        if error.provider == "openrouter":
            lines.extend([
                "",
                "Check your OpenRouter balance or select a different model.",
                (
                    "Models ending with ':free' require sufficient balance despite"
                    " being marked free; try a paid route or top up your credits."
                ),
            ])

        panel = Panel.fit(
            "\n".join(lines),
            title="[yellow]🚦 Rate Limit[/yellow]",
            border_style="yellow",
            padding=(1, 2),
        )
        console.print("\n")
        console.print(panel)
        console.print()
        return

    error_panel = Panel.fit(
        dedent(f"""[bold red]Exception Type:[/bold red] {type(error).__name__}
            [bold red]Message:[/bold red] {str(error)}
            [bold red]Call Stack:[/bold red]
            {traceback.format_exc()}"""),
        title="[red]⚠️  Debate Failed[/red]",
        border_style="red",
        padding=(1, 2),
    )

    console.print("\n")
    console.print(error_panel)
    console.print()


def display_individual_judge_decision(
    console: Console,
    decision: JudgeDecisionWithScores,
    judge_number: int,
    get_display_name_func: Callable[[str], str],
) -> None:
    """Render an individual judge decision for ensemble judging using Pydantic model."""
    judge_model = decision.metadata.get("judge_model", f"Judge {judge_number}")
    winner_id = decision.winner_id
    winner_display_name = get_display_name_func(winner_id)
    winner_margin = decision.winner_margin

    console.print(f"\n[bold cyan]🤖 Judge {judge_number} ({judge_model})[/bold cyan]")
    console.print(f"[green]Winner: {winner_display_name}[/green]")

    if winner_margin > 0:
        victory_strength = _get_victory_strength(winner_margin)
        console.print(
            f"[dim]Margin: {winner_margin:.1f} points ({victory_strength})[/dim]"
        )

    if decision.overall_feedback:
        console.print(f"[italic]{decision.overall_feedback}[/italic]")

    _display_individual_scores(
        console,
        decision.criterion_scores,
        get_display_name_func,
        f"Judge {judge_number} Detailed Scoring",
    )
    reasoning = decision.reasoning
    if reasoning and not _is_structured_data(reasoning):
        console.print(
            "[dim]Reasoning:"
            f" {reasoning[:MAX_REASONING_PREVIEW_LENGTH]}{'...' if len(reasoning) > MAX_REASONING_PREVIEW_LENGTH else ''}[/dim]"
        )


def _format_participants(config: AppConfig) -> str:
    participants: list[str] = []
    for model_id, model_config in config.models.items():
        participants.append(
            f"- {model_id}: {model_config.name} ({model_config.personality})"
        )
    return "\n".join(participants)


def _format_judge_info(config: AppConfig) -> str:
    judge_count = len(config.judging.judge_models)

    if judge_count == 0:
        return "No judging"
    if judge_count == 1:
        judge_info = (
            f"Single judge: {config.judging.judge_models[0]} "
            f"({config.judging.judge_provider})"
        )
        logger.info(
            "Configured single judge: %s via %s",
            config.judging.judge_models[0],
            config.judging.judge_provider,
        )
        return judge_info

    judge_info = (
        f"Ensemble: {judge_count} judges ({', '.join(config.judging.judge_models)}) via"
        f" {config.judging.judge_provider}"
    )
    logger.info(
        "Configured ensemble judges: %s via %s",
        config.judging.judge_models,
        config.judging.judge_provider,
    )
    return judge_info


def _format_judge_decision_info(judge_decision: DisplayJudgeDecision) -> str:
    """Format judge decision info string from Pydantic model."""
    metadata = judge_decision.metadata
    ensemble_size = metadata.ensemble_size

    if ensemble_size and ensemble_size > 1:
        return f"Ensemble Decision ({ensemble_size} judges)"

    judge_model = metadata.judge_model
    if judge_model:
        return f"Judge: {judge_model}"
    return "AI Judge"


def _get_victory_strength(margin: float) -> str:
    if margin < 0.5:
        return "Very Close"
    if margin < 1.0:
        return "Close Victory"
    if margin < 2.0:
        return "Clear Victory"
    if margin < 3.0:
        return "Strong Victory"
    return "Decisive Victory"


def _check_incomplete_scoring(criterion_scores: list[CriterionScoreRow]) -> bool:
    """Check if scoring is incomplete (missing categories for any participant)."""
    if not criterion_scores:
        return True

    participant_counts: dict[str, int] = {}
    for score in criterion_scores:
        participant_id = score.participant_id
        participant_counts[participant_id] = (
            participant_counts.get(participant_id, 0) + 1
        )

    expected_categories = 3
    return any(count < expected_categories for count in participant_counts.values())


def _is_structured_data(text: str) -> bool:
    if not text:
        return False

    stripped = text.strip()
    if stripped.startswith("{") and stripped.endswith("}"):
        try:
            json.loads(stripped)
            return True
        except json.JSONDecodeError:
            pass

    dict_patterns = [
        r"^\s*\{.*:\s*.*\}\s*$",
        r"winner_id.*participant_id",
    ]

    return any(re.search(pattern, text, re.DOTALL) for pattern in dict_patterns)


def _display_detailed_scoring(
    console: Console,
    criterion_scores: list[CriterionScoreRow],
    get_display_name: Callable[[str], str],
) -> None:
    """Display detailed scoring table using Pydantic models."""
    if not criterion_scores:
        return

    console.print("\n[bold blue]Detailed Scoring:[/bold blue]")

    if _check_incomplete_scoring(criterion_scores):
        console.print(
            "[yellow]⚠️ Warning: Some scoring categories may be incomplete[/yellow]"
        )

    scoring_table = Table(title="Judge Scoring Breakdown")
    scoring_table.add_column("Participant", style="magenta", width=25)
    scoring_table.add_column("Criterion", style="cyan", width=15)
    scoring_table.add_column("Score", justify="center", style="yellow", width=8)
    scoring_table.add_column("Feedback", style="dim", width=FEEDBACK_COLUMN_WIDTH)

    for score in criterion_scores:
        participant_id = score.participant_id
        participant_display_name = get_display_name(participant_id)
        criterion = score.criterion
        score_value = score.score
        feedback = score.feedback or ""

        scoring_table.add_row(
            participant_display_name,
            criterion.title(),
            f"{score_value:.1f}/10",
            feedback[:FEEDBACK_TRUNCATE_LENGTH] + "..."
            if len(feedback) > FEEDBACK_COLUMN_WIDTH
            else feedback,
        )

    console.print(scoring_table)


def _display_reasoning(console: Console, reasoning: str | None) -> None:
    if not reasoning or _is_structured_data(reasoning):
        return

    console.print("\n[bold blue]Judge's Reasoning:[/bold blue]")
    reasoning_lines = reasoning.split("\n")
    for line in reasoning_lines:
        if len(line) > LINE_WRAP_LENGTH:
            words = line.split()
            current_line: list[str] = []
            for word in words:
                candidate = " ".join(current_line + [word])
                if len(candidate) <= LINE_WRAP_LENGTH:
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


def _display_individual_scores(
    console: Console,
    criterion_scores: list[CriterionScoreRow],
    get_display_name_func: Callable[[str], str],
    title: str,
) -> None:
    """Display individual scores table using Pydantic models."""
    if not criterion_scores:
        return

    individual_table = Table(title=title, width=80)
    individual_table.add_column("Participant", style="magenta", width=20)
    individual_table.add_column("Criterion", style="cyan", width=12)
    individual_table.add_column("Score", justify="center", style="yellow", width=6)
    individual_table.add_column("Feedback", style="dim", width=35)

    for score in criterion_scores:
        participant_id = score.participant_id
        participant_display_name = get_display_name_func(participant_id)
        criterion = score.criterion
        score_value = score.score
        feedback = score.feedback or ""

        individual_table.add_row(
            participant_display_name,
            criterion.title(),
            f"{score_value:.1f}/10",
            feedback[:32] + "..." if len(feedback) > 35 else feedback,
        )

    console.print(individual_table)


__all__ = [
    "display_debate_info",
    "display_error",
    "display_individual_judge_decision",
    "display_judge_decision",
    "_format_participants",
    "_format_judge_info",
    "_get_victory_strength",
    "_is_structured_data",
    "_check_incomplete_scoring",
]
