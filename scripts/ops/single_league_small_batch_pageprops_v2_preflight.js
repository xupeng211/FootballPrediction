#!/usr/bin/env node
/* eslint-disable complexity, max-lines, max-statements */
'use strict';

const fs = require('node:fs');
const path = require('node:path');
const {
    CANDIDATE_VERSION,
    HASH_STRATEGY,
    buildFotMobMatchUrl,
    fetchHtml,
    extractNextDataJsonFromHtml,
    getPageProps,
    buildPagePropsV2Candidate: buildSingleTargetPagePropsV2Candidate,
    computeStablePagePropsHash,
    listJsonPaths,
    summarizeJsonShape,
} = require('./pageprops_v2_no_write_preview');

const PHASE = 'PHASE5_21L2T_SINGLE_LEAGUE_SMALL_BATCH_PAGEPROPS_V2_PREFLIGHT';
const MANIFEST_PATH = 'docs/_manifests/fotmob_pageprops_v2_ligue1_2025_2026_profile_001.proposal.json';
const REPORT_PATH = 'docs/_reports/SINGLE_LEAGUE_SMALL_BATCH_PAGEPROPS_V2_PREFLIGHT_PHASE5_21L2T.md';
const SOURCE = 'fotmob';
const LEAGUE_ID = 53;
const LEAGUE_NAME = 'Ligue 1';
const SEASON = '2025/2026';
const SEASON_COMPACT = '20252026';
const ROUTE = 'html_hydration';
const BATCH_ID = 'fotmob-pageprops-v2-ligue1-2025-2026-profile-001';
const TARGET_COUNT = 50;
const KNOWN_COMPLETED_COUNT = 8;
const EXPECTED_PROTECTED_TABLE_BASELINE = Object.freeze({
    matches: 10,
    bookmaker_odds_history: 2,
    raw_match_data: 18,
    l3_features: 2,
    match_features_training: 2,
    predictions: 2,
});
const PROTECTED_TABLES = Object.freeze(Object.keys(EXPECTED_PROTECTED_TABLE_BASELINE));
const REQUIRED_NO_FLAGS = Object.freeze([
    'allowDbWrite',
    'allowRawMatchDataWrite',
    'allowControlledWrite',
    'allowSchemaMigration',
    'allowParserImplementation',
    'allowFeatureExtraction',
    'allowTraining',
    'allowPrediction',
    'allowBrowserRuntime',
    'allowProxyRuntime',
    'printFullBody',
    'saveFullBody',
    'printFullJson',
    'saveFullJson',
    'printFullPageprops',
    'saveFullPageprops',
]);
const BLOCKED_TRUE_FLAGS = Object.freeze([
    'executeWrite',
    'commit',
    'inventTargets',
    'fabricateExternalIds',
    'allowOddsWrite',
    'allowMatchesWrite',
    'allowRawDataPrint',
]);
const MODULE_PRESENCE_PATHS = Object.freeze([
    'content.matchFacts',
    'content.lineup',
    'content.liveticker',
    'content.playerStats',
    'content.shotmap',
    'content.stats',
    'content.h2h',
    'content.table',
    'content.momentum',
    'content.topPlayers',
    'content.insights',
    'content.highlights',
    'seo',
    'seo.eventJSONLD',
    'seo.breadcrumbJSONLD',
    'translations',
    'fallback',
    'nav',
    'ongoing',
    'ssr',
]);
const BLOCK_MARKER_PATTERNS = Object.freeze([
    ['http_403', /403|forbidden/i],
    ['http_429', /429|too many requests|rate limit/i],
    ['cloudflare', /cloudflare|cf-chl|cf_clearance|attention required|just a moment/i],
    ['captcha', /captcha|verify you are human|human verification/i],
    ['access_denied', /access denied|request blocked/i],
]);

function normalizeText(value) {
    return String(value ?? '').trim();
}

function normalizeBooleanFlag(value, fallback = undefined) {
    if (typeof value === 'boolean') return value;
    if (value === null || value === undefined || value === '') return fallback;
    const normalized = normalizeText(value).toLowerCase();
    if (['1', 'true', 'yes', 'y', 'on'].includes(normalized)) return true;
    if (['0', 'false', 'no', 'n', 'off'].includes(normalized)) return false;
    return fallback;
}

function parseInteger(value, fallback = null) {
    if (value === null || value === undefined || value === '') return fallback;
    const normalized = normalizeText(value);
    if (!/^\d+$/.test(normalized)) return Number.NaN;
    return Number.parseInt(normalized, 10);
}

function parseOptionValue(arg, argv, index) {
    if (arg.includes('=')) return { value: arg.slice(arg.indexOf('=') + 1), consumedNext: false };
    const nextArg = argv[index + 1];
    if (typeof nextArg === 'string' && !nextArg.startsWith('--')) return { value: nextArg, consumedNext: true };
    return { value: true, consumedNext: false };
}

function toCamelKey(rawKey) {
    return normalizeText(rawKey).replace(/[-_]([a-z0-9])/g, (_match, char) => char.toUpperCase());
}

function parseArgs(argv = process.argv.slice(2)) {
    const options = {
        manifest: null,
        source: null,
        leagueId: null,
        leagueName: null,
        season: null,
        route: null,
        rawVersion: null,
        hashStrategy: null,
        batchId: null,
        targetCount: null,
        networkAuthorization: null,
        matchDetailPreflightAuthorization: null,
        allowDbWrite: null,
        allowRawMatchDataWrite: null,
        allowControlledWrite: null,
        allowSchemaMigration: null,
        allowParserImplementation: null,
        allowFeatureExtraction: null,
        allowTraining: null,
        allowPrediction: null,
        allowBrowserRuntime: null,
        allowProxyRuntime: null,
        concurrency: null,
        retry: null,
        printFullBody: null,
        saveFullBody: null,
        printFullJson: null,
        saveFullJson: null,
        printFullPageprops: null,
        saveFullPageprops: null,
        executeWrite: false,
        commit: false,
        inventTargets: false,
        fabricateExternalIds: false,
        allowOddsWrite: false,
        allowMatchesWrite: false,
        allowRawDataPrint: false,
        help: false,
        unknown: [],
    };
    const knownKeys = new Set(Object.keys(options));
    const booleanKeys = new Set([
        'networkAuthorization',
        'matchDetailPreflightAuthorization',
        ...REQUIRED_NO_FLAGS,
        ...BLOCKED_TRUE_FLAGS,
        'help',
    ]);

    for (let index = 0; index < argv.length; index += 1) {
        const arg = String(argv[index]);
        if (!arg.startsWith('--')) {
            options.unknown.push(arg);
            continue;
        }
        const rawKey = arg.replace(/^--/, '').split('=')[0];
        const key = toCamelKey(rawKey);
        const { value, consumedNext } = parseOptionValue(arg, argv, index);
        if (consumedNext) index += 1;
        if (!knownKeys.has(key)) {
            options.unknown.push(rawKey);
            continue;
        }
        options[key] = booleanKeys.has(key) ? normalizeBooleanFlag(value, true) : value;
    }
    return options;
}

