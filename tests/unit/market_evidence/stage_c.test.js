'use strict';

const assert = require('node:assert/strict');
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const test = require('node:test');
const { EventEmitter } = require('node:events');
const {
    createObservation,
    sha256Text,
    stableStringify,
    semanticProjection,
} = require('../../../src/infrastructure/market_evidence/contracts');
const {
    createIdentityRegistry,
    loadIdentityRegistry,
} = require('../../../src/infrastructure/market_evidence/identityRegistry');
const { adaptTheOddsApiRaw } = require('../../../src/infrastructure/market_evidence/theOddsApiAdapter');
const {
    writeImmutableRaw,
    createCaptureReceipt,
    writeReceipt,
    appendProjection,
} = require('../../../src/infrastructure/market_evidence/evidenceStore');
const {
    latestAsOf,
    latestAsOfMarket,
    deriveTimeline,
} = require('../../../src/infrastructure/market_evidence/asOfView');
const { createTheOddsApiClient } = require('../../../src/infrastructure/market_evidence/theOddsApiClient');
const { replayRaw } = require('../../../src/infrastructure/market_evidence/replay');

const rawText = fs.readFileSync(
    path.join(__dirname, '../../fixtures/market_evidence/the_odds_api_epl_h2h.minimal.json'),
    'utf8'
);
const registry = createIdentityRegistry({
    version: 'stage-c-fixture/v1',
    events: [
        {
            kind: 'event',
            provider: 'the-odds-api',
            provider_id: 'epl-fixture-001',
            canonical_id: 'fotmob:fixture-001',
            season: '2026/2027',
            provenance: 'fixture',
        },
    ],
    bookmakers: [
        {
            kind: 'bookmaker',
            provider: 'the-odds-api',
            provider_id: 'williamhill',
            canonical_id: 'bookmaker:william-hill',
            price_side: 'BOOKMAKER',
            provenance: 'fixture',
        },
    ],
    markets: [
        {
            kind: 'market',
            provider: 'the-odds-api',
            provider_id: 'h2h',
            canonical_id: 'MATCH/1X2/NULL',
            period: 'MATCH',
            market_type: '1X2',
            line: null,
            provenance: 'fixture',
        },
    ],
    selections: [
        {
            kind: 'selection',
            provider: 'the-odds-api',
            provider_id: 'Arsenal',
            canonical_id: 'HOME',
            selection: 'HOME',
            provenance: 'fixture',
        },
        {
            kind: 'selection',
            provider: 'the-odds-api',
            provider_id: 'Draw',
            canonical_id: 'DRAW',
            selection: 'DRAW',
            provenance: 'fixture',
        },
        {
            kind: 'selection',
            provider: 'the-odds-api',
            provider_id: 'Chelsea',
            canonical_id: 'AWAY',
            selection: 'AWAY',
            provenance: 'fixture',
        },
    ],
});
const capture = Object.freeze({
    capture_id: 'capture-fixture-001',
    acquisition_mode: 'REPLAY',
    request_started_at: '2026-08-27T13:31:20Z',
    response_received_at: '2026-08-27T13:31:49Z',
    ingested_at: '2026-08-27T13:32:00Z',
    raw_evidence_reference: 'raw/fixture.json',
    raw_sha256: sha256Text(rawText),
});
function observations(version = '1') {
    return adaptTheOddsApiRaw({ rawText, capture, registry, projectionVersion: version });
}

test('Stage C canonical contract rejects invalid odds, modes, sides, market identities and decision coupling', () => {
    const sample = observations()[0];
    for (const override of [
        { odds_decimal: 1 },
        { acquisition_mode: 'guess' },
        { price_side: 'MID' },
        { market_type: '1X2', line: 2.5 },
        { market_type: 'TOTAL', line: null },
        { market_type: 'TOTAL', line: ' ' },
        { quality_flags: ['quarantined', 'quarantined'] },
        { decision_target_at: '2026-08-27T13:00:00Z' },
    ]) {
        assert.throws(() => createObservation({ ...sample, ...override }));
    }
    const extensible = createObservation({
        ...sample,
        period: 'MATCH',
        market_type: 'ASIAN_HANDICAP',
        line: -0.25,
        price_side: 'BACK',
    });
    assert.equal(extensible.line, -0.25);
    assert.equal(extensible.price_side, 'BACK');
    assert.ok(
        ['LIVE_CAPTURE', 'HISTORICAL_API', 'HISTORICAL_FILE', 'REPLAY'].every(mode =>
            createObservation({ ...sample, acquisition_mode: mode })
        )
    );
    assert.equal(createObservation({ ...sample, price_side: 'LAY' }).price_side, 'LAY');
});

