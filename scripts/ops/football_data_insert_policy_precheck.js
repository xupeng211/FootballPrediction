#!/usr/bin/env node
'use strict';

const crypto = require('crypto');
const fs = require('fs');

const { runDryRun, parseArgs: parseDryRunArgs } = require('./football_data_adapter_dry_run');
const {
    READ_ONLY_BEGIN_SQL,
    READ_ONLY_ROLLBACK_SQL,
    runCandidatePrechecks,
    buildDbConfig,
    assertSelectOnlySql,
} = require('./football_data_duplicate_precheck');

const INSERT_POLICY_PHASE = 'PHASE4.66C_FOOTBALL_DATA_INSERT_POLICY';
const MATCH_ID_STRATEGY = 'fd_<league>_<season>_<date>_<home>_<away>_<hash8>';
const DEFAULT_MATCH_ID_MAX_LENGTH = 64;
const APPROVED_FOR_DB_WRITE = 'approved_for_db_write';

const MATCH_ID_COLUMN_SQL = `
SELECT column_name, data_type, character_maximum_length, is_nullable, column_default
FROM information_schema.columns
WHERE table_schema = 'public'
  AND table_name = 'matches'
  AND column_name = 'match_id'
LIMIT 1
`;

const MATCHES_CONSTRAINT_SQL = `
SELECT
  tc.constraint_name,
  tc.constraint_type,
  kcu.column_name
FROM information_schema.table_constraints tc
LEFT JOIN information_schema.key_column_usage kcu
  ON tc.constraint_name = kcu.constraint_name
  AND tc.table_schema = kcu.table_schema
WHERE tc.table_schema = 'public'
  AND tc.table_name = 'matches'
ORDER BY tc.constraint_type, tc.constraint_name, kcu.ordinal_position
`;

function usage() {
    return [
        'Usage:',
        '  node scripts/ops/football_data_insert_policy_precheck.js --source-manifest <path> --local-csv <path> [--json]',
        '  node scripts/ops/football_data_insert_policy_precheck.js --source-manifest <path> --local-csv <path> --commit',
        '',
        'Safety:',
        '  Phase 4.66C is SELECT-only insert policy preview. No DB writes, no pg_dump execution, no network harvest.',
    ].join('\n');
}

function parseArgs(argv) {
    return parseDryRunArgs(argv);
}

function readJsonFile(filePath) {
    return JSON.parse(fs.readFileSync(filePath, 'utf8'));
}

function createPool() {
    const { Pool } = require('pg');
    return new Pool(buildDbConfig());
}

async function withDbClient(dependencies, callback) {
    if (dependencies.dbClient) {
        return callback(dependencies.dbClient);
    }

    const pool = dependencies.pool || createPool();
    const client = await pool.connect();
    try {
        return await callback(client);
    } finally {
        client.release();
        if (!dependencies.pool && typeof pool.end === 'function') {
            await pool.end();
        }
    }
}

async function querySelectOnly(client, sql, params = []) {
    assertSelectOnlySql(sql);
    return client.query(sql, params);
}

function buildNonExecutionConfirmations() {
    return [
        'no_external_network',
        'select_only_db_reads',
        'no_db_writes',
        'no_file_writes',
        'no_legacy_runtime',
        'no_pg_dump_execution',
        'no_training',
        'no_prediction_execution',
        'no_model_artifact_load',
        'no_adapted_csv_writes',
        'no_staging_writes',
    ];
}

function buildSafetyFlags() {
    return {
        select_only_db_reads: true,
        no_db_writes: true,
        db_write_allowed: false,
        would_insert_matches: false,
        would_insert_odds: false,
        would_write_db: false,
        would_execute_pg_dump: false,
        would_access_network: false,
        would_write_files: false,
        would_execute_legacy_runtime: false,
        would_train_model: false,
        would_execute_prediction: false,
    };
}

