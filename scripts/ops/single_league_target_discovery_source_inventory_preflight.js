#!/usr/bin/env node
/* eslint-disable complexity, max-lines, max-statements */
'use strict';

const fs = require('node:fs');
const path = require('node:path');
const { Pool } = require('pg');
const {
    FotMobSourceInventoryAdapter,
    ROUTE_KIND: L1_SOURCE_INVENTORY_ROUTE_KIND,
    deriveSourceInventoryIdentityEvidence,
} = require('../../src/infrastructure/services/FotMobSourceInventoryAdapter');

const PHASE = 'PHASE5_21L2T0_AUTHORIZED_SINGLE_LEAGUE_TARGET_DISCOVERY_SOURCE_INVENTORY_PREFLIGHT';
const SOURCE = 'fotmob';
const LEAGUE_ID = 53;
const LEAGUE_NAME = 'Ligue 1';
const SEASON = '2025/2026';
const SOURCE_INVENTORY_ROUTE = 'source_inventory';
const TARGET_ROUTE = 'html_hydration';
const RAW_VERSION = 'fotmob_pageprops_v2';
const HASH_STRATEGY = 'stable_pageprops_payload_v1';
const BATCH_ID = 'fotmob-pageprops-v2-ligue1-2025-2026-profile-001';
const BATCH_TYPE = 'profile_batch';
const TARGET_COUNT_MIN = 20;
const TARGET_COUNT_MAX = 50;
const READY_FOR_PREFLIGHT = 'ready_for_no_write_preflight';
const INSUFFICIENT_CANDIDATES = 'insufficient_candidates_discovered';
const NEXT_PREFLIGHT = 'single_league_small_batch_no_write_pageprops_v2_preflight';
const NEXT_ADDITIONAL_DISCOVERY = 'adjust_source_inventory_route_or_authorize_additional_discovery';
const MANIFEST_PATH = path.resolve(
    __dirname,
    '../../docs/_manifests/fotmob_pageprops_v2_ligue1_2025_2026_profile_001.proposal.json'
);

const EXPECTED_ROW_COUNTS = Object.freeze({
    matches: 10,
    raw_match_data: 18,
    bookmaker_odds_history: 2,
    l3_features: 2,
    match_features_training: 2,
    predictions: 2,
});

const REQUIRED_NO_FLAGS = Object.freeze([
    'allowDbWrite',
    'allowRawMatchDataWrite',
    'allowMatchDetailFetch',
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
]);

const BLOCKED_TRUE_FLAGS = Object.freeze([
    'executeWrite',
    'execute',
    'commit',
    'inventTargets',
    'fabricateExternalIds',
    'allowOddsWrite',
]);

const TARGET_MANIFEST_FIELDS = Object.freeze([
    'target_id',
    'batch_id',
    'source',
    'route',
    'source_inventory_route',
    'raw_data_version',
    'hash_strategy',
    'match_id',
    'external_id',
    'source_url',
    'source_path',
    'source_page_url',
    'source_page_url_base',
    'source_url_fragment_external_id',
    'source_slug',
    'source_route_code',
    'source_url_path_slug',
    'detail_external_id_candidate',
    'detail_identity_source',
    'schedule_external_id',
    'schedule_date',
    'schedule_home_team',
    'schedule_away_team',
    'source_inventory_record_key',
    'source_inventory_generated_at',
    'identity_evidence_status',
    'league_id',
    'league_name',
    'season',
    'home_team',
    'away_team',
    'kickoff_time',
    'match_date',
    'status',
    'target_status',
    'priority',
    'expected_coverage_tier',
    'existing_versions',
    'preflight_status',
    'baseline_hash',
    'last_preflight_at',
    'write_status',
    'write_attempt_count',
    'failure_reason',
    'source_fidelity_notes',
    'odds_alignment_ready',
    'created_at',
    'updated_at',
]);

const BLOCK_MARKERS = Object.freeze([
    'captcha',
    'cloudflare',
    'cf-ray',
    'access denied',
    'checking your browser',
    'just a moment',
    'unusual traffic',
    'temporarily blocked',
]);

