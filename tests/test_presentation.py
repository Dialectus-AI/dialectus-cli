"""Tests for presentation and display formatting functions."""

from pathlib import Path
from unittest.mock import Mock

import pytest
from rich.console import Console

from dialectus.cli.presentation import (
    display_debate_info,
    display_judge_decision,
    display_error,
    _format_participants,  # pyright: ignore[reportPrivateUsage]
    _format_judge_info,  # pyright: ignore[reportPrivateUsage]
    _get_victory_strength,  # pyright: ignore[reportPrivateUsage]
    _is_structured_data,  # pyright: ignore[reportPrivateUsage]
    _check_incomplete_scoring,  # pyright: ignore[reportPrivateUsage]
)
from dialectus.cli.config import AppConfig
from dialectus.cli.db_types import (
    CriterionScoreRow,
    DisplayEnsembleMetadata,
    DisplayJudgeDecision,
    JudgeDecisionWithScores,
)
from dialectus.engine.models.providers import ProviderRateLimitError


@pytest.fixture
def mock_console() -> Mock:
    console = Mock(spec=Console)
    return console


@pytest.fixture
def sample_config(temp_config_file: Path) -> AppConfig:
    return AppConfig.load_from_file(temp_config_file)


class TestDisplayFunctions:
    def test_display_debate_info(self, mock_console: Mock, sample_config: AppConfig):
        display_debate_info(mock_console, sample_config)
        mock_console.print.assert_called_once()

    def test_format_participants(self, sample_config: AppConfig):
        result = _format_participants(sample_config)

        assert "model_a" in result
        assert "model_b" in result
        assert "qwen2.5:7b" in result
        assert "llama3.2:3b" in result
        assert "analytical" in result
        assert "passionate" in result

    def test_format_judge_info_no_judges(self, sample_config: AppConfig):
        sample_config.judging.judge_models = []
        result = _format_judge_info(sample_config)
        assert result == "No judging"

    def test_format_judge_info_single_judge(self, sample_config: AppConfig):
        sample_config.judging.judge_models = ["openthinker:7b"]
        result = _format_judge_info(sample_config)
        assert "Single judge" in result
        assert "openthinker:7b" in result

    def test_format_judge_info_ensemble(self, sample_config: AppConfig):
        sample_config.judging.judge_models = ["judge1", "judge2", "judge3"]
        result = _format_judge_info(sample_config)
        assert "Ensemble" in result
        assert "3 judges" in result

    def test_get_victory_strength(self):
        assert _get_victory_strength(0.3) == "Very Close"
        assert _get_victory_strength(0.7) == "Close Victory"
        assert _get_victory_strength(1.5) == "Clear Victory"
        assert _get_victory_strength(2.5) == "Strong Victory"
        assert _get_victory_strength(3.5) == "Decisive Victory"

    def test_is_structured_data_with_json(self):
        assert _is_structured_data('{"key": "value"}')
        assert _is_structured_data('  {"winner": "model_a"}  ')

    def test_is_structured_data_with_dict_pattern(self):
        assert _is_structured_data("winner_id: model_a, participant_id: model_b")

    def test_is_structured_data_with_plain_text(self):
        assert not _is_structured_data("This is plain text reasoning.")
        assert not _is_structured_data("")

    def test_check_incomplete_scoring_empty(self):
        assert _check_incomplete_scoring([])

    def test_check_incomplete_scoring_complete(self):
        scores = [
            CriterionScoreRow(
                id=1,
                judge_decision_id=1,
                participant_id="model_a",
                criterion="logic",
                score=8.0,
                feedback="Good",
            ),
            CriterionScoreRow(
                id=2,
                judge_decision_id=1,
                participant_id="model_a",
                criterion="evidence",
                score=7.5,
                feedback="Good",
            ),
            CriterionScoreRow(
                id=3,
                judge_decision_id=1,
                participant_id="model_a",
                criterion="persuasion",
                score=8.5,
                feedback="Great",
            ),
            CriterionScoreRow(
                id=4,
                judge_decision_id=1,
                participant_id="model_b",
                criterion="logic",
                score=7.0,
                feedback="OK",
            ),
            CriterionScoreRow(
                id=5,
                judge_decision_id=1,
                participant_id="model_b",
                criterion="evidence",
                score=8.0,
                feedback="Good",
            ),
            CriterionScoreRow(
                id=6,
                judge_decision_id=1,
                participant_id="model_b",
                criterion="persuasion",
                score=7.5,
                feedback="Good",
            ),
        ]
        assert not _check_incomplete_scoring(scores)

    def test_check_incomplete_scoring_incomplete(self):
        scores = [
            CriterionScoreRow(
                id=1,
                judge_decision_id=1,
                participant_id="model_a",
                criterion="logic",
                score=8.0,
                feedback="Good",
            ),
            CriterionScoreRow(
                id=2,
                judge_decision_id=1,
                participant_id="model_b",
                criterion="logic",
                score=7.0,
                feedback="OK",
            ),
        ]
        assert _check_incomplete_scoring(scores)

    def test_display_judge_decision(self, mock_console: Mock, sample_config: AppConfig):
        decision = DisplayJudgeDecision(
            winner_id="model_a",
            winner_margin=2.5,
            overall_feedback="Strong performance.",
            reasoning="Clear logical structure.",
            criterion_scores=[
                CriterionScoreRow(
                    id=1,
                    judge_decision_id=1,
                    participant_id="model_a",
                    criterion="logic",
                    score=8.5,
                    feedback="Excellent",
                )
            ],
            metadata=DisplayEnsembleMetadata(
                ensemble_size=1,
                consensus_level=None,
                ensemble_method="single",
                individual_decisions=[],
            ),
        )

        display_judge_decision(mock_console, sample_config, decision)

        assert mock_console.print.call_count > 0

    def test_display_judge_decision_with_ensemble(
        self, mock_console: Mock, sample_config: AppConfig
    ):
        decision = DisplayJudgeDecision(
            winner_id="model_a",
            winner_margin=3.0,
            overall_feedback="Ensemble decision",
            reasoning="Majority vote",
            criterion_scores=[],
            metadata=DisplayEnsembleMetadata(
                ensemble_size=3,
                consensus_level=0.9,
                ensemble_method="majority",
                individual_decisions=[
                    JudgeDecisionWithScores(
                        id=1,
                        debate_id=1,
                        winner_id="model_a",
                        winner_margin=2.5,
                        overall_feedback="Good",
                        reasoning="Good reasoning",
                        judge_model="judge1",
                        judge_provider="ollama",
                        generation_time_ms=1000,
                        cost=None,
                        generation_id=None,
                        cost_queried_at=None,
                        created_at="2025-01-01T00:00:00",
                        criterion_scores=[],
                        metadata={"judge_model": "judge1"},
                    )
                ],
            ),
        )

        display_judge_decision(mock_console, sample_config, decision)

        assert mock_console.print.call_count > 0

    def test_display_error_with_rate_limit(self, mock_console: Mock):
        error = ProviderRateLimitError(
            provider="openrouter",
            status_code=429,
            model="gpt-4",
            detail="Rate limit exceeded",
        )

        display_error(mock_console, error)

        assert mock_console.print.call_count >= 3

    def test_display_error_with_generic_exception(self, mock_console: Mock):
        error = ValueError("Something went wrong")

        display_error(mock_console, error)

        assert mock_console.print.call_count >= 3

    def test_display_judge_decision_minimal(
        self, mock_console: Mock, sample_config: AppConfig
    ):
        """Test display with minimal required fields."""
        decision = DisplayJudgeDecision(
            winner_id="model_a",
            winner_margin=0.0,
            overall_feedback=None,
            reasoning=None,
            criterion_scores=[],
            metadata=DisplayEnsembleMetadata(
                ensemble_size=1,
                consensus_level=None,
                ensemble_method="single",
                individual_decisions=[],
            ),
        )

        display_judge_decision(mock_console, sample_config, decision)

        assert mock_console.print.call_count > 0

    def test_display_judge_decision_with_criterion_scores(
        self, mock_console: Mock, sample_config: AppConfig
    ):
        decision = DisplayJudgeDecision(
            winner_id="model_a",
            winner_margin=2.0,
            overall_feedback="Good performance",
            reasoning="Clear arguments",
            criterion_scores=[
                CriterionScoreRow(
                    id=1,
                    judge_decision_id=1,
                    participant_id="model_a",
                    criterion="logic",
                    score=8.5,
                    feedback="Strong",
                )
            ],
            metadata=DisplayEnsembleMetadata(
                ensemble_size=1,
                consensus_level=None,
                ensemble_method="single",
                individual_decisions=[],
            ),
        )

        display_judge_decision(mock_console, sample_config, decision)

        assert mock_console.print.call_count > 0
