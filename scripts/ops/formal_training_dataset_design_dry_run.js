#!/usr/bin/env node
'use strict';
/* eslint-disable max-lines */

// lifecycle: permanent
// scope: read-only formal training dataset design and readiness dry-run

const PHASE = 'FORMAL_TRAINING_DATASET_DESIGN_DRY_RUN';
const READ_ONLY_BEGIN_SQL = 'BEGIN READ ONLY';
const READ_ONLY_ROLLBACK_SQL = 'ROLLBACK';

const TARGET_SCOPE = Object.freeze({
    league_name: 'Ligue 1',
    season: '2025/2026',
});

const MINIMUM_RECOMMENDATION = Object.freeze({
    absolute_pilot_floor_matches: 1500,
    formal_baseline_matches: 3000,
    preferred_stable_matches: 5000,
    minimum_competitions: 3,
    preferred_competitions: 5,
    minimum_completed_seasons_per_competition: 3,
});

const RECOMMENDED_COMPETITIONS = Object.freeze({
    minimum_set: [
        'Premier League',
        'La Liga',
        'Ligue 1',
    ],
    preferred_official_set: [
        'Premier League',
        'La Liga',
        'Serie A',
        'Bundesliga',
        'Ligue 1',
    ],
    rationale: [
        'Top-five leagues are the richest current-quality target for schedule, identity, and downstream feature completeness.',
        'A minimum three-competition set reduces league-specific bias while remaining operationally smaller than a full Europe-wide acquisition.',
    ],
});

const RECOMMENDED_SEASONS = Object.freeze({
    minimum_completed_seasons_per_competition: 3,
    preferred_training_seasons: [
        '2022/2023',
        '2023/2024',
        '2024/2025',
    ],
    preferred_initial_out_of_time_test_season: '2025/2026 (only after full acquisition and dataset freeze)',
    time_range_policy: [
        'Use only completed seasons for the first official training baseline.',
        'Keep the newest fully acquired season as the first out-of-time test window instead of mixing it into the initial training fit.',
        'Do not mix older and newer matches with random splits; all splits must remain chronological.',
    ],
});

const DIRECT_SAFE_FEATURES = Object.freeze({
    available_now_in_matches: [
        {
            field: 'league_name',
            source: 'matches',
            readiness: 'available_now',
            note: 'Competition identity; encode categorically.',
        },
        {
            field: 'season',
            source: 'matches',
            readiness: 'available_now',
            note: 'Season identity; also derive season phase once round coverage exists.',
        },
        {
            field: 'home_team',
            source: 'matches',
            readiness: 'available_now',
            note: 'Safe as identity context only; historical strength features must be derived with strict time gating.',
        },
        {
            field: 'away_team',
            source: 'matches',
            readiness: 'available_now',
            note: 'Same constraint as home_team.',
        },
        {
            field: 'match_date',
            source: 'matches',
            readiness: 'available_now',
            note: 'Use for kickoff timestamp and derived calendar features.',
        },
        {
            field: 'venue',
            source: 'matches',
            readiness: 'available_but_currently_missing',
            note: 'Currently 100% missing in the 58-row smoke scope; keep optional until populated.',
        },
        {
            field: 'referee',
            source: 'matches',
            readiness: 'available_but_currently_missing',
            note: 'Currently 100% missing in the 58-row smoke scope; use only if appointment is known before cutoff.',
        },
    ],
    metadata_only_not_model_x: [
        'match_id',
        'external_id',
        'future canonical home_team_id from raw identity parser',
        'future canonical away_team_id from raw identity parser',
        'future canonical league_id from raw identity parser',
    ],
    conditional_timestamped_raw_candidates: [
        {
            family: 'table_snapshot_context',
            source: 'raw_match_data.fotmob_pageprops_v2',
            rule: 'table_snapshot_at <= prediction_cutoff_time',
            note: 'Only safe if snapshot time is preserved and verified pre-kickoff.',
        },
        {
            family: 'historical_h2h_context',
            source: 'raw_match_data.fotmob_pageprops_v2',
            rule: 'all referenced matches must have event_time < kickoff_time and snapshot_at <= prediction_cutoff_time',
            note: 'Must exclude current-fixture echo and any future-contaminated rows.',
        },
        {
            family: 'confirmed_lineup_context',
            source: 'raw_match_data.fotmob_pageprops_v2',
            rule: 'lineup_timestamp <= prediction_cutoff_time',
            note: 'Allowed only for late-horizon models such as T-1h or near-kickoff.',
        },
    ],
});

