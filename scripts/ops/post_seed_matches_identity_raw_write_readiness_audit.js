#!/usr/bin/env node
/* eslint-disable complexity, max-lines, max-statements */
'use strict';

const fs = require('node:fs');
const path = require('node:path');

const PHASE = 'PHASE5_21L2V2_POST_SEED_MATCHES_IDENTITY_RAW_WRITE_READINESS_AUDIT';
const MANIFEST_PATH = 'docs/_manifests/fotmob_pageprops_v2_ligue1_2025_2026_profile_001.proposal.json';
const REPORT_PATH = 'docs/_reports/POST_SEED_MATCHES_IDENTITY_RAW_WRITE_READINESS_AUDIT_PHASE5_21L2V2.md';
const SOURCE = 'fotmob';
const LEAGUE_ID = 53;
const LEAGUE_NAME = 'Ligue 1';
const SEASON = '2025/2026';
const SEASON_COMPACT = '20252026';
const BATCH_ID = 'fotmob-pageprops-v2-ligue1-2025-2026-profile-001';
const TARGET_COUNT = 50;
const KNOWN_COMPLETED_COUNT = 8;
const DATA_VERSION = 'fotmob_pageprops_v2';
const NEXT_STEP_AFTER_READY = 'renewed_controlled_pageprops_v2_raw_write_execution';
const EXPECTED_DB_COUNTS = Object.freeze({
    matches: 60,
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
const VALID_TARGET_WRITE_PLAN_STATUSES = Object.freeze(['eligible_for_insert', 'ready_for_final_authorization']);

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
        readinessAuditAuthorization: null,
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
    const booleanKeys = new Set(['readinessAuditAuthorization', ...REQUIRED_NO_FLAGS, ...BLOCKED_TRUE_FLAGS, 'help']);

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
        errors.push(`${name}=yes is required for Phase 5.21L2V2`);
        return;
    }
    errors.push(`missing ${name}=yes`);
}

function requireNo(errors, value, name) {
    if (value === false) return;
    if (value === true) {
        errors.push(`${name}=yes is blocked in Phase 5.21L2V2`);
        return;
    }
    errors.push(`missing ${name}=no`);
}

