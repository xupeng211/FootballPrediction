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
const MODULE_PATH = path.join(PROJECT_ROOT, 'scripts/ops/single_league_pageprops_v2_controlled_write_execute.js');
const PREVIEW_PATH = path.join(PROJECT_ROOT, 'scripts/ops/pageprops_v2_no_write_preview.js');

function loadFreshModule() {
    delete require.cache[require.resolve(MODULE_PATH)];
    return require(MODULE_PATH);
}

const mod = loadFreshModule();
const preview = require(PREVIEW_PATH);

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
        finalDbWriteConfirmation: true,
        networkAuthorization: true,
        matchDetailRecaptureAuthorization: true,
        allowDbWrite: true,
        allowRawMatchDataWrite: true,
        allowControlledWrite: true,
        allowMatchesWrite: false,
        allowBookmakerOddsWrite: false,
        allowFeatureWrite: false,
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
        printFullPageprops: false,
        saveFullPageprops: false,
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
        'final-db-write-confirmation': 'yes',
        'network-authorization': 'yes',
        'match-detail-recapture-authorization': 'yes',
        'allow-db-write': 'yes',
        'allow-raw-match-data-write': 'yes',
        'allow-controlled-write': 'yes',
        'allow-matches-write': 'no',
        'allow-bookmaker-odds-write': 'no',
        'allow-feature-write': 'no',
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
        'print-full-pageprops': 'no',
        'save-full-pageprops': 'no',
        ...overrides,
    };
    return Object.entries(base).flatMap(([key, value]) => [`--${key}`, value]);
}

function matchTimeForExternalId(externalId) {
    const index = Number(externalId) - 4830460;
    const day = String((index % 20) + 1).padStart(2, '0');
    return `2025-08-${day}T18:45:00.000Z`;
}

function fakePageProps(externalId, overrides = {}) {
    return {
        content: {
            matchFacts: { infoBox: { Tournament: 'Ligue 1' } },
            lineup: { home: [], away: [] },
            liveticker: { events: [] },
            playerStats: { players: [] },
            shotmap: { shots: [] },
            stats: { Periods: { All: { stats: [{ key: 'Expected goals', stats: [1.1, 0.9] }] } } },
            h2h: { matches: [] },
            table: { all: [] },
        },
        general: { matchId: externalId, leagueId: 53, matchTimeUTC: matchTimeForExternalId(externalId) },
        header: { teams: [{ name: `Home ${externalId}` }, { name: `Away ${externalId}` }] },
        seo: { eventJSONLD: { '@type': 'SportsEvent' } },
        translations: { ok: true },
        fallback: false,
        nav: { locale: 'en' },
        ongoing: false,
        ssr: true,
        ...overrides,
    };
}

function fakeHtml(externalId, pageProps = fakePageProps(externalId)) {
    return `<html><body><script id="__NEXT_DATA__" type="application/json">${JSON.stringify({
        props: { pageProps },
    })}</script></body></html>`;
}

function fetchResultFor(externalId, overrides = {}) {
    const body = overrides.body ?? fakeHtml(externalId, overrides.pageProps || fakePageProps(externalId));
    const status = overrides.http_status ?? overrides.status ?? 200;
    return {
        ok: overrides.ok ?? (status >= 200 && status < 300),
        request_url: `https://www.fotmob.com/match/${externalId}`,
        final_url: `https://www.fotmob.com/match/${externalId}`,
        http_status: status,
        content_type: overrides.content_type || 'text/html; charset=utf-8',
        body_byte_length: Buffer.byteLength(body, 'utf8'),
        body_sha256: `body-sha-${externalId}`,
        body,
        error: overrides.error,
    };
}

function baselineHash(externalId, overrides = {}) {
    return preview.computeStablePagePropsHash(fakePageProps(externalId, overrides));
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
        existing_versions: [],
        preflight_status: 'hash_baseline_ready',
        baseline_hash: baselineHash(externalId),
        last_preflight_at: '2026-05-17T10:42:45.212Z',
        write_status: 'not_started',
        write_plan_status: 'eligible_for_insert',
        write_attempt_count: 0,
        failure_reason: null,
        created_at: '2026-05-17T09:30:55.640Z',
        updated_at: '2026-05-17T10:42:45.212Z',
        required_next_step: 'single_league_small_batch_controlled_pageprops_v2_write_execution',
        ...overrides,
    };
}

