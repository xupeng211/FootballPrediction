#!/usr/bin/env node
/* eslint-disable complexity, max-lines, max-statements */
'use strict';

const fs = require('node:fs');
const path = require('node:path');
const { assertDbWriteAllowed } = require('./helpers/db_write_guard');

const PHASE = 'PHASE5_21L2V1_CONTROLLED_MATCHES_IDENTITY_SEED_EXECUTION';
const MANIFEST_PATH = 'docs/_manifests/fotmob_pageprops_v2_ligue1_2025_2026_profile_001.proposal.json';
const REPORT_PATH = 'docs/_reports/CONTROLLED_MATCHES_IDENTITY_SEED_EXECUTION_PHASE5_21L2V1.md';
const SOURCE = 'fotmob';
const LEAGUE_ID = 53;
const LEAGUE_NAME = 'Ligue 1';
const SEASON = '2025/2026';
const SEASON_COMPACT = '20252026';
const BATCH_ID = 'fotmob-pageprops-v2-ligue1-2025-2026-profile-001';
const TARGET_COUNT = 50;
const KNOWN_COMPLETED_COUNT = 8;
const NEXT_STEP_AFTER_SUCCESS = 'post_seed_matches_identity_verification_raw_write_retry_readiness_audit';
const EXPECTED_BEFORE_COUNTS = Object.freeze({
    matches: 10,
    bookmaker_odds_history: 2,
    raw_match_data: 18,
    l3_features: 2,
    match_features_training: 2,
    predictions: 2,
});
const EXPECTED_AFTER_COUNTS = Object.freeze({
    ...EXPECTED_BEFORE_COUNTS,
    matches: 60,
});
const REQUIRED_YES_FLAGS = Object.freeze(['finalDbWriteConfirmation', 'allowDbWrite', 'allowMatchesWrite']);
const REQUIRED_NO_FLAGS = Object.freeze([
    'allowRawMatchDataWrite',
    'allowBookmakerOddsWrite',
    'allowFeatureWrite',
    'allowNetwork',
    'allowMatchDetailFetch',
    'allowControlledRawWrite',
    'allowSchemaMigration',
    'allowParserImplementation',
    'allowFeatureExtraction',
    'allowTraining',
    'allowPrediction',
]);
const BLOCKED_TRUE_FLAGS = Object.freeze(['allowOddsWrite']);
const REQUIRED_MATCHES_COLUMNS = Object.freeze(['match_id', 'league_name', 'season', 'home_team', 'away_team']);
const PREFERRED_INSERT_COLUMNS = Object.freeze([
    'match_id',
    'external_id',
    'league_name',
    'season',
    'home_team',
    'away_team',
    'match_date',
    'status',
    'is_finished',
    'data_source',
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
        batchId: null,
        targetCount: null,
        finalDbWriteConfirmation: null,
        allowDbWrite: null,
        allowMatchesWrite: null,
        allowRawMatchDataWrite: null,
        allowBookmakerOddsWrite: null,
        allowFeatureWrite: null,
        allowNetwork: null,
        allowMatchDetailFetch: null,
        allowControlledRawWrite: null,
        allowSchemaMigration: null,
        allowParserImplementation: null,
        allowFeatureExtraction: null,
        allowTraining: null,
        allowPrediction: null,
        allowOddsWrite: false,
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

function requireExact(errors, actual, expected, name) {
    if (!normalizeText(actual)) {
        errors.push(`missing ${name}=${expected}`);
        return;
    }
    if (normalizeText(actual) !== expected) errors.push(`${name} must be ${expected}`);
}

function requireYes(errors, value, name) {
    if (value === true) return;
    if (value === false) {
        errors.push(`${name}=yes is required for Phase 5.21L2V1`);
        return;
    }
    errors.push(`missing ${name}=yes`);
}

function requireNo(errors, value, name) {
    if (value === false) return;
    if (value === true) {
        errors.push(`${name}=yes is blocked in Phase 5.21L2V1`);
        return;
    }
    errors.push(`missing ${name}=no`);
}

function validateExecuteInput(input = {}) {
    const errors = [];
    if (Array.isArray(input.unknown) && input.unknown.length > 0) {
        errors.push(`unknown arguments: ${input.unknown.join(',')}`);
    }
    requireExact(errors, input.manifest, MANIFEST_PATH, 'manifest');
    requireExact(errors, input.source, SOURCE, 'source');
    if (parseInteger(input.leagueId) !== LEAGUE_ID) errors.push('league-id must be 53');
    requireExact(errors, input.leagueName, LEAGUE_NAME, 'league-name');
    requireExact(errors, input.season, SEASON, 'season');
    requireExact(errors, input.batchId, BATCH_ID, 'batch-id');
    if (parseInteger(input.targetCount) !== TARGET_COUNT) errors.push(`target-count must be ${TARGET_COUNT}`);
    for (const flag of REQUIRED_YES_FLAGS) requireYes(errors, input[flag], flagName(flag));
    for (const flag of REQUIRED_NO_FLAGS) requireNo(errors, input[flag], flagName(flag));
    for (const flag of BLOCKED_TRUE_FLAGS) {
        if (input[flag] === true) errors.push(`${flagName(flag)}=yes is blocked in Phase 5.21L2V1`);
    }
    return {
        ok: errors.length === 0,
        errors,
        value: {
            manifest: normalizeText(input.manifest),
            source: SOURCE,
            leagueId: LEAGUE_ID,
            leagueName: LEAGUE_NAME,
            season: SEASON,
            batchId: BATCH_ID,
            targetCount: TARGET_COUNT,
        },
    };
}

function readJsonFile(filePath) {
    return JSON.parse(fs.readFileSync(path.resolve(filePath), 'utf8'));
}

function writeJsonFile(filePath, data) {
    fs.writeFileSync(path.resolve(filePath), `${JSON.stringify(data, null, 2)}\n`, 'utf8');
}

function writeReportFile(filePath, content) {
    fs.mkdirSync(path.dirname(path.resolve(filePath)), { recursive: true });
    fs.writeFileSync(path.resolve(filePath), content, 'utf8');
}

function normalizeComparableTimestamp(value) {
    const raw = normalizeText(value);
    if (!raw) return '';
    if (value instanceof Date && !Number.isNaN(value.getTime())) return value.toISOString();
    const timestamp = Date.parse(raw);
    if (Number.isNaN(timestamp)) return raw;
    return new Date(timestamp).toISOString();
}

function hasInventedMarker(target = {}) {
    return [
        target.invented_external_id,
        target.invented_target,
        target.fake_target,
        target.fabricated_external_id,
        target.synthetic_target,
    ].some(value => normalizeBooleanFlag(value, false) === true);
}

function normalizeCandidateTarget(target = {}) {
    return {
        ...target,
        match_id: normalizeText(target.match_id),
        external_id: normalizeText(target.external_id),
        league_id: Number(target.league_id),
        league_name: normalizeText(target.league_name),
        season: normalizeText(target.season),
        home_team: normalizeText(target.home_team),
        away_team: normalizeText(target.away_team),
        match_date: normalizeComparableTimestamp(target.match_date || target.kickoff_time),
        status: normalizeText(target.status),
    };
}

function getStatusDistribution(targets = [], field = 'matches_seed_status') {
    return targets.reduce((acc, target) => {
        const status = normalizeText(target[field]) || 'missing';
        acc[status] = (acc[status] || 0) + 1;
        return acc;
    }, {});
}

function validateManifestForExecution(manifest = {}) {
    const errors = [];
    if (normalizeText(manifest.schema_version) !== 'target_manifest_proposal_v1') {
        errors.push('manifest schema_version must be target_manifest_proposal_v1');
    }
    if (normalizeText(manifest.batch_id) !== BATCH_ID) errors.push('manifest batch_id mismatch');
    if (normalizeLower(manifest.source) !== SOURCE) errors.push('manifest source mismatch');
    if (Number(manifest.league?.league_id) !== LEAGUE_ID) errors.push('manifest league_id mismatch');
    if (normalizeText(manifest.league?.league_name) !== LEAGUE_NAME) errors.push('manifest league_name mismatch');
    if (normalizeText(manifest.league?.season) !== SEASON) errors.push('manifest season mismatch');
    if (
        !Array.isArray(manifest.known_completed_targets) ||
        manifest.known_completed_targets.length !== KNOWN_COMPLETED_COUNT
    ) {
        errors.push(`manifest known_completed_targets must contain ${KNOWN_COMPLETED_COUNT} targets`);
    }
    if (!Array.isArray(manifest.candidate_targets) || manifest.candidate_targets.length !== TARGET_COUNT) {
        errors.push(`manifest candidate_targets must contain ${TARGET_COUNT} targets`);
    }
    if (normalizeText(manifest.matches_identity_seed_plan_status) !== 'ready_for_final_authorization') {
        errors.push('matches_identity_seed_plan_status must be ready_for_final_authorization');
    }
    if (normalizeText(manifest.matches_identity_seed_authorization_status) !== 'pending_final_db_write_confirmation') {
        errors.push('matches_identity_seed_authorization_status must be pending_final_db_write_confirmation');
    }
    if (Number(manifest.eligible_matches_insert_count) !== TARGET_COUNT) {
        errors.push(`eligible_matches_insert_count must be ${TARGET_COUNT}`);
    }
    if (normalizeText(manifest.required_next_step) !== 'controlled_matches_identity_seed_execution') {
        errors.push('required_next_step must be controlled_matches_identity_seed_execution');
    }
    return { ok: errors.length === 0, errors };
}

function validateCandidateTargets(candidates = []) {
    const normalizedCandidates = candidates.map(normalizeCandidateTarget);
    const errors = [];
    const matchIdCounts = new Map();
    const externalIdCounts = new Map();
    const invalidByMatchId = new Map();

    for (const target of normalizedCandidates) {
        const targetErrors = [];
        if (!target.match_id) targetErrors.push('missing match_id');
        if (!/^\d+$/.test(target.external_id)) targetErrors.push('external_id must be numeric');
        if (target.match_id !== `${LEAGUE_ID}_${SEASON_COMPACT}_${target.external_id}`) {
            targetErrors.push('match_id convention mismatch');
        }
        if (target.league_id !== LEAGUE_ID) targetErrors.push('league_id mismatch');
        if (target.league_name !== LEAGUE_NAME) targetErrors.push('league_name mismatch');
        if (target.season !== SEASON) targetErrors.push('season mismatch');
        if (!target.home_team) targetErrors.push('missing home_team');
        if (!target.away_team) targetErrors.push('missing away_team');
        if (!target.match_date) targetErrors.push('missing match_date/kickoff_time');
        if (!target.status) targetErrors.push('missing status');
        if (normalizeText(target.status) !== normalizeLower(target.status)) {
            targetErrors.push('status must be lowercase');
        }
        if (hasInventedMarker(target)) targetErrors.push('invented/fake marker present');
        if (normalizeText(target.matches_identity_seed_status) !== 'eligible_matches_insert') {
            targetErrors.push('matches_identity_seed_status must be eligible_matches_insert');
        }
        matchIdCounts.set(target.match_id, (matchIdCounts.get(target.match_id) || 0) + 1);
        externalIdCounts.set(target.external_id, (externalIdCounts.get(target.external_id) || 0) + 1);
        if (targetErrors.length > 0) {
            invalidByMatchId.set(target.match_id || `missing:${invalidByMatchId.size}`, targetErrors);
            errors.push(`${target.match_id || target.external_id || 'candidate'}: ${targetErrors.join(';')}`);
        }
    }

    const duplicateMatchIds = [...matchIdCounts.entries()].filter(([, count]) => count > 1).map(([value]) => value);
    const duplicateExternalIds = [...externalIdCounts.entries()]
        .filter(([, count]) => count > 1)
        .map(([value]) => value);
    for (const matchId of duplicateMatchIds) errors.push(`duplicate match_id ${matchId}`);
    for (const externalId of duplicateExternalIds) errors.push(`duplicate external_id ${externalId}`);

    return {
        ok: errors.length === 0,
        errors,
        candidates: normalizedCandidates,
        invalidByMatchId,
        invalid_identity_count: invalidByMatchId.size,
        duplicate_match_id_count: duplicateMatchIds.length,
        duplicate_external_id_count: duplicateExternalIds.length,
    };
}

function normalizeTableRows(rows = []) {
    return rows.reduce((acc, row) => {
        acc[normalizeText(row.table_name)] = Number(row.rows);
        return acc;
    }, {});
}

function validateExpectedCounts(actual = {}, expected = {}) {
    const errors = [];
    for (const [tableName, expectedRows] of Object.entries(expected)) {
        if (Number(actual[tableName]) !== expectedRows) {
            errors.push(`${tableName}=${actual[tableName]} expected ${expectedRows}`);
        }
    }
    return errors;
}

function parsePipelineStatusesFromConstraint(constraints = []) {
    const constraint = constraints.find(row => normalizeText(row.conname) === 'matches_pipeline_status_valid');
    if (!constraint) return [];
    const definition = normalizeText(constraint.definition);
    const values = [];
    const regex = /'([^']+)'::character varying/g;
    let match = regex.exec(definition);
    while (match) {
        values.push(match[1]);
        match = regex.exec(definition);
    }
    return [...new Set(values)];
}

