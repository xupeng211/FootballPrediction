#!/usr/bin/env node
'use strict';

const PHASE = 'PHASE5_07L1_CONTROLLED_MATCHES_SEED_COMMIT_AUTHORIZATION';
const SAFE_SOURCE = 'fotmob';
const SAFE_SCOPES = new Set(['league_season_date', 'controlled_candidates_preview']);
const MAX_SEED_ROWS_LIMIT = 10;
const DEFAULT_MAX_SEED_ROWS = 10;
const BLOCKED_COMMIT_MESSAGE = 'BLOCKED: L1 matches seed commit remains authorization-only in Phase 5.07L1.';
const NEXT_REQUIRED_PHASE = 'Phase 5.08L1 controlled matches seed commit execution';

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
        userAuthorizedMatchesSeedCommit: false,
        allowMatchesWriteNextPhase: false,
        allowDbWriteNow: false,
        allowRawMatchDataWrite: false,
        allowTraining: false,
        allowPrediction: false,
        finalHumanConfirmation: false,
        commit: false,
        execute: false,
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
        'user-authorized-matches-seed-commit': 'userAuthorizedMatchesSeedCommit',
        user_authorized_matches_seed_commit: 'userAuthorizedMatchesSeedCommit',
        'allow-matches-write-next-phase': 'allowMatchesWriteNextPhase',
        allow_matches_write_next_phase: 'allowMatchesWriteNextPhase',
        'allow-db-write-now': 'allowDbWriteNow',
        allow_db_write_now: 'allowDbWriteNow',
        'allow-raw-match-data-write': 'allowRawMatchDataWrite',
        allow_raw_match_data_write: 'allowRawMatchDataWrite',
        'allow-training': 'allowTraining',
        allow_training: 'allowTraining',
        training: 'allowTraining',
        'allow-prediction': 'allowPrediction',
        allow_prediction: 'allowPrediction',
        prediction: 'allowPrediction',
        'final-human-confirmation': 'finalHumanConfirmation',
        final_human_confirmation: 'finalHumanConfirmation',
        commit: 'commit',
        execute: 'execute',
        help: 'help',
        h: 'help',
    };

    const booleanOptions = new Set([
        'userAuthorizedMatchesSeedCommit',
        'allowMatchesWriteNextPhase',
        'allowDbWriteNow',
        'allowRawMatchDataWrite',
        'allowTraining',
        'allowPrediction',
        'finalHumanConfirmation',
        'commit',
        'execute',
        'help',
    ]);

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

        if (booleanOptions.has(optionKey)) {
            options[optionKey] = normalizeBooleanFlag(value, true);
            continue;
        }

        options[optionKey] = typeof value === 'boolean' ? String(value) : value;
    }

    return options;
}

