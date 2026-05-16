#!/usr/bin/env node
'use strict';

const PHASE = 'PHASE5_21L2Q_LARGE_SCALE_PAGEPROPS_V2_ACQUISITION_STRATEGY_PLAN';
const SOURCE = 'fotmob';
const RAW_VERSION = 'fotmob_pageprops_v2';
const PLANNING_SCOPE = 'large-scale-acquisition-strategy';
const EXPECTED_ROW_COUNTS = Object.freeze({
    matches: 10,
    raw_match_data: 18,
    bookmaker_odds_history: 2,
    l3_features: 2,
    match_features_training: 2,
    predictions: 2,
});
const EXPECTED_DISTRIBUTION = Object.freeze({
    'PHASE4.23': 1,
    'PHASE4.43_SYNTHETIC': 1,
    fotmob_html_hyd_v1: 8,
    fotmob_pageprops_v2: 8,
});
const COVERAGE_MODULE_PATHS = Object.freeze([
    'content',
    'content.lineup',
    'content.matchFacts',
    'content.playerStats',
    'content.shotmap',
    'content.stats',
    'content.h2h',
    'content.table',
    'content.momentum',
    'seo',
    'fallback',
    'translations',
    'header',
    'general',
    'nav',
    'ssr',
    'fetchingLeagueData',
    'hasPendingVAR',
]);
const REQUIRED_NO_FLAGS = Object.freeze([
    'allowDbWrite',
    'allowNetwork',
    'allowRawAcquisition',
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
    'allowSchemaMigration',
    'allowMatchesWrite',
    'allowOddsWrite',
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
        allowRawAcquisition: null,
        allowParserImplementation: null,
        allowFeatureExtraction: null,
        allowTraining: null,
        allowPrediction: null,
        execute: false,
        commit: false,
        touchFotmob: false,
        liveRequest: false,
        allowRawMatchDataWrite: false,
        allowSchemaMigration: false,
        allowMatchesWrite: false,
        allowOddsWrite: false,
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
        'allow-raw-acquisition': 'allowRawAcquisition',
        allow_raw_acquisition: 'allowRawAcquisition',
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
        'allow-schema-migration': 'allowSchemaMigration',
        allow_schema_migration: 'allowSchemaMigration',
        'allow-matches-write': 'allowMatchesWrite',
        allow_matches_write: 'allowMatchesWrite',
        'allow-odds-write': 'allowOddsWrite',
        allow_odds_write: 'allowOddsWrite',
        help: 'help',
        h: 'help',
    };
    const booleanKeys = new Set([
        'allowDbWrite',
        'allowNetwork',
        'allowRawAcquisition',
        'allowParserImplementation',
        'allowFeatureExtraction',
        'allowTraining',
        'allowPrediction',
        'execute',
        'commit',
        'touchFotmob',
        'liveRequest',
        'allowRawMatchDataWrite',
        'allowSchemaMigration',
        'allowMatchesWrite',
        'allowOddsWrite',
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
        errors.push('missing planning-scope=large-scale-acquisition-strategy');
    } else if (planningScope !== PLANNING_SCOPE) {
        errors.push('planning-scope must be large-scale-acquisition-strategy');
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
            allowRawAcquisition: false,
            allowParserImplementation: false,
            allowFeatureExtraction: false,
            allowTraining: false,
            allowPrediction: false,
        },
    };
}

function buildCurrentStateSummary() {
    return {
        current_8_seeded_matches_are_validation_samples_not_training_data: true,
        current_pageprops_v2_pipeline_is_technically_validated: true,
        canonical_read_selects_v2_for_all_8_seeded_matches: true,
        raw_completeness_audit_shows_high_coverage_for_seeded_ligue1_sample: true,
        must_not_be_generalized_to_all_leagues: true,
        current_db_baseline: EXPECTED_ROW_COUNTS,
        raw_match_data_data_version_distribution: EXPECTED_DISTRIBUTION,
        limitation_statement:
            'the seeded Ligue 1 sample validates the pageProps v2 storage/selector/completeness path but does not prove cross-league coverage or training readiness',
        status_priority_note:
            'future expansion should profile finished matches first, keep scheduled slices separate, and continue to block live acquisition until explicitly authorized',
    };
}