const DERIVED_FEATURE_CANDIDATES = Object.freeze([
    {
        family: 'elo_strength',
        priority: 'P0',
        example_features: [
            'home_pre_match_elo',
            'away_pre_match_elo',
            'elo_gap',
            'home_advantage_adjusted_elo_gap',
        ],
        required_inputs: [
            'stable team identity',
            'historical finished matches',
            'kickoff_time',
        ],
        feature_time: 'prediction_cutoff_time',
        cutoff_rule: 'Only matches with historical match_date < current kickoff may update the rating state.',
    },
    {
        family: 'recent_form',
        priority: 'P0',
        example_features: [
            'last_5_points',
            'last_5_goal_diff',
            'last_5_non_penalty_xg_for',
            'last_5_non_penalty_xg_against',
            'win_draw_loss_counts_last_5',
        ],
        required_inputs: [
            'historical finished matches',
            'stable team identity',
        ],
        feature_time: 'prediction_cutoff_time',
        cutoff_rule: 'Use only prior matches ordered by kickoff_time; never include the current match or future fixtures.',
    },
    {
        family: 'home_away_split_form',
        priority: 'P0',
        example_features: [
            'home_team_home_form_points_last_5',
            'away_team_away_form_points_last_5',
            'home_clean_sheet_rate_home_last_10',
            'away_scoring_rate_away_last_10',
        ],
        required_inputs: [
            'historical finished matches',
            'stable venue interpretation',
        ],
        feature_time: 'prediction_cutoff_time',
        cutoff_rule: 'Split by the historical venue of prior matches only; current match must remain excluded.',
    },
    {
        family: 'head_to_head_history',
        priority: 'P1',
        example_features: [
            'h2h_home_win_rate',
            'h2h_draw_rate',
            'h2h_avg_goal_diff',
            'h2h_recent_3_match_points',
        ],
        required_inputs: [
            'stable home/away team identity',
            'historical finished matches',
        ],
        feature_time: 'prediction_cutoff_time',
        cutoff_rule: 'All referenced H2H matches must have kickoff_time < current kickoff; current-fixture echo from raw payload is forbidden.',
    },
    {
        family: 'rest_and_schedule',
        priority: 'P1',
        example_features: [
            'home_rest_days',
            'away_rest_days',
            'fixture_congestion_last_14d',
            'travel_gap_days_proxy',
        ],
        required_inputs: [
            'historical fixture timeline',
            'kickoff_time',
        ],
        feature_time: 'prediction_cutoff_time',
        cutoff_rule: 'Derived only from already scheduled or completed matches known before the current kickoff.',
    },
    {
        family: 'table_snapshot',
        priority: 'P1',
        example_features: [
            'home_table_position',
            'away_table_position',
            'points_diff',
            'goal_difference_diff',
        ],
        required_inputs: [
            'timestamped standings snapshot',
        ],
        feature_time: 'prediction_cutoff_time',
        cutoff_rule: 'Standings snapshot must be captured at or before the active prediction horizon cutoff.',
    },
    {
        family: 'odds_snapshots',
        priority: 'P1',
        example_features: [
            'opening_home_implied_prob',
            't_minus_24h_draw_implied_prob',
            't_minus_6h_market_margin',
            't_minus_1h_clv_proxy',
        ],
        required_inputs: [
            'timestamped bookmaker odds history',
            'kickoff_time',
            'market/bookmaker normalization',
        ],
        feature_time: 'prediction_cutoff_time',
        cutoff_rule: 'Only odds_timestamp <= prediction_cutoff_time are allowed; T-24h models cannot use closing odds.',
    },
    {
        family: 'confirmed_lineup_and_availability',
        priority: 'P2',
        example_features: [
            'confirmed_starters_count',
            'bench_experience_proxy',
            'formation_family',
            'goalkeeper_confirmation_flag',
        ],
        required_inputs: [
            'timestamped lineup payload',
            'stable player/team identity',
        ],
        feature_time: 'prediction_cutoff_time',
        cutoff_rule: 'Use only for late-horizon models where lineup_timestamp <= prediction_cutoff_time.',
    },
]);

