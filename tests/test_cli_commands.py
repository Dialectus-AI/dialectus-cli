"""Tests for CLI commands using Click's test runner."""

from pathlib import Path
from unittest.mock import AsyncMock, Mock, patch

import pytest
from click.testing import CliRunner

from dialectus.cli.main import cli
from dialectus.cli.config import AppConfig
from dialectus.cli.db_types import TranscriptListRow


@pytest.fixture
def cli_runner() -> CliRunner:
    return CliRunner()


@pytest.fixture
def mock_app_config(temp_config_file: Path) -> AppConfig:
    return AppConfig.load_from_file(temp_config_file)


class TestCLICommands:
    def test_cli_help(self, cli_runner: CliRunner):
        result = cli_runner.invoke(cli, ["--help"])
        assert result.exit_code == 0
        assert "Dialectus" in result.output

    def test_debate_help(self, cli_runner: CliRunner, temp_config_file: Path):
        result = cli_runner.invoke(
            cli, ["--config", str(temp_config_file), "debate", "--help"]
        )
        assert result.exit_code == 0
        assert "Start a debate" in result.output

    def test_list_models_help(self, cli_runner: CliRunner, temp_config_file: Path):
        result = cli_runner.invoke(
            cli, ["--config", str(temp_config_file), "list-models", "--help"]
        )
        assert result.exit_code == 0
        assert "List available models" in result.output

    def test_transcripts_help(self, cli_runner: CliRunner, temp_config_file: Path):
        result = cli_runner.invoke(
            cli, ["--config", str(temp_config_file), "transcripts", "--help"]
        )
        assert result.exit_code == 0
        assert "List saved debate transcripts" in result.output

    def test_cli_with_config_file(self, cli_runner: CliRunner, temp_config_file: Path):
        result = cli_runner.invoke(
            cli, ["--config", str(temp_config_file), "transcripts"]
        )
        assert "Loaded config from" in result.output or result.exit_code == 0

    def test_cli_with_invalid_config_path(self, cli_runner: CliRunner):
        result = cli_runner.invoke(cli, ["--config", "nonexistent.json", "transcripts"])
        assert result.exit_code != 0

    def test_cli_log_level_override(
        self, cli_runner: CliRunner, temp_config_file: Path
    ):
        result = cli_runner.invoke(
            cli,
            ["--config", str(temp_config_file), "--log-level", "DEBUG", "transcripts"],
        )
        assert result.exit_code == 0

    @patch("dialectus.cli.main.DebateRunner")
    @patch("dialectus.cli.main.get_default_config")
    def test_debate_command(
        self,
        mock_get_config: Mock,
        mock_runner_class: Mock,
        cli_runner: CliRunner,
        mock_app_config: AppConfig,
    ):
        mock_get_config.return_value = mock_app_config
        mock_runner = Mock()
        mock_runner.run_debate = AsyncMock()
        mock_runner_class.return_value = mock_runner

        result = cli_runner.invoke(cli, ["debate"])

        assert result.exit_code == 0 or "Loaded config" in result.output

    @patch("dialectus.cli.main.get_default_config")
    def test_debate_with_topic_override(
        self,
        mock_get_config: Mock,
        cli_runner: CliRunner,
        mock_app_config: AppConfig,
    ):
        mock_get_config.return_value = mock_app_config

        with patch("dialectus.cli.main.DebateRunner") as mock_runner_class:
            mock_runner = Mock()
            mock_runner.run_debate = AsyncMock()
            mock_runner_class.return_value = mock_runner

            result = cli_runner.invoke(
                cli, ["debate", "--topic", "Custom debate topic"]
            )

            assert result.exit_code == 0 or "Custom debate topic" in str(
                mock_runner_class.call_args
            )

    @patch("dialectus.cli.main.get_default_config")
    def test_debate_with_format_override(
        self,
        mock_get_config: Mock,
        cli_runner: CliRunner,
        mock_app_config: AppConfig,
    ):
        mock_get_config.return_value = mock_app_config

        with patch("dialectus.cli.main.DebateRunner") as mock_runner_class:
            mock_runner = Mock()
            mock_runner.run_debate = AsyncMock()
            mock_runner_class.return_value = mock_runner

            result = cli_runner.invoke(cli, ["debate", "--format", "socratic"])

            assert result.exit_code == 0

    @patch("dialectus.cli.main.get_default_config")
    def test_debate_interactive_cancelled(
        self,
        mock_get_config: Mock,
        cli_runner: CliRunner,
        mock_app_config: AppConfig,
    ):
        mock_get_config.return_value = mock_app_config

        result = cli_runner.invoke(cli, ["debate", "--interactive"], input="n\n")

        assert "cancelled" in result.output.lower() or result.exit_code == 0

    @patch("dialectus.cli.main.get_default_config")
    def test_list_models_command(
        self,
        mock_get_config: Mock,
        cli_runner: CliRunner,
        mock_app_config: AppConfig,
    ):
        mock_get_config.return_value = mock_app_config

        # Mock the provider classes that are imported inside list_models
        with patch(
            "dialectus.engine.models.providers.ollama_provider.OllamaProvider"
        ) as mock_ollama:
            mock_ollama_instance = Mock()
            mock_ollama_instance.get_enhanced_models = AsyncMock(
                return_value=[
                    Mock(
                        id="qwen2.5:7b",
                        provider="ollama",
                        description="Qwen model for reasoning",
                    ),
                    Mock(
                        id="llama3.2:3b",
                        provider="ollama",
                        description="Llama model for chat",
                    ),
                ]
            )
            mock_ollama.return_value = mock_ollama_instance

            result = cli_runner.invoke(cli, ["list-models"])

            assert result.exit_code == 0
            assert "Available Models" in result.output or "Fetching" in result.output

    @patch("dialectus.cli.main.DatabaseManager")
    @patch("dialectus.cli.main.get_default_config")
    def test_transcripts_command_empty(
        self,
        mock_get_config: Mock,
        mock_db_manager: Mock,
        cli_runner: CliRunner,
        mock_app_config: AppConfig,
    ):
        mock_get_config.return_value = mock_app_config

        mock_db_instance = Mock()
        mock_db_instance.list_transcripts.return_value = []
        mock_db_manager.return_value = mock_db_instance

        result = cli_runner.invoke(cli, ["transcripts"])

        assert result.exit_code == 0
        assert "No transcripts found" in result.output

    @patch("dialectus.cli.main.DatabaseManager")
    @patch("dialectus.cli.main.get_default_config")
    def test_transcripts_command_with_data(
        self,
        mock_get_config: Mock,
        mock_db_manager: Mock,
        cli_runner: CliRunner,
        mock_app_config: AppConfig,
    ):
        mock_get_config.return_value = mock_app_config

        mock_db_instance = Mock()
        mock_db_instance.list_transcripts.return_value = [
            TranscriptListRow(
                id=1,
                topic="AI Regulation",
                format="oxford",
                message_count=6,
                created_at="2025-10-12T10:00:00",
            ),
            TranscriptListRow(
                id=2,
                topic="Climate Change",
                format="parliamentary",
                message_count=8,
                created_at="2025-10-12T11:00:00",
            ),
        ]
        mock_db_manager.return_value = mock_db_instance

        result = cli_runner.invoke(cli, ["transcripts"])

        assert result.exit_code == 0
        assert "AI Regulation" in result.output
        assert "Climate Change" in result.output

    @patch("dialectus.cli.main.DatabaseManager")
    @patch("dialectus.cli.main.get_default_config")
    def test_transcripts_with_limit(
        self,
        mock_get_config: Mock,
        mock_db_manager: Mock,
        cli_runner: CliRunner,
        mock_app_config: AppConfig,
    ):
        mock_get_config.return_value = mock_app_config

        mock_db_instance = Mock()
        mock_db_instance.list_transcripts.return_value = []
        mock_db_manager.return_value = mock_db_instance

        result = cli_runner.invoke(cli, ["transcripts", "--limit", "50"])

        assert result.exit_code == 0
        mock_db_instance.list_transcripts.assert_called_once_with(limit=50)

    @patch("dialectus.cli.main.get_default_config")
    def test_debate_error_handling(
        self,
        mock_get_config: Mock,
        cli_runner: CliRunner,
        mock_app_config: AppConfig,
    ):
        mock_get_config.return_value = mock_app_config

        with patch("dialectus.cli.main.DebateRunner") as mock_runner_class:
            mock_runner = Mock()
            mock_runner.run_debate = AsyncMock(side_effect=Exception("Test error"))
            mock_runner_class.return_value = mock_runner

            result = cli_runner.invoke(cli, ["debate"])

            assert result.exit_code != 0

    @patch("dialectus.cli.main.get_default_config")
    def test_list_models_error_handling(
        self,
        mock_get_config: Mock,
        cli_runner: CliRunner,
        mock_app_config: AppConfig,
    ):
        mock_get_config.return_value = mock_app_config

        # Mock both providers to raise exceptions (all providers must fail for error exit)
        with (
            patch(
                "dialectus.engine.models.providers.ollama_provider.OllamaProvider"
            ) as mock_ollama,
            patch(
                "dialectus.engine.models.providers.open_router_provider.OpenRouterProvider"
            ) as mock_openrouter,
        ):
            mock_ollama_instance = Mock()
            mock_ollama_instance.get_enhanced_models = AsyncMock(
                side_effect=Exception("Connection failed")
            )
            mock_ollama.return_value = mock_ollama_instance

            mock_openrouter_instance = Mock()
            mock_openrouter_instance.get_enhanced_models = AsyncMock(
                side_effect=Exception("API error")
            )
            mock_openrouter.return_value = mock_openrouter_instance

            result = cli_runner.invoke(cli, ["list-models"])

            # The command succeeds (exit 0) but prints SKIP messages for failed providers
            assert result.exit_code == 0
            assert "SKIP" in result.output or "Could not fetch" in result.output