function buildMatchesSchemaReadiness(columns = [], constraints = []) {
    const columnMap = new Map(columns.map(column => [normalizeText(column.column_name), column]));
    const constraintNames = new Set(constraints.map(row => normalizeText(row.conname)));
    const missingRequiredColumns = REQUIRED_MATCHES_COLUMNS.filter(columnName => !columnMap.has(columnName));
    const insertColumns = PREFERRED_INSERT_COLUMNS.filter(columnName => columnMap.has(columnName));
    const pipelineStatuses = parsePipelineStatusesFromConstraint(constraints);
    const pipelineColumn = columnMap.get('pipeline_status');
    const pipelineHasDefault = Boolean(normalizeText(pipelineColumn?.column_default));
    const pipelineRequiredWithoutDefault = pipelineColumn?.is_nullable === 'NO' && !pipelineHasDefault;
    const pipelineStatusPolicy = {
        column_exists: Boolean(pipelineColumn),
        use_default: Boolean(pipelineColumn && pipelineHasDefault),
        insert_value: null,
        allowed_values: pipelineStatuses,
        ready: true,
        blocked_reason: null,
    };
    if (pipelineRequiredWithoutDefault) {
        if (pipelineStatuses.includes('pending')) {
            pipelineStatusPolicy.insert_value = 'pending';
            insertColumns.push('pipeline_status');
        } else {
            pipelineStatusPolicy.ready = false;
            pipelineStatusPolicy.blocked_reason = 'pipeline_status required but valid value cannot be determined';
        }
    }

    const requiredConstraintNames = [
        'matches_pkey',
        'season_format',
        'status_lowercase',
        'matches_pipeline_status_valid',
        'valid_scores',
    ];
    const missingConstraints = requiredConstraintNames.filter(name => !constraintNames.has(name));
    const primaryKeyMatchIdPresent = constraints.some(
        row =>
            normalizeText(row.conname) === 'matches_pkey' &&
            normalizeText(row.definition).includes('PRIMARY KEY (match_id)')
    );
    if (!primaryKeyMatchIdPresent && !missingConstraints.includes('matches_pkey')) {
        missingConstraints.push('matches_pkey');
    }

    const errors = [];
    if (missingRequiredColumns.length > 0) {
        errors.push(`missing required matches columns: ${missingRequiredColumns.join(',')}`);
    }
    if (missingConstraints.length > 0) {
        errors.push(`missing required matches constraints: ${missingConstraints.join(',')}`);
    }
    if (!pipelineStatusPolicy.ready) errors.push(pipelineStatusPolicy.blocked_reason);
    if (insertColumns.includes('league_id')) errors.push('insert columns must not include league_id');

    return {
        ready: errors.length === 0,
        errors,
        matches_columns: columns,
        matches_constraints: constraints,
        required_columns: REQUIRED_MATCHES_COLUMNS,
        missing_required_columns: missingRequiredColumns,
        insert_columns: insertColumns,
        constraints_checked: requiredConstraintNames,
        missing_constraints: missingConstraints,
        primary_key_match_id_present: primaryKeyMatchIdPresent,
        pipeline_status_policy: pipelineStatusPolicy,
        is_finished_policy: 'true when status=finished, false otherwise',
    };
}

