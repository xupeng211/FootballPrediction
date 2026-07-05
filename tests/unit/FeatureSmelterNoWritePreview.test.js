/**
 * FeatureSmelter No-Write Preview 单元测试
 * =======================================
 *
 * 验证 dryRun / noWrite / preview 模式：
 * 1. 不会执行 INSERT INTO l3_features
 * 2. 不会执行 UPDATE l3_features
 * 3. 仍会调用 extractor / process 逻辑
 * 4. 返回 preview summary
 * 5. 非 dryRun 模式原有写入路径不被破坏
 *
 * GOLD-AUDIT-2B: test-only, no DB write, no network.
 *
 * @module tests/unit/FeatureSmelterNoWritePreview.test
 * @version GOLD-AUDIT-2B
 */

'use strict';

const { describe, test } = require('node:test');
const assert = require('node:assert/strict');

// We import the module to verify its exports but mock the DB-heavy path.
const { FeatureSmelter } = require('../../src/feature_engine/smelter/FeatureSmelter');

// ===========================================================================
// Helper: collect SQL strings that would be sent to a DB client
// ===========================================================================

function buildMockPool(opts = {}) {
    const queries = [];
    const pool = {
        query: async (sql, params) => {
            queries.push({ sql, params });
            if (opts.queryResult !== undefined) return opts.queryResult;
            return { rows: [] };
        },
        connect: async () => {
            const clientQueries = [];
            const client = {
                query: async (sql, params) => {
                    clientQueries.push({ sql, params });
                    if (opts.clientResult !== undefined) return opts.clientResult;
                    return { rows: [] };
                },
                release: () => {},
            };
            return client;
        },
        _queries: queries,
    };
    return pool;
}

function hasForbiddenSQL(queries) {
    const forbidden = /\b(INSERT|UPDATE|DELETE|TRUNCATE|DROP|ALTER|CREATE)\b/i;
    const found = [];
    for (const q of queries) {
        if (forbidden.test(q.sql)) {
            found.push(q.sql.trim().substring(0, 120));
        }
    }
    return found;
}

// ===========================================================================
// Synthetic inline fixture — minimal raw_data that extractors can handle
// ===========================================================================

const SYNTHETIC_RAW_DATA = {
    content: {
        header: {
            name: 'Fixture Home vs Fixture Away',
            status: { started: false, finished: true, cancelled: false, utcTime: '2026-07-04T12:00:00.000Z' }
        },
        home: { name: 'Fixture Home', shortName: 'FIXH', id: 'home-fixture-001', score: 2 },
        away: { name: 'Fixture Away', shortName: 'FIXA', id: 'away-fixture-001', score: 1 },
        stats: { expectedGoals: { home: 1.5, away: 0.8 }, shots: { home: 14, away: 7 } },
        lineup: { home: { players: [{ id: 'p1', name: 'Player 1' }] }, away: { players: [{ id: 'p2', name: 'Player 2' }] } },
        events: [{ id: 'ev1', type: 'Goal', minute: 30 }],
        playerStats: { home: [{ id: 'p1', rating: 7.5 }], away: [{ id: 'p2', rating: 6.8 }] },
        general: { matchTimeUTC: '2026-07-04T12:00:00.000Z', homeTeam: { name: 'Fixture Home' }, awayTeam: { name: 'Fixture Away' } }
    },
    general: { matchTimeUTC: '2026-07-04T12:00:00.000Z', league: 'Fixture League', homeTeam: { id: 'home-fixture-001', name: 'Fixture Home' }, awayTeam: { id: 'away-fixture-001', name: 'Fixture Away' } },
    header: { status: { utcTime: '2026-07-04T12:00:00.000Z' }, teams: [{ id: 'home-fixture-001', name: 'Fixture Home', score: 2 }, { id: 'away-fixture-001', name: 'Fixture Away', score: 1 }] }
};

// ===========================================================================
// Tests
// ===========================================================================

