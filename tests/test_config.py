"""Tests for configuration loading and validation."""

import os
from pathlib import Path
from unittest.mock import patch

import pytest

from dialectus.cli.config import get_default_config, AppConfig


class TestConfigLoading:
    def test_load_config_from_file(self, temp_config_file: Path):
        with patch("dialectus.cli.config.Path") as mock_path_class:
            mock_path_instance = mock_path_class.return_value
            mock_path_instance.exists.return_value = True

            config = AppConfig.load_from_file(temp_config_file)

            assert config.debate.topic == "Test topic"
            assert config.debate.format == "oxford"
            assert config.debate.time_per_turn == 120
            assert config.debate.word_limit == 200

    def test_config_file_not_found(self):
        with patch("dialectus.cli.config.Path") as mock_path_class:
            mock_path_instance = mock_path_class.return_value
            mock_path_instance.exists.return_value = False

            with pytest.raises(FileNotFoundError, match="debate_config.json not found"):
                get_default_config()

    def test_env_var_overrides_config(
        self, temp_config_file: Path, monkeypatch: pytest.MonkeyPatch
    ):
        monkeypatch.setenv("OPENROUTER_API_KEY", "test-api-key-from-env")

        with patch("dialectus.cli.config.Path") as mock_path_class:
            mock_path_instance = mock_path_class.return_value
            mock_path_instance.exists.return_value = True

            with patch("dialectus.cli.config.AppConfig.load_from_file") as mock_load:
                mock_load.return_value = AppConfig.load_from_file(temp_config_file)

                config = get_default_config()

                assert config.system.openrouter.api_key == "test-api-key-from-env"

    def test_openrouter_validation_missing_key(
        self, temp_config_file: Path, monkeypatch: pytest.MonkeyPatch
    ):
        if "OPENROUTER_API_KEY" in os.environ:
            monkeypatch.delenv("OPENROUTER_API_KEY")

        config = AppConfig.load_from_file(temp_config_file)
        config.models["model_a"].provider = "openrouter"
        config.system.openrouter.api_key = None

        with patch("dialectus.cli.config.Path") as mock_path_class:
            mock_path_instance = mock_path_class.return_value
            mock_path_instance.exists.return_value = True

            with patch(
                "dialectus.cli.config.AppConfig.load_from_file", return_value=config
            ):
                with pytest.raises(
                    ValueError, match="OpenRouter models configured but no API key"
                ):
                    get_default_config()

    def test_openrouter_with_valid_key(self, temp_config_file: Path):
        with patch("dialectus.cli.config.Path") as mock_path_class:
            mock_path_instance = mock_path_class.return_value
            mock_path_instance.exists.return_value = True

            with patch("dialectus.cli.config.AppConfig.load_from_file") as mock_load:
                config = AppConfig.load_from_file(temp_config_file)
                config.models["model_a"].provider = "openrouter"
                config.system.openrouter.api_key = "test-key-in-config"
                mock_load.return_value = config

                config = get_default_config()

                assert config.system.openrouter.api_key == "test-key-in-config"

    def test_ollama_models_no_key_required(
        self, temp_config_file: Path, monkeypatch: pytest.MonkeyPatch
    ):
        if "OPENROUTER_API_KEY" in os.environ:
            monkeypatch.delenv("OPENROUTER_API_KEY")

        loaded_config = AppConfig.load_from_file(temp_config_file)

        with patch("dialectus.cli.config.Path") as mock_path_class:
            mock_path_instance = mock_path_class.return_value
            mock_path_instance.exists.return_value = True

            with patch(
                "dialectus.cli.config.AppConfig.load_from_file",
                return_value=loaded_config,
            ):
                config = get_default_config()

                assert config.models["model_a"].provider == "ollama"
                assert config.models["model_b"].provider == "ollama"

    def test_config_preserves_all_settings(self, temp_config_file: Path):
        loaded_config = AppConfig.load_from_file(temp_config_file)

        with patch("dialectus.cli.config.Path") as mock_path_class:
            mock_path_instance = mock_path_class.return_value
            mock_path_instance.exists.return_value = True

            with patch(
                "dialectus.cli.config.AppConfig.load_from_file",
                return_value=loaded_config,
            ):
                config = get_default_config()

                assert config.models["model_a"].name == "qwen2.5:7b"
                assert config.models["model_a"].personality == "analytical"
                assert config.models["model_a"].max_tokens == 300
                assert config.models["model_a"].temperature == 0.7

                assert config.judging.judge_models == ["openthinker:7b"]
                assert config.judging.judge_provider == "ollama"
                assert config.judging.criteria == [
                    "logic",
                    "evidence",
                    "persuasiveness",
                ]

                assert config.system.ollama_base_url == "http://localhost:11434"
                assert config.system.log_level == "INFO"
