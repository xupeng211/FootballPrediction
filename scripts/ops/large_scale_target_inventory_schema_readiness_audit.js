#!/usr/bin/env node
'use strict';

const PHASE = 'PHASE5_21L2R_LARGE_SCALE_TARGET_INVENTORY_SCHEMA_READINESS_AUDIT';
const SOURCE = 'fotmob';
const RAW_VERSION = 'fotmob_pageprops_v2';
const PLANNING_SCOPE = 'target-inventory-schema-readiness';
const EXPECTED_ROW_COUNTS = Object.freeze({
    matches: 10,
    raw_match_data: 18,
    bookmaker_odds_history: 2,
    l3_features: 2,
    match_features_training: 2,
    predictions: 2,
});
const EXPECTED_VERSION_DISTRIBUTION = Object.freeze({
    'PHASE4.23': 1,
    'PHASE4.43_SYNTHETIC': 1,
    fotmob_html_hyd_v1: 8,
    fotmob_pageprops_v2: 8,
});
const MATCHES_COLUMNS = Object.freeze([
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
    'collection_date',
    'created_at',
    'updated_at',
    'data_version',
    'data_source',
    'pipeline_status',
    'home_corners',
    'away_corners',
    'home_yellow_cards',
    'away_yellow_cards',
    'home_red_cards',
    'away_red_cards',
    'referee',
]);
const MATCHES_CONSTRAINTS = Object.freeze([
    'PRIMARY KEY (match_id)',
    'CHECK pipeline_status in pending/processing/harvested/failed/skipped/RECON_LINKED/RECON_MISMATCH',
    'CHECK season format ^\\d{4}/\\d{4}$',
    'CHECK status is lowercase',
    'CHECK valid_scores',
]);
const RAW_MATCH_DATA_COLUMNS = Object.freeze([
    'id',
    'match_id',
    'external_id',
    'raw_data',
    'collected_at',
    'data_version',
    'data_hash',
]);
const RAW_MATCH_DATA_CONSTRAINTS = Object.freeze([
    'PRIMARY KEY (id)',
    'UNIQUE (match_id, data_version)',
    'FOREIGN KEY (match_id) REFERENCES matches(match_id) ON DELETE CASCADE',
    'CHECK collected_at_not_null',
    'CHECK match_id_format',
    'CHECK raw_data_not_empty',
    'CHECK raw_data_has_match_id_or_general_or_header',
]);
const EXISTING_VERSION_STATE = Object.freeze([
    { match_id: '140_20252026_4837496', external_id: '4837496', versions: ['PHASE4.23'], raw_rows: 1 },
    { match_id: '47_20242025_900002', external_id: '900002', versions: ['PHASE4.43_SYNTHETIC'], raw_rows: 1 },
    {
        match_id: '53_20252026_4830746',
        external_id: '4830746',
        versions: ['fotmob_html_hyd_v1', 'fotmob_pageprops_v2'],
        raw_rows: 2,
    },
    {
        match_id: '53_20252026_4830747',
        external_id: '4830747',
        versions: ['fotmob_html_hyd_v1', 'fotmob_pageprops_v2'],
        raw_rows: 2,
    },
    {
        match_id: '53_20252026_4830748',
        external_id: '4830748',
        versions: ['fotmob_html_hyd_v1', 'fotmob_pageprops_v2'],
        raw_rows: 2,
    },
    {
        match_id: '53_20252026_4830750',
        external_id: '4830750',
        versions: ['fotmob_html_hyd_v1', 'fotmob_pageprops_v2'],
        raw_rows: 2,
    },
    {
        match_id: '53_20252026_4830751',
        external_id: '4830751',
        versions: ['fotmob_html_hyd_v1', 'fotmob_pageprops_v2'],
        raw_rows: 2,
    },
    {
        match_id: '53_20252026_4830752',
        external_id: '4830752',
        versions: ['fotmob_html_hyd_v1', 'fotmob_pageprops_v2'],
        raw_rows: 2,
    },
    {
        match_id: '53_20252026_4830753',
        external_id: '4830753',
        versions: ['fotmob_html_hyd_v1', 'fotmob_pageprops_v2'],
        raw_rows: 2,
    },
    {
        match_id: '53_20252026_4830754',
        external_id: '4830754',
        versions: ['fotmob_html_hyd_v1', 'fotmob_pageprops_v2'],
        raw_rows: 2,
    },
]);
const REQUIRED_NO_FLAGS = Object.freeze([
    'allowDbWrite',
    'allowNetwork',
    'allowRawAcquisition',
    'allowSchemaMigration',
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
    'allowMatchesWrite',
    'allowOddsWrite',
    'migrate',
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
        allowSchemaMigration: null,
        allowParserImplementation: null,
        allowFeatureExtraction: null,
        allowTraining: null,
        allowPrediction: null,
        execute: false,
        commit: false,
        touchFotmob: false,
        liveRequest: false,
        allowRawMatchDataWrite: false,
        allowMatchesWrite: false,
        allowOddsWrite: false,
        migrate: false,
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
        'allow-schema-migration': 'allowSchemaMigration',
        allow_schema_migration: 'allowSchemaMigration',
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
        'allow-matches-write': 'allowMatchesWrite',
        allow_matches_write: 'allowMatchesWrite',
        'allow-odds-write': 'allowOddsWrite',
        allow_odds_write: 'allowOddsWrite',
        migrate: 'migrate',
        help: 'help',
        h: 'help',
    };
    const booleanKeys = new Set([
        'allowDbWrite',
        'allowNetwork',
        'allowRawAcquisition',
        'allowSchemaMigration',
        'allowParserImplementation',
        'allowFeatureExtraction',
        'allowTraining',
        'allowPrediction',
        'execute',
        'commit',
        'touchFotmob',
        'liveRequest',
        'allowRawMatchDataWrite',
        'allowMatchesWrite',
        'allowOddsWrite',
        'migrate',
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
        errors.push('missing planning-scope=target-inventory-schema-readiness');
    } else if (planningScope !== PLANNING_SCOPE) {
        errors.push('planning-scope must be target-inventory-schema-readiness');
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
            allowSchemaMigration: false,
            allowParserImplementation: false,
            allowFeatureExtraction: false,
            allowTraining: false,
            allowPrediction: false,
        },
    };
}

