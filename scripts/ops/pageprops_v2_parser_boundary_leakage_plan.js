#!/usr/bin/env node
'use strict';

const PHASE = 'PHASE5_21L2P_PAGEPROPS_V2_PARSER_BOUNDARY_LEAKAGE_PLAN';
const SOURCE = 'fotmob';
const RAW_VERSION = 'fotmob_pageprops_v2';
const PLANNING_SCOPE = 'parser-boundary-leakage-acquisition-odds-roadmap';
const PREDICTION_HORIZONS = Object.freeze(['T_MINUS_24H', 'T_MINUS_6H', 'T_MINUS_1H', 'CLOSING_OR_NEAR_KICKOFF']);
const REQUIRED_NO_FLAGS = Object.freeze([
    'allowDbWrite',
    'allowNetwork',
    'allowParserImplementation',
    'allowFeatureExtraction',
    'allowTraining',
    'allowPrediction',
]);
const BLOCKED_TRUE_FLAGS = Object.freeze([
    'execute',
    'commit',
    'touchFotmob',
    'liveRequest',
    'allowRawMatchDataWrite',
    'allowOddsWrite',
    'allowSchemaMigration',
    'allowMatchesWrite',
]);

function normalizeText(value) {
    return String(value ?? '').trim();
}

function normalizeBooleanFlag(value, fallback = undefined) {
    if (typeof value === 'boolean') {
        return value;
    }
    if (value === null || value === undefined || value === '') {
        return fallback;
    }
    const normalized = String(value).trim().toLowerCase();
    if (['1', 'true', 'yes', 'y', 'on'].includes(normalized)) {
        return true;
    }
    if (['0', 'false', 'no', 'n', 'off'].includes(normalized)) {
        return false;
    }
    return fallback;
}

function parseOptionValue(arg, argv, index) {
    if (arg.includes('=')) {
        return { value: arg.slice(arg.indexOf('=') + 1), consumedNext: false };
    }
    const nextArg = argv[index + 1];
    if (typeof nextArg === 'string' && !nextArg.startsWith('--')) {
        return { value: nextArg, consumedNext: true };
    }
    return { value: true, consumedNext: false };
}

function parseArgs(argv = process.argv.slice(2)) {
    const options = {
        source: null,
        rawVersion: null,
        planningScope: null,
        allowDbWrite: null,
        allowNetwork: null,
        allowParserImplementation: null,
        allowFeatureExtraction: null,
        allowTraining: null,
        allowPrediction: null,
        execute: false,
        commit: false,
        touchFotmob: false,
        liveRequest: false,
        allowRawMatchDataWrite: false,
        allowOddsWrite: false,
        allowSchemaMigration: false,
        allowMatchesWrite: false,
        help: false,
        unknown: [],
    };
    const keyMap = {
        source: 'source',
        'raw-version': 'rawVersion',
        raw_version: 'rawVersion',
        'planning-scope': 'planningScope',
        planning_scope: 'planningScope',
        'allow-db-write': 'allowDbWrite',
        allow_db_write: 'allowDbWrite',
        'allow-network': 'allowNetwork',
        allow_network: 'allowNetwork',
        'allow-parser-implementation': 'allowParserImplementation',
        allow_parser_implementation: 'allowParserImplementation',
        'allow-feature-extraction': 'allowFeatureExtraction',
        allow_feature_extraction: 'allowFeatureExtraction',
        'allow-training': 'allowTraining',
        allow_training: 'allowTraining',
        'allow-prediction': 'allowPrediction',
        allow_prediction: 'allowPrediction',
        execute: 'execute',
        commit: 'commit',
        'touch-fotmob': 'touchFotmob',
        touch_fotmob: 'touchFotmob',
        'live-request': 'liveRequest',
        live_request: 'liveRequest',
        'allow-raw-match-data-write': 'allowRawMatchDataWrite',
        allow_raw_match_data_write: 'allowRawMatchDataWrite',
        'allow-odds-write': 'allowOddsWrite',
        allow_odds_write: 'allowOddsWrite',
        'allow-schema-migration': 'allowSchemaMigration',
        allow_schema_migration: 'allowSchemaMigration',
        'allow-matches-write': 'allowMatchesWrite',
        allow_matches_write: 'allowMatchesWrite',
        help: 'help',
        h: 'help',
    };
    const booleanKeys = new Set([
        'allowDbWrite',
        'allowNetwork',
        'allowParserImplementation',
        'allowFeatureExtraction',
        'allowTraining',
        'allowPrediction',
        'execute',
        'commit',
        'touchFotmob',
        'liveRequest',
        'allowRawMatchDataWrite',
        'allowOddsWrite',
        'allowSchemaMigration',
        'allowMatchesWrite',
        'help',
    ]);

    for (let index = 0; index < argv.length; index += 1) {
        const arg = String(argv[index]);
        if (!arg.startsWith('--')) {
            options.unknown.push(arg);
            continue;
        }
        const rawKey = arg.replace(/^--/, '').split('=')[0];
        const optionKey = keyMap[rawKey];
        const { value, consumedNext } = parseOptionValue(arg, argv, index);
        if (consumedNext) {
            index += 1;
        }
        if (!optionKey) {
            options.unknown.push(rawKey);
            continue;
        }
        options[optionKey] = booleanKeys.has(optionKey) ? normalizeBooleanFlag(value, true) : value;
    }

    return options;
}

