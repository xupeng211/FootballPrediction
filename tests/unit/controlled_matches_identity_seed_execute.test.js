'use strict';

/* eslint-disable max-lines */

const assert = require('node:assert/strict');
const fs = require('node:fs');
const Module = require('node:module');
const path = require('node:path');
const test = require('node:test');

const PROJECT_ROOT = path.resolve(__dirname, '../..');
const MODULE_PATH = path.join(PROJECT_ROOT, 'scripts/ops/controlled_matches_identity_seed_execute.js');

function loadFreshModule() {
    delete require.cache[require.resolve(MODULE_PATH)];
    return require(MODULE_PATH);
}

const mod = loadFreshModule();

const DB_WRITE_GUARD_ENV_KEYS = [
    'ALLOW_DB_WRITE',
    'FINAL_DB_WRITE_CONFIRMATION',
    'ALLOW_MATCHES_WRITE',
    'DRY_RUN',
];

function snapshotEnv(keys = DB_WRITE_GUARD_ENV_KEYS) {
    return Object.fromEntries(keys.map(key => [key, process.env[key]]));
}

function restoreEnv(snapshot) {
    for (const [key, value] of Object.entries(snapshot)) {
        if (value === undefined) {
            delete process.env[key];
        } else {
            process.env[key] = value;
        }
    }
}

async function withDbWriteGuardEnv(callback, overrides = {}) {
    const savedEnv = snapshotEnv();
    try {
        process.env.ALLOW_DB_WRITE = 'yes';
        process.env.FINAL_DB_WRITE_CONFIRMATION = 'yes';
        process.env.ALLOW_MATCHES_WRITE = 'yes';
        process.env.DRY_RUN = 'false';
        for (const [key, value] of Object.entries(overrides)) {
            if (value === undefined) {
                delete process.env[key];
            } else {
                process.env[key] = value;
            }
        }
        return await callback();
    } finally {
        restoreEnv(savedEnv);
    }
}

function runCliWithDbWriteGuardEnv(argv, dependencies, envOverrides) {
    return withDbWriteGuardEnv(() => mod.runCli(argv, dependencies), envOverrides);
}

const MATCHES_INSERT_PREFIX = ['INSERT', 'INTO', 'matches'].join(' ');
const MATCHES_INSERT_RE = new RegExp(`^${MATCHES_INSERT_PREFIX}`, 'i');

function validInput(overrides = {}) {
    return {
        manifest: mod.MANIFEST_PATH,
        source: 'fotmob',
        leagueId: 53,
        leagueName: 'Ligue 1',
        season: '2025/2026',
        batchId: mod.BATCH_ID,
        targetCount: 50,
        finalDbWriteConfirmation: true,
        allowDbWrite: true,
        allowMatchesWrite: true,
        allowRawMatchDataWrite: false,
        allowBookmakerOddsWrite: false,
        allowFeatureWrite: false,
        allowNetwork: false,
        allowMatchDetailFetch: false,
        allowControlledRawWrite: false,
        allowSchemaMigration: false,
        allowParserImplementation: false,
        allowFeatureExtraction: false,
        allowTraining: false,
        allowPrediction: false,
        ...overrides,
    };
}

function validArgv(overrides = {}) {
    const base = {
        manifest: mod.MANIFEST_PATH,
        source: 'fotmob',
        'league-id': '53',
        'league-name': 'Ligue 1',
        season: '2025/2026',
        'batch-id': mod.BATCH_ID,
        'target-count': '50',
        'final-db-write-confirmation': 'yes',
        'allow-db-write': 'yes',
        'allow-matches-write': 'yes',
        'allow-raw-match-data-write': 'no',
        'allow-bookmaker-odds-write': 'no',
        'allow-feature-write': 'no',
        'allow-network': 'no',
        'allow-match-detail-fetch': 'no',
        'allow-controlled-raw-write': 'no',
        'allow-schema-migration': 'no',
        'allow-parser-implementation': 'no',
        'allow-feature-extraction': 'no',
        'allow-training': 'no',
        'allow-prediction': 'no',
        ...overrides,
    };
    return Object.entries(base).flatMap(([key, value]) => [`--${key}`, value]);
}

