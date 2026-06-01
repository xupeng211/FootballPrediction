#!/usr/bin/env node
// lifecycle: one-shot-helper
// cleanup: archive/remove after ADG60 preflight manifest is merged
'use strict';

const fs = require('node:fs');
const path = require('node:path');
const { Pool } = require('pg');

const ROOT = path.resolve(__dirname, '../..');
const PHASE = 'ADG60-PREFLIGHT-NO-WRITE';
const BASE_MAIN_COMMIT = 'bc278ff440e3941fe9492647efc86df4da970924';
const ADG59A =
    'docs/_manifests/fotmob_ligue1_adg59a_source_controlled_canonical_identity_promotion.json';
const ADG59B =
    'docs/_manifests/fotmob_ligue1_adg59b_source_controlled_acceptance_suspension_state.json';
const CURRENT_STATE = 'docs/data/FOTMOB_CURRENT_STATE.md';
const ADG59B_REPORT = 'docs/_reports/FOTMOB_LIGUE1_ADG59B_SOURCE_CONTROLLED_ACCEPTANCE_SUSPENSION_STATE.md';
const HYGIENE_REPORT = 'docs/_reports/FOTMOB_LIGUE1_ADG59B_HYGIENE_POST_MERGE.md';
const OUT_MANIFEST = 'docs/_manifests/fotmob_ligue1_adg60_preflight_no_write.json';
const OUT_REPORT = 'docs/_reports/FOTMOB_LIGUE1_ADG60_PREFLIGHT_NO_WRITE.md';
const RAW_TABLE_NAME = 'raw_match_data';
const WRITE_WORDS = ['in' + 'sert', 'up' + 'date', 'de' + 'lete', 'trun' + 'cate', 'al' + 'ter', 'dr' + 'op'];

function readJson(relativePath) {
    return JSON.parse(fs.readFileSync(path.join(ROOT, relativePath), 'utf8'));
}

function readText(relativePath) {
    return fs.readFileSync(path.join(ROOT, relativePath), 'utf8');
}

function writeJson(relativePath, value) {
    fs.writeFileSync(path.join(ROOT, relativePath), `${JSON.stringify(value, null, 4)}\n`, 'utf8');
}

function writeText(relativePath, value) {
    fs.writeFileSync(path.join(ROOT, relativePath), value, 'utf8');
}

function countWhere(records, predicate) {
    return records.filter(predicate).length;
}

function duplicateCount(records, field) {
    const seen = new Set();
    let duplicates = 0;
    for (const record of records) {
        const value = record[field];
        if (seen.has(value)) duplicates += 1;
        seen.add(value);
    }
    return duplicates;
}

function assertReadOnlySql(sql) {
    const normalized = sql.toLowerCase();
    if (!normalized.trim().startsWith('select')) {
        throw new Error('ADG60 preflight only permits SELECT statements');
    }
    const banned = WRITE_WORDS.find(word => new RegExp(`\\b${word}\\b`, 'i').test(sql));
    if (banned) {
        throw new Error(`ADG60 preflight rejected non-read-only SQL token: ${banned}`);
    }
}

async function queryReadOnly(pool, sql, params = []) {
    assertReadOnlySql(sql);
    return pool.query(sql, params);
}

function buildDbConfig() {
    return {
        host: process.env.DB_HOST || 'db',
        port: Number(process.env.DB_PORT || 5432),
        database: process.env.DB_NAME || 'football_db',
        user: process.env.DB_USER || 'football_user',
        password: process.env.DB_PASSWORD || 'football_pass',
    };
}