function pushRequiredYes(errors, value, flagName) {
    if (value === true) return;
    if (value === false) {
        errors.push(`${flagName}=yes is required in Phase 5.21L2T`);
        return;
    }
    errors.push(`missing ${flagName}=yes`);
}

function pushRequiredNo(errors, value, flagName) {
    if (value === false) return;
    if (value === true) {
        errors.push(`${flagName}=yes is blocked in Phase 5.21L2T`);
        return;
    }
    errors.push(`missing ${flagName}=no`);
}

function requireExact(errors, actual, expected, flagName) {
    if (!normalizeText(actual)) {
        errors.push(`missing ${flagName}=${expected}`);
        return;
    }
    if (normalizeText(actual) !== expected) {
        errors.push(`${flagName} must be ${expected}`);
    }
}

function normalizePreflightInput(input = {}) {
    return {
        manifest: normalizeText(input.manifest),
        source: normalizeText(input.source).toLowerCase(),
        leagueId: parseInteger(input.leagueId, null),
        leagueName: normalizeText(input.leagueName),
        season: normalizeText(input.season),
        route: normalizeText(input.route),
        rawVersion: normalizeText(input.rawVersion),
        hashStrategy: normalizeText(input.hashStrategy),
        batchId: normalizeText(input.batchId),
        targetCount: parseInteger(input.targetCount, null),
        networkAuthorization: normalizeBooleanFlag(input.networkAuthorization, undefined),
        matchDetailPreflightAuthorization: normalizeBooleanFlag(input.matchDetailPreflightAuthorization, undefined),
        allowDbWrite: normalizeBooleanFlag(input.allowDbWrite, undefined),
        allowRawMatchDataWrite: normalizeBooleanFlag(input.allowRawMatchDataWrite, undefined),
        allowControlledWrite: normalizeBooleanFlag(input.allowControlledWrite, undefined),
        allowSchemaMigration: normalizeBooleanFlag(input.allowSchemaMigration, undefined),
        allowParserImplementation: normalizeBooleanFlag(input.allowParserImplementation, undefined),
        allowFeatureExtraction: normalizeBooleanFlag(input.allowFeatureExtraction, undefined),
        allowTraining: normalizeBooleanFlag(input.allowTraining, undefined),
        allowPrediction: normalizeBooleanFlag(input.allowPrediction, undefined),
        allowBrowserRuntime: normalizeBooleanFlag(input.allowBrowserRuntime, undefined),
        allowProxyRuntime: normalizeBooleanFlag(input.allowProxyRuntime, undefined),
        concurrency: parseInteger(input.concurrency, null),
        retry: parseInteger(input.retry, null),
        printFullBody: normalizeBooleanFlag(input.printFullBody, undefined),
        saveFullBody: normalizeBooleanFlag(input.saveFullBody, undefined),
        printFullJson: normalizeBooleanFlag(input.printFullJson, undefined),
        saveFullJson: normalizeBooleanFlag(input.saveFullJson, undefined),
        printFullPageprops: normalizeBooleanFlag(input.printFullPageprops, undefined),
        saveFullPageprops: normalizeBooleanFlag(input.saveFullPageprops, undefined),
        executeWrite: normalizeBooleanFlag(input.executeWrite, false),
        commit: normalizeBooleanFlag(input.commit, false),
        inventTargets: normalizeBooleanFlag(input.inventTargets, false),
        fabricateExternalIds: normalizeBooleanFlag(input.fabricateExternalIds, false),
        allowOddsWrite: normalizeBooleanFlag(input.allowOddsWrite, false),
        allowMatchesWrite: normalizeBooleanFlag(input.allowMatchesWrite, false),
        allowRawDataPrint: normalizeBooleanFlag(input.allowRawDataPrint, false),
        unknown: Array.isArray(input.unknown) ? input.unknown : [],
    };
}

function validatePreflightInput(input = {}) {
    const value = normalizePreflightInput(input);
    const errors = [];
    if (value.unknown.length > 0) errors.push(`unknown arguments: ${value.unknown.join(', ')}`);
    requireExact(errors, value.manifest, MANIFEST_PATH, 'manifest');
    requireExact(errors, value.source, SOURCE, 'source');
    if (value.leagueId !== LEAGUE_ID) errors.push('league-id must be 53');
    requireExact(errors, value.leagueName, LEAGUE_NAME, 'league-name');
    requireExact(errors, value.season, SEASON, 'season');
    requireExact(errors, value.route, ROUTE, 'route');
    requireExact(errors, value.rawVersion, CANDIDATE_VERSION, 'raw-version');
    requireExact(errors, value.hashStrategy, HASH_STRATEGY, 'hash-strategy');
    requireExact(errors, value.batchId, BATCH_ID, 'batch-id');
    if (value.targetCount !== TARGET_COUNT) errors.push('target-count must be 50');
    pushRequiredYes(errors, value.networkAuthorization, 'network-authorization');
    pushRequiredYes(errors, value.matchDetailPreflightAuthorization, 'match-detail-preflight-authorization');
    for (const key of REQUIRED_NO_FLAGS) {
        pushRequiredNo(
            errors,
            value[key],
            key.replace(/[A-Z]/g, char => `-${char.toLowerCase()}`)
        );
    }
    if (value.concurrency !== 1) errors.push('concurrency=1 is required');
    if (value.retry !== 0) errors.push('retry=0 is required');
    for (const key of BLOCKED_TRUE_FLAGS) {
        if (value[key] === true) {
            errors.push(`${key.replace(/[A-Z]/g, char => `-${char.toLowerCase()}`)}=yes is blocked`);
        }
    }
    return { ok: errors.length === 0, errors, value };
}

function isPlainObject(value) {
    return value !== null && typeof value === 'object' && !Array.isArray(value);
}

function jsonClone(value) {
    if (value === undefined) return undefined;
    return JSON.parse(JSON.stringify(value));
}

function jsonByteLength(value) {
    return Buffer.byteLength(JSON.stringify(value), 'utf8');
}

function topLevelKeys(value) {
    return isPlainObject(value) ? Object.keys(value).sort() : [];
}

function hasPath(value, dottedPath) {
    const parts = dottedPath.split('.');
    let cursor = value;
    for (const part of parts) {
        if (!isPlainObject(cursor) || !Object.prototype.hasOwnProperty.call(cursor, part)) return false;
        cursor = cursor[part];
    }
    return true;
}

function summarizeModulePresence(pageProps = {}) {
    return Object.fromEntries(MODULE_PRESENCE_PATHS.map(modulePath => [modulePath, hasPath(pageProps, modulePath)]));
}

function buildProtectedTableBaseline(rows = []) {
    const baseline = {};
    const safeRows = Array.isArray(rows) ? rows : [];
    for (const table of PROTECTED_TABLES) {
        const row = safeRows.find(item => normalizeText(item.table_name) === table);
        baseline[table] = row ? Number(row.rows || 0) : 0;
    }
    return baseline;
}

function validateProtectedTableBaseline(baseline = {}) {
    const errors = [];
    for (const [table, expectedRows] of Object.entries(EXPECTED_PROTECTED_TABLE_BASELINE)) {
        if (Number(baseline[table]) !== expectedRows) {
            errors.push(`${table} expected ${expectedRows}, got ${Number(baseline[table] || 0)}`);
        }
    }
    return errors;
}