function buildTargetExpansionTiers() {
    return [
        {
            tier: 'TIER_0_CURRENT_SEEDED_VALIDATION',
            label: 'Tier 0 current seeded validation',
            purpose: 'preserve the 8-match seeded baseline as the technical validation reference set',
            estimated_scale: '8 matches',
            priority_scope: {
                leagues: ['Ligue 1'],
                seasons: ['2025/2026'],
                statuses: ['finished'],
            },
            expected_risk: 'low technical risk, high representativeness risk',
            required_preflight: 'none beyond existing seeded baselines already completed in L2L/L2M/L2N/L2O',
            required_completeness_audit: 'already completed for the seeded sample',
            go_no_go_gate: 'validation-only reference; never treat Tier 0 as training data',
        },
        {
            tier: 'TIER_1_SINGLE_LEAGUE_SINGLE_SEASON',
            label: 'Tier 1 single-league single-season',
            purpose: 'validate inventory -> preflight -> write -> audit cycle on one controlled expansion slice',
            estimated_scale: '20-50 matches per initial batch',
            priority_scope: {
                leagues: ['Ligue 1'],
                seasons: ['2025/2026'],
                statuses: ['finished first', 'scheduled only in separate profile slices'],
            },
            expected_risk: 'moderate operational risk, low-to-moderate schema risk',
            required_preflight:
                'explicit no-write preflight with stable_pageprops_payload_v1 baselines for every target',
            required_completeness_audit: 'per-batch completeness audit and seeded-sample comparison before scale-up',
            go_no_go_gate:
                'only proceed to larger same-league batches after preflight/write/canonical/audit all stay green',
        },
        {
            tier: 'TIER_2_TOP_EUROPEAN_MULTI_SEASON',
            label: 'Tier 2 top European multi-season',
            purpose: 'expand across top leagues and recent seasons once Tier 1 repeatedly passes',
            estimated_scale: 'hundreds to low thousands of matches across multiple batches',
            priority_scope: {
                leagues: ['Ligue 1', 'EPL', 'La Liga', 'Bundesliga', 'Serie A'],
                seasons: ['2025/2026', '2024/2025', '2023/2024'],
                statuses: ['finished first', 'scheduled slices only after schema/timing readiness review'],
            },
            expected_risk: 'mixed coverage and season-to-season variance, still batch-gated',
            required_preflight: 'batch-level target inventory and conservative serial preflight by league-season slice',
            required_completeness_audit: 'publish league+season coverage profiles before widening season breadth',
            go_no_go_gate: 'only scale after repeated green audits and no systemic 403/hash-drift issues',
        },
        {
            tier: 'TIER_3_BROADER_UEFA_SECOND_TIER',
            label: 'Tier 3 broader UEFA / second-tier',
            purpose: 'test broader competition diversity while explicitly measuring module sparsity risk',
            estimated_scale: 'hundreds per wave after league-specific profile approval',
            priority_scope: {
                leagues: ['Championship', '2. Bundesliga', 'Ligue 2', 'Segunda', 'Serie B'],
                seasons: ['recent completed seasons first'],
                statuses: ['finished first'],
            },
            expected_risk: 'higher coverage variance and league-specific module gaps',
            required_preflight:
                'league-specific preflight slices with duplicate/version audit before any write approval',
            required_completeness_audit:
                'mandatory per-league completeness profile before broader expansion inside that league family',
            go_no_go_gate:
                'no broader rollout inside a second-tier family until the first slice produces an accepted coverage profile',
        },
        {
            tier: 'TIER_4_LOW_TIER_OBSCURE_LEAGUES',
            label: 'Tier 4 low-tier / obscure leagues',
            purpose: 'measure whether low-tier competitions are even usable for advanced parser coverage assumptions',
            estimated_scale: 'small profile-only samples at the low end of the 20-50 range',
            priority_scope: {
                leagues: ['low-tier domestic leagues', 'obscure regional competitions'],
                seasons: ['single recent season first'],
                statuses: ['finished first'],
            },
            expected_risk: 'highest risk for missing lineup/playerStats/shotmap/momentum/stats/table modules',
            required_preflight: 'profile-only no-write sample before any controlled write request',
            required_completeness_audit: 'league-specific profile required; parser remains optional-first',
            go_no_go_gate: 'no advanced-parser assumption unless the profile proves acceptable coverage',
        },
    ];
}

