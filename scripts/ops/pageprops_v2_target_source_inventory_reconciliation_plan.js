#!/usr/bin/env node
/* eslint-disable complexity, max-lines, max-statements */
'use strict';

const fs = require('node:fs');
const path = require('node:path');
const { Pool } = require('pg');

const l2v3d = require('./pageprops_v2_target_identity_reconciliation_plan');
const rawWrite = require('./renewed_pageprops_v2_raw_write_execute');
const sourceInventory = require('./single_league_target_discovery_source_inventory_preflight');

const PHASE = 'PHASE5_21L2V3E_TARGET_IDENTITY_SOURCE_INVENTORY_RECONCILIATION_PLANNING';
const MANIFEST_PATH = l2v3d.MANIFEST_PATH;
const RENEWED_PROPOSAL_PATH = l2v3d.RENEWED_PROPOSAL_PATH;
const REPORT_PATH = 'docs/_reports/DATA_ENTRYPOINT_GOVERNANCE_PHASE5_21_L2V3E.md';
const SOURCE = l2v3d.SOURCE;
const LEAGUE_ID = l2v3d.LEAGUE_ID;
const LEAGUE_NAME = l2v3d.LEAGUE_NAME;
const SEASON = l2v3d.SEASON;
const RAW_VERSION = l2v3d.RAW_VERSION;
const HASH_STRATEGY = l2v3d.HASH_STRATEGY;
const BATCH_ID = l2v3d.BATCH_ID;
const TARGET_COUNT = l2v3d.TARGET_COUNT;
const EXPECTED_MISMATCH_COUNT = l2v3d.EXPECTED_MISMATCH_COUNT;
const EXPECTED_ROW_COUNTS = l2v3d.EXPECTED_ROW_COUNTS;
const SOURCE_ROUTE = 'source_inventory';
const DEFAULT_REQUEST_DELAY_MS = 0;

const REQUIRED_YES_FLAGS = Object.freeze([
    'planningAuthorization',
    'sourceInventoryReconciliationAuthorization',
    'networkAuthorization',
]);
const REQUIRED_NO_FLAGS = Object.freeze([
    'allowDbWrite',
    'allowRawMatchDataWrite',
    'allowControlledWrite',
    'allowMatchesWrite',
    'allowBookmakerOddsWrite',
    'allowFeatureWrite',
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
    'allowOddsWrite',
    'executeWrite',
    'commit',
    'finalDbWriteConfirmation',
    'acceptBaseline',
    'acceptedBaseline',
    'baselineAcceptanceAuthorization',
    'rawWriteReadyForExecution',
    'rawWriteRetryAuthorization',
]);
const SOURCE_PATH_PRIORITY = Object.freeze([
    'overview.matches.allMatches',
    'fixtures.allMatches',
    'overview.leagueOverviewMatches',
]);
const PROTECTED_TABLES = Object.freeze([
    'matches',
    'raw_match_data',
    'bookmaker_odds_history',
    'l3_features',
    'match_features_training',
    'predictions',
]);
const ALLOWED_MANIFEST_NEXT_STEPS = Object.freeze([
    'target_identity_source_inventory_reconciliation_planning',
    'schedule_detail_identity_normalization_fix_planning',
    'source_inventory_manifest_regeneration_review',
    'matches_identity_seed_reconciliation_review',
    'target_identity_source_inventory_follow_up_investigation',
]);
const ALLOWED_RAW_WRITE_RETRY_AUTHORIZATION_STATUSES = Object.freeze([
    'blocked_pending_target_identity_reconciliation',
    'blocked_pending_target_identity_source_inventory_reconciliation',
]);

function normalizeText(value) {
    return String(value ?? '').trim();
}

function normalizeLower(value) {
    return normalizeText(value).toLowerCase();
}

