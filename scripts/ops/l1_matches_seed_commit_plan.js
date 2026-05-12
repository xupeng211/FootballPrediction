#!/usr/bin/env node
'use strict';

const PHASE = 'PHASE5_06L1_CONTROLLED_MATCHES_SEED_COMMIT_PLANNING';
const SAFE_SOURCE = 'fotmob';
const SAFE_SCOPES = new Set(['league_season_date', 'controlled_candidates_preview']);
const MAX_SEED_ROWS_LIMIT = 10;
const DEFAULT_MAX_SEED_ROWS = 10;
const BLOCKED_COMMIT_MESSAGE = 'BLOCKED: L1 matches seed commit is not executable in Phase 5.06L1 planning.';
const NEXT_REQUIRED_PHASE = 'Phase 5.07L1 controlled matches seed commit authorization';

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

function parseInteger(value, fallback = null) {
    if (value === null || value === undefined || value === '') {
        return fallback;
    }
    const normalized = String(value).trim();
    if (!/^\d+$/.test(normalized)) {
        return Number.NaN;
    }
    const parsed = Number.parseInt(normalized, 10);
    return Number.isInteger(parsed) ? parsed : Number.NaN;
}

function normalizeOptionalText(value) {
    if (value === null || value === undefined || value === '') {
        return null;
    }
    return String(value).trim();
}

function normalizeEnvBoolean(inputValue, envValue) {
    return normalizeBooleanFlag(inputValue, false) || normalizeBooleanFlag(envValue, false);
}

function parseOptionValue(arg, argv, index) {
    if (arg.includes('=')) {
        return {
            value: arg.slice(arg.indexOf('=') + 1),
            consumedNext: false,
        };
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
        scope: null,
        leagueId: null,
        season: null,
        date: null,
        candidateCount: null,
        containsTargetMatchId: null,
        containsTargetLabel: null,
        maxSeedRows: null,
        commit: false,
        allowDbWrite: false,
        allowMatchesWrite: false,
        allowRawMatchDataWrite: false,
        training: false,
        prediction: false,
        help: false,
    };

    const keyMap = {
        source: 'source',
        scope: 'scope',
        'league-id': 'leagueId',
        league_id: 'leagueId',
        season: 'season',
        date: 'date',
        'candidate-count': 'candidateCount',
        candidate_count: 'candidateCount',
        'contains-target-match-id': 'containsTargetMatchId',
        contains_target_match_id: 'containsTargetMatchId',
        'contains-target-label': 'containsTargetLabel',
        contains_target_label: 'containsTargetLabel',
        'max-seed-rows': 'maxSeedRows',
        max_seed_rows: 'maxSeedRows',
        commit: 'commit',
        'allow-db-write': 'allowDbWrite',
        allow_db_write: 'allowDbWrite',
        'allow-matches-write': 'allowMatchesWrite',
        allow_matches_write: 'allowMatchesWrite',
        'allow-raw-match-data-write': 'allowRawMatchDataWrite',
        allow_raw_match_data_write: 'allowRawMatchDataWrite',
        training: 'training',
        prediction: 'prediction',
        help: 'help',
        h: 'help',
    };

    for (let index = 0; index < argv.length; index += 1) {
        const arg = argv[index];
        if (!arg.startsWith('--')) {
            continue;
        }

        const rawKey = arg.replace(/^--/, '').split('=')[0];
        const optionKey = keyMap[rawKey];
        if (!optionKey) {
            continue;
        }

        const { value, consumedNext } = parseOptionValue(arg, argv, index);
        if (consumedNext) {
            index += 1;
        }

        if (
            [
                'commit',
                'allowDbWrite',
                'allowMatchesWrite',
                'allowRawMatchDataWrite',
                'training',
                'prediction',
                'help',
            ].includes(optionKey)
        ) {
            options[optionKey] = normalizeBooleanFlag(value, true);
            continue;
        }

        options[optionKey] = typeof value === 'boolean' ? String(value) : value;
    }

    return options;
}

