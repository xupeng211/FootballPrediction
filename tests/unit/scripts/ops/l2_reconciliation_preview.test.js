'use strict';

// lifecycle: permanent
// scope: unit safety coverage for FotMob L2 reconciliation preview

const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');

const PROJECT_ROOT = path.resolve(__dirname, '../../../..');
const SCRIPT_PATH = path.join(PROJECT_ROOT, 'scripts/ops/l2_reconciliation_preview.js');

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

            if (normalized.startsWith('SELECT column_name FROM information_schema.columns')) {
                return {
                    rows: [
                        { column_name: 'id' },
                        { column_name: 'match_id' },
                        { column_name: 'external_id' },
                        { column_name: 'raw_data' },
                        { column_name: 'data_version' },
                        { column_name: 'data_hash' },
                    ],
                };
            }

            if (normalized.startsWith('WITH raw_version_scope AS')) {
                return {
                    rows: [
                        {
                            match_id: '53_20252026_4830466',
                            external_id: '4830466',
                            league_name: 'Ligue 1',
                            season: '2025/2026',
                            home_team: 'Rennes',
                            away_team: 'Marseille',
                            match_date: '2025-08-15T18:45:00.000Z',
                            match_status: 'finished',
                            normalized_match_status: 'finished',
                            pipeline_status: 'pending',
                            raw_data_version: 'fotmob_live_v1',
                            raw_row_count: 1,
                            raw_external_id: '4830466',
                            raw_external_id_distinct_count: 1,
                            has_raw_data: true,
                            has_data_hash: true,
                        },
                        {
                            match_id: '53_20252026_4830461',
                            external_id: '4830461',
                            league_name: 'Ligue 1',
                            season: '2025/2026',
                            home_team: 'Lens',
                            away_team: 'Lyon',
                            match_date: '2025-08-16T15:00:00.000Z',
                            match_status: 'finished',
                            normalized_match_status: 'finished',
                            pipeline_status: 'pending',
                            raw_data_version: 'fotmob_live_v1',
                            raw_row_count: 2,
                            raw_external_id: '4830461',
                            raw_external_id_distinct_count: 1,
                            has_raw_data: true,
                            has_data_hash: true,
                        },
                        {
                            match_id: '140_20252026_4837496',
                            external_id: '4837496',
                            league_name: 'Segunda División',
                            season: '2025/2026',
                            home_team: 'Burgos',
                            away_team: 'Oviedo',
                            match_date: '2025-09-01T18:30:00.000Z',
                            match_status: 'scheduled',
                            normalized_match_status: 'scheduled',
                            pipeline_status: 'pending',
                            raw_data_version: 'fotmob_live_v1',
                            raw_row_count: 1,
                            raw_external_id: '4837496',
                            raw_external_id_distinct_count: 1,
                            has_raw_data: true,
                            has_data_hash: true,
                        },
                        {
                            match_id: '53_20252026_4830469',
                            external_id: '4830469',
                            league_name: 'Ligue 1',
                            season: '2025/2026',
                            home_team: 'Lorient',
                            away_team: 'Rennes',
                            match_date: '2025-08-24T13:00:00.000Z',
                            match_status: 'finished',
                            normalized_match_status: 'finished',
                            pipeline_status: 'pending',
                            raw_data_version: 'fotmob_live_v1',
                            raw_row_count: 1,
                            raw_external_id: '9999999',
                            raw_external_id_distinct_count: 1,
                            has_raw_data: true,
                            has_data_hash: true,
                        },
                        {
                            match_id: '53_20252026_4830470',
                            external_id: '4830470',
                            league_name: 'Ligue 1',
                            season: '2025/2026',
                            home_team: 'Lyon',
                            away_team: 'Metz',
                            match_date: '2025-08-24T19:05:00.000Z',
                            match_status: 'finished',
                            normalized_match_status: 'finished',
                            pipeline_status: 'pending',
                            raw_data_version: 'fotmob_live_v1',
                            raw_row_count: 1,
                            raw_external_id: '4830470',
                            raw_external_id_distinct_count: 1,
                            has_raw_data: false,
                            has_data_hash: false,
                        },
                        {
                            match_id: '47_20242025_900002',
                            external_id: '900002',
                            league_name: 'Segunda',
                            season: '2024/2025',
                            home_team: 'Burgos',
                            away_team: 'Oviedo',
                            match_date: '2024-08-17T17:30:00.000Z',
                            match_status: 'finished',
                            normalized_match_status: 'finished',
                            pipeline_status: 'pending',
                            raw_data_version: null,
                            raw_row_count: 0,
                            raw_external_id: null,
                            raw_external_id_distinct_count: 0,
                            has_raw_data: null,
                            has_data_hash: null,
                        },
                    ],
                };
            }

            throw new Error(`Unhandled SQL in test double: ${normalized}`);
        },
    };
}

test('parseArgs uses reconciliation defaults and clamps limit to 58', () => {
    const gate = loadGateFresh();

    const defaults = gate.parseArgs([]);
    assert.equal(defaults.limit, 20);
    assert.equal(defaults.json, false);

    const limited = gate.parseArgs(['--limit', '999', '--json']);
    assert.equal(limited.limit, 58);
    assert.equal(limited.json, true);
});