function normalizeExistingMatchRow(row = {}) {
    return {
        match_id: normalizeText(row.match_id),
        external_id: normalizeText(row.external_id),
        league_name: normalizeText(row.league_name),
        season: normalizeText(row.season),
        home_team: normalizeText(row.home_team),
        away_team: normalizeText(row.away_team),
        match_date: normalizeComparableTimestamp(row.match_date),
        status: normalizeLower(row.status),
        is_finished:
            row.is_finished === true ||
            normalizeLower(row.is_finished) === 'true' ||
            normalizeLower(row.is_finished) === 't',
        data_source: normalizeText(row.data_source),
        pipeline_status: normalizeText(row.pipeline_status),
    };
}

function buildIdentityConflictAudit(candidates = [], existingRows = [], candidateValidation = {}) {
    const normalizedExistingRows = existingRows.map(normalizeExistingMatchRow);
    const candidateMatchIds = new Set(candidates.map(target => target.match_id));
    const existingByMatchId = normalizedExistingRows.filter(row => candidateMatchIds.has(row.match_id));
    const externalIdConflicts = [];

    for (const target of candidates) {
        for (const row of normalizedExistingRows) {
            if (row.external_id && row.external_id === target.external_id && row.match_id !== target.match_id) {
                externalIdConflicts.push({
                    external_id: target.external_id,
                    existing_match_id: row.match_id,
                    target_match_id: target.match_id,
                });
            }
        }
    }

    const errors = [];
    if (candidateValidation.invalid_identity_count > 0) errors.push('invalid candidate identity');
    if (candidateValidation.duplicate_match_id_count > 0) errors.push('duplicate candidate match_id');
    if (candidateValidation.duplicate_external_id_count > 0) errors.push('duplicate candidate external_id');
    if (existingByMatchId.length > 0) errors.push('candidate match_id already exists in matches');
    if (externalIdConflicts.length > 0) errors.push('candidate external_id conflicts with existing match_id');

    return {
        ready: errors.length === 0,
        errors,
        existing_matches_count: existingByMatchId.length,
        missing_matches_count: TARGET_COUNT - existingByMatchId.length,
        duplicate_match_id_count: candidateValidation.duplicate_match_id_count,
        duplicate_external_id_count: candidateValidation.duplicate_external_id_count,
        match_id_conflict_count: existingByMatchId.length,
        external_id_conflict_count: externalIdConflicts.length,
        invalid_identity_count: candidateValidation.invalid_identity_count,
        external_id_conflicts: externalIdConflicts,
    };
}