function normalizeAuthorizationInput(input = {}) {
    return {
        source: typeof input.source === 'string' ? input.source.trim().toLowerCase() : '',
        scope: typeof input.scope === 'string' ? input.scope.trim() : '',
        leagueId: normalizeOptionalText(input.leagueId),
        season: typeof input.season === 'string' ? input.season.trim() : null,
        date: typeof input.date === 'string' ? input.date.trim() : null,
        candidateCount: parseInteger(input.candidateCount, null),
        containsTargetMatchId: normalizeOptionalText(input.containsTargetMatchId),
        containsTargetLabel: normalizeOptionalText(input.containsTargetLabel),
        maxSeedRows: parseInteger(input.maxSeedRows, DEFAULT_MAX_SEED_ROWS),
        userAuthorizedMatchesSeedCommit: normalizeBooleanFlag(input.userAuthorizedMatchesSeedCommit, false),
        allowMatchesWriteNextPhase: normalizeBooleanFlag(input.allowMatchesWriteNextPhase, false),
        allowDbWriteNow: normalizeBooleanFlag(input.allowDbWriteNow, false),
        allowRawMatchDataWrite: normalizeBooleanFlag(input.allowRawMatchDataWrite, false),
        allowTraining: normalizeBooleanFlag(input.allowTraining, false),
        allowPrediction: normalizeBooleanFlag(input.allowPrediction, false),
        finalHumanConfirmation: normalizeBooleanFlag(input.finalHumanConfirmation, false),
        commit: normalizeBooleanFlag(input.commit, false),
        execute: normalizeBooleanFlag(input.execute, false),
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

function validateRequiredFields(value, errors) {
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
    if (!value.containsTargetMatchId) {
        errors.push('missing contains-target-match-id');
    }
    if (!value.containsTargetLabel) {
        errors.push('missing contains-target-label');
    }
}

function validateLimits(value, errors) {
    if (!Number.isInteger(value.candidateCount) || value.candidateCount < 0) {
        errors.push('invalid candidate-count: provide a non-negative integer');
    }
    if (!Number.isInteger(value.maxSeedRows) || value.maxSeedRows < 1) {
        errors.push('invalid max-seed-rows: provide a positive integer');
    } else if (value.maxSeedRows > MAX_SEED_ROWS_LIMIT) {
        errors.push(`max-seed-rows > ${MAX_SEED_ROWS_LIMIT} is blocked in Phase 5.07L1`);
    }
    if (
        Number.isInteger(value.candidateCount) &&
        Number.isInteger(value.maxSeedRows) &&
        value.candidateCount > value.maxSeedRows
    ) {
        errors.push('candidate-count must be <= max-seed-rows');
    }
}

function validateAuthorizationFlags(value, errors) {
    if (value.userAuthorizedMatchesSeedCommit !== true) {
        errors.push('user-authorized-matches-seed-commit must be yes in Phase 5.07L1');
    }
    if (value.allowMatchesWriteNextPhase !== true) {
        errors.push('allow-matches-write-next-phase must be yes in Phase 5.07L1');
    }
    if (value.allowDbWriteNow === true) {
        errors.push('allow-db-write-now=yes is blocked in Phase 5.07L1');
    }
    if (value.allowRawMatchDataWrite === true) {
        errors.push('allow-raw-match-data-write=yes is blocked in Phase 5.07L1');
    }
    if (value.allowTraining === true) {
        errors.push('allow-training=yes is blocked in Phase 5.07L1');
    }
    if (value.allowPrediction === true) {
        errors.push('allow-prediction=yes is blocked in Phase 5.07L1');
    }
    if (value.finalHumanConfirmation !== true) {
        errors.push('final-human-confirmation must be yes in Phase 5.07L1');
    }
    if (value.commit === true) {
        errors.push(BLOCKED_COMMIT_MESSAGE);
    }
    if (value.execute === true) {
        errors.push('execute=yes is blocked in Phase 5.07L1');
    }
}

function validateAuthorizationInput(input = {}) {
    const value = normalizeAuthorizationInput(input);
    const errors = [];

    validateSourceScope(value, errors);
    validateRequiredFields(value, errors);
    validateLimits(value, errors);
    validateAuthorizationFlags(value, errors);

    return {
        ok: errors.length === 0,
        errors,
        value,
    };
}

function buildAffectedScope(value) {
    return {
        source: value.source,
        league_id: value.leagueId,
        season: value.season,
        date: value.date,
        max_rows: value.maxSeedRows,
    };
}

function buildPreCommitBaselineRequirements(value) {
    return [
        'main CI green',
        'clean worktree',
        'DB row counts baseline',
        'affected candidate set reloaded or explicitly supplied',
        'affected existing matches SELECT',
        `rows <= ${value.maxSeedRows}`,
        `source=${value.source}`,
        `league_id=${value.leagueId}`,
        `season=${value.season}`,
        `date=${value.date}`,
        'no raw_match_data write',
        'no feature/prediction write',
        'rollback plan acknowledged',
        'post-commit verification plan acknowledged',
    ];
}

function buildAuthorizationGates(value) {
    return [
        `user_authorized_matches_seed_commit=${value.userAuthorizedMatchesSeedCommit === true}`,
        `final_human_confirmation=${value.finalHumanConfirmation === true}`,
        `allow_db_write_now=${value.allowDbWriteNow === true}`,
        `allow_matches_write_next_phase=${value.allowMatchesWriteNextPhase === true}`,
        `allow_raw_match_data_write=${value.allowRawMatchDataWrite === true}`,
        `allow_training=${value.allowTraining === true}`,
        `allow_prediction=${value.allowPrediction === true}`,
        'commit_this_phase=false',
    ];
}

function buildBlockedActionsThisPhase() {
    return [
        'execute_db_write',
        'write_matches',
        'write_raw_match_data',
        'call_fixture_repository_persist',
        'run_titan_discovery',
        'run_discovery_service_discover',
        'harvest',
        'ingest',
        'training',
        'prediction',
    ];
}

function buildNextPhaseRequirements() {
    return [
        'regenerate exact candidate set or use captured candidate payload',
        'SELECT existing affected match rows',
        'show would_insert / would_update / would_skip',
        'require user final execution confirmation',
        'execute in transaction',
        'verify matches row delta / affected rows',
        'verify raw_match_data unchanged',
        'verify features/predictions unchanged',
    ];
}

function buildMatchesSeedCommitAuthorization(input = {}) {
    const validation = validateAuthorizationInput(input);
    if (!validation.ok) {
        const error = new Error(validation.errors[0]);
        error.validationErrors = validation.errors;
        throw error;
    }

    const value = validation.value;
    return {
        phase: PHASE,
        authorization_only: true,
        authorization_status: 'authorized_for_next_phase_only',
        source: value.source,
        scope: value.scope,
        league_id: value.leagueId,
        season: value.season,
        date: value.date,
        candidate_count: value.candidateCount,
        max_seed_rows: value.maxSeedRows,
        contains_target_match_id: value.containsTargetMatchId,
        contains_target_label: value.containsTargetLabel,
        user_authorized_matches_seed_commit: true,
        matches_seed_commit_authorization_recorded: true,
        matches_seed_commit_ready_for_next_phase: true,
        commit_allowed_this_phase: false,
        db_write_allowed_this_phase: false,
        matches_write_allowed_this_phase: false,
        matches_write_allowed_next_phase: true,
        raw_match_data_write_allowed: false,
        training_allowed: false,
        prediction_allowed: false,
        final_human_confirmation: true,
        affected_scope: buildAffectedScope(value),
        pre_commit_baseline_requirements: buildPreCommitBaselineRequirements(value),
        authorization_gates: buildAuthorizationGates(value),
        blocked_actions_this_phase: buildBlockedActionsThisPhase(),
        next_phase_requirements: buildNextPhaseRequirements(value),
        would_write_matches: false,
        would_write_raw_match_data: false,
        would_write_db: false,
        would_call_fixture_repository_persist: false,
        would_call_discovery_service_discover: false,
        would_run_titan_discovery: false,
        would_train: false,
        would_predict: false,
        commit_gate: 'blocked_this_phase',
        next_required_phase: NEXT_REQUIRED_PHASE,
    };
}

function buildErrorPayload(options, errors) {
    const value = normalizeAuthorizationInput(options);
    return {
        phase: PHASE,
        authorization_only: true,
        authorization_status: 'blocked',
        ok: false,
        errors: Array.isArray(errors) ? errors : [String(errors)],
        source: value.source || null,
        scope: value.scope || null,
        league_id: value.leagueId,
        season: value.season,
        date: value.date,
        candidate_count: value.candidateCount,
        max_seed_rows: value.maxSeedRows,
        contains_target_match_id: value.containsTargetMatchId,
        contains_target_label: value.containsTargetLabel,
        user_authorized_matches_seed_commit: value.userAuthorizedMatchesSeedCommit === true,
        matches_seed_commit_authorization_recorded: false,
        matches_seed_commit_ready_for_next_phase: false,
        commit_allowed_this_phase: false,
        db_write_allowed_this_phase: false,
        matches_write_allowed_this_phase: false,
        matches_write_allowed_next_phase: value.allowMatchesWriteNextPhase === true,
        raw_match_data_write_allowed: false,
        training_allowed: false,
        prediction_allowed: false,
        final_human_confirmation: value.finalHumanConfirmation === true,
        affected_scope: buildAffectedScope(value),
        pre_commit_baseline_requirements: buildPreCommitBaselineRequirements(value),
        authorization_gates: buildAuthorizationGates(value),
        blocked_actions_this_phase: buildBlockedActionsThisPhase(),
        next_phase_requirements: buildNextPhaseRequirements(value),
        would_write_matches: false,
        would_write_raw_match_data: false,
        would_write_db: false,
        would_call_fixture_repository_persist: false,
        would_call_discovery_service_discover: false,
        would_run_titan_discovery: false,
        would_train: false,
        would_predict: false,
        commit_gate: 'blocked_this_phase',
        next_required_phase: NEXT_REQUIRED_PHASE,
    };
}

function showHelp(io = {}) {
    const stdout = io.stdout || (text => process.stdout.write(text));
    stdout(
        [
            'Usage:',
            '  node scripts/ops/l1_matches_seed_commit_authorization.js --source=fotmob --scope=league_season_date --league-id=53 --season=2025/2026 --date=2026-05-10 --candidate-count=8 --contains-target-match-id=4830746 --contains-target-label="Angers vs Strasbourg" --max-seed-rows=10 --user-authorized-matches-seed-commit=yes --allow-matches-write-next-phase=yes --allow-db-write-now=no --allow-raw-match-data-write=no --allow-training=no --allow-prediction=no --final-human-confirmation=yes',
            '',
            'Phase 5.07L1: authorization-only, stdout-only, no DB writes, no matches/raw writes.',
        ].join('\n')
    );
}

async function runCli(argv = process.argv.slice(2), io = {}) {
    const stdout = io.stdout || (text => process.stdout.write(text));
    const stderr = io.stderr || (text => process.stderr.write(text));
    const options = parseArgs(argv);

    if (options.help) {
        showHelp({ stdout });
        return 0;
    }

    try {
        const payload = buildMatchesSeedCommitAuthorization(options);
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
    validateAuthorizationInput,
    buildAffectedScope,
    buildPreCommitBaselineRequirements,
    buildAuthorizationGates,
    buildBlockedActionsThisPhase,
    buildNextPhaseRequirements,
    buildMatchesSeedCommitAuthorization,
    runCli,
};
