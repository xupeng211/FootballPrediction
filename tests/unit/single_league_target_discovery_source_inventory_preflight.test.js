/* eslint-disable max-lines, max-statements */
'use strict';

const assert = require('node:assert/strict');
const childProcess = require('node:child_process');
const Module = require('node:module');
const path = require('node:path');
const test = require('node:test');

const PROJECT_ROOT = path.resolve(__dirname, '../..');
const MODULE_PATH = path.join(PROJECT_ROOT, 'scripts/ops/single_league_target_discovery_source_inventory_preflight.js');

function loadFreshModule() {
    delete require.cache[require.resolve(MODULE_PATH)];
    return require(MODULE_PATH);
}

const mod = loadFreshModule();

function validInput(overrides = {}) {
    return {
        source: 'fotmob',
        leagueId: 53,
        leagueName: 'Ligue 1',
        season: '2025/2026',
        route: 'source_inventory',
        rawVersion: 'fotmob_pageprops_v2',
        hashStrategy: 'stable_pageprops_payload_v1',
        batchId: 'fotmob-pageprops-v2-ligue1-2025-2026-profile-001',
        targetCountMin: 20,
        targetCountMax: 50,
        networkAuthorization: true,
        sourceInventoryAuthorization: true,
        allowDbWrite: false,
        allowRawMatchDataWrite: false,
        allowMatchDetailFetch: false,
        allowSchemaMigration: false,
        allowParserImplementation: false,
        allowFeatureExtraction: false,
        allowTraining: false,
        allowPrediction: false,
        allowBrowserRuntime: false,
        allowProxyRuntime: false,
        concurrency: 1,
        retry: 0,
        printFullBody: false,
        saveFullBody: false,
        printFullJson: false,
        saveFullJson: false,
        executeWrite: false,
        commit: false,
        inventTargets: false,
        fabricateExternalIds: false,
        allowOddsWrite: false,
        ...overrides,
    };
}

function validArgv(overrides = {}) {
    const base = {
        source: 'fotmob',
        'league-id': '53',
        'league-name': 'Ligue 1',
        season: '2025/2026',
        route: 'source_inventory',
        'raw-version': 'fotmob_pageprops_v2',
        'hash-strategy': 'stable_pageprops_payload_v1',
        'batch-id': 'fotmob-pageprops-v2-ligue1-2025-2026-profile-001',
        'target-count-min': '20',
        'target-count-max': '50',
        'network-authorization': 'yes',
        'source-inventory-authorization': 'yes',
        'allow-db-write': 'no',
        'allow-raw-match-data-write': 'no',
        'allow-match-detail-fetch': 'no',
        'allow-schema-migration': 'no',
        'allow-parser-implementation': 'no',
        'allow-feature-extraction': 'no',
        'allow-training': 'no',
        'allow-prediction': 'no',
        'allow-browser-runtime': 'no',
        'allow-proxy-runtime': 'no',
        concurrency: '1',
        retry: '0',
        'print-full-body': 'no',
        'save-full-body': 'no',
        'print-full-json': 'no',
        'save-full-json': 'no',
        ...overrides,
    };
    return Object.entries(base).flatMap(([key, value]) => [`--${key}`, value]);
}

function assertInvalid(overrides, pattern) {
    const validation = mod.validatePreflightInput(validInput(overrides));
    assert.equal(validation.ok, false);
    assert.match(validation.errors.join('\n'), pattern);
}

function completedTarget(externalId, homeTeam = `Completed ${externalId}`, awayTeam = `Away ${externalId}`) {
    const matchId = `53_20252026_${externalId}`;
    return {
        target_id: `fotmob-pageprops-v2-ligue1-2025-2026-profile-001:${matchId}`,
        batch_id: 'fotmob-pageprops-v2-ligue1-2025-2026-profile-001',
        source: 'fotmob',
        route: 'html_hydration',
        raw_data_version: 'fotmob_pageprops_v2',
        hash_strategy: 'stable_pageprops_payload_v1',
        match_id: matchId,
        external_id: String(externalId),
        league_id: 53,
        league_name: 'Ligue 1',
        season: '2025/2026',
        home_team: homeTeam,
        away_team: awayTeam,
        kickoff_time: '2026-05-10T19:00:00.000Z',
        match_date: '2026-05-10T19:00:00.000Z',
        status: 'finished',
        existing_versions: ['fotmob_html_hyd_v1', 'fotmob_pageprops_v2'],
        target_status: 'already_completed',
        exclude_from_new_profile_batch: true,
        reason: 'already_has_fotmob_pageprops_v2',
        odds_alignment_ready: true,
    };
}