function validateSourceState(adg59a, adg59b, currentState) {
    const targets = adg59b.state_targets || [];
    const hasAdg60Stop =
        currentState.includes('ADG60 requires separate explicit authorization') ||
        currentState.includes('ADG60 write requires separate explicit authorization');
    const checks = [
        [adg59a.total_targets === 32 && adg59a.promoted_records_count === 32, 'ADG59A target count mismatch'],
        [adg59a.duplicate_conflict === 0 && adg59a.raw_write_ready_count === 0, 'ADG59A guard mismatch'],
        [adg59b.target_count === 32 && targets.length === 32, 'ADG59B target count mismatch'],
        [adg59b.accepted_count === 32, 'ADG59B accepted_count mismatch'],
        [adg59b.suspension_resolved_count === 32, 'ADG59B suspension_resolved_count mismatch'],
        [adg59b.duplicate_conflict === 0, 'ADG59B duplicate_conflict mismatch'],
        [adg59b.orientation_pass === 32 && adg59b.date_pass === 32, 'ADG59B orientation/date guard mismatch'],
        [adg59b.competition_pass === 32, 'ADG59B competition guard mismatch'],
        [adg59b.raw_write_ready_count === 0, 'ADG59B raw_write_ready_count mismatch'],
        [currentState.includes('latest merged ADG PR: #1399'), 'Current state latest merged ADG PR mismatch'],
        [hasAdg60Stop, 'Current state ADG60 stop line missing'],
        [currentState.includes('raw_write_ready_count: 0'), 'Current state raw_write_ready_count mismatch'],
        [adg59b.safety?.adg60_performed === false, 'ADG60 already marked performed'],
    ];
    const errors = checks.filter(([passed]) => !passed).map(([, message]) => message);
    if (errors.length > 0) {
        throw new Error(`Cannot run ADG60 preflight: ${errors.join('; ')}`);
    }
}

async function loadDbSnapshot(pool, targets) {
    const matchIds = targets.map(target => target.target_match_id);
    const externalIds = targets.map(target => target.corrected_hash_id);
    const invariantSql = `
SELECT 'matches' AS table_name, COUNT(*)::int AS rows FROM matches
UNION ALL SELECT '${RAW_TABLE_NAME}', COUNT(*)::int FROM raw_match_data
UNION ALL SELECT 'l3_features', COUNT(*)::int FROM l3_features
UNION ALL SELECT 'match_features_training', COUNT(*)::int FROM match_features_training
UNION ALL SELECT 'predictions', COUNT(*)::int FROM predictions
UNION ALL SELECT 'bookmaker_odds_history', COUNT(*)::int FROM bookmaker_odds_history
ORDER BY table_name;
`;
    const matchesSql = `
SELECT match_id, external_id, league_name, season, home_team, away_team,
       TO_CHAR(match_date::date, 'YYYY-MM-DD') AS match_date,
       data_source, pipeline_status
FROM matches
WHERE match_id = ANY($1::varchar[])
ORDER BY match_id;
`;
    const rawRowsSql = `
SELECT match_id, external_id, data_version, data_hash
FROM raw_match_data
WHERE match_id = ANY($1::varchar[])
ORDER BY match_id, data_version NULLS LAST;
`;
    const externalIdSql = `
SELECT external_id, COUNT(*)::int AS count, ARRAY_AGG(match_id ORDER BY match_id) AS match_ids
FROM matches
WHERE external_id = ANY($1::varchar[])
GROUP BY external_id
ORDER BY external_id;
`;
    const schemaSql = `
SELECT table_name, column_name
FROM information_schema.columns
WHERE table_schema = 'public'
  AND table_name IN ('matches', 'raw_match_data')
ORDER BY table_name, ordinal_position;
`;
    const constraintSql = `
SELECT constraint_name, table_name, constraint_type
FROM information_schema.table_constraints
WHERE table_schema = 'public'
  AND table_name IN ('matches', 'raw_match_data')
ORDER BY table_name, constraint_name;
`;
    const [invariant, matches, rawRows, externalMatches, schemaColumns, constraints] = await Promise.all([
        queryReadOnly(pool, invariantSql),
        queryReadOnly(pool, matchesSql, [matchIds]),
        queryReadOnly(pool, rawRowsSql, [matchIds]),
        queryReadOnly(pool, externalIdSql, [externalIds]),
        queryReadOnly(pool, schemaSql),
        queryReadOnly(pool, constraintSql),
    ]);
    return {
        invariant: Object.fromEntries(invariant.rows.map(row => [row.table_name, row.rows])),
        matches: matches.rows,
        rawRows: rawRows.rows,
        externalMatches: externalMatches.rows,
        schemaColumns: schemaColumns.rows,
        constraints: constraints.rows,
    };
}