function normalizeCandidateTarget(target = {}) {
    return {
        ...target,
        batch_id: normalizeText(target.batch_id),
        source: normalizeText(target.source).toLowerCase(),
        route: normalizeText(target.route),
        raw_data_version: normalizeText(target.raw_data_version),
        hash_strategy: normalizeText(target.hash_strategy),
        match_id: normalizeText(target.match_id),
        external_id: normalizeText(target.external_id),
        league_id: Number(target.league_id),
        league_name: normalizeText(target.league_name),
        season: normalizeText(target.season),
        home_team: normalizeText(target.home_team),
        away_team: normalizeText(target.away_team),
    };
}

function validateCandidateTargets(manifest = {}) {
    const errors = [];
    const candidates = Array.isArray(manifest.candidate_targets)
        ? manifest.candidate_targets.map(normalizeCandidateTarget)
        : null;
    if (!candidates) return { ok: false, errors: ['manifest candidate_targets must be an array'], candidates: [] };
    if (candidates.length !== TARGET_COUNT) {
        errors.push(`manifest candidate_targets must contain ${TARGET_COUNT} targets`);
    }

    const completedExternalIds = new Set(
        (manifest.known_completed_targets || []).map(target => normalizeText(target.external_id)).filter(Boolean)
    );
    const seenExternalIds = new Set();
    const seenMatchIds = new Set();
    for (const target of candidates) {
        if (!/^\d+$/.test(target.external_id)) {
            errors.push(`${target.external_id || 'missing'}: external_id must be numeric`);
        }
        const expectedMatchId = `${LEAGUE_ID}_${SEASON_COMPACT}_${target.external_id}`;
        if (target.match_id !== expectedMatchId) {
            errors.push(`${target.external_id}: match_id must be ${expectedMatchId}`);
        }
        if (seenExternalIds.has(target.external_id)) errors.push(`${target.external_id}: duplicate external_id`);
        if (seenMatchIds.has(target.match_id)) errors.push(`${target.match_id}: duplicate match_id`);
        seenExternalIds.add(target.external_id);
        seenMatchIds.add(target.match_id);
        if (completedExternalIds.has(target.external_id)) {
            errors.push(`${target.external_id}: candidate overlaps known_completed_targets`);
        }
        if (target.batch_id !== BATCH_ID) errors.push(`${target.external_id}: batch_id mismatch`);
        if (target.source !== SOURCE) errors.push(`${target.external_id}: source mismatch`);
        if (target.route !== ROUTE) errors.push(`${target.external_id}: route mismatch`);
        if (target.raw_data_version !== CANDIDATE_VERSION) {
            errors.push(`${target.external_id}: raw_data_version mismatch`);
        }
        if (target.hash_strategy !== HASH_STRATEGY) errors.push(`${target.external_id}: hash_strategy mismatch`);
        if (target.league_id !== LEAGUE_ID) errors.push(`${target.external_id}: league_id mismatch`);
        if (target.league_name !== LEAGUE_NAME) errors.push(`${target.external_id}: league_name mismatch`);
        if (target.season !== SEASON) errors.push(`${target.external_id}: season mismatch`);
    }
    return { ok: errors.length === 0, errors, candidates };
}

function validateManifest(manifest = {}) {
    const errors = [];
    if (normalizeText(manifest.schema_version) !== 'target_manifest_proposal_v1') {
        errors.push('manifest schema_version must be target_manifest_proposal_v1');
    }
    if (normalizeText(manifest.batch_id) !== BATCH_ID) errors.push('manifest batch_id mismatch');
    if (normalizeText(manifest.source).toLowerCase() !== SOURCE) errors.push('manifest source mismatch');
    if (normalizeText(manifest.route) !== ROUTE) errors.push('manifest route mismatch');
    if (normalizeText(manifest.raw_data_version) !== CANDIDATE_VERSION) {
        errors.push('manifest raw_data_version mismatch');
    }
    if (normalizeText(manifest.hash_strategy) !== HASH_STRATEGY) errors.push('manifest hash_strategy mismatch');
    if (Number(manifest.league?.league_id) !== LEAGUE_ID) errors.push('manifest league_id mismatch');
    if (normalizeText(manifest.league?.league_name) !== LEAGUE_NAME) errors.push('manifest league_name mismatch');
    if (normalizeText(manifest.league?.season) !== SEASON) errors.push('manifest season mismatch');
    if (!Array.isArray(manifest.known_completed_targets)) {
        errors.push('manifest known_completed_targets must be an array');
    } else if (manifest.known_completed_targets.length !== KNOWN_COMPLETED_COUNT) {
        errors.push(`manifest known_completed_targets must contain ${KNOWN_COMPLETED_COUNT} targets`);
    }
    if (normalizeText(manifest.target_population_status) !== 'ready_for_no_write_preflight') {
        errors.push('manifest target_population_status must be ready_for_no_write_preflight before L2T');
    }
    const candidateValidation = validateCandidateTargets(manifest);
    errors.push(...candidateValidation.errors);
    return {
        ok: errors.length === 0,
        errors,
        candidates: candidateValidation.candidates,
    };
}

function groupRowsByMatchId(rows = []) {
    const grouped = new Map();
    for (const row of Array.isArray(rows) ? rows : []) {
        const matchId = normalizeText(row.match_id);
        if (!grouped.has(matchId)) grouped.set(matchId, []);
        grouped.get(matchId).push(row);
    }
    return grouped;
}

function summarizeExistingVersions(rows = []) {
    return [
        ...new Set((Array.isArray(rows) ? rows : []).map(row => normalizeText(row.data_version)).filter(Boolean)),
    ].sort();
}

function assertNoDuplicateVersions(rows = []) {
    const seen = new Set();
    for (const row of Array.isArray(rows) ? rows : []) {
        const key = `${normalizeText(row.match_id)}\u0000${normalizeText(row.data_version)}`;
        if (seen.has(key)) throw new Error(`DUPLICATE_MATCH_ID_DATA_VERSION:${normalizeText(row.match_id)}`);
        seen.add(key);
    }
}

function buildExistingVersionDecision(rows = []) {
    const safeRows = Array.isArray(rows) ? rows : [];
    assertNoDuplicateVersions(safeRows);
    const versions = summarizeExistingVersions(safeRows);
    const v2Rows = safeRows.filter(row => normalizeText(row.data_version) === CANDIDATE_VERSION);
    if (v2Rows.length > 0) {
        return {
            decision: 'skipped_existing_v2',
            existing_versions: versions,
            target_version_exists: true,
            existing_v2_data_hash: normalizeText(v2Rows[0].data_hash).toLowerCase() || null,
            should_fetch: false,
            failure_reason: 'existing_fotmob_pageprops_v2',
        };
    }
    return {
        decision: 'needs_preflight',
        existing_versions: versions,
        target_version_exists: false,
        existing_v2_data_hash: null,
        should_fetch: true,
        failure_reason: null,
    };
}

