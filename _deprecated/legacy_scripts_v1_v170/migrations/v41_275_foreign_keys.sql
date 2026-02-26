-- V41.275 "Quantum Linkage" - Relational Integrity Enforcement
-- ===================================================================
--
-- This migration adds FOREIGN KEY constraints to ensure referential
-- integrity between match_odds_intelligence, match_lineups, and matches.
--
-- Core Principle: "Physical Isolation" - No orphaned records allowed.
--
-- Author: Data Architect & Entity Resolution Specialist
-- Date: 2026-01-20
-- Version: V41.275 "Quantum Linkage"

BEGIN;

-- ============================================================================
-- Step 1: Clean up existing orphaned records BEFORE adding constraints
-- ============================================================================

DO $$
DECLARE
    orphaned_odds_count INT;
    orphaned_lineups_count INT;
BEGIN
    RAISE NOTICE '=== V41.275 Step 1: Cleaning up orphaned records ===';

    -- Count orphaned odds records
    SELECT COUNT(*) INTO orphaned_odds_count
    FROM match_odds_intelligence moi
    LEFT JOIN matches m ON moi.match_id = m.match_id
    WHERE m.match_id IS NULL;

    RAISE NOTICE 'Found % orphaned odds records - deleting...', orphaned_odds_count;

    -- Delete orphaned odds records
    DELETE FROM match_odds_intelligence
    WHERE match_id IN (
        SELECT moi.match_id
        FROM match_odds_intelligence moi
        LEFT JOIN matches m ON moi.match_id = m.match_id
        WHERE m.match_id IS NULL
    );

    -- Count orphaned lineup records
    SELECT COUNT(*) INTO orphaned_lineups_count
    FROM match_lineups ml
    LEFT JOIN matches m ON ml.match_id = m.match_id
    WHERE m.match_id IS NULL;

    RAISE NOTICE 'Found % orphaned lineup records - deleting...', orphaned_lineups_count;

    -- Delete orphaned lineup records
    DELETE FROM match_lineups
    WHERE match_id IN (
        SELECT ml.match_id
        FROM match_lineups ml
        LEFT JOIN matches m ON ml.match_id = m.match_id
        WHERE m.match_id IS NULL
    );

    RAISE NOTICE 'Orphan cleanup complete';
END $$;

-- ============================================================================
-- Step 2: Add FOREIGN KEY constraint to match_odds_intelligence
-- ============================================================================

DO $$
BEGIN
    -- Check if foreign key already exists
    IF NOT EXISTS (
        SELECT 1
        FROM pg_constraint
        WHERE conname = 'fk_odds_match_id'
    ) THEN
        ALTER TABLE match_odds_intelligence
            ADD CONSTRAINT fk_odds_match_id
            FOREIGN KEY (match_id)
            REFERENCES matches(match_id)
            ON DELETE CASCADE
            ON UPDATE CASCADE;

        RAISE NOTICE '✓ Foreign key fk_odds_match_id added to match_odds_intelligence';
    ELSE
        RAISE NOTICE 'Foreign key fk_odds_match_id already exists';
    END IF;
END $$;

-- ============================================================================
-- Step 3: Add FOREIGN KEY constraint to match_lineups
-- ============================================================================

DO $$
BEGIN
    -- Check if foreign key already exists
    IF NOT EXISTS (
        SELECT 1
        FROM pg_constraint
        WHERE conname = 'fk_lineups_match_id'
    ) THEN
        ALTER TABLE match_lineups
            ADD CONSTRAINT fk_lineups_match_id
            FOREIGN KEY (match_id)
            REFERENCES matches(match_id)
            ON DELETE CASCADE
            ON UPDATE CASCADE;

        RAISE NOTICE '✓ Foreign key fk_lineups_match_id added to match_lineups';
    ELSE
        RAISE NOTICE 'Foreign key fk_lineups_match_id already exists';
    END IF;
END $$;

-- ============================================================================
-- Step 4: Create indexes for foreign key performance
-- ============================================================================

-- Ensure match_id indexes exist for performance
CREATE INDEX IF NOT EXISTS idx_odds_match_id_lookup
    ON match_odds_intelligence(match_id);

CREATE INDEX IF NOT EXISTS idx_lineups_match_id_lookup
    ON match_lineups(match_id);

-- ============================================================================
-- Verification
-- ============================================================================

DO $$
DECLARE
    odds_orphans INT;
    lineups_orphans INT;
BEGIN
    RAISE NOTICE '=== V41.275 Foreign Key Constraints Active ===';

    -- Check match_odds_intelligence foreign key
    IF EXISTS (
        SELECT 1
        FROM pg_constraint
        WHERE conname = 'fk_odds_match_id'
    ) THEN
        RAISE NOTICE '✓ fk_odds_match_id: ACTIVE on match_odds_intelligence';
    ELSE
        RAISE NOTICE '✗ fk_odds_match_id: MISSING';
    END IF;

    -- Check match_lineups foreign key
    IF EXISTS (
        SELECT 1
        FROM pg_constraint
        WHERE conname = 'fk_lineups_match_id'
    ) THEN
        RAISE NOTICE '✓ fk_lineups_match_id: ACTIVE on match_lineups';
    ELSE
        RAISE NOTICE '✗ fk_lineups_match_id: MISSING';
    END IF;

    -- Count orphaned records (should be 0)
    SELECT COUNT(*) INTO odds_orphans
    FROM match_odds_intelligence moi
    LEFT JOIN matches m ON moi.match_id = m.match_id
    WHERE m.match_id IS NULL;

    SELECT COUNT(*) INTO lineups_orphans
    FROM match_lineups ml
    LEFT JOIN matches m ON ml.match_id = m.match_id
    WHERE m.match_id IS NULL;

    RAISE NOTICE 'Orphaned odds records: % (should be 0)', odds_orphans;
    RAISE NOTICE 'Orphaned lineup records: % (should be 0)', lineups_orphans;
END $$;

COMMIT;
