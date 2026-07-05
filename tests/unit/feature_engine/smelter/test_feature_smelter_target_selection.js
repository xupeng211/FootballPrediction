/**
 * FeatureSmelter target selection unit tests
 * =========================================
 *
 * V5.2.1: Verify getPendingMatches uses distinct match_id selection
 * with data_version priority, and excludes PHASE legacy versions.
 *
 * @module tests/unit/feature_engine/smelter/test_feature_smelter_target_selection
 */

'use strict';

const { describe, it } = require('node:test');
const assert = require('node:assert');

// ============================================================================
// Static query structure verification (no DB required)
// ============================================================================

// Load FeatureSmelter source to inspect the query strings
const fs = require('fs');
const path = require('path');

const SMELTER_SRC = path.join(__dirname, '..', '..', '..', '..', 'src', 'feature_engine', 'smelter', 'FeatureSmelter.js');
const source = fs.readFileSync(SMELTER_SRC, 'utf-8');

describe('getPendingMatches target selection query', () => {

    it('should use ROW_NUMBER() for distinct match_id selection', () => {
        assert.ok(source.includes('ROW_NUMBER()'), 'missing ROW_NUMBER()');
        assert.ok(source.includes('PARTITION BY m.match_id'), 'missing PARTITION BY m.match_id');
        assert.ok(source.includes('WHERE rn = 1'), 'missing WHERE rn = 1 filter');
    });

    it('should include data_version priority ordering', () => {
        assert.ok(source.includes("'fotmob_live_v1' THEN 1"), 'missing fotmob_live_v1 priority');
        assert.ok(source.includes("'fotmob_pageprops_v2' THEN 2"), 'missing fotmob_pageprops_v2 priority');
        assert.ok(source.includes("'fotmob_html_hyd_v1' THEN 3"), 'missing fotmob_html_hyd_v1 priority');
    });

    it('should exclude PHASE legacy and synthetic versions', () => {
        assert.ok(source.includes("PHASE4.23"), 'missing PHASE4.23 exclusion');
        assert.ok(source.includes("PHASE4.43_SYNTHETIC"), 'missing PHASE4.43_SYNTHETIC exclusion');
        assert.ok(source.includes("NOT IN"), 'missing NOT IN clause for exclusion');
    });

    it('should have deterministic ORDER BY with match_date DESC and match_id', () => {
        assert.ok(source.includes('match_date DESC NULLS LAST'), 'missing match_date DESC NULLS LAST');
        assert.ok(source.includes('ORDER BY'), 'missing outer ORDER BY');
    });

    it('should include data_version in the SELECT columns', () => {
        assert.ok(source.includes('r.data_version'), 'missing r.data_version in SELECT');
    });
});


// ============================================================================
// Preview entry structure verification
// ============================================================================

describe('_buildPreviewEntry structure', () => {

    it('should include data_version in preview entries', () => {
        assert.ok(source.includes('data_version: match.data_version'), 'missing data_version in preview entry');
    });

    it('should still set actual_db_write=false in preview', () => {
        assert.ok(source.includes('actual_db_write: false'), 'missing actual_db_write: false');
    });
});


// ============================================================================
// smelt_all.js preview output
// ============================================================================

const SMELT_ALL_SRC = path.join(__dirname, '..', '..', '..', '..', 'scripts', 'ops', 'smelt_all.js');
const smeltAllSource = fs.readFileSync(SMELT_ALL_SRC, 'utf-8');

describe('smelt_all.js preview output', () => {

    it('should display data_version in preview entries', () => {
        assert.ok(smeltAllSource.includes('data_version:'), 'missing data_version display in preview');
    });

    it('should still show NO-WRITE PREVIEW and suppressed messages', () => {
        assert.ok(smeltAllSource.includes('NO-WRITE PREVIEW'), 'missing NO-WRITE PREVIEW header');
        assert.ok(smeltAllSource.includes('INSERT/UPDATE suppressed'), 'missing suppressed message');
    });
});
