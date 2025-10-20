"""Type-safe models for database row returns.

These Pydantic models match the exact schema from schema.sql, ensuring
type-safe access to database query results throughout the CLI.
"""

from typing import Any

from pydantic import BaseModel, ConfigDict


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


class DebateRow(BaseModel):
    """Row from debates table (SELECT *)."""

    model_config = ConfigDict(extra="forbid")

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


class MessageRow(BaseModel):
    """Row from messages table (SELECT *)."""

    model_config = ConfigDict(extra="forbid")

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


class JudgeDecisionRow(BaseModel):
    """Row from judge_decisions table (SELECT *)."""

    model_config = ConfigDict(extra="forbid")

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


class CriterionScoreRow(BaseModel):
    """Row from criterion_scores table (SELECT *)."""

    model_config = ConfigDict(extra="forbid")

    id: int
    judge_decision_id: int
    criterion: str
    participant_id: str
    score: float
    feedback: str | None


class EnsembleSummaryRow(BaseModel):
    """Row from ensemble_summary table (SELECT *)."""

    model_config = ConfigDict(extra="forbid")

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


class TranscriptListRow(BaseModel):
    """Row from list_transcripts query (subset of debates table)."""

    model_config = ConfigDict(extra="forbid")

    id: int
    topic: str
    format: str
    message_count: int
    created_at: str


class JudgeDecisionWithScores(JudgeDecisionRow):
    """Complete judge decision data with criterion scores."""

    criterion_scores: list[CriterionScoreRow]
    metadata: dict[str, str]  # Contains judge_model


class ParticipantInfo(BaseModel):
    """Participant information for transcript metadata."""

    model_config = ConfigDict(extra="forbid")

    name: str
    personality: str


class DebateMetadata(BaseModel):
    """Metadata structure for saving a debate transcript.

    This is the 'metadata' field in DebateTranscriptData, containing
    all the debate-level information needed to populate the debates table.
    """

    model_config = ConfigDict(extra="forbid")

    topic: str
    format: str
    participants: dict[str, ParticipantInfo]  # participant_id -> info
    final_phase: str
    total_rounds: int
    saved_at: str  # ISO timestamp
    message_count: int
    word_count: int
    total_debate_time_ms: int


class MessageData(BaseModel):
    """Message structure for saving to database.

    This is an individual message in the 'messages' list of DebateTranscriptData.
    """

    model_config = ConfigDict(extra="forbid")

    speaker_id: str
    position: str
    phase: str
    round_number: int
    content: str
    timestamp: str  # ISO timestamp
    word_count: int
    metadata: dict[str, Any] | None = None
    cost: float | None = None
    generation_id: str | None = None
    cost_queried_at: str | None = None


class DebateTranscriptData(BaseModel):
    """Complete transcript data structure for saving a debate.

    This is the input to save_debate(), containing both metadata and messages.
    """

    model_config = ConfigDict(extra="forbid")

    metadata: DebateMetadata
    messages: list[MessageData]


class EnsembleSummaryData(BaseModel):
    """Data structure for saving ensemble summary to database.

    This is the input to save_ensemble_summary(), containing the fields
    needed to populate the ensemble_summary table.
    """

    model_config = ConfigDict(extra="forbid")

    final_winner_id: str
    final_margin: float
    ensemble_method: str
    num_judges: int
    consensus_level: float | None
    summary_reasoning: str | None
    summary_feedback: str | None
    participating_judge_decision_ids: str  # CSV string of decision IDs


class TranscriptData(BaseModel):
    """Full transcript with metadata and messages."""

    model_config = ConfigDict(extra="forbid")

    metadata: DebateRow
    messages: list[MessageRow]