const LEAKAGE_FORBIDDEN_FEATURES = Object.freeze([
    {
        field_or_family: 'matches.actual_result',
        reason: 'Primary label; never part of X.',
    },
    {
        field_or_family: 'matches.home_score / matches.away_score',
        reason: 'Direct post-match label leakage.',
    },
    {
        field_or_family: 'matches.home_corners / away_corners / cards / reds',
        reason: 'Current-match stats are generated by the match itself.',
    },
    {
        field_or_family: 'matches.status / is_finished',
        reason: 'Finished-state knowledge leaks that the match already happened.',
    },
    {
        field_or_family: 'matches.collection_date / created_at / updated_at',
        reason: 'Pipeline timing metadata is not a valid pre-match feature and can encode post-hoc processing order.',
    },
    {
        field_or_family: 'raw_match_data.content.matchFacts',
        reason: 'Goals, cards, substitutions, and event summaries are direct outcome leakage.',
    },
    {
        field_or_family: 'raw_match_data.content.stats',
        reason: 'xG, possession, shots, and aggregate match stats are post-match or in-match outcomes.',
    },
    {
        field_or_family: 'raw_match_data.content.playerStats',
        reason: 'Minutes played and player performance recaps are post-match only.',
    },
    {
        field_or_family: 'raw_match_data.content.shotmap',
        reason: 'Resolved shot events and xG sequence are in-match outcome traces.',
    },
    {
        field_or_family: 'raw_match_data.content.momentum',
        reason: 'Momentum is inherently live or post-match state.',
    },
    {
        field_or_family: 'current or future H2H entries echoed by the current raw payload',
        reason: 'The builder must exclude current-fixture echo and any future contamination.',
    },
    {
        field_or_family: 'standings snapshots captured after kickoff',
        reason: 'Post-kickoff context leak.',
    },
    {
        field_or_family: 'odds snapshots after prediction_cutoff_time',
        reason: 'Not available to the model at the chosen horizon.',
    },
    {
        field_or_family: 'predictions table rows',
        reason: 'Model outputs must never become training features for the first formal dataset.',
    },
    {
        field_or_family: 'scheduled or unlabeled rows from match_features_training',
        reason: 'Current downstream rows are local closure artifacts, not a clean supervised dataset contract.',
    },
]);

const TEMPORAL_CUTOFF_RULES = Object.freeze({
    global_rules: [
        'Dataset grain must be one row per match_id per prediction_horizon.',
        'Every row must persist kickoff_time and prediction_cutoff_time.',
        'Every feature must satisfy feature_observed_at <= prediction_cutoff_time <= kickoff_time.',
        'Historical aggregations may use finished prior matches only, ordered by kickoff_time.',
        'No random split across time; all evaluation splits must be chronological.',
    ],
    horizons: [
        {
            prediction_horizon: 'T_MINUS_24H',
            allowed: [
                'schedule metadata',
                'historical form / ELO / H2H built from prior matches',
                'odds snapshots observed at or before T-24h',
            ],
            forbidden: [
                'closing odds',
                'late lineup data',
                'any current-match live or post-match branch',
            ],
        },
        {
            prediction_horizon: 'T_MINUS_6H',
            allowed: [
                'all T-24h families',
                'odds snapshots observed at or before T-6h',
                'timestamp-safe table snapshots',
            ],
            forbidden: [
                'lineups announced after cutoff',
                'any current-match live or post-match branch',
            ],
        },
        {
            prediction_horizon: 'T_MINUS_1H',
            allowed: [
                'all T-6h families',
                'confirmed lineup context when lineup_timestamp <= cutoff',
                'odds snapshots observed at or before T-1h',
            ],
            forbidden: [
                'any event data from the current match',
                'odds captured after the T-1h cutoff',
            ],
        },
        {
            prediction_horizon: 'CLOSING_OR_NEAR_KICKOFF',
            allowed: [
                'all pre-match families',
                'near-kickoff odds captured before kickoff',
                'confirmed lineup and late availability signals captured before kickoff',
            ],
            forbidden: [
                'kickoff-or-later live events',
                'post-final-whistle recaps',
            ],
        },
    ],
});

const DATASET_BUILDER_DESIGN = Object.freeze({
    dataset_grain: 'one row per match_id per prediction_horizon',
    output_contract: {
        X: [
            'direct_context_features',
            'historical_strength_features',
            'historical_form_features',
            'historical_h2h_features',
            'optional_market_features',
            'optional_lineup_features',
        ],
        y: {
            label_column: 'actual_result',
            label_values: ['home_win', 'draw', 'away_win'],
            fallback_rule: 'derive from final scores only for finished matches when actual_result is missing but scores are present',
        },
        metadata_not_in_X: [
            'match_id',
            'external_id',
            'competition',
            'season',
            'kickoff_time',
            'prediction_horizon',
            'prediction_cutoff_time',
            'feature_schema_version',
            'label_policy_version',
            'row_data_hash',
        ],
    },
    source_priority: [
        'matches for schedule contract, labels, and base context',
        'raw_match_data via data_version-aware canonical selector for normalized identity and timestamp-safe optional context',
        'bookmaker_odds_history as a separate market source joined by stable match_id',
        'derived historical aggregates computed from prior finished matches only',
    ],
    builder_steps: [
        'Select the authorized competition/season cohort and exclude synthetic, scheduled, cancelled, or policy-ambiguous rows.',
        'Normalize competition/team identity with a version-aware reader; do not trust name-only joins when raw IDs are available.',
        'For each prediction_horizon, compute prediction_cutoff_time from kickoff_time.',
        'Build direct schedule/context fields from matches.',
        'Build derived historical features using only prior finished matches with kickoff_time < current kickoff_time.',
        'Attach odds or lineup features only when their timestamps are at or before prediction_cutoff_time.',
        'Construct y from actual_result or score-derived label only after feature freeze.',
        'Emit split-ready dataset plus a manifest containing counts, missingness, class balance, feature families, and hashes.',
    ],
    split_strategy: {
        policy: 'chronological_only',
        recommended_windows: {
            train: 'oldest 70%',
            validation: 'next 15%',
            test: 'latest 15%',
        },
        guards: [
            'Do not random-shuffle across time.',
            'Report class balance per split.',
            'Keep the newest competition window untouched for final approval.',
        ],
    },
    quality_gates: [
        'Minimum label count and per-class count must pass before training.',
        'Missingness must be reported for every feature family.',
        'Every optional feature family must tolerate absence without dropping the whole row.',
        'Rows with unresolved cutoff provenance must be excluded.',
        'Synthetic/local-closure artifacts must be excluded from the formal dataset.',
    ],
    legacy_paths_to_avoid: [
        'scripts/ops/train_model.py currently uses random train_test_split and writes model/scaler artifacts.',
        'src/ml/dataset/dataset_generator.py contains synthetic/random fallback logic and is not a formal cutoff-safe builder.',
    ],
});