function validatePlanningInput(input = {}) {
    const errors = [];
    const source = normalizeText(input.source).toLowerCase();
    const rawVersion = normalizeText(input.rawVersion);
    const planningScope = normalizeText(input.planningScope);

    if (Array.isArray(input.unknown) && input.unknown.length > 0) {
        errors.push(`unknown arguments: ${input.unknown.join(', ')}`);
    }

    if (!source) {
        errors.push('missing source=fotmob');
    } else if (source !== SOURCE) {
        errors.push('source must be fotmob');
    }
    if (!rawVersion) {
        errors.push('missing raw-version=fotmob_pageprops_v2');
    } else if (rawVersion !== RAW_VERSION) {
        errors.push('raw-version must be fotmob_pageprops_v2');
    }
    if (!planningScope) {
        errors.push('missing planning-scope=parser-boundary-leakage-acquisition-odds-roadmap');
    } else if (planningScope !== PLANNING_SCOPE) {
        errors.push('planning-scope must be parser-boundary-leakage-acquisition-odds-roadmap');
    }

    for (const flagName of REQUIRED_NO_FLAGS) {
        const normalizedValue = normalizeBooleanFlag(input[flagName]);
        const cliName = flagName.replace(/[A-Z]/g, match => `-${match.toLowerCase()}`);
        if (normalizedValue === true) {
            errors.push(`${cliName}=yes is blocked`);
            continue;
        }
        if (normalizedValue !== false) {
            errors.push(`${cliName}=no is required`);
        }
    }

    for (const flagName of BLOCKED_TRUE_FLAGS) {
        if (normalizeBooleanFlag(input[flagName]) === true) {
            const cliName = flagName.replace(/[A-Z]/g, match => `-${match.toLowerCase()}`);
            errors.push(`${cliName}=yes is blocked`);
        }
    }

    return {
        ok: errors.length === 0,
        errors,
        value: {
            source,
            rawVersion,
            planningScope,
            allowDbWrite: false,
            allowNetwork: false,
            allowParserImplementation: false,
            allowFeatureExtraction: false,
            allowTraining: false,
            allowPrediction: false,
        },
    };
}

