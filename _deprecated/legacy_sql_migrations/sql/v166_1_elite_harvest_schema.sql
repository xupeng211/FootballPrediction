
-- V166.1: Schema Upgrade for Elite Harvest
-- =========================================
-- Purpose: Add support for L3 trajectory and Market Payout
-- Date: 2026-02-02
-- Author: Genesis.SchemaUpgrade

-- 1. Add odds_history (JSONB) to store full trajectory
ALTER TABLE metrics_multi_source_data
ADD COLUMN IF NOT EXISTS odds_history JSONB;

-- 2. Add market_payout (Numeric) to store payout percentage
ALTER TABLE metrics_multi_source_data
ADD COLUMN IF NOT EXISTS market_payout NUMERIC(5,2);

-- 3. Add provider_internal_id (Integer) to store internal ID (18, 32, etc)
ALTER TABLE metrics_multi_source_data
ADD COLUMN IF NOT EXISTS provider_internal_id INTEGER;

-- 4. Create index on provider_internal_id for fast lookup
CREATE INDEX IF NOT EXISTS idx_multisource_provider_id 
ON metrics_multi_source_data(provider_internal_id);

-- 5. Comment on new columns
COMMENT ON COLUMN metrics_multi_source_data.odds_history IS 'Full L3 odds trajectory with timestamps';
COMMENT ON COLUMN metrics_multi_source_data.market_payout IS 'Real market payout percentage (e.g., 98.4)';
COMMENT ON COLUMN metrics_multi_source_data.provider_internal_id IS 'Internal Provider ID (18=Pinnacle, 32=bet365)';

-- Verification
SELECT column_name, data_type 
FROM information_schema.columns 
WHERE table_name = 'metrics_multi_source_data' 
AND column_name IN ('odds_history', 'market_payout', 'provider_internal_id');