function candidates(overridesByIndex = {}) {
    return Array.from({ length: 50 }, (_, index) => candidate(index, overridesByIndex[index] || {}));
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
        write_authorization_status: 'pending_final_db_write_confirmation',
        write_plan_status: 'ready_for_final_authorization',
        known_completed_targets: knownCompleted(),
        candidate_targets: candidates(),
        required_next_step: 'single_league_small_batch_controlled_pageprops_v2_write_execution',
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
        { conname: 'collected_at_not_null', contype: 'c', definition: 'CHECK ((collected_at IS NOT NULL))' },
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
        { conname: 'raw_data_has_match_id', contype: 'c', definition: "CHECK ((raw_data ? 'matchId'))" },
        { conname: 'raw_data_not_empty', contype: 'c', definition: 'CHECK ((raw_data IS NOT NULL))' },
        ...overrides,
    ];
}

function matchRows(targets = candidates()) {
    return targets.map(target => ({
        match_id: target.match_id,
        external_id: target.external_id,
        home_team: target.home_team,
        away_team: target.away_team,
        match_date: target.match_date,
        status: target.status,
    }));
}

function fetchResults(targets = candidates(), overridesByExternalId = {}) {
    const out = {};
    for (const target of targets) {
        out[target.external_id] = fetchResultFor(target.external_id, overridesByExternalId[target.external_id] || {});
    }
    return out;
}

function postWriteRows(targets = candidates()) {
    return targets.map((target, index) => ({
        id: index + 1000,
        match_id: target.match_id,
        external_id: target.external_id,
        data_version: 'fotmob_pageprops_v2',
        data_hash: target.baseline_hash,
        collected_at: '2026-05-18T00:00:00.000Z',
        has_meta: true,
        has_match_id: true,
        has_pageprops: true,
        meta_hash_strategy: 'stable_pageprops_payload_v1',
    }));
}

function fakeClient({ insertCount = 50 } = {}) {
    const queries = [];
    return {
        queries,
        async query(sql, params) {
            queries.push({ sql, params });
            const normalized = String(sql).trim().replace(/\s+/g, ' ').toUpperCase();
            if (normalized === 'BEGIN' || normalized === 'COMMIT' || normalized === 'ROLLBACK') {
                return { rows: [] };
            }
            if (normalized.startsWith('INSERT INTO RAW_MATCH_DATA')) {
                return {
                    rows: Array.from({ length: insertCount }, (_, index) => ({
                        id: index + 1,
                        match_id: params[index * 6],
                        external_id: params[index * 6 + 1],
                        data_version: params[index * 6 + 4],
                        data_hash: params[index * 6 + 5],
                        collected_at: params[index * 6 + 3],
                    })),
                };
            }
            assert.match(normalized, /^SELECT /);
            assert.doesNotMatch(normalized, /\b(UPDATE|DELETE|TRUNCATE|ALTER|DROP|CREATE|LOCK|COPY)\b/);
            return { rows: [] };
        },
    };
}

function assertInvalid(overrides, pattern) {
    const result = mod.validateExecutionInput(validInput(overrides));
    assert.equal(result.ok, false);
    assert.match(result.errors.join('\n'), pattern);
}

test('valid input succeeds', () => {
    assert.equal(mod.validateExecutionInput(validInput()).ok, true);
});

