-- V41.272 "Holy Grail" - Database Physical Circuit Breaker
-- ==========================================================
--
-- This migration adds CHECK constraints to physically lock the database
-- against invalid odds data at the storage engine level.
--
-- Core Principle: "Physical Laws" - The database itself learns to reject garbage.
--
-- Author: Database Security Architect
-- Date: 2026-01-20
-- Version: V41.272 "Holy Grail"

BEGIN;

-- ============================================================================
-- Step 1: Add Overround CHECK Constraint for initial_price
-- ============================================================================

-- Constraint: Overround must be between 0.95 and 1.20
-- Formula: (1/H + 1/D + 1/A) must be in valid range
--
-- This ensures:
-- 1. No Asian Handicap data (odds < 1.01 would fail)
-- 2. No corrupted data (Overround < 0.95 is mathematically impossible)
-- 3. No abnormal structure (Overround > 1.20 indicates non-1X2 table)

DO $$
BEGIN
    -- Check if constraint already exists
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint
        WHERE conname = 'chk_initial_price_overround'
    ) THEN
        ALTER TABLE match_odds_intelligence
        ADD CONSTRAINT chk_initial_price_overround
        CHECK (
            initial_price IS NULL OR
            jsonb_array_length(initial_price) < 3 OR
            (
                (1.0::float / (initial_price->>0::float)) +
                (1.0::float / (initial_price->>1::float)) +
                (1.0::float / (initial_price->>2::float))
            ) BETWEEN 0.95 AND 1.20
        );

        RAISE NOTICE 'Constraint chk_initial_price_overround added successfully';
    ELSE
        RAISE NOTICE 'Constraint chk_initial_price_overround already exists';
    END IF;
END $$;

-- ============================================================================
-- Step 2: Add Overround CHECK Constraint for closing_price
-- ============================================================================

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint
        WHERE conname = 'chk_closing_price_overround'
    ) THEN
        ALTER TABLE match_odds_intelligence
        ADD CONSTRAINT chk_closing_price_overround
        CHECK (
            closing_price IS NULL OR
            jsonb_array_length(closing_price) < 3 OR
            (
                (1.0::float / (closing_price->>0::float)) +
                (1.0::float / (closing_price->>1::float)) +
                (1.0::float / (closing_price->>2::float))
            ) BETWEEN 0.95 AND 1.20
        );

        RAISE NOTICE 'Constraint chk_closing_price_overround added successfully';
    ELSE
        RAISE NOTICE 'Constraint chk_closing_price_overround already exists';
    END IF;
END $$;

-- ============================================================================
-- Step 3: Add minimum odds CHECK constraint
-- ============================================================================

-- This provides additional protection against Asian Handicap data
-- by ensuring no odds value is below 1.01

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint
        WHERE conname = 'chk_minimum_odds_value'
    ) THEN
        ALTER TABLE match_odds_intelligence
        ADD CONSTRAINT chk_minimum_odds_value
        CHECK (
            initial_price IS NULL OR
            jsonb_array_length(initial_price) < 3 OR
            (
                (initial_price->>0::float) >= 1.01 AND
                (initial_price->>1::float) >= 1.01 AND
                (initial_price->>2::float) >= 1.01
            )
        );

        RAISE NOTICE 'Constraint chk_minimum_odds_value added successfully';
    ELSE
        RAISE NOTICE 'Constraint chk_minimum_odds_value already exists';
    END IF;
END $$;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint
        WHERE conname = 'chk_minimum_odds_value_closing'
    ) THEN
        ALTER TABLE match_odds_intelligence
        ADD CONSTRAINT chk_minimum_odds_value_closing
        CHECK (
            closing_price IS NULL OR
            jsonb_array_length(closing_price) < 3 OR
            (
                (closing_price->>0::float) >= 1.01 AND
                (closing_price->>1::float) >= 1.01 AND
                (closing_price->>2::float) >= 1.01
            )
        );

        RAISE NOTICE 'Constraint chk_minimum_odds_value_closing added successfully';
    ELSE
        RAISE NOTICE 'Constraint chk_minimum_odds_value_closing already exists';
    END IF;
END $$;

-- ============================================================================
-- Verification: List all CHECK constraints on match_odds_intelligence
-- ============================================================================

DO $$
BEGIN
    RAISE NOTICE '=== V41.272 Physical Constraints Active ===';

    FOR constraint IN
        SELECT conname, pg_get_constraintdef(oid) as definition
        FROM pg_constraint
        WHERE conrelid = 'match_odds_intelligence'::regclass
          AND contype = 'c'
        ORDER BY conname
    LOOP
        RAISE NOTICE 'Constraint: %', constraint.conname;
    END IF;
END $$;

COMMIT;

-- ============================================================================
-- Post-Migration Report
-- ============================================================================

-- Verify the constraints are in place
SELECT
    conname as constraint_name,
    pg_get_constraintdef(oid) as constraint_definition
FROM pg_constraint
WHERE conrelid = 'match_odds_intelligence'::regclass
  AND contype = 'c'
ORDER BY conname;

-- Expected output:
-- constraint_name                    | constraint_definition
-- -----------------------------------+---------------------------------------------------
-- chk_initial_price_overround        | CHECK ( ...)
-- chk_closing_price_overround        | CHECK ( ...)
-- chk_minimum_odds_value             | CHECK ( ...)
-- chk_minimum_odds_value_closing     | CHECK ( ...)
