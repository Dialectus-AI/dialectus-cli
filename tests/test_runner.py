"""Tests for debate runner orchestration with async patterns and mocking."""

from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock, Mock, patch

import pytest

from dialectus.cli.runner import DebateRunner, _safe_isoformat  # pyright: ignore[reportPrivateUsage]
from dialectus.cli.config import AppConfig
from dialectus.engine.debate_engine import DebateContext, DebatePhase
from dialectus.engine.judges.base import (
    JudgeDecision,
    CriterionScore,
    JudgmentCriterion,
)
from dialectus.engine.models.providers import ProviderRateLimitError


@pytest.fixture
def mock_config(temp_config_file: Path) -> AppConfig:
    return AppConfig.load_from_file(temp_config_file)


@pytest.fixture
def mock_console() -> Mock:
    return Mock()


@pytest.fixture
def mock_debate_context() -> Mock:
    context = Mock(spec=DebateContext)
    context.topic = "Should AI be regulated?"
    context.participants = {
        "model_a": Mock(
            name="qwen2.5:7b",
            personality="analytical",
        ),
        "model_b": Mock(
            name="llama3.2:3b",
            personality="passionate",
        ),
    }
    context.current_phase = DebatePhase.CLOSING
    context.current_round = 3
    context.metadata = {"format": "oxford", "total_debate_time_ms": 45000}

    mock_message = Mock()
    mock_message.speaker_id = "model_a"
    mock_message.position = Mock(value="pro")
    mock_message.phase = Mock(value="opening")
    mock_message.round_number = 1
    mock_message.content = "AI regulation is essential."
    mock_message.word_count = 4
    mock_message.metadata = {}
    mock_message.cost = 0.001
    mock_message.generation_id = "gen_1"
    mock_message.timestamp = None
    mock_message.cost_queried_at = None

    context.messages = [mock_message]

    return context


@pytest.fixture
def mock_judge_decision() -> JudgeDecision:
    return JudgeDecision(
        winner_id="model_a",
        winner_margin=2.5,
        overall_feedback="Strong arguments.",
        reasoning="Clear logic.",
        judge_model="openthinker:7b",
        judge_provider="ollama",
        criterion_scores=[
            CriterionScore(
                criterion=JudgmentCriterion.LOGIC,
                participant_id="model_a",
                score=8.5,
                feedback="Excellent",
            ),
        ],
        generation_time_ms=5000,
    )


