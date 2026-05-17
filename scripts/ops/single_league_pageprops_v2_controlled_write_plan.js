#!/usr/bin/env node
/* eslint-disable complexity, max-lines, max-statements */
'use strict';

const fs = require('node:fs');
const path = require('node:path');

const PHASE = 'PHASE5_21L2U_SINGLE_LEAGUE_PAGEPROPS_V2_CONTROLLED_WRITE_PLANNING';
const MANIFEST_PATH = 'docs/_manifests/fotmob_pageprops_v2_ligue1_2025_2026_profile_001.proposal.json';
const REPORT_PATH = 'docs/_reports/SINGLE_LEAGUE_PAGEPROPS_V2_CONTROLLED_WRITE_PLANNING_PHASE5_21L2U.md';
const SOURCE = 'fotmob';
const LEAGUE_ID = 53;
const LEAGUE_NAME = 'Ligue 1';
const SEASON = '2025/2026';
const SEASON_COMPACT = '20252026';
const ROUTE = 'html_hydration';
const RAW_VERSION = 'fotmob_pageprops_v2';
const HASH_STRATEGY = 'stable_pageprops_payload_v1';
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
    'allowNetwork',
    'allowMatchDetailFetch',
    'allowSchemaMigration',
    'allowParserImplementation',
    'allowFeatureExtraction',
    'allowTraining',
    'allowPrediction',
]);
const BLOCKED_TRUE_FLAGS = Object.freeze(['executeWrite', 'commit', 'finalDbWriteConfirmation', 'allowOddsWrite']);

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
        writePlanningAuthorization: null,
        allowDbWrite: null,
        allowRawMatchDataWrite: null,
        allowControlledWrite: null,
        allowNetwork: null,
        allowMatchDetailFetch: null,
        allowSchemaMigration: null,
        allowParserImplementation: null,
        allowFeatureExtraction: null,
        allowTraining: null,
        allowPrediction: null,
        executeWrite: false,
        commit: false,
        finalDbWriteConfirmation: false,
        allowOddsWrite: false,
        help: false,
        unknown: [],
    };
    const knownKeys = new Set(Object.keys(options));
    const booleanKeys = new Set(['writePlanningAuthorization', ...REQUIRED_NO_FLAGS, ...BLOCKED_TRUE_FLAGS, 'help']);

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

function requireExact(errors, actual, expected, name) {
    if (!normalizeText(actual)) {
        errors.push(`missing ${name}=${expected}`);
        return;
    }
    if (normalizeText(actual) !== expected) errors.push(`${name} must be ${expected}`);
}

function pushRequiredYes(errors, value, name) {
    if (value === true) return;
    if (value === false) {
        errors.push(`${name}=yes is required in Phase 5.21L2U`);
        return;
    }
    errors.push(`missing ${name}=yes`);
}

function pushRequiredNo(errors, value, name) {
    if (value === false) return;
    if (value === true) {
        errors.push(`${name}=yes is blocked in Phase 5.21L2U`);
        return;
    }
    errors.push(`missing ${name}=no`);
}

function normalizePlanInput(input = {}) {
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
        writePlanningAuthorization: normalizeBooleanFlag(input.writePlanningAuthorization, undefined),
        allowDbWrite: normalizeBooleanFlag(input.allowDbWrite, undefined),
        allowRawMatchDataWrite: normalizeBooleanFlag(input.allowRawMatchDataWrite, undefined),
        allowControlledWrite: normalizeBooleanFlag(input.allowControlledWrite, undefined),
        allowNetwork: normalizeBooleanFlag(input.allowNetwork, undefined),
        allowMatchDetailFetch: normalizeBooleanFlag(input.allowMatchDetailFetch, undefined),
        allowSchemaMigration: normalizeBooleanFlag(input.allowSchemaMigration, undefined),
        allowParserImplementation: normalizeBooleanFlag(input.allowParserImplementation, undefined),
        allowFeatureExtraction: normalizeBooleanFlag(input.allowFeatureExtraction, undefined),
        allowTraining: normalizeBooleanFlag(input.allowTraining, undefined),
        allowPrediction: normalizeBooleanFlag(input.allowPrediction, undefined),
        executeWrite: normalizeBooleanFlag(input.executeWrite, false),
        commit: normalizeBooleanFlag(input.commit, false),
        finalDbWriteConfirmation: normalizeBooleanFlag(input.finalDbWriteConfirmation, false),
        allowOddsWrite: normalizeBooleanFlag(input.allowOddsWrite, false),
        unknown: Array.isArray(input.unknown) ? input.unknown : [],
    };
}

