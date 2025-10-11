-- ============================================
-- DEBATE TABLES
-- ============================================

CREATE TABLE IF NOT EXISTS debates (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    topic TEXT NOT NULL,
    format TEXT NOT NULL,
    participants TEXT NOT NULL,  -- JSON string
    final_phase TEXT NOT NULL,
    total_rounds INTEGER NOT NULL,
    saved_at TEXT NOT NULL,
    message_count INTEGER NOT NULL,
    word_count INTEGER NOT NULL,
    total_debate_time_ms INTEGER NOT NULL,
    scores TEXT,  -- JSON string
    context_metadata TEXT,  -- JSON string
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS messages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    debate_id INTEGER NOT NULL,
    speaker_id TEXT NOT NULL,
    position TEXT NOT NULL,
    phase TEXT NOT NULL,
    round_number INTEGER NOT NULL,
    content TEXT NOT NULL,
    timestamp TEXT NOT NULL,
    word_count INTEGER NOT NULL,
    metadata TEXT,  -- JSON string
    cost REAL,
    generation_id TEXT,
    cost_queried_at DATETIME,
    FOREIGN KEY (debate_id) REFERENCES debates (id) ON DELETE CASCADE
);

-- ============================================
-- JUDGING TABLES
-- ============================================

CREATE TABLE IF NOT EXISTS judge_decisions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    debate_id INTEGER NOT NULL,
    judge_model TEXT NOT NULL,
    judge_provider TEXT NOT NULL,
    winner_id TEXT NOT NULL,
    winner_margin REAL NOT NULL,
    overall_feedback TEXT,
    reasoning TEXT,
    generation_time_ms INTEGER,
    cost REAL,
    generation_id TEXT,
    cost_queried_at DATETIME,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (debate_id) REFERENCES debates(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS criterion_scores (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    judge_decision_id INTEGER NOT NULL,
    criterion TEXT NOT NULL,
    participant_id TEXT NOT NULL,
    score REAL NOT NULL,
    feedback TEXT,
    FOREIGN KEY (judge_decision_id) REFERENCES judge_decisions (id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS ensemble_summary (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    debate_id INTEGER NOT NULL UNIQUE,
    final_winner_id TEXT NOT NULL,
    final_margin REAL NOT NULL,
    ensemble_method TEXT NOT NULL DEFAULT 'majority',
    num_judges INTEGER NOT NULL,
    consensus_level REAL,
    summary_reasoning TEXT,
    summary_feedback TEXT,
    participating_judge_decision_ids TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (debate_id) REFERENCES debates(id) ON DELETE CASCADE
);

-- ============================================
-- INDEXES FOR PERFORMANCE
-- ============================================

CREATE INDEX IF NOT EXISTS idx_messages_debate_id ON messages (debate_id);
CREATE INDEX IF NOT EXISTS idx_messages_round_phase ON messages (debate_id, round_number, phase);
CREATE INDEX IF NOT EXISTS idx_judge_decisions_debate_id ON judge_decisions (debate_id);
CREATE INDEX IF NOT EXISTS idx_criterion_scores_decision_id ON criterion_scores (judge_decision_id);
CREATE INDEX IF NOT EXISTS idx_ensemble_summary_debate_id ON ensemble_summary (debate_id);
