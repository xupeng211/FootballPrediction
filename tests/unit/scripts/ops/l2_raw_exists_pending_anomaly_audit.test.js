'use strict';

// lifecycle: permanent
// scope: unit safety coverage for FotMob L2 raw-exists pending anomaly audit

const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');

const PROJECT_ROOT = path.resolve(__dirname, '../../../..');
const SCRIPT_PATH = path.join(PROJECT_ROOT, 'scripts/ops/l2_raw_exists_pending_anomaly_audit.js');

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
                        { column_name: 'data_version' },
                        { column_name: 'created_at' },
                        { column_name: 'updated_at' },
                    ],
                };
            }

            if (normalized.startsWith('WITH scoped_raw AS')) {
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
                            pipeline_status: 'pending',
                            raw_data_version: 'fotmob_live_v1',
                            raw_rows_for_version: 1,
                            raw_created_at: '2026-06-13T11:00:00.000Z',
                            raw_updated_at: '2026-06-13T11:05:00.000Z',
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
                            pipeline_status: 'pending',
                            raw_data_version: 'fotmob_live_v1',
                            raw_rows_for_version: 2,
                            raw_created_at: '2026-06-13T12:00:00.000Z',
                            raw_updated_at: '2026-06-13T12:10:00.000Z',
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
                            pipeline_status: 'pending',
                            raw_data_version: 'fotmob_live_v1',
                            raw_rows_for_version: 1,
                            raw_created_at: '2026-06-13T13:00:00.000Z',
                            raw_updated_at: '2026-06-13T13:05:00.000Z',
                        },
                    ],
                };
            }

            throw new Error(`Unhandled SQL in test double: ${normalized}`);
        },
    };
}

test('parseArgs uses anomaly audit defaults and clamps limit to 50', () => {
    const gate = loadGateFresh();

    const defaults = gate.parseArgs([]);
    assert.equal(defaults.limit, 10);
    assert.equal(defaults.json, false);

    const limited = gate.parseArgs(['--limit', '999', '--json']);
    assert.equal(limited.limit, 50);
    assert.equal(limited.json, true);
});

test('buildQueryBundle only prepares BEGIN READ ONLY, SELECT, WITH, and ROLLBACK safe SQL', () => {
    const gate = loadGateFresh();
    const options = gate.parseArgs(['--league', 'Ligue 1', '--season', '2025/2026', '--status', 'finished']);
    const bundle = gate.buildQueryBundle(options, ['match_id', 'data_version', 'created_at', 'updated_at']);

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

test('runAnomalyAudit wraps audit query in BEGIN READ ONLY and ROLLBACK and keeps raw payload output disabled', async () => {
    const gate = loadGateFresh();
    const client = createMockClient();
    const payload = await gate.runAnomalyAudit(gate.parseArgs(['--limit', '2']), { client });

    assert.equal(client.calls[0].sql, gate.READ_ONLY_BEGIN_SQL);
    assert.equal(client.calls[client.calls.length - 1].sql, gate.READ_ONLY_ROLLBACK_SQL);
    assert.equal(payload.phase, 'FOTMOB_L2_RAW_EXISTS_PENDING_ANOMALY_AUDIT');
    assert.equal(payload.summary.anomaly_total, 3);
    assert.equal(payload.summary.raw_row_count, 4);
    assert.equal(payload.summary.duplicate_raw_count, 1);
    assert.equal(payload.safety.live_fetch_allowed, false);
    assert.equal(payload.safety.db_write_allowed, false);
    assert.equal(payload.safety.raw_match_data_write_allowed, false);
    assert.equal(payload.safety.pipeline_status_update_allowed, false);
    assert.equal(payload.safety.read_only_transaction_used, true);
    assert.equal(payload.safety.raw_payload_output_allowed, false);
    assert.equal(payload.sample_anomalies.length, 2);
    assert.equal(payload.sample_anomalies[0].audit_decision, 'anomaly');
    assert.equal(payload.sample_anomalies[0].raw_exists, true);
    assert.deepEqual(
        Object.keys(payload.sample_anomalies[0]).sort(),
        [
            'audit_decision',
            'audit_reason',
            'away_team',
            'external_id',
            'home_team',
            'league_name',
            'match_date',
            'match_id',
            'match_status',
            'pipeline_status',
            'raw_created_at',
            'raw_data_version',
            'raw_exists',
            'raw_source_hint',
            'raw_updated_at',
            'season',
        ].sort(),
    );
    assert.equal(Object.prototype.hasOwnProperty.call(payload.sample_anomalies[0], 'raw_data'), false);
    assert.equal(Object.prototype.hasOwnProperty.call(payload.sample_anomalies[0], 'raw_payload'), false);
    assert.equal(Object.prototype.hasOwnProperty.call(payload.sample_anomalies[0], 'body'), false);
});

test('script source does not contain write SQL keywords or forbidden imports', () => {
    const source = fs.readFileSync(SCRIPT_PATH, 'utf8');

    assert.doesNotMatch(source, /\b(INSERT|UPDATE|UPSERT|DELETE|TRUNCATE|CREATE|ALTER|DROP)\b/i);
    assert.doesNotMatch(source, /FotMobRawDetailFetcher/);
    assert.doesNotMatch(source, /n3_live_fotmob_raw_retain/);
    assert.doesNotMatch(source, /l2_raw_match_data_write/);
});
