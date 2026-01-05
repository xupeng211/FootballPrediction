-- V57.4 Production Audit Fields Migration
-- This script adds missing production-grade audit fields to metrics_multi_source_data table
-- Required by OddsProductionExtractor.save_multi_source_data()

-- Migration Date: 2026-01-02
-- Author: V57.4 Repository Hardening

BEGIN;

-- 1. Add is_valid flag for data integrity validation
ALTER TABLE metrics_multi_source_data
ADD COLUMN IF NOT EXISTS is_valid BOOLEAN DEFAULT TRUE;

-- 2. Add validation_error to store failure reasons
ALTER TABLE metrics_multi_source_data
ADD COLUMN IF NOT EXISTS validation_error TEXT;

-- 3. Add fully_captured flag to indicate complete data (H/D/A all present)
ALTER TABLE metrics_multi_source_data
ADD COLUMN IF NOT EXISTS fully_captured BOOLEAN DEFAULT FALSE;

-- 4. Add data_timestamp for precise data collection timing
ALTER TABLE metrics_multi_source_data
ADD COLUMN IF NOT EXISTS data_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP;

-- 5. Create indexes for audit fields
CREATE INDEX IF NOT EXISTS idx_multisource_is_valid
ON metrics_multi_source_data(is_valid) WHERE is_valid IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_multisource_fully_captured
ON metrics_multi_source_data(fully_captured) WHERE fully_captured IS NOT NULL;

-- 6. Add comment for documentation
COMMENT ON COLUMN metrics_multi_source_data.is_valid IS 'V57.4: Data integrity validation flag (TRUE = passes 1.02 < Score < 1.08)';
COMMENT ON COLUMN metrics_multi_source_data.validation_error IS 'V57.4: Human-readable validation failure reason';
COMMENT ON COLUMN metrics_multi_source_data.fully_captured IS 'V57.4: All H/D/A odds captured (init + opening_time + final)';
COMMENT ON COLUMN metrics_multi_source_data.data_timestamp IS 'V57.4: Timestamp when odds data was harvested';

COMMIT;

-- Verification query (run separately to verify)
-- SELECT column_name, data_type, column_default
-- FROM information_schema.columns
-- WHERE table_name = 'metrics_multi_source_data'
-- AND column_name IN ('is_valid', 'validation_error', 'fully_captured', 'data_timestamp');
