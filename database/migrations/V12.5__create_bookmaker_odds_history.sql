-- =============================================================================
-- V12.5 Database Migration: Create bookmaker_odds_history
-- =============================================================================
-- 目标:
--   为“人工辅助 + 本地半自动清洗”路线提供正式赔率时序仓，保存开盘、终盘与变盘轨迹。
-- =============================================================================

CREATE TABLE IF NOT EXISTS bookmaker_odds_history (
    id SERIAL PRIMARY KEY,
    match_id VARCHAR(255) NOT NULL REFERENCES matches(match_id) ON DELETE CASCADE,
    bookmaker_name VARCHAR(100) NOT NULL,
    market_type VARCHAR(50) NOT NULL,
    open_odds JSONB NOT NULL DEFAULT '{}'::jsonb,
    close_odds JSONB NOT NULL DEFAULT '{}'::jsonb,
    movement_trajectory JSONB NOT NULL DEFAULT '[]'::jsonb,
    alignment_meta JSONB NOT NULL DEFAULT '{}'::jsonb,
    source_html_path TEXT,
    source_digest VARCHAR(64),
    collected_at TIMESTAMP DEFAULT NOW(),
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    CONSTRAINT bookmaker_odds_history_unique_market
        UNIQUE (match_id, bookmaker_name, market_type),
    CONSTRAINT bookmaker_odds_history_open_is_object
        CHECK (jsonb_typeof(open_odds) = 'object'),
    CONSTRAINT bookmaker_odds_history_close_is_object
        CHECK (jsonb_typeof(close_odds) = 'object'),
    CONSTRAINT bookmaker_odds_history_trajectory_is_array
        CHECK (jsonb_typeof(movement_trajectory) = 'array'),
    CONSTRAINT bookmaker_odds_history_alignment_meta_is_object
        CHECK (jsonb_typeof(alignment_meta) = 'object')
);

CREATE INDEX IF NOT EXISTS idx_bookmaker_odds_history_match
ON bookmaker_odds_history(match_id);

CREATE INDEX IF NOT EXISTS idx_bookmaker_odds_history_bookmaker
ON bookmaker_odds_history(bookmaker_name);

CREATE INDEX IF NOT EXISTS idx_bookmaker_odds_history_market
ON bookmaker_odds_history(market_type);

CREATE INDEX IF NOT EXISTS idx_bookmaker_odds_history_collected_at
ON bookmaker_odds_history(collected_at DESC);

CREATE OR REPLACE FUNCTION update_bookmaker_odds_history_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trigger_update_bookmaker_odds_history_timestamp
ON bookmaker_odds_history;

CREATE TRIGGER trigger_update_bookmaker_odds_history_timestamp
    BEFORE UPDATE ON bookmaker_odds_history
    FOR EACH ROW
    EXECUTE FUNCTION update_bookmaker_odds_history_updated_at();

COMMENT ON TABLE bookmaker_odds_history IS
'V12.5: 本地离线 ETL 赔率时序仓，保存 bookmaker / market 的开终盘与变盘轨迹';

COMMENT ON COLUMN bookmaker_odds_history.open_odds IS
'V12.5: 开盘快照，推荐存为 JSON object，例如 {"home":2.10,"draw":3.20,"away":3.55}';

COMMENT ON COLUMN bookmaker_odds_history.close_odds IS
'V12.5: 终盘快照，推荐存为 JSON object';

COMMENT ON COLUMN bookmaker_odds_history.movement_trajectory IS
'V12.5: 变盘轨迹，推荐存为 JSON array，元素包含 captured_at 与赔率快照';

COMMENT ON COLUMN bookmaker_odds_history.alignment_meta IS
'V12.8: Football-Data CSV 对齐到 FotMob 基座的审计证据，记录 match_score / name_similarity / time_diff_seconds';
