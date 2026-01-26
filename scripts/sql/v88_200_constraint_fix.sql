-- ============================================================================
-- V88.200 Database Constraint Alignment
-- ============================================================================
-- Purpose: Align database unique indexes with code-level ON CONFLICT clauses
--
-- Context: High-concurrency data persistence testing revealed mismatches
-- between database constraints and UPSERT logic in storage.js
--
-- Usage: psql -U football_user -d football_db -f scripts/sql/v88_200_constraint_fix.sql
-- ============================================================================

-- ============================================================================
-- 1. entities_mapping Table Index
-- ============================================================================
-- Corresponds to: getOrCreateEntity() ON CONFLICT clause (line 160)
-- Fields: source_system, source_id, entity_type

DO $$
BEGIN
    -- Drop existing index if exists (idempotent)
    DROP INDEX IF EXISTS entities_mapping_source_unique;

    -- Create unique index
    CREATE UNIQUE INDEX entities_mapping_source_unique
        ON entities_mapping (source_system, source_id, entity_type);

    RAISE NOTICE '[V88.200] Index created: entities_mapping_source_unique';
END $$;

-- ============================================================================
-- 2. temporal_metric_records Table Index (Scenario 1)
-- ============================================================================
-- Corresponds to: upsertTemporalRecords() ON CONFLICT clause (line 232)
-- Fields: entity_id, provider_name, metric_type, occurred_at

DO $$
BEGIN
    -- Drop existing index if exists (idempotent)
    DROP INDEX IF EXISTS temporal_metric_records_basic_unique;

    -- Create unique index for basic temporal records
    CREATE UNIQUE INDEX temporal_metric_records_basic_unique
        ON temporal_metric_records (entity_id, provider_name, metric_type, occurred_at);

    RAISE NOTICE '[V88.200] Index created: temporal_metric_records_basic_unique';
END $$;

-- ============================================================================
-- 3. temporal_metric_records Table Index (Scenario 2)
-- ============================================================================
-- Corresponds to: upsertFullTemporalRecords() ON CONFLICT clause (line 449)
-- Fields: entity_id, provider_name, occurred_at, dimension, sequence

DO $$
BEGIN
    -- Drop existing index if exists (idempotent)
    DROP INDEX IF EXISTS temporal_metric_records_full_spectrum_unique;

    -- Create unique index for full-spectrum temporal records (V49.000)
    CREATE UNIQUE INDEX temporal_metric_records_full_spectrum_unique
        ON temporal_metric_records (entity_id, provider_name, occurred_at, dimension, sequence);

    RAISE NOTICE '[V88.200] Index created: temporal_metric_records_full_spectrum_unique';
END $$;

-- ============================================================================
-- Verification Queries
-- ============================================================================

-- Verify indexes exist
SELECT
    indexname,
    tablename,
    indexdef
FROM pg_indexes
WHERE tablename IN ('entities_mapping', 'temporal_metric_records')
    AND indexname LIKE '%unique%'
ORDER BY tablename, indexname;

-- Expected output:
-- indexname                              | tablename                 | indexdef
-- --------------------------------------|---------------------------|----------
-- entities_mapping_source_unique        | entities_mapping          | ...
-- temporal_metric_records_basic_unique  | temporal_metric_records  | ...
-- temporal_metric_records_full_spectrum_unique | temporal_metric_records | ...

RAISE NOTICE '[V88.200] All database indexes aligned successfully!';