const NEXT_RECOMMENDED_TASK = Object.freeze({
    task_id: 'formal_training_cohort_inventory_dry_run',
    objective:
        'Read-only inventory and gap audit for the official training cohort across recommended competitions/seasons, producing a source-controlled manifest of what historical acquisition is still missing before builder implementation.',
    why_minimal:
        'It converts this design into an exact acquisition target set without touching DB state, networks, training code, or model artifacts.',
    requires_user_confirmation: true,
});

const COUNTS_SQL = `
SELECT
    (SELECT COUNT(*) FROM matches) AS matches,
    (SELECT COUNT(*) FROM raw_match_data) AS raw_match_data,
    (SELECT COUNT(*) FROM bookmaker_odds_history) AS bookmaker_odds_history,
    (SELECT COUNT(*) FROM l3_features) AS l3_features,
    (SELECT COUNT(*) FROM match_features_training) AS match_features_training,
    (SELECT COUNT(*) FROM predictions) AS predictions,
    (SELECT COUNT(*) FROM matches WHERE is_training_eligible = true) AS training_eligible_matches,
    (SELECT COUNT(*) FROM matches WHERE status = 'finished' AND actual_result IS NOT NULL) AS finished_labeled_matches,
    (SELECT COUNT(*) FROM matches m WHERE EXISTS (SELECT 1 FROM raw_match_data r WHERE r.match_id = m.match_id)) AS matches_with_raw,
    (SELECT COUNT(*) FROM matches m WHERE EXISTS (SELECT 1 FROM l3_features l WHERE l.match_id = m.match_id)) AS matches_with_l3,
    (SELECT COUNT(*) FROM matches m WHERE EXISTS (SELECT 1 FROM match_features_training t WHERE t.match_id = m.match_id)) AS matches_with_training_features,
    (SELECT COUNT(*) FROM matches m WHERE EXISTS (SELECT 1 FROM bookmaker_odds_history o WHERE o.match_id = m.match_id)) AS matches_with_odds,
    (SELECT COUNT(*) FROM matches m
        WHERE m.actual_result IS NOT NULL
          AND EXISTS (SELECT 1 FROM raw_match_data r WHERE r.match_id = m.match_id)
          AND EXISTS (SELECT 1 FROM l3_features l WHERE l.match_id = m.match_id)
          AND EXISTS (SELECT 1 FROM match_features_training t WHERE t.match_id = m.match_id)
          AND EXISTS (SELECT 1 FROM bookmaker_odds_history o WHERE o.match_id = m.match_id)
    ) AS full_feature_chain_rows
`;

const SCOPE_SQL = `
SELECT
    league_name,
    season,
    COUNT(*) AS matches,
    COUNT(*) FILTER (WHERE is_training_eligible = true) AS training_eligible,
    COUNT(*) FILTER (WHERE actual_result IS NOT NULL) AS labeled,
    COUNT(*) FILTER (WHERE status = 'finished') AS finished
FROM matches
GROUP BY league_name, season
ORDER BY matches DESC, league_name ASC, season ASC
`;

const RAW_VERSION_SQL = `
SELECT
    data_version,
    COUNT(*) AS rows,
    COUNT(DISTINCT match_id) AS distinct_matches
FROM raw_match_data
GROUP BY data_version
ORDER BY rows DESC, data_version ASC
`;

const SMOKE_QUALITY_SQL = `
SELECT
    COUNT(*) AS sample_count,
    COUNT(*) FILTER (WHERE league_name = $1 AND season = $2) AS target_scope_rows,
    COUNT(*) FILTER (WHERE venue IS NULL OR BTRIM(venue) = '') AS venue_missing,
    COUNT(*) FILTER (WHERE referee IS NULL OR BTRIM(referee) = '') AS referee_missing
FROM matches
WHERE is_training_eligible = true
`;