function detectBlockMarkers(fetchResult = {}) {
    const markers = new Set();
    const status = Number(fetchResult.http_status || fetchResult.status || 0);
    if (status === 403) markers.add('http_403');
    if (status === 429) markers.add('http_429');
    const sample = `${normalizeText(fetchResult.error)} ${normalizeText(fetchResult.body).slice(0, 2000)}`;
    for (const [name, pattern] of BLOCK_MARKER_PATTERNS) {
        if (pattern.test(sample)) markers.add(name);
    }
    return [...markers].sort();
}

function isSystemicBlockedFetch(fetchResult = {}) {
    const markers = detectBlockMarkers(fetchResult);
    return {
        blocked: markers.length > 0,
        markers,
    };
}

function buildPagePropsV2Candidate({ target = {}, pageProps = {}, fetchResult = {}, generatedAt = null } = {}) {
    const input = {
        source: SOURCE,
        route: ROUTE,
        matchId: target.match_id,
        externalId: target.external_id,
        homeTeam: target.home_team,
        awayTeam: target.away_team,
    };
    const baseCandidate = buildSingleTargetPagePropsV2Candidate({
        input,
        pageProps,
        fetchResult,
        generatedAt,
    });
    const requestUrl = fetchResult.request_url || buildFotMobMatchUrl(target.external_id);
    const candidate = {
        _meta: {
            ...baseCandidate._meta,
            source: SOURCE,
            route: ROUTE,
            data_version: CANDIDATE_VERSION,
            hash_strategy: HASH_STRATEGY,
            match_id: target.match_id,
            external_id: target.external_id,
            request_url: requestUrl,
            final_url: fetchResult.final_url || requestUrl,
            http_status: Number(fetchResult.http_status || 0),
            content_type: fetchResult.content_type || null,
            body_byte_length: Number(fetchResult.body_byte_length || 0),
            fetch_body_sha256: fetchResult.body_sha256 || null,
            generated_at: generatedAt || new Date().toISOString(),
            full_html_body_stored: false,
            full_next_data_stored: false,
            full_json_printed: false,
            full_pageprops_printed: false,
            data_hash: computeStablePagePropsHash(pageProps),
        },
        matchId: Number(target.external_id),
        pageProps: baseCandidate.pageProps,
    };
    return candidate;
}

function validateCandidateShape(candidate = {}) {
    const errors = [];
    if (!isPlainObject(candidate)) return ['candidate must be an object'];
    if (!isPlainObject(candidate._meta)) errors.push('candidate missing _meta');
    if (!Object.prototype.hasOwnProperty.call(candidate, 'matchId')) errors.push('candidate missing matchId');
    if (!isPlainObject(candidate.pageProps)) errors.push('candidate missing pageProps');
    if (candidate._meta?.full_html_body_stored !== false) {
        errors.push('candidate _meta.full_html_body_stored must be false');
    }
    if (candidate._meta?.full_next_data_stored !== false) {
        errors.push('candidate _meta.full_next_data_stored must be false');
    }
    return errors;
}

function buildSkippedTargetSummary(target = {}, decision = {}, generatedAt = null) {
    return {
        ok: true,
        skipped: true,
        match_id: target.match_id,
        external_id: target.external_id,
        home_team: target.home_team,
        away_team: target.away_team,
        kickoff_time: target.kickoff_time || target.match_date || null,
        status: target.status || null,
        request_url: null,
        final_url: null,
        http_status: null,
        content_type: null,
        body_byte_length: 0,
        body_sha256: null,
        parse_status: 'skipped_existing_v2',
        next_data_parse_ok: false,
        page_props_found: false,
        stable_pageprops_hash: null,
        candidate_json_byte_length: 0,
        pageProps_top_level_keys: [],
        pageProps_path_count: 0,
        pageProps_content_path_count: 0,
        raw_data_shape_valid: false,
        has_meta: false,
        has_matchId: false,
        has_pageProps: false,
        module_presence: {},
        block_markers: [],
        suspicious_small_payload: false,
        existing_versions: decision.existing_versions || [],
        target_version_exists: true,
        target_status: 'skipped_existing_v2',
        preflight_status: 'skipped_existing_v2',
        failure_reason: decision.failure_reason,
        last_preflight_at: generatedAt,
    };
}

function buildFailedTargetSummary(target = {}, reason, context = {}, generatedAt = null) {
    const blockMarkers = context.block_markers || [];
    return {
        ok: false,
        skipped: false,
        match_id: target.match_id,
        external_id: target.external_id,
        home_team: target.home_team,
        away_team: target.away_team,
        kickoff_time: target.kickoff_time || target.match_date || null,
        status: target.status || null,
        request_url: context.request_url || buildFotMobMatchUrl(target.external_id),
        final_url: context.final_url || null,
        http_status: context.http_status || null,
        content_type: context.content_type || null,
        body_byte_length: Number(context.body_byte_length || 0),
        body_sha256: context.body_sha256 || null,
        parse_status: context.parse_status || 'failed',
        next_data_parse_ok: false,
        page_props_found: false,
        stable_pageprops_hash: null,
        candidate_json_byte_length: 0,
        pageProps_top_level_keys: [],
        pageProps_path_count: 0,
        pageProps_content_path_count: 0,
        raw_data_shape_valid: false,
        has_meta: false,
        has_matchId: false,
        has_pageProps: false,
        module_presence: {},
        block_markers: blockMarkers,
        suspicious_small_payload:
            Number(context.body_byte_length || 0) > 0 && Number(context.body_byte_length || 0) < 5000,
        existing_versions: context.existing_versions || [],
        target_version_exists: context.target_version_exists === true,
        target_status: blockMarkers.length > 0 ? 'blocked' : 'preflight_failed',
        preflight_status: blockMarkers.length > 0 ? 'blocked' : 'failed',
        failure_reason: reason,
        last_preflight_at: generatedAt,
    };
}

