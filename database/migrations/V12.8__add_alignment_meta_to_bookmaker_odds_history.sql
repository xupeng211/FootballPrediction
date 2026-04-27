-- =============================================================================
-- V12.8 Database Migration: Add alignment_meta to bookmaker_odds_history
-- =============================================================================

ALTER TABLE bookmaker_odds_history
ADD COLUMN IF NOT EXISTS alignment_meta JSONB NOT NULL DEFAULT '{}'::jsonb;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM pg_constraint
        WHERE conname = 'bookmaker_odds_history_alignment_meta_is_object'
    ) THEN
        ALTER TABLE bookmaker_odds_history
        ADD CONSTRAINT bookmaker_odds_history_alignment_meta_is_object
            CHECK (jsonb_typeof(alignment_meta) = 'object');
    END IF;
END $$;

COMMENT ON COLUMN bookmaker_odds_history.alignment_meta IS
'V12.8: Football-Data CSV 对齐到 FotMob 基座的审计证据，记录 match_score / name_similarity / time_diff_seconds';