function candidate(index, overrides = {}) {
    const externalId = String(4830460 + index);
    const day = String((index % 20) + 1).padStart(2, '0');
    return {
        target_id: `${mod.BATCH_ID}:53_20252026_${externalId}`,
        batch_id: mod.BATCH_ID,
        source: 'fotmob',
        route: 'html_hydration',
        source_inventory_route: 'source_inventory',
        raw_data_version: 'fotmob_pageprops_v2',
        hash_strategy: 'stable_pageprops_payload_v1',
        match_id: `53_20252026_${externalId}`,
        external_id: externalId,
        league_id: 53,
        league_name: 'Ligue 1',
        season: '2025/2026',
        home_team: `Home ${index}`,
        away_team: `Away ${index}`,
        kickoff_time: `2025-08-${day}T18:45:00.000Z`,
        match_date: `2025-08-${day}T18:45:00.000Z`,
        status: 'finished',
        matches_identity_seed_status: 'eligible_matches_insert',
        ...overrides,
    };
}

function candidates50(overridesByIndex = {}) {
    return Array.from({ length: 50 }, (_unused, index) => candidate(index, overridesByIndex[index] || {}));
}

function manifest(overrides = {}) {
    return {
        schema_version: 'target_manifest_proposal_v1',
        batch_id: mod.BATCH_ID,
        source: 'fotmob',
        league: {
            league_id: 53,
            league_name: 'Ligue 1',
            season: '2025/2026',
        },
        known_completed_targets: Array.from({ length: 8 }, (_unused, index) => ({
            match_id: `53_20252026_${4830746 + index}`,
            external_id: String(4830746 + index),
        })),
        candidate_targets: candidates50(),
        matches_identity_seed_plan_status: 'ready_for_final_authorization',
        matches_identity_seed_authorization_status: 'pending_final_db_write_confirmation',
        eligible_matches_insert_count: 50,
        expected_matches_after: 60,
        required_next_step: 'controlled_matches_identity_seed_execution',
        ...overrides,
    };
}

function protectedRows(counts = mod.EXPECTED_BEFORE_COUNTS) {
    return Object.entries(counts).map(([table_name, rows]) => ({ table_name, rows }));
}

function schemaColumns(overrides = {}) {
    const rows = [
        ['match_id', 'NO', null],
        ['external_id', 'YES', null],
        ['league_name', 'NO', "'Premier League'::character varying"],
        ['season', 'NO', "'2324'::character varying"],
        ['home_team', 'NO', null],
        ['away_team', 'NO', null],
        ['match_date', 'YES', null],
        ['status', 'YES', "'Scheduled'::character varying"],
        ['is_finished', 'YES', 'false'],
        ['data_source', 'YES', "'FotMob'::character varying"],
        [
            'pipeline_status',
            overrides.pipelineNullable || 'YES',
            overrides.pipelineDefault ?? "'pending'::character varying",
        ],
    ];
    return rows.map(([column_name, is_nullable, column_default]) => ({
        column_name,
        data_type: column_name === 'match_date' ? 'timestamp with time zone' : 'character varying',
        is_nullable,
        column_default,
    }));
}

