"""Configuration wrapper for CLI - uses engine's config models with env var fallback."""

import os
import sys
from pathlib import Path

# Import config models directly from the engine
from dialectus.engine.config.settings import (
    AppConfig,
    ModelConfig,
    DebateConfig,
    JudgingConfig,
    SystemConfig,
    OllamaConfig,
    OpenRouterConfig,
    AnthropicConfig,
)


class ConfigurationError(Exception):
    """Raised when configuration validation fails (e.g., missing API keys)."""

    pass


def get_default_config() -> AppConfig:
    """
    Load default configuration from debate_config.json with environment variable fallback.

    Environment variables checked (in priority order):
    - OPENROUTER_API_KEY: OpenRouter API key (overrides config file)
    - ANTHROPIC_API_KEY: Anthropic API key (overrides config file)
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

    anthropic_key_from_env = os.environ.get("ANTHROPIC_API_KEY")
    if anthropic_key_from_env:
        config.system.anthropic.api_key = anthropic_key_from_env

    # Validate API keys for configured providers
    _validate_provider_api_keys(config)

    return config


def _validate_provider_api_keys(config: AppConfig) -> None:
    """Validate that API keys are provided for all configured providers.

    Raises:
        ConfigurationError: If a provider is configured but missing an API key.
    """
    # Check OpenRouter
    uses_openrouter = any(
        model.provider == "openrouter" for model in config.models.values()
    )
    if uses_openrouter and not config.system.openrouter.api_key:
        _print_api_key_error("OpenRouter", "OPENROUTER_API_KEY")
        raise ConfigurationError("Missing OpenRouter API key")

    # Check Anthropic
    uses_anthropic = any(
        model.provider == "anthropic" for model in config.models.values()
    )
    if uses_anthropic and not config.system.anthropic.api_key:
        _print_api_key_error("Anthropic", "ANTHROPIC_API_KEY")
        raise ConfigurationError("Missing Anthropic API key")


def _print_api_key_error(provider_name: str, env_var_name: str) -> None:
    """Print a user-friendly error message for missing API keys."""
    print(f"\n❌ [ERROR] Missing {provider_name} API Key\n", file=sys.stderr)
    print(
        f"You're using {provider_name} models but no API key was found.\n",
        file=sys.stderr,
    )
    print("To fix this, you can either:", file=sys.stderr)
    print(
        f"  1. Set environment variable: export {env_var_name}='your-key-here'",
        file=sys.stderr,
    )
    print(
        f"  2. Add to debate_config.json under system.{provider_name.lower()}.api_key\n",
        file=sys.stderr,
    )


# Re-export all config models for backward compatibility
__all__ = [
    "AppConfig",
    "ModelConfig",
    "DebateConfig",
    "JudgingConfig",
    "SystemConfig",
    "OllamaConfig",
    "OpenRouterConfig",
    "AnthropicConfig",
    "ConfigurationError",
    "get_default_config",
]