for (const [name, override, pattern] of [
    [
        'final-db-write-confirmation missing blocked',
        { finalDbWriteConfirmation: undefined },
        /missing final-db-write-confirmation=yes/,
    ],
    ['allow-db-write not yes blocked', { allowDbWrite: false }, /allow-db-write=yes is required/],
    ['allow-raw-match-data-write not yes blocked', { allowRawMatchDataWrite: false }, /allow-raw-match-data-write=yes/],
    ['allow-controlled-write not yes blocked', { allowControlledWrite: false }, /allow-controlled-write=yes/],
    ['allow-matches-write=yes blocked', { allowMatchesWrite: true }, /allow-matches-write=yes is blocked/],
    ['allow-bookmaker-odds-write=yes blocked', { allowBookmakerOddsWrite: true }, /allow-bookmaker-odds-write=yes/],
    ['allow-feature-write=yes blocked', { allowFeatureWrite: true }, /allow-feature-write=yes/],
    ['allow-schema-migration=yes blocked', { allowSchemaMigration: true }, /allow-schema-migration=yes/],
    ['allow-parser-implementation=yes blocked', { allowParserImplementation: true }, /allow-parser-implementation=yes/],
    ['allow-feature-extraction=yes blocked', { allowFeatureExtraction: true }, /allow-feature-extraction=yes/],
    ['allow-training=yes blocked', { allowTraining: true }, /allow-training=yes/],
    ['allow-prediction=yes blocked', { allowPrediction: true }, /allow-prediction=yes/],
    ['allow-browser-runtime=yes blocked', { allowBrowserRuntime: true }, /allow-browser-runtime=yes/],
    ['allow-proxy-runtime=yes blocked', { allowProxyRuntime: true }, /allow-proxy-runtime=yes/],
    ['concurrency > 1 blocked', { concurrency: 2 }, /concurrency must be 1/],
    ['retry > 0 blocked', { retry: 1 }, /retry must be 0/],
    ['print-full-body=yes blocked', { printFullBody: true }, /print-full-body=yes/],
    ['save-full-body=yes blocked', { saveFullBody: true }, /save-full-body=yes/],
    ['print-full-json=yes blocked', { printFullJson: true }, /print-full-json=yes/],
    ['save-full-json=yes blocked', { saveFullJson: true }, /save-full-json=yes/],
    ['print-full-pageprops=yes blocked', { printFullPageprops: true }, /print-full-pageprops=yes/],
    ['save-full-pageprops=yes blocked', { saveFullPageprops: true }, /save-full-pageprops=yes/],
    ['allow-odds-write=yes blocked', { allowOddsWrite: true }, /allow-odds-write=yes/],
]) {
    test(name, () => assertInvalid(override, pattern));
}

test('parseArgs maps Makefile-style flags', () => {
    const parsed = mod.parseArgs(validArgv());
    assert.equal(parsed.finalDbWriteConfirmation, true);
    assert.equal(parsed.allowMatchesWrite, false);
    assert.equal(parsed.concurrency, '1');
});

test('parseArgs records unknown and positional arguments', () => {
    const parsed = mod.parseArgs(['loose', '--not-real=yes']);
    assert.deepEqual(parsed.unknown, ['loose', 'not-real']);
});

test('manifest candidate_targets not 50 blocked', () => {
    const result = mod.validateManifestGate(manifest({ candidate_targets: candidates().slice(0, 49) }));
    assert.equal(result.ok, false);
    assert.match(result.errors.join('\n'), /candidate_targets must contain 50/);
});

test('write_plan_status not ready blocked', () => {
    const result = mod.validateManifestGate(
        manifest({ target_population_status: 'not_ready', write_plan_status: 'not_ready' })
    );
    assert.equal(result.ok, false);
    assert.match(result.errors.join('\n'), /not ready/);
});

for (const [name, override, pattern] of [
    ['baseline_hash missing blocked', { baseline_hash: '' }, /baseline_hash must be 64 hex/],
    ['baseline_hash invalid blocked', { baseline_hash: 'bad' }, /baseline_hash must be 64 hex/],
    ['preflight_status not hash_baseline_ready blocked', { preflight_status: 'failed' }, /preflight_status/],
    ['invalid external_id blocked', { external_id: 'abc', match_id: '53_20252026_abc' }, /external_id must be numeric/],
    ['wrong match_id convention blocked', { match_id: 'wrong' }, /match_id must be/],
    ['failure_reason present blocked', { failure_reason: 'bad' }, /failure_reason must be empty/],
]) {
    test(name, () => {
        const result = mod.validateManifestGate(manifest({ candidate_targets: candidates({ 0: override }) }));
        assert.equal(result.ok, false);
        assert.match(result.errors.join('\n'), pattern);
    });
}

test('duplicate external_id blocked', () => {
    const result = mod.validateManifestGate(
        manifest({ candidate_targets: candidates({ 1: { external_id: '4830460', match_id: '53_20252026_4830460' } }) })
    );
    assert.equal(result.ok, false);
    assert.match(result.errors.join('\n'), /duplicate external_id/);
});

