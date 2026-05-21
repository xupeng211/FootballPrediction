#!/usr/bin/env node
'use strict';

const PHASE = 'PHASE5_21L2S_SINGLE_LEAGUE_SMALL_BATCH_TARGET_MANIFEST_PLANNING';
const SOURCE = 'fotmob';
const ROUTE = 'html_hydration';
const RAW_VERSION = 'fotmob_pageprops_v2';
const HASH_STRATEGY = 'stable_pageprops_payload_v1';
const LEAGUE_ID = 53;
const LEAGUE_NAME = 'Ligue 1';
const SEASON = '2025/2026';
const BATCH_ID = 'fotmob-pageprops-v2-ligue1-2025-2026-profile-001';
const BATCH_TYPE = 'profile_batch';
const BATCH_SIZE_POLICY = '20-50';
const PLANNING_SCOPE = 'single-league-small-batch-target-manifest';
const MIN_PROFILE_TARGETS = 20;
const MAX_PROFILE_TARGETS = 50;
const BLOCKED_PENDING_DISCOVERY = 'blocked_pending_authorized_target_discovery';
const READY_FOR_PREFLIGHT = 'ready_for_no_write_preflight';
const REQUIRED_NEXT_STEP = 'authorized_target_discovery_or_source_inventory';

const EXPECTED_ROW_COUNTS = Object.freeze({
    matches: 10,
    raw_match_data: 18,
    bookmaker_odds_history: 2,
    l3_features: 2,
    match_features_training: 2,
    predictions: 2,
});

function completedInventoryRow(match_id, external_id, home_team, away_team) {
    return {
        match_id,
        external_id,
        league_id: LEAGUE_ID,
        league_name: LEAGUE_NAME,
        season: SEASON,
        home_team,
        away_team,
        match_date: '2026-05-10T19:00:00Z',
        status: 'finished',
        existing_versions: ['fotmob_html_hyd_v1', 'fotmob_pageprops_v2'],
    };
}

const LOCAL_LIGUE1_2025_2026_INVENTORY = Object.freeze([
    completedInventoryRow('53_20252026_4830746', '4830746', 'Angers', 'Strasbourg'),
    completedInventoryRow('53_20252026_4830747', '4830747', 'Auxerre', 'Nice'),
    completedInventoryRow('53_20252026_4830748', '4830748', 'Le Havre', 'Marseille'),
    completedInventoryRow('53_20252026_4830750', '4830750', 'Metz', 'Lorient'),
    completedInventoryRow('53_20252026_4830751', '4830751', 'Monaco', 'Lille'),
    completedInventoryRow('53_20252026_4830752', '4830752', 'Paris Saint-Germain', 'Brest'),
    completedInventoryRow('53_20252026_4830753', '4830753', 'Rennes', 'Paris FC'),
    completedInventoryRow('53_20252026_4830754', '4830754', 'Toulouse', 'Lyon'),
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
    'inventTargets',
    'fabricateExternalIds',
]);

