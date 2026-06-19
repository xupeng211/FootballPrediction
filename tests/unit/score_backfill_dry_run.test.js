'use strict';

// lifecycle: permanent
// scope: unit safety coverage for read-only score backfill dry-run

const test = require('node:test');
const assert = require('node:assert/strict');

const {
    parseArgs,
    assertSelectOnlySql,
    parseScoreStr,
    deriveActualResult,
    classifyScannedMatch,
    buildDryRunPayload,
    runDryRun,
    READ_ONLY_BEGIN_SQL,
    READ_ONLY_ROLLBACK_SQL,
} = require('../../scripts/ops/score_backfill_dry_run');

function buildTargetRow(overrides = {}) {
    return {
        match_id: '53_20252026_4830466',
        external_id: '4830466',
        league_name: 'Ligue 1',
        season: '2025/2026',
        status: 'finished',
        pipeline_status: 'harvested',
        source_type: 'fotmob_live_fetch',
        evidence_level: 'strong',
        home_score: null,
        away_score: null,
        actual_result: null,
        fotmob_live_v1_count: 1,
        fotmob_live_v1_data_version: 'fotmob_live_v1',
        raw_score_str: '2 - 1',
        raw_home_score_text: '2',
        raw_away_score_text: '1',
        ...overrides,
    };
}

function buildNoRawExcludedRows() {
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
            home_score: 1,
            away_score: 0,
            actual_result: 'home_win',
            fotmob_live_v1_count: 0,
            fotmob_live_v1_data_version: null,
            raw_score_str: null,
            raw_home_score_text: null,
            raw_away_score_text: null,
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
            home_score: null,
            away_score: null,
            actual_result: null,
            fotmob_live_v1_count: 0,
            fotmob_live_v1_data_version: null,
            raw_score_str: null,
            raw_home_score_text: null,
            raw_away_score_text: null,
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

            if (normalized.startsWith('WITH fotmob_live_raw AS')) {
                return { rows };
            }

            throw new Error(`Unexpected SQL in test mock: ${normalized.slice(0, 80)}`);
        },
    };
}

test('parseArgs supports --json and --sample-limit', () => {
    const options = parseArgs(['--json', '--sample-limit', '7']);
    assert.equal(options.json, true);
    assert.equal(options.sampleLimit, 7);
});

test('assertSelectOnlySql rejects UPDATE and allows WITH/ROLLBACK', () => {
    assert.doesNotThrow(() => assertSelectOnlySql('WITH scoped AS (SELECT 1) SELECT * FROM scoped'));
    assert.doesNotThrow(() => assertSelectOnlySql('ROLLBACK'));
    assert.throws(() => assertSelectOnlySql('UPDATE matches SET home_score = 1'));
});

test('parseScoreStr parses 2 - 1 and deriveActualResult maps to repository vocabulary', () => {
    assert.deepEqual(parseScoreStr('2 - 1'), { home: 2, away: 1 });
    assert.equal(deriveActualResult(2, 1), 'home_win');
    assert.equal(deriveActualResult(1, 1), 'draw');
    assert.equal(deriveActualResult(0, 3), 'away_win');
});

test('classifyScannedMatch marks a Ligue 1 harvested row as would_update', () => {
    const classified = classifyScannedMatch(buildTargetRow());

    assert.equal(classified.target_scope, true);
    assert.equal(classified.would_update, true);
    assert.equal(classified.proposed_home_score, 2);
    assert.equal(classified.proposed_away_score, 1);
    assert.equal(classified.proposed_actual_result, 'home_win');
    assert.equal(classified.proposed_actual_result_hda, 'H');
    assert.deepEqual(classified.skip_reasons, []);
});

test('classifyScannedMatch blocks mismatched scoreStr even when team scores exist', () => {
    const classified = classifyScannedMatch(buildTargetRow({ raw_score_str: '9 - 9' }));

    assert.equal(classified.target_scope, true);
    assert.equal(classified.would_update, false);
    assert.equal(classified.validations.score_str_matches_team_scores, false);
    assert.ok(classified.skip_reasons.includes('score_str_mismatch'));
});

test('buildDryRunPayload summarizes target updates, result distribution, and no-raw exclusions', () => {
    const classifiedRows = [
        classifyScannedMatch(buildTargetRow({ match_id: '53_20252026_4830466', raw_score_str: '2 - 1' })),
        classifyScannedMatch(buildTargetRow({
            match_id: '53_20252026_4830467',
            external_id: '4830467',
            raw_score_str: '1 - 1',
            raw_home_score_text: '1',
            raw_away_score_text: '1',
        })),
        classifyScannedMatch(buildTargetRow({
            match_id: '53_20252026_4830468',
            external_id: '4830468',
            raw_score_str: '0 - 2',
            raw_home_score_text: '0',
            raw_away_score_text: '2',
        })),
        ...buildNoRawExcludedRows().map(classifyScannedMatch),
    ];

    const payload = buildDryRunPayload(classifiedRows, { sampleLimit: 5 });

    assert.equal(payload.total_matches_scanned, 5);
    assert.equal(payload.target_ligue1_count, 3);
    assert.equal(payload.would_update_count, 3);
    assert.equal(payload.would_skip_count, 2);
    assert.equal(payload.excluded_no_raw_count, 2);
    assert.deepEqual(payload.actual_result_distribution, {
        home_win: 1,
        draw: 1,
        away_win: 1,
    });
    assert.deepEqual(payload.auxiliary_result_distribution_hda, {
        H: 1,
        D: 1,
        A: 1,
    });
    assert.equal(payload.score_consistency_summary.score_str_mismatch_count, 0);
    assert.deepEqual(payload.excluded_no_raw_match_ids, [
        '47_20242025_900002',
        '140_20252026_4837496',
    ]);
});

test('runDryRun uses read-only SQL and returns the expected dry-run safety shape', async () => {
    const rows = [
        buildTargetRow(),
        buildTargetRow({
            match_id: '53_20252026_4830467',
            external_id: '4830467',
            raw_score_str: '1 - 1',
            raw_home_score_text: '1',
            raw_away_score_text: '1',
        }),
        ...buildNoRawExcludedRows(),
    ];
    const mockClient = createMockClient(rows);

    const payload = await runDryRun(
        { sampleLimit: 5 },
        { client: mockClient }
    );

    assert.equal(payload.mode, 'dry_run');
    assert.equal(payload.actual_update_executed, false);
    assert.equal(payload.total_matches_scanned, 4);
    assert.equal(payload.target_ligue1_count, 2);
    assert.equal(payload.would_update_count, 2);
    assert.equal(payload.would_skip_count, 2);
    assert.equal(payload.safety.db_write_allowed, false);
    assert.equal(payload.safety.read_only_transaction_used, true);
    assert.equal(mockClient.calls.length, 3);
    assert.equal(mockClient.calls[0].sql.trim(), READ_ONLY_BEGIN_SQL);
    assert.match(mockClient.calls[1].sql.trim(), /^WITH fotmob_live_raw AS/);
    assert.equal(mockClient.calls[2].sql.trim(), READ_ONLY_ROLLBACK_SQL);
});