function buildCurrentSchemaReadinessSummary() {
    return {
        current_db_baseline: EXPECTED_ROW_COUNTS,
        raw_match_data_data_version_distribution: EXPECTED_VERSION_DISTRIBUTION,
        matches_columns: MATCHES_COLUMNS,
        matches_constraints: MATCHES_CONSTRAINTS,
        raw_match_data_columns: RAW_MATCH_DATA_COLUMNS,
        raw_match_data_constraints: RAW_MATCH_DATA_CONSTRAINTS,
        existing_version_state: EXISTING_VERSION_STATE,
        judgments: {
            matches_is_canonical_match_identity: true,
            matches_is_not_acquisition_workflow_queue: true,
            raw_match_data_is_versioned_raw_store: true,
            future_acquisition_state_must_not_be_mixed_into_raw_match_data: true,
            do_not_add_uncontrolled_workflow_flags_into_matches_without_explicit_migration_design: true,
        },
        schema_readiness_statement:
            'matches can anchor canonical match identity, but current matches columns do not cleanly represent future acquisition candidate workflow state, baseline hashes, or per-target preflight/write lifecycle',
    };
}

function buildRepresentationOptions() {
    return [
        {
            option: 'A_REUSE_MATCHES_ONLY',
            label: 'Reuse matches only',
            pros: [
                'reuses the existing canonical identity table',
                'no new table required for short-term discussion',
                'can reference already seeded matches directly',
            ],
            cons: [
                'mixes workflow queue state into canonical identity rows',
                'lacks explicit fields for batch_id, preflight_status, baseline_hash, write_status, failure_reason',
                'encourages matches to become an uncontrolled acquisition queue',
            ],
            risk: 'high risk of schema drift and workflow-state leakage into canonical match identity',
            when_to_use: 'only for read-only identity lookup, not for real acquisition workflow state',
            db_migration_requirement:
                'likely yes if done seriously, because current matches schema lacks core workflow fields',
            ci_review_implications:
                'review noise increases because routine workflow state would touch canonical match rows',
            suitability_for_batch_preflight_write: 'poor',
        },
        {
            option: 'B_DOCS_ONLY_MANIFEST',
            label: 'Docs-only manifest',
            pros: [
                'no DB migration required',
                'easy to review in PRs',
                'works for small planning batches and exact-scope proposals',
            ],
            cons: [
                'not machine-enforced as operational state',
                'manual updates become cumbersome at larger scale',
                'weaker dedupe/state transition guarantees',
            ],
            risk: 'acceptable for short-term planning, weak for sustained operational rollout',
            when_to_use: 'short-term planning and exact-scope batch proposal before real acquisition begins',
            db_migration_requirement: 'no',
            ci_review_implications: 'good human review visibility, but limited automation',
            suitability_for_batch_preflight_write: 'acceptable for small batches only',
        },
        {
            option: 'C_SOURCE_CONTROLLED_JSON_YAML_MANIFEST',
            label: 'JSON/YAML source-controlled target manifest',
            pros: [
                'no DB migration required initially',
                'structured and machine-readable',
                'works better than free-form docs for deterministic batch generation and review',
            ],
            cons: [
                'state transitions still require file churn',
                'concurrent operational updates are awkward',
                'large-scale batch history becomes noisy in Git',
            ],
            risk: 'medium; good interim control plane but not ideal long-term operational store',
            when_to_use: 'short-term and early-medium-term controlled batches before dedicated schema is approved',
            db_migration_requirement: 'no',
            ci_review_implications: 'strong reviewability and deterministic diffs',
            suitability_for_batch_preflight_write: 'good for early controlled batches',
        },
        {
            option: 'D_DEDICATED_ACQUISITION_TARGETS_TABLE_OR_STAGING_TABLE',
            label: 'Dedicated acquisition_targets table / staging table',
            pros: [
                'clean separation between canonical identity and workflow state',
                'supports explicit target state machine and batch metadata',
                'better for dedupe, auditability, and later automation',
            ],
            cons: [
                'needs separate schema planning and migration preflight',
                'requires more upfront design discipline',
                'not allowed in this phase',
            ],
            risk: 'lowest long-term workflow risk, but requires future migration work',
            when_to_use: 'medium-term once target inventory contract is stable and migration preflight is approved',
            db_migration_requirement: 'yes',
            ci_review_implications: 'cleaner long-term diffs once workflow state leaves matches/docs',
            suitability_for_batch_preflight_write: 'best long-term option',
        },
    ];
}

