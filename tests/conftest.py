"""Shared pytest fixtures for Dialectus CLI tests."""

import tempfile
from pathlib import Path
from typing import Any, Generator

import pytest


@pytest.fixture
def temp_db() -> Generator[str, None, None]:
    """Provide a temporary database file path."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = f.name
    yield db_path
    Path(db_path).unlink(missing_ok=True)


@pytest.fixture
def sample_debate_data() -> dict[str, Any]:
    """Provide sample debate transcript data."""
    return {
        "metadata": {
            "topic": "Should AI be regulated?",
            "format": "oxford",
            "participants": {
                "model_a": {"name": "qwen2.5:7b", "personality": "analytical"},
                "model_b": {"name": "llama3.2:3b", "personality": "passionate"},
            },
            "final_phase": "closing",
            "total_rounds": 3,
            "saved_at": "2025-10-12T10:30:00",
            "message_count": 6,
            "word_count": 1200,
            "total_debate_time_ms": 45000,
        },
        "messages": [
            {
                "speaker_id": "model_a",
                "position": "pro",
                "phase": "opening",
                "round_number": 1,
                "content": "AI regulation is essential for safety.",
                "timestamp": "2025-10-12T10:30:00",
                "word_count": 6,
                "metadata": {},
                "cost": 0.001,
                "generation_id": "gen_123",
                "cost_queried_at": "2025-10-12T10:30:05",
            },
            {
                "speaker_id": "model_b",
                "position": "con",
                "phase": "opening",
                "round_number": 1,
                "content": "AI regulation stifles innovation.",
                "timestamp": "2025-10-12T10:30:15",
                "word_count": 4,
                "metadata": {},
                "cost": 0.001,
                "generation_id": "gen_124",
                "cost_queried_at": "2025-10-12T10:30:20",
            },
        ],
    }


@pytest.fixture
def sample_judge_decision() -> dict[str, Any]:
    """Provide sample judge decision data."""
    return {
        "winner_id": "model_a",
        "winner_margin": 2.5,
        "overall_feedback": "Model A provided stronger arguments.",
        "reasoning": "Superior evidence and logical structure.",
        "judge_model": "openthinker:7b",
        "judge_provider": "ollama",
        "generation_time_ms": 5000,
        "cost": 0.002,
        "generation_id": "gen_judge_1",
        "cost_queried_at": "2025-10-12T10:31:00",
    }


@pytest.fixture
def sample_criterion_scores() -> list[dict[str, Any]]:
    """Provide sample criterion scoring data."""
    return [
        {
            "criterion": "logic",
            "participant_id": "model_a",
            "score": 8.5,
            "feedback": "Strong logical flow",
        },
        {
            "criterion": "logic",
            "participant_id": "model_b",
            "score": 7.0,
            "feedback": "Good but some gaps",
        },
        {
            "criterion": "evidence",
            "participant_id": "model_a",
            "score": 9.0,
            "feedback": "Excellent citations",
        },
        {
            "criterion": "evidence",
            "participant_id": "model_b",
            "score": 6.5,
            "feedback": "Limited evidence",
        },
    ]


@pytest.fixture
def temp_config_file() -> Generator[Path, None, None]:
    """Provide a temporary config file."""
    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".json", delete=False, encoding="utf-8"
    ) as f:
        f.write("""{
  "debate": {
    "topic": "Test topic",
    "format": "oxford",
    "time_per_turn": 120,
    "word_limit": 200
  },
  "models": {
    "model_a": {
      "name": "qwen2.5:7b",
      "provider": "ollama",
      "personality": "analytical",
      "max_tokens": 300,
      "temperature": 0.7
    },
    "model_b": {
      "name": "llama3.2:3b",
      "provider": "ollama",
      "personality": "passionate",
      "max_tokens": 300,
      "temperature": 0.8
    }
  },
  "judging": {
    "judge_models": ["openthinker:7b"],
    "judge_provider": "ollama",
    "criteria": ["logic", "evidence", "persuasiveness"]
  },
  "system": {
    "ollama_base_url": "http://localhost:11434",
    "ollama": {
      "num_gpu_layers": -1,
      "keep_alive": "5m"
    },
    "openrouter": {
      "api_key": null,
      "base_url": "https://openrouter.ai/api/v1"
    },
    "log_level": "INFO"
  }
}""")
        config_path = Path(f.name)
    yield config_path
    config_path.unlink(missing_ok=True)