function schemaConstraints(overrides = {}) {
    const constraints = [
        [
            'matches_pipeline_status_valid',
            'c',
            "CHECK (((pipeline_status)::text = ANY ((ARRAY['pending'::character varying, 'processing'::character varying, 'harvested'::character varying, 'failed'::character varying, 'skipped'::character varying, 'RECON_LINKED'::character varying, 'RECON_MISMATCH'::character varying])::text[])))",
        ],
        ['matches_pkey', 'p', 'PRIMARY KEY (match_id)'],
        ['season_format', 'c', "CHECK (((season)::text ~ '^\\d{4}/\\d{4}$'::text))"],
        ['status_lowercase', 'c', 'CHECK (((status)::text = lower((status)::text)))'],
        [
            'valid_scores',
            'c',
            'CHECK ((((home_score IS NULL) AND (away_score IS NULL)) OR ((home_score >= 0) AND (away_score >= 0))))',
        ],
    ];
    const filtered = constraints.filter(([name]) => !new Set(overrides.omit || []).has(name));
    return filtered.map(([conname, contype, definition]) => ({ conname, contype, definition }));
}

function postRowsFor(candidates = candidates50()) {
    return candidates.map(target => ({
        match_id: target.match_id,
        external_id: target.external_id,
        league_name: 'Ligue 1',
        season: '2025/2026',
        home_team: target.home_team,
        away_team: target.away_team,
        match_date: target.match_date || target.kickoff_time,
        status: target.status,
        is_finished: target.status === 'finished',
        data_source: 'fotmob',
        pipeline_status: 'pending',
    }));
}

function buildPlan(customManifest = manifest(), options = {}) {
    return mod.buildExecutionPlanPayload({
        input: validInput(),
        manifest: customManifest,
        protectedTableRowsBefore: protectedRows(options.beforeCounts || mod.EXPECTED_BEFORE_COUNTS),
        matchesColumnRows: options.columns || schemaColumns(options.columnOptions),
        matchesConstraintRows: options.constraints || schemaConstraints(options.constraintOptions),
        existingMatchRows: options.existingRows || [],
        generatedAt: '2026-05-18T00:00:00.000Z',
    });
}

class FakeClient {
    constructor(options = {}) {
        this.options = options;
        this.queries = [];
        this.inserted = false;
        this.begin = false;
        this.committed = false;
        this.rolledBack = false;
    }

    async query(sql, params = []) {
        this.queries.push({ sql, params });
        const compact = String(sql).replace(/\s+/g, ' ').trim();
        const transactionResult = this.queryTransactionControl(compact);
        if (transactionResult) return transactionResult;
        if (MATCHES_INSERT_RE.test(compact)) {
            this.inserted = true;
            return { rows: [], rowCount: this.options.insertedRowCount ?? 50 };
        }
        return this.querySelect(compact);
    }

    queryTransactionControl(compact) {
        if (compact === 'BEGIN') {
            this.begin = true;
            return { rows: [], rowCount: 0 };
        }
        if (compact === 'COMMIT') {
            this.committed = true;
            return { rows: [], rowCount: 0 };
        }
        if (compact === 'ROLLBACK') {
            this.rolledBack = true;
            return { rows: [], rowCount: 0 };
        }
        return null;
    }

    querySelect(compact) {
        if (compact.includes('FROM information_schema.columns')) {
            return { rows: this.options.columns || schemaColumns() };
        }
        if (compact.includes('FROM pg_constraint')) {
            return { rows: this.options.constraints || schemaConstraints() };
        }
        if (compact.includes('GROUP BY match_id')) {
            return { rows: this.options.duplicateRows || [] };
        }
        if (compact.includes('WHERE match_id = ANY($1::text[]) OR external_id = ANY($2::text[])')) {
            return { rows: this.options.existingRows || [] };
        }
        if (compact.includes('WHERE match_id = ANY($1::text[])')) {
            return { rows: this.options.postRows || postRowsFor(this.options.candidates || candidates50()) };
        }
        const countRows = this.queryProtectedCounts(compact);
        if (countRows) return countRows;
        return { rows: [], rowCount: 0 };
    }

    queryProtectedCounts(compact) {
        if (compact.includes("SELECT 'matches' AS table_name")) {
            if (this.inserted) {
                return {
                    rows: protectedRows(this.options.afterCounts || mod.EXPECTED_AFTER_COUNTS),
                };
            }
            return { rows: protectedRows(this.options.beforeCounts || mod.EXPECTED_BEFORE_COUNTS) };
        }
        return null;
    }
}

