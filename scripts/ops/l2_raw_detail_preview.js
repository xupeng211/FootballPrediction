#!/usr/bin/env node
/* eslint-disable complexity */
'use strict';

const crypto = require('node:crypto');
const { extractFromHtml, transformToApiFormat } = require('../../src/parsers/fotmob/NextDataParser');
const { createFotMobDetailRouteSelector } = require('../../src/infrastructure/services/FotMobDetailRouteSelector');

const PHASE = 'PHASE5_12L2B_SAFE_FOTMOB_DETAIL_ROUTE_SELECTOR';
const NEXT_REQUIRED_PHASE = 'Phase 5.12L2C controlled raw detail preview via audited route selector';
const DEFAULT_TIMEOUT_MS = 20000;
const FOTMOB_BASE_URL = 'https://www.fotmob.com';
const FOTMOB_DETAIL_URL = 'https://www.fotmob.com/api/data/matchDetails';
const FOTMOB_ALTERNATE_DETAIL_URL = 'https://www.fotmob.com/api/matchDetails';
const TARGET = Object.freeze({
    source: 'fotmob',
    matchId: '53_20252026_4830746',
    externalId: '4830746',
    homeTeam: 'Angers',
    awayTeam: 'Strasbourg',
});
const ROUTES = Object.freeze({
    AUTO: 'auto',
    HTML_HYDRATION: 'html_hydration',
    API_MATCH_DETAILS: 'api_match_details',
    ALTERNATE_ROUTE: 'alternate_route',
});
const EXECUTABLE_ROUTES = new Set([ROUTES.HTML_HYDRATION, ROUTES.API_MATCH_DETAILS]);
const BLOCK_SIGNAL_PATTERNS = Object.freeze([
    /captcha/i,
    /cloudflare/i,
    /cf-challenge/i,
    /access denied/i,
    /too many requests/i,
    /rate limit/i,
]);
const CANDIDATE_KEYS = new Set([
    'content',
    'general',
    'header',
    'lineup',
    'matchFacts',
    'matchDetails',
    'stats',
    'shotmap',
    'teamColors',
    'teams',
]);

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
    return Number.parseInt(normalized, 10);
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
        matchId: null,
        externalId: null,
        homeTeam: null,
        awayTeam: null,
        route: ROUTES.AUTO,
        networkAuthorization: null,
        livePreviewAuthorization: null,
        allowDbWrite: null,
        allowRawMatchDataWrite: null,
        allowBrowserRuntime: null,
        allowProxyRuntime: null,
        concurrency: null,
        retry: null,
        printBody: null,
        saveBody: null,
        bulk: false,
        help: false,
        unknown: [],
    };
    const keyMap = {
        source: 'source',
        'match-id': 'matchId',
        match_id: 'matchId',
        'external-id': 'externalId',
        external_id: 'externalId',
        'home-team': 'homeTeam',
        home_team: 'homeTeam',
        'away-team': 'awayTeam',
        away_team: 'awayTeam',
        route: 'route',
        'network-authorization': 'networkAuthorization',
        network_authorization: 'networkAuthorization',
        'live-preview-authorization': 'livePreviewAuthorization',
        live_preview_authorization: 'livePreviewAuthorization',
        'allow-db-write': 'allowDbWrite',
        allow_db_write: 'allowDbWrite',
        'allow-raw-match-data-write': 'allowRawMatchDataWrite',
        allow_raw_match_data_write: 'allowRawMatchDataWrite',
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
        help: 'help',
        h: 'help',
    };

    for (let index = 0; index < argv.length; index += 1) {
        const arg = argv[index];
        if (!String(arg).startsWith('--')) {
            options.unknown.push(String(arg));
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

        if (
            [
                'networkAuthorization',
                'livePreviewAuthorization',
                'allowDbWrite',
                'allowRawMatchDataWrite',
                'allowBrowserRuntime',
                'allowProxyRuntime',
                'printBody',
                'saveBody',
                'bulk',
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

function normalizeText(value) {
    return String(value || '').trim();
}

function includesText(value, expected) {
    return normalizeText(value).toLowerCase().includes(normalizeText(expected).toLowerCase());
}

function pushRequiredBooleanError(errors, value, flagName, expected) {
    if (value === expected) {
        return;
    }
    if (value === true) {
        errors.push(`${flagName}=yes is blocked in Phase 5.12L2B`);
        return;
    }
    if (value === false) {
        errors.push(`${flagName}=no is required in Phase 5.12L2B`);
        return;
    }
    errors.push(`missing ${flagName}=${expected ? 'yes' : 'no'}`);
}

function normalizePreviewInput(input = {}) {
    return {
        source: normalizeText(input.source).toLowerCase(),
        matchId: normalizeText(input.matchId),
        externalId: normalizeText(input.externalId),
        homeTeam: normalizeText(input.homeTeam),
        awayTeam: normalizeText(input.awayTeam),
        route: normalizeText(input.route || ROUTES.AUTO).toLowerCase(),
        networkAuthorization: normalizeBooleanFlag(
            input.networkAuthorization,
            normalizeBooleanFlag(process.env.NETWORK_AUTHORIZATION, false)
        ),
        livePreviewAuthorization: normalizeBooleanFlag(
            input.livePreviewAuthorization,
            normalizeBooleanFlag(process.env.LIVE_PREVIEW_AUTHORIZATION, false)
        ),
        allowDbWrite: normalizeBooleanFlag(input.allowDbWrite, undefined),
        allowRawMatchDataWrite: normalizeBooleanFlag(input.allowRawMatchDataWrite, undefined),
        allowBrowserRuntime: normalizeBooleanFlag(input.allowBrowserRuntime, undefined),
        allowProxyRuntime: normalizeBooleanFlag(input.allowProxyRuntime, undefined),
        concurrency: parseInteger(input.concurrency, null),
        retry: parseInteger(input.retry, null),
        printBody: normalizeBooleanFlag(input.printBody, undefined),
        saveBody: normalizeBooleanFlag(input.saveBody, undefined),
        bulk: normalizeBooleanFlag(input.bulk, false),
        unknown: Array.isArray(input.unknown) ? input.unknown : [],
    };
}

function validatePreviewInput(input = {}) {
    const value = normalizePreviewInput(input);
    const errors = [];

    if (value.unknown.length > 0) {
        errors.push(`unknown arguments: ${value.unknown.join(', ')}`);
    }
    if (!value.source) {
        errors.push('missing source: provide --source=fotmob');
    } else if (value.source !== TARGET.source) {
        errors.push('unsupported source: only fotmob is allowed');
    }
    if (!value.matchId) {
        errors.push('missing match-id');
    } else if (value.matchId !== TARGET.matchId) {
        errors.push(`match-id must be ${TARGET.matchId} in Phase 5.12L2B`);
    }
    if (!value.externalId) {
        errors.push('missing external-id');
    } else if (value.externalId !== TARGET.externalId) {
        errors.push(`external-id must be ${TARGET.externalId} in Phase 5.12L2B`);
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
    if (![ROUTES.AUTO, ROUTES.HTML_HYDRATION, ROUTES.API_MATCH_DETAILS].includes(value.route)) {
        errors.push(`unsupported route: use ${ROUTES.AUTO}, ${ROUTES.HTML_HYDRATION}, or ${ROUTES.API_MATCH_DETAILS}`);
    }

    pushRequiredBooleanError(errors, value.allowDbWrite, 'allow-db-write', false);
    pushRequiredBooleanError(errors, value.allowRawMatchDataWrite, 'allow-raw-match-data-write', false);
    pushRequiredBooleanError(errors, value.allowBrowserRuntime, 'allow-browser-runtime', false);
    pushRequiredBooleanError(errors, value.allowProxyRuntime, 'allow-proxy-runtime', false);
    pushRequiredBooleanError(errors, value.printBody, 'print-body', false);
    pushRequiredBooleanError(errors, value.saveBody, 'save-body', false);

    if (value.concurrency !== 1) {
        errors.push(value.concurrency > 1 ? 'concurrency > 1 is blocked' : 'concurrency must be 1');
    }
    if (value.retry !== 0) {
        errors.push(value.retry > 0 ? 'retry > 0 is blocked' : 'retry must be 0');
    }
    if (value.bulk === true) {
        errors.push('bulk=yes is blocked in Phase 5.12L2B');
    }

    return {
        ok: errors.length === 0,
        errors,
        value,
    };
}

function buildFotMobPageRequest(input = {}) {
    const validation = validatePreviewInput(input);
    if (!validation.ok) {
        throw new Error(`INVALID_PREVIEW_INPUT:${validation.errors.join('; ')}`);
    }

    const url = new URL(`/match/${validation.value.externalId}`, FOTMOB_BASE_URL);

    return {
        route: ROUTES.HTML_HYDRATION,
        method: 'GET',
        url: url.href,
        headers: {
            accept: 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'accept-language': 'en-US,en;q=0.9',
            'accept-encoding': 'identity',
            referer: FOTMOB_BASE_URL,
            'user-agent':
                'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
        },
    };
}

function buildFotMobDetailRequest(input = {}) {
    const validation = validatePreviewInput(input);
    if (!validation.ok) {
        throw new Error(`INVALID_PREVIEW_INPUT:${validation.errors.join('; ')}`);
    }

    const url = new URL(FOTMOB_DETAIL_URL);
    url.searchParams.set('matchId', validation.value.externalId);

    return {
        route: ROUTES.API_MATCH_DETAILS,
        method: 'GET',
        url: url.href,
        headers: {
            accept: 'application/json, text/plain, */*',
            'accept-language': 'en-US,en;q=0.9',
            'accept-encoding': 'identity',
            referer: `https://www.fotmob.com/match/${validation.value.externalId}`,
            'user-agent':
                'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
            'x-requested-with': 'XMLHttpRequest',
        },
    };
}

function buildAlternateRoutePlan(input = {}) {
    const validation = validatePreviewInput(input);
    if (!validation.ok) {
        throw new Error(`INVALID_PREVIEW_INPUT:${validation.errors.join('; ')}`);
    }

    const url = new URL(FOTMOB_ALTERNATE_DETAIL_URL);
    url.searchParams.set('matchId', validation.value.externalId);

    return {
        route: ROUTES.ALTERNATE_ROUTE,
        method: 'GET',
        url: url.href,
        headers: {
            accept: 'application/json, text/plain, */*',
            'accept-language': 'en-US,en;q=0.9',
            'accept-encoding': 'identity',
            referer: buildFotMobPageRequest(input).url,
            'user-agent':
                'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
            'x-requested-with': 'XMLHttpRequest',
        },
        plan_only: true,
    };
}

function resolveRouteOrder(route = ROUTES.AUTO) {
    if (route === ROUTES.HTML_HYDRATION) {
        return [ROUTES.HTML_HYDRATION];
    }
    if (route === ROUTES.API_MATCH_DETAILS) {
        return [ROUTES.API_MATCH_DETAILS];
    }
    return [ROUTES.HTML_HYDRATION, ROUTES.API_MATCH_DETAILS];
}

function buildRequestForRoute(route, input = {}) {
    if (route === ROUTES.HTML_HYDRATION) {
        return buildFotMobPageRequest(input);
    }
    if (route === ROUTES.API_MATCH_DETAILS) {
        return buildFotMobDetailRequest(input);
    }
    if (route === ROUTES.ALTERNATE_ROUTE) {
        return buildAlternateRoutePlan(input);
    }
    throw new Error(`UNSUPPORTED_ROUTE:${route}`);
}

function buildFotMobDetailRoutePlan(input = {}) {
    const validation = validatePreviewInput(input);
    if (!validation.ok) {
        throw new Error(`INVALID_PREVIEW_INPUT:${validation.errors.join('; ')}`);
    }

    const executableRouteOrder = resolveRouteOrder(validation.value.route);
    const plannedRoutes = [...executableRouteOrder, ROUTES.ALTERNATE_ROUTE];
    return plannedRoutes.map(route => ({
        route,
        request: buildRequestForRoute(route, input),
        executable: EXECUTABLE_ROUTES.has(route),
        plan_only: route === ROUTES.ALTERNATE_ROUTE,
    }));
}

function getObjectKeys(value) {
    if (!value || typeof value !== 'object' || Array.isArray(value)) {
        return [];
    }
    return Object.keys(value).sort();
}

function collectCandidatePaths(value, prefix = '', paths = new Set(), depth = 0) {
    if (!value || typeof value !== 'object' || depth > 5) {
        return paths;
    }

    for (const key of Object.keys(value)) {
        const nextPath = prefix ? `${prefix}.${key}` : key;
        if (CANDIDATE_KEYS.has(key)) {
            paths.add(nextPath);
        }
        collectCandidatePaths(value[key], nextPath, paths, depth + 1);
    }

    return paths;
}

function parseJsonPayload(bodyText) {
    try {
        return {
            ok: true,
            value: JSON.parse(bodyText),
        };
    } catch (error) {
        return {
            ok: false,
            error: error.message,
            value: null,
        };
    }
}

function detectBlockSignals(bodyText, httpStatus = null) {
    const signals = [];
    if ([403, 429].includes(Number(httpStatus))) {
        signals.push(`HTTP_${httpStatus}`);
    }
    for (const pattern of BLOCK_SIGNAL_PATTERNS) {
        if (pattern.test(bodyText)) {
            signals.push(pattern.source.replace(/\\/g, ''));
        }
    }
    return [...new Set(signals)].sort();
}

function extractJsonOrHydrationPreview(body, contentType = '', context = {}) {
    const bodyText = String(body || '');
    const markers = [];
    const candidatePaths = new Set();
    const contentTypeText = String(contentType || '').toLowerCase();
    const likelyJson = contentTypeText.includes('json') || /^[\s\n\r]*[{[]/.test(bodyText);
    let jsonParseOk = false;
    let hydrationParseOk = false;
    let hydrationTransformOk = false;
    let parseError = null;
    let parsedRoot = null;

    if (likelyJson) {
        const parsed = parseJsonPayload(bodyText);
        jsonParseOk = parsed.ok;
        if (parsed.ok) {
            parsedRoot = parsed.value;
            markers.push('json');
            collectCandidatePaths(parsed.value, '', candidatePaths);
        } else {
            parseError = parsed.error;
        }
    }

    if (bodyText.includes('__NEXT_DATA__')) {
        markers.push('__NEXT_DATA__');
        const nextData = extractFromHtml(bodyText);
        hydrationParseOk = nextData.success === true;
        if (hydrationParseOk) {
            const transformedData = transformToApiFormat(
                nextData.data,
                String(context.externalId || TARGET.externalId)
            );
            hydrationTransformOk = Boolean(transformedData);
            parsedRoot = transformedData || nextData.data;
            markers.push('next_data_parser');
            if (transformedData) {
                markers.push('transformed_api_format');
                collectCandidatePaths(transformedData, '', candidatePaths);
            }
            collectCandidatePaths(nextData.data, '__NEXT_DATA__', candidatePaths);
        } else {
            parseError = nextData.error || 'NEXT_DATA_PARSE_FAILED';
        }
    }

    const topLevelKeys = getObjectKeys(parsedRoot);
    const containsMatchId = bodyText.includes(String(context.externalId || TARGET.externalId));
    const containsHomeTeam = includesText(bodyText, context.homeTeam || TARGET.homeTeam);
    const containsAwayTeam = includesText(bodyText, context.awayTeam || TARGET.awayTeam);
    const blockSignals = detectBlockSignals(bodyText, context.httpStatus);
    const hasExpectedStructure = [...candidatePaths].some(path =>
        /(content|general|header|matchDetails|matchFacts|lineup|stats)/i.test(path)
    );

    return {
        contains_match_id: containsMatchId,
        contains_home_team: containsHomeTeam,
        contains_away_team: containsAwayTeam,
        json_parse_ok: jsonParseOk,
        hydration_parse_ok: hydrationParseOk,
        hydration_transform_ok: hydrationTransformOk,
        hydration_or_json_markers: [...new Set(markers)].sort(),
        top_level_keys: topLevelKeys,
        candidate_raw_data_paths: [...candidatePaths].sort().slice(0, 30),
        block_signals: blockSignals,
        parse_error: parseError,
        looks_like_valid_match_detail:
            blockSignals.length === 0 && containsMatchId && (jsonParseOk || hydrationParseOk) && hasExpectedStructure,
    };
}

function getHeaderValue(headers, name) {
    if (!headers) {
        return '';
    }
    if (typeof headers.get === 'function') {
        return String(headers.get(name) || '');
    }
    const targetName = String(name).toLowerCase();
    const foundKey = Object.keys(headers).find(key => key.toLowerCase() === targetName);
    return foundKey ? String(headers[foundKey] || '') : '';
}

function sha256(bodyText) {
    return crypto
        .createHash('sha256')
        .update(String(bodyText || ''), 'utf8')
        .digest('hex');
}

function buildRawDetailPreviewSummary({ input, request, response = {}, body = '', extraction = null, error = null }) {
    const normalized = normalizePreviewInput(input);
    const bodyText = String(body || '');
    const httpStatus = Number(response.status || response.statusCode || 0) || null;
    const contentType = getHeaderValue(response.headers, 'content-type');
    const preview =
        extraction ||
        extractJsonOrHydrationPreview(bodyText, contentType, {
            externalId: normalized.externalId,
            homeTeam: normalized.homeTeam,
            awayTeam: normalized.awayTeam,
            httpStatus,
        });
    const controlledError = error
        ? String(error.message || error)
        : preview.block_signals.length > 0
          ? `CONTROLLED_BLOCK_SIGNAL:${preview.block_signals.join(',')}`
          : null;
    const isHttpOk = httpStatus !== null && httpStatus >= 200 && httpStatus < 300;
    const ok = !controlledError && isHttpOk && preview.looks_like_valid_match_detail;

    return {
        phase: PHASE,
        preview_only: true,
        source: TARGET.source,
        match_id: TARGET.matchId,
        external_id: TARGET.externalId,
        home_team: TARGET.homeTeam,
        away_team: TARGET.awayTeam,
        network_authorization_used: normalized.networkAuthorization === true,
        external_network_used: error ? false : true,
        request_url: request?.url || '',
        final_url: response.url || request?.url || '',
        http_status: httpStatus,
        ok,
        controlled_error: controlledError,
        content_type: contentType,
        body_byte_length: Buffer.byteLength(bodyText, 'utf8'),
        body_sha256: sha256(bodyText),
        contains_match_id: preview.contains_match_id,
        contains_home_team: preview.contains_home_team,
        contains_away_team: preview.contains_away_team,
        looks_like_valid_match_detail: preview.looks_like_valid_match_detail,
        json_parse_ok: preview.json_parse_ok,
        hydration_parse_ok: preview.hydration_parse_ok,
        hydration_transform_ok: preview.hydration_transform_ok,
        hydration_or_json_markers: preview.hydration_or_json_markers,
        top_level_keys: preview.top_level_keys,
        candidate_raw_data_paths: preview.candidate_raw_data_paths,
        route_selector_enabled: false,
        selected_route: request?.route || ROUTES.API_MATCH_DETAILS,
        attempted_routes: [],
        fallback_routes_planned: [],
        existing_client_integration: buildExistingClientIntegrationSummary(),
        raw_match_data_write_allowed: false,
        db_write_allowed: false,
        would_write_raw_match_data: false,
        would_write_db: false,
        would_train: false,
        would_predict: false,
        browser_used: false,
        proxy_used: false,
        body_printed: false,
        body_saved: false,
        next_required_phase: NEXT_REQUIRED_PHASE,
    };
}

async function fetchPreviewBody(request, dependencies = {}) {
    const fetchImpl = dependencies.fetchImpl || global.fetch;
    if (typeof fetchImpl !== 'function') {
        throw new Error('FETCH_UNAVAILABLE: native fetch is not available');
    }

    const timeoutMs = Number(dependencies.requestTimeoutMs || DEFAULT_TIMEOUT_MS);
    const controller = typeof AbortController === 'function' ? new AbortController() : null;
    const timeout = controller
        ? setTimeout(() => {
              controller.abort();
          }, timeoutMs)
        : null;

    try {
        const response = await fetchImpl(request.url, {
            method: request.method,
            headers: request.headers,
            redirect: 'follow',
            signal: controller?.signal,
        });
        const body = typeof response.text === 'function' ? await response.text() : '';
        return {
            response,
            body,
        };
    } finally {
        if (timeout) {
            clearTimeout(timeout);
        }
    }
}

const routeSelector = createFotMobDetailRouteSelector({
    TARGET,
    ROUTES,
    validatePreviewInput,
    normalizePreviewInput,
    buildFotMobDetailRoutePlan,
    fetchPreviewBody,
    extractJsonOrHydrationPreview,
    getHeaderValue,
    sha256,
    PHASE,
    NEXT_REQUIRED_PHASE,
});
const { buildExistingClientIntegrationSummary, runFotMobDetailRouteSelector, buildRouteSelectorPreviewSummary } =
    routeSelector;

function buildValidationFailureSummary(args, errors) {
    return {
        phase: PHASE,
        preview_only: true,
        ok: false,
        errors,
        source: args.source || null,
        match_id: args.matchId || null,
        external_id: args.externalId || null,
        route_selector_enabled: true,
        selected_route: 'none',
        attempted_routes: [],
        fallback_routes_planned: [],
        existing_client_integration: buildExistingClientIntegrationSummary(),
        raw_match_data_write_allowed: false,
        db_write_allowed: false,
        would_write_raw_match_data: false,
        would_write_db: false,
        would_train: false,
        would_predict: false,
        browser_used: false,
        proxy_used: false,
        body_printed: false,
        body_saved: false,
        next_required_phase: NEXT_REQUIRED_PHASE,
    };
}

function usage() {
    return [
        'Usage:',
        '  node scripts/ops/l2_raw_detail_preview.js --source=fotmob --match-id=53_20252026_4830746 --external-id=4830746 --home-team=Angers --away-team=Strasbourg --route=auto --network-authorization=no --live-preview-authorization=no --allow-db-write=no --allow-raw-match-data-write=no --allow-browser-runtime=no --allow-proxy-runtime=no --concurrency=1 --retry=0 --print-body=no --save-body=no',
        '',
        'Safety:',
        '  Phase 5.12L2B is route-selector preview planning by default: no DB write, no raw_match_data write, no browser/proxy, no full body print/save.',
        '  Default route order is html_hydration before api_match_details; alternate_route is plan-only.',
        '  Live external execution remains blocked unless a future phase provides explicit authorization.',
    ].join('\n');
}

async function runCli(argv = process.argv.slice(2), streams = {}, dependencies = {}) {
    const stdout = streams.stdout || (text => process.stdout.write(text));
    const args = parseArgs(argv);

    if (args.help) {
        stdout(`${usage()}\n`);
        return 0;
    }

    const validation = validatePreviewInput(args);
    if (!validation.ok) {
        stdout(`${JSON.stringify(buildValidationFailureSummary(args, validation.errors), null, 2)}\n`);
        return 1;
    }

    try {
        const selectorResult = await runFotMobDetailRouteSelector(validation.value, dependencies);
        const summary = buildRouteSelectorPreviewSummary(validation.value, selectorResult);
        stdout(`${JSON.stringify(summary, null, 2)}\n`);
        return summary.ok ? 0 : 1;
    } catch (error) {
        const selectorResult = {
            ok: false,
            plan_only: true,
            selected_route: 'none',
            attempted_routes: [],
            fallback_routes_planned: [],
            controlled_error: String(error.message || error),
            live_network_used: false,
            existing_client_integration: buildExistingClientIntegrationSummary(),
        };
        const summary = buildRouteSelectorPreviewSummary(validation.value, selectorResult);
        stdout(`${JSON.stringify(summary, null, 2)}\n`);
        return 1;
    }
}

function buildFatalErrorSummary(error) {
    return {
        phase: PHASE,
        preview_only: true,
        ok: false,
        error: error.message,
        route_selector_enabled: true,
        selected_route: 'none',
        attempted_routes: [],
        fallback_routes_planned: [],
        existing_client_integration: buildExistingClientIntegrationSummary(),
        raw_match_data_write_allowed: false,
        db_write_allowed: false,
        would_write_raw_match_data: false,
        would_write_db: false,
        would_train: false,
        would_predict: false,
        browser_used: false,
        proxy_used: false,
        body_printed: false,
        body_saved: false,
        next_required_phase: NEXT_REQUIRED_PHASE,
    };
}

if (require.main === module) {
    runCli()
        .then(status => {
            process.exitCode = status;
        })
        .catch(error => {
            console.error(JSON.stringify(buildFatalErrorSummary(error), null, 2));
            process.exitCode = 1;
        });
}

module.exports = {
    parseArgs,
    normalizeBooleanFlag,
    validatePreviewInput,
    buildFotMobPageRequest,
    buildFotMobDetailRequest,
    buildAlternateRoutePlan,
    buildFotMobDetailRoutePlan,
    extractJsonOrHydrationPreview,
    buildRawDetailPreviewSummary,
    runFotMobDetailRouteSelector,
    buildRouteSelectorPreviewSummary,
    runCli,
};
