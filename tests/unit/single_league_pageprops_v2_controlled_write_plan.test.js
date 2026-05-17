'use strict';

/* eslint-disable max-lines */

const assert = require('node:assert/strict');
const childProcess = require('node:child_process');
const fs = require('node:fs');
const http = require('node:http');
const https = require('node:https');
const Module = require('node:module');
const path = require('node:path');
const test = require('node:test');

const PROJECT_ROOT = path.resolve(__dirname, '../..');
const MODULE_PATH = path.join(PROJECT_ROOT, 'scripts/ops/single_league_pageprops_v2_controlled_write_plan.js');

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
        route: 'html_hydration',
        rawVersion: 'fotmob_pageprops_v2',
        hashStrategy: 'stable_pageprops_payload_v1',
        batchId: mod.BATCH_ID,
        targetCount: 50,
        writePlanningAuthorization: true,
        allowDbWrite: false,
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
        route: 'html_hydration',
        'raw-version': 'fotmob_pageprops_v2',
        'hash-strategy': 'stable_pageprops_payload_v1',
        'batch-id': mod.BATCH_ID,
        'target-count': '50',
        'write-planning-authorization': 'yes',
        'allow-db-write': 'no',
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
    return {
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
        home_team: `Home ${index}`,
        away_team: `Away ${index}`,
        kickoff_time: `2025-08-${String((index % 20) + 1).padStart(2, '0')}T18:45:00.000Z`,
        match_date: `2025-08-${String((index % 20) + 1).padStart(2, '0')}T18:45:00.000Z`,
        status: 'finished',
        target_status: 'preflight_passed',
        priority: index + 1,
        expected_coverage_tier: 'unknown_until_profiled',
        existing_versions: [],
        preflight_status: 'hash_baseline_ready',
        baseline_hash: 'a'.repeat(64),
        last_preflight_at: '2026-05-17T10:42:45.212Z',
        write_status: 'not_started',
        write_attempt_count: 0,
        failure_reason: null,
        source_fidelity_notes: 'pageprops_v2_no_write_preflight_passed_no_full_body_or_pageprops_saved',
        odds_alignment_ready: true,
        created_at: '2026-05-17T09:30:55.640Z',
        updated_at: '2026-05-17T10:42:45.212Z',
        pageprops_summary: {
            http_status: 200,
            parse_status: 'pageprops_v2_parsed',
            raw_data_shape_valid: true,
            has_meta: true,
            has_matchId: true,
            has_pageProps: true,
        },
        required_next_step: 'controlled_write_authorization_required',
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
        required_next_step: 'single_league_small_batch_controlled_pageprops_v2_write_authorization',
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

function constraintRows(overrides = []) {
    return [
        {
            conname: 'raw_match_data_match_id_data_version_key',
            contype: 'u',
            definition: 'UNIQUE (match_id, data_version)',
        },
        {
            conname: 'raw_match_data_match_id_fkey',
            contype: 'f',
            definition: 'FOREIGN KEY (match_id) REFERENCES matches(match_id)',
        },
        { conname: 'raw_data_not_empty', contype: 'c', definition: 'CHECK ((raw_data IS NOT NULL))' },
        ...overrides,
    ];
}

function buildPayload(overrides = {}) {
    return mod.buildWritePlanningPayload({
        input: validInput(),
        manifest: overrides.manifest || manifest(),
        protectedTableRowsBefore: overrides.protectedTableRowsBefore || protectedRows(),
        protectedTableRowsAfter: overrides.protectedTableRowsAfter || protectedRows(),
        constraintRows: overrides.constraintRows || constraintRows(),
        existingRows: overrides.existingRows || [],
        generatedAt: '2026-05-18T00:00:00.000Z',
    });
}

function fakeClient({ existingRows = [], constraints = constraintRows(), baseline = protectedRows() } = {}) {
    const queries = [];
    return {
        queries,
        async query(sql, params) {
            queries.push({ sql, params });
            assert.match(sql.trim(), /^SELECT/i);
            assert.doesNotMatch(sql, /\b(INSERT|UPDATE|DELETE|TRUNCATE|ALTER|DROP|CREATE|LOCK|COPY)\b/i);
            if (/UNION ALL/i.test(sql)) return { rows: baseline };
            if (/FROM pg_constraint/i.test(sql)) return { rows: constraints };
            if (/FROM raw_match_data/i.test(sql)) return { rows: existingRows };
            return { rows: [] };
        },
    };
}

function assertInvalid(overrides, pattern) {
    const result = mod.validatePlanInput(validInput(overrides));
    assert.equal(result.ok, false);
    assert.match(result.errors.join('\n'), pattern);
}

async function withPatched(object, property, replacement, callback) {
    const original = object[property];
    object[property] = replacement;
    try {
        return await callback();
    } finally {
        object[property] = original;
    }
}

test('valid input succeeds', () => {
    assert.equal(mod.validatePlanInput(validInput()).ok, true);
});

for (const [name, override, pattern] of [
    ['manifest missing fails', { manifest: '' }, /missing manifest=/],
    ['wrong manifest path fails', { manifest: 'docs/other.json' }, /manifest must be/],
    ['source missing fails', { source: '' }, /missing source=fotmob/],
    ['source non-fotmob fails', { source: 'other' }, /source must be fotmob/],
    ['league-id missing fails', { leagueId: null }, /league-id must be 53/],
    ['league-id not 53 fails', { leagueId: 54 }, /league-id must be 53/],
    ['league-name missing fails', { leagueName: '' }, /missing league-name/],
    ['league-name not Ligue 1 fails', { leagueName: 'Ligue 2' }, /league-name must be Ligue 1/],
    ['season missing fails', { season: '' }, /missing season/],
    ['season not 2025/2026 fails', { season: '2024/2025' }, /season must be 2025\/2026/],
    ['route missing fails', { route: '' }, /missing route/],
    ['route not html_hydration fails', { route: 'api_match_details' }, /route must be html_hydration/],
    ['raw-version missing fails', { rawVersion: '' }, /missing raw-version/],
    ['raw-version not fotmob_pageprops_v2 fails', { rawVersion: 'fotmob_html_hyd_v1' }, /raw-version must/],
    ['hash-strategy missing fails', { hashStrategy: '' }, /missing hash-strategy/],
    [
        'hash-strategy not stable_pageprops_payload_v1 fails',
        { hashStrategy: 'stable_raw_payload_v1' },
        /hash-strategy must/,
    ],
    ['batch-id missing fails', { batchId: '' }, /missing batch-id/],
    ['batch-id wrong fails', { batchId: 'wrong' }, /batch-id must/],
    ['target-count not 50 fails', { targetCount: 49 }, /target-count must be 50/],
    [
        'write-planning-authorization=no blocked',
        { writePlanningAuthorization: false },
        /write-planning-authorization=yes/,
    ],
    ['allow-db-write=yes blocked', { allowDbWrite: true }, /allow-db-write=yes is blocked/],
    ['allow-raw-match-data-write=yes blocked', { allowRawMatchDataWrite: true }, /allow-raw-match-data-write=yes/],
    ['allow-controlled-write=yes blocked', { allowControlledWrite: true }, /allow-controlled-write=yes/],
    ['allow-network=yes blocked', { allowNetwork: true }, /allow-network=yes/],
    ['allow-match-detail-fetch=yes blocked', { allowMatchDetailFetch: true }, /allow-match-detail-fetch=yes/],
    ['allow-schema-migration=yes blocked', { allowSchemaMigration: true }, /allow-schema-migration=yes/],
    ['allow-parser-implementation=yes blocked', { allowParserImplementation: true }, /allow-parser-implementation=yes/],
    ['allow-feature-extraction=yes blocked', { allowFeatureExtraction: true }, /allow-feature-extraction=yes/],
    ['allow-training=yes blocked', { allowTraining: true }, /allow-training=yes/],
    ['allow-prediction=yes blocked', { allowPrediction: true }, /allow-prediction=yes/],
    ['execute-write=yes blocked', { executeWrite: true }, /execute-write=yes is blocked/],
    ['commit=yes blocked', { commit: true }, /commit=yes is blocked/],
    [
        'final-db-write-confirmation=yes blocked in planning phase',
        { finalDbWriteConfirmation: true },
        /final-db-write-confirmation=yes/,
    ],
    ['allow-odds-write=yes blocked', { allowOddsWrite: true }, /allow-odds-write=yes is blocked/],
]) {
    test(name, () => {
        assertInvalid(override, pattern);
    });
}

test('parseArgs maps Makefile-style flags', () => {
    const parsed = mod.parseArgs(validArgv());
    assert.equal(parsed.leagueId, '53');
    assert.equal(parsed.writePlanningAuthorization, true);
    assert.equal(parsed.allowNetwork, false);
});

test('parseArgs records positional and unknown arguments', () => {
    const parsed = mod.parseArgs(['loose-token', '--unknown-flag=yes', '--write-planning-authorization']);
    assert.deepEqual(parsed.unknown, ['loose-token', 'unknown-flag']);
    assert.equal(parsed.writePlanningAuthorization, true);
});

test('normalizeBooleanFlag covers accepted aliases and fallback', () => {
    for (const value of ['1', 'true', 'yes', 'y', 'on']) assert.equal(mod.normalizeBooleanFlag(value, false), true);
    for (const value of ['0', 'false', 'no', 'n', 'off']) assert.equal(mod.normalizeBooleanFlag(value, true), false);
    assert.equal(mod.normalizeBooleanFlag('maybe', 'fallback'), 'fallback');
});

test('manifest candidate_targets not 50 fails', () => {
    const result = mod.validateManifestStructure(manifest({ candidate_targets: [] }));
    assert.equal(result.ok, false);
    assert.match(result.errors.join('\n'), /candidate_targets must contain 50/);
});

test('manifest target_population_status not ready_for_controlled_write_authorization fails', () => {
    const result = mod.validateManifestStructure(manifest({ target_population_status: 'partial_preflight_completed' }));
    assert.equal(result.ok, false);
    assert.match(result.errors.join('\n'), /ready_for_controlled_write_authorization/);
});

test('candidate preflight_status not hash_baseline_ready blocked', () => {
    const sourceManifest = manifest();
    sourceManifest.candidate_targets[0] = candidate(0, { preflight_status: 'failed' });
    const payload = buildPayload({ manifest: sourceManifest });
    assert.equal(payload.write_plan_status, 'blocked');
    assert.equal(payload.blocked_count, 1);
    assert.match(payload.target_summaries[0].failure_reason, /preflight_status/);
});

test('candidate baseline_hash missing blocked', () => {
    const sourceManifest = manifest();
    sourceManifest.candidate_targets[0] = candidate(0, { baseline_hash: null });
    const payload = buildPayload({ manifest: sourceManifest });
    assert.equal(payload.invalid_hash_count, 1);
    assert.equal(payload.write_plan_status, 'blocked');
});

test('candidate baseline_hash not 64 hex blocked', () => {
    const sourceManifest = manifest();
    sourceManifest.candidate_targets[0] = candidate(0, { baseline_hash: 'not-a-hash' });
    const payload = buildPayload({ manifest: sourceManifest });
    assert.equal(payload.invalid_hash_count, 1);
    assert.match(payload.target_summaries[0].failure_reason, /baseline_hash/);
});

test('candidate external_id invalid blocked', () => {
    const sourceManifest = manifest();
    sourceManifest.candidate_targets[0] = candidate(0, { external_id: 'abc', match_id: '53_20252026_abc' });
    const payload = buildPayload({ manifest: sourceManifest });
    assert.equal(payload.invalid_identity_count, 1);
    assert.equal(payload.write_plan_status, 'blocked');
});

test('candidate match_id convention wrong blocked', () => {
    const sourceManifest = manifest();
    sourceManifest.candidate_targets[0] = candidate(0, { match_id: 'wrong' });
    const payload = buildPayload({ manifest: sourceManifest });
    assert.equal(payload.invalid_identity_count, 1);
    assert.match(payload.target_summaries[0].failure_reason, /match_id/);
});

test('duplicate external_id blocked', () => {
    const sourceManifest = manifest();
    sourceManifest.candidate_targets[1] = candidate(1, {
        external_id: sourceManifest.candidate_targets[0].external_id,
        match_id: sourceManifest.candidate_targets[1].match_id,
    });
    const payload = buildPayload({ manifest: sourceManifest });
    assert.equal(payload.duplicate_external_id_count, 1);
    assert.equal(payload.write_plan_status, 'blocked');
});

test('duplicate match_id blocked', () => {
    const sourceManifest = manifest();
    sourceManifest.candidate_targets[1] = candidate(1, {
        match_id: sourceManifest.candidate_targets[0].match_id,
    });
    const payload = buildPayload({ manifest: sourceManifest });
    assert.equal(payload.duplicate_match_id_count, 1);
    assert.equal(payload.write_plan_status, 'blocked');
});

test('failure_reason present blocked', () => {
    const sourceManifest = manifest();
    sourceManifest.candidate_targets[0] = candidate(0, { failure_reason: 'PAGE_PROPS_NOT_FOUND' });
    const payload = buildPayload({ manifest: sourceManifest });
    assert.equal(payload.write_plan_status, 'blocked');
    assert.match(payload.target_summaries[0].failure_reason, /failure_reason/);
});

test('existing v2 in fake DB sets skipped_existing_v2', () => {
    const target = manifest().candidate_targets[0];
    const payload = buildPayload({
        existingRows: [
            {
                match_id: target.match_id,
                external_id: target.external_id,
                data_version: 'fotmob_pageprops_v2',
                data_hash: 'b'.repeat(64),
            },
        ],
    });
    assert.equal(payload.skipped_existing_v2_count, 1);
    assert.equal(payload.target_summaries[0].write_eligibility_status, 'skipped_existing_v2');
});

test('no existing v2 -> eligible insert', () => {
    const payload = buildPayload();
    assert.equal(payload.eligible_insert_count, 50);
    assert.equal(payload.target_summaries[0].write_eligibility_status, 'eligible_insert');
});

test('all 50 eligible -> write_plan_status ready_for_final_authorization', () => {
    const payload = buildPayload();
    assert.equal(payload.write_plan_status, 'ready_for_final_authorization');
    assert.equal(payload.required_next_step, 'single_league_small_batch_controlled_pageprops_v2_write_execution');
});

test('partial existing v2 -> would_skip_count > 0', () => {
    const target = manifest().candidate_targets[0];
    const payload = buildPayload({
        existingRows: [
            {
                match_id: target.match_id,
                external_id: target.external_id,
                data_version: 'fotmob_pageprops_v2',
                data_hash: 'b'.repeat(64),
            },
        ],
    });
    assert.equal(payload.would_skip_count, 1);
    assert.equal(payload.write_plan_status, 'review_existing_v2_before_final_authorization');
});

test('blocked target -> write_plan_status blocked', () => {
    const sourceManifest = manifest();
    sourceManifest.candidate_targets[0] = candidate(0, { write_status: 'started' });
    const payload = buildPayload({ manifest: sourceManifest });
    assert.equal(payload.write_plan_status, 'blocked');
    assert.equal(payload.blocked_count, 1);
});

test('expected_raw_match_data_after calculated correctly', () => {
    const payload = buildPayload();
    assert.equal(payload.current_raw_match_data_count, 18);
    assert.equal(payload.expected_raw_match_data_after, 68);
});

test('manifest update sets write_authorization_status pending_final_db_write_confirmation', () => {
    const payload = buildPayload();
    const updated = mod.updateManifestWithWritePlan(manifest(), payload, '2026-05-18T00:00:00.000Z');
    assert.equal(updated.write_authorization_status, 'pending_final_db_write_confirmation');
    assert.equal(updated.candidate_targets[0].write_authorization_status, 'pending_final_db_write_confirmation');
});

test('manifest update sets required_next_step write execution', () => {
    const payload = buildPayload();
    const updated = mod.updateManifestWithWritePlan(manifest(), payload, '2026-05-18T00:00:00.000Z');
    assert.equal(updated.required_next_step, 'single_league_small_batch_controlled_pageprops_v2_write_execution');
    assert.equal(updated.single_league_pageprops_v2_write_planning_result.expected_raw_match_data_after, 68);
});

test('schema readiness requires UNIQUE(match_id,data_version) and old UNIQUE(match_id) absent', () => {
    const ready = mod.buildSchemaReadiness(constraintRows());
    assert.equal(ready.ready, true);
    assert.equal(ready.raw_match_data_unique_match_id_data_version_present, true);
    assert.equal(ready.raw_match_data_old_unique_match_id_absent, true);

    const blocked = mod.buildSchemaReadiness([
        { conname: 'raw_match_data_match_id_key', definition: 'UNIQUE (match_id)' },
    ]);
    assert.equal(blocked.ready, false);
});

test('schema not ready blocks write plan', () => {
    const payload = buildPayload({
        constraintRows: [{ conname: 'raw_match_data_match_id_key', definition: 'UNIQUE (match_id)' }],
    });
    assert.equal(payload.write_plan_status, 'blocked');
    assert.equal(payload.blocked_count, 1);
});

test('buildReport renders planning metrics without raw/pageProps body', () => {
    const report = mod.buildReport(buildPayload());
    assert.match(report, /eligible_insert_count=50/);
    assert.match(report, /expected_raw_match_data_after=68/);
    assert.doesNotMatch(report, /__NEXT_DATA__/);
});

test('queryReadOnly blocks non SELECT SQL and SELECT locks', async () => {
    await assert.rejects(
        () =>
            mod.queryReadOnly({ query: async () => ({ rows: [] }) }, 'UPDATE raw_match_data SET data_hash = $1', ['x']),
        /NON_SELECT|BLOCKED/
    );
    await assert.rejects(
        () => mod.queryReadOnly({ query: async () => ({ rows: [] }) }, 'SELECT * FROM raw_match_data FOR UPDATE'),
        /SQL_WRITE_OR_LOCK_BLOCKED/
    );
});

test('SELECT helper loaders default to empty rows when client omits rows', async () => {
    const client = {
        async query() {
            return {};
        },
    };
    assert.deepEqual(await mod.loadProtectedTableBaselineRows(client), []);
    assert.deepEqual(await mod.loadRawMatchDataConstraints(client), []);
    assert.deepEqual(await mod.loadExistingRawVersions(client, ['53_20252026_4830460']), []);
});

test('runCli valid input writes manifest and report through injected writers', async () => {
    const writes = [];
    const result = await mod.runCli(validArgv(), {
        client: fakeClient(),
        manifest: manifest(),
        writeManifestFile: (filePath, value) => writes.push({ type: 'manifest', filePath, value }),
        writeReportFile: (filePath, value) => writes.push({ type: 'report', filePath, value }),
        output: () => {},
        generatedAt: '2026-05-18T00:00:00.000Z',
    });
    assert.equal(result.status, 0);
    assert.deepEqual(
        writes.map(write => write.type),
        ['manifest', 'report']
    );
});

test('runCli invalid input exits non-zero without DB access', async () => {
    const outputs = [];
    const result = await mod.runCli(validArgv({ 'allow-db-write': 'yes' }), {
        output: payload => outputs.push(payload),
    });
    assert.equal(result.status, 1);
    assert.match(outputs[0].failure_reason, /INPUT_INVALID/);
});

test('runCli invalid manifest exits non-zero without writing files', async () => {
    const writes = [];
    const result = await mod.runCli(validArgv(), {
        client: fakeClient(),
        manifest: manifest({ target_population_status: 'blocked' }),
        writeManifestFile: () => writes.push('manifest'),
        writeReportFile: () => writes.push('report'),
        output: () => {},
    });
    assert.equal(result.status, 1);
    assert.deepEqual(writes, []);
});

test('no DB write through runCli', async () => {
    const client = fakeClient();
    const result = await mod.runCli(validArgv(), {
        client,
        manifest: manifest(),
        writeManifest: false,
        writeReport: false,
        output: () => {},
        generatedAt: '2026-05-18T00:00:00.000Z',
    });
    assert.equal(result.status, 0);
    assert.equal(result.payload.db_write_executed, false);
    assert.equal(result.payload.raw_match_data_write_executed, false);
    assert.equal(client.queries.length, 4);
});

test('no network or match detail fetch', async () => {
    await withPatched(
        globalThis,
        'fetch',
        () => {
            throw new Error('fetch should not be called');
        },
        async () => {
            await withPatched(
                http,
                'request',
                () => {
                    throw new Error('http.request should not be called');
                },
                async () => {
                    await withPatched(
                        https,
                        'request',
                        () => {
                            throw new Error('https.request should not be called');
                        },
                        async () => {
                            const result = await mod.runCli(validArgv(), {
                                client: fakeClient(),
                                manifest: manifest(),
                                writeManifest: false,
                                writeReport: false,
                                output: () => {},
                            });
                            assert.equal(result.status, 0);
                            assert.equal(result.payload.network_access_executed, false);
                            assert.equal(result.payload.match_detail_fetch_executed, false);
                        }
                    );
                }
            );
        }
    );
});

test('no controlled write and no parser/features/training flags in payload', () => {
    const payload = buildPayload();
    assert.equal(payload.controlled_write_executed, false);
    assert.equal(payload.parser_implementation_executed, false);
    assert.equal(payload.feature_extraction_executed, false);
    assert.equal(payload.training_executed, false);
    assert.equal(payload.prediction_executed, false);
});

test('no child process execution', async () => {
    await withPatched(
        childProcess,
        'spawn',
        () => {
            throw new Error('spawn should not be called');
        },
        async () => {
            await withPatched(
                childProcess,
                'exec',
                () => {
                    throw new Error('exec should not be called');
                },
                async () => {
                    await withPatched(
                        childProcess,
                        'execFile',
                        () => {
                            throw new Error('execFile should not be called');
                        },
                        async () => {
                            const result = await mod.runCli(validArgv(), {
                                client: fakeClient(),
                                manifest: manifest(),
                                writeManifest: false,
                                writeReport: false,
                                output: () => {},
                            });
                            assert.equal(result.status, 0);
                        }
                    );
                }
            );
        }
    );
});

test('no ProductionHarvester/raw ingest import', () => {
    const source = fs.readFileSync(MODULE_PATH, 'utf8');
    assert.doesNotMatch(source, /ProductionHarvester|raw_match_data_local_ingest|backfill_historical_raw_match_data/);
});

test('no odds_harvest_pipeline import', () => {
    const source = fs.readFileSync(MODULE_PATH, 'utf8');
    assert.doesNotMatch(source, /odds_harvest_pipeline|total_war_pipeline|titan_discovery/);
});

test('no forbidden runtime imports while loading module', () => {
    const originalLoad = Module._load;
    Module._load = function guardedLoad(request, parent, isMain) {
        if (/ProductionHarvester|odds_harvest_pipeline|playwright|puppeteer|BrowserProvider/i.test(request)) {
            throw new Error(`forbidden import ${request}`);
        }
        return originalLoad.call(this, request, parent, isMain);
    };
    try {
        loadFreshModule();
        assert.ok(true);
    } finally {
        Module._load = originalLoad;
    }
});

test('module source does not call file deletion APIs', () => {
    const source = fs.readFileSync(MODULE_PATH, 'utf8');
    assert.doesNotMatch(source, /unlink|rmSync|rmdir|rm\s+-rf|git reset|git clean/);
});