const TRAINING_FEATURE_STATE_SQL = `
SELECT
    COUNT(*) AS total_rows,
    COUNT(*) FILTER (WHERE m.status <> 'finished') AS non_finished_rows,
    COUNT(*) FILTER (WHERE m.actual_result IS NULL) AS unlabeled_rows,
    COUNT(*) FILTER (WHERE COALESCE(t.feature_count, 0) = 0) AS zero_feature_count_rows
FROM match_features_training t
INNER JOIN matches m ON m.match_id = t.match_id
`;

const PREDICTION_STATE_SQL = `
SELECT
    COUNT(*) AS total_rows,
    COUNT(*) FILTER (WHERE m.status <> 'finished') AS non_finished_rows,
    COUNT(*) FILTER (WHERE m.actual_result IS NULL) AS unlabeled_rows
FROM predictions p
INNER JOIN matches m ON m.match_id = p.match_id
`;

const MATCHES_COLUMNS_SQL = `
SELECT column_name
FROM information_schema.columns
WHERE table_name = 'matches'
ORDER BY ordinal_position
`;

function usage() {
    return [
        'Usage:',
        '  node scripts/ops/formal_training_dataset_design_dry_run.js [--json]',
        '',
        'Safety:',
        '  Read-only dry-run only. No DB write, no migration, no schema change,',
        '  no live fetch, no raw payload output, no model training, no model artifact.',
    ].join('\n');
}

function parseArgs(argv = process.argv.slice(2)) {
    const options = { json: false, help: false };
    for (let index = 0; index < argv.length; index += 1) {
        const arg = String(argv[index]);
        if (arg === '--json') {
            options.json = true;
        } else if (arg === '--help' || arg === '-h') {
            options.help = true;
        } else {
            throw new Error(`Unknown argument: ${arg}`);
        }
    }
    return options;
}

function buildDbConfig() {
    return {
        host: process.env.DB_HOST || process.env.POSTGRES_HOST || 'db',
        port: Number.parseInt(process.env.DB_PORT || process.env.POSTGRES_PORT || '5432', 10),
        database: process.env.DB_NAME || process.env.POSTGRES_DB || 'football_db',
        user: process.env.DB_USER || process.env.POSTGRES_USER || 'football_user',
        password: process.env.DB_PASSWORD || process.env.POSTGRES_PASSWORD,
        max: 1,
        idleTimeoutMillis: 30000,
        connectionTimeoutMillis: 5000,
    };
}

async function openReadOnlyClient(dependencies = {}) {
    if (dependencies.client) {
        return { client: dependencies.client, close: async () => {} };
    }

    const { Pool } = require('pg');
    const pool = new Pool(buildDbConfig());
    const client = await pool.connect();

    return {
        client,
        close: async () => {
            if (typeof client.release === 'function') {
                client.release();
            }
            await pool.end();
        },
    };
}

function assertSelectOnlySql(sql) {
    const normalized = String(sql || '').replace(/\s+/g, ' ').trim().toUpperCase();
    const allowed =
        normalized === READ_ONLY_BEGIN_SQL ||
        normalized === READ_ONLY_ROLLBACK_SQL ||
        normalized.startsWith('SELECT ') ||
        normalized.startsWith('WITH ');

    if (!allowed) {
        throw new Error(`Unsafe SQL rejected by ${PHASE}: ${normalized.slice(0, 80)}`);
    }
}

async function querySelectOnly(client, sql, params = []) {
    assertSelectOnlySql(sql);
    return client.query(sql, params);
}

function toInt(value) {
    return Number.parseInt(value ?? '0', 10) || 0;
}

function normalizeCountsRow(row = {}) {
    return Object.fromEntries(
        Object.entries(row).map(([key, value]) => [key, toInt(value)])
    );
}

function normalizeScopeRows(rows = []) {
    return rows.map(row => ({
        league_name: row.league_name,
        season: row.season,
        matches: toInt(row.matches),
        training_eligible: toInt(row.training_eligible),
        labeled: toInt(row.labeled),
        finished: toInt(row.finished),
    }));
}

function normalizeRawVersionRows(rows = []) {
    return rows.map(row => ({
        data_version: row.data_version,
        rows: toInt(row.rows),
        distinct_matches: toInt(row.distinct_matches),
    }));
}

function normalizeColumnRows(rows = []) {
    return rows.map(row => String(row.column_name));
}

