#!/usr/bin/env node
/* eslint-disable complexity, max-lines, max-statements */
'use strict';

const fs = require('node:fs');
const path = require('node:path');

const base = require('./single_league_pageprops_v2_controlled_write_execute');

const PHASE = 'PHASE5_21L2V3_RENEWED_CONTROLLED_PAGEPROPS_V2_RAW_WRITE_EXECUTION';
const MANIFEST_PATH = base.MANIFEST_PATH;
const REPORT_PATH = 'docs/_reports/DATA_ENTRYPOINT_GOVERNANCE_PHASE5_21_L2V3.md';
const SOURCE = base.SOURCE;
const LEAGUE_ID = base.LEAGUE_ID;
const LEAGUE_NAME = base.LEAGUE_NAME;
const SEASON = base.SEASON;
const ROUTE = base.ROUTE;
const RAW_VERSION = base.RAW_VERSION;
const HASH_STRATEGY = base.HASH_STRATEGY;
const BATCH_ID = base.BATCH_ID;
const TARGET_COUNT = base.TARGET_COUNT;
const KNOWN_COMPLETED_COUNT = 8;
const DEFAULT_REQUEST_DELAY_MS = 750;
const EXPECTED_ROW_COUNTS_BEFORE = Object.freeze({
    matches: 60,
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
    'renewedRawWriteAuthorization',
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
        renewedRawWriteAuthorization: null,
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
        requestDelayMs: null,
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
        startHead: null,
        branch: null,
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

function pushRequiredYes(errors, value, name) {
    if (value === true) return;
    errors.push(value === false ? `${name}=yes is required in Phase 5.21L2V3` : `missing ${name}=yes`);
}

function pushRequiredNo(errors, value, name) {
    if (value === false) return;
    errors.push(value === true ? `${name}=yes is blocked in Phase 5.21L2V3` : `missing ${name}=no`);
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
        renewedRawWriteAuthorization: normalizeBooleanFlag(input.renewedRawWriteAuthorization, undefined),
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
        requestDelayMs: parseInteger(input.requestDelayMs, DEFAULT_REQUEST_DELAY_MS),
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
        startHead: normalizeText(input.startHead),
        branch: normalizeText(input.branch),
        unknown: Array.isArray(input.unknown) ? input.unknown : [],
    };
}

function validateExecutionInput(input = {}) {
    const value = normalizeExecutionInput(input);
    const errors = [];
    if (value.unknown.length > 0) errors.push(`unknown arguments: ${value.unknown.join(', ')}`);
    requireExact(errors, value.manifest, MANIFEST_PATH, 'manifest');
    requireExact(errors, value.source, SOURCE, 'source');
    if (value.leagueId !== LEAGUE_ID) errors.push('league-id must be 53');
    requireExact(errors, value.leagueName, LEAGUE_NAME, 'league-name');
    requireExact(errors, value.season, SEASON, 'season');
    requireExact(errors, value.route, ROUTE, 'route');
    requireExact(errors, value.rawVersion, RAW_VERSION, 'raw-version');
    requireExact(errors, value.hashStrategy, HASH_STRATEGY, 'hash-strategy');
    requireExact(errors, value.batchId, BATCH_ID, 'batch-id');
    if (value.targetCount !== TARGET_COUNT) errors.push('target-count must be 50');
    for (const key of REQUIRED_YES_FLAGS) pushRequiredYes(errors, value[key], flagName(key));
    for (const key of REQUIRED_NO_FLAGS) pushRequiredNo(errors, value[key], flagName(key));
    if (value.concurrency !== 1) errors.push('concurrency must be 1');
    if (value.retry !== 0) errors.push('retry must be 0');
    if (!Number.isInteger(value.requestDelayMs) || value.requestDelayMs < 0) {
        errors.push('request-delay-ms must be a non-negative integer');
    }
    for (const key of BLOCKED_TRUE_FLAGS) {
        if (value[key] === true) errors.push(`${flagName(key)}=yes is blocked in Phase 5.21L2V3`);
    }
    return { ok: errors.length === 0, errors, value };
}

function jsonClone(value) {
    if (value === undefined) return undefined;
    return JSON.parse(JSON.stringify(value));
}

function findDuplicates(values = []) {
    const seen = new Set();
    const duplicates = new Set();
    for (const value of values.map(normalizeText).filter(Boolean)) {
        if (seen.has(value)) duplicates.add(value);
        seen.add(value);
    }
    return duplicates;
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
        home_team: normalizeText(target.home_team),
        away_team: normalizeText(target.away_team),
        match_date: normalizeText(target.match_date),
        kickoff_time: normalizeText(target.kickoff_time),
        status: normalizeText(target.status).toLowerCase(),
        preflight_status: normalizeText(target.preflight_status),
        baseline_hash: normalizeText(target.baseline_hash).toLowerCase(),
        write_plan_status: normalizeText(target.write_plan_status),
        write_status: normalizeText(target.write_status),
        write_execution_status: normalizeText(target.write_execution_status),
        matches_seed_status: normalizeText(target.matches_seed_status),
        failure_reason: target.failure_reason === undefined ? null : normalizeText(target.failure_reason),
    };
}

function hasFakeMarker(target = {}) {
    return /fake|invented|placeholder/i.test(
        [
            target.target_id,
            target.match_id,
            target.external_id,
            target.home_team,
            target.away_team,
            target.failure_reason,
        ].join(' ')
    );
}

