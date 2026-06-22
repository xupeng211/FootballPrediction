#!/usr/bin/env node
/* eslint-disable complexity, max-lines, max-statements */
'use strict';

const fs = require('node:fs');
const path = require('node:path');

const { assertDbWriteAllowed } = require('./helpers/db_write_guard');

const {
    CANDIDATE_VERSION,
    HASH_STRATEGY,
    buildFotMobMatchUrl,
    fetchHtml,
    extractNextDataJsonFromHtml,
    getPageProps,
    computeStablePagePropsHash,
    listJsonPaths,
    summarizeJsonShape,
} = require('./pageprops_v2_no_write_preview');
const {
    reconcileRouteIdentity,
    assertRawWriteIdentityGate,
} = require('../../src/infrastructure/services/FotMobRouteIdentityReconciler');

const PHASE = 'PHASE5_21L2V_SINGLE_LEAGUE_PAGEPROPS_V2_CONTROLLED_WRITE_EXECUTION';
const MANIFEST_PATH = 'docs/_manifests/fotmob_pageprops_v2_ligue1_2025_2026_profile_001.proposal.json';
const REPORT_PATH = 'docs/_reports/SINGLE_LEAGUE_PAGEPROPS_V2_CONTROLLED_WRITE_EXECUTION_PHASE5_21L2V.md';
const SOURCE = 'fotmob';
const LEAGUE_ID = 53;
const LEAGUE_NAME = 'Ligue 1';
const SEASON = '2025/2026';
const SEASON_COMPACT = '20252026';
const ROUTE = 'html_hydration';
const RAW_VERSION = CANDIDATE_VERSION;
const BATCH_ID = 'fotmob-pageprops-v2-ligue1-2025-2026-profile-001';
const TARGET_COUNT = 50;
const KNOWN_COMPLETED_COUNT = 8;
const EXPECTED_ROW_COUNTS_BEFORE = Object.freeze({
    matches: 10,
    bookmaker_odds_history: 2,
    raw_match_data: 18,
    l3_features: 2,
    match_features_training: 2,
    predictions: 2,
});
const EXPECTED_ROW_COUNTS_AFTER_SUCCESS = Object.freeze({
    ...EXPECTED_ROW_COUNTS_BEFORE,
    raw_match_data: 68,
});
const PROTECTED_TABLES = Object.freeze(Object.keys(EXPECTED_ROW_COUNTS_BEFORE));
const REQUIRED_YES_FLAGS = Object.freeze([
    'finalDbWriteConfirmation',
    'networkAuthorization',
    'matchDetailRecaptureAuthorization',
    'allowDbWrite',
    'allowRawMatchDataWrite',
    'allowControlledWrite',
]);
const REQUIRED_NO_FLAGS = Object.freeze([
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
    'inventTargets',
    'fabricateExternalIds',
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
    if (arg.includes('=')) {
        return { value: arg.slice(arg.indexOf('=') + 1), consumedNext: false };
    }
    const nextArg = argv[index + 1];
    if (typeof nextArg === 'string' && !nextArg.startsWith('--')) {
        return { value: nextArg, consumedNext: true };
    }
    return { value: true, consumedNext: false };
}

function toCamelKey(rawKey) {
    return normalizeText(rawKey).replace(/[-_]([a-z0-9])/g, (_match, char) => char.toUpperCase());
}

function flagName(key) {
    return key.replace(/[A-Z]/g, char => `-${char.toLowerCase()}`);
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
        finalDbWriteConfirmation: null,
        networkAuthorization: null,
        matchDetailRecaptureAuthorization: null,
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
        concurrency: null,
        retry: null,
        printFullBody: null,
        saveFullBody: null,
        printFullJson: null,
        saveFullJson: null,
        printFullPageprops: null,
        saveFullPageprops: null,
        allowOddsWrite: false,
        executeWrite: false,
        commit: false,
        inventTargets: false,
        fabricateExternalIds: false,
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
        if (consumedNext) {
            index += 1;
        }
        if (!knownKeys.has(key)) {
            options.unknown.push(rawKey);
            continue;
        }
        options[key] = booleanKeys.has(key) ? normalizeBooleanFlag(value, true) : value;
    }
    return options;
}

function pushRequiredYes(errors, value, name) {
    if (value === true) {
        return;
    }
    if (value === false) {
        errors.push(`${name}=yes is required in Phase 5.21L2V`);
        return;
    }
    errors.push(`missing ${name}=yes`);
}

function pushRequiredNo(errors, value, name) {
    if (value === false) {
        return;
    }
    if (value === true) {
        errors.push(`${name}=yes is blocked in Phase 5.21L2V`);
        return;
    }
    errors.push(`missing ${name}=no`);
}

function requireExact(errors, actual, expected, name) {
    if (!normalizeText(actual)) {
        errors.push(`missing ${name}=${expected}`);
        return;
    }
    if (normalizeText(actual) !== expected) {
        errors.push(`${name} must be ${expected}`);
    }
}

function normalizeExecutionInput(input = {}) {
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
        finalDbWriteConfirmation: normalizeBooleanFlag(input.finalDbWriteConfirmation, undefined),
        networkAuthorization: normalizeBooleanFlag(input.networkAuthorization, undefined),
        matchDetailRecaptureAuthorization: normalizeBooleanFlag(input.matchDetailRecaptureAuthorization, undefined),
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
        concurrency: parseInteger(input.concurrency, null),
        retry: parseInteger(input.retry, null),
        printFullBody: normalizeBooleanFlag(input.printFullBody, undefined),
        saveFullBody: normalizeBooleanFlag(input.saveFullBody, undefined),
        printFullJson: normalizeBooleanFlag(input.printFullJson, undefined),
        saveFullJson: normalizeBooleanFlag(input.saveFullJson, undefined),
        printFullPageprops: normalizeBooleanFlag(input.printFullPageprops, undefined),
        saveFullPageprops: normalizeBooleanFlag(input.saveFullPageprops, undefined),
        allowOddsWrite: normalizeBooleanFlag(input.allowOddsWrite, false),
        executeWrite: normalizeBooleanFlag(input.executeWrite, false),
        commit: normalizeBooleanFlag(input.commit, false),
        inventTargets: normalizeBooleanFlag(input.inventTargets, false),
        fabricateExternalIds: normalizeBooleanFlag(input.fabricateExternalIds, false),
        unknown: Array.isArray(input.unknown) ? input.unknown : [],
    };
}

function validateExecutionInput(input = {}) {
    const value = normalizeExecutionInput(input);
    const errors = [];
    if (value.unknown.length > 0) {
        errors.push(`unknown arguments: ${value.unknown.join(', ')}`);
    }
    requireExact(errors, value.manifest, MANIFEST_PATH, 'manifest');
    requireExact(errors, value.source, SOURCE, 'source');
    if (value.leagueId !== LEAGUE_ID) {
        errors.push('league-id must be 53');
    }
    requireExact(errors, value.leagueName, LEAGUE_NAME, 'league-name');
    requireExact(errors, value.season, SEASON, 'season');
    requireExact(errors, value.route, ROUTE, 'route');
    requireExact(errors, value.rawVersion, RAW_VERSION, 'raw-version');
    requireExact(errors, value.hashStrategy, HASH_STRATEGY, 'hash-strategy');
    requireExact(errors, value.batchId, BATCH_ID, 'batch-id');
    if (value.targetCount !== TARGET_COUNT) {
        errors.push('target-count must be 50');
    }
    for (const key of REQUIRED_YES_FLAGS) {
        pushRequiredYes(errors, value[key], flagName(key));
    }
    for (const key of REQUIRED_NO_FLAGS) {
        pushRequiredNo(errors, value[key], flagName(key));
    }
    if (value.concurrency !== 1) {
        errors.push('concurrency must be 1');
    }
    if (value.retry !== 0) {
        errors.push('retry must be 0');
    }
    for (const key of BLOCKED_TRUE_FLAGS) {
        if (value[key] === true) {
            errors.push(`${flagName(key)}=yes is blocked in Phase 5.21L2V`);
        }
    }
    return { ok: errors.length === 0, errors, value };
}

