'use strict';

/* eslint-disable max-lines */

const assert = require('node:assert/strict');
const fs = require('node:fs');
const Module = require('node:module');
const path = require('node:path');
const test = require('node:test');

const PROJECT_ROOT = path.resolve(__dirname, '../..');
const MODULE_PATH = path.join(PROJECT_ROOT, 'scripts/ops/controlled_matches_identity_seed_prerequisite_plan.js');

function loadFreshModule() {
    delete require.cache[require.resolve(MODULE_PATH)];
    return require(MODULE_PATH);
}

const mod = loadFreshModule();

function validInput(overrides = {}) {
    return {
        manifest: mod.MANIFEST_PATH,
        source: 'fotmob',
        leagueId: 53,
        leagueName: 'Ligue 1',
        season: '2025/2026',
        batchId: mod.BATCH_ID,
        targetCount: 50,
        planningAuthorization: true,
        allowDbWrite: false,
        allowMatchesWrite: false,
        allowRawMatchDataWrite: false,
        allowControlledWrite: false,
        allowNetwork: false,
        allowMatchDetailFetch: false,
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
        'planning-authorization': 'yes',
        'allow-db-write': 'no',
        'allow-matches-write': 'no',
        'allow-raw-match-data-write': 'no',
        'allow-controlled-write': 'no',
        'allow-network': 'no',
        'allow-match-detail-fetch': 'no',
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
        source_path: 'l1_api_data_leagues',
        league_id: 53,
        league_name: 'Ligue 1',
        season: '2025/2026',
        home_team: `Home ${index}`,
        away_team: `Away ${index}`,
        kickoff_time: `2025-08-${day}T18:45:00.000Z`,
        match_date: `2025-08-${day}T18:45:00.000Z`,
        status: 'finished',
        priority: index + 1,
        existing_versions: [],
        preflight_status: 'hash_baseline_ready',
        baseline_hash: 'a'.repeat(64),
        write_status: 'blocked_missing_matches_fk_prerequisite',
        failure_reason: 'blocked_missing_matches_fk_prerequisite',
        source_fidelity_notes: 'pageprops_v2_no_write_preflight_passed_no_full_body_or_pageprops_saved',
        required_next_step: 'controlled_matches_identity_seed_prerequisite_planning',
        ...overrides,
    };
}

function knownCompleted() {
    return ['4830746', '4830747', '4830748', '4830750', '4830751', '4830752', '4830753', '4830754'].map(externalId => ({
        target_id: `${mod.BATCH_ID}:53_20252026_${externalId}`,
        batch_id: mod.BATCH_ID,
        source: 'fotmob',
        route: 'html_hydration',
        raw_data_version: 'fotmob_pageprops_v2',
        hash_strategy: 'stable_pageprops_payload_v1',
        match_id: `53_20252026_${externalId}`,
        external_id: externalId,
        league_id: 53,
        league_name: 'Ligue 1',
        season: '2025/2026',
        target_status: 'already_completed',
    }));
}

function manifest(overrides = {}) {
    return {
        schema_version: 'target_manifest_proposal_v1',
        batch_id: mod.BATCH_ID,
        source: 'fotmob',
        route: 'html_hydration',
        raw_data_version: 'fotmob_pageprops_v2',
        hash_strategy: 'stable_pageprops_payload_v1',
        league: {
            league_id: 53,
            league_name: 'Ligue 1',
            season: '2025/2026',
        },
        target_population_status: 'ready_for_controlled_write_authorization',
        known_completed_targets: knownCompleted(),
        candidate_targets: Array.from({ length: 50 }, (_, index) => candidate(index)),
        write_execution_status: 'blocked_missing_matches_fk_prerequisite',
        raw_match_data_write_status: 'not_executed',
        required_next_step: 'controlled_matches_identity_seed_prerequisite_planning',
        ...overrides,
    };
}

function protectedRows(overrides = {}) {
    const rows = {
        matches: 10,
        bookmaker_odds_history: 2,
        raw_match_data: 18,
        l3_features: 2,
        match_features_training: 2,
        predictions: 2,
        ...overrides,
    };
    return Object.entries(rows).map(([table_name, rowsValue]) => ({ table_name, rows: rowsValue }));
}