function validatePlanInput(input = {}) {
    const value = normalizePlanInput(input);
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
    pushRequiredYes(errors, value.writePlanningAuthorization, 'write-planning-authorization');
    for (const key of REQUIRED_NO_FLAGS) {
        pushRequiredNo(errors, value[key], flagName(key));
    }
    for (const key of BLOCKED_TRUE_FLAGS) {
        if (value[key] === true) errors.push(`${flagName(key)}=yes is blocked in Phase 5.21L2U`);
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
        preflight_status: normalizeText(target.preflight_status),
        baseline_hash: normalizeText(target.baseline_hash).toLowerCase(),
        failure_reason: target.failure_reason === null ? null : normalizeText(target.failure_reason),
        write_status: normalizeText(target.write_status),
    };
}

function countDuplicateExtras(values = []) {
    const counts = new Map();
    for (const value of values.filter(Boolean)) counts.set(value, (counts.get(value) || 0) + 1);
    return [...counts.values()].reduce((sum, count) => sum + Math.max(0, count - 1), 0);
}

function buildDuplicateSets(candidates = []) {
    const externalCounts = new Map();
    const matchCounts = new Map();
    for (const target of candidates) {
        externalCounts.set(target.external_id, (externalCounts.get(target.external_id) || 0) + 1);
        matchCounts.set(target.match_id, (matchCounts.get(target.match_id) || 0) + 1);
    }
    return {
        duplicateExternalIds: new Set([...externalCounts].filter(([, count]) => count > 1).map(([value]) => value)),
        duplicateMatchIds: new Set([...matchCounts].filter(([, count]) => count > 1).map(([value]) => value)),
    };
}

function validateManifestStructure(manifest = {}) {
    const errors = [];
    if (normalizeText(manifest.schema_version) !== 'target_manifest_proposal_v1') {
        errors.push('manifest schema_version must be target_manifest_proposal_v1');
    }
    if (normalizeText(manifest.batch_id) !== BATCH_ID) errors.push('manifest batch_id mismatch');
    if (normalizeText(manifest.source).toLowerCase() !== SOURCE) errors.push('manifest source mismatch');
    if (normalizeText(manifest.route) !== ROUTE) errors.push('manifest route mismatch');
    if (normalizeText(manifest.raw_data_version) !== RAW_VERSION) errors.push('manifest raw_data_version mismatch');
    if (normalizeText(manifest.hash_strategy) !== HASH_STRATEGY) errors.push('manifest hash_strategy mismatch');
    if (Number(manifest.league?.league_id) !== LEAGUE_ID) errors.push('manifest league_id mismatch');
    if (normalizeText(manifest.league?.league_name) !== LEAGUE_NAME) errors.push('manifest league_name mismatch');
    if (normalizeText(manifest.league?.season) !== SEASON) errors.push('manifest season mismatch');
    if (!Array.isArray(manifest.known_completed_targets)) {
        errors.push('manifest known_completed_targets must be an array');
    } else if (manifest.known_completed_targets.length !== KNOWN_COMPLETED_COUNT) {
        errors.push(`manifest known_completed_targets must contain ${KNOWN_COMPLETED_COUNT} targets`);
    }
    if (!Array.isArray(manifest.candidate_targets)) {
        errors.push('manifest candidate_targets must be an array');
    } else if (manifest.candidate_targets.length !== TARGET_COUNT) {
        errors.push(`manifest candidate_targets must contain ${TARGET_COUNT} targets`);
    }
    if (normalizeText(manifest.target_population_status) !== 'ready_for_controlled_write_authorization') {
        errors.push('manifest target_population_status must be ready_for_controlled_write_authorization before L2U');
    }
    const nextStep = normalizeText(manifest.required_next_step);
    if (!nextStep.includes('controlled') || !nextStep.includes('write') || !nextStep.includes('authorization')) {
        errors.push('manifest required_next_step must point to controlled write authorization/planning');
    }
    return { ok: errors.length === 0, errors };
}

