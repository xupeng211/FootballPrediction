#!/usr/bin/env node
/* eslint-disable complexity, max-lines */
'use strict';

/**
 * Phase 5.19L2 — remaining raw_match_data acquisition PREFLIGHT.
 *
 * Recaptures the 7 remaining seeded match detail payloads via safe
 * direct html_hydration fetch, computes canonical raw_data and data_hash per
 * target, SELECTs existing raw_match_data rows, and outputs would_insert /
 * would_update / would_skip per target WITHOUT writing the DB.
 */

const { extractFromHtml, transformToApiFormat } = require('../../src/parsers/fotmob/NextDataParser');
const {
    fetchFotMobRawDetail,
    HASH_STRATEGY_STABLE_RAW_PAYLOAD_V1,
    canonicalizeJson,
    buildStableRawPayload,
    buildRawDataFromStablePayload,
    buildFetchMetadata,
    normalizeMatchId,
    sha256CanonicalJson,
    sha256StableRawPayload,
    validateCanonicalRawDataShape,
} = require('../../src/infrastructure/services/FotMobRawDetailFetcher');

const PHASE = 'PHASE5_19L2_REMAINING_RAW_MATCH_DATA_ACQUISITION_PREFLIGHT';
const NEXT_REQUIRED_PHASE = 'Phase 5.20L2 controlled remaining raw_match_data write';

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

const EXPECTED_EXTERNAL_IDS = Object.freeze(REMAINING_TARGET_REGISTRY.map(t => t.external_id));

const EXPECTED_SCOPE = Object.freeze({
    source: 'fotmob',
    leagueId: '53',
    season: '2025/2026',
    date: '2026-05-10',
    route: 'html_hydration',
    dataVersion: 'fotmob_html_hyd_v1',
    targetCount: 7,
});

// ── helpers ──────────────────────────────────────────────────────────────────

function normalizeText(value) {
    return String(value || '').trim();
}

function normalizeBooleanFlag(value, fallback = undefined) {
    if (typeof value === 'boolean') return value;
    if (value === null || value === undefined || value === '') return fallback;
    const trimmed = String(value).trim().toLowerCase();
    if (['1', 'true', 'yes', 'y', 'on'].includes(trimmed)) return true;
    if (['0', 'false', 'no', 'n', 'off'].includes(trimmed)) return false;
    return fallback;
}

function parseInteger(value, fallback = null) {
    if (value === null || value === undefined || value === '') return fallback;
    const clean = String(value).trim();
    if (!/^\d+$/.test(clean)) return Number.NaN;
    return Number.parseInt(clean, 10);
}

function parseRemainingExternalIds(value) {
    if (Array.isArray(value)) return value.map(id => normalizeText(id)).filter(Boolean);
    if (value === null || value === undefined || value === '') return [];
    return String(value)
        .split(',')
        .map(id => normalizeText(id))
        .filter(Boolean);
}