function matchesColumns(extra = []) {
    return [
        { column_name: 'match_id', data_type: 'character varying', is_nullable: 'NO', column_default: null },
        { column_name: 'external_id', data_type: 'character varying', is_nullable: 'YES', column_default: null },
        {
            column_name: 'league_name',
            data_type: 'character varying',
            is_nullable: 'NO',
            column_default: "'Premier League'::character varying",
        },
        {
            column_name: 'season',
            data_type: 'character varying',
            is_nullable: 'NO',
            column_default: "'2324'::character varying",
        },
        { column_name: 'home_team', data_type: 'character varying', is_nullable: 'NO', column_default: null },
        { column_name: 'away_team', data_type: 'character varying', is_nullable: 'NO', column_default: null },
        { column_name: 'match_date', data_type: 'timestamp with time zone', is_nullable: 'YES', column_default: null },
        {
            column_name: 'status',
            data_type: 'character varying',
            is_nullable: 'YES',
            column_default: "'Scheduled'::character varying",
        },
        { column_name: 'is_finished', data_type: 'boolean', is_nullable: 'YES', column_default: 'false' },
        { column_name: 'data_source', data_type: 'character varying', is_nullable: 'YES', column_default: "'FotMob'" },
        {
            column_name: 'pipeline_status',
            data_type: 'character varying',
            is_nullable: 'YES',
            column_default: "'pending'",
        },
        ...extra,
    ];
}

function matchesConstraints(extra = []) {
    return [
        { conname: 'matches_pkey', contype: 'p', definition: 'PRIMARY KEY (match_id)' },
        { conname: 'season_format', contype: 'c', definition: "CHECK (((season)::text ~ '^\\d{4}/\\d{4}$'::text))" },
        { conname: 'status_lowercase', contype: 'c', definition: 'CHECK (((status)::text = lower((status)::text)))' },
        {
            conname: 'matches_pipeline_status_valid',
            contype: 'c',
            definition:
                "CHECK (((pipeline_status)::text = ANY ((ARRAY['pending','processing','harvested','failed','skipped','RECON_LINKED','RECON_MISMATCH'])::text[])))",
        },
        ...extra,
    ];
}

function matchesIndexes(extra = []) {
    return [
        {
            indexname: 'matches_pkey',
            indexdef: 'CREATE UNIQUE INDEX matches_pkey ON public.matches USING btree (match_id)',
        },
        {
            indexname: 'idx_matches_season',
            indexdef: 'CREATE INDEX idx_matches_season ON public.matches USING btree (season)',
        },
        ...extra,
    ];
}

function existingMatchFromCandidate(index, overrides = {}) {
    const target = candidate(index);
    return {
        match_id: target.match_id,
        external_id: target.external_id,
        league_name: target.league_name,
        season: target.season,
        home_team: target.home_team,
        away_team: target.away_team,
        match_date: target.match_date,
        status: target.status,
        ...overrides,
    };
}

function buildPayload(overrides = {}) {
    return mod.buildMatchesIdentitySeedPlanningPayload({
        input: validInput(),
        manifest: overrides.manifest || manifest(),
        protectedTableRowsBefore: overrides.protectedTableRowsBefore || protectedRows(),
        protectedTableRowsAfter: overrides.protectedTableRowsAfter || protectedRows(),
        matchesColumnRows: overrides.matchesColumnRows || matchesColumns(),
        matchesConstraintRows: overrides.matchesConstraintRows || matchesConstraints(),
        matchesIndexRows: overrides.matchesIndexRows || matchesIndexes(),
        existingMatchRows: overrides.existingMatchRows || [],
        generatedAt: '2026-05-18T00:00:00.000Z',
    });
}

function fakeClient({
    existingMatchRows = [],
    columns = matchesColumns(),
    constraints = matchesConstraints(),
    indexes = matchesIndexes(),
    baseline = protectedRows(),
} = {}) {
    const queries = [];
    return {
        queries,
        async query(sql, params) {
            queries.push({ sql, params });
            assert.match(sql.trim(), /^SELECT/i);
            assert.doesNotMatch(sql, /\b(INSERT|UPDATE|DELETE|TRUNCATE|ALTER|DROP|CREATE|LOCK|COPY)\b/i);
            if (/UNION ALL/i.test(sql)) return { rows: baseline };
            if (/information_schema\.columns/i.test(sql)) return { rows: columns };
            if (/FROM pg_constraint/i.test(sql)) return { rows: constraints };
            if (/FROM pg_indexes/i.test(sql)) return { rows: indexes };
            if (/FROM matches/i.test(sql)) return { rows: existingMatchRows };
            return { rows: [] };
        },
    };
}

function assertInvalid(overrides, pattern) {
    const result = mod.validatePlanInput(validInput(overrides));
    assert.equal(result.ok, false);
    assert.match(result.errors.join('\n'), pattern);
}

test('valid input succeeds', () => {
    assert.equal(mod.validatePlanInput(validInput()).ok, true);
});