function validateCandidateTargets(manifest = {}) {
    const candidates = Array.isArray(manifest.candidate_targets)
        ? manifest.candidate_targets.map(normalizeCandidateTarget)
        : [];
    const { duplicateExternalIds, duplicateMatchIds } = buildDuplicateSets(candidates);
    const completedExternalIds = new Set(
        (manifest.known_completed_targets || []).map(target => normalizeText(target.external_id)).filter(Boolean)
    );
    const targetErrors = new Map();
    const addError = (target, message) => {
        const key = target.external_id || target.match_id || `target-${targetErrors.size + 1}`;
        if (!targetErrors.has(key)) targetErrors.set(key, []);
        targetErrors.get(key).push(message);
    };

    for (const target of candidates) {
        if (!/^\d+$/.test(target.external_id)) addError(target, 'external_id must be numeric');
        const expectedMatchId = `${LEAGUE_ID}_${SEASON_COMPACT}_${target.external_id}`;
        if (target.match_id !== expectedMatchId) addError(target, `match_id must be ${expectedMatchId}`);
        if (duplicateExternalIds.has(target.external_id)) addError(target, 'duplicate external_id');
        if (duplicateMatchIds.has(target.match_id)) addError(target, 'duplicate match_id');
        if (completedExternalIds.has(target.external_id)) {
            addError(target, 'candidate overlaps known_completed_targets');
        }
        if (target.batch_id !== BATCH_ID) addError(target, 'batch_id mismatch');
        if (target.source !== SOURCE) addError(target, 'source mismatch');
        if (target.route !== ROUTE) addError(target, 'route mismatch');
        if (target.raw_data_version !== RAW_VERSION) addError(target, 'raw_data_version mismatch');
        if (target.hash_strategy !== HASH_STRATEGY) addError(target, 'hash_strategy mismatch');
        if (target.league_id !== LEAGUE_ID) addError(target, 'league_id mismatch');
        if (target.league_name !== LEAGUE_NAME) addError(target, 'league_name mismatch');
        if (target.season !== SEASON) addError(target, 'season mismatch');
        if (target.preflight_status !== 'hash_baseline_ready') {
            addError(target, 'preflight_status must be hash_baseline_ready');
        }
        if (!/^[a-f0-9]{64}$/.test(target.baseline_hash)) {
            addError(target, 'baseline_hash must be 64 hex');
        }
        if (target.failure_reason) addError(target, 'failure_reason must be empty');
        if (target.write_status !== 'not_started') addError(target, 'write_status must be not_started');
    }

    return {
        candidates,
        targetErrors,
        duplicate_external_id_count: countDuplicateExtras(candidates.map(target => target.external_id)),
        duplicate_match_id_count: countDuplicateExtras(candidates.map(target => target.match_id)),
        invalid_hash_count: candidates.filter(target => !/^[a-f0-9]{64}$/.test(target.baseline_hash)).length,
        invalid_identity_count: candidates.filter(target => {
            const expectedMatchId = `${LEAGUE_ID}_${SEASON_COMPACT}_${target.external_id}`;
            return !/^\d+$/.test(target.external_id) || target.match_id !== expectedMatchId;
        }).length,
    };
}

function normalizeSchemaDefinitions(rows = []) {
    return (Array.isArray(rows) ? rows : [])
        .map(row => [row.conname, row.contype, row.definition].filter(Boolean).join(' '))
        .map(value => normalizeText(value).replace(/\s+/g, ' ').toLowerCase())
        .filter(Boolean);
}

function buildSchemaReadiness(rows = []) {
    const definitions = normalizeSchemaDefinitions(rows);
    const hasVersionedUnique = definitions.some(definition =>
        /unique\s*\(\s*match_id\s*,\s*data_version\s*\)/i.test(definition)
    );
    const hasOldUniqueMatchId = definitions.some(definition => /unique\s*\(\s*match_id\s*\)/i.test(definition));
    const constraintNames = (Array.isArray(rows) ? rows : []).map(row => normalizeText(row.conname)).filter(Boolean);
    return {
        raw_match_data_unique_match_id_data_version_present: hasVersionedUnique,
        raw_match_data_old_unique_match_id_absent: !hasOldUniqueMatchId,
        raw_match_data_constraint_names: constraintNames,
        raw_match_data_fk_present: definitions.some(definition => definition.includes('foreign key')),
        raw_match_data_check_constraints_present: definitions.some(definition => definition.includes('check')),
        ready: hasVersionedUnique && !hasOldUniqueMatchId,
    };
}