function buildBatchAcquisitionLifecycle() {
    return [
        {
            step: 1,
            key: 'target_inventory_planning',
            description:
                'generate deterministic candidate inventory by league / season / status with explicit target priority',
            hard_gate: 'inventory must have stable identity fields before any future preflight request',
        },
        {
            step: 2,
            key: 'duplicate_existing_version_audit',
            description: 'audit duplicate targets, existing versions, and unexpected v2 presence before any live step',
            hard_gate: 'duplicates or unresolved version state block the target before preflight',
        },
        {
            step: 3,
            key: 'no_write_live_preflight',
            description: 'future authorized no-write preflight recaptures pageProps candidates without DB write',
            hard_gate: 'no preflight execution without explicit network authorization',
        },
        {
            step: 4,
            key: 'stable_pageprops_payload_v1_baseline_hash_capture',
            description: 'capture stable_pageprops_payload_v1 baselines for every target in the authorized batch',
            hard_gate: 'baseline hash must exist for every write candidate',
        },
        {
            step: 5,
            key: 'controlled_write_after_explicit_confirmation',
            description: 'run controlled write only after explicit final confirmation and exact-scope authorization',
            hard_gate: 'hash gate, target scope, and transactional write policy must all pass',
        },
        {
            step: 6,
            key: 'post_write_canonical_read_verification',
            description: 'verify canonical selector chooses fotmob_pageprops_v2 after write',
            hard_gate: 'post-write canonical mismatch blocks further rollout',
        },
        {
            step: 7,
            key: 'raw_completeness_audit',
            description: 'run local completeness audit for the written slice and inspect module/path coverage',
            hard_gate: 'unexpected degradation or suspicious payloads block the next expansion wave',
        },
        {
            step: 8,
            key: 'league_season_status_coverage_profile_update',
            description: 'publish/update league / season / status coverage profile from audit results',
            hard_gate: 'new tier rollout requires an explicit coverage profile update',
        },
        {
            step: 9,
            key: 'parser_eligibility_decision',
            description:
                'decide whether the acquired slice is eligible for future parser planning at that coverage tier',
            hard_gate:
                'parser/features/training stay blocked until coverage profile and leakage policy reviews are accepted',
        },
    ];
}