test('manifest missing fails', async () => {
    const originalReadFileSync = fs.readFileSync;
    fs.readFileSync = function patchedReadFileSync(filePath, ...args) {
        if (String(filePath).endsWith(mod.MANIFEST_PATH)) {
            const error = new Error('ENOENT: no such file or directory');
            error.code = 'ENOENT';
            throw error;
        }
        return originalReadFileSync.call(this, filePath, ...args);
    };
    try {
        const result = await mod.runCli(validArgv({ manifest: mod.MANIFEST_PATH }), {
            client: fakeClient(),
            writeManifest: false,
            writeReport: false,
            output: () => {},
        });
        assert.equal(result.status, 1);
        assert.match(result.payload.failure_reason, /ENOENT|no such file/i);
    } finally {
        fs.readFileSync = originalReadFileSync;
    }
});

test('wrong manifest path fails', () => {
    assertInvalid({ manifest: 'docs/_manifests/wrong.json' }, /manifest/);
});

for (const [title, overrides, pattern] of [
    ['source missing fails', { source: '' }, /source/],
    ['source non-fotmob fails', { source: 'other' }, /source/],
    ['league-id missing fails', { leagueId: null }, /league-id/],
    ['league-id not 53 fails', { leagueId: 54 }, /league-id/],
    ['league-name missing fails', { leagueName: '' }, /league-name/],
    ['league-name not Ligue 1 fails', { leagueName: 'Premier League' }, /league-name/],
    ['season missing fails', { season: '' }, /season/],
    ['season not 2025/2026 fails', { season: '2024/2025' }, /season/],
    ['batch-id missing fails', { batchId: '' }, /batch-id/],
    ['batch-id wrong fails', { batchId: 'wrong' }, /batch-id/],
    ['target-count not 50 fails', { targetCount: 49 }, /target-count/],
    ['planning-authorization=no blocked', { planningAuthorization: false }, /planning-authorization/],
    ['allow-db-write=yes blocked', { allowDbWrite: true }, /allow-db-write/],
    ['allow-matches-write=yes blocked', { allowMatchesWrite: true }, /allow-matches-write/],
    ['allow-raw-match-data-write=yes blocked', { allowRawMatchDataWrite: true }, /allow-raw-match-data-write/],
    ['allow-controlled-write=yes blocked', { allowControlledWrite: true }, /allow-controlled-write/],
    ['allow-network=yes blocked', { allowNetwork: true }, /allow-network/],
    ['allow-match-detail-fetch=yes blocked', { allowMatchDetailFetch: true }, /allow-match-detail-fetch/],
    ['allow-schema-migration=yes blocked', { allowSchemaMigration: true }, /allow-schema-migration/],
    ['allow-parser-implementation=yes blocked', { allowParserImplementation: true }, /allow-parser-implementation/],
    ['allow-feature-extraction=yes blocked', { allowFeatureExtraction: true }, /allow-feature-extraction/],
    ['allow-training=yes blocked', { allowTraining: true }, /allow-training/],
    ['allow-prediction=yes blocked', { allowPrediction: true }, /allow-prediction/],
    ['execute-write=yes blocked', { executeWrite: true }, /execute-write/],
    ['commit=yes blocked', { commit: true }, /commit/],
    [
        'final-db-write-confirmation=yes blocked in planning phase',
        { finalDbWriteConfirmation: true },
        /final-db-write-confirmation/,
    ],
    ['allow-odds-write=yes blocked', { allowOddsWrite: true }, /allow-odds-write/],
]) {
    test(title, () => {
        assertInvalid(overrides, pattern);
    });
}

test('parseArgs maps Makefile-style flags', () => {
    const parsed = mod.parseArgs(validArgv());
    assert.equal(parsed.manifest, mod.MANIFEST_PATH);
    assert.equal(parsed.leagueId, '53');
    assert.equal(parsed.planningAuthorization, true);
    assert.equal(parsed.allowDbWrite, false);
});

test('manifest candidate_targets not 50 fails', () => {
    const payload = buildPayload({ manifest: manifest({ candidate_targets: [candidate(0)] }) });
    assert.equal(payload.ok, false);
    assert.match(payload.failure_reason, /candidate_targets/);
});

test('manifest not blocked_missing_matches_fk_prerequisite fails', () => {
    const altered = manifest({
        write_execution_status: 'not_started',
        required_next_step: 'other_step',
        candidate_targets: Array.from({ length: 50 }, (_, index) => candidate(index, { write_status: 'not_started' })),
    });
    const payload = buildPayload({ manifest: altered });
    assert.equal(payload.ok, false);
    assert.match(payload.failure_reason, /blocked_missing_matches_fk_prerequisite/);
});

