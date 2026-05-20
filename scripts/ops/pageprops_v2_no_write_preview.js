#!/usr/bin/env node
'use strict';

const crypto = require('node:crypto');
const {
    listJsonPaths: listAuditJsonPaths,
    summarizeJsonShape,
} = require('./raw_match_data_completeness_fidelity_audit');

const PHASE = 'PHASE5_21L2D_PAGEPROPS_V2_NO_WRITE_PREVIEW';
const FOTMOB_BASE_URL = 'https://www.fotmob.com';
const CANDIDATE_VERSION = 'fotmob_pageprops_v2';
const HASH_STRATEGY = 'stable_pageprops_payload_v1';
const SAMPLE_LIMIT = 50;
const TARGET = Object.freeze({
    source: 'fotmob',
    route: 'html_hydration',
    matchId: '53_20252026_4830747',
    externalId: '4830747',
    homeTeam: 'Auxerre',
    awayTeam: 'Nice',
});
const REQUIRED_NO_FLAGS = Object.freeze([
    'allow-db-write',
    'allow-raw-match-data-write',
    'allow-matches-write',
    'allow-parser-features',
    'allow-training',
    'allow-prediction',
    'print-body',
    'save-body',
    'print-full-json',
    'save-full-json',
]);
const BLOCKED_YES_FLAGS = Object.freeze(['allow-browser-runtime', 'allow-proxy-runtime', 'bulk', 'execute', 'commit']);
const MODULE_COMPARISON_PATHS = Object.freeze([
    'content.matchFacts',
    'content.lineup',
    'content.liveticker',
    'content.playerStats',
    'content.shotmap',
    'content.stats',
    'content.h2h',
    'content.table',
    'content.momentum',
    'seo',
    'seo.eventJSONLD',
    'seo.breadcrumbJSONLD',
    'translations',
    'fallback',
    'nav',
    'ongoing',
    'ssr',
    'fetchingLeagueData',
    'hasPendingVAR',
]);

function normalizeText(value) {
    return String(value ?? '').trim();
}

function toKebabKey(key) {
    return normalizeText(key)
        .replace(/[A-Z]/g, char => `-${char.toLowerCase()}`)
        .replace(/^--+/, '');
}

function parseArgs(argv = []) {
    const args = {};
    for (let index = 0; index < argv.length; index += 1) {
        const token = argv[index];
        if (!token.startsWith('--')) continue;
        const raw = token.slice(2);
        const eqIndex = raw.indexOf('=');
        if (eqIndex >= 0) {
            args[toKebabKey(raw.slice(0, eqIndex))] = raw.slice(eqIndex + 1);
            continue;
        }
        const next = argv[index + 1];
        if (next && !next.startsWith('--')) {
            args[toKebabKey(raw)] = next;
            index += 1;
        } else {
            args[toKebabKey(raw)] = 'yes';
        }
    }
    return args;
}

function normalizeBooleanFlag(value) {
    const normalized = normalizeText(value).toLowerCase();
    if (['yes', 'true', '1', 'y'].includes(normalized)) return true;
    if (['no', 'false', '0', 'n'].includes(normalized)) return false;
    return null;
}

function parseInteger(value) {
    const normalized = normalizeText(value);
    if (!/^\d+$/.test(normalized)) return null;
    return Number.parseInt(normalized, 10);
}

function requireExact(input, key, expected, errors) {
    const actual = normalizeText(input[key]);
    if (!actual) {
        errors.push(`${key}=${expected} is required`);
    } else if (actual !== expected) {
        errors.push(`${key} must be ${expected}`);
    }
    return actual;
}

function requireYes(input, key, errors) {
    const value = normalizeBooleanFlag(input[key]);
    if (value !== true) {
        errors.push(`${key}=yes is required`);
    }
    return value;
}

function requireNo(input, key, errors) {
    const value = normalizeBooleanFlag(input[key]);
    if (value !== false) {
        errors.push(`${key}=no is required`);
    }
    return value;
}

function blockYes(input, key, errors) {
    const value = normalizeBooleanFlag(input[key]);
    if (value === true) {
        errors.push(`${key}=yes is blocked in Phase 5.21L2D`);
    }
    return value;
}