function buildParserModulePlan() {
    return [
        {
            parser_key: 'identity_metadata_parser',
            raw_paths: ['matchId', 'general', 'header'],
            candidate_outputs: [
                'match_id',
                'kickoff_time',
                'home_team_identity',
                'away_team_identity',
                'league_identity',
                'season_identity',
                'basic_status_metadata',
            ],
            leakage_tier: 'metadata_only',
            field_categories: {
                safe_pre_match_candidate: [
                    'matchId',
                    'general.matchTimeUTC',
                    'general.homeTeam.id',
                    'general.awayTeam.id',
                ],
                metadata_only: ['general.leagueId', 'general.leagueName', 'header.status'],
                exclude_from_training_by_default: ['identity labels used for joins/normalization only'],
            },
            pre_match_usability:
                'safe for joins, dedupe, scheduling and normalization; not a direct predictive feature by itself',
            optional_handling:
                'require only minimal identifiers and kickoff metadata; deeper descriptive branches remain optional',
            training_default: 'exclude_from_training_by_default',
            notes: ['safe identity metadata, not predictive by itself'],
        },
        {
            parser_key: 'team_context_parser',
            raw_paths: ['header.teams', 'general', 'content.table'],
            candidate_outputs: [
                'league_context',
                'season_context',
                'round_context',
                'team_identity_context',
                'table_snapshot_features',
            ],
            leakage_tier: 'conditional_pre_match_if_timestamped',
            field_categories: {
                safe_pre_match_candidate: ['general.leagueId', 'general.leagueName', 'general.parentLeagueName'],
                conditional_pre_match_if_timestamped: [
                    'content.table',
                    'general.round',
                    'header.teams form/context captured before cutoff',
                ],
                metadata_only: ['header.teams names and badges'],
            },
            timestamp_rule: 'table_snapshot_at <= prediction_cutoff_time',
            pre_match_usability:
                'usable only when standings/context snapshot is confirmed at or before prediction_cutoff_time',
            optional_handling:
                'optional-first; do not assume table or richer context exists outside top leagues or finished samples',
            training_default: 'conditional_pre_match_if_timestamped',
            notes: ['table snapshots after kickoff are forbidden in pre-match training'],
        },
        {
            parser_key: 'h2h_parser',
            raw_paths: ['content.h2h'],
            candidate_outputs: [
                'historical_h2h_counts',
                'recent_h2h_results',
                'historical_goal_totals',
                'venue_split_history',
            ],
            leakage_tier: 'conditional_pre_match_if_timestamped',
            field_categories: {
                conditional_pre_match_if_timestamped: [
                    'content.h2h.matches[] where historical_match_time < kickoff_time',
                ],
                exclude_from_training_by_default: [
                    'undated or unresolved h2h entries',
                    'branches that may include current/future match context',
                ],
            },
            timestamp_rule: 'all referenced h2h matches must be historical and snapshot_at <= prediction_cutoff_time',
            pre_match_usability:
                'allowed only after filtering out current/future match entries and any snapshot taken after kickoff',
            optional_handling:
                'treat h2h as optional and aggressively filter incomplete or semantically ambiguous rows',
            training_default: 'conditional_pre_match_if_timestamped',
            notes: ['must ensure no current or future match is included'],
        },
        {
            parser_key: 'lineup_parser',
            raw_paths: ['content.lineup'],
            candidate_outputs: [
                'confirmed_starters',
                'bench_depth',
                'formation',
                'coach_context',
                'player_availability_signals',
            ],
            leakage_tier: 'conditional_pre_match_if_timestamped',
            field_categories: {
                conditional_pre_match_if_timestamped: [
                    'content.lineup.homeTeam.starters',
                    'content.lineup.awayTeam.starters',
                    'content.lineup.formations',
                ],
                live_only: ['late in-match performance/event branches inside lineup payloads'],
                exclude_from_training_by_default: ['unconfirmed lineups', 'late updates beyond selected horizon'],
            },
            timestamp_rule: 'lineup_timestamp <= prediction_cutoff_time',
            pre_match_usability:
                'usable only for horizons where the lineup is officially announced before the cutoff; excluded from T-24h by default',
            optional_handling:
                'optional-first because many leagues and statuses will miss confirmed lineups or only expose them near kickoff',
            training_default: 'exclude_from_training_by_default',
            notes: ['otherwise treat lineup as live_only for pre-match modeling'],
        },
        {
            parser_key: 'match_facts_parser',
            raw_paths: ['content.matchFacts'],
            candidate_outputs: ['event stream', 'goals/cards/substitutions', 'referee recap', 'match summary facts'],
            leakage_tier: 'post_match_only',
            field_categories: {
                post_match_only: ['goals', 'cards', 'substitutions', 'result-bearing match facts'],
                live_only: ['in-match events and evolving timelines'],
                exclude_from_training_by_default: ['all matchFacts-derived outputs for pre-match models'],
            },
            pre_match_usability: 'not safe for pre-match training by default',
            optional_handling: 'keep parser optional and isolated for future live/post-match analytics only',
            training_default: 'exclude_from_training_by_default',
            notes: ['mostly post_match_only or live_only'],
        },
        {
            parser_key: 'stats_parser',
            raw_paths: ['content.stats'],
            candidate_outputs: ['team stat splits', 'xG recap', 'possession recap', 'period aggregates'],
            leakage_tier: 'post_match_only',
            field_categories: {
                post_match_only: ['full-time team statistics and period aggregates'],
                live_only: ['in-match stat progression'],
                exclude_from_training_by_default: ['stats-derived values for any pre-match horizon'],
            },
            pre_match_usability: 'not safe for pre-match training',
            optional_handling: 'parser must tolerate missing stats in lower tiers and pre-match states',
            training_default: 'exclude_from_training_by_default',
            notes: ['post_match_only or live_only'],
        },
        {
            parser_key: 'player_stats_parser',
            raw_paths: ['content.playerStats'],
            candidate_outputs: ['player stat recap', 'minutes played', 'xG/xA recap', 'player event summaries'],
            leakage_tier: 'post_match_only',
            field_categories: {
                post_match_only: ['player performance recaps and minutes played'],
                live_only: ['in-match player event accumulators'],
                exclude_from_training_by_default: ['all playerStats outputs for pre-match training'],
            },
            pre_match_usability: 'not safe for pre-match training',
            optional_handling: 'assume playerStats may be absent in colder leagues and should not block parsing',
            training_default: 'exclude_from_training_by_default',
            notes: ['playerStats should remain live/post-match only'],
        },
        {
            parser_key: 'shotmap_parser',
            raw_paths: ['content.shotmap'],
            candidate_outputs: ['shot locations', 'xG shot sequence', 'chance quality recap'],
            leakage_tier: 'post_match_only',
            field_categories: {
                post_match_only: ['resolved shot events and xG shot map'],
                live_only: ['in-match shot feed'],
                exclude_from_training_by_default: ['all shotmap outputs for pre-match models'],
            },
            pre_match_usability: 'not safe for pre-match training',
            optional_handling: 'expect missing shotmap coverage in lower tiers and sparse competitions',
            training_default: 'exclude_from_training_by_default',
            notes: ['shotmap is live/post-match only'],
        },
        {
            parser_key: 'momentum_parser',
            raw_paths: ['content.momentum'],
            candidate_outputs: ['momentum curve', 'pressure swings', 'period dominance summaries'],
            leakage_tier: 'live_only',
            field_categories: {
                live_only: ['minute-by-minute momentum and pressure curves'],
                post_match_only: ['post-match summarized momentum'],
                exclude_from_training_by_default: ['all momentum outputs for pre-match models'],
            },
            pre_match_usability: 'not safe for pre-match training',
            optional_handling: 'treat as optional because many leagues or statuses may omit momentum entirely',
            training_default: 'exclude_from_training_by_default',
            notes: ['momentum is live/post-match only'],
        },
        {
            parser_key: 'seo_auxiliary_parser',
            raw_paths: ['seo', 'seo.eventJSONLD', 'seo.breadcrumbJSONLD'],
            candidate_outputs: [
                'canonical labels',
                'structured metadata',
                'kickoff metadata cross-checks',
                'breadcrumb mapping',
            ],
            leakage_tier: 'metadata_only',
            field_categories: {
                metadata_only: ['seo.eventJSONLD.startDate', 'seo.eventJSONLD.name'],
                auxiliary_only: ['seo.breadcrumbJSONLD', 'slug/title normalization'],
                exclude_from_training_by_default: ['SEO text and breadcrumb strings as direct model features'],
            },
            pre_match_usability:
                'useful for metadata reconciliation and QA, not as direct predictive features by default',
            optional_handling: 'treat SEO branches as optional helpers rather than core parser dependencies',
            training_default: 'exclude_from_training_by_default',
            notes: ['metadata or auxiliary only'],
        },
        {
            parser_key: 'fallback_translations_parser',
            raw_paths: ['fallback', 'translations'],
            candidate_outputs: ['label normalization', 'localization mapping', 'missing-field fallback markers'],
            leakage_tier: 'auxiliary_only',
            field_categories: {
                auxiliary_only: ['translations.*', 'fallback flags and labels'],
                exclude_from_training_by_default: ['localization strings and fallback flags as direct model features'],
            },
            pre_match_usability: 'use only for normalization/mapping; not predictive by default',
            optional_handling: 'fully optional and never allowed to block parser success',
            training_default: 'exclude_from_training_by_default',
            notes: ['useful for mappings/normalization, not predictive feature input'],
        },
    ];
}