describe('GOLD-AUDIT-2B FeatureSmelter no-write preview', () => {

    // -----------------------------------------------------------------------
    // 1. dryRun mode prevents INSERT/UPDATE
    // -----------------------------------------------------------------------

    test('dryRun mode: saveFeatures is never called', async () => {
        const smelter = new FeatureSmelter({ batchSize: 500, delayMs: 0 });
        smelter.pool = buildMockPool({
            queryResult: { rows: [] },
            clientResult: { rows: [] },
        });
        smelter.eloCache = new Map();
        smelter.isInitialized = true;

        // Override getPendingMatches to return a single match
        const originalGetPending = smelter.getPendingMatches.bind(smelter);
        smelter.getPendingMatches = async () => [{
            match_id: 'test-001',
            external_id: 'ext-001',
            home_team: 'Fixture Home',
            away_team: 'Fixture Away',
            match_date: '2026-07-04',
            home_score: 2,
            away_score: 1,
            raw_data: SYNTHETIC_RAW_DATA,
        }];

        let saveFeaturesCalled = false;
        smelter.saveFeatures = async () => { saveFeaturesCalled = true; return 0; };

        const result = await smelter.run({ dryRun: true, limit: 1 });

        assert.equal(saveFeaturesCalled, false, 'saveFeatures must NOT be called in dryRun mode');
        assert.equal(result.isNoWrite, true);
        assert.equal(result.isDryRun, true);
        assert.ok(result.previewEntries, 'previewEntries must exist');
        assert.equal(result.previewEntries.length, 1);
        assert.equal(result.previewEntries[0].actual_db_write, false);
        assert.equal(result.previewEntries[0].would_write_l3_features, true);
    });

    // -----------------------------------------------------------------------
    // 2. noWrite mode prevents INSERT/UPDATE
    // -----------------------------------------------------------------------

    test('noWrite mode: saveFeatures is never called', async () => {
        const smelter = new FeatureSmelter({ batchSize: 500, delayMs: 0 });
        smelter.pool = buildMockPool();
        smelter.eloCache = new Map();
        smelter.isInitialized = true;

        smelter.getPendingMatches = async () => [{
            match_id: 'test-002', external_id: 'ext-002',
            home_team: 'A', away_team: 'B', match_date: '2026-07-04',
            home_score: 1, away_score: 0, raw_data: SYNTHETIC_RAW_DATA,
        }];

        let saveFeaturesCalled = false;
        smelter.saveFeatures = async () => { saveFeaturesCalled = true; return 0; };

        const result = await smelter.run({ noWrite: true, limit: 1 });
        assert.equal(saveFeaturesCalled, false);
        assert.equal(result.isNoWrite, true);
    });

    // -----------------------------------------------------------------------
    // 3. preview mode prevents INSERT/UPDATE
    // -----------------------------------------------------------------------

    test('preview mode: saveFeatures is never called', async () => {
        const smelter = new FeatureSmelter({ batchSize: 500, delayMs: 0 });
        smelter.pool = buildMockPool();
        smelter.eloCache = new Map();
        smelter.isInitialized = true;

        smelter.getPendingMatches = async () => [{
            match_id: 'test-003', external_id: 'ext-003',
            home_team: 'C', away_team: 'D', match_date: '2026-07-04',
            home_score: 0, away_score: 0, raw_data: SYNTHETIC_RAW_DATA,
        }];

        let saveFeaturesCalled = false;
        smelter.saveFeatures = async () => { saveFeaturesCalled = true; return 0; };

        const result = await smelter.run({ preview: true, limit: 1 });
        assert.equal(saveFeaturesCalled, false);
        assert.equal(result.isNoWrite, true);
    });

    // -----------------------------------------------------------------------
    // 4. dryRun mode still calls extractors (processMatch path)
    // -----------------------------------------------------------------------

    test('dryRun mode: processMatch is still called and produces feature output', async () => {
        const smelter = new FeatureSmelter({ batchSize: 500, delayMs: 0 });
        smelter.pool = buildMockPool();
        smelter.eloCache = new Map();
        smelter.isInitialized = true;

        smelter.getPendingMatches = async () => [{
            match_id: 'test-004', external_id: 'ext-004',
            home_team: 'Fixture Home', away_team: 'Fixture Away',
            match_date: '2026-07-04', home_score: 2, away_score: 1,
            raw_data: SYNTHETIC_RAW_DATA,
        }];

        smelter.saveFeatures = async () => 0;

        const result = await smelter.run({ dryRun: true, limit: 1 });

        assert.equal(result.previewEntries.length, 1);
        const entry = result.previewEntries[0];
        assert.equal(entry.has_raw_data, true);
        assert.equal(entry.would_write_l3_features, true);
        assert.equal(entry.error, null);

        // Check that extractors produced output
        assert.ok(entry.extractors.golden_features, 'golden_features must exist');
        assert.ok(entry.extractors.tactical_features, 'tactical_features must exist');
        assert.ok(entry.extractors.odds_movement_features, 'odds_movement_features must exist');
        assert.ok(entry.extractors.elo_features, 'elo_features must exist');
    });

    // -----------------------------------------------------------------------
    // 5. Non-dryRun mode still calls saveFeatures (existing path preserved)
    // -----------------------------------------------------------------------

    test('normal mode: saveFeatures IS called (existing write path preserved)', async () => {
        const smelter = new FeatureSmelter({ batchSize: 500, delayMs: 0 });
        smelter.pool = buildMockPool();
        smelter.eloCache = new Map();
        smelter.isInitialized = true;

        smelter.getPendingMatches = async () => [{
            match_id: 'test-005', external_id: 'ext-005',
            home_team: 'E', away_team: 'F', match_date: '2026-07-04',
            home_score: 1, away_score: 1, raw_data: SYNTHETIC_RAW_DATA,
        }];

        let saveFeaturesCalled = false;
        smelter.saveFeatures = async () => { saveFeaturesCalled = true; return 1; };

        const result = await smelter.run({ limit: 1 }); // NO dryRun
        assert.equal(saveFeaturesCalled, true, 'saveFeatures MUST be called in normal mode');
        assert.ok(!result.isNoWrite, 'normal mode must not set isNoWrite');
    });

    // -----------------------------------------------------------------------
    // 6. dryRun preview returns empty extractors when raw_data missing
    // -----------------------------------------------------------------------

    test('dryRun mode: raw_data missing → error in preview', async () => {
        const smelter = new FeatureSmelter({ batchSize: 500, delayMs: 0 });
        smelter.pool = buildMockPool();
        smelter.eloCache = new Map();
        smelter.isInitialized = true;

        smelter.getPendingMatches = async () => [{
            match_id: 'test-006', external_id: 'ext-006',
            home_team: 'G', away_team: 'H', match_date: '2026-07-04',
            home_score: 0, away_score: 0, raw_data: null,
        }];

        smelter.saveFeatures = async () => 0;

        const result = await smelter.run({ dryRun: true, limit: 1 });

        assert.equal(result.previewEntries.length, 1);
        const entry = result.previewEntries[0];
        assert.equal(entry.has_raw_data, false);
        assert.equal(entry.would_write_l3_features, false);
        assert.ok(entry.error, 'must have error when raw_data is missing');
        assert.ok(entry.error.includes('raw_data'), 'error must mention raw_data');
    });

    // -----------------------------------------------------------------------
    // 7. _buildPreviewEntry structure integrity
    // -----------------------------------------------------------------------

    test('_buildPreviewEntry: returns well-formed preview entry for valid features', () => {
        const smelter = new FeatureSmelter({ batchSize: 500, delayMs: 0 });

        const match = {
            match_id: 'test-007', external_id: 'ext-007',
            home_team: 'Team A', away_team: 'Team B',
            raw_data: SYNTHETIC_RAW_DATA,
        };

        const features = {
            match_id: 'test-007',
            golden_features: { home_market_value_total: 1000000, away_market_value_total: 800000 },
            tactical_features: { home_possession_avg: 55, away_possession_avg: 45 },
            odds_movement_features: { has_odds_data: false, _data_quality: 'INCOMPLETE_ODDS' },
            elo_features: { home_elo: 1600, away_elo: 1550, elo_diff: 50 },
            computed_at: '2026-07-04T12:00:00Z',
        };

        const entry = smelter._buildPreviewEntry(match, features);

        assert.equal(entry.match_id, 'test-007');
        assert.equal(entry.external_id, 'ext-007');
        assert.equal(entry.has_raw_data, true);
        assert.equal(entry.would_write_l3_features, true);
        assert.equal(entry.actual_db_write, false);
        assert.equal(entry.error, null);

        // golden_features should have non-empty data_keys
        assert.equal(entry.extractors.golden_features.empty, false);
        assert.ok(entry.extractors.golden_features.data_keys >= 1);

        // odds_movement_features: has_odds_data=false is a valid data key (value=false means no odds)
        assert.equal(entry.extractors.odds_movement_features.data_keys, 1);
        assert.ok(entry.extractors.odds_movement_features.present);

        // elo_features should not be empty
        assert.equal(entry.extractors.elo_features.empty, false);
    });

    // -----------------------------------------------------------------------
    // 8. No forbidden SQL in dryRun mode (mock DB tracking)
    // -----------------------------------------------------------------------

    test('dryRun mode: pool.query never receives INSERT/UPDATE/DELETE', async () => {
        const smelter = new FeatureSmelter({ batchSize: 500, delayMs: 0 });
        const pool = buildMockPool();
        smelter.pool = pool;
        smelter.eloCache = new Map();
        smelter.isInitialized = true;

        // getPendingMatches uses pool.query (SELECT) — that's fine
        // But saveFeatures should NOT be called, so no INSERT via client
        smelter.getPendingMatches = async () => [{
            match_id: 'test-008', external_id: 'ext-008',
            home_team: 'X', away_team: 'Y', match_date: '2026-07-04',
            home_score: 1, away_score: 0, raw_data: SYNTHETIC_RAW_DATA,
        }];

        smelter.saveFeatures = async () => 0;

        await smelter.run({ dryRun: true, limit: 1 });

        const forbidden = hasForbiddenSQL(pool._queries);
        assert.deepEqual(forbidden, [], 'dryRun mode must not emit INSERT/UPDATE/DELETE SQL');
    });
});