const COMPLETED_EXTERNAL_IDS = ['4830746', '4830747', '4830748', '4830750', '4830751', '4830752', '4830753', '4830754'];
const KNOWN_COMPLETED = COMPLETED_EXTERNAL_IDS.map(id => completedTarget(id));

function fakeManifest(overrides = {}) {
    return {
        schema_version: 'target_manifest_proposal_v1',
        batch_id: 'fotmob-pageprops-v2-ligue1-2025-2026-profile-001',
        source: 'fotmob',
        route: 'html_hydration',
        raw_data_version: 'fotmob_pageprops_v2',
        hash_strategy: 'stable_pageprops_payload_v1',
        league: {
            league_id: 53,
            league_name: 'Ligue 1',
            season: '2025/2026',
        },
        batch_type: 'profile_batch',
        batch_size_policy: '20-50',
        target_population_status: 'blocked_pending_authorized_target_discovery',
        known_completed_targets: KNOWN_COMPLETED,
        candidate_targets: [],
        readiness_gates: [],
        required_next_step: 'authorized_target_discovery_or_source_inventory',
        ...overrides,
    };
}

function fakeDbSnapshot(overrides = {}) {
    return {
        row_counts: {
            matches: 10,
            raw_match_data: 18,
            bookmaker_odds_history: 2,
            l3_features: 2,
            match_features_training: 2,
            predictions: 2,
        },
        known_completed_targets: KNOWN_COMPLETED,
        ...overrides,
    };
}

function sourceMatch(index, overrides = {}) {
    const externalId = String(6000000 + index);
    return {
        id: externalId,
        home: { name: `Home ${index}` },
        away: { name: `Away ${index}` },
        status: {
            utcTime: `2026-03-${String((index % 27) + 1).padStart(2, '0')}T19:00:00.000Z`,
            finished: true,
        },
        round: `Round ${Math.floor(index / 10) + 1}`,
        pageUrl: `/matches/${externalId}`,
        ...overrides,
    };
}

function sourceInventory(count, startIndex = 1) {
    return {
        matches: {
            allMatches: Array.from({ length: count }, (_, index) => sourceMatch(startIndex + index)),
        },
    };
}

function fakeResponse(body, status = 200, contentType = 'application/json') {
    const bodyText = typeof body === 'string' ? body : JSON.stringify(body);
    return {
        status,
        headers: {
            get(name) {
                return name.toLowerCase() === 'content-type' ? contentType : null;
            },
        },
        async text() {
            return bodyText;
        },
    };
}

function depsFor(body, overrides = {}) {
    const writes = [];
    const requestedUrls = [];
    return {
        deps: {
            dbSnapshot: fakeDbSnapshot(overrides.dbSnapshot || {}),
            manifest: fakeManifest(overrides.manifest || {}),
            nowIso: '2026-05-17T00:00:00.000Z',
            async fetch(url) {
                requestedUrls.push(url);
                return fakeResponse(body, overrides.status || 200, overrides.contentType || 'application/json');
            },
            writeManifest(manifest) {
                writes.push(manifest);
            },
        },
        writes,
        requestedUrls,
    };
}

async function runPreflight(body, overrides = {}) {
    const harness = depsFor(body, overrides);
    const output = await mod.buildPreflightOutput(validInput(), harness.deps);
    return { output, writes: harness.writes, requestedUrls: harness.requestedUrls };
}

async function runExecute(body, overrides = {}) {
    const harness = depsFor(body, overrides);
    const stdout = [];
    const stderr = [];
    const exitCode = await mod.execute(
        validArgv(overrides.argv || {}),
        {
            stdout: { write: chunk => stdout.push(String(chunk)) },
            stderr: { write: chunk => stderr.push(String(chunk)) },
        },
        harness.deps
    );
    const stdoutText = stdout.join('');
    const stderrText = stderr.join('');
    return {
        exitCode,
        stdout: stdoutText,
        stderr: stderrText,
        json: stdoutText ? JSON.parse(stdoutText) : null,
        errorJson: stderrText ? JSON.parse(stderrText) : null,
        writes: harness.writes,
        requestedUrls: harness.requestedUrls,
    };
}