function isPlainObject(value) {
    return value !== null && typeof value === 'object' && !Array.isArray(value);
}

function jsonClone(value) {
    if (value === undefined) {
        return undefined;
    }
    return JSON.parse(JSON.stringify(value));
}

function jsonByteLength(value) {
    return Buffer.byteLength(JSON.stringify(value), 'utf8');
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
        league_id: parseInteger(target.league_id, null),
        league_name: normalizeText(target.league_name),
        season: normalizeText(target.season),
        preflight_status: normalizeText(target.preflight_status),
        baseline_hash: normalizeText(target.baseline_hash).toLowerCase(),
        write_plan_status: normalizeText(target.write_plan_status),
        write_status: normalizeText(target.write_status),
        failure_reason: target.failure_reason === undefined ? null : target.failure_reason,
    };
}

function findDuplicates(values = []) {
    const seen = new Set();
    const duplicates = new Set();
    for (const value of values.map(normalizeText).filter(Boolean)) {
        if (seen.has(value)) {
            duplicates.add(value);
        }
        seen.add(value);
    }
    return duplicates;
}

function validateCandidateTargets(manifest = {}) {
    const candidates = Array.isArray(manifest.candidate_targets)
        ? manifest.candidate_targets.map(normalizeCandidateTarget)
        : [];
    const errors = [];
    if (candidates.length !== TARGET_COUNT) {
        errors.push(`candidate_targets must contain ${TARGET_COUNT} targets`);
    }
    const duplicateExternalIds = findDuplicates(candidates.map(target => target.external_id));
    const duplicateMatchIds = findDuplicates(candidates.map(target => target.match_id));
    const candidateErrors = [];
    for (const target of candidates) {
        const targetErrors = [];
        if (!/^\d+$/.test(target.external_id)) {
            targetErrors.push('external_id must be numeric');
        }
        const expectedMatchId = `${LEAGUE_ID}_${SEASON_COMPACT}_${target.external_id}`;
        if (target.match_id !== expectedMatchId) {
            targetErrors.push(`match_id must be ${expectedMatchId}`);
        }
        if (duplicateExternalIds.has(target.external_id)) {
            targetErrors.push('duplicate external_id');
        }
        if (duplicateMatchIds.has(target.match_id)) {
            targetErrors.push('duplicate match_id');
        }
        if (target.batch_id !== BATCH_ID) {
            targetErrors.push('batch_id mismatch');
        }
        if (target.source !== SOURCE) {
            targetErrors.push('source mismatch');
        }
        if (target.route !== ROUTE) {
            targetErrors.push('route mismatch');
        }
        if (target.raw_data_version !== RAW_VERSION) {
            targetErrors.push('raw_data_version mismatch');
        }
        if (target.hash_strategy !== HASH_STRATEGY) {
            targetErrors.push('hash_strategy mismatch');
        }
        if (target.league_id !== LEAGUE_ID) {
            targetErrors.push('league_id mismatch');
        }
        if (target.league_name !== LEAGUE_NAME) {
            targetErrors.push('league_name mismatch');
        }
        if (target.season !== SEASON) {
            targetErrors.push('season mismatch');
        }
        if (target.preflight_status !== 'hash_baseline_ready') {
            targetErrors.push('preflight_status must be hash_baseline_ready');
        }
        if (!/^[a-f0-9]{64}$/.test(target.baseline_hash)) {
            targetErrors.push('baseline_hash must be 64 hex');
        }
        if (target.failure_reason !== null && normalizeText(target.failure_reason)) {
            targetErrors.push('failure_reason must be empty');
        }
        if (!['not_started', 'pending_final_db_write_confirmation'].includes(target.write_status)) {
            targetErrors.push('write_status must be not_started or pending_final_db_write_confirmation');
        }
        if (target.write_plan_status && target.write_plan_status !== 'eligible_for_insert') {
            targetErrors.push('write_plan_status must be eligible_for_insert when set on target');
        }
        if (targetErrors.length > 0) {
            candidateErrors.push({
                match_id: target.match_id,
                external_id: target.external_id,
                errors: targetErrors,
            });
        }
    }
    for (const targetError of candidateErrors) {
        errors.push(`${targetError.match_id || targetError.external_id}: ${targetError.errors.join(', ')}`);
    }
    return {
        ok: errors.length === 0,
        errors,
        candidates,
        duplicate_external_id_count: duplicateExternalIds.size,
        duplicate_match_id_count: duplicateMatchIds.size,
    };
}