function buildTargetInventoryDesign() {
    return {
        schema_readiness_note:
            'current read-only matches baseline exposes league_name and match_date but not a standalone league_id column; Phase 5.21L2R should define how future acquisition inventory preserves source-native league_id and kickoff_time aliases before any live FotMob expansion',
        candidate_sources: [
            'existing matches rows that already have stable match_id/external_id metadata',
            'future controlled L1 seeding outputs for new league/season/date windows',
            'manually reviewed staging documents for broader multi-season expansion',
        ],
        inventory_fields: [
            { name: 'match_id', purpose: 'stable internal join key for raw versions and future odds alignment' },
            { name: 'external_id', purpose: 'source-native FotMob match identifier' },
            {
                name: 'league_id',
                purpose: 'source-native competition identifier preserved independently of display name',
            },
            { name: 'season', purpose: 'season partition used for batching and profile aggregation' },
            { name: 'home_team', purpose: 'team identity needed for audit readability and future normalization' },
            { name: 'away_team', purpose: 'team identity needed for audit readability and future normalization' },
            { name: 'kickoff_time', purpose: 'stable kickoff anchor for future cutoff-time and odds alignment work' },
            { name: 'status', purpose: 'finished vs scheduled vs postponed handling' },
            { name: 'source', purpose: 'raw source family, fixed to fotmob for this workflow' },
            { name: 'route', purpose: 'source route, expected html_hydration for pageProps v2' },
            { name: 'data_version', purpose: 'target raw version, fixed to fotmob_pageprops_v2' },
            { name: 'batch_id', purpose: 'deterministic acquisition batch identifier' },
            { name: 'priority', purpose: 'target ordering inside controlled batches' },
            { name: 'existing_versions', purpose: 'current raw versions already stored for the match' },
            { name: 'expected_coverage_tier', purpose: 'expected profile class before write' },
            {
                name: 'acquisition_state',
                purpose: 'planned/preflight_ready/written/profiled/manual_review lifecycle state',
            },
        ],
        inventory_generation_rules: [
            'sort inventory deterministically by priority, league, season, kickoff_time, external_id',
            'track finished, scheduled, postponed, and cancelled targets in separate status slices',
            'preserve route=html_hydration and data_version=fotmob_pageprops_v2 in every future candidate inventory row',
            'record existing raw version state before any authorized preflight is requested',
        ],
        duplicate_detection_rules: [
            'block duplicate (match_id, data_version) targets before preflight',
            'block duplicate (source, external_id, route, data_version) targets before preflight',
            'surface existing fotmob_pageprops_v2 rows as skip/manual-review candidates instead of rewriting them',
        ],
        cancellation_postponement_handling: [
            'carry source status and kickoff changes in inventory metadata instead of silently overwriting older planning state',
            'split rescheduled matches into fresh batch ids when kickoff_time changes materially',
            'keep cancelled/postponed targets out of the same write scope as finished historical backfill',
        ],
        finished_vs_scheduled_match_handling: [
            'prioritize finished matches for completeness profiling and post-write audit stability',
            'treat scheduled matches as separate status slices because module coverage is structurally different before kickoff',
            'keep live matches blocked unless a future phase explicitly authorizes them',
        ],
    };
}

function buildBatchSizingAndSafetyPolicy() {
    return {
        first_batch_should_be_small: true,
        suggested_batch_sizes: {
            profile_batch: '20-50 matches',
            controlled_write_batch: '20-100 matches',
            large_batch_gate: 'allow larger batches only after repeated green preflight/canonical/audit cycles',
        },
        rate_limit_and_concurrency_policy: {
            initial_mode: 'serial only (concurrency=1)',
            future_rate_limit:
                'keep future live requests low-rate and human-reviewed; do not open parallel browser/proxy runtimes',
        },
        retry_policy: {
            default: 'retry=0',
            future_escalation_rule:
                'allow only conservative per-target retry after explicit authorization and route-health evidence',
        },
        hash_gate_required: true,
        hash_strategy: 'stable_pageprops_payload_v1',
        hash_drift_policy: 'any hash drift blocks the target; repeated or multi-target drift blocks the batch',
        systemic_403_captcha_policy:
            'systemic 403/captcha/forbidden markers stop the entire batch and require route-health review',
        invalid_hydration_policy:
            'invalid or truncated hydration blocks the target and routes it to manual source-fidelity review',
        duplicate_target_policy:
            'duplicate target or unexpected existing v2 presence blocks the target before any write scope is approved',
        transaction_policy:
            'all writes must be transactional per authorized batch or per explicitly defined small target group',
        partial_write_policy:
            'no partial write unless the user explicitly authorizes a reduced scope after reviewing blockers',
        missing_module_policy:
            'missing optional modules feed coverage profiling and do not fail ingestion by default; missing core structures block the target',
        post_write_mismatch_policy:
            'any post-write canonical mismatch blocks further rollout until SELECT-only reconciliation succeeds',
        full_body_json_policy: 'full HTML body and full pageProps JSON must never be printed or saved by default',
    };
}

