#!/usr/bin/env node
/* eslint-disable complexity */
'use strict';

const PHASE = 'PHASE5_18L2_REMAINING_RAW_MATCH_DATA_ACQUISITION_AUTHORIZATION';
const NEXT_REQUIRED_PHASE = 'Phase 5.19L2 remaining raw_match_data acquisition preflight';
const EXPECTED_SCOPE = Object.freeze({
    source: 'fotmob',
    leagueId: '53',
    season: '2025/2026',
    date: '2026-05-10',
    route: 'html_hydration',
    expectedSeededCount: 8,
    expectedExistingRawCount: 1,
    expectedMissingRawCount: 7,
});
const EXPECTED_INGESTED_MATCH_ID = '53_20252026_4830746';
const EXPECTED_REMAINING_EXTERNAL_IDS = Object.freeze([
    '4830747',
    '4830748',
    '4830750',
    '4830751',
    '4830752',
    '4830753',
    '4830754',
]);
const AUTHORIZED_REMAINING_TARGETS = Object.freeze([
    Object.freeze({
        match_id: '53_20252026_4830747',
        external_id: '4830747',
        home_team: 'Auxerre',
        away_team: 'Nice',
    }),
    Object.freeze({
        match_id: '53_20252026_4830748',
        external_id: '4830748',
        home_team: 'Le Havre',
        away_team: 'Marseille',
    }),
    Object.freeze({
        match_id: '53_20252026_4830750',
        external_id: '4830750',
        home_team: 'Metz',
        away_team: 'Lorient',
    }),
    Object.freeze({
        match_id: '53_20252026_4830751',
        external_id: '4830751',
        home_team: 'Monaco',
        away_team: 'Lille',
    }),
    Object.freeze({
        match_id: '53_20252026_4830752',
        external_id: '4830752',
        home_team: 'Paris Saint-Germain',
        away_team: 'Brest',
    }),
    Object.freeze({
        match_id: '53_20252026_4830753',
        external_id: '4830753',
        home_team: 'Rennes',
        away_team: 'Paris FC',
    }),
    Object.freeze({
        match_id: '53_20252026_4830754',
        external_id: '4830754',
        home_team: 'Toulouse',
        away_team: 'Lyon',
    }),
]);

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
    const trimmed = String(value).trim().toLowerCase();
    if (['1', 'true', 'yes', 'y', 'on'].includes(trimmed)) {
        return true;
    }
    if (['0', 'false', 'no', 'n', 'off'].includes(trimmed)) {
        return false;
    }
    return fallback;
}

function parseInteger(value, fallback = null) {
    if (value === null || value === undefined || value === '') {
        return fallback;
    }
    const clean = String(value).trim();
    if (!/^\d+$/.test(clean)) {
        return Number.NaN;
    }
    return Number.parseInt(clean, 10);
}