for (const [title, changedCandidate, pattern] of [
    ['candidate missing match_id blocked', { match_id: '' }, /match_id is required/],
    ['candidate invalid external_id blocked', { external_id: 'abc', match_id: '53_20252026_abc' }, /external_id/],
    ['candidate wrong match_id convention blocked', { match_id: '53_20252026_9999999' }, /match_id must be/],
    ['candidate missing home_team blocked', { home_team: '' }, /home_team/],
    ['candidate missing away_team blocked', { away_team: '' }, /away_team/],
    [
        'candidate missing match_date/kickoff_time blocked',
        { match_date: '', kickoff_time: '' },
        /match_date or kickoff_time/,
    ],
    ['candidate missing status blocked', { status: '' }, /status/],
]) {
    test(title, () => {
        const targets = Array.from({ length: 50 }, (_, index) => candidate(index, index === 0 ? changedCandidate : {}));
        const payload = buildPayload({ manifest: manifest({ candidate_targets: targets }) });
        assert.equal(payload.ok, false);
        assert.match(JSON.stringify(payload.target_summaries), pattern);
    });
}

test('duplicate match_id blocked', () => {
    const targets = Array.from({ length: 50 }, (_, index) =>
        candidate(index, index === 1 ? { match_id: '53_20252026_4830460' } : {})
    );
    const payload = buildPayload({ manifest: manifest({ candidate_targets: targets }) });
    assert.equal(payload.ok, false);
    assert.equal(payload.duplicate_match_id_count, 1);
});

test('duplicate external_id blocked', () => {
    const targets = Array.from({ length: 50 }, (_, index) =>
        candidate(index, index === 1 ? { external_id: '4830460' } : {})
    );
    const payload = buildPayload({ manifest: manifest({ candidate_targets: targets }) });
    assert.equal(payload.ok, false);
    assert.equal(payload.duplicate_external_id_count, 1);
});

test('existing matches count 0 -> eligible insert', () => {
    const payload = buildPayload();
    assert.equal(payload.ok, true);
    assert.equal(payload.eligible_matches_insert_count, 50);
    assert.equal(payload.missing_matches_count, 50);
    assert.equal(payload.matches_identity_seed_plan_status, 'ready_for_final_authorization');
});

test('existing matching matches rows -> skipped_existing_matches', () => {
    const rows = Array.from({ length: 50 }, (_, index) => existingMatchFromCandidate(index));
    const payload = buildPayload({ existingMatchRows: rows });
    assert.equal(payload.ok, false);
    assert.equal(payload.skipped_existing_matches_count, 50);
    assert.equal(payload.eligible_matches_insert_count, 0);
});

test('existing conflicting match_id identity -> blocked', () => {
    const payload = buildPayload({ existingMatchRows: [existingMatchFromCandidate(0, { home_team: 'Different' })] });
    assert.equal(payload.ok, false);
    assert.equal(payload.match_id_conflict_count, 1);
});

test('existing conflicting external_id identity -> blocked', () => {
    const payload = buildPayload({
        existingMatchRows: [existingMatchFromCandidate(0, { match_id: '53_20252026_9999999' })],
    });
    assert.equal(payload.ok, false);
    assert.equal(payload.external_id_conflict_count, 1);
});

test('required matches column missing in manifest -> blocked', () => {
    const payload = buildPayload({
        matchesColumnRows: matchesColumns([
            { column_name: 'neutral_site', data_type: 'boolean', is_nullable: 'NO', column_default: null },
        ]),
    });
    assert.equal(payload.ok, false);
    assert.match(payload.matches_schema_readiness.unmapped_required_columns.join(','), /neutral_site/);
});

test('all 50 eligible -> seed_plan_status ready_for_final_authorization', () => {
    const payload = buildPayload();
    assert.equal(payload.matches_identity_seed_plan_status, 'ready_for_final_authorization');
});

test('expected_matches_after calculated 10 + 50 = 60', () => {
    const payload = buildPayload();
    assert.equal(payload.expected_matches_after, 60);
});

test('raw_match_data remains unchanged in plan', () => {
    const payload = buildPayload();
    assert.equal(payload.raw_match_data_current_count, 18);
    assert.equal(payload.raw_match_data_after_planning, 18);
});

test('manifest update sets matches_identity_seed_authorization_status pending_final_db_write_confirmation', () => {
    const payload = buildPayload();
    const updated = mod.updateManifestWithMatchesIdentitySeedPlan(manifest(), payload, '2026-05-18T00:00:00.000Z');
    assert.equal(updated.matches_identity_seed_authorization_status, 'pending_final_db_write_confirmation');
    assert.equal(updated.candidate_targets[0].matches_identity_seed_status, 'eligible_matches_insert');
});

