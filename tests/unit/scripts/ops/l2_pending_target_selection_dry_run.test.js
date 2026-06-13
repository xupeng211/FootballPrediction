'use strict';

// lifecycle: permanent
// scope: unit safety coverage for FotMob L2 pending target selection dry-run

const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');

const PROJECT_ROOT = path.resolve(__dirname, '../../../..');
const SCRIPT_PATH = path.join(PROJECT_ROOT, 'scripts/ops/l2_pending_target_selection_dry_run.js');

function loadGateFresh() {
    delete require.cache[SCRIPT_PATH];
    return require(SCRIPT_PATH);
}

function createMockClient() {
    const calls = [];

    return {
        calls,
        async query(sql, params = []) {
            calls.push({
                sql: String(sql),
                params,
            });

            const normalized = String(sql).replace(/\s+/g, ' ').trim();
            if (normalized === 'BEGIN READ ONLY' || normalized === 'ROLLBACK') {
                return { rows: [] };
            }

            if (normalized.includes('COUNT(*) FILTER')) {
                return {
                    rows: [{
                        total_pending_candidates: '5',
                        selected_count: '4',
                        missing_external_id_count: '1',
                        already_processing_count: '2',
                        already_harvested_count: '8',
                        failed_count: '3',
                        skipped_count: '1',
                        oldest_match_date: '2025-08-15T18:00:00.000Z',
                        newest_match_date: '2025-08-20T18:00:00.000Z',
                    }],
                };
            }

            if (normalized.includes('GROUP BY COALESCE(NULLIF(BTRIM(league_name)')) {
                return {
                    rows: [
                        { league_name: 'Premier League', match_count: '3' },
                        { league_name: 'La Liga', match_count: '1' },
                    ],
                };
            }

            if (normalized.includes('GROUP BY COALESCE(NULLIF(BTRIM(season)')) {
                return {
                    rows: [
                        { season: '2025/2026', match_count: '4' },
                    ],
                };
            }

            if (normalized.includes('ORDER BY match_date ASC NULLS LAST, match_id ASC')) {
                return {
                    rows: [
                        {
                            match_id: '47_20252026_1001',
                            external_id: '1001',
                            league_name: 'Premier League',
                            season: '2025/2026',
                            home_team: 'Arsenal',
                            away_team: 'Chelsea',
                            match_date: '2025-08-15T18:00:00.000Z',
                            status: 'finished',
                            pipeline_status: 'pending',
                        },
                    ],
                };
            }

            throw new Error(`Unhandled SQL in test double: ${normalized}`);
        },
    };
}

test('parseArgs uses DRY-RUN defaults and clamps sample limit', () => {
    const gate = loadGateFresh();

    const defaults = gate.parseArgs([]);
    assert.equal(defaults.limit, 10);
    assert.equal(defaults.includeFailed, false);
    assert.equal(defaults.json, false);

    const limited = gate.parseArgs(['--limit', '25', '--include-failed', '--json']);
    assert.equal(limited.limit, 10);
    assert.equal(limited.includeFailed, true);
    assert.equal(limited.json, true);
});

test('buildQueryBundle only prepares read-only SQL and keeps default sample limit', () => {
    const gate = loadGateFresh();
    const options = gate.parseArgs([]);
    const bundle = gate.buildQueryBundle(options);

    gate.assertSelectOnlySql(gate.READ_ONLY_BEGIN_SQL);
    gate.assertSelectOnlySql(bundle.summary.sql);
    gate.assertSelectOnlySql(bundle.byLeague.sql);
    gate.assertSelectOnlySql(bundle.bySeason.sql);
    gate.assertSelectOnlySql(bundle.sample.sql);
    gate.assertSelectOnlySql(gate.READ_ONLY_ROLLBACK_SQL);

    assert.deepEqual(bundle.summary.params[0], ['pending']);
    assert.equal(bundle.sample.params[1], 10);

    for (const sql of [bundle.summary.sql, bundle.byLeague.sql, bundle.bySeason.sql, bundle.sample.sql]) {
        const normalized = sql.replace(/\s+/g, ' ').trim().toUpperCase();
        assert.ok(normalized.startsWith('WITH '));
        assert.doesNotMatch(normalized, /\b(INSERT|UPDATE|UPSERT|DELETE|TRUNCATE|CREATE|ALTER|DROP)\b/);
    }
});

test('runSelectionDryRun executes BEGIN READ ONLY, SELECT-only queries, then ROLLBACK', async () => {
    const gate = loadGateFresh();
    const client = createMockClient();
    const payload = await gate.runSelectionDryRun(gate.parseArgs([]), { client });

    assert.equal(payload.dry_run, true);
    assert.equal(payload.read_only, true);
    assert.equal(payload.contract_carrier, 'matches + pipeline_status');
    assert.equal(payload.selected_count, 4);
    assert.equal(payload.sample_targets.length, 1);
    assert.equal(payload.sample_targets[0].match_id, '47_20252026_1001');

    assert.equal(client.calls[0].sql, gate.READ_ONLY_BEGIN_SQL);
    assert.equal(client.calls[client.calls.length - 1].sql, gate.READ_ONLY_ROLLBACK_SQL);

    for (const call of client.calls) {
        gate.assertSelectOnlySql(call.sql);
    }
});

test('script source does not reference live fetch or raw write paths', () => {
    const source = fs.readFileSync(SCRIPT_PATH, 'utf8');

    assert.doesNotMatch(source, /\b(INSERT|UPDATE|UPSERT|DELETE|TRUNCATE|CREATE|ALTER|DROP)\b/);
    assert.doesNotMatch(source, /FotMobRawDetailFetcher/);
    assert.doesNotMatch(source, /l2_raw_match_data_write/);
    assert.doesNotMatch(source, /n3_live_fotmob_raw_retain/);
    assert.doesNotMatch(source, /single_live_fotmob_raw_ingest_smoke/);
});
