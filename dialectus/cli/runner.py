"""Debate runner - direct engine integration for CLI (mirrors API's debate_manager)."""

from __future__ import annotations

import logging
from typing import Any, cast
from datetime import datetime

from rich.console import Console
from rich.panel import Panel

from dialectus.cli.config import AppConfig
from dialectus.engine.models.manager import ModelManager
from dialectus.engine.models.providers import ProviderRateLimitError
from dialectus.engine.debate_engine import DebateContext, DebateEngine
from dialectus.engine.formats import format_registry
from dialectus.engine.judges.factory import create_judges
from dialectus.engine.judges.base import BaseJudge, JudgeDecision
from dialectus.cli.database import DatabaseManager

from dialectus.cli.presentation import display_judge_decision

logger = logging.getLogger(__name__)

__all__ = [
    "DebateRunner",
    "_safe_isoformat",
]


def _safe_isoformat(value: Any) -> str | None:
    """Return an ISO formatted string for datetime-like values."""
    if value is None:
        return None
    if isinstance(value, str):
        return value
    iso_callable = getattr(value, "isoformat", None)
    if callable(iso_callable):
        iso_value = iso_callable()
        return iso_value if isinstance(iso_value, str) else str(iso_value)
    return str(value)


class DebateRunner:
    """Runs debates using DebateEngine and displays output to Rich console."""

    def __init__(self, config: AppConfig, console: Console):
        self.config = config
        self.console = console

        # Validate format exists (fail fast)
        if self.config.debate.format not in format_registry.list_formats():
            available = ", ".join(format_registry.list_formats())
            raise ValueError(
                f"Invalid debate format: {self.config.debate.format}. "
                f"Available formats: {available}"
            )

        self.model_manager = ModelManager(config.system)
        self.engine = DebateEngine(config, self.model_manager)
        self.db = DatabaseManager()

    async def run_debate(self) -> None:
        """Run a full debate with judging and save to database."""
        try:
            # Initialize debate
            self.console.print("[cyan]Initializing debate...[/cyan]")
            context = await self.engine.initialize_debate()

            # Phase callback
            async def phase_callback(event_type: str, data: dict[str, Any]):
                if event_type == "phase_started":
                    phase_name = data.get("phase", "unknown").upper()
                    self.console.print(
                        f"\n[bold magenta]═══ {phase_name} ═══[/bold magenta]\n"
                    )

            # Message callback
            async def message_callback(event_type: str, data: dict[str, Any]):
                if event_type == "message_complete":
                    self.display_message(data)

            # Run debate with callbacks
            self.console.print("\n[bold blue]═══ DEBATE START ═══[/bold blue]\n")
            context = await self.engine.run_full_debate(
                phase_callback=phase_callback,
                message_callback=message_callback,
            )

            # Judging
            judge_models = self.config.judging.judge_models
            judge_provider = self.config.judging.judge_provider
            criteria = self.config.judging.criteria

            judges: list[BaseJudge] = []
            if judge_models:
                if judge_provider is None:
                    raise ValueError(
                        "Judge provider must be specified when judge models are"
                        " configured."
                    )

                judges = cast(
                    list[BaseJudge],
                    create_judges(
                        judge_models,
                        judge_provider,
                        self.config.system,
                        self.model_manager,
                        criteria,
                    ),
                )

            judge_result = None
            judges_configured = bool(judge_models)
            judging_succeeded = True

            if judges:
                try:
                    self.console.print(
                        "\n[bold yellow]═══ JUDGING PHASE ═══[/bold yellow]\n"
                    )
                    self.console.print("[cyan]Evaluating debate...[/cyan]")

                    judge_result = await self.engine.judge_debate_with_judges(judges)

                except Exception as e:
                    judging_succeeded = False
                    logger.error(f"Judge evaluation failed: {e}")
                    self.console.print(
                        f"\n[red]Judge evaluation failed: {e}[/red]", style="bold"
                    )

            # Save transcript
            try:
                if judges_configured and not judging_succeeded:
                    error_msg = (
                        "Debate configured with judges but judging failed - transcript"
                        " NOT saved"
                    )
                    logger.error(error_msg)
                    raise RuntimeError(error_msg)

                db_id = await self.save_transcript(context, judge_result)
                context.metadata["transcript_id"] = db_id

                # Display judge results if judging succeeded
                if judges_configured and judging_succeeded:
                    self.display_judge_results(db_id, judge_result)

                self.console.print(
                    f"\n[green]✓ Debate completed and saved (ID: {db_id})[/green]\n"
                )

            except Exception as e:
                logger.error(f"Failed to save transcript: {e}")
                self.console.print(
                    f"\n[red]Failed to save transcript: {e}[/red]", style="bold"
                )
                raise

        except ProviderRateLimitError as e:
            logger.error("Debate failed due to provider rate limit: %s", e)
            raise
        except Exception as e:
            logger.error(f"Debate failed: {e}")
            self.console.print(f"\n[red]Debate failed: {e}[/red]", style="bold")
            raise

    def display_message(self, message: dict[str, Any]) -> None:
        """Display a debate message with Rich formatting."""
        style_map = {"pro": "green", "con": "red", "neutral": "blue"}

        position = message.get("position", "neutral")
        speaker_style = style_map.get(position, "white")

        # Get model name from config
        speaker_id = message.get("speaker_id", "unknown")
        display_name = speaker_id
        if speaker_id in self.config.models:
            display_name = self.config.models[speaker_id].name

        phase = message.get("phase", "unknown")
        content = message.get("content", "")

        panel = Panel(
            content,
            title=(
                f"[{speaker_style}]{display_name}[/{speaker_style}]"
                f" ({position.upper()})"
            ),
            border_style=speaker_style,
            subtitle=f"{phase.title()}",
        )

        self.console.print(panel)
        self.console.print()

    async def save_transcript(
        self,
        context: DebateContext,
        judge_result: JudgeDecision | dict[str, Any] | None,
    ) -> int:
        """Save debate transcript to database. Returns debate ID."""
        total_debate_time_ms = context.metadata.get("total_debate_time_ms", 0)

        transcript_data = {
            "metadata": {
                "topic": context.topic,
                "format": context.metadata.get("format", "unknown"),
                "participants": {
                    pid: {
                        "name": p.name,
                        "personality": p.personality,
                    }
                    for pid, p in context.participants.items()
                },
                "final_phase": context.current_phase.value,
                "total_rounds": context.current_round,
                "saved_at": datetime.now().isoformat(),
                "message_count": len(context.messages),
                "word_count": sum(len(m.content.split()) for m in context.messages),
                "total_debate_time_ms": total_debate_time_ms,
            },
            "messages": [
                {
                    "speaker_id": m.speaker_id,
                    "position": m.position.value,
                    "phase": m.phase.value,
                    "round_number": m.round_number,
                    "content": m.content,
                    "timestamp": _safe_isoformat(m.timestamp)
                    or datetime.now().isoformat(),
                    "word_count": len(m.content.split()),
                    "metadata": m.metadata,
                    "cost": m.cost,
                    "generation_id": m.generation_id,
                    "cost_queried_at": _safe_isoformat(m.cost_queried_at),
                }
                for m in context.messages
            ],
        }

        db_id = self.db.save_debate(transcript_data)
        logger.info(f"Saved transcript with database ID {db_id}")

        # Save judge results if provided
        if judge_result:
            if (
                isinstance(judge_result, dict)
                and judge_result.get("type") == "ensemble"
            ):
                await self.save_ensemble_result(db_id, judge_result)
            elif isinstance(judge_result, JudgeDecision):
                await self.save_individual_decision(db_id, judge_result)

        return db_id

    async def save_individual_decision(
        self, debate_id: int, judge_decision: JudgeDecision
    ) -> int:
        """Save a single judge decision to the database."""
        logger.info(f"Saving individual judge decision for debate {debate_id}")

        decision_id = self.db.save_judge_decision(
            debate_id=debate_id,
            winner_id=judge_decision.winner_id,
            winner_margin=judge_decision.winner_margin,
            overall_feedback=judge_decision.overall_feedback,
            reasoning=judge_decision.reasoning,
            judge_model=judge_decision.judge_model,
            judge_provider=judge_decision.judge_provider,
            generation_time_ms=judge_decision.generation_time_ms,
            cost=judge_decision.cost,
            generation_id=judge_decision.generation_id,
            cost_queried_at=_safe_isoformat(
                getattr(judge_decision, "cost_queried_at", None)
            ),
        )

        # Save criterion scores
        if judge_decision.criterion_scores:
            criterion_data = [
                {
                    "criterion": score.criterion.value,
                    "participant_id": score.participant_id,
                    "score": score.score,
                    "feedback": score.feedback,
                }
                for score in judge_decision.criterion_scores
            ]
            self.db.save_criterion_scores(decision_id, criterion_data)

        logger.info(f"Saved judge decision {decision_id} for debate {debate_id}")
        return decision_id

    async def save_ensemble_result(
        self, debate_id: int, ensemble_result: dict[str, Any]
    ) -> None:
        """Save ensemble result - individual decisions + ensemble summary."""
        decisions: list[JudgeDecision] = ensemble_result["decisions"]
        ensemble_summary: dict[str, Any] = ensemble_result["ensemble_summary"]

        logger.info(
            f"Saving ensemble result with {len(decisions)} decisions for debate"
            f" {debate_id}"
        )

        # Save each individual decision
        decision_ids: list[int] = []
        for i, decision in enumerate(decisions):
            decision_id = await self.save_individual_decision(debate_id, decision)
            decision_ids.append(decision_id)
            logger.info(
                f"Saved decision {i + 1}/{len(decisions)} with ID {decision_id}"
            )

        # Save ensemble summary
        ensemble_data: dict[str, Any] = {
            "final_winner_id": ensemble_summary["final_winner_id"],
            "final_margin": ensemble_summary["final_margin"],
            "ensemble_method": ensemble_summary.get("ensemble_method", "majority"),
            "num_judges": ensemble_summary["num_judges"],
            "consensus_level": ensemble_summary.get("consensus_level"),
            "summary_reasoning": ensemble_summary.get("summary_reasoning"),
            "summary_feedback": ensemble_summary.get("summary_feedback"),
            "participating_judge_decision_ids": ",".join(map(str, decision_ids)),
        }

        ensemble_id = self.db.save_ensemble_summary(debate_id, ensemble_data)
        logger.info(f"Saved ensemble summary {ensemble_id} for debate {debate_id}")

    def display_judge_results(
        self, db_id: int, judge_result: JudgeDecision | dict[str, Any] | None
    ) -> None:
        """Load and display judge results from database."""
        try:
            # Check if this is an ensemble result
            if (
                isinstance(judge_result, dict)
                and judge_result.get("type") == "ensemble"
            ):
                # Load ensemble summary
                ensemble_summary = self.db.load_ensemble_summary(db_id)
                if ensemble_summary:
                    # Load all individual decisions
                    individual_decisions = self.db.load_judge_decisions(db_id)

                    # Collect all criterion scores
                    all_criterion_scores: list[dict[str, Any]] = []
                    for decision in individual_decisions:
                        all_criterion_scores.extend(decision["criterion_scores"])

                    decision_dict: dict[str, Any] = {
                        "winner_id": ensemble_summary["final_winner_id"],
                        "winner_margin": ensemble_summary["final_margin"],
                        "overall_feedback": ensemble_summary["summary_feedback"],
                        "reasoning": ensemble_summary["summary_reasoning"],
                        "criterion_scores": all_criterion_scores,
                        "metadata": {
                            "ensemble_size": ensemble_summary["num_judges"],
                            "consensus_level": ensemble_summary["consensus_level"],
                            "ensemble_method": ensemble_summary["ensemble_method"],
                            "individual_decisions": individual_decisions,
                        },
                    }

                    display_judge_decision(self.console, self.config, decision_dict)
            else:
                # Single judge case
                judge_decision = self.db.load_judge_decision(db_id)
                if judge_decision:
                    display_judge_decision(self.console, self.config, judge_decision)

        except Exception as e:
            logger.error(f"Failed to display judge results: {e}")
            self.console.print(f"\n[red]Failed to display judge results: {e}[/red]")