function buildRecommendedRepresentationStrategy() {
    return {
        short_term_strategy:
            'use source-controlled docs/manifest or generated report outputs to plan exact batch scope without DB mutation',
        medium_term_strategy:
            'move to a dedicated acquisition_targets table or acquisition_batches + acquisition_targets schema after separate schema planning and migration preflight',
        canonical_identity_rule: 'matches remains canonical identity, not workflow queue',
        raw_storage_rule: 'raw_match_data remains versioned raw store, not acquisition workflow tracker',
        current_phase_rule: 'do not create acquisition_targets or staging tables in this phase',
    };
}

function buildProposedTargetFields() {
    return [
        'target_id',
        'batch_id',
        'source',
        'route',
        'raw_data_version',
        'hash_strategy',
        'match_id',
        'external_id',
        'league_id_or_league_name',
        'season',
        'home_team',
        'away_team',
        'kickoff_time_or_match_date',
        'status',
        'target_status',
        'priority',
        'expected_coverage_tier',
        'existing_versions',
        'preflight_status',
        'baseline_hash',
        'last_preflight_at',
        'write_status',
        'write_attempt_count',
        'failure_reason',
        'source_fidelity_notes',
        'odds_alignment_ready',
        'created_at',
        'updated_at',
    ];
}

function buildTargetStateMachine() {
    return {
        states: [
            'planned',
            'inventory_validated',
            'existing_version_checked',
            'preflight_ready',
            'preflight_passed',
            'preflight_failed',
            'hash_baseline_ready',
            'write_authorized',
            'write_completed',
            'write_failed',
            'skipped',
            'blocked',
        ],
        transition_rules: [
            'planned -> inventory_validated only after identity fields and exact scope are reviewed',
            'inventory_validated -> existing_version_checked only after duplicate detection runs',
            'existing_version_checked -> preflight_ready only when no conflicting v2 target already exists',
            'preflight_ready -> preflight_passed only after authorized no-write preflight succeeds',
            'preflight_passed -> hash_baseline_ready only after stable baseline hash is captured',
            'hash_baseline_ready -> write_authorized only after explicit final authorization',
            'write_authorized -> write_completed only after hash-gated controlled write succeeds',
            'hash drift returns the target to preflight_failed or blocked depending on severity',
            'duplicate existing v2 should move to skipped or already_exists review state',
            '403/captcha should move target or batch to blocked',
            'invalid hydration should move target to preflight_failed',
            'cancelled/postponed targets should be skipped or blocked according to status policy and kickoff stability',
        ],
        hard_gate: 'no write without preflight_passed + hash_baseline_ready + explicit authorization',
    };
}