test('valid input succeeds', () => {
    assert.equal(mod.validateExecuteInput(validInput()).ok, true);
});

for (const [name, overrides] of [
    ['final-db-write-confirmation missing blocked', { finalDbWriteConfirmation: null }],
    ['allow-db-write not yes blocked', { allowDbWrite: false }],
    ['allow-matches-write not yes blocked', { allowMatchesWrite: false }],
    ['allow-raw-match-data-write=yes blocked', { allowRawMatchDataWrite: true }],
    ['allow-bookmaker-odds-write=yes blocked', { allowBookmakerOddsWrite: true }],
    ['allow-feature-write=yes blocked', { allowFeatureWrite: true }],
    ['allow-network=yes blocked', { allowNetwork: true }],
    ['allow-match-detail-fetch=yes blocked', { allowMatchDetailFetch: true }],
    ['allow-controlled-raw-write=yes blocked', { allowControlledRawWrite: true }],
    ['allow-schema-migration=yes blocked', { allowSchemaMigration: true }],
    ['allow-parser-implementation=yes blocked', { allowParserImplementation: true }],
    ['allow-feature-extraction=yes blocked', { allowFeatureExtraction: true }],
    ['allow-training=yes blocked', { allowTraining: true }],
    ['allow-prediction=yes blocked', { allowPrediction: true }],
    ['allow-odds-write=yes blocked', { allowOddsWrite: true }],
]) {
    test(name, () => {
        assert.equal(mod.validateExecuteInput(validInput(overrides)).ok, false);
    });
}

test('parseArgs maps Makefile flags', () => {
    const parsed = mod.parseArgs(validArgv());
    assert.equal(parsed.finalDbWriteConfirmation, true);
    assert.equal(parsed.allowRawMatchDataWrite, false);
});

test('parseArgs handles equals syntax, bare booleans, positional and unknown args', () => {
    const parsed = mod.parseArgs(['positional', '--source=fotmob', '--help', '--unexpected=value']);
    assert.equal(parsed.source, 'fotmob');
    assert.equal(parsed.help, true);
    assert.deepEqual(parsed.unknown, ['positional', 'unexpected']);
});

test('normalizeBooleanFlag covers aliases and fallback', () => {
    assert.equal(mod.normalizeBooleanFlag('y'), true);
    assert.equal(mod.normalizeBooleanFlag('off'), false);
    assert.equal(mod.normalizeBooleanFlag('maybe', 'fallback'), 'fallback');
});

test('missing no guardrail is blocked explicitly', () => {
    const result = mod.validateExecuteInput(validInput({ allowNetwork: null }));
    assert.equal(result.ok, false);
    assert.match(result.errors.join('\n'), /missing allow-network=no/);
});

test('manifest candidate_targets not 50 blocked', () => {
    assert.equal(buildPlan(manifest({ candidate_targets: candidates50().slice(0, 49) })).ok, false);
});

test('seed plan status not ready blocked', () => {
    assert.equal(buildPlan(manifest({ matches_identity_seed_plan_status: 'pending' })).ok, false);
});

test('manifest metadata mismatches are blocked', () => {
    const result = buildPlan(
        manifest({
            schema_version: 'wrong',
            batch_id: 'wrong',
            source: 'other',
            league: { league_id: 1, league_name: 'Other', season: '2024/2025' },
            known_completed_targets: [],
            matches_identity_seed_authorization_status: 'pending',
            eligible_matches_insert_count: 49,
            required_next_step: 'other_step',
        })
    );
    assert.equal(result.ok, false);
    assert.match(result.blocked_reason, /schema_version|batch_id|authorization_status|required_next_step/);
});