function loadWithBlockedImportPattern(t, pattern) {
    const originalLoad = Module._load;
    Module._load = function patchedLoad(request, parent, isMain) {
        if (pattern.test(request)) {
            throw new Error(`blocked import: ${request}`);
        }
        return originalLoad.call(this, request, parent, isMain);
    };
    t.after(() => {
        Module._load = originalLoad;
    });
    return loadFreshModule();
}

test('valid input succeeds', () => {
    assert.equal(mod.validatePreflightInput(validInput()).ok, true);
});

test('source missing fails', () => assertInvalid({ source: '' }, /missing source=fotmob/));
test('source non-fotmob fails', () => assertInvalid({ source: 'other' }, /source must be fotmob/));
test('league-id missing fails', () => assertInvalid({ leagueId: '' }, /missing league-id=53/));
test('league-id not 53 fails', () => assertInvalid({ leagueId: 57 }, /league-id must be 53/));
test('league-name missing fails', () => assertInvalid({ leagueName: '' }, /missing league-name=Ligue 1/));
test('league-name not Ligue 1 fails', () => assertInvalid({ leagueName: 'Serie A' }, /league-name must be Ligue 1/));
test('season missing fails', () => assertInvalid({ season: '' }, /missing season=2025\/2026/));
test('season not 2025/2026 fails', () => assertInvalid({ season: '2024/2025' }, /season must be 2025\/2026/));
test('route missing fails', () => assertInvalid({ route: '' }, /missing route=source_inventory/));
test('route not source_inventory fails', () =>
    assertInvalid({ route: 'html_hydration' }, /route must be source_inventory/));
test('raw-version missing fails', () => assertInvalid({ rawVersion: '' }, /missing raw-version=fotmob_pageprops_v2/));
test('raw-version not fotmob_pageprops_v2 fails', () =>
    assertInvalid({ rawVersion: 'fotmob_html_hyd_v1' }, /raw-version must be fotmob_pageprops_v2/));
test('hash-strategy missing fails', () =>
    assertInvalid({ hashStrategy: '' }, /missing hash-strategy=stable_pageprops_payload_v1/));
test('hash-strategy not stable_pageprops_payload_v1 fails', () =>
    assertInvalid({ hashStrategy: 'other' }, /hash-strategy must be stable_pageprops_payload_v1/));
test('batch-id missing fails', () =>
    assertInvalid({ batchId: '' }, /missing batch-id=fotmob-pageprops-v2-ligue1-2025-2026-profile-001/));
test('batch-id wrong fails', () => assertInvalid({ batchId: 'wrong' }, /batch-id must be/));
test('target-count-min not 20 fails', () => assertInvalid({ targetCountMin: 19 }, /target-count-min must be 20/));
test('target-count-max not 50 fails', () => assertInvalid({ targetCountMax: 51 }, /target-count-max must be 50/));
test('network-authorization=no blocked', () =>
    assertInvalid({ networkAuthorization: false }, /network-authorization=yes is required/));
test('source-inventory-authorization=no blocked', () =>
    assertInvalid({ sourceInventoryAuthorization: false }, /source-inventory-authorization=yes is required/));
test('allow-db-write=yes blocked', () => assertInvalid({ allowDbWrite: true }, /allow-db-write=yes is blocked/));
test('allow-raw-match-data-write=yes blocked', () =>
    assertInvalid({ allowRawMatchDataWrite: true }, /allow-raw-match-data-write=yes is blocked/));
test('allow-match-detail-fetch=yes blocked', () =>
    assertInvalid({ allowMatchDetailFetch: true }, /allow-match-detail-fetch=yes is blocked/));
test('allow-schema-migration=yes blocked', () =>
    assertInvalid({ allowSchemaMigration: true }, /allow-schema-migration=yes is blocked/));
test('allow-parser-implementation=yes blocked', () =>
    assertInvalid({ allowParserImplementation: true }, /allow-parser-implementation=yes is blocked/));
test('allow-feature-extraction=yes blocked', () =>
    assertInvalid({ allowFeatureExtraction: true }, /allow-feature-extraction=yes is blocked/));
test('allow-training=yes blocked', () => assertInvalid({ allowTraining: true }, /allow-training=yes is blocked/));
test('allow-prediction=yes blocked', () => assertInvalid({ allowPrediction: true }, /allow-prediction=yes is blocked/));
test('allow-browser-runtime=yes blocked', () =>
    assertInvalid({ allowBrowserRuntime: true }, /allow-browser-runtime=yes is blocked/));
test('allow-proxy-runtime=yes blocked', () =>
    assertInvalid({ allowProxyRuntime: true }, /allow-proxy-runtime=yes is blocked/));