test('duplicate match_id blocked', () => {
    const result = mod.validateManifestGate(
        manifest({ candidate_targets: candidates({ 1: { match_id: '53_20252026_4830460' } }) })
    );
    assert.equal(result.ok, false);
    assert.match(result.errors.join('\n'), /duplicate match_id/);
});

test('schema missing UNIQUE(match_id,data_version) blocked', () => {
    const readiness = mod.buildSchemaReadiness(
        constraintRows().filter(row => row.conname !== 'raw_match_data_match_id_data_version_key')
    );
    assert.equal(readiness.ok, false);
    assert.match(readiness.errors.join('\n'), /missing/);
});

test('old UNIQUE(match_id) present blocked', () => {
    const readiness = mod.buildSchemaReadiness([
        ...constraintRows(),
        { conname: 'raw_match_data_match_id_key', contype: 'u', definition: 'UNIQUE (match_id)' },
    ]);
    assert.equal(readiness.ok, false);
    assert.match(readiness.errors.join('\n'), /legacy/);
});

test('DB baseline mismatch blocks before network and write', async () => {
    let fetchCalled = false;
    const result = await mod.runCli(validInput(), {
        client: fakeClient(),
        manifest: manifest(),
        protectedTableRowsBefore: protectedRows({ raw_match_data: 19 }),
        constraintRows: constraintRows(),
        matchRows: matchRows(),
        existingV2Rows: [],
        fetchHtmlFn: async () => {
            fetchCalled = true;
            return fetchResultFor('4830460');
        },
        writeManifestFile: () => {},
        writeReportFile: () => {},
        output: () => {},
    });
    assert.equal(result.status, 1);
    assert.match(result.payload.blocked_reason, /DB_BASELINE_BLOCKED/);
    assert.equal(result.payload.network_executed, false);
    assert.equal(result.payload.raw_match_data_write_executed, false);
    assert.equal(fetchCalled, false);
});

test('schema gate failure blocks through runCli before network and write', async () => {
    let fetchCalled = false;
    const result = await mod.runCli(validInput(), {
        client: fakeClient(),
        manifest: manifest(),
        protectedTableRowsBefore: protectedRows(),
        constraintRows: constraintRows().filter(row => row.conname !== 'raw_match_data_match_id_data_version_key'),
        matchRows: matchRows(),
        existingV2Rows: [],
        fetchHtmlFn: async () => {
            fetchCalled = true;
            return fetchResultFor('4830460');
        },
        writeManifestFile: () => {},
        writeReportFile: () => {},
        output: () => {},
    });
    assert.equal(result.status, 1);
    assert.match(result.payload.blocked_reason, /SCHEMA_GATE_BLOCKED/);
    assert.equal(result.payload.network_executed, false);
    assert.equal(result.payload.raw_match_data_write_executed, false);
    assert.equal(fetchCalled, false);
});

test('missing matches FK prerequisite blocks before network', async () => {
    let fetchCalled = false;
    const writes = [];
    const result = await mod.runCli(validInput(), {
        client: fakeClient(),
        manifest: manifest(),
        protectedTableRowsBefore: protectedRows(),
        constraintRows: constraintRows(),
        matchRows: [],
        existingV2Rows: [],
        fetchHtmlFn: async () => {
            fetchCalled = true;
            throw new Error('network should not run');
        },
        writeManifestFile: (_file, value) => writes.push(value),
        writeReportFile: () => {},
        output: () => {},
        generatedAt: '2026-05-18T00:00:00.000Z',
    });
    assert.equal(result.status, 1);
    assert.equal(result.payload.blocked_reason, 'blocked_missing_matches_fk_prerequisite');
    assert.equal(result.payload.network_executed, false);
    assert.equal(result.payload.raw_match_data_write_executed, false);
    assert.equal(fetchCalled, false);
    assert.equal(writes[0].write_execution_status, 'blocked_missing_matches_fk_prerequisite');
});

