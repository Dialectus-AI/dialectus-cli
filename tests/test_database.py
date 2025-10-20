"""Tests for database layer (SQLite operations and data persistence)."""

import sqlite3
from typing import Any

import pytest

from dialectus.cli.database import DatabaseManager
from dialectus.cli.db_types import DebateTranscriptData, EnsembleSummaryData


class TestDatabaseManager:
    def test_database_initialization(self, temp_db: str):
        db = DatabaseManager(db_path=temp_db)
        assert db.db_path == temp_db

    def test_schema_creation(self, temp_db: str):
        DatabaseManager(db_path=temp_db)

        with DatabaseManager(db_path=temp_db).get_connection(read_only=True) as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
            )
            tables = [row[0] for row in cursor.fetchall()]

            assert "debates" in tables
            assert "messages" in tables
            assert "judge_decisions" in tables
            assert "criterion_scores" in tables
            assert "ensemble_summary" in tables

    def test_save_and_load_debate(
        self, temp_db: str, sample_debate_data: DebateTranscriptData
    ):
        db = DatabaseManager(db_path=temp_db)
        debate_id = db.save_debate(sample_debate_data)

        assert debate_id > 0

        loaded = db.load_transcript(debate_id)
        assert loaded is not None
        assert loaded.metadata.topic == "Should AI be regulated?"
        assert loaded.metadata.format == "oxford"
        assert len(loaded.messages) == 2

    def test_list_transcripts(
        self, temp_db: str, sample_debate_data: DebateTranscriptData
    ):
        db = DatabaseManager(db_path=temp_db)

        debate_id_1 = db.save_debate(sample_debate_data)
        debate_id_2 = db.save_debate(sample_debate_data)

        transcripts = db.list_transcripts(limit=10)
        assert len(transcripts) == 2
        assert {transcripts[0].id, transcripts[1].id} == {
            debate_id_1,
            debate_id_2,
        }

    def test_list_transcripts_with_limit(
        self, temp_db: str, sample_debate_data: DebateTranscriptData
    ):
        db = DatabaseManager(db_path=temp_db)

        for _ in range(5):
            db.save_debate(sample_debate_data)

        transcripts = db.list_transcripts(limit=3)
        assert len(transcripts) == 3

    def test_list_transcripts_with_offset(
        self, temp_db: str, sample_debate_data: DebateTranscriptData
    ):
        db = DatabaseManager(db_path=temp_db)

        ids = [db.save_debate(sample_debate_data) for _ in range(5)]

        transcripts = db.list_transcripts(limit=2, offset=2)
        assert len(transcripts) == 2
        transcript_ids = {t.id for t in transcripts}
        assert transcript_ids.issubset(set(ids))

    def test_load_nonexistent_transcript(self, temp_db: str):
        from dialectus.cli.db_types import DebateNotFoundError

        db = DatabaseManager(db_path=temp_db)
        with pytest.raises(DebateNotFoundError):
            db.load_transcript(99999)

    def test_save_judge_decision(
        self,
        temp_db: str,
        sample_debate_data: DebateTranscriptData,
        sample_judge_decision: dict[str, Any],
    ):
        db = DatabaseManager(db_path=temp_db)
        debate_id = db.save_debate(sample_debate_data)

        decision_id = db.save_judge_decision(
            debate_id=debate_id, **sample_judge_decision
        )

        assert decision_id > 0

        loaded = db.load_judge_decision(debate_id)
        assert loaded is not None
        assert loaded.winner_id == "model_a"
        assert loaded.winner_margin == 2.5
        assert loaded.judge_model == "openthinker:7b"

    def test_save_criterion_scores(
        self,
        temp_db: str,
        sample_debate_data: DebateTranscriptData,
        sample_judge_decision: dict[str, Any],
        sample_criterion_scores: list[dict[str, Any]],
    ):
        db = DatabaseManager(db_path=temp_db)
        debate_id = db.save_debate(sample_debate_data)
        decision_id = db.save_judge_decision(
            debate_id=debate_id, **sample_judge_decision
        )

        db.save_criterion_scores(decision_id, sample_criterion_scores)

        loaded = db.load_judge_decision(debate_id)
        assert loaded is not None
        assert len(loaded.criterion_scores) == 4
        assert loaded.criterion_scores[0].criterion == "logic"
        assert loaded.criterion_scores[0].participant_id == "model_a"
        assert loaded.criterion_scores[0].score == 8.5

    def test_save_ensemble_summary(
        self, temp_db: str, sample_debate_data: DebateTranscriptData
    ):
        db = DatabaseManager(db_path=temp_db)
        debate_id = db.save_debate(sample_debate_data)

        ensemble_data = EnsembleSummaryData(
            final_winner_id="model_a",
            final_margin=3.2,
            ensemble_method="majority",
            num_judges=3,
            consensus_level=0.85,
            summary_reasoning="Unanimous decision based on evidence.",
            summary_feedback="Strong performance across all criteria.",
            participating_judge_decision_ids="1,2,3",
        )

        ensemble_id = db.save_ensemble_summary(debate_id, ensemble_data)
        assert ensemble_id > 0

        loaded = db.load_ensemble_summary(debate_id)
        assert loaded is not None
        assert loaded.final_winner_id == "model_a"
        assert loaded.final_margin == 3.2
        assert loaded.num_judges == 3
        assert loaded.consensus_level == 0.85

    def test_load_judge_decisions_multiple(
        self,
        temp_db: str,
        sample_debate_data: DebateTranscriptData,
        sample_judge_decision: dict[str, Any],
        sample_criterion_scores: list[dict[str, Any]],
    ):
        db = DatabaseManager(db_path=temp_db)
        debate_id = db.save_debate(sample_debate_data)

        decision_id_1 = db.save_judge_decision(
            debate_id=debate_id, **sample_judge_decision
        )
        db.save_criterion_scores(decision_id_1, sample_criterion_scores[:2])

        decision_id_2 = db.save_judge_decision(
            debate_id=debate_id, **sample_judge_decision
        )
        db.save_criterion_scores(decision_id_2, sample_criterion_scores[2:])

        decisions = db.load_judge_decisions(debate_id)
        assert len(decisions) == 2
        assert len(decisions[0].criterion_scores) == 2
        assert len(decisions[1].criterion_scores) == 2

    def test_foreign_key_constraint(
        self, temp_db: str, sample_judge_decision: dict[str, Any]
    ):
        db = DatabaseManager(db_path=temp_db)

        with pytest.raises(sqlite3.IntegrityError):
            db.save_judge_decision(debate_id=99999, **sample_judge_decision)

    def test_read_only_connection_disallows_writes(
        self, temp_db: str, sample_debate_data: DebateTranscriptData
    ):
        db = DatabaseManager(db_path=temp_db)
        db.save_debate(sample_debate_data)

        with db.get_connection(read_only=True) as conn:
            with pytest.raises(sqlite3.OperationalError):
                conn.execute("DELETE FROM debates")

    def test_message_storage_preserves_metadata(
        self, temp_db: str, sample_debate_data: DebateTranscriptData
    ):
        db = DatabaseManager(db_path=temp_db)

        sample_debate_data.messages[0].metadata = {"custom_field": "test_value"}
        debate_id = db.save_debate(sample_debate_data)

        loaded = db.load_transcript(debate_id)
        assert loaded is not None
        assert loaded.messages[0].speaker_id == "model_a"

    def test_empty_database_list_transcripts(self, temp_db: str):
        db = DatabaseManager(db_path=temp_db)
        transcripts = db.list_transcripts()
        assert transcripts == []

    def test_load_nonexistent_judge_decision(self, temp_db: str):
        from dialectus.cli.db_types import JudgeDecisionNotFoundError

        db = DatabaseManager(db_path=temp_db)
        with pytest.raises(JudgeDecisionNotFoundError):
            db.load_judge_decision(99999)

    def test_load_nonexistent_ensemble_summary(self, temp_db: str):
        from dialectus.cli.db_types import EnsembleSummaryNotFoundError

        db = DatabaseManager(db_path=temp_db)
        with pytest.raises(EnsembleSummaryNotFoundError):
            db.load_ensemble_summary(99999)