function validateAuditInput(input = {}) {
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
    requireYes(errors, input.readinessAuditAuthorization, 'readiness-audit-authorization');
    for (const flag of REQUIRED_NO_FLAGS) requireNo(errors, input[flag], flagName(flag));
    for (const flag of BLOCKED_TRUE_FLAGS) {
        if (input[flag] === true) errors.push(`${flagName(flag)}=yes is blocked in Phase 5.21L2V2`);
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

function normalizeBooleanFromDb(value) {
    return value === true || normalizeLower(value) === 'true' || normalizeLower(value) === 't';
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
        status: normalizeLower(target.status),
        baseline_hash: normalizeLower(target.baseline_hash),
        preflight_status: normalizeText(target.preflight_status),
        write_plan_status: normalizeText(target.write_plan_status),
        matches_seed_status: normalizeText(target.matches_seed_status),
    };
}

function normalizeMatchRow(row = {}) {
    return {
        match_id: normalizeText(row.match_id),
        external_id: normalizeText(row.external_id),
        league_name: normalizeText(row.league_name),
        season: normalizeText(row.season),
        home_team: normalizeText(row.home_team),
        away_team: normalizeText(row.away_team),
        match_date: normalizeComparableTimestamp(row.match_date),
        status: normalizeLower(row.status),
        is_finished: normalizeBooleanFromDb(row.is_finished),
        data_source: normalizeLower(row.data_source),
        pipeline_status: normalizeText(row.pipeline_status),
    };
}

function getStatusDistribution(targets = [], field) {
    return targets.reduce((acc, target) => {
        const status = normalizeText(target[field]) || 'missing';
        acc[status] = (acc[status] || 0) + 1;
        return acc;
    }, {});
}

function normalizeTableRows(rows = []) {
    return rows.reduce((acc, row) => {
        acc[normalizeText(row.table_name)] = Number(row.rows);
        return acc;
    }, {});
}

function validateExpectedCounts(actual = {}, expected = EXPECTED_DB_COUNTS) {
    const errors = [];
    for (const [tableName, expectedRows] of Object.entries(expected)) {
        if (Number(actual[tableName]) !== expectedRows) {
            errors.push(`${tableName}=${actual[tableName]} expected ${expectedRows}`);
        }
    }
    return errors;
}

function validateManifestForAudit(manifest = {}) {
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
    if (normalizeText(manifest.matches_identity_seed_execution_status) !== 'completed') {
        errors.push('matches_identity_seed_execution_status must be completed');
    }
    if (normalizeText(manifest.write_execution_status) !== 'blocked_missing_matches_fk_prerequisite') {
        errors.push('write_execution_status must still record blocked_missing_matches_fk_prerequisite');
    }
    const matchesSeedStatusDistribution = getStatusDistribution(
        manifest.candidate_targets || [],
        'matches_seed_status'
    );
    if (Number(matchesSeedStatusDistribution.inserted_matches_identity || 0) !== TARGET_COUNT) {
        errors.push('candidate matches_seed_status distribution must include inserted_matches_identity=50');
    }
    return {
        ok: errors.length === 0,
        errors,
        candidate_targets: Array.isArray(manifest.candidate_targets) ? manifest.candidate_targets.length : 0,
        known_completed_targets: Array.isArray(manifest.known_completed_targets)
            ? manifest.known_completed_targets.length
            : 0,
        matches_identity_seed_execution_status: manifest.matches_identity_seed_execution_status || null,
        matches_seed_status_distribution: matchesSeedStatusDistribution,
    };
}

function validateCandidateTargets(candidates = []) {
    const normalizedCandidates = candidates.map(normalizeCandidateTarget);
    const errors = [];
    const matchIdCounts = new Map();
    const externalIdCounts = new Map();
    let baselineHashReadyCount = 0;
    let missingRequiredFieldCount = 0;
    let invalidIdentityCount = 0;

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
        if (target.preflight_status !== 'hash_baseline_ready') {
            targetErrors.push('preflight_status must be hash_baseline_ready');
        }
        if (/^[a-f0-9]{64}$/.test(target.baseline_hash)) {
            baselineHashReadyCount += 1;
        } else {
            targetErrors.push('baseline_hash must be 64 hex');
        }
        if (!VALID_TARGET_WRITE_PLAN_STATUSES.includes(target.write_plan_status)) {
            targetErrors.push('write_plan_status must remain eligible/ready for insert');
        }
        if (target.matches_seed_status !== 'inserted_matches_identity') {
            targetErrors.push('matches_seed_status must be inserted_matches_identity');
        }
        if (hasInventedMarker(target)) targetErrors.push('invented/fake marker present');

        matchIdCounts.set(target.match_id, (matchIdCounts.get(target.match_id) || 0) + 1);
        externalIdCounts.set(target.external_id, (externalIdCounts.get(target.external_id) || 0) + 1);
        if (targetErrors.length > 0) {
            invalidIdentityCount += 1;
            if (
                targetErrors.some(error =>
                    /missing match_id|missing home_team|missing away_team|missing match_date|missing status/.test(error)
                )
            ) {
                missingRequiredFieldCount += 1;
            }
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
        baseline_hash_ready_count: baselineHashReadyCount,
        invalid_identity_count: invalidIdentityCount,
        missing_required_field_count: missingRequiredFieldCount,
        duplicate_match_id_count: duplicateMatchIds.length,
        duplicate_external_id_count: duplicateExternalIds.length,
    };
}

function buildMatchesIdentityVerification(candidates = [], matchRows = []) {
    const byMatchId = new Map(matchRows.map(row => [normalizeText(row.match_id), normalizeMatchRow(row)]));
    const mismatches = [];
    let externalIdMismatchCount = 0;
    let teamDateStatusMismatchCount = 0;

    for (const candidate of candidates) {
        const row = byMatchId.get(candidate.match_id);
        if (!row) continue;
        const expected = {
            external_id: candidate.external_id,
            league_name: LEAGUE_NAME,
            season: SEASON,
            home_team: candidate.home_team,
            away_team: candidate.away_team,
            match_date: candidate.match_date,
            status: candidate.status,
            is_finished: candidate.status === 'finished',
            data_source: SOURCE,
            pipeline_status: 'pending',
        };
        for (const [field, expectedValue] of Object.entries(expected)) {
            const actualValue = row[field];
            const comparableActual = field === 'data_source' ? normalizeLower(actualValue) : normalizeText(actualValue);
            const comparableExpected =
                field === 'data_source' ? normalizeLower(expectedValue) : normalizeText(expectedValue);
            if (field === 'is_finished') {
                if (Boolean(actualValue) !== Boolean(expectedValue)) {
                    mismatches.push(`${candidate.match_id}: ${field} expected ${expectedValue} got ${actualValue}`);
                    teamDateStatusMismatchCount += 1;
                }
                continue;
            }
            if (comparableActual !== comparableExpected) {
                mismatches.push(`${candidate.match_id}: ${field} expected ${expectedValue} got ${actualValue}`);
                if (field === 'external_id') externalIdMismatchCount += 1;
                if (['home_team', 'away_team', 'match_date', 'status'].includes(field)) {
                    teamDateStatusMismatchCount += 1;
                }
            }
        }
    }

    const matchesFoundCount = candidates.filter(candidate => byMatchId.has(candidate.match_id)).length;
    const missingMatchesCount = TARGET_COUNT - matchesFoundCount;
    return {
        ok: missingMatchesCount === 0 && mismatches.length === 0,
        expected_candidate_count: TARGET_COUNT,
        matches_found_count: matchesFoundCount,
        missing_matches_count: missingMatchesCount,
        identity_mismatch_count: mismatches.length,
        external_id_mismatch_count: externalIdMismatchCount,
        team_date_status_mismatch_count: teamDateStatusMismatchCount,
        mismatches,
    };
}

function buildRawConstraintReadiness(constraints = []) {
    const rawConstraints = constraints.map(row => ({
        conname: normalizeText(row.conname),
        contype: normalizeText(row.contype),
        definition: normalizeText(row.definition),
    }));
    const uniqueMatchIdDataVersionPresent = rawConstraints.some(
        row => row.contype === 'u' && /\bUNIQUE\s*\(\s*match_id\s*,\s*data_version\s*\)/i.test(row.definition)
    );
    const oldUniqueMatchIdPresent = rawConstraints.some(
        row => row.contype === 'u' && /\bUNIQUE\s*\(\s*match_id\s*\)/i.test(row.definition)
    );
    const rawMatchDataFkPresent = rawConstraints.some(
        row =>
            row.contype === 'f' &&
            /FOREIGN KEY\s*\(\s*match_id\s*\)\s+REFERENCES\s+matches\s*\(\s*match_id\s*\)/i.test(row.definition)
    );
    const errors = [];
    if (!uniqueMatchIdDataVersionPresent) errors.push('raw_match_data UNIQUE(match_id,data_version) missing');
    if (oldUniqueMatchIdPresent) errors.push('old raw_match_data UNIQUE(match_id) still present');
    if (!rawMatchDataFkPresent) errors.push('raw_match_data match_id FK missing');
    return {
        ok: errors.length === 0,
        errors,
        raw_constraints: rawConstraints,
        unique_match_id_data_version_present: uniqueMatchIdDataVersionPresent,
        old_unique_match_id_present: oldUniqueMatchIdPresent,
        raw_match_data_fk_present: rawMatchDataFkPresent,
    };
}

function buildRawReadiness({
    dbCounts = {},
    matchVerification = {},
    rawConstraintReadiness = {},
    existingV2Rows = [],
} = {}) {
    const existingV2RawRowsForCandidates = existingV2Rows.length;
    const errors = [];
    if (!matchVerification.ok) errors.push('raw write FK prerequisite is not satisfied for all candidates');
    if (existingV2RawRowsForCandidates > 0) errors.push('candidate fotmob_pageprops_v2 raw rows already exist');
    if (Number(dbCounts.raw_match_data) !== EXPECTED_DB_COUNTS.raw_match_data) {
        errors.push(`raw_match_data=${dbCounts.raw_match_data} expected ${EXPECTED_DB_COUNTS.raw_match_data}`);
    }
    if (!rawConstraintReadiness.ok) errors.push(...rawConstraintReadiness.errors);
    return {
        ok: errors.length === 0,
        errors,
        raw_match_data_fk_prerequisite_status: matchVerification.ok ? 'satisfied' : 'blocked',
        existing_v2_raw_rows_for_candidates: existingV2RawRowsForCandidates,
        raw_match_data_current_count: Number(dbCounts.raw_match_data || 0),
        unique_match_id_data_version_status: rawConstraintReadiness.unique_match_id_data_version_present
            ? 'present'
            : 'missing',
        old_unique_match_id_status: rawConstraintReadiness.old_unique_match_id_present ? 'present' : 'absent',
        raw_match_data_fk_status: rawConstraintReadiness.raw_match_data_fk_present ? 'present' : 'missing',
        eligible_raw_insert_count: errors.length === 0 ? TARGET_COUNT : 0,
        expected_raw_match_data_after_retry: EXPECTED_DB_COUNTS.raw_match_data + TARGET_COUNT,
    };
}

function buildAuditPayload({
    input = {},
    manifest = {},
    protectedTableRows = [],
    candidateMatchRows = [],
    rawConstraintRows = [],
    existingV2Rows = [],
    generatedAt = null,
} = {}) {
    const dbCounts = normalizeTableRows(protectedTableRows);
    const dbCountErrors = validateExpectedCounts(dbCounts);
    const manifestGate = validateManifestForAudit(manifest);
    const candidateValidation = validateCandidateTargets(
        Array.isArray(manifest.candidate_targets) ? manifest.candidate_targets : []
    );
    const matchVerification = buildMatchesIdentityVerification(candidateValidation.candidates, candidateMatchRows);
    const rawConstraintReadiness = buildRawConstraintReadiness(rawConstraintRows);
    const rawReadiness = buildRawReadiness({
        dbCounts,
        matchVerification,
        rawConstraintReadiness,
        existingV2Rows,
    });
    const gateErrors = [
        ...dbCountErrors.map(error => `DB_BASELINE_INVALID:${error}`),
        ...manifestGate.errors,
        ...candidateValidation.errors,
        ...matchVerification.mismatches,
        ...rawReadiness.errors,
    ];
    if (candidateValidation.duplicate_match_id_count > 0) gateErrors.push('duplicate candidate match_id');
    if (candidateValidation.duplicate_external_id_count > 0) gateErrors.push('duplicate candidate external_id');
    const ready = gateErrors.length === 0 && candidateValidation.candidates.length === TARGET_COUNT;

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
        db_baseline: dbCounts,
        manifest_gate: manifestGate,
        candidate_validation: candidateValidation,
        matches_identity_verification: matchVerification,
        raw_constraint_readiness: rawConstraintReadiness,
        raw_write_readiness: rawReadiness,
        raw_write_retry_readiness_status: ready ? 'ready_for_renewed_authorization' : 'blocked',
        fk_prerequisite_status: matchVerification.ok ? 'satisfied' : 'blocked',
        eligible_raw_insert_count: ready ? TARGET_COUNT : 0,
        expected_raw_match_data_after_retry: EXPECTED_DB_COUNTS.raw_match_data + TARGET_COUNT,
        required_next_step: ready ? NEXT_STEP_AFTER_READY : 'review_blocked_raw_write_retry_readiness',
        db_write_executed: false,
        matches_write_executed: false,
        raw_match_data_write_executed: false,
        network_executed: false,
        match_detail_fetch_executed: false,
        parser_features_training_executed: false,
    };
}