function validateCandidateTargets(manifest = {}) {
    const candidates = Array.isArray(manifest.candidate_targets)
        ? manifest.candidate_targets.map(normalizeCandidateTarget)
        : [];
    const errors = [];
    if (candidates.length !== TARGET_COUNT) errors.push(`candidate_targets must contain ${TARGET_COUNT} targets`);
    const duplicateExternalIds = findDuplicates(candidates.map(target => target.external_id));
    const duplicateMatchIds = findDuplicates(candidates.map(target => target.match_id));
    for (const target of candidates) {
        const targetErrors = [];
        if (!/^\d+$/.test(target.external_id)) targetErrors.push('external_id must be numeric');
        const expectedMatchId = `${LEAGUE_ID}_20252026_${target.external_id}`;
        if (target.match_id !== expectedMatchId) targetErrors.push(`match_id must be ${expectedMatchId}`);
        if (duplicateExternalIds.has(target.external_id)) targetErrors.push('duplicate external_id');
        if (duplicateMatchIds.has(target.match_id)) targetErrors.push('duplicate match_id');
        if (target.batch_id !== BATCH_ID) targetErrors.push('batch_id mismatch');
        if (target.source !== SOURCE) targetErrors.push('source mismatch');
        if (target.route !== ROUTE) targetErrors.push('route mismatch');
        if (target.raw_data_version !== RAW_VERSION) targetErrors.push('raw_data_version mismatch');
        if (target.hash_strategy !== HASH_STRATEGY) targetErrors.push('hash_strategy mismatch');
        if (target.league_id !== LEAGUE_ID) targetErrors.push('league_id mismatch');
        if (target.league_name !== LEAGUE_NAME) targetErrors.push('league_name mismatch');
        if (target.season !== SEASON) targetErrors.push('season mismatch');
        if (!target.home_team) targetErrors.push('home_team missing');
        if (!target.away_team) targetErrors.push('away_team missing');
        if (!target.match_date && !target.kickoff_time) targetErrors.push('match_date/kickoff_time missing');
        if (!target.status) targetErrors.push('status missing');
        if (target.status && target.status !== target.status.toLowerCase()) {
            targetErrors.push('status must be lowercase');
        }
        if (target.preflight_status !== 'hash_baseline_ready') {
            targetErrors.push('preflight_status must be hash_baseline_ready');
        }
        if (!/^[a-f0-9]{64}$/.test(target.baseline_hash)) targetErrors.push('baseline_hash must be 64 hex');
        if (target.write_plan_status !== 'eligible_for_insert') {
            targetErrors.push('write_plan_status must be eligible_for_insert');
        }
        if (target.write_status !== 'blocked_missing_matches_fk_prerequisite') {
            targetErrors.push('write_status must be blocked_missing_matches_fk_prerequisite for renewed retry');
        }
        if (target.write_execution_status !== 'blocked_missing_matches_fk_prerequisite') {
            targetErrors.push('write_execution_status must be blocked_missing_matches_fk_prerequisite');
        }
        if (target.matches_seed_status !== 'inserted_matches_identity') {
            targetErrors.push('matches_seed_status must be inserted_matches_identity');
        }
        if (target.failure_reason && target.failure_reason !== 'blocked_missing_matches_fk_prerequisite') {
            targetErrors.push('failure_reason must be prior FK prerequisite block or empty');
        }
        if (hasFakeMarker(target)) targetErrors.push('fake/invented marker blocked');
        if (targetErrors.length > 0) {
            errors.push(`${target.match_id || target.external_id}: ${targetErrors.join(', ')}`);
        }
    }
    return {
        ok: errors.length === 0,
        errors,
        candidates,
        duplicate_external_id_count: duplicateExternalIds.size,
        duplicate_match_id_count: duplicateMatchIds.size,
    };
}

function distribution(values = []) {
    return values.reduce((acc, value) => {
        const key = value === null || value === undefined || value === '' ? 'missing' : String(value);
        acc[key] = (acc[key] || 0) + 1;
        return acc;
    }, {});
}