function validatePreviewInput(input = {}) {
    const errors = [];
    const source = normalizeText(input.source).toLowerCase();
    const route = normalizeText(input.route);
    if (!source) {
        errors.push('source=fotmob is required');
    } else if (source !== TARGET.source) {
        errors.push('source must be fotmob');
    }
    if (route !== TARGET.route) {
        errors.push('route=html_hydration is required');
    }

    const matchId = requireExact(input, 'match-id', TARGET.matchId, errors);
    const externalId = requireExact(input, 'external-id', TARGET.externalId, errors);
    const homeTeam = requireExact(input, 'home-team', TARGET.homeTeam, errors);
    const awayTeam = requireExact(input, 'away-team', TARGET.awayTeam, errors);
    const candidateVersion = requireExact(input, 'candidate-version', CANDIDATE_VERSION, errors);
    const hashStrategy = requireExact(input, 'hash-strategy', HASH_STRATEGY, errors);
    const networkAuthorization = requireYes(input, 'network-authorization', errors);
    const pagePropsV2PreviewAuthorization = requireYes(input, 'pageprops-v2-preview-authorization', errors);

    const noFlags = {};
    for (const flag of REQUIRED_NO_FLAGS) {
        noFlags[flag] = requireNo(input, flag, errors);
    }
    for (const flag of BLOCKED_YES_FLAGS) {
        blockYes(input, flag, errors);
    }

    const concurrency = parseInteger(input.concurrency);
    if (concurrency !== 1) {
        errors.push('concurrency=1 is required');
    }
    const retry = parseInteger(input.retry);
    if (retry !== 0) {
        errors.push('retry=0 is required');
    }

    return {
        ok: errors.length === 0,
        errors,
        value: {
            source: TARGET.source,
            route: TARGET.route,
            matchId,
            externalId,
            homeTeam,
            awayTeam,
            candidateVersion,
            hashStrategy,
            networkAuthorization,
            pagePropsV2PreviewAuthorization,
            allowDbWrite: noFlags['allow-db-write'],
            allowRawMatchDataWrite: noFlags['allow-raw-match-data-write'],
            allowMatchesWrite: noFlags['allow-matches-write'],
            allowParserFeatures: noFlags['allow-parser-features'],
            allowTraining: noFlags['allow-training'],
            allowPrediction: noFlags['allow-prediction'],
            concurrency,
            retry,
            printBody: noFlags['print-body'],
            saveBody: noFlags['save-body'],
            printFullJson: noFlags['print-full-json'],
            saveFullJson: noFlags['save-full-json'],
            allowBrowserRuntime: false,
            allowProxyRuntime: false,
        },
    };
}

function buildFotMobMatchUrl(externalId) {
    const id = normalizeText(externalId);
    if (!/^\d+$/.test(id)) {
        throw new Error(`INVALID_EXTERNAL_ID:${externalId}`);
    }
    return new URL(`/match/${id}`, FOTMOB_BASE_URL).href;
}

function sha256Text(text) {
    return crypto
        .createHash('sha256')
        .update(String(text ?? ''))
        .digest('hex');
}

function createAbortTimeout(timeoutMs) {
    const controller = typeof AbortController === 'function' ? new AbortController() : null;
    const timeoutHandle = controller
        ? setTimeout(() => {
              controller.abort(new Error(`FETCH_TIMEOUT:${timeoutMs}ms`));
          }, timeoutMs)
        : null;
    return { controller, timeoutHandle };
}

function clearAbortTimeout(timeoutHandle) {
    if (timeoutHandle) clearTimeout(timeoutHandle);
}

