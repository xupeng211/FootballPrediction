'use strict';

// lifecycle: permanent
// scope: unit safety coverage for FotMob L2 guarded reconciliation write draft

const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');

const PROJECT_ROOT = path.resolve(__dirname, '../../../..');
const SCRIPT_PATH = path.join(PROJECT_ROOT, 'scripts/ops/l2_guarded_reconciliation_write.js');

function loadGateFresh() {
    delete require.cache[SCRIPT_PATH];
    return require(SCRIPT_PATH);
}

function buildReadRows() {
    return [
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
            raw_row_count: 1,
            raw_external_id: '4830461',
            raw_external_id_distinct_count: 1,
            has_raw_data: true,
            has_data_hash: true,
        },
        {
            match_id: '53_20252026_4830463',
            external_id: '4830463',
            league_name: 'Ligue 1',
            season: '2025/2026',
            home_team: 'Monaco',
            away_team: 'Le Havre',
            match_date: '2025-08-16T17:00:00.000Z',
            match_status: 'finished',
            normalized_match_status: 'finished',
            pipeline_status: 'pending',
            raw_data_version: 'fotmob_live_v1',
            raw_row_count: 1,
            raw_external_id: '4830463',
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
            match_date: '2025-08-23T19:05:00.000Z',
            match_status: 'finished',
            normalized_match_status: 'finished',
            pipeline_status: 'pending',
            raw_data_version: 'fotmob_live_v1',
            raw_row_count: 2,
            raw_external_id: '4830470',
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
            raw_data_version: null,
            raw_row_count: 0,
            raw_external_id: null,
            raw_external_id_distinct_count: 0,
            has_raw_data: null,
            has_data_hash: null,
        },
        {
            match_id: '53_20252026_4830499',
            external_id: '4830499',
            league_name: 'Ligue 1',
            season: '2025/2026',
            home_team: 'Marseille',
            away_team: 'Paris Saint-Germain',
            match_date: '2025-09-22T18:00:00.000Z',
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
            match_id: '53_20252026_4830500',
            external_id: '4830500',
            league_name: 'Ligue 1',
            season: '2025/2026',
            home_team: 'Monaco',
            away_team: 'Metz',
            match_date: '2025-09-21T15:15:00.000Z',
            match_status: 'finished',
            normalized_match_status: 'finished',
            pipeline_status: 'pending',
            raw_data_version: 'fotmob_live_v1',
            raw_row_count: 1,
            raw_external_id: '4830500',
            raw_external_id_distinct_count: 1,
            has_raw_data: true,
            has_data_hash: false,
        },
    ];
}

