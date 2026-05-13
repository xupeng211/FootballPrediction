#!/usr/bin/env node
/* eslint-disable complexity */
'use strict';

const PHASE = 'PHASE5_14L2_RAW_MATCH_DATA_INGEST_AUTHORIZATION';
const NEXT_REQUIRED_PHASE = 'Phase 5.15L2 raw_match_data ingest preflight';
const TARGET = Object.freeze({
    source: 'fotmob',
    route: 'html_hydration',
    matchId: '53_20252026_4830746',
    externalId: '4830746',
    homeTeam: 'Angers',
    awayTeam: 'Strasbourg',
    dataVersion: 'fotmob_html_hyd_v1',
});

function normalizeText(value) {
    return String(value || '').trim();
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
        return {
            value: arg.slice(arg.indexOf('=') + 1),
            consumedNext: false,
        };
    }

    const nextArg = argv[index + 1];
    if (typeof nextArg === 'string' && !nextArg.startsWith('--')) {
        return {
            value: nextArg,
            consumedNext: true,
        };
    }

    return {
        value: true,
        consumedNext: false,
    };
}

function parseArgs(argv = process.argv.slice(2)) {
    const options = {
        source: null,
        route: null,
        matchId: null,
        externalId: null,
        homeTeam: null,
        awayTeam: null,
        dataVersion: null,
        previewBodySha256: null,
        hydrationParseOk: null,
        looksLikeValidMatchDetail: null,
        userAuthorizedRawMatchDataIngest: null,
        allowRawMatchDataWriteNextPhase: null,
        allowDbWriteNow: null,
        allowRawMatchDataWriteNow: null,
        allowMatchesWrite: null,
        allowTraining: null,
        allowPrediction: null,
        finalHumanConfirmation: null,
        commit: false,
        execute: false,
        networkAuthorization: false,
        livePreviewAuthorization: false,
        help: false,
        unknown: [],
    };
    const keyMap = {
        source: 'source',
        route: 'route',
        'match-id': 'matchId',
        match_id: 'matchId',
        'external-id': 'externalId',
        external_id: 'externalId',
        'home-team': 'homeTeam',
        home_team: 'homeTeam',
        'away-team': 'awayTeam',
        away_team: 'awayTeam',
        'data-version': 'dataVersion',
        data_version: 'dataVersion',
        'preview-body-sha256': 'previewBodySha256',
        preview_body_sha256: 'previewBodySha256',
        'hydration-parse-ok': 'hydrationParseOk',
        hydration_parse_ok: 'hydrationParseOk',
        'looks-like-valid-match-detail': 'looksLikeValidMatchDetail',
        looks_like_valid_match_detail: 'looksLikeValidMatchDetail',
        'user-authorized-raw-match-data-ingest': 'userAuthorizedRawMatchDataIngest',
        user_authorized_raw_match_data_ingest: 'userAuthorizedRawMatchDataIngest',
        'allow-raw-match-data-write-next-phase': 'allowRawMatchDataWriteNextPhase',
        allow_raw_match_data_write_next_phase: 'allowRawMatchDataWriteNextPhase',
        'allow-db-write-now': 'allowDbWriteNow',
        allow_db_write_now: 'allowDbWriteNow',
        'allow-raw-match-data-write-now': 'allowRawMatchDataWriteNow',
        allow_raw_match_data_write_now: 'allowRawMatchDataWriteNow',
        'allow-matches-write': 'allowMatchesWrite',
        allow_matches_write: 'allowMatchesWrite',
        'allow-training': 'allowTraining',
        allow_training: 'allowTraining',
        'allow-prediction': 'allowPrediction',
        allow_prediction: 'allowPrediction',
        'final-human-confirmation': 'finalHumanConfirmation',
        final_human_confirmation: 'finalHumanConfirmation',
        commit: 'commit',
        execute: 'execute',
        'network-authorization': 'networkAuthorization',
        network_authorization: 'networkAuthorization',
        'live-preview-authorization': 'livePreviewAuthorization',
        live_preview_authorization: 'livePreviewAuthorization',
        help: 'help',
        h: 'help',
    };
    const booleanKeys = new Set([
        'hydrationParseOk',
        'looksLikeValidMatchDetail',
        'userAuthorizedRawMatchDataIngest',
        'allowRawMatchDataWriteNextPhase',
        'allowDbWriteNow',
        'allowRawMatchDataWriteNow',
        'allowMatchesWrite',
        'allowTraining',
        'allowPrediction',
        'finalHumanConfirmation',
        'commit',
        'execute',
        'networkAuthorization',
        'livePreviewAuthorization',
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

        if (booleanKeys.has(optionKey)) {
            options[optionKey] = normalizeBooleanFlag(value, true);
            continue;
        }

        options[optionKey] = typeof value === 'boolean' ? String(value) : value;
    }

    return options;
}

function includesText(value, expected) {
    return normalizeText(value).toLowerCase().includes(normalizeText(expected).toLowerCase());
}

function pushRequiredTrueError(errors, value, flagName) {
    if (value === true) {
        return;
    }
    if (value === false) {
        errors.push(`${flagName}=yes is required in Phase 5.14L2`);
        return;
    }
    errors.push(`missing ${flagName}=yes`);
}

function pushRequiredFalseError(errors, value, flagName) {
    if (value === false) {
        return;
    }
    if (value === true) {
        errors.push(`${flagName}=yes is blocked in Phase 5.14L2`);
        return;
    }
    errors.push(`missing ${flagName}=no`);
}

function normalizeAuthorizationInput(input = {}) {
    return {
        source: normalizeText(input.source).toLowerCase(),
        route: normalizeText(input.route).toLowerCase(),
        matchId: normalizeText(input.matchId),
        externalId: normalizeText(input.externalId),
        homeTeam: normalizeText(input.homeTeam),
        awayTeam: normalizeText(input.awayTeam),
        dataVersion: normalizeText(input.dataVersion).toLowerCase(),
        previewBodySha256: normalizeText(input.previewBodySha256).toLowerCase(),
        hydrationParseOk: normalizeBooleanFlag(input.hydrationParseOk, undefined),
        looksLikeValidMatchDetail: normalizeBooleanFlag(input.looksLikeValidMatchDetail, undefined),
        userAuthorizedRawMatchDataIngest: normalizeBooleanFlag(input.userAuthorizedRawMatchDataIngest, undefined),
        allowRawMatchDataWriteNextPhase: normalizeBooleanFlag(input.allowRawMatchDataWriteNextPhase, undefined),
        allowDbWriteNow: normalizeBooleanFlag(input.allowDbWriteNow, undefined),
        allowRawMatchDataWriteNow: normalizeBooleanFlag(input.allowRawMatchDataWriteNow, undefined),
        allowMatchesWrite: normalizeBooleanFlag(input.allowMatchesWrite, undefined),
        allowTraining: normalizeBooleanFlag(input.allowTraining, undefined),
        allowPrediction: normalizeBooleanFlag(input.allowPrediction, undefined),
        finalHumanConfirmation: normalizeBooleanFlag(input.finalHumanConfirmation, undefined),
        commit: normalizeBooleanFlag(input.commit, false),
        execute: normalizeBooleanFlag(input.execute, false),
        networkAuthorization: normalizeBooleanFlag(input.networkAuthorization, false),
        livePreviewAuthorization: normalizeBooleanFlag(input.livePreviewAuthorization, false),
        unknown: Array.isArray(input.unknown) ? input.unknown : [],
    };
}

function validateAuthorizationInput(input = {}) {
    const value = normalizeAuthorizationInput(input);
    const errors = [];

    if (value.unknown.length > 0) {
        errors.push(`unknown arguments: ${value.unknown.join(', ')}`);
    }
    if (!value.source) {
        errors.push('missing source: provide --source=fotmob');
    } else if (value.source !== TARGET.source) {
        errors.push('unsupported source: only fotmob is allowed');
    }
    if (!value.route) {
        errors.push('missing route: provide --route=html_hydration');
    } else if (value.route !== TARGET.route) {
        errors.push('unsupported route: Phase 5.14L2 only authorizes html_hydration raw_data ingest');
    }
    if (!value.matchId) {
        errors.push('missing match-id');
    } else if (value.matchId !== TARGET.matchId) {
        errors.push(`match-id must be ${TARGET.matchId} in Phase 5.14L2`);
    }
    if (!value.externalId) {
        errors.push('missing external-id');
    } else if (value.externalId !== TARGET.externalId) {
        errors.push(`external-id must be ${TARGET.externalId} in Phase 5.14L2`);
    }
    if (!value.homeTeam) {
        errors.push('missing home-team');
    } else if (!includesText(value.homeTeam, TARGET.homeTeam)) {
        errors.push(`home-team must contain ${TARGET.homeTeam}`);
    }
    if (!value.awayTeam) {
        errors.push('missing away-team');
    } else if (!includesText(value.awayTeam, TARGET.awayTeam)) {
        errors.push(`away-team must contain ${TARGET.awayTeam}`);
    }
    if (!value.dataVersion) {
        errors.push('missing data-version');
    } else if (value.dataVersion !== TARGET.dataVersion) {
        errors.push(`data-version must be ${TARGET.dataVersion} in Phase 5.14L2`);
    }
    if (!value.previewBodySha256) {
        errors.push('missing preview-body-sha256');
    } else if (!/^[a-f0-9]{64}$/.test(value.previewBodySha256)) {
        errors.push('preview-body-sha256 must be a 64-character SHA-256 hex digest');
    }
    if (value.hydrationParseOk !== true) {
        errors.push('hydration-parse-ok=yes is required');
    }
    if (value.looksLikeValidMatchDetail !== true) {
        errors.push('looks-like-valid-match-detail=yes is required');
    }

    pushRequiredTrueError(errors, value.userAuthorizedRawMatchDataIngest, 'user-authorized-raw-match-data-ingest');
    pushRequiredTrueError(errors, value.allowRawMatchDataWriteNextPhase, 'allow-raw-match-data-write-next-phase');
    pushRequiredTrueError(errors, value.finalHumanConfirmation, 'final-human-confirmation');
    pushRequiredFalseError(errors, value.allowDbWriteNow, 'allow-db-write-now');
    pushRequiredFalseError(errors, value.allowRawMatchDataWriteNow, 'allow-raw-match-data-write-now');
    pushRequiredFalseError(errors, value.allowMatchesWrite, 'allow-matches-write');
    pushRequiredFalseError(errors, value.allowTraining, 'allow-training');
    pushRequiredFalseError(errors, value.allowPrediction, 'allow-prediction');

    if (value.commit === true) {
        errors.push('commit=yes is blocked in Phase 5.14L2');
    }
    if (value.execute === true) {
        errors.push('execute=yes is blocked in Phase 5.14L2');
    }
    if (value.networkAuthorization === true) {
        errors.push('network-authorization=yes is blocked: authorization phase is no-network');
    }
    if (value.livePreviewAuthorization === true) {
        errors.push('live-preview-authorization=yes is blocked: authorization phase is not live preview');
    }

    return {
        ok: errors.length === 0,
        errors,
        value,
    };
}

function buildAuthorizedScope() {
    return {
        source: TARGET.source,
        route: TARGET.route,
        match_id: TARGET.matchId,
        external_id: TARGET.externalId,
        home_team: TARGET.homeTeam,
        away_team: TARGET.awayTeam,
        target_table: 'raw_match_data',
        rows_limit: 1,
        data_version: TARGET.dataVersion,
        raw_data_policy: 'canonical transformed detail payload',
        data_hash_policy: 'SHA-256(canonical_json(raw_data))',
        protected_tables: [
            'matches',
            'bookmaker_odds_history',
            'l3_features',
            'match_features_training',
            'predictions',
        ],
    };
}

function buildAuthorizationGates() {
    return [
        'user_authorized_raw_match_data_ingest=true',
        'final_human_confirmation=true',
        'allow_raw_match_data_write_next_phase=true',
        'allow_raw_match_data_write_now=false',
        'allow_db_write_now=false',
        'allow_matches_write=false',
        'allow_training=false',
        'allow_prediction=false',
        'network_authorization_this_phase=false',
    ];
}

function buildBlockedActionsThisPhase() {
    return [
        'write_raw_match_data',
        'write_db',
        'write_matches',
        'run_live_preview',
        'run_harvest',
        'run_backfill',
        'run_training',
        'run_prediction',
        'save_full_body',
        'print_full_body',
    ];
}

function buildNextPhaseRequirements() {
    return [
        'reload or recapture exact raw payload under explicit preview/write flow',
        'compute canonical raw_data',
        'compute data_hash',
        'SELECT existing raw_match_data row',
        'output would_insert / would_update / would_skip',
        'show protected table baselines',
        'require final DB-write confirmation before execution',
        'transaction required for future write',
    ];
}

function buildRawMatchDataIngestAuthorization(input = {}) {
    const validation = validateAuthorizationInput(input);
    const normalized = validation.value;
    const base = {
        phase: PHASE,
        authorization_only: true,
        ok: validation.ok,
        source: TARGET.source,
        route: TARGET.route,
        match_id: TARGET.matchId,
        external_id: TARGET.externalId,
        home_team: TARGET.homeTeam,
        away_team: TARGET.awayTeam,
        data_version: TARGET.dataVersion,
        user_authorized_raw_match_data_ingest: normalized.userAuthorizedRawMatchDataIngest === true,
        raw_match_data_ingest_authorization_recorded: validation.ok,
        raw_match_data_write_allowed_next_phase: validation.ok,
        raw_match_data_write_allowed_this_phase: false,
        db_write_allowed_this_phase: false,
        matches_write_allowed: false,
        training_allowed: false,
        prediction_allowed: false,
        final_human_confirmation: normalized.finalHumanConfirmation === true,
        authorized_scope: buildAuthorizedScope(),
        authorization_gates: buildAuthorizationGates(),
        blocked_actions_this_phase: buildBlockedActionsThisPhase(),
        next_phase_requirements: buildNextPhaseRequirements(),
        would_write_raw_match_data: false,
        would_write_db: false,
        would_write_matches: false,
        would_train: false,
        would_predict: false,
        next_required_phase: NEXT_REQUIRED_PHASE,
    };

    if (!validation.ok) {
        return {
            ...base,
            raw_match_data_write_allowed_next_phase: false,
            controlled_error: `INVALID_INGEST_AUTHORIZATION_INPUT:${validation.errors.join('; ')}`,
            errors: validation.errors,
        };
    }

    return {
        ...base,
        controlled_error: null,
        errors: [],
    };
}

function usage() {
    return [
        'Usage:',
        '  node scripts/ops/l2_raw_match_data_ingest_authorization.js --source=fotmob --route=html_hydration --match-id=53_20252026_4830746 --external-id=4830746 --home-team=Angers --away-team=Strasbourg --data-version=fotmob_html_hyd_v1 --preview-body-sha256=<sha256> --hydration-parse-ok=yes --looks-like-valid-match-detail=yes --user-authorized-raw-match-data-ingest=yes --allow-raw-match-data-write-next-phase=yes --allow-db-write-now=no --allow-raw-match-data-write-now=no --allow-matches-write=no --allow-training=no --allow-prediction=no --final-human-confirmation=yes',
        '',
        'Safety:',
        '  Phase 5.14L2 is authorization-only: no network, no DB write, no raw_match_data write.',
    ].join('\n');
}

async function runCli(argv = process.argv.slice(2), io = {}) {
    const stdout = io.stdout || process.stdout.write.bind(process.stdout);
    const args = parseArgs(argv);
    if (args.help) {
        stdout(`${usage()}\n`);
        return 0;
    }

    const authorization = buildRawMatchDataIngestAuthorization(args);
    stdout(`${JSON.stringify(authorization, null, 2)}\n`);
    return authorization.ok ? 0 : 1;
}

if (require.main === module) {
    runCli()
        .then(status => {
            process.exitCode = status;
        })
        .catch(error => {
            process.stdout.write(
                `${JSON.stringify(
                    {
                        phase: PHASE,
                        authorization_only: true,
                        ok: false,
                        controlled_error: String(error.message || error),
                        raw_match_data_write_allowed_next_phase: false,
                        raw_match_data_write_allowed_this_phase: false,
                        db_write_allowed_this_phase: false,
                        would_write_raw_match_data: false,
                        would_write_db: false,
                    },
                    null,
                    2
                )}\n`
            );
            process.exitCode = 1;
        });
}

module.exports = {
    parseArgs,
    normalizeBooleanFlag,
    validateAuthorizationInput,
    buildAuthorizedScope,
    buildAuthorizationGates,
    buildBlockedActionsThisPhase,
    buildNextPhaseRequirements,
    buildRawMatchDataIngestAuthorization,
    runCli,
};