test('buildQueryBundle only prepares BEGIN READ ONLY, SELECT, WITH, and ROLLBACK safe SQL', () => {
    const gate = loadGateFresh();
    const options = gate.parseArgs(['--league', 'Ligue 1', '--season', '2025/2026', '--status', 'finished']);
    const bundle = gate.buildQueryBundle(options, ['match_id', 'external_id', 'raw_data', 'data_version', 'data_hash']);

    gate.assertSelectOnlySql(gate.READ_ONLY_BEGIN_SQL);
    gate.assertSelectOnlySql(bundle.rawColumns.sql);
    gate.assertSelectOnlySql(bundle.rows.sql);
    gate.assertSelectOnlySql(gate.READ_ONLY_ROLLBACK_SQL);

    const rawColumnsSql = bundle.rawColumns.sql.replace(/\s+/g, ' ').trim().toUpperCase();
    const rowsSql = bundle.rows.sql.replace(/\s+/g, ' ').trim().toUpperCase();

    assert.ok(rawColumnsSql.startsWith('SELECT '));
    assert.ok(rowsSql.startsWith('WITH '));
    assert.equal(bundle.rows.params[0], 'fotmob_live_v1');
    assert.doesNotMatch(rowsSql, /\b(INSERT|UPDATE|UPSERT|DELETE|TRUNCATE|CREATE|ALTER|DROP)\b/i);
});

test('classifyRow suggests harvested for finished pending row with single complete raw', () => {
    const gate = loadGateFresh();
    const result = gate.classifyRow({
        external_id: '4830466',
        match_status: 'finished',
        pipeline_status: 'pending',
        raw_row_count: 1,
        raw_external_id: '4830466',
        has_raw_data: true,
        has_data_hash: true,
    });

    assert.equal(result.reconciliation_decision, 'suggest_harvested');
});

test('classifyRow holds duplicate raw', () => {
    const gate = loadGateFresh();
    const result = gate.classifyRow({
        external_id: '4830461',
        match_status: 'finished',
        pipeline_status: 'pending',
        raw_row_count: 2,
        raw_external_id: '4830461',
        has_raw_data: true,
        has_data_hash: true,
    });

    assert.equal(result.reconciliation_decision, 'hold_duplicate_raw');
});

test('classifyRow holds non-finished row', () => {
    const gate = loadGateFresh();
    const result = gate.classifyRow({
        external_id: '4837496',
        match_status: 'scheduled',
        pipeline_status: 'pending',
        raw_row_count: 1,
        raw_external_id: '4837496',
        has_raw_data: true,
        has_data_hash: true,
    });

    assert.equal(result.reconciliation_decision, 'hold_non_finished');
});

test('classifyRow holds external_id mismatch', () => {
    const gate = loadGateFresh();
    const result = gate.classifyRow({
        external_id: '4830469',
        match_status: 'finished',
        pipeline_status: 'pending',
        raw_row_count: 1,
        raw_external_id: '9999999',
        has_raw_data: true,
        has_data_hash: true,
    });

    assert.equal(result.reconciliation_decision, 'hold_external_id_mismatch');
});

test('runReconciliationPreview wraps preview query in BEGIN READ ONLY and ROLLBACK and keeps raw payload output disabled', async () => {
    const gate = loadGateFresh();
    const client = createMockClient();
    const payload = await gate.runReconciliationPreview(gate.parseArgs(['--limit', '20']), { client });

    assert.equal(client.calls[0].sql, gate.READ_ONLY_BEGIN_SQL);
    assert.equal(client.calls[client.calls.length - 1].sql, gate.READ_ONLY_ROLLBACK_SQL);
    assert.equal(payload.phase, 'FOTMOB_L2_RECONCILIATION_PREVIEW');
    assert.equal(payload.summary.candidate_total, 5);
    assert.equal(payload.summary.suggest_harvested_count, 1);
    assert.equal(payload.summary.hold_duplicate_raw_count, 1);
    assert.equal(payload.summary.hold_non_finished_count, 1);
    assert.equal(payload.summary.hold_missing_hash_or_payload_count, 1);
    assert.equal(payload.summary.hold_external_id_mismatch_count, 1);
    assert.equal(payload.summary.excluded_no_raw_count, 1);
    assert.equal(payload.summary.raw_row_count, 6);
    assert.equal(payload.summary.duplicate_raw_count, 1);
    assert.equal(payload.safety.live_fetch_allowed, false);
    assert.equal(payload.safety.db_write_allowed, false);
    assert.equal(payload.safety.raw_match_data_write_allowed, false);
    assert.equal(payload.safety.pipeline_status_update_allowed, false);
    assert.equal(payload.safety.read_only_transaction_used, true);
    assert.equal(payload.safety.raw_payload_output_allowed, false);
    assert.equal(payload.suggest_harvested_sample.length, 1);
    assert.equal(payload.hold_sample.length, 4);
    assert.equal(payload.suggest_harvested_sample[0].reconciliation_decision, 'suggest_harvested');
    assert.equal(Object.prototype.hasOwnProperty.call(payload.suggest_harvested_sample[0], 'raw_data'), false);
    assert.equal(Object.prototype.hasOwnProperty.call(payload.suggest_harvested_sample[0], 'raw_payload'), false);
    assert.equal(Object.prototype.hasOwnProperty.call(payload.suggest_harvested_sample[0], 'body'), false);
});

test('script source does not contain write SQL keywords or forbidden imports', () => {
    const source = fs.readFileSync(SCRIPT_PATH, 'utf8');

    assert.doesNotMatch(source, /\b(INSERT|UPDATE|UPSERT|DELETE|TRUNCATE|CREATE|ALTER|DROP)\b/i);
    assert.doesNotMatch(source, /FotMobRawDetailFetcher/);
    assert.doesNotMatch(source, /n3_live_fotmob_raw_retain/);
    assert.doesNotMatch(source, /l2_raw_match_data_write/);
});
