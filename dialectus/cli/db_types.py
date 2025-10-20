"""Type-safe models for database row returns.

These TypedDict classes match the exact schema from schema.sql, ensuring
type-safe access to database query results throughout the CLI.
"""

from typing import TypedDict


# ============================================
# EXCEPTIONS
# ============================================


class DatabaseError(Exception):
    """Base exception for database errors."""


class DebateNotFoundError(DatabaseError):
    """Raised when a debate ID is not found in the database."""

    def __init__(self, debate_id: int):
        self.debate_id = debate_id
        super().__init__(f"Debate with ID {debate_id} not found")


class JudgeDecisionNotFoundError(DatabaseError):
    """Raised when a judge decision is not found for a debate."""

    def __init__(self, debate_id: int):
        self.debate_id = debate_id
        super().__init__(f"No judge decision found for debate ID {debate_id}")


class EnsembleSummaryNotFoundError(DatabaseError):
    """Raised when an ensemble summary is not found for a debate."""

    def __init__(self, debate_id: int):
        self.debate_id = debate_id
        super().__init__(f"No ensemble summary found for debate ID {debate_id}")


# ============================================
# ROW TYPES
# ============================================


class DebateRow(TypedDict):
    """Row from debates table (SELECT *)."""

    id: int
    topic: str
    format: str
    participants: str  # JSON string
    final_phase: str
    total_rounds: int
    saved_at: str
    message_count: int
    word_count: int
    total_debate_time_ms: int
    scores: str | None  # JSON string
    context_metadata: str | None  # JSON string
    created_at: str


class MessageRow(TypedDict):
    """Row from messages table (SELECT *)."""

    id: int
    debate_id: int
    speaker_id: str
    position: str
    phase: str
    round_number: int
    content: str
    timestamp: str
    word_count: int
    metadata: str | None  # JSON string
    cost: float | None
    generation_id: str | None
    cost_queried_at: str | None


class JudgeDecisionRow(TypedDict):
    """Row from judge_decisions table (SELECT *)."""

    id: int
    debate_id: int
    judge_model: str
    judge_provider: str
    winner_id: str
    winner_margin: float
    overall_feedback: str | None
    reasoning: str | None
    generation_time_ms: int | None
    cost: float | None
    generation_id: str | None
    cost_queried_at: str | None
    created_at: str


class CriterionScoreRow(TypedDict):
    """Row from criterion_scores table (SELECT *)."""

    id: int
    judge_decision_id: int
    criterion: str
    participant_id: str
    score: float
    feedback: str | None


class EnsembleSummaryRow(TypedDict):
    """Row from ensemble_summary table (SELECT *)."""

    id: int
    debate_id: int
    final_winner_id: str
    final_margin: float
    ensemble_method: str
    num_judges: int
    consensus_level: float | None
    summary_reasoning: str | None
    summary_feedback: str | None
    participating_judge_decision_ids: str | None  # CSV string
    created_at: str


class TranscriptListRow(TypedDict):
    """Row from list_transcripts query (subset of debates table)."""

    id: int
    topic: str
    format: str
    message_count: int
    created_at: str


class _JudgeDecisionWithScoresBase(JudgeDecisionRow):
    """Base for JudgeDecisionWithScores with additional fields."""

    criterion_scores: list[CriterionScoreRow]
    metadata: dict[str, str]  # Contains judge_model


# Type alias for cleaner code - represents complete judge decision data
JudgeDecisionWithScores = _JudgeDecisionWithScoresBase


class TranscriptData(TypedDict):
    """Full transcript with metadata and messages."""

    metadata: DebateRow
    messages: list[MessageRow]