function buildInsertRow(candidate = {}, schemaReadiness = {}) {
    const row = {};
    for (const column of schemaReadiness.insert_columns || []) {
        if (column === 'match_id') row[column] = candidate.match_id;
        if (column === 'external_id') row[column] = candidate.external_id;
        if (column === 'league_name') row[column] = LEAGUE_NAME;
        if (column === 'season') row[column] = SEASON;
        if (column === 'home_team') row[column] = candidate.home_team;
        if (column === 'away_team') row[column] = candidate.away_team;
        if (column === 'match_date') row[column] = candidate.match_date;
        if (column === 'status') row[column] = candidate.status;
        if (column === 'is_finished') row[column] = candidate.status === 'finished';
        if (column === 'data_source') row[column] = SOURCE;
        if (column === 'pipeline_status') {
            row[column] = schemaReadiness.pipeline_status_policy?.insert_value || 'pending';
        }
    }
    return row;
}

function quoteIdentifier(identifier) {
    return `"${normalizeText(identifier).replace(/"/g, '""')}"`;
}

function buildInsertStatement(insertRows = [], insertColumns = []) {
    const values = [];
    const placeholders = insertRows.map(row => {
        const rowPlaceholders = insertColumns.map(column => {
            values.push(row[column]);
            return `$${values.length}`;
        });
        return `(${rowPlaceholders.join(', ')})`;
    });
    const sql = `INSERT INTO matches (${insertColumns.map(quoteIdentifier).join(', ')}) VALUES ${placeholders.join(', ')}`;
    return { sql, values };
}

function buildFailurePayload({ input = {}, reason = 'blocked', errors = [] } = {}) {
    return {
        phase: PHASE,
        ok: false,
        blocked: true,
        blocked_reason: reason,
        errors,
        manifest_path: input.manifest || MANIFEST_PATH,
        db_write_executed: false,
        matches_write_executed: false,
        raw_match_data_write_executed: false,
        network_executed: false,
        match_detail_fetch_executed: false,
        parser_features_training_executed: false,
    };
}

