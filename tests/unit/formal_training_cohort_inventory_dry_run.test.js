'use strict';

// lifecycle: permanent
// scope: unit safety coverage for formal training cohort inventory dry-run

const test = require('node:test');
const assert = require('node:assert/strict');

const {
    READ_ONLY_BEGIN_SQL,
    READ_ONLY_ROLLBACK_SQL,
    EXPLICIT_EXCLUDED_MATCH_IDS,
    COUNTS_SQL,
    LEAGUE_SEASON_SQL,
    FINISHED_LABEL_DISTRIBUTION_SQL,
    TRAINING_ELIGIBLE_DISTRIBUTION_SQL,
    RAW_VERSION_SQL,
    MISSING_FIELDS_SQL,
    MATCHES_COLUMNS_SQL,
    FORMAL_CANDIDATES_SQL,
    EXCLUDED_MATCHES_SQL,
    parseArgs,
    assertSelectOnlySql,
    normalizeCountRow,
    normalizeLeagueSeasonRows,
    normalizeRawVersionRows,
    buildExcludedRows,
    buildThresholdGaps,
    buildSevereMissingFields,
    buildPayload,
    runDryRun,
} = require('../../scripts/ops/formal_training_cohort_inventory_dry_run');

function compact(sql) {
    return String(sql).replace(/\s+/g, ' ').trim();
}

function createMockClient(resultMap) {
    const calls = [];
    return {
        calls,
        async query(sql, params = []) {
            calls.push({ sql: String(sql), params });
            const normalized = compact(sql);

            if (normalized === READ_ONLY_BEGIN_SQL || normalized === READ_ONLY_ROLLBACK_SQL) {
                return { rows: [] };
            }
            if (normalized === compact(COUNTS_SQL)) {
                return { rows: [resultMap.counts] };
            }
            if (normalized === compact(LEAGUE_SEASON_SQL)) {
                return { rows: resultMap.leagueSeasonRows };
            }
            if (normalized === compact(FINISHED_LABEL_DISTRIBUTION_SQL)) {
                return { rows: resultMap.finishedLabelRows };
            }
            if (normalized === compact(TRAINING_ELIGIBLE_DISTRIBUTION_SQL)) {
                return { rows: resultMap.trainingEligibleRows };
            }
            if (normalized === compact(RAW_VERSION_SQL)) {
                return { rows: resultMap.rawVersionRows };
            }
            if (normalized === compact(MISSING_FIELDS_SQL)) {
                return { rows: [resultMap.missingFields] };
            }
            if (normalized === compact(MATCHES_COLUMNS_SQL)) {
                return { rows: resultMap.matchesColumns.map(column_name => ({ column_name })) };
            }
            if (normalized === compact(FORMAL_CANDIDATES_SQL)) {
                return { rows: resultMap.candidateRows };
            }
            if (normalized === compact(EXCLUDED_MATCHES_SQL)) {
                return { rows: resultMap.excludedRows };
            }

            throw new Error(`Unexpected SQL in test mock: ${normalized.slice(0, 120)}`);
        },
    };
}

