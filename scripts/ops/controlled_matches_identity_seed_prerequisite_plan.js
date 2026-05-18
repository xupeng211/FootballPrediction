#!/usr/bin/env node
/* eslint-disable complexity, max-lines, max-statements */
'use strict';

const fs = require('node:fs');
const path = require('node:path');

const PHASE = 'PHASE5_21L2V0_CONTROLLED_MATCHES_IDENTITY_SEED_PREREQUISITE_PLANNING';
const MANIFEST_PATH = 'docs/_manifests/fotmob_pageprops_v2_ligue1_2025_2026_profile_001.proposal.json';
const REPORT_PATH = 'docs/_reports/CONTROLLED_MATCHES_IDENTITY_SEED_PREREQUISITE_PLANNING_PHASE5_21L2V0.md';
const SOURCE = 'fotmob';
const LEAGUE_ID = 53;
const LEAGUE_NAME = 'Ligue 1';
const SEASON = '2025/2026';
const SEASON_COMPACT = '20252026';
const BATCH_ID = 'fotmob-pageprops-v2-ligue1-2025-2026-profile-001';
const TARGET_COUNT = 50;
const KNOWN_COMPLETED_COUNT = 8;
const L2V0_REQUIRED_NEXT_STEP_BEFORE_PLANNING = 'controlled_matches_identity_seed_prerequisite_planning';
const L2V1_REQUIRED_NEXT_STEP_AFTER_PLANNING = 'controlled_matches_identity_seed_execution';
const EXPECTED_PROTECTED_TABLE_BASELINE = Object.freeze({
    matches: 10,
    bookmaker_odds_history: 2,
    raw_match_data: 18,
    l3_features: 2,
    match_features_training: 2,
    predictions: 2,
});
const REQUIRED_NO_FLAGS = Object.freeze([
    'allowDbWrite',
    'allowMatchesWrite',
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
const MANIFEST_TO_MATCHES_COLUMN = Object.freeze({
    match_id: 'match_id',
    external_id: 'external_id',
    league_name: 'league_name',
    season: 'season',
    home_team: 'home_team',
    away_team: 'away_team',
    match_date: 'match_date',
    status: 'status',
});
const POLICY_REQUIRED_IDENTITY_FIELDS = Object.freeze([
    'match_id',
    'external_id',
    'league_id',
    'league_name',
    'season',
    'home_team',
    'away_team',
    'match_date',
    'status',
]);
const FUTURE_INSERT_COLUMNS = Object.freeze([
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
    'pipeline_status',
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
        planningAuthorization: null,
        allowDbWrite: null,
        allowMatchesWrite: null,
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
    const booleanKeys = new Set(['planningAuthorization', ...REQUIRED_NO_FLAGS, ...BLOCKED_TRUE_FLAGS, 'help']);

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
        errors.push(`${name}=yes is required in Phase 5.21L2V0`);
        return;
    }
    errors.push(`missing ${name}=yes`);
}

function pushRequiredNo(errors, value, name) {
    if (value === false) return;
    if (value === true) {
        errors.push(`${name}=yes is blocked in Phase 5.21L2V0`);
        return;
    }
    errors.push(`missing ${name}=no`);
}

function normalizePlanInput(input = {}) {
    return {
        manifest: normalizeText(input.manifest),
        source: normalizeLower(input.source),
        leagueId: parseInteger(input.leagueId, null),
        leagueName: normalizeText(input.leagueName),
        season: normalizeText(input.season),
        batchId: normalizeText(input.batchId),
        targetCount: parseInteger(input.targetCount, null),
        planningAuthorization: normalizeBooleanFlag(input.planningAuthorization, undefined),
        allowDbWrite: normalizeBooleanFlag(input.allowDbWrite, undefined),
        allowMatchesWrite: normalizeBooleanFlag(input.allowMatchesWrite, undefined),
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
    requireExact(errors, value.batchId, BATCH_ID, 'batch-id');
    if (value.targetCount !== TARGET_COUNT) errors.push('target-count must be 50');
    pushRequiredYes(errors, value.planningAuthorization, 'planning-authorization');
    for (const key of REQUIRED_NO_FLAGS) pushRequiredNo(errors, value[key], flagName(key));
    for (const key of BLOCKED_TRUE_FLAGS) {
        if (value[key] === true) errors.push(`${flagName(key)}=yes is blocked in Phase 5.21L2V0`);
    }
    return { ok: errors.length === 0, errors, value };
}

function jsonClone(value) {
    if (value === undefined) return undefined;
    return JSON.parse(JSON.stringify(value));
}

function readManifestFile(manifestPath = MANIFEST_PATH) {
    return JSON.parse(fs.readFileSync(path.resolve(process.cwd(), manifestPath), 'utf8'));
}

function writeJsonFile(filePath, payload) {
    fs.writeFileSync(path.resolve(process.cwd(), filePath), `${JSON.stringify(payload, null, 2)}\n`, 'utf8');
}

function writeReportFile(filePath, content) {
    fs.mkdirSync(path.dirname(path.resolve(process.cwd(), filePath)), { recursive: true });
    fs.writeFileSync(path.resolve(process.cwd(), filePath), content, 'utf8');
}

function buildFailurePayload({ input = {}, reason = 'UNKNOWN_FAILURE', errors = [], dbBaselineBefore = null } = {}) {
    return {
        phase: PHASE,
        ok: false,
        planning_only: true,
        manifest_path: input.manifest || MANIFEST_PATH,
        failure_reason: reason,
        errors,
        db_baseline_before: dbBaselineBefore,
        db_write_executed: false,
        matches_write_executed: false,
        raw_match_data_write_executed: false,
        network_executed: false,
        match_detail_fetch_executed: false,
        parser_features_training_executed: false,
    };
}

function normalizeCandidateTarget(target = {}) {
    const kickoffOrMatchDate = normalizeText(target.kickoff_time || target.match_date);
    return {
        ...target,
        target_id: normalizeText(target.target_id),
        batch_id: normalizeText(target.batch_id),
        source: normalizeLower(target.source),
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
        kickoff_time: normalizeText(target.kickoff_time),
        match_date: normalizeText(target.match_date || target.kickoff_time),
        status: normalizeLower(target.status),
        source_inventory_route: normalizeText(target.source_inventory_route),
        source_path: normalizeText(target.source_path),
        write_status: normalizeText(target.write_status),
        preflight_status: normalizeText(target.preflight_status),
        baseline_hash: normalizeLower(target.baseline_hash),
        failure_reason: normalizeText(target.failure_reason),
        identity_tuple: [
            normalizeLower(target.home_team),
            normalizeLower(target.away_team),
            normalizeComparableTimestamp(kickoffOrMatchDate),
        ].join('|'),
    };
}

function countDuplicateExtras(values = []) {
    const counts = new Map();
    for (const value of values.filter(Boolean)) counts.set(value, (counts.get(value) || 0) + 1);
    return [...counts.values()].reduce((sum, count) => sum + Math.max(0, count - 1), 0);
}

function buildDuplicateSets(candidates = []) {
    const matchCounts = new Map();
    const externalCounts = new Map();
    const tupleCounts = new Map();
    for (const target of candidates) {
        matchCounts.set(target.match_id, (matchCounts.get(target.match_id) || 0) + 1);
        externalCounts.set(target.external_id, (externalCounts.get(target.external_id) || 0) + 1);
        tupleCounts.set(target.identity_tuple, (tupleCounts.get(target.identity_tuple) || 0) + 1);
    }
    return {
        duplicateMatchIds: new Set([...matchCounts].filter(([, count]) => count > 1).map(([value]) => value)),
        duplicateExternalIds: new Set([...externalCounts].filter(([, count]) => count > 1).map(([value]) => value)),
        duplicateIdentityTuples: new Set([...tupleCounts].filter(([, count]) => count > 1).map(([value]) => value)),
    };
}

function getCandidateWriteStatusDistribution(candidates = []) {
    return candidates.reduce((acc, target) => {
        const status = normalizeText(target.write_status) || 'missing';
        acc[status] = (acc[status] || 0) + 1;
        return acc;
    }, {});
}

function getRequiredNextStepBeforePlanning(manifest = {}) {
    const currentNextStep = normalizeText(manifest.required_next_step);
    if (
        currentNextStep === L2V1_REQUIRED_NEXT_STEP_AFTER_PLANNING &&
        manifest.matches_identity_seed_prerequisite_planning_result
    ) {
        return L2V0_REQUIRED_NEXT_STEP_BEFORE_PLANNING;
    }
    return currentNextStep || null;
}

function validateManifestStructure(manifest = {}) {
    const errors = [];
    const candidates = Array.isArray(manifest.candidate_targets) ? manifest.candidate_targets : [];
    const distribution = getCandidateWriteStatusDistribution(candidates);
    if (normalizeText(manifest.schema_version) !== 'target_manifest_proposal_v1') {
        errors.push('manifest schema_version must be target_manifest_proposal_v1');
    }
    if (normalizeText(manifest.batch_id) !== BATCH_ID) errors.push('manifest batch_id mismatch');
    if (normalizeLower(manifest.source) !== SOURCE) errors.push('manifest source mismatch');
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
    const nextStep = normalizeText(manifest.required_next_step);
    const writeExecutionStatus = normalizeText(manifest.write_execution_status);
    if (
        writeExecutionStatus !== 'blocked_missing_matches_fk_prerequisite' &&
        nextStep !== L2V0_REQUIRED_NEXT_STEP_BEFORE_PLANNING
    ) {
        errors.push('manifest must show L2V blocked_missing_matches_fk_prerequisite before L2V0');
    }
    if (distribution.blocked_missing_matches_fk_prerequisite !== TARGET_COUNT) {
        errors.push('candidate write_status distribution must contain blocked_missing_matches_fk_prerequisite=50');
    }
    return { ok: errors.length === 0, errors, writeStatusDistribution: distribution };
}

function hasSourceInventoryEvidence(target = {}) {
    return (
        target.source_inventory_route === 'source_inventory' ||
        target.source_path === 'l1_api_data_leagues' ||
        normalizeText(target.source_fidelity_notes).includes('pageprops_v2_no_write_preflight_passed')
    );
}

function isInventedCandidate(target = {}) {
    return [
        target.invented_external_id,
        target.invented_target,
        target.fake_target,
        target.fabricated_external_id,
        target.synthetic_target,
    ].some(value => normalizeBooleanFlag(value, false) === true);
}

function validateCandidateTargets(manifest = {}) {
    const candidates = Array.isArray(manifest.candidate_targets)
        ? manifest.candidate_targets.map(normalizeCandidateTarget)
        : [];
    const { duplicateMatchIds, duplicateExternalIds, duplicateIdentityTuples } = buildDuplicateSets(candidates);
    const targetErrors = new Map();
    const candidateErrorKey = target => target.match_id || target.external_id || `target-${targetErrors.size + 1}`;
    const addError = (target, message) => {
        const key = candidateErrorKey(target);
        if (!targetErrors.has(key)) targetErrors.set(key, []);
        targetErrors.get(key).push(message);
    };

    for (const target of candidates) {
        if (!target.match_id) addError(target, 'match_id is required');
        if (!/^\d+$/.test(target.external_id)) addError(target, 'external_id must be numeric');
        const expectedMatchId = `${LEAGUE_ID}_${SEASON_COMPACT}_${target.external_id}`;
        if (target.match_id !== expectedMatchId) addError(target, `match_id must be ${expectedMatchId}`);
        if (duplicateMatchIds.has(target.match_id)) addError(target, 'duplicate match_id');
        if (duplicateExternalIds.has(target.external_id)) addError(target, 'duplicate external_id');
        if (duplicateIdentityTuples.has(target.identity_tuple)) addError(target, 'duplicate home/away/kickoff tuple');
        if (target.batch_id !== BATCH_ID) addError(target, 'batch_id mismatch');
        if (target.source !== SOURCE) addError(target, 'source mismatch');
        if (target.league_id !== LEAGUE_ID) addError(target, 'league_id mismatch');
        if (target.league_name !== LEAGUE_NAME) addError(target, 'league_name mismatch');
        if (target.season !== SEASON) addError(target, 'season mismatch');
        if (!target.home_team) addError(target, 'home_team is required');
        if (!target.away_team) addError(target, 'away_team is required');
        if (!target.match_date && !target.kickoff_time) addError(target, 'match_date or kickoff_time is required');
        if (!target.status) addError(target, 'status is required');
        if (!hasSourceInventoryEvidence(target)) addError(target, 'source inventory evidence is required');
        if (isInventedCandidate(target)) addError(target, 'invented or fake target marker is blocked');
    }

    const missingRequiredFieldCount = candidates.filter(target =>
        POLICY_REQUIRED_IDENTITY_FIELDS.some(field => {
            if (field === 'league_id') return target.league_id !== LEAGUE_ID;
            return !normalizeText(target[field]);
        })
    ).length;
    const invalidIdentityCount = candidates.filter(target => {
        const expectedMatchId = `${LEAGUE_ID}_${SEASON_COMPACT}_${target.external_id}`;
        return !target.match_id || !/^\d+$/.test(target.external_id) || target.match_id !== expectedMatchId;
    }).length;

    return {
        candidates,
        targetErrors,
        duplicate_match_id_count: countDuplicateExtras(candidates.map(target => target.match_id)),
        duplicate_external_id_count: countDuplicateExtras(candidates.map(target => target.external_id)),
        duplicate_identity_tuple_count: countDuplicateExtras(candidates.map(target => target.identity_tuple)),
        invalid_identity_count: invalidIdentityCount,
        missing_required_field_count: missingRequiredFieldCount,
        candidate_error_key: candidateErrorKey,
    };
}

function normalizeTableRows(rows = []) {
    const result = {};
    for (const row of Array.isArray(rows) ? rows : []) {
        const tableName = normalizeText(row.table_name);
        if (tableName) result[tableName] = Number(row.rows || 0);
    }
    return result;
}

function validateProtectedTableBaseline(baseline = {}) {
    const errors = [];
    for (const [table, expected] of Object.entries(EXPECTED_PROTECTED_TABLE_BASELINE)) {
        if (Number(baseline[table]) !== expected) errors.push(`${table}=${baseline[table]} expected ${expected}`);
    }
    return errors;
}

function normalizeSchemaColumns(rows = []) {
    return (Array.isArray(rows) ? rows : []).map(row => ({
        column_name: normalizeText(row.column_name),
        data_type: normalizeText(row.data_type),
        is_nullable: normalizeText(row.is_nullable),
        column_default:
            row.column_default === null || row.column_default === undefined ? null : normalizeText(row.column_default),
    }));
}

function normalizeConstraintRows(rows = []) {
    return (Array.isArray(rows) ? rows : []).map(row => ({
        conname: normalizeText(row.conname),
        contype: normalizeText(row.contype),
        definition: normalizeText(row.definition),
    }));
}

function normalizeIndexRows(rows = []) {
    return (Array.isArray(rows) ? rows : []).map(row => ({
        indexname: normalizeText(row.indexname),
        indexdef: normalizeText(row.indexdef),
    }));
}

function buildMatchesSchemaReadiness({ columnRows = [], constraintRows = [], indexRows = [], candidates = [] } = {}) {
    const columns = normalizeSchemaColumns(columnRows);
    const constraints = normalizeConstraintRows(constraintRows);
    const indexes = normalizeIndexRows(indexRows);
    const columnNames = new Set(columns.map(column => column.column_name));
    const requiredNonNullColumns = columns
        .filter(column => column.is_nullable === 'NO')
        .map(column => column.column_name);
    const requiredColumnsMissingFromSchema = ['match_id', 'league_name', 'season', 'home_team', 'away_team'].filter(
        column => !columnNames.has(column)
    );
    const manifestMappedRequiredColumns = requiredNonNullColumns.filter(column => MANIFEST_TO_MATCHES_COLUMN[column]);
    const unmappedRequiredColumns = requiredNonNullColumns.filter(column => !MANIFEST_TO_MATCHES_COLUMN[column]);
    const candidatesMissingMappedRequired = candidates.filter(target =>
        manifestMappedRequiredColumns.some(column => !normalizeText(target[MANIFEST_TO_MATCHES_COLUMN[column]]))
    ).length;
    const definitions = constraints.map(row => row.definition.toLowerCase());
    const hasPrimaryKey = constraints.some(
        row => row.contype === 'p' && /primary key\s*\(\s*match_id\s*\)/i.test(row.definition)
    );
    const hasSeasonFormatCheck = definitions.some(
        definition => definition.includes('season') && definition.includes('^\\d{4}/\\d{4}$')
    );
    const hasStatusLowercaseCheck = definitions.some(
        definition => definition.includes('status') && definition.includes('lower')
    );
    const hasPipelineStatusCheck = definitions.some(definition => definition.includes('pipeline_status'));
    const hasMatchesPkeyIndex = indexes.some(
        row => row.indexname === 'matches_pkey' && /unique index/i.test(row.indexdef)
    );
    const statusNormalizationCompatible = candidates.every(target => normalizeLower(target.status) === target.status);
    const seasonFormatCompatible = candidates.every(target => /^\d{4}\/\d{4}$/.test(target.season));
    const matchDateCompatible = candidates.every(
        target => !Number.isNaN(Date.parse(target.match_date || target.kickoff_time))
    );
    const schemaReady =
        requiredColumnsMissingFromSchema.length === 0 &&
        unmappedRequiredColumns.length === 0 &&
        candidatesMissingMappedRequired === 0 &&
        hasPrimaryKey &&
        hasSeasonFormatCheck &&
        hasStatusLowercaseCheck &&
        statusNormalizationCompatible &&
        seasonFormatCompatible &&
        matchDateCompatible;

    return {
        matches_columns: columns,
        matches_constraints: constraints,
        matches_indexes: indexes,
        required_non_null_columns: requiredNonNullColumns,
        manifest_mapped_required_columns: manifestMappedRequiredColumns,
        unmapped_required_columns: unmappedRequiredColumns,
        required_columns_missing_from_schema: requiredColumnsMissingFromSchema,
        candidates_missing_mapped_required_count: candidatesMissingMappedRequired,
        primary_key_match_id_present: hasPrimaryKey,
        matches_pkey_index_present: hasMatchesPkeyIndex,
        season_format_check_present: hasSeasonFormatCheck,
        status_lowercase_check_present: hasStatusLowercaseCheck,
        pipeline_status_check_present: hasPipelineStatusCheck,
        status_normalization_compatible: statusNormalizationCompatible,
        season_format_compatible: seasonFormatCompatible,
        match_date_type_compatible: matchDateCompatible,
        ready: schemaReady,
    };
}

function normalizeComparableTimestamp(value) {
    const raw = normalizeText(value);
    if (!raw) return '';
    const timestamp = Date.parse(raw);
    if (Number.isNaN(timestamp)) return raw;
    return new Date(timestamp).toISOString();
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
    };
}

function groupBy(rows = [], key) {
    const grouped = new Map();
    for (const row of rows) {
        const value = normalizeText(row[key]);
        if (!value) continue;
        if (!grouped.has(value)) grouped.set(value, []);
        grouped.get(value).push(row);
    }
    return grouped;
}

function compareCandidateToExisting(candidate = {}, row = {}) {
    const existing = normalizeExistingMatchRow(row);
    const expectedMatchDate = normalizeComparableTimestamp(candidate.match_date || candidate.kickoff_time);
    const mismatches = [];
    for (const [field, expected, actual] of [
        ['match_id', candidate.match_id, existing.match_id],
        ['external_id', candidate.external_id, existing.external_id],
        ['league_name', candidate.league_name, existing.league_name],
        ['season', candidate.season, existing.season],
        ['home_team', candidate.home_team, existing.home_team],
        ['away_team', candidate.away_team, existing.away_team],
        ['match_date', expectedMatchDate, existing.match_date],
        ['status', candidate.status, existing.status],
    ]) {
        if (normalizeText(expected) !== normalizeText(actual)) mismatches.push(field);
    }
    return { matches: mismatches.length === 0, mismatches };
}

function buildTargetSeedDecision(
    candidate = {},
    existingRowsByMatchId = new Map(),
    existingRowsByExternalId = new Map(),
    candidateErrors = []
) {
    const existingByMatchId = existingRowsByMatchId.get(candidate.match_id) || [];
    const existingByExternalId = existingRowsByExternalId.get(candidate.external_id) || [];
    const externalConflicts = existingByExternalId.filter(row => normalizeText(row.match_id) !== candidate.match_id);

    if (candidateErrors.length > 0) {
        return {
            match_id: candidate.match_id,
            external_id: candidate.external_id,
            home_team: candidate.home_team,
            away_team: candidate.away_team,
            match_date: candidate.match_date || candidate.kickoff_time,
            status: candidate.status,
            seed_eligibility_status: 'blocked_invalid_manifest_identity',
            planned_seed_action: 'none',
            failure_reason: candidateErrors.join(';'),
        };
    }

    if (existingByMatchId.length > 0) {
        const comparison = compareCandidateToExisting(candidate, existingByMatchId[0]);
        if (comparison.matches) {
            return {
                match_id: candidate.match_id,
                external_id: candidate.external_id,
                home_team: candidate.home_team,
                away_team: candidate.away_team,
                match_date: candidate.match_date || candidate.kickoff_time,
                status: candidate.status,
                seed_eligibility_status: 'skipped_existing_matches',
                planned_seed_action: 'skip_existing_matching_match',
                existing_matches_count: existingByMatchId.length,
                failure_reason: null,
            };
        }
        return {
            match_id: candidate.match_id,
            external_id: candidate.external_id,
            home_team: candidate.home_team,
            away_team: candidate.away_team,
            match_date: candidate.match_date || candidate.kickoff_time,
            status: candidate.status,
            seed_eligibility_status: 'blocked_match_id_identity_conflict',
            planned_seed_action: 'none',
            existing_matches_count: existingByMatchId.length,
            conflict_fields: comparison.mismatches,
            failure_reason: `match_id identity conflict: ${comparison.mismatches.join(',')}`,
        };
    }

    if (externalConflicts.length > 0) {
        return {
            match_id: candidate.match_id,
            external_id: candidate.external_id,
            home_team: candidate.home_team,
            away_team: candidate.away_team,
            match_date: candidate.match_date || candidate.kickoff_time,
            status: candidate.status,
            seed_eligibility_status: 'blocked_external_id_identity_conflict',
            planned_seed_action: 'none',
            existing_matches_count: 0,
            conflict_match_ids: externalConflicts.map(row => normalizeText(row.match_id)),
            failure_reason: 'external_id already exists on a different match_id',
        };
    }

    return {
        match_id: candidate.match_id,
        external_id: candidate.external_id,
        home_team: candidate.home_team,
        away_team: candidate.away_team,
        match_date: candidate.match_date || candidate.kickoff_time,
        status: candidate.status,
        seed_eligibility_status: 'eligible_matches_insert',
        planned_seed_action: 'insert_missing_matches_identity_row_in_l2v1',
        existing_matches_count: 0,
        failure_reason: null,
    };
}

function computeSeedPlanStatus({ eligibleMatchesInsertCount, skippedExistingMatchesCount, blockedCount } = {}) {
    if (blockedCount > 0) {
        return {
            matchesIdentitySeedPlanStatus: 'blocked',
            requiredNextStep: 'review_blocked_matches_identity_targets',
        };
    }
    if (eligibleMatchesInsertCount === TARGET_COUNT && skippedExistingMatchesCount === 0) {
        return {
            matchesIdentitySeedPlanStatus: 'ready_for_final_authorization',
            requiredNextStep: L2V1_REQUIRED_NEXT_STEP_AFTER_PLANNING,
        };
    }
    return {
        matchesIdentitySeedPlanStatus: 'review_existing_matches_before_final_authorization',
        requiredNextStep: 'review_existing_matches_identity_before_execution',
    };
}

function buildFutureControlledMatchesSeedPlan() {
    return {
        phase: 'PHASE5_21L2V1_CONTROLLED_MATCHES_IDENTITY_SEED_EXECUTION',
        final_db_write_confirmation_required: true,
        required_flags: {
            final_db_write_confirmation: 'yes',
            allow_db_write: 'yes',
            allow_matches_write: 'yes',
            allow_raw_match_data_write: 'no',
        },
        insert_only_missing_matches_rows: true,
        future_insert_columns: FUTURE_INSERT_COLUMNS,
        transaction_policy: 'single_transaction_for_authorized_50_matches_identity_rows',
        expected_matches_after_success: 60,
        raw_match_data_remains: 18,
        no_network: true,
        no_raw_match_data_write: true,
        no_odds_features_training_prediction_writes: true,
        after_success: 'retry L2V raw pageProps write only with separate renewed final authorization',
    };
}

function buildMatchesIdentitySeedPlanningPayload({
    input = {},
    manifest = {},
    protectedTableRowsBefore = [],
    protectedTableRowsAfter = [],
    matchesColumnRows = [],
    matchesConstraintRows = [],
    matchesIndexRows = [],
    existingMatchRows = [],
    generatedAt = null,
} = {}) {
    const dbBaselineBefore = normalizeTableRows(protectedTableRowsBefore);
    const dbBaselineAfter = normalizeTableRows(
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

    const candidateValidation = validateCandidateTargets(manifest);
    const schemaReadiness = buildMatchesSchemaReadiness({
        columnRows: matchesColumnRows,
        constraintRows: matchesConstraintRows,
        indexRows: matchesIndexRows,
        candidates: candidateValidation.candidates,
    });
    const normalizedExistingRows = (Array.isArray(existingMatchRows) ? existingMatchRows : []).map(
        normalizeExistingMatchRow
    );
    const existingRowsByMatchId = groupBy(normalizedExistingRows, 'match_id');
    const existingRowsByExternalId = groupBy(normalizedExistingRows, 'external_id');
    const targetSummaries = candidateValidation.candidates.map(target =>
        buildTargetSeedDecision(
            target,
            existingRowsByMatchId,
            existingRowsByExternalId,
            candidateValidation.targetErrors.get(candidateValidation.candidate_error_key(target)) || []
        )
    );
    const eligibleMatchesInsertCount = targetSummaries.filter(
        target => target.seed_eligibility_status === 'eligible_matches_insert'
    ).length;
    const skippedExistingMatchesCount = targetSummaries.filter(
        target => target.seed_eligibility_status === 'skipped_existing_matches'
    ).length;
    const candidateBlockedCount = targetSummaries.filter(target =>
        target.seed_eligibility_status.startsWith('blocked_')
    ).length;
    const schemaBlockedCount = schemaReadiness.ready ? 0 : 1;
    const blockedCount = candidateBlockedCount + schemaBlockedCount;
    const existingMatchesCount = new Set(
        normalizedExistingRows
            .map(row => row.match_id)
            .filter(matchId => candidateValidation.candidates.some(target => target.match_id === matchId))
    ).size;
    const missingMatchesCount = TARGET_COUNT - existingMatchesCount;
    const externalIdConflictCount = targetSummaries.filter(
        target => target.seed_eligibility_status === 'blocked_external_id_identity_conflict'
    ).length;
    const matchIdConflictCount = targetSummaries.filter(
        target => target.seed_eligibility_status === 'blocked_match_id_identity_conflict'
    ).length;
    const status = computeSeedPlanStatus({
        eligibleMatchesInsertCount,
        skippedExistingMatchesCount,
        blockedCount,
    });
    const expectedMatchesAfter = Number(dbBaselineBefore.matches || 0) + eligibleMatchesInsertCount;

    return {
        phase: PHASE,
        ok: status.matchesIdentitySeedPlanStatus === 'ready_for_final_authorization',
        planning_only: true,
        source: SOURCE,
        league_id: LEAGUE_ID,
        league_name: LEAGUE_NAME,
        season: SEASON,
        manifest_path: input.manifest || MANIFEST_PATH,
        report_path: REPORT_PATH,
        batch_id: BATCH_ID,
        generated_at: generatedAt,
        db_baseline_before: dbBaselineBefore,
        db_baseline_after: dbBaselineAfter,
        manifest_summary: {
            candidate_targets: manifest.candidate_targets?.length || 0,
            known_completed_targets: manifest.known_completed_targets?.length || 0,
            write_execution_status: manifest.write_execution_status || null,
            candidate_write_status_distribution: structureValidation.writeStatusDistribution,
            required_next_step_before: getRequiredNextStepBeforePlanning(manifest),
        },
        matches_schema_readiness: schemaReadiness,
        candidate_count: candidateValidation.candidates.length,
        eligible_matches_insert_count: eligibleMatchesInsertCount,
        skipped_existing_matches_count: skippedExistingMatchesCount,
        blocked_count: blockedCount,
        duplicate_match_id_count: candidateValidation.duplicate_match_id_count,
        duplicate_external_id_count: candidateValidation.duplicate_external_id_count,
        duplicate_identity_tuple_count: candidateValidation.duplicate_identity_tuple_count,
        external_id_conflict_count: externalIdConflictCount,
        match_id_conflict_count: matchIdConflictCount,
        invalid_identity_count: candidateValidation.invalid_identity_count,
        missing_required_field_count:
            candidateValidation.missing_required_field_count +
            schemaReadiness.candidates_missing_mapped_required_count +
            schemaReadiness.unmapped_required_columns.length,
        existing_matches_count: existingMatchesCount,
        missing_matches_count: missingMatchesCount,
        would_insert_matches_count: eligibleMatchesInsertCount,
        would_update_matches_count: 0,
        expected_matches_after: expectedMatchesAfter,
        raw_match_data_current_count: Number(dbBaselineBefore.raw_match_data || 0),
        raw_match_data_after_planning: Number(dbBaselineBefore.raw_match_data || 0),
        matches_identity_seed_plan_status: status.matchesIdentitySeedPlanStatus,
        matches_identity_seed_authorization_status: 'pending_final_db_write_confirmation',
        required_next_step: status.requiredNextStep,
        target_summaries: targetSummaries,
        future_l2v1_controlled_matches_seed_plan: buildFutureControlledMatchesSeedPlan(),
        db_write_executed: false,
        matches_write_executed: false,
        raw_match_data_write_executed: false,
        network_executed: false,
        match_detail_fetch_executed: false,
        parser_features_training_executed: false,
    };
}

function updateManifestWithMatchesIdentitySeedPlan(
    manifest = {},
    payload = {},
    generatedAt = new Date().toISOString()
) {
    const updated = jsonClone(manifest);
    const summaryByMatchId = new Map((payload.target_summaries || []).map(target => [target.match_id, target]));
    updated.matches_identity_seed_plan_status = payload.matches_identity_seed_plan_status;
    updated.matches_identity_seed_authorization_status = payload.matches_identity_seed_authorization_status;
    updated.eligible_matches_insert_count = payload.eligible_matches_insert_count;
    updated.skipped_existing_matches_count = payload.skipped_existing_matches_count;
    updated.matches_identity_seed_blocked_count = payload.blocked_count;
    updated.expected_matches_after = payload.expected_matches_after;
    updated.required_next_step = payload.required_next_step;
    updated.matches_identity_seed_prerequisite_planning_result = {
        phase: PHASE,
        planned_at: generatedAt,
        planning_only: true,
        matches_identity_seed_plan_status: payload.matches_identity_seed_plan_status,
        matches_identity_seed_authorization_status: payload.matches_identity_seed_authorization_status,
        candidate_count: payload.candidate_count,
        eligible_matches_insert_count: payload.eligible_matches_insert_count,
        skipped_existing_matches_count: payload.skipped_existing_matches_count,
        blocked_count: payload.blocked_count,
        duplicate_match_id_count: payload.duplicate_match_id_count,
        duplicate_external_id_count: payload.duplicate_external_id_count,
        external_id_conflict_count: payload.external_id_conflict_count,
        match_id_conflict_count: payload.match_id_conflict_count,
        invalid_identity_count: payload.invalid_identity_count,
        missing_required_field_count: payload.missing_required_field_count,
        expected_matches_after: payload.expected_matches_after,
        raw_match_data_after_planning: payload.raw_match_data_after_planning,
        required_next_step: payload.required_next_step,
        db_write_executed: false,
        matches_write_executed: false,
        raw_match_data_write_executed: false,
        network_executed: false,
    };
    updated.candidate_targets = (updated.candidate_targets || []).map(target => {
        const summary = summaryByMatchId.get(normalizeText(target.match_id));
        if (!summary) return target;
        return {
            ...target,
            matches_identity_seed_status: summary.seed_eligibility_status,
            matches_identity_seed_action: summary.planned_seed_action,
            matches_identity_seed_failure_reason: summary.failure_reason,
            matches_identity_seed_planned_at: generatedAt,
            required_next_step: payload.required_next_step,
            updated_at: generatedAt,
        };
    });
    return updated;
}

function renderTableRows(rows = [], columns = []) {
    if (!Array.isArray(rows) || rows.length === 0) return '- none\n';
    return rows
        .map(row => `- ${columns.map(column => `${column}=${normalizeText(row[column]) || 'null'}`).join(', ')}`)
        .join('\n');
}

function buildReport(payload = {}) {
    const schema = payload.matches_schema_readiness || {};
    return `# Controlled Matches Identity Seed Prerequisite Planning - Phase 5.21L2V0

## 1. Executive summary

- L2V raw write was blocked by the FK / matches existence gate.
- The 50 candidate match_id values are missing from matches.
- L2V0 is matches identity seed prerequisite planning only.
- No DB write, matches write, raw_match_data write, network access, match detail fetch, parser, features, or training was executed.
- Real matches insert must happen in Phase 5.21L2V1 with separate final DB-write authorization.

## 2. Current DB baseline

- matches=${payload.db_baseline_before?.matches}
- raw_match_data=${payload.db_baseline_before?.raw_match_data}
- bookmaker_odds_history=${payload.db_baseline_before?.bookmaker_odds_history}
- protected tables: l3_features=${payload.db_baseline_before?.l3_features}, match_features_training=${payload.db_baseline_before?.match_features_training}, predictions=${payload.db_baseline_before?.predictions}

## 3. Manifest input summary

- manifest path: \`${payload.manifest_path}\`
- candidate_targets=${payload.manifest_summary?.candidate_targets}
- known_completed_targets=${payload.manifest_summary?.known_completed_targets}
- write_execution_status=${payload.manifest_summary?.write_execution_status}
- candidate write_status distribution=${JSON.stringify(payload.manifest_summary?.candidate_write_status_distribution || {})}
- required_next_step before planning=${payload.manifest_summary?.required_next_step_before}

## 4. Matches schema readiness

- matches columns: ${(schema.matches_columns || []).map(column => column.column_name).join(', ')}
- required non-null columns: ${(schema.required_non_null_columns || []).join(', ')}
- primary key match_id present=${schema.primary_key_match_id_present}
- matches_pkey index present=${schema.matches_pkey_index_present}
- season_format check present=${schema.season_format_check_present}
- status_lowercase check present=${schema.status_lowercase_check_present}
- pipeline_status check present=${schema.pipeline_status_check_present}
- manifest has all mapped required values=${schema.candidates_missing_mapped_required_count === 0}
- schema ready=${schema.ready}

Constraints:
${renderTableRows(schema.matches_constraints || [], ['conname', 'contype', 'definition'])}

Indexes:
${renderTableRows(schema.matches_indexes || [], ['indexname', 'indexdef'])}

## 5. Identity eligibility audit

- candidate_count=${payload.candidate_count}
- eligible_matches_insert_count=${payload.eligible_matches_insert_count}
- skipped_existing_matches_count=${payload.skipped_existing_matches_count}
- blocked_count=${payload.blocked_count}
- duplicate_match_id_count=${payload.duplicate_match_id_count}
- duplicate_external_id_count=${payload.duplicate_external_id_count}
- external_id_conflict_count=${payload.external_id_conflict_count}
- match_id_conflict_count=${payload.match_id_conflict_count}
- invalid_identity_count=${payload.invalid_identity_count}
- missing_required_field_count=${payload.missing_required_field_count}
- existing_matches_count=${payload.existing_matches_count}
- missing_matches_count=${payload.missing_matches_count}
- would_insert_matches_count=${payload.would_insert_matches_count}
- would_update_matches_count=${payload.would_update_matches_count}
- expected_matches_after=${payload.expected_matches_after}

## 6. Future L2V1 controlled matches seed plan

L2V1 must require \`FINAL_DB_WRITE_CONFIRMATION=yes\`, \`ALLOW_DB_WRITE=yes\`, and \`ALLOW_MATCHES_WRITE=yes\`. It must keep \`ALLOW_RAW_MATCH_DATA_WRITE=no\`, insert only the 50 missing matches identity rows, avoid raw writes, odds writes, parser/features/training, and use a single transaction. Success verification should confirm matches 10 -> 60, raw_match_data remains 18, and protected tables remain unchanged. After L2V1 succeeds, retrying L2V raw write still needs separate renewed authorization.

## 7. Manifest update result

- manifest updated=true
- matches_identity_seed_plan_status=${payload.matches_identity_seed_plan_status}
- matches_identity_seed_authorization_status=${payload.matches_identity_seed_authorization_status}
- eligible_matches_insert_count=${payload.eligible_matches_insert_count}
- expected_matches_after=${payload.expected_matches_after}
- required_next_step=${payload.required_next_step}

## 8. DB safety result

- matches=${payload.db_baseline_after?.matches}
- raw_match_data=${payload.db_baseline_after?.raw_match_data}
- bookmaker_odds_history=${payload.db_baseline_after?.bookmaker_odds_history}
- l3_features=${payload.db_baseline_after?.l3_features}
- match_features_training=${payload.db_baseline_after?.match_features_training}
- predictions=${payload.db_baseline_after?.predictions}

## 9. Verification results

- new matches seed prerequisite planning tests: pending before PR
- L2V execution tests: pending before PR
- L2U planning tests: pending before PR
- L2T preflight tests: pending before PR
- FotMobRawDetailFetcher tests: pending before PR
- npm test: pending before PR
- npm run test:coverage: pending before PR
- eslint / prettier / git diff: pending before PR
- DB row counts unchanged: confirmed by planning script
- l1-config residue absent: pending final safety check
- docs/_staging_preview absent: pending final safety check
- PR CI: pending
- main push CI: pending

## 10. Recommended next phase

Phase 5.21L2V1: controlled matches identity seed execution.

Requirements: explicit final DB-write authorization, only write matches table, no raw_match_data write, no FotMob/network access, no parser/features/training, use manifest identity fields, controlled transaction, verify matches 10 -> 60, raw_match_data remains 18, then retry L2V raw write only after separate renewed authorization.

## 11. Explicit non-execution

- no DB writes
- no matches writes
- no raw_match_data writes
- no bookmaker_odds_history writes
- no network / FotMob access
- no match detail pageProps fetch
- no controlled raw write
- no schema migration
- no parser implementation
- no feature extraction
- no l3_features write
- no match_features_training write
- no training/prediction
- no browser/proxy/captcha bypass
- no full raw_data/pageProps/source body print/save
- no file deletion
- no invented external_id / fake target data
`;
}

function ensureReadOnlySql(sql) {
    const normalized = normalizeText(sql).replace(/\s+/g, ' ');
    if (!/^SELECT\b/i.test(normalized)) {
        throw new Error('READ_ONLY_QUERY_REQUIRED');
    }
    if (/\b(INSERT|UPDATE|DELETE|TRUNCATE|ALTER|DROP|CREATE|LOCK|COPY|GRANT|REVOKE|MERGE)\b/i.test(normalized)) {
        throw new Error('READ_ONLY_QUERY_FORBIDDEN_TOKEN');
    }
    if (/\bFOR\s+(UPDATE|SHARE|NO\s+KEY\s+UPDATE|KEY\s+SHARE)\b/i.test(normalized)) {
        throw new Error('READ_ONLY_QUERY_LOCK_FORBIDDEN');
    }
}

async function queryReadOnly(client, sql, params = []) {
    ensureReadOnlySql(sql);
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
WHERE table_name = 'matches'
ORDER BY ordinal_position
`
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
WHERE t.relname = 'matches'
ORDER BY conname
`
    );
    return result.rows || [];
}

async function loadMatchesIndexes(client) {
    const result = await queryReadOnly(
        client,
        `
SELECT indexname, indexdef
FROM pg_indexes
WHERE tablename = 'matches'
ORDER BY indexname
`
    );
    return result.rows || [];
}

async function loadExistingMatches(client, candidates = []) {
    const matchIds = candidates.map(target => target.match_id).filter(Boolean);
    const externalIds = candidates.map(target => target.external_id).filter(Boolean);
    const result = await queryReadOnly(
        client,
        `
SELECT match_id, external_id, league_name, season, home_team, away_team, match_date, status
FROM matches
WHERE match_id = ANY($1::text[])
   OR external_id = ANY($2::text[])
ORDER BY match_id
`,
        [matchIds, externalIds]
    );
    return result.rows || [];
}

function createDefaultPool() {
    const { Pool } = require('pg');
    return new Pool({
        host: process.env.DB_HOST || process.env.PGHOST || 'db',
        port: Number(process.env.DB_PORT || process.env.PGPORT || 5432),
        database: process.env.DB_NAME || process.env.PGDATABASE || 'football_db',
        user: process.env.DB_USER || process.env.PGUSER || 'football_user',
        password: process.env.DB_PASSWORD || process.env.PGPASSWORD,
    });
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
        dependencies.protectedTableRowsBefore ||
        dependencies.protectedTableRowsAfter ||
        dependencies.matchesColumnRows ||
        dependencies.matchesConstraintRows ||
        dependencies.matchesIndexRows ||
        dependencies.existingMatchRows
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
        const protectedTableRowsBefore =
            dependencies.protectedTableRowsBefore || (await loadProtectedTableBaselineRows(client));
        const matchesColumnRows = dependencies.matchesColumnRows || (await loadMatchesColumns(client));
        const matchesConstraintRows = dependencies.matchesConstraintRows || (await loadMatchesConstraints(client));
        const matchesIndexRows = dependencies.matchesIndexRows || (await loadMatchesIndexes(client));
        const existingMatchRows = dependencies.existingMatchRows || (await loadExistingMatches(client, candidates));
        const protectedTableRowsAfter =
            dependencies.protectedTableRowsAfter || (await loadProtectedTableBaselineRows(client));
        const payload = buildMatchesIdentitySeedPlanningPayload({
            input,
            manifest,
            protectedTableRowsBefore,
            protectedTableRowsAfter,
            matchesColumnRows,
            matchesConstraintRows,
            matchesIndexRows,
            existingMatchRows,
            generatedAt,
        });
        if (payload.phase && !payload.failure_reason) {
            const updatedManifest = updateManifestWithMatchesIdentitySeedPlan(manifest, payload, generatedAt);
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
    LEAGUE_ID,
    LEAGUE_NAME,
    SEASON,
    BATCH_ID,
    TARGET_COUNT,
    parseArgs,
    normalizeBooleanFlag,
    validatePlanInput,
    validateManifestStructure,
    validateCandidateTargets,
    buildMatchesSchemaReadiness,
    buildTargetSeedDecision,
    buildMatchesIdentitySeedPlanningPayload,
    updateManifestWithMatchesIdentitySeedPlan,
    buildReport,
    queryReadOnly,
    loadProtectedTableBaselineRows,
    loadMatchesColumns,
    loadMatchesConstraints,
    loadMatchesIndexes,
    loadExistingMatches,
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
