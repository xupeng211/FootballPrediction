-- V41.272 "Holy Grail" - Database Physical Circuit Breaker (FIXED v2)
-- ===========================================================================

BEGIN;

-- Drop existing constraints if they exist
DO $$
BEGIN
    -- Check and drop from match_odds_intelligence table
    IF EXISTS (
        SELECT 1 FROM pg_constraint
        WHERE conrelid = 'match_odds_intelligence'::regclass
          AND conname = 'chk_initial_price_overround'
    ) THEN
        ALTER TABLE match_odds_intelligence
            DROP CONSTRAINT chk_initial_price_overround;
        RAISE NOTICE 'Dropped chk_initial_price_overround';
    END IF;

    IF EXISTS (
        SELECT 1 FROM pg_constraint
        WHERE conrelid = 'match_odds_intelligence'::regclass
          AND conname = 'chk_closing_price_overround'
    ) THEN
        ALTER TABLE match_odds_intelligence
            DROP CONSTRAINT chk_closing_price_overround;
        RAISE NOTICE 'Dropped chk_closing_price_overround';
    END IF;

    IF EXISTS (
        SELECT 1 FROM pg_constraint
        WHERE conrelid = 'match_odds_intelligence'::regclass
          AND conname = 'chk_minimum_odds_value'
    ) THEN
        ALTER TABLE match_odds_intelligence
            DROP CONSTRAINT chk_minimum_odds_value;
        RAISE NOTICE 'Dropped chk_minimum_odds_value';
    END IF;

    IF EXISTS (
        SELECT 1 FROM pg_constraint
        WHERE conrelid = 'match_odds_intelligence'::regclass
          AND conname = 'chk_minimum_odds_value_closing'
    ) THEN
        ALTER TABLE match_odds_intelligence
            DROP CONSTRAINT chk_minimum_odds_value_closing;
        RAISE NOTICE 'Dropped chk_minimum_odds_value_closing';
    END IF;
END $$;

-- ============================================================================
-- Step 1: Add Overround CHECK Constraint for initial_price
-- ============================================================================

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

    RAISE NOTICE '✓ chk_initial_price_overround added';
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

    RAISE NOTICE '✓ chk_closing_price_overround added';
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

    RAISE NOTICE '✓ chk_minimum_odds_value added';
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

    RAISE NOTICE '✓ chk_minimum_odds_value_closing added';
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
