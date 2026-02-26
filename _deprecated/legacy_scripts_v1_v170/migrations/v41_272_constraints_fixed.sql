-- V41.272 "Holy Grail" - Database Physical Circuit Breaker (FIXED)
-- =======================================================================

BEGIN;

-- Drop existing constraints if they exist
DO $$
BEGIN
    DROP CONSTRAINT IF EXISTS chk_initial_price_overround CASCADE;
    DROP CONSTRAINT IF EXISTS chk_closing_price_overround CASCADE;
    DROP CONSTRAINT IF EXISTS chk_minimum_odds_value CASCADE;
    DROP CONSTRAINT IF EXISTS chk_minimum_odds_value_closing CASCADE;
    RAISE NOTICE 'Old constraints dropped (if any existed)';
END $$;

-- ============================================================================
-- Step 1: Add Overround CHECK Constraint for initial_price
-- ============================================================================

COMMENT ON TABLE match_odds_intelligence IS '';

DO $$
BEGIN
    ALTER TABLE match_odds_intelligence
        ADD CONSTRAINT chk_initial_price_overround
        CHECK (
            initial_price IS NULL OR
            NOT jsonb_typeof(initial_price) = 'array' OR
            jsonb_array_length(initial_price) < 3 OR
            (
                (1.0::float8 / (initial_price->>0)::float8) +
                (1.0::float8 / (initial_price->>1)::float8) +
                (1.0::float8 / (initial_price->>2)::float8)
            ) BETWEEN 0.95 AND 1.20
        );

    RAISE NOTICE 'Constraint chk_initial_price_overround added successfully';
END $$;

-- ============================================================================
-- Step 2: Add Overround CHECK Constraint for closing_price
-- ============================================================================

DO $$
BEGIN
    ALTER TABLE match_odds_intelligence
        ADD CONSTRAINT chk_closing_price_overround
        CHECK (
            closing_price IS NULL OR
            NOT jsonb_typeof(closing_price) = 'array' OR
            jsonb_array_length(closing_price) < 3 OR
            (
                (1.0::float8 / (closing_price->>0)::float8) +
                (1.0::float8 / (closing_price->>1)::float8) +
                (1.0::float8 / (closing_price->>2)::float8)
            ) BETWEEN 0.95 AND 1.20
        );

    RAISE NOTICE 'Constraint chk_closing_price_overround added successfully';
END $$;

-- ============================================================================
-- Step 3: Add minimum odds CHECK constraint
-- ============================================================================

DO $$
BEGIN
    ALTER TABLE match_odds_intelligence
        ADD CONSTRAINT chk_minimum_odds_value
        CHECK (
            initial_price IS NULL OR
            NOT jsonb_typeof(initial_price) = 'array' OR
            jsonb_array_length(initial_price) < 3 OR
            (
                (initial_price->>0)::float8 >= 1.01 AND
                (initial_price->>1)::float8 >= 1.01 AND
                (initial_price->>2)::float8 >= 1.01
            )
        );

    RAISE NOTICE 'Constraint chk_minimum_odds_value added successfully';
END $$;

DO $$
BEGIN
    ALTER TABLE match_odds_intelligence
        ADD CONSTRAINT chk_minimum_odds_value_closing
        CHECK (
            closing_price IS NULL OR
            NOT jsonb_typeof(closing_price) = 'array' OR
            jsonb_array_length(closing_price) < 3 OR
            (
                (closing_price->>0)::float8 >= 1.01 AND
                (closing_price->>1)::float8 >= 1.01 AND
                (closing_price->>2)::float8 >= 1.01
            )
        );

    RAISE NOTICE 'Constraint chk_minimum_odds_value_closing added successfully';
END $$;

COMMIT;

-- ============================================================================
-- Verification
-- ============================================================================

SELECT
    conname as constraint_name
FROM pg_constraint
WHERE conrelid = 'match_odds_intelligence'::regclass
  AND contype = 'c'
ORDER BY conname;
