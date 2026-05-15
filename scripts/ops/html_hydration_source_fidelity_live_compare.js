#!/usr/bin/env node
'use strict';

const crypto = require('node:crypto');
const {
    listJsonPaths: listAuditJsonPaths,
    summarizeJsonShape,
} = require('./raw_match_data_completeness_fidelity_audit');

const PHASE = 'PHASE5_21L2B_HTML_HYDRATION_SOURCE_FIDELITY_LIVE_COMPARE';
const FOTMOB_BASE_URL = 'https://www.fotmob.com';
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
]);
const SAMPLE_LIMIT = 50;

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
    if (actual !== expected) {
        errors.push(`${key}=${expected} is required`);
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
        errors.push(`${key}=yes is blocked in Phase 5.21L2B`);
    }
    return value;
}

function validateLiveCompareInput(input = {}) {
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
    const networkAuthorization = requireYes(input, 'network-authorization', errors);
    const liveCompareAuthorization = requireYes(input, 'live-compare-authorization', errors);

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
            networkAuthorization,
            liveCompareAuthorization,
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

async function fetchHtml(requestUrl, dependencies = {}) {
    const fetchFn = dependencies.fetchFn || globalThis.fetch;
    if (typeof fetchFn !== 'function') {
        return {
            ok: false,
            controlled_failure: true,
            error: 'FETCH_DEPENDENCY_MISSING',
            request_url: requestUrl,
        };
    }

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
        });
    } catch (error) {
        return {
            ok: false,
            controlled_failure: true,
            error: `FETCH_ERROR:${error.message}`,
            request_url: requestUrl,
        };
    }

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

function listJsonPaths(value, options = {}) {
    return listAuditJsonPaths(value, { includeContainers: options.includeContainers !== false });
}

function pathSet(paths = []) {
    return new Set(paths);
}