function buildFailurePayload(args, fields = {}) {
    return {
        phase: INSERT_POLICY_PHASE,
        mode: fields.mode || 'football-data-insert-policy-precheck',
        ok: false,
        source_manifest: args.sourceManifest || null,
        local_csv: args.localCsv || null,
        source_manifest_found: false,
        local_csv_found: false,
        dry_run_passed: false,
        duplicate_precheck_passed: false,
        sha256_match: false,
        row_count_match: false,
        match_id_strategy: MATCH_ID_STRATEGY,
        match_id_strategy_finalized: false,
        manifest_approval_status: null,
        candidate_rows: 0,
        future_insert_candidates: 0,
        blocked_by_manifest_policy: 0,
        skip_existing_matches: 0,
        manual_review_required: 0,
        invalid_candidates: 0,
        candidate_previews: [],
        commit_gate: 'blocked',
        ...buildSafetyFlags(),
        non_execution_confirmations: buildNonExecutionConfirmations(),
        errors: [],
        warnings: [],
        ...fields,
    };
}

function buildBlockedCommitPayload(args) {
    return buildFailurePayload(args, {
        mode: 'blocked-commit',
        blocked: true,
        blocked_reason: 'BLOCKED: football-data insert policy commit is not wired in Phase 4.66C.',
        errors: ['BLOCKED: football-data insert policy commit is not wired in Phase 4.66C.'],
    });
}

function normalizeIdentityText(value) {
    return String(value || '')
        .normalize('NFKD')
        .replace(/[\u0300-\u036f]/g, '')
        .trim()
        .replace(/\s+/g, ' ')
        .toLowerCase();
}

function toDateOnly(value) {
    const date = new Date(value);
    if (Number.isNaN(date.getTime())) {
        return '';
    }
    return date.toISOString().slice(0, 10);
}

function toDateSlug(value) {
    return toDateOnly(value).replace(/-/g, '');
}

function slugToken(value, options = {}) {
    const separator = options.separator === undefined ? '_' : options.separator;
    const fallback = options.fallback || 'x';
    const normalized = String(value || '')
        .normalize('NFKD')
        .replace(/[\u0300-\u036f]/g, '')
        .toLowerCase()
        .trim();
    const spaced = separator ? normalized.replace(/\s+/g, separator) : normalized.replace(/\s+/g, '');
    const pattern = separator ? /[^a-z0-9_]/g : /[^a-z0-9]/g;
    const collapsed = spaced
        .replace(pattern, '')
        .replace(/_+/g, '_')
        .replace(/^_+|_+$/g, '');
    return collapsed || fallback;
}

function truncateSlug(value, maxLength) {
    const truncated = String(value || '')
        .slice(0, Math.max(1, maxLength))
        .replace(/^_+|_+$/g, '');
    return truncated || 'x';
}

function buildCandidateIdentityKey(candidate, sourceName = '') {
    return [
        'football_data',
        normalizeIdentityText(sourceName),
        normalizeIdentityText(candidate.league_name || candidate.league_code || ''),
        normalizeIdentityText(candidate.season || ''),
        toDateOnly(candidate.match_date),
        normalizeIdentityText(candidate.home_team),
        normalizeIdentityText(candidate.away_team),
    ].join('|');
}

function sha256Prefix(text, length = 8) {
    return crypto.createHash('sha256').update(text).digest('hex').slice(0, length);
}

function buildProposedMatchId(candidate, options = {}) {
    const maxLength =
        Number.isInteger(options.maxLength) && options.maxLength > 0 ? options.maxLength : DEFAULT_MATCH_ID_MAX_LENGTH;
    const sourceName = options.sourceName || '';
    const candidateIdentityKey = options.candidateIdentityKey || buildCandidateIdentityKey(candidate, sourceName);
    const hash8 = sha256Prefix(candidateIdentityKey);
    let leagueSlug = truncateSlug(
        slugToken(candidate.league_name || candidate.league_code || 'league', {
            separator: '',
            fallback: 'league',
        }),
        10
    );
    let seasonSlug = truncateSlug(slugToken(candidate.season || 'season', { separator: '', fallback: 'season' }), 12);
    const dateSlug = truncateSlug(toDateSlug(candidate.match_date) || 'date', 8);
    let homeSlug = slugToken(candidate.home_team, { separator: '_', fallback: 'home' });
    let awaySlug = slugToken(candidate.away_team, { separator: '_', fallback: 'away' });
    const joinParts = () => ['fd', leagueSlug, seasonSlug, dateSlug, homeSlug, awaySlug, hash8].join('_');

    if (joinParts().length > maxLength) {
        let overhead = ['fd', leagueSlug, seasonSlug, dateSlug, '', '', hash8].join('_').length;
        let availableTeamLength = maxLength - overhead;
        if (availableTeamLength < 2) {
            leagueSlug = truncateSlug(leagueSlug, 4);
            seasonSlug = truncateSlug(seasonSlug, 8);
            overhead = ['fd', leagueSlug, seasonSlug, dateSlug, '', '', hash8].join('_').length;
            availableTeamLength = maxLength - overhead;
        }
        if (availableTeamLength < 2) {
            throw new Error(`proposed_match_id cannot fit match_id max length: ${maxLength}`);
        }
        const homeBudget = Math.max(1, Math.floor(availableTeamLength / 2));
        const awayBudget = Math.max(1, availableTeamLength - homeBudget);
        homeSlug = truncateSlug(homeSlug, homeBudget);
        awaySlug = truncateSlug(awaySlug, awayBudget);
    }

    const proposedMatchId = joinParts();
    if (proposedMatchId.length > maxLength) {
        throw new Error(`proposed_match_id exceeds match_id max length: ${proposedMatchId.length} > ${maxLength}`);
    }

    return {
        proposed_match_id: proposedMatchId,
        proposed_match_id_length: proposedMatchId.length,
        proposed_match_id_valid_length: proposedMatchId.length <= maxLength,
        candidate_identity_key: candidateIdentityKey,
        hash8,
        max_length: maxLength,
    };
}

