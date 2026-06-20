'use strict';

// lifecycle: permanent
// scope: unit safety coverage for formal training dataset design dry-run

const test = require('node:test');
const assert = require('node:assert/strict');

const {
    TARGET_SCOPE,
    MINIMUM_RECOMMENDATION,
    DIRECT_SAFE_FEATURES,
    DERIVED_FEATURE_CANDIDATES,
    LEAKAGE_FORBIDDEN_FEATURES,
    TEMPORAL_CUTOFF_RULES,
    DATASET_BUILDER_DESIGN,
    NEXT_RECOMMENDED_TASK,
    READ_ONLY_BEGIN_SQL,
    READ_ONLY_ROLLBACK_SQL,
    COUNTS_SQL,
    SCOPE_SQL,
    RAW_VERSION_SQL,
    SMOKE_QUALITY_SQL,
    TRAINING_FEATURE_STATE_SQL,
    PREDICTION_STATE_SQL,
    MATCHES_COLUMNS_SQL,
    parseArgs,
    assertSelectOnlySql,
    normalizeCountsRow,
    normalizeScopeRows,
    normalizeRawVersionRows,
    normalizeColumnRows,
    buildCurrentSampleLimitations,
    buildMissingDataBlockers,
    buildPayload,
    runDryRun,
} = require('../../scripts/ops/formal_training_dataset_design_dry_run');

function createMockClient(resultMap) {
    const calls = [];
    return {
        calls,
        async query(sql, params = []) {
            calls.push({ sql: String(sql), params });
            const normalized = String(sql).replace(/\s+/g, ' ').trim();

            if (normalized === READ_ONLY_BEGIN_SQL || normalized === READ_ONLY_ROLLBACK_SQL) {
                return { rows: [] };
            }
            if (normalized === COUNTS_SQL.replace(/\s+/g, ' ').trim()) {
                return { rows: [resultMap.counts] };
            }
            if (normalized === SCOPE_SQL.replace(/\s+/g, ' ').trim()) {
                return { rows: resultMap.scopeRows };
            }
            if (normalized === RAW_VERSION_SQL.replace(/\s+/g, ' ').trim()) {
                return { rows: resultMap.rawVersionRows };
            }
            if (normalized === SMOKE_QUALITY_SQL.replace(/\s+/g, ' ').trim()) {
                return { rows: [resultMap.smokeQuality] };
            }
            if (normalized === TRAINING_FEATURE_STATE_SQL.replace(/\s+/g, ' ').trim()) {
                return { rows: [resultMap.trainingFeatureState] };
            }
            if (normalized === PREDICTION_STATE_SQL.replace(/\s+/g, ' ').trim()) {
                return { rows: [resultMap.predictionState] };
            }
            if (normalized === MATCHES_COLUMNS_SQL.replace(/\s+/g, ' ').trim()) {
                return { rows: resultMap.matchesColumns.map(column_name => ({ column_name })) };
            }

            throw new Error(`Unexpected SQL in test mock: ${normalized.slice(0, 120)}`);
        },
    };
}

function buildState() {
    return {
        counts: {
            matches: 60,
            raw_match_data: 76,
            bookmaker_odds_history: 2,
            l3_features: 2,
            match_features_training: 2,
            predictions: 2,
            training_eligible_matches: 58,
            finished_labeled_matches: 59,
            matches_with_raw: 60,
            matches_with_l3: 2,
            matches_with_training_features: 2,
            matches_with_odds: 1,
            full_feature_chain_rows: 1,
        },
        scope_rows: [
            {
                league_name: 'Ligue 1',
                season: '2025/2026',
                matches: 58,
                training_eligible: 58,
                labeled: 58,
                finished: 58,
            },
            {
                league_name: 'Segunda',
                season: '2024/2025',
                matches: 1,
                training_eligible: 0,
                labeled: 1,
                finished: 1,
            },
        ],
        raw_version_rows: [
            { data_version: 'fotmob_live_v1', rows: 58, distinct_matches: 58 },
            { data_version: 'fotmob_html_hyd_v1', rows: 8, distinct_matches: 8 },
            { data_version: 'fotmob_pageprops_v2', rows: 8, distinct_matches: 8 },
            { data_version: 'PHASE4.43_SYNTHETIC', rows: 1, distinct_matches: 1 },
        ],
        smoke_quality: {
            sample_count: 58,
            target_scope_rows: 58,
            venue_missing: 58,
            referee_missing: 58,
        },
        training_feature_state: {
            total_rows: 2,
            non_finished_rows: 1,
            unlabeled_rows: 1,
            zero_feature_count_rows: 2,
        },
        prediction_state: {
            total_rows: 2,
            non_finished_rows: 1,
            unlabeled_rows: 1,
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
        ],
    };
}

test('parseArgs supports --json and --help', () => {
    assert.equal(parseArgs(['--json']).json, true);
    assert.equal(parseArgs(['--help']).help, true);
    assert.equal(parseArgs([]).json, false);
});

