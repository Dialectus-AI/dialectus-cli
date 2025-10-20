"""Simplified SQLite database for CLI transcript storage (no users/auth/tournaments)."""

import sqlite3
import json
import logging
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Generator

from dialectus.cli.db_types import (
    CriterionScoreRow,
    DebateNotFoundError,
    DebateRow,
    DebateTranscriptData,
    EnsembleSummaryData,
    EnsembleSummaryNotFoundError,
    EnsembleSummaryRow,
    JudgeDecisionNotFoundError,
    JudgeDecisionWithScores,
    MessageRow,
    TranscriptData,
    TranscriptListRow,
)

logger = logging.getLogger(__name__)


def get_database_path() -> Path:
    """Get the database path (in user's home directory)."""
    db_dir = Path.home() / ".dialectus"
    db_dir.mkdir(parents=True, exist_ok=True)
    return db_dir / "debates.db"


class DatabaseManager:
    """Simplified database manager for CLI transcript storage."""

    def __init__(self, db_path: str | None = None):
        self.db_path = db_path or str(get_database_path())
        self._ensure_schema()

    @contextmanager
    def get_connection(
        self, read_only: bool = False
    ) -> Generator[sqlite3.Connection, None, None]:
        """Context manager for database connections with automatic commit/rollback."""
        if read_only:
            db_uri = f"file:{Path(self.db_path).resolve().as_posix()}?mode=ro"
            conn = sqlite3.connect(db_uri, uri=True)
            conn.row_factory = sqlite3.Row
        else:
            conn = sqlite3.connect(self.db_path)

        conn.execute("PRAGMA foreign_keys = ON")
        try:
            yield conn
            if not read_only:
                conn.commit()
        except Exception:
            if not read_only:
                conn.rollback()
            raise
        finally:
            conn.close()

    def _ensure_schema(self) -> None:
        """Create database schema if it doesn't exist."""
        conn = sqlite3.connect(self.db_path)
        conn.execute("PRAGMA foreign_keys = ON")
        try:
            # Read and execute schema from schema.sql
            schema_path = Path(__file__).parent / "schema.sql"
            if schema_path.exists():
                with open(schema_path, encoding="utf-8") as f:
                    schema_sql = f.read()
                conn.executescript(schema_sql)
            else:
                raise RuntimeError(f"Database schema file not found: {schema_path}")

            conn.commit()
            logger.info(f"Database schema initialized at {self.db_path}")
        finally:
            conn.close()

    def save_debate(self, transcript_data: DebateTranscriptData) -> int:
        """Save debate transcript and messages. Returns debate ID."""
        with self.get_connection() as conn:
            cursor = conn.cursor()

            # Extract metadata
            metadata = transcript_data.metadata

            # Insert debate record
            cursor.execute(
                """
                INSERT INTO debates (
                    topic, format, participants, final_phase, total_rounds,
                    saved_at, message_count, word_count, total_debate_time_ms,
                    context_metadata
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    metadata.topic,
                    metadata.format,
                    json.dumps(
                        {k: v.model_dump() for k, v in metadata.participants.items()}
                    ),
                    metadata.final_phase,
                    metadata.total_rounds,
                    metadata.saved_at,
                    metadata.message_count,
                    metadata.word_count,
                    metadata.total_debate_time_ms,
                    json.dumps(metadata.model_dump()),
                ),
            )

            debate_id = cursor.lastrowid

            if debate_id is None:
                raise RuntimeError(
                    "Failed to determine debate_id for saved transcript."
                )

            # Insert messages
            for message in transcript_data.messages:
                cursor.execute(
                    """
                    INSERT INTO messages (
                        debate_id, speaker_id, position, phase, round_number,
                        content, timestamp, word_count, metadata, cost,
                        generation_id, cost_queried_at
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        debate_id,
                        message.speaker_id,
                        message.position,
                        message.phase,
                        message.round_number,
                        message.content,
                        message.timestamp,
                        message.word_count,
                        json.dumps(message.metadata or {}),
                        message.cost,
                        message.generation_id,
                        message.cost_queried_at,
                    ),
                )

            logger.info(f"Saved debate transcript with ID {debate_id}")
            return debate_id

    def save_judge_decision(
        self,
        debate_id: int,
        winner_id: str,
        winner_margin: float,
        overall_feedback: str | None,
        reasoning: str | None,
        judge_model: str,
        judge_provider: str,
        generation_time_ms: int | None = None,
        cost: float | None = None,
        generation_id: str | None = None,
        cost_queried_at: str | None = None,
    ) -> int:
        """Save judge decision. Returns decision ID."""
        with self.get_connection() as conn:
            cursor = conn.cursor()

            cursor.execute(
                """
                INSERT INTO judge_decisions (
                    debate_id, judge_model, judge_provider, winner_id,
                    winner_margin, overall_feedback, reasoning,
                    generation_time_ms, cost, generation_id, cost_queried_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    debate_id,
                    judge_model,
                    judge_provider,
                    winner_id,
                    winner_margin,
                    overall_feedback,
                    reasoning,
                    generation_time_ms,
                    cost,
                    generation_id,
                    cost_queried_at,
                ),
            )

            decision_id = cursor.lastrowid

            if decision_id is None:
                raise RuntimeError(
                    "Failed to determine judge decision ID after insert."
                )
            logger.info(f"Saved judge decision with ID {decision_id}")
            return decision_id

    def save_criterion_scores(
        self, decision_id: int, criterion_data: list[dict[str, Any]]
    ) -> None:
        """Save criterion scores for a judge decision."""
        with self.get_connection() as conn:
            cursor = conn.cursor()

            for score in criterion_data:
                cursor.execute(
                    """
                    INSERT INTO criterion_scores (
                        judge_decision_id, criterion, participant_id, score, feedback
                    )
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    (
                        decision_id,
                        score["criterion"],
                        score["participant_id"],
                        score["score"],
                        score.get("feedback"),
                    ),
                )

            logger.info(f"Saved {len(criterion_data)} criterion scores")

    def save_ensemble_summary(
        self, debate_id: int, ensemble_data: EnsembleSummaryData
    ) -> int:
        """Save ensemble summary. Returns summary ID."""
        with self.get_connection() as conn:
            cursor = conn.cursor()

            cursor.execute(
                """
                INSERT INTO ensemble_summary (
                    debate_id, final_winner_id, final_margin, ensemble_method,
                    num_judges, consensus_level, summary_reasoning,
                    summary_feedback, participating_judge_decision_ids
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    debate_id,
                    ensemble_data.final_winner_id,
                    ensemble_data.final_margin,
                    ensemble_data.ensemble_method,
                    ensemble_data.num_judges,
                    ensemble_data.consensus_level,
                    ensemble_data.summary_reasoning,
                    ensemble_data.summary_feedback,
                    ensemble_data.participating_judge_decision_ids,
                ),
            )

            summary_id = cursor.lastrowid

            if summary_id is None:
                raise RuntimeError(
                    "Failed to determine ensemble summary ID after insert."
                )
            logger.info(f"Saved ensemble summary with ID {summary_id}")
            return summary_id

    def list_transcripts(
        self, limit: int = 20, offset: int = 0
    ) -> list[TranscriptListRow]:
        """List debate transcripts (metadata only)."""
        with self.get_connection(read_only=True) as conn:
            cursor = conn.cursor()

            cursor.execute(
                """
                SELECT id, topic, format, message_count, created_at
                FROM debates
                ORDER BY created_at DESC
                LIMIT ? OFFSET ?
                """,
                (limit, offset),
            )

            rows = cursor.fetchall()
            return [TranscriptListRow.model_validate(dict(row)) for row in rows]

    def load_transcript(self, debate_id: int) -> TranscriptData:
        """Load full debate transcript including messages.

        Raises:
            DebateNotFoundError: If debate_id does not exist.
        """
        with self.get_connection(read_only=True) as conn:
            cursor = conn.cursor()

            # Get debate metadata
            cursor.execute("SELECT * FROM debates WHERE id = ?", (debate_id,))
            debate_row = cursor.fetchone()

            if not debate_row:
                raise DebateNotFoundError(debate_id)

            debate = DebateRow.model_validate(dict(debate_row))

            # Get messages
            cursor.execute(
                """
                SELECT * FROM messages
                WHERE debate_id = ?
                ORDER BY round_number, id
                """,
                (debate_id,),
            )
            messages = [MessageRow.model_validate(dict(row)) for row in cursor.fetchall()]

            return TranscriptData(metadata=debate, messages=messages)

    def load_judge_decision(self, debate_id: int) -> JudgeDecisionWithScores:
        """Load judge decision (single judge case).

        Raises:
            JudgeDecisionNotFoundError: If no judge decision exists for debate_id.
        """
        with self.get_connection(read_only=True) as conn:
            cursor = conn.cursor()

            # Get decision
            cursor.execute(
                "SELECT * FROM judge_decisions WHERE debate_id = ? LIMIT 1",
                (debate_id,),
            )
            decision_row = cursor.fetchone()

            if not decision_row:
                raise JudgeDecisionNotFoundError(debate_id)

            decision_dict = dict(decision_row)

            # Get criterion scores
            cursor.execute(
                """
                SELECT * FROM criterion_scores
                WHERE judge_decision_id = ?
                """,
                (decision_dict["id"],),
            )
            criterion_scores = [
                CriterionScoreRow.model_validate(dict(row)) for row in cursor.fetchall()
            ]

            # Build the complete result
            return JudgeDecisionWithScores.model_validate({
                **decision_dict,
                "criterion_scores": criterion_scores,
                "metadata": {"judge_model": decision_dict["judge_model"]},
            })

    def load_judge_decisions(self, debate_id: int) -> list[JudgeDecisionWithScores]:
        """Load all judge decisions for a debate (ensemble case).

        Returns:
            List of judge decisions with criterion scores. Returns empty list
            if no decisions exist (ensemble may not have been run yet).
        """
        with self.get_connection(read_only=True) as conn:
            cursor = conn.cursor()

            # Get all decisions
            cursor.execute(
                "SELECT * FROM judge_decisions WHERE debate_id = ?", (debate_id,)
            )
            decision_rows = [dict(row) for row in cursor.fetchall()]

            # Get criterion scores for each decision
            results: list[JudgeDecisionWithScores] = []
            for decision_dict in decision_rows:
                cursor.execute(
                    """
                    SELECT * FROM criterion_scores
                    WHERE judge_decision_id = ?
                    """,
                    (decision_dict["id"],),
                )
                criterion_scores = [
                    CriterionScoreRow.model_validate(dict(row)) for row in cursor.fetchall()
                ]

                result = JudgeDecisionWithScores.model_validate({
                    **decision_dict,
                    "criterion_scores": criterion_scores,
                    "metadata": {"judge_model": decision_dict["judge_model"]},
                })
                results.append(result)

            return results

    def load_ensemble_summary(self, debate_id: int) -> EnsembleSummaryRow:
        """Load ensemble summary.

        Raises:
            EnsembleSummaryNotFoundError: If no ensemble summary exists for debate_id.
        """
        with self.get_connection(read_only=True) as conn:
            cursor = conn.cursor()

            cursor.execute(
                "SELECT * FROM ensemble_summary WHERE debate_id = ?", (debate_id,)
            )
            row = cursor.fetchone()

            if not row:
                raise EnsembleSummaryNotFoundError(debate_id)

            return EnsembleSummaryRow.model_validate(dict(row))
