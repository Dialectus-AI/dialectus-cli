"""Simplified SQLite database for CLI transcript storage (no users/auth/tournaments)."""

import sqlite3
import json
import logging
from pathlib import Path
from typing import Any

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

    def _ensure_schema(self) -> None:
        """Create database schema if it doesn't exist."""
        conn = sqlite3.connect(self.db_path)
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

    def save_debate(self, transcript_data: dict[str, Any]) -> int:
        """Save debate transcript and messages. Returns debate ID."""
        conn = sqlite3.connect(self.db_path)
        try:
            cursor = conn.cursor()

            # Extract metadata
            metadata = transcript_data["metadata"]

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
                    metadata["topic"],
                    metadata["format"],
                    json.dumps(metadata["participants"]),
                    metadata["final_phase"],
                    metadata["total_rounds"],
                    metadata["saved_at"],
                    metadata["message_count"],
                    metadata["word_count"],
                    metadata["total_debate_time_ms"],
                    json.dumps(metadata),
                ),
            )

            debate_id = cursor.lastrowid

            if debate_id is None:
                raise RuntimeError("Failed to determine debate_id for saved transcript.")

            # Insert messages
            for message in transcript_data["messages"]:
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
                        message["speaker_id"],
                        message["position"],
                        message["phase"],
                        message["round_number"],
                        message["content"],
                        message["timestamp"],
                        message["word_count"],
                        json.dumps(message.get("metadata", {})),
                        message.get("cost"),
                        message.get("generation_id"),
                        message.get("cost_queried_at"),
                    ),
                )

            conn.commit()
            logger.info(f"Saved debate transcript with ID {debate_id}")
            return debate_id

        finally:
            conn.close()

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
        conn = sqlite3.connect(self.db_path)
        try:
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
                raise RuntimeError("Failed to determine judge decision ID after insert.")
            conn.commit()
            logger.info(f"Saved judge decision with ID {decision_id}")
            return decision_id

        finally:
            conn.close()

    def save_criterion_scores(
        self, decision_id: int, criterion_data: list[dict[str, Any]]
    ) -> None:
        """Save criterion scores for a judge decision."""
        conn = sqlite3.connect(self.db_path)
        try:
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

            conn.commit()
            logger.info(f"Saved {len(criterion_data)} criterion scores")

        finally:
            conn.close()

    def save_ensemble_summary(
        self, debate_id: int, ensemble_data: dict[str, Any]
    ) -> int:
        """Save ensemble summary. Returns summary ID."""
        conn = sqlite3.connect(self.db_path)
        try:
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
                    ensemble_data["final_winner_id"],
                    ensemble_data["final_margin"],
                    ensemble_data.get("ensemble_method", "majority"),
                    ensemble_data["num_judges"],
                    ensemble_data.get("consensus_level"),
                    ensemble_data.get("summary_reasoning"),
                    ensemble_data.get("summary_feedback"),
                    ensemble_data.get("participating_judge_decision_ids"),
                ),
            )

            summary_id = cursor.lastrowid

            if summary_id is None:
                raise RuntimeError("Failed to determine ensemble summary ID after insert.")
            conn.commit()
            logger.info(f"Saved ensemble summary with ID {summary_id}")
            return summary_id

        finally:
            conn.close()

    def list_transcripts(
        self, limit: int = 20, offset: int = 0
    ) -> list[dict[str, Any]]:
        """List debate transcripts (metadata only)."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
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
            return [dict(row) for row in rows]

        finally:
            conn.close()

    def load_transcript(self, debate_id: int) -> dict[str, Any] | None:
        """Load full debate transcript including messages."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            cursor = conn.cursor()

            # Get debate metadata
            cursor.execute("SELECT * FROM debates WHERE id = ?", (debate_id,))
            debate_row = cursor.fetchone()

            if not debate_row:
                return None

            debate = dict(debate_row)

            # Get messages
            cursor.execute(
                """
                SELECT * FROM messages
                WHERE debate_id = ?
                ORDER BY round_number, id
                """,
                (debate_id,),
            )
            messages = [dict(row) for row in cursor.fetchall()]

            return {"metadata": debate, "messages": messages}

        finally:
            conn.close()

    def load_judge_decision(self, debate_id: int) -> dict[str, Any] | None:
        """Load judge decision (single judge case)."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            cursor = conn.cursor()

            # Get decision
            cursor.execute(
                "SELECT * FROM judge_decisions WHERE debate_id = ? LIMIT 1",
                (debate_id,),
            )
            decision_row = cursor.fetchone()

            if not decision_row:
                return None

            decision = dict(decision_row)

            # Get criterion scores
            cursor.execute(
                """
                SELECT * FROM criterion_scores
                WHERE judge_decision_id = ?
                """,
                (decision["id"],),
            )
            criterion_scores = [dict(row) for row in cursor.fetchall()]

            decision["criterion_scores"] = criterion_scores
            decision["metadata"] = {"judge_model": decision["judge_model"]}

            return decision

        finally:
            conn.close()

    def load_judge_decisions(self, debate_id: int) -> list[dict[str, Any]]:
        """Load all judge decisions for a debate (ensemble case)."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            cursor = conn.cursor()

            # Get all decisions
            cursor.execute(
                "SELECT * FROM judge_decisions WHERE debate_id = ?", (debate_id,)
            )
            decisions = [dict(row) for row in cursor.fetchall()]

            # Get criterion scores for each decision
            for decision in decisions:
                cursor.execute(
                    """
                    SELECT * FROM criterion_scores
                    WHERE judge_decision_id = ?
                    """,
                    (decision["id"],),
                )
                decision["criterion_scores"] = [dict(row) for row in cursor.fetchall()]
                decision["metadata"] = {"judge_model": decision["judge_model"]}

            return decisions

        finally:
            conn.close()

    def load_ensemble_summary(self, debate_id: int) -> dict[str, Any] | None:
        """Load ensemble summary."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            cursor = conn.cursor()

            cursor.execute(
                "SELECT * FROM ensemble_summary WHERE debate_id = ?", (debate_id,)
            )
            row = cursor.fetchone()

            return dict(row) if row else None

        finally:
            conn.close()