function buildSchemaGapFindings() {
    return [
        {
            gap: 'reliable_kickoff_time_alias',
            severity: 'medium',
            finding:
                'matches currently has match_date, but future inventory should define kickoff_time semantics explicitly for acquisition and odds alignment',
        },
        {
            gap: 'league_id_vs_league_name',
            severity: 'high',
            finding:
                'current matches rows expose league_name but not a dedicated source-native league_id column, creating ambiguity for large-scale source mapping',
        },
        {
            gap: 'source_specific_external_id_mapping',
            severity: 'medium',
            finding:
                'external_id exists, but future multi-source or route-aware inventory needs an explicit source-mapping contract',
        },
        {
            gap: 'season_normalization',
            severity: 'low',
            finding:
                'matches has a season format check, which is good, but future inventory should still keep season normalization explicit across source-controlled manifests',
        },
        {
            gap: 'team_identity_normalization',
            severity: 'medium',
            finding:
                'home_team and away_team exist, but no dedicated normalized team identity contract is present for future cross-source joins',
        },
        {
            gap: 'match_status_normalization',
            severity: 'medium',
            finding:
                'status exists and is lowercase, but acquisition-specific handling for cancelled/postponed/abandoned/scheduled/finished is not modeled as workflow state',
        },
        {
            gap: 'acquisition_batch_id',
            severity: 'acceptable_for_short_term_manifest',
            finding:
                'no batch_id exists in matches or raw_match_data; acceptable in docs/manifest short term, but not for long-term workflow storage',
        },
        {
            gap: 'acquisition_state',
            severity: 'acceptable_for_short_term_manifest',
            finding:
                'no target_status/preflight_status/write_status fields exist; these should remain outside matches and raw_match_data until dedicated schema planning',
        },
        {
            gap: 'expected_coverage_tier',
            severity: 'acceptable_for_short_term_manifest',
            finding:
                'coverage-tier planning can live in manifests initially, but not in current canonical tables without explicit design',
        },
        {
            gap: 'baseline_hash_storage_outside_raw_match_data',
            severity: 'high',
            finding:
                'baseline hashes for preflight/write workflow should not be stored ad hoc in raw_match_data before actual writes; they need manifest or future acquisition-target storage',
        },
        {
            gap: 'odds_alignment_metadata',
            severity: 'medium',
            finding:
                'future odds alignment needs stable identity metadata readiness signals, but inventory-level odds readiness is not currently represented',
        },
    ];
}

function buildFutureSchemaOptions() {
    return [
        {
            option: 'OPTION_1_DOCS_ONLY_MANIFEST_FIRST',
            summary: 'start with docs-only or report-generated target manifests while no DB write remains in force',
            migration_required: false,
        },
        {
            option: 'OPTION_2_ACQUISITION_TARGETS_TABLE',
            summary: 'single dedicated acquisition_targets table with explicit per-target workflow fields',
            migration_required: true,
        },
        {
            option: 'OPTION_3_ACQUISITION_BATCHES_PLUS_TARGETS',
            summary: 'separate batch header and target rows for cleaner long-term auditability',
            migration_required: true,
        },
        {
            option: 'OPTION_4_TEMPORARY_ONE_BATCH_STAGING_TABLE',
            summary:
                'temporary staging table for a single batch only, if future operational pressure appears before full schema design',
            migration_required: true,
        },
    ];
}

function buildExampleManifestShape() {
    return {
        batch_id: 'fotmob-pageprops-v2-ligue1-2025-2026-profile-001',
        source: 'fotmob',
        route: 'html_hydration',
        raw_data_version: 'fotmob_pageprops_v2',
        hash_strategy: 'stable_pageprops_payload_v1',
        targets: [
            {
                match_id: '53_20252026_4830746',
                external_id: '4830746',
                league_name: 'Ligue 1',
                season: '2025/2026',
                home_team: 'Angers',
                away_team: 'Strasbourg',
                kickoff_time: '2026-05-10T19:00:00Z',
                status: 'finished',
                target_status: 'planned',
                priority: 1,
                expected_coverage_tier: 'unknown_until_profiled',
            },
        ],
    };
}