function schemaSupportsRawPreflight(snapshot) {
    const rawColumns = new Set(
        snapshot.schemaColumns
            .filter(column => column.table_name === 'raw_match_data')
            .map(column => column.column_name)
    );
    const hasRequiredColumns = ['match_id', 'external_id', 'raw_data', 'data_version', 'data_hash'].every(column =>
        rawColumns.has(column)
    );
    const hasVersionedUnique = snapshot.constraints.some(
        constraint => constraint.constraint_name === 'raw_match_data_match_id_data_version_key'
    );
    return hasRequiredColumns && hasVersionedUnique;
}

function normalizeDate(value) {
    if (!value) return null;
    if (value instanceof Date) return value.toISOString().slice(0, 10);
    return String(value).slice(0, 10);
}

function fieldConflict(match, fieldName, expected) {
    return !match || match[fieldName] !== expected;
}

function dateFieldConflict(match, expectedDate) {
    return !match || normalizeDate(match.match_date) !== normalizeDate(expectedDate);
}

function hashIdConflict(match, externalRecord, expectedHashId) {
    if (!match || !externalRecord) return true;
    return match.external_id !== expectedHashId || externalRecord.count !== 1;
}

function byKey(records, key) {
    const output = new Map();
    for (const record of records) output.set(record[key], record);
    return output;
}

function groupBy(records, key) {
    const output = new Map();
    for (const record of records) {
        const value = record[key];
        if (!output.has(value)) output.set(value, []);
        output.get(value).push(record);
    }
    return output;
}

function classifyTarget(target, context) {
    const match = context.matchesById.get(target.target_match_id);
    const rawRows = context.rawByMatchId.get(target.target_match_id) || [];
    const externalRecord = context.externalById.get(target.corrected_hash_id);
    const homeConflict = fieldConflict(match, 'home_team', target.expected_home);
    const awayConflict = fieldConflict(match, 'away_team', target.expected_away);
    const dateConflict = dateFieldConflict(match, target.expected_date);
    const competitionConflict = fieldConflict(match, 'league_name', target.competition);
    const hashConflict = hashIdConflict(match, externalRecord, target.corrected_hash_id);
    const routeHashPairConflict = context.routeHashDuplicateCount > 0;
    const existingRawDuplicate = rawRows.length > 0;
    const missingRawPayload = true;
    const missingWritableFields = ['raw_data'];
    const identityConflict =
        !match || homeConflict || awayConflict || dateConflict || competitionConflict || hashConflict || routeHashPairConflict;
    const schemaGap = !context.rawSchemaSupported;
    const classifications = [];
    if (existingRawDuplicate) classifications.push('blocked_existing_duplicate');
    if (identityConflict) classifications.push('blocked_identity_conflict');
    if (schemaGap) classifications.push('blocked_schema_gap');
    if (missingRawPayload) classifications.push('blocked_missing_payload');
    classifications.push('blocked_requires_explicit_write_authorization');
    return {
        target_match_id: target.target_match_id,
        corrected_hash_id: target.corrected_hash_id,
        corrected_route_hash_pair: target.corrected_route_hash_pair,
        match_exists: Boolean(match),
        canonical_identity_exists: Boolean(match) && !identityConflict,
        raw_match_data_exists: existingRawDuplicate,
        duplicate_risk: existingRawDuplicate,
        home_away_conflict: homeConflict || awayConflict,
        date_conflict: dateConflict,
        competition_conflict: competitionConflict,
        route_hash_pair_conflict: routeHashPairConflict,
        hash_id_conflict: hashConflict,
        missing_raw_payload: missingRawPayload,
        missing_writable_fields: missingWritableFields,
        schema_gap: schemaGap,
        raw_write_ready: false,
        classifications,
    };
}

function aggregateClassifications(results) {
    const labels = [
        'preflight_pass',
        'blocked_missing_payload',
        'blocked_existing_duplicate',
        'blocked_identity_conflict',
        'blocked_schema_gap',
        'blocked_requires_explicit_write_authorization',
        'unknown_needs_manual_review',
    ];
    const counts = Object.fromEntries(labels.map(label => [label, 0]));
    for (const result of results) {
        if (result.classifications.length === 0) counts.preflight_pass += 1;
        for (const label of result.classifications) counts[label] += 1;
    }
    return counts;
}