async function collectAuditState(dependencies = {}) {
    const connection = await openReadOnlyClient(dependencies);
    let rolledBack = false;

    try {
        await querySelectOnly(connection.client, READ_ONLY_BEGIN_SQL);

        const counts = normalizeCountsRow(
            (await querySelectOnly(connection.client, COUNTS_SQL)).rows[0]
        );
        const scopeRows = normalizeScopeRows(
            (await querySelectOnly(connection.client, SCOPE_SQL)).rows
        );
        const rawVersionRows = normalizeRawVersionRows(
            (await querySelectOnly(connection.client, RAW_VERSION_SQL)).rows
        );
        const smokeQuality = normalizeCountsRow(
            (await querySelectOnly(connection.client, SMOKE_QUALITY_SQL, [
                TARGET_SCOPE.league_name,
                TARGET_SCOPE.season,
            ])).rows[0]
        );
        const trainingFeatureState = normalizeCountsRow(
            (await querySelectOnly(connection.client, TRAINING_FEATURE_STATE_SQL)).rows[0]
        );
        const predictionState = normalizeCountsRow(
            (await querySelectOnly(connection.client, PREDICTION_STATE_SQL)).rows[0]
        );
        const matchesColumns = normalizeColumnRows(
            (await querySelectOnly(connection.client, MATCHES_COLUMNS_SQL)).rows
        );

        await querySelectOnly(connection.client, READ_ONLY_ROLLBACK_SQL);
        rolledBack = true;

        return {
            counts,
            scope_rows: scopeRows,
            raw_version_rows: rawVersionRows,
            smoke_quality: smokeQuality,
            training_feature_state: trainingFeatureState,
            prediction_state: predictionState,
            matches_columns: matchesColumns,
        };
    } finally {
        if (!rolledBack) {
            try {
                await querySelectOnly(connection.client, READ_ONLY_ROLLBACK_SQL);
            } catch {
                // preserve original error
            }
        }
        await connection.close();
    }
}

function buildCurrentSampleLimitations(state) {
    const currentScope = state.scope_rows[0] || {
        league_name: TARGET_SCOPE.league_name,
        season: TARGET_SCOPE.season,
        matches: state.counts.training_eligible_matches,
        training_eligible: state.counts.training_eligible_matches,
    };
    const missingIdentityColumns = [
        'home_team_id',
        'away_team_id',
        'league_id',
    ].filter(column => !state.matches_columns.includes(column));

    return [
        {
            code: 'smoke_only_sample_size',
            detail:
                `${state.counts.training_eligible_matches} training-eligible rows exist, all from ` +
                `${currentScope.league_name} ${currentScope.season}; this is below the repo discussion threshold ` +
                `(${200}) and far below a formal baseline (${MINIMUM_RECOMMENDATION.formal_baseline_matches}).`,
        },
        {
            code: 'single_competition_single_season',
            detail:
                `Current league/season coverage shows only one real training scope with ` +
                `${currentScope.matches} matches; the remaining local rows are edge-case Segunda samples, not a formal corpus.`,
        },
        {
            code: 'direct_features_too_thin',
            detail:
                `The current safe direct features are effectively league_name, season, home_team, away_team, and match_date. ` +
                `venue missing=${state.smoke_quality.venue_missing}/${state.smoke_quality.sample_count}, ` +
                `referee missing=${state.smoke_quality.referee_missing}/${state.smoke_quality.sample_count}.`,
        },
        {
            code: 'mixed_raw_provenance',
            detail:
                `raw_match_data mixes multiple contracts: ${state.raw_version_rows
                    .map(row => `${row.data_version}=${row.rows}`)
                    .join(', ')}. Formal training cannot treat these rows as a single homogeneous source without version-aware parsing.`,
        },
        {
            code: 'feature_chain_not_scaled',
            detail:
                `Downstream feature coverage is tiny relative to labeled matches: ` +
                `l3_features=${state.counts.l3_features}, ` +
                `match_features_training=${state.counts.match_features_training}, ` +
                `full_feature_chain_rows=${state.counts.full_feature_chain_rows}.`,
        },
        {
            code: 'downstream_table_contamination',
            detail:
                `match_features_training has ${state.training_feature_state.total_rows} rows, ` +
                `${state.training_feature_state.non_finished_rows} on non-finished matches, ` +
                `${state.training_feature_state.unlabeled_rows} unlabeled, and ` +
                `${state.training_feature_state.zero_feature_count_rows} with feature_count=0. ` +
                `predictions has ${state.prediction_state.total_rows} rows, including ` +
                `${state.prediction_state.non_finished_rows} on non-finished matches.`,
        },
        {
            code: 'odds_coverage_insufficient',
            detail:
                `bookmaker_odds_history has ${state.counts.bookmaker_odds_history} rows covering ` +
                `${state.counts.matches_with_odds} match; this is not enough for cutoff-safe market features.`,
        },
        {
            code: 'identity_contract_gap',
            detail:
                missingIdentityColumns.length === 0
                    ? 'matches already contains stable identity columns.'
                    : `matches lacks stable identity columns: ${missingIdentityColumns.join(', ')}. ` +
                      'Formal derived features should prefer canonical raw identity normalization over name-only joins.',
        },
        {
            code: 'legacy_training_entry_not_formal',
            detail:
                'The current training entry writes artifacts and uses random train/test split, so it cannot serve as the formal dataset builder contract.',
        },
    ];
}