for (const [name, override] of [
    ['missing match_id blocked', { match_id: '' }],
    ['invalid external_id blocked', { external_id: 'abc' }],
    ['wrong match_id convention blocked', { match_id: '53_20252026_9999999' }],
    ['missing home_team blocked', { home_team: '' }],
    ['missing away_team blocked', { away_team: '' }],
    ['missing match_date/kickoff_time blocked', { match_date: '', kickoff_time: '' }],
    ['missing status blocked', { status: '' }],
    ['status not lowercase-compatible blocked', { status: 'Finished' }],
]) {
    test(name, () => {
        const targets = candidates50({ 0: override });
        assert.equal(buildPlan(manifest({ candidate_targets: targets })).ok, false);
    });
}

test('invented marker and wrong matches seed status are blocked', () => {
    const targets = candidates50({
        0: { invented_external_id: true },
        1: { matches_identity_seed_status: 'pending' },
    });
    const plan = buildPlan(manifest({ candidate_targets: targets }));
    assert.equal(plan.ok, false);
    assert.equal(plan.identity_conflict_gate.invalid_identity_count, 2);
});

test('duplicate match_id blocked', () => {
    const targets = candidates50({ 1: { match_id: '53_20252026_4830460', external_id: '4830460' } });
    const plan = buildPlan(manifest({ candidate_targets: targets }));
    assert.equal(plan.ok, false);
    assert.equal(plan.identity_conflict_gate.duplicate_match_id_count, 1);
});

test('duplicate external_id blocked', () => {
    const targets = candidates50({ 1: { external_id: '4830460', match_id: '53_20252026_4830460' } });
    const plan = buildPlan(manifest({ candidate_targets: targets }));
    assert.equal(plan.ok, false);
    assert.equal(plan.identity_conflict_gate.duplicate_external_id_count, 1);
});

test('matches schema missing required column blocked', () => {
    const columns = schemaColumns().filter(row => row.column_name !== 'home_team');
    assert.equal(buildPlan(manifest(), { columns }).ok, false);
});

test('pipeline_status required but valid value cannot be determined blocked', () => {
    const columns = schemaColumns({ pipelineNullable: 'NO', pipelineDefault: '' });
    const constraints = schemaConstraints({ omit: ['matches_pipeline_status_valid'] });
    const plan = buildPlan(manifest(), { columns, constraints });
    assert.equal(plan.ok, false);
    assert.match(plan.blocked_reason, /pipeline_status|required/i);
});

test('pipeline_status required without default uses pending when constraint allows it', () => {
    const columns = schemaColumns({ pipelineNullable: 'NO', pipelineDefault: '' });
    const plan = buildPlan(manifest(), { columns });
    assert.equal(plan.ok, true);
    assert.equal(plan.schema_gate.pipeline_status_policy.insert_value, 'pending');
    assert.equal(plan.insert_columns.includes('pipeline_status'), true);
});

test('existing match_id conflict blocked', () => {
    const first = candidates50()[0];
    const plan = buildPlan(manifest(), { existingRows: [postRowsFor([first])[0]] });
    assert.equal(plan.ok, false);
    assert.equal(plan.identity_conflict_gate.match_id_conflict_count, 1);
});

test('external_id conflict blocked', () => {
    const first = candidates50()[0];
    const plan = buildPlan(manifest(), {
        existingRows: [{ ...postRowsFor([first])[0], match_id: '53_20252026_9999999' }],
    });
    assert.equal(plan.ok, false);
    assert.equal(plan.identity_conflict_gate.external_id_conflict_count, 1);
});

test('schema gate excludes league_id and uses pipeline default', () => {
    const plan = buildPlan();
    assert.equal(plan.ok, true);
    assert.equal(plan.insert_columns.includes('league_id'), false);
    assert.equal(plan.schema_gate.pipeline_status_policy.use_default, true);
});