function normalizeText(value) {
    return String(value ?? '').trim();
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

function parseInteger(value, fallback = Number.NaN) {
    if (value === null || value === undefined || value === '') {
        return fallback;
    }
    const parsed = Number.parseInt(String(value), 10);
    return Number.isInteger(parsed) ? parsed : Number.NaN;
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
        leagueName: null,
        season: null,
        route: null,
        rawVersion: null,
        hashStrategy: null,
        batchId: null,
        targetCountMin: null,
        targetCountMax: null,
        networkAuthorization: null,
        sourceInventoryAuthorization: null,
        concurrency: null,
        retry: null,
        allowDbWrite: null,
        allowRawMatchDataWrite: null,
        allowMatchDetailFetch: null,
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
        executeWrite: false,
        execute: false,
        commit: false,
        inventTargets: false,
        fabricateExternalIds: false,
        allowOddsWrite: false,
        help: false,
        unknown: [],
    };
    const keyMap = {
        source: 'source',
        'league-id': 'leagueId',
        league_id: 'leagueId',
        'league-name': 'leagueName',
        league_name: 'leagueName',
        season: 'season',
        route: 'route',
        'raw-version': 'rawVersion',
        raw_version: 'rawVersion',
        'hash-strategy': 'hashStrategy',
        hash_strategy: 'hashStrategy',
        'batch-id': 'batchId',
        batch_id: 'batchId',
        'target-count-min': 'targetCountMin',
        target_count_min: 'targetCountMin',
        'target-count-max': 'targetCountMax',
        target_count_max: 'targetCountMax',
        'network-authorization': 'networkAuthorization',
        network_authorization: 'networkAuthorization',
        'source-inventory-authorization': 'sourceInventoryAuthorization',
        source_inventory_authorization: 'sourceInventoryAuthorization',
        concurrency: 'concurrency',
        retry: 'retry',
        'allow-db-write': 'allowDbWrite',
        allow_db_write: 'allowDbWrite',
        'allow-raw-match-data-write': 'allowRawMatchDataWrite',
        allow_raw_match_data_write: 'allowRawMatchDataWrite',
        'allow-match-detail-fetch': 'allowMatchDetailFetch',
        allow_match_detail_fetch: 'allowMatchDetailFetch',
        'allow-schema-migration': 'allowSchemaMigration',
        allow_schema_migration: 'allowSchemaMigration',
        'allow-parser-implementation': 'allowParserImplementation',
        allow_parser_implementation: 'allowParserImplementation',
        'allow-feature-extraction': 'allowFeatureExtraction',
        allow_feature_extraction: 'allowFeatureExtraction',
        'allow-training': 'allowTraining',
        allow_training: 'allowTraining',
        'allow-prediction': 'allowPrediction',
        allow_prediction: 'allowPrediction',
        'allow-browser-runtime': 'allowBrowserRuntime',
        allow_browser_runtime: 'allowBrowserRuntime',
        'allow-proxy-runtime': 'allowProxyRuntime',
        allow_proxy_runtime: 'allowProxyRuntime',
        'print-full-body': 'printFullBody',
        print_full_body: 'printFullBody',
        'save-full-body': 'saveFullBody',
        save_full_body: 'saveFullBody',
        'print-full-json': 'printFullJson',
        print_full_json: 'printFullJson',
        'save-full-json': 'saveFullJson',
        save_full_json: 'saveFullJson',
        'execute-write': 'executeWrite',
        execute_write: 'executeWrite',
        execute: 'execute',
        commit: 'commit',
        'invent-targets': 'inventTargets',
        invent_targets: 'inventTargets',
        'fabricate-external-ids': 'fabricateExternalIds',
        fabricate_external_ids: 'fabricateExternalIds',
        'allow-odds-write': 'allowOddsWrite',
        allow_odds_write: 'allowOddsWrite',
        help: 'help',
        h: 'help',
    };
    const booleanKeys = new Set([
        'networkAuthorization',
        'sourceInventoryAuthorization',
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
        const optionKey = keyMap[rawKey];
        const { value, consumedNext } = parseOptionValue(arg, argv, index);
        if (consumedNext) {
            index += 1;
        }
        if (!optionKey) {
            options.unknown.push(rawKey);
            continue;
        }
        options[optionKey] = booleanKeys.has(optionKey) ? normalizeBooleanFlag(value, true) : value;
    }

    return options;
}

function cliName(flagName) {
    return flagName.replace(/[A-Z]/g, match => `-${match.toLowerCase()}`);
}

function addExactTextValidation(errors, value, expected, missingMessage, invalidMessage) {
    const normalized = normalizeText(value);
    if (!normalized) {
        errors.push(missingMessage);
        return;
    }
    if (normalized !== expected) {
        errors.push(invalidMessage);
    }
}

function addSourceValidation(errors, value) {
    const normalized = normalizeText(value).toLowerCase();
    if (!normalized) {
        errors.push('missing source=fotmob');
        return;
    }
    if (normalized !== SOURCE) {
        errors.push('source must be fotmob');
    }
}

function addLeagueIdValidation(errors, value) {
    const normalized = normalizeText(value);
    if (!normalized) {
        errors.push('missing league-id=53');
        return;
    }
    if (Number(normalized) !== LEAGUE_ID) {
        errors.push('league-id must be 53 for this phase');
    }
}

function addRequiredNoFlagValidation(errors, input) {
    for (const flagName of REQUIRED_NO_FLAGS) {
        const normalizedValue = normalizeBooleanFlag(input[flagName]);
        if (normalizedValue === true) {
            errors.push(`${cliName(flagName)}=yes is blocked`);
            continue;
        }
        if (normalizedValue !== false) {
            errors.push(`${cliName(flagName)}=no is required`);
        }
    }
}

function addBlockedTrueFlagValidation(errors, input) {
    for (const flagName of BLOCKED_TRUE_FLAGS) {
        if (normalizeBooleanFlag(input[flagName]) === true) {
            errors.push(`${cliName(flagName)}=yes is blocked`);
        }
    }
}

function validatePreflightInput(input = {}) {
    const errors = [];
    const source = normalizeText(input.source).toLowerCase();
    const leagueId = Number(normalizeText(input.leagueId));
    const leagueName = normalizeText(input.leagueName);
    const season = normalizeText(input.season);
    const route = normalizeText(input.route);
    const rawVersion = normalizeText(input.rawVersion);
    const hashStrategy = normalizeText(input.hashStrategy);
    const batchId = normalizeText(input.batchId);
    const targetCountMin = parseInteger(input.targetCountMin);
    const targetCountMax = parseInteger(input.targetCountMax);
    const concurrency = parseInteger(input.concurrency);
    const retry = parseInteger(input.retry);

    if (Array.isArray(input.unknown) && input.unknown.length > 0) {
        errors.push(`unknown arguments: ${input.unknown.join(', ')}`);
    }

    addSourceValidation(errors, input.source);
    addLeagueIdValidation(errors, input.leagueId);
    addExactTextValidation(
        errors,
        leagueName,
        LEAGUE_NAME,
        'missing league-name=Ligue 1',
        'league-name must be Ligue 1 for this phase'
    );
    addExactTextValidation(
        errors,
        season,
        SEASON,
        'missing season=2025/2026',
        'season must be 2025/2026 for this phase'
    );
    addExactTextValidation(
        errors,
        route,
        SOURCE_INVENTORY_ROUTE,
        'missing route=source_inventory',
        'route must be source_inventory'
    );
    addExactTextValidation(
        errors,
        rawVersion,
        RAW_VERSION,
        'missing raw-version=fotmob_pageprops_v2',
        'raw-version must be fotmob_pageprops_v2'
    );
    addExactTextValidation(
        errors,
        hashStrategy,
        HASH_STRATEGY,
        'missing hash-strategy=stable_pageprops_payload_v1',
        'hash-strategy must be stable_pageprops_payload_v1'
    );
    addExactTextValidation(errors, batchId, BATCH_ID, `missing batch-id=${BATCH_ID}`, `batch-id must be ${BATCH_ID}`);

    if (targetCountMin !== TARGET_COUNT_MIN) {
        errors.push('target-count-min must be 20');
    }
    if (targetCountMax !== TARGET_COUNT_MAX) {
        errors.push('target-count-max must be 50');
    }
    if (normalizeBooleanFlag(input.networkAuthorization) !== true) {
        errors.push('network-authorization=yes is required');
    }
    if (normalizeBooleanFlag(input.sourceInventoryAuthorization) !== true) {
        errors.push('source-inventory-authorization=yes is required');
    }
    if (concurrency !== 1) {
        errors.push('concurrency must be 1');
    }
    if (retry !== 0) {
        errors.push('retry must be 0');
    }

    addRequiredNoFlagValidation(errors, input);
    addBlockedTrueFlagValidation(errors, input);

    return {
        ok: errors.length === 0,
        errors,
        value: {
            source,
            leagueId,
            leagueName,
            season,
            route,
            rawVersion,
            hashStrategy,
            batchId,
            targetCountMin,
            targetCountMax,
            networkAuthorization: true,
            sourceInventoryAuthorization: true,
            concurrency,
            retry,
        },
    };
}

function createSourceInventoryAdapter(dependencies = {}) {
    if (dependencies.sourceInventoryAdapter) {
        return dependencies.sourceInventoryAdapter;
    }
    if (typeof dependencies.createSourceInventoryAdapter === 'function') {
        return dependencies.createSourceInventoryAdapter();
    }
    return new FotMobSourceInventoryAdapter({
        configManager: dependencies.configManager,
        parser: dependencies.discoveryParser,
        logger: dependencies.logger,
    });
}

function buildSourceInventoryUrl(options = {}, dependencies = {}) {
    const adapter = createSourceInventoryAdapter(dependencies);
    return adapter.buildSourceInventoryUrl({
        source: options.source || SOURCE,
        leagueId: options.leagueId || LEAGUE_ID,
        season: options.season || SEASON,
    });
}

function detectBlockedMarkers(bodyText = '') {
    const normalized = String(bodyText).toLowerCase();
    return BLOCK_MARKERS.filter(marker => normalized.includes(marker));
}

function buildContentTypeSummary(headers) {
    if (!headers || typeof headers.get !== 'function') {
        return null;
    }
    return headers.get('content-type') || null;
}

async function fetchSourceInventoryJson(options, dependencies = {}) {
    const fetchImpl = dependencies.fetch || global.fetch;
    if (typeof fetchImpl !== 'function') {
        throw new Error('global fetch is unavailable');
    }

    const adapter = createSourceInventoryAdapter(dependencies);
    const fetchRequest = adapter.buildFetchRequest({
        source: options.source || SOURCE,
        leagueId: options.leagueId || LEAGUE_ID,
        season: options.season || SEASON,
    });
    const url = dependencies.sourceInventoryUrl || fetchRequest.sourceUrl;
    const response = await fetchImpl(url, {
        method: 'GET',
        headers: { accept: 'application/json' },
    });
    const statusCode = Number(response?.status);
    const contentType = buildContentTypeSummary(response?.headers);
    const bodyText = await response.text();
    const blockedMarkers = detectBlockedMarkers(bodyText);
    const requestMetadata = {
        route_used: SOURCE_INVENTORY_ROUTE,
        reused_l1_capability: true,
        l1_capability: 'FotMobSourceInventoryAdapter',
        l1_route_kind: L1_SOURCE_INVENTORY_ROUTE_KIND,
        source_url: url,
        request_count: 1,
        status_codes: [statusCode],
        content_type_summary: [contentType].filter(Boolean),
        blocked_markers: blockedMarkers,
        full_body_printed: false,
        full_body_saved: false,
        full_json_printed: false,
        full_json_saved: false,
    };

    if (statusCode === 403) {
        const error = new Error('source inventory request returned 403');
        error.requestMetadata = requestMetadata;
        error.blocked = true;
        throw error;
    }
    if (blockedMarkers.length > 0) {
        const error = new Error(`source inventory blocked markers detected: ${blockedMarkers.join(', ')}`);
        error.requestMetadata = requestMetadata;
        error.blocked = true;
        throw error;
    }
    if (statusCode < 200 || statusCode >= 300) {
        const error = new Error(`source inventory request failed with status ${statusCode}`);
        error.requestMetadata = requestMetadata;
        throw error;
    }

    try {
        return {
            json: JSON.parse(bodyText),
            requestMetadata: {
                ...requestMetadata,
                parse_status: 'parsed_json',
            },
        };
    } catch (parseError) {
        const error = new Error(`invalid JSON source inventory response: ${parseError.message}`);
        error.requestMetadata = {
            ...requestMetadata,
            parse_status: 'invalid_json',
        };
        throw error;
    }
}

function isObjectLike(value) {
    return Boolean(value) && typeof value === 'object';
}

function getExternalId(match) {
    return match?.id ?? match?.matchId ?? match?.match_id ?? match?.eventId ?? null;
}

function pickText(values) {
    return values.find(value => typeof value === 'string' && value.trim())?.trim() || null;
}

function getTeamSeed(match, side) {
    return (
        match?.[side] ??
        match?.[`${side}Team`] ??
        match?.[`${side}_team`] ??
        match?.[`${side}Name`] ??
        match?.[`${side}_name`] ??
        match?.teams?.[side] ??
        null
    );
}

function resolveTeamName(match, side) {
    const seed = getTeamSeed(match, side);
    if (typeof seed === 'string') {
        return pickText([seed]);
    }
    if (isObjectLike(seed)) {
        return pickText([seed.name, seed.shortName, seed.longName, seed.fullName]);
    }
    return null;
}

function parseDateValue(value) {
    if (value === null || value === undefined || value === '') {
        return null;
    }
    if (typeof value === 'number' && Number.isFinite(value)) {
        const millis = value > 100000000000 ? value : value * 1000;
        const parsed = new Date(millis);
        return Number.isNaN(parsed.getTime()) ? null : parsed.toISOString();
    }
    const parsed = new Date(value);
    return Number.isNaN(parsed.getTime()) ? null : parsed.toISOString();
}

function resolveKickoffTime(match) {
    return (
        parseDateValue(match?.status?.utcTime) ||
        parseDateValue(match?.time?.utc) ||
        parseDateValue(match?.matchTime) ||
        parseDateValue(match?.kickoff?.datetime) ||
        parseDateValue(match?.startTime) ||
        parseDateValue(match?.utcTime) ||
        parseDateValue(match?.timeTS) ||
        parseDateValue(match?.date) ||
        null
    );
}

function resolveStatus(match) {
    if (match?.status?.finished || match?.status?.completed || match?.finished || match?.isFinished) {
        return 'finished';
    }
    if (match?.status?.cancelled || match?.cancelled) {
        return 'cancelled';
    }
    if (match?.status?.postponed || match?.postponed) {
        return 'postponed';
    }
    if (match?.status?.abandoned || match?.abandoned) {
        return 'abandoned';
    }
    if (match?.status?.live || match?.status?.started || match?.isLive || match?.live) {
        return 'live';
    }
    return (
        pickText([
            typeof match?.status === 'string' ? match.status : null,
            match?.status?.type,
            match?.status?.reason?.short,
            match?.status?.reason?.long,
            match?.status?.short,
            match?.status?.long,
        ])?.toLowerCase() || 'scheduled'
    );
}

function resolveRound(match, sourcePath) {
    return pickText([match?.round, match?.roundName, match?.matchRound, match?.matchday, sourcePath]) || null;
}

function resolveSourcePath(match) {
    return pickText([match?.pageUrl, match?.matchUrl, match?.url, match?.href, match?.sourcePath]) || null;
}

function buildMissingSourceIdentityEvidence(candidate = {}) {
    return {
        source_page_url: candidate.source_page_url || null,
        source_page_url_base: candidate.source_page_url_base || null,
        source_url_fragment_external_id: candidate.source_url_fragment_external_id || null,
        source_slug: candidate.source_slug || null,
        source_route_code: candidate.source_route_code || null,
        source_url_path_slug: candidate.source_url_path_slug || candidate.source_route_code || null,
        detail_external_id_candidate: candidate.detail_external_id_candidate || null,
        detail_identity_source: candidate.detail_identity_source || null,
        source_inventory_record_key: candidate.source_inventory_record_key || null,
        source_inventory_generated_at: candidate.source_inventory_generated_at || 'unknown',
        identity_evidence_status: candidate.identity_evidence_status || 'missing',
    };
}

function looksLikeMatchObject(value) {
    return isObjectLike(value) && getExternalId(value) !== null;
}

function appendSourceMatches(items, sourcePath, state) {
    for (const item of Array.isArray(items) ? items : []) {
        if (isObjectLike(item) && state.seenObjects?.has(item)) {
            continue;
        }
        if (looksLikeMatchObject(item)) {
            state.seenObjects?.add(item);
            state.matches.push({ match: item, sourcePath });
        }
    }
}

function appendGroupedMatches(grouped, sourcePath, state) {
    if (!isObjectLike(grouped)) {
        return;
    }
    for (const [key, value] of Object.entries(grouped)) {
        if (Array.isArray(value)) {
            appendSourceMatches(value, `${sourcePath}.${key}`, state);
        }
    }
}

function appendKnownSourcePaths(response, state) {
    appendSourceMatches(
        response?.weeksWithMatches?.flatMap(week => week?.matches || []) || [],
        'weeksWithMatches.matches',
        state
    );
    appendSourceMatches(
        response?.weeks?.flatMap(week => week?.matches || week?.fixtures || []) || [],
        'weeks.matches',
        state
    );
    appendSourceMatches(
        response?.rounds?.flatMap(round => round?.matches || round?.fixtures || []) || [],
        'rounds.matches',
        state
    );
    appendSourceMatches(response?.fixtures?.allMatches, 'fixtures.allMatches', state);
    appendSourceMatches(Array.isArray(response?.fixtures) ? response.fixtures : [], 'fixtures', state);
    appendGroupedMatches(!Array.isArray(response?.fixtures) ? response?.fixtures : null, 'fixtures', state);
    appendSourceMatches(response?.matches?.allMatches, 'matches.allMatches', state);
    appendSourceMatches(Array.isArray(response?.matches) ? response.matches : [], 'matches', state);
    appendGroupedMatches(!Array.isArray(response?.matches) ? response?.matches : null, 'matches', state);
    appendSourceMatches(response?.allMatches, 'allMatches', state);
}

function greedyScanSourceMatches(node, sourcePath, depth, state) {
    if (depth > 5 || !isObjectLike(node)) {
        return;
    }
    if (Array.isArray(node)) {
        appendSourceMatches(node, sourcePath, state);
        for (const item of node) {
            greedyScanSourceMatches(item, sourcePath, depth + 1, state);
        }
        return;
    }
    if (looksLikeMatchObject(node)) {
        if (state.seenObjects?.has(node)) {
            return;
        }
        state.seenObjects?.add(node);
        state.matches.push({ match: node, sourcePath });
    }
    for (const [key, value] of Object.entries(node)) {
        greedyScanSourceMatches(value, sourcePath ? `${sourcePath}.${key}` : key, depth + 1, state);
    }
}

function extractSourceInventoryMatches(sourceJson) {
    const state = { matches: [], seenObjects: new WeakSet() };
    appendKnownSourcePaths(sourceJson, state);
    greedyScanSourceMatches(sourceJson, '', 0, state);
    return state.matches;
}

function isNumericExternalId(value) {
    return /^\d+$/.test(normalizeText(value));
}

function buildMatchId(externalId) {
    return `${LEAGUE_ID}_${SEASON.replace(/[/_-]/g, '')}_${externalId}`;
}

function isIdentityComplete(candidate) {
    return Boolean(candidate.external_id && candidate.home_team && candidate.away_team && candidate.kickoff_time);
}

function buildCandidateTarget(candidate, priority, nowIso) {
    const identityComplete = isIdentityComplete(candidate);
    const matchId = identityComplete ? buildMatchId(candidate.external_id) : null;
    const targetStatus = identityComplete ? 'source_inventory_discovered' : 'identity_incomplete';
    const sourceEvidence = buildMissingSourceIdentityEvidence(candidate);
    return {
        target_id: identityComplete ? `${BATCH_ID}:${matchId}` : `${BATCH_ID}:external:${candidate.external_id}`,
        batch_id: BATCH_ID,
        source: SOURCE,
        route: TARGET_ROUTE,
        source_inventory_route: SOURCE_INVENTORY_ROUTE,
        raw_data_version: RAW_VERSION,
        hash_strategy: HASH_STRATEGY,
        match_id: matchId,
        external_id: candidate.external_id,
        source_url: candidate.source_url,
        source_path: candidate.source_path,
        source_page_url: sourceEvidence.source_page_url,
        source_page_url_base: sourceEvidence.source_page_url_base,
        source_url_fragment_external_id: sourceEvidence.source_url_fragment_external_id,
        source_slug: sourceEvidence.source_slug,
        source_route_code: sourceEvidence.source_route_code,
        source_url_path_slug: sourceEvidence.source_url_path_slug,
        detail_external_id_candidate: sourceEvidence.detail_external_id_candidate,
        detail_identity_source: sourceEvidence.detail_identity_source,
        schedule_external_id: candidate.external_id || null,
        schedule_date: candidate.kickoff_time || null,
        schedule_home_team: candidate.home_team || null,
        schedule_away_team: candidate.away_team || null,
        source_inventory_record_key: sourceEvidence.source_inventory_record_key,
        source_inventory_generated_at: sourceEvidence.source_inventory_generated_at,
        identity_evidence_status: sourceEvidence.identity_evidence_status,
        league_id: LEAGUE_ID,
        league_name: LEAGUE_NAME,
        season: SEASON,
        home_team: candidate.home_team,
        away_team: candidate.away_team,
        kickoff_time: candidate.kickoff_time,
        match_date: candidate.kickoff_time,
        status: candidate.status,
        round: candidate.round,
        target_status: targetStatus,
        priority,
        expected_coverage_tier: 'unknown_until_profiled',
        existing_versions: [],
        preflight_status: identityComplete ? 'not_started' : 'blocked',
        baseline_hash: null,
        last_preflight_at: null,
        write_status: 'not_started',
        write_attempt_count: 0,
        failure_reason: identityComplete ? null : 'missing_identity_metadata',
        source_fidelity_notes: identityComplete
            ? 'source_inventory_discovered_no_match_detail_fetch'
            : 'source_inventory_identity_incomplete_no_match_detail_fetch',
        odds_alignment_ready: identityComplete,
        created_at: nowIso,
        updated_at: nowIso,
    };
}

function normalizeSourceCandidate(rawEntry) {
    const match = rawEntry.match;
    const externalId = normalizeText(getExternalId(match));
    if (!isNumericExternalId(externalId)) {
        return { validExternalId: false, external_id: externalId || null };
    }
    const sourcePath = resolveSourcePath(match) || rawEntry.sourcePath || null;
    const sourceEvidence = deriveSourceInventoryIdentityEvidence({
        match,
        sourcePath: rawEntry.sourcePath || sourcePath,
        externalId,
        generatedAt: rawEntry.sourceInventoryGeneratedAt || rawEntry.generatedAt || 'unknown',
    });
    return {
        validExternalId: true,
        external_id: externalId,
        source_url: sourcePath && /^https?:\/\//.test(sourcePath) ? sourcePath : null,
        source_path: sourcePath && !/^https?:\/\//.test(sourcePath) ? sourcePath : null,
        source_page_url: sourceEvidence.source_page_url,
        source_page_url_base: sourceEvidence.source_page_url_base,
        source_url_fragment_external_id: sourceEvidence.source_url_fragment_external_id,
        source_slug: sourceEvidence.source_slug,
        source_route_code: sourceEvidence.source_route_code,
        source_url_path_slug: sourceEvidence.source_url_path_slug,
        detail_external_id_candidate: sourceEvidence.detail_external_id_candidate,
        detail_identity_source: sourceEvidence.detail_identity_source,
        source_inventory_record_key: sourceEvidence.source_inventory_record_key,
        source_inventory_generated_at: sourceEvidence.source_inventory_generated_at,
        identity_evidence_status: sourceEvidence.identity_evidence_status,
        home_team: resolveTeamName(match, 'home'),
        away_team: resolveTeamName(match, 'away'),
        kickoff_time: resolveKickoffTime(match),
        status: resolveStatus(match),
        round: resolveRound(match, rawEntry.sourcePath),
    };
}

function buildKnownCompletedExternalIds(knownCompletedTargets = []) {
    return new Set(
        knownCompletedTargets
            .filter(target => Array.isArray(target.existing_versions) && target.existing_versions.includes(RAW_VERSION))
            .map(target => normalizeText(target.external_id))
            .filter(Boolean)
    );
}

function normalizeL1Candidate(candidate) {
    const externalId = normalizeText(candidate?.external_id);
    if (!isNumericExternalId(externalId) || candidate?.valid_external_id === false) {
        return { validExternalId: false, external_id: externalId || null };
    }
    return {
        validExternalId: true,
        external_id: externalId,
        source_url: candidate?.source_url || null,
        source_path: candidate?.source_path || L1_SOURCE_INVENTORY_ROUTE_KIND,
        source_page_url: candidate?.source_page_url || null,
        source_page_url_base: candidate?.source_page_url_base || null,
        source_url_fragment_external_id: candidate?.source_url_fragment_external_id || null,
        source_slug: candidate?.source_slug || null,
        source_route_code: candidate?.source_route_code || null,
        source_url_path_slug: candidate?.source_url_path_slug || candidate?.source_route_code || null,
        detail_external_id_candidate: candidate?.detail_external_id_candidate || null,
        detail_identity_source: candidate?.detail_identity_source || null,
        source_inventory_record_key: candidate?.source_inventory_record_key || null,
        source_inventory_generated_at: candidate?.source_inventory_generated_at || 'unknown',
        identity_evidence_status: candidate?.identity_evidence_status || 'missing',
        home_team: normalizeText(candidate?.home_team) || null,
        away_team: normalizeText(candidate?.away_team) || null,
        kickoff_time: parseDateValue(candidate?.kickoff_time || candidate?.match_date),
        status: normalizeText(candidate?.status).toLowerCase() || 'scheduled',
        round: candidate?.round || null,
    };
}

function buildCandidateTargetsFromNormalizedItems(items, normalizeCandidate, knownCompletedTargets = [], options = {}) {
    const nowIso = options.nowIso || new Date().toISOString();
    const knownCompletedExternalIds = buildKnownCompletedExternalIds(knownCompletedTargets);
    const seenCandidateExternalIds = new Set();
    const candidateTargets = [];
    const stats = {
        discovered_raw_target_count: items.length,
        excluded_completed_count: 0,
        duplicate_removed_count: 0,
        invalid_identity_count: 0,
        capped_removed_count: 0,
    };

    for (const item of items) {
        const candidate = normalizeCandidate(item);
        if (!candidate.validExternalId) {
            stats.invalid_identity_count += 1;
            continue;
        }
        if (seenCandidateExternalIds.has(candidate.external_id)) {
            stats.duplicate_removed_count += 1;
            continue;
        }
        seenCandidateExternalIds.add(candidate.external_id);
        if (knownCompletedExternalIds.has(candidate.external_id)) {
            stats.excluded_completed_count += 1;
            continue;
        }
        if (!candidate.home_team || !candidate.away_team || !candidate.kickoff_time) {
            stats.invalid_identity_count += 1;
        }
        if (candidateTargets.length >= TARGET_COUNT_MAX) {
            stats.capped_removed_count += 1;
            continue;
        }
        candidateTargets.push(buildCandidateTarget(candidate, candidateTargets.length + 1, nowIso));
    }

    const eligibleCandidateTargets = candidateTargets.filter(
        target => target.target_status === 'source_inventory_discovered'
    );
    const targetPopulationStatus =
        eligibleCandidateTargets.length >= TARGET_COUNT_MIN ? READY_FOR_PREFLIGHT : INSUFFICIENT_CANDIDATES;
    const requiredNextStep =
        targetPopulationStatus === READY_FOR_PREFLIGHT ? NEXT_PREFLIGHT : NEXT_ADDITIONAL_DISCOVERY;

    return {
        candidate_targets: candidateTargets,
        candidate_targets_count: candidateTargets.length,
        preflight_eligible_candidate_targets_count: eligibleCandidateTargets.length,
        target_population_status: targetPopulationStatus,
        required_next_step: requiredNextStep,
        ...stats,
    };
}

function buildCandidateTargetsFromSource(rawSourceMatches, knownCompletedTargets = [], options = {}) {
    return buildCandidateTargetsFromNormalizedItems(
        rawSourceMatches,
        normalizeSourceCandidate,
        knownCompletedTargets,
        options
    );
}

function buildCandidateTargetsFromL1Candidates(l1Candidates, knownCompletedTargets = [], options = {}) {
    return buildCandidateTargetsFromNormalizedItems(
        Array.isArray(l1Candidates) ? l1Candidates : [],
        normalizeL1Candidate,
        knownCompletedTargets,
        options
    );
}

function buildTargetManifestSchema() {
    return TARGET_MANIFEST_FIELDS.map(field => ({
        field,
        required_for_future_target: true,
    }));
}

function buildReadinessGates() {
    return [
        'manifest reviewed',
        'target identities verified',
        'no invented external_id',
        'duplicate detection passed',
        'no existing fotmob_pageprops_v2 for new targets',
        'explicit network authorization before target discovery/preflight',
        'no-write preflight before write',
        'baseline hash capture before write',
        'separate final DB write confirmation before controlled write',
    ];
}

function buildSelectionPolicy() {
    return [
        'same league/season as seeded validation first',
        'exclude completed fotmob_pageprops_v2 targets',
        'prefer finished matches first for stable pageProps profile',
        'defer scheduled matches until prediction-time raw policy exists',
        'exclude cancelled/postponed/abandoned unless explicitly profiled',
        'require duplicate detection before preflight',
        'require kickoff_time / match identity for odds alignment readiness',
    ];
}

function updateManifestProposal(existingManifest, discoveryResult, requestMetadata) {
    const knownCompletedTargets = Array.isArray(existingManifest.known_completed_targets)
        ? existingManifest.known_completed_targets
        : [];
    return {
        ...existingManifest,
        schema_version: 'target_manifest_proposal_v1',
        batch_id: BATCH_ID,
        source: SOURCE,
        route: TARGET_ROUTE,
        source_inventory_route: SOURCE_INVENTORY_ROUTE,
        raw_data_version: RAW_VERSION,
        hash_strategy: HASH_STRATEGY,
        league: {
            league_id: LEAGUE_ID,
            league_name: LEAGUE_NAME,
            season: SEASON,
        },
        batch_type: BATCH_TYPE,
        batch_size_policy: '20-50',
        target_population_status: discoveryResult.target_population_status,
        known_completed_targets: knownCompletedTargets,
        candidate_targets: discoveryResult.candidate_targets,
        candidate_targets_count: discoveryResult.candidate_targets_count,
        preflight_eligible_candidate_targets_count: discoveryResult.preflight_eligible_candidate_targets_count,
        target_manifest_schema: buildTargetManifestSchema(),
        selection_policy: buildSelectionPolicy(),
        readiness_gates: buildReadinessGates(),
        required_next_step: discoveryResult.required_next_step,
        source_inventory_result: {
            route_used: SOURCE_INVENTORY_ROUTE,
            generated_url: requestMetadata.source_url,
            reused_l1_capability: true,
            l1_capability: 'FotMobSourceInventoryAdapter',
            l1_route_kind: requestMetadata.l1_route_kind || L1_SOURCE_INVENTORY_ROUTE_KIND,
            request_count: requestMetadata.request_count,
            status_code: requestMetadata.status_codes?.[0] ?? null,
            status_codes: requestMetadata.status_codes,
            content_type_summary: requestMetadata.content_type_summary,
            parse_status: requestMetadata.parse_status,
            blocked_markers: requestMetadata.blocked_markers,
            discovered_raw_target_count: discoveryResult.discovered_raw_target_count,
            excluded_completed_count: discoveryResult.excluded_completed_count,
            duplicate_removed_count: discoveryResult.duplicate_removed_count,
            invalid_identity_count: discoveryResult.invalid_identity_count,
            capped_removed_count: discoveryResult.capped_removed_count,
            candidate_targets_count: discoveryResult.candidate_targets_count,
            preflight_eligible_candidate_targets_count: discoveryResult.preflight_eligible_candidate_targets_count,
            target_population_status: discoveryResult.target_population_status,
            required_next_step: discoveryResult.required_next_step,
            no_full_body_printed: true,
            no_full_body_saved: true,
            no_full_json_printed: true,
            no_full_json_saved: true,
        },
        non_execution: {
            db_write_executed: false,
            raw_match_data_write_executed: false,
            bookmaker_odds_history_write_executed: false,
            match_detail_pageprops_fetch_executed: false,
            controlled_write_executed: false,
            schema_migration_executed: false,
            parser_implementation_executed: false,
            feature_extraction_executed: false,
            training_executed: false,
            prediction_executed: false,
            browser_proxy_executed: false,
            invented_targets: false,
            fabricated_external_ids: false,
        },
    };
}

async function queryReadOnlyDbSnapshot(dependencies = {}) {
    if (dependencies.dbSnapshot) {
        return dependencies.dbSnapshot;
    }
    const pool =
        dependencies.pool ||
        new Pool({
            host: process.env.DB_HOST || 'localhost',
            port: Number(process.env.DB_PORT || 5432),
            database: process.env.DB_NAME || 'football_db',
            user: process.env.DB_USER || 'football_user',
            password: process.env.DB_PASSWORD,
        });
    const shouldEndPool = !dependencies.pool;
    try {
        const rowCountResult = await pool.query(`
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
        `);
        const completedResult = await pool.query(
            `
            SELECT
                m.match_id,
                m.external_id,
                m.league_name,
                m.season,
                m.home_team,
                m.away_team,
                m.match_date,
                m.status,
                array_agg(r.data_version ORDER BY r.data_version) FILTER (WHERE r.id IS NOT NULL) AS existing_versions
            FROM matches m
            LEFT JOIN raw_match_data r ON r.match_id = m.match_id
            WHERE m.match_id LIKE $1
              AND m.league_name = $2
              AND m.season = $3
            GROUP BY m.match_id, m.external_id, m.league_name, m.season, m.home_team, m.away_team, m.match_date, m.status
            ORDER BY m.match_date, m.match_id
        `,
            [`${LEAGUE_ID}_%`, LEAGUE_NAME, SEASON]
        );
        return {
            row_counts: Object.fromEntries(rowCountResult.rows.map(row => [row.table_name, Number(row.rows)])),
            known_completed_targets: completedResult.rows
                .map(row => ({
                    target_id: `${BATCH_ID}:${row.match_id}`,
                    batch_id: BATCH_ID,
                    source: SOURCE,
                    route: TARGET_ROUTE,
                    raw_data_version: RAW_VERSION,
                    hash_strategy: HASH_STRATEGY,
                    match_id: row.match_id,
                    external_id: row.external_id,
                    league_id: LEAGUE_ID,
                    league_name: row.league_name,
                    season: row.season,
                    home_team: row.home_team,
                    away_team: row.away_team,
                    kickoff_time: row.match_date instanceof Date ? row.match_date.toISOString() : row.match_date,
                    match_date: row.match_date instanceof Date ? row.match_date.toISOString() : row.match_date,
                    status: row.status,
                    existing_versions: Array.isArray(row.existing_versions) ? row.existing_versions : [],
                    target_status: 'already_completed',
                    exclude_from_new_profile_batch: true,
                    reason: 'already_has_fotmob_pageprops_v2',
                    odds_alignment_ready: true,
                }))
                .filter(target => target.existing_versions.includes(RAW_VERSION)),
        };
    } finally {
        if (shouldEndPool) {
            await pool.end();
        }
    }
}

function validateDbBaseline(rowCounts) {
    const mismatches = [];
    for (const [tableName, expectedRows] of Object.entries(EXPECTED_ROW_COUNTS)) {
        if (Number(rowCounts?.[tableName]) !== expectedRows) {
            mismatches.push(`${tableName} expected ${expectedRows}, got ${rowCounts?.[tableName]}`);
        }
    }
    return mismatches;
}

function readManifestProposal(dependencies = {}) {
    if (dependencies.manifest) {
        return dependencies.manifest;
    }
    const readFileSync = dependencies.readFileSync || fs.readFileSync;
    return JSON.parse(readFileSync(dependencies.manifestPath || MANIFEST_PATH, 'utf8'));
}

function writeManifestProposal(manifest, dependencies = {}) {
    if (typeof dependencies.writeManifest === 'function') {
        dependencies.writeManifest(manifest);
        return;
    }
    const writeFileSync = dependencies.writeFileSync || fs.writeFileSync;
    writeFileSync(dependencies.manifestPath || MANIFEST_PATH, `${JSON.stringify(manifest, null, 4)}\n`);
}

async function buildPreflightOutput(input, dependencies = {}) {
    const dbSnapshot = await queryReadOnlyDbSnapshot(dependencies);
    const baselineMismatches = validateDbBaseline(dbSnapshot.row_counts);
    if (baselineMismatches.length > 0) {
        throw new Error(`DB baseline mismatch: ${baselineMismatches.join('; ')}`);
    }

    const existingManifest = readManifestProposal(dependencies);
    const completedTargets =
        Array.isArray(dbSnapshot.known_completed_targets) && dbSnapshot.known_completed_targets.length > 0
            ? dbSnapshot.known_completed_targets
            : existingManifest.known_completed_targets || [];
    const adapter = createSourceInventoryAdapter(dependencies);
    const { json, requestMetadata } = await fetchSourceInventoryJson(input, {
        ...dependencies,
        sourceInventoryAdapter: adapter,
    });
    const l1Candidates = adapter.parseSourceInventory(json, input);
    const discoveryResult = buildCandidateTargetsFromL1Candidates(l1Candidates, completedTargets, {
        nowIso: dependencies.nowIso,
    });
    const updatedManifest = updateManifestProposal(
        { ...existingManifest, known_completed_targets: completedTargets },
        discoveryResult,
        requestMetadata
    );
    writeManifestProposal(updatedManifest, dependencies);

    return {
        phase: PHASE,
        source_inventory_preflight_only: true,
        controlled_network_source_inventory_only: true,
        db_write_executed: false,
        raw_match_data_write_executed: false,
        match_detail_pageprops_fetch_executed: false,
        schema_migration_executed: false,
        parser_implementation_executed: false,
        feature_extraction_executed: false,
        training_executed: false,
        prediction_executed: false,
        browser_runtime_executed: false,
        proxy_runtime_executed: false,
        retry_executed: false,
        full_body_printed: false,
        full_body_saved: false,
        full_json_printed: false,
        full_json_saved: false,
        invented_targets: false,
        fabricated_external_ids: false,
        db_baseline: dbSnapshot.row_counts,
        known_completed_targets_count: completedTargets.length,
        known_completed_external_ids: completedTargets.map(target => target.external_id),
        discovery_authorization: {
            network_authorization: 'yes',
            source_inventory_authorization: 'yes',
            concurrency: 1,
            retry: 0,
            no_browser_proxy: true,
            no_match_detail_fetch: true,
            no_db_write: true,
            no_full_body_json_print_save: true,
        },
        source_inventory_route: {
            route_used: SOURCE_INVENTORY_ROUTE,
            generated_url: requestMetadata.source_url,
            reused_l1_capability: true,
            l1_capability: 'FotMobSourceInventoryAdapter',
            l1_route_kind: requestMetadata.l1_route_kind || L1_SOURCE_INVENTORY_ROUTE_KIND,
            request_count: requestMetadata.request_count,
            status_code: requestMetadata.status_codes?.[0] ?? null,
            status_codes: requestMetadata.status_codes,
            content_type_summary: requestMetadata.content_type_summary,
            parse_status: requestMetadata.parse_status,
            blocked_markers: requestMetadata.blocked_markers,
        },
        candidate_discovery_result: {
            discovered_raw_target_count: discoveryResult.discovered_raw_target_count,
            excluded_completed_count: discoveryResult.excluded_completed_count,
            duplicate_removed_count: discoveryResult.duplicate_removed_count,
            invalid_identity_count: discoveryResult.invalid_identity_count,
            capped_removed_count: discoveryResult.capped_removed_count,
            candidate_targets_count: discoveryResult.candidate_targets_count,
            preflight_eligible_candidate_targets_count: discoveryResult.preflight_eligible_candidate_targets_count,
            target_population_status: discoveryResult.target_population_status,
            required_next_step: discoveryResult.required_next_step,
        },
        candidate_targets: discoveryResult.candidate_targets,
        manifest_update: {
            manifest_path: dependencies.manifestPath || MANIFEST_PATH,
            known_completed_targets_count: completedTargets.length,
            candidate_targets_count: discoveryResult.candidate_targets_count,
            target_population_status: discoveryResult.target_population_status,
            required_next_step: discoveryResult.required_next_step,
            no_invented_external_id: true,
        },
    };
}

function buildErrorOutput(errors = [], extra = {}) {
    return {
        phase: PHASE,
        blocked: true,
        errors,
        db_write_executed: false,
        raw_match_data_write_executed: false,
        match_detail_pageprops_fetch_executed: false,
        schema_migration_executed: false,
        parser_implementation_executed: false,
        feature_extraction_executed: false,
        training_executed: false,
        prediction_executed: false,
        browser_runtime_executed: false,
        proxy_runtime_executed: false,
        retry_executed: false,
        full_body_printed: false,
        full_body_saved: false,
        full_json_printed: false,
        full_json_saved: false,
        invented_targets: false,
        fabricated_external_ids: false,
        ...extra,
    };
}

function printUsage(io = process.stderr) {
    io.write(
        [
            'Usage:',
            '  node scripts/ops/single_league_target_discovery_source_inventory_preflight.js \\',
            '    --source=fotmob --league-id=53 --league-name="Ligue 1" --season=2025/2026 \\',
            '    --route=source_inventory --raw-version=fotmob_pageprops_v2 \\',
            '    --hash-strategy=stable_pageprops_payload_v1 \\',
            `    --batch-id=${BATCH_ID} --target-count-min=20 --target-count-max=50 \\`,
            '    --network-authorization=yes --source-inventory-authorization=yes \\',
            '    --allow-db-write=no --allow-raw-match-data-write=no --allow-match-detail-fetch=no \\',
            '    --allow-schema-migration=no --allow-parser-implementation=no --allow-feature-extraction=no \\',
            '    --allow-training=no --allow-prediction=no --allow-browser-runtime=no --allow-proxy-runtime=no \\',
            '    --concurrency=1 --retry=0 --print-full-body=no --save-full-body=no \\',
            '    --print-full-json=no --save-full-json=no',
            '',
        ].join('\n')
    );
}

async function execute(argv = process.argv.slice(2), io = {}, dependencies = {}) {
    const stdout = io.stdout || process.stdout;
    const stderr = io.stderr || process.stderr;
    const parsed = parseArgs(argv);

    if (parsed.help) {
        printUsage(stdout);
        return 0;
    }

    const validation = validatePreflightInput(parsed);
    if (!validation.ok) {
        stderr.write(`${JSON.stringify(buildErrorOutput(validation.errors), null, 2)}\n`);
        return 1;
    }

    try {
        const output = await buildPreflightOutput(validation.value, dependencies);
        stdout.write(`${JSON.stringify(output, null, 2)}\n`);
        return 0;
    } catch (error) {
        stderr.write(
            `${JSON.stringify(
                buildErrorOutput([error.message], {
                    source_inventory_route: error.requestMetadata || null,
                }),
                null,
                2
            )}\n`
        );
        return 1;
    }
}

if (require.main === module) {
    execute().then(exitCode => {
        process.exitCode = exitCode;
    });
}

module.exports = {
    PHASE,
    parseArgs,
    validatePreflightInput,
    buildSourceInventoryUrl,
    detectBlockedMarkers,
    extractSourceInventoryMatches,
    buildCandidateTargetsFromSource,
    buildCandidateTargetsFromL1Candidates,
    updateManifestProposal,
    validateDbBaseline,
    buildPreflightOutput,
    execute,
};