function buildMissingDataBlockers(state) {
    return [
        {
            blocker: 'historical_match_volume_missing',
            detail:
                `Need at least ${MINIMUM_RECOMMENDATION.formal_baseline_matches} finished labeled matches; local DB currently has ${state.counts.finished_labeled_matches}.`,
        },
        {
            blocker: 'multi_competition_multi_season_gap',
            detail:
                `Need at least ${MINIMUM_RECOMMENDATION.minimum_competitions} competitions and ` +
                `${MINIMUM_RECOMMENDATION.minimum_completed_seasons_per_competition} completed seasons per competition; ` +
                `current local scope is effectively one competition-season.`,
        },
        {
            blocker: 'raw_identity_coverage_gap',
            detail:
                'Only eight matches currently have fotmob_pageprops_v2 coverage; large-scale canonical raw identity coverage is missing.',
        },
        {
            blocker: 'odds_history_gap',
            detail:
                `Only ${state.counts.bookmaker_odds_history} odds rows / ${state.counts.matches_with_odds} match currently exist; market features cannot be formalized yet.`,
        },
        {
            blocker: 'cutoff_provenance_gap',
            detail:
                'No formal feature_time / prediction_cutoff_time contract exists for current derived tables, so lineage-safe pre-match reuse is not provable.',
        },
        {
            blocker: 'downstream_cleanroom_gap',
            detail:
                'Existing match_features_training and predictions rows are local closure artifacts and must be excluded from the first formal supervised dataset.',
        },
    ];
}

function buildPayload(state) {
    const currentSampleLimitations = buildCurrentSampleLimitations(state);
    const missingDataBlockers = buildMissingDataBlockers(state);

    return {
        phase: PHASE,
        mode: 'dry_run',
        actual_update_executed: false,
        read_only: true,
        script: 'scripts/ops/formal_training_dataset_design_dry_run.js',
        generated_at: new Date().toISOString(),
        current_db_state: {
            ...state.counts,
            smoke_scope: TARGET_SCOPE,
            smoke_quality: state.smoke_quality,
            league_season_coverage: state.scope_rows,
            raw_version_distribution: state.raw_version_rows,
            training_feature_state: state.training_feature_state,
            prediction_state: state.prediction_state,
        },
        current_training_eligible_count: state.counts.training_eligible_matches,
        current_sample_limitations: currentSampleLimitations,
        recommended_min_sample_size: {
            ...MINIMUM_RECOMMENDATION,
            rationale: [
                'A 3-class 1X2 task needs enough draw examples across train/validation/test windows.',
                'Three competitions x three completed seasons gives a defensible first official baseline and reduces single-league bias.',
                'Big-five x three seasons is the preferred stable target once acquisition capacity exists.',
            ],
        },
        recommended_competitions: RECOMMENDED_COMPETITIONS,
        recommended_seasons: RECOMMENDED_SEASONS,
        direct_safe_features: DIRECT_SAFE_FEATURES,
        derived_feature_candidates: DERIVED_FEATURE_CANDIDATES,
        leakage_forbidden_features: LEAKAGE_FORBIDDEN_FEATURES,
        temporal_cutoff_rules: TEMPORAL_CUTOFF_RULES,
        dataset_builder_design: DATASET_BUILDER_DESIGN,
        missing_data_blockers: missingDataBlockers,
        next_recommended_task: NEXT_RECOMMENDED_TASK,
        safety: {
            migration_in_scope: false,
            schema_change_in_scope: false,
            db_write_allowed: false,
            db_write_executed: false,
            live_fetch_allowed: false,
            live_fetch_executed: false,
            raw_payload_output_allowed: false,
            raw_payload_output_detected: false,
            model_training_performed: false,
            model_output_generated: false,
            prediction_execution_performed: false,
            read_only_transaction_used: true,
        },
    };
}