test('concurrency > 1 blocked', () => assertInvalid({ concurrency: 2 }, /concurrency must be 1/));
test('retry > 0 blocked', () => assertInvalid({ retry: 1 }, /retry must be 0/));
test('print-full-body=yes blocked', () => assertInvalid({ printFullBody: true }, /print-full-body=yes is blocked/));
test('save-full-body=yes blocked', () => assertInvalid({ saveFullBody: true }, /save-full-body=yes is blocked/));
test('print-full-json=yes blocked', () => assertInvalid({ printFullJson: true }, /print-full-json=yes is blocked/));
test('save-full-json=yes blocked', () => assertInvalid({ saveFullJson: true }, /save-full-json=yes is blocked/));
test('execute-write=yes blocked', () => assertInvalid({ executeWrite: true }, /execute-write=yes is blocked/));
test('commit=yes blocked', () => assertInvalid({ commit: true }, /commit=yes is blocked/));
test('invent-targets=yes blocked', () => assertInvalid({ inventTargets: true }, /invent-targets=yes is blocked/));
test('fabricate-external-ids=yes blocked', () =>
    assertInvalid({ fabricateExternalIds: true }, /fabricate-external-ids=yes is blocked/));
test('allow-odds-write=yes blocked', () => assertInvalid({ allowOddsWrite: true }, /allow-odds-write=yes is blocked/));

test('fake source inventory extracts candidate external_ids', async () => {
    const { output } = await runPreflight(sourceInventory(20));
    assert.equal(output.candidate_targets.length, 20);
    assert.equal(output.candidate_targets[0].external_id, '6000001');
    assert.equal(output.source_inventory_route.reused_l1_capability, true);
    assert.equal(output.source_inventory_route.l1_capability, 'FotMobSourceInventoryAdapter');
    assert.equal(output.source_inventory_route.l1_route_kind, 'l1_api_data_leagues');
    assert.equal(
        output.source_inventory_route.generated_url,
        'https://www.fotmob.com/api/data/leagues?id=53&season=20252026'
    );
    assert.equal(output.source_inventory_route.status_code, 200);
    assert.ok(!output.source_inventory_route.generated_url.includes('/api/leagues?'));
});

test('source inventory preflight propagates requested-side source URL identity fields', async () => {
    const body = sourceInventory(20);
    body.matches.allMatches[0] = sourceMatch(1, {
        pageUrl: '/matches/home-vs-away/abcd12#6000001',
    });

    const { output, writes } = await runPreflight(body);
    const target = output.candidate_targets[0];
    const writtenTarget = writes[0].candidate_targets[0];

    assert.equal(target.source_page_url, '/matches/home-vs-away/abcd12#6000001');
    assert.equal(target.source_page_url_base, '/matches/home-vs-away/abcd12');
    assert.equal(target.source_url_fragment_external_id, '6000001');
    assert.equal(target.source_slug, 'home-vs-away');
    assert.equal(target.source_route_code, 'abcd12');
    assert.equal(target.schedule_external_id, '6000001');
    assert.equal(target.schedule_date, '2026-03-02T19:00:00.000Z');
    assert.equal(target.schedule_home_team, 'Home 1');
    assert.equal(target.schedule_away_team, 'Away 1');
    assert.equal(target.source_inventory_record_key, 'l1_api_data_leagues:matches.allMatches.0:6000001');
    assert.equal(target.identity_evidence_status, 'complete');
    assert.equal(writtenTarget.source_url_fragment_external_id, '6000001');
});

test('source URL evidence does not imply accepted mapping or raw write readiness', async () => {
    const body = sourceInventory(20);
    body.matches.allMatches[0] = sourceMatch(1, {
        pageUrl: '/matches/home-vs-away/abcd12#6000001',
    });

    const { output } = await runPreflight(body);
    const target = output.candidate_targets[0];

    assert.equal(target.identity_evidence_status, 'complete');
    assert.equal(output.raw_match_data_write_executed, false);
    assert.equal(output.db_write_executed, false);
    assert.equal(Object.hasOwn(target, 'accepted_mapping_count'), false);
    assert.equal(Object.hasOwn(target, 'raw_write_ready_for_execution'), false);
    assert.equal(target.write_status, 'not_started');
});