function normalizePlanningInput(input = {}, env = process.env) {
    const candidateCount = parseInteger(input.candidateCount, null);
    const maxSeedRows = parseInteger(input.maxSeedRows, DEFAULT_MAX_SEED_ROWS);

    return {
        source: typeof input.source === 'string' ? input.source.trim().toLowerCase() : '',
        scope: typeof input.scope === 'string' ? input.scope.trim() : '',
        leagueId: normalizeOptionalText(input.leagueId),
        season: typeof input.season === 'string' ? input.season.trim() : null,
        date: typeof input.date === 'string' ? input.date.trim() : null,
        candidateCount,
        containsTargetMatchId: normalizeOptionalText(input.containsTargetMatchId),
        containsTargetLabel: normalizeOptionalText(input.containsTargetLabel),
        maxSeedRows,
        commit: normalizeBooleanFlag(input.commit, false),
        allowDbWrite: normalizeEnvBoolean(input.allowDbWrite, env.DB_WRITE),
        allowMatchesWrite: normalizeEnvBoolean(input.allowMatchesWrite, env.MATCHES_WRITE),
        allowRawMatchDataWrite: normalizeEnvBoolean(input.allowRawMatchDataWrite, env.RAW_MATCH_DATA_WRITE),
        training: normalizeEnvBoolean(input.training, env.TRAINING),
        prediction: normalizeEnvBoolean(input.prediction, env.PREDICTION),
    };
}

function validateSourceScope(value, errors) {
    if (!value.source) {
        errors.push('missing source: provide --source=fotmob');
    } else if (value.source !== SAFE_SOURCE) {
        errors.push('unsupported source: only fotmob is allowed');
    }

    if (!value.scope) {
        errors.push('missing scope: provide --scope=league_season_date or --scope=controlled_candidates_preview');
    } else if (!SAFE_SCOPES.has(value.scope)) {
        errors.push(`unsupported scope: ${value.scope}`);
    }
}

function validateRequiredPlanningFields(value, errors) {
    if (!value.leagueId) {
        errors.push('missing league-id');
    }
    if (!value.season) {
        errors.push('missing season');
    }
    if (!value.date) {
        errors.push('missing date');
    } else if (!/^\d{4}-\d{2}-\d{2}$/.test(value.date)) {
        errors.push('invalid date: provide YYYY-MM-DD');
    }
}

function validatePlanningLimits(value, errors) {
    if (!Number.isInteger(value.candidateCount) || value.candidateCount < 0) {
        errors.push('invalid candidate-count: provide a non-negative integer');
    }
    if (!Number.isInteger(value.maxSeedRows) || value.maxSeedRows < 1) {
        errors.push('invalid max-seed-rows: provide a positive integer');
    } else if (value.maxSeedRows > MAX_SEED_ROWS_LIMIT) {
        errors.push(`max-seed-rows > ${MAX_SEED_ROWS_LIMIT} is blocked in Phase 5.06L1`);
    }
    if (
        Number.isInteger(value.candidateCount) &&
        Number.isInteger(value.maxSeedRows) &&
        value.candidateCount > value.maxSeedRows
    ) {
        errors.push('candidate-count must be <= max-seed-rows');
    }
}

function validateBlockedPlanningFlags(value, errors) {
    if (value.commit === true) {
        errors.push(BLOCKED_COMMIT_MESSAGE);
    }
    if (value.allowDbWrite === true) {
        errors.push('allow-db-write=yes is blocked in Phase 5.06L1');
    }
    if (value.allowMatchesWrite === true) {
        errors.push('allow-matches-write=yes is blocked in Phase 5.06L1');
    }
    if (value.allowRawMatchDataWrite === true) {
        errors.push('allow-raw-match-data-write=yes is blocked in Phase 5.06L1');
    }
    if (value.training === true) {
        errors.push('training=yes is blocked in Phase 5.06L1');
    }
    if (value.prediction === true) {
        errors.push('prediction=yes is blocked in Phase 5.06L1');
    }
}

function validatePlanningInput(input = {}, env = process.env) {
    const value = normalizePlanningInput(input, env);
    const errors = [];

    validateSourceScope(value, errors);
    validateRequiredPlanningFields(value, errors);
    validatePlanningLimits(value, errors);
    validateBlockedPlanningFlags(value, errors);

    return {
        ok: errors.length === 0,
        errors,
        value,
    };
}