function updateManifestWithReadiness(manifest = {}, payload = {}, generatedAt = null) {
    const ready = payload.ok === true;
    const updated = {
        ...manifest,
        post_seed_matches_identity_verification_status: ready ? 'completed' : 'blocked',
        post_seed_matches_identity_verification_at: generatedAt,
        raw_write_fk_prerequisite_status: payload.fk_prerequisite_status,
        raw_write_retry_readiness_status: payload.raw_write_retry_readiness_status,
        eligible_raw_insert_count: payload.eligible_raw_insert_count,
        expected_raw_match_data_after_retry: payload.expected_raw_match_data_after_retry,
        required_next_step: payload.required_next_step,
        post_seed_matches_identity_raw_write_readiness_audit_result: {
            phase: PHASE,
            generated_at: generatedAt,
            ok: payload.ok,
            blocked_reason: payload.blocked_reason,
            matches_identity_verification: payload.matches_identity_verification,
            raw_write_readiness: payload.raw_write_readiness,
        },
    };
    updated.candidate_targets = (updated.candidate_targets || []).map(target => ({
        ...target,
        post_seed_matches_identity_verification_status: ready ? 'completed' : 'blocked',
        raw_write_fk_prerequisite_status: payload.fk_prerequisite_status,
        raw_write_retry_readiness_status: ready ? 'ready_for_renewed_authorization' : 'blocked',
        raw_write_retry_readiness_failure_reason: ready ? null : payload.blocked_reason,
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
    const manifestGate = payload.manifest_gate || {};
    const candidateValidation = payload.candidate_validation || {};
    const matchesVerification = payload.matches_identity_verification || {};
    const rawReadiness = payload.raw_write_readiness || {};
    const rawConstraints = payload.raw_constraint_readiness || {};
    return `# Post-Seed Matches Identity Raw Write Readiness Audit - Phase 5.21L2V2

## 1. Executive summary

- L2V1 successfully inserted 50 matches identity rows.
- L2V2 is post-seed verification / raw write retry readiness audit only.
- It does not write DB.
- It does not touch FotMob/network.
- It does not run parser/features/training.
- Raw write retry still requires separate renewed authorization.

## 2. Current DB baseline

- matches=${payload.db_baseline?.matches}
- raw_match_data=${payload.db_baseline?.raw_match_data}
- bookmaker_odds_history=${payload.db_baseline?.bookmaker_odds_history}
- l3_features=${payload.db_baseline?.l3_features}
- match_features_training=${payload.db_baseline?.match_features_training}
- predictions=${payload.db_baseline?.predictions}

## 3. Manifest input summary

- manifest path=${payload.manifest_path}
- candidate_targets=${manifestGate.candidate_targets}
- known_completed_targets=${manifestGate.known_completed_targets}
- matches_identity_seed_execution_status=${manifestGate.matches_identity_seed_execution_status}
- matches_seed_status distribution=${JSON.stringify(manifestGate.matches_seed_status_distribution || {})}
- baseline_hash_ready_count=${candidateValidation.baseline_hash_ready_count}

## 4. Matches identity verification

- expected_candidate_count=${matchesVerification.expected_candidate_count}
- matches_found_count=${matchesVerification.matches_found_count}
- missing_matches_count=${matchesVerification.missing_matches_count}
- identity_mismatch_count=${matchesVerification.identity_mismatch_count}
- external_id_mismatch_count=${matchesVerification.external_id_mismatch_count}
- team_date_status_mismatch_count=${matchesVerification.team_date_status_mismatch_count}

## 5. Raw write FK / existing row readiness

- raw_match_data FK prerequisite status=${rawReadiness.raw_match_data_fk_prerequisite_status}
- existing_v2_raw_rows_for_candidates=${rawReadiness.existing_v2_raw_rows_for_candidates}
- raw_match_data current count=${rawReadiness.raw_match_data_current_count}
- UNIQUE(match_id,data_version) present=${rawConstraints.unique_match_id_data_version_present}
- old UNIQUE(match_id) absent=${!rawConstraints.old_unique_match_id_present}
- raw_match_data.match_id FK present=${rawConstraints.raw_match_data_fk_present}
- eligible_raw_insert_count=${rawReadiness.eligible_raw_insert_count}
- expected_raw_match_data_after_retry=${rawReadiness.expected_raw_match_data_after_retry}

Raw constraints:
${renderRows(rawConstraints.raw_constraints || [], ['conname', 'contype', 'definition'])}

## 6. Readiness decision

- raw_write_retry_readiness_status=${payload.raw_write_retry_readiness_status}
- fk_prerequisite_status=${payload.fk_prerequisite_status}
- blockers=${payload.blocked_reason || 'none'}
- required_next_step=${payload.required_next_step}

## 7. Manifest update result

- manifest updated=${payload.manifest_updated}
- post_seed_matches_identity_verification_status=${payload.post_seed_matches_identity_verification_status}
- raw_write_fk_prerequisite_status=${payload.raw_write_fk_prerequisite_status}
- raw_write_retry_readiness_status=${payload.raw_write_retry_readiness_status}
- eligible_raw_insert_count=${payload.eligible_raw_insert_count}
- expected_raw_match_data_after_retry=${payload.expected_raw_match_data_after_retry}
- required_next_step=${payload.required_next_step}

## 8. DB safety result

DB row counts unchanged during audit:

- matches=${payload.db_baseline?.matches}
- raw_match_data=${payload.db_baseline?.raw_match_data}
- bookmaker_odds_history=${payload.db_baseline?.bookmaker_odds_history}
- l3_features=${payload.db_baseline?.l3_features}
- match_features_training=${payload.db_baseline?.match_features_training}
- predictions=${payload.db_baseline?.predictions}

## 9. Verification results

- new readiness audit tests: pending before PR
- V1 execution tests: pending before PR
- V0 planning tests: pending before PR
- L2V execution tests: pending before PR
- L2U planning tests: pending before PR
- L2T preflight tests: pending before PR
- FotMobRawDetailFetcher tests: pending before PR
- npm test: pending before PR
- npm run test:coverage: pending before PR
- eslint / prettier / git diff: pending before PR
- DB row counts unchanged during audit: pending final safety check
- l1-config residue absent: pending final safety check
- docs/_staging_preview absent: pending final safety check
- PR CI: pending
- main push CI: pending

## 10. Recommended next phase

Phase 5.21L2V3: renewed controlled pageProps v2 raw write execution.

Requirements: explicit renewed final DB-write authorization, raw_match_data write only, no matches write, no odds/features/training/prediction, recapture pageProps, compare stable_pageprops_payload_v1 hash with manifest baseline_hash, controlled transaction, expected raw_match_data 18 -> 68, and no parser/features/training.

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

async function loadRawMatchDataConstraints(client) {
    const result = await queryReadOnly(
        client,
        `
SELECT conname, contype, pg_get_constraintdef(c.oid) AS definition
FROM pg_constraint c
JOIN pg_class t ON c.conrelid = t.oid
WHERE t.relname = $1
ORDER BY conname
`,
        ['raw_match_data']
    );
    return result.rows || [];
}

async function loadExistingCandidateV2Rows(client, candidates = []) {
    const matchIds = candidates.map(candidate => candidate.match_id).filter(Boolean);
    const result = await queryReadOnly(
        client,
        `
SELECT match_id, data_version, data_hash
FROM raw_match_data
WHERE match_id = ANY($1::text[]) AND data_version = $2
ORDER BY match_id
`,
        [matchIds, DATA_VERSION]
    );
    return result.rows || [];
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

async function runCli(argv = process.argv.slice(2), dependencies = {}) {
    const output = dependencies.output || (payload => process.stdout.write(`${JSON.stringify(payload, null, 2)}\n`));
    const parsed = Array.isArray(argv) ? parseArgs(argv) : argv;
    const validation = validateAuditInput(parsed);
    if (!validation.ok) {
        const payload = buildFailurePayload({
            input: parsed,
            reason: `INPUT_BLOCKED:${validation.errors.join(';')}`,
            errors: validation.errors,
        });
        output(payload);
        return { status: 1, payload };
    }

    const input = validation.value;
    const generatedAt = dependencies.generatedAt || new Date().toISOString();
    const pool = dependencies.client ? null : dependencies.pool || createDefaultPool();
    const { client, release } = await getClient(dependencies.client || pool);

    try {
        const manifest = dependencies.manifest || readJsonFile(input.manifest);
        const candidatesForSelect = Array.isArray(manifest.candidate_targets)
            ? manifest.candidate_targets.map(normalizeCandidateTarget)
            : [];
        const protectedTableRows = dependencies.protectedTableRows || (await loadProtectedTableBaselineRows(client));
        const candidateMatchRows =
            dependencies.candidateMatchRows || (await loadCandidateMatches(client, candidatesForSelect));
        const rawConstraintRows = dependencies.rawConstraintRows || (await loadRawMatchDataConstraints(client));
        const existingV2Rows =
            dependencies.existingV2Rows || (await loadExistingCandidateV2Rows(client, candidatesForSelect));
        let payload = buildAuditPayload({
            input,
            manifest,
            protectedTableRows,
            candidateMatchRows,
            rawConstraintRows,
            existingV2Rows,
            generatedAt,
        });
        const updatedManifest = updateManifestWithReadiness(manifest, payload, generatedAt);
        payload = {
            ...payload,
            manifest_updated: dependencies.writeManifest !== false,
            report_updated: dependencies.writeReport !== false,
            post_seed_matches_identity_verification_status:
                updatedManifest.post_seed_matches_identity_verification_status,
            raw_write_fk_prerequisite_status: updatedManifest.raw_write_fk_prerequisite_status,
            raw_write_retry_readiness_status: updatedManifest.raw_write_retry_readiness_status,
            required_next_step: updatedManifest.required_next_step,
        };
        if (dependencies.writeManifest !== false) {
            (dependencies.writeManifestFile || writeJsonFile)(input.manifest, updatedManifest);
        }
        if (dependencies.writeReport !== false) {
            (dependencies.writeReportFile || writeReportFile)(REPORT_PATH, buildReport(payload));
        }
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
    DATA_VERSION,
    EXPECTED_DB_COUNTS,
    NEXT_STEP_AFTER_READY,
    parseArgs,
    normalizeBooleanFlag,
    validateAuditInput,
    validateManifestForAudit,
    validateCandidateTargets,
    buildMatchesIdentityVerification,
    buildRawConstraintReadiness,
    buildRawReadiness,
    buildAuditPayload,
    updateManifestWithReadiness,
    buildReport,
    queryReadOnly,
    loadProtectedTableBaselineRows,
    loadCandidateMatches,
    loadRawMatchDataConstraints,
    loadExistingCandidateV2Rows,
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