function deriveMatchIdSchema(columnRows, constraintRows) {
    const matchIdColumn = columnRows[0] || null;
    const rawMaxLength = Number.parseInt(matchIdColumn?.character_maximum_length, 10);
    const matchIdMaxLength =
        Number.isInteger(rawMaxLength) && rawMaxLength > 0 ? rawMaxLength : DEFAULT_MATCH_ID_MAX_LENGTH;
    const matchIdConstraintRows = constraintRows.filter(row => row.column_name === 'match_id');
    const primaryKey = matchIdConstraintRows.some(row => row.constraint_type === 'PRIMARY KEY');
    const explicitUnique = matchIdConstraintRows.some(row => row.constraint_type === 'UNIQUE');

    return {
        table_name: 'matches',
        match_id_column_found: Boolean(matchIdColumn),
        match_id_data_type: matchIdColumn?.data_type || null,
        match_id_character_maximum_length: matchIdColumn?.character_maximum_length || null,
        match_id_max_length: matchIdMaxLength,
        match_id_max_length_source: matchIdColumn?.character_maximum_length ? 'information_schema' : 'default_64',
        match_id_is_nullable: matchIdColumn?.is_nullable || null,
        match_id_column_default: matchIdColumn?.column_default || null,
        match_id_primary_key: primaryKey,
        match_id_unique: primaryKey || explicitUnique,
        constraints: constraintRows.map(row => ({
            constraint_name: row.constraint_name,
            constraint_type: row.constraint_type,
            column_name: row.column_name,
        })),
    };
}

async function inspectMatchesSchema(client) {
    await querySelectOnly(client, READ_ONLY_BEGIN_SQL);
    try {
        const columnResult = await querySelectOnly(client, MATCH_ID_COLUMN_SQL);
        const constraintResult = await querySelectOnly(client, MATCHES_CONSTRAINT_SQL);
        return deriveMatchIdSchema(columnResult.rows || [], constraintResult.rows || []);
    } finally {
        await querySelectOnly(client, READ_ONLY_ROLLBACK_SQL);
    }
}

function decideInsertPolicy(duplicatePreview, manifestApprovalStatus, proposedMatchId) {
    if (duplicatePreview.duplicate_risk === 'invalid_candidate') {
        return {
            insert_policy: 'invalid_candidate',
            policy_reason: 'candidate is missing required identity or finished-label fields',
            skip_reason: 'invalid_candidate',
            review_reason: null,
        };
    }
    if (duplicatePreview.duplicate_risk === 'exact_existing_match') {
        return {
            insert_policy: 'skip_existing_match',
            policy_reason: 'exact existing match already exists in DB',
            skip_reason: 'exact_existing_match',
            review_reason: null,
        };
    }
    if (
        duplicatePreview.duplicate_risk === 'reversed_teams_possible_duplicate' ||
        duplicatePreview.duplicate_risk === 'nearby_date_possible_duplicate'
    ) {
        return {
            insert_policy: 'manual_review_required',
            policy_reason: `${duplicatePreview.duplicate_risk} requires manual review before any future insert`,
            skip_reason: null,
            review_reason: duplicatePreview.duplicate_risk,
        };
    }
    if (!proposedMatchId.proposed_match_id_valid_length) {
        return {
            insert_policy: 'invalid_candidate',
            policy_reason: 'proposed_match_id does not fit matches.match_id length limit',
            skip_reason: 'invalid_match_id_length',
            review_reason: null,
        };
    }
    if (manifestApprovalStatus !== APPROVED_FOR_DB_WRITE) {
        return {
            insert_policy: 'blocked_by_manifest_policy',
            policy_reason: 'source manifest approval_status is not approved_for_db_write',
            skip_reason: 'manifest_not_approved_for_db_write',
            review_reason: null,
        };
    }

    return {
        insert_policy: 'future_insert_candidate',
        policy_reason: 'clean candidate under approved_for_db_write manifest; Phase 4.66C still does not write DB',
        skip_reason: null,
        review_reason: null,
    };
}