test('guard blocks write path when DRY_RUN is not false', async () => {
    const client = new FakeClient();
    await assert.rejects(
        () => runCliWithDbWriteGuardEnv(
            validArgv(),
            {
                client,
                manifest: manifest(),
                writeManifestFile: () => {},
                writeReportFile: () => {},
                output: () => {},
            },
            { DRY_RUN: undefined }
        ),
        /DRY_RUN is enabled/
    );
    assert.equal(client.begin, false);
});

test('all gates pass begins transaction', async () => {
    const client = new FakeClient();
    const result = await runCliWithDbWriteGuardEnv(validArgv(), {
        client,
        manifest: manifest(),
        generatedAt: '2026-05-18T00:00:00.000Z',
        writeManifestFile: () => {},
        writeReportFile: () => {},
        output: () => {},
    });
    assert.equal(result.status, 0);
    assert.equal(client.begin, true);
});

test('inserts exactly 50 matches rows', async () => {
    const client = new FakeClient();
    const result = await runCliWithDbWriteGuardEnv(validArgv(), {
        client,
        manifest: manifest(),
        writeManifestFile: () => {},
        writeReportFile: () => {},
        output: () => {},
    });
    assert.equal(result.payload.inserted_count, 50);
    assert.equal(client.inserted, true);
});

test('inserted_count mismatch rolls back', async () => {
    const client = new FakeClient({ insertedRowCount: 49 });
    const result = await runCliWithDbWriteGuardEnv(validArgv(), {
        client,
        manifest: manifest(),
        writeManifestFile: () => {},
        writeReportFile: () => {},
        output: () => {},
    });
    assert.equal(result.status, 1);
    assert.equal(client.rolledBack, true);
});

test('raw_match_data count changed rolls back or blocks', async () => {
    const client = new FakeClient({ afterCounts: { ...mod.EXPECTED_AFTER_COUNTS, raw_match_data: 19 } });
    const result = await runCliWithDbWriteGuardEnv(validArgv(), {
        client,
        manifest: manifest(),
        writeManifestFile: () => {},
        writeReportFile: () => {},
        output: () => {},
    });
    assert.equal(result.status, 1);
    assert.equal(client.rolledBack, true);
});

test('protected table count changed rolls back or blocks', async () => {
    const client = new FakeClient({ afterCounts: { ...mod.EXPECTED_AFTER_COUNTS, predictions: 3 } });
    const result = await runCliWithDbWriteGuardEnv(validArgv(), {
        client,
        manifest: manifest(),
        writeManifestFile: () => {},
        writeReportFile: () => {},
        output: () => {},
    });
    assert.equal(result.status, 1);
    assert.equal(client.rolledBack, true);
});

test('post-write matches 10->60 verified', async () => {
    const result = await runCliWithDbWriteGuardEnv(validArgv(), {
        client: new FakeClient(),
        manifest: manifest(),
        writeManifestFile: () => {},
        writeReportFile: () => {},
        output: () => {},
    });
    assert.equal(result.payload.post_write_verification.db_counts_after.matches, 60);
});

test('post-write raw_match_data remains 18 verified', async () => {
    const result = await runCliWithDbWriteGuardEnv(validArgv(), {
        client: new FakeClient(),
        manifest: manifest(),
        writeManifestFile: () => {},
        writeReportFile: () => {},
        output: () => {},
    });
    assert.equal(result.payload.post_write_verification.db_counts_after.raw_match_data, 18);
});

test('inserted identity fields match manifest', async () => {
    const result = await runCliWithDbWriteGuardEnv(validArgv(), {
        client: new FakeClient(),
        manifest: manifest(),
        writeManifestFile: () => {},
        writeReportFile: () => {},
        output: () => {},
    });
    assert.equal(result.payload.post_write_verification.identity_fields_match_manifest, true);
});

