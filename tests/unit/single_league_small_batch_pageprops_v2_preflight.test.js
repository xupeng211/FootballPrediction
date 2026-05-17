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
const MODULE_PATH = path.join(PROJECT_ROOT, 'scripts/ops/single_league_small_batch_pageprops_v2_preflight.js');

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
        networkAuthorization: true,
        matchDetailPreflightAuthorization: true,
        allowDbWrite: false,
        allowRawMatchDataWrite: false,
        allowControlledWrite: false,
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
        'network-authorization': 'yes',
        'match-detail-preflight-authorization': 'yes',
        'allow-db-write': 'no',
        'allow-raw-match-data-write': 'no',
        'allow-controlled-write': 'no',
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
        target_status: 'source_inventory_discovered',
        priority: index + 1,
        expected_coverage_tier: 'unknown_until_profiled',
        existing_versions: [],
        preflight_status: 'not_started',
        baseline_hash: null,
        last_preflight_at: null,
        write_status: 'not_started',
        write_attempt_count: 0,
        failure_reason: null,
        source_fidelity_notes: 'source_inventory_discovered_no_match_detail_fetch',
        odds_alignment_ready: true,
        created_at: '2026-05-17T00:00:00.000Z',
        updated_at: '2026-05-17T00:00:00.000Z',
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
        target_population_status: 'ready_for_no_write_preflight',
        known_completed_targets: knownCompleted(),
        candidate_targets: Array.from({ length: 50 }, (_, index) => candidate(index)),
        required_next_step: 'single_league_small_batch_no_write_pageprops_v2_preflight',
        ...overrides,
    };
}