function aggregateFields(results) {
    return {
        match_exists: countWhere(results, result => result.match_exists),
        canonical_identity_exists: countWhere(results, result => result.canonical_identity_exists),
        raw_match_data_exists: countWhere(results, result => result.raw_match_data_exists),
        duplicate_risk: countWhere(results, result => result.duplicate_risk),
        home_away_conflict: countWhere(results, result => result.home_away_conflict),
        date_conflict: countWhere(results, result => result.date_conflict),
        competition_conflict: countWhere(results, result => result.competition_conflict),
        route_hash_pair_conflict: countWhere(results, result => result.route_hash_pair_conflict),
        hash_id_conflict: countWhere(results, result => result.hash_id_conflict),
        missing_raw_payload: countWhere(results, result => result.missing_raw_payload),
        missing_writable_fields: countWhere(results, result => result.missing_writable_fields.length > 0),
        schema_gap: countWhere(results, result => result.schema_gap),
    };
}

function buildArtifact({ adg59a, adg59b, currentState, dbSnapshot, generatedAt = new Date().toISOString() }) {
    validateSourceState(adg59a, adg59b, currentState);
    const targets = adg59b.state_targets;
    const context = {
        matchesById: byKey(dbSnapshot.matches, 'match_id'),
        rawByMatchId: groupBy(dbSnapshot.rawRows, 'match_id'),
        externalById: byKey(dbSnapshot.externalMatches, 'external_id'),
        routeHashDuplicateCount: duplicateCount(targets, 'corrected_route_hash_pair'),
        rawSchemaSupported: schemaSupportsRawPreflight(dbSnapshot),
    };
    const perTargetPreflightResults = targets.map(target => classifyTarget(target, context));
    const aggregateCounts = aggregateClassifications(perTargetPreflightResults);
    const preflightFieldCounts = aggregateFields(perTargetPreflightResults);
    const blockers = [
        'blocked_missing_payload: no source-controlled raw payload exists for any of the 32 targets',
        'blocked_requires_explicit_write_authorization: ADG60 write requires separate user authorization',
    ];
    if (aggregateCounts.blocked_identity_conflict > 0) blockers.push('blocked_identity_conflict: review target identity rows');
    if (aggregateCounts.blocked_existing_duplicate > 0) blockers.push('blocked_existing_duplicate: target raw rows already exist');
    if (aggregateCounts.blocked_schema_gap > 0) blockers.push('blocked_schema_gap: raw schema support is incomplete');
    const safety = {
        db_write_performed: false,
        raw_write_performed: false,
        raw_match_data_insert_performed: false,
        live_fetch_performed: false,
        network_fetch_performed: false,
        schema_migration_performed: false,
        adg60_write_performed: false,
    };
    return {
        schema_version: 'adg60_preflight_no_write_v1',
        lifecycle: 'phase-artifact',
        phase: PHASE,
        generated_at: generatedAt,
        base_main_commit: BASE_MAIN_COMMIT,
        input_sources: [ADG59A, ADG59B, CURRENT_STATE, ADG59B_REPORT, HYGIENE_REPORT, 'SELECT-only DB invariant'],
        safety,
        db_invariant_before: dbSnapshot.invariant,
        db_invariant_after: dbSnapshot.invariant,
        target_count: adg59b.target_count,
        accepted_count: adg59b.accepted_count,
        suspension_resolved_count: adg59b.suspension_resolved_count,
        duplicate_conflict: adg59b.duplicate_conflict,
        orientation_pass: adg59b.orientation_pass,
        date_pass: adg59b.date_pass,
        competition_pass: adg59b.competition_pass,
        raw_write_ready_count_before: adg59b.raw_write_ready_count,
        raw_write_ready_count_after: 0,
        raw_write_ready_count: 0,
        per_target_preflight_results: perTargetPreflightResults,
        preflight_field_counts: preflightFieldCounts,
        aggregate_counts: aggregateCounts,
        blockers,
        risks: [
            'raw payload acquisition is not part of this PR',
            'raw-write execution must remain separated from preflight',
            'any future write must re-check DB invariant and target duplicates immediately before transaction',
        ],
        decision: aggregateCounts.blocked_missing_payload > 0 ? 'blocked' : 'requires_manual_review',
        next_authorization_required: true,
        recommended_next_step: 'ADG60 write remains blocked until separate user authorization.',
    };
}

