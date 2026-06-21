#!/usr/bin/env node
'use strict';

const { assertDbWriteAllowed } = require('./helpers/db_write_guard');
const { runDryRun, parseArgs: parseDryRunArgs } = require('./football_data_adapter_dry_run');

const DUPLICATE_PRECHECK_PHASE = 'PHASE4.65C_FOOTBALL_DATA_DUPLICATE_PRECHECK';

const MATCH_SELECT_COLUMNS = [
    'match_id',
    'league_name',
    'season',
    'match_date',
    'home_team',
    'away_team',
    'home_score',
    'away_score',
    'actual_result',
    'status',
    'is_finished',
    'data_source',
].join(', ');

const EXACT_MATCH_SQL = `
SELECT ${MATCH_SELECT_COLUMNS}
FROM matches
WHERE lower(home_team) = lower($1)
  AND lower(away_team) = lower($2)
  AND match_date::date = $3::date
LIMIT 10
`;

const REVERSED_MATCH_SQL = `
SELECT ${MATCH_SELECT_COLUMNS}
FROM matches
WHERE lower(home_team) = lower($1)
  AND lower(away_team) = lower($2)
  AND match_date::date = $3::date
LIMIT 10
`;

const NEARBY_MATCH_SQL = `
SELECT ${MATCH_SELECT_COLUMNS}
FROM matches
WHERE (
    (lower(home_team) = lower($1) AND lower(away_team) = lower($2))
    OR
    (lower(home_team) = lower($2) AND lower(away_team) = lower($1))
)
AND match_date::date BETWEEN $3::date - interval '2 days' AND $3::date + interval '2 days'
LIMIT 20
`;

const READ_ONLY_BEGIN_SQL = 'BEGIN READ ONLY';
const READ_ONLY_ROLLBACK_SQL = 'ROLLBACK';

function usage() {
    return [
        'Usage:',
        '  node scripts/ops/football_data_duplicate_precheck.js --source-manifest <path> --local-csv <path> [--json]',
        '  node scripts/ops/football_data_duplicate_precheck.js --source-manifest <path> --local-csv <path> --commit',
        '',
        'Safety:',
        '  Phase 4.65C is SELECT-only duplicate precheck. No DB writes, no pg_dump execution, no network harvest.',
    ].join('\n');
}

function parseArgs(argv) {
    return parseDryRunArgs(argv);
}

function buildDbConfig() {
    return {
        host: process.env.DB_HOST || process.env.POSTGRES_HOST || 'db',
        port: Number.parseInt(process.env.DB_PORT || process.env.POSTGRES_PORT || '5432', 10),
        database: process.env.DB_NAME || process.env.POSTGRES_DB || 'football_db',
        user: process.env.DB_USER || process.env.POSTGRES_USER || 'football_user',
        password: process.env.DB_PASSWORD || process.env.POSTGRES_PASSWORD,
        max: 1,
        idleTimeoutMillis: 30000,
        connectionTimeoutMillis: 5000,
    };
}

function createPool() {
    const { Pool } = require('pg');
    return new Pool(buildDbConfig());
}

function buildRequiredBeforeDbWrite() {
    return [
        'deterministic match_id strategy must be finalized',
        'duplicate policy must be approved',
        'exact_existing_match rows must not be inserted',
        'nearby_date_possible_duplicate rows require manual review',
        'pg_dump backup must run immediately before write',
        'max rows must be explicit',
        'target table list must be explicit',
        'post-write validation must compare row counts and target rows',
        'training/prediction must remain blocked',
    ];
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
        phase: DUPLICATE_PRECHECK_PHASE,
        mode: fields.mode || 'football-data-duplicate-precheck',
        ok: false,
        source_manifest: args.sourceManifest || null,
        local_csv: args.localCsv || null,
        source_manifest_found: false,
        local_csv_found: false,
        dry_run_passed: false,
        sha256_match: false,
        row_count_match: false,
        candidate_rows: 0,
        trainable_label_rows: 0,
        exact_existing_matches: 0,
        reversed_team_matches: 0,
        nearby_date_matches: 0,
        invalid_candidates: 0,
        candidate_previews: [],
        commit_gate: 'blocked',
        required_before_db_write: buildRequiredBeforeDbWrite(),
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
        blocked_reason: 'BLOCKED: football-data duplicate precheck commit is not wired in Phase 4.65C.',
        errors: ['BLOCKED: football-data duplicate precheck commit is not wired in Phase 4.65C.'],
    });
}