function buildSuccessfulTargetSummary(target = {}, fetchResult = {}, pageProps = {}, generatedAt = null) {
    const candidate = buildPagePropsV2Candidate({ target, pageProps, fetchResult, generatedAt });
    const shapeErrors = validateCandidateShape(candidate);
    const pagePropsPaths = listJsonPaths(pageProps);
    const contentPaths = listJsonPaths(isPlainObject(pageProps.content) ? pageProps.content : {});
    const stableHash = computeStablePagePropsHash(candidate);
    const modulePresence = summarizeModulePresence(pageProps);
    const candidateByteLength = jsonByteLength(candidate);
    return {
        ok: shapeErrors.length === 0,
        skipped: false,
        match_id: target.match_id,
        external_id: target.external_id,
        home_team: target.home_team,
        away_team: target.away_team,
        kickoff_time: target.kickoff_time || target.match_date || null,
        status: target.status || null,
        request_url: fetchResult.request_url || buildFotMobMatchUrl(target.external_id),
        final_url: fetchResult.final_url || fetchResult.request_url || buildFotMobMatchUrl(target.external_id),
        http_status: fetchResult.http_status,
        content_type: fetchResult.content_type,
        body_byte_length: Number(fetchResult.body_byte_length || 0),
        body_sha256: fetchResult.body_sha256 || null,
        parse_status:
            shapeErrors.length === 0 ? 'pageprops_v2_parsed' : `candidate_shape_invalid:${shapeErrors.join(',')}`,
        next_data_parse_ok: true,
        page_props_found: true,
        stable_pageprops_hash: shapeErrors.length === 0 ? stableHash : null,
        candidate_json_byte_length: candidateByteLength,
        pageProps_top_level_keys: topLevelKeys(pageProps),
        pageProps_path_count: pagePropsPaths.length,
        pageProps_content_path_count: contentPaths.length,
        pageProps_shape_summary: summarizeJsonShape(pageProps),
        candidate_shape_summary: summarizeJsonShape(candidate),
        raw_data_shape_valid: shapeErrors.length === 0,
        has_meta: isPlainObject(candidate._meta),
        has_matchId: Object.prototype.hasOwnProperty.call(candidate, 'matchId'),
        has_pageProps: isPlainObject(candidate.pageProps),
        module_presence: modulePresence,
        block_markers: [],
        suspicious_small_payload: candidateByteLength < 5000,
        existing_versions: target.existing_versions || [],
        target_version_exists: false,
        target_status: shapeErrors.length === 0 ? 'preflight_passed' : 'preflight_failed',
        preflight_status: shapeErrors.length === 0 ? 'hash_baseline_ready' : 'failed',
        failure_reason: shapeErrors.length === 0 ? null : `CANDIDATE_SHAPE_INVALID:${shapeErrors.join(';')}`,
        last_preflight_at: generatedAt,
    };
}

async function preflightTarget(target = {}, index, dependencies = {}, generatedAt = null) {
    const decision = buildExistingVersionDecision(target.existingRows || []);
    if (!decision.should_fetch) return buildSkippedTargetSummary(target, decision, generatedAt);

    const fetchHtmlFn = dependencies.fetchHtmlFn || fetchHtml;
    const requestUrl = buildFotMobMatchUrl(target.external_id);
    const fetchResult = await fetchHtmlFn(requestUrl, { fetchFn: dependencies.fetchFn });
    const blockDetection = isSystemicBlockedFetch(fetchResult);
    if (blockDetection.blocked) {
        return buildFailedTargetSummary(
            target,
            blockDetection.markers.join(',') || fetchResult.error || 'SYSTEMIC_BLOCK_DETECTED',
            {
                ...fetchResult,
                block_markers: blockDetection.markers,
                parse_status: 'blocked',
                existing_versions: decision.existing_versions,
                target_version_exists: decision.target_version_exists,
            },
            generatedAt
        );
    }
    if (!fetchResult.ok) {
        return buildFailedTargetSummary(
            target,
            fetchResult.error || `HTTP_${fetchResult.http_status || 0}`,
            {
                ...fetchResult,
                parse_status: 'http_failed',
                existing_versions: decision.existing_versions,
                target_version_exists: decision.target_version_exists,
            },
            generatedAt
        );
    }

    const extraction = extractNextDataJsonFromHtml(fetchResult.body);
    if (!extraction.ok) {
        return buildFailedTargetSummary(
            target,
            extraction.error,
            {
                ...fetchResult,
                parse_status: 'next_data_parse_failed',
                existing_versions: decision.existing_versions,
                target_version_exists: decision.target_version_exists,
            },
            generatedAt
        );
    }
    const pageProps = getPageProps(extraction.data);
    if (!pageProps) {
        return buildFailedTargetSummary(
            target,
            'PAGE_PROPS_NOT_FOUND',
            {
                ...fetchResult,
                parse_status: 'page_props_missing',
                existing_versions: decision.existing_versions,
                target_version_exists: decision.target_version_exists,
            },
            generatedAt
        );
    }

    const summary = buildSuccessfulTargetSummary(
        { ...target, existing_versions: decision.existing_versions },
        fetchResult,
        pageProps,
        generatedAt
    );
    return { ...summary, sequence_index: index + 1 };
}

function buildTargetContexts(candidates = [], existingRows = []) {
    const groupedRows = groupRowsByMatchId(existingRows);
    return candidates.map(target => ({
        ...target,
        existingRows: groupedRows.get(target.match_id) || [],
    }));
}

function computeResultStatus(targetSummaries = []) {
    const successCount = targetSummaries.filter(target => target.preflight_status === 'hash_baseline_ready').length;
    const skippedExistingV2Count = targetSummaries.filter(
        target => target.preflight_status === 'skipped_existing_v2'
    ).length;
    const blockedCount = targetSummaries.filter(target => target.preflight_status === 'blocked').length;
    const failedCount = targetSummaries.filter(target => target.preflight_status === 'failed').length;
    if (blockedCount > 0) {
        return {
            successCount,
            skippedExistingV2Count,
            failedCount,
            blockedCount,
            targetPopulationStatus: 'blocked',
            requiredNextStep: 'source_or_rate_limit_review',
        };
    }
    if (successCount === TARGET_COUNT && failedCount === 0 && skippedExistingV2Count === 0) {
        return {
            successCount,
            skippedExistingV2Count,
            failedCount,
            blockedCount,
            targetPopulationStatus: 'ready_for_controlled_write_authorization',
            requiredNextStep: 'single_league_small_batch_controlled_pageprops_v2_write_authorization',
        };
    }
    return {
        successCount,
        skippedExistingV2Count,
        failedCount,
        blockedCount,
        targetPopulationStatus: 'partial_preflight_completed',
        requiredNextStep: 'review_failed_targets_before_write_authorization',
    };
}

function buildCoverageSummary(targetSummaries = []) {
    const passed = targetSummaries.filter(target => target.preflight_status === 'hash_baseline_ready');
    const moduleCoverage = {};
    for (const modulePath of MODULE_PRESENCE_PATHS) {
        moduleCoverage[modulePath] = passed.filter(target => target.module_presence?.[modulePath] === true).length;
    }
    return {
        pageProps_found_count: targetSummaries.filter(target => target.page_props_found).length,
        raw_data_shape_valid_count: targetSummaries.filter(target => target.raw_data_shape_valid).length,
        has_meta_count: targetSummaries.filter(target => target.has_meta).length,
        has_matchId_count: targetSummaries.filter(target => target.has_matchId).length,
        has_pageProps_count: targetSummaries.filter(target => target.has_pageProps).length,
        module_coverage: moduleCoverage,
        suspicious_small_payloads: targetSummaries
            .filter(target => target.suspicious_small_payload)
            .map(target => target.external_id),
        block_captcha_markers: [...new Set(targetSummaries.flatMap(target => target.block_markers || []))].sort(),
    };
}

function summarizeTargetForManifest(summary = {}) {
    return {
        http_status: summary.http_status,
        content_type: summary.content_type,
        parse_status: summary.parse_status,
        next_data_parse_ok: summary.next_data_parse_ok,
        page_props_found: summary.page_props_found,
        raw_data_shape_valid: summary.raw_data_shape_valid,
        has_meta: summary.has_meta,
        has_matchId: summary.has_matchId,
        has_pageProps: summary.has_pageProps,
        candidate_json_byte_length: summary.candidate_json_byte_length,
        pageProps_top_level_keys: summary.pageProps_top_level_keys,
        pageProps_path_count: summary.pageProps_path_count,
        pageProps_content_path_count: summary.pageProps_content_path_count,
        module_presence: summary.module_presence,
        suspicious_small_payload: summary.suspicious_small_payload,
        block_markers: summary.block_markers,
    };
}