function comparePathCoverage(sourcePaths = [], storedPaths = [], sampleLimit = SAMPLE_LIMIT) {
    const source = pathSet(sourcePaths);
    const stored = pathSet(storedPaths);
    const overlap = [];
    const missingFromStored = [];
    const storedOnly = [];

    for (const path of source) {
        if (stored.has(path)) {
            overlap.push(path);
        } else {
            missingFromStored.push(path);
        }
    }
    for (const path of stored) {
        if (!source.has(path)) {
            storedOnly.push(path);
        }
    }

    return {
        source_path_count: source.size,
        stored_path_count: stored.size,
        overlap_count: overlap.length,
        missing_count: missingFromStored.length,
        stored_only_count: storedOnly.length,
        missing_path_samples: missingFromStored.sort().slice(0, sampleLimit),
        stored_only_path_samples: storedOnly.sort().slice(0, sampleLimit),
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

function summarizeModuleCoverage(pageProps = {}, storedRawData = {}) {
    const coverage = {};
    for (const modulePath of MODULE_COMPARISON_PATHS) {
        if (modulePath.startsWith('content.')) {
            coverage[modulePath] = {
                live: hasPath(pageProps, modulePath),
                stored: hasPath(storedRawData, modulePath),
            };
        } else {
            coverage[modulePath] = {
                live: hasPath(pageProps, modulePath),
                stored: hasPath(storedRawData, modulePath),
            };
        }
    }
    return coverage;
}

function classifyMissingPathCategory(path) {
    const normalized = normalizeText(path);
    if (normalized === 'seo' || normalized.startsWith('seo.')) {
        if (normalized.toLowerCase().includes('breadcrumb')) return 'breadcrumb';
        return 'seo';
    }
    if (normalized === 'content' || normalized.startsWith('content.')) {
        if (normalized.includes('playerStats')) return 'player_stat_level';
        if (normalized.includes('lineup')) return 'lineup_level';
        if (normalized.includes('liveticker') || normalized.includes('events')) return 'event_level';
        if (normalized.includes('stats') || normalized.includes('shotmap')) return 'stat_level';
        return 'deep_content';
    }
    if (normalized === 'props' || normalized.startsWith('props.')) return 'wrapper_source_level';
    return 'source_level';
}

function countCategories(paths = []) {
    const counts = {};
    for (const path of paths) {
        const category = classifyMissingPathCategory(path);
        counts[category] = (counts[category] || 0) + 1;
    }
    return counts;
}

function topLevelKeys(value) {
    if (!isPlainObject(value)) return [];
    return Object.keys(value).sort();
}

function detectStoredShape(storedRawData = {}) {
    const storedHasFullNextData = hasPath(storedRawData, 'props.pageProps');
    const storedHasPageProps = hasPath(storedRawData, 'pageProps') || storedHasFullNextData;
    const storedTransformedPayload =
        !storedHasFullNextData &&
        !storedHasPageProps &&
        hasPath(storedRawData, 'content') &&
        hasPath(storedRawData, 'general') &&
        hasPath(storedRawData, 'header');
    return {
        storedHasFullNextData,
        storedHasPageProps,
        storedTransformedPayload,
    };
}

function summarizePagePropsSiblingGaps(pageProps = {}, storedRawData = {}) {
    const pagePropsSiblingKeys = topLevelKeys(pageProps).filter(key => !['content', 'general', 'header'].includes(key));
    const missing = pagePropsSiblingKeys.filter(key => !Object.prototype.hasOwnProperty.call(storedRawData, key));
    return {
        pagePropsSiblingsMissing: missing.length > 0,
        missing,
    };
}

function detectSeoBreadcrumbMissing(moduleCoverage = {}) {
    return (
        (moduleCoverage.seo?.live && !moduleCoverage.seo?.stored) ||
        (moduleCoverage['seo.breadcrumbJSONLD']?.live && !moduleCoverage['seo.breadcrumbJSONLD']?.stored)
    );
}

function assessDeepContentPreservation(coverage = {}) {
    const liveContentPathCount = coverage.live_content_path_count || 0;
    const contentMissingCount = coverage.stored_vs_content_missing_count || 0;
    const contentMissingRatio = liveContentPathCount > 0 ? contentMissingCount / liveContentPathCount : null;
    let deepContentLikelyPreserved = 'unknown';
    if (liveContentPathCount > 0 && contentMissingCount === 0) {
        deepContentLikelyPreserved = true;
    } else if (liveContentPathCount > 0 && contentMissingRatio <= 0.02) {
        deepContentLikelyPreserved = true;
    } else if (liveContentPathCount > 0) {
        deepContentLikelyPreserved = false;
    }
    return {
        deepContentLikelyPreserved,
        contentMissingRatio,
    };
}

function findSourceWrapperKeysMissingFromStored(nextData = {}, storedRawData = {}) {
    return topLevelKeys(nextData).filter(key => !Object.prototype.hasOwnProperty.call(storedRawData, key));
}

function buildSourceFidelityAssessment({
    nextData = {},
    pageProps = {},
    storedRawData = {},
    coverage = {},
    moduleCoverage = {},
}) {
    const storedShape = detectStoredShape(storedRawData);
    const siblingGaps = summarizePagePropsSiblingGaps(pageProps, storedRawData);
    const seoBreadcrumbMissing = detectSeoBreadcrumbMissing(moduleCoverage);
    const deepContent = assessDeepContentPreservation(coverage);
    const sourceWrapperKeysPresent = findSourceWrapperKeysMissingFromStored(nextData, storedRawData);
    const storageStrategyReviewRecommended =
        !storedShape.storedHasFullNextData ||
        !storedShape.storedHasPageProps ||
        siblingGaps.pagePropsSiblingsMissing ||
        seoBreadcrumbMissing ||
        deepContent.deepContentLikelyPreserved !== true;

    return {
        stored_raw_data_is_full_next_data: storedShape.storedHasFullNextData,
        stored_raw_data_is_full_page_props: storedShape.storedHasPageProps,
        stored_raw_data_is_transformed_payload: storedShape.storedTransformedPayload,
        page_props_siblings_missing: siblingGaps.pagePropsSiblingsMissing,
        page_props_sibling_keys_missing_from_stored: siblingGaps.missing,
        seo_breadcrumb_missing: Boolean(seoBreadcrumbMissing),
        deep_content_likely_preserved: deepContent.deepContentLikelyPreserved,
        deep_content_missing_ratio: deepContent.contentMissingRatio,
        source_level_metadata_missing: sourceWrapperKeysPresent.length > 0,
        source_wrapper_keys_missing_from_stored: sourceWrapperKeysPresent,
        storage_strategy_review_recommended: storageStrategyReviewRecommended,
        raw_storage_strategy_risk: storageStrategyReviewRecommended ? 'review_required' : 'low',
        summary: storageStrategyReviewRecommended
            ? 'Stored raw_data is a transformed content/general/header payload rather than full __NEXT_DATA__ or full pageProps; storage strategy needs an explicit decision before parser/features/training.'
            : 'Stored raw_data appears to preserve the compared pageProps paths, but raw storage policy still needs an explicit decision before parser/features/training.',
    };
}

function normalizeCollectedAt(row = {}) {
    if (row.collected_at instanceof Date) return row.collected_at.toISOString();
    return normalizeText(row.collected_at || row.collectedAt);
}

function buildControlledFailure(input, requestUrl, fetchResult, reason) {
    return {
        phase: PHASE,
        ok: false,
        controlled_failure: true,
        compare_only: true,
        source: TARGET.source,
        route: TARGET.route,
        match_id: input.matchId,
        external_id: input.externalId,
        home_team: input.homeTeam,
        away_team: input.awayTeam,
        request_url: requestUrl,
        final_url: fetchResult?.final_url || null,
        http_status: fetchResult?.http_status || null,
        content_type: fetchResult?.content_type || null,
        body_byte_length: fetchResult?.body_byte_length || 0,
        body_sha256: fetchResult?.body_sha256 || null,
        next_data_parse_ok: false,
        page_props_found: false,
        stored_raw_data_found: false,
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

function buildHtmlHydrationSourceFidelityLiveCompare({ input = {}, storedRow = {}, fetchResult = {} } = {}) {
    const requestUrl = buildFotMobMatchUrl(input.externalId || TARGET.externalId);
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
    const nextData = extraction.data;
    const pageProps = getPageProps(nextData);
    if (!pageProps) {
        return buildControlledFailure(input, requestUrl, fetchResult, 'PAGE_PROPS_NOT_FOUND');
    }

    const storedRawData = storedRow.raw_data;
    const liveNextDataPaths = listJsonPaths(nextData);
    const livePagePropsPaths = listJsonPaths(pageProps);
    const liveContentPaths = listJsonPaths(pageProps.content || {});
    const storedRawDataPaths = listJsonPaths(storedRawData);
    const storedContentPaths = listJsonPaths(storedRawData.content || {});
    const pagePropsCoverage = comparePathCoverage(livePagePropsPaths, storedRawDataPaths);
    const contentCoverage = comparePathCoverage(liveContentPaths, storedContentPaths);
    const moduleCoverage = summarizeModuleCoverage(pageProps, storedRawData);
    const pathCoverage = {
        live_next_data_path_count: liveNextDataPaths.length,
        live_page_props_path_count: livePagePropsPaths.length,
        live_content_path_count: liveContentPaths.length,
        stored_raw_data_path_count: storedRawDataPaths.length,
        stored_content_path_count: storedContentPaths.length,
        stored_vs_page_props_overlap_count: pagePropsCoverage.overlap_count,
        stored_vs_page_props_missing_count: pagePropsCoverage.missing_count,
        stored_vs_page_props_stored_only_count: pagePropsCoverage.stored_only_count,
        stored_vs_content_overlap_count: contentCoverage.overlap_count,
        stored_vs_content_missing_count: contentCoverage.missing_count,
        stored_vs_content_stored_only_count: contentCoverage.stored_only_count,
    };
    const missingPathSamples = {
        source_level_missing_from_stored: pagePropsCoverage.missing_path_samples,
        content_level_missing_from_stored: contentCoverage.missing_path_samples,
        stored_only_paths: pagePropsCoverage.stored_only_path_samples,
    };

    return {
        phase: PHASE,
        ok: true,
        compare_only: true,
        source: TARGET.source,
        route: TARGET.route,
        match_id: input.matchId,
        external_id: input.externalId,
        home_team: input.homeTeam,
        away_team: input.awayTeam,
        request_url: fetchResult.request_url || requestUrl,
        final_url: fetchResult.final_url || requestUrl,
        http_status: fetchResult.http_status,
        content_type: fetchResult.content_type,
        body_byte_length: fetchResult.body_byte_length,
        body_sha256: fetchResult.body_sha256,
        next_data_parse_ok: true,
        page_props_found: true,
        stored_raw_data_found: true,
        stored_raw_data_metadata: {
            id: storedRow.id === undefined || storedRow.id === null ? null : String(storedRow.id),
            match_id: normalizeText(storedRow.match_id),
            external_id: normalizeText(storedRow.external_id),
            collected_at: normalizeCollectedAt(storedRow),
            data_version: normalizeText(storedRow.data_version),
            data_hash: normalizeText(storedRow.data_hash),
        },
        shape_summary: {
            live_next_data: summarizeJsonShape(nextData),
            live_page_props: summarizeJsonShape(pageProps),
            live_content: summarizeJsonShape(pageProps.content || {}),
            stored_raw_data: summarizeJsonShape(storedRawData),
            stored_content: summarizeJsonShape(storedRawData.content || {}),
        },
        path_coverage: pathCoverage,
        module_coverage: moduleCoverage,
        page_props_top_level_keys: topLevelKeys(pageProps),
        stored_raw_data_top_level_keys: topLevelKeys(storedRawData),
        missing_path_category_counts: {
            source_level_missing_from_stored: countCategories(pagePropsCoverage.missing_path_samples),
            content_level_missing_from_stored: countCategories(contentCoverage.missing_path_samples),
        },
        missing_path_samples: missingPathSamples,
        fidelity_assessment: buildSourceFidelityAssessment({
            nextData,
            pageProps,
            storedRawData,
            coverage: pathCoverage,
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
    const validation = validateLiveCompareInput(parsedArgs);
    const output = dependencies.output || (payload => process.stdout.write(`${JSON.stringify(payload, null, 2)}\n`));

    if (!validation.ok) {
        output({
            phase: PHASE,
            ok: false,
            blocked: true,
            errors: validation.errors,
            compare_only: true,
            db_write_executed: false,
            raw_match_data_write_executed: false,
            body_printed: false,
            body_saved: false,
            full_json_printed: false,
            full_json_saved: false,
            browser_used: false,
            proxy_used: false,
        });
        return { status: 1, payload: null };
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
        const payload = buildHtmlHydrationSourceFidelityLiveCompare({
            input,
            storedRow,
            fetchResult,
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
    MODULE_COMPARISON_PATHS,
    parseArgs,
    normalizeBooleanFlag,
    validateLiveCompareInput,
    buildFotMobMatchUrl,
    fetchHtml,
    extractNextDataJsonFromHtml,
    getPageProps,
    listJsonPaths,
    summarizeJsonShape,
    pathSet,
    comparePathCoverage,
    summarizeModuleCoverage,
    classifyMissingPathCategory,
    buildSourceFidelityAssessment,
    buildHtmlHydrationSourceFidelityLiveCompare,
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