test('post-write verification detects missing row, identity mismatch, and duplicate match_id', () => {
    const targets = candidates50().map(target => mod.buildInsertRow(target, buildPlan().schema_gate));
    const candidateRowsAfter = postRowsFor(candidates50()).slice(1);
    candidateRowsAfter[0] = { ...candidateRowsAfter[0], home_team: 'Wrong Home' };
    const verification = mod.buildPostWriteVerification({
        protectedTableRowsAfter: protectedRows(mod.EXPECTED_AFTER_COUNTS),
        candidateRowsAfter,
        duplicateRows: [{ match_id: 'duplicate', rows: 1 }],
        candidates: targets,
    });
    assert.equal(verification.ok, false);
    assert.equal(verification.duplicate_match_id_count, 1);
    assert.equal(verification.identity_fields_match_manifest, false);
});

test('manifest update records execution status and next step', async () => {
    let updatedManifest = null;
    const result = await runCliWithDbWriteGuardEnv(validArgv(), {
        client: new FakeClient(),
        manifest: manifest(),
        writeManifestFile: (_file, data) => {
            updatedManifest = data;
        },
        writeReportFile: () => {},
        output: () => {},
    });
    assert.equal(result.status, 0);
    assert.equal(updatedManifest.matches_identity_seed_execution_status, 'completed');
    assert.equal(updatedManifest.required_next_step, mod.NEXT_STEP_AFTER_SUCCESS);
    assert.equal(result.payload.matches_seed_status_distribution.inserted_matches_identity, 50);
});

test('runCli invalid input exits non-zero before DB access', async () => {
    const client = {
        query() {
            throw new Error('DB_SHOULD_NOT_BE_USED');
        },
    };
    const result = await mod.runCli(validArgv({ 'allow-network': 'yes' }), {
        client,
        output: () => {},
    });
    assert.equal(result.status, 1);
    assert.match(result.payload.blocked_reason, /INPUT_BLOCKED/);
});

test('runCli catches read failures and can skip manifest/report writes', async () => {
    const result = await runCliWithDbWriteGuardEnv(validArgv(), {
        client: {
            query() {
                throw new Error('READ_FAILED');
            },
        },
        manifest: manifest(),
        writeManifest: false,
        writeReport: false,
        output: () => {},
    });
    assert.equal(result.status, 1);
    assert.equal(result.payload.blocked_reason, 'READ_FAILED');
});

test('runCli write toggles can skip manifest and report output after success', async () => {
    const result = await runCliWithDbWriteGuardEnv(validArgv(), {
        client: new FakeClient(),
        manifest: manifest(),
        writeManifest: false,
        writeReport: false,
        output: () => {},
    });
    assert.equal(result.status, 0);
    assert.equal(result.payload.manifest_updated, false);
    assert.equal(result.payload.report_updated, false);
});

test('transaction insert error rolls back and reports controlled failure', async () => {
    class InsertFailureClient extends FakeClient {
        async query(sql, params = []) {
            const compact = String(sql).replace(/\s+/g, ' ').trim();
            if (MATCHES_INSERT_RE.test(compact)) {
                this.inserted = true;
                throw new Error('INSERT_FAILED');
            }
            return super.query(sql, params);
        }
    }
    const client = new InsertFailureClient();
    const result = await runCliWithDbWriteGuardEnv(validArgv(), {
        client,
        manifest: manifest(),
        writeManifestFile: () => {},
        writeReportFile: () => {},
        output: () => {},
    });
    assert.equal(result.status, 1);
    assert.equal(client.rolledBack, true);
    assert.equal(result.payload.blocked_reason, 'INSERT_FAILED');
});

test('no raw_match_data write', async () => {
    const client = new FakeClient();
    await runCliWithDbWriteGuardEnv(validArgv(), {
        client,
        manifest: manifest(),
        writeManifestFile: () => {},
        writeReportFile: () => {},
        output: () => {},
    });
    assert.doesNotMatch(client.queries.map(query => query.sql).join('\n'), /\bINSERT\s+INTO\s+raw_match_data\b/i);
});