function buildExecutionPlanPayload({
    input = {},
    manifest = {},
    protectedTableRowsBefore = [],
    matchesColumnRows = [],
    matchesConstraintRows = [],
    existingMatchRows = [],
    generatedAt = null,
} = {}) {
    const dbBaselineBefore = normalizeTableRows(protectedTableRowsBefore);
    const baselineErrors = validateExpectedCounts(dbBaselineBefore, EXPECTED_BEFORE_COUNTS);
    const manifestValidation = validateManifestForExecution(manifest);
    const candidateValidation = validateCandidateTargets(
        Array.isArray(manifest.candidate_targets) ? manifest.candidate_targets : []
    );
    const schemaReadiness = buildMatchesSchemaReadiness(matchesColumnRows, matchesConstraintRows);
    const candidates = candidateValidation.candidates;
    const identityAudit = buildIdentityConflictAudit(candidates, existingMatchRows, candidateValidation);
    const gateErrors = [
        ...baselineErrors.map(error => `DB_BASELINE_INVALID:${error}`),
        ...manifestValidation.errors,
        ...candidateValidation.errors,
        ...schemaReadiness.errors,
        ...identityAudit.errors,
    ];
    const insertRows = candidates.map(candidate => buildInsertRow(candidate, schemaReadiness));
    const ready = gateErrors.length === 0 && candidates.length === TARGET_COUNT;

    return {
        phase: PHASE,
        ok: ready,
        blocked: !ready,
        blocked_reason: ready ? null : gateErrors.join(';'),
        generated_at: generatedAt,
        source: SOURCE,
        league_id: LEAGUE_ID,
        league_name: LEAGUE_NAME,
        season: SEASON,
        manifest_path: input.manifest || MANIFEST_PATH,
        report_path: REPORT_PATH,
        batch_id: BATCH_ID,
        db_baseline_before: dbBaselineBefore,
        manifest_gate: {
            ok: manifestValidation.ok,
            errors: manifestValidation.errors,
            candidate_targets: Array.isArray(manifest.candidate_targets) ? manifest.candidate_targets.length : 0,
            known_completed_targets: Array.isArray(manifest.known_completed_targets)
                ? manifest.known_completed_targets.length
                : 0,
            seed_plan_status: manifest.matches_identity_seed_plan_status || null,
            eligible_matches_insert_count: Number(manifest.eligible_matches_insert_count || 0),
        },
        schema_gate: schemaReadiness,
        identity_conflict_gate: identityAudit,
        candidate_count: candidates.length,
        attempted_target_count: TARGET_COUNT,
        insert_rows: insertRows,
        insert_columns: schemaReadiness.insert_columns || [],
        transaction_began: false,
        committed: false,
        rolled_back: false,
        inserted_count: 0,
        updated_count: 0,
        skipped_count: 0,
        blocked_count: ready ? 0 : TARGET_COUNT,
        matches_write_executed: false,
        raw_match_data_write_executed: false,
        odds_write_executed: false,
        features_write_executed: false,
        training_prediction_executed: false,
        network_executed: false,
        match_detail_fetch_executed: false,
        parser_features_training_executed: false,
        required_next_step: ready ? NEXT_STEP_AFTER_SUCCESS : 'review_blocked_matches_identity_seed_execution',
    };
}

function rowsByMatchId(rows = []) {
    const map = new Map();
    for (const row of rows) map.set(normalizeText(row.match_id), normalizeExistingMatchRow(row));
    return map;
}

function verifyInsertedIdentities(candidates = [], insertedRows = []) {
    const byMatchId = rowsByMatchId(insertedRows);
    const mismatches = [];
    for (const candidate of candidates) {
        const row = byMatchId.get(candidate.match_id);
        if (!row) {
            mismatches.push(`${candidate.match_id}: missing inserted row`);
            continue;
        }
        const expected = {
            external_id: candidate.external_id,
            league_name: LEAGUE_NAME,
            season: SEASON,
            home_team: candidate.home_team,
            away_team: candidate.away_team,
            match_date: candidate.match_date,
            status: candidate.status,
        };
        for (const [field, value] of Object.entries(expected)) {
            const actual = row[field];
            if (normalizeText(actual) !== normalizeText(value)) {
                mismatches.push(`${candidate.match_id}: ${field} expected ${value} got ${actual}`);
            }
        }
    }
    return {
        ok: mismatches.length === 0,
        inserted_rows_count: insertedRows.length,
        mismatches,
    };
}

function buildPostWriteVerification({
    protectedTableRowsAfter = [],
    candidateRowsAfter = [],
    duplicateRows = [],
    candidates = [],
} = {}) {
    const dbCountsAfter = normalizeTableRows(protectedTableRowsAfter);
    const countErrors = validateExpectedCounts(dbCountsAfter, EXPECTED_AFTER_COUNTS);
    const identityVerification = verifyInsertedIdentities(candidates, candidateRowsAfter);
    const duplicateCount = duplicateRows.reduce((sum, row) => sum + Number(row.rows || row.count || 0), 0);
    const errors = [...countErrors, ...identityVerification.mismatches];
    if (duplicateCount > 0) errors.push(`duplicate match_id count ${duplicateCount}`);
    return {
        ok: errors.length === 0,
        errors,
        db_counts_after: dbCountsAfter,
        inserted_rows_count: identityVerification.inserted_rows_count,
        identity_fields_match_manifest: identityVerification.ok,
        duplicate_match_id_count: duplicateCount,
    };
}

async function queryReadOnly(client, sql, params = []) {
    const normalized = normalizeText(sql).replace(/\s+/g, ' ');
    if (!/^SELECT\b/i.test(normalized)) throw new Error('READ_ONLY_QUERY_REQUIRED');
    if (/\b(INSERT|UPDATE|DELETE|TRUNCATE|ALTER|DROP|CREATE|LOCK|COPY|GRANT|REVOKE|MERGE)\b/i.test(normalized)) {
        throw new Error('READ_ONLY_QUERY_FORBIDDEN_TOKEN');
    }
    if (/\bFOR\s+(UPDATE|SHARE|NO\s+KEY\s+UPDATE|KEY\s+SHARE)\b/i.test(normalized)) {
        throw new Error('READ_ONLY_QUERY_LOCK_FORBIDDEN');
    }
    return client.query(sql, params);
}

async function loadProtectedTableBaselineRows(client) {
    const result = await queryReadOnly(
        client,
        `
SELECT 'matches' AS table_name, COUNT(*) AS rows FROM matches
UNION ALL
SELECT 'bookmaker_odds_history', COUNT(*) FROM bookmaker_odds_history
UNION ALL
SELECT 'raw_match_data', COUNT(*) FROM raw_match_data
UNION ALL
SELECT 'l3_features', COUNT(*) FROM l3_features
UNION ALL
SELECT 'match_features_training', COUNT(*) FROM match_features_training
UNION ALL
SELECT 'predictions', COUNT(*) FROM predictions
`
    );
    return result.rows || [];
}