function payloadToText(payload) {
    const limitLines = payload.current_sample_limitations
        .map(item => `  - ${item.code}: ${item.detail}`)
        .join('\n');
    const competitionLines = payload.recommended_competitions.preferred_official_set
        .map(name => `  - ${name}`)
        .join('\n');
    const seasonLines = payload.recommended_seasons.preferred_training_seasons
        .map(name => `  - ${name}`)
        .join('\n');
    const directSafe = payload.direct_safe_features.available_now_in_matches
        .map(item => `  - ${item.field} (${item.readiness})`)
        .join('\n');
    const derivedFamilies = payload.derived_feature_candidates
        .map(item => `  - ${item.priority} ${item.family}: ${item.cutoff_rule}`)
        .join('\n');
    const forbidden = payload.leakage_forbidden_features
        .map(item => `  - ${item.field_or_family}: ${item.reason}`)
        .join('\n');
    const cutoffRules = payload.temporal_cutoff_rules.global_rules
        .map(rule => `  - ${rule}`)
        .join('\n');
    const blockers = payload.missing_data_blockers
        .map(item => `  - ${item.blocker}: ${item.detail}`)
        .join('\n');

    return [
        `mode=${payload.mode}`,
        `actual_update_executed=${payload.actual_update_executed}`,
        `current_training_eligible_count=${payload.current_training_eligible_count}`,
        'current_sample_limitations=',
        limitLines,
        'recommended_min_sample_size=',
        `  - absolute_pilot_floor_matches=${payload.recommended_min_sample_size.absolute_pilot_floor_matches}`,
        `  - formal_baseline_matches=${payload.recommended_min_sample_size.formal_baseline_matches}`,
        `  - preferred_stable_matches=${payload.recommended_min_sample_size.preferred_stable_matches}`,
        'recommended_competitions=',
        competitionLines,
        'recommended_seasons=',
        seasonLines,
        'direct_safe_features=',
        directSafe,
        'derived_feature_candidates=',
        derivedFamilies,
        'leakage_forbidden_features=',
        forbidden,
        'temporal_cutoff_rules=',
        cutoffRules,
        'dataset_builder_design=',
        `  - dataset_grain=${payload.dataset_builder_design.dataset_grain}`,
        `  - split_policy=${payload.dataset_builder_design.split_strategy.policy}`,
        `  - next_builder_step=${payload.dataset_builder_design.builder_steps[0]}`,
        'missing_data_blockers=',
        blockers,
        'next_recommended_task=',
        `  - ${payload.next_recommended_task.task_id}: ${payload.next_recommended_task.objective}`,
    ].join('\n');
}

function writePayload(payload, json, io) {
    const output = json
        ? `${JSON.stringify(payload, null, 2)}\n`
        : `${payloadToText(payload)}\n`;
    io.stdout(output);
}

function buildFailurePayload(error) {
    return {
        phase: PHASE,
        mode: 'dry_run',
        actual_update_executed: false,
        read_only: true,
        script: 'scripts/ops/formal_training_dataset_design_dry_run.js',
        errors: [error.message],
        safety: {
            migration_in_scope: false,
            schema_change_in_scope: false,
            db_write_allowed: false,
            db_write_executed: false,
            live_fetch_allowed: false,
            live_fetch_executed: false,
            raw_payload_output_allowed: false,
            raw_payload_output_detected: false,
            model_training_performed: false,
            model_output_generated: false,
            prediction_execution_performed: false,
            read_only_transaction_used: true,
        },
    };
}

async function runDryRun(options = {}, dependencies = {}) {
    const state = await collectAuditState(dependencies);
    return buildPayload(state);
}

async function main(argv = process.argv.slice(2), io = {}) {
    const output = {
        stdout: io.stdout || (text => process.stdout.write(text)),
        stderr: io.stderr || (text => process.stderr.write(text)),
    };
    let options = { json: false, help: false };

    try {
        options = parseArgs(argv);
        if (options.help) {
            output.stdout(`${usage()}\n`);
            return 0;
        }

        const payload = await runDryRun(options);
        writePayload(payload, options.json, output);
        return 0;
    } catch (error) {
        const payload = buildFailurePayload(error);
        writePayload(payload, options.json === true, output);
        return 1;
    }
}

if (require.main === module) {
    main().then(code => {
        process.exitCode = code;
    });
}

module.exports = {
    PHASE,
    TARGET_SCOPE,
    MINIMUM_RECOMMENDATION,
    DIRECT_SAFE_FEATURES,
    DERIVED_FEATURE_CANDIDATES,
    LEAKAGE_FORBIDDEN_FEATURES,
    TEMPORAL_CUTOFF_RULES,
    DATASET_BUILDER_DESIGN,
    NEXT_RECOMMENDED_TASK,
    COUNTS_SQL,
    SCOPE_SQL,
    RAW_VERSION_SQL,
    SMOKE_QUALITY_SQL,
    TRAINING_FEATURE_STATE_SQL,
    PREDICTION_STATE_SQL,
    MATCHES_COLUMNS_SQL,
    READ_ONLY_BEGIN_SQL,
    READ_ONLY_ROLLBACK_SQL,
    parseArgs,
    assertSelectOnlySql,
    normalizeCountsRow,
    normalizeScopeRows,
    normalizeRawVersionRows,
    normalizeColumnRows,
    buildCurrentSampleLimitations,
    buildMissingDataBlockers,
    buildPayload,
    collectAuditState,
    runDryRun,
    main,
};