function buildPredictionHorizonPolicy() {
    return {
        prediction_time_cutoff_is_mandatory: true,
        feature_availability_must_be_evaluated_relative_to_cutoff: true,
        no_post_match_or_in_match_data_in_pre_match_model: true,
        no_closing_odds_in_t_minus_24h_model: true,
        no_current_match_result_score_or_event_outcome_leakage: true,
        no_future_h2h_or_table_snapshot_after_kickoff: true,
        lineup_timestamp_rule: 'lineup_timestamp <= prediction_cutoff_time',
        odds_timestamp_rule: 'odds_timestamp <= prediction_cutoff_time',
        table_snapshot_rule: 'table_snapshot_at <= prediction_cutoff_time',
        h2h_future_leakage_rule:
            'content.h2h entries must refer only to matches with event_time < kickoff_time and no current/future fixture echo',
        prediction_horizons: [
            {
                horizon: 'T_MINUS_24H',
                odds_rule: 'may use only snapshots captured at or before T_MINUS_24H; closing odds forbidden',
            },
            {
                horizon: 'T_MINUS_6H',
                odds_rule: 'may use only snapshots captured at or before T_MINUS_6H',
            },
            {
                horizon: 'T_MINUS_1H',
                odds_rule: 'may use only snapshots captured at or before T_MINUS_1H',
            },
            {
                horizon: 'CLOSING_OR_NEAR_KICKOFF',
                odds_rule: 'near-kickoff model may use near-kickoff odds only if captured before kickoff',
            },
        ],
    };
}

