-- V65.100 Diagnostic Query - Check BASELINE_V64 data structure
-- ================================================================

-- 1. Sample raw data structure
SELECT
    entity_id,
    provider_name,
    dimension,
    value,
    occurred_at,
    sequence,
    raw_data::text
FROM temporal_metric_records
WHERE raw_data::jsonb ->> 'baseline_tag' = 'BASELINE_V64'
ORDER BY entity_id, provider_name, dimension, sequence
LIMIT 10;

-- 2. Count records by entity and sequence
SELECT
    entity_id,
    COUNT(DISTINCT sequence) as unique_sequences,
    COUNT(*) as total_records,
    string_agg(DISTINCT dimension::text, ', ' ORDER BY dimension) as dimensions
FROM temporal_metric_records
WHERE raw_data::jsonb ->> 'baseline_tag' = 'BASELINE_V64'
GROUP BY entity_id
ORDER BY entity_id;

-- 3. Check temporal grouping (entity + provider + dimension)
SELECT
    entity_id,
    provider_name,
    dimension,
    COUNT(*) as record_count,
    MIN(value) as min_value,
    MAX(value) as max_value,
    COUNT(DISTINCT sequence) as distinct_sequences
FROM temporal_metric_records
WHERE raw_data::jsonb ->> 'baseline_tag' = 'BASELINE_V64'
GROUP BY entity_id, provider_name, dimension
ORDER BY entity_id, provider_name, dimension;