const TARGET_MANIFEST_FIELDS = Object.freeze([
    'target_id',
    'batch_id',
    'source',
    'route',
    'raw_data_version',
    'hash_strategy',
    'match_id',
    'external_id',
    'source_url',
    'source_path',
    'source_page_url',
    'source_page_url_base',
    'source_url_fragment_external_id',
    'source_slug',
    'source_route_code',
    'schedule_external_id',
    'schedule_date',
    'schedule_home_team',
    'schedule_away_team',
    'source_inventory_record_key',
    'source_inventory_generated_at',
    'identity_evidence_status',
    'league_id',
    'league_name',
    'season',
    'home_team',
    'away_team',
    'kickoff_time',
    'match_date',
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
        route: null,
        rawVersion: null,
        hashStrategy: null,
        leagueId: null,
        leagueName: null,
        season: null,
        batchId: null,
        batchSizePolicy: null,
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
        inventTargets: false,
        fabricateExternalIds: false,
        help: false,
        unknown: [],
    };
    const keyMap = {
        source: 'source',
        route: 'route',
        'raw-version': 'rawVersion',
        raw_version: 'rawVersion',
        'hash-strategy': 'hashStrategy',
        hash_strategy: 'hashStrategy',
        'league-id': 'leagueId',
        league_id: 'leagueId',
        'league-name': 'leagueName',
        league_name: 'leagueName',
        season: 'season',
        'batch-id': 'batchId',
        batch_id: 'batchId',
        'batch-size-policy': 'batchSizePolicy',
        batch_size_policy: 'batchSizePolicy',
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
        'invent-targets': 'inventTargets',
        invent_targets: 'inventTargets',
        'fabricate-external-ids': 'fabricateExternalIds',
        fabricate_external_ids: 'fabricateExternalIds',
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
        'inventTargets',
        'fabricateExternalIds',
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

function cliName(flagName) {
    return flagName.replace(/[A-Z]/g, match => `-${match.toLowerCase()}`);
}

function addExactTextValidation(errors, value, expected, missingMessage, invalidMessage) {
    const normalized = normalizeText(value);
    if (!normalized) {
        errors.push(missingMessage);
        return;
    }
    if (normalized !== expected) {
        errors.push(invalidMessage);
    }
}

function addSourceValidation(errors, value) {
    const normalized = normalizeText(value).toLowerCase();
    if (!normalized) {
        errors.push('missing source=fotmob');
        return;
    }
    if (normalized !== SOURCE) {
        errors.push('source must be fotmob');
    }
}

function addLeagueIdValidation(errors, value) {
    const normalized = normalizeText(value);
    if (!normalized) {
        errors.push('missing league-id=53');
        return;
    }
    if (Number(normalized) !== LEAGUE_ID) {
        errors.push('league-id must be 53 for this phase');
    }
}

function addRequiredNoFlagValidation(errors, input) {
    for (const flagName of REQUIRED_NO_FLAGS) {
        const normalizedValue = normalizeBooleanFlag(input[flagName]);
        if (normalizedValue === true) {
            errors.push(`${cliName(flagName)}=yes is blocked`);
            continue;
        }
        if (normalizedValue !== false) {
            errors.push(`${cliName(flagName)}=no is required`);
        }
    }
}

function addBlockedTrueFlagValidation(errors, input) {
    for (const flagName of BLOCKED_TRUE_FLAGS) {
        if (normalizeBooleanFlag(input[flagName]) === true) {
            errors.push(`${cliName(flagName)}=yes is blocked`);
        }
    }
}

function validatePlanningInput(input = {}) {
    const errors = [];
    const source = normalizeText(input.source).toLowerCase();
    const route = normalizeText(input.route);
    const rawVersion = normalizeText(input.rawVersion);
    const hashStrategy = normalizeText(input.hashStrategy);
    const leagueId = Number(normalizeText(input.leagueId));
    const leagueName = normalizeText(input.leagueName);
    const season = normalizeText(input.season);
    const batchId = normalizeText(input.batchId);
    const batchSizePolicy = normalizeText(input.batchSizePolicy);
    const planningScope = normalizeText(input.planningScope);

    if (Array.isArray(input.unknown) && input.unknown.length > 0) {
        errors.push(`unknown arguments: ${input.unknown.join(', ')}`);
    }

    addSourceValidation(errors, input.source);
    addExactTextValidation(errors, route, ROUTE, 'missing route=html_hydration', 'route must be html_hydration');
    addExactTextValidation(
        errors,
        rawVersion,
        RAW_VERSION,
        'missing raw-version=fotmob_pageprops_v2',
        'raw-version must be fotmob_pageprops_v2'
    );
    addExactTextValidation(
        errors,
        hashStrategy,
        HASH_STRATEGY,
        'missing hash-strategy=stable_pageprops_payload_v1',
        'hash-strategy must be stable_pageprops_payload_v1'
    );
    addLeagueIdValidation(errors, input.leagueId);
    addExactTextValidation(
        errors,
        leagueName,
        LEAGUE_NAME,
        'missing league-name=Ligue 1',
        'league-name must be Ligue 1 for this phase'
    );
    addExactTextValidation(
        errors,
        season,
        SEASON,
        'missing season=2025/2026',
        'season must be 2025/2026 for this phase'
    );
    addExactTextValidation(errors, batchId, BATCH_ID, `missing batch-id=${BATCH_ID}`, `batch-id must be ${BATCH_ID}`);
    addExactTextValidation(
        errors,
        batchSizePolicy,
        BATCH_SIZE_POLICY,
        'missing batch-size-policy=20-50',
        'batch-size-policy must be 20-50'
    );
    addExactTextValidation(
        errors,
        planningScope,
        PLANNING_SCOPE,
        'missing planning-scope=single-league-small-batch-target-manifest',
        'planning-scope must be single-league-small-batch-target-manifest'
    );
    addRequiredNoFlagValidation(errors, input);
    addBlockedTrueFlagValidation(errors, input);

    return {
        ok: errors.length === 0,
        errors,
        value: {
            source,
            route,
            rawVersion,
            hashStrategy,
            leagueId,
            leagueName,
            season,
            batchId,
            batchSizePolicy,
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

function hasVersion(row, version) {
    return Array.isArray(row.existing_versions) && row.existing_versions.includes(version);
}

function isSameScope(row) {
    return (
        Number(row.league_id) === LEAGUE_ID &&
        normalizeText(row.league_name) === LEAGUE_NAME &&
        normalizeText(row.season) === SEASON
    );
}

function isOddsAlignmentReady(row) {
    return Boolean(
        normalizeText(row.match_id) &&
        normalizeText(row.external_id) &&
        normalizeText(row.home_team) &&
        normalizeText(row.away_team) &&
        normalizeText(row.match_date)
    );
}

function baseTarget(row) {
    return {
        target_id: `${BATCH_ID}:${row.match_id}`,
        batch_id: BATCH_ID,
        source: SOURCE,
        route: ROUTE,
        raw_data_version: RAW_VERSION,
        hash_strategy: HASH_STRATEGY,
        match_id: row.match_id,
        external_id: row.external_id,
        source_url: null,
        source_path: null,
        source_page_url: null,
        source_page_url_base: null,
        source_url_fragment_external_id: null,
        source_slug: null,
        source_route_code: null,
        schedule_external_id: row.external_id,
        schedule_date: row.match_date,
        schedule_home_team: row.home_team,
        schedule_away_team: row.away_team,
        source_inventory_record_key: null,
        source_inventory_generated_at: 'unknown',
        identity_evidence_status: 'missing',
        league_id: Number(row.league_id),
        league_name: row.league_name,
        season: row.season,
        home_team: row.home_team,
        away_team: row.away_team,
        kickoff_time: row.match_date,
        match_date: row.match_date,
        status: row.status,
        existing_versions: Array.isArray(row.existing_versions) ? [...row.existing_versions] : [],
        odds_alignment_ready: isOddsAlignmentReady(row),
    };
}

function buildKnownCompletedTargets(localInventory = LOCAL_LIGUE1_2025_2026_INVENTORY) {
    return localInventory
        .filter(row => isSameScope(row) && hasVersion(row, RAW_VERSION))
        .sort((left, right) => String(left.match_id).localeCompare(String(right.match_id)))
        .map(row => ({
            ...baseTarget(row),
            target_status: 'already_completed',
            exclude_from_new_profile_batch: true,
            reason: 'already_has_fotmob_pageprops_v2',
        }));
}

function buildCandidateTargets(localInventory = LOCAL_LIGUE1_2025_2026_INVENTORY) {
    return localInventory
        .filter(row => isSameScope(row) && !hasVersion(row, RAW_VERSION))
        .sort((left, right) => {
            const dateCompare = String(left.match_date || '').localeCompare(String(right.match_date || ''));
            if (dateCompare !== 0) {
                return dateCompare;
            }
            return String(left.match_id).localeCompare(String(right.match_id));
        })
        .map((row, index) => ({
            ...baseTarget(row),
            target_status: 'planned',
            priority: index + 1,
            expected_coverage_tier: 'unknown_until_profiled',
            preflight_status: 'not_started',
            baseline_hash: null,
            last_preflight_at: null,
            write_status: 'not_authorized',
            write_attempt_count: 0,
            failure_reason: null,
            source_fidelity_notes: 'pending_authorized_no_write_preflight',
            created_at: null,
            updated_at: null,
        }));
}

function determineTargetPopulationStatus(candidateTargets) {
    if (candidateTargets.length >= MIN_PROFILE_TARGETS && candidateTargets.length <= MAX_PROFILE_TARGETS) {
        return READY_FOR_PREFLIGHT;
    }
    return BLOCKED_PENDING_DISCOVERY;
}

function buildBatchMetadata(targetPopulationStatus = BLOCKED_PENDING_DISCOVERY) {
    return {
        batch_id: BATCH_ID,
        source: SOURCE,
        route: ROUTE,
        raw_data_version: RAW_VERSION,
        hash_strategy: HASH_STRATEGY,
        league_id: LEAGUE_ID,
        league_name: LEAGUE_NAME,
        season: SEASON,
        batch_type: BATCH_TYPE,
        batch_size_policy: BATCH_SIZE_POLICY,
        target_population_status: targetPopulationStatus,
    };
}

function buildTargetManifestSchema() {
    return TARGET_MANIFEST_FIELDS.map(field => ({
        field,
        required_for_future_target: true,
    }));
}

function buildSelectionPolicy() {
    return [
        'first profile batch should target the same league/season as seeded validation',
        'exclude already completed fotmob_pageprops_v2 targets',
        'prefer finished matches first for stable pageProps profile',
        'include scheduled matches only in a later phase if prediction-time raw policy is defined',
        'avoid cancelled/postponed/abandoned unless explicitly profiled',
        'require stable external_id and match_id',
        'require kickoff_time / match_date for odds alignment readiness',
        'require duplicate detection before preflight',
        'do not use matches as an uncontrolled acquisition workflow queue',
    ];
}

function buildReadinessGates() {
    return [
        'manifest reviewed',
        'target identities verified',
        'no invented external_id',
        'duplicate detection passed',
        'no existing fotmob_pageprops_v2 for new targets',
        'explicit network authorization before target discovery/preflight',
        'no-write preflight before write',
        'baseline hash capture before write',
        'separate final DB write confirmation before controlled write',
    ];
}

function buildNextPhaseRecommendation(candidateTargets) {
    if (candidateTargets.length < MIN_PROFILE_TARGETS) {
        return [
            {
                phase: 'Phase 5.21L2T0',
                title: 'authorized single-league target discovery / source inventory preflight',
                required_because: 'local DB does not contain 20-50 real new Ligue 1 2025/2026 candidates without v2',
                constraints: [
                    'requires explicit network authorization',
                    'no DB write',
                    'discover 20-50 real FotMob external_ids for Ligue 1 2025/2026',
                    'output manifest update proposal',
                    'no raw_match_data write',
                    'no parser/features/training',
                ],
            },
            {
                phase: 'Phase 5.21L2T',
                title: 'single-league small-batch no-write pageProps v2 preflight',
                constraints: [
                    'only after manifest has 20-50 verified real targets',
                    'only after explicit network authorization',
                    'no DB write',
                    'capture stable_pageprops_payload_v1 baseline hashes',
                ],
            },
            {
                phase: 'Phase 5.22L2A',
                title: 'odds raw schema / source / leakage policy planning and existing module audit',
                constraints: ['no odds access', 'no DB write', 'inspect existing odds modules only'],
            },
        ];
    }
    return [
        {
            phase: 'Phase 5.21L2T',
            title: 'single-league small-batch no-write pageProps v2 preflight',
            constraints: [
                'only after explicit network authorization',
                'no DB write',
                'limited 20-50 targets',
                'capture stable_pageprops_payload_v1 baseline hashes',
            ],
        },
        {
            phase: 'Phase 5.22L2A',
            title: 'odds raw schema / source / leakage policy planning and existing module audit',
            constraints: ['no odds access', 'no DB write', 'inspect existing odds modules only'],
        },
    ];
}

function buildManifestProposal(localInventory = LOCAL_LIGUE1_2025_2026_INVENTORY) {
    const knownCompletedTargets = buildKnownCompletedTargets(localInventory);
    const candidateTargets = buildCandidateTargets(localInventory);
    const targetPopulationStatus = determineTargetPopulationStatus(candidateTargets);

    return {
        schema_version: 'target_manifest_proposal_v1',
        ...buildBatchMetadata(targetPopulationStatus),
        league: {
            league_id: LEAGUE_ID,
            league_name: LEAGUE_NAME,
            season: SEASON,
        },
        target_population_status: targetPopulationStatus,
        known_completed_targets: knownCompletedTargets,
        candidate_targets: candidateTargets,
        candidate_targets_count: candidateTargets.length,
        candidate_targets_required_min: MIN_PROFILE_TARGETS,
        candidate_targets_required_max: MAX_PROFILE_TARGETS,
        local_inventory_status:
            candidateTargets.length >= MIN_PROFILE_TARGETS
                ? 'local_inventory_has_enough_real_candidates'
                : 'local_inventory_does_not_have_20_to_50_real_candidates',
        target_manifest_schema: buildTargetManifestSchema(),
        selection_policy: buildSelectionPolicy(),
        readiness_gates: buildReadinessGates(),
        required_next_step:
            candidateTargets.length < MIN_PROFILE_TARGETS ? REQUIRED_NEXT_STEP : 'single_league_no_write_preflight',
        no_invented_targets: true,
        no_fabricated_external_ids: true,
        no_fabricated_match_ids: true,
        no_fabricated_kickoff_times: true,
        no_fabricated_teams: true,
    };
}

function buildPlanningOutput(options = {}) {
    const localInventory = options.localInventory || LOCAL_LIGUE1_2025_2026_INVENTORY;
    const manifestProposal = buildManifestProposal(localInventory);
    const candidateTargets = manifestProposal.candidate_targets;

    return {
        phase: PHASE,
        planning_only: true,
        manifest_proposal_only: true,
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
        invented_targets: false,
        fabricated_external_ids: false,
        current_db_baseline: EXPECTED_ROW_COUNTS,
        local_inventory_source: 'read-only DB baseline captured for Phase 5.21L2S planning',
        batch_metadata: buildBatchMetadata(manifestProposal.target_population_status),
        known_completed_targets: manifestProposal.known_completed_targets,
        new_target_candidate_population: {
            candidate_targets_count: candidateTargets.length,
            candidate_targets: candidateTargets,
            target_population_status: manifestProposal.target_population_status,
            enough_for_profile_batch: candidateTargets.length >= MIN_PROFILE_TARGETS,
            required_next_step: manifestProposal.required_next_step,
            local_db_insufficient_for_20_to_50_real_targets: candidateTargets.length < MIN_PROFILE_TARGETS,
            do_not_invent_target_ids: true,
            do_not_fabricate_external_id: true,
            do_not_fabricate_kickoff_time: true,
            do_not_fabricate_teams: true,
        },
        target_manifest_schema: manifestProposal.target_manifest_schema,
        selection_policy: manifestProposal.selection_policy,
        readiness_gates: manifestProposal.readiness_gates,
        manifest_proposal: manifestProposal,
        next_phase_recommendation: buildNextPhaseRecommendation(candidateTargets),
        parser_features_training_blocked: true,
    };
}

function buildErrorOutput(errors = []) {
    return {
        phase: PHASE,
        planning_only: true,
        manifest_proposal_only: true,
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
        invented_targets: false,
        fabricated_external_ids: false,
    };
}

function printUsage(io = process.stderr) {
    io.write(
        [
            'Usage:',
            '  node scripts/ops/single_league_small_batch_target_manifest_plan.js \\',
            '    --source=fotmob \\',
            '    --route=html_hydration \\',
            '    --raw-version=fotmob_pageprops_v2 \\',
            '    --hash-strategy=stable_pageprops_payload_v1 \\',
            '    --league-id=53 \\',
            '    --league-name="Ligue 1" \\',
            '    --season=2025/2026 \\',
            `    --batch-id=${BATCH_ID} \\`,
            '    --batch-size-policy=20-50 \\',
            '    --planning-scope=single-league-small-batch-target-manifest \\',
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
    parseArgs,
    validatePlanningInput,
    buildKnownCompletedTargets,
    buildCandidateTargets,
    determineTargetPopulationStatus,
    buildBatchMetadata,
    buildTargetManifestSchema,
    buildSelectionPolicy,
    buildReadinessGates,
    buildNextPhaseRecommendation,
    buildManifestProposal,
    buildPlanningOutput,
    execute,
};