function buildLargeScaleAcquisitionRoadmap() {
    return {
        current_8_matches_are_samples_not_training_set: true,
        training_requires_large_scale_dataset: true,
        future_expansion_axes: ['league', 'season', 'status'],
        workflow: [
            'batch target inventory',
            'no-write preflight first',
            'controlled write second',
            'coverage profile by league/season',
        ],
        low_tier_league_risks: [
            'missing lineup',
            'missing playerStats',
            'missing shotmap',
            'missing momentum',
            'missing stats',
        ],
        parser_must_be_optional_first: true,
        no_assumption_seeded_ligue1_generalizes_to_all_leagues: true,
    };
}

function buildOddsRawRoadmap() {
    return {
        fotmob_pageprops_role: 'match-detail/factual raw source',
        odds_role: 'market-pricing raw source',
        odds_should_be_stored_separately: true,
        odds_storage_recommendation: 'bookmaker_odds_history or versioned odds raw table',
        odds_raw_should_be_ingested_early: true,
        odds_features_must_wait_for_cutoff_policy: true,
        required_raw_fields: [
            'match_id',
            'source',
            'bookmaker',
            'market_type',
            'selection',
            'odds_decimal',
            'collected_at',
            'odds_timestamp',
            'source_snapshot_at',
            'kickoff_time',
            'time_to_kickoff',
            'raw_payload',
            'data_hash',
            'data_version',
        ],
        odds_feature_examples: [
            'implied probabilities',
            'market margin',
            'consensus odds',
            'movement between snapshots',
            'opening / T-24h / T-6h / T-1h / closing odds',
        ],
        leakage_policy: {
            odds_timestamp_rule: 'odds_timestamp <= prediction_cutoff_time',
            t_minus_24h_rule: 'T_MINUS_24H model cannot use closing odds',
            near_kickoff_rule: 'near-kickoff model can use near-kickoff odds',
        },
        existing_schema_audit: {
            bookmaker_odds_history_row_count: 2,
            columns: [
                'match_id',
                'bookmaker_name',
                'market_type',
                'open_odds',
                'close_odds',
                'movement_trajectory',
                'alignment_meta',
                'source_html_path',
                'source_digest',
                'collected_at',
            ],
            unique_constraint: '(match_id, bookmaker_name, market_type)',
            finding:
                'current schema is open/close + trajectory oriented, not yet cutoff-time-first raw snapshot design',
        },
        no_odds_ingestion_this_phase: true,
    };
}