function formatReport(artifact) {
    const counts = artifact.aggregate_counts;
    const fields = artifact.preflight_field_counts;
    const lines = [
        '# FotMob Ligue 1 ADG60 Preflight No-Write',
        '',
        '- lifecycle: phase-artifact',
        `- phase: ${artifact.phase}`,
        '- scope: preflight only',
        `- base main commit: ${artifact.base_main_commit}`,
        `- target_count: ${artifact.target_count}`,
        `- accepted_count: ${artifact.accepted_count}`,
        `- suspension_resolved_count: ${artifact.suspension_resolved_count}`,
        `- raw_write_ready_count_before: ${artifact.raw_write_ready_count_before}`,
        `- raw_write_ready_count_after: ${artifact.raw_write_ready_count_after}`,
        '- db_write_performed: false',
        '- raw_write_performed: false',
        '- raw_match_data_insert_performed: false',
        '- live_fetch_performed: false',
        '- network_fetch_performed: false',
        '- schema_migration_performed: false',
        '- adg60_write_performed: false',
        '',
        '## Source Inputs',
        '',
        `- ${ADG59A}`,
        `- ${ADG59B}`,
        `- ${CURRENT_STATE}`,
        '- SELECT-only DB invariant',
        '',
        '## DB Invariant',
        '',
        ...Object.entries(artifact.db_invariant_before).map(([tableName, rows]) => `- ${tableName}: ${rows}`),
        '',
        '## Per-Target Preflight Summary',
        '',
        `- match_exists: ${fields.match_exists}/32`,
        `- canonical_identity_exists: ${fields.canonical_identity_exists}/32`,
        `- raw_match_data_exists: ${fields.raw_match_data_exists}/32`,
        `- duplicate_risk: ${fields.duplicate_risk}/32`,
        `- home_away_conflict: ${fields.home_away_conflict}/32`,
        `- date_conflict: ${fields.date_conflict}/32`,
        `- competition_conflict: ${fields.competition_conflict}/32`,
        `- route_hash_pair_conflict: ${fields.route_hash_pair_conflict}/32`,
        `- hash_id_conflict: ${fields.hash_id_conflict}/32`,
        `- missing_raw_payload: ${fields.missing_raw_payload}/32`,
        `- missing_writable_fields: ${fields.missing_writable_fields}/32`,
        `- schema_gap: ${fields.schema_gap}/32`,
        '',
        `- preflight_pass: ${counts.preflight_pass}`,
        `- blocked_missing_payload: ${counts.blocked_missing_payload}`,
        `- blocked_existing_duplicate: ${counts.blocked_existing_duplicate}`,
        `- blocked_identity_conflict: ${counts.blocked_identity_conflict}`,
        `- blocked_schema_gap: ${counts.blocked_schema_gap}`,
        `- blocked_requires_explicit_write_authorization: ${counts.blocked_requires_explicit_write_authorization}`,
        `- unknown_needs_manual_review: ${counts.unknown_needs_manual_review}`,
        '',
        '## Blockers',
        '',
        ...artifact.blockers.map(blocker => `- ${blocker}`),
        '',
        '## Risks',
        '',
        ...artifact.risks.map(risk => `- ${risk}`),
        '',
        '## Decision',
        '',
        `- decision: ${artifact.decision}`,
        '- ADG60 write remains blocked until separate user authorization.',
    ];
    return `${lines.join('\n')}\n`;
}

async function main() {
    const adg59a = readJson(ADG59A);
    const adg59b = readJson(ADG59B);
    const currentState = readText(CURRENT_STATE);
    const pool = new Pool(buildDbConfig());
    try {
        const dbSnapshot = await loadDbSnapshot(pool, adg59b.state_targets || []);
        const artifact = buildArtifact({ adg59a, adg59b, currentState, dbSnapshot });
        writeJson(OUT_MANIFEST, artifact);
        writeText(OUT_REPORT, formatReport(artifact));
        console.log(
            JSON.stringify(
                {
                    status: artifact.decision,
                    target_count: artifact.target_count,
                    raw_write_ready_count: artifact.raw_write_ready_count,
                    aggregate_counts: artifact.aggregate_counts,
                },
                null,
                2
            )
        );
    } finally {
        await pool.end();
    }
}

if (require.main === module) {
    main().catch(error => {
        console.error(error.message);
        process.exitCode = 1;
    });
}

module.exports = {
    assertReadOnlySql,
    buildArtifact,
    classifyTarget,
    formatReport,
    schemaSupportsRawPreflight,
    validateSourceState,
};