test('existing v2 rows block before network', async () => {
    const targets = candidates();
    let fetchCalled = false;
    const result = await mod.runCli(validInput(), {
        client: fakeClient(),
        manifest: manifest({ candidate_targets: targets }),
        protectedTableRowsBefore: protectedRows(),
        constraintRows: constraintRows(),
        matchRows: matchRows(targets),
        existingV2Rows: [
            {
                id: 1,
                match_id: targets[0].match_id,
                external_id: targets[0].external_id,
                data_version: 'fotmob_pageprops_v2',
            },
        ],
        fetchHtmlFn: async () => {
            fetchCalled = true;
            return fetchResultFor(targets[0].external_id);
        },
        writeManifestFile: () => {},
        writeReportFile: () => {},
        output: () => {},
    });
    assert.equal(result.status, 1);
    assert.equal(result.payload.blocked_reason, 'blocked_existing_fotmob_pageprops_v2_rows');
    assert.equal(fetchCalled, false);
});

for (const [name, fetchOverride, pattern] of [
    [
        'recapture non-200 blocks before transaction',
        { ok: false, status: 500, body: '<html>down</html>', error: 'HTTP_500' },
        /recapture_hash_gate_blocked/,
    ],
    [
        'missing pageProps blocks before transaction',
        { body: '<html><script id="__NEXT_DATA__" type="application/json">{}</script></html>' },
        /recapture_hash_gate_blocked/,
    ],
    [
        'hash drift blocks before transaction',
        { pageProps: fakePageProps('4830460', { drift: true }) },
        /recapture_hash_gate_blocked/,
    ],
    [
        'captcha/block marker blocks before transaction',
        { body: '<html>Cloudflare captcha verify you are human</html>' },
        /recapture_hash_gate_blocked/,
    ],
]) {
    test(name, async () => {
        const targets = candidates();
        const byExternalId = fetchResults(targets);
        byExternalId[targets[0].external_id] = fetchResultFor(targets[0].external_id, fetchOverride);
        const client = fakeClient();
        const result = await mod.runCli(validInput(), {
            client,
            manifest: manifest({ candidate_targets: targets }),
            protectedTableRowsBefore: protectedRows(),
            constraintRows: constraintRows(),
            matchRows: matchRows(targets),
            existingV2Rows: [],
            fetchResultsByExternalId: byExternalId,
            writeManifestFile: () => {},
            writeReportFile: () => {},
            output: () => {},
        });
        assert.equal(result.status, 1);
        assert.match(result.payload.blocked_reason, pattern);
        assert.equal(
            client.queries.some(query => /BEGIN/i.test(query.sql)),
            false
        );
    });
}

test('single-league controlled write blocks reverse fixture before transaction', async () => {
    const requestedExternalId = '4830460';
    const observedPageProps = fakePageProps(requestedExternalId, {
        general: {
            ...fakePageProps(requestedExternalId).general,
            matchId: '4830759',
            homeTeam: { name: 'Away 0' },
            awayTeam: { name: 'Home 0' },
            matchTimeUTC: '2026-05-17T19:00:00.000Z',
            status: 'finished',
            pageUrl: '/matches/away-0-vs-home-0/reused#4830759',
        },
        header: { teams: [{ name: 'Away 0' }, { name: 'Home 0' }] },
    });
    const targets = candidates({
        0: {
            external_id: requestedExternalId,
            match_id: `53_20252026_${requestedExternalId}`,
            home_team: 'Home 0',
            away_team: 'Away 0',
            match_date: '2025-08-01T18:45:00.000Z',
            baseline_hash: preview.computeStablePagePropsHash(observedPageProps),
            page_url_base: '/matches/away-0-vs-home-0/reused',
        },
    });
    const byExternalId = fetchResults(targets, {
        [requestedExternalId]: { pageProps: observedPageProps },
    });
    const client = fakeClient();
    const result = await mod.runCli(validInput(), {
        client,
        acceptedIdentityMappingPresent: true,
        manifest: manifest({ candidate_targets: targets }),
        protectedTableRowsBefore: protectedRows(),
        constraintRows: constraintRows(),
        matchRows: matchRows(targets),
        existingV2Rows: [],
        fetchResultsByExternalId: byExternalId,
        writeManifestFile: () => {},
        writeReportFile: () => {},
        output: () => {},
    });

    assert.equal(result.status, 1);
    assert.equal(result.payload.blocked_reason, 'recapture_hash_gate_blocked');
    assert.equal(result.payload.recapture_hash_gate.reverse_fixture_detected_count, 1);
    assert.equal(result.payload.recapture_hash_gate.targets[0].date_compatibility_status, 'reverse_fixture_detected');
    assert.equal(result.payload.raw_match_data_write_executed, false);
    assert.equal(result.payload.transaction.began, false);
    assert.equal(
        client.queries.some(query => /^BEGIN$/i.test(query.sql)),
        false
    );
});