function parseOptionValue(arg, argv, index) {
    if (arg.includes('=')) return { value: arg.slice(arg.indexOf('=') + 1), consumedNext: false };
    const nextArg = argv[index + 1];
    if (typeof nextArg === 'string' && !nextArg.startsWith('--')) return { value: nextArg, consumedNext: true };
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
        networkAuthorization: null,
        livePreviewAuthorization: null,
        allowDbWrite: null,
        allowRawMatchDataWrite: null,
        allowMatchesWrite: null,
        allowParserFeatures: null,
        allowTraining: null,
        allowPrediction: null,
        concurrency: null,
        retry: null,
        printBody: null,
        saveBody: null,
        allowBrowserRuntime: false,
        allowProxyRuntime: false,
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
        'network-authorization': 'networkAuthorization',
        network_authorization: 'networkAuthorization',
        'live-preview-authorization': 'livePreviewAuthorization',
        live_preview_authorization: 'livePreviewAuthorization',
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
        concurrency: 'concurrency',
        retry: 'retry',
        'print-body': 'printBody',
        print_body: 'printBody',
        'save-body': 'saveBody',
        save_body: 'saveBody',
        'allow-browser-runtime': 'allowBrowserRuntime',
        allow_browser_runtime: 'allowBrowserRuntime',
        'allow-proxy-runtime': 'allowProxyRuntime',
        allow_proxy_runtime: 'allowProxyRuntime',
        bulk: 'bulk',
        commit: 'commit',
        execute: 'execute',
        help: 'help',
        h: 'help',
    };
    const booleanKeys = new Set([
        'allowDbWrite',
        'allowRawMatchDataWrite',
        'allowMatchesWrite',
        'allowParserFeatures',
        'allowTraining',
        'allowPrediction',
        'allowBrowserRuntime',
        'allowProxyRuntime',
        'bulk',
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
        if (consumedNext) i += 1;
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

// ── validation ───────────────────────────────────────────────────────────────

function pushRequiredYesError(errors, value, flagName) {
    if (value !== true) errors.push(`${flagName}=yes is required for Phase 5.19L2`);
}

function pushRequiredNoError(errors, value, flagName) {
    if (value === true) {
        errors.push(`${flagName}=yes is blocked in Phase 5.19L2`);
        return;
    }
    if (value !== false) errors.push(`missing ${flagName}=no`);
}

function pushRequiredIntegerError(errors, value, expected, flagName) {
    if (!Number.isFinite(value) || value !== expected) {
        errors.push(`${flagName} must be ${expected} in Phase 5.19L2`);
    }
}

function normalizePreflightInput(input = {}) {
    return {
        source: normalizeText(input.source).toLowerCase(),
        leagueId: normalizeText(input.leagueId),
        season: normalizeText(input.season),
        date: normalizeText(input.date),
        route: normalizeText(input.route).toLowerCase(),
        remainingExternalIds: parseRemainingExternalIds(input.remainingExternalIds),
        expectedTargetCount: parseInteger(input.expectedTargetCount, null),
        networkAuthorization: normalizeBooleanFlag(input.networkAuthorization, undefined),
        livePreviewAuthorization: normalizeBooleanFlag(input.livePreviewAuthorization, undefined),
        allowDbWrite: normalizeBooleanFlag(input.allowDbWrite, undefined),
        allowRawMatchDataWrite: normalizeBooleanFlag(input.allowRawMatchDataWrite, undefined),
        allowMatchesWrite: normalizeBooleanFlag(input.allowMatchesWrite, undefined),
        allowParserFeatures: normalizeBooleanFlag(input.allowParserFeatures, undefined),
        allowTraining: normalizeBooleanFlag(input.allowTraining, undefined),
        allowPrediction: normalizeBooleanFlag(input.allowPrediction, undefined),
        concurrency: parseInteger(input.concurrency, 1),
        retry: parseInteger(input.retry, 0),
        printBody: normalizeBooleanFlag(input.printBody, false),
        saveBody: normalizeBooleanFlag(input.saveBody, false),
        allowBrowserRuntime: normalizeBooleanFlag(input.allowBrowserRuntime, false),
        allowProxyRuntime: normalizeBooleanFlag(input.allowProxyRuntime, false),
        bulk: normalizeBooleanFlag(input.bulk, false),
        commit: normalizeBooleanFlag(input.commit, false),
        execute: normalizeBooleanFlag(input.execute, false),
        unknown: Array.isArray(input.unknown) ? input.unknown : [],
    };
}

function validatePreflightInput(input = {}) {
    const value = normalizePreflightInput(input);
    const errors = [];

    if (value.unknown.length > 0) errors.push(`unknown arguments: ${value.unknown.join(', ')}`);
    if (!value.source || value.source !== EXPECTED_SCOPE.source) errors.push('source must be fotmob');
    if (!value.leagueId || value.leagueId !== EXPECTED_SCOPE.leagueId) errors.push('league-id must be 53');
    if (!value.season || value.season !== EXPECTED_SCOPE.season) errors.push('season must be 2025/2026');
    if (!value.date || value.date !== EXPECTED_SCOPE.date) errors.push('date must be 2026-05-10');
    if (!value.route || value.route !== EXPECTED_SCOPE.route) errors.push('route must be html_hydration');

    const ids = value.remainingExternalIds;
    if (ids.length === 0) {
        errors.push('remaining-external-ids is required');
    } else if (ids.length !== EXPECTED_EXTERNAL_IDS.length) {
        errors.push(`remaining-external-ids must have ${EXPECTED_EXTERNAL_IDS.length} ids`);
    } else {
        const expectedSet = new Set(EXPECTED_EXTERNAL_IDS);
        for (const id of ids) {
            if (!expectedSet.has(id)) errors.push(`unexpected remaining external_id: ${id}`);
            if (id === '4830746') errors.push('4830746 is already ingested');
        }
        for (const id of EXPECTED_EXTERNAL_IDS) {
            if (!ids.includes(id)) errors.push(`missing expected remaining external_id: ${id}`);
        }
    }

    pushRequiredIntegerError(errors, value.expectedTargetCount, EXPECTED_SCOPE.targetCount, 'expected-target-count');
    pushRequiredYesError(errors, value.networkAuthorization, 'network-authorization');
    pushRequiredYesError(errors, value.livePreviewAuthorization, 'live-preview-authorization');
    pushRequiredNoError(errors, value.allowDbWrite, 'allow-db-write');
    pushRequiredNoError(errors, value.allowRawMatchDataWrite, 'allow-raw-match-data-write');
    pushRequiredNoError(errors, value.allowMatchesWrite, 'allow-matches-write');
    pushRequiredNoError(errors, value.allowParserFeatures, 'allow-parser-features');
    pushRequiredNoError(errors, value.allowTraining, 'allow-training');
    pushRequiredNoError(errors, value.allowPrediction, 'allow-prediction');
    pushRequiredIntegerError(errors, value.concurrency, 1, 'concurrency');
    pushRequiredIntegerError(errors, value.retry, 0, 'retry');
    pushRequiredNoError(errors, value.printBody, 'print-body');
    pushRequiredNoError(errors, value.saveBody, 'save-body');
    if (value.allowBrowserRuntime === true) errors.push('allow-browser-runtime=yes is blocked');
    if (value.allowProxyRuntime === true) errors.push('allow-proxy-runtime=yes is blocked');
    if (value.bulk === true) errors.push('bulk=yes is blocked');
    if (value.commit === true) errors.push('commit=yes is blocked');
    if (value.execute === true) errors.push('execute=yes is blocked');

    return { ok: errors.length === 0, errors, value };
}

// ── data recapture (delegates to FotMobRawDetailFetcher) ───────────────────

/**
 * Recapture a single target via FotMobRawDetailFetcher.
 * Maps fetcher output to preflight-compatible shape.
 * @param {object} target - { external_id, home_team, away_team }
 * @param {object} [fetcherDeps] - { fetchFn, now?, parser? }
 * @returns {object} recapture result (snake_case fields for buildPerTargetPreflight)
 */
async function recaptureTarget(target, fetcherDeps = {}) {
    const fetchFn =
        fetcherDeps.fetchFn ||
        (() => {
            throw new Error('FETCH_DEPENDENCY_MISSING: live preflight requires --network-authorization=yes');
        });
    const parser = fetcherDeps.parser || { extractFromHtml, transformToApiFormat };

    const result = await fetchFotMobRawDetail(
        {
            externalId: target.external_id,
            matchId: target.match_id,
            homeTeam: target.home_team,
            awayTeam: target.away_team,
        },
        { fetchFn, parser, now: fetcherDeps.now }
    );

    return {
        request_url: result.request_url,
        final_url: result.final_url,
        http_status: result.http_status,
        content_type: result.content_type,
        body_byte_length: result.body_byte_length,
        body_sha256: result.body_sha256,
        hydration_parse_ok: result.hydration_parse_ok,
        looks_like_valid_match_detail: result.looks_like_valid_match_detail,
        stable_raw_payload: result.stable_raw_payload || null,
        raw_data_hash: result.raw_data_hash || null,
        data_hash: result.data_hash || null,
        stable_raw_payload_hash: result.stable_raw_payload_hash || null,
        raw_data_with_meta_hash: result.raw_data_with_meta_hash || null,
        hash_strategy: result.hash_strategy || HASH_STRATEGY_STABLE_RAW_PAYLOAD_V1,
        match_id_source: result.match_id_source || null,
        fetched_at: result.raw_data?._meta?.fetched_at || null,
        data_version: result.raw_data?._meta?.data_version || null,
        payload: result.raw_data || (result.ok ? {} : null),
        error: result.controlled_error || null,
    };
}

// Kept for backward compatibility with tests
function buildHtmlHydrationRequest(externalId) {
    return require('../../src/infrastructure/services/FotMobRawDetailFetcher').buildFotMobHtmlHydrationRequest(
        externalId
    );
}

// ── canonical data & preflight entry ────────────────────────────────────────

function getRemainingTargetRegistry() {
    return REMAINING_TARGET_REGISTRY.map(t => ({ ...t }));
}

function buildRawDataFromPreviewPayload(preview = {}) {
    const stableRawPayload = buildStableRawPayload(preview, {}, {});
    const matchIdSource = normalizeMatchId(preview, {}, {}).matchIdSource;
    const dataHash = sha256StableRawPayload(stableRawPayload);
    return buildRawDataFromStablePayload(
        stableRawPayload,
        buildFetchMetadata({
            dataHash,
            matchIdSource,
        })
    );
}

function buildPerTargetPreflight(target, recaptureResult, existingRawRow) {
    const fetcherInput = {
        externalId: target.external_id,
        matchId: target.match_id,
        homeTeam: target.home_team,
        awayTeam: target.away_team,
    };
    const sourcePayload =
        recaptureResult.payload &&
        typeof recaptureResult.payload === 'object' &&
        !Array.isArray(recaptureResult.payload)
            ? recaptureResult.payload
            : recaptureResult;
    const originalMatchResolution = normalizeMatchId(sourcePayload, fetcherInput, {
        requestUrl: recaptureResult.request_url,
        finalUrl: recaptureResult.final_url,
    });
    const stableRawPayload =
        recaptureResult.stable_raw_payload &&
        typeof recaptureResult.stable_raw_payload === 'object' &&
        !Array.isArray(recaptureResult.stable_raw_payload)
            ? JSON.parse(JSON.stringify(recaptureResult.stable_raw_payload))
            : buildStableRawPayload(sourcePayload, fetcherInput, {
                  requestUrl: recaptureResult.request_url,
                  finalUrl: recaptureResult.final_url,
              });
    const rawDataHash =
        recaptureResult.raw_data_hash ||
        recaptureResult.data_hash ||
        recaptureResult.stable_raw_payload_hash ||
        sha256StableRawPayload(stableRawPayload);
    const rawData = buildRawDataFromStablePayload(
        stableRawPayload,
        buildFetchMetadata({
            requestedRoute: EXPECTED_SCOPE.route,
            requestUrl: recaptureResult.request_url,
            finalUrl: recaptureResult.final_url,
            httpStatus: recaptureResult.http_status,
            contentType: recaptureResult.content_type,
            bodyByteLength: recaptureResult.body_byte_length,
            bodySha256: recaptureResult.body_sha256,
            dataVersion: recaptureResult.data_version || 'fotmob_html_hyd_v1',
            fetchedAt: recaptureResult.fetched_at || null,
            hasStats: Boolean(stableRawPayload.content?.stats),
            hasLineup: Boolean(stableRawPayload.content?.lineup),
            hasShotmap: Boolean(stableRawPayload.content?.shotmap),
            dataHash: rawDataHash,
            matchIdSource: recaptureResult.match_id_source || originalMatchResolution.matchIdSource,
        })
    );
    const rawDataErrors = validateCanonicalRawDataShape(rawData);
    const dataVersion = recaptureResult.data_version || EXPECTED_SCOPE.dataVersion;

    let decision = 'would_insert';
    let reason = 'no existing raw_match_data row for match_id,data_version';

    if (existingRawRow) {
        if (existingRawRow.data_hash === rawDataHash) {
            decision = 'would_skip';
            reason = 'existing raw_match_data row has identical data_hash';
        } else {
            decision = 'would_update';
            reason = 'existing raw_match_data row has different data_hash';
        }
    }

    return {
        match_id: target.match_id,
        external_id: target.external_id,
        data_version: dataVersion,
        home_team: target.home_team,
        away_team: target.away_team,
        selected_route: EXPECTED_SCOPE.route,
        request_url: recaptureResult.request_url || null,
        final_url: recaptureResult.final_url || null,
        http_status: recaptureResult.http_status,
        content_type: recaptureResult.content_type || null,
        body_byte_length: recaptureResult.body_byte_length || 0,
        body_sha256: recaptureResult.body_sha256 || null,
        hydration_parse_ok: recaptureResult.hydration_parse_ok === true,
        looks_like_valid_match_detail: recaptureResult.looks_like_valid_match_detail === true,
        hash_strategy: recaptureResult.hash_strategy || HASH_STRATEGY_STABLE_RAW_PAYLOAD_V1,
        raw_data_hash: rawDataHash,
        data_hash: rawDataHash,
        stable_raw_payload_hash: rawDataHash,
        raw_data_with_meta_hash: recaptureResult.raw_data_with_meta_hash || null,
        match_id_source: recaptureResult.match_id_source || originalMatchResolution.matchIdSource,
        existing_raw_match_data_found: !!existingRawRow,
        decision,
        reason: rawDataErrors.length > 0 ? `${reason}; ${rawDataErrors.join('; ')}` : reason,
        body_printed: false,
        body_saved: false,
        browser_used: false,
        proxy_used: false,
    };
}

function buildProtectedTableBaseline(baseline) {
    return {
        matches: baseline.matches ?? 10,
        raw_match_data: baseline.raw_match_data ?? 3,
        bookmaker_odds_history: baseline.bookmaker_odds_history ?? 2,
        l3_features: baseline.l3_features ?? 2,
        match_features_training: baseline.match_features_training ?? 2,
        predictions: baseline.predictions ?? 2,
    };
}

// ── plan builders ────────────────────────────────────────────────────────────

function buildInvalidPreflight(input = {}, errors = [], controlledError = null) {
    const value = normalizePreflightInput(input);
    return {
        phase: PHASE,
        preflight_only: true,
        ok: false,
        source: value.source || null,
        league_id: value.leagueId || null,
        season: value.season || null,
        date: value.date || null,
        route: value.route || null,
        hash_strategy: HASH_STRATEGY_STABLE_RAW_PAYLOAD_V1,
        target_count: value.expectedTargetCount || 0,
        attempted_target_count: 0,
        valid_payload_count: 0,
        failed_target_count: 0,
        would_insert_count: 0,
        would_update_count: 0,
        would_skip_count: 0,
        per_target_preflight: [],
        protected_table_baseline: buildProtectedTableBaseline({}),
        plan_only: true,
        live_preflight_used: false,
        db_write_allowed_this_phase: false,
        raw_match_data_write_allowed_this_phase: false,
        matches_write_allowed: false,
        parser_features_allowed: false,
        training_allowed: false,
        prediction_allowed: false,
        would_write_db: false,
        would_write_raw_match_data: false,
        would_parse_features: false,
        would_train: false,
        would_predict: false,
        errors,
        controlled_error: controlledError || `INVALID_PREFLIGHT_INPUT:${errors.join('; ')}`,
        next_required_phase: NEXT_REQUIRED_PHASE,
    };
}

async function buildRemainingRawMatchDataAcquisitionPreflight(input = {}, options = {}) {
    const validation = validatePreflightInput(input);
    if (!validation.ok) return buildInvalidPreflight(input, validation.errors);

    const targetRegistry = getRemainingTargetRegistry();
    const recaptureFn = options.recaptureFn || recaptureTarget;
    const recaptureDeps = options.recaptureDeps || { fetchFn: global.fetch };
    const dbSelectFn = options.dbSelectFn || null;

    const perTarget = [];
    let validCount = 0;
    let failedCount = 0;

    for (const target of targetRegistry) {
        let result;
        try {
            result = await recaptureFn(target, recaptureDeps);
        } catch (err) {
            perTarget.push({
                match_id: target.match_id,
                external_id: target.external_id,
                data_version: EXPECTED_SCOPE.dataVersion,
                home_team: target.home_team,
                away_team: target.away_team,
                selected_route: EXPECTED_SCOPE.route,
                request_url: null,
                final_url: null,
                http_status: 0,
                content_type: null,
                body_byte_length: 0,
                body_sha256: null,
                hydration_parse_ok: false,
                looks_like_valid_match_detail: false,
                raw_data_hash: null,
                existing_raw_match_data_found: false,
                decision: 'failed',
                reason: `recapture error: ${err.message}`,
                body_printed: false,
                body_saved: false,
                browser_used: false,
                proxy_used: false,
            });
            failedCount += 1;
            continue;
        }

        let existingRawRow = null;
        if (dbSelectFn) {
            try {
                existingRawRow = await dbSelectFn({
                    match_id: target.match_id,
                    external_id: target.external_id,
                    data_version: EXPECTED_SCOPE.dataVersion,
                });
            } catch (_) {
                /* non-fatal */
            }
        }

        const entry = buildPerTargetPreflight(target, result, existingRawRow);
        perTarget.push(entry);

        if (entry.hydration_parse_ok && entry.looks_like_valid_match_detail) {
            validCount += 1;
        } else {
            failedCount += 1;
        }
    }

    let baseline = {};
    if (dbSelectFn) {
        try {
            baseline = await dbSelectFn('__baseline__');
        } catch (_) {
            /* ignore */
        }
    }

    return {
        phase: PHASE,
        preflight_only: true,
        ok: true,
        source: EXPECTED_SCOPE.source,
        league_id: EXPECTED_SCOPE.leagueId,
        season: EXPECTED_SCOPE.season,
        date: EXPECTED_SCOPE.date,
        route: EXPECTED_SCOPE.route,
        hash_strategy: HASH_STRATEGY_STABLE_RAW_PAYLOAD_V1,
        target_count: targetRegistry.length,
        attempted_target_count: perTarget.length,
        valid_payload_count: validCount,
        failed_target_count: failedCount,
        would_insert_count: perTarget.filter(e => e.decision === 'would_insert').length,
        would_update_count: perTarget.filter(e => e.decision === 'would_update').length,
        would_skip_count: perTarget.filter(e => e.decision === 'would_skip').length,
        per_target_preflight: perTarget,
        protected_table_baseline: buildProtectedTableBaseline(baseline),
        plan_only: false,
        live_preflight_used: true,
        db_write_allowed_this_phase: false,
        raw_match_data_write_allowed_this_phase: false,
        matches_write_allowed: false,
        parser_features_allowed: false,
        training_allowed: false,
        prediction_allowed: false,
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
        '  node scripts/ops/l2_remaining_raw_match_data_acquisition_preflight.js \\',
        '    --source=fotmob --league-id=53 --season=2025/2026 --date=2026-05-10 \\',
        '    --route=html_hydration \\',
        '    --remaining-external-ids=4830747,4830748,4830750,4830751,4830752,4830753,4830754 \\',
        '    --expected-target-count=7 --network-authorization=yes --live-preview-authorization=yes \\',
        '    --allow-db-write=no --allow-raw-match-data-write=no --allow-matches-write=no \\',
        '    --allow-parser-features=no --allow-training=no --allow-prediction=no \\',
        '    --concurrency=1 --retry=0 --print-body=no --save-body=no',
        '',
        'Safety:',
        '  Phase 5.19L2 is preflight-only: direct html_hydration fetch for 7 targets,',
        '  computes canonical raw_data and hash per target,',
        '  outputs would_insert/update/skip. No DB write. No body save/print.',
    ].join('\n');
}

async function runCli(argv = process.argv.slice(2), streams = {}) {
    const stdout = streams.stdout || (text => process.stdout.write(text));
    const args = parseArgs(argv);

    if (args.help) {
        stdout(`${usage()}\n`);
        return 0;
    }

    const plan = await buildRemainingRawMatchDataAcquisitionPreflight(args);
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
                    buildInvalidPreflight(
                        {},
                        [String(error.message || error)],
                        `UNHANDLED_PHASE5_19L2_ERROR:${error.message}`
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
    canonicalizeJson,
    sha256CanonicalJson,
    validatePreflightInput,
    getRemainingTargetRegistry,
    buildRawDataFromPreviewPayload,
    buildPerTargetPreflight,
    buildProtectedTableBaseline,
    buildRemainingRawMatchDataAcquisitionPreflight,
    recaptureTarget,
    buildHtmlHydrationRequest,
    runCli,
};