async function loadMatchesColumns(client) {
    const result = await queryReadOnly(
        client,
        `
SELECT column_name, data_type, is_nullable, column_default
FROM information_schema.columns
WHERE table_name = $1
ORDER BY ordinal_position
`,
        ['matches']
    );
    return result.rows || [];
}

async function loadMatchesConstraints(client) {
    const result = await queryReadOnly(
        client,
        `
SELECT conname, contype, pg_get_constraintdef(c.oid) AS definition
FROM pg_constraint c
JOIN pg_class t ON c.conrelid = t.oid
WHERE t.relname = $1
ORDER BY conname
`,
        ['matches']
    );
    return result.rows || [];
}

async function loadExistingMatches(client, candidates = []) {
    const matchIds = candidates.map(candidate => candidate.match_id).filter(Boolean);
    const externalIds = candidates.map(candidate => candidate.external_id).filter(Boolean);
    const result = await queryReadOnly(
        client,
        `
SELECT match_id, external_id, league_name, season, home_team, away_team, match_date, status, is_finished, data_source, pipeline_status
FROM matches
WHERE match_id = ANY($1::text[]) OR external_id = ANY($2::text[])
ORDER BY match_id
`,
        [matchIds, externalIds]
    );
    return result.rows || [];
}

async function loadCandidateMatches(client, candidates = []) {
    const matchIds = candidates.map(candidate => candidate.match_id).filter(Boolean);
    const result = await queryReadOnly(
        client,
        `
SELECT match_id, external_id, league_name, season, home_team, away_team, match_date, status, is_finished, data_source, pipeline_status
FROM matches
WHERE match_id = ANY($1::text[])
ORDER BY match_id
`,
        [matchIds]
    );
    return result.rows || [];
}

async function loadDuplicateMatchIds(client) {
    const result = await queryReadOnly(
        client,
        `
SELECT match_id, COUNT(*) AS rows
FROM matches
GROUP BY match_id
HAVING COUNT(*) > 1
`
    );
    return result.rows || [];
}

async function executeTransaction(client, plan = {}) {
    const insertRows = plan.insert_rows || [];
    const insertColumns = plan.insert_columns || [];
    const { sql, values } = buildInsertStatement(insertRows, insertColumns);
    const result = {
        transaction_began: false,
        inserted_count: 0,
        committed: false,
        rolled_back: false,
        error: null,
    };
    await client.query('BEGIN');
    result.transaction_began = true;
    try {
        const insertResult = await client.query(sql, values);
        result.inserted_count = Number(insertResult.rowCount || 0);
        if (result.inserted_count !== TARGET_COUNT) {
            throw new Error(`INSERTED_COUNT_MISMATCH:${result.inserted_count}`);
        }
        const inTransactionCounts = normalizeTableRows(await loadProtectedTableBaselineRows(client));
        const inTransactionErrors = validateExpectedCounts(inTransactionCounts, EXPECTED_AFTER_COUNTS);
        if (inTransactionErrors.length > 0) {
            throw new Error(`POST_INSERT_COUNT_MISMATCH:${inTransactionErrors.join(';')}`);
        }
        await client.query('COMMIT');
        result.committed = true;
    } catch (error) {
        result.error = error.message;
        await client.query('ROLLBACK');
        result.rolled_back = true;
    }
    return result;
}

function updateManifestWithExecution(manifest = {}, payload = {}, generatedAt = null) {
    const status = payload.ok ? 'inserted_matches_identity' : 'blocked_matches_identity_seed_execution';
    const updated = {
        ...manifest,
        matches_identity_seed_execution_status: payload.ok ? 'completed' : 'blocked',
        matches_identity_seed_execution_at: generatedAt,
        matches_identity_seed_inserted_count: payload.inserted_count || 0,
        matches_identity_seed_blocked_count: payload.blocked_count || 0,
        matches_identity_seed_transaction_began: Boolean(payload.transaction_began),
        matches_identity_seed_committed: Boolean(payload.committed),
        matches_identity_seed_rolled_back: Boolean(payload.rolled_back),
        required_next_step: payload.required_next_step,
    };
    updated.candidate_targets = (updated.candidate_targets || []).map(target => ({
        ...target,
        matches_seed_status: status,
        matches_seed_inserted_at: payload.ok ? generatedAt : null,
        matches_seed_failure_reason: payload.ok ? null : payload.blocked_reason,
        required_next_step: payload.required_next_step,
        updated_at: generatedAt,
    }));
    return updated;
}

function renderRows(rows = [], columns = []) {
    if (!Array.isArray(rows) || rows.length === 0) return '- none\n';
    return rows
        .map(row => `- ${columns.map(column => `${column}=${normalizeText(row[column]) || 'null'}`).join(', ')}`)
        .join('\n');
}