test('manifest update required_next_step controlled_matches_identity_seed_execution', () => {
    const payload = buildPayload();
    const updated = mod.updateManifestWithMatchesIdentitySeedPlan(manifest(), payload, '2026-05-18T00:00:00.000Z');
    assert.equal(updated.required_next_step, 'controlled_matches_identity_seed_execution');
});

test('no DB write through runCli', async () => {
    const client = fakeClient();
    const result = await mod.runCli(validArgv(), {
        client,
        manifest: manifest(),
        writeManifestFile: () => {},
        writeReportFile: () => {},
        output: () => {},
        generatedAt: '2026-05-18T00:00:00.000Z',
    });
    assert.equal(result.status, 0);
    assert.ok(client.queries.length > 0);
    for (const query of client.queries) assert.match(query.sql.trim(), /^SELECT/i);
});

test('no matches write', async () => {
    const client = fakeClient();
    const result = await mod.runCli(validArgv(), {
        client,
        manifest: manifest(),
        writeManifestFile: () => {},
        writeReportFile: () => {},
        output: () => {},
    });
    assert.equal(result.payload.matches_write_executed, false);
    assert.doesNotMatch(client.queries.map(query => query.sql).join('\n'), /\bINSERT\s+INTO\s+matches\b/i);
});

test('no raw_match_data write', async () => {
    const result = await mod.runCli(validArgv(), {
        client: fakeClient(),
        manifest: manifest(),
        writeManifestFile: () => {},
        writeReportFile: () => {},
        output: () => {},
    });
    assert.equal(result.payload.raw_match_data_write_executed, false);
});

test('no network', async () => {
    const result = await mod.runCli(validArgv(), {
        client: fakeClient(),
        manifest: manifest(),
        writeManifestFile: () => {},
        writeReportFile: () => {},
        output: () => {},
    });
    assert.equal(result.payload.network_executed, false);
});

test('no match detail fetch', async () => {
    const result = await mod.runCli(validArgv(), {
        client: fakeClient(),
        manifest: manifest(),
        writeManifestFile: () => {},
        writeReportFile: () => {},
        output: () => {},
    });
    assert.equal(result.payload.match_detail_fetch_executed, false);
});

test('no parser/features/training', async () => {
    const result = await mod.runCli(validArgv(), {
        client: fakeClient(),
        manifest: manifest(),
        writeManifestFile: () => {},
        writeReportFile: () => {},
        output: () => {},
    });
    assert.equal(result.payload.parser_features_training_executed, false);
});

test('queryReadOnly blocks non SELECT SQL and SELECT locks', async () => {
    const client = {
        async query() {
            return { rows: [] };
        },
    };
    await assert.rejects(
        () => mod.queryReadOnly(client, 'INSERT INTO matches(match_id) VALUES($1)', ['x']),
        /READ_ONLY/
    );
    await assert.rejects(() => mod.queryReadOnly(client, 'SELECT * FROM matches FOR UPDATE'), /READ_ONLY/);
});

test('runCli writes manifest and report through injected writers', async () => {
    let wroteManifest = null;
    let wroteReport = null;
    const result = await mod.runCli(validArgv(), {
        client: fakeClient(),
        manifest: manifest(),
        writeManifestFile: (_file, payload) => {
            wroteManifest = payload;
        },
        writeReportFile: (_file, content) => {
            wroteReport = content;
        },
        output: () => {},
        generatedAt: '2026-05-18T00:00:00.000Z',
    });
    assert.equal(result.status, 0);
    assert.equal(wroteManifest.matches_identity_seed_plan_status, 'ready_for_final_authorization');
    assert.match(wroteReport, /Controlled Matches Identity Seed Prerequisite Planning/);
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

test('no forbidden runtime imports while loading module', async () => {
    const originalLoad = Module._load;
    const loaded = [];
    Module._load = function patchedLoad(request, parent, isMain) {
        loaded.push(request);
        return originalLoad.call(this, request, parent, isMain);
    };
    try {
        loadFreshModule();
    } finally {
        Module._load = originalLoad;
    }
    assert.ok(!loaded.some(request => ['http', 'https', 'child_process', 'playwright', 'puppeteer'].includes(request)));
});

test('module source does not call file deletion APIs', () => {
    const source = fs.readFileSync(MODULE_PATH, 'utf8');
    assert.doesNotMatch(source, /\b(unlinkSync|rmSync|rmdirSync|fs\.rm|fs\.unlink|fs\.rmdir)\b/);
});