function validateManifestGate(manifest = {}) {
    const errors = [];
    if (normalizeText(manifest.batch_id) !== BATCH_ID) {
        errors.push('manifest batch_id mismatch');
    }
    if (normalizeText(manifest.source).toLowerCase() !== SOURCE) {
        errors.push('manifest source mismatch');
    }
    if (normalizeText(manifest.route) !== ROUTE) {
        errors.push('manifest route mismatch');
    }
    if (normalizeText(manifest.raw_data_version) !== RAW_VERSION) {
        errors.push('manifest raw_data_version mismatch');
    }
    if (normalizeText(manifest.hash_strategy) !== HASH_STRATEGY) {
        errors.push('manifest hash_strategy mismatch');
    }
    if (Number(manifest.league?.league_id) !== LEAGUE_ID) {
        errors.push('manifest league_id mismatch');
    }
    if (normalizeText(manifest.league?.league_name) !== LEAGUE_NAME) {
        errors.push('manifest league_name mismatch');
    }
    if (normalizeText(manifest.league?.season) !== SEASON) {
        errors.push('manifest season mismatch');
    }
    if (
        !Array.isArray(manifest.known_completed_targets) ||
        manifest.known_completed_targets.length !== KNOWN_COMPLETED_COUNT
    ) {
        errors.push(`known_completed_targets must contain ${KNOWN_COMPLETED_COUNT} targets`);
    }
    const targetPopulationReady =
        normalizeText(manifest.target_population_status) === 'ready_for_controlled_write_authorization';
    const writePlanReady = normalizeText(manifest.write_plan_status) === 'ready_for_final_authorization';
    if (!targetPopulationReady && !writePlanReady) {
        errors.push('target_population_status/write_plan_status not ready for controlled write execution');
    }
    if (normalizeText(manifest.write_authorization_status) !== 'pending_final_db_write_confirmation') {
        errors.push('write_authorization_status must be pending_final_db_write_confirmation');
    }
    if (!normalizeText(manifest.required_next_step).includes('controlled_pageprops_v2_write_execution')) {
        errors.push('required_next_step must point to controlled pageProps v2 write execution');
    }
    const candidateValidation = validateCandidateTargets(manifest);
    errors.push(...candidateValidation.errors);
    return {
        ok: errors.length === 0,
        errors,
        candidates: candidateValidation.candidates,
        candidate_validation: candidateValidation,
    };
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

function validateExactRowCounts(rowCounts = {}, expected = EXPECTED_ROW_COUNTS_BEFORE) {
    const errors = [];
    for (const [table, expectedRows] of Object.entries(expected)) {
        if (Number(rowCounts[table]) !== expectedRows) {
            errors.push(`${table} expected ${expectedRows}, got ${Number(rowCounts[table] || 0)}`);
        }
    }
    return errors;
}

function buildSchemaReadiness(constraintRows = []) {
    const rows = Array.isArray(constraintRows) ? constraintRows : [];
    const byName = new Map(rows.map(row => [normalizeText(row.conname), row]));
    const errors = [];
    const versionedUnique = byName.get('raw_match_data_match_id_data_version_key');
    if (!versionedUnique) {
        errors.push('raw_match_data_match_id_data_version_key missing');
    } else if (!/UNIQUE\s*\(\s*match_id\s*,\s*data_version\s*\)/i.test(normalizeText(versionedUnique.definition))) {
        errors.push('raw_match_data_match_id_data_version_key must be UNIQUE(match_id,data_version)');
    }
    if (byName.has('raw_match_data_match_id_key')) {
        errors.push('legacy raw_match_data_match_id_key must be absent');
    }
    if (!byName.has('raw_match_data_match_id_fkey')) {
        errors.push('raw_match_data_match_id_fkey missing');
    }
    if (!byName.has('raw_data_not_empty')) {
        errors.push('raw_data_not_empty check missing');
    }
    if (!byName.has('raw_data_has_match_id')) {
        errors.push('raw_data_has_match_id check missing');
    }
    if (!byName.has('collected_at_not_null')) {
        errors.push('collected_at_not_null check missing');
    }
    return {
        ok: errors.length === 0,
        errors,
        unique_match_id_data_version_present: Boolean(versionedUnique),
        old_unique_match_id_absent: !byName.has('raw_match_data_match_id_key'),
        fk_present: byName.has('raw_match_data_match_id_fkey'),
        check_constraints_present: ['raw_data_not_empty', 'raw_data_has_match_id', 'collected_at_not_null'].every(
            name => byName.has(name)
        ),
    };
}

function buildMatchesExistenceGate(candidates = [], matchRows = []) {
    const rowsByMatchId = new Map(
        (Array.isArray(matchRows) ? matchRows : []).map(row => [normalizeText(row.match_id), row])
    );
    const missingMatches = candidates.filter(target => !rowsByMatchId.has(target.match_id));
    return {
        ok: missingMatches.length === 0,
        existing_matches_count: candidates.length - missingMatches.length,
        missing_matches_count: missingMatches.length,
        missing_matches: missingMatches.map(target => ({
            match_id: target.match_id,
            external_id: target.external_id,
            home_team: target.home_team || null,
            away_team: target.away_team || null,
            kickoff_time: target.kickoff_time || target.match_date || null,
        })),
    };
}

function buildExistingRawGate(candidates = [], rows = []) {
    const v2Rows = (Array.isArray(rows) ? rows : []).filter(row => normalizeText(row.data_version) === RAW_VERSION);
    return {
        ok: v2Rows.length === 0,
        existing_v2_count: v2Rows.length,
        conflicts: v2Rows.map(row => ({
            id: row.id ?? null,
            match_id: normalizeText(row.match_id),
            external_id: normalizeText(row.external_id),
            data_hash: normalizeText(row.data_hash) || null,
        })),
        candidate_count: candidates.length,
    };
}

function detectBlockMarkers(fetchResult = {}) {
    const markers = new Set();
    const status = Number(fetchResult.http_status || fetchResult.status || 0);
    if (status === 403) {
        markers.add('http_403');
    }
    if (status === 429) {
        markers.add('http_429');
    }
    const sample = `${normalizeText(fetchResult.error)} ${normalizeText(fetchResult.body).slice(0, 2000)}`;
    for (const [name, pattern] of BLOCK_MARKER_PATTERNS) {
        if (pattern.test(sample)) {
            markers.add(name);
        }
    }
    return [...markers].sort();
}

function buildRawDataForTarget({ target = {}, pageProps = {}, fetchResult = {}, collectedAt, generatedAt } = {}) {
    const safePageProps = jsonClone(pageProps) || {};
    const stableHash = computeStablePagePropsHash(safePageProps);
    const requestUrl = fetchResult.request_url || buildFotMobMatchUrl(target.external_id);
    return {
        _meta: {
            source: SOURCE,
            route: ROUTE,
            data_version: RAW_VERSION,
            hash_strategy: HASH_STRATEGY,
            data_hash: stableHash,
            collected_at: collectedAt || null,
            batch_id: BATCH_ID,
            match_id: target.match_id,
            external_id: target.external_id,
            request_url: requestUrl,
            final_url: fetchResult.final_url || requestUrl,
            http_status: Number(fetchResult.http_status || 0),
            content_type: fetchResult.content_type || null,
            body_byte_length: Number(fetchResult.body_byte_length || 0),
            fetch_body_sha256: fetchResult.body_sha256 || null,
            generated_at: generatedAt || new Date().toISOString(),
            preflight_baseline_hash: target.baseline_hash,
            recaptured_hash: stableHash,
            full_html_body_stored: false,
            full_next_data_stored: false,
            full_json_printed: false,
            full_pageprops_printed: false,
        },
        matchId: Number(target.external_id),
        pageProps: safePageProps,
    };
}

function validateRawDataShape(rawData = {}) {
    const errors = [];
    if (!isPlainObject(rawData)) {
        return ['raw_data must be object'];
    }
    if (!isPlainObject(rawData._meta)) {
        errors.push('raw_data._meta missing');
    }
    if (!Object.prototype.hasOwnProperty.call(rawData, 'matchId')) {
        errors.push('raw_data top-level matchId missing');
    }
    if (!isPlainObject(rawData.pageProps)) {
        errors.push('raw_data.pageProps missing');
    }
    if (rawData._meta?.hash_strategy !== HASH_STRATEGY) {
        errors.push('raw_data._meta.hash_strategy mismatch');
    }
    if (rawData._meta?.data_version !== RAW_VERSION) {
        errors.push('raw_data._meta.data_version mismatch');
    }
    return errors;
}

async function resolveFetchResultForTarget(target, index, dependencies = {}) {
    const byExternalId = dependencies.fetchResultsByExternalId || {};
    if (byExternalId[target.external_id]) {
        return byExternalId[target.external_id];
    }
    if (Array.isArray(dependencies.fetchResults) && dependencies.fetchResults[index]) {
        return dependencies.fetchResults[index];
    }
    const requestUrl = buildFotMobMatchUrl(target.external_id);
    const fetchHtmlFn = dependencies.fetchHtmlFn || fetchHtml;
    return fetchHtmlFn(requestUrl, { fetchFn: dependencies.fetchFn });
}

function publicRecaptureSummary(summary = {}) {
    const {
        rawData: _rawData,
        pageProps: _pageProps,
        candidate_shape_summary: _candidateShapeSummary,
        pageProps_shape_summary: _pagePropsShapeSummary,
        ...publicFields
    } = summary;
    return publicFields;
}

async function recaptureTarget(target, index, dependencies = {}) {
    const generatedAt = dependencies.generatedAt || new Date().toISOString();
    const fetchResult = await resolveFetchResultForTarget(target, index, dependencies);
    const requestUrl = fetchResult.request_url || buildFotMobMatchUrl(target.external_id);
    const blockMarkers = detectBlockMarkers(fetchResult);
    const base = {
        match_id: target.match_id,
        external_id: target.external_id,
        home_team: target.home_team || null,
        away_team: target.away_team || null,
        kickoff_time: target.kickoff_time || target.match_date || null,
        status: target.status || null,
        request_url: requestUrl,
        final_url: fetchResult.final_url || requestUrl,
        http_status: Number(fetchResult.http_status || fetchResult.status || 0),
        content_type: fetchResult.content_type || null,
        body_byte_length: Number(fetchResult.body_byte_length || 0),
        body_sha256: fetchResult.body_sha256 || null,
        baseline_hash: target.baseline_hash,
        block_markers: blockMarkers,
        next_data_parse_ok: false,
        page_props_found: false,
        raw_data_shape_valid: false,
        has_meta: false,
        has_matchId: false,
        has_pageProps: false,
        recaptured_hash: null,
        hash_matches_baseline: false,
        target_status: 'blocked',
        failure_reason: null,
    };
    if (blockMarkers.length > 0) {
        return { ...base, failure_reason: `BLOCK_MARKERS:${blockMarkers.join(',')}` };
    }
    if (!fetchResult.ok || Number(fetchResult.http_status || 0) !== 200) {
        return { ...base, target_status: 'recapture_failed', failure_reason: fetchResult.error || 'HTTP_NON_200' };
    }
    const extraction = extractNextDataJsonFromHtml(fetchResult.body);
    if (!extraction.ok) {
        return {
            ...base,
            target_status: 'recapture_failed',
            failure_reason: extraction.error || 'NEXT_DATA_PARSE_FAILED',
        };
    }
    const pageProps = getPageProps(extraction.data);
    if (!pageProps) {
        return {
            ...base,
            target_status: 'recapture_failed',
            next_data_parse_ok: true,
            failure_reason: 'PAGE_PROPS_NOT_FOUND',
        };
    }
    const routeIdentity = reconcileRouteIdentity({
        target,
        pageProps,
        requestedScheduleExternalId: target.external_id,
        requestedUrl: requestUrl,
        finalUrl: fetchResult.final_url || requestUrl,
        proposalOnlyMapping: target.mapping_status === 'proposal_only_unaccepted',
        acceptedIdentityMappingPresent: dependencies.acceptedIdentityMappingPresent === true,
    });
    const routeIdentityGate = assertRawWriteIdentityGate(routeIdentity);
    const rawData = buildRawDataForTarget({
        target,
        pageProps,
        fetchResult,
        collectedAt: null,
        generatedAt,
    });
    const shapeErrors = validateRawDataShape(rawData);
    const recapturedHash = computeStablePagePropsHash(pageProps);
    const hashMatchesBaseline = recapturedHash === target.baseline_hash;
    const pagePropsPaths = listJsonPaths(pageProps);
    const contentPaths = listJsonPaths(isPlainObject(pageProps.content) ? pageProps.content : {});
    const targetStatus =
        shapeErrors.length > 0
            ? 'hash_gate_failed'
            : !hashMatchesBaseline
              ? 'hash_gate_failed'
              : routeIdentityGate.ok
                ? 'hash_gate_passed'
                : 'route_identity_gate_blocked';
    const failureReason =
        shapeErrors.length > 0
            ? `RAW_DATA_SHAPE_INVALID:${shapeErrors.join(',')}`
            : !hashMatchesBaseline
              ? `HASH_DRIFT: recaptured ${recapturedHash} differs from baseline ${target.baseline_hash}`
              : routeIdentityGate.ok
                ? null
                : `${routeIdentityGate.blocked_reason}:${routeIdentity.safety_blockers.join(',')}`;
    return {
        ...base,
        ...routeIdentity,
        route_identity_gate_ok: routeIdentityGate.ok,
        next_data_parse_ok: true,
        page_props_found: true,
        raw_data_shape_valid: shapeErrors.length === 0,
        has_meta: isPlainObject(rawData._meta),
        has_matchId: Object.prototype.hasOwnProperty.call(rawData, 'matchId'),
        has_pageProps: isPlainObject(rawData.pageProps),
        recaptured_hash: recapturedHash,
        hash_matches_baseline: hashMatchesBaseline,
        target_status: targetStatus,
        failure_reason: failureReason,
        candidate_json_byte_length: jsonByteLength(rawData),
        pageProps_top_level_keys: Object.keys(pageProps).sort(),
        pageProps_path_count: pagePropsPaths.length,
        pageProps_content_path_count: contentPaths.length,
        pageProps_shape_summary: summarizeJsonShape(pageProps),
        candidate_shape_summary: summarizeJsonShape(rawData),
        rawData,
        pageProps,
    };
}

async function recaptureTargets(candidates = [], dependencies = {}) {
    const summaries = [];
    for (let index = 0; index < candidates.length; index += 1) {
        summaries.push(await recaptureTarget(candidates[index], index, dependencies));
    }
    const publicTargets = summaries.map(publicRecaptureSummary);
    return {
        targets: summaries,
        public_targets: publicTargets,
        attempted_target_count: candidates.length,
        recapture_success_count: publicTargets.filter(target => target.target_status === 'hash_gate_passed').length,
        hash_match_count: publicTargets.filter(target => target.hash_matches_baseline === true).length,
        hash_drift_count: publicTargets.filter(target => target.recaptured_hash && !target.hash_matches_baseline)
            .length,
        failed_count: publicTargets.filter(target => target.failure_reason && !target.block_markers?.length).length,
        blocked_count: publicTargets.filter(target => (target.block_markers || []).length > 0).length,
        route_identity_blocked_count: publicTargets.filter(target => target.route_identity_gate_ok === false).length,
        unresolved_schedule_detail_mapping_count: publicTargets.filter(
            target => target.identity_reconciliation_status === 'unresolved_schedule_detail_mapping'
        ).length,
        reverse_fixture_detected_count: publicTargets.filter(
            target => target.date_compatibility_status === 'reverse_fixture_detected'
        ).length,
        unresolved_large_gap_count: publicTargets.filter(
            target => target.date_compatibility_status === 'unresolved_large_gap'
        ).length,
        cross_season_slug_reuse_count: publicTargets.filter(
            target => target.date_compatibility_status === 'cross_season_slug_reuse'
        ).length,
        unknown_date_status_count: publicTargets.filter(target => target.date_compatibility_status === 'unknown')
            .length,
        request_count: candidates.length,
    };
}

function normalizeRowCounts(rowsOrObject = {}) {
    if (Array.isArray(rowsOrObject)) {
        return buildProtectedTableBaseline(rowsOrObject);
    }
    const output = {};
    for (const table of PROTECTED_TABLES) {
        output[table] = Number(rowsOrObject[table] || 0);
    }
    return output;
}

function buildInsertRawMatchDataSql(recapturedTargets = [], collectedAt) {
    const placeholders = [];
    const values = [];
    recapturedTargets.forEach((target, index) => {
        const rawData = buildRawDataForTarget({
            target,
            pageProps: target.pageProps,
            fetchResult: {
                request_url: target.request_url,
                final_url: target.final_url,
                http_status: target.http_status,
                content_type: target.content_type,
                body_byte_length: target.body_byte_length,
                body_sha256: target.body_sha256,
            },
            collectedAt,
            generatedAt: collectedAt,
        });
        target.rawData = rawData;
        const base = index * 6;
        placeholders.push(
            `($${base + 1}, $${base + 2}, $${base + 3}::jsonb, $${base + 4}::timestamptz, $${base + 5}, $${base + 6})`
        );
        values.push(
            target.match_id,
            target.external_id,
            JSON.stringify(rawData),
            collectedAt,
            RAW_VERSION,
            target.recaptured_hash
        );
    });
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
            VALUES ${placeholders.join(',\n')}
            ON CONFLICT (match_id, data_version) DO NOTHING
            RETURNING id, match_id, external_id, data_version, data_hash, collected_at
        `,
        values,
    };
}

function buildPostWriteVerification({
    candidates = [],
    rowCountsBefore = {},
    rowCountsAfter = {},
    postWriteRows = [],
    duplicateRows = [],
} = {}) {
    const errors = validateExactRowCounts(rowCountsAfter, EXPECTED_ROW_COUNTS_AFTER_SUCCESS);
    const rowsByMatchId = new Map(
        (Array.isArray(postWriteRows) ? postWriteRows : []).map(row => [normalizeText(row.match_id), row])
    );
    for (const target of candidates) {
        const row = rowsByMatchId.get(target.match_id);
        if (!row) {
            errors.push(`missing inserted v2 row ${target.match_id}`);
            continue;
        }
        if (normalizeText(row.data_version) !== RAW_VERSION) {
            errors.push(`wrong data_version ${target.match_id}`);
        }
        if (normalizeText(row.data_hash).toLowerCase() !== target.baseline_hash) {
            errors.push(`data_hash mismatch ${target.match_id}`);
        }
        if (row.has_meta !== true) {
            errors.push(`raw_data missing _meta ${target.match_id}`);
        }
        if (row.has_match_id !== true) {
            errors.push(`raw_data missing matchId ${target.match_id}`);
        }
        if (row.has_pageprops !== true) {
            errors.push(`raw_data missing pageProps ${target.match_id}`);
        }
        if (normalizeText(row.meta_hash_strategy) !== HASH_STRATEGY) {
            errors.push(`raw_data._meta.hash_strategy mismatch ${target.match_id}`);
        }
    }
    if ((duplicateRows || []).length > 0) {
        errors.push(`duplicate match_id/data_version rows: ${duplicateRows.length}`);
    }
    return {
        ok: errors.length === 0,
        errors,
        raw_match_data_before: rowCountsBefore.raw_match_data,
        raw_match_data_after: rowCountsAfter.raw_match_data,
        protected_tables_unchanged:
            rowCountsAfter.matches === EXPECTED_ROW_COUNTS_BEFORE.matches &&
            rowCountsAfter.bookmaker_odds_history === EXPECTED_ROW_COUNTS_BEFORE.bookmaker_odds_history &&
            rowCountsAfter.l3_features === EXPECTED_ROW_COUNTS_BEFORE.l3_features &&
            rowCountsAfter.match_features_training === EXPECTED_ROW_COUNTS_BEFORE.match_features_training &&
            rowCountsAfter.predictions === EXPECTED_ROW_COUNTS_BEFORE.predictions,
        inserted_rows_count: postWriteRows.length,
        duplicate_match_id_data_version_count: (duplicateRows || []).length,
        data_hash_matches_baseline_count: (postWriteRows || []).filter(row => {
            const target = candidates.find(candidate => candidate.match_id === normalizeText(row.match_id));
            return target && normalizeText(row.data_hash).toLowerCase() === target.baseline_hash;
        }).length,
        raw_data_shape_valid_count: (postWriteRows || []).filter(
            row => row.has_meta === true && row.has_match_id === true && row.has_pageprops === true
        ).length,
    };
}

function buildBasePayload({ input = {}, manifestGate = null, rowCountsBefore = null, schemaReadiness = null } = {}) {
    return {
        phase: PHASE,
        source: SOURCE,
        route: ROUTE,
        raw_version: RAW_VERSION,
        hash_strategy: HASH_STRATEGY,
        batch_id: BATCH_ID,
        authorization: {
            final_db_write_confirmation: input.finalDbWriteConfirmation === true,
            allow_db_write: input.allowDbWrite === true,
            allow_raw_match_data_write: input.allowRawMatchDataWrite === true,
            allow_controlled_write: input.allowControlledWrite === true,
            allow_matches_write: input.allowMatchesWrite === true,
            allow_bookmaker_odds_write: input.allowBookmakerOddsWrite === true,
            allow_feature_write: input.allowFeatureWrite === true,
            allow_schema_migration: input.allowSchemaMigration === true,
            allow_browser_runtime: input.allowBrowserRuntime === true,
            allow_proxy_runtime: input.allowProxyRuntime === true,
            concurrency: input.concurrency,
            retry: input.retry,
            print_full_body: input.printFullBody === true,
            save_full_body: input.saveFullBody === true,
            print_full_json: input.printFullJson === true,
            save_full_json: input.saveFullJson === true,
            print_full_pageprops: input.printFullPageprops === true,
            save_full_pageprops: input.saveFullPageprops === true,
        },
        manifest_gate: manifestGate
            ? {
                  ok: manifestGate.ok,
                  candidate_targets: manifestGate.candidates.length,
                  hash_baseline_ready_count: manifestGate.candidates.filter(
                      target => target.preflight_status === 'hash_baseline_ready'
                  ).length,
                  baseline_hash_valid_count: manifestGate.candidates.filter(target =>
                      /^[a-f0-9]{64}$/.test(target.baseline_hash)
                  ).length,
                  write_plan_status: 'ready_for_final_authorization',
                  errors: manifestGate.errors,
              }
            : null,
        schema_gate: schemaReadiness || null,
        row_counts_before: rowCountsBefore,
        no_full_body_json_pageprops_print_save: true,
        browser_used: false,
        proxy_used: false,
        retry_count: 0,
        parser_features_training_executed: false,
        matches_write_executed: false,
        bookmaker_odds_write_executed: false,
        feature_write_executed: false,
        training_executed: false,
        prediction_executed: false,
    };
}

function buildFailurePayload({
    input = {},
    reason,
    manifestGate = null,
    rowCountsBefore = null,
    schemaReadiness = null,
    matchesGate = null,
    existingRawGate = null,
    recaptureGate = null,
    transaction = {},
    rowCountsAfter = null,
    insertedCount = 0,
} = {}) {
    return {
        ...buildBasePayload({ input, manifestGate, rowCountsBefore, schemaReadiness }),
        ok: false,
        controlled_failure: true,
        failure_reason: reason,
        blocked_reason: reason,
        fk_gate: matchesGate,
        existing_raw_gate: existingRawGate,
        recapture_hash_gate: recaptureGate
            ? {
                  attempted_target_count: recaptureGate.attempted_target_count,
                  recapture_success_count: recaptureGate.recapture_success_count,
                  hash_match_count: recaptureGate.hash_match_count,
                  hash_drift_count: recaptureGate.hash_drift_count,
                  failed_count: recaptureGate.failed_count,
                  blocked_count: recaptureGate.blocked_count,
                  route_identity_blocked_count: recaptureGate.route_identity_blocked_count,
                  unresolved_schedule_detail_mapping_count: recaptureGate.unresolved_schedule_detail_mapping_count,
                  reverse_fixture_detected_count: recaptureGate.reverse_fixture_detected_count,
                  unresolved_large_gap_count: recaptureGate.unresolved_large_gap_count,
                  cross_season_slug_reuse_count: recaptureGate.cross_season_slug_reuse_count,
                  unknown_date_status_count: recaptureGate.unknown_date_status_count,
                  request_count: recaptureGate.request_count,
                  targets: recaptureGate.public_targets,
              }
            : null,
        transaction: {
            began: transaction.began === true,
            committed: transaction.committed === true,
            rolled_back: transaction.rolled_back === true,
        },
        inserted_count: insertedCount,
        updated_count: 0,
        skipped_count: 0,
        row_counts_after: rowCountsAfter,
        raw_match_data_write_executed: false,
        network_executed: Boolean(recaptureGate),
    };
}

function buildSuccessPayload({
    input = {},
    manifestGate,
    rowCountsBefore,
    schemaReadiness,
    matchesGate,
    existingRawGate,
    recaptureGate,
    insertedRows,
    rowCountsAfter,
    postWriteVerification,
    transaction,
} = {}) {
    return {
        ...buildBasePayload({ input, manifestGate, rowCountsBefore, schemaReadiness }),
        ok: true,
        controlled_failure: false,
        fk_gate: matchesGate,
        existing_raw_gate: existingRawGate,
        recapture_hash_gate: {
            attempted_target_count: recaptureGate.attempted_target_count,
            recapture_success_count: recaptureGate.recapture_success_count,
            hash_match_count: recaptureGate.hash_match_count,
            hash_drift_count: recaptureGate.hash_drift_count,
            failed_count: recaptureGate.failed_count,
            blocked_count: recaptureGate.blocked_count,
            route_identity_blocked_count: recaptureGate.route_identity_blocked_count,
            unresolved_schedule_detail_mapping_count: recaptureGate.unresolved_schedule_detail_mapping_count,
            reverse_fixture_detected_count: recaptureGate.reverse_fixture_detected_count,
            unresolved_large_gap_count: recaptureGate.unresolved_large_gap_count,
            cross_season_slug_reuse_count: recaptureGate.cross_season_slug_reuse_count,
            unknown_date_status_count: recaptureGate.unknown_date_status_count,
            request_count: recaptureGate.request_count,
            first_target: recaptureGate.public_targets[0] || null,
            last_target: recaptureGate.public_targets[recaptureGate.public_targets.length - 1] || null,
        },
        transaction: {
            began: transaction.began === true,
            committed: transaction.committed === true,
            rolled_back: transaction.rolled_back === true,
        },
        inserted_count: insertedRows.length,
        updated_count: 0,
        skipped_count: 0,
        row_counts_after: rowCountsAfter,
        post_write_verification: postWriteVerification,
        raw_match_data_write_executed: true,
        network_executed: true,
    };
}

function updateManifestWithExecution(manifest = {}, payload = {}, generatedAt = new Date().toISOString()) {
    const next = jsonClone(manifest);
    const status = payload.ok
        ? 'inserted'
        : payload.blocked_reason === 'blocked_missing_matches_fk_prerequisite'
          ? 'blocked_missing_matches_fk_prerequisite'
          : 'blocked_before_write';
    next.write_execution_status = payload.ok ? 'completed' : status;
    next.raw_match_data_write_status = payload.ok ? 'completed' : 'not_executed';
    next.write_execution_at = generatedAt;
    next.inserted_count = payload.inserted_count || 0;
    next.blocked_count = payload.ok ? 0 : TARGET_COUNT;
    next.required_next_step = payload.ok
        ? 'post_write_canonical_read_completeness_audit_for_50_pageprops_v2_rows'
        : payload.blocked_reason === 'blocked_missing_matches_fk_prerequisite'
          ? 'controlled_matches_identity_seed_prerequisite_planning'
          : 'controlled_pageprops_v2_write_execution_blocked_review';
    next.single_league_pageprops_v2_write_execution_result = {
        phase: PHASE,
        generated_at: generatedAt,
        ok: payload.ok === true,
        blocked_reason: payload.blocked_reason || null,
        inserted_count: payload.inserted_count || 0,
        raw_match_data_write_executed: payload.raw_match_data_write_executed === true,
        network_executed: payload.network_executed === true,
        raw_match_data_before: payload.row_counts_before?.raw_match_data ?? null,
        raw_match_data_after: payload.row_counts_after?.raw_match_data ?? null,
        missing_matches_count: payload.fk_gate?.missing_matches_count ?? null,
        existing_v2_count: payload.existing_raw_gate?.existing_v2_count ?? null,
    };
    next.candidate_targets = (next.candidate_targets || []).map(target => {
        const matchId = normalizeText(target.match_id);
        const resultTarget = payload.recapture_hash_gate?.targets?.find(
            item => normalizeText(item.match_id) === matchId
        );
        return {
            ...target,
            updated_at: generatedAt,
            write_status: status,
            write_execution_status: status,
            write_executed_at: payload.ok ? generatedAt : null,
            failure_reason: payload.ok
                ? null
                : payload.blocked_reason || payload.failure_reason || 'controlled_write_blocked',
            required_next_step: next.required_next_step,
            recaptured_hash: resultTarget?.recaptured_hash || null,
            hash_matches_baseline: resultTarget?.hash_matches_baseline ?? null,
        };
    });
    return next;
}

function formatRowCounts(rowCounts = {}) {
    return [
        `- matches=${Number(rowCounts.matches || 0)}`,
        `- raw_match_data=${Number(rowCounts.raw_match_data || 0)}`,
        `- bookmaker_odds_history=${Number(rowCounts.bookmaker_odds_history || 0)}`,
        `- l3_features=${Number(rowCounts.l3_features || 0)}`,
        `- match_features_training=${Number(rowCounts.match_features_training || 0)}`,
        `- predictions=${Number(rowCounts.predictions || 0)}`,
    ].join('\n');
}

function buildReport(payload = {}) {
    const blockedMissingMatches = payload.blocked_reason === 'blocked_missing_matches_fk_prerequisite';
    const lines = [
        '# Single-League pageProps v2 Controlled Write Execution - Phase 5.21L2V',
        '',
        '## 1. Executive summary',
        '',
        '- L2V is real controlled write execution.',
        '- Only `raw_match_data` write is allowed, and only after all gates pass.',
        '- Parser/features/training/prediction remain out of scope.',
        `- execution_status: \`${payload.ok ? 'completed' : payload.blocked_reason || 'blocked'}\``,
        '',
        '## 2. Current DB baseline',
        '',
        formatRowCounts(payload.row_counts_before || EXPECTED_ROW_COUNTS_BEFORE),
        '',
        '## 3. Authorization / guardrails',
        '',
        '- FINAL_DB_WRITE_CONFIRMATION=yes',
        '- ALLOW_DB_WRITE=yes',
        '- ALLOW_RAW_MATCH_DATA_WRITE=yes',
        '- ALLOW_CONTROLLED_WRITE=yes',
        '- ALLOW_MATCHES_WRITE=no',
        '- ALLOW_BOOKMAKER_ODDS_WRITE=no',
        '- ALLOW_FEATURE_WRITE=no',
        '- no parser/features/training',
        '- no browser/proxy',
        '- concurrency=1',
        '- retry=0',
        '- no full body/json/pageProps print/save',
        '',
        '## 4. Manifest gate result',
        '',
        `- candidate_targets=${payload.manifest_gate?.candidate_targets || 0}`,
        `- hash_baseline_ready count=${payload.manifest_gate?.hash_baseline_ready_count || 0}`,
        `- baseline_hash valid count=${payload.manifest_gate?.baseline_hash_valid_count || 0}`,
        `- write_plan_status=${payload.manifest_gate?.write_plan_status || null}`,
        `- blocked count=${payload.manifest_gate?.errors?.length || 0}`,
        '',
        '## 5. Schema / FK gate result',
        '',
        `- UNIQUE(match_id,data_version) present=${payload.schema_gate?.unique_match_id_data_version_present === true}`,
        `- old UNIQUE(match_id) absent=${payload.schema_gate?.old_unique_match_id_absent === true}`,
        `- matches existence count=${payload.fk_gate?.existing_matches_count ?? 0}`,
        `- missing_matches_count=${payload.fk_gate?.missing_matches_count ?? 0}`,
    ];
    if (blockedMissingMatches) {
        lines.push('- blocked_reason=blocked_missing_matches_fk_prerequisite');
        lines.push('- no network executed');
        lines.push('- no DB write executed');
    }
    lines.push(
        '',
        '## 6. Existing raw gate result',
        '',
        `- existing_v2_count=${payload.existing_raw_gate?.existing_v2_count ?? 0}`,
        `- conflict count=${payload.existing_raw_gate?.conflicts?.length ?? 0}`,
        '',
        '## 7. Live recapture hash gate result',
        '',
        `- attempted_target_count=${payload.recapture_hash_gate?.attempted_target_count || 0}`,
        `- recapture_success_count=${payload.recapture_hash_gate?.recapture_success_count || 0}`,
        `- hash_match_count=${payload.recapture_hash_gate?.hash_match_count || 0}`,
        `- hash_drift_count=${payload.recapture_hash_gate?.hash_drift_count || 0}`,
        `- failed_count=${payload.recapture_hash_gate?.failed_count || 0}`,
        `- blocked_count=${payload.recapture_hash_gate?.blocked_count || 0}`,
        `- request_count=${payload.recapture_hash_gate?.request_count || 0}`,
        '- no full pageProps saved/printed',
        '',
        '## 8. Transaction result',
        '',
        `- transaction_began=${payload.transaction?.began === true}`,
        `- inserted_count=${payload.inserted_count || 0}`,
        `- committed=${payload.transaction?.committed === true}`,
        `- rolled_back=${payload.transaction?.rolled_back === true}`,
        `- raw_match_data_write_executed=${payload.raw_match_data_write_executed === true}`,
        '- matches_write_executed=false',
        '- odds_write_executed=false',
        '- features_write_executed=false',
        '- training/prediction=false',
        '',
        '## 9. Post-write verification',
        '',
        payload.post_write_verification
            ? [
                  `- raw_match_data ${payload.post_write_verification.raw_match_data_before} -> ${payload.post_write_verification.raw_match_data_after}`,
                  `- protected_tables_unchanged=${payload.post_write_verification.protected_tables_unchanged === true}`,
                  `- inserted rows count=${payload.post_write_verification.inserted_rows_count}`,
                  `- duplicate match_id/data_version=${payload.post_write_verification.duplicate_match_id_data_version_count}`,
                  `- data_hash matches baseline=${payload.post_write_verification.data_hash_matches_baseline_count}`,
                  `- raw_data shape valid=${payload.post_write_verification.raw_data_shape_valid_count}`,
              ].join('\n')
            : '- not executed',
        '',
        '## 10. Manifest update result',
        '',
        `- write_status distribution=${payload.ok ? '{"inserted":50}' : `{"${payload.blocked_reason || 'blocked_before_write'}":50}`}`,
        `- inserted_count=${payload.inserted_count || 0}`,
        `- blocked_count=${payload.ok ? 0 : TARGET_COUNT}`,
        `- required_next_step=${
            payload.ok
                ? 'post_write_canonical_read_completeness_audit_for_50_pageprops_v2_rows'
                : blockedMissingMatches
                  ? 'controlled_matches_identity_seed_prerequisite_planning'
                  : 'controlled_pageprops_v2_write_execution_blocked_review'
        }`,
        '',
        '## 11. Verification results',
        '',
        '- new execution tests: pending at report generation time',
        '- planning tests: pending at report generation time',
        '- preflight tests: pending at report generation time',
        '- FotMobRawDetailFetcher tests: pending at report generation time',
        '- source inventory tests: pending at report generation time',
        '- npm test: pending at report generation time',
        '- npm run test:coverage: pending at report generation time',
        '- eslint / prettier / git diff: pending at report generation time',
        '- DB row counts final: pending final safety check',
        '- l1-config residue absent: pending final safety check',
        '- docs/_staging_preview absent: pending final safety check',
        '- PR CI: pending',
        '- main push CI: pending',
        '',
        '## 12. Recommended next phase',
        '',
        payload.ok
            ? '- Phase 5.21L2W: post-write canonical read / completeness audit for 50 inserted pageProps v2 rows. No DB write, no network, use RawMatchDataVersionSelector, no parser/features/training.'
            : blockedMissingMatches
              ? '- Phase 5.21L2V0: controlled matches identity seed prerequisite planning. No raw write until matches rows exist; define controlled matches identity insert from manifest; no parser/features/training.'
              : '- Phase 5.21L2V1: controlled write block review / retry policy planning.',
        '',
        '## 13. Explicit non-execution',
        '',
        '- no matches writes',
        '- no bookmaker_odds_history writes',
        '- no features/training/prediction writes',
        '- no parser implementation',
        '- no feature extraction',
        '- no browser/proxy/captcha bypass',
        '- no retry',
        '- no full raw_data/pageProps/source body print/save',
        '- no invented external_id / fake target data',
        '- no file deletion',
        ''
    );
    return `${lines.join('\n')}\n`;
}