function fakePageProps(externalId, overrides = {}) {
    return {
        content: {
            matchFacts: { events: [{ type: 'Goal', secret: 'SECRET_PAGEPROPS_VALUE' }] },
            lineup: { homeTeam: { starters: [{ id: 1, name: 'Home Player' }] } },
            liveticker: { events: [{ minute: 1, text: 'Kickoff' }] },
            playerStats: { 1: { stats: { rating: 7.1 } } },
            shotmap: { shots: [{ id: Number(externalId), expectedGoals: 0.2 }] },
            stats: { Periods: { All: { stats: [{ key: 'Expected goals', stats: [1.2, 0.8] }] } } },
            h2h: { matches: [] },
            table: { all: [] },
            momentum: { main: { data: [1, 2, 3] } },
        },
        general: { matchId: externalId, leagueId: 53 },
        header: { teams: [{ name: `Home ${externalId}` }, { name: `Away ${externalId}` }] },
        seo: {
            eventJSONLD: { '@type': 'SportsEvent' },
            breadcrumbJSONLD: { itemListElement: [{ name: 'Ligue 1' }] },
        },
        translations: { hello: 'world' },
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
    const body = overrides.body ?? fakeHtml(externalId);
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

async function buildPayload(overrides = {}) {
    const calls = overrides.calls || [];
    const sourceManifest = overrides.manifest || manifest();
    const payload = await mod.buildSingleLeagueSmallBatchPagePropsV2Preflight({
        input: validInput(),
        manifest: sourceManifest,
        existingRows: overrides.existingRows || [],
        protectedTableRowsBefore: overrides.protectedTableRowsBefore || protectedRows(),
        protectedTableRowsAfter: overrides.protectedTableRowsAfter || protectedRows(),
        generatedAt: '2026-05-17T10:00:00.000Z',
        dependencies: {
            fetchHtmlFn: async requestUrl => {
                calls.push(requestUrl);
                const externalId = requestUrl.split('/').pop();
                if (overrides.fetchResultsByExternalId?.[externalId]) {
                    return overrides.fetchResultsByExternalId[externalId];
                }
                return fetchResultFor(externalId);
            },
        },
    });
    return { payload, calls };
}

function fakeClient() {
    const queries = [];
    return {
        queries,
        async query(sql, params) {
            queries.push({ sql, params });
            assert.match(sql.trim(), /^SELECT/i);
            assert.doesNotMatch(sql, /\b(INSERT|UPDATE|DELETE|TRUNCATE|ALTER|DROP|CREATE|LOCK|COPY)\b/i);
            if (/UNION ALL/i.test(sql)) return { rows: protectedRows() };
            if (/FROM raw_match_data/i.test(sql)) return { rows: [] };
            return { rows: [] };
        },
    };
}

test('valid input succeeds', () => {
    assert.equal(mod.validatePreflightInput(validInput()).ok, true);
});

for (const [name, override, pattern] of [
    ['manifest path missing fails', { manifest: '' }, /missing manifest=/],
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
    ['network-authorization=no blocked', { networkAuthorization: false }, /network-authorization=yes is required/],
    [
        'match-detail-preflight-authorization=no blocked',
        { matchDetailPreflightAuthorization: false },
        /match-detail-preflight-authorization=yes is required/,
    ],
    ['allow-db-write=yes blocked', { allowDbWrite: true }, /allow-db-write=yes is blocked/],
    ['allow-raw-match-data-write=yes blocked', { allowRawMatchDataWrite: true }, /allow-raw-match-data-write=yes/],
    ['allow-controlled-write=yes blocked', { allowControlledWrite: true }, /allow-controlled-write=yes/],
    ['allow-schema-migration=yes blocked', { allowSchemaMigration: true }, /allow-schema-migration=yes/],
    ['allow-parser-implementation=yes blocked', { allowParserImplementation: true }, /allow-parser-implementation=yes/],
    ['allow-feature-extraction=yes blocked', { allowFeatureExtraction: true }, /allow-feature-extraction=yes/],
    ['allow-training=yes blocked', { allowTraining: true }, /allow-training=yes/],
    ['allow-prediction=yes blocked', { allowPrediction: true }, /allow-prediction=yes/],
    ['allow-browser-runtime=yes blocked', { allowBrowserRuntime: true }, /allow-browser-runtime=yes/],
    ['allow-proxy-runtime=yes blocked', { allowProxyRuntime: true }, /allow-proxy-runtime=yes/],
    ['concurrency > 1 blocked', { concurrency: 2 }, /concurrency=1 is required/],
    ['retry > 0 blocked', { retry: 1 }, /retry=0 is required/],
    ['print-full-body=yes blocked', { printFullBody: true }, /print-full-body=yes/],
    ['save-full-body=yes blocked', { saveFullBody: true }, /save-full-body=yes/],
    ['print-full-json=yes blocked', { printFullJson: true }, /print-full-json=yes/],
    ['save-full-json=yes blocked', { saveFullJson: true }, /save-full-json=yes/],
    ['print-full-pageprops=yes blocked', { printFullPageprops: true }, /print-full-pageprops=yes/],
    ['save-full-pageprops=yes blocked', { saveFullPageprops: true }, /save-full-pageprops=yes/],
    ['execute-write=yes blocked', { executeWrite: true }, /execute-write=yes is blocked/],
    ['commit=yes blocked', { commit: true }, /commit=yes is blocked/],
    ['invent-targets=yes blocked', { inventTargets: true }, /invent-targets=yes is blocked/],
    ['fabricate-external-ids=yes blocked', { fabricateExternalIds: true }, /fabricate-external-ids=yes is blocked/],
    ['allow-odds-write=yes blocked', { allowOddsWrite: true }, /allow-odds-write=yes is blocked/],
]) {
    test(name, () => {
        const result = mod.validatePreflightInput(validInput(override));
        assert.equal(result.ok, false);
        assert.match(result.errors.join('\n'), pattern);
    });
}

test('parseArgs maps Makefile-style flags', () => {
    const parsed = mod.parseArgs(validArgv());
    assert.equal(parsed.leagueId, '53');
    assert.equal(parsed.matchDetailPreflightAuthorization, true);
    assert.equal(parsed.printFullPageprops, false);
});

test('parseArgs records positional and unknown arguments', () => {
    const parsed = mod.parseArgs(['loose-token', '--unknown-flag=yes', '--network-authorization']);
    assert.deepEqual(parsed.unknown, ['loose-token', 'unknown-flag']);
    assert.equal(parsed.networkAuthorization, true);
});

test('normalizeBooleanFlag falls back for invalid boolean text', () => {
    assert.equal(mod.normalizeBooleanFlag('maybe', 'fallback'), 'fallback');
});

test('missing required yes/no guardrails fail explicitly', () => {
    const result = mod.validatePreflightInput(
        validInput({
            networkAuthorization: undefined,
            allowDbWrite: undefined,
        })
    );
    assert.equal(result.ok, false);
    assert.match(result.errors.join('\n'), /missing network-authorization=yes/);
    assert.match(result.errors.join('\n'), /missing allow-db-write=no/);
});

for (const [name, inputManifest, pattern] of [
    ['manifest missing candidate_targets fails', { ...manifest(), candidate_targets: undefined }, /candidate_targets/],
    ['manifest candidate_targets not 50 fails', { ...manifest(), candidate_targets: [candidate(0)] }, /50 targets/],
    [
        'known completed external_id inside candidates blocked',
        {
            ...manifest(),
            candidate_targets: [
                candidate(0, { external_id: '4830746', match_id: '53_20252026_4830746' }),
                ...Array.from({ length: 49 }, (_, index) => candidate(index + 1)),
            ],
        },
        /overlaps known_completed_targets/,
    ],
    [
        'duplicate candidate external_id blocked',
        {
            ...manifest(),
            candidate_targets: [
                candidate(0),
                candidate(1, { external_id: '4830460' }),
                ...Array.from({ length: 48 }, (_, index) => candidate(index + 2)),
            ],
        },
        /duplicate external_id/,
    ],
    [
        'duplicate candidate match_id blocked',
        {
            ...manifest(),
            candidate_targets: [
                candidate(0),
                candidate(1, { match_id: '53_20252026_4830460' }),
                ...Array.from({ length: 48 }, (_, index) => candidate(index + 2)),
            ],
        },
        /duplicate match_id/,
    ],
    [
        'invalid external_id blocked',
        {
            ...manifest(),
            candidate_targets: [
                candidate(0, { external_id: 'abc' }),
                ...Array.from({ length: 49 }, (_, index) => candidate(index + 1)),
            ],
        },
        /external_id must be numeric/,
    ],
    [
        'wrong match_id convention blocked',
        {
            ...manifest(),
            candidate_targets: [
                candidate(0, { match_id: 'wrong' }),
                ...Array.from({ length: 49 }, (_, index) => candidate(index + 1)),
            ],
        },
        /match_id must be/,
    ],
    ['manifest schema mismatch fails', { ...manifest(), schema_version: 'wrong' }, /schema_version/],
    [
        'manifest known_completed_targets must be an array',
        { ...manifest(), known_completed_targets: null },
        /known_completed_targets must be an array/,
    ],
    [
        'manifest known_completed_targets count mismatch fails',
        { ...manifest(), known_completed_targets: knownCompleted().slice(0, 7) },
        /known_completed_targets must contain 8 targets/,
    ],
    [
        'manifest target_population_status mismatch fails',
        { ...manifest(), target_population_status: 'blocked' },
        /ready_for_no_write_preflight/,
    ],
    [
        'candidate batch_id mismatch fails',
        {
            ...manifest(),
            candidate_targets: [
                candidate(0, { batch_id: 'wrong' }),
                ...Array.from({ length: 49 }, (_, index) => candidate(index + 1)),
            ],
        },
        /batch_id mismatch/,
    ],
    [
        'candidate source mismatch fails',
        {
            ...manifest(),
            candidate_targets: [
                candidate(0, { source: 'other' }),
                ...Array.from({ length: 49 }, (_, index) => candidate(index + 1)),
            ],
        },
        /source mismatch/,
    ],
    [
        'candidate route mismatch fails',
        {
            ...manifest(),
            candidate_targets: [
                candidate(0, { route: 'api_match_details' }),
                ...Array.from({ length: 49 }, (_, index) => candidate(index + 1)),
            ],
        },
        /route mismatch/,
    ],
    [
        'candidate version mismatch fails',
        {
            ...manifest(),
            candidate_targets: [
                candidate(0, { raw_data_version: 'fotmob_html_hyd_v1' }),
                ...Array.from({ length: 49 }, (_, index) => candidate(index + 1)),
            ],
        },
        /raw_data_version mismatch/,
    ],
    [
        'candidate hash strategy mismatch fails',
        {
            ...manifest(),
            candidate_targets: [
                candidate(0, { hash_strategy: 'stable_raw_payload_v1' }),
                ...Array.from({ length: 49 }, (_, index) => candidate(index + 1)),
            ],
        },
        /hash_strategy mismatch/,
    ],
    [
        'candidate league metadata mismatch fails',
        {
            ...manifest(),
            candidate_targets: [
                candidate(0, { league_id: 54 }),
                ...Array.from({ length: 49 }, (_, index) => candidate(index + 1)),
            ],
        },
        /league_id mismatch/,
    ],
]) {
    test(name, () => {
        const result = mod.validateManifest(inputManifest);
        assert.equal(result.ok, false);
        assert.match(result.errors.join('\n'), pattern);
    });
}

test('existing v2 in DB marks skipped_existing_v2', async () => {
    const first = manifest().candidate_targets[0];
    const { payload, calls } = await buildPayload({
        existingRows: [
            {
                id: 1,
                match_id: first.match_id,
                external_id: first.external_id,
                data_version: 'fotmob_pageprops_v2',
                data_hash: 'a'.repeat(64),
            },
        ],
    });
    assert.equal(payload.skipped_existing_v2_count, 1);
    assert.equal(payload.target_summaries[0].preflight_status, 'skipped_existing_v2');
    assert.equal(calls.length, 49);
});

test('fake 50 successful pageProps preflight -> all hash_baseline_ready', async () => {
    const { payload, calls } = await buildPayload();
    assert.equal(payload.ok, true);
    assert.equal(payload.attempted_target_count, 50);
    assert.equal(payload.success_count, 50);
    assert.equal(payload.failed_count, 0);
    assert.equal(payload.blocked_count, 0);
    assert.equal(payload.target_population_status_after, 'ready_for_controlled_write_authorization');
    assert.equal(calls.length, 50);
    assert.ok(payload.target_summaries.every(target => target.preflight_status === 'hash_baseline_ready'));
});

test('stable_pageprops_payload_v1 hash computed as 64 hex', async () => {
    const { payload } = await buildPayload();
    assert.match(payload.target_summaries[0].stable_pageprops_hash, /^[a-f0-9]{64}$/);
});

test('raw_data shape _meta/matchId/pageProps verified', async () => {
    const { payload } = await buildPayload();
    const first = payload.target_summaries[0];
    assert.equal(first.raw_data_shape_valid, true);
    assert.equal(first.has_meta, true);
    assert.equal(first.has_matchId, true);
    assert.equal(first.has_pageProps, true);
});

test('missing pageProps marks preflight_failed and partial_preflight_completed', async () => {
    const badId = manifest().candidate_targets[0].external_id;
    const { payload } = await buildPayload({
        fetchResultsByExternalId: {
            [badId]: fetchResultFor(badId, { body: fakeHtml(badId, null) }),
        },
    });
    assert.equal(payload.failed_count, 1);
    assert.equal(payload.target_population_status_after, 'partial_preflight_completed');
    assert.equal(payload.target_summaries[0].preflight_status, 'failed');
    assert.equal(payload.target_summaries[0].failure_reason, 'PAGE_PROPS_NOT_FOUND');
});

test('invalid next data marks preflight_failed', async () => {
    const badId = manifest().candidate_targets[0].external_id;
    const { payload } = await buildPayload({
        fetchResultsByExternalId: {
            [badId]: fetchResultFor(badId, { body: '<html>no next data</html>' }),
        },
    });
    assert.equal(payload.target_summaries[0].preflight_status, 'failed');
    assert.match(payload.target_summaries[0].failure_reason, /NO_NEXT_DATA/);
});

test('non-blocking HTTP failure marks target failed and continues', async () => {
    const badId = manifest().candidate_targets[0].external_id;
    const { payload, calls } = await buildPayload({
        fetchResultsByExternalId: {
            [badId]: fetchResultFor(badId, { ok: false, status: 500, body: '<html>upstream error</html>' }),
        },
    });
    assert.equal(payload.failed_count, 1);
    assert.equal(payload.blocked_count, 0);
    assert.equal(payload.target_summaries[0].preflight_status, 'failed');
    assert.equal(payload.target_summaries[0].parse_status, 'http_failed');
    assert.equal(calls.length, 50);
});

test('403 response triggers blocked and no retry', async () => {
    const blockedId = manifest().candidate_targets[0].external_id;
    const { payload, calls } = await buildPayload({
        fetchResultsByExternalId: {
            [blockedId]: fetchResultFor(blockedId, {
                ok: false,
                status: 403,
                body: '<html>403 forbidden</html>',
                error: 'HTTP_403',
            }),
        },
    });
    assert.equal(payload.ok, false);
    assert.equal(payload.blocked_count, 1);
    assert.equal(payload.target_population_status_after, 'blocked');
    assert.equal(payload.target_summaries.length, 1);
    assert.equal(calls.length, 1);
});

test('captcha/cloudflare marker triggers blocked', async () => {
    const blockedId = manifest().candidate_targets[0].external_id;
    const { payload } = await buildPayload({
        fetchResultsByExternalId: {
            [blockedId]: fetchResultFor(blockedId, {
                body: '<html>Cloudflare captcha verify you are human</html>',
            }),
        },
    });
    assert.equal(payload.blocked_count, 1);
    assert.ok(payload.coverage_summary.block_captcha_markers.includes('captcha'));
});

test('access denied marker is captured as block marker', () => {
    const markers = mod.detectBlockMarkers({ http_status: 200, body: '<html>Access denied request blocked</html>' });
    assert.ok(markers.includes('access_denied'));
});

test('no retry and sequential manifest order', async () => {
    const { calls } = await buildPayload();
    assert.deepEqual(
        calls.slice(0, 3),
        manifest()
            .candidate_targets.slice(0, 3)
            .map(target => `https://www.fotmob.com/match/${target.external_id}`)
    );
});

test('no DB write / no raw_match_data write / no controlled write through runCli', async () => {
    const client = fakeClient();
    const outputs = [];
    const result = await mod.runCli(validArgv(), {
        client,
        manifest: manifest(),
        fetchHtmlFn: async requestUrl => fetchResultFor(requestUrl.split('/').pop()),
        writeManifest: false,
        writeReport: false,
        output: payload => outputs.push(payload),
        generatedAt: '2026-05-17T10:00:00.000Z',
    });
    assert.equal(result.status, 0);
    assert.equal(outputs[0].db_write_executed, false);
    assert.equal(outputs[0].raw_match_data_write_executed, false);
    assert.equal(outputs[0].controlled_write_executed, false);
    assert.equal(client.queries.length, 3);
});

test('runCli invalid input exits non-zero without DB access', async () => {
    const outputs = [];
    const result = await mod.runCli(validArgv({ 'allow-db-write': 'yes' }), {
        output: payload => outputs.push(payload),
    });
    assert.equal(result.status, 1);
    assert.match(outputs[0].failure_reason, /INPUT_INVALID/);
});

test('runCli writes manifest and report through injected writers', async () => {
    const writes = [];
    const result = await mod.runCli(validArgv(), {
        client: fakeClient(),
        manifest: manifest(),
        fetchHtmlFn: async requestUrl => fetchResultFor(requestUrl.split('/').pop()),
        writeManifestFile: (filePath, value) => writes.push({ type: 'manifest', filePath, value }),
        writeReportFile: (filePath, value) => writes.push({ type: 'report', filePath, value }),
        output: () => {},
        generatedAt: '2026-05-17T10:00:00.000Z',
    });
    assert.equal(result.status, 0);
    assert.deepEqual(
        writes.map(write => write.type),
        ['manifest', 'report']
    );
});

test('runCli catches read-only DB failures without writing files', async () => {
    const writes = [];
    const result = await mod.runCli(validArgv(), {
        client: {
            async query() {
                throw new Error('DB_READ_FAILED');
            },
        },
        manifest: manifest(),
        writeManifestFile: () => writes.push('manifest'),
        writeReportFile: () => writes.push('report'),
        output: () => {},
    });
    assert.equal(result.status, 1);
    assert.match(result.payload.failure_reason, /DB_READ_FAILED/);
    assert.deepEqual(writes, []);
});

test('invalid DB baseline before and after are blocked', async () => {
    const before = await mod.buildSingleLeagueSmallBatchPagePropsV2Preflight({
        input: validInput(),
        manifest: manifest(),
        protectedTableRowsBefore: protectedRows({ matches: 11 }),
        generatedAt: '2026-05-17T10:00:00.000Z',
    });
    assert.match(before.failure_reason, /DB_BASELINE_INVALID/);

    const after = await mod.buildSingleLeagueSmallBatchPagePropsV2Preflight({
        input: validInput(),
        manifest: manifest(),
        protectedTableRowsBefore: protectedRows(),
        protectedTableRowsAfter: protectedRows({ raw_match_data: 19 }),
        generatedAt: '2026-05-17T10:00:00.000Z',
        dependencies: {
            fetchHtmlFn: async requestUrl => fetchResultFor(requestUrl.split('/').pop()),
        },
    });
    assert.match(after.failure_reason, /DB_BASELINE_AFTER_INVALID/);
});

test('invalid manifest blocks preflight before fetch', async () => {
    const calls = [];
    const payload = await mod.buildSingleLeagueSmallBatchPagePropsV2Preflight({
        input: validInput(),
        manifest: { ...manifest(), target_population_status: 'blocked' },
        protectedTableRowsBefore: protectedRows(),
        generatedAt: '2026-05-17T10:00:00.000Z',
        dependencies: {
            fetchHtmlFn: async requestUrl => {
                calls.push(requestUrl);
                return fetchResultFor(requestUrl.split('/').pop());
            },
        },
    });
    assert.match(payload.failure_reason, /MANIFEST_INVALID/);
    assert.deepEqual(calls, []);
});

test('no browser/proxy and no parser/features/training side effects in payload', async () => {
    const { payload } = await buildPayload();
    assert.equal(payload.browser_used, false);
    assert.equal(payload.proxy_used, false);
    assert.equal(payload.parser_implementation_executed, false);
    assert.equal(payload.feature_extraction_executed, false);
    assert.equal(payload.training_executed, false);
    assert.equal(payload.prediction_executed, false);
});

test('no full body or pageProps printed/saved', async () => {
    const outputs = [];
    await mod.runCli(validArgv(), {
        client: fakeClient(),
        manifest: manifest(),
        fetchHtmlFn: async requestUrl => {
            const externalId = requestUrl.split('/').pop();
            return fetchResultFor(externalId);
        },
        writeManifest: false,
        writeReport: false,
        output: payload => outputs.push(payload),
        generatedAt: '2026-05-17T10:00:00.000Z',
    });
    const rendered = JSON.stringify(outputs[0]);
    assert.equal(rendered.includes('SECRET_PAGEPROPS_VALUE'), false);
    assert.equal(rendered.includes('__NEXT_DATA__'), false);
    assert.equal(outputs[0].full_pageprops_printed, false);
    assert.equal(outputs[0].full_pageprops_saved, false);
});

test('manifest update preserves known_completed_targets and writes baseline only for passed targets', async () => {
    const sourceManifest = manifest();
    const firstId = sourceManifest.candidate_targets[0].external_id;
    const { payload } = await buildPayload({
        manifest: sourceManifest,
        fetchResultsByExternalId: {
            [firstId]: fetchResultFor(firstId, { body: '<html>no next data</html>' }),
        },
    });
    const updated = mod.updateManifestWithPreflight(
        sourceManifest,
        payload.target_summaries,
        '2026-05-17T10:00:00.000Z'
    );
    assert.equal(updated.known_completed_targets.length, 8);
    assert.equal(updated.candidate_targets.length, 50);
    assert.equal(updated.candidate_targets[0].baseline_hash, null);
    assert.match(updated.candidate_targets[1].baseline_hash, /^[a-f0-9]{64}$/);
    assert.equal(updated.target_population_status, 'partial_preflight_completed');
});

test('all pass sets ready_for_controlled_write_authorization in manifest', async () => {
    const sourceManifest = manifest();
    const { payload } = await buildPayload({ manifest: sourceManifest });
    const updated = mod.updateManifestWithPreflight(
        sourceManifest,
        payload.target_summaries,
        '2026-05-17T10:00:00.000Z'
    );
    assert.equal(updated.preflight_passed_count, 50);
    assert.equal(updated.target_population_status, 'ready_for_controlled_write_authorization');
    assert.equal(updated.required_next_step, 'single_league_small_batch_controlled_pageprops_v2_write_authorization');
});

test('queryReadOnly blocks non SELECT SQL', async () => {
    await assert.rejects(
        () =>
            mod.queryReadOnly({ query: async () => ({ rows: [] }) }, 'UPDATE raw_match_data SET data_hash = $1', ['x']),
        /NON_SELECT|BLOCKED/
    );
});

test('no ProductionHarvester/raw ingest/odds pipeline import', () => {
    const originalLoad = Module._load;
    Module._load = function guardedLoad(request, parent, isMain) {
        if (/ProductionHarvester|raw_match_data_local_ingest|odds_harvest_pipeline|total_war_pipeline/i.test(request)) {
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

test('no browser/proxy runtime imports', () => {
    const originalLoad = Module._load;
    Module._load = function guardedLoad(request, parent, isMain) {
        if (/playwright|puppeteer|BrowserProvider|Chromium|proxy/i.test(request)) {
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

test('no child process or low-level network unless injected fetch path is used', async t => {
    const originals = {
        spawn: childProcess.spawn,
        exec: childProcess.exec,
        execFile: childProcess.execFile,
        request: http.request,
        httpsRequest: https.request,
    };
    const fail = name => () => {
        throw new Error(`${name} blocked`);
    };
    childProcess.spawn = fail('spawn');
    childProcess.exec = fail('exec');
    childProcess.execFile = fail('execFile');
    http.request = fail('http.request');
    https.request = fail('https.request');
    t.after(() => {
        childProcess.spawn = originals.spawn;
        childProcess.exec = originals.exec;
        childProcess.execFile = originals.execFile;
        http.request = originals.request;
        https.request = originals.httpsRequest;
    });
    const { payload } = await buildPayload();
    assert.equal(payload.success_count, 50);
});

test('module source does not call file deletion APIs', () => {
    const source = fs.readFileSync(MODULE_PATH, 'utf8');
    assert.doesNotMatch(source, /unlink|rmSync|rmdir|rm\s+-rf|git reset|git clean/);
});
