"""Strictly typed configuration system for CLI client."""

import json
from pathlib import Path
from typing import TYPE_CHECKING
from pydantic import BaseModel, Field

if TYPE_CHECKING:
    pass


class ModelConfig(BaseModel):
    """Model configuration."""
    name: str
    provider: str
    personality: str
    max_tokens: int
    temperature: float


class DebateConfig(BaseModel):
    """Debate configuration."""
    topic: str
    format: str
    time_per_turn: int
    word_limit: int


class JudgingConfig(BaseModel):
    """Judging configuration."""
    judge_models: list[str]
    judge_provider: str
    criteria: list[str]


class SystemConfig(BaseModel):
    """System configuration."""
    api_base_url: str = Field(default="http://localhost:8000")
    log_level: str = Field(default="INFO")
    # Timeout configurations
    http_timeout_local: float = Field(default=120.0, description="HTTP timeout for local providers (Ollama)")
    http_timeout_remote: float = Field(default=30.0, description="HTTP timeout for remote providers (OpenRouter)")
    websocket_timeout: float = Field(default=60.0, description="WebSocket handshake timeout")


class AppConfig(BaseModel):
    """Complete application configuration."""
    debate: DebateConfig
    models: dict[str, ModelConfig]
    judging: JudgingConfig
    system: SystemConfig

    @classmethod
    def load_from_file(cls, config_path: Path) -> 'AppConfig':
        """Load configuration from JSON file."""
        with open(config_path, 'r', encoding='utf-8') as f:
            config_data = json.load(f)
        return cls(**config_data)


def get_default_config() -> AppConfig:
    """Get default configuration from debate_config.json."""
    config_path = Path("debate_config.json")
    return AppConfig.load_from_file(config_path)