function countPolicy(previews, policy) {
    return previews.filter(preview => preview.insert_policy === policy).length;
}

function buildPolicyPreview(candidate, duplicatePreview, dryRunPayload, matchIdSchema) {
    const sourceName = dryRunPayload.source_name || '';
    const candidateIdentityKey = buildCandidateIdentityKey(candidate, sourceName);
    const proposedMatchId = buildProposedMatchId(candidate, {
        sourceName,
        candidateIdentityKey,
        maxLength: matchIdSchema.match_id_max_length,
    });
    const policy = decideInsertPolicy(duplicatePreview, dryRunPayload.approval_status, proposedMatchId);

    return {
        row_number: candidate.row_number || duplicatePreview.row_number || null,
        home_team: candidate.home_team || duplicatePreview.home_team || null,
        away_team: candidate.away_team || duplicatePreview.away_team || null,
        match_date: toDateOnly(candidate.match_date) || duplicatePreview.match_date || null,
        actual_result: candidate.actual_result || duplicatePreview.actual_result || null,
        candidate_identity_key: proposedMatchId.candidate_identity_key,
        proposed_match_id: proposedMatchId.proposed_match_id,
        proposed_match_id_length: proposedMatchId.proposed_match_id_length,
        proposed_match_id_valid_length: proposedMatchId.proposed_match_id_valid_length,
        duplicate_risk: duplicatePreview.duplicate_risk,
        insert_policy: policy.insert_policy,
        policy_reason: policy.policy_reason,
        skip_reason: policy.skip_reason,
        review_reason: policy.review_reason,
        existing_match_ids: duplicatePreview.existing_match_ids || [],
        nearby_match_ids: duplicatePreview.nearby_match_ids || [],
        would_insert_match: false,
        would_insert_odds: false,
    };
}

function buildPolicyPreviews(dryRunPayload, duplicatePreviews, matchIdSchema) {
    const candidates = dryRunPayload.candidate_rows || [];
    return candidates.map((candidate, index) =>
        buildPolicyPreview(
            candidate,
            duplicatePreviews[index] || { duplicate_risk: 'invalid_candidate' },
            dryRunPayload,
            matchIdSchema
        )
    );
}