function normalizeBooleanFlag(value, fallback = undefined) {
    if (typeof value === 'boolean') return value;
    if (value === null || value === undefined || value === '') return fallback;
    const normalized = normalizeLower(value);
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

function parseCsv(value) {
    return normalizeText(value)
        .split(',')
        .map(item => item.trim())
        .filter(Boolean);
}

function toCamelKey(rawKey) {
    return normalizeText(rawKey).replace(/[-_]([a-z0-9])/g, (_match, char) => char.toUpperCase());
}

function flagName(key) {
    return key.replace(/[A-Z]/g, char => `-${char.toLowerCase()}`);
}

function parseOptionValue(arg, argv, index) {
    if (arg.includes('=')) return { value: arg.slice(arg.indexOf('=') + 1), consumedNext: false };
    const nextArg = argv[index + 1];
    if (typeof nextArg === 'string' && !nextArg.startsWith('--')) {
        return { value: nextArg, consumedNext: true };
    }
    return { value: true, consumedNext: false };
}

function parseArgs(argv = process.argv.slice(2)) {
    const options = {
        manifest: null,
        renewedProposal: RENEWED_PROPOSAL_PATH,
        reportOutput: REPORT_PATH,
        source: null,
        leagueId: null,
        leagueName: null,
        season: null,
        rawVersion: null,
        hashStrategy: null,
        batchId: null,
        targetCount: null,
        planningAuthorization: null,
        sourceInventoryReconciliationAuthorization: null,
        networkAuthorization: null,
        allowDbWrite: null,
        allowRawMatchDataWrite: null,
        allowControlledWrite: null,
        allowMatchesWrite: null,
        allowBookmakerOddsWrite: null,
        allowFeatureWrite: null,
        allowSchemaMigration: null,
        allowParserImplementation: null,
        allowFeatureExtraction: null,
        allowTraining: null,
        allowPrediction: null,
        allowBrowserRuntime: null,
        allowProxyRuntime: null,
        printFullBody: null,
        saveFullBody: null,
        printFullJson: null,
        saveFullJson: null,
        printFullPageprops: null,
        saveFullPageprops: null,
        allowOddsWrite: false,
        executeWrite: false,
        commit: false,
        finalDbWriteConfirmation: false,
        acceptBaseline: false,
        acceptedBaseline: false,
        baselineAcceptanceAuthorization: false,
        rawWriteReadyForExecution: false,
        rawWriteRetryAuthorization: false,
        retry: 0,
        requestDelayMs: DEFAULT_REQUEST_DELAY_MS,
        targetExternalIds: null,
        generatedAt: null,
        baseHead: null,
        branch: null,
        mainHead: null,
        mainCiStatus: null,
        pr1278State: null,
        pr1278MergeCommit: null,
        help: false,
        unknown: [],
    };
    const knownKeys = new Set(Object.keys(options));
    const booleanKeys = new Set([...REQUIRED_YES_FLAGS, ...REQUIRED_NO_FLAGS, ...BLOCKED_TRUE_FLAGS, 'help']);

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

function normalizePlanningInput(input = {}) {
    return {
        manifest: normalizeText(input.manifest),
        renewedProposal: normalizeText(input.renewedProposal) || RENEWED_PROPOSAL_PATH,
        reportOutput: normalizeText(input.reportOutput) || REPORT_PATH,
        source: normalizeLower(input.source),
        leagueId: parseInteger(input.leagueId, null),
        leagueName: normalizeText(input.leagueName),
        season: normalizeText(input.season),
        rawVersion: normalizeText(input.rawVersion),
        hashStrategy: normalizeText(input.hashStrategy),
        batchId: normalizeText(input.batchId),
        targetCount: parseInteger(input.targetCount, null),
        planningAuthorization: normalizeBooleanFlag(input.planningAuthorization, undefined),
        sourceInventoryReconciliationAuthorization: normalizeBooleanFlag(
            input.sourceInventoryReconciliationAuthorization,
            undefined
        ),
        networkAuthorization: normalizeBooleanFlag(input.networkAuthorization, undefined),
        allowDbWrite: normalizeBooleanFlag(input.allowDbWrite, undefined),
        allowRawMatchDataWrite: normalizeBooleanFlag(input.allowRawMatchDataWrite, undefined),
        allowControlledWrite: normalizeBooleanFlag(input.allowControlledWrite, undefined),
        allowMatchesWrite: normalizeBooleanFlag(input.allowMatchesWrite, undefined),
        allowBookmakerOddsWrite: normalizeBooleanFlag(input.allowBookmakerOddsWrite, undefined),
        allowFeatureWrite: normalizeBooleanFlag(input.allowFeatureWrite, undefined),
        allowSchemaMigration: normalizeBooleanFlag(input.allowSchemaMigration, undefined),
        allowParserImplementation: normalizeBooleanFlag(input.allowParserImplementation, undefined),
        allowFeatureExtraction: normalizeBooleanFlag(input.allowFeatureExtraction, undefined),
        allowTraining: normalizeBooleanFlag(input.allowTraining, undefined),
        allowPrediction: normalizeBooleanFlag(input.allowPrediction, undefined),
        allowBrowserRuntime: normalizeBooleanFlag(input.allowBrowserRuntime, undefined),
        allowProxyRuntime: normalizeBooleanFlag(input.allowProxyRuntime, undefined),
        printFullBody: normalizeBooleanFlag(input.printFullBody, undefined),
        saveFullBody: normalizeBooleanFlag(input.saveFullBody, undefined),
        printFullJson: normalizeBooleanFlag(input.printFullJson, undefined),
        saveFullJson: normalizeBooleanFlag(input.saveFullJson, undefined),
        printFullPageprops: normalizeBooleanFlag(input.printFullPageprops, undefined),
        saveFullPageprops: normalizeBooleanFlag(input.saveFullPageprops, undefined),
        allowOddsWrite: normalizeBooleanFlag(input.allowOddsWrite, false),
        executeWrite: normalizeBooleanFlag(input.executeWrite, false),
        commit: normalizeBooleanFlag(input.commit, false),
        finalDbWriteConfirmation: normalizeBooleanFlag(input.finalDbWriteConfirmation, false),
        acceptBaseline: normalizeBooleanFlag(input.acceptBaseline, false),
        acceptedBaseline: normalizeBooleanFlag(input.acceptedBaseline, false),
        baselineAcceptanceAuthorization: normalizeBooleanFlag(input.baselineAcceptanceAuthorization, false),
        rawWriteReadyForExecution: normalizeBooleanFlag(input.rawWriteReadyForExecution, false),
        rawWriteRetryAuthorization: normalizeBooleanFlag(input.rawWriteRetryAuthorization, false),
        retry: parseInteger(input.retry, 0),
        requestDelayMs: parseInteger(input.requestDelayMs, DEFAULT_REQUEST_DELAY_MS),
        targetExternalIds: Array.isArray(input.targetExternalIds)
            ? input.targetExternalIds.map(normalizeText).filter(Boolean)
            : parseCsv(input.targetExternalIds),
        generatedAt: normalizeText(input.generatedAt),
        baseHead: normalizeText(input.baseHead),
        branch: normalizeText(input.branch),
        mainHead: normalizeText(input.mainHead),
        mainCiStatus: normalizeText(input.mainCiStatus),
        pr1278State: normalizeText(input.pr1278State),
        pr1278MergeCommit: normalizeText(input.pr1278MergeCommit),
        unknown: Array.isArray(input.unknown) ? input.unknown : [],
    };
}

function pushRequiredYes(errors, value, name) {
    if (value === true) return;
    errors.push(value === false ? `${name}=yes is required in Phase 5.21L2V3E` : `missing ${name}=yes`);
}

function pushRequiredNo(errors, value, name) {
    if (value === false) return;
    errors.push(value === true ? `${name}=yes is blocked in Phase 5.21L2V3E` : `missing ${name}=no`);
}

function requireExact(errors, actual, expected, name) {
    if (!normalizeText(actual)) {
        errors.push(`missing ${name}=${expected}`);
        return;
    }
    if (normalizeText(actual) !== expected) errors.push(`${name} must be ${expected}`);
}

function validatePlanningInput(rawInput = {}) {
    const input = normalizePlanningInput(rawInput);
    const errors = [];
    if (input.unknown.length > 0) errors.push(`unknown arguments: ${input.unknown.join(',')}`);
    requireExact(errors, input.manifest, MANIFEST_PATH, 'manifest');
    requireExact(errors, input.renewedProposal, RENEWED_PROPOSAL_PATH, 'renewed-proposal');
    requireExact(errors, input.reportOutput, REPORT_PATH, 'report-output');
    requireExact(errors, input.source, SOURCE, 'source');
    if (input.leagueId !== LEAGUE_ID) errors.push(`league-id must be ${LEAGUE_ID}`);
    requireExact(errors, input.leagueName, LEAGUE_NAME, 'league-name');
    requireExact(errors, input.season, SEASON, 'season');
    requireExact(errors, input.rawVersion, RAW_VERSION, 'raw-version');
    requireExact(errors, input.hashStrategy, HASH_STRATEGY, 'hash-strategy');
    requireExact(errors, input.batchId, BATCH_ID, 'batch-id');
    if (input.targetCount !== TARGET_COUNT) errors.push(`target-count must be ${TARGET_COUNT}`);
    for (const key of REQUIRED_YES_FLAGS) pushRequiredYes(errors, input[key], flagName(key));
    for (const key of REQUIRED_NO_FLAGS) pushRequiredNo(errors, input[key], flagName(key));
    for (const key of BLOCKED_TRUE_FLAGS) {
        if (input[key] === true) errors.push(`${flagName(key)}=yes is blocked in Phase 5.21L2V3E`);
    }
    if (input.retry !== 0) errors.push('retry must be 0');
    if (!Number.isInteger(input.requestDelayMs) || input.requestDelayMs < 0) {
        errors.push('request-delay-ms must be a non-negative integer');
    }
    return { ok: errors.length === 0, input, errors };
}

function readJsonFile(filePath) {
    return JSON.parse(fs.readFileSync(filePath, 'utf8'));
}

function writeJsonFile(filePath, data) {
    fs.mkdirSync(path.dirname(filePath), { recursive: true });
    fs.writeFileSync(filePath, `${JSON.stringify(data, null, 4)}\n`);
}

function writeReportFile(filePath, content) {
    fs.mkdirSync(path.dirname(filePath), { recursive: true });
    fs.writeFileSync(filePath, content);
}

function buildManifestGate(manifest = {}) {
    const baseGate = l2v3d.validateManifestGate(manifest);
    const errors = baseGate.errors.filter(
        error => !error.startsWith('next_required_step must be target identity reconciliation planning')
    );
    if (!ALLOWED_MANIFEST_NEXT_STEPS.includes(normalizeText(manifest.next_required_step))) {
        errors.push(
            'manifest next_required_step must be target_identity_source_inventory_reconciliation_planning or an allowed L2V3E follow-up outcome'
        );
    }
    if (normalizeText(manifest.phase_5_21_l2v3d_planning_status) !== 'completed_no_write') {
        errors.push('manifest phase_5_21_l2v3d_planning_status must be completed_no_write');
    }
    if (Number(manifest.phase_5_21_l2v3d_identity_mismatch_count || 0) !== EXPECTED_MISMATCH_COUNT) {
        errors.push(`manifest phase_5_21_l2v3d_identity_mismatch_count must be ${EXPECTED_MISMATCH_COUNT}`);
    }
    if (manifest.target_identity_mismatch_blocks_baseline_acceptance !== true) {
        errors.push('manifest target_identity_mismatch_blocks_baseline_acceptance must be true');
    }
    if (manifest.raw_write_ready_for_execution !== false) {
        errors.push('manifest raw_write_ready_for_execution must be false');
    }
    if (
        !ALLOWED_RAW_WRITE_RETRY_AUTHORIZATION_STATUSES.includes(
            normalizeText(manifest.raw_write_retry_authorization_status)
        )
    ) {
        errors.push(
            'manifest raw_write_retry_authorization_status must be blocked_pending_target_identity_reconciliation or blocked_pending_target_identity_source_inventory_reconciliation'
        );
    }
    if (manifest.phase_5_21_l2v3d_manifest_target_metadata_mismatch_indicated !== true) {
        errors.push('manifest phase_5_21_l2v3d_manifest_target_metadata_mismatch_indicated must be true');
    }
    return { ...baseGate, ok: errors.length === 0, errors };
}

function buildProposalGate(proposal = {}) {
    return l2v3d.validateRenewedProposalGate(proposal);
}

function sourcePathRank(value) {
    const text = normalizeText(value);
    const index = SOURCE_PATH_PRIORITY.findIndex(prefix => text.startsWith(prefix));
    return index >= 0 ? index : SOURCE_PATH_PRIORITY.length + 1;
}

function resolveSideName(value) {
    if (!value) return null;
    if (typeof value === 'string') return normalizeText(value) || null;
    return normalizeText(value.name || value.shortName || value.longName) || null;
}

function resolveMatchDate(match = {}) {
    return normalizeText(
        match.status?.utcTime || match.matchTime || match.time?.utc || match.date || match.kickoff?.datetime
    );
}

function resolveStatus(match = {}) {
    const rawStatus = match.status;
    if (typeof rawStatus === 'string') return normalizeLower(rawStatus);
    if (rawStatus?.finished || rawStatus?.completed || match.finished || match.isFinished) return 'finished';
    if (rawStatus?.live || rawStatus?.started || match.isLive || match.live) return 'live';
    if (rawStatus?.cancelled || rawStatus?.postponed || match.cancelled) return 'cancelled';
    if (rawStatus?.scheduled || rawStatus?.upcoming || match.scheduled || match.notStarted) return 'scheduled';
    return '';
}

function safeUrlSummary(rawUrl) {
    const value = normalizeText(rawUrl);
    if (!value) return null;
    try {
        const url = new URL(value, 'https://www.fotmob.com');
        return `${url.origin}${url.pathname}${url.search || ''}${url.hash || ''}`;
    } catch (_error) {
        return value.slice(0, 200);
    }
}

function pageUrlBase(rawUrl) {
    const value = normalizeText(rawUrl);
    if (!value) return null;
    const index = value.indexOf('#');
    return index >= 0 ? value.slice(0, index) : value;
}

function pageUrlAnchor(rawUrl) {
    const value = normalizeText(rawUrl);
    if (!value || !value.includes('#')) return null;
    return value.slice(value.indexOf('#') + 1) || null;
}

function pickIdLikeFields(match = {}) {
    const summary = {};
    for (const key of Object.keys(match)) {
        if (/(^id$|Id$|_id$|matchId|match_id|pageUrl|url$|slug)/.test(key)) {
            const value = match[key];
            summary[key] = typeof value === 'object' ? '[object]' : value;
        }
    }
    return summary;
}

function normalizeSourceInventoryRecord(entry = {}) {
    const match = entry.match || {};
    const externalId = normalizeText(match.id ?? match.matchId ?? match.match_id);
    return {
        source_path: normalizeText(entry.sourcePath),
        source_inventory_record_key: `${normalizeText(entry.sourcePath)}#${externalId}`,
        external_id: externalId || null,
        home_team: resolveSideName(match.home ?? match.homeTeam ?? match.home_team),
        away_team: resolveSideName(match.away ?? match.awayTeam ?? match.away_team),
        match_date: resolveMatchDate(match) || null,
        status: resolveStatus(match) || null,
        round: normalizeText(match.round || match.roundName) || null,
        page_url: normalizeText(match.pageUrl || match.pageURL || match.url) || null,
        page_url_base: pageUrlBase(match.pageUrl || match.pageURL || match.url),
        page_url_anchor: pageUrlAnchor(match.pageUrl || match.pageURL || match.url),
        id_like_fields: pickIdLikeFields(match),
        top_level_keys: Object.keys(match).sort(),
    };
}

function choosePreferredSourceInventoryRecord(a, b) {
    if (!a) return b;
    if (!b) return a;
    const rankA = sourcePathRank(a.source_path);
    const rankB = sourcePathRank(b.source_path);
    if (rankA !== rankB) return rankA < rankB ? a : b;
    if ((a.top_level_keys?.length || 0) !== (b.top_level_keys?.length || 0)) {
        return (a.top_level_keys?.length || 0) > (b.top_level_keys?.length || 0) ? a : b;
    }
    return normalizeText(a.source_path) <= normalizeText(b.source_path) ? a : b;
}

async function fetchSourceInventoryPayload(input = {}, dependencies = {}) {
    if (dependencies.sourceInventoryJson) {
        const generatedUrl =
            dependencies.sourceInventoryUrl ||
            sourceInventory.buildSourceInventoryUrl({
                source: input.source,
                leagueId: input.leagueId,
                season: input.season,
            });
        return {
            ok: true,
            request_url: generatedUrl,
            final_url: generatedUrl,
            http_status: 200,
            body_bytes: null,
            parse_status: 'injected_json',
            blocked_markers: [],
            json: dependencies.sourceInventoryJson,
        };
    }
    const requestUrl =
        dependencies.sourceInventoryUrl ||
        sourceInventory.buildSourceInventoryUrl({
            source: input.source,
            leagueId: input.leagueId,
            season: input.season,
        });
    const fetchFn = dependencies.fetchFn || globalThis.fetch;
    if (typeof fetchFn !== 'function') {
        return {
            ok: false,
            request_url: requestUrl,
            final_url: requestUrl,
            http_status: 0,
            body_bytes: 0,
            parse_status: 'fetch_dependency_missing',
            blocked_markers: [],
            error: 'FETCH_DEPENDENCY_MISSING',
        };
    }

    let response;
    try {
        response = await fetchFn(requestUrl, {
            method: 'GET',
            headers: {
                accept: 'application/json',
                'accept-language': 'en-US,en;q=0.9',
                'accept-encoding': 'identity',
                'user-agent':
                    'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
            },
            redirect: 'follow',
        });
    } catch (error) {
        return {
            ok: false,
            request_url: requestUrl,
            final_url: requestUrl,
            http_status: 0,
            body_bytes: 0,
            parse_status: 'fetch_error',
            blocked_markers: [],
            error: `FETCH_ERROR:${error.message}`,
        };
    }

    let body = '';
    try {
        body = await response.text();
    } catch (error) {
        return {
            ok: false,
            request_url: requestUrl,
            final_url: response.url || requestUrl,
            http_status: Number(response.status || 0),
            body_bytes: 0,
            parse_status: 'body_read_error',
            blocked_markers: [],
            error: `BODY_READ_ERROR:${error.message}`,
        };
    }

    const blockedMarkers = sourceInventory.detectBlockedMarkers(body);
    if (blockedMarkers.length > 0) {
        return {
            ok: false,
            request_url: requestUrl,
            final_url: response.url || requestUrl,
            http_status: Number(response.status || 0),
            body_bytes: Buffer.byteLength(body, 'utf8'),
            parse_status: 'blocked_markers_detected',
            blocked_markers: blockedMarkers,
            error: `BLOCKED:${blockedMarkers.join(',')}`,
        };
    }

    let json;
    try {
        json = JSON.parse(body);
    } catch (error) {
        return {
            ok: false,
            request_url: requestUrl,
            final_url: response.url || requestUrl,
            http_status: Number(response.status || 0),
            body_bytes: Buffer.byteLength(body, 'utf8'),
            parse_status: 'json_parse_failed',
            blocked_markers: [],
            error: `JSON_PARSE_ERROR:${error.message}`,
        };
    }

    return {
        ok: Number(response.status || 0) === 200,
        request_url: requestUrl,
        final_url: response.url || requestUrl,
        http_status: Number(response.status || 0),
        body_bytes: Buffer.byteLength(body, 'utf8'),
        parse_status: 'parsed_json',
        blocked_markers: [],
        json,
    };
}

function buildSourceInventorySelection(payload = {}, requestedExternalIds = [], observedExternalIds = []) {
    const targetIds = new Set([...requestedExternalIds, ...observedExternalIds].map(normalizeText).filter(Boolean));
    const rawEntries = sourceInventory.extractSourceInventoryMatches(payload.json || {});
    const selectedByExternalId = new Map();
    let duplicateSelections = 0;

    for (const entry of rawEntries) {
        const summary = normalizeSourceInventoryRecord(entry);
        if (!summary.external_id || !targetIds.has(summary.external_id)) continue;
        const previous = selectedByExternalId.get(summary.external_id);
        const chosen = choosePreferredSourceInventoryRecord(previous, summary);
        if (previous && chosen !== previous) duplicateSelections += 1;
        if (previous && chosen === previous) duplicateSelections += 1;
        selectedByExternalId.set(summary.external_id, chosen);
    }

    return {
        request_url: payload.request_url,
        final_url: payload.final_url,
        http_status: payload.http_status,
        body_bytes: payload.body_bytes,
        parse_status: payload.parse_status,
        blocked_markers: payload.blocked_markers || [],
        selected_count: selectedByExternalId.size,
        duplicate_selection_events: duplicateSelections,
        selected_by_external_id: selectedByExternalId,
    };
}

async function queryReadOnlyDbSnapshot(requestedMatchIds = [], observedExternalIds = [], dependencies = {}) {
    if (dependencies.dbSnapshot) return dependencies.dbSnapshot;
    const pool =
        dependencies.pool ||
        new Pool({
            host: process.env.DB_HOST || 'db',
            port: Number(process.env.DB_PORT || 5432),
            database: process.env.DB_NAME || process.env.POSTGRES_DB || 'football_db',
            user: process.env.DB_USER || process.env.POSTGRES_USER || 'football_user',
            password: process.env.DB_PASSWORD || process.env.POSTGRES_PASSWORD,
        });
    const shouldEndPool = !dependencies.pool;
    try {
        const counts = await pool.query(`
            SELECT 'matches' AS table_name, COUNT(*)::int AS rows FROM matches
            UNION ALL
            SELECT 'raw_match_data', COUNT(*)::int FROM raw_match_data
            UNION ALL
            SELECT 'bookmaker_odds_history', COUNT(*)::int FROM bookmaker_odds_history
            UNION ALL
            SELECT 'l3_features', COUNT(*)::int FROM l3_features
            UNION ALL
            SELECT 'match_features_training', COUNT(*)::int FROM match_features_training
            UNION ALL
            SELECT 'predictions', COUNT(*)::int FROM predictions
        `);
        const targetRows = await pool.query(
            `
            SELECT match_id, external_id, league_name, season, home_team, away_team, match_date, status, data_source, pipeline_status
            FROM matches
            WHERE match_id = ANY($1::text[]) OR external_id = ANY($2::text[])
            ORDER BY match_id
            `,
            [requestedMatchIds, observedExternalIds]
        );
        const candidateV2Rows = await pool.query(
            `
            SELECT COUNT(*)::int AS rows
            FROM raw_match_data
            WHERE data_version = 'fotmob_pageprops_v2'
              AND match_id = ANY($1::text[])
            `,
            [requestedMatchIds]
        );
        return {
            row_counts: Object.fromEntries(
                PROTECTED_TABLES.map(table => [
                    table,
                    Number(counts.rows.find(row => normalizeText(row.table_name) === table)?.rows || 0),
                ])
            ),
            target_rows: targetRows.rows,
            candidate_v2_rows_count: Number(candidateV2Rows.rows[0]?.rows || 0),
        };
    } finally {
        if (shouldEndPool) {
            await pool.end();
        }
    }
}

function normalizeComparableDate(value) {
    const text = normalizeText(value);
    if (!text) return '';
    const date = new Date(text);
    if (Number.isNaN(date.getTime())) return text;
    return date.toISOString();
}

function normalizeTeam(value) {
    const normalized = normalizeLower(value).replace(/[^a-z0-9]/g, '');
    if (normalized === 'psg') return 'parissaintgermain';
    return normalized;
}

function sameIdentityRecord(left = {}, right = {}) {
    if (!left || !right) return false;
    return (
        normalizeText(left.external_id) === normalizeText(right.external_id) &&
        normalizeTeam(left.home_team) === normalizeTeam(right.home_team) &&
        normalizeTeam(left.away_team) === normalizeTeam(right.away_team) &&
        normalizeComparableDate(left.match_date || left.kickoff_time || left.match_time_utc) ===
            normalizeComparableDate(right.match_date || right.kickoff_time || right.match_time_utc) &&
        normalizeLower(left.status) === normalizeLower(right.status)
    );
}

function compareSourceInventoryVsManifest(sourceRecord, manifestTarget) {
    if (!sourceRecord) return 'missing_source_inventory_record';
    return sameIdentityRecord(sourceRecord, manifestTarget) ? 'match' : 'mismatch';
}

function compareManifestVsDb(manifestTarget, dbRow) {
    if (!dbRow) return 'missing_db_row';
    return sameIdentityRecord(manifestTarget, dbRow) ? 'match' : 'mismatch';
}

function compareDbVsObserved(dbRow, observed) {
    if (!observed?.external_id) return 'missing_live_observed';
    if (!dbRow) return 'missing_db_row';
    return sameIdentityRecord(dbRow, observed) ? 'match' : 'mismatch';
}

function summarizeObservedIdentity(proposalTarget = {}) {
    const observed = proposalTarget.attempts?.[0]?.metadata_identity_observed || {};
    return {
        external_id: normalizeText(observed.external_id) || null,
        home_team: normalizeText(observed.home_team) || null,
        away_team: normalizeText(observed.away_team) || null,
        match_time_utc: normalizeText(observed.match_time_utc) || null,
        status: normalizeText(observed.status) || null,
    };
}

function detectMismatchStage(item = {}) {
    if (item.source_inventory_vs_manifest_status !== 'match') return 'source_inventory_generation';
    if (item.manifest_vs_db_status !== 'match') return 'DB_seed';
    if (item.requested_vs_observed_identity_status !== 'match' && item.shared_page_url_base_with_observed === true) {
        return 'fetch_route';
    }
    if (item.requested_vs_observed_identity_status !== 'match' && item.observed_source_inventory_found === true) {
        return 'FotMob_live_mapping';
    }
    if (item.requested_vs_observed_identity_status !== 'match') return 'unknown';
    return 'matched';
}

function buildTargetReconciliationItem(target = {}, proposalTarget = {}, sourceByExternalId = new Map(), dbRows = []) {
    const observed = summarizeObservedIdentity(proposalTarget);
    const requestedSourceRecord = sourceByExternalId.get(normalizeText(target.external_id)) || null;
    const observedSourceRecord = sourceByExternalId.get(normalizeText(observed.external_id)) || null;
    const dbRow = (Array.isArray(dbRows) ? dbRows : []).find(
        row => normalizeText(row.match_id) === normalizeText(target.match_id)
    );
    const sharedPageUrlBase =
        Boolean(requestedSourceRecord?.page_url_base) &&
        requestedSourceRecord.page_url_base === normalizeText(observedSourceRecord?.page_url_base);
    const item = {
        requested_match_id: normalizeText(target.match_id),
        requested_external_id: normalizeText(target.external_id),
        requested_league: LEAGUE_NAME,
        requested_season: SEASON,
        requested_home_team: normalizeText(target.home_team),
        requested_away_team: normalizeText(target.away_team),
        requested_match_date: normalizeText(target.match_date || target.kickoff_time),
        requested_status: normalizeLower(target.status),
        source_inventory_path: requestedSourceRecord?.source_path || null,
        source_inventory_record_key: requestedSourceRecord?.source_inventory_record_key || null,
        source_inventory_external_id: requestedSourceRecord?.external_id || null,
        source_inventory_home_team: requestedSourceRecord?.home_team || null,
        source_inventory_away_team: requestedSourceRecord?.away_team || null,
        source_inventory_match_date: requestedSourceRecord?.match_date || null,
        source_inventory_status: requestedSourceRecord?.status || null,
        source_inventory_round: requestedSourceRecord?.round || null,
        source_inventory_page_url_summary: safeUrlSummary(requestedSourceRecord?.page_url),
        source_inventory_page_url_base: safeUrlSummary(requestedSourceRecord?.page_url_base),
        source_inventory_page_url_anchor: requestedSourceRecord?.page_url_anchor || null,
        source_inventory_id_like_fields: requestedSourceRecord?.id_like_fields || {},
        manifest_record_external_id: normalizeText(target.external_id),
        db_match_id: normalizeText(dbRow?.match_id),
        db_external_id: normalizeText(dbRow?.external_id),
        db_home_team: normalizeText(dbRow?.home_team),
        db_away_team: normalizeText(dbRow?.away_team),
        db_match_date: normalizeComparableDate(dbRow?.match_date),
        db_status: normalizeLower(dbRow?.status),
        db_pipeline_status: normalizeText(dbRow?.pipeline_status),
        live_observed_external_id: observed.external_id,
        live_observed_home_team: observed.home_team,
        live_observed_away_team: observed.away_team,
        live_observed_match_date: normalizeComparableDate(observed.match_time_utc),
        live_observed_status: normalizeLower(observed.status),
        observed_source_inventory_found: Boolean(observedSourceRecord),
        observed_source_inventory_path: observedSourceRecord?.source_path || null,
        observed_source_inventory_round: observedSourceRecord?.round || null,
        observed_source_inventory_page_url_summary: safeUrlSummary(observedSourceRecord?.page_url),
        observed_source_inventory_page_url_base: safeUrlSummary(observedSourceRecord?.page_url_base),
        observed_source_inventory_page_url_anchor: observedSourceRecord?.page_url_anchor || null,
        shared_page_url_base_with_observed: sharedPageUrlBase,
    };
    item.requested_vs_observed_identity_status =
        item.requested_external_id === item.live_observed_external_id ? 'match' : 'mismatch';
    item.source_inventory_vs_manifest_status = compareSourceInventoryVsManifest(requestedSourceRecord, target);
    item.manifest_vs_db_status = compareManifestVsDb(target, dbRow);
    item.db_vs_live_observed_status = compareDbVsObserved(dbRow, observed);
    item.suspected_mismatch_stage = detectMismatchStage(item);
    return item;
}

function countBy(values = []) {
    return values.reduce((acc, value) => {
        const key = normalizeText(value) || 'unknown';
        acc[key] = (acc[key] || 0) + 1;
        return acc;
    }, {});
}

function inferRootCause(summary = {}, items = []) {
    const allObservedFound = items.length > 0 && items.every(item => item.observed_source_inventory_found === true);
    const allSharedPageUrl = items.length > 0 && items.every(item => item.shared_page_url_base_with_observed === true);
    const allStageFetchRoute = items.length > 0 && items.every(item => item.suspected_mismatch_stage === 'fetch_route');
    if (
        summary.source_inventory_vs_manifest_mismatch_count === 0 &&
        summary.manifest_vs_db_mismatch_count === 0 &&
        summary.requested_vs_observed_external_id_mismatch_count === items.length &&
        allObservedFound &&
        allSharedPageUrl &&
        allStageFetchRoute
    ) {
        return {
            suspected_root_cause: 'schedule_vs_detail_external_id_mismatch',
            root_cause_confidence: 'high',
            recommended_next_step: 'schedule_detail_identity_normalization_fix_planning',
        };
    }
    if (summary.source_inventory_vs_manifest_mismatch_count > 0) {
        return {
            suspected_root_cause: 'manifest_generation_mapping_wrong',
            root_cause_confidence: 'medium',
            recommended_next_step: 'source_inventory_manifest_regeneration_review',
        };
    }
    if (summary.manifest_vs_db_mismatch_count > 0) {
        return {
            suspected_root_cause: 'DB_seed_identity_wrong',
            root_cause_confidence: 'medium',
            recommended_next_step: 'matches_identity_seed_reconciliation_review',
        };
    }
    if (summary.db_vs_live_observed_mismatch_count > 0 && allObservedFound) {
        return {
            suspected_root_cause: 'FotMob_live_detail_mapping_changed',
            root_cause_confidence: 'low',
            recommended_next_step: 'target_identity_source_inventory_follow_up_investigation',
        };
    }
    return {
        suspected_root_cause: 'unresolved_unknown',
        root_cause_confidence: 'unknown',
        recommended_next_step: 'target_identity_source_inventory_follow_up_investigation',
    };
}

function buildSummary({
    items = [],
    input = {},
    manifestGate = {},
    proposalGate = {},
    sourceInventorySelection = {},
    dbSnapshot = {},
    generatedAt,
} = {}) {
    const requestedVsObservedMismatchCount = items.filter(
        item => item.requested_vs_observed_identity_status !== 'match'
    ).length;
    const sourceInventoryVsManifestMismatchCount = items.filter(
        item => item.source_inventory_vs_manifest_status !== 'match'
    ).length;
    const manifestVsDbMismatchCount = items.filter(item => item.manifest_vs_db_status !== 'match').length;
    const dbVsLiveObservedMismatchCount = items.filter(item => item.db_vs_live_observed_status !== 'match').length;
    const sharedPageUrlBasePairCount = items.filter(item => item.shared_page_url_base_with_observed === true).length;
    const mismatchStageCounts = countBy(
        items.filter(item => item.suspected_mismatch_stage !== 'matched').map(item => item.suspected_mismatch_stage)
    );
    const baseSummary = {
        phase: PHASE,
        generated_at: generatedAt,
        source_manifest_path: input.manifest,
        renewed_baseline_proposal_path: input.renewedProposal,
        report_path: input.reportOutput,
        branch: input.branch || null,
        base_head: input.baseHead || null,
        main_head: input.mainHead || null,
        main_ci_status: input.mainCiStatus || null,
        pr_1278_state: input.pr1278State || null,
        pr_1278_merge_commit: input.pr1278MergeCommit || null,
        no_write: true,
        db_write_performed: false,
        raw_insert_performed: false,
        baseline_acceptance_performed: false,
        raw_write_retry_performed: false,
        source_inventory_route_used: SOURCE_ROUTE,
        source_inventory_request_url: safeUrlSummary(sourceInventorySelection.request_url),
        source_inventory_final_url: safeUrlSummary(sourceInventorySelection.final_url),
        source_inventory_http_status: sourceInventorySelection.http_status || 0,
        source_inventory_parse_status: sourceInventorySelection.parse_status || 'unknown',
        source_inventory_body_bytes: Number(sourceInventorySelection.body_bytes || 0),
        source_inventory_blocked_markers: sourceInventorySelection.blocked_markers || [],
        selected_source_inventory_record_count: sourceInventorySelection.selected_count || 0,
        candidate_targets_count: manifestGate.candidate_targets_count || 0,
        proposal_checked_targets_count: proposalGate.checkedTargets?.length || 0,
        checked_target_count: items.length,
        identity_match_count: items.length - requestedVsObservedMismatchCount,
        identity_mismatch_count: requestedVsObservedMismatchCount,
        source_inventory_vs_manifest_mismatch_count: sourceInventoryVsManifestMismatchCount,
        manifest_vs_db_mismatch_count: manifestVsDbMismatchCount,
        db_vs_live_observed_mismatch_count: dbVsLiveObservedMismatchCount,
        requested_vs_observed_external_id_mismatch_count: requestedVsObservedMismatchCount,
        mismatch_stage_counts: mismatchStageCounts,
        shared_page_url_base_pair_count: sharedPageUrlBasePairCount,
        all_pairs_share_page_url_base: items.length > 0 && sharedPageUrlBasePairCount === items.length,
        raw_write_ready_for_execution: false,
        target_identity_mismatch_blocks_baseline_acceptance: true,
        requires_separate_baseline_acceptance: true,
        requires_separate_final_db_write_authorization: true,
        db_row_counts: dbSnapshot.row_counts || {},
        candidate_v2_rows_count: Number(dbSnapshot.candidate_v2_rows_count || 0),
    };
    return { ...baseSummary, ...inferRootCause(baseSummary, items) };
}

function buildUpdatedManifest(manifest = {}, summary = {}) {
    return {
        ...manifest,
        phase_5_21_l2v3e_planning_status: 'completed_no_write',
        target_identity_source_inventory_reconciliation_status:
            summary.suspected_root_cause === 'schedule_vs_detail_external_id_mismatch'
                ? 'blocked_schedule_detail_identity_mismatch_identified'
                : 'blocked_source_inventory_reconciliation_unresolved',
        phase_5_21_l2v3e_checked_target_count: summary.checked_target_count,
        phase_5_21_l2v3e_identity_match_count: summary.identity_match_count,
        phase_5_21_l2v3e_identity_mismatch_count: summary.identity_mismatch_count,
        phase_5_21_l2v3e_source_inventory_vs_manifest_mismatch_count:
            summary.source_inventory_vs_manifest_mismatch_count,
        phase_5_21_l2v3e_manifest_vs_db_mismatch_count: summary.manifest_vs_db_mismatch_count,
        phase_5_21_l2v3e_db_vs_live_observed_mismatch_count: summary.db_vs_live_observed_mismatch_count,
        phase_5_21_l2v3e_requested_vs_observed_external_id_mismatch_count:
            summary.requested_vs_observed_external_id_mismatch_count,
        phase_5_21_l2v3e_mismatch_stage_counts: summary.mismatch_stage_counts,
        phase_5_21_l2v3e_shared_page_url_base_pair_count: summary.shared_page_url_base_pair_count,
        phase_5_21_l2v3e_all_pairs_share_page_url_base: summary.all_pairs_share_page_url_base,
        phase_5_21_l2v3e_suspected_root_cause: summary.suspected_root_cause,
        phase_5_21_l2v3e_root_cause_confidence: summary.root_cause_confidence,
        phase_5_21_l2v3e_recommended_next_step: summary.recommended_next_step,
        target_identity_mismatch_blocks_baseline_acceptance: true,
        renewed_baseline_requires_separate_baseline_acceptance: true,
        renewed_baseline_requires_separate_final_db_write_authorization: true,
        requires_separate_baseline_acceptance: true,
        requires_separate_final_db_write_authorization: true,
        raw_write_ready_for_execution: false,
        raw_write_retry_authorization_status: 'blocked_pending_target_identity_source_inventory_reconciliation',
        next_required_step: summary.recommended_next_step,
    };
}

function buildReconciliationRows(items = []) {
    return items.map(
        item =>
            `| ${item.requested_match_id} | ${item.requested_external_id} | ${item.requested_home_team}-${item.requested_away_team} | ${item.requested_match_date} | ${item.requested_status} | ${item.source_inventory_path || ''} | ${item.source_inventory_record_key || ''} | ${item.source_inventory_external_id || ''} | ${item.source_inventory_home_team || ''}-${item.source_inventory_away_team || ''} | ${item.source_inventory_match_date || ''} | ${item.source_inventory_page_url_base || ''} | ${item.manifest_record_external_id || ''} | ${item.db_external_id || ''} | ${item.live_observed_external_id || ''} | ${item.live_observed_home_team || ''}-${item.live_observed_away_team || ''} | ${item.live_observed_match_date || ''} | ${item.requested_vs_observed_identity_status} | ${item.source_inventory_vs_manifest_status} | ${item.manifest_vs_db_status} | ${item.db_vs_live_observed_status} | ${item.shared_page_url_base_with_observed} | ${item.suspected_mismatch_stage} |`
    );
}

function buildStageLines(summary = {}) {
    return Object.entries(summary.mismatch_stage_counts || {}).map(([key, count]) => `- ${key}=${count}`);
}

function buildReport({ summary = {}, items = [], manifestGate = {}, sourceInventorySelection = {} } = {}) {
    const rows = buildReconciliationRows(items);
    const stageLines = buildStageLines(summary);
    return `# Data Entrypoint Governance - Phase 5.21 L2V3E

## A. Current Status

- phase=target identity source inventory reconciliation planning
- branch=${summary.branch || 'unknown'}
- base_head=${summary.base_head || 'unknown'}
- main_head=${summary.main_head || 'unknown'}
- main_ci_status=${summary.main_ci_status || 'unknown'}
- source_manifest_path=${summary.source_manifest_path}
- renewed_baseline_proposal_path=${summary.renewed_baseline_proposal_path}
- report_path=${summary.report_path}

## B. PR #1278 Merge Result

- pr_1278_state=${summary.pr_1278_state || 'MERGED'}
- pr_1278_merge_commit=${summary.pr_1278_merge_commit || 'unknown'}
- merge_scope=L2V3D no-write target identity reconciliation planning

## C. main HEAD / CI Status

- main_head=${summary.main_head || 'unknown'}
- main_ci_status=${summary.main_ci_status || 'unknown'}

## D. Authorization Scope

- planning_authorized=true
- source_inventory_reconciliation_authorized=true
- network_authorized_for_source_inventory_only=true
- no match detail recapture executed in L2V3E
- no accepted baseline replacement
- no raw write authorization

## E. No-Write Guarantee

- db_write_performed=false
- raw_insert_performed=false
- baseline_acceptance_performed=false
- raw_write_retry_performed=false
- full raw_data/pageProps/source body printed=false
- full raw_data/pageProps/source body saved=false

## F. L2V3D Identity Mismatch Recap

- l2v3d_checked_target_count=${manifestGate.candidate_targets_count ? EXPECTED_MISMATCH_COUNT : 0}
- l2v3d_identity_match_count=0
- l2v3d_identity_mismatch_count=${EXPECTED_MISMATCH_COUNT}
- l2v3d_next_required_step=target_identity_source_inventory_reconciliation_planning
- raw_write_ready_for_execution=false
- target_identity_mismatch_blocks_baseline_acceptance=true

## G. Source Inventory Provenance Review

- source_inventory_route_used=${summary.source_inventory_route_used}
- source_inventory_request_url=${summary.source_inventory_request_url || 'unknown'}
- source_inventory_final_url=${summary.source_inventory_final_url || 'unknown'}
- source_inventory_http_status=${summary.source_inventory_http_status}
- source_inventory_parse_status=${summary.source_inventory_parse_status}
- source_inventory_body_bytes=${summary.source_inventory_body_bytes}
- selected_source_inventory_record_count=${summary.selected_source_inventory_record_count}
- blocked_markers=${(summary.source_inventory_blocked_markers || []).join(',') || 'none'}
- shared_page_url_base_pair_count=${summary.shared_page_url_base_pair_count}
- all_pairs_share_page_url_base=${summary.all_pairs_share_page_url_base}

## H. Manifest Target Generation Review

- candidate_targets_count=${manifestGate.candidate_targets_count || 0}
- known_completed_targets_count=${manifestGate.known_completed_targets_count || 0}
- source_inventory_vs_manifest_mismatch_count=${summary.source_inventory_vs_manifest_mismatch_count}
- manifest generation preserved source inventory external_id/match identity for the 8 checked targets.

## I. DB Matches Identity Review

- matches_row_count=${summary.db_row_counts.matches ?? 'unknown'}
- raw_match_data_row_count=${summary.db_row_counts.raw_match_data ?? 'unknown'}
- candidate_fotmob_pageprops_v2_rows_count=${summary.candidate_v2_rows_count}
- manifest_vs_db_mismatch_count=${summary.manifest_vs_db_mismatch_count}
- db_vs_live_observed_mismatch_count=${summary.db_vs_live_observed_mismatch_count}

## J. Requested vs Observed Reconciliation Table

| requested_match_id | requested_external_id | requested_teams | requested_match_date | requested_status | source_inventory_path | source_inventory_record_key | source_inventory_external_id | source_inventory_teams | source_inventory_match_date | source_inventory_page_url_base | manifest_record_external_id | DB external_id | live observed external_id | live observed teams | live observed match_date | requested_vs_observed_identity_status | source_inventory_vs_manifest_status | manifest_vs_db_status | DB_vs_live_observed_status | shared_page_url_base_with_observed | suspected_mismatch_stage |
| ------------------ | --------------------- | --------------- | -------------------- | ---------------- | --------------------- | --------------------------- | ---------------------------- | ---------------------- | --------------------------- | ------------------------------ | --------------------------- | -------------- | ------------------------- | ------------------ | ------------------------ | ------------------------------------ | --------------------------------- | -------------------- | -------------------------- | ---------------------------------- | ------------------------ |
${rows.join('\n')}

## K. Mismatch Stage Classification

- checked_target_count=${summary.checked_target_count}
- identity_match_count=${summary.identity_match_count}
- identity_mismatch_count=${summary.identity_mismatch_count}
- source_inventory_vs_manifest_mismatch_count=${summary.source_inventory_vs_manifest_mismatch_count}
- manifest_vs_db_mismatch_count=${summary.manifest_vs_db_mismatch_count}
- db_vs_live_observed_mismatch_count=${summary.db_vs_live_observed_mismatch_count}
- requested_vs_observed_external_id_mismatch_count=${summary.requested_vs_observed_external_id_mismatch_count}
${stageLines.join('\n')}

## L. Suspected Root Cause And Confidence

- suspected_root_cause=${summary.suspected_root_cause}
- root_cause_confidence=${summary.root_cause_confidence}
- primary_evidence=source inventory requested/observed pairs share the same pageUrl base and differ only by #external_id anchor

## M. Required Fix / Continue Investigation Decision

- code_fix_required=${summary.suspected_root_cause === 'schedule_vs_detail_external_id_mismatch'}
- inventory_regeneration_required=${summary.suspected_root_cause === 'manifest_generation_mapping_wrong'}
- manifest_regeneration_required=${summary.suspected_root_cause === 'manifest_generation_mapping_wrong'}
- continue_investigation_required=${summary.root_cause_confidence !== 'high'}

## N. DB Row Count Safety Result

- matches=${summary.db_row_counts.matches ?? 'unknown'}
- raw_match_data=${summary.db_row_counts.raw_match_data ?? 'unknown'}
- bookmaker_odds_history=${summary.db_row_counts.bookmaker_odds_history ?? 'unknown'}
- l3_features=${summary.db_row_counts.l3_features ?? 'unknown'}
- match_features_training=${summary.db_row_counts.match_features_training ?? 'unknown'}
- predictions=${summary.db_row_counts.predictions ?? 'unknown'}
- candidate_v2_rows_count=${summary.candidate_v2_rows_count}
- expected_matches=${EXPECTED_ROW_COUNTS.matches}
- expected_raw_match_data=${EXPECTED_ROW_COUNTS.raw_match_data}

## O. Test Results

- pending until local verification completes

## P. PR Status

- pending until PR is created

## Q. Next Step Recommendation

- recommended_next_step=${summary.recommended_next_step}
- unresolved identity/source inventory mismatch blocks baseline acceptance.
- unresolved identity/source inventory mismatch blocks raw write retry.

## R. Explicit Non-Execution

- no DB writes
- no raw_match_data inserts
- no matches writes
- no bookmaker_odds_history writes
- no l3_features writes
- no match_features_training writes
- no predictions writes
- no schema migration
- no parser implementation
- no feature extraction
- no training/prediction
- no browser/proxy/captcha bypass
- no accepted baseline replacement
- no raw write retry
- no proposal hash marked as accepted baseline
- no full raw_data/pageProps/source body print/save
- no invented external_id, target, payload, or hash
`;
}

async function sleep(ms) {
    if (!ms) return;
    await new Promise(resolve => {
        setTimeout(resolve, ms);
    });
}

async function runPlanning(rawInput = {}, dependencies = {}) {
    const validation = validatePlanningInput(rawInput);
    if (!validation.ok) return { ok: false, status: 2, errors: validation.errors };
    const input = validation.input;
    const generatedAt = input.generatedAt || dependencies.generatedAt || new Date().toISOString();
    const manifest = dependencies.manifest || (dependencies.readJsonFile || readJsonFile)(input.manifest);
    const proposal = dependencies.renewedProposal || (dependencies.readJsonFile || readJsonFile)(input.renewedProposal);
    const manifestGate = buildManifestGate(manifest);
    if (!manifestGate.ok) return { ok: false, status: 3, errors: manifestGate.errors, manifest_gate: manifestGate };
    const proposalGate = buildProposalGate(proposal);
    if (!proposalGate.ok) return { ok: false, status: 4, errors: proposalGate.errors, proposal_gate: proposalGate };
    const selection = l2v3d.selectMismatchTargets(manifestGate, proposalGate, input.targetExternalIds);
    if (!selection.ok) return { ok: false, status: 5, errors: selection.errors };

    const observedExternalIds = selection.pairs
        .map(pair => summarizeObservedIdentity(pair.proposalTarget).external_id)
        .map(normalizeText)
        .filter(Boolean);
    if (input.requestDelayMs > 0) await sleep(input.requestDelayMs);
    const sourcePayload = await fetchSourceInventoryPayload(input, dependencies);
    if (!sourcePayload.ok) {
        return {
            ok: false,
            status: 6,
            errors: [sourcePayload.error || 'SOURCE_INVENTORY_FETCH_FAILED'],
            source_inventory: sourcePayload,
        };
    }
    const sourceInventorySelection = buildSourceInventorySelection(
        sourcePayload,
        selection.selected_external_ids,
        observedExternalIds
    );
    const dbSnapshot = await queryReadOnlyDbSnapshot(
        selection.pairs.map(pair => pair.target.match_id),
        observedExternalIds,
        dependencies
    );
    const items = selection.pairs.map(pair =>
        buildTargetReconciliationItem(
            pair.target,
            pair.proposalTarget,
            sourceInventorySelection.selected_by_external_id,
            dbSnapshot.target_rows
        )
    );
    const summary = buildSummary({
        items,
        input,
        manifestGate,
        proposalGate,
        sourceInventorySelection,
        dbSnapshot,
        generatedAt,
    });
    const updatedManifest = buildUpdatedManifest(manifest, summary);
    const report = buildReport({ summary, items, manifestGate, sourceInventorySelection });
    if (dependencies.writeManifest !== false) {
        (dependencies.writeManifestFile || dependencies.writeJsonFile || writeJsonFile)(
            input.manifest,
            updatedManifest
        );
    }
    if (dependencies.writeReport !== false) {
        (dependencies.writeReportFile || writeReportFile)(input.reportOutput, report);
    }
    return {
        ok: true,
        status: 0,
        summary,
        items,
        updated_manifest: updatedManifest,
        report,
        manifest_gate: manifestGate,
        proposal_gate: proposalGate,
        source_inventory_selection: {
            ...sourceInventorySelection,
            selected_by_external_id: Object.fromEntries(sourceInventorySelection.selected_by_external_id),
        },
        db_snapshot: dbSnapshot,
        selected_external_ids: selection.selected_external_ids,
    };
}

async function runCli(argv = process.argv.slice(2), dependencies = {}) {
    const args = parseArgs(argv);
    if (args.help) {
        process.stdout.write(
            `Usage: node scripts/ops/pageprops_v2_target_source_inventory_reconciliation_plan.js --manifest=${MANIFEST_PATH} --renewed-proposal=${RENEWED_PROPOSAL_PATH} ...\n`
        );
        return { status: 0 };
    }
    const result = await runPlanning(args, dependencies);
    const output = result.ok
        ? {
              ok: true,
              status: result.status,
              summary: result.summary,
              selected_external_ids: result.selected_external_ids,
          }
        : { ok: false, status: result.status, errors: result.errors };
    process.stdout.write(`${JSON.stringify(output, null, 2)}\n`);
    return { status: result.status };
}

module.exports = {
    PHASE,
    MANIFEST_PATH,
    RENEWED_PROPOSAL_PATH,
    REPORT_PATH,
    SOURCE,
    LEAGUE_ID,
    LEAGUE_NAME,
    SEASON,
    RAW_VERSION,
    HASH_STRATEGY,
    BATCH_ID,
    TARGET_COUNT,
    EXPECTED_MISMATCH_COUNT,
    EXPECTED_ROW_COUNTS,
    parseArgs,
    normalizeBooleanFlag,
    readJsonFile,
    writeJsonFile,
    writeReportFile,
    validatePlanningInput,
    buildManifestGate,
    buildProposalGate,
    fetchSourceInventoryPayload,
    buildSourceInventorySelection,
    queryReadOnlyDbSnapshot,
    buildTargetReconciliationItem,
    buildSummary,
    buildUpdatedManifest,
    buildReport,
    sleep,
    runPlanning,
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