test('assertSelectOnlySql rejects non-select SQL', () => {
    assert.doesNotThrow(() => assertSelectOnlySql('SELECT 1'));
    assert.doesNotThrow(() => assertSelectOnlySql('ROLLBACK'));
    assert.throws(() => assertSelectOnlySql('COMMIT'));
    assert.throws(() => assertSelectOnlySql(['UPDATE', 'matches', 'SET status = 1'].join(' ')));
});

test('design constants expose expected families and policies', () => {
    assert.equal(TARGET_SCOPE.league_name, 'Ligue 1');
    assert.equal(MINIMUM_RECOMMENDATION.formal_baseline_matches, 3000);
    assert.ok(DIRECT_SAFE_FEATURES.available_now_in_matches.length >= 5);
    assert.ok(DERIVED_FEATURE_CANDIDATES.some(item => item.family === 'elo_strength'));
    assert.ok(LEAKAGE_FORBIDDEN_FEATURES.some(item => item.field_or_family === 'matches.actual_result'));
    assert.equal(TEMPORAL_CUTOFF_RULES.horizons.length, 4);
    assert.equal(DATASET_BUILDER_DESIGN.split_strategy.policy, 'chronological_only');
    assert.equal(NEXT_RECOMMENDED_TASK.requires_user_confirmation, true);
});

test('normalize helpers convert query rows to numeric state', () => {
    assert.deepEqual(
        normalizeCountsRow({ matches: '60', raw_match_data: '76' }),
        { matches: 60, raw_match_data: 76 }
    );
    assert.deepEqual(
        normalizeScopeRows([{ league_name: 'Ligue 1', season: '2025/2026', matches: '58', training_eligible: '58', labeled: '58', finished: '58' }]),
        [{ league_name: 'Ligue 1', season: '2025/2026', matches: 58, training_eligible: 58, labeled: 58, finished: 58 }]
    );
    assert.deepEqual(
        normalizeRawVersionRows([{ data_version: 'fotmob_live_v1', rows: '58', distinct_matches: '58' }]),
        [{ data_version: 'fotmob_live_v1', rows: 58, distinct_matches: 58 }]
    );
    assert.deepEqual(
        normalizeColumnRows([{ column_name: 'match_id' }, { column_name: 'home_team' }]),
        ['match_id', 'home_team']
    );
});

test('buildCurrentSampleLimitations captures the main blockers', () => {
    const limitations = buildCurrentSampleLimitations(buildState());
    const codes = limitations.map(item => item.code);

    assert.ok(codes.includes('smoke_only_sample_size'));
    assert.ok(codes.includes('mixed_raw_provenance'));
    assert.ok(codes.includes('identity_contract_gap'));
    assert.ok(limitations.some(item => /venue missing=58\/58/.test(item.detail)));
});

test('buildMissingDataBlockers highlights scale and cutoff gaps', () => {
    const blockers = buildMissingDataBlockers(buildState());
    const blockerNames = blockers.map(item => item.blocker);

    assert.ok(blockerNames.includes('historical_match_volume_missing'));
    assert.ok(blockerNames.includes('odds_history_gap'));
    assert.ok(blockers.some(item => /3000/.test(item.detail)));
});

test('buildPayload includes required top-level dry-run keys', () => {
    const payload = buildPayload(buildState());

    assert.equal(payload.mode, 'dry_run');
    assert.equal(payload.actual_update_executed, false);
    assert.equal(payload.current_training_eligible_count, 58);
    assert.equal(payload.recommended_min_sample_size.formal_baseline_matches, 3000);
    assert.equal(payload.recommended_competitions.preferred_official_set.length, 5);
    assert.ok(payload.direct_safe_features.available_now_in_matches.length >= 5);
    assert.ok(payload.derived_feature_candidates.length >= 6);
    assert.ok(payload.leakage_forbidden_features.length >= 10);
    assert.equal(payload.temporal_cutoff_rules.horizons[0].prediction_horizon, 'T_MINUS_24H');
    assert.equal(payload.dataset_builder_design.dataset_grain, 'one row per match_id per prediction_horizon');
    assert.equal(payload.next_recommended_task.task_id, 'formal_training_cohort_inventory_dry_run');
    assert.equal(payload.safety.db_write_executed, false);
});

test('runDryRun uses BEGIN READ ONLY, SELECTs, and ROLLBACK only', async () => {
    const state = buildState();
    const mockClient = createMockClient({
        counts: state.counts,
        scopeRows: state.scope_rows,
        rawVersionRows: state.raw_version_rows,
        smokeQuality: state.smoke_quality,
        trainingFeatureState: state.training_feature_state,
        predictionState: state.prediction_state,
        matchesColumns: state.matches_columns,
    });

    const payload = await runDryRun({}, { client: mockClient });

    assert.equal(payload.current_training_eligible_count, 58);
    assert.equal(mockClient.calls.length, 9);
    assert.equal(mockClient.calls[0].sql.trim(), READ_ONLY_BEGIN_SQL);
    assert.deepEqual(mockClient.calls[4].params, [TARGET_SCOPE.league_name, TARGET_SCOPE.season]);
    assert.equal(mockClient.calls[8].sql.trim(), READ_ONLY_ROLLBACK_SQL);
    for (const call of mockClient.calls.slice(1, 8)) {
        assert.match(call.sql.trim(), /^(SELECT|WITH)/);
    }
});