function buildPlanningOutput() {
    return {
        phase: PHASE,
        planning_only: true,
        db_write_executed: false,
        network_executed: false,
        parser_implementation_executed: false,
        feature_extraction_executed: false,
        training_executed: false,
        prediction_executed: false,
        filesystem_write_executed: false,
        child_process_executed: false,
        current_sample_notice: {
            current_seeded_pageprops_v2_rows: 8,
            training_dataset: false,
            statement: 'current 8 matches are samples, not training data',
        },
        parser_module_plan: buildParserModulePlan(),
        leakage_safe_feature_policy: buildPredictionHorizonPolicy(),
        large_scale_pageprops_v2_acquisition_roadmap: buildLargeScaleAcquisitionRoadmap(),
        odds_raw_roadmap: buildOddsRawRoadmap(),
        recommended_next_phases: [
            'Phase 5.21L2Q: large-scale pageProps v2 acquisition strategy planning',
            'Phase 5.22L2A: odds raw schema / source / leakage policy planning and existing module audit',
            'Phase 5.22L2B: odds raw controlled preflight small sample',
        ],
    };
}

function buildErrorOutput(errors = []) {
    return {
        phase: PHASE,
        planning_only: true,
        blocked: true,
        errors,
        db_write_executed: false,
        network_executed: false,
        parser_implementation_executed: false,
        feature_extraction_executed: false,
        training_executed: false,
        prediction_executed: false,
    };
}

function printUsage(io = process.stderr) {
    io.write(
        [
            'Usage:',
            '  node scripts/ops/pageprops_v2_parser_boundary_leakage_plan.js \\',
            '    --source=fotmob \\',
            '    --raw-version=fotmob_pageprops_v2 \\',
            '    --planning-scope=parser-boundary-leakage-acquisition-odds-roadmap \\',
            '    --allow-db-write=no \\',
            '    --allow-network=no \\',
            '    --allow-parser-implementation=no \\',
            '    --allow-feature-extraction=no \\',
            '    --allow-training=no \\',
            '    --allow-prediction=no',
            '',
        ].join('\n')
    );
}

function execute(argv = process.argv.slice(2), io = {}) {
    const stdout = io.stdout || process.stdout;
    const stderr = io.stderr || process.stderr;
    const parsed = parseArgs(argv);

    if (parsed.help) {
        printUsage(stdout);
        return 0;
    }

    const validation = validatePlanningInput(parsed);
    if (!validation.ok) {
        stderr.write(`${JSON.stringify(buildErrorOutput(validation.errors), null, 2)}\n`);
        return 1;
    }

    stdout.write(`${JSON.stringify(buildPlanningOutput(), null, 2)}\n`);
    return 0;
}

if (require.main === module) {
    process.exitCode = execute();
}

module.exports = {
    PHASE,
    SOURCE,
    RAW_VERSION,
    PLANNING_SCOPE,
    PREDICTION_HORIZONS,
    parseArgs,
    validatePlanningInput,
    buildParserModulePlan,
    buildPredictionHorizonPolicy,
    buildLargeScaleAcquisitionRoadmap,
    buildOddsRawRoadmap,
    buildPlanningOutput,
    execute,
};