function buildCoverageProfileStrategy() {
    return {
        profile_dimensions: ['league', 'season', 'status'],
        output_metrics: ['present_count', 'missing_count', 'coverage_percent', 'sample_size', 'coverage_tier'],
        coverage_tier_labels: ['high_coverage', 'medium_coverage', 'sparse_coverage', 'unusable_for_advanced_parser'],
        coverage_tier_guidance: {
            high_coverage: 'module is broadly present in the slice and core structure looks healthy',
            medium_coverage: 'module is often present but not reliable enough for default assumptions',
            sparse_coverage: 'module exists only in a minority of targets and should remain optional-only',
            unusable_for_advanced_parser:
                'coverage is too weak or core structure is degraded for advanced parser assumptions',
        },
        module_output_schema: COVERAGE_MODULE_PATHS.map(modulePath => ({
            module_path: modulePath,
            required_metrics: ['present_count', 'missing_count', 'coverage_percent', 'sample_size', 'coverage_tier'],
        })),
        suspicious_payload_checks: [
            'unexpectedly small payloads',
            'captcha/block/forbidden/placeholder markers',
            'invalid hydration payloads',
            'missing core top-level structures',
            'league-season-status slices with abnormal module loss',
        ],
        league_season_status_profile_update_rule:
            'every completed write batch must update a coverage profile keyed by league + season + status before broader rollout',
        current_seeded_sample_warning:
            'the seeded Ligue 1 slice is high coverage, but that result must not be generalized to all leagues or statuses',
    };
}

function buildLowTierObscureLeagueRiskPolicy() {
    return {
        low_tier_leagues_may_not_have_full_module_coverage: true,
        do_not_assume_lineup_playerStats_shotmap_momentum_stats_exist: true,
        parser_must_use_optional_first_design: true,
        feature_groups_must_be_coverage_aware: true,
        leagues_without_shotmap_can_still_support_basic_safe_features: true,
        leagues_without_table_snapshots_may_be_excluded_from_table_based_features: true,
        missing_advanced_modules_should_not_fail_ingestion: true,
        profile_only_sampling_rule:
            'start new low-tier leagues with small profile-only samples and require a league-specific completeness profile before wider write planning',
        no_ligue1_generalization: true,
    };
}

function buildDataVersionSourceFidelityPolicy() {
    return {
        canonical_raw_version: 'fotmob_pageprops_v2',
        legacy_fallback_version: 'fotmob_html_hyd_v1',
        synthetic_unknown_excluded_by_default: true,
        canonical_selector_priority: ['fotmob_pageprops_v2', 'fotmob_html_hyd_v1'],
        data_hash_strategy: 'stable_pageprops_payload_v1',
        raw_data_shape: '_meta + matchId + pageProps',
        source_route_must_be_recorded: true,
        body_sha_metadata_only: true,
        writer_conflict_target: '(match_id, data_version)',
        no_rewrite_of_existing_rows_without_explicit_authorization: true,
    };
}

function buildMatchIdentityAndOddsAlignmentReadiness() {
    return {
        odds_ingestion_this_phase: false,
        stable_match_id_is_critical: true,
        kickoff_time_must_be_reliable: true,
        league_season_team_identity_must_be_normalized: true,
        odds_raw_should_not_be_mixed_into_raw_match_data: true,
        future_odds_join_strategy:
            'future odds raw should join on stable match_id while respecting prediction_cutoff_time / odds_timestamp semantics',
        inventory_metadata_required_for_odds_alignment: [
            'match_id',
            'external_id',
            'league_id',
            'season',
            'home_team',
            'away_team',
            'kickoff_time',
            'status',
            'source',
            'route',
        ],
        current_schema_readiness_note:
            'Phase 5.21L2R should decide how future acquisition inventory stores source-native league_id and kickoff_time without relying only on display labels such as league_name',
    };
}

function buildFailureStrategyMatrix() {
    return [
        {
            failure: 'systemic_403_or_captcha',
            response: 'stop the entire batch, do not retry, and require route-health review before any next attempt',
        },
        {
            failure: 'invalid_hydration',
            response: 'block the target, skip any write, and route it to source-fidelity/manual review',
        },
        {
            failure: 'hash_drift',
            response:
                'block the target immediately; if drift appears repeatedly or across multiple targets, stop the batch and require a fresh preflight baseline',
        },
        {
            failure: 'missing_modules',
            response:
                'record module loss in the coverage profile; missing optional modules do not fail ingestion by default, but missing core modules mark the target unusable',
        },
        {
            failure: 'duplicate_target_or_existing_unexpected_v2',
            response: 'block before preflight/write and require manual dedupe/version audit',
        },
        {
            failure: 'post_write_mismatch',
            response:
                'stop further rollout, run SELECT-only canonical reconciliation, and do not advance to the next batch until resolved',
        },
    ];
}