function createMockClient() {
    const calls = [];

    return {
        calls,
        async query(sql, params = []) {
            calls.push({ sql: String(sql), params });

            const normalized = String(sql).replace(/\s+/g, ' ').trim();
            if (normalized === 'BEGIN READ ONLY' || normalized === 'BEGIN' || normalized === 'ROLLBACK' || normalized === 'COMMIT') {
                return { rows: [] };
            }

            if (normalized.startsWith('SELECT column_name FROM information_schema.columns WHERE table_name = \'raw_match_data\'')) {
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

            if (normalized.startsWith('SELECT column_name FROM information_schema.columns WHERE table_name = \'matches\'')) {
                return {
                    rows: [
                        { column_name: 'id' },
                        { column_name: 'match_id' },
                        { column_name: 'pipeline_status' },
                        { column_name: 'status' },
                        { column_name: 'external_id' },
                        { column_name: 'updated_at' },
                    ],
                };
            }

            if (normalized.startsWith('WITH raw_version_scope AS')) {
                return { rows: buildReadRows() };
            }

            if (normalized.startsWith('UPDATE matches SET pipeline_status = \'harvested\'')) {
                const matchId = params[0];
                return {
                    rows: [
                        {
                            match_id: matchId,
                            external_id: matchId === '53_20252026_4830466' ? '4830466' : '4830461',
                            new_pipeline_status: 'harvested',
                        },
                    ],
                };
            }

            throw new Error(`Unhandled SQL in test double: ${normalized}`);
        },
    };
}

test('parseArgs defaults to dry_run limit=3 and clamps larger values to 3', () => {
    const gate = loadGateFresh();

    const defaults = gate.parseArgs([]);
    assert.equal(defaults.limit, 3);
    assert.equal(defaults.allowWrite, false);
    assert.equal(defaults.expectedCount, null);

    const limited = gate.parseArgs(['--limit', '99', '--json']);
    assert.equal(limited.limit, 3);
    assert.equal(limited.json, true);
});

test('build candidate query only prepares BEGIN READ ONLY, SELECT, WITH, and ROLLBACK safe SQL', () => {
    const gate = loadGateFresh();
    const options = gate.parseArgs(['--league', 'Ligue 1', '--season', '2025/2026', '--status', 'finished']);
    const bundle = gate.buildQueryBundle(options, ['match_id', 'external_id', 'raw_data', 'data_version', 'data_hash']);

    gate.assertSelectOnlySql(gate.READ_ONLY_BEGIN_SQL);
    gate.assertSelectOnlySql(bundle.rawColumns.sql);
    gate.assertSelectOnlySql(bundle.matchesColumns.sql);
    gate.assertSelectOnlySql(bundle.rows.sql);
    gate.assertSelectOnlySql(gate.ROLLBACK_SQL);

    const rowsSql = bundle.rows.sql.replace(/\s+/g, ' ').trim().toUpperCase();
    assert.ok(rowsSql.startsWith('WITH '));
    assert.equal(bundle.rows.params[0], 'fotmob_live_v1');
});

test('write SQL contains pending guard, raw exists guard, and RETURNING match_id', () => {
    const gate = loadGateFresh();
    const sql = gate.GUARDED_UPDATE_SQL.replace(/\s+/g, ' ').trim();

    assert.match(sql, /WHERE match_id = \$1/i);
    assert.match(sql, /pipeline_status = 'pending'/i);
    assert.match(sql, /EXISTS \(/i);
    assert.match(sql, /r\.data_version = 'fotmob_live_v1'/i);
    assert.match(sql, /RETURNING/i);
    assert.match(sql, /match_id/i);
});

test('classifyRow handles clean candidate and hold reasons', () => {
    const gate = loadGateFresh();

    assert.equal(
        gate.classifyRow({
            external_id: '4830466',
            match_status: 'finished',
            pipeline_status: 'pending',
            raw_row_count: 1,
            raw_external_id: '4830466',
            has_raw_data: true,
            has_data_hash: true,
        }).decision,
        'would_update',
    );

    assert.equal(
        gate.classifyRow({
            external_id: '4830470',
            match_status: 'finished',
            pipeline_status: 'pending',
            raw_row_count: 2,
            raw_external_id: '4830470',
            has_raw_data: true,
            has_data_hash: true,
        }).decision,
        'hold_duplicate_raw',
    );

    assert.equal(
        gate.classifyRow({
            external_id: '4837496',
            match_status: 'scheduled',
            pipeline_status: 'pending',
            raw_row_count: 1,
            raw_external_id: '4837496',
            has_raw_data: true,
            has_data_hash: true,
        }).decision,
        'hold_non_finished',
    );

    assert.equal(
        gate.classifyRow({
            external_id: '4830500',
            match_status: 'finished',
            pipeline_status: 'pending',
            raw_row_count: 1,
            raw_external_id: '4830500',
            has_raw_data: true,
            has_data_hash: false,
        }).decision,
        'hold_missing_hash_or_payload',
    );

    assert.equal(
        gate.classifyRow({
            external_id: '4830499',
            match_status: 'finished',
            pipeline_status: 'pending',
            raw_row_count: 1,
            raw_external_id: '9999999',
            has_raw_data: true,
            has_data_hash: true,
        }).decision,
        'hold_external_id_mismatch',
    );
});

test('default dry_run mode uses BEGIN READ ONLY and ROLLBACK and does not execute UPDATE', async () => {
    const gate = loadGateFresh();
    const client = createMockClient();
    const payload = await gate.runGuardedReconciliationWrite(gate.parseArgs(['--limit', '3']), { client });

    const sqlCalls = client.calls.map(call => call.sql);
    assert.equal(sqlCalls[0], gate.READ_ONLY_BEGIN_SQL);
    assert.equal(sqlCalls[sqlCalls.length - 1], gate.ROLLBACK_SQL);
    assert.equal(sqlCalls.some(sql => /^UPDATE /i.test(sql)), false);
    assert.equal(payload.mode, 'dry_run');
    assert.equal(payload.summary.candidate_total, 3);
    assert.equal(payload.summary.selected_count, 3);
    assert.equal(payload.summary.would_update_count, 3);
    assert.equal(payload.summary.actual_update_executed, false);
    assert.equal(payload.summary.hold_duplicate_raw_count, 1);
    assert.equal(payload.summary.hold_non_finished_count, 0);
    assert.equal(payload.summary.hold_missing_hash_or_payload_count, 1);
    assert.equal(payload.summary.hold_external_id_mismatch_count, 1);
    assert.equal(payload.summary.excluded_no_raw_count, 1);
    assert.equal(payload.safety.db_write_allowed, false);
    assert.equal(payload.safety.pipeline_status_update_allowed, false);
    assert.equal(payload.safety.requires_allow_write, true);
    assert.equal(payload.safety.max_batch_size, 3);
    assert.equal(Object.prototype.hasOwnProperty.call(payload.selected_candidates[0], 'raw_data'), false);
    assert.equal(Object.prototype.hasOwnProperty.call(payload.selected_candidates[0], 'raw_payload'), false);
    assert.equal(Object.prototype.hasOwnProperty.call(payload.selected_candidates[0], 'body'), false);
});

test('allow-write path fails closed and rolls back when expected-count mismatches', async () => {
    const gate = loadGateFresh();
    const client = createMockClient();

    await assert.rejects(
        gate.runGuardedReconciliationWrite(gate.parseArgs(['--allow-write', '--expected-count', '99']), { client }),
        /Expected selected_count=99 but found 3/,
    );

    const sqlCalls = client.calls.map(call => call.sql);
    assert.equal(sqlCalls[0], gate.WRITE_BEGIN_SQL);
    assert.equal(sqlCalls.includes(gate.ROLLBACK_SQL), true);
    assert.equal(sqlCalls.some(sql => /^UPDATE /i.test(sql)), false);
    assert.equal(sqlCalls.includes(gate.COMMIT_SQL), false);
});

test('mock write transaction validates BEGIN, UPDATE, COMMIT without real DB writes', async () => {
    const gate = loadGateFresh();
    const client = createMockClient();
    const payload = await gate.runGuardedReconciliationWrite(
        gate.parseArgs(['--allow-write', '--expected-count', '2', '--limit', '2']),
        { client },
    );

    const sqlCalls = client.calls.map(call => call.sql);
    assert.equal(sqlCalls[0], gate.WRITE_BEGIN_SQL);
    assert.equal(sqlCalls.filter(sql => /^UPDATE /i.test(sql.trim())).length, 2);
    assert.equal(sqlCalls.includes(gate.COMMIT_SQL), true);
    assert.equal(sqlCalls.includes(gate.ROLLBACK_SQL), false);
    assert.equal(payload.mode, 'write_executed');
    assert.equal(payload.summary.actual_update_executed, true);
    assert.equal(payload.summary.updated_count, 2);
});

test('script source does not import forbidden live/raw write modules', () => {
    const source = fs.readFileSync(SCRIPT_PATH, 'utf8');

    assert.doesNotMatch(source, /FotMobRawDetailFetcher/);
    assert.doesNotMatch(source, /n3_live_fotmob_raw_retain/);
    assert.doesNotMatch(source, /l2_raw_match_data_write/);
});
