'use strict';

// lifecycle: permanent
// scope: unit safety coverage for FotMob L2 pending transition preview

const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');

const PROJECT_ROOT = path.resolve(__dirname, '../../../..');
const SCRIPT_PATH = path.join(PROJECT_ROOT, 'scripts/ops/l2_pending_transition_preview.js');

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

            if (normalized.startsWith('WITH pending_scope AS')) {
                return {
                    rows: [
                        {
                            match_id: '53_20252026_1111111',
                            external_id: '1111111',
                            league_name: 'Ligue 1',
                            season: '2025/2026',
                            home_team: 'Lille',
                            away_team: 'Lyon',
                            match_date: '2025-08-17T18:45:00.000Z',
                            status: 'finished',
                            pipeline_status: 'pending',
                            normalized_external_id: '1111111',
                            normalized_status: 'finished',
                            raw_exists: false,
                        },
                        {
                            match_id: '53_20252026_2222222',
                            external_id: '2222222',
                            league_name: 'Ligue 1',
                            season: '2025/2026',
                            home_team: 'Nice',
                            away_team: 'Lens',
                            match_date: '2025-08-18T18:45:00.000Z',
                            status: 'finished',
                            pipeline_status: 'pending',
                            normalized_external_id: '2222222',
                            normalized_status: 'finished',
                            raw_exists: true,
                        },
                        {
                            match_id: '53_20252026_3333333',
                            external_id: '3333333',
                            league_name: 'Ligue 1',
                            season: '2025/2026',
                            home_team: 'Brest',
                            away_team: 'Rennes',
                            match_date: '2025-08-19T18:45:00.000Z',
                            status: 'scheduled',
                            pipeline_status: 'pending',
                            normalized_external_id: '3333333',
                            normalized_status: 'scheduled',
                            raw_exists: false,
                        },
                        {
                            match_id: '53_20252026_missing',
                            external_id: '',
                            league_name: 'Ligue 1',
                            season: '2025/2026',
                            home_team: 'Metz',
                            away_team: 'Nantes',
                            match_date: '2025-08-20T18:45:00.000Z',
                            status: 'finished',
                            pipeline_status: 'pending',
                            normalized_external_id: null,
                            normalized_status: 'finished',
                            raw_exists: false,
                        },
                    ],
                };
            }

            throw new Error(`Unhandled SQL in test double: ${normalized}`);
        },
    };
}

test('parseArgs uses preview defaults and clamps limit to 10', () => {
    const gate = loadGateFresh();

    const defaults = gate.parseArgs([]);
    assert.equal(defaults.limit, 3);
    assert.equal(defaults.json, false);

    const limited = gate.parseArgs(['--limit', '25', '--json']);
    assert.equal(limited.limit, 10);
    assert.equal(limited.json, true);
});

test('buildQueryBundle only prepares BEGIN READ ONLY, WITH SELECT, and ROLLBACK safe SQL', () => {
    const gate = loadGateFresh();
    const options = gate.parseArgs(['--league', 'Ligue 1', '--season', '2025/2026']);
    const bundle = gate.buildQueryBundle(options);

    gate.assertSelectOnlySql(gate.READ_ONLY_BEGIN_SQL);
    gate.assertSelectOnlySql(bundle.rows.sql);
    gate.assertSelectOnlySql(gate.READ_ONLY_ROLLBACK_SQL);

    const normalized = bundle.rows.sql.replace(/\s+/g, ' ').trim().toUpperCase();
    assert.ok(normalized.startsWith('WITH '));
    assert.equal(bundle.rows.params[0], 'fotmob_live_v1');
    assert.doesNotMatch(normalized, /\b(INSERT|UPDATE|UPSERT|DELETE|TRUNCATE|CREATE|ALTER|DROP)\b/i);
});

test('runTransitionPreview wraps preview query in BEGIN READ ONLY and ROLLBACK and returns read-only safety flags', async () => {
    const gate = loadGateFresh();
    const client = createMockClient();
    const payload = await gate.runTransitionPreview(gate.parseArgs(['--limit', '10']), { client });

    assert.equal(client.calls[0].sql, gate.READ_ONLY_BEGIN_SQL);
    assert.equal(client.calls[client.calls.length - 1].sql, gate.READ_ONLY_ROLLBACK_SQL);
    assert.equal(payload.phase, 'FOTMOB_L2_PENDING_TRANSITION_PREVIEW');
    assert.equal(payload.summary.pending_with_external_id, 3);
    assert.equal(payload.summary.would_claim_count, 1);
    assert.equal(payload.summary.anomaly_raw_exists_but_pending_count, 1);
    assert.equal(payload.summary.missing_external_id_count, 1);
    assert.equal(payload.summary.non_finished_pending_count, 1);
    assert.equal(payload.safety.live_fetch_allowed, false);
    assert.equal(payload.safety.db_write_allowed, false);
    assert.equal(payload.safety.raw_match_data_write_allowed, false);
    assert.equal(payload.safety.pipeline_status_update_allowed, false);
    assert.equal(payload.safety.read_only_transaction_used, true);
    assert.equal(payload.would_claim_sample[0].preview_decision, 'would_claim');
    assert.equal(payload.anomaly_sample[0].preview_decision, 'anomaly');
    assert.equal(payload.non_finished_sample[0].preview_decision, 'caution');
});

test('script source does not contain write SQL keywords or forbidden imports', () => {
    const source = fs.readFileSync(SCRIPT_PATH, 'utf8');

    assert.doesNotMatch(source, /\b(INSERT|UPDATE|UPSERT|DELETE|TRUNCATE|CREATE|ALTER|DROP)\b/i);
    assert.doesNotMatch(source, /FotMobRawDetailFetcher/);
    assert.doesNotMatch(source, /n3_live_fotmob_raw_retain/);
    assert.doesNotMatch(source, /l2_raw_match_data_write/);
});