function buildCandidateToMatchesMappingPolicy() {
    return {
        source_candidate_fields: [
            'match_id',
            'external_id',
            'league_name',
            'season',
            'home_team',
            'away_team',
            'match_date',
            'status',
            'is_finished',
            'data_source',
        ],
        matches_target_fields: {
            match_id: {
                source: 'candidate.match_id',
                required: true,
                rule: 'primary key / identity key; must match matches.match_id varchar(50)',
            },
            external_id: { source: 'candidate.external_id', required: true },
            league_name: { source: 'candidate.league_name or candidate.league', required: true },
            season: { source: 'candidate.season', required: true, rule: 'must satisfy YYYY/YYYY check constraint' },
            home_team: { source: 'candidate.home_team or candidate.home', required: true },
            away_team: { source: 'candidate.away_team or candidate.away', required: true },
            match_date: { source: 'candidate.match_date', required: true },
            status: { source: 'candidate.status', required: false, rule: 'lowercase value required by schema' },
            is_finished: { source: 'candidate.is_finished or normalized status', required: false },
            data_source: { source: 'candidate.data_source', required: false, default: 'FotMob' },
        },
        allowed_matches_fields_for_future_commit: [
            'match_id',
            'external_id',
            'league_name',
            'season',
            'home_team',
            'away_team',
            'match_date',
            'status',
            'is_finished',
            'data_source',
        ],
        forbidden_tables: [
            'raw_match_data',
            'bookmaker_odds_history',
            'l3_features',
            'match_features_training',
            'predictions',
        ],
        forbidden_field_families: ['features', 'predictions', 'odds history', 'raw JSON payloads'],
    };
}

function buildUpsertPolicy(input) {
    return {
        identity_key: 'matches.match_id',
        conflict_target: 'match_id',
        if_match_id_exists: {
            action: 'would_update_only_after_future_authorization',
            delete_allowed: false,
            preserve_manual_fields: true,
            fields_not_to_overwrite_without_future_authorization: [
                'actual_result',
                'home_score',
                'away_score',
                'venue',
                'referee',
                'pipeline_status',
                'manual review fields',
            ],
        },
        if_match_id_missing: {
            action: 'would_insert_only_after_future_authorization',
        },
        transaction_required_for_future_commit: true,
        max_rows_per_future_commit: input.maxSeedRows,
        only_user_confirmed_candidate_set: true,
        delete_allowed: false,
        raw_match_data_write_allowed: false,
    };
}

function buildBackupPolicy(input) {
    return {
        planning_phase_executes_backup: false,
        pg_dump_allowed_this_phase: false,
        backup_file_write_allowed_this_phase: false,
        future_commit_precheck:
            'SELECT existing rows for the exact affected match_id set before any INSERT/UPDATE executes',
        affected_rows_output: 'stdout or future user-authorized backup artifact only',
        backup_artifact_requires_future_user_authorization: true,
        max_rows: input.maxSeedRows,
    };
}

function buildRollbackPolicy() {
    return {
        planning_phase_executes_rollback: false,
        transaction_required_for_future_commit: true,
        on_commit_failure: 'ROLLBACK transaction',
        post_commit_compensation:
            'Use saved affected rows to generate reviewed compensation SQL in a later authorized phase',
        runtime_rollback_file_write_allowed_this_phase: false,
        delete_execution_allowed_this_phase: false,
        delete_allowed_without_future_authorization: false,
    };
}

function buildPreCommitChecks(input) {
    return [
        'user explicit authorization required',
        'PR/main CI green',
        'clean worktree',
        'DB row counts baseline captured',
        'exact candidate set captured',
        `max rows <= ${input.maxSeedRows}`,
        'source=fotmob',
        'league/date/season match user scope',
        'no raw_match_data write',
        'no feature/prediction write',
        'rollback/backup plan acknowledged',
    ];
}

function buildPostCommitChecks() {
    return [
        'matches row count delta expected',
        'affected match_ids exist',
        'raw_match_data unchanged',
        'features unchanged',
        'predictions unchanged',
        'no training/prediction executed',
    ];
}