function updateManifestWithPreflight(manifest = {}, targetSummaries = [], generatedAt = null) {
    const byExternalId = new Map(targetSummaries.map(summary => [summary.external_id, summary]));
    const status = computeResultStatus(targetSummaries);
    const updated = jsonClone(manifest);
    updated.candidate_targets = updated.candidate_targets.map(target => {
        const summary = byExternalId.get(normalizeText(target.external_id));
        if (!summary) return target;
        return {
            ...target,
            existing_versions: summary.existing_versions || target.existing_versions || [],
            target_status: summary.target_status,
            preflight_status: summary.preflight_status,
            baseline_hash: summary.preflight_status === 'hash_baseline_ready' ? summary.stable_pageprops_hash : null,
            last_preflight_at: summary.last_preflight_at || generatedAt,
            write_status: 'not_started',
            write_attempt_count: 0,
            failure_reason: summary.failure_reason || null,
            source_fidelity_notes:
                summary.preflight_status === 'hash_baseline_ready'
                    ? 'pageprops_v2_no_write_preflight_passed_no_full_body_or_pageprops_saved'
                    : `pageprops_v2_no_write_preflight_${summary.preflight_status}`,
            pageprops_summary: summarizeTargetForManifest(summary),
            required_next_step:
                summary.preflight_status === 'hash_baseline_ready'
                    ? 'controlled_write_authorization_required'
                    : 'review_before_write_authorization',
            updated_at: generatedAt,
        };
    });
    updated.target_population_status = status.targetPopulationStatus;
    updated.required_next_step = status.requiredNextStep;
    updated.preflight_passed_count = status.successCount;
    updated.preflight_failed_count = status.failedCount;
    updated.preflight_blocked_count = status.blockedCount;
    updated.skipped_existing_v2_count = status.skippedExistingV2Count;
    updated.baseline_hash_populated_count = status.successCount;
    updated.small_batch_pageprops_v2_preflight_result = {
        phase: PHASE,
        generated_at: generatedAt,
        attempted_target_count: targetSummaries.length,
        skipped_existing_v2_count: status.skippedExistingV2Count,
        success_count: status.successCount,
        failed_count: status.failedCount,
        blocked_count: status.blockedCount,
        request_count: targetSummaries.filter(target => !target.skipped).length,
        hash_strategy: HASH_STRATEGY,
        target_population_status: status.targetPopulationStatus,
        required_next_step: status.requiredNextStep,
        no_db_write: true,
        no_raw_match_data_write: true,
        no_controlled_write: true,
        no_full_body_json_pageprops_print_save: true,
    };
    updated.non_execution = {
        ...(updated.non_execution || {}),
        db_write_executed: false,
        raw_match_data_write_executed: false,
        bookmaker_odds_history_write_executed: false,
        controlled_write_executed: false,
        schema_migration_executed: false,
        parser_implementation_executed: false,
        feature_extraction_executed: false,
        training_executed: false,
        prediction_executed: false,
        browser_proxy_executed: false,
        invented_targets: false,
        fabricated_external_ids: false,
    };
    return updated;
}

function buildPreflightPayload({
    input = {},
    manifest = {},
    targetSummaries = [],
    dbBaselineBefore = {},
    dbBaselineAfter = {},
    generatedAt = null,
} = {}) {
    const resultStatus = computeResultStatus(targetSummaries);
    const coverageSummary = buildCoverageSummary(targetSummaries);
    return {
        phase: PHASE,
        ok: resultStatus.blockedCount === 0,
        preflight_only: true,
        source: SOURCE,
        route: ROUTE,
        league_id: LEAGUE_ID,
        league_name: LEAGUE_NAME,
        season: SEASON,
        manifest_path: input.manifest || MANIFEST_PATH,
        report_path: REPORT_PATH,
        batch_id: BATCH_ID,
        raw_version: CANDIDATE_VERSION,
        hash_strategy: HASH_STRATEGY,
        known_completed_targets_count: manifest.known_completed_targets?.length || 0,
        candidate_targets_count: manifest.candidate_targets?.length || 0,
        target_population_status_before: manifest.target_population_status,
        attempted_target_count: targetSummaries.length,
        skipped_existing_v2_count: resultStatus.skippedExistingV2Count,
        success_count: resultStatus.successCount,
        failed_count: resultStatus.failedCount,
        blocked_count: resultStatus.blockedCount,
        request_count: targetSummaries.filter(target => !target.skipped).length,
        target_population_status_after: resultStatus.targetPopulationStatus,
        required_next_step: resultStatus.requiredNextStep,
        coverage_summary: coverageSummary,
        target_summaries: targetSummaries.map(target => ({
            external_id: target.external_id,
            match_id: target.match_id,
            home_team: target.home_team,
            away_team: target.away_team,
            kickoff_time: target.kickoff_time,
            status: target.status,
            http_status: target.http_status,
            parse_status: target.parse_status,
            stable_pageprops_hash: target.stable_pageprops_hash,
            preflight_status: target.preflight_status,
            failure_reason: target.failure_reason,
            pageProps_path_count: target.pageProps_path_count,
            pageProps_content_path_count: target.pageProps_content_path_count,
            raw_data_shape_valid: target.raw_data_shape_valid,
            has_meta: target.has_meta,
            has_matchId: target.has_matchId,
            has_pageProps: target.has_pageProps,
            suspicious_small_payload: target.suspicious_small_payload,
            block_markers: target.block_markers,
        })),
        db_baseline_before: dbBaselineBefore,
        db_baseline_after: dbBaselineAfter,
        db_row_counts_unchanged: JSON.stringify(dbBaselineBefore) === JSON.stringify(dbBaselineAfter),
        generated_at: generatedAt,
        db_write_executed: false,
        raw_match_data_write_executed: false,
        bookmaker_odds_history_write_executed: false,
        controlled_write_executed: false,
        schema_migration_executed: false,
        matches_write_executed: false,
        parser_implementation_executed: false,
        feature_extraction_executed: false,
        training_executed: false,
        prediction_executed: false,
        body_printed: false,
        body_saved: false,
        full_json_printed: false,
        full_json_saved: false,
        full_pageprops_printed: false,
        full_pageprops_saved: false,
        browser_used: false,
        proxy_used: false,
        retry_count: 0,
    };
}

function markdownTableRow(values = []) {
    return `| ${values.map(value => normalizeText(value)).join(' | ')} |`;
}