async function queryReadOnly(client, sql, params = []) {
    const normalized = normalizeText(sql).replace(/\s+/g, ' ').toLowerCase();
    if (!normalized.startsWith('select ')) {
        throw new Error('NON_SELECT_SQL_BLOCKED');
    }
    if (/\b(insert|update|delete|truncate|alter|drop|create|grant|revoke|copy|for update|lock)\b/i.test(normalized)) {
        throw new Error('SQL_WRITE_OR_LOCK_BLOCKED');
    }
    return client.query(sql, params);
}

async function queryControlledWrite(client, sql, params = []) {
    const normalized = normalizeText(sql).replace(/\s+/g, ' ').toLowerCase();
    const isTransaction = ['begin', 'commit', 'rollback'].includes(normalized);
    const isAllowedInsert =
        normalized.startsWith('insert into raw_match_data ') &&
        !/\b(update|delete|truncate|alter|drop|create|grant|revoke|copy|lock)\b/i.test(normalized);
    if (!isTransaction && !isAllowedInsert) {
        throw new Error('CONTROLLED_WRITE_SQL_BLOCKED');
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

async function loadRawMatchDataConstraints(client) {
    const result = await queryReadOnly(
        client,
        `
        SELECT
          conname,
          contype,
          pg_get_constraintdef(c.oid) AS definition
        FROM pg_constraint c
        JOIN pg_class t ON c.conrelid = t.oid
        WHERE t.relname = 'raw_match_data'
        ORDER BY conname
        `,
        []
    );
    return result.rows || [];
}

async function loadCandidateMatches(client, matchIds = []) {
    const result = await queryReadOnly(
        client,
        `
        SELECT match_id, external_id, home_team, away_team, match_date, status
        FROM matches
        WHERE match_id = ANY($1::text[])
        ORDER BY match_id
        `,
        [matchIds]
    );
    return result.rows || [];
}

async function loadExistingCandidateV2Rows(client, matchIds = []) {
    const result = await queryReadOnly(
        client,
        `
        SELECT id, match_id, external_id, data_version, data_hash, collected_at
        FROM raw_match_data
        WHERE match_id = ANY($1::text[])
          AND data_version = $2
        ORDER BY match_id, id
        `,
        [matchIds, RAW_VERSION]
    );
    return result.rows || [];
}

async function loadPostWriteCandidateRows(client, matchIds = []) {
    const result = await queryReadOnly(
        client,
        `
        SELECT
          id,
          match_id,
          external_id,
          data_version,
          data_hash,
          collected_at,
          raw_data ? '_meta' AS has_meta,
          raw_data ? 'matchId' AS has_match_id,
          raw_data ? 'pageProps' AS has_pageprops,
          raw_data #>> '{_meta,hash_strategy}' AS meta_hash_strategy
        FROM raw_match_data
        WHERE match_id = ANY($1::text[])
          AND data_version = $2
        ORDER BY match_id, id
        `,
        [matchIds, RAW_VERSION]
    );
    return result.rows || [];
}

async function loadDuplicateCandidateVersionRows(client, matchIds = []) {
    const result = await queryReadOnly(
        client,
        `
        SELECT match_id, data_version, COUNT(*)::int AS duplicate_count
        FROM raw_match_data
        WHERE match_id = ANY($1::text[])
          AND data_version = $2
        GROUP BY match_id, data_version
        HAVING COUNT(*) > 1
        ORDER BY match_id
        `,
        [matchIds, RAW_VERSION]
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

function nowUtcIso(dependencies = {}) {
    if (typeof dependencies.now === 'function') {
        return dependencies.now();
    }
    if (dependencies.now) {
        return dependencies.now;
    }
    return new Date().toISOString();
}

async function loadGateData({ client, candidates, dependencies }) {
    const matchIds = candidates.map(target => target.match_id);
    const rowCountsBefore = normalizeRowCounts(
        dependencies.protectedTableRowsBefore || (await loadProtectedTableBaselineRows(client))
    );
    const constraintRows = dependencies.constraintRows || (await loadRawMatchDataConstraints(client));
    const matchRows = dependencies.matchRows || (await loadCandidateMatches(client, matchIds));
    const existingV2Rows = dependencies.existingV2Rows || (await loadExistingCandidateV2Rows(client, matchIds));
    return { rowCountsBefore, constraintRows, matchRows, existingV2Rows };
}

async function executeTransaction({ client, candidates, recaptureGate, rowCountsBefore, dependencies, generatedAt }) {
    const transaction = { began: false, committed: false, rolled_back: false };
    const collectedAt = dependencies.collectedAt || generatedAt;
    const insertSql = buildInsertRawMatchDataSql(recaptureGate.targets, collectedAt);
    try {
        assertDbWriteAllowed({
            script: 'single_league_pageprops_v2_controlled_write_execute.js',
            tables: ['raw_match_data'],
            operations: ['INSERT']
        });

        await queryControlledWrite(client, 'BEGIN');
        transaction.began = true;
        const insertResult = await queryControlledWrite(client, insertSql.text, insertSql.values);
        const insertedRows = insertResult.rows || [];
        if (insertedRows.length !== TARGET_COUNT) {
            await queryControlledWrite(client, 'ROLLBACK');
            transaction.rolled_back = true;
            return {
                ok: false,
                reason: `INSERTED_COUNT_MISMATCH:${insertedRows.length}`,
                insertedRows,
                transaction,
                rowCountsAfter: normalizeRowCounts(await loadProtectedTableBaselineRows(client)),
            };
        }
        const rowCountsInsideTransaction = normalizeRowCounts(
            dependencies.protectedTableRowsInsideTransaction || (await loadProtectedTableBaselineRows(client))
        );
        const insideErrors = validateExactRowCounts(rowCountsInsideTransaction, EXPECTED_ROW_COUNTS_AFTER_SUCCESS);
        if (insideErrors.length > 0) {
            await queryControlledWrite(client, 'ROLLBACK');
            transaction.rolled_back = true;
            return {
                ok: false,
                reason: `PROTECTED_TABLE_COUNT_CHANGED:${insideErrors.join(';')}`,
                insertedRows,
                transaction,
                rowCountsAfter: rowCountsInsideTransaction,
            };
        }
        await queryControlledWrite(client, 'COMMIT');
        transaction.committed = true;
        const rowCountsAfter = normalizeRowCounts(
            dependencies.protectedTableRowsAfter || (await loadProtectedTableBaselineRows(client))
        );
        const postWriteRows =
            dependencies.postWriteRows ||
            (await loadPostWriteCandidateRows(
                client,
                candidates.map(target => target.match_id)
            ));
        const duplicateRows =
            dependencies.duplicateRows ||
            (await loadDuplicateCandidateVersionRows(
                client,
                candidates.map(target => target.match_id)
            ));
        const postWriteVerification = buildPostWriteVerification({
            candidates,
            rowCountsBefore,
            rowCountsAfter,
            postWriteRows,
            duplicateRows,
        });
        return {
            ok: postWriteVerification.ok,
            reason: postWriteVerification.ok
                ? null
                : `POST_WRITE_VERIFICATION_FAILED:${postWriteVerification.errors.join(';')}`,
            insertedRows,
            transaction,
            rowCountsAfter,
            postWriteVerification,
        };
    } catch (error) {
        if (transaction.began && !transaction.committed && !transaction.rolled_back) {
            try {
                await queryControlledWrite(client, 'ROLLBACK');
                transaction.rolled_back = true;
            } catch {
                transaction.rollback_failed = true;
            }
        }
        return {
            ok: false,
            reason: error.message,
            insertedRows: [],
            transaction,
            rowCountsAfter: null,
            postWriteVerification: null,
        };
    }
}

async function runCli(argv = process.argv.slice(2), dependencies = {}) {
    const parsed = Array.isArray(argv) ? parseArgs(argv) : argv;
    const validation = validateExecutionInput(parsed);
    const output = dependencies.output || (payload => process.stdout.write(`${JSON.stringify(payload, null, 2)}\n`));
    if (!validation.ok) {
        const payload = buildFailurePayload({
            input: normalizeExecutionInput(parsed),
            reason: `INPUT_INVALID:${validation.errors.join(';')}`,
        });
        output(payload);
        return { status: 1, payload };
    }

    const input = validation.value;
    const generatedAt = dependencies.generatedAt || nowUtcIso(dependencies);
    const pool =
        dependencies.client ||
        dependencies.manifest ||
        dependencies.constraintRows ||
        dependencies.matchRows ||
        dependencies.existingV2Rows ||
        dependencies.protectedTableRowsBefore
            ? null
            : createDefaultPool();
    const client = dependencies.client || pool;
    try {
        const manifest = dependencies.manifest || readManifestFile(input.manifest);
        const manifestGate = validateManifestGate(manifest);
        if (!manifestGate.ok) {
            const payload = buildFailurePayload({
                input,
                reason: `MANIFEST_GATE_BLOCKED:${manifestGate.errors.join(';')}`,
                manifestGate,
            });
            if (dependencies.writeReport !== false) {
                (dependencies.writeReportFile || writeReportFile)(REPORT_PATH, buildReport(payload));
            }
            output(payload);
            return { status: 1, payload };
        }
        const candidates = manifestGate.candidates;
        const { rowCountsBefore, constraintRows, matchRows, existingV2Rows } = await loadGateData({
            client,
            candidates,
            dependencies,
        });
        const baselineErrors = validateExactRowCounts(rowCountsBefore, EXPECTED_ROW_COUNTS_BEFORE);
        const schemaReadiness = buildSchemaReadiness(constraintRows);
        const matchesGate = buildMatchesExistenceGate(candidates, matchRows);
        const existingRawGate = buildExistingRawGate(candidates, existingV2Rows);

        if (baselineErrors.length > 0 || !schemaReadiness.ok) {
            const reason =
                baselineErrors.length > 0
                    ? `DB_BASELINE_BLOCKED:${baselineErrors.join(';')}`
                    : `SCHEMA_GATE_BLOCKED:${schemaReadiness.errors.join(';')}`;
            const payload = buildFailurePayload({
                input,
                reason,
                manifestGate,
                rowCountsBefore,
                schemaReadiness,
                matchesGate,
                existingRawGate,
            });
            writeExecutionArtifacts({ manifest, payload, input, generatedAt, dependencies });
            output(payload);
            return { status: 1, payload };
        }
        if (!matchesGate.ok) {
            const payload = buildFailurePayload({
                input,
                reason: 'blocked_missing_matches_fk_prerequisite',
                manifestGate,
                rowCountsBefore,
                schemaReadiness,
                matchesGate,
                existingRawGate,
            });
            writeExecutionArtifacts({ manifest, payload, input, generatedAt, dependencies });
            output(payload);
            return { status: 1, payload };
        }
        if (!existingRawGate.ok) {
            const payload = buildFailurePayload({
                input,
                reason: 'blocked_existing_fotmob_pageprops_v2_rows',
                manifestGate,
                rowCountsBefore,
                schemaReadiness,
                matchesGate,
                existingRawGate,
            });
            writeExecutionArtifacts({ manifest, payload, input, generatedAt, dependencies });
            output(payload);
            return { status: 1, payload };
        }

        const recaptureGate = await recaptureTargets(candidates, dependencies);
        if (
            recaptureGate.recapture_success_count !== TARGET_COUNT ||
            recaptureGate.hash_match_count !== TARGET_COUNT ||
            recaptureGate.failed_count > 0 ||
            recaptureGate.blocked_count > 0
        ) {
            const payload = buildFailurePayload({
                input,
                reason: 'recapture_hash_gate_blocked',
                manifestGate,
                rowCountsBefore,
                schemaReadiness,
                matchesGate,
                existingRawGate,
                recaptureGate,
            });
            writeExecutionArtifacts({ manifest, payload, input, generatedAt, dependencies });
            output(payload);
            return { status: 1, payload };
        }

        const transactionResult = await executeTransaction({
            client,
            candidates,
            recaptureGate,
            rowCountsBefore,
            dependencies,
            generatedAt,
        });
        if (!transactionResult.ok) {
            const payload = buildFailurePayload({
                input,
                reason: transactionResult.reason,
                manifestGate,
                rowCountsBefore,
                schemaReadiness,
                matchesGate,
                existingRawGate,
                recaptureGate,
                transaction: transactionResult.transaction,
                rowCountsAfter: transactionResult.rowCountsAfter,
                insertedCount: transactionResult.insertedRows.length,
            });
            writeExecutionArtifacts({ manifest, payload, input, generatedAt, dependencies });
            output(payload);
            return { status: 1, payload };
        }

        const payload = buildSuccessPayload({
            input,
            manifestGate,
            rowCountsBefore,
            schemaReadiness,
            matchesGate,
            existingRawGate,
            recaptureGate,
            insertedRows: transactionResult.insertedRows,
            rowCountsAfter: transactionResult.rowCountsAfter,
            postWriteVerification: transactionResult.postWriteVerification,
            transaction: transactionResult.transaction,
        });
        writeExecutionArtifacts({ manifest, payload, input, generatedAt, dependencies });
        output(payload);
        return { status: 0, payload };
    } catch (error) {
        const payload = buildFailurePayload({ input, reason: error.message });
        output(payload);
        return { status: 1, payload };
    } finally {
        if (pool && typeof pool.end === 'function') {
            await pool.end();
        }
    }
}

function writeExecutionArtifacts({ manifest, payload, input, generatedAt, dependencies } = {}) {
    const updatedManifest = updateManifestWithExecution(manifest, payload, generatedAt);
    if (dependencies.writeManifest !== false) {
        (dependencies.writeManifestFile || writeJsonFile)(input.manifest, updatedManifest);
    }
    if (dependencies.writeReport !== false) {
        (dependencies.writeReportFile || writeReportFile)(REPORT_PATH, buildReport(payload));
    }
    payload.manifest_updated = dependencies.writeManifest !== false;
    payload.report_updated = dependencies.writeReport !== false;
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
    RAW_VERSION,
    HASH_STRATEGY,
    TARGET_COUNT,
    parseArgs,
    normalizeBooleanFlag,
    validateExecutionInput,
    validateManifestGate,
    validateCandidateTargets,
    buildProtectedTableBaseline,
    buildSchemaReadiness,
    buildMatchesExistenceGate,
    buildExistingRawGate,
    buildRawDataForTarget,
    validateRawDataShape,
    recaptureTarget,
    recaptureTargets,
    buildInsertRawMatchDataSql,
    buildPostWriteVerification,
    updateManifestWithExecution,
    buildReport,
    queryReadOnly,
    queryControlledWrite,
    loadProtectedTableBaselineRows,
    loadRawMatchDataConstraints,
    loadCandidateMatches,
    loadExistingCandidateV2Rows,
    loadPostWriteCandidateRows,
    loadDuplicateCandidateVersionRows,
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
