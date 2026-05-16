#!/usr/bin/env node
/* eslint-disable complexity, max-lines */
'use strict';

const { extractFromHtml, transformToApiFormat } = require('../../src/parsers/fotmob/NextDataParser');
const {
    fetchFotMobRawDetail,
    HASH_STRATEGY_STABLE_RAW_PAYLOAD_V1,
    validateCanonicalRawDataShape,
} = require('../../src/infrastructure/services/FotMobRawDetailFetcher');

const PHASE = 'PHASE5_20L2F_CONTROLLED_REMAINING_RAW_MATCH_DATA_WRITE_STABLE_BASELINES';
const NEXT_REQUIRED_PHASE = 'Phase 5.21L2 raw_match_data inventory and parser-deferred training design';

const REMAINING_TARGET_REGISTRY = Object.freeze([
    Object.freeze({ match_id: '53_20252026_4830747', external_id: '4830747', home_team: 'Auxerre', away_team: 'Nice' }),
    Object.freeze({
        match_id: '53_20252026_4830748',
        external_id: '4830748',
        home_team: 'Le Havre',
        away_team: 'Marseille',
    }),
    Object.freeze({ match_id: '53_20252026_4830750', external_id: '4830750', home_team: 'Metz', away_team: 'Lorient' }),
    Object.freeze({ match_id: '53_20252026_4830751', external_id: '4830751', home_team: 'Monaco', away_team: 'Lille' }),
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

const BASELINE_RAW_DATA_HASHES = Object.freeze({
    4830747: '8dfc7faaf236ee9f8090301cce9dede32a11ed5b66f2a89e1b3324064f788b25',
    4830748: '538fc2c33281f65d56f5fc004378e5933c0d3bbabc81d8e640bcb7abb4ad9bc3',
    4830750: 'c04915c0e972566f56bcb88a004f9e7e282777f9ca512c626a6acd4bd05e7304',
    4830751: '5c603f83265887f223776941dde430e7abc8b8b9a9577d649cfd149339ffbd37',
    4830752: '241e21be67a3f854d3320bbe86857a19c4bc357b6647d8b798df9b2dec6f56d6',
    4830753: '358466958ec7b60b4dfa5e847537391b85153a564300804636497dd683311567',
    4830754: '3a0832dc6bc16892491c11905ad8ab2fd80e4b29ea2f0aaa71d5659e57785c30',
});

const EXPECTED_EXTERNAL_IDS = Object.freeze(REMAINING_TARGET_REGISTRY.map(target => target.external_id));

const EXPECTED_SCOPE = Object.freeze({
    source: 'fotmob',
    leagueId: '53',
    season: '2025/2026',
    date: '2026-05-10',
    route: 'html_hydration',
    dataVersion: 'fotmob_html_hyd_v1',
    targetCount: 7,
});

const EXPECTED_PRE_WRITE_BASELINE = Object.freeze({
    matches: 10,
    raw_match_data: 3,
    bookmaker_odds_history: 2,
    l3_features: 2,
    match_features_training: 2,
    predictions: 2,
});

const EXPECTED_POST_WRITE_BASELINE = Object.freeze({
    matches: 10,
    raw_match_data: 10,
    bookmaker_odds_history: 2,
    l3_features: 2,
    match_features_training: 2,
    predictions: 2,
});

const FORBIDDEN_SELECT_SQL_VERBS = Object.freeze([
    'INSERT',
    'UPDATE',
    'DELETE',
    'CREATE',
    'ALTER',
    'DROP',
    'TRUNCATE',
    'UPSERT',
    'MERGE',
    'GRANT',
    'REVOKE',
    'LOCK',
    'COPY',
]);

function normalizeText(value) {
    return String(value || '').trim();
}

function normalizeBooleanFlag(value, fallback = undefined) {
    if (typeof value === 'boolean') return value;
    if (value === null || value === undefined || value === '') return fallback;
    const normalized = String(value).trim().toLowerCase();
    if (['1', 'true', 'yes', 'y', 'on'].includes(normalized)) return true;
    if (['0', 'false', 'no', 'n', 'off'].includes(normalized)) return false;
    return fallback;
}

function parseInteger(value, fallback = null) {
    if (value === null || value === undefined || value === '') return fallback;
    const normalized = String(value).trim();
    if (!/^\d+$/.test(normalized)) return Number.NaN;
    return Number.parseInt(normalized, 10);
}

function parseRemainingExternalIds(value) {
    if (Array.isArray(value)) {
        return value.map(id => normalizeText(id)).filter(Boolean);
    }
    if (value === null || value === undefined || value === '') return [];
    return String(value)
        .split(',')
        .map(id => normalizeText(id))
        .filter(Boolean);
}

function parseBaselineRawDataHashes(value) {
    if (value && typeof value === 'object' && !Array.isArray(value)) {
        return Object.fromEntries(
            Object.entries(value)
                .map(([externalId, payload]) => {
                    if (payload && typeof payload === 'object' && !Array.isArray(payload)) {
                        return [
                            normalizeText(externalId),
                            {
                                hash: normalizeText(payload.hash).toLowerCase(),
                                strategy: normalizeText(payload.strategy) || null,
                            },
                        ];
                    }
                    return [
                        normalizeText(externalId),
                        {
                            hash: normalizeText(payload).toLowerCase(),
                            strategy: null,
                        },
                    ];
                })
                .filter(([externalId]) => Boolean(externalId))
        );
    }
    if (value === null || value === undefined || value === '') return {};

    const parsed = {};
    const segments = String(value)
        .split(',')
        .map(segment => segment.trim())
        .filter(Boolean);

    for (const segment of segments) {
        const separatorIndex = segment.indexOf(':');
        if (separatorIndex === -1) {
            parsed[`__invalid__${Object.keys(parsed).length}`] = {
                hash: normalizeText(segment).toLowerCase(),
                strategy: null,
            };
            continue;
        }
        const externalId = normalizeText(segment.slice(0, separatorIndex));
        const rawValue = normalizeText(segment.slice(separatorIndex + 1));
        const [hashPart, strategyPart] = rawValue.split('@');
        if (externalId) {
            parsed[externalId] = {
                hash: normalizeText(hashPart).toLowerCase(),
                strategy: normalizeText(strategyPart) || null,
            };
        }
    }

    return parsed;
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
        remainingExternalIds: null,
        expectedTargetCount: null,
        hashStrategy: null,
        baselineRawDataHashes: null,
        dataVersion: null,
        networkAuthorization: null,
        livePreviewAuthorization: null,
        finalDbWriteConfirmation: null,
        allowDbWrite: null,
        allowRawMatchDataWrite: null,
        allowMatchesWrite: null,
        allowParserFeatures: null,
        allowTraining: null,
        allowPrediction: null,
        allowBrowserRuntime: false,
        allowProxyRuntime: false,
        concurrency: null,
        retry: null,
        printBody: null,
        saveBody: null,
        bulk: false,
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
        'remaining-external-ids': 'remainingExternalIds',
        remaining_external_ids: 'remainingExternalIds',
        'expected-target-count': 'expectedTargetCount',
        expected_target_count: 'expectedTargetCount',
        'hash-strategy': 'hashStrategy',
        hash_strategy: 'hashStrategy',
        'baseline-raw-data-hashes': 'baselineRawDataHashes',
        baseline_raw_data_hashes: 'baselineRawDataHashes',
        'data-version': 'dataVersion',
        data_version: 'dataVersion',
        'network-authorization': 'networkAuthorization',
        network_authorization: 'networkAuthorization',
        'live-preview-authorization': 'livePreviewAuthorization',
        live_preview_authorization: 'livePreviewAuthorization',
        'final-db-write-confirmation': 'finalDbWriteConfirmation',
        final_db_write_confirmation: 'finalDbWriteConfirmation',
        'allow-db-write': 'allowDbWrite',
        allow_db_write: 'allowDbWrite',
        'allow-raw-match-data-write': 'allowRawMatchDataWrite',
        allow_raw_match_data_write: 'allowRawMatchDataWrite',
        'allow-matches-write': 'allowMatchesWrite',
        allow_matches_write: 'allowMatchesWrite',
        'allow-parser-features': 'allowParserFeatures',
        allow_parser_features: 'allowParserFeatures',
        'allow-training': 'allowTraining',
        allow_training: 'allowTraining',
        'allow-prediction': 'allowPrediction',
        allow_prediction: 'allowPrediction',
        'allow-browser-runtime': 'allowBrowserRuntime',
        allow_browser_runtime: 'allowBrowserRuntime',
        'allow-proxy-runtime': 'allowProxyRuntime',
        allow_proxy_runtime: 'allowProxyRuntime',
        concurrency: 'concurrency',
        retry: 'retry',
        'print-body': 'printBody',
        print_body: 'printBody',
        'save-body': 'saveBody',
        save_body: 'saveBody',
        bulk: 'bulk',
        commit: 'commit',
        execute: 'execute',
        help: 'help',
        h: 'help',
    };
    const booleanKeys = new Set([
        'networkAuthorization',
        'livePreviewAuthorization',
        'finalDbWriteConfirmation',
        'allowDbWrite',
        'allowRawMatchDataWrite',
        'allowMatchesWrite',
        'allowParserFeatures',
        'allowTraining',
        'allowPrediction',
        'allowBrowserRuntime',
        'allowProxyRuntime',
        'printBody',
        'saveBody',
        'bulk',
        'commit',
        'execute',
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
        if (consumedNext) index += 1;

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

function pushRequiredYesError(errors, value, flagName) {
    if (value === true) return;
    if (value === false) {
        errors.push(`${flagName}=yes is required in Phase 5.20L2F`);
        return;
    }
    errors.push(`missing ${flagName}=yes`);
}

function pushRequiredNoError(errors, value, flagName) {
    if (value === false) return;
    if (value === true) {
        errors.push(`${flagName}=yes is blocked in Phase 5.20L2F`);
        return;
    }
    errors.push(`missing ${flagName}=no`);
}

function pushRequiredIntegerError(errors, value, expected, flagName) {
    if (!Number.isFinite(value) || value !== expected) {
        errors.push(`${flagName} must be ${expected} in Phase 5.20L2F`);
    }
}

function normalizeWriteInput(input = {}) {
    return {
        source: normalizeText(input.source).toLowerCase(),
        leagueId: normalizeText(input.leagueId),
        season: normalizeText(input.season),
        date: normalizeText(input.date),
        route: normalizeText(input.route).toLowerCase(),
        remainingExternalIds: parseRemainingExternalIds(input.remainingExternalIds),
        expectedTargetCount: parseInteger(input.expectedTargetCount, null),
        hashStrategy: normalizeText(input.hashStrategy).toLowerCase(),
        baselineRawDataHashes: parseBaselineRawDataHashes(input.baselineRawDataHashes),
        dataVersion: normalizeText(input.dataVersion).toLowerCase(),
        networkAuthorization: normalizeBooleanFlag(input.networkAuthorization, undefined),
        livePreviewAuthorization: normalizeBooleanFlag(input.livePreviewAuthorization, undefined),
        finalDbWriteConfirmation: normalizeBooleanFlag(input.finalDbWriteConfirmation, undefined),
        allowDbWrite: normalizeBooleanFlag(input.allowDbWrite, undefined),
        allowRawMatchDataWrite: normalizeBooleanFlag(input.allowRawMatchDataWrite, undefined),
        allowMatchesWrite: normalizeBooleanFlag(input.allowMatchesWrite, undefined),
        allowParserFeatures: normalizeBooleanFlag(input.allowParserFeatures, undefined),
        allowTraining: normalizeBooleanFlag(input.allowTraining, undefined),
        allowPrediction: normalizeBooleanFlag(input.allowPrediction, undefined),
        allowBrowserRuntime: normalizeBooleanFlag(input.allowBrowserRuntime, false),
        allowProxyRuntime: normalizeBooleanFlag(input.allowProxyRuntime, false),
        concurrency: parseInteger(input.concurrency, null),
        retry: parseInteger(input.retry, null),
        printBody: normalizeBooleanFlag(input.printBody, undefined),
        saveBody: normalizeBooleanFlag(input.saveBody, undefined),
        bulk: normalizeBooleanFlag(input.bulk, false),
        commit: normalizeBooleanFlag(input.commit, false),
        execute: normalizeBooleanFlag(input.execute, false),
        unknown: Array.isArray(input.unknown) ? input.unknown : [],
    };
}

function validateWriteInput(input = {}) {
    const value = normalizeWriteInput(input);
    const errors = [];

    if (value.unknown.length > 0) {
        errors.push(`unknown arguments: ${value.unknown.join(', ')}`);
    }
    if (!value.source) {
        errors.push('missing source: provide --source=fotmob');
    } else if (value.source !== EXPECTED_SCOPE.source) {
        errors.push('source must be fotmob');
    }
    if (!value.leagueId) {
        errors.push('missing league-id');
    } else if (value.leagueId !== EXPECTED_SCOPE.leagueId) {
        errors.push('league-id must be 53');
    }
    if (!value.season) {
        errors.push('missing season');
    } else if (value.season !== EXPECTED_SCOPE.season) {
        errors.push('season must be 2025/2026');
    }
    if (!value.date) {
        errors.push('missing date');
    } else if (value.date !== EXPECTED_SCOPE.date) {
        errors.push('date must be 2026-05-10');
    }
    if (!value.route) {
        errors.push('missing route');
    } else if (value.route !== EXPECTED_SCOPE.route) {
        errors.push('route must be html_hydration');
    }

    const ids = value.remainingExternalIds;
    if (ids.length === 0) {
        errors.push('remaining-external-ids is required');
    } else if (ids.length !== EXPECTED_EXTERNAL_IDS.length) {
        errors.push(`remaining-external-ids must have ${EXPECTED_EXTERNAL_IDS.length} ids`);
    } else {
        const expectedIds = new Set(EXPECTED_EXTERNAL_IDS);
        for (const externalId of ids) {
            if (externalId === '4830746') {
                errors.push('4830746 is already ingested');
            }
            if (!expectedIds.has(externalId)) {
                errors.push(`unexpected remaining external_id: ${externalId}`);
            }
        }
        for (const expectedExternalId of EXPECTED_EXTERNAL_IDS) {
            if (!ids.includes(expectedExternalId)) {
                errors.push(`missing expected remaining external_id: ${expectedExternalId}`);
            }
        }
    }

    pushRequiredIntegerError(errors, value.expectedTargetCount, EXPECTED_SCOPE.targetCount, 'expected-target-count');

    if (!value.hashStrategy) {
        errors.push('missing hash-strategy=stable_raw_payload_v1');
    } else if (value.hashStrategy !== HASH_STRATEGY_STABLE_RAW_PAYLOAD_V1) {
        errors.push(`hash-strategy must be ${HASH_STRATEGY_STABLE_RAW_PAYLOAD_V1}`);
    }

    const baselineHashKeys = Object.keys(value.baselineRawDataHashes);
    if (baselineHashKeys.length === 0) {
        errors.push('baseline-raw-data-hashes is required');
    } else if (baselineHashKeys.length !== EXPECTED_EXTERNAL_IDS.length) {
        errors.push(`baseline-raw-data-hashes must contain ${EXPECTED_EXTERNAL_IDS.length} hashes`);
    }
    for (const externalId of baselineHashKeys) {
        if (!EXPECTED_EXTERNAL_IDS.includes(externalId)) {
            errors.push(`unexpected baseline external_id: ${externalId}`);
        }
    }
    for (const externalId of EXPECTED_EXTERNAL_IDS) {
        const baseline = value.baselineRawDataHashes[externalId];
        const hash = baseline && typeof baseline === 'object' ? baseline.hash : null;
        const strategy = baseline && typeof baseline === 'object' ? baseline.strategy || value.hashStrategy : null;
        if (!hash) {
            errors.push(`missing baseline raw_data_hash for external_id ${externalId}`);
            continue;
        }
        if (!/^[a-f0-9]{64}$/.test(hash)) {
            errors.push(`invalid baseline raw_data_hash format for external_id ${externalId}`);
            continue;
        }
        if (hash !== BASELINE_RAW_DATA_HASHES[externalId]) {
            errors.push(
                `baseline raw_data_hash mismatch for external_id ${externalId}; expected Phase 5.20L2E stable baseline`
            );
            continue;
        }
        if (!strategy) {
            errors.push(`missing baseline hash_strategy for external_id ${externalId}`);
            continue;
        }
        if (strategy !== HASH_STRATEGY_STABLE_RAW_PAYLOAD_V1) {
            errors.push(`baseline hash_strategy mismatch for external_id ${externalId}`);
            continue;
        }
        value.baselineRawDataHashes[externalId].strategy = strategy;
    }

    if (!value.dataVersion) {
        errors.push('missing data-version');
    } else if (value.dataVersion !== EXPECTED_SCOPE.dataVersion) {
        errors.push(`data-version must be ${EXPECTED_SCOPE.dataVersion}`);
    }

    pushRequiredYesError(errors, value.networkAuthorization, 'network-authorization');
    pushRequiredYesError(errors, value.livePreviewAuthorization, 'live-preview-authorization');
    pushRequiredYesError(errors, value.finalDbWriteConfirmation, 'final-db-write-confirmation');
    pushRequiredYesError(errors, value.allowDbWrite, 'allow-db-write');
    pushRequiredYesError(errors, value.allowRawMatchDataWrite, 'allow-raw-match-data-write');
    pushRequiredNoError(errors, value.allowMatchesWrite, 'allow-matches-write');
    pushRequiredNoError(errors, value.allowParserFeatures, 'allow-parser-features');
    pushRequiredNoError(errors, value.allowTraining, 'allow-training');
    pushRequiredNoError(errors, value.allowPrediction, 'allow-prediction');
    pushRequiredNoError(errors, value.printBody, 'print-body');
    pushRequiredNoError(errors, value.saveBody, 'save-body');
    pushRequiredIntegerError(errors, value.concurrency, 1, 'concurrency');
    pushRequiredIntegerError(errors, value.retry, 0, 'retry');

    if (value.allowBrowserRuntime === true) {
        errors.push('allow-browser-runtime=yes is blocked in Phase 5.20L2F');
    }
    if (value.allowProxyRuntime === true) {
        errors.push('allow-proxy-runtime=yes is blocked in Phase 5.20L2F');
    }
    if (value.bulk === true) {
        errors.push('bulk=yes is blocked in Phase 5.20L2F');
    }
    if (value.commit === true) {
        errors.push('commit=yes is blocked in Phase 5.20L2F');
    }
    if (value.execute === true) {
        errors.push('execute=yes is blocked in Phase 5.20L2F');
    }

    return {
        ok: errors.length === 0,
        errors,
        value,
    };
}

function getRemainingTargetRegistry(baselineRawDataHashes = BASELINE_RAW_DATA_HASHES) {
    return REMAINING_TARGET_REGISTRY.map(target => ({
        ...target,
        baseline_raw_data_hash:
            (baselineRawDataHashes[target.external_id] &&
                typeof baselineRawDataHashes[target.external_id] === 'object' &&
                baselineRawDataHashes[target.external_id].hash) ||
            baselineRawDataHashes[target.external_id] ||
            null,
        baseline_hash_strategy:
            (baselineRawDataHashes[target.external_id] &&
                typeof baselineRawDataHashes[target.external_id] === 'object' &&
                baselineRawDataHashes[target.external_id].strategy) ||
            (baselineRawDataHashes[target.external_id] ? HASH_STRATEGY_STABLE_RAW_PAYLOAD_V1 : null),
    }));
}

async function recaptureTarget(target, fetcherDeps = {}) {
    const fetchFn = fetcherDeps.fetchFn || global.fetch;
    if (typeof fetchFn !== 'function') {
        throw new Error('FETCH_DEPENDENCY_MISSING: fetchFn is required');
    }

    return fetchFotMobRawDetail(
        {
            externalId: target.external_id,
            matchId: target.match_id,
            homeTeam: target.home_team,
            awayTeam: target.away_team,
            route: EXPECTED_SCOPE.route,
            dataVersion: EXPECTED_SCOPE.dataVersion,
            printBody: false,
            saveBody: false,
            retry: 0,
            allowBrowserRuntime: false,
            allowProxyRuntime: false,
        },
        {
            fetchFn,
            now: fetcherDeps.now,
            parser: fetcherDeps.parser || { extractFromHtml, transformToApiFormat },
        }
    );
}

function buildRecaptureDecision({
    validPayload,
    baselineStrategy,
    hashStrategy,
    hasStableHashOutput,
    hashMatchesBaseline,
}) {
    if (!validPayload) return 'invalid_payload';
    if (!hashStrategy) return 'hash_strategy_missing';
    if (baselineStrategy !== HASH_STRATEGY_STABLE_RAW_PAYLOAD_V1) return 'baseline_strategy_mismatch';
    if (hashStrategy !== HASH_STRATEGY_STABLE_RAW_PAYLOAD_V1) return 'hash_strategy_mismatch';
    if (!hasStableHashOutput) return 'stable_hash_output_missing';
    if (hashMatchesBaseline) return 'would_insert';
    return 'hash_drift';
}

function buildPerTargetRecapture(target, recaptureResult = {}) {
    const rawData =
        recaptureResult.raw_data &&
        typeof recaptureResult.raw_data === 'object' &&
        !Array.isArray(recaptureResult.raw_data)
            ? JSON.parse(JSON.stringify(recaptureResult.raw_data))
            : null;
    const rawDataHash = normalizeText(
        recaptureResult.raw_data_hash || recaptureResult.data_hash || recaptureResult.stable_raw_payload_hash
    ).toLowerCase();
    const rawDataErrors = rawData ? validateCanonicalRawDataShape(rawData) : ['raw_data missing from recapture result'];
    const validPayload =
        recaptureResult.ok === true &&
        recaptureResult.hydration_parse_ok === true &&
        recaptureResult.looks_like_valid_match_detail === true &&
        rawDataErrors.length === 0;
    const hashStrategy = normalizeText(recaptureResult.hash_strategy).toLowerCase() || null;
    const hasStableHashOutput =
        Boolean(rawDataHash) &&
        normalizeText(recaptureResult.raw_data_hash).toLowerCase() === rawDataHash &&
        normalizeText(recaptureResult.data_hash).toLowerCase() === rawDataHash &&
        normalizeText(recaptureResult.stable_raw_payload_hash).toLowerCase() === rawDataHash;
    const matchIdSource = recaptureResult.match_id_source || rawData?._meta?.match_id_source || null;
    const baselineStrategy = target.baseline_hash_strategy || null;
    const hashMatchesBaseline =
        validPayload &&
        hasStableHashOutput &&
        baselineStrategy === HASH_STRATEGY_STABLE_RAW_PAYLOAD_V1 &&
        hashStrategy === HASH_STRATEGY_STABLE_RAW_PAYLOAD_V1 &&
        rawDataHash === target.baseline_raw_data_hash;

    return {
        match_id: target.match_id,
        external_id: target.external_id,
        data_version: EXPECTED_SCOPE.dataVersion,
        home_team: target.home_team,
        away_team: target.away_team,
        selected_route: recaptureResult.route || EXPECTED_SCOPE.route,
        request_url: recaptureResult.request_url || null,
        final_url: recaptureResult.final_url || null,
        http_status: recaptureResult.http_status ?? 0,
        content_type: recaptureResult.content_type || null,
        body_byte_length: recaptureResult.body_byte_length ?? 0,
        body_sha256: recaptureResult.body_sha256 || null,
        hydration_parse_ok: recaptureResult.hydration_parse_ok === true,
        looks_like_valid_match_detail: recaptureResult.looks_like_valid_match_detail === true,
        hash_strategy: hashStrategy,
        baseline_hash_strategy: baselineStrategy,
        baseline_raw_data_hash: target.baseline_raw_data_hash,
        raw_data_hash: rawDataHash,
        data_hash: rawDataHash,
        stable_hash_output_complete: hasStableHashOutput,
        hash_matches_baseline: hashMatchesBaseline,
        match_id_source: matchIdSource,
        existing_raw_match_data_found: false,
        decision: buildRecaptureDecision({
            validPayload,
            baselineStrategy,
            hashStrategy,
            hasStableHashOutput,
            hashMatchesBaseline,
        }),
        body_printed: false,
        body_saved: false,
        browser_used: false,
        proxy_used: false,
        valid_payload: validPayload,
        raw_data_errors: rawDataErrors,
        raw_data: rawData,
        controlled_error: recaptureResult.controlled_error || null,
    };
}

function buildHashGateResult(perTargetRecapture = [], targetCount = EXPECTED_SCOPE.targetCount) {
    const attemptedTargetCount = perTargetRecapture.length;
    const validPayloadCount = perTargetRecapture.filter(entry => entry.valid_payload === true).length;
    const hashMatchCount = perTargetRecapture.filter(entry => entry.hash_matches_baseline === true).length;
    const hashDriftCount = perTargetRecapture.filter(
        entry => entry.valid_payload === true && entry.hash_matches_baseline === false
    ).length;
    const invalidPayloadCount = perTargetRecapture.filter(entry => entry.valid_payload !== true).length;

    return {
        ok:
            attemptedTargetCount === targetCount &&
            validPayloadCount === targetCount &&
            hashMatchCount === targetCount &&
            hashDriftCount === 0 &&
            invalidPayloadCount === 0,
        targetCount,
        attemptedTargetCount,
        validPayloadCount,
        hashMatchCount,
        hashDriftCount,
        invalidPayloadCount,
    };
}

function buildInsertRawMatchDataRows(perTargetRecapture = [], collectedAt, dataVersion = EXPECTED_SCOPE.dataVersion) {
    return perTargetRecapture.map(entry => ({
        matchId: entry.match_id,
        externalId: entry.external_id,
        rawData: JSON.parse(JSON.stringify(entry.raw_data)),
        collectedAt,
        dataVersion,
        dataHash: entry.raw_data_hash,
    }));
}

function buildProtectedTableBaseline(source = {}) {
    const rows = Array.isArray(source) ? source : null;
    const objectSource = rows
        ? Object.fromEntries(rows.map(row => [row.table_name, Number(row.rows)]))
        : source && typeof source === 'object'
          ? source
          : {};

    return {
        matches: Number(objectSource.matches ?? 0),
        raw_match_data: Number(objectSource.raw_match_data ?? 0),
        bookmaker_odds_history: Number(objectSource.bookmaker_odds_history ?? 0),
        l3_features: Number(objectSource.l3_features ?? 0),
        match_features_training: Number(objectSource.match_features_training ?? 0),
        predictions: Number(objectSource.predictions ?? 0),
    };
}

function buildPostWriteVerification(baselineSource = {}) {
    const baseline = buildProtectedTableBaseline(baselineSource);
    return {
        matches: baseline.matches,
        raw_match_data: baseline.raw_match_data,
        bookmaker_odds_history: baseline.bookmaker_odds_history,
        l3_features: baseline.l3_features,
        match_features_training: baseline.match_features_training,
        predictions: baseline.predictions,
    };
}

function createEmptyPostWriteVerification() {
    return {
        matches: null,
        raw_match_data: null,
        bookmaker_odds_history: null,
        l3_features: null,
        match_features_training: null,
        predictions: null,
    };
}

function includesText(value, expected) {
    return normalizeText(value).toLowerCase().includes(normalizeText(expected).toLowerCase());
}

function validateBaselineExact(actual = {}, expected = {}) {
    return Object.entries(expected)
        .filter(([key, expectedValue]) => Number(actual[key]) !== expectedValue)
        .map(([key, expectedValue]) => `${key} baseline expected ${expectedValue}, got ${actual[key]}`);
}

function validateTargetMatchRows(rows = [], targetRegistry = []) {
    if (!Array.isArray(rows)) return ['target match SELECT did not return an array'];
    if (rows.length !== targetRegistry.length) {
        return [`target match SELECT expected ${targetRegistry.length} rows, got ${rows.length}`];
    }

    const rowByMatchId = new Map(rows.map(row => [normalizeText(row.match_id), row]));
    const errors = [];
    for (const target of targetRegistry) {
        const row = rowByMatchId.get(target.match_id);
        if (!row) {
            errors.push(`missing target match row for ${target.match_id}`);
            continue;
        }
        if (normalizeText(row.external_id) !== target.external_id) {
            errors.push(`target external_id mismatch for ${target.match_id}: ${row.external_id}`);
        }
        if (!includesText(row.home_team, target.home_team)) {
            errors.push(`target home_team mismatch for ${target.match_id}: ${row.home_team}`);
        }
        if (!includesText(row.away_team, target.away_team)) {
            errors.push(`target away_team mismatch for ${target.match_id}: ${row.away_team}`);
        }
    }
    return errors;
}

function validateInsertedRows(rows = [], targetRegistry = [], dataVersion = EXPECTED_SCOPE.dataVersion) {
    if (!Array.isArray(rows)) return ['inserted row metadata SELECT did not return an array'];
    if (rows.length !== targetRegistry.length) {
        return [`inserted row metadata expected ${targetRegistry.length} rows, got ${rows.length}`];
    }

    const rowByExternalId = new Map(rows.map(row => [normalizeText(row.external_id), row]));
    const errors = [];
    for (const target of targetRegistry) {
        const row = rowByExternalId.get(target.external_id);
        if (!row) {
            errors.push(`missing inserted row metadata for external_id ${target.external_id}`);
            continue;
        }
        if (normalizeText(row.match_id) !== target.match_id) {
            errors.push(`inserted row match_id mismatch for external_id ${target.external_id}`);
        }
        if (normalizeText(row.data_version).toLowerCase() !== dataVersion) {
            errors.push(`inserted row data_version mismatch for external_id ${target.external_id}`);
        }
        if (normalizeText(row.data_hash).toLowerCase() !== normalizeText(target.baseline_raw_data_hash).toLowerCase()) {
            errors.push(`inserted row data_hash mismatch for external_id ${target.external_id}`);
        }
    }
    return errors;
}

function assertSafeSelect(sql) {
    const text = String(sql || '').trim();
    const withoutTrailingSemicolon = text.replace(/;+\s*$/, '');
    if (!/^\s*SELECT\b/i.test(withoutTrailingSemicolon)) {
        throw new Error('Unsafe SQL blocked: query must start with SELECT');
    }
    if (withoutTrailingSemicolon.includes(';')) {
        throw new Error('Unsafe SQL blocked: multiple statements are not allowed');
    }
    if (/\bFOR\s+UPDATE\b/i.test(withoutTrailingSemicolon)) {
        throw new Error('Unsafe SQL blocked: SELECT FOR UPDATE is not allowed');
    }
    for (const verb of FORBIDDEN_SELECT_SQL_VERBS) {
        if (new RegExp(`\\b${verb}\\b`, 'i').test(withoutTrailingSemicolon)) {
            throw new Error(`Unsafe SQL blocked: ${verb} is not allowed`);
        }
    }
}

async function safeSelect(client, sql, values = []) {
    assertSafeSelect(sql);
    return client.query(sql, values);
}

function buildDbConfig() {
    return {
        host: process.env.DB_HOST || process.env.POSTGRES_HOST || 'db',
        port: Number.parseInt(process.env.DB_PORT || process.env.POSTGRES_PORT || '5432', 10),
        database: process.env.DB_NAME || process.env.POSTGRES_DB || 'football_db',
        user: process.env.DB_USER || process.env.POSTGRES_USER || 'football_user',
        password: process.env.DB_PASSWORD || process.env.POSTGRES_PASSWORD || 'football_pass',
        application_name: 'l2_remaining_raw_match_data_write',
        max: 2,
        idleTimeoutMillis: 5000,
        connectionTimeoutMillis: 5000,
    };
}

function createPgPool() {
    const { Pool } = require('pg');
    return new Pool(buildDbConfig());
}

async function acquireDbConnection(dependencies = {}) {
    if (dependencies.client) {
        return {
            client: dependencies.client,
            release: async () => {},
            cleanupPool: async () => {},
        };
    }

    const pool = dependencies.pool || (dependencies.createPool || createPgPool)();
    if (pool && typeof pool.connect === 'function') {
        const client = await pool.connect();
        return {
            client,
            release: async () => {
                if (typeof client.release === 'function') client.release();
            },
            cleanupPool: async () => {
                if (!dependencies.pool && typeof pool.end === 'function') await pool.end();
            },
        };
    }

    return {
        client: pool,
        release: async () => {},
        cleanupPool: async () => {
            if (!dependencies.pool && pool && typeof pool.end === 'function') await pool.end();
        },
    };
}

async function selectTargetMatches(client, targetRegistry = []) {
    const query = `
        SELECT match_id, external_id, home_team, away_team, match_date, status
        FROM matches
        WHERE match_id = ANY($1::text[])
        ORDER BY match_id
    `;
    const result = await safeSelect(client, query, [targetRegistry.map(target => target.match_id)]);
    return result.rows || [];
}

async function selectExistingRawMatchData(client, targetRegistry = [], dataVersion = EXPECTED_SCOPE.dataVersion) {
    const query = `
        SELECT id, match_id, external_id, collected_at, data_version, data_hash
        FROM raw_match_data
        WHERE match_id = ANY($1::text[])
          AND data_version = $2
        ORDER BY external_id, collected_at DESC NULLS LAST, id DESC
    `;
    const result = await safeSelect(client, query, [targetRegistry.map(target => target.match_id), dataVersion]);
    return result.rows || [];
}

async function selectProtectedTableBaseline(client) {
    const query = `
        SELECT 'matches' AS table_name, COUNT(*)::int AS rows FROM matches
        UNION ALL
        SELECT 'bookmaker_odds_history', COUNT(*)::int FROM bookmaker_odds_history
        UNION ALL
        SELECT 'raw_match_data', COUNT(*)::int FROM raw_match_data
        UNION ALL
        SELECT 'l3_features', COUNT(*)::int FROM l3_features
        UNION ALL
        SELECT 'match_features_training', COUNT(*)::int FROM match_features_training
        UNION ALL
        SELECT 'predictions', COUNT(*)::int FROM predictions
    `;
    const result = await safeSelect(client, query, []);
    return buildProtectedTableBaseline(result.rows || []);
}

async function selectInsertedRowsMetadata(client, targetRegistry = [], dataVersion = EXPECTED_SCOPE.dataVersion) {
    const query = `
        SELECT id, match_id, external_id, collected_at, data_version, data_hash
        FROM raw_match_data
        WHERE match_id = ANY($1::text[])
          AND data_version = $2
        ORDER BY external_id, id
    `;
    const result = await safeSelect(client, query, [targetRegistry.map(target => target.match_id), dataVersion]);
    return result.rows || [];
}

function buildInsertRawMatchDataSql({ matchId, externalId, rawData, collectedAt, dataVersion, dataHash }) {
    return {
        text: `
            INSERT INTO raw_match_data (
                match_id,
                external_id,
                raw_data,
                collected_at,
                data_version,
                data_hash
            )
            VALUES ($1, $2, $3::jsonb, $4::timestamptz, $5, $6)
            ON CONFLICT (match_id, data_version) DO NOTHING
            RETURNING id, match_id, external_id, collected_at, data_version, data_hash
        `,
        values: [matchId, externalId, JSON.stringify(rawData), collectedAt, dataVersion, dataHash],
    };
}

function nowUtcIso(dependencies = {}) {
    if (typeof dependencies.now === 'function') return dependencies.now();
    if (dependencies.now) return dependencies.now;
    return new Date().toISOString();
}

function sanitizePerTargetWrite(perTargetWrite = []) {
    return perTargetWrite.map(entry => ({
        match_id: entry.match_id,
        external_id: entry.external_id,
        home_team: entry.home_team,
        away_team: entry.away_team,
        selected_route: entry.selected_route,
        request_url: entry.request_url,
        final_url: entry.final_url,
        http_status: entry.http_status,
        content_type: entry.content_type,
        body_byte_length: entry.body_byte_length,
        body_sha256: entry.body_sha256,
        hydration_parse_ok: entry.hydration_parse_ok === true,
        looks_like_valid_match_detail: entry.looks_like_valid_match_detail === true,
        hash_strategy: entry.hash_strategy,
        baseline_hash_strategy: entry.baseline_hash_strategy,
        baseline_raw_data_hash: entry.baseline_raw_data_hash,
        raw_data_hash: entry.raw_data_hash,
        data_hash: entry.data_hash,
        stable_hash_output_complete: entry.stable_hash_output_complete === true,
        hash_matches_baseline: entry.hash_matches_baseline === true,
        match_id_source: entry.match_id_source,
        existing_raw_match_data_found: entry.existing_raw_match_data_found === true,
        decision: entry.decision,
        body_printed: false,
        body_saved: false,
        browser_used: false,
        proxy_used: false,
    }));
}

function buildControlledRemainingWriteResult({
    input = {},
    executionCompleted = false,
    targetCount = EXPECTED_SCOPE.targetCount,
    attemptedTargetCount = 0,
    validPayloadCount = 0,
    hashMatchCount = 0,
    hashDriftCount = 0,
    invalidPayloadCount = 0,
    existingRawMatchDataCount = 0,
    insertedCount = 0,
    updatedCount = 0,
    skippedCount = 0,
    rawMatchDataWriteExecuted = false,
    dbWriteExecuted = false,
    matchesWriteExecuted = false,
    parserFeaturesExecuted = false,
    trainingExecuted = false,
    predictionExecuted = false,
    perTargetWrite = [],
    transaction = {},
    postWriteVerification = null,
    insertedRowsMetadata = [],
    controlledError = null,
    reason = null,
}) {
    const value = normalizeWriteInput(input);
    const result = {
        phase: PHASE,
        execution_completed: executionCompleted,
        source: value.source || EXPECTED_SCOPE.source,
        league_id: value.leagueId || EXPECTED_SCOPE.leagueId,
        season: value.season || EXPECTED_SCOPE.season,
        date: value.date || EXPECTED_SCOPE.date,
        route: value.route || EXPECTED_SCOPE.route,
        data_version: value.dataVersion || EXPECTED_SCOPE.dataVersion,
        target_count: targetCount,
        attempted_target_count: attemptedTargetCount,
        valid_payload_count: validPayloadCount,
        hash_match_count: hashMatchCount,
        hash_drift_count: hashDriftCount,
        invalid_payload_count: invalidPayloadCount,
        hash_strategy: value.hashStrategy || HASH_STRATEGY_STABLE_RAW_PAYLOAD_V1,
        existing_raw_match_data_count: existingRawMatchDataCount,
        inserted_count: insertedCount,
        updated_count: updatedCount,
        skipped_count: skippedCount,
        raw_match_data_write_executed: rawMatchDataWriteExecuted,
        db_write_executed: dbWriteExecuted,
        matches_write_executed: matchesWriteExecuted,
        parser_features_executed: parserFeaturesExecuted,
        training_executed: trainingExecuted,
        prediction_executed: predictionExecuted,
        consolidated_fetcher_used: true,
        per_target_write: sanitizePerTargetWrite(perTargetWrite),
        transaction: {
            began: transaction.began === true,
            committed: transaction.committed === true,
            rolled_back: transaction.rolled_back === true,
        },
        post_write_verification: postWriteVerification || createEmptyPostWriteVerification(),
        inserted_row_metadata: Array.isArray(insertedRowsMetadata)
            ? insertedRowsMetadata.map(row => ({
                  id: row.id ?? null,
                  match_id: row.match_id ?? null,
                  external_id: row.external_id ?? null,
                  collected_at: row.collected_at ?? null,
                  data_version: row.data_version ?? null,
                  data_hash: row.data_hash ?? null,
              }))
            : [],
        body_printed: false,
        body_saved: false,
        browser_used: false,
        proxy_used: false,
        next_required_phase: NEXT_REQUIRED_PHASE,
    };

    if (reason) result.reason = reason;
    if (controlledError) result.controlled_error = controlledError;
    return result;
}

function buildRecaptureFailure(target, error) {
    return {
        route: EXPECTED_SCOPE.route,
        request_url: null,
        final_url: null,
        http_status: 0,
        content_type: null,
        body_byte_length: 0,
        body_sha256: null,
        ok: false,
        hydration_parse_ok: false,
        looks_like_valid_match_detail: false,
        raw_data: null,
        raw_data_hash: null,
        controlled_error: `RECAPTURE_ERROR:${target.external_id}:${String(error.message || error)}`,
    };
}

async function executeRemainingRawMatchDataWrite(input = {}, dependencies = {}) {
    const validation = dependencies.skipValidation
        ? { ok: true, errors: [], value: normalizeWriteInput(input) }
        : validateWriteInput(input);

    if (!validation.ok) {
        return buildControlledRemainingWriteResult({
            input,
            executionCompleted: false,
            controlledError: `INVALID_CONTROLLED_REMAINING_WRITE_INPUT:${validation.errors.join('; ')}`,
        });
    }

    const value = validation.value;
    const targetRegistry = getRemainingTargetRegistry(value.baselineRawDataHashes);
    const recaptureFn = dependencies.recaptureFn || recaptureTarget;
    const recaptureDeps = dependencies.recaptureDeps || {
        fetchFn: dependencies.fetchFn || global.fetch,
        now: dependencies.fetchNow || dependencies.now,
    };

    const perTargetRecapture = [];
    for (const target of targetRegistry) {
        let recaptureResult;
        try {
            recaptureResult = await recaptureFn(target, recaptureDeps);
        } catch (error) {
            recaptureResult = buildRecaptureFailure(target, error);
        }

        const entry = buildPerTargetRecapture(target, recaptureResult);
        perTargetRecapture.push(entry);

        if (entry.valid_payload !== true) {
            const hashGate = buildHashGateResult(perTargetRecapture, targetRegistry.length);
            return buildControlledRemainingWriteResult({
                input: value,
                executionCompleted: false,
                targetCount: targetRegistry.length,
                attemptedTargetCount: hashGate.attemptedTargetCount,
                validPayloadCount: hashGate.validPayloadCount,
                hashMatchCount: hashGate.hashMatchCount,
                hashDriftCount: hashGate.hashDriftCount,
                invalidPayloadCount: hashGate.invalidPayloadCount,
                perTargetWrite: perTargetRecapture,
                reason: 'invalid_payload',
                controlledError:
                    entry.controlled_error ||
                    `INVALID_PAYLOAD_FOR_EXTERNAL_ID:${entry.external_id}:${entry.raw_data_errors.join('; ')}`,
            });
        }

        if (entry.baseline_hash_strategy !== HASH_STRATEGY_STABLE_RAW_PAYLOAD_V1) {
            return buildControlledRemainingWriteResult({
                input: value,
                executionCompleted: false,
                targetCount: targetRegistry.length,
                attemptedTargetCount: perTargetRecapture.length,
                validPayloadCount: perTargetRecapture.filter(item => item.valid_payload === true).length,
                hashMatchCount: 0,
                hashDriftCount: 0,
                invalidPayloadCount: perTargetRecapture.filter(item => item.valid_payload !== true).length,
                perTargetWrite: perTargetRecapture,
                reason: 'baseline_strategy_mismatch',
                controlledError: `BASELINE_HASH_STRATEGY_MISMATCH:${entry.external_id}: expected ${HASH_STRATEGY_STABLE_RAW_PAYLOAD_V1}, got ${entry.baseline_hash_strategy || 'missing'}; run Phase 5.20L2E stable-hash preflight refresh`,
            });
        }

        if (entry.hash_strategy !== HASH_STRATEGY_STABLE_RAW_PAYLOAD_V1) {
            return buildControlledRemainingWriteResult({
                input: value,
                executionCompleted: false,
                targetCount: targetRegistry.length,
                attemptedTargetCount: perTargetRecapture.length,
                validPayloadCount: perTargetRecapture.filter(item => item.valid_payload === true).length,
                hashMatchCount: 0,
                hashDriftCount: 0,
                invalidPayloadCount: perTargetRecapture.filter(item => item.valid_payload !== true).length,
                perTargetWrite: perTargetRecapture,
                reason: entry.hash_strategy ? 'hash_strategy_mismatch' : 'hash_strategy_missing',
                controlledError: `FETCHER_HASH_STRATEGY_MISMATCH:${entry.external_id}: expected ${HASH_STRATEGY_STABLE_RAW_PAYLOAD_V1}, got ${entry.hash_strategy || 'missing'}`,
            });
        }

        if (entry.stable_hash_output_complete !== true) {
            return buildControlledRemainingWriteResult({
                input: value,
                executionCompleted: false,
                targetCount: targetRegistry.length,
                attemptedTargetCount: perTargetRecapture.length,
                validPayloadCount: perTargetRecapture.filter(item => item.valid_payload === true).length,
                hashMatchCount: 0,
                hashDriftCount: 0,
                invalidPayloadCount: perTargetRecapture.filter(item => item.valid_payload !== true).length,
                perTargetWrite: perTargetRecapture,
                reason: 'stable_hash_output_missing',
                controlledError: `FETCHER_STABLE_HASH_OUTPUT_MISSING:${entry.external_id}`,
            });
        }

        if (entry.hash_matches_baseline !== true) {
            const hashGate = buildHashGateResult(perTargetRecapture, targetRegistry.length);
            return buildControlledRemainingWriteResult({
                input: value,
                executionCompleted: false,
                targetCount: targetRegistry.length,
                attemptedTargetCount: hashGate.attemptedTargetCount,
                validPayloadCount: hashGate.validPayloadCount,
                hashMatchCount: hashGate.hashMatchCount,
                hashDriftCount: hashGate.hashDriftCount,
                invalidPayloadCount: hashGate.invalidPayloadCount,
                perTargetWrite: perTargetRecapture,
                reason: 'hash_drift',
                controlledError: `RAW_DATA_HASH_DRIFT:${entry.external_id}: computed ${entry.raw_data_hash} differs from baseline ${entry.baseline_raw_data_hash}`,
            });
        }
    }

    const hashGate = buildHashGateResult(perTargetRecapture, targetRegistry.length);
    if (!hashGate.ok) {
        return buildControlledRemainingWriteResult({
            input: value,
            executionCompleted: false,
            targetCount: targetRegistry.length,
            attemptedTargetCount: hashGate.attemptedTargetCount,
            validPayloadCount: hashGate.validPayloadCount,
            hashMatchCount: hashGate.hashMatchCount,
            hashDriftCount: hashGate.hashDriftCount,
            invalidPayloadCount: hashGate.invalidPayloadCount,
            perTargetWrite: perTargetRecapture,
            reason: 'hash_gate_failed',
            controlledError: 'HASH_GATE_FAILED',
        });
    }

    const rowsToInsert = buildInsertRawMatchDataRows(perTargetRecapture, nowUtcIso(dependencies), value.dataVersion);
    let connection = null;
    const transaction = {
        began: false,
        committed: false,
        rolled_back: false,
    };

    try {
        connection = await acquireDbConnection(dependencies);
        await connection.client.query('BEGIN');
        transaction.began = true;

        const targetMatchRows =
            dependencies.targetMatchRowsOverride || (await selectTargetMatches(connection.client, targetRegistry));
        const targetErrors = validateTargetMatchRows(targetMatchRows, targetRegistry);
        if (targetErrors.length > 0) {
            await connection.client.query('ROLLBACK');
            transaction.rolled_back = true;
            return buildControlledRemainingWriteResult({
                input: value,
                executionCompleted: false,
                targetCount: targetRegistry.length,
                attemptedTargetCount: hashGate.attemptedTargetCount,
                validPayloadCount: hashGate.validPayloadCount,
                hashMatchCount: hashGate.hashMatchCount,
                hashDriftCount: hashGate.hashDriftCount,
                invalidPayloadCount: hashGate.invalidPayloadCount,
                perTargetWrite: perTargetRecapture,
                transaction,
                reason: 'target_match_validation_failed',
                controlledError: `TARGET_MATCH_VALIDATION_FAILED:${targetErrors.join('; ')}`,
            });
        }

        const existingRawRows =
            dependencies.existingRawRowsOverride ||
            (await selectExistingRawMatchData(connection.client, targetRegistry, value.dataVersion));
        if (!Array.isArray(existingRawRows)) {
            await connection.client.query('ROLLBACK');
            transaction.rolled_back = true;
            return buildControlledRemainingWriteResult({
                input: value,
                executionCompleted: false,
                targetCount: targetRegistry.length,
                attemptedTargetCount: hashGate.attemptedTargetCount,
                validPayloadCount: hashGate.validPayloadCount,
                hashMatchCount: hashGate.hashMatchCount,
                hashDriftCount: hashGate.hashDriftCount,
                invalidPayloadCount: hashGate.invalidPayloadCount,
                perTargetWrite: perTargetRecapture,
                transaction,
                reason: 'existing_raw_query_invalid',
                controlledError: 'EXISTING_RAW_MATCH_DATA_QUERY_INVALID',
            });
        }

        if (existingRawRows.length > 0) {
            const existingByExternalId = new Map(existingRawRows.map(row => [normalizeText(row.external_id), row]));
            const blockedPerTarget = perTargetRecapture.map(entry => {
                const existing = existingByExternalId.get(entry.external_id);
                if (!existing) return entry;
                return {
                    ...entry,
                    existing_raw_match_data_found: true,
                    decision:
                        normalizeText(existing.data_hash).toLowerCase() ===
                        normalizeText(entry.raw_data_hash).toLowerCase()
                            ? 'existing_row_conflict_same_hash'
                            : 'existing_row_conflict_different_hash',
                };
            });
            await connection.client.query('ROLLBACK');
            transaction.rolled_back = true;
            return buildControlledRemainingWriteResult({
                input: value,
                executionCompleted: false,
                targetCount: targetRegistry.length,
                attemptedTargetCount: hashGate.attemptedTargetCount,
                validPayloadCount: hashGate.validPayloadCount,
                hashMatchCount: hashGate.hashMatchCount,
                hashDriftCount: hashGate.hashDriftCount,
                invalidPayloadCount: hashGate.invalidPayloadCount,
                existingRawMatchDataCount: existingRawRows.length,
                perTargetWrite: blockedPerTarget,
                transaction,
                reason: 'existing_raw_match_data_found',
                controlledError: `EXISTING_RAW_MATCH_DATA_FOUND:${existingRawRows
                    .map(row => `${row.external_id}:${row.data_hash}`)
                    .join(', ')}`,
            });
        }

        const preWriteBaseline =
            dependencies.preWriteBaselineOverride || (await selectProtectedTableBaseline(connection.client));
        const preWriteBaselineErrors = validateBaselineExact(preWriteBaseline, EXPECTED_PRE_WRITE_BASELINE);
        if (preWriteBaselineErrors.length > 0) {
            await connection.client.query('ROLLBACK');
            transaction.rolled_back = true;
            return buildControlledRemainingWriteResult({
                input: value,
                executionCompleted: false,
                targetCount: targetRegistry.length,
                attemptedTargetCount: hashGate.attemptedTargetCount,
                validPayloadCount: hashGate.validPayloadCount,
                hashMatchCount: hashGate.hashMatchCount,
                hashDriftCount: hashGate.hashDriftCount,
                invalidPayloadCount: hashGate.invalidPayloadCount,
                perTargetWrite: perTargetRecapture,
                transaction,
                reason: 'pre_write_baseline_mismatch',
                controlledError: `PRE_WRITE_BASELINE_MISMATCH:${preWriteBaselineErrors.join('; ')}`,
            });
        }

        for (const row of rowsToInsert) {
            const insertSql = buildInsertRawMatchDataSql(row);
            await connection.client.query(insertSql.text, insertSql.values);
        }

        const insertedRowsMetadata =
            dependencies.insertedRowsMetadataOverride ||
            (await selectInsertedRowsMetadata(connection.client, targetRegistry, value.dataVersion));
        const insertedRowErrors = validateInsertedRows(insertedRowsMetadata, targetRegistry, value.dataVersion);
        const postWriteBaseline =
            dependencies.postWriteBaselineOverride || (await selectProtectedTableBaseline(connection.client));
        const postWriteBaselineErrors = validateBaselineExact(postWriteBaseline, EXPECTED_POST_WRITE_BASELINE);
        const verificationErrors = [...insertedRowErrors, ...postWriteBaselineErrors];

        if (verificationErrors.length > 0) {
            await connection.client.query('ROLLBACK');
            transaction.rolled_back = true;
            return buildControlledRemainingWriteResult({
                input: value,
                executionCompleted: false,
                targetCount: targetRegistry.length,
                attemptedTargetCount: hashGate.attemptedTargetCount,
                validPayloadCount: hashGate.validPayloadCount,
                hashMatchCount: hashGate.hashMatchCount,
                hashDriftCount: hashGate.hashDriftCount,
                invalidPayloadCount: hashGate.invalidPayloadCount,
                perTargetWrite: perTargetRecapture,
                transaction,
                reason: 'post_write_verification_failed',
                controlledError: `POST_WRITE_VERIFICATION_FAILED:${verificationErrors.join('; ')}`,
            });
        }

        await connection.client.query('COMMIT');
        transaction.committed = true;

        const successPerTarget = perTargetRecapture.map(entry => ({
            ...entry,
            existing_raw_match_data_found: false,
            decision: 'inserted',
        }));

        return buildControlledRemainingWriteResult({
            input: value,
            executionCompleted: true,
            targetCount: targetRegistry.length,
            attemptedTargetCount: hashGate.attemptedTargetCount,
            validPayloadCount: hashGate.validPayloadCount,
            hashMatchCount: hashGate.hashMatchCount,
            hashDriftCount: hashGate.hashDriftCount,
            invalidPayloadCount: hashGate.invalidPayloadCount,
            existingRawMatchDataCount: 0,
            insertedCount: targetRegistry.length,
            updatedCount: 0,
            skippedCount: 0,
            rawMatchDataWriteExecuted: true,
            dbWriteExecuted: true,
            matchesWriteExecuted: false,
            parserFeaturesExecuted: false,
            trainingExecuted: false,
            predictionExecuted: false,
            perTargetWrite: successPerTarget,
            transaction,
            postWriteVerification: buildPostWriteVerification(postWriteBaseline),
            insertedRowsMetadata,
        });
    } catch (error) {
        if (transaction.began && transaction.committed !== true && transaction.rolled_back !== true) {
            try {
                await connection.client.query('ROLLBACK');
                transaction.rolled_back = true;
            } catch (rollbackError) {
                error.rollback_error = rollbackError.message;
            }
        }
        return buildControlledRemainingWriteResult({
            input: value,
            executionCompleted: false,
            targetCount: targetRegistry.length,
            attemptedTargetCount: hashGate.attemptedTargetCount,
            validPayloadCount: hashGate.validPayloadCount,
            hashMatchCount: hashGate.hashMatchCount,
            hashDriftCount: hashGate.hashDriftCount,
            invalidPayloadCount: hashGate.invalidPayloadCount,
            perTargetWrite: perTargetRecapture,
            transaction,
            reason: 'controlled_write_error',
            controlledError: String(error.message || error),
        });
    } finally {
        if (connection) {
            await connection.release();
            await connection.cleanupPool();
        }
    }
}

function usage() {
    return [
        'Usage:',
        '  node scripts/ops/l2_remaining_raw_match_data_write.js \\',
        '    --source=fotmob --league-id=53 --season=2025/2026 --date=2026-05-10 \\',
        '    --route=html_hydration \\',
        '    --remaining-external-ids=4830747,4830748,4830750,4830751,4830752,4830753,4830754 \\',
        '    --expected-target-count=7 \\',
        '    --hash-strategy=stable_raw_payload_v1 \\',
        '    --baseline-raw-data-hashes=4830747:8dfc7faaf236ee9f8090301cce9dede32a11ed5b66f2a89e1b3324064f788b25,4830748:538fc2c33281f65d56f5fc004378e5933c0d3bbabc81d8e640bcb7abb4ad9bc3,4830750:c04915c0e972566f56bcb88a004f9e7e282777f9ca512c626a6acd4bd05e7304,4830751:5c603f83265887f223776941dde430e7abc8b8b9a9577d649cfd149339ffbd37,4830752:241e21be67a3f854d3320bbe86857a19c4bc357b6647d8b798df9b2dec6f56d6,4830753:358466958ec7b60b4dfa5e847537391b85153a564300804636497dd683311567,4830754:3a0832dc6bc16892491c11905ad8ab2fd80e4b29ea2f0aaa71d5659e57785c30 \\',
        '    --data-version=fotmob_html_hyd_v1 \\',
        '    --network-authorization=yes --live-preview-authorization=yes --final-db-write-confirmation=yes \\',
        '    --allow-db-write=yes --allow-raw-match-data-write=yes --allow-matches-write=no \\',
        '    --allow-parser-features=no --allow-training=no --allow-prediction=no \\',
        '    --concurrency=1 --retry=0 --print-body=no --save-body=no',
        '',
        'Safety:',
        '  Phase 5.20L2F performs one controlled recapture pass for the remaining 7 targets,',
        '  compares every stable raw_data_hash with stable_raw_payload_v1 baselines,',
        '  and writes only raw_match_data inside one transaction.',
    ].join('\n');
}

async function runCli(argv = process.argv.slice(2), io = {}, dependencies = {}) {
    const stdout = io.stdout || process.stdout.write.bind(process.stdout);
    const args = parseArgs(argv);
    if (args.help) {
        stdout(`${usage()}\n`);
        return 0;
    }

    const result = await executeRemainingRawMatchDataWrite(args, dependencies);
    stdout(`${JSON.stringify(result, null, 2)}\n`);
    return result.execution_completed ? 0 : 1;
}

if (require.main === module) {
    runCli()
        .then(status => {
            process.exitCode = status;
        })
        .catch(error => {
            process.stdout.write(
                `${JSON.stringify(
                    buildControlledRemainingWriteResult({
                        input: {},
                        executionCompleted: false,
                        controlledError: String(error.message || error),
                    }),
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
    parseRemainingExternalIds,
    parseBaselineRawDataHashes,
    validateWriteInput,
    getRemainingTargetRegistry,
    buildPerTargetRecapture,
    buildHashGateResult,
    buildInsertRawMatchDataRows,
    buildPostWriteVerification,
    executeRemainingRawMatchDataWrite,
    buildControlledRemainingWriteResult,
    runCli,
};