test('all hashes match begins transaction and inserts exactly 50 rows', async () => {
    const targets = candidates();
    const client = fakeClient();
    const result = await mod.runCli(validInput(), {
        client,
        manifest: manifest({ candidate_targets: targets }),
        protectedTableRowsBefore: protectedRows(),
        protectedTableRowsInsideTransaction: protectedRows({ raw_match_data: 68 }),
        protectedTableRowsAfter: protectedRows({ raw_match_data: 68 }),
        constraintRows: constraintRows(),
        matchRows: matchRows(targets),
        existingV2Rows: [],
        fetchResultsByExternalId: fetchResults(targets),
        postWriteRows: postWriteRows(targets),
        duplicateRows: [],
        writeManifestFile: () => {},
        writeReportFile: () => {},
        output: () => {},
        generatedAt: '2026-05-18T00:00:00.000Z',
    });
    assert.equal(result.status, 0);
    assert.equal(result.payload.inserted_count, 50);
    assert.equal(result.payload.transaction.began, true);
    assert.equal(result.payload.transaction.committed, true);
    assert.equal(result.payload.raw_match_data_write_executed, true);
    assert.equal(
        client.queries.some(query => /^BEGIN$/i.test(query.sql)),
        true
    );
    assert.equal(
        client.queries.some(query => /^COMMIT$/i.test(query.sql)),
        true
    );
});

test('inserted_count mismatch rolls back', async () => {
    const targets = candidates();
    const client = fakeClient({ insertCount: 49 });
    const result = await mod.runCli(validInput(), {
        client,
        manifest: manifest({ candidate_targets: targets }),
        protectedTableRowsBefore: protectedRows(),
        protectedTableRowsInsideTransaction: protectedRows({ raw_match_data: 67 }),
        constraintRows: constraintRows(),
        matchRows: matchRows(targets),
        existingV2Rows: [],
        fetchResultsByExternalId: fetchResults(targets),
        writeManifestFile: () => {},
        writeReportFile: () => {},
        output: () => {},
    });
    assert.equal(result.status, 1);
    assert.match(result.payload.blocked_reason, /INSERTED_COUNT_MISMATCH/);
    assert.equal(result.payload.transaction.rolled_back, true);
});

test('unexpected protected table count change rolls back', async () => {
    const targets = candidates();
    const client = fakeClient();
    const result = await mod.runCli(validInput(), {
        client,
        manifest: manifest({ candidate_targets: targets }),
        protectedTableRowsBefore: protectedRows(),
        protectedTableRowsInsideTransaction: protectedRows({ matches: 11, raw_match_data: 68 }),
        constraintRows: constraintRows(),
        matchRows: matchRows(targets),
        existingV2Rows: [],
        fetchResultsByExternalId: fetchResults(targets),
        writeManifestFile: () => {},
        writeReportFile: () => {},
        output: () => {},
    });
    assert.equal(result.status, 1);
    assert.match(result.payload.blocked_reason, /PROTECTED_TABLE_COUNT_CHANGED/);
    assert.equal(result.payload.transaction.rolled_back, true);
});

test('transaction insert error rolls back and reports controlled failure', async () => {
    const targets = candidates();
    const client = {
        queries: [],
        async query(sql) {
            this.queries.push({ sql });
            const normalized = String(sql).trim().replace(/\s+/g, ' ').toUpperCase();
            if (normalized === 'BEGIN' || normalized === 'ROLLBACK') {
                return { rows: [] };
            }
            if (normalized.startsWith('INSERT INTO RAW_MATCH_DATA')) {
                throw new Error('INSERT_FAILED_FOR_TEST');
            }
            assert.match(normalized, /^SELECT /);
            return { rows: [] };
        },
    };
    const result = await mod.runCli(validInput(), {
        client,
        manifest: manifest({ candidate_targets: targets }),
        protectedTableRowsBefore: protectedRows(),
        constraintRows: constraintRows(),
        matchRows: matchRows(targets),
        existingV2Rows: [],
        fetchResultsByExternalId: fetchResults(targets),
        writeManifestFile: () => {},
        writeReportFile: () => {},
        output: () => {},
    });
    assert.equal(result.status, 1);
    assert.match(result.payload.blocked_reason, /INSERT_FAILED_FOR_TEST/);
    assert.equal(result.payload.transaction.began, true);
    assert.equal(result.payload.transaction.rolled_back, true);
    assert.equal(
        client.queries.some(query => /^ROLLBACK$/i.test(query.sql)),
        true
    );
});

