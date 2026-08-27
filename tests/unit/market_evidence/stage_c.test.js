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
const {
    adaptTheOddsApiRaw,
    adaptTheOddsApiCapture,
    buildCoverageEvidence,
} = require('../../../src/infrastructure/market_evidence/theOddsApiAdapter');
const {
    writeImmutableRaw,
    readImmutableRaw,
    createCaptureReceipt,
    writeReceipt,
    writeCoverageEvidence,
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
            home_team: 'Arsenal',
            away_team: 'Chelsea',
            kickoff_utc: '2026-09-12T15:00:00Z',
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

function captureForRaw(rawPayload) {
    return { ...capture, raw_sha256: sha256Text(rawPayload) };
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
        { odds_decimal: '2.1' },
        { line: 2.5, canonical_market_id: 'MATCH/1X2/NULL' },
        { available_volume: '10' },
        { bet_limit: '10' },
        { season: 2026 },
        { canonical_market_id: 'MATCH/TOTAL/2.5' },
        { canonical_selection_id: 'HOME_ALIAS' },
        { raw_evidence_reference: '../outside.json' },
        { quality_flags: ['quarantined', 'quarantined'] },
        { decision_target_at: '2026-08-27T13:00:00Z' },
    ]) {
        assert.throws(() => createObservation({ ...sample, ...override }));
    }
    assert.throws(() => createObservation({ ...sample, decision_target_at: undefined }));
    const extensible = createObservation({
        ...sample,
        period: 'MATCH',
        market_type: 'ASIAN_HANDICAP',
        line: -0.25,
        canonical_market_id: 'MATCH/ASIAN_HANDICAP/-0.25',
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

test('machine-readable JSON Schema rejects calendar-invalid, blank and inconsistent observations', () => {
    const Ajv = require('ajv');
    const schema = JSON.parse(
        fs.readFileSync(path.join(__dirname, '../../../schemas/market_evidence/market_observation.schema.json'), 'utf8')
    );
    delete schema.$schema;
    const validate = new Ajv({ allErrors: true, format: 'full' }).compile(schema);
    const sample = observations()[0];
    assert.equal(validate(sample), true);
    assert.equal(validate({ ...sample, kickoff_utc: '2026-02-30T00:00:00Z' }), false);
    assert.equal(validate({ ...sample, provider: '   ' }), false);
    assert.equal(validate({ ...sample, canonical_market_id: 'MATCH/TOTAL/2.5' }), false);
    assert.equal(
        validate({
            ...sample,
            market_type: 'ASIAN_HANDICAP',
            line: -0.25,
            canonical_market_id: 'MATCH/ASIAN_HANDICAP/0.25',
        }),
        false
    );
});

test('identity registry is independent and fails closed for unknown or ambiguous provider identities', () => {
    for (const kind of ['event', 'bookmaker', 'market', 'selection']) {
        assert.throws(() => registry.resolve(kind, 'the-odds-api', 'not-guessed'));
    }
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
    const registryWithoutHashDir = fs.mkdtempSync(path.join(os.tmpdir(), 'stage-c-registry-'));
    const registryWithoutHashPath = path.join(registryWithoutHashDir, 'registry.json');
    fs.writeFileSync(registryWithoutHashPath, JSON.stringify({ version: 'v1' }));
    try {
        assert.throws(() => loadIdentityRegistry(registryWithoutHashPath), /content_sha256 is required/);
    } finally {
        fs.rmSync(registryWithoutHashDir, { recursive: true, force: true });
    }
    assert.throws(
        () =>
            createIdentityRegistry({
                version: 'bad-market',
                markets: [
                    {
                        kind: 'market',
                        provider: 'x',
                        provider_id: 'h2h',
                        canonical_id: 'MATCH/TOTAL/2.5',
                        period: 'MATCH',
                        market_type: '1X2',
                        line: null,
                        provenance: 'fixture',
                    },
                ],
            }),
        /canonical_id does not match/
    );
    assert.throws(
        () =>
            createIdentityRegistry({
                version: 'bad-selection',
                selections: [
                    {
                        kind: 'selection',
                        provider: 'x',
                        provider_id: 'home',
                        canonical_id: 'HOME_ALIAS',
                        selection: 'HOME',
                        provenance: 'fixture',
                    },
                ],
            }),
        /canonical_id does not match selection/
    );
    assert.throws(
        () =>
            createIdentityRegistry({
                version: 'bad-kind',
                events: [
                    { kind: 'bookmaker', provider: 'x', provider_id: 'x', canonical_id: 'x', provenance: 'fixture' },
                ],
            }),
        /invalid mapping kind/
    );
    assert.throws(
        () =>
            createIdentityRegistry({
                version: 'bad-hash',
                content_sha256: '0'.repeat(64),
            }),
        /content_sha256 does not match/
    );
    assert.throws(
        () => createIdentityRegistry({ version: 'bad-field', unexpected: true }),
        /unknown identity registry field/
    );
    assert.throws(
        () =>
            createIdentityRegistry({
                version: 'bad-mapping-field',
                bookmakers: [
                    {
                        kind: 'bookmaker',
                        provider: 'the-odds-api',
                        provider_id: 'williamhill',
                        canonical_id: 'bookmaker:william-hill',
                        price_side: 'BOOKMAKER',
                        provenance: 'fixture',
                        hidden_alias: true,
                    },
                ],
            }),
        /unknown identity mapping field/
    );
    assert.throws(
        () =>
            createIdentityRegistry({
                version: 'missing-side',
                bookmakers: [
                    {
                        kind: 'bookmaker',
                        provider: 'the-odds-api',
                        provider_id: 'unknown-side',
                        canonical_id: 'bookmaker:unknown-side',
                        provenance: 'fixture',
                    },
                ],
            }),
        /price_side/
    );
    const exchangeRegistry = createIdentityRegistry({
        version: 'exchange/v1',
        bookmakers: [
            {
                kind: 'bookmaker',
                provider: 'the-odds-api',
                provider_id: 'betfair_exchange',
                canonical_id: 'bookmaker:betfair-exchange',
                price_side: 'BACK',
                provenance: 'official-provider-response',
            },
        ],
    });
    assert.equal(exchangeRegistry.resolve('bookmaker', 'the-odds-api', 'betfair_exchange').price_side, 'BACK');
    const asianRegistry = createIdentityRegistry({
        version: 'market-extensibility/v1',
        markets: [
            {
                kind: 'market',
                provider: 'the-odds-api',
                provider_id: 'asian_handicap',
                canonical_id: 'MATCH/ASIAN_HANDICAP/-0.25',
                period: 'MATCH',
                market_type: 'ASIAN_HANDICAP',
                line: -0.25,
                provenance: 'contract-only',
            },
        ],
    });
    assert.equal(
        asianRegistry.resolve('market', 'the-odds-api', 'asian_handicap').canonical_id,
        'MATCH/ASIAN_HANDICAP/-0.25'
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
    assert.match(rows[0].identity_registry_sha256, /^[a-f0-9]{64}$/);
});

test('event identity is checked against the independently governed registry and IDs bind projection versions', () => {
    const swapped = JSON.parse(rawText);
    swapped[0].home_team = 'Chelsea';
    swapped[0].away_team = 'Arsenal';
    const swappedText = JSON.stringify(swapped);
    assert.throws(
        () =>
            adaptTheOddsApiRaw({
                rawText: swappedText,
                capture: captureForRaw(swappedText),
                registry,
                projectionVersion: '1',
            }),
        /event identity conflicts with registry/
    );
    const v1 = observations('1');
    const v2Registry = createIdentityRegistry({
        version: 'stage-c-fixture/v2',
        events: [
            {
                kind: 'event',
                provider: 'the-odds-api',
                provider_id: 'epl-fixture-001',
                canonical_id: 'fotmob:fixture-001',
                season: '2026/2027',
                home_team: 'Arsenal',
                away_team: 'Chelsea',
                kickoff_utc: '2026-09-12T15:00:00Z',
                provenance: 'fixture-v2',
            },
        ],
        bookmakers: registry.list('bookmaker', 'the-odds-api'),
        markets: registry.list('market', 'the-odds-api'),
        selections: registry.list('selection', 'the-odds-api'),
    });
    const v2 = adaptTheOddsApiRaw({ rawText, capture, registry: v2Registry, projectionVersion: '1' });
    assert.notEqual(v1[0].observation_id, v2[0].observation_id);
});

test('adapter fails closed for malformed or incomplete EPL market payloads and side conflicts', () => {
    const payload = JSON.parse(rawText);
    assert.throws(
        () => adaptTheOddsApiRaw({ rawText: '{}', capture: captureForRaw('{}'), registry, projectionVersion: '1' }),
        /payload must be an array/
    );
    const unknownEvent = JSON.parse(rawText);
    unknownEvent[0].id = 'not-mapped-event';
    assert.throws(
        () =>
            adaptTheOddsApiRaw({
                rawText: JSON.stringify(unknownEvent),
                capture: captureForRaw(JSON.stringify(unknownEvent)),
                registry,
                projectionVersion: '1',
            }),
        /identity mapping unknown: event/
    );
    assert.throws(
        () =>
            adaptTheOddsApiRaw({
                rawText: JSON.stringify([{ ...payload[0], bookmakers: [] }]),
                capture: captureForRaw(JSON.stringify([{ ...payload[0], bookmakers: [] }])),
                registry,
                projectionVersion: '1',
            }),
        /bookmakers must be a non-empty array/
    );
    const unknownMarket = JSON.parse(rawText);
    unknownMarket[0].bookmakers[0].markets[0].key = 'totals';
    assert.throws(
        () =>
            adaptTheOddsApiRaw({
                rawText: JSON.stringify(unknownMarket),
                capture: captureForRaw(JSON.stringify(unknownMarket)),
                registry,
                projectionVersion: '1',
            }),
        /unsupported Stage C provider market/
    );
    const unknownBookmaker = JSON.parse(rawText);
    unknownBookmaker[0].bookmakers[0].key = 'not-mapped-bookmaker';
    assert.throws(
        () =>
            adaptTheOddsApiRaw({
                rawText: JSON.stringify(unknownBookmaker),
                capture: captureForRaw(JSON.stringify(unknownBookmaker)),
                registry,
                projectionVersion: '1',
            }),
        /identity mapping unknown: bookmaker/
    );
    const unknownSelection = JSON.parse(rawText);
    unknownSelection[0].bookmakers[0].markets[0].outcomes[0].name = 'Arsenal FC';
    assert.throws(
        () =>
            adaptTheOddsApiRaw({
                rawText: JSON.stringify(unknownSelection),
                capture: captureForRaw(JSON.stringify(unknownSelection)),
                registry,
                projectionVersion: '1',
            }),
        /identity mapping unknown: selection/
    );
    const missingSelection = JSON.parse(rawText);
    missingSelection[0].bookmakers[0].markets[0].outcomes.pop();
    assert.throws(
        () =>
            adaptTheOddsApiRaw({
                rawText: JSON.stringify(missingSelection),
                capture: captureForRaw(JSON.stringify(missingSelection)),
                registry,
                projectionVersion: '1',
            }),
        /missing canonical selection: AWAY/
    );
    const sideConflict = JSON.parse(rawText);
    sideConflict[0].bookmakers[0].markets[0].outcomes[0].price_side = 'LAY';
    assert.throws(
        () =>
            adaptTheOddsApiRaw({
                rawText: JSON.stringify(sideConflict),
                capture: captureForRaw(JSON.stringify(sideConflict)),
                registry,
                projectionVersion: '1',
            }),
        /conflicts with identity registry/
    );
});

test('UTC contract rejects calendar-invalid timestamps instead of Date.parse normalization', () => {
    const sample = observations()[0];
    assert.throws(() => createObservation({ ...sample, kickoff_utc: '2026-02-30T00:00:00Z' }), /UTC ISO-8601/);
});

test('raw is sha256-verifiable and receipts are immutable and secret-safe', t => {
    const root = fs.mkdtempSync(path.join(os.tmpdir(), 'stage-c-'));
    t.after(() => fs.rmSync(root, { recursive: true, force: true }));
    const evidence = writeImmutableRaw({ rootDir: root, rawText });
    assert.equal(evidence.raw_sha256, sha256Text(rawText));
    assert.equal(fs.readFileSync(path.join(root, evidence.raw_evidence_reference), 'utf8'), rawText);
    writeImmutableRaw({ rootDir: root, rawText });
    fs.chmodSync(path.join(root, evidence.raw_evidence_reference), 0o644);
    fs.writeFileSync(path.join(root, evidence.raw_evidence_reference), `${rawText}tampered`);
    assert.throws(() => writeImmutableRaw({ rootDir: root, rawText }), /immutable raw hash collision/);
    fs.chmodSync(path.join(root, evidence.raw_evidence_reference), 0o444);
    assert.throws(
        () =>
            readImmutableRaw({
                rootDir: root,
                rawEvidenceReference: evidence.raw_evidence_reference,
                expectedSha256: evidence.raw_sha256,
            }),
        /does not match immutable content/
    );
    const receipt = createCaptureReceipt({
        ...capture,
        provider: 'the-odds-api',
        http_status: 200,
        sanitized_request_parameters: { regions: 'uk', markets: 'h2h' },
        coverage_evidence: buildCoverageEvidence({
            rawText,
            expectedProviderBookmakerIds: ['williamhill', 'pinnacle'],
        }),
        raw_sha256: evidence.raw_sha256,
        response_size_bytes: Buffer.byteLength(rawText),
    });
    writeReceipt({ rootDir: root, receipt });
    assert.equal(fs.statSync(path.join(root, 'receipts', `${receipt.capture_id}.json`)).mode & 0o222, 0);
    assert.equal(
        JSON.parse(fs.readFileSync(path.join(root, 'receipts', `${receipt.capture_id}.json`), 'utf8')).ingested_at,
        capture.ingested_at
    );
    assert.throws(
        () =>
            createCaptureReceipt({
                ...receipt,
                ingested_at: '2026-08-27T13:31:48Z',
            }),
        /ingestion precedes response/
    );
    assert.throws(() =>
        writeReceipt({
            rootDir: root,
            receipt: { ...capture, capture_id: 'capture-fixture-001', provider: 'the-odds-api' },
        })
    );
    assert.throws(() =>
        createCaptureReceipt({
            ...receipt,
            ingested_at: undefined,
        })
    );
    assert.throws(() =>
        writeReceipt({
            rootDir: root,
            receipt: { ...receipt, capture_id: 'invalid-extra-field', unexpected: 'not-allowed' },
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
    assert.throws(() =>
        createCaptureReceipt({
            ...receipt,
            sanitized_request_parameters: { headers: { x: 'secret-value-without-keyword' } },
        })
    );
    assert.throws(() =>
        createCaptureReceipt({
            ...receipt,
            provider_quota: { 'x-provider-internal': '123' },
        })
    );
});

test('coverage evidence explicitly records observed and missing provider bookmaker coverage', t => {
    const expected = ['williamhill', 'pinnacle', 'betfair_exchange'];
    const evidence = buildCoverageEvidence({ rawText, expectedProviderBookmakerIds: expected });
    assert.equal(evidence.status, 'PARTIAL');
    assert.deepEqual(evidence.missing_expected_provider_bookmaker_ids, ['betfair_exchange', 'pinnacle']);
    const captureResult = adaptTheOddsApiCapture({ rawText, capture, registry, projectionVersion: '1' });
    assert.equal(captureResult.observations.length, 3);
    assert.equal(captureResult.coverage_evidence.status, 'OBSERVED');
    const root = fs.mkdtempSync(path.join(os.tmpdir(), 'stage-c-coverage-'));
    t.after(() => fs.rmSync(root, { recursive: true, force: true }));
    const target = writeCoverageEvidence({ rootDir: root, captureId: capture.capture_id, evidence });
    assert.equal(JSON.parse(fs.readFileSync(target, 'utf8')).status, 'PARTIAL');
    assert.throws(() => writeCoverageEvidence({ rootDir: root, captureId: capture.capture_id, evidence }), /immutable/);
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
    fs.chmodSync(rawPath, 0o444);
    const ledgerPath = path.join(root, 'ledger.jsonl');
    const replayed = replayRaw({ rawPath, capture, registry, projectionVersion: '1', ledgerPath });
    const replayedAgain = replayRaw({ rawPath, capture, registry, projectionVersion: '1' });
    assert.equal(replayed.length, 3);
    assert.equal(fs.readFileSync(ledgerPath, 'utf8').trim().split('\n').length, 3);
    assert.equal(
        sha256Text(stableStringify(replayed.map(semanticProjection))),
        sha256Text(stableStringify(replayedAgain.map(semanticProjection))),
        'replaying the same raw with fixed adapter and registry versions is deterministic'
    );
    assert.throws(
        () => replayRaw({ rawPath, capture: { ...capture, raw_sha256: undefined }, registry, projectionVersion: '1' }),
        /raw_sha256 is required/
    );
    assert.throws(
        () =>
            adaptTheOddsApiRaw({
                rawText,
                capture: { ...capture, raw_sha256: '0'.repeat(64) },
                registry,
                projectionVersion: '1',
            }),
        /does not match provider payload/
    );
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
    assert.throws(
        () => appendProjection({ ledgerPath: ledger, projection: { foo: 'bar' } }),
        /invalid MarketObservation/
    );
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
        latestAsOf([{ ...row, price_side: 'BACK', observation_id: `${row.observation_id}-back` }], {
            ...query,
            price_side: 'BACK',
            decision_time: '2026-08-27T13:31:50Z',
        }).price_side,
        'BACK'
    );
    assert.throws(
        () => latestAsOf([row], { ...query, price_side: 'MID', decision_time: '2026-08-27T13:31:50Z' }),
        /price_side/
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
        decision_time: '2026-09-12T14:00:00Z',
    });
    assert.ok(timeline.opening && timeline.current && timeline.closing);
    assert.deepEqual(Object.keys(timeline.opening_by_selection).sort(), ['AWAY', 'DRAW', 'HOME']);
    const postKickoffHome = {
        ...row,
        observation_id: `${row.observation_id}-post`,
        response_received_at: '2026-09-12T15:01:00Z',
        ingested_at: '2026-09-12T15:01:01Z',
    };
    const timelineWithPostKickoff = deriveTimeline([row, ...observations().slice(1), postKickoffHome], {
        canonical_event_id: row.canonical_event_id,
        canonical_bookmaker_id: row.canonical_bookmaker_id,
        kickoff_utc: row.kickoff_utc,
        decision_time: '2026-09-12T15:02:00Z',
    });
    assert.equal(timelineWithPostKickoff.opening_by_selection.HOME.observation_id, row.observation_id);
    assert.equal(timelineWithPostKickoff.closing_by_selection.HOME.observation_id, row.observation_id);
    assert.equal(timelineWithPostKickoff.current_by_selection.HOME.observation_id, postKickoffHome.observation_id);
    const atKickoffHome = {
        ...row,
        observation_id: `${row.observation_id}-at-kickoff`,
        response_received_at: row.kickoff_utc,
        ingested_at: row.kickoff_utc,
    };
    const timelineWithAtKickoff = deriveTimeline([row, ...observations().slice(1), atKickoffHome], {
        canonical_event_id: row.canonical_event_id,
        canonical_bookmaker_id: row.canonical_bookmaker_id,
        kickoff_utc: row.kickoff_utc,
        decision_time: '2026-09-12T15:02:00Z',
    });
    assert.equal(timelineWithAtKickoff.closing_by_selection.HOME.observation_id, row.observation_id);
    assert.throws(
        () =>
            deriveTimeline(observations(), {
                canonical_event_id: row.canonical_event_id,
                canonical_bookmaker_id: row.canonical_bookmaker_id,
                kickoff_utc: row.kickoff_utc,
            }),
        /decision_time must be UTC ISO-8601/
    );
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