function buildState() {
    return {
        counts: {
            total_matches: 60,
            finished_labeled_matches: 59,
            training_eligible_matches: 58,
            formal_candidate_matches: 58,
            raw_match_data_rows: 76,
            raw_match_data_distinct_matches: 60,
            fotmob_pageprops_v2_rows: 8,
            fotmob_pageprops_v2_matches: 8,
            odds_rows: 2,
            odds_matches: 1,
            formal_candidates_with_odds: 1,
            formal_candidates_with_pageprops_v2: 8,
        },
        league_season_coverage: [
            {
                league_name: 'Ligue 1',
                season: '2025/2026',
                matches: 58,
                finished_labeled: 58,
                training_eligible: 58,
                formal_candidates: 58,
            },
            {
                league_name: 'Segunda',
                season: '2024/2025',
                matches: 1,
                finished_labeled: 1,
                training_eligible: 0,
                formal_candidates: 0,
            },
        ],
        finished_label_distribution: [
            { league_name: 'Ligue 1', season: '2025/2026', actual_result: 'home_win', count: 23 },
            { league_name: 'Ligue 1', season: '2025/2026', actual_result: 'draw', count: 17 },
            { league_name: 'Ligue 1', season: '2025/2026', actual_result: 'away_win', count: 18 },
        ],
        training_eligible_distribution: [
            { league_name: 'Ligue 1', season: '2025/2026', actual_result: 'home_win', count: 23 },
            { league_name: 'Ligue 1', season: '2025/2026', actual_result: 'draw', count: 17 },
            { league_name: 'Ligue 1', season: '2025/2026', actual_result: 'away_win', count: 18 },
        ],
        raw_version_distribution: [
            {
                raw_version: 'fotmob_live_v1',
                source_version: 'unknown',
                hash_strategy: 'unknown',
                rows: 58,
                distinct_matches: 58,
            },
            {
                raw_version: 'fotmob_pageprops_v2',
                source_version: 'unknown',
                hash_strategy: 'stable_pageprops_payload_v1',
                rows: 8,
                distinct_matches: 8,
            },
        ],
        missing_fields: {
            total_matches: 60,
            external_id_missing: 0,
            league_name_missing: 0,
            season_missing: 0,
            home_team_missing: 0,
            away_team_missing: 0,
            match_date_missing: 0,
            venue_missing: 58,
            referee_missing: 58,
            finished_score_missing: 0,
            finished_label_missing: 0,
            training_eligible_label_missing: 0,
            training_eligible_not_finished: 0,
        },
        matches_columns: [
            'match_id',
            'external_id',
            'league_name',
            'season',
            'home_team',
            'away_team',
            'home_score',
            'away_score',
            'actual_result',
            'match_date',
            'venue',
            'status',
            'is_finished',
            'referee',
        ],
        formal_cohort_candidates: [
            {
                match_id: '53_20252026_4830458',
                external_id: '4830458',
                league_name: 'Ligue 1',
                season: '2025/2026',
                home_team: 'Rennes',
                away_team: 'Marseille',
                match_date: '2025-08-15 18:45:00+00',
                actual_result: 'home_win',
                has_fotmob_pageprops_v2: false,
                has_odds: false,
            },
        ],
        explicit_exclusions: buildExcludedRows([
            {
                match_id: '47_20242025_900002',
                external_id: '900002',
                league_name: 'Segunda',
                season: '2024/2025',
                home_team: 'Burgos',
                away_team: 'Oviedo',
                status: 'finished',
                actual_result: 'home_win',
                source_type: 'synthetic',
                evidence_level: 'synthetic_invalid',
                is_production_scope: false,
                is_reconciliation_eligible: false,
                is_training_eligible: false,
                pipeline_status: 'pending',
                pipeline_status_reason: 'no_raw',
                has_raw: true,
                has_fotmob_pageprops_v2: false,
                has_odds: false,
            },
            {
                match_id: '140_20252026_4837496',
                external_id: '4837496',
                league_name: 'Segunda Division',
                season: '2025/2026',
                home_team: 'Cultural Leonesa',
                away_team: 'Burgos',
                status: 'scheduled',
                actual_result: null,
                source_type: 'synthetic',
                evidence_level: 'synthetic_invalid',
                is_production_scope: false,
                is_reconciliation_eligible: false,
                is_training_eligible: false,
                pipeline_status: 'pending',
                pipeline_status_reason: 'no_raw',
                has_raw: true,
                has_fotmob_pageprops_v2: false,
                has_odds: true,
            },
        ]),
    };
}

test('parseArgs supports --json and --help', () => {
    assert.equal(parseArgs(['--json']).json, true);
    assert.equal(parseArgs(['--help']).help, true);
    assert.equal(parseArgs([]).json, false);
});

test('assertSelectOnlySql rejects writes and commits', () => {
    assert.doesNotThrow(() => assertSelectOnlySql('SELECT 1'));
    assert.doesNotThrow(() => assertSelectOnlySql('WITH x AS (SELECT 1) SELECT * FROM x'));
    assert.doesNotThrow(() => assertSelectOnlySql('ROLLBACK'));
    assert.throws(() => assertSelectOnlySql(['UPDATE', 'matches', 'SET status = status'].join(' ')));
    assert.throws(() => assertSelectOnlySql('COMMIT'));
});

test('normalizers coerce database count strings', () => {
    assert.deepEqual(normalizeCountRow({ total_matches: '60', odds_rows: null }), {
        total_matches: 60,
        odds_rows: 0,
    });
    assert.deepEqual(
        normalizeLeagueSeasonRows([{ league_name: 'Ligue 1', season: '2025/2026', matches: '58', finished_labeled: '58', training_eligible: '58', formal_candidates: '58' }]),
        [{ league_name: 'Ligue 1', season: '2025/2026', matches: 58, finished_labeled: 58, training_eligible: 58, formal_candidates: 58 }]
    );
    assert.deepEqual(
        normalizeRawVersionRows([{ raw_version: 'fotmob_pageprops_v2', source_version: 'unknown', hash_strategy: 'stable_pageprops_payload_v1', rows: '8', distinct_matches: '8' }]),
        [{ raw_version: 'fotmob_pageprops_v2', source_version: 'unknown', hash_strategy: 'stable_pageprops_payload_v1', rows: 8, distinct_matches: 8 }]
    );
});