function parseRemainingExternalIds(value) {
    if (Array.isArray(value)) {
        return value.map(id => normalizeText(id)).filter(Boolean);
    }
    if (value === null || value === undefined || value === '') {
        return [];
    }
    return String(value)
        .split(',')
        .map(id => normalizeText(id))
        .filter(Boolean);
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
        leagueId: null,
        season: null,
        date: null,
        route: null,
        expectedSeededCount: null,
        expectedExistingRawCount: null,
        expectedMissingRawCount: null,
        remainingExternalIds: null,
        userAuthorizedRemainingRawAcquisition: null,
        allowNetworkNextPhase: null,
        allowRawMatchDataWriteFuturePhase: null,
        allowNetworkThisPhase: null,
        allowDbWriteThisPhase: null,
        allowRawMatchDataWriteThisPhase: null,
        allowMatchesWrite: null,
        allowParserFeatures: null,
        allowTraining: null,
        allowPrediction: null,
        finalHumanConfirmation: null,
        networkAuthorization: false,
        livePreviewAuthorization: false,
        commit: false,
        execute: false,
        help: false,
        unknown: [],
    };
    const keyMap = {
        source: 'source',
        'league-id': 'leagueId',
        league_id: 'leagueId',
        season: 'season',
        date: 'date',
        route: 'route',
        'expected-seeded-count': 'expectedSeededCount',
        expected_seeded_count: 'expectedSeededCount',
        'expected-existing-raw-count': 'expectedExistingRawCount',
        expected_existing_raw_count: 'expectedExistingRawCount',
        'expected-missing-raw-count': 'expectedMissingRawCount',
        expected_missing_raw_count: 'expectedMissingRawCount',
        'remaining-external-ids': 'remainingExternalIds',
        remaining_external_ids: 'remainingExternalIds',
        'user-authorized-remaining-raw-acquisition': 'userAuthorizedRemainingRawAcquisition',
        user_authorized_remaining_raw_acquisition: 'userAuthorizedRemainingRawAcquisition',
        'allow-network-next-phase': 'allowNetworkNextPhase',
        allow_network_next_phase: 'allowNetworkNextPhase',
        'allow-raw-match-data-write-future-phase': 'allowRawMatchDataWriteFuturePhase',
        allow_raw_match_data_write_future_phase: 'allowRawMatchDataWriteFuturePhase',
        'allow-network-this-phase': 'allowNetworkThisPhase',
        allow_network_this_phase: 'allowNetworkThisPhase',
        'allow-db-write-this-phase': 'allowDbWriteThisPhase',
        allow_db_write_this_phase: 'allowDbWriteThisPhase',
        'allow-raw-match-data-write-this-phase': 'allowRawMatchDataWriteThisPhase',
        allow_raw_match_data_write_this_phase: 'allowRawMatchDataWriteThisPhase',
        'allow-matches-write': 'allowMatchesWrite',
        allow_matches_write: 'allowMatchesWrite',
        'allow-parser-features': 'allowParserFeatures',
        allow_parser_features: 'allowParserFeatures',
        'allow-training': 'allowTraining',
        allow_training: 'allowTraining',
        'allow-prediction': 'allowPrediction',
        allow_prediction: 'allowPrediction',
        'final-human-confirmation': 'finalHumanConfirmation',
        final_human_confirmation: 'finalHumanConfirmation',
        'network-authorization': 'networkAuthorization',
        network_authorization: 'networkAuthorization',
        'live-preview-authorization': 'livePreviewAuthorization',
        live_preview_authorization: 'livePreviewAuthorization',
        commit: 'commit',
        execute: 'execute',
        help: 'help',
        h: 'help',
    };
    const booleanKeys = new Set([
        'allowNetworkThisPhase',
        'allowDbWriteThisPhase',
        'allowRawMatchDataWriteThisPhase',
        'allowMatchesWrite',
        'allowParserFeatures',
        'allowTraining',
        'allowPrediction',
        'networkAuthorization',
        'livePreviewAuthorization',
        'commit',
        'execute',
        'help',
    ]);

    for (let i = 0; i < argv.length; i += 1) {
        const arg = String(argv[i]);
        if (!arg.startsWith('--')) {
            options.unknown.push(arg);
            continue;
        }
        const rawKey = arg.replace(/^--/, '').split('=')[0];
        const optionKey = keyMap[rawKey];
        const { value, consumedNext } = parseOptionValue(arg, argv, i);
        if (consumedNext) {
            i += 1;
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

function pushRequiredYesError(errors, value, flagName, phase) {
    if (value === true) {
        return;
    }
    errors.push(`${flagName}=yes is required for ${phase}`);
}

function pushRequiredNoError(errors, value, flagName, phase) {
    if (value === false) {
        return;
    }
    if (value === true) {
        errors.push(`${flagName}=yes is blocked in ${phase}`);
        return;
    }
    errors.push(`missing ${flagName}=no`);
}

function pushBlockedError(errors, value, flagName, phase) {
    if (value === true) {
        errors.push(`${flagName}=yes is blocked in ${phase}`);
    }
}

function normalizeAuthorizationInput(input = {}) {
    return {
        source: normalizeText(input.source).toLowerCase(),
        leagueId: normalizeText(input.leagueId),
        season: normalizeText(input.season),
        date: normalizeText(input.date),
        route: normalizeText(input.route).toLowerCase(),
        expectedSeededCount: parseInteger(input.expectedSeededCount, null),
        expectedExistingRawCount: parseInteger(input.expectedExistingRawCount, null),
        expectedMissingRawCount: parseInteger(input.expectedMissingRawCount, null),
        remainingExternalIds: parseRemainingExternalIds(input.remainingExternalIds),
        userAuthorizedRemainingRawAcquisition: normalizeBooleanFlag(
            input.userAuthorizedRemainingRawAcquisition,
            undefined
        ),
        allowNetworkNextPhase: normalizeBooleanFlag(input.allowNetworkNextPhase, undefined),
        allowRawMatchDataWriteFuturePhase: normalizeBooleanFlag(input.allowRawMatchDataWriteFuturePhase, undefined),
        allowNetworkThisPhase: normalizeBooleanFlag(input.allowNetworkThisPhase, undefined),
        allowDbWriteThisPhase: normalizeBooleanFlag(input.allowDbWriteThisPhase, undefined),
        allowRawMatchDataWriteThisPhase: normalizeBooleanFlag(input.allowRawMatchDataWriteThisPhase, undefined),
        allowMatchesWrite: normalizeBooleanFlag(input.allowMatchesWrite, undefined),
        allowParserFeatures: normalizeBooleanFlag(input.allowParserFeatures, undefined),
        allowTraining: normalizeBooleanFlag(input.allowTraining, undefined),
        allowPrediction: normalizeBooleanFlag(input.allowPrediction, undefined),
        finalHumanConfirmation: normalizeBooleanFlag(input.finalHumanConfirmation, undefined),
        networkAuthorization: normalizeBooleanFlag(input.networkAuthorization, false),
        livePreviewAuthorization: normalizeBooleanFlag(input.livePreviewAuthorization, false),
        commit: normalizeBooleanFlag(input.commit, false),
        execute: normalizeBooleanFlag(input.execute, false),
        unknown: Array.isArray(input.unknown) ? input.unknown : [],
    };
}

function validateAuthorizationInput(input = {}) {
    const value = normalizeAuthorizationInput(input);
    const errors = [];

    if (value.unknown.length > 0) {
        errors.push(`unknown arguments: ${value.unknown.join(', ')}`);
    }
    if (!value.source || value.source !== EXPECTED_SCOPE.source) {
        errors.push('source must be fotmob');
    }
    if (!value.leagueId || value.leagueId !== EXPECTED_SCOPE.leagueId) {
        errors.push('league-id must be 53');
    }
    if (!value.season || value.season !== EXPECTED_SCOPE.season) {
        errors.push('season must be 2025/2026');
    }
    if (!value.date || value.date !== EXPECTED_SCOPE.date) {
        errors.push('date must be 2026-05-10');
    }
    if (!value.route || value.route !== EXPECTED_SCOPE.route) {
        errors.push('route must be html_hydration');
    }
    if (value.expectedSeededCount !== EXPECTED_SCOPE.expectedSeededCount) {
        errors.push('expected-seeded-count must be 8');
    }
    if (value.expectedExistingRawCount !== EXPECTED_SCOPE.expectedExistingRawCount) {
        errors.push('expected-existing-raw-count must be 1');
    }
    if (value.expectedMissingRawCount !== EXPECTED_SCOPE.expectedMissingRawCount) {
        errors.push('expected-missing-raw-count must be 7');
    }

    const remainingIds = value.remainingExternalIds;
    if (remainingIds.length === 0) {
        errors.push('remaining-external-ids is required');
    } else if (remainingIds.length !== EXPECTED_REMAINING_EXTERNAL_IDS.length) {
        errors.push(
            `remaining-external-ids must have exactly ${EXPECTED_REMAINING_EXTERNAL_IDS.length} ids, got ${remainingIds.length}`
        );
    } else {
        const expectedSet = new Set(EXPECTED_REMAINING_EXTERNAL_IDS);
        for (const id of remainingIds) {
            if (!expectedSet.has(id)) {
                errors.push(`unexpected remaining external_id: ${id}`);
            }
            if (id === '4830746') {
                errors.push('4830746 is already ingested, must not be in remaining-external-ids');
            }
        }
        for (const id of EXPECTED_REMAINING_EXTERNAL_IDS) {
            if (!remainingIds.includes(id)) {
                errors.push(`missing expected remaining external_id: ${id}`);
            }
        }
    }

    pushRequiredYesError(
        errors,
        value.userAuthorizedRemainingRawAcquisition,
        'user-authorized-remaining-raw-acquisition',
        'Phase 5.18L2'
    );
    pushRequiredYesError(errors, value.allowNetworkNextPhase, 'allow-network-next-phase', 'Phase 5.18L2');
    pushRequiredYesError(
        errors,
        value.allowRawMatchDataWriteFuturePhase,
        'allow-raw-match-data-write-future-phase',
        'Phase 5.18L2'
    );
    pushRequiredYesError(errors, value.finalHumanConfirmation, 'final-human-confirmation', 'Phase 5.18L2');

    pushRequiredNoError(errors, value.allowNetworkThisPhase, 'allow-network-this-phase', 'Phase 5.18L2');
    pushRequiredNoError(errors, value.allowDbWriteThisPhase, 'allow-db-write-this-phase', 'Phase 5.18L2');
    pushRequiredNoError(
        errors,
        value.allowRawMatchDataWriteThisPhase,
        'allow-raw-match-data-write-this-phase',
        'Phase 5.18L2'
    );
    pushRequiredNoError(errors, value.allowMatchesWrite, 'allow-matches-write', 'Phase 5.18L2');
    pushRequiredNoError(errors, value.allowParserFeatures, 'allow-parser-features', 'Phase 5.18L2');
    pushRequiredNoError(errors, value.allowTraining, 'allow-training', 'Phase 5.18L2');
    pushRequiredNoError(errors, value.allowPrediction, 'allow-prediction', 'Phase 5.18L2');

    pushBlockedError(errors, value.networkAuthorization, 'network-authorization', 'Phase 5.18L2');
    pushBlockedError(errors, value.livePreviewAuthorization, 'live-preview-authorization', 'Phase 5.18L2');
    pushBlockedError(errors, value.commit, 'commit', 'Phase 5.18L2');
    pushBlockedError(errors, value.execute, 'execute', 'Phase 5.18L2');

    return { ok: errors.length === 0, errors, value };
}

function buildAlreadyIngestedTargets() {
    return [
        {
            match_id: EXPECTED_INGESTED_MATCH_ID,
            external_id: '4830746',
            home_team: 'Angers',
            away_team: 'Strasbourg',
            raw_status: 'has_raw',
        },
    ];
}

function buildAuthorizedRemainingTargets() {
    return AUTHORIZED_REMAINING_TARGETS.map(target => ({
        match_id: target.match_id,
        external_id: target.external_id,
        home_team: target.home_team,
        away_team: target.away_team,
        route: EXPECTED_SCOPE.route,
        status: 'authorized_for_future_preflight',
    }));
}

function buildAuthorizedScope() {
    return {
        target_table: 'raw_match_data',
        rows_limit: EXPECTED_REMAINING_EXTERNAL_IDS.length,
        route: EXPECTED_SCOPE.route,
        concurrency: 1,
        retry: 0,
        browser: false,
        proxy: false,
        full_body_save: false,
        full_body_print: false,
        raw_first_parse_later: true,
        parser_deferred_until_training_design: true,
    };
}

function buildBlockedActionsThisPhase() {
    return [
        'live_preview',
        'network_request',
        'write_db',
        'write_raw_match_data',
        'write_matches',
        'parser_features',
        'training',
        'prediction',
        'legacy_harvest',
        'legacy_backfill',
    ];
}

function buildNextPhaseRequirements() {
    return [
        'Phase 5.19L2 remaining raw_match_data acquisition preflight',
        'recapture each authorized target under safe html_hydration route',
        'compute canonical raw_data per target',
        'compute data_hash per target',
        'SELECT existing raw_match_data rows',
        'output would_insert/would_update/would_skip',
        'verify protected table baselines',
        'no DB write in preflight',
    ];
}

function buildInvalidAuthorization(input = {}, errors = [], controlledError = null) {
    const value = normalizeAuthorizationInput(input);
    return {
        phase: PHASE,
        authorization_only: true,
        ok: false,
        source: value.source || null,
        league_id: value.leagueId || null,
        season: value.season || null,
        date: value.date || null,
        route: value.route || null,
        seeded_match_count: null,
        existing_raw_match_data_count: null,
        missing_raw_match_data_count: null,
        user_authorized_remaining_raw_acquisition: value.userAuthorizedRemainingRawAcquisition || false,
        remaining_raw_acquisition_authorization_recorded: false,
        network_allowed_next_phase: value.allowNetworkNextPhase || false,
        raw_match_data_write_allowed_future_phase: value.allowRawMatchDataWriteFuturePhase || false,
        network_allowed_this_phase: false,
        db_write_allowed_this_phase: false,
        raw_match_data_write_allowed_this_phase: false,
        matches_write_allowed: false,
        parser_features_allowed: false,
        training_allowed: false,
        prediction_allowed: false,
        final_human_confirmation: value.finalHumanConfirmation || false,
        already_ingested_targets: [],
        authorized_remaining_targets: [],
        authorized_scope: buildAuthorizedScope(),
        blocked_actions_this_phase: buildBlockedActionsThisPhase(),
        next_phase_requirements: buildNextPhaseRequirements(),
        would_write_db: false,
        would_write_raw_match_data: false,
        would_parse_features: false,
        would_train: false,
        would_predict: false,
        errors,
        controlled_error:
            controlledError || `INVALID_REMAINING_RAW_MATCH_DATA_ACQUISITION_AUTHORIZATION:${errors.join('; ')}`,
        next_required_phase: NEXT_REQUIRED_PHASE,
    };
}

function buildRemainingRawMatchDataAcquisitionAuthorization(input = {}) {
    const validation = validateAuthorizationInput(input);
    if (!validation.ok) {
        return buildInvalidAuthorization(input, validation.errors);
    }

    const alreadyIngested = buildAlreadyIngestedTargets();
    const authorizedRemaining = buildAuthorizedRemainingTargets();
    const value = validation.value;

    return {
        phase: PHASE,
        authorization_only: true,
        ok: true,
        source: EXPECTED_SCOPE.source,
        league_id: EXPECTED_SCOPE.leagueId,
        season: EXPECTED_SCOPE.season,
        date: EXPECTED_SCOPE.date,
        route: EXPECTED_SCOPE.route,
        seeded_match_count: EXPECTED_SCOPE.expectedSeededCount,
        existing_raw_match_data_count: EXPECTED_SCOPE.expectedExistingRawCount,
        missing_raw_match_data_count: EXPECTED_SCOPE.expectedMissingRawCount,
        user_authorized_remaining_raw_acquisition: true,
        remaining_raw_acquisition_authorization_recorded: true,
        network_allowed_next_phase: true,
        raw_match_data_write_allowed_future_phase: true,
        network_allowed_this_phase: false,
        db_write_allowed_this_phase: false,
        raw_match_data_write_allowed_this_phase: false,
        matches_write_allowed: false,
        parser_features_allowed: false,
        training_allowed: false,
        prediction_allowed: false,
        final_human_confirmation: true,
        already_ingested_targets: alreadyIngested,
        authorized_remaining_targets: authorizedRemaining,
        authorized_scope: buildAuthorizedScope(),
        blocked_actions_this_phase: buildBlockedActionsThisPhase(),
        next_phase_requirements: buildNextPhaseRequirements(),
        would_write_db: false,
        would_write_raw_match_data: false,
        would_parse_features: false,
        would_train: false,
        would_predict: false,
        next_required_phase: NEXT_REQUIRED_PHASE,
    };
}

function usage() {
    return [
        'Usage:',
        '  node scripts/ops/l2_remaining_raw_match_data_acquisition_authorization.js \\',
        '    --source=fotmob --league-id=53 --season=2025/2026 --date=2026-05-10 \\',
        '    --route=html_hydration --expected-seeded-count=8 --expected-existing-raw-count=1 \\',
        '    --expected-missing-raw-count=7 \\',
        '    --remaining-external-ids=4830747,4830748,4830750,4830751,4830752,4830753,4830754 \\',
        '    --user-authorized-remaining-raw-acquisition=yes \\',
        '    --allow-network-next-phase=yes --allow-raw-match-data-write-future-phase=yes \\',
        '    --allow-network-this-phase=no --allow-db-write-this-phase=no \\',
        '    --allow-raw-match-data-write-this-phase=no --allow-matches-write=no \\',
        '    --allow-parser-features=no --allow-training=no --allow-prediction=no \\',
        '    --final-human-confirmation=yes',
        '',
        'Safety:',
        '  Phase 5.18L2 is authorization-only: no network, no DB write, no raw_match_data write,',
        '  no parser/features, no training/prediction.',
    ].join('\n');
}

async function runCli(argv = process.argv.slice(2), streams = {}) {
    const stdout = streams.stdout || (text => process.stdout.write(text));
    const args = parseArgs(argv);

    if (args.help) {
        stdout(`${usage()}\n`);
        return 0;
    }

    const plan = buildRemainingRawMatchDataAcquisitionAuthorization(args);
    stdout(`${JSON.stringify(plan, null, 2)}\n`);
    return plan.ok ? 0 : 1;
}

if (require.main === module) {
    runCli()
        .then(status => {
            process.exitCode = status;
        })
        .catch(error => {
            console.error(
                JSON.stringify(
                    buildInvalidAuthorization(
                        {},
                        [String(error.message || error)],
                        `UNHANDLED_PHASE5_18L2_ERROR:${error.message}`
                    ),
                    null,
                    2
                )
            );
            process.exitCode = 1;
        });
}

module.exports = {
    parseArgs,
    normalizeBooleanFlag,
    parseRemainingExternalIds,
    validateAuthorizationInput,
    buildAlreadyIngestedTargets,
    buildAuthorizedRemainingTargets,
    buildAuthorizedScope,
    buildBlockedActionsThisPhase,
    buildNextPhaseRequirements,
    buildRemainingRawMatchDataAcquisitionAuthorization,
    runCli,
};