function buildReadinessGates() {
    return [
        'target inventory reviewed',
        'duplicate detection passed',
        'match identity stable',
        'kickoff_time present',
        'external_id valid',
        'source route fixed',
        'raw_data_version fixed',
        'no existing target version',
        'network authorization granted',
        'no-write preflight passes',
        'baseline hashes captured',
        'controlled write separately authorized',
    ];
}

function buildOddsAlignmentReadiness() {
    return {
        odds_ingestion_this_phase: false,
        kickoff_time_must_be_preserved: true,
        future_odds_join_depends_on: ['match_id', 'kickoff_time', 'source mapping'],
        odds_raw_remains_separate_source: true,
        target_inventory_must_not_store_odds_values: true,
        odds_alignment_ready_flag_meaning:
            'identity metadata is sufficient for a future odds join; it does not imply any odds values were captured',
    };
}

function buildRecommendedNextPhases() {
    return [
        {
            phase: 'Phase 5.21L2S',
            title: 'single-league small-batch target manifest planning',
            constraints: [
                'no DB write',
                'no network',
                'no raw acquisition',
                'choose one league/season profile batch',
                'generate docs-only target manifest proposal',
                'still no FotMob access',
            ],
        },
        {
            phase: 'Phase 5.21L2T',
            title: 'single-league small-batch no-write preflight',
            constraints: [
                'only after explicit network authorization',
                'no DB write',
                'limited 20-50 targets',
                'capture baseline hashes',
            ],
        },
        {
            phase: 'Phase 5.22L2A',
            title: 'odds raw schema / source / leakage policy planning and existing module audit',
            constraints: ['no odds access', 'no DB write', 'inspect existing odds modules only'],
        },
    ];
}

function buildPlanningOutput() {
    return {
        phase: PHASE,
        planning_only: true,
        audit_only: true,
        db_write_executed: false,
        network_executed: false,
        raw_acquisition_executed: false,
        schema_migration_executed: false,
        parser_implementation_executed: false,
        feature_extraction_executed: false,
        training_executed: false,
        prediction_executed: false,
        filesystem_write_executed: false,
        child_process_executed: false,
        current_schema_readiness_summary: buildCurrentSchemaReadinessSummary(),
        target_inventory_representation_options: buildRepresentationOptions(),
        recommended_representation_strategy: buildRecommendedRepresentationStrategy(),
        proposed_future_acquisition_target_fields: buildProposedTargetFields(),
        target_state_machine: buildTargetStateMachine(),
        schema_gaps_readiness_findings: buildSchemaGapFindings(),
        future_schema_options: buildFutureSchemaOptions(),
        example_manifest_shape: buildExampleManifestShape(),
        readiness_gates_before_real_acquisition: buildReadinessGates(),
        odds_alignment_readiness: buildOddsAlignmentReadiness(),
        recommended_next_phases: buildRecommendedNextPhases(),
    };
}

function buildErrorOutput(errors = []) {
    return {
        phase: PHASE,
        planning_only: true,
        audit_only: true,
        blocked: true,
        errors,
        db_write_executed: false,
        network_executed: false,
        raw_acquisition_executed: false,
        schema_migration_executed: false,
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
            '  node scripts/ops/large_scale_target_inventory_schema_readiness_audit.js \\',
            '    --source=fotmob \\',
            '    --raw-version=fotmob_pageprops_v2 \\',
            '    --planning-scope=target-inventory-schema-readiness \\',
            '    --allow-db-write=no \\',
            '    --allow-network=no \\',
            '    --allow-raw-acquisition=no \\',
            '    --allow-schema-migration=no \\',
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
    MATCHES_COLUMNS,
    MATCHES_CONSTRAINTS,
    RAW_MATCH_DATA_COLUMNS,
    RAW_MATCH_DATA_CONSTRAINTS,
    EXISTING_VERSION_STATE,
    parseArgs,
    validatePlanningInput,
    buildCurrentSchemaReadinessSummary,
    buildRepresentationOptions,
    buildRecommendedRepresentationStrategy,
    buildProposedTargetFields,
    buildTargetStateMachine,
    buildSchemaGapFindings,
    buildFutureSchemaOptions,
    buildExampleManifestShape,
    buildReadinessGates,
    buildOddsAlignmentReadiness,
    buildRecommendedNextPhases,
    buildPlanningOutput,
    execute,
};