function buildSuccessPayload(args, dryRunPayload, duplicatePreviews, matchIdSchema, policyPreviews) {
    return {
        phase: INSERT_POLICY_PHASE,
        mode: 'football-data-insert-policy-precheck',
        ok: true,
        source_manifest: args.sourceManifest,
        local_csv: args.localCsv,
        source_manifest_found: dryRunPayload.source_manifest_found,
        local_csv_found: dryRunPayload.local_csv_found,
        dry_run_passed: true,
        duplicate_precheck_passed: true,
        sha256_match: dryRunPayload.sha256_match,
        row_count_match: dryRunPayload.row_count_match,
        select_only_db_reads: true,
        match_id_strategy: MATCH_ID_STRATEGY,
        match_id_strategy_finalized: false,
        match_id_schema: matchIdSchema,
        manifest_approval_status: dryRunPayload.approval_status,
        source_name: dryRunPayload.source_name,
        candidate_rows: (dryRunPayload.candidate_rows || []).length,
        future_insert_candidates: countPolicy(policyPreviews, 'future_insert_candidate'),
        blocked_by_manifest_policy: countPolicy(policyPreviews, 'blocked_by_manifest_policy'),
        skip_existing_matches: countPolicy(policyPreviews, 'skip_existing_match'),
        manual_review_required: countPolicy(policyPreviews, 'manual_review_required'),
        invalid_candidates: countPolicy(policyPreviews, 'invalid_candidate'),
        candidate_previews: policyPreviews,
        duplicate_precheck_summary: {
            exact_existing_matches: duplicatePreviews.filter(
                preview => preview.duplicate_risk === 'exact_existing_match'
            ).length,
            reversed_team_matches: duplicatePreviews.filter(
                preview => preview.duplicate_risk === 'reversed_teams_possible_duplicate'
            ).length,
            nearby_date_matches: duplicatePreviews.filter(
                preview => preview.duplicate_risk === 'nearby_date_possible_duplicate'
            ).length,
            invalid_candidates: duplicatePreviews.filter(preview => preview.duplicate_risk === 'invalid_candidate')
                .length,
        },
        commit_gate: 'blocked',
        ...buildSafetyFlags(),
        non_execution_confirmations: buildNonExecutionConfirmations(),
        warnings: dryRunPayload.warnings || [],
        errors: [],
    };
}

function runPolicyDryRun(args, dependencies = {}) {
    if (dependencies.runDryRun) {
        return dependencies.runDryRun(args);
    }

    const dryRunDependencies = {
        ...(dependencies.dryRunDependencies || {}),
    };
    const readManifest = dryRunDependencies.readManifest || readJsonFile;
    let originalApprovalStatus = null;

    dryRunDependencies.readManifest = manifestPath => {
        const manifest = readManifest(manifestPath);
        originalApprovalStatus = manifest.approval_status || null;
        if (manifest.approval_status === APPROVED_FOR_DB_WRITE) {
            return {
                ...manifest,
                approval_status: 'approved_for_dry_run',
            };
        }
        return manifest;
    };

    const dryRunPayload = runDryRun(args, dryRunDependencies);
    if (dryRunPayload.ok && originalApprovalStatus) {
        return {
            ...dryRunPayload,
            approval_status: originalApprovalStatus,
        };
    }
    return dryRunPayload;
}

async function runInsertPolicyPrecheck(args, dependencies = {}) {
    if (!args.sourceManifest || !args.localCsv) {
        return buildFailurePayload(args, {
            mode: 'argument-error',
            select_only_db_reads: false,
            errors: ['ERROR: provide --source-manifest=<path> and --local-csv=<path>'],
        });
    }

    const dryRunPayload = runPolicyDryRun(
        {
            sourceManifest: args.sourceManifest,
            localCsv: args.localCsv,
        },
        dependencies
    );

    if (!dryRunPayload.ok) {
        return buildFailurePayload(args, {
            mode: 'dry-run-failed',
            source_manifest_found: dryRunPayload.source_manifest_found,
            local_csv_found: dryRunPayload.local_csv_found,
            sha256_match: dryRunPayload.sha256_match,
            row_count_match: dryRunPayload.row_count_match,
            dry_run_passed: false,
            select_only_db_reads: false,
            dry_run_failure_mode: dryRunPayload.mode,
            errors: dryRunPayload.errors || ['football-data CSV dry-run failed'],
            warnings: dryRunPayload.warnings || [],
        });
    }

    return withDbClient(dependencies, async client => {
        const matchIdSchema = dependencies.matchIdSchema || (await inspectMatchesSchema(client));
        const duplicatePreviews =
            dependencies.duplicatePreviews || (await runCandidatePrechecks(client, dryRunPayload.candidate_rows || []));
        const policyPreviews = buildPolicyPreviews(dryRunPayload, duplicatePreviews, matchIdSchema);
        return buildSuccessPayload(args, dryRunPayload, duplicatePreviews, matchIdSchema, policyPreviews);
    });
}

function appendOptionalTextFields(lines, payload) {
    if (payload.blocked_reason) {
        lines.push(`blocked_reason=${payload.blocked_reason}`);
    }
    if (Array.isArray(payload.errors) && payload.errors.length > 0) {
        lines.push(`errors=${payload.errors.join('; ')}`);
    }
    if (Array.isArray(payload.warnings) && payload.warnings.length > 0) {
        lines.push(`warnings=${JSON.stringify(payload.warnings)}`);
    }
}