function buildBlockingPolicy() {
    return {
        parser_features_training_remain_blocked: true,
        block_conditions: [
            'do not implement parser logic until large-scale acquisition coverage tiers and completeness profiles are reviewed',
            'do not generate features until prediction_cutoff_time policy and module-level leakage rules are accepted',
            'do not train or predict until large-scale raw coverage and leakage-safe policy are both approved',
        ],
    };
}

function buildRecommendedNextPhases() {
    return [
        {
            phase: 'Phase 5.21L2R',
            title: 'large-scale acquisition target inventory planning / schema-readiness audit',
            constraints: ['no DB write', 'no network', 'no raw acquisition execution', 'still no FotMob access'],
            purpose:
                'inspect matches schema and source mapping, decide how to represent future acquisition candidates, and define target inventory schema or staging documentation',
        },
        {
            phase: 'Phase 5.21L2S',
            title: 'single-league small-batch pageProps v2 acquisition preflight',
            constraints: [
                'only after explicit network authorization',
                'no DB write',
                'small batch 20-50',
                'collect hashes and coverage summary only',
            ],
            purpose:
                'run the first same-league/same-season no-write preflight and measure stability before any controlled write request',
        },
        {
            phase: 'Phase 5.22L2A',
            title: 'odds raw schema / source / leakage policy planning and existing module audit',
            constraints: ['parallel track', 'no odds access', 'no DB write'],
            purpose:
                'keep odds ingestion separate while planning raw odds history schema, source readiness, and cutoff-time policy',
        },
    ];
}

function buildPlanningOutput() {
    return {
        phase: PHASE,
        planning_only: true,
        db_write_executed: false,
        network_executed: false,
        raw_acquisition_executed: false,
        parser_implementation_executed: false,
        feature_extraction_executed: false,
        training_executed: false,
        prediction_executed: false,
        filesystem_write_executed: false,
        child_process_executed: false,
        current_state_summary: buildCurrentStateSummary(),
        target_expansion_tiers: buildTargetExpansionTiers(),
        batch_acquisition_lifecycle: buildBatchAcquisitionLifecycle(),
        target_inventory_design: buildTargetInventoryDesign(),
        batch_sizing_and_safety_policy: buildBatchSizingAndSafetyPolicy(),
        coverage_profile_strategy: buildCoverageProfileStrategy(),
        low_tier_obscure_league_risk_policy: buildLowTierObscureLeagueRiskPolicy(),
        data_version_source_fidelity_policy: buildDataVersionSourceFidelityPolicy(),
        match_identity_and_odds_alignment_readiness: buildMatchIdentityAndOddsAlignmentReadiness(),
        failure_strategy_matrix: buildFailureStrategyMatrix(),
        blocking_policy: buildBlockingPolicy(),
        recommended_next_phases: buildRecommendedNextPhases(),
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
        raw_acquisition_executed: false,
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
            '  node scripts/ops/large_scale_pageprops_v2_acquisition_strategy_plan.js \\',
            '    --source=fotmob \\',
            '    --raw-version=fotmob_pageprops_v2 \\',
            '    --planning-scope=large-scale-acquisition-strategy \\',
            '    --allow-db-write=no \\',
            '    --allow-network=no \\',
            '    --allow-raw-acquisition=no \\',
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
    COVERAGE_MODULE_PATHS,
    parseArgs,
    validatePlanningInput,
    buildCurrentStateSummary,
    buildTargetExpansionTiers,
    buildBatchAcquisitionLifecycle,
    buildTargetInventoryDesign,
    buildBatchSizingAndSafetyPolicy,
    buildCoverageProfileStrategy,
    buildLowTierObscureLeagueRiskPolicy,
    buildDataVersionSourceFidelityPolicy,
    buildMatchIdentityAndOddsAlignmentReadiness,
    buildFailureStrategyMatrix,
    buildBlockingPolicy,
    buildRecommendedNextPhases,
    buildPlanningOutput,
    execute,
};