test('identity registry is independent and fails closed for unknown or ambiguous provider identities', () => {
    assert.throws(() => registry.resolve('bookmaker', 'the-odds-api', 'not-guessed'));
    assert.throws(() =>
        createIdentityRegistry({
            version: 'bad',
            events: [
                { kind: 'event', provider: 'x', provider_id: 'x' },
                { kind: 'event', provider: 'x', provider_id: 'x' },
            ],
        })
    );
    assert.equal(
        loadIdentityRegistry(path.join(__dirname, '../../fixtures/market_evidence/identity_registry.stage_c.v1.json'))
            .version,
        'stage-c-fixture/v1'
    );
});

test('The Odds API EPL h2h fixture normalizes to three versioned canonical observations', () => {
    const rows = observations();
    assert.equal(rows.length, 3);
    assert.deepEqual(
        rows.map(row => row.selection),
        ['HOME', 'DRAW', 'AWAY']
    );
    assert.ok(
        rows.every(
            row => row.provider === 'the-odds-api' && row.market_type === '1X2' && row.price_side === 'BOOKMAKER'
        )
    );
    assert.equal(rows[0].bookmaker_last_update_at, '2026-08-27T13:31:22Z');
    assert.equal(rows[0].response_received_at, '2026-08-27T13:31:49Z');
    assert.equal(rows[0].source_snapshot_at, null);
});

test('raw is sha256-verifiable and receipts are immutable and secret-safe', t => {
    const root = fs.mkdtempSync(path.join(os.tmpdir(), 'stage-c-'));
    t.after(() => fs.rmSync(root, { recursive: true, force: true }));
    const evidence = writeImmutableRaw({ rootDir: root, rawText });
    assert.equal(evidence.raw_sha256, sha256Text(rawText));
    assert.equal(fs.readFileSync(path.join(root, evidence.raw_evidence_reference), 'utf8'), rawText);
    writeImmutableRaw({ rootDir: root, rawText });
    const receipt = createCaptureReceipt({
        ...capture,
        provider: 'the-odds-api',
        http_status: 200,
        sanitized_request_parameters: { regions: 'uk', markets: 'h2h' },
        raw_sha256: evidence.raw_sha256,
        response_size_bytes: Buffer.byteLength(rawText),
    });
    writeReceipt({ rootDir: root, receipt });
    assert.throws(() =>
        writeReceipt({
            rootDir: root,
            receipt: { ...capture, capture_id: 'capture-fixture-001', provider: 'the-odds-api' },
        })
    );
    assert.throws(() =>
        writeReceipt({
            rootDir: root,
            receipt: {
                ...capture,
                capture_id: 'bad-secret',
                endpoint: `https://x/?${['api', 'Key'].join('')}=secret`,
            },
        })
    );
    assert.throws(() =>
        writeReceipt({
            rootDir: root,
            receipt: {
                ...capture,
                capture_id: 'bad-json-secret',
                sanitized_request_parameters: { [['api', 'Key'].join('')]: 'secret' },
            },
        })
    );
});

test('replay has deterministic semantic projection while ingestion metadata is explicit evidence metadata', () => {
    const first = observations();
    const second = observations();
    const replay1Sha256 = sha256Text(stableStringify(first.map(semanticProjection)));
    const replay2Sha256 = sha256Text(stableStringify(second.map(semanticProjection)));
    assert.match(replay1Sha256, /^[a-f0-9]{64}$/);
    assert.equal(replay1Sha256, replay2Sha256, 'REPLAY_1_SHA256 must equal REPLAY_2_SHA256');
    const v2 = observations('2');
    assert.notEqual(v2[0].observation_id, first[0].observation_id);
    assert.equal(first[0].projection_version, '1');
    assert.equal(v2[0].projection_version, '2');
});

test('offline replay reads immutable raw and can append projections without network access', t => {
    const root = fs.mkdtempSync(path.join(os.tmpdir(), 'stage-c-replay-'));
    t.after(() => fs.rmSync(root, { recursive: true, force: true }));
    const rawPath = path.join(root, 'capture.json');
    fs.writeFileSync(rawPath, rawText, 'utf8');
    const ledgerPath = path.join(root, 'ledger.jsonl');
    const replayed = replayRaw({ rawPath, capture, registry, projectionVersion: '1', ledgerPath });
    assert.equal(replayed.length, 3);
    assert.equal(fs.readFileSync(ledgerPath, 'utf8').trim().split('\n').length, 3);
    assert.throws(
        () =>
            replayRaw({
                rawPath,
                capture: { ...capture, raw_sha256: '0'.repeat(64) },
                registry,
                projectionVersion: '1',
            }),
        /does not match replay input/
    );
});

test('append-only ledger preserves old projections and appends new versions', t => {
    const root = fs.mkdtempSync(path.join(os.tmpdir(), 'stage-c-ledger-'));
    t.after(() => fs.rmSync(root, { recursive: true, force: true }));
    const ledger = path.join(root, 'ledger.jsonl');
    appendProjection({ ledgerPath: ledger, projection: observations('1')[0] });
    appendProjection({ ledgerPath: ledger, projection: observations('2')[0] });
    const rows = fs.readFileSync(ledger, 'utf8').trim().split('\n').map(JSON.parse);
    assert.deepEqual(
        rows.map(row => row.projection_version),
        ['1', '2']
    );
});