function appendListSection(lines, title, values) {
    lines.push(`${title}:`);
    for (const value of values || []) {
        lines.push(`- ${value}`);
    }
}

function payloadToText(payload) {
    const lines = [
        `phase=${payload.phase}`,
        `mode=${payload.mode}`,
        `ok=${payload.ok}`,
        `source_manifest_found=${payload.source_manifest_found}`,
        `local_csv_found=${payload.local_csv_found}`,
        `dry_run_passed=${payload.dry_run_passed}`,
        `duplicate_precheck_passed=${payload.duplicate_precheck_passed}`,
        `sha256_match=${payload.sha256_match}`,
        `row_count_match=${payload.row_count_match}`,
        `select_only_db_reads=${payload.select_only_db_reads}`,
        `match_id_strategy=${payload.match_id_strategy}`,
        `match_id_strategy_finalized=${payload.match_id_strategy_finalized}`,
        `manifest_approval_status=${payload.manifest_approval_status}`,
        `db_write_allowed=${payload.db_write_allowed}`,
        `candidate_rows=${payload.candidate_rows || 0}`,
        `future_insert_candidates=${payload.future_insert_candidates || 0}`,
        `blocked_by_manifest_policy=${payload.blocked_by_manifest_policy || 0}`,
        `skip_existing_matches=${payload.skip_existing_matches || 0}`,
        `manual_review_required=${payload.manual_review_required || 0}`,
        `invalid_candidates=${payload.invalid_candidates || 0}`,
        `would_insert_matches=${payload.would_insert_matches}`,
        `would_insert_odds=${payload.would_insert_odds}`,
        `would_write_db=${payload.would_write_db}`,
        `would_access_network=${payload.would_access_network}`,
        `would_write_files=${payload.would_write_files}`,
        `commit_gate=${payload.commit_gate}`,
    ];

    if (payload.match_id_schema) {
        lines.push(`match_id_schema=${JSON.stringify(payload.match_id_schema)}`);
    }
    if (Array.isArray(payload.candidate_previews) && payload.candidate_previews.length > 0) {
        lines.push(`candidate_previews=${JSON.stringify(payload.candidate_previews)}`);
    }
    if (payload.duplicate_precheck_summary) {
        lines.push(`duplicate_precheck_summary=${JSON.stringify(payload.duplicate_precheck_summary)}`);
    }

    appendOptionalTextFields(lines, payload);
    appendListSection(lines, 'non_execution_confirmations', payload.non_execution_confirmations);
    return lines.join('\n');
}

function writePayload(payload, json, io) {
    const output = json ? `${JSON.stringify(payload, null, 2)}\n` : `${payloadToText(payload)}\n`;
    io.stdout(output);
}

async function main(argv = process.argv.slice(2), io = {}) {
    const output = {
        stdout: io.stdout || (text => process.stdout.write(text)),
        stderr: io.stderr || (text => process.stderr.write(text)),
    };

    try {
        const args = parseArgs(argv);
        if (args.help) {
            output.stdout(`${usage()}\n`);
            return 0;
        }
        if (args.commit) {
            const payload = buildBlockedCommitPayload(args);
            writePayload(payload, args.json, output);
            return 1;
        }

        const payload = await runInsertPolicyPrecheck(args);
        writePayload(payload, args.json, output);
        return payload.ok ? 0 : 1;
    } catch (error) {
        const json = argv.includes('--json');
        const payload = buildFailurePayload(
            {
                sourceManifest: '',
                localCsv: '',
            },
            {
                mode: 'runtime-error',
                errors: [error.message],
            }
        );
        writePayload(payload, json, output);
        return 1;
    }
}

if (require.main === module) {
    main().then(status => {
        process.exitCode = status;
    });
}

module.exports = {
    INSERT_POLICY_PHASE,
    MATCH_ID_STRATEGY,
    MATCH_ID_COLUMN_SQL,
    MATCHES_CONSTRAINT_SQL,
    READ_ONLY_BEGIN_SQL,
    READ_ONLY_ROLLBACK_SQL,
    parseArgs,
    runInsertPolicyPrecheck,
    inspectMatchesSchema,
    deriveMatchIdSchema,
    buildCandidateIdentityKey,
    buildProposedMatchId,
    decideInsertPolicy,
    assertSelectOnlySql,
    payloadToText,
    main,
};