function buildReport(payload = {}) {
    const schema = payload.schema_gate || {};
    const conflict = payload.identity_conflict_gate || {};
    const verification = payload.post_write_verification || {};
    return `# Controlled Matches Identity Seed Execution - Phase 5.21L2V1

## 1. Executive summary

- L2V1 is real controlled matches identity seed execution.
- It writes only matches identity rows.
- It does not write raw_match_data, bookmaker_odds_history, features, training, or predictions.
- It does not touch FotMob/network or fetch match details.
- It does not run parser/features/training.
- Purpose: satisfy the matches FK prerequisite that blocked the L2V raw pageProps write.

## 2. Current DB baseline

- matches=${payload.db_baseline_before?.matches}
- raw_match_data=${payload.db_baseline_before?.raw_match_data}
- bookmaker_odds_history=${payload.db_baseline_before?.bookmaker_odds_history}
- l3_features=${payload.db_baseline_before?.l3_features}
- match_features_training=${payload.db_baseline_before?.match_features_training}
- predictions=${payload.db_baseline_before?.predictions}

## 3. Authorization / guardrails

- FINAL_DB_WRITE_CONFIRMATION=yes
- ALLOW_DB_WRITE=yes
- ALLOW_MATCHES_WRITE=yes
- ALLOW_RAW_MATCH_DATA_WRITE=no
- ALLOW_BOOKMAKER_ODDS_WRITE=no
- ALLOW_FEATURE_WRITE=no
- ALLOW_NETWORK=no
- ALLOW_MATCH_DETAIL_FETCH=no
- no parser/features/training

## 4. Manifest gate result

- candidate_targets=${payload.manifest_gate?.candidate_targets}
- seed_plan_status=${payload.manifest_gate?.seed_plan_status}
- eligible_matches_insert_count=${payload.manifest_gate?.eligible_matches_insert_count}
- blocked_count=${payload.blocked_count}
- ok=${payload.manifest_gate?.ok}

## 5. Schema gate result

- matches columns: ${(schema.matches_columns || []).map(column => column.column_name).join(', ')}
- insert columns used: ${(schema.insert_columns || []).join(', ')}
- required columns: ${(schema.required_columns || []).join(', ')}
- constraints checked: ${(schema.constraints_checked || []).join(', ')}
- pipeline_status policy: ${JSON.stringify(schema.pipeline_status_policy || {})}
- is_finished policy: ${schema.is_finished_policy}
- schema ready=${schema.ready}

Constraints:
${renderRows(schema.matches_constraints || [], ['conname', 'contype', 'definition'])}

## 6. Identity conflict gate result

- existing_matches_count=${conflict.existing_matches_count}
- missing_matches_count=${conflict.missing_matches_count}
- duplicate_match_id_count=${conflict.duplicate_match_id_count}
- duplicate_external_id_count=${conflict.duplicate_external_id_count}
- match_id_conflict_count=${conflict.match_id_conflict_count}
- external_id_conflict_count=${conflict.external_id_conflict_count}
- invalid_identity_count=${conflict.invalid_identity_count}
- ready=${conflict.ready}

## 7. Transaction result

- transaction_began=${payload.transaction_began}
- inserted_count=${payload.inserted_count}
- committed=${payload.committed}
- rolled_back=${payload.rolled_back}
- matches_write_executed=${payload.matches_write_executed}
- raw_match_data_write_executed=${payload.raw_match_data_write_executed}
- odds_write_executed=${payload.odds_write_executed}
- features_write_executed=${payload.features_write_executed}
- training/prediction=${payload.training_prediction_executed}

## 8. Post-write verification

- matches ${payload.db_baseline_before?.matches} -> ${verification.db_counts_after?.matches}
- raw_match_data remains ${verification.db_counts_after?.raw_match_data}
- bookmaker_odds_history remains ${verification.db_counts_after?.bookmaker_odds_history}
- l3_features remains ${verification.db_counts_after?.l3_features}
- match_features_training remains ${verification.db_counts_after?.match_features_training}
- predictions remains ${verification.db_counts_after?.predictions}
- inserted rows count=${verification.inserted_rows_count}
- identity fields match manifest=${verification.identity_fields_match_manifest}
- duplicate_match_id_count=${verification.duplicate_match_id_count}
- ok=${verification.ok}

## 9. Manifest update result

- matches_identity_seed_execution_status=${payload.matches_identity_seed_execution_status}
- candidate matches_seed_status distribution=${JSON.stringify(payload.matches_seed_status_distribution || {})}
- inserted_count=${payload.inserted_count}
- blocked_count=${payload.blocked_count}
- required_next_step=${payload.required_next_step}

## 10. Verification results

- new execution tests: pending before PR
- V0 planning tests: pending before PR
- L2V execution tests: pending before PR
- L2U planning tests: pending before PR
- L2T preflight tests: pending before PR
- FotMobRawDetailFetcher tests: pending before PR
- npm test: pending before PR
- npm run test:coverage: pending before PR
- eslint / prettier / git diff: pending before PR
- DB row counts final: pending final safety check
- l1-config residue absent: pending final safety check
- docs/_staging_preview absent: pending final safety check
- PR CI: pending
- main push CI: pending

## 11. Recommended next phase

Phase 5.21L2V2: post-seed matches identity verification / raw write retry readiness audit.

Requirements: no DB write, no network, verify the 50 matches rows, verify the raw write FK prerequisite is now satisfied, prepare renewed L2V raw write retry, and no parser/features/training. The raw write retry still requires separate renewed authorization.

## 12. Explicit non-execution

- no raw_match_data writes
- no bookmaker_odds_history writes
- no features/training/prediction writes
- no network / FotMob access
- no match detail pageProps fetch
- no controlled raw write
- no schema migration
- no parser implementation
- no feature extraction
- no browser/proxy/captcha bypass
- no full raw_data/pageProps/source body print/save
- no file deletion
- no invented external_id / fake target data
`;
}

function createDefaultPool() {
    const { Pool } = require('pg');
    return new Pool({
        host: process.env.DB_HOST || process.env.POSTGRES_HOST || 'db',
        port: parseInteger(process.env.DB_PORT || process.env.POSTGRES_PORT, 5432),
        database: process.env.DB_NAME || process.env.POSTGRES_DB || 'football_db',
        user: process.env.DB_USER || process.env.POSTGRES_USER || 'football_user',
        password: process.env.DB_PASSWORD || process.env.POSTGRES_PASSWORD || 'football_password',
    });
}

async function getClient(poolOrClient) {
    if (poolOrClient && typeof poolOrClient.connect === 'function') {
        const client = await poolOrClient.connect();
        return { client, release: () => client.release() };
    }
    return { client: poolOrClient, release: () => {} };
}