class TestDebateRunner:
    def test_runner_initialization(
        self, mock_config: AppConfig, mock_console: Mock, temp_db: str
    ):
        with patch("dialectus.cli.runner.DatabaseManager") as mock_db:
            mock_db_instance = Mock()
            mock_db_instance.db_path = temp_db
            mock_db.return_value = mock_db_instance

            runner = DebateRunner(mock_config, mock_console)

            assert runner.config == mock_config
            assert runner.console == mock_console
            assert runner.model_manager is not None
            assert runner.engine is not None
            assert runner.db is not None

    @pytest.mark.asyncio
    async def test_run_debate_success(
        self,
        mock_config: AppConfig,
        mock_console: Mock,
        mock_debate_context: Mock,
        mock_judge_decision: JudgeDecision,
        temp_db: str,
    ):
        with patch("dialectus.cli.runner.DatabaseManager") as mock_db_class:
            mock_db = Mock()
            mock_db.save_debate.return_value = 1
            mock_db.save_judge_decision.return_value = 1
            mock_db.save_criterion_scores.return_value = None
            mock_db.load_judge_decision.return_value = None
            mock_db_class.return_value = mock_db

            runner = DebateRunner(mock_config, mock_console)

            runner.engine.initialize_debate = AsyncMock(
                return_value=mock_debate_context
            )
            runner.engine.run_full_debate = AsyncMock(return_value=mock_debate_context)
            runner.engine.judge_debate_with_judges = AsyncMock(
                return_value=mock_judge_decision
            )

            with patch("dialectus.cli.runner.create_judges", return_value=[Mock()]):
                await runner.run_debate()

            runner.engine.initialize_debate.assert_called_once()
            runner.engine.run_full_debate.assert_called_once()
            mock_console.print.assert_called()

    @pytest.mark.asyncio
    async def test_run_debate_invalid_format(
        self, mock_config: AppConfig, mock_console: Mock, temp_db: str
    ):
        mock_config.debate.format = "invalid_format"

        with patch("dialectus.cli.runner.DatabaseManager") as mock_db:
            mock_db_instance = Mock()
            mock_db_instance.db_path = temp_db
            mock_db.return_value = mock_db_instance

            with pytest.raises(ValueError):
                DebateRunner(mock_config, mock_console)

    @pytest.mark.asyncio
    async def test_run_debate_rate_limit_error(
        self,
        mock_config: AppConfig,
        mock_console: Mock,
        mock_debate_context: DebateContext,
    ):
        runner = DebateRunner(mock_config, mock_console)

        runner.engine.initialize_debate = AsyncMock(return_value=mock_debate_context)
        runner.engine.run_full_debate = AsyncMock(
            side_effect=ProviderRateLimitError(
                provider="openrouter", status_code=429, model="gpt-4"
            )
        )

        with pytest.raises(ProviderRateLimitError):
            await runner.run_debate()

    @pytest.mark.asyncio
    async def test_run_debate_generic_error(
        self,
        mock_config: AppConfig,
        mock_console: Mock,
        mock_debate_context: DebateContext,
    ):
        runner = DebateRunner(mock_config, mock_console)

        runner.engine.initialize_debate = AsyncMock(return_value=mock_debate_context)
        runner.engine.run_full_debate = AsyncMock(
            side_effect=Exception("Unexpected error")
        )

        with pytest.raises(Exception, match="Unexpected error"):
            await runner.run_debate()

    @pytest.mark.asyncio
    async def test_run_debate_with_no_judges(
        self,
        mock_config: AppConfig,
        mock_console: Mock,
        mock_debate_context: Mock,
        temp_db: str,
    ):
        mock_config.judging.judge_models = []

        with patch("dialectus.cli.runner.DatabaseManager") as mock_db_class:
            mock_db = Mock()
            mock_db.save_debate.return_value = 1
            mock_db_class.return_value = mock_db

            runner = DebateRunner(mock_config, mock_console)

            runner.engine.initialize_debate = AsyncMock(
                return_value=mock_debate_context
            )
            runner.engine.run_full_debate = AsyncMock(return_value=mock_debate_context)

            await runner.run_debate()

            runner.engine.initialize_debate.assert_called_once()
            runner.engine.run_full_debate.assert_called_once()

    @pytest.mark.asyncio
    async def test_run_debate_judge_failure(
        self,
        mock_config: AppConfig,
        mock_console: Mock,
        mock_debate_context: DebateContext,
        temp_db: str,
    ):
        runner = DebateRunner(mock_config, mock_console)
        runner.db.db_path = temp_db

        runner.engine.initialize_debate = AsyncMock(return_value=mock_debate_context)
        runner.engine.run_full_debate = AsyncMock(return_value=mock_debate_context)
        runner.engine.judge_debate_with_judges = AsyncMock(
            side_effect=Exception("Judge error")
        )

        with patch("dialectus.cli.runner.create_judges", return_value=[Mock()]):
            with pytest.raises(RuntimeError, match="judging failed"):
                await runner.run_debate()

    @pytest.mark.asyncio
    async def test_save_transcript(
        self,
        mock_config: AppConfig,
        mock_console: Mock,
        mock_debate_context: Mock,
        mock_judge_decision: JudgeDecision,
        temp_db: str,
    ):
        with patch("dialectus.cli.runner.DatabaseManager") as mock_db_class:
            mock_db = Mock()
            mock_db.save_debate.return_value = 42
            mock_db.save_judge_decision.return_value = 1
            mock_db.save_criterion_scores.return_value = None
            mock_db_class.return_value = mock_db

            runner = DebateRunner(mock_config, mock_console)

            debate_id = await runner.save_transcript(
                mock_debate_context, mock_judge_decision
            )

            assert debate_id == 42
            mock_db.save_debate.assert_called_once()

            args, _ = mock_db.save_debate.call_args
            transcript_payload = args[0]
            assert transcript_payload["messages"][0]["timestamp"] is not None

    @pytest.mark.asyncio
    async def test_save_individual_decision(
        self,
        mock_config: AppConfig,
        mock_console: Mock,
        mock_judge_decision: JudgeDecision,
        temp_db: str,
        sample_debate_data: dict[str, Any],
    ):
        with patch("dialectus.cli.runner.DatabaseManager") as mock_db_class:
            mock_db = Mock()
            mock_db.db_path = temp_db
            mock_db_class.return_value = mock_db

            from dialectus.cli.database import DatabaseManager

            real_db = DatabaseManager(temp_db)
            mock_db.save_debate = real_db.save_debate
            mock_db.load_judge_decision = real_db.load_judge_decision
            mock_db.save_judge_decision = real_db.save_judge_decision
            mock_db.save_criterion_scores = real_db.save_criterion_scores

            runner = DebateRunner(mock_config, mock_console)

            debate_id = real_db.save_debate(sample_debate_data)
            decision_id = await runner.save_individual_decision(
                debate_id, mock_judge_decision
            )

            assert decision_id > 0

            loaded = real_db.load_judge_decision(debate_id)
            assert loaded is not None
            assert loaded["winner_id"] == "model_a"

    @pytest.mark.asyncio
    async def test_save_ensemble_result(
        self,
        mock_config: AppConfig,
        mock_console: Mock,
        mock_judge_decision: JudgeDecision,
        temp_db: str,
        sample_debate_data: dict[str, Any],
    ):
        with patch("dialectus.cli.runner.DatabaseManager") as mock_db_class:
            from dialectus.cli.database import DatabaseManager

            real_db = DatabaseManager(temp_db)
            mock_db_class.return_value = real_db

            runner = DebateRunner(mock_config, mock_console)

            debate_id = real_db.save_debate(sample_debate_data)

            ensemble_result = {
                "type": "ensemble",
                "decisions": [mock_judge_decision, mock_judge_decision],
                "ensemble_summary": {
                    "final_winner_id": "model_a",
                    "final_margin": 2.8,
                    "num_judges": 2,
                    "consensus_level": 0.95,
                    "summary_reasoning": "Unanimous",
                    "summary_feedback": "Strong",
                },
            }

            await runner.save_ensemble_result(debate_id, ensemble_result)

            loaded = real_db.load_ensemble_summary(debate_id)
            assert loaded is not None
            assert loaded["final_winner_id"] == "model_a"
            assert loaded["num_judges"] == 2

    def test_display_message(
        self, mock_config: AppConfig, mock_console: Mock, temp_db: str
    ):
        with patch("dialectus.cli.runner.DatabaseManager") as mock_db:
            mock_db_instance = Mock()
            mock_db_instance.db_path = temp_db
            mock_db.return_value = mock_db_instance

            runner = DebateRunner(mock_config, mock_console)

            message = {
                "speaker_id": "model_a",
                "position": "pro",
                "phase": "opening",
                "content": "Test message",
            }

            runner.display_message(message)

            mock_console.print.assert_called()

    def test_display_judge_results(
        self,
        mock_config: AppConfig,
        mock_console: Mock,
        mock_judge_decision: JudgeDecision,
        temp_db: str,
        sample_debate_data: dict[str, Any],
    ):
        with patch("dialectus.cli.runner.DatabaseManager") as mock_db_class:
            mock_db = Mock()
            mock_db.load_judge_decision.return_value = {
                "winner_id": "model_a",
                "winner_margin": 2.5,
                "overall_feedback": "Good",
                "reasoning": "Clear",
                "criterion_scores": [],
                "metadata": {},
            }
            mock_db.load_ensemble_summary.return_value = None
            mock_db_class.return_value = mock_db

            runner = DebateRunner(mock_config, mock_console)

            runner.display_judge_results(1, mock_judge_decision)

            assert mock_console.print.call_count > 0


class TestHelperFunctions:
    def test_safe_isoformat_with_none(self):
        assert _safe_isoformat(None) is None

    def test_safe_isoformat_with_string(self):
        assert _safe_isoformat("2025-10-12T10:00:00") == "2025-10-12T10:00:00"

    def test_safe_isoformat_with_datetime(self):
        from datetime import datetime

        dt = datetime(2025, 10, 12, 10, 0, 0)
        result = _safe_isoformat(dt)
        assert result is not None
        assert "2025-10-12" in result

    def test_safe_isoformat_with_other_type(self):
        result = _safe_isoformat(12345)
        assert result == "12345"

    def test_safe_isoformat_with_isoformat_method(self):
        class MockDateTime:
            def isoformat(self) -> str:
                return "2025-10-12T10:00:00"

        result = _safe_isoformat(MockDateTime())
        assert result == "2025-10-12T10:00:00"