function normalizeTeamName(value) {
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

function buildCandidateIdentityKey(candidate) {
    return [
        String(candidate.league_name || '').trim(),
        String(candidate.season || '').trim(),
        toDateOnly(candidate.match_date),
        normalizeTeamName(candidate.home_team),
        normalizeTeamName(candidate.away_team),
    ].join('|');
}

function isCandidateValid(candidate) {
    return (
        Boolean(String(candidate.home_team || '').trim()) &&
        Boolean(String(candidate.away_team || '').trim()) &&
        Boolean(toDateOnly(candidate.match_date)) &&
        Boolean(String(candidate.actual_result || '').trim())
    );
}

function mapMatchRows(rows) {
    return rows.map(row => ({
        match_id: row.match_id,
        league_name: row.league_name,
        season: row.season,
        match_date: row.match_date,
        home_team: row.home_team,
        away_team: row.away_team,
        home_score: row.home_score,
        away_score: row.away_score,
        actual_result: row.actual_result,
        status: row.status,
        is_finished: row.is_finished,
        data_source: row.data_source,
    }));
}

function uniqueIds(rows) {
    return [...new Set(rows.map(row => row.match_id).filter(Boolean))];
}

function assertSelectOnlySql(sql) {
    const normalized = String(sql || '')
        .replace(/\s+/g, ' ')
        .trim()
        .toUpperCase();
    const allowed =
        normalized === READ_ONLY_BEGIN_SQL || normalized === READ_ONLY_ROLLBACK_SQL || normalized.startsWith('SELECT ');
    const forbidden =
        /\b(INSERT|UPDATE|DELETE|CREATE|ALTER|DROP|TRUNCATE|COPY|MERGE|GRANT|REVOKE|COMMIT)\b|\\COPY/.test(normalized);

    if (!allowed || forbidden) {
        throw new Error(`Unsafe SQL rejected by duplicate precheck: ${normalized.slice(0, 80)}`);
    }
}

async function querySelectOnly(client, sql, params = []) {
    assertSelectOnlySql(sql);
    return client.query(sql, params);
}

function classifyDuplicateRisk(exactRows, reversedRows, nearbyRows, valid) {
    if (!valid) {
        return 'invalid_candidate';
    }
    if (exactRows.length > 0) {
        return 'exact_existing_match';
    }
    if (reversedRows.length > 0) {
        return 'reversed_teams_possible_duplicate';
    }
    if (nearbyRows.length > 0) {
        return 'nearby_date_possible_duplicate';
    }
    return 'none';
}

async function precheckCandidate(client, candidate) {
    const valid = isCandidateValid(candidate);
    const dateOnly = toDateOnly(candidate.match_date);
    const basePreview = {
        row_number: candidate.row_number || null,
        home_team: candidate.home_team || null,
        away_team: candidate.away_team || null,
        match_date: dateOnly || candidate.match_date || null,
        actual_result: candidate.actual_result || null,
        duplicate_risk: 'invalid_candidate',
        existing_match_ids: [],
        nearby_match_ids: [],
        candidate_identity_key: buildCandidateIdentityKey(candidate),
        proposed_match_id_strategy: 'not_finalized',
        match_id_write_allowed: false,
        would_insert_match: false,
        would_insert_odds: false,
        exact_matches: [],
        reversed_matches: [],
        nearby_matches: [],
    };

    if (!valid) {
        return basePreview;
    }

    const exactResult = await querySelectOnly(client, EXACT_MATCH_SQL, [
        candidate.home_team,
        candidate.away_team,
        dateOnly,
    ]);
    const reversedResult = await querySelectOnly(client, REVERSED_MATCH_SQL, [
        candidate.away_team,
        candidate.home_team,
        dateOnly,
    ]);
    const nearbyResult = await querySelectOnly(client, NEARBY_MATCH_SQL, [
        candidate.home_team,
        candidate.away_team,
        dateOnly,
    ]);
    const exactRows = mapMatchRows(exactResult.rows || []);
    const reversedRows = mapMatchRows(reversedResult.rows || []);
    const nearbyRows = mapMatchRows(nearbyResult.rows || []);
    const risk = classifyDuplicateRisk(exactRows, reversedRows, nearbyRows, valid);

    return {
        ...basePreview,
        duplicate_risk: risk,
        existing_match_ids: uniqueIds([...exactRows, ...reversedRows]),
        nearby_match_ids: uniqueIds(nearbyRows),
        exact_matches: exactRows,
        reversed_matches: reversedRows,
        nearby_matches: nearbyRows,
    };
}

async function runCandidatePrechecks(client, candidates) {
    const previews = [];
    let began = false;

    await querySelectOnly(client, READ_ONLY_BEGIN_SQL);
    began = true;
    try {
        for (const candidate of candidates) {
            previews.push(await precheckCandidate(client, candidate));
        }
    } finally {
        if (began) {
            await querySelectOnly(client, READ_ONLY_ROLLBACK_SQL);
        }
    }

    return previews;
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

function countRisk(previews, risk) {
    return previews.filter(preview => preview.duplicate_risk === risk).length;
}

function sumMatchRows(previews, field) {
    return previews.reduce((total, preview) => total + (preview[field] || []).length, 0);
}

function buildInsertRiskSummary(candidatePreviews) {
    return {
        duplicate_free_candidates: countRisk(candidatePreviews, 'none'),
        exact_existing_match_candidates: countRisk(candidatePreviews, 'exact_existing_match'),
        reversed_team_possible_duplicate_candidates: countRisk(candidatePreviews, 'reversed_teams_possible_duplicate'),
        nearby_date_possible_duplicate_candidates: countRisk(candidatePreviews, 'nearby_date_possible_duplicate'),
        invalid_candidates: countRisk(candidatePreviews, 'invalid_candidate'),
        policy: 'future_insert_blocked_until_duplicate_policy_and_match_id_strategy_are_approved',
    };
}

function buildSuccessPayload(args, dryRunPayload, candidatePreviews) {
    const rowClassification = dryRunPayload.row_classification || {};
    return {
        phase: DUPLICATE_PRECHECK_PHASE,
        mode: 'football-data-duplicate-precheck',
        ok: true,
        source_manifest: args.sourceManifest,
        local_csv: args.localCsv,
        source_manifest_found: dryRunPayload.source_manifest_found,
        local_csv_found: dryRunPayload.local_csv_found,
        dry_run_passed: true,
        sha256_match: dryRunPayload.sha256_match,
        row_count_match: dryRunPayload.row_count_match,
        approval_status: dryRunPayload.approval_status,
        source_name: dryRunPayload.source_name,
        parser_version: dryRunPayload.parser_version,
        dry_run_version: dryRunPayload.dry_run_version,
        candidate_rows: dryRunPayload.candidate_rows.length,
        trainable_label_rows: rowClassification.trainable_label_rows || 0,
        exact_existing_matches: sumMatchRows(candidatePreviews, 'exact_matches'),
        reversed_team_matches: sumMatchRows(candidatePreviews, 'reversed_matches'),
        nearby_date_matches: sumMatchRows(candidatePreviews, 'nearby_matches'),
        invalid_candidates: countRisk(candidatePreviews, 'invalid_candidate'),
        candidate_previews: candidatePreviews,
        insert_risk_summary: buildInsertRiskSummary(candidatePreviews),
        identity_strategy: {
            candidate_identity_key_fields: [
                'league_name',
                'season',
                'match_date',
                'normalized_home_team',
                'normalized_away_team',
            ],
            proposed_match_id_strategy: 'not_finalized',
            match_id_write_allowed: false,
        },
        commit_gate: 'blocked',
        required_before_db_write: buildRequiredBeforeDbWrite(),
        ...buildSafetyFlags(),
        non_execution_confirmations: buildNonExecutionConfirmations(),
        dry_run_non_execution_confirmations: dryRunPayload.non_execution_confirmations,
        warnings: dryRunPayload.warnings || [],
        errors: [],
    };
}

async function runDuplicatePrecheck(args, dependencies = {}) {
    if (!args.sourceManifest || !args.localCsv) {
        return buildFailurePayload(args, {
            mode: 'argument-error',
            select_only_db_reads: false,
            errors: ['ERROR: provide --source-manifest=<path> and --local-csv=<path>'],
        });
    }

    const dryRun = dependencies.runDryRun || runDryRun;
    const dryRunPayload = dryRun(
        {
            sourceManifest: args.sourceManifest,
            localCsv: args.localCsv,
        },
        dependencies.dryRunDependencies || {}
    );

    if (!dryRunPayload.ok) {
        return buildFailurePayload(args, {
            mode: 'dry-run-failed',
            source_manifest_found: dryRunPayload.source_manifest_found,
            local_csv_found: dryRunPayload.local_csv_found,
            sha256_match: dryRunPayload.sha256_match,
            row_count_match: dryRunPayload.row_count_match,
            dry_run_passed: false,
            dry_run_failure_mode: dryRunPayload.mode,
            select_only_db_reads: false,
            errors: dryRunPayload.errors || ['football-data CSV dry-run failed'],
            warnings: dryRunPayload.warnings || [],
        });
    }

    const candidatePreviews = await withDbClient(dependencies, client =>
        runCandidatePrechecks(client, dryRunPayload.candidate_rows || [])
    );
    return buildSuccessPayload(args, dryRunPayload, candidatePreviews);
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
        `sha256_match=${payload.sha256_match}`,
        `row_count_match=${payload.row_count_match}`,
        `select_only_db_reads=${payload.select_only_db_reads}`,
        `no_db_writes=${payload.no_db_writes}`,
        `candidate_rows=${payload.candidate_rows || 0}`,
        `trainable_label_rows=${payload.trainable_label_rows || 0}`,
        `exact_existing_matches=${payload.exact_existing_matches || 0}`,
        `reversed_team_matches=${payload.reversed_team_matches || 0}`,
        `nearby_date_matches=${payload.nearby_date_matches || 0}`,
        `invalid_candidates=${payload.invalid_candidates || 0}`,
        `db_write_allowed=${payload.db_write_allowed}`,
        `would_insert_matches=${payload.would_insert_matches}`,
        `would_insert_odds=${payload.would_insert_odds}`,
        `would_write_db=${payload.would_write_db}`,
        `would_access_network=${payload.would_access_network}`,
        `would_write_files=${payload.would_write_files}`,
        `commit_gate=${payload.commit_gate}`,
    ];

    if (Array.isArray(payload.candidate_previews) && payload.candidate_previews.length > 0) {
        lines.push(`candidate_previews=${JSON.stringify(payload.candidate_previews)}`);
    }
    if (payload.insert_risk_summary) {
        lines.push(`insert_risk_summary=${JSON.stringify(payload.insert_risk_summary)}`);
    }
    if (payload.identity_strategy) {
        lines.push(`identity_strategy=${JSON.stringify(payload.identity_strategy)}`);
    }

    appendOptionalTextFields(lines, payload);
    appendListSection(lines, 'required_before_db_write', payload.required_before_db_write);
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
            assertDbWriteAllowed({
                script: 'football_data_duplicate_precheck.js',
                tables: ['matches'],
                operations: ['INSERT'],
            });
            const payload = buildBlockedCommitPayload(args);
            writePayload(payload, args.json, output);
            return 1;
        }

        const payload = await runDuplicatePrecheck(args);
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
    DUPLICATE_PRECHECK_PHASE,
    EXACT_MATCH_SQL,
    REVERSED_MATCH_SQL,
    NEARBY_MATCH_SQL,
    READ_ONLY_BEGIN_SQL,
    READ_ONLY_ROLLBACK_SQL,
    parseArgs,
    runDuplicatePrecheck,
    runCandidatePrechecks,
    buildRequiredBeforeDbWrite,
    buildNonExecutionConfirmations,
    buildDbConfig,
    assertSelectOnlySql,
    buildCandidateIdentityKey,
    payloadToText,
    main,
};