function buildReport(payload = {}) {
    const rows = payload.target_summaries || [];
    const coverage = payload.coverage_summary || {};
    const db = payload.db_baseline_after || payload.db_baseline_before || {};
    const statusDistribution = rows.reduce((acc, row) => {
        const key = row.preflight_status || 'unknown';
        acc[key] = (acc[key] || 0) + 1;
        return acc;
    }, {});
    const targetRows = rows.map(row =>
        markdownTableRow([
            row.external_id,
            row.match_id,
            row.home_team,
            row.away_team,
            row.kickoff_time,
            row.status,
            row.http_status,
            row.parse_status,
            row.stable_pageprops_hash,
            row.preflight_status,
            row.failure_reason || '',
        ])
    );
    return [
        '# Single-League Small-Batch pageProps v2 Preflight - Phase 5.21L2T',
        '',
        '## 1. Executive summary',
        '',
        '- T0C discovered 50 real Ligue 1 2025/2026 candidate targets.',
        '- L2T performed match detail pageProps v2 no-write preflight for manifest candidates only.',
        '- No DB write, no raw_match_data write, no controlled write, and no parser/features/training were executed.',
        '',
        '## 2. Current DB baseline',
        '',
        markdownTableRow(['table', 'rows']),
        markdownTableRow(['---', '---']),
        ...PROTECTED_TABLES.map(table => markdownTableRow([table, db[table]])),
        '',
        '## 3. Authorization / guardrails',
        '',
        '- network_authorization=yes',
        '- match_detail_preflight_authorization=yes',
        `- target_count=${TARGET_COUNT}`,
        '- concurrency=1',
        '- retry=0',
        '- no browser/proxy',
        '- no DB write',
        '- no controlled write',
        '- no full body/json/pageProps print/save',
        '',
        '## 4. Manifest input summary',
        '',
        `- manifest path: \`${payload.manifest_path}\``,
        `- known_completed_targets=${payload.known_completed_targets_count}`,
        `- candidate_targets=${payload.candidate_targets_count}`,
        `- target_population_status before preflight: \`${payload.target_population_status_before}\``,
        '',
        '## 5. Preflight result',
        '',
        `- attempted_target_count=${payload.attempted_target_count}`,
        `- skipped_existing_v2_count=${payload.skipped_existing_v2_count}`,
        `- success_count=${payload.success_count}`,
        `- failed_count=${payload.failed_count}`,
        `- blocked_count=${payload.blocked_count}`,
        `- request_count=${payload.request_count}`,
        `- hash_strategy=${payload.hash_strategy}`,
        `- target_population_status after preflight: \`${payload.target_population_status_after}\``,
        `- required_next_step: \`${payload.required_next_step}\``,
        '',
        '## 6. Candidate target preflight summary',
        '',
        markdownTableRow([
            'external_id',
            'match_id',
            'home_team',
            'away_team',
            'kickoff_time',
            'status',
            'http_status',
            'parse_status',
            'stable_pageprops_hash',
            'preflight_status',
            'failure_reason',
        ]),
        markdownTableRow(['---', '---', '---', '---', '---', '---', '---', '---', '---', '---', '---']),
        ...targetRows,
        '',
        '## 7. Coverage / shape summary',
        '',
        `- pageProps_found_count=${coverage.pageProps_found_count || 0}`,
        `- raw_data_shape_valid_count=${coverage.raw_data_shape_valid_count || 0}`,
        `- has_meta_count=${coverage.has_meta_count || 0}`,
        `- has_matchId_count=${coverage.has_matchId_count || 0}`,
        `- has_pageProps_count=${coverage.has_pageProps_count || 0}`,
        `- module coverage: \`${JSON.stringify(coverage.module_coverage || {})}\``,
        `- suspicious small payloads: \`${(coverage.suspicious_small_payloads || []).join(',') || 'none'}\``,
        `- block/captcha markers: \`${(coverage.block_captcha_markers || []).join(',') || 'none'}\``,
        '',
        '## 8. Manifest update result',
        '',
        '- manifest updated: yes',
        `- candidate_targets count: ${payload.candidate_targets_count}`,
        `- baseline_hash populated count: ${payload.success_count}`,
        `- preflight_status distribution: \`${JSON.stringify(statusDistribution)}\``,
        `- target_population_status: \`${payload.target_population_status_after}\``,
        `- required_next_step: \`${payload.required_next_step}\``,
        '',
        '## 9. DB safety result',
        '',
        `- matches=${db.matches}`,
        `- raw_match_data=${db.raw_match_data}`,
        `- bookmaker_odds_history=${db.bookmaker_odds_history}`,
        `- l3_features=${db.l3_features}`,
        `- match_features_training=${db.match_features_training}`,
        `- predictions=${db.predictions}`,
        `- row counts unchanged: ${payload.db_row_counts_unchanged}`,
        '',
        '## 10. Verification results',
        '',
        '- To be completed after local tests, PR CI, and main push CI.',
        '',
        '## 11. Recommended next phase',
        '',
        payload.target_population_status_after === 'ready_for_controlled_write_authorization'
            ? '- Phase 5.21L2U: single-league small-batch controlled pageProps v2 write authorization / planning.'
            : '- Phase 5.21L2T1: failed-target review / retry policy planning.',
        '- Any future write requires explicit final DB-write authorization, baseline hash gates, a controlled transaction, and no parser/features/training.',
        '',
        '## 12. Explicit non-execution',
        '',
        '- no DB writes',
        '- no raw_match_data writes',
        '- no bookmaker_odds_history writes',
        '- no controlled write',
        '- no schema migration',
        '- no matches writes',
        '- no parser implementation',
        '- no feature extraction',
        '- no l3_features write',
        '- no match_features_training write',
        '- no training/prediction',
        '- no browser/proxy/captcha bypass',
        '- no retry',
        '- no full raw_data/pageProps/source body print/save',
        '- no file deletion',
        '- no invented external_id / fake target data',
        '',
    ].join('\n');
}

function buildFailurePayload({ input = {}, reason, errors = [], dbBaselineBefore = null } = {}) {
    return {
        phase: PHASE,
        ok: false,
        blocked: true,
        preflight_only: true,
        source: SOURCE,
        route: ROUTE,
        manifest_path: input.manifest || MANIFEST_PATH,
        batch_id: BATCH_ID,
        failure_reason: reason,
        errors,
        db_baseline_before: dbBaselineBefore,
        db_write_executed: false,
        raw_match_data_write_executed: false,
        controlled_write_executed: false,
        schema_migration_executed: false,
        parser_implementation_executed: false,
        feature_extraction_executed: false,
        training_executed: false,
        prediction_executed: false,
        body_printed: false,
        body_saved: false,
        full_json_printed: false,
        full_json_saved: false,
        full_pageprops_printed: false,
        full_pageprops_saved: false,
        browser_used: false,
        proxy_used: false,
        retry_count: 0,
    };
}

async function queryReadOnly(client, sql, params = []) {
    const normalized = normalizeText(sql).replace(/\s+/g, ' ').toLowerCase();
    if (!normalized.startsWith('select ')) throw new Error('NON_SELECT_SQL_BLOCKED');
    if (/\b(insert|update|delete|truncate|alter|drop|create|grant|revoke|copy|for update|lock)\b/i.test(normalized)) {
        throw new Error('SQL_WRITE_OR_LOCK_BLOCKED');
    }
    return client.query(sql, params);
}

async function loadProtectedTableBaselineRows(client) {
    const result = await queryReadOnly(
        client,
        `
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
        `,
        []
    );
    return result.rows || [];
}