function validateManifestGate(manifest = {}) {
    const errors = [];
    if (normalizeText(manifest.batch_id) !== BATCH_ID) errors.push('manifest batch_id mismatch');
    if (normalizeText(manifest.source).toLowerCase() !== SOURCE) errors.push('manifest source mismatch');
    if (normalizeText(manifest.route) !== ROUTE) errors.push('manifest route mismatch');
    if (normalizeText(manifest.raw_data_version) !== RAW_VERSION) errors.push('manifest raw_data_version mismatch');
    if (normalizeText(manifest.hash_strategy) !== HASH_STRATEGY) errors.push('manifest hash_strategy mismatch');
    if (Number(manifest.league?.league_id) !== LEAGUE_ID) errors.push('manifest league_id mismatch');
    if (normalizeText(manifest.league?.league_name) !== LEAGUE_NAME) errors.push('manifest league_name mismatch');
    if (normalizeText(manifest.league?.season) !== SEASON) errors.push('manifest season mismatch');
    if (
        !Array.isArray(manifest.known_completed_targets) ||
        manifest.known_completed_targets.length !== KNOWN_COMPLETED_COUNT
    ) {
        errors.push(`known_completed_targets must contain ${KNOWN_COMPLETED_COUNT} targets`);
    }
    if (normalizeText(manifest.matches_identity_seed_execution_status) !== 'completed') {
        errors.push('matches_identity_seed_execution_status must be completed');
    }
    if (normalizeText(manifest.post_seed_matches_identity_verification_status) !== 'completed') {
        errors.push('post_seed_matches_identity_verification_status must be completed');
    }
    if (normalizeText(manifest.raw_write_fk_prerequisite_status) !== 'satisfied') {
        errors.push('raw_write_fk_prerequisite_status must be satisfied');
    }
    if (normalizeText(manifest.raw_write_retry_readiness_status) !== 'ready_for_renewed_authorization') {
        errors.push('raw_write_retry_readiness_status must be ready_for_renewed_authorization');
    }
    if (Number(manifest.eligible_raw_insert_count) !== TARGET_COUNT) {
        errors.push('eligible_raw_insert_count must be 50');
    }
    if (Number(manifest.expected_raw_match_data_after_retry) !== 68) {
        errors.push('expected_raw_match_data_after_retry must be 68');
    }
    if (normalizeText(manifest.required_next_step) !== 'renewed_controlled_pageprops_v2_raw_write_execution') {
        errors.push('required_next_step must be renewed_controlled_pageprops_v2_raw_write_execution');
    }
    if (normalizeText(manifest.write_execution_status) !== 'blocked_missing_matches_fk_prerequisite') {
        errors.push('write_execution_status must retain prior blocked_missing_matches_fk_prerequisite before retry');
    }
    if (normalizeText(manifest.raw_match_data_write_status) !== 'not_executed') {
        errors.push('raw_match_data_write_status must be not_executed before retry');
    }
    const candidateValidation = validateCandidateTargets(manifest);
    errors.push(...candidateValidation.errors);
    return {
        ok: errors.length === 0,
        errors,
        candidates: candidateValidation.candidates,
        candidate_validation: candidateValidation,
        candidate_targets: candidateValidation.candidates.length,
        known_completed_targets: Array.isArray(manifest.known_completed_targets)
            ? manifest.known_completed_targets.length
            : 0,
        matches_seed_status_distribution: distribution(
            candidateValidation.candidates.map(target => target.matches_seed_status)
        ),
        baseline_hash_ready_count: candidateValidation.candidates.filter(target =>
            /^[a-f0-9]{64}$/.test(target.baseline_hash)
        ).length,
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

function normalizeRowCounts(rowsOrObject = {}) {
    if (Array.isArray(rowsOrObject)) return buildProtectedTableBaseline(rowsOrObject);
    const output = {};
    for (const table of PROTECTED_TABLES) output[table] = Number(rowsOrObject[table] || 0);
    return output;
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

function normalizeDateIso(value) {
    if (!value) return '';
    const date = value instanceof Date ? value : new Date(value);
    if (Number.isNaN(date.getTime())) return normalizeText(value);
    return date.toISOString();
}

function buildMatchesIdentityGate(candidates = [], matchRows = []) {
    const rowsByMatchId = new Map(
        (Array.isArray(matchRows) ? matchRows : []).map(row => [normalizeText(row.match_id), row])
    );
    const mismatches = [];
    let externalIdMismatchCount = 0;
    let teamDateStatusMismatchCount = 0;
    for (const target of candidates) {
        const row = rowsByMatchId.get(target.match_id);
        if (!row) {
            mismatches.push({ match_id: target.match_id, field: 'match_id', expected: 'exists', actual: 'missing' });
            continue;
        }
        const rowExternalId = normalizeText(row.external_id);
        if (rowExternalId !== target.external_id) {
            externalIdMismatchCount += 1;
            mismatches.push({
                match_id: target.match_id,
                field: 'external_id',
                expected: target.external_id,
                actual: rowExternalId,
            });
        }
        const comparisons = [
            ['league_name', target.league_name, normalizeText(row.league_name)],
            ['season', target.season, normalizeText(row.season)],
            ['home_team', target.home_team, normalizeText(row.home_team)],
            ['away_team', target.away_team, normalizeText(row.away_team)],
            [
                'match_date',
                normalizeDateIso(target.match_date || target.kickoff_time),
                normalizeDateIso(row.match_date),
            ],
            ['status', target.status, normalizeText(row.status).toLowerCase()],
            ['is_finished', target.status === 'finished', row.is_finished === true],
            ['data_source', SOURCE, normalizeText(row.data_source).toLowerCase()],
            ['pipeline_status', 'pending', normalizeText(row.pipeline_status).toLowerCase()],
        ];
        for (const [field, expected, actual] of comparisons) {
            if (expected !== actual) {
                if (['home_team', 'away_team', 'match_date', 'status'].includes(field)) {
                    teamDateStatusMismatchCount += 1;
                }
                mismatches.push({ match_id: target.match_id, field, expected, actual });
            }
        }
    }
    const missingMatchesCount = candidates.length - rowsByMatchId.size;
    return {
        ok: mismatches.length === 0 && rowsByMatchId.size === candidates.length,
        expected_candidate_count: candidates.length,
        matches_found_count: rowsByMatchId.size,
        missing_matches_count: missingMatchesCount < 0 ? 0 : missingMatchesCount,
        identity_mismatch_count: mismatches.length,
        external_id_mismatch_count: externalIdMismatchCount,
        team_date_status_mismatch_count: teamDateStatusMismatchCount,
        mismatches: mismatches.slice(0, 25),
    };
}

function buildExistingRawGate(candidates = [], rows = []) {
    const safeRows = Array.isArray(rows) ? rows : [];
    const v2Rows = safeRows.filter(row => normalizeText(row.data_version) === RAW_VERSION);
    return {
        ok: v2Rows.length === 0,
        existing_v2_raw_rows_for_candidates: v2Rows.length,
        conflicts: v2Rows.map(row => ({
            id: row.id ?? null,
            match_id: normalizeText(row.match_id),
            external_id: normalizeText(row.external_id),
            data_hash: normalizeText(row.data_hash) || null,
        })),
        candidate_count: candidates.length,
    };
}

function publicRecaptureSummary(summary = {}) {
    const {
        rawData: _rawData,
        pageProps: _pageProps,
        candidate_shape_summary: _candidateShapeSummary,
        pageProps_shape_summary: _pagePropsShapeSummary,
        pageProps_top_level_keys: _pagePropsTopLevelKeys,
        ...publicFields
    } = summary;
    return publicFields;
}

function sleep(ms) {
    if (!ms) return Promise.resolve();
    return new Promise(resolve => {
        setTimeout(resolve, ms);
    });
}

function isRecapturePass(summary = {}) {
    return (
        summary.target_status === 'hash_gate_passed' &&
        summary.hash_matches_baseline === true &&
        !summary.failure_reason &&
        (summary.block_markers || []).length === 0
    );
}

async function recaptureTargetsSequential(candidates = [], dependencies = {}) {
    const targets = [];
    const publicTargets = [];
    const requestDelayMs = Number.isInteger(dependencies.requestDelayMs)
        ? dependencies.requestDelayMs
        : DEFAULT_REQUEST_DELAY_MS;
    for (let index = 0; index < candidates.length; index += 1) {
        const target = candidates[index];
        const summary = await base.recaptureTarget(target, index, dependencies);
        targets.push(summary);
        const publicSummary = publicRecaptureSummary(summary);
        publicTargets.push(publicSummary);
        if (typeof dependencies.progress === 'function') {
            dependencies.progress({
                index: index + 1,
                total: candidates.length,
                match_id: publicSummary.match_id,
                external_id: publicSummary.external_id,
                target_status: publicSummary.target_status,
                http_status: publicSummary.http_status,
                recaptured_hash: publicSummary.recaptured_hash,
                hash_matches_baseline: publicSummary.hash_matches_baseline,
                body_byte_length: publicSummary.body_byte_length,
                failure_reason: publicSummary.failure_reason,
                block_markers: publicSummary.block_markers,
                identity_reconciliation_status: publicSummary.identity_reconciliation_status,
                route_identity_gate_ok: publicSummary.route_identity_gate_ok,
            });
        }
        if (!isRecapturePass(summary)) break;
        if (index < candidates.length - 1) await sleep(requestDelayMs);
    }
    return {
        targets,
        public_targets: publicTargets,
        attempted_target_count: publicTargets.length,
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
        request_count: publicTargets.length,
        request_delay_ms: requestDelayMs,
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
        if (normalizeText(row.data_version) !== RAW_VERSION) errors.push(`wrong data_version ${target.match_id}`);
        if (normalizeText(row.data_hash).toLowerCase() !== target.baseline_hash) {
            errors.push(`data_hash mismatch ${target.match_id}`);
        }
        if (row.has_meta !== true) errors.push(`raw_data missing _meta ${target.match_id}`);
        if (row.has_match_id !== true) errors.push(`raw_data missing matchId ${target.match_id}`);
        if (row.has_pageprops !== true) errors.push(`raw_data missing pageProps ${target.match_id}`);
        if (normalizeText(row.meta_hash_strategy) !== HASH_STRATEGY) {
            errors.push(`raw_data._meta.hash_strategy mismatch ${target.match_id}`);
        }
    }
    if ((duplicateRows || []).length > 0) errors.push(`duplicate match_id/data_version rows: ${duplicateRows.length}`);
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
        existing_v2_raw_rows_for_candidates: postWriteRows.length,
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

async function loadCandidateMatchesFull(client, matchIds = []) {
    const result = await base.queryReadOnly(
        client,
        `
        SELECT
          match_id,
          external_id,
          league_name,
          season,
          home_team,
          away_team,
          match_date,
          status,
          is_finished,
          data_source,
          pipeline_status
        FROM matches
        WHERE match_id = ANY($1::text[])
        ORDER BY match_id
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

function nowUtcIso(dependencies = {}) {
    if (typeof dependencies.now === 'function') return dependencies.now();
    if (dependencies.now) return dependencies.now;
    return new Date().toISOString();
}

async function loadGateData({ client, candidates, dependencies }) {
    const matchIds = candidates.map(target => target.match_id);
    const rowCountsBefore = normalizeRowCounts(
        dependencies.protectedTableRowsBefore || (await base.loadProtectedTableBaselineRows(client))
    );
    const constraintRows = dependencies.constraintRows || (await base.loadRawMatchDataConstraints(client));
    const matchRows = dependencies.matchRows || (await loadCandidateMatchesFull(client, matchIds));
    const existingV2Rows = dependencies.existingV2Rows || (await base.loadExistingCandidateV2Rows(client, matchIds));
    return { rowCountsBefore, constraintRows, matchRows, existingV2Rows };
}

async function executeTransaction({ client, candidates, recaptureGate, rowCountsBefore, dependencies, generatedAt }) {
    const transaction = { began: false, committed: false, rolled_back: false };
    const matchIds = candidates.map(target => target.match_id);
    const collectedAt = dependencies.collectedAt || generatedAt;
    const insertSql = base.buildInsertRawMatchDataSql(recaptureGate.targets, collectedAt);
    try {
        await base.queryControlledWrite(client, 'BEGIN');
        transaction.began = true;
        const existingInside =
            dependencies.existingV2RowsInsideTransaction || (await base.loadExistingCandidateV2Rows(client, matchIds));
        if (existingInside.length > 0) {
            await base.queryControlledWrite(client, 'ROLLBACK');
            transaction.rolled_back = true;
            return {
                ok: false,
                reason: `EXISTING_V2_ROWS_RACE:${existingInside.length}`,
                insertedRows: [],
                transaction,
                rowCountsAfter: normalizeRowCounts(await base.loadProtectedTableBaselineRows(client)),
                postWriteVerification: null,
            };
        }
        const insertResult = await base.queryControlledWrite(client, insertSql.text, insertSql.values);
        const insertedRows = insertResult.rows || [];
        if (insertedRows.length !== TARGET_COUNT) {
            await base.queryControlledWrite(client, 'ROLLBACK');
            transaction.rolled_back = true;
            return {
                ok: false,
                reason: `INSERTED_COUNT_MISMATCH:${insertedRows.length}`,
                insertedRows,
                transaction,
                rowCountsAfter: normalizeRowCounts(await base.loadProtectedTableBaselineRows(client)),
                postWriteVerification: null,
            };
        }
        const rowCountsInsideTransaction = normalizeRowCounts(
            dependencies.protectedTableRowsInsideTransaction || (await base.loadProtectedTableBaselineRows(client))
        );
        const insideErrors = validateExactRowCounts(rowCountsInsideTransaction, EXPECTED_ROW_COUNTS_AFTER_SUCCESS);
        const postWriteRowsInside =
            dependencies.postWriteRowsInsideTransaction || (await base.loadPostWriteCandidateRows(client, matchIds));
        const duplicateRowsInside =
            dependencies.duplicateRowsInsideTransaction ||
            (await base.loadDuplicateCandidateVersionRows(client, matchIds));
        const insideVerification = buildPostWriteVerification({
            candidates,
            rowCountsBefore,
            rowCountsAfter: rowCountsInsideTransaction,
            postWriteRows: postWriteRowsInside,
            duplicateRows: duplicateRowsInside,
        });
        if (insideErrors.length > 0 || !insideVerification.ok) {
            await base.queryControlledWrite(client, 'ROLLBACK');
            transaction.rolled_back = true;
            return {
                ok: false,
                reason: `IN_TRANSACTION_VERIFICATION_FAILED:${[...insideErrors, ...insideVerification.errors].join(';')}`,
                insertedRows,
                transaction,
                rowCountsAfter: rowCountsInsideTransaction,
                postWriteVerification: insideVerification,
            };
        }
        await base.queryControlledWrite(client, 'COMMIT');
        transaction.committed = true;
        const rowCountsAfter = normalizeRowCounts(
            dependencies.protectedTableRowsAfter || (await base.loadProtectedTableBaselineRows(client))
        );
        const postWriteRows =
            dependencies.postWriteRowsAfter || (await base.loadPostWriteCandidateRows(client, matchIds));
        const duplicateRows =
            dependencies.duplicateRowsAfter || (await base.loadDuplicateCandidateVersionRows(client, matchIds));
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
                await base.queryControlledWrite(client, 'ROLLBACK');
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

function buildPayload({
    ok,
    input = {},
    reason = null,
    manifestGate = null,
    rowCountsBefore = null,
    schemaReadiness = null,
    matchesIdentityGate = null,
    existingRawGate = null,
    recaptureGate = null,
    transactionResult = null,
} = {}) {
    const rowCountsAfter = transactionResult?.rowCountsAfter || null;
    const insertedCount = transactionResult?.insertedRows?.length || 0;
    return {
        phase: PHASE,
        ok: ok === true,
        controlled_failure: ok !== true,
        blocked_reason: ok ? null : reason,
        source: SOURCE,
        route: ROUTE,
        raw_version: RAW_VERSION,
        hash_strategy: HASH_STRATEGY,
        batch_id: BATCH_ID,
        start_head: input.startHead || null,
        branch: input.branch || null,
        authorization: {
            renewed_raw_write_authorization: input.renewedRawWriteAuthorization === true,
            final_db_write_confirmation: input.finalDbWriteConfirmation === true,
            network_authorization: input.networkAuthorization === true,
            match_detail_recapture_authorization: input.matchDetailRecaptureAuthorization === true,
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
            request_delay_ms: input.requestDelayMs,
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
                  candidate_targets: manifestGate.candidate_targets,
                  known_completed_targets: manifestGate.known_completed_targets,
                  matches_seed_status_distribution: manifestGate.matches_seed_status_distribution,
                  baseline_hash_ready_count: manifestGate.baseline_hash_ready_count,
                  errors: manifestGate.errors,
              }
            : null,
        schema_gate: schemaReadiness,
        matches_identity_gate: matchesIdentityGate,
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
                  request_delay_ms: recaptureGate.request_delay_ms,
                  first_target: recaptureGate.public_targets[0] || null,
                  last_target: recaptureGate.public_targets[recaptureGate.public_targets.length - 1] || null,
                  failed_targets: recaptureGate.public_targets.filter(target => target.failure_reason).slice(0, 10),
              }
            : null,
        transaction: {
            began: transactionResult?.transaction?.began === true,
            committed: transactionResult?.transaction?.committed === true,
            rolled_back: transactionResult?.transaction?.rolled_back === true,
        },
        attempted_raw_insert_count: ok ? TARGET_COUNT : insertedCount,
        inserted_raw_match_data_count: ok ? insertedCount : 0,
        inserted_count: insertedCount,
        updated_count: 0,
        skipped_count: 0,
        row_counts_before: rowCountsBefore,
        row_counts_after: rowCountsAfter,
        post_write_verification: transactionResult?.postWriteVerification || null,
        raw_match_data_write_executed: transactionResult?.transaction?.began === true,
        matches_write_executed: false,
        bookmaker_odds_write_executed: false,
        feature_write_executed: false,
        training_executed: false,
        prediction_executed: false,
        parser_features_training_executed: false,
        browser_used: false,
        proxy_used: false,
        no_full_body_json_pageprops_print_save: true,
        blockers: ok ? [] : [reason].filter(Boolean),
        next_required_step: ok
            ? 'post_l2v3_pageprops_v2_canonical_read_completeness_audit'
            : 'renewed_controlled_pageprops_v2_raw_write_execution_blocked_review',
    };
}

function updateManifestWithExecution(manifest = {}, payload = {}, generatedAt = new Date().toISOString()) {
    const next = jsonClone(manifest);
    const success = payload.ok === true;
    next.phase_5_21_l2v3_execution_status = success ? 'completed' : 'blocked';
    next.renewed_controlled_pageprops_v2_raw_write_status = success ? 'completed' : 'blocked';
    next.raw_write_execution_authorization_status = 'explicitly_authorized_by_user';
    next.recapture_target_count = payload.recapture_hash_gate?.attempted_target_count || 0;
    next.hash_gate_status = success ? 'passed' : payload.recapture_hash_gate ? 'blocked' : 'not_executed';
    next.attempted_raw_insert_count = payload.attempted_raw_insert_count || 0;
    next.inserted_raw_match_data_count = success ? payload.inserted_raw_match_data_count : 0;
    next.raw_match_data_before_count = payload.row_counts_before?.raw_match_data ?? null;
    next.raw_match_data_after_count = payload.row_counts_after?.raw_match_data ?? null;
    next.expected_raw_match_data_after_count = EXPECTED_ROW_COUNTS_AFTER_SUCCESS.raw_match_data;
    next.non_raw_tables_unchanged_status = payload.post_write_verification?.protected_tables_unchanged
        ? 'unchanged'
        : success
          ? 'verification_failed'
          : 'not_executed';
    next.transaction_status = payload.transaction?.committed
        ? 'committed'
        : payload.transaction?.rolled_back
          ? 'rolled_back'
          : 'not_started';
    next.blockers = payload.blockers || [];
    next.write_execution_status = success ? 'completed' : payload.blocked_reason || 'blocked';
    next.raw_match_data_write_status = success ? 'completed' : 'not_executed';
    next.write_execution_at = generatedAt;
    next.inserted_count = success ? payload.inserted_raw_match_data_count : 0;
    next.blocked_count = success ? 0 : TARGET_COUNT;
    next.required_next_step = payload.next_required_step;
    next.next_required_step = payload.next_required_step;
    next.phase_5_21_l2v3_execution_result = {
        phase: PHASE,
        generated_at: generatedAt,
        ok: success,
        blocked_reason: payload.blocked_reason || null,
        recapture_target_count: next.recapture_target_count,
        hash_gate_status: next.hash_gate_status,
        attempted_raw_insert_count: next.attempted_raw_insert_count,
        inserted_raw_match_data_count: next.inserted_raw_match_data_count,
        raw_match_data_before_count: next.raw_match_data_before_count,
        raw_match_data_after_count: next.raw_match_data_after_count,
        expected_raw_match_data_after_count: next.expected_raw_match_data_after_count,
        non_raw_tables_unchanged_status: next.non_raw_tables_unchanged_status,
        transaction_status: next.transaction_status,
        existing_v2_raw_rows_for_candidates:
            payload.post_write_verification?.existing_v2_raw_rows_for_candidates ?? null,
        blockers: next.blockers,
        next_required_step: next.next_required_step,
    };
    next.candidate_targets = (next.candidate_targets || []).map(target => {
        const matchId = normalizeText(target.match_id);
        const recaptured =
            payload.recapture_hash_gate?.first_target?.match_id === matchId
                ? payload.recapture_hash_gate.first_target
                : payload.recapture_hash_gate?.last_target?.match_id === matchId
                  ? payload.recapture_hash_gate.last_target
                  : null;
        return {
            ...target,
            updated_at: generatedAt,
            write_status: success ? 'inserted_raw_match_data' : target.write_status,
            write_execution_status: success
                ? 'inserted_raw_match_data'
                : payload.blocked_reason || target.write_execution_status,
            raw_match_data_write_status: success ? 'inserted_raw_match_data' : 'not_executed',
            write_executed_at: success ? generatedAt : target.write_executed_at || null,
            failure_reason: success ? null : payload.blocked_reason || target.failure_reason || 'l2v3_blocked',
            required_next_step: next.next_required_step,
            phase_5_21_l2v3_status: success ? 'inserted_raw_match_data' : 'blocked',
            recaptured_hash: success
                ? target.baseline_hash
                : recaptured?.recaptured_hash || target.recaptured_hash || null,
            hash_matches_baseline: success
                ? true
                : (recaptured?.hash_matches_baseline ?? target.hash_matches_baseline ?? null),
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
    const decision = payload.ok ? 'GO for post-write read-only verification' : 'NO-GO for raw write retry completion';
    const lines = [
        '# Data Entrypoint Governance - Phase 5.21 L2V3',
        '',
        '## 1. Executive summary',
        '',
        '- Phase 5.21L2V3 is renewed controlled pageProps v2 raw write execution.',
        '- It is authorized for raw_match_data only.',
        '- It does not write matches, odds, features, training, or predictions.',
        '- It does not run parser/features/training/prediction.',
        `- decision=${decision}`,
        '',
        '## 2. Start context',
        '',
        `- start_head=${payload.start_head || 'not_recorded'}`,
        `- branch=${payload.branch || 'not_recorded'}`,
        `- manifest_path=${MANIFEST_PATH}`,
        '',
        '## 3. Preflight result',
        '',
        `- input_authorized=${payload.authorization?.renewed_raw_write_authorization === true}`,
        `- final_db_write_confirmation=${payload.authorization?.final_db_write_confirmation === true}`,
        `- target_count=${TARGET_COUNT}`,
        `- request_delay_ms=${payload.authorization?.request_delay_ms ?? DEFAULT_REQUEST_DELAY_MS}`,
        '- no browser/proxy/captcha bypass',
        '- no full body/pageProps/source body print/save',
        '',
        '## 4. Discovery result',
        '',
        `- manifest_gate_ok=${payload.manifest_gate?.ok === true}`,
        `- candidate_targets=${payload.manifest_gate?.candidate_targets || 0}`,
        `- known_completed_targets=${payload.manifest_gate?.known_completed_targets || 0}`,
        `- baseline_hash_ready_count=${payload.manifest_gate?.baseline_hash_ready_count || 0}`,
        `- raw_match_data UNIQUE(match_id,data_version) present=${payload.schema_gate?.unique_match_id_data_version_present === true}`,
        `- old UNIQUE(match_id) absent=${payload.schema_gate?.old_unique_match_id_absent === true}`,
        `- raw_match_data FK present=${payload.schema_gate?.fk_present === true}`,
        `- matches_found_count=${payload.matches_identity_gate?.matches_found_count ?? 0}`,
        `- missing_matches_count=${payload.matches_identity_gate?.missing_matches_count ?? 0}`,
        `- identity_mismatch_count=${payload.matches_identity_gate?.identity_mismatch_count ?? 0}`,
        `- existing_v2_raw_rows_for_candidates=${payload.existing_raw_gate?.existing_v2_raw_rows_for_candidates ?? 0}`,
        '',
        '## 5. Recapture summary',
        '',
        `- network_executed=${payload.recapture_hash_gate ? true : false}`,
        `- attempted_target_count=${payload.recapture_hash_gate?.attempted_target_count || 0}`,
        `- request_count=${payload.recapture_hash_gate?.request_count || 0}`,
        `- recapture_success_count=${payload.recapture_hash_gate?.recapture_success_count || 0}`,
        `- failed_count=${payload.recapture_hash_gate?.failed_count || 0}`,
        `- blocked_count=${payload.recapture_hash_gate?.blocked_count || 0}`,
        '- full pageProps/source body printed=false',
        '- full pageProps/source body saved=false',
        '',
        '## 6. Hash gate summary',
        '',
        `- hash_strategy=${HASH_STRATEGY}`,
        `- hash_match_count=${payload.recapture_hash_gate?.hash_match_count || 0}`,
        `- hash_drift_count=${payload.recapture_hash_gate?.hash_drift_count || 0}`,
        `- hash_gate_status=${payload.ok ? 'passed' : payload.recapture_hash_gate ? 'blocked' : 'not_executed'}`,
        '',
        '## 7. DB transaction summary',
        '',
        `- transaction_began=${payload.transaction?.began === true}`,
        `- attempted_raw_insert_count=${payload.attempted_raw_insert_count || 0}`,
        `- inserted_raw_match_data_count=${payload.inserted_raw_match_data_count || 0}`,
        `- committed=${payload.transaction?.committed === true}`,
        `- rolled_back=${payload.transaction?.rolled_back === true}`,
        `- blocked_reason=${payload.blocked_reason || 'none'}`,
        '',
        '## 8. Row count before/after',
        '',
        'Before:',
        '',
        formatRowCounts(payload.row_counts_before || {}),
        '',
        'After:',
        '',
        payload.row_counts_after ? formatRowCounts(payload.row_counts_after) : '- not executed',
        '',
        '## 9. Tables explicitly confirmed unchanged',
        '',
        `- matches unchanged=${payload.row_counts_after ? payload.row_counts_after.matches === EXPECTED_ROW_COUNTS_BEFORE.matches : false}`,
        `- bookmaker_odds_history unchanged=${
            payload.row_counts_after
                ? payload.row_counts_after.bookmaker_odds_history === EXPECTED_ROW_COUNTS_BEFORE.bookmaker_odds_history
                : false
        }`,
        `- l3_features unchanged=${
            payload.row_counts_after
                ? payload.row_counts_after.l3_features === EXPECTED_ROW_COUNTS_BEFORE.l3_features
                : false
        }`,
        `- match_features_training unchanged=${
            payload.row_counts_after
                ? payload.row_counts_after.match_features_training ===
                  EXPECTED_ROW_COUNTS_BEFORE.match_features_training
                : false
        }`,
        `- predictions unchanged=${
            payload.row_counts_after
                ? payload.row_counts_after.predictions === EXPECTED_ROW_COUNTS_BEFORE.predictions
                : false
        }`,
        '',
        '## 10. Tests run',
        '',
        '- L2V3 execution tests: pending final validation',
        '- L2V/L2U/L2T safety tests: pending final validation',
        '- FotMobRawDetailFetcher tests: pending final validation',
        '- RawMatchDataVersionSelector tests: pending final validation',
        '- Makefile audit target: pending final validation',
        '- npm test: pending final validation',
        '- npm run test:coverage: pending final validation',
        '- eslint / prettier / git diff: pending final validation',
        '',
        '## 11. PR / CI',
        '',
        '- PR: pending',
        '- PR CI: pending',
        '- main push CI: pending',
        '',
        '## 12. Next phase decision',
        '',
        `- decision=${decision}`,
        `- next_required_step=${payload.next_required_step}`,
        '',
        '## 13. Explicit non-execution',
        '',
        '- no matches writes',
        '- no bookmaker_odds_history writes',
        '- no l3_features writes',
        '- no match_features_training writes',
        '- no predictions writes',
        '- no schema migration',
        '- no parser implementation',
        '- no feature extraction',
        '- no training/prediction',
        '- no browser/proxy/captcha bypass',
        '- no full raw_data/pageProps/source body print/save',
        '- no file deletion',
        '- no invented external_id / fake target data',
        '',
    ];
    return `${lines.join('\n')}\n`;
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

async function runCli(argv = process.argv.slice(2), dependencies = {}) {
    const parsed = Array.isArray(argv) ? parseArgs(argv) : argv;
    const validation = validateExecutionInput(parsed);
    const output = dependencies.output || (payload => process.stdout.write(`${JSON.stringify(payload, null, 2)}\n`));
    if (!validation.ok) {
        const payload = buildPayload({
            ok: false,
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
            const payload = buildPayload({
                ok: false,
                input,
                reason: `MANIFEST_GATE_BLOCKED:${manifestGate.errors.join(';')}`,
                manifestGate,
            });
            writeExecutionArtifacts({ manifest, payload, input, generatedAt, dependencies });
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
        const schemaReadiness = base.buildSchemaReadiness(constraintRows);
        const matchesIdentityGate = buildMatchesIdentityGate(candidates, matchRows);
        const existingRawGate = buildExistingRawGate(candidates, existingV2Rows);
        if (baselineErrors.length > 0 || !schemaReadiness.ok || !matchesIdentityGate.ok || !existingRawGate.ok) {
            const reason =
                baselineErrors.length > 0
                    ? `DB_BASELINE_BLOCKED:${baselineErrors.join(';')}`
                    : !schemaReadiness.ok
                      ? `SCHEMA_GATE_BLOCKED:${schemaReadiness.errors.join(';')}`
                      : !matchesIdentityGate.ok
                        ? 'MATCHES_IDENTITY_GATE_BLOCKED'
                        : 'EXISTING_V2_RAW_ROWS_BLOCKED';
            const payload = buildPayload({
                ok: false,
                input,
                reason,
                manifestGate,
                rowCountsBefore,
                schemaReadiness,
                matchesIdentityGate,
                existingRawGate,
            });
            writeExecutionArtifacts({ manifest, payload, input, generatedAt, dependencies });
            output(payload);
            return { status: 1, payload };
        }
        const progress =
            dependencies.progress ||
            (summary => {
                process.stderr.write(
                    `[L2V3_RECAPTURE] ${summary.index}/${summary.total} match_id=${summary.match_id} external_id=${summary.external_id} status=${summary.target_status} http=${summary.http_status} hash=${summary.recaptured_hash || 'none'} bytes=${summary.body_byte_length || 0}\n`
                );
            });
        const recaptureGate = await recaptureTargetsSequential(candidates, {
            ...dependencies,
            progress,
            requestDelayMs: input.requestDelayMs,
        });
        if (
            recaptureGate.recapture_success_count !== TARGET_COUNT ||
            recaptureGate.hash_match_count !== TARGET_COUNT ||
            recaptureGate.failed_count > 0 ||
            recaptureGate.blocked_count > 0 ||
            recaptureGate.route_identity_blocked_count > 0 ||
            recaptureGate.attempted_target_count !== TARGET_COUNT
        ) {
            const reason =
                recaptureGate.route_identity_blocked_count > 0
                    ? 'ROUTE_IDENTITY_GATE_BLOCKED'
                    : 'RECAPTURE_HASH_GATE_BLOCKED';
            const payload = buildPayload({
                ok: false,
                input,
                reason,
                manifestGate,
                rowCountsBefore,
                schemaReadiness,
                matchesIdentityGate,
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
        const payload = buildPayload({
            ok: transactionResult.ok,
            input,
            reason: transactionResult.ok ? null : transactionResult.reason,
            manifestGate,
            rowCountsBefore,
            schemaReadiness,
            matchesIdentityGate,
            existingRawGate,
            recaptureGate,
            transactionResult,
        });
        writeExecutionArtifacts({ manifest, payload, input, generatedAt, dependencies });
        output(payload);
        return { status: transactionResult.ok ? 0 : 1, payload };
    } catch (error) {
        const payload = buildPayload({ ok: false, input, reason: error.message });
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
    RAW_VERSION,
    HASH_STRATEGY,
    TARGET_COUNT,
    EXPECTED_ROW_COUNTS_BEFORE,
    EXPECTED_ROW_COUNTS_AFTER_SUCCESS,
    parseArgs,
    normalizeBooleanFlag,
    validateExecutionInput,
    validateManifestGate,
    validateCandidateTargets,
    buildProtectedTableBaseline,
    buildMatchesIdentityGate,
    buildExistingRawGate,
    recaptureTargetsSequential,
    buildPostWriteVerification,
    updateManifestWithExecution,
    buildReport,
    executeTransaction,
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