test('threshold gaps are computed from formal candidate count', () => {
    assert.deepEqual(buildThresholdGaps(58), [
        { threshold: 1500, current_formal_candidate_matches: 58, gap: 1442, reached: false },
        { threshold: 3000, current_formal_candidate_matches: 58, gap: 2942, reached: false },
        { threshold: 5000, current_formal_candidate_matches: 58, gap: 4942, reached: false },
    ]);
});

test('explicit exclusions preserve required blocker reasons', () => {
    const excluded = buildState().explicit_exclusions;

    assert.deepEqual(excluded.map(row => row.match_id), EXPLICIT_EXCLUDED_MATCH_IDS);
    assert.equal(excluded[0].must_exclude, true);
    assert.equal(excluded[0].reason, 'synthetic_invalid_legacy_sample_not_real_fotmob_evidence');
    assert.equal(excluded[1].reason, 'scheduled_or_no_valid_outcome_with_synthetic_invalid_evidence');
});

test('buildSevereMissingFields reports schema and coverage blockers', () => {
    const state = buildState();
    const missing = buildSevereMissingFields(state);
    const fields = missing.map(row => row.field);

    assert.ok(fields.includes('home_team_id'));
    assert.ok(fields.includes('prediction_cutoff_time'));
    assert.ok(fields.includes('venue_missing'));
    assert.ok(fields.includes('fotmob_pageprops_v2_coverage'));
    assert.ok(fields.includes('odds_coverage'));
});

test('buildPayload includes inventory, candidates, exclusions, and safety', () => {
    const payload = buildPayload(buildState());

    assert.equal(payload.mode, 'dry_run');
    assert.equal(payload.actual_update_executed, false);
    assert.equal(payload.current_counts.formal_candidate_matches, 58);
    assert.equal(payload.volume_threshold_gaps[1].gap, 2942);
    assert.equal(payload.conclusion.current_58_rows_are_smoke_or_integration_only, true);
    assert.equal(payload.conclusion.formal_training_allowed_now, false);
    assert.equal(payload.conclusion.next_step_is_training, false);
    assert.equal(payload.conclusion.should_enter_multi_league_multi_season_expansion, true);
    assert.equal(payload.formal_cohort_candidates.match_ids[0], '53_20252026_4830458');
    assert.equal(payload.must_exclude_matches.length, 2);
    assert.equal(payload.safety.db_write_executed, false);
    assert.equal(payload.safety.live_fetch_executed, false);
    assert.equal(payload.safety.model_training_performed, false);
    assert.equal(payload.safety.governance_conclusion_changed, false);
});

test('runDryRun uses BEGIN READ ONLY, SELECT/WITH queries, and ROLLBACK only', async () => {
    const state = buildState();
    const mockClient = createMockClient({
        counts: state.counts,
        leagueSeasonRows: state.league_season_coverage,
        finishedLabelRows: state.finished_label_distribution,
        trainingEligibleRows: state.training_eligible_distribution,
        rawVersionRows: state.raw_version_distribution,
        missingFields: state.missing_fields,
        matchesColumns: state.matches_columns,
        candidateRows: state.formal_cohort_candidates,
        excludedRows: state.explicit_exclusions,
    });

    const payload = await runDryRun({}, { client: mockClient });

    assert.equal(payload.formal_cohort_candidates.count, 58);
    assert.equal(mockClient.calls.length, 11);
    assert.equal(mockClient.calls[0].sql.trim(), READ_ONLY_BEGIN_SQL);
    assert.equal(mockClient.calls[10].sql.trim(), READ_ONLY_ROLLBACK_SQL);
    assert.deepEqual(mockClient.calls[1].params, [EXPLICIT_EXCLUDED_MATCH_IDS]);
    assert.deepEqual(mockClient.calls[2].params, [EXPLICIT_EXCLUDED_MATCH_IDS]);
    assert.deepEqual(mockClient.calls[8].params, [EXPLICIT_EXCLUDED_MATCH_IDS]);
    assert.deepEqual(mockClient.calls[9].params, [EXPLICIT_EXCLUDED_MATCH_IDS]);
    for (const call of mockClient.calls.slice(1, 10)) {
        assert.match(call.sql.trim(), /^(SELECT|WITH)/);
    }
});