test('no odds write', async () => {
    const client = new FakeClient();
    await runCliWithDbWriteGuardEnv(validArgv(), {
        client,
        manifest: manifest(),
        writeManifestFile: () => {},
        writeReportFile: () => {},
        output: () => {},
    });
    assert.doesNotMatch(
        client.queries.map(query => query.sql).join('\n'),
        /\bINSERT\s+INTO\s+bookmaker_odds_history\b/i
    );
});

test('no feature/training/prediction write', async () => {
    const client = new FakeClient();
    await runCliWithDbWriteGuardEnv(validArgv(), {
        client,
        manifest: manifest(),
        writeManifestFile: () => {},
        writeReportFile: () => {},
        output: () => {},
    });
    const sql = client.queries.map(query => query.sql).join('\n');
    assert.doesNotMatch(sql, /\bINSERT\s+INTO\s+(l3_features|match_features_training|predictions)\b/i);
});

test('no network', () => {
    const source = fs.readFileSync(MODULE_PATH, 'utf8');
    const forbiddenNetworkPattern = new RegExp([
        `${['fet', 'ch'].join('')}\\(`,
        ['ax', 'ios'].join(''),
        ['https', 'request'].join('\\.'),
        ['http', 'request'].join('\\.'),
    ].join('|'));
    assert.doesNotMatch(source, forbiddenNetworkPattern);
});

test('no match detail fetch', () => {
    const source = fs.readFileSync(MODULE_PATH, 'utf8');
    assert.doesNotMatch(
        source,
        /require\(['"].*FotMobRawDetailFetcher|from\s+['"].*FotMobRawDetailFetcher|new\s+FotMobRawDetailFetcher|matchDetails\(|fetchMatchDetail/i
    );
});

test('no parser/features/training', () => {
    const source = fs.readFileSync(MODULE_PATH, 'utf8');
    assert.doesNotMatch(
        source,
        /require\(['"].*(train_model|feature_extraction|parser)|from\s+['"].*(train_model|feature_extraction|parser)|npm\s+run\s+train|spawn\([^)]*train/i
    );
});

test('no ProductionHarvester/raw ingest import', () => {
    const source = fs.readFileSync(MODULE_PATH, 'utf8');
    assert.doesNotMatch(
        source,
        /ProductionHarvester|raw_match_data_local_ingest|remaining_seeded_pageprops_v2_controlled_write/
    );
});

test('no odds_harvest_pipeline import', () => {
    const source = fs.readFileSync(MODULE_PATH, 'utf8');
    assert.doesNotMatch(source, /odds_harvest_pipeline/);
});

test('no forbidden runtime imports while loading module', () => {
    const loaded = [];
    const originalLoad = Module._load;
    Module._load = function patchedLoad(request, parent, isMain) {
        loaded.push(request);
        return originalLoad.apply(this, [request, parent, isMain]);
    };
    try {
        loadFreshModule();
    } finally {
        Module._load = originalLoad;
    }
    assert.ok(!loaded.some(request => ['http', 'https', 'child_process', 'playwright', 'puppeteer'].includes(request)));
});

test('queryReadOnly blocks non SELECT SQL and SELECT locks', async () => {
    const client = new FakeClient();
    await assert.rejects(
        () => mod.queryReadOnly(client, `${MATCHES_INSERT_PREFIX}(match_id) VALUES($1)`, ['x']),
        /READ_ONLY/
    );
    await assert.rejects(() => mod.queryReadOnly(client, 'SELECT CREATE FROM matches'), /READ_ONLY/);
    await assert.rejects(() => mod.queryReadOnly(client, 'SELECT * FROM matches FOR UPDATE'), /READ_ONLY/);
});

test('buildInsertStatement targets matches only', () => {
    const plan = buildPlan();
    const statement = mod.buildInsertStatement(plan.insert_rows, plan.insert_columns);
    assert.match(statement.sql, new RegExp(`^${MATCHES_INSERT_PREFIX} `));
    assert.equal(statement.sql.includes('league_id'), false);
});