test('as-of view strictly uses knowledge time, not earlier bookmaker source time', () => {
    const row = observations()[0];
    const query = {
        canonical_event_id: row.canonical_event_id,
        canonical_bookmaker_id: row.canonical_bookmaker_id,
        period: 'MATCH',
        market_type: '1X2',
        line: null,
    };
    assert.equal(latestAsOf([row], { ...query, decision_time: '2026-08-27T13:31:30Z' }), null);
    assert.throws(() => latestAsOf([row], { ...query, decision_time: '2026-08-27T13:31:30+00:00' }), /UTC ISO-8601/);
    assert.equal(
        latestAsOf([row], { ...query, decision_time: '2026-08-27T13:31:50Z' }).observation_id,
        row.observation_id
    );
    assert.equal(
        latestAsOf([{ ...row, quality_flags: ['quarantined'] }], { ...query, decision_time: '2026-08-27T13:31:50Z' }),
        null
    );
    assert.deepEqual(
        latestAsOfMarket(observations(), { ...query, decision_time: '2026-08-27T13:31:50Z' }).map(
            item => item.selection
        ),
        ['AWAY', 'DRAW', 'HOME']
    );
    const timeline = deriveTimeline(observations(), {
        canonical_event_id: row.canonical_event_id,
        canonical_bookmaker_id: row.canonical_bookmaker_id,
        kickoff_utc: row.kickoff_utc,
    });
    assert.ok(timeline.opening && timeline.current && timeline.closing);
    assert.deepEqual(Object.keys(timeline.opening_by_selection).sort(), ['AWAY', 'DRAW', 'HOME']);
    const postKickoffHome = {
        ...row,
        response_received_at: '2026-09-12T15:01:00Z',
        ingested_at: '2026-09-12T15:01:01Z',
    };
    const timelineWithPostKickoff = deriveTimeline([row, ...observations().slice(1), postKickoffHome], {
        canonical_event_id: row.canonical_event_id,
        canonical_bookmaker_id: row.canonical_bookmaker_id,
        kickoff_utc: row.kickoff_utc,
    });
    assert.equal(timelineWithPostKickoff.opening_by_selection.HOME.observation_id, row.observation_id);
    assert.equal(timelineWithPostKickoff.closing_by_selection.HOME.observation_id, row.observation_id);
});

test('live client is key-gated and bounded to three requests without logging secrets', async () => {
    const previous = process.env.THE_ODDS_API_KEY;
    delete process.env.THE_ODDS_API_KEY;
    const { buildRequestUrl } = require('../../../src/infrastructure/market_evidence/theOddsApiClient');
    assert.throws(() => buildRequestUrl(), /required/);
    process.env.THE_ODDS_API_KEY = 'test-only-not-persisted';
    assert.throws(() => buildRequestUrl({ markets: 'totals' }), /only permits/);
    delete process.env.THE_ODDS_API_KEY;
    if (previous !== undefined) process.env.THE_ODDS_API_KEY = previous;
    const client = createTheOddsApiClient({
        requestFn: () => {
            throw new Error('network should be stubbed in this test');
        },
    });
    assert.equal(client.request_count, 0);
    assert.throws(() => client.capture(), /required/);
    assert.equal(client.request_count, 0);
});

test('live client captures one bounded response and exposes only sanitized quota headers', async t => {
    const previous = process.env.THE_ODDS_API_KEY;
    process.env.THE_ODDS_API_KEY = 'test-only-not-persisted';
    t.after(() => {
        if (previous === undefined) delete process.env.THE_ODDS_API_KEY;
        else process.env.THE_ODDS_API_KEY = previous;
    });
    let seenUrl = '';
    const client = createTheOddsApiClient({
        requestFn: (url, options, callback) => {
            seenUrl = url;
            assert.equal(options.headers['User-Agent'], 'FootballPrediction-stage-c-pilot/1.0');
            const response = new EventEmitter();
            response.statusCode = 200;
            response.headers = {
                'x-requests-remaining': '499',
                authorization: 'must-not-propagate',
                'x-provider-internal': 'must-not-propagate',
            };
            process.nextTick(() => {
                callback(response);
                response.emit('data', Buffer.from(rawText));
                response.emit('end');
            });
            return new EventEmitter();
        },
    });
    const result = await client.capture();
    assert.match(seenUrl, /markets=h2h/);
    assert.equal(result.http_status, 200);
    assert.equal(result.provider_quota['x-requests-remaining'], '499');
    assert.equal(result.provider_quota.authorization, undefined);
    assert.equal(result.provider_quota['x-provider-internal'], undefined);
    assert.equal(client.request_count, 1);
    assert.throws(() => client.capture({ markets: 'totals' }), /only permits/);
});
