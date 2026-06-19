'use strict';

// lifecycle: permanent
// scope: unit safety coverage for read-only training eligibility after score dry-run

const test = require('node:test');
const assert = require('node:assert/strict');

const {
    parseArgs,
    assertSelectOnlySql,
    normalizeOptionalText,
    isTargetScope,
    evaluateRow,
    countDistribution,
    countByReason,
    buildDryRunPayload,
    runDryRun,
    READ_ONLY_BEGIN_SQL,
    READ_ONLY_ROLLBACK_SQL,
} = require('../../scripts/ops/training_eligibility_after_score_dry_run');

function buildTargetRow(overrides = {}) {
    return {
        match_id: '53_20252026_4830458',
        external_id: '4830458',
        league_name: 'Ligue 1',
        season: '2025/2026',
        status: 'finished',
        pipeline_status: 'harvested',
        source_type: 'fotmob_live_fetch',
        evidence_level: 'strong',
        is_production_scope: true,
        is_reconciliation_eligible: true,
        is_training_eligible: false,
        pipeline_status_reason: null,
        home_score: 2,
        away_score: 1,
        actual_result: 'home_win',
        ...overrides,
    };
}

function buildExcludedRows() {
    return [
        {
            match_id: '47_20242025_900002',
            external_id: '900002',
            league_name: 'Segunda',
            season: '2024/2025',
            status: 'finished',
            pipeline_status: 'pending',
            source_type: 'synthetic',
            evidence_level: 'synthetic_invalid',
            is_production_scope: false,
            is_reconciliation_eligible: false,
            is_training_eligible: false,
            pipeline_status_reason: 'no_raw',
            home_score: 1,
            away_score: 0,
            actual_result: 'home_win',
        },
        {
            match_id: '140_20252026_4837496',
            external_id: '4837496',
            league_name: 'Segunda División',
            season: '2025/2026',
            status: 'scheduled',
            pipeline_status: 'pending',
            source_type: 'synthetic',
            evidence_level: 'synthetic_invalid',
            is_production_scope: false,
            is_reconciliation_eligible: false,
            is_training_eligible: false,
            pipeline_status_reason: 'no_raw',
            home_score: null,
            away_score: null,
            actual_result: null,
        },
    ];
}

function createMockClient(rows) {
    const calls = [];

    return {
        calls,
        async query(sql, params = []) {
            calls.push({ sql: String(sql), params });

            const normalized = String(sql).replace(/\s+/g, ' ').trim();
            if (normalized === READ_ONLY_BEGIN_SQL || normalized === READ_ONLY_ROLLBACK_SQL) {
                return { rows: [] };
            }

            if (normalized.startsWith('SELECT')) {
                return { rows };
            }

            throw new Error(`Unexpected SQL in test mock: ${normalized.slice(0, 80)}`);
        },
    };
}

test('parseArgs supports --json and --help', () => {
    const jsonOpts = parseArgs(['--json']);
    assert.equal(jsonOpts.json, true);

    const helpOpts = parseArgs(['--help']);
    assert.equal(helpOpts.help, true);

    const defaultOpts = parseArgs([]);
    assert.equal(defaultOpts.json, false);
    assert.equal(defaultOpts.help, false);
});

test('assertSelectOnlySql rejects non-select and allows WITH/ROLLBACK', () => {
    assert.doesNotThrow(() => assertSelectOnlySql('SELECT 1'));
    assert.doesNotThrow(() => assertSelectOnlySql('ROLLBACK'));
    assert.throws(() => assertSelectOnlySql('COMMIT'));
    assert.throws(() => assertSelectOnlySql('DROP TABLE x'));
});

test('isTargetScope identifies Ligue 1 2025/2026', () => {
    assert.equal(isTargetScope({ league_name: 'Ligue 1', season: '2025/2026' }), true);
    assert.equal(isTargetScope({ league_name: 'Premier League', season: '2025/2026' }), false);
    assert.equal(isTargetScope({ league_name: 'Ligue 1', season: '2024/2025' }), false);
});

test('evaluateRow marks a fully qualified Ligue 1 row as would_set_true', () => {
    const result = evaluateRow(buildTargetRow());

    assert.equal(result.would_set_true, true);
    assert.deepEqual(result.skip_reasons, []);
    assert.equal(result.validations.status_finished, true);
    assert.equal(result.validations.pipeline_status_harvested, true);
    assert.equal(result.validations.source_type_fotmob_live_fetch, true);
    assert.equal(result.validations.evidence_level_strong, true);
    assert.equal(result.validations.is_production_scope_true, true);
    assert.equal(result.validations.is_reconciliation_eligible_true, true);
    assert.equal(result.validations.home_score_not_null, true);
    assert.equal(result.validations.away_score_not_null, true);
    assert.equal(result.validations.actual_result_valid, true);
    assert.equal(result.validations.pipeline_status_reason_null, true);
    assert.equal(result.validations.currently_training_eligible_false, true);
});

