'use strict';

/**
 * FotMobRawDetailFetcher — reusable html_hydration raw detail acquisition.
 *
 * NOT tied to a single external_id. Takes external_id per call.
 * Uses injected fetchFn (default none → fails closed).
 * No DB writes, no browser/proxy, no body save/print.
 */

const crypto = require('node:crypto');

const FOTMOB_BASE_URL = 'https://www.fotmob.com';

// ══════════════════════════════════════════════════════════════════════════════
// URL builder
// ══════════════════════════════════════════════════════════════════════════════

function buildFotMobMatchUrl(externalId) {
    const id = String(externalId || '').trim();
    if (!id || !/^\d+$/.test(id)) {
        throw new Error(`INVALID_EXTERNAL_ID:${externalId}`);
    }
    const url = new URL(`/match/${id}`, FOTMOB_BASE_URL);
    return url.href;
}

function buildFotMobHtmlHydrationRequest(externalId) {
    return {
        route: 'html_hydration',
        method: 'GET',
        url: buildFotMobMatchUrl(externalId),
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

// ══════════════════════════════════════════════════════════════════════════════
// Input / dependency validation
// ══════════════════════════════════════════════════════════════════════════════

// eslint-disable-next-line complexity
function validateFetchInput(input = {}) {
    const errors = [];
    const externalId = String(input.externalId || '').trim();
    if (!externalId || !/^\d+$/.test(externalId)) {
        errors.push('externalId is required and must be numeric');
    }
    if (input.matchId && typeof input.matchId !== 'string') {
        errors.push('matchId must be a string if provided');
    }
    const route = String(input.route || 'html_hydration').trim();
    if (route !== 'html_hydration') {
        errors.push('unsupported route: only html_hydration is supported');
    }
    if (input.printBody === true) {
        errors.push('printBody is blocked');
    }
    if (input.saveBody === true) {
        errors.push('saveBody is blocked');
    }
    if (input.retry > 0) {
        errors.push('retry > 0 is blocked');
    }
    if (input.allowBrowserRuntime === true) {
        errors.push('browser runtime is blocked');
    }
    if (input.allowProxyRuntime === true) {
        errors.push('proxy runtime is blocked');
    }
    return {
        ok: errors.length === 0,
        errors,
        value: {
            source: 'fotmob',
            route: 'html_hydration',
            externalId,
            matchId: input.matchId || null,
            homeTeam: input.homeTeam || null,
            awayTeam: input.awayTeam || null,
            dataVersion: input.dataVersion || 'fotmob_html_hyd_v1',
            requestUrl: input.requestUrl || null,
            printBody: false,
            saveBody: false,
            allowBrowserRuntime: false,
            allowProxyRuntime: false,
            retry: 0,
        },
    };
}

function validateFetchDependencies(dependencies = {}) {
    const fetchFn = dependencies.fetchFn;
    if (typeof fetchFn !== 'function') {
        return {
            ok: false,
            error: 'FETCH_DEPENDENCY_MISSING: fetchFn is required and must be a function',
        };
    }
    return { ok: true };
}

// ══════════════════════════════════════════════════════════════════════════════
// JSON / hash helpers
// ══════════════════════════════════════════════════════════════════════════════

function canonicalizeJson(value) {
    if (value === null || typeof value !== 'object') return value;
    if (Array.isArray(value)) return value.map(canonicalizeJson);
    const sorted = {};
    for (const key of Object.keys(value).sort()) {
        sorted[key] = canonicalizeJson(value[key]);
    }
    return sorted;
}

function sha256Text(text) {
    return crypto
        .createHash('sha256')
        .update(String(text || ''))
        .digest('hex');
}

function sha256CanonicalJson(value) {
    return sha256Text(JSON.stringify(canonicalizeJson(value)));
}

// ══════════════════════════════════════════════════════════════════════════════
// HTML hydration extraction
// ══════════════════════════════════════════════════════════════════════════════

function extractHydrationPayload(html, parserDeps = {}) {
    const extractFn = parserDeps.extractFromHtml;
    const transformFn = parserDeps.transformToApiFormat;

    if (typeof extractFn !== 'function' || typeof transformFn !== 'function') {
        return { ok: false, error: 'PARSER_DEPENDENCY_MISSING' };
    }
    if (!html || typeof html !== 'string') {
        return { ok: false, error: 'EMPTY_HTML' };
    }

    let extracted;
    try {
        extracted = extractFn(html);
    } catch (err) {
        return { ok: false, error: `EXTRACT_ERROR:${err.message}` };
    }

    if (!extracted || extracted.success === false || !extracted.data) {
        return { ok: false, error: 'HYDRATION_PARSE_FAILED: no NextData payload found' };
    }

    let transformed;
    try {
        transformed = transformFn(extracted.data);
    } catch (err) {
        return { ok: false, error: `TRANSFORM_ERROR:${err.message}` };
    }

    if (!transformed || typeof transformed !== 'object') {
        return { ok: false, error: 'TRANSFORM_FAILED: no structured match data' };
    }

    return { ok: true, data: transformed };
}

// ══════════════════════════════════════════════════════════════════════════════
// raw_data construction
// ══════════════════════════════════════════════════════════════════════════════

function buildRawDataFromTransformedPayload(payload, meta) {
    const raw = {};
    if (meta && typeof meta === 'object') raw._meta = { ...meta };
    if (payload.content) raw.content = payload.content;
    if (payload.general) raw.general = payload.general;
    if (payload.header) raw.header = payload.header;
    if (payload.matchId) raw.matchId = payload.matchId;
    return raw;
}

function looksLikeValidRawDetail(rawData, input = {}) {
    if (!rawData || typeof rawData !== 'object') return false;
    const gen = rawData.general || {};
    const externalId = String(input.externalId || '').trim();
    const homeTeam = (input.homeTeam || '').toLowerCase();
    const awayTeam = (input.awayTeam || '').toLowerCase();

    const hasMatchId = !!(gen.matchId || rawData.matchId);
    const matchStr = JSON.stringify(rawData).toLowerCase();
    const containsExternal = !externalId || matchStr.includes(externalId);
    const containsHome = !homeTeam || matchStr.includes(homeTeam);
    const containsAway = !awayTeam || matchStr.includes(awayTeam);

    return hasMatchId && containsExternal && containsHome && containsAway;
}

// ══════════════════════════════════════════════════════════════════════════════
// Core fetch function
// ══════════════════════════════════════════════════════════════════════════════

/**
 * Fetch FotMob raw match detail via html_hydration.
 *
 * @param {object} input - { externalId, matchId?, homeTeam?, awayTeam?, dataVersion?, requestUrl? }
 * @param {object} dependencies - { fetchFn, now?, parser?, logger? }
 * @returns {Promise<object>} unified fetch result
 */
async function fetchFotMobRawDetail(input = {}, dependencies = {}) {
    const inputValidation = validateFetchInput(input);
    if (!inputValidation.ok) {
        return {
            source: 'fotmob',
            route: 'html_hydration',
            external_id: null,
            match_id: null,
            home_team: null,
            away_team: null,
            request_url: null,
            final_url: null,
            http_status: 0,
            ok: false,
            controlled_error: `INVALID_FETCH_INPUT:${inputValidation.errors.join('; ')}`,
            content_type: null,
            body_byte_length: 0,
            body_sha256: null,
            hydration_parse_ok: false,
            transformed_api_format: false,
            raw_data: null,
            raw_data_hash: null,
            contains_external_id: false,
            contains_home_team: false,
            contains_away_team: false,
            looks_like_valid_match_detail: false,
            body_printed: false,
            body_saved: false,
            browser_used: false,
            proxy_used: false,
        };
    }

    const depValidation = validateFetchDependencies(dependencies);
    if (!depValidation.ok) {
        return {
            ...inputValidation.value,
            request_url: null,
            final_url: null,
            http_status: 0,
            ok: false,
            controlled_error: `FETCH_DEPENDENCY_INVALID:${depValidation.error}`,
            content_type: null,
            body_byte_length: 0,
            body_sha256: null,
            hydration_parse_ok: false,
            transformed_api_format: false,
            raw_data: null,
            raw_data_hash: null,
            contains_external_id: false,
            contains_home_team: false,
            contains_away_team: false,
            looks_like_valid_match_detail: false,
            body_printed: false,
            body_saved: false,
            browser_used: false,
            proxy_used: false,
            external_id: inputValidation.value.externalId,
            match_id: inputValidation.value.matchId,
            home_team: inputValidation.value.homeTeam,
            away_team: inputValidation.value.awayTeam,
        };
    }

    const fetchFn = dependencies.fetchFn;
    const parser = dependencies.parser || {};
    const now = dependencies.now || (() => new Date().toISOString());
    const v = inputValidation.value;
    const request = buildFotMobHtmlHydrationRequest(v.externalId);
    const requestUrl = v.requestUrl || request.url;
    const fetchedAt = now();

    let response;
    let body = '';

    try {
        response = await fetchFn(requestUrl, {
            method: request.method,
            headers: request.headers,
            redirect: 'follow',
        });
        body = typeof response.text === 'function' ? await response.text() : '';
    } catch (err) {
        return {
            source: 'fotmob',
            route: 'html_hydration',
            external_id: v.externalId,
            match_id: v.matchId,
            home_team: v.homeTeam,
            away_team: v.awayTeam,
            request_url: requestUrl,
            final_url: requestUrl,
            http_status: 0,
            ok: false,
            controlled_error: `FETCH_ERROR:${err.message}`,
            content_type: null,
            body_byte_length: 0,
            body_sha256: null,
            hydration_parse_ok: false,
            transformed_api_format: false,
            raw_data: null,
            raw_data_hash: null,
            contains_external_id: false,
            contains_home_team: false,
            contains_away_team: false,
            looks_like_valid_match_detail: false,
            body_printed: false,
            body_saved: false,
            browser_used: false,
            proxy_used: false,
        };
    }

    const httpStatus = response ? response.status : 0;
    const finalUrl = (response && response.url) || requestUrl;
    const contentType =
        response && typeof response.headers.get === 'function' ? response.headers.get('content-type') || '' : '';
    const bodyByteLength = Buffer.byteLength(body, 'utf8');
    const bodySha256 = sha256Text(body);
    const fetchedBodySha256 = bodySha256;

    const extraction = extractHydrationPayload(body, parser);

    if (!extraction.ok) {
        return {
            source: 'fotmob',
            route: 'html_hydration',
            external_id: v.externalId,
            match_id: v.matchId,
            home_team: v.homeTeam,
            away_team: v.awayTeam,
            request_url: requestUrl,
            final_url: finalUrl,
            http_status: httpStatus,
            ok: false,
            controlled_error: extraction.error,
            content_type: contentType,
            body_byte_length: bodyByteLength,
            body_sha256: bodySha256,
            hydration_parse_ok: false,
            transformed_api_format: false,
            raw_data: null,
            raw_data_hash: null,
            contains_external_id: false,
            contains_home_team: false,
            contains_away_team: false,
            looks_like_valid_match_detail: false,
            body_printed: false,
            body_saved: false,
            browser_used: false,
            proxy_used: false,
        };
    }

    const meta = {
        source: 'fotmob',
        route: 'html_hydration',
        request_url: requestUrl,
        final_url: finalUrl,
        http_status: httpStatus,
        content_type: contentType,
        body_byte_length: bodyByteLength,
        fetch_body_sha256: fetchedBodySha256,
        parser: 'NextDataParser',
        data_version: v.dataVersion,
        fetched_at: fetchedAt,
    };

    const rawData = buildRawDataFromTransformedPayload(extraction.data, meta);
    const rawDataHash = sha256CanonicalJson(rawData);
    const valid = looksLikeValidRawDetail(rawData, v);

    return {
        source: 'fotmob',
        route: 'html_hydration',
        external_id: v.externalId,
        match_id: v.matchId,
        home_team: v.homeTeam,
        away_team: v.awayTeam,
        request_url: requestUrl,
        final_url: finalUrl,
        http_status: httpStatus,
        ok: true,
        content_type: contentType,
        body_byte_length: bodyByteLength,
        body_sha256: bodySha256,
        hydration_parse_ok: true,
        transformed_api_format: true,
        raw_data: rawData,
        raw_data_hash: rawDataHash,
        contains_external_id: valid,
        contains_home_team: valid,
        contains_away_team: valid,
        looks_like_valid_match_detail: valid,
        body_printed: false,
        body_saved: false,
        browser_used: false,
        proxy_used: false,
    };
}

module.exports = {
    buildFotMobMatchUrl,
    buildFotMobHtmlHydrationRequest,
    validateFetchInput,
    validateFetchDependencies,
    canonicalizeJson,
    sha256Text,
    sha256CanonicalJson,
    extractHydrationPayload,
    buildRawDataFromTransformedPayload,
    looksLikeValidRawDetail,
    fetchFotMobRawDetail,
};