function buildMatchesSeedCommitPlan(input = {}, env = process.env) {
    const validation = validatePlanningInput(input, env);
    if (!validation.ok) {
        const error = new Error(validation.errors[0]);
        error.validationErrors = validation.errors;
        throw error;
    }

    const value = validation.value;
    return {
        phase: PHASE,
        planning_only: true,
        source: value.source,
        scope: value.scope,
        league_id: value.leagueId,
        season: value.season,
        date: value.date,
        candidate_count_from_previous_preview: value.candidateCount,
        max_seed_rows: value.maxSeedRows,
        contains_target_match_id: value.containsTargetMatchId,
        contains_target_label: value.containsTargetLabel,
        matches_seed_commit_ready: false,
        matches_seed_commit_authorized: false,
        db_write_allowed: false,
        matches_write_allowed: false,
        raw_match_data_write_allowed: false,
        training_allowed: false,
        prediction_allowed: false,
        would_write_matches: false,
        would_write_raw_match_data: false,
        would_write_db: false,
        would_call_fixture_repository_persist: false,
        would_call_discovery_service_discover: false,
        would_run_titan_discovery: false,
        would_train: false,
        would_predict: false,
        commit_gate: 'blocked',
        candidate_to_matches_mapping_policy: buildCandidateToMatchesMappingPolicy(value),
        upsert_policy: buildUpsertPolicy(value),
        backup_policy: buildBackupPolicy(value),
        rollback_policy: buildRollbackPolicy(value),
        pre_commit_checks: buildPreCommitChecks(value),
        post_commit_checks: buildPostCommitChecks(value),
        next_required_phase: NEXT_REQUIRED_PHASE,
    };
}

function buildErrorPayload(options, errors) {
    const normalized = normalizePlanningInput(options);
    return {
        phase: PHASE,
        planning_only: true,
        ok: false,
        errors: Array.isArray(errors) ? errors : [String(errors)],
        source: normalized.source || null,
        scope: normalized.scope || null,
        league_id: normalized.leagueId,
        season: normalized.season,
        date: normalized.date,
        db_write_allowed: false,
        matches_write_allowed: false,
        raw_match_data_write_allowed: false,
        would_write_matches: false,
        would_write_raw_match_data: false,
        would_write_db: false,
        would_call_fixture_repository_persist: false,
        would_call_discovery_service_discover: false,
        would_run_titan_discovery: false,
        would_train: false,
        would_predict: false,
        commit_gate: 'blocked',
        next_required_phase: NEXT_REQUIRED_PHASE,
    };
}

function showHelp(io = {}) {
    const stdout = io.stdout || (text => process.stdout.write(text));
    stdout(
        [
            'Usage:',
            '  node scripts/ops/l1_matches_seed_commit_plan.js --source=fotmob --scope=league_season_date --league-id=53 --season=2025/2026 --date=2026-05-10 --candidate-count=8 --contains-target-match-id=4830746 --contains-target-label="Angers vs Strasbourg" --max-seed-rows=10 --commit=no',
            '',
            'Phase 5.06L1: planning-only, no DB writes, no network, no browser/proxy.',
        ].join('\n')
    );
}

async function runCli(argv = process.argv.slice(2), io = {}, dependencies = {}) {
    const stdout = io.stdout || (text => process.stdout.write(text));
    const stderr = io.stderr || (text => process.stderr.write(text));
    const options = parseArgs(argv);

    if (options.help) {
        showHelp({ stdout });
        return 0;
    }

    try {
        const payload = buildMatchesSeedCommitPlan(options, dependencies.env || process.env);
        stdout(`${JSON.stringify(payload, null, 2)}\n`);
        return 0;
    } catch (error) {
        const payload = buildErrorPayload(options, error.validationErrors || [error.message]);
        stderr(`${payload.errors[0]}\n`);
        stdout(`${JSON.stringify(payload, null, 2)}\n`);
        return 1;
    }
}

if (require.main === module) {
    runCli().then(code => {
        process.exitCode = code;
    });
}

module.exports = {
    parseArgs,
    normalizeBooleanFlag,
    validatePlanningInput,
    buildCandidateToMatchesMappingPolicy,
    buildUpsertPolicy,
    buildBackupPolicy,
    buildRollbackPolicy,
    buildPreCommitChecks,
    buildPostCommitChecks,
    buildMatchesSeedCommitPlan,
    runCli,
};