test('evaluateRow returns would_set_true=false with reasons for excluded rows', () => {
    const excluded = buildExcludedRows();

    const result0 = evaluateRow(excluded[0]);
    assert.equal(result0.would_set_true, false);
    assert.ok(result0.skip_reasons.includes('excluded_non_target_scope'));
    assert.ok(result0.skip_reasons.includes('pipeline_status_not_harvested'));
    assert.ok(result0.skip_reasons.includes('source_type_not_fotmob_live_fetch'));
    assert.ok(result0.skip_reasons.includes('evidence_level_not_strong'));

    const result1 = evaluateRow(excluded[1]);
    assert.equal(result1.would_set_true, false);
    assert.ok(result1.skip_reasons.includes('status_not_finished'));
    assert.ok(result1.skip_reasons.includes('home_score_null'));
    assert.ok(result1.skip_reasons.includes('actual_result_invalid_or_null'));
});

test('evaluateRow catches null home_score even when other fields pass', () => {
    const result = evaluateRow(buildTargetRow({ home_score: null }));

    assert.equal(result.would_set_true, false);
    assert.ok(result.skip_reasons.includes('home_score_null'));
    assert.equal(result.validations.home_score_not_null, false);
});

test('evaluateRow catches null away_score even when other fields pass', () => {
    const result = evaluateRow(buildTargetRow({ away_score: null }));

    assert.equal(result.would_set_true, false);
    assert.ok(result.skip_reasons.includes('away_score_null'));
});

test('evaluateRow catches invalid actual_result', () => {
    const result = evaluateRow(buildTargetRow({ actual_result: null }));

    assert.equal(result.would_set_true, false);
    assert.ok(result.skip_reasons.includes('actual_result_invalid_or_null'));
});

test('evaluateRow catches non-null pipeline_status_reason', () => {
    const result = evaluateRow(buildTargetRow({ pipeline_status_reason: 'blocked' }));

    assert.equal(result.would_set_true, false);
    assert.ok(result.skip_reasons.includes('pipeline_status_reason_not_null'));
});

test('evaluateRow handles already-eligible row correctly', () => {
    const result = evaluateRow(buildTargetRow({ is_training_eligible: true }));

    assert.equal(result.would_set_true, false);
    assert.ok(result.skip_reasons.includes('already_training_eligible_true'));
});

test('buildDryRunPayload summarizes target scope, eligibility, and false reasons', () => {
    const classifiedRows = [
        { ...buildTargetRow(), ...evaluateRow(buildTargetRow()), is_target_scope: true, actual_result: 'home_win' },
        { ...buildTargetRow({
            match_id: '53_20252026_4830459',
            external_id: '4830459',
            home_score: 1,
            away_score: 1,
            actual_result: 'draw',
        }), ...evaluateRow(buildTargetRow({
            match_id: '53_20252026_4830459',
            external_id: '4830459',
            home_score: 1,
            away_score: 1,
            actual_result: 'draw',
        })), is_target_scope: true, actual_result: 'draw' },
        { ...buildTargetRow({
            match_id: '53_20252026_4830460',
            external_id: '4830460',
            home_score: 0,
            away_score: 2,
            actual_result: 'away_win',
        }), ...evaluateRow(buildTargetRow({
            match_id: '53_20252026_4830460',
            external_id: '4830460',
            home_score: 0,
            away_score: 2,
            actual_result: 'away_win',
        })), is_target_scope: true, actual_result: 'away_win' },
        ...buildExcludedRows().map(row => ({
            ...row,
            ...evaluateRow(row),
            is_target_scope: false,
            actual_result: row.actual_result,
        })),
    ];

    const payload = buildDryRunPayload(classifiedRows);

    assert.equal(payload.total_matches_scanned, 5);
    assert.equal(payload.target_ligue1_count, 3);
    assert.equal(payload.would_set_true_count, 3);
    assert.equal(payload.would_keep_false_count, 2);
    assert.deepEqual(payload.actual_result_distribution, {
        home_win: 1,
        draw: 1,
        away_win: 1,
    });
    assert.ok(Object.keys(payload.by_reason).length > 0);
    assert.equal(payload.sample_true.length, 3);
    assert.equal(payload.sample_false.length, 2);
    assert.equal(payload.safety.db_write_allowed, false);
    assert.equal(payload.safety.read_only_transaction_used, true);
});

test('runDryRun uses read-only SQL and returns the expected dry-run safety shape', async () => {
    const rows = [
        buildTargetRow(),
        buildTargetRow({
            match_id: '53_20252026_4830459',
            external_id: '4830459',
            home_score: 1,
            away_score: 1,
            actual_result: 'draw',
        }),
        ...buildExcludedRows(),
    ];
    const mockClient = createMockClient(rows);

    const payload = await runDryRun(
        {},
        { client: mockClient }
    );

    assert.equal(payload.mode, 'dry_run');
    assert.equal(payload.actual_update_executed, false);
    assert.equal(payload.total_matches_scanned, 4);
    assert.equal(payload.target_ligue1_count, 2);
    assert.equal(payload.would_set_true_count, 2);
    assert.equal(payload.would_keep_false_count, 2);
    assert.equal(payload.current_training_eligible_true, 0);
    assert.equal(payload.safety.db_write_allowed, false);
    assert.equal(payload.safety.read_only_transaction_used, true);
    assert.equal(mockClient.calls.length, 3);
    assert.equal(mockClient.calls[0].sql.trim(), READ_ONLY_BEGIN_SQL);
    assert.match(mockClient.calls[1].sql.trim(), /^SELECT/);
    assert.equal(mockClient.calls[2].sql.trim(), READ_ONLY_ROLLBACK_SQL);
});