test('post-write raw_count 18->68 and protected tables unchanged verified', () => {
    const targets = candidates();
    const verification = mod.buildPostWriteVerification({
        candidates: targets,
        rowCountsBefore: {
            matches: 10,
            raw_match_data: 18,
            bookmaker_odds_history: 2,
            l3_features: 2,
            match_features_training: 2,
            predictions: 2,
        },
        rowCountsAfter: {
            matches: 10,
            raw_match_data: 68,
            bookmaker_odds_history: 2,
            l3_features: 2,
            match_features_training: 2,
            predictions: 2,
        },
        postWriteRows: postWriteRows(targets),
        duplicateRows: [],
    });
    assert.equal(verification.ok, true);
    assert.equal(verification.raw_match_data_before, 18);
    assert.equal(verification.raw_match_data_after, 68);
    assert.equal(verification.protected_tables_unchanged, true);
});

test('duplicate (match_id,data_version) check verified', () => {
    const targets = candidates();
    const verification = mod.buildPostWriteVerification({
        candidates: targets,
        rowCountsBefore: protectedRows(),
        rowCountsAfter: {
            matches: 10,
            raw_match_data: 68,
            bookmaker_odds_history: 2,
            l3_features: 2,
            match_features_training: 2,
            predictions: 2,
        },
        postWriteRows: postWriteRows(targets),
        duplicateRows: [{ match_id: targets[0].match_id, data_version: 'fotmob_pageprops_v2', duplicate_count: 2 }],
    });
    assert.equal(verification.ok, false);
    assert.match(verification.errors.join('\n'), /duplicate/);
});

test('raw_data shape _meta/matchId/pageProps verified and data_hash equals baseline_hash', () => {
    const target = candidate(0);
    const rawData = mod.buildRawDataForTarget({
        target,
        pageProps: fakePageProps(target.external_id),
        fetchResult: fetchResultFor(target.external_id),
        collectedAt: '2026-05-18T00:00:00.000Z',
    });
    assert.deepEqual(mod.validateRawDataShape(rawData), []);
    assert.equal(rawData._meta.data_hash, target.baseline_hash);
    assert.equal(rawData._meta.preflight_baseline_hash, target.baseline_hash);
    assert.equal(rawData._meta.recaptured_hash, target.baseline_hash);
});

test('queryReadOnly and queryControlledWrite block unsafe SQL', async () => {
    const client = { query: async () => ({ rows: [] }) };
    await assert.rejects(
        () => mod.queryReadOnly(client, 'UPDATE matches SET status=$1', ['x']),
        /NON_SELECT|SQL_WRITE/
    );
    await assert.rejects(
        () => mod.queryControlledWrite(client, 'UPDATE matches SET status=$1', ['x']),
        /CONTROLLED_WRITE_SQL_BLOCKED/
    );
});

test('no matches, odds, feature, training, prediction writes are issued', async () => {
    const targets = candidates();
    const client = fakeClient();
    await mod.runCli(validInput(), {
        client,
        manifest: manifest({ candidate_targets: targets }),
        protectedTableRowsBefore: protectedRows(),
        protectedTableRowsInsideTransaction: protectedRows({ raw_match_data: 68 }),
        protectedTableRowsAfter: protectedRows({ raw_match_data: 68 }),
        constraintRows: constraintRows(),
        matchRows: matchRows(targets),
        existingV2Rows: [],
        fetchResultsByExternalId: fetchResults(targets),
        postWriteRows: postWriteRows(targets),
        duplicateRows: [],
        writeManifestFile: () => {},
        writeReportFile: () => {},
        output: () => {},
    });
    const sql = client.queries.map(query => query.sql).join('\n');
    assert.doesNotMatch(sql, /INSERT INTO matches/i);
    assert.doesNotMatch(sql, /bookmaker_odds_history/i);
    assert.doesNotMatch(sql, /l3_features|match_features_training|predictions/i);
});