test('fake source inventory excludes known completed 8', async () => {
    const body = {
        matches: {
            allMatches: [
                ...COMPLETED_EXTERNAL_IDS.map((id, index) => sourceMatch(index + 1, { id })),
                ...sourceInventory(20).matches.allMatches,
            ],
        },
    };
    const { output } = await runPreflight(body);
    assert.equal(output.candidate_discovery_result.excluded_completed_count, 8);
    assert.ok(!output.candidate_targets.some(target => COMPLETED_EXTERNAL_IDS.includes(target.external_id)));
});

test('fake duplicate external_ids deduped by reused L1 parser/adapter', async () => {
    const body = {
        matches: {
            allMatches: [sourceMatch(1), sourceMatch(1), ...sourceInventory(20, 2).matches.allMatches],
        },
    };
    const { output } = await runPreflight(body);
    assert.equal(output.candidate_targets.filter(target => target.external_id === '6000001').length, 1);
    assert.equal(output.candidate_discovery_result.duplicate_removed_count, 0);
});

test('fake candidates <20 sets insufficient_candidates_discovered', async () => {
    const { output } = await runPreflight(sourceInventory(5));
    assert.equal(output.candidate_discovery_result.target_population_status, 'insufficient_candidates_discovered');
});

test('fake candidates 20-50 sets ready_for_no_write_preflight', async () => {
    const { output } = await runPreflight(sourceInventory(20));
    assert.equal(output.candidate_discovery_result.target_population_status, 'ready_for_no_write_preflight');
});

test('fake >50 candidates caps at 50', async () => {
    const { output } = await runPreflight(sourceInventory(60));
    assert.equal(output.candidate_targets.length, 50);
    assert.equal(output.candidate_discovery_result.capped_removed_count, 10);
});

test('numeric external_id validation', async () => {
    const result = mod.buildCandidateTargetsFromSource(
        [{ match: sourceMatch(1, { id: '1234567' }), sourcePath: 'matches' }],
        KNOWN_COMPLETED,
        {
            nowIso: '2026-05-17T00:00:00.000Z',
        }
    );
    assert.equal(result.candidate_targets[0].external_id, '1234567');
});

test('invalid external_id rejected', async () => {
    const result = mod.buildCandidateTargetsFromSource(
        [{ match: sourceMatch(1, { id: 'abc' }), sourcePath: 'matches' }],
        KNOWN_COMPLETED,
        {
            nowIso: '2026-05-17T00:00:00.000Z',
        }
    );
    assert.equal(result.candidate_targets.length, 0);
    assert.equal(result.invalid_identity_count, 1);
});

test('match_id generated only when safe', async () => {
    const result = mod.buildCandidateTargetsFromSource(
        [
            { match: sourceMatch(1, { id: '7000001' }), sourcePath: 'matches' },
            { match: sourceMatch(2, { id: '7000002', away: null }), sourcePath: 'matches' },
        ],
        KNOWN_COMPLETED,
        { nowIso: '2026-05-17T00:00:00.000Z' }
    );
    assert.equal(result.candidate_targets[0].match_id, '53_20252026_7000001');
    assert.equal(result.candidate_targets[1].match_id, null);
});

test('identity incomplete candidate blocked', async () => {
    const result = mod.buildCandidateTargetsFromSource(
        [{ match: sourceMatch(1, { away: null, status: {} }), sourcePath: 'matches' }],
        KNOWN_COMPLETED,
        { nowIso: '2026-05-17T00:00:00.000Z' }
    );
    assert.equal(result.candidate_targets[0].target_status, 'identity_incomplete');
    assert.equal(result.candidate_targets[0].preflight_status, 'blocked');
    assert.equal(result.candidate_targets[0].failure_reason, 'missing_identity_metadata');
});

test('403 response blocks with no retry', async () => {
    let calls = 0;
    const result = await runExecute(sourceInventory(20), {
        status: 403,
        argv: {},
    });
    calls = result.requestedUrls.length;
    assert.equal(result.exitCode, 1);
    assert.match(result.stderr, /403/);
    assert.equal(calls, 1);
});

test('captcha marker blocks', async () => {
    const result = await runExecute('captcha challenge');
    assert.equal(result.exitCode, 1);
    assert.match(result.stderr, /captcha/);
});

test('Cloudflare/block marker blocks', async () => {
    const result = await runExecute('Just a moment Cloudflare');
    assert.equal(result.exitCode, 1);
    assert.match(result.stderr, /cloudflare|just a moment/i);
});

test('invalid JSON / invalid source body controlled failure', async () => {
    const result = await runExecute('{not-json');
    assert.equal(result.exitCode, 1);
    assert.match(result.stderr, /invalid JSON/);
});