async function fetchHtml(requestUrl, dependencies = {}) {
    const fetchFn = dependencies.fetchFn || globalThis.fetch;
    const timeoutMs =
        Number.isInteger(dependencies.timeoutMs) && dependencies.timeoutMs > 0 ? dependencies.timeoutMs : 15000;
    if (typeof fetchFn !== 'function') {
        return {
            ok: false,
            controlled_failure: true,
            error: 'FETCH_DEPENDENCY_MISSING',
            request_url: requestUrl,
        };
    }

    const { controller, timeoutHandle } = createAbortTimeout(timeoutMs);
    let response;
    try {
        response = await fetchFn(requestUrl, {
            method: 'GET',
            headers: {
                accept: 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                'accept-language': 'en-US,en;q=0.9',
                'accept-encoding': 'identity',
                referer: FOTMOB_BASE_URL,
                'user-agent':
                    'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
            },
            redirect: 'follow',
            signal: controller?.signal,
        });
    } catch (error) {
        clearAbortTimeout(timeoutHandle);
        return {
            ok: false,
            controlled_failure: true,
            error: `FETCH_ERROR:${error.message}`,
            request_url: requestUrl,
        };
    }
    clearAbortTimeout(timeoutHandle);

    let body = '';
    try {
        body = await response.text();
    } catch (error) {
        return {
            ok: false,
            controlled_failure: true,
            error: `FETCH_BODY_READ_ERROR:${error.message}`,
            request_url: requestUrl,
            final_url: response.url || requestUrl,
            http_status: response.status || 0,
            content_type: response.headers?.get?.('content-type') || null,
        };
    }

    const result = {
        ok: response.ok === true,
        request_url: requestUrl,
        final_url: response.url || requestUrl,
        http_status: response.status || 0,
        content_type: response.headers?.get?.('content-type') || null,
        body_byte_length: Buffer.byteLength(body, 'utf8'),
        body_sha256: sha256Text(body),
        body,
    };
    if (!result.ok) {
        return {
            ...result,
            controlled_failure: true,
            error: `HTTP_${result.http_status}`,
        };
    }
    return result;
}

