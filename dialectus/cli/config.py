"""Configuration wrapper for CLI - uses engine's config models with env var fallback."""

import os
from pathlib import Path

# Import config models directly from the engine
from config.settings import (
    AppConfig,
    ModelConfig,
    DebateConfig,
    JudgingConfig,
    SystemConfig,
    OllamaConfig,
    OpenRouterConfig,
)


def get_default_config() -> AppConfig:
    """
    Load default configuration from debate_config.json with environment variable fallback.

    Environment variables checked (in priority order):
    - OPENROUTER_API_KEY: OpenRouter API key (overrides config file)
    """
    config_path = Path("debate_config.json")

    if not config_path.exists():
        raise FileNotFoundError(
            "debate_config.json not found. "
            "Copy debate_config.example.json to get started."
        )

    # Load base config from file
    config = AppConfig.load_from_file(config_path)

    # Apply environment variable overrides
    # Priority: env var > config file > fail
    openrouter_key_from_env = os.environ.get("OPENROUTER_API_KEY")
    if openrouter_key_from_env:
        config.system.openrouter.api_key = openrouter_key_from_env

    # Validate OpenRouter key if using OpenRouter models
    uses_openrouter = any(
        model.provider == "openrouter" for model in config.models.values()
    )

    if uses_openrouter and not config.system.openrouter.api_key:
        raise ValueError(
            "OpenRouter models configured but no API key provided. "
            "Set OPENROUTER_API_KEY environment variable or add to config file."
        )

    return config


# Re-export all config models for backward compatibility
__all__ = [
    "AppConfig",
    "ModelConfig",
    "DebateConfig",
    "JudgingConfig",
    "SystemConfig",
    "OllamaConfig",
    "OpenRouterConfig",
    "get_default_config",
]