async function runCli(argv = process.argv.slice(2), dependencies = {}) {
    const output = dependencies.output || (payload => process.stdout.write(`${JSON.stringify(payload, null, 2)}\n`));
    const parsed = Array.isArray(argv) ? parseArgs(argv) : argv;
    const validation = validateExecuteInput(parsed);
    if (!validation.ok) {
        const payload = buildFailurePayload({
            input: parsed,
            reason: `INPUT_BLOCKED:${validation.errors.join(';')}`,
            errors: validation.errors,
        });
        output(payload);
        return { status: 1, payload };
    }

    assertDbWriteAllowed({
        script: 'controlled_matches_identity_seed_execute.js',
        tables: ['matches'],
        operations: ['INSERT'],
    });

    const input = validation.value;
    const generatedAt = dependencies.generatedAt || new Date().toISOString();
    const pool = dependencies.client ? null : dependencies.pool || createDefaultPool();
    const { client, release } = await getClient(dependencies.client || pool);

    try {
        const manifest = dependencies.manifest || readJsonFile(input.manifest);
        const candidatesForSelect = Array.isArray(manifest.candidate_targets)
            ? manifest.candidate_targets.map(normalizeCandidateTarget)
            : [];
        const protectedTableRowsBefore =
            dependencies.protectedTableRowsBefore || (await loadProtectedTableBaselineRows(client));
        const matchesColumnRows = dependencies.matchesColumnRows || (await loadMatchesColumns(client));
        const matchesConstraintRows = dependencies.matchesConstraintRows || (await loadMatchesConstraints(client));
        const existingMatchRows =
            dependencies.existingMatchRows || (await loadExistingMatches(client, candidatesForSelect));
        const plan = buildExecutionPlanPayload({
            input,
            manifest,
            protectedTableRowsBefore,
            matchesColumnRows,
            matchesConstraintRows,
            existingMatchRows,
            generatedAt,
        });

        let payload = plan;
        if (plan.ok) {
            const tx = await executeTransaction(client, plan);
            payload = {
                ...plan,
                ...tx,
                ok: tx.committed,
                blocked: !tx.committed,
                blocked_reason: tx.committed ? null : tx.error,
                blocked_count: tx.committed ? 0 : TARGET_COUNT,
                matches_write_executed: tx.inserted_count > 0,
                inserted_count: tx.inserted_count,
                required_next_step: tx.committed
                    ? NEXT_STEP_AFTER_SUCCESS
                    : 'review_failed_matches_identity_seed_execution',
            };
            if (tx.committed) {
                const protectedTableRowsAfter =
                    dependencies.protectedTableRowsAfter || (await loadProtectedTableBaselineRows(client));
                const candidateRowsAfter =
                    dependencies.candidateRowsAfter || (await loadCandidateMatches(client, plan.insert_rows));
                const duplicateRows = dependencies.duplicateRows || (await loadDuplicateMatchIds(client));
                const postVerification = buildPostWriteVerification({
                    protectedTableRowsAfter,
                    candidateRowsAfter,
                    duplicateRows,
                    candidates: plan.insert_rows,
                });
                payload = {
                    ...payload,
                    ok: postVerification.ok,
                    blocked: !postVerification.ok,
                    blocked_reason: postVerification.ok
                        ? null
                        : `POST_WRITE_VERIFICATION_FAILED:${postVerification.errors.join(';')}`,
                    post_write_verification: postVerification,
                    db_baseline_after: postVerification.db_counts_after,
                };
            }
        }

        payload.matches_identity_seed_execution_status = payload.ok ? 'completed' : 'blocked';
        const updatedManifest = updateManifestWithExecution(manifest, payload, generatedAt);
        payload.matches_seed_status_distribution = getStatusDistribution(
            updatedManifest.candidate_targets,
            'matches_seed_status'
        );
        if (dependencies.writeManifest !== false) {
            (dependencies.writeManifestFile || writeJsonFile)(input.manifest, updatedManifest);
        }
        if (dependencies.writeReport !== false) {
            (dependencies.writeReportFile || writeReportFile)(REPORT_PATH, buildReport(payload));
        }
        payload.manifest_updated = dependencies.writeManifest !== false;
        payload.report_updated = dependencies.writeReport !== false;
        output(payload);
        return { status: payload.ok ? 0 : 1, payload };
    } catch (error) {
        const payload = buildFailurePayload({ input, reason: error.message });
        output(payload);
        return { status: 1, payload };
    } finally {
        release();
        if (pool && typeof pool.end === 'function') await pool.end();
    }
}

module.exports = {
    PHASE,
    MANIFEST_PATH,
    REPORT_PATH,
    SOURCE,
    LEAGUE_ID,
    LEAGUE_NAME,
    SEASON,
    BATCH_ID,
    TARGET_COUNT,
    EXPECTED_BEFORE_COUNTS,
    EXPECTED_AFTER_COUNTS,
    NEXT_STEP_AFTER_SUCCESS,
    parseArgs,
    normalizeBooleanFlag,
    validateExecuteInput,
    validateManifestForExecution,
    validateCandidateTargets,
    buildMatchesSchemaReadiness,
    buildIdentityConflictAudit,
    buildInsertRow,
    buildInsertStatement,
    buildExecutionPlanPayload,
    buildPostWriteVerification,
    updateManifestWithExecution,
    buildReport,
    queryReadOnly,
    loadProtectedTableBaselineRows,
    loadMatchesColumns,
    loadMatchesConstraints,
    loadExistingMatches,
    loadCandidateMatches,
    loadDuplicateMatchIds,
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