function extractNextDataJsonFromHtml(html) {
    if (!html || typeof html !== 'string') {
        return { ok: false, error: 'INVALID_HTML' };
    }
    const match =
        html.match(/<script\s+id=["']__NEXT_DATA__["']\s+type=["']application\/json["'][^>]*>([\s\S]*?)<\/script>/i) ||
        html.match(/<script[^>]*id=["']__NEXT_DATA__["'][^>]*>([\s\S]*?)<\/script>/i);
    if (!match || !match[1]) {
        return { ok: false, error: 'NO_NEXT_DATA' };
    }
    try {
        return {
            ok: true,
            data: JSON.parse(match[1].trim()),
        };
    } catch (error) {
        return {
            ok: false,
            error: `NEXT_DATA_PARSE_ERROR:${error.message}`,
        };
    }
}

function isPlainObject(value) {
    return value !== null && typeof value === 'object' && !Array.isArray(value);
}

function getPageProps(nextData) {
    if (!isPlainObject(nextData?.props?.pageProps)) {
        return null;
    }
    return nextData.props.pageProps;
}

function jsonClone(value) {
    if (value === undefined) return undefined;
    return JSON.parse(JSON.stringify(value));
}

function canonicalizeJson(value) {
    if (value === null || typeof value !== 'object') return value;
    if (Array.isArray(value)) return value.map(canonicalizeJson);
    const sorted = {};
    for (const key of Object.keys(value).sort()) {
        sorted[key] = canonicalizeJson(value[key]);
    }
    return sorted;
}

function sha256CanonicalJson(value) {
    return sha256Text(JSON.stringify(canonicalizeJson(value)));
}

function extractPagePropsForHash(value = {}) {
    if (isPlainObject(value) && isPlainObject(value.pageProps)) {
        return value.pageProps;
    }
    return value;
}

function computeStablePagePropsHash(pagePropsOrCandidate = {}) {
    return sha256CanonicalJson(extractPagePropsForHash(pagePropsOrCandidate));
}

function buildPagePropsV2Candidate({ input = {}, pageProps = {}, fetchResult = {}, generatedAt = null } = {}) {
    const safePageProps = jsonClone(pageProps) || {};
    const stableHash = computeStablePagePropsHash(safePageProps);
    const meta = {
        source: TARGET.source,
        route: TARGET.route,
        data_version: CANDIDATE_VERSION,
        hash_strategy: HASH_STRATEGY,
        match_id: input.matchId || TARGET.matchId,
        external_id: input.externalId || TARGET.externalId,
        request_url: fetchResult.request_url || buildFotMobMatchUrl(input.externalId || TARGET.externalId),
        final_url:
            fetchResult.final_url ||
            fetchResult.request_url ||
            buildFotMobMatchUrl(input.externalId || TARGET.externalId),
        http_status: Number(fetchResult.http_status || 0),
        content_type: fetchResult.content_type || null,
        body_byte_length: Number(fetchResult.body_byte_length || 0),
        fetch_body_sha256: fetchResult.body_sha256 || null,
        candidate_generated_at: generatedAt || new Date().toISOString(),
        full_html_body_stored: false,
        full_next_data_stored: false,
        full_json_printed: false,
        data_hash: stableHash,
    };
    return {
        _meta: meta,
        pageProps: safePageProps,
    };
}

function listJsonPaths(value, options = {}) {
    return listAuditJsonPaths(value, { includeContainers: options.includeContainers !== false });
}

function pathSet(paths = []) {
    return new Set(paths);
}

function comparePathCoverage(v2Paths = [], v1Paths = [], sampleLimit = SAMPLE_LIMIT) {
    const v2 = pathSet(v2Paths);
    const v1 = pathSet(v1Paths);
    const overlap = [];
    const v2Only = [];
    const v1Only = [];

    for (const path of v2) {
        if (v1.has(path)) {
            overlap.push(path);
        } else {
            v2Only.push(path);
        }
    }
    for (const path of v1) {
        if (!v2.has(path)) {
            v1Only.push(path);
        }
    }

    return {
        v2_path_count: v2.size,
        v1_path_count: v1.size,
        overlap_count: overlap.length,
        v2_only_count: v2Only.length,
        v1_only_count: v1Only.length,
        v2_only_path_samples: v2Only.sort().slice(0, sampleLimit),
        v1_only_path_samples: v1Only.sort().slice(0, sampleLimit),
    };
}

function hasPath(value, dottedPath) {
    const parts = dottedPath.split('.');
    let cursor = value;
    for (const part of parts) {
        if (!isPlainObject(cursor) || !Object.prototype.hasOwnProperty.call(cursor, part)) {
            return false;
        }
        cursor = cursor[part];
    }
    return true;
}

function summarizeModuleCoverage(v1RawData = {}, v2PageProps = {}) {
    const coverage = {};
    for (const modulePath of MODULE_COMPARISON_PATHS) {
        coverage[modulePath] = {
            v1: hasPath(v1RawData, modulePath),
            v2: hasPath(v2PageProps, modulePath),
        };
    }
    return coverage;
}

function topLevelKeys(value) {
    if (!isPlainObject(value)) return [];
    return Object.keys(value).sort();
}

function normalizeCollectedAt(row = {}) {
    if (row.collected_at instanceof Date) return row.collected_at.toISOString();
    return normalizeText(row.collected_at || row.collectedAt);
}

function normalizeRowId(row = {}) {
    if (row.id === undefined || row.id === null) return null;
    return String(row.id);
}

function valueOrFallback(value, fallback) {
    return value === undefined || value === null || value === '' ? fallback : value;
}

function objectOrEmpty(value) {
    return isPlainObject(value) ? value : {};
}

function jsonByteLength(value) {
    return Buffer.byteLength(JSON.stringify(value), 'utf8');
}

function computeSizeRatio(numerator, denominator) {
    return denominator > 0 ? Number((numerator / denominator).toFixed(6)) : null;
}

function buildStoredV1Metadata(storedRow = {}) {
    return {
        id: normalizeRowId(storedRow),
        match_id: normalizeText(storedRow.match_id),
        external_id: normalizeText(storedRow.external_id),
        collected_at: normalizeCollectedAt(storedRow),
        data_version: normalizeText(storedRow.data_version),
        data_hash: normalizeText(storedRow.data_hash),
    };
}

function validateStoredTargetRow(row = {}, input = {}) {
    const errors = [];
    if (!row) {
        return ['stored target raw row not found'];
    }
    if (normalizeText(row.match_id) !== input.matchId) errors.push('stored match_id mismatch');
    if (normalizeText(row.external_id) !== input.externalId) errors.push('stored external_id mismatch');
    if (normalizeText(row.data_version) !== 'fotmob_html_hyd_v1') errors.push('stored data_version mismatch');
    if (!isPlainObject(row.raw_data)) errors.push('stored raw_data must be object');
    for (const key of ['_meta', 'content', 'general', 'header', 'matchId']) {
        if (!Object.prototype.hasOwnProperty.call(row.raw_data || {}, key)) {
            errors.push(`stored raw_data missing ${key}`);
        }
    }
    return errors;
}

function buildControlledFailure(input, requestUrl, fetchResult, reason) {
    return {
        phase: PHASE,
        ok: false,
        controlled_failure: true,
        preview_only: true,
        source: TARGET.source,
        route: TARGET.route,
        match_id: input.matchId,
        external_id: input.externalId,
        home_team: input.homeTeam,
        away_team: input.awayTeam,
        candidate_version: CANDIDATE_VERSION,
        hash_strategy: HASH_STRATEGY,
        request_url: requestUrl,
        final_url: fetchResult?.final_url || null,
        http_status: fetchResult?.http_status || null,
        content_type: fetchResult?.content_type || null,
        body_byte_length: fetchResult?.body_byte_length || 0,
        body_sha256: fetchResult?.body_sha256 || null,
        next_data_parse_ok: false,
        page_props_found: false,
        stored_v1_raw_data_found: false,
        failure_reason: reason,
        db_write_executed: false,
        raw_match_data_write_executed: false,
        body_printed: false,
        body_saved: false,
        full_json_printed: false,
        full_json_saved: false,
        browser_used: false,
        proxy_used: false,
        retry_count: 0,
    };
}

function buildContentDiffSamples(contentCoverage = {}) {
    const v2Only = contentCoverage.v2_only_path_samples || [];
    const v1Only = contentCoverage.v1_only_path_samples || [];
    return [...v2Only.map(path => `v2_only:${path}`), ...v1Only.map(path => `v1_only:${path}`)].slice(0, SAMPLE_LIMIT);
}

function buildAssessment({
    pageProps = {},
    v1RawData = {},
    pageCoverage = {},
    contentCoverage = {},
    moduleCoverage = {},
}) {
    const v2TopLevelKeys = topLevelKeys(pageProps);
    const v1TopLevelKeys = topLevelKeys(v1RawData);
    const pagePropsSiblings = v2TopLevelKeys.filter(key => !['content', 'general', 'header'].includes(key));
    const extraSiblingKeys = pagePropsSiblings.filter(key => !v1TopLevelKeys.includes(key));
    const deepContentPreserved = contentCoverage.v1_only_count === 0;
    const pagePropsV2MoreComplete =
        pageCoverage.v2_only_count > 0 ||
        extraSiblingKeys.length > 0 ||
        Object.values(moduleCoverage).some(item => item.v2 === true && item.v1 === false);
    const pagePropsV2CandidateValid = isPlainObject(pageProps) && hasPath(pageProps, 'content');

    return {
        pageprops_v2_candidate_valid: pagePropsV2CandidateValid,
        pageprops_v2_more_complete_than_v1: pagePropsV2MoreComplete,
        deep_content_preserved: deepContentPreserved,
        pageprops_siblings_preserved_in_v2: extraSiblingKeys.length > 0,
        extra_pageprops_sibling_keys: extraSiblingKeys,
        recommended_next_phase: pagePropsV2CandidateValid
            ? 'Phase 5.21L2E pageProps v2 controlled write planning'
            : 'Stop and diagnose route/parser issue before any write planning',
        parser_features_training_deferred: true,
    };
}

function buildPagePropsV2NoWritePreview({ input = {}, storedRow = {}, fetchResult = {}, generatedAt = null } = {}) {
    const requestUrl = buildFotMobMatchUrl(valueOrFallback(input.externalId, TARGET.externalId));
    const storedErrors = validateStoredTargetRow(storedRow, input);
    if (storedErrors.length > 0) {
        return buildControlledFailure(
            input,
            requestUrl,
            fetchResult,
            `STORED_TARGET_INVALID:${storedErrors.join(',')}`
        );
    }
    if (!fetchResult.ok) {
        return buildControlledFailure(input, requestUrl, fetchResult, fetchResult.error || 'LIVE_REQUEST_FAILED');
    }

    const extraction = extractNextDataJsonFromHtml(fetchResult.body);
    if (!extraction.ok) {
        return buildControlledFailure(input, requestUrl, fetchResult, extraction.error);
    }
    const pageProps = getPageProps(extraction.data);
    if (!pageProps) {
        return buildControlledFailure(input, requestUrl, fetchResult, 'PAGE_PROPS_NOT_FOUND');
    }

    const v1RawData = storedRow.raw_data;
    const candidate = buildPagePropsV2Candidate({
        input,
        pageProps,
        fetchResult,
        generatedAt,
    });
    const stableHash = computeStablePagePropsHash(candidate);
    const v1RawDataPaths = listJsonPaths(v1RawData);
    const v2PagePropsPaths = listJsonPaths(pageProps);
    const v1ContentPaths = listJsonPaths(objectOrEmpty(v1RawData.content));
    const v2ContentPaths = listJsonPaths(objectOrEmpty(pageProps.content));
    const pageCoverage = comparePathCoverage(v2PagePropsPaths, v1RawDataPaths);
    const contentCoverage = comparePathCoverage(v2ContentPaths, v1ContentPaths);
    const moduleCoverage = summarizeModuleCoverage(v1RawData, pageProps);
    const v1JsonByteLength = jsonByteLength(v1RawData);
    const v2CandidateJsonByteLength = jsonByteLength(candidate);
    const sizeRatio = computeSizeRatio(v2CandidateJsonByteLength, v1JsonByteLength);
    const resolvedRequestUrl = valueOrFallback(fetchResult.request_url, requestUrl);
    const resolvedFinalUrl = valueOrFallback(fetchResult.final_url, requestUrl);

    return {
        phase: PHASE,
        ok: true,
        preview_only: true,
        source: TARGET.source,
        route: TARGET.route,
        match_id: input.matchId,
        external_id: input.externalId,
        home_team: input.homeTeam,
        away_team: input.awayTeam,
        candidate_version: CANDIDATE_VERSION,
        hash_strategy: HASH_STRATEGY,
        request_url: resolvedRequestUrl,
        final_url: resolvedFinalUrl,
        http_status: fetchResult.http_status,
        content_type: fetchResult.content_type,
        body_byte_length: fetchResult.body_byte_length,
        body_sha256: fetchResult.body_sha256,
        next_data_parse_ok: true,
        page_props_found: true,
        stored_v1_raw_data_found: true,
        stored_v1_raw_data_metadata: buildStoredV1Metadata(storedRow),
        candidate: {
            data_version: CANDIDATE_VERSION,
            stable_pageprops_hash: stableHash,
            has_meta: isPlainObject(candidate._meta),
            has_pageProps: isPlainObject(candidate.pageProps),
            pageProps_top_level_keys: topLevelKeys(pageProps),
        },
        shape_summary: {
            v1_raw_data: summarizeJsonShape(v1RawData),
            v2_candidate: summarizeJsonShape(candidate),
            v2_pageProps: summarizeJsonShape(pageProps),
            v1_content: summarizeJsonShape(objectOrEmpty(v1RawData.content)),
            v2_content: summarizeJsonShape(objectOrEmpty(pageProps.content)),
        },
        comparison: {
            v1_data_version: normalizeText(storedRow.data_version),
            v1_json_byte_length: v1JsonByteLength,
            v2_candidate_json_byte_length: v2CandidateJsonByteLength,
            size_ratio_v2_candidate_to_v1: sizeRatio,
            v1_path_count: v1RawDataPaths.length,
            v2_path_count: v2PagePropsPaths.length,
            v1_content_path_count: v1ContentPaths.length,
            v2_content_path_count: v2ContentPaths.length,
            v2_only_path_count: pageCoverage.v2_only_count,
            v1_only_path_count: pageCoverage.v1_only_count,
            content_missing_from_v2_count: contentCoverage.v1_only_count,
            content_missing_from_v1_count: contentCoverage.v2_only_count,
            content_diff_path_count: contentCoverage.v1_only_count + contentCoverage.v2_only_count,
        },
        module_coverage: moduleCoverage,
        limited_samples: {
            v2_only_paths: pageCoverage.v2_only_path_samples,
            v1_only_paths: pageCoverage.v1_only_path_samples,
            content_diff_paths: buildContentDiffSamples(contentCoverage),
        },
        assessment: buildAssessment({
            pageProps,
            v1RawData,
            pageCoverage,
            contentCoverage,
            moduleCoverage,
        }),
        db_write_executed: false,
        raw_match_data_write_executed: false,
        body_printed: false,
        body_saved: false,
        full_json_printed: false,
        full_json_saved: false,
        browser_used: false,
        proxy_used: false,
        retry_count: 0,
    };
}

async function queryReadOnly(client, sql, params = []) {
    const normalizedSql = normalizeText(sql).replace(/\s+/g, ' ').toLowerCase();
    if (!normalizedSql.startsWith('select ')) {
        throw new Error('NON_SELECT_SQL_BLOCKED');
    }
    if (/\b(insert|update|delete|truncate|alter|drop|create|grant|revoke|copy|for update)\b/i.test(normalizedSql)) {
        throw new Error('SQL_WRITE_OR_LOCK_BLOCKED');
    }
    return client.query(sql, params);
}

async function loadStoredTargetRow(client, input) {
    const result = await queryReadOnly(
        client,
        `
        SELECT id, match_id, external_id, data_version, data_hash, collected_at, raw_data
        FROM raw_match_data
        WHERE external_id = $1
        ORDER BY id
        `,
        [input.externalId]
    );
    const rows = result.rows || [];
    if (rows.length !== 1) {
        throw new Error(`STORED_TARGET_ROW_COUNT:${rows.length}`);
    }
    return rows[0];
}

function createDefaultPool() {
    const { Pool } = require('pg');
    const { buildDbConnectionConfig } = require('./helpers/dbBlueprint');
    return new Pool(buildDbConnectionConfig());
}

async function runCli(argv = process.argv.slice(2), dependencies = {}) {
    const parsedArgs = Array.isArray(argv) ? parseArgs(argv) : argv;
    const validation = validatePreviewInput(parsedArgs);
    const output = dependencies.output || (payload => process.stdout.write(`${JSON.stringify(payload, null, 2)}\n`));

    if (!validation.ok) {
        const payload = {
            phase: PHASE,
            ok: false,
            blocked: true,
            errors: validation.errors,
            preview_only: true,
            db_write_executed: false,
            raw_match_data_write_executed: false,
            body_printed: false,
            body_saved: false,
            full_json_printed: false,
            full_json_saved: false,
            browser_used: false,
            proxy_used: false,
        };
        output(payload);
        return { status: 1, payload };
    }

    const input = validation.value;
    const pool = dependencies.client || dependencies.storedRow ? null : createDefaultPool();
    const client = dependencies.client || pool;
    const requestUrl = buildFotMobMatchUrl(input.externalId);
    try {
        let storedRow = dependencies.storedRow;
        if (!storedRow) {
            storedRow = await loadStoredTargetRow(client, input);
        }
        const fetchResult =
            dependencies.fetchResult ||
            (await fetchHtml(requestUrl, {
                fetchFn: dependencies.fetchFn,
            }));
        const payload = buildPagePropsV2NoWritePreview({
            input,
            storedRow,
            fetchResult,
            generatedAt: dependencies.generatedAt,
        });
        output(payload);
        return { status: payload.ok ? 0 : 1, payload };
    } catch (error) {
        const payload = buildControlledFailure(input, requestUrl, null, error.message);
        output(payload);
        return { status: 1, payload };
    } finally {
        if (pool && typeof pool.end === 'function') {
            await pool.end();
        }
    }
}

module.exports = {
    PHASE,
    TARGET,
    CANDIDATE_VERSION,
    HASH_STRATEGY,
    MODULE_COMPARISON_PATHS,
    parseArgs,
    normalizeBooleanFlag,
    validatePreviewInput,
    buildFotMobMatchUrl,
    fetchHtml,
    extractNextDataJsonFromHtml,
    getPageProps,
    buildPagePropsV2Candidate,
    canonicalizeJson,
    sha256CanonicalJson,
    computeStablePagePropsHash,
    listJsonPaths,
    summarizeJsonShape,
    comparePathCoverage,
    summarizeModuleCoverage,
    buildPagePropsV2NoWritePreview,
    runCli,
};

if (require.main === module) {
    runCli()
        .then(result => {
            process.exitCode = result.status;
        })
        .catch(error => {
            process.stderr.write(`${error.stack || error.message}\n`);
            process.exitCode = 1;
        });
}