test('no full body printed', async () => {
    const body = { marker: 'secret_full_body_marker', matches: { allMatches: sourceInventory(20).matches.allMatches } };
    const result = await runExecute(body);
    assert.equal(result.exitCode, 0);
    assert.ok(!result.stdout.includes('secret_full_body_marker'));
});

test('no full body saved', async () => {
    const body = { marker: 'secret_full_body_marker', matches: { allMatches: sourceInventory(20).matches.allMatches } };
    const result = await runExecute(body);
    assert.equal(result.exitCode, 0);
    assert.ok(!JSON.stringify(result.writes).includes('secret_full_body_marker'));
});

test('no DB write', async () => {
    const { output } = await runPreflight(sourceInventory(20));
    assert.equal(output.db_write_executed, false);
    assert.deepEqual(output.db_baseline, fakeDbSnapshot().row_counts);
});

test('no match detail fetch', async () => {
    const { output, requestedUrls } = await runPreflight(sourceInventory(20));
    assert.equal(output.match_detail_pageprops_fetch_executed, false);
    assert.equal(requestedUrls.length, 1);
    assert.ok(requestedUrls[0].includes('/api/data/leagues'));
    assert.ok(requestedUrls[0].includes('season=20252026'));
    assert.ok(!requestedUrls[0].includes('/matchDetails'));
});

test('no parser/features/training', async () => {
    const { output } = await runPreflight(sourceInventory(20));
    assert.equal(output.parser_implementation_executed, false);
    assert.equal(output.feature_extraction_executed, false);
    assert.equal(output.training_executed, false);
    assert.equal(output.prediction_executed, false);
});

test('manifest update preserves known_completed_targets', async () => {
    const { writes } = await runPreflight(sourceInventory(20));
    assert.equal(writes[0].known_completed_targets.length, 8);
    assert.deepEqual(
        writes[0].known_completed_targets.map(target => target.external_id),
        COMPLETED_EXTERNAL_IDS
    );
});

test('manifest update writes candidate_targets only from source inventory', async () => {
    const { writes } = await runPreflight(sourceInventory(3));
    assert.equal(writes[0].candidate_targets.length, 3);
    assert.equal(
        writes[0].source_inventory_result.generated_url,
        'https://www.fotmob.com/api/data/leagues?id=53&season=20252026'
    );
    assert.equal(writes[0].source_inventory_result.status_code, 200);
    assert.deepEqual(
        writes[0].candidate_targets.map(target => target.external_id),
        ['6000001', '6000002', '6000003']
    );
});

test('no invented targets when source inventory empty', async () => {
    const { output, writes } = await runPreflight({ matches: { allMatches: [] } });
    assert.equal(output.candidate_targets.length, 0);
    assert.equal(writes[0].candidate_targets.length, 0);
    assert.equal(writes[0].target_population_status, 'insufficient_candidates_discovered');
});

test('no child_process spawn', async t => {
    const originalSpawn = childProcess.spawn;
    const originalExec = childProcess.exec;
    const originalExecFile = childProcess.execFile;
    const fail = name => () => {
        throw new Error(`${name} should not be called`);
    };
    childProcess.spawn = fail('spawn');
    childProcess.exec = fail('exec');
    childProcess.execFile = fail('execFile');
    t.after(() => {
        childProcess.spawn = originalSpawn;
        childProcess.exec = originalExec;
        childProcess.execFile = originalExecFile;
    });
    const result = await runExecute(sourceInventory(20));
    assert.equal(result.exitCode, 0);
});

test('no ProductionHarvester/raw ingest import', t => {
    const loaded = loadWithBlockedImportPattern(
        t,
        /ProductionHarvester|raw_match_data_local_ingest|backfill_historical_raw_match_data/i
    );
    assert.equal(loaded.validatePreflightInput(validInput()).ok, true);
});

test('no odds_harvest_pipeline import', t => {
    const loaded = loadWithBlockedImportPattern(t, /odds_harvest_pipeline/i);
    assert.equal(loaded.validatePreflightInput(validInput()).ok, true);
});

test('does not import old unsafe L1 runner, DiscoveryService.discover path, browser, proxy, or odds pipeline', t => {
    const loaded = loadWithBlockedImportPattern(
        t,
        /titan_discovery|DiscoveryService|ProductionHarvester|run_production|odds_harvest_pipeline|BrowserProvider|ProxyProvider|playwright/i
    );
    assert.equal(loaded.validatePreflightInput(validInput()).ok, true);
});