test('no parser/features/training, browser/proxy, retry, full body/pageProps print/save in payload', async () => {
    const result = await mod.runCli(validInput(), {
        client: fakeClient(),
        manifest: manifest(),
        protectedTableRowsBefore: protectedRows(),
        constraintRows: constraintRows(),
        matchRows: [],
        existingV2Rows: [],
        writeManifestFile: () => {},
        writeReportFile: () => {},
        output: () => {},
    });
    assert.equal(result.payload.parser_features_training_executed, false);
    assert.equal(result.payload.browser_used, false);
    assert.equal(result.payload.proxy_used, false);
    assert.equal(result.payload.retry_count, 0);
    assert.equal(result.payload.no_full_body_json_pageprops_print_save, true);
});

test('buildReport does not include full raw_data/pageProps/source body', () => {
    const rendered = mod.buildReport(
        mod.buildFailurePayloadForTest || {
            ok: false,
            blocked_reason: 'blocked_missing_matches_fk_prerequisite',
            row_counts_before: {
                matches: 10,
                raw_match_data: 18,
                bookmaker_odds_history: 2,
                l3_features: 2,
                match_features_training: 2,
                predictions: 2,
            },
            manifest_gate: {
                candidate_targets: 50,
                hash_baseline_ready_count: 50,
                baseline_hash_valid_count: 50,
                write_plan_status: 'ready_for_final_authorization',
                errors: [],
            },
            schema_gate: { unique_match_id_data_version_present: true, old_unique_match_id_absent: true },
            fk_gate: { existing_matches_count: 0, missing_matches_count: 50 },
            existing_raw_gate: { existing_v2_count: 0, conflicts: [] },
            transaction: {},
        }
    );
    assert.doesNotMatch(rendered, /__NEXT_DATA__/);
    assert.doesNotMatch(rendered, /pageProps":/);
    assert.doesNotMatch(rendered, /rawData/);
});

test('CLI entrypoint invalid input exits non-zero without DB or network', () => {
    const result = childProcess.spawnSync(process.execPath, [MODULE_PATH, '--manifest', mod.MANIFEST_PATH], {
        cwd: PROJECT_ROOT,
        encoding: 'utf8',
    });
    assert.notEqual(result.status, 0);
    assert.match(result.stdout, /INPUT_INVALID/);
    assert.equal(result.stderr, '');
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
    const forbidden = [];
    const originalLoad = Module._load;
    Module._load = function patchedLoad(request, parent, isMain) {
        if (/ProductionHarvester|odds_harvest_pipeline|playwright|puppeteer/.test(request)) {
            forbidden.push(request);
        }
        return originalLoad.apply(this, arguments);
    };
    try {
        loadFreshModule();
    } finally {
        Module._load = originalLoad;
    }
    assert.deepEqual(forbidden, []);
});

test('no low-level network or child process during blocked FK gate', async () => {
    let networkCalled = false;
    const originalHttp = http.request;
    const originalHttps = https.request;
    const originalSpawn = childProcess.spawn;
    http.request = () => {
        networkCalled = true;
        throw new Error('network blocked');
    };
    https.request = () => {
        networkCalled = true;
        throw new Error('network blocked');
    };
    childProcess.spawn = () => {
        throw new Error('spawn blocked');
    };
    try {
        await mod.runCli(validInput(), {
            client: fakeClient(),
            manifest: manifest(),
            protectedTableRowsBefore: protectedRows(),
            constraintRows: constraintRows(),
            matchRows: [],
            existingV2Rows: [],
            writeManifestFile: () => {},
            writeReportFile: () => {},
            output: () => {},
        });
    } finally {
        http.request = originalHttp;
        https.request = originalHttps;
        childProcess.spawn = originalSpawn;
    }
    assert.equal(networkCalled, false);
});

test('module source does not call file deletion APIs', () => {
    const source = fs.readFileSync(MODULE_PATH, 'utf8');
    assert.doesNotMatch(source, /rmSync|unlinkSync|rmdirSync|rm -rf|fs\\.rm|fs\\.unlink/);
});