function assertNoDuplicateExistingRows(rows = []) {
    const seen = new Set();
    for (const row of Array.isArray(rows) ? rows : []) {
        const key = `${normalizeText(row.match_id)}\u0000${normalizeText(row.data_version)}`;
        if (seen.has(key)) throw new Error(`DUPLICATE_EXISTING_RAW_VERSION:${normalizeText(row.match_id)}`);
        seen.add(key);
    }
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

function buildTargetWriteDecision(target = {}, existingRows = [], candidateErrors = []) {
    const existingVersions = summarizeExistingVersions(existingRows);
    const existingV2Rows = existingRows.filter(row => normalizeText(row.data_version) === RAW_VERSION);
    if (candidateErrors.length > 0) {
        return {
            external_id: target.external_id,
            match_id: target.match_id,
            home_team: target.home_team,
            away_team: target.away_team,
            kickoff_time: target.kickoff_time || target.match_date || null,
            status: target.status || null,
            baseline_hash: target.baseline_hash || null,
            existing_versions: existingVersions,
            existing_v2_count: existingV2Rows.length,
            write_eligibility_status: 'blocked',
            planned_write_action: 'none',
            write_plan_status: 'blocked',
            failure_reason: candidateErrors.join(';'),
        };
    }
    if (existingV2Rows.length > 0) {
        return {
            external_id: target.external_id,
            match_id: target.match_id,
            home_team: target.home_team,
            away_team: target.away_team,
            kickoff_time: target.kickoff_time || target.match_date || null,
            status: target.status || null,
            baseline_hash: target.baseline_hash,
            existing_versions: existingVersions,
            existing_v2_count: existingV2Rows.length,
            existing_v2_data_hash: normalizeText(existingV2Rows[0].data_hash).toLowerCase() || null,
            write_eligibility_status: 'skipped_existing_v2',
            planned_write_action: 'skip_existing_v2',
            write_plan_status: 'skipped_existing_v2',
            failure_reason: null,
        };
    }
    return {
        external_id: target.external_id,
        match_id: target.match_id,
        home_team: target.home_team,
        away_team: target.away_team,
        kickoff_time: target.kickoff_time || target.match_date || null,
        status: target.status || null,
        baseline_hash: target.baseline_hash,
        existing_versions: existingVersions,
        existing_v2_count: 0,
        write_eligibility_status: 'eligible_insert',
        planned_write_action: 'insert_fotmob_pageprops_v2_after_l2v_hash_gate',
        write_plan_status: 'eligible_for_insert',
        failure_reason: null,
    };
}

function computeWritePlanStatus({ eligibleInsertCount, skippedExistingV2Count, blockedCount } = {}) {
    if (blockedCount > 0) {
        return {
            writePlanStatus: 'blocked',
            requiredNextStep: 'review_blocked_targets_before_write_authorization',
        };
    }
    if (eligibleInsertCount === TARGET_COUNT && skippedExistingV2Count === 0) {
        return {
            writePlanStatus: 'ready_for_final_authorization',
            requiredNextStep: 'single_league_small_batch_controlled_pageprops_v2_write_execution',
        };
    }
    return {
        writePlanStatus: 'review_existing_v2_before_final_authorization',
        requiredNextStep: 'review_existing_v2_targets_before_write_execution',
    };
}

function buildFutureControlledWritePlan() {
    return {
        phase: 'PHASE5_21L2V_SINGLE_LEAGUE_SMALL_BATCH_CONTROLLED_PAGEPROPS_V2_WRITE_EXECUTION',
        final_db_write_confirmation_required: true,
        required_flags: {
            final_db_write_confirmation: 'yes',
            allow_db_write: 'yes',
            allow_raw_match_data_write: 'yes',
            allow_controlled_write: 'yes',
        },
        recapture_before_write: true,
        hash_strategy: HASH_STRATEGY,
        hash_gate: 'compute stable_pageprops_payload_v1 and compare with manifest baseline_hash before insert',
        write_only_matching_targets: true,
        transaction_policy: 'single_transaction_for_authorized_batch_unless_future_scope_reduces_target_set',
        conflict_policy: 'INSERT ... ON CONFLICT (match_id, data_version) DO NOTHING with post-write verification',
        data_version: RAW_VERSION,
        do_not_rewrite_v1: true,
        do_not_write_matches: true,
        do_not_write_bookmaker_odds_history: true,
        do_not_parser_features_training: true,
        post_write_verification: [
            'verify raw_match_data count reaches expected_raw_match_data_after',
            'verify protected tables unchanged',
            'verify each inserted data_hash equals manifest baseline_hash',
        ],
    };
}

function buildWritePlanningPayload({
    input = {},
    manifest = {},
    protectedTableRowsBefore = [],
    protectedTableRowsAfter = [],
    constraintRows = [],
    existingRows = [],
    generatedAt = null,
} = {}) {
    const dbBaselineBefore = buildProtectedTableBaseline(protectedTableRowsBefore);
    const dbBaselineAfter = buildProtectedTableBaseline(
        protectedTableRowsAfter.length > 0 ? protectedTableRowsAfter : protectedTableRowsBefore
    );
    const beforeErrors = validateProtectedTableBaseline(dbBaselineBefore);
    const afterErrors = validateProtectedTableBaseline(dbBaselineAfter);
    if (beforeErrors.length > 0 || afterErrors.length > 0) {
        return buildFailurePayload({
            input,
            reason: `DB_BASELINE_INVALID:${[...beforeErrors, ...afterErrors].join(';')}`,
            errors: [...beforeErrors, ...afterErrors],
            dbBaselineBefore,
        });
    }
    const structureValidation = validateManifestStructure(manifest);
    if (!structureValidation.ok) {
        return buildFailurePayload({
            input,
            reason: `MANIFEST_INVALID:${structureValidation.errors.join(';')}`,
            errors: structureValidation.errors,
            dbBaselineBefore,
        });
    }

    assertNoDuplicateExistingRows(existingRows);
    const candidateValidation = validateCandidateTargets(manifest);
    const groupedRows = groupRowsByMatchId(existingRows);
    const targetSummaries = candidateValidation.candidates.map(target =>
        buildTargetWriteDecision(
            target,
            groupedRows.get(target.match_id) || [],
            candidateValidation.targetErrors.get(target.external_id) || []
        )
    );
    const eligibleInsertCount = targetSummaries.filter(
        target => target.write_eligibility_status === 'eligible_insert'
    ).length;
    const skippedExistingV2Count = targetSummaries.filter(
        target => target.write_eligibility_status === 'skipped_existing_v2'
    ).length;
    const blockedCount = targetSummaries.filter(target => target.write_eligibility_status === 'blocked').length;
    const existingV2Count = targetSummaries.reduce((sum, target) => sum + Number(target.existing_v2_count || 0), 0);
    const schemaReadiness = buildSchemaReadiness(constraintRows);
    const schemaBlockedCount = schemaReadiness.ready ? 0 : 1;
    const result = computeWritePlanStatus({
        eligibleInsertCount,
        skippedExistingV2Count,
        blockedCount: blockedCount + schemaBlockedCount,
    });
    const currentRawMatchDataCount = Number(dbBaselineBefore.raw_match_data || 0);
    const expectedRawMatchDataAfter = currentRawMatchDataCount + eligibleInsertCount;

    return {
        phase: PHASE,
        ok: result.writePlanStatus === 'ready_for_final_authorization',
        planning_only: true,
        source: SOURCE,
        route: ROUTE,
        league_id: LEAGUE_ID,
        league_name: LEAGUE_NAME,
        season: SEASON,
        manifest_path: input.manifest || MANIFEST_PATH,
        report_path: REPORT_PATH,
        batch_id: BATCH_ID,
        raw_version: RAW_VERSION,
        hash_strategy: HASH_STRATEGY,
        known_completed_targets_count: manifest.known_completed_targets?.length || 0,
        candidate_targets_count: manifest.candidate_targets?.length || 0,
        baseline_hash_populated_count: candidateValidation.candidates.filter(target =>
            /^[a-f0-9]{64}$/.test(target.baseline_hash)
        ).length,
        preflight_status_distribution: candidateValidation.candidates.reduce((acc, target) => {
            acc[target.preflight_status || 'missing'] = (acc[target.preflight_status || 'missing'] || 0) + 1;
            return acc;
        }, {}),
        target_population_status_before: manifest.target_population_status,
        target_population_status_after: manifest.target_population_status,
        write_authorization_status: 'pending_final_db_write_confirmation',
        write_plan_status: result.writePlanStatus,
        required_next_step: result.requiredNextStep,
        candidate_count: candidateValidation.candidates.length,
        eligible_insert_count: eligibleInsertCount,
        skipped_existing_v2_count: skippedExistingV2Count,
        blocked_count: blockedCount + schemaBlockedCount,
        invalid_hash_count: candidateValidation.invalid_hash_count,
        invalid_identity_count: candidateValidation.invalid_identity_count,
        duplicate_external_id_count: candidateValidation.duplicate_external_id_count,
        duplicate_match_id_count: candidateValidation.duplicate_match_id_count,
        existing_v2_count: existingV2Count,
        existing_candidate_raw_rows_count: existingRows.length,
        existing_candidate_v1_rows_count: existingRows.filter(
            row => normalizeText(row.data_version) === 'fotmob_html_hyd_v1'
        ).length,
        would_insert_count: eligibleInsertCount,
        would_update_count: 0,
        would_skip_count: skippedExistingV2Count + blockedCount + schemaBlockedCount,
        current_raw_match_data_count: currentRawMatchDataCount,
        expected_raw_match_data_after: expectedRawMatchDataAfter,
        schema_readiness: schemaReadiness,
        future_controlled_write_plan: buildFutureControlledWritePlan(),
        target_summaries: targetSummaries,
        db_baseline_before: dbBaselineBefore,
        db_baseline_after: dbBaselineAfter,
        db_row_counts_unchanged: JSON.stringify(dbBaselineBefore) === JSON.stringify(dbBaselineAfter),
        generated_at: generatedAt,
        network_access_executed: false,
        match_detail_fetch_executed: false,
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
        full_raw_data_printed: false,
        full_pageprops_printed: false,
        full_source_body_printed: false,
        browser_used: false,
        proxy_used: false,
        invented_targets: false,
        fabricated_external_ids: false,
    };
}

function updateManifestWithWritePlan(manifest = {}, payload = {}, generatedAt = null) {
    const updated = jsonClone(manifest);
    const byExternalId = new Map((payload.target_summaries || []).map(target => [target.external_id, target]));
    updated.candidate_targets = updated.candidate_targets.map(target => {
        const summary = byExternalId.get(normalizeText(target.external_id));
        if (!summary) return target;
        return {
            ...target,
            existing_versions: summary.existing_versions || target.existing_versions || [],
            write_authorization_status: 'pending_final_db_write_confirmation',
            write_plan_status: summary.write_plan_status,
            write_eligibility_status: summary.write_eligibility_status,
            planned_write_action: summary.planned_write_action,
            write_status: 'not_started',
            write_attempt_count: Number(target.write_attempt_count || 0),
            failure_reason: summary.failure_reason || null,
            required_next_step:
                summary.write_eligibility_status === 'eligible_insert'
                    ? 'single_league_small_batch_controlled_pageprops_v2_write_execution'
                    : 'review_before_write_execution',
            updated_at: generatedAt,
        };
    });
    updated.write_authorization_status = 'pending_final_db_write_confirmation';
    updated.write_plan_status = payload.write_plan_status;
    updated.eligible_insert_count = payload.eligible_insert_count;
    updated.skipped_existing_v2_count = payload.skipped_existing_v2_count;
    updated.write_planning_blocked_count = payload.blocked_count;
    updated.existing_v2_count = payload.existing_v2_count;
    updated.would_insert_count = payload.would_insert_count;
    updated.would_update_count = payload.would_update_count;
    updated.would_skip_count = payload.would_skip_count;
    updated.expected_raw_match_data_after = payload.expected_raw_match_data_after;
    updated.required_next_step = payload.required_next_step;
    updated.single_league_pageprops_v2_write_planning_result = {
        phase: PHASE,
        generated_at: generatedAt,
        candidate_count: payload.candidate_count,
        eligible_insert_count: payload.eligible_insert_count,
        skipped_existing_v2_count: payload.skipped_existing_v2_count,
        blocked_count: payload.blocked_count,
        invalid_hash_count: payload.invalid_hash_count,
        invalid_identity_count: payload.invalid_identity_count,
        duplicate_external_id_count: payload.duplicate_external_id_count,
        duplicate_match_id_count: payload.duplicate_match_id_count,
        existing_v2_count: payload.existing_v2_count,
        would_insert_count: payload.would_insert_count,
        would_update_count: payload.would_update_count,
        would_skip_count: payload.would_skip_count,
        expected_raw_match_data_after: payload.expected_raw_match_data_after,
        write_authorization_status: payload.write_authorization_status,
        write_plan_status: payload.write_plan_status,
        required_next_step: payload.required_next_step,
        no_db_write: true,
        no_network: true,
        no_match_detail_fetch: true,
        no_parser_features_training: true,
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

function markdownTableRow(values = []) {
    return `| ${values.map(value => normalizeText(value)).join(' | ')} |`;
}

function buildReport(payload = {}) {
    const db = payload.db_baseline_after || payload.db_baseline_before || {};
    const schema = payload.schema_readiness || {};
    return [
        '# Single-League pageProps v2 Controlled Write Planning - Phase 5.21L2U',
        '',
        '## 1. Executive summary',
        '',
        '- L2T generated baseline hashes for 50 real Ligue 1 2025/2026 targets.',
        '- L2U performs controlled write authorization / planning only.',
        '- No DB write, no network, no match detail fetch, and no parser/features/training were executed.',
        '- Real write execution must wait for Phase 5.21L2V with separate final DB-write authorization.',
        '',
        '## 2. Current DB baseline',
        '',
        markdownTableRow(['table', 'rows']),
        markdownTableRow(['---', '---']),
        ...PROTECTED_TABLES.map(table => markdownTableRow([table, db[table]])),
        '',
        '- protected tables with existing rows: 2 (`l3_features`, `match_features_training`)',
        '',
        '## 3. Manifest input summary',
        '',
        `- manifest path: \`${payload.manifest_path}\``,
        `- known_completed_targets=${payload.known_completed_targets_count}`,
        `- candidate_targets=${payload.candidate_targets_count}`,
        `- baseline_hash populated count=${payload.baseline_hash_populated_count}`,
        `- preflight_status distribution: \`${JSON.stringify(payload.preflight_status_distribution || {})}\``,
        `- target_population_status before planning: \`${payload.target_population_status_before}\``,
        '',
        '## 4. Schema / constraint readiness',
        '',
        `- raw_match_data UNIQUE(match_id,data_version) present: ${schema.raw_match_data_unique_match_id_data_version_present}`,
        `- old UNIQUE(match_id) absent: ${schema.raw_match_data_old_unique_match_id_absent}`,
        `- FK/check constraints still present: ${schema.raw_match_data_fk_present && schema.raw_match_data_check_constraints_present}`,
        `- raw_match_data current count=${payload.current_raw_match_data_count}`,
        '',
        '## 5. Write eligibility audit',
        '',
        `- candidate_count=${payload.candidate_count}`,
        `- eligible_insert_count=${payload.eligible_insert_count}`,
        `- skipped_existing_v2_count=${payload.skipped_existing_v2_count}`,
        `- blocked_count=${payload.blocked_count}`,
        `- invalid_hash_count=${payload.invalid_hash_count}`,
        `- invalid_identity_count=${payload.invalid_identity_count}`,
        `- duplicate_external_id_count=${payload.duplicate_external_id_count}`,
        `- duplicate_match_id_count=${payload.duplicate_match_id_count}`,
        `- existing_v2_count=${payload.existing_v2_count}`,
        `- would_insert_count=${payload.would_insert_count}`,
        `- would_update_count=${payload.would_update_count}`,
        `- expected_raw_match_data_after=${payload.expected_raw_match_data_after}`,
        '',
        '## 6. Future controlled write plan',
        '',
        '- L2V must require `FINAL_DB_WRITE_CONFIRMATION=yes`.',
        '- L2V must require `ALLOW_DB_WRITE=yes` and `ALLOW_RAW_MATCH_DATA_WRITE=yes`.',
        '- Recapture each target live pageProps, compute `stable_pageprops_payload_v1`, and compare with manifest `baseline_hash`.',
        '- Only matching targets may be inserted as `data_version=fotmob_pageprops_v2`.',
        '- Use a controlled transaction and `(match_id,data_version)` conflict policy.',
        '- Do not rewrite v1, write `matches`, write bookmaker odds, or run parser/features/training.',
        `- Post-write verification should confirm raw_match_data ${payload.current_raw_match_data_count} -> ${payload.expected_raw_match_data_after} if ${payload.would_insert_count} inserts are authorized.`,
        '',
        '## 7. Manifest update result',
        '',
        '- manifest updated: yes',
        `- write_authorization_status=\`${payload.write_authorization_status}\``,
        `- write_plan_status=\`${payload.write_plan_status}\``,
        `- eligible_insert_count=${payload.eligible_insert_count}`,
        `- expected_raw_match_data_after=${payload.expected_raw_match_data_after}`,
        `- required_next_step=\`${payload.required_next_step}\``,
        '',
        '## 8. DB safety result',
        '',
        `- matches=${db.matches}`,
        `- raw_match_data=${db.raw_match_data}`,
        `- bookmaker_odds_history=${db.bookmaker_odds_history}`,
        `- l3_features=${db.l3_features}`,
        `- match_features_training=${db.match_features_training}`,
        `- predictions=${db.predictions}`,
        `- row counts unchanged: ${payload.db_row_counts_unchanged}`,
        '',
        '## 9. Verification results',
        '',
        '- To be completed after local tests, PR CI, and main push CI.',
        '',
        '## 10. Recommended next phase',
        '',
        '- Phase 5.21L2V: single-league small-batch controlled pageProps v2 write execution.',
        '- Requirements: explicit final DB-write authorization, no parser/features/training, use manifest baseline hashes, recapture and compare before insert, controlled transaction, no full body/json/pageProps print/save, and post-write verification.',
        '',
        '## 11. Explicit non-execution',
        '',
        '- no DB writes',
        '- no raw_match_data writes',
        '- no bookmaker_odds_history writes',
        '- no network / FotMob access',
        '- no match detail pageProps fetch',
        '- no controlled write',
        '- no schema migration',
        '- no matches writes',
        '- no parser implementation',
        '- no feature extraction',
        '- no l3_features write',
        '- no match_features_training write',
        '- no training/prediction',
        '- no browser/proxy/captcha bypass',
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
        planning_only: true,
        source: SOURCE,
        route: ROUTE,
        manifest_path: input.manifest || MANIFEST_PATH,
        batch_id: BATCH_ID,
        failure_reason: reason,
        errors,
        db_baseline_before: dbBaselineBefore,
        network_access_executed: false,
        match_detail_fetch_executed: false,
        db_write_executed: false,
        raw_match_data_write_executed: false,
        controlled_write_executed: false,
        schema_migration_executed: false,
        parser_implementation_executed: false,
        feature_extraction_executed: false,
        training_executed: false,
        prediction_executed: false,
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

async function runCli(argv = process.argv.slice(2), dependencies = {}) {
    const parsed = Array.isArray(argv) ? parseArgs(argv) : argv;
    const validation = validatePlanInput(parsed);
    const output = dependencies.output || (payload => process.stdout.write(`${JSON.stringify(payload, null, 2)}\n`));
    if (!validation.ok) {
        const payload = buildFailurePayload({
            input: normalizePlanInput(parsed),
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
        dependencies.constraintRows ||
        dependencies.protectedTableRowsBefore ||
        dependencies.protectedTableRowsAfter
            ? null
            : createDefaultPool();
    const client = dependencies.client || pool;
    try {
        const manifest = dependencies.manifest || readManifestFile(input.manifest);
        const structureValidation = validateManifestStructure(manifest);
        if (!structureValidation.ok) {
            const payload = buildFailurePayload({
                input,
                reason: `MANIFEST_INVALID:${structureValidation.errors.join(';')}`,
                errors: structureValidation.errors,
            });
            output(payload);
            return { status: 1, payload };
        }
        const candidates = manifest.candidate_targets.map(normalizeCandidateTarget);
        const candidateMatchIds = candidates.map(target => target.match_id);
        const protectedTableRowsBefore =
            dependencies.protectedTableRowsBefore || (await loadProtectedTableBaselineRows(client));
        const constraintRows = dependencies.constraintRows || (await loadRawMatchDataConstraints(client));
        const existingRows = dependencies.existingRows || (await loadExistingRawVersions(client, candidateMatchIds));
        const protectedTableRowsAfter =
            dependencies.protectedTableRowsAfter || (await loadProtectedTableBaselineRows(client));
        const payload = buildWritePlanningPayload({
            input,
            manifest,
            protectedTableRowsBefore,
            protectedTableRowsAfter,
            constraintRows,
            existingRows,
            generatedAt,
        });
        if (payload.phase && !payload.failure_reason) {
            const updatedManifest = updateManifestWithWritePlan(manifest, payload, generatedAt);
            if (dependencies.writeManifest !== false) {
                (dependencies.writeManifestFile || writeJsonFile)(input.manifest, updatedManifest);
            }
            const reportMarkdown = buildReport(payload);
            if (dependencies.writeReport !== false) {
                (dependencies.writeReportFile || writeReportFile)(REPORT_PATH, reportMarkdown);
            }
            payload.manifest_updated = dependencies.writeManifest !== false;
            payload.report_updated = dependencies.writeReport !== false;
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
    RAW_VERSION,
    HASH_STRATEGY,
    TARGET_COUNT,
    parseArgs,
    normalizeBooleanFlag,
    validatePlanInput,
    validateManifestStructure,
    validateCandidateTargets,
    buildProtectedTableBaseline,
    buildSchemaReadiness,
    buildTargetWriteDecision,
    buildWritePlanningPayload,
    updateManifestWithWritePlan,
    buildReport,
    queryReadOnly,
    loadProtectedTableBaselineRows,
    loadRawMatchDataConstraints,
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