async function loadExistingRawVersions(client, matchIds = []) {
    const result = await queryReadOnly(
        client,
        `
        SELECT id, match_id, external_id, data_version, data_hash, collected_at
        FROM raw_match_data
        WHERE match_id = ANY($1::text[])
        ORDER BY match_id, data_version, id
        `,
        [matchIds]
    );
    return result.rows || [];
}

function createDefaultPool() {
    const { Pool } = require('pg');
    const { buildDbConnectionConfig } = require('./helpers/dbBlueprint');
    return new Pool(buildDbConnectionConfig());
}

function readManifestFile(manifestPath = MANIFEST_PATH) {
    return JSON.parse(fs.readFileSync(path.resolve(process.cwd(), manifestPath), 'utf8'));
}

function writeJsonFile(filePath, value) {
    fs.writeFileSync(path.resolve(process.cwd(), filePath), `${JSON.stringify(value, null, 4)}\n`);
}

function writeReportFile(filePath, markdown) {
    fs.writeFileSync(path.resolve(process.cwd(), filePath), markdown);
}

async function buildSingleLeagueSmallBatchPagePropsV2Preflight({
    input = {},
    manifest = {},
    existingRows = [],
    protectedTableRowsBefore = [],
    protectedTableRowsAfter = [],
    generatedAt = null,
    dependencies = {},
} = {}) {
    const dbBaselineBefore = buildProtectedTableBaseline(protectedTableRowsBefore);
    const beforeErrors = validateProtectedTableBaseline(dbBaselineBefore);
    if (beforeErrors.length > 0) {
        return buildFailurePayload({
            input,
            reason: `DB_BASELINE_INVALID:${beforeErrors.join(';')}`,
            errors: beforeErrors,
            dbBaselineBefore,
        });
    }
    const manifestValidation = validateManifest(manifest);
    if (!manifestValidation.ok) {
        return buildFailurePayload({
            input,
            reason: `MANIFEST_INVALID:${manifestValidation.errors.join(';')}`,
            errors: manifestValidation.errors,
            dbBaselineBefore,
        });
    }
    const targets = buildTargetContexts(manifestValidation.candidates, existingRows);
    const targetSummaries = [];
    for (let index = 0; index < targets.length; index += 1) {
        const summary = await preflightTarget(targets[index], index, dependencies, generatedAt);
        targetSummaries.push(summary);
        if (summary.preflight_status === 'blocked') break;
    }
    const dbBaselineAfter = buildProtectedTableBaseline(
        protectedTableRowsAfter.length > 0 ? protectedTableRowsAfter : protectedTableRowsBefore
    );
    const afterErrors = validateProtectedTableBaseline(dbBaselineAfter);
    if (afterErrors.length > 0) {
        return buildFailurePayload({
            input,
            reason: `DB_BASELINE_AFTER_INVALID:${afterErrors.join(';')}`,
            errors: afterErrors,
            dbBaselineBefore,
        });
    }
    return buildPreflightPayload({
        input,
        manifest,
        targetSummaries,
        dbBaselineBefore,
        dbBaselineAfter,
        generatedAt,
    });
}

async function runCli(argv = process.argv.slice(2), dependencies = {}) {
    const parsed = Array.isArray(argv) ? parseArgs(argv) : argv;
    const validation = validatePreflightInput(parsed);
    const output = dependencies.output || (payload => process.stdout.write(`${JSON.stringify(payload, null, 2)}\n`));
    if (!validation.ok) {
        const payload = buildFailurePayload({
            input: normalizePreflightInput(parsed),
            reason: `INPUT_INVALID:${validation.errors.join(';')}`,
            errors: validation.errors,
        });
        output(payload);
        return { status: 1, payload };
    }

    const input = validation.value;
    const generatedAt = dependencies.generatedAt || new Date().toISOString();
    const pool =
        dependencies.client ||
        dependencies.manifest ||
        dependencies.existingRows ||
        dependencies.protectedTableRowsBefore ||
        dependencies.protectedTableRowsAfter
            ? null
            : createDefaultPool();
    const client = dependencies.client || pool;
    try {
        const manifest = dependencies.manifest || readManifestFile(input.manifest);
        const manifestValidation = validateManifest(manifest);
        const candidateMatchIds = manifestValidation.candidates.map(target => target.match_id);
        const protectedTableRowsBefore =
            dependencies.protectedTableRowsBefore || (await loadProtectedTableBaselineRows(client));
        const existingRows = dependencies.existingRows || (await loadExistingRawVersions(client, candidateMatchIds));
        const payload = await buildSingleLeagueSmallBatchPagePropsV2Preflight({
            input,
            manifest,
            existingRows,
            protectedTableRowsBefore,
            protectedTableRowsAfter: protectedTableRowsBefore,
            generatedAt,
            dependencies,
        });
        if (payload.ok || payload.target_population_status_after) {
            const updatedManifest = updateManifestWithPreflight(manifest, payload.target_summaries || [], generatedAt);
            const protectedTableRowsAfter =
                dependencies.protectedTableRowsAfter || (await loadProtectedTableBaselineRows(client));
            payload.db_baseline_after = buildProtectedTableBaseline(protectedTableRowsAfter);
            payload.db_row_counts_unchanged =
                JSON.stringify(payload.db_baseline_before) === JSON.stringify(payload.db_baseline_after);
            if (dependencies.writeManifest !== false) {
                (dependencies.writeManifestFile || writeJsonFile)(input.manifest, updatedManifest);
            }
            const reportMarkdown = buildReport(payload);
            if (dependencies.writeReport !== false) {
                (dependencies.writeReportFile || writeReportFile)(REPORT_PATH, reportMarkdown);
            }
            payload.manifest_updated = dependencies.writeManifest !== false;
            payload.report_updated = dependencies.writeReport !== false;
            payload.baseline_hash_populated_count = payload.success_count;
            payload.preflight_status_distribution = (payload.target_summaries || []).reduce((acc, target) => {
                acc[target.preflight_status] = (acc[target.preflight_status] || 0) + 1;
                return acc;
            }, {});
        }
        output(payload);
        return { status: payload.ok === false ? 1 : 0, payload };
    } catch (error) {
        const payload = buildFailurePayload({
            input,
            reason: error.message,
        });
        output(payload);
        return { status: 1, payload };
    } finally {
        if (pool && typeof pool.end === 'function') await pool.end();
    }
}

module.exports = {
    PHASE,
    MANIFEST_PATH,
    REPORT_PATH,
    SOURCE,
    ROUTE,
    LEAGUE_ID,
    LEAGUE_NAME,
    SEASON,
    BATCH_ID,
    TARGET_COUNT,
    parseArgs,
    normalizeBooleanFlag,
    validatePreflightInput,
    validateManifest,
    validateCandidateTargets,
    buildProtectedTableBaseline,
    buildExistingVersionDecision,
    detectBlockMarkers,
    buildPagePropsV2Candidate,
    validateCandidateShape,
    buildSuccessfulTargetSummary,
    buildSingleLeagueSmallBatchPagePropsV2Preflight,
    updateManifestWithPreflight,
    buildCoverageSummary,
    buildReport,
    queryReadOnly,
    loadProtectedTableBaselineRows,
    loadExistingRawVersions,
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
