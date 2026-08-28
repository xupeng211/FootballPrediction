'use strict';
/* eslint-disable max-lines -- Stage C acceptance tests intentionally keep the full invariant matrix together. */

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
    readProjectionLedger,
    ledgerManifestPath,
} = require('../../../src/infrastructure/market_evidence/evidenceStore');
const {
    latestAsOf,
    latestAsOfMarket,
    deriveTimeline,
} = require('../../../src/infrastructure/market_evidence/asOfView');
const {
    createDirectRequestFn,
    createStableProxyRequestFn,
    createTheOddsApiClient,
    resolveTransportPolicy,
} = require('../../../src/infrastructure/market_evidence/theOddsApiClient');
const { replayRaw } = require('../../../src/infrastructure/market_evidence/replay');
const { createGovernedFixtureTestContext } = require('../../helpers/market_evidence_authority');

const rawText = fs.readFileSync(
    path.join(__dirname, '../../fixtures/market_evidence/the_odds_api_epl_h2h.minimal.json'),
    'utf8'
);
/* const registry = createIdentityRegistry({
    version: 'stage-c-fixture/v1',
    governed_event_ids: ['evt_fixture001'],
    events: [
        {
            kind: 'event',
            provider: 'the-odds-api',
            provider_id: 'epl-fixture-001',
            canonical_id: 'evt_fixture001',
            season: '2026/2027',
            home_team: 'Arsenal',
            away_team: 'Chelsea',
            kickoff_utc: '2026-09-12T15:00:00Z',
            provider_observed_kickoff_utc: '2026-09-12T15:00:00Z',
            identity_decision_id: 'idn-fixture-001',
            identity_decision_status: 'MATCHED',
            identity_ruleset_version: 'fixture-identity-ruleset/v1',
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
}); */
const capture = Object.freeze({
    capture_id: 'capture-fixture-001',
    provider: 'the-odds-api',
    acquisition_mode: 'HISTORICAL_FILE',
    request_started_at: '2026-08-27T13:31:20Z',
    response_received_at: '2026-08-27T13:31:49Z',
    ingested_at: '2026-08-27T13:31:49Z',
    raw_evidence_reference: 'raw/fixture.json',
    raw_sha256: sha256Text(rawText),
});
const governed = createGovernedFixtureTestContext({ rawText });
const { registry, decisionLedger } = governed;
function observations(version = '1') {
    return adaptTheOddsApiRaw({ rawText, capture, registry, decisionLedger, projectionVersion: version });
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
        { competition: 'Championship' },
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
    const validate = new Ajv({ allErrors: true, format: 'full' }).compile(schema);
    const sample = observations()[0];
    assert.equal(validate(sample), true);
    assert.equal(validate({ ...sample, kickoff_utc: '2026-02-30T00:00:00Z' }), false);
    assert.equal(validate({ ...sample, provider: '   ' }), false);
    assert.equal(validate({ ...sample, canonical_market_id: 'MATCH/TOTAL/2.5' }), false);
    assert.equal(
        validate({
            ...sample,
            market_type: 'TOTAL',
            line: 3.5,
            canonical_market_id: 'MATCH/TOTAL/2.5',
        }),
        false
    );
    assert.equal(
        validate({
            ...sample,
            market_type: 'ASIAN_HANDICAP',
            line: -0.25,
            canonical_market_id: 'MATCH/ASIAN_HANDICAP/0.25',
        }),
        false
    );
    assert.equal(
        validate({
            ...sample,
            market_type: 'ASIAN_HANDICAP',
            line: -0.25,
            canonical_market_id: 'MATCH/ASIAN_HANDICAP/-0.25',
        }),
        true
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
            governed_event_ids: ['evt_bad'],
            events: [
                { kind: 'event', provider: 'x', provider_id: 'x' },
                { kind: 'event', provider: 'x', provider_id: 'x' },
            ],
        })
    );
    assert.throws(() => createIdentityRegistry({
        version: 'outside-kickoff-tolerance',
        allocationAuthority: registry.allocationAuthority,
        events: [{ ...registry.resolve('event', 'the-odds-api', 'epl-fixture-001'), provider_observed_kickoff_utc: '2026-09-12T15:15:01Z' }],
    }), /kickoff exceeds identity tolerance/);
    assert.throws(() => loadIdentityRegistry(path.join(__dirname, '../../fixtures/market_evidence/identity_registry.stage_c.v1.json')), /verified Fixture Universe allocation authority/);
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

test('event registry accepts only governed FootballPrediction allocations', () => {
    const event = registry.resolve('event', 'the-odds-api', 'epl-fixture-001');
    assert.throws(() => createIdentityRegistry({ version: 'provider-shaped', allocationAuthority: registry.allocationAuthority, events: [{ ...event, canonical_id: 'fotmob:fixture-001' }] }), /absent from the verified allocation/);
    assert.throws(() => createIdentityRegistry({ version: 'unknown-event', allocationAuthority: registry.allocationAuthority, events: [{ ...event, canonical_id: 'evt_other' }] }), /absent from the verified allocation/);
    assert.equal(createIdentityRegistry({ version: 'governed-event', allocationAuthority: registry.allocationAuthority, events: [event] }).resolve('event', 'the-odds-api', 'epl-fixture-001').canonical_id, event.canonical_id);
});

test('LIVE_CAPTURE requires an explicit post-projection availability boundary', () => {
    const live = { ...capture, acquisition_mode: 'LIVE_CAPTURE' };
    assert.throws(() => adaptTheOddsApiRaw({ rawText, capture: live, registry, projectionVersion: '1' }), /LIVE_CAPTURE projection availability is required/);
    const rows = adaptTheOddsApiRaw({ rawText, capture: live, registry, projectionVersion: '1', projectionAvailableAt: '2026-08-27T13:31:50Z' }); const row = rows[0];
    const query = { canonical_event_id: row.canonical_event_id, canonical_bookmaker_id: row.canonical_bookmaker_id, canonical_selection_id: row.canonical_selection_id, period: row.period, market_type: row.market_type, line: row.line };
    assert.equal(latestAsOf(rows, { ...query, decision_time: '2026-08-27T13:31:49Z' }), null); assert.equal(latestAsOf(rows, { ...query, decision_time: '2026-08-27T13:31:50Z' }).observation_id, row.observation_id);
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
        allocationAuthority: registry.allocationAuthority,
        events: [
            {
                kind: 'event',
                provider: 'the-odds-api',
                provider_id: 'epl-fixture-001',
                canonical_id: registry.resolve('event', 'the-odds-api', 'epl-fixture-001').canonical_id,
                season: '2026/2027',
                home_team: 'Arsenal',
                away_team: 'Chelsea',
                kickoff_utc: '2026-09-12T15:00:00Z',
                provider_observed_kickoff_utc: '2026-09-12T15:00:00Z',
                identity_decision_id: registry.resolve('event', 'the-odds-api', 'epl-fixture-001').identity_decision_id,
                identity_decision_status: 'MATCHED',
                identity_ruleset_version: 'fixture-identity-ruleset/v1',
                provenance: 'fixture-v2',
            },
        ],
        bookmakers: registry.list('bookmaker', 'the-odds-api'),
        markets: registry.list('market', 'the-odds-api'),
        selections: registry.list('selection', 'the-odds-api'),
    });
    const v2 = adaptTheOddsApiRaw({ rawText, capture, registry: v2Registry, decisionLedger, projectionVersion: '1' });
    assert.notEqual(v1[0].observation_id, v2[0].observation_id);
});

test('adapter fails closed for malformed or incomplete EPL market payloads and side conflicts', () => {
    const payload = JSON.parse(rawText);
    assert.throws(
        () =>
            adaptTheOddsApiRaw({
                rawText,
                capture: { ...capture, provider: undefined },
                registry,
                projectionVersion: '1',
            }),
        /capture provider must be the-odds-api/
    );
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
    const swappedSelectionRegistry = createIdentityRegistry({
        version: 'selection-swap/v1',
        allocationAuthority: registry.allocationAuthority,
        events: registry.list('event', 'the-odds-api'),
        bookmakers: registry.list('bookmaker', 'the-odds-api'),
        markets: registry.list('market', 'the-odds-api'),
        selections: [
            {
                kind: 'selection', provider: 'the-odds-api', provider_id: 'Arsenal', provenance: 'fixture',
                canonical_id: 'AWAY',
                selection: 'AWAY',
            },
            registry.resolve('selection', 'the-odds-api', 'Draw'),
            {
                kind: 'selection', provider: 'the-odds-api', provider_id: 'Chelsea', provenance: 'fixture',
                canonical_id: 'HOME',
                selection: 'HOME',
            },
        ],
    });
    assert.throws(
        () => adaptTheOddsApiRaw({ rawText, capture, registry: swappedSelectionRegistry, decisionLedger, projectionVersion: '1' }),
        /provider selection identity conflicts with event identity/
    );
    const duplicateEvent = JSON.parse(rawText);
    duplicateEvent.push(duplicateEvent[0]);
    assert.throws(
        () =>
            adaptTheOddsApiRaw({
                rawText: JSON.stringify(duplicateEvent),
                capture: captureForRaw(JSON.stringify(duplicateEvent)),
                registry,
                projectionVersion: '1',
            }),
        /duplicate provider event identity/
    );
    const duplicateBookmaker = JSON.parse(rawText);
    duplicateBookmaker[0].bookmakers.push({ ...duplicateBookmaker[0].bookmakers[0] });
    assert.throws(
        () =>
            adaptTheOddsApiRaw({
                rawText: JSON.stringify(duplicateBookmaker),
                capture: captureForRaw(JSON.stringify(duplicateBookmaker)),
                registry,
                projectionVersion: '1',
            }),
        /duplicate provider bookmaker identity/
    );
    const duplicateMarket = JSON.parse(rawText);
    duplicateMarket[0].bookmakers[0].markets.push({ ...duplicateMarket[0].bookmakers[0].markets[0] });
    assert.throws(
        () =>
            adaptTheOddsApiRaw({
                rawText: JSON.stringify(duplicateMarket),
                capture: captureForRaw(JSON.stringify(duplicateMarket)),
                registry,
                projectionVersion: '1',
            }),
        /duplicate provider market identity/
    );
});

test('UTC contract rejects calendar-invalid timestamps instead of Date.parse normalization', () => {
    const sample = observations()[0];
    assert.throws(() => createObservation({ ...sample, kickoff_utc: '2026-02-30T00:00:00Z' }), /UTC ISO-8601/);
});

test('canonical observations require governed identity decision and ruleset', () => {
    const sample = observations()[0];
    for (const field of ['identity_decision_id', 'identity_ruleset_version']) {
        assert.throws(() => createObservation({ ...sample, [field]: undefined }), new RegExp(`${field} is required`));
        assert.throws(() => createObservation({ ...sample, [field]: null }), new RegExp(`${field} is required`));
    }
    const root = fs.mkdtempSync(path.join(os.tmpdir(), 'stage-c-identity-ledger-'));
    try {
        for (const field of ['identity_decision_id', 'identity_ruleset_version']) {
            assert.throws(() => appendProjection({ ledgerPath: path.join(root, 'ledger.jsonl'), projection: { ...sample, [field]: null }, registry }), /invalid MarketObservation/);
        }
        assert.throws(() => appendProjection({ ledgerPath: path.join(root, 'ledger.jsonl'), projection: { ...sample, identity_decision_id: 'forged-decision' }, registry }), /valid MATCHED registry decision/);
        assert.throws(() => appendProjection({ ledgerPath: path.join(root, 'ledger.jsonl'), projection: { ...sample, identity_registry_sha256: 'f'.repeat(64) }, registry }), /valid MATCHED registry decision/);
        assert.throws(() => appendProjection({ ledgerPath: path.join(root, 'ledger.jsonl'), projection: { ...sample, home_team: 'Forged Home' }, registry }), /valid MATCHED registry decision/);
        assert.throws(() => appendProjection({ ledgerPath: path.join(root, 'ledger.jsonl'), projection: { ...sample, provider_bookmaker_id: 'forged-bookmaker' }, registry }), /identity mapping unknown/);
    } finally {
        fs.rmSync(root, { recursive: true, force: true });
    }
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
    assert.throws(() =>
        createCaptureReceipt({
            ...receipt,
            provider_endpoint_identity: 'api.the-odds-api.com/v4/sports/soccer_epl/odds/internal-secret-path',
        })
    );
    assert.throws(() => createCaptureReceipt({ ...receipt, provider: 'unapproved-provider' }), /identity/);
    assert.throws(() =>
        createCaptureReceipt({
            ...receipt,
            sanitized_request_parameters: { regions: 'private-token', markets: 'h2h' },
        })
    );
    assert.throws(
        () =>
            readImmutableRaw({
                rawEvidenceReference: evidence.raw_evidence_reference,
                expectedSha256: evidence.raw_sha256,
            }),
        /evidence root is required/
    );
});

test('coverage evidence explicitly records observed and missing provider bookmaker coverage', t => {
    const expected = ['williamhill', 'pinnacle', 'betfair_exchange'];
    const evidence = buildCoverageEvidence({ rawText, expectedProviderBookmakerIds: expected });
    assert.equal(evidence.status, 'PARTIAL');
    assert.deepEqual(evidence.missing_expected_provider_bookmaker_ids, ['betfair_exchange', 'pinnacle']);
    const missingMarketPayload = JSON.parse(rawText);
    missingMarketPayload[0].bookmakers[0].markets = [];
    const missingMarketEvidence = buildCoverageEvidence({
        rawText: JSON.stringify(missingMarketPayload),
        expectedProviderBookmakerIds: ['williamhill'],
    });
    assert.equal(missingMarketEvidence.status, 'PARTIAL');
    assert.equal(missingMarketEvidence.reason, 'EXPECTED_MARKET_NOT_OBSERVED');
    assert.deepEqual(missingMarketEvidence.missing_expected_provider_market_bookmaker_ids, ['williamhill']);
    const nonEplPayload = JSON.parse(rawText);
    nonEplPayload[0].sport_key = 'soccer_fa_cup';
    const nonEplEvidence = buildCoverageEvidence({
        rawText: JSON.stringify(nonEplPayload),
        expectedProviderBookmakerIds: ['williamhill'],
    });
    assert.equal(nonEplEvidence.status, 'PARTIAL');
    assert.deepEqual(nonEplEvidence.missing_expected_provider_bookmaker_ids, ['williamhill']);
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

test('documented Stage C replay audit hash is recomputed from the committed fixture', () => {
    const replayHash = sha256Text(stableStringify(observations('1').map(semanticProjection)));
    const document = fs.readFileSync(path.join(__dirname, '../../../docs/data/STAGE_C_CANONICAL_MARKET_EVIDENCE_PILOT.md'), 'utf8');
    assert.match(replayHash, /^[a-f0-9]{64}$/);
    assert.match(document, /governed identity registry/);
});

test('offline replay reads immutable raw and can append projections without network access', t => {
    const root = fs.mkdtempSync(path.join(os.tmpdir(), 'stage-c-replay-'));
    t.after(() => fs.rmSync(root, { recursive: true, force: true }));
    const rawPath = path.join(root, 'capture.json');
    fs.writeFileSync(rawPath, rawText, 'utf8');
    fs.chmodSync(rawPath, 0o444);
    const ledgerPath = path.join(root, 'ledger.jsonl');
    const replayed = replayRaw({ rawPath, capture, registry, projectionVersion: '1', projectionAvailableAt: capture.ingested_at, ledgerPath });
    const replayedAgain = replayRaw({ rawPath, capture, registry, projectionVersion: '1', projectionAvailableAt: capture.ingested_at });
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
                projectionAvailableAt: capture.ingested_at,
            }),
        /does not match replay input/
    );
});

test('append-only ledger preserves old projections and appends new versions', t => {
    const root = fs.mkdtempSync(path.join(os.tmpdir(), 'stage-c-ledger-'));
    t.after(() => fs.rmSync(root, { recursive: true, force: true }));
    const ledger = path.join(root, 'ledger.jsonl');
    appendProjection({ ledgerPath: ledger, projection: observations('1')[0], registry });
    assert.equal(fs.statSync(ledger).mode & 0o222, 0);
    assert.equal(fs.statSync(ledgerManifestPath(ledger)).mode & 0o222, 0);
    appendProjection({ ledgerPath: ledger, projection: observations('2')[0], registry });
    assert.throws(
        () => appendProjection({ ledgerPath: ledger, projection: { foo: 'bar' }, registry }),
        /invalid MarketObservation/
    );
    const rows = fs.readFileSync(ledger, 'utf8').trim().split('\n').map(JSON.parse);
    assert.deepEqual(
        rows.map(row => row.projection_version),
        ['1', '2']
    );
    assert.equal(readProjectionLedger({ ledgerPath: ledger }).length, 2);
    fs.chmodSync(ledger, 0o644);
    fs.appendFileSync(ledger, '\n');
    fs.chmodSync(ledger, 0o444);
    assert.throws(() => readProjectionLedger({ ledgerPath: ledger }), /integrity/);
    assert.throws(() => appendProjection({ ledgerPath: ledger, projection: observations('2')[1], registry }), /integrity/);
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
    const lateIngestion = {
        ...row,
        response_received_at: '2026-08-27T13:31:49Z',
        ingested_at: '2026-08-27T13:40:00Z',
    };
    assert.equal(latestAsOf([lateIngestion], { ...query, decision_time: '2026-08-27T13:35:00Z' }), null);
    assert.equal(
        latestAsOf([lateIngestion], { ...query, decision_time: '2026-08-27T13:40:00Z' }).observation_id,
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

test('as-of projection selection is explicit and later reprojection cannot rewrite historical selection', () => {
    const v1 = observations('1')[0];
    const v2 = { ...observations('2')[0], odds_decimal: 9.99 };
    const query = {
        canonical_event_id: v1.canonical_event_id,
        canonical_bookmaker_id: v1.canonical_bookmaker_id,
        canonical_selection_id: v1.canonical_selection_id,
        period: v1.period,
        market_type: v1.market_type,
        line: v1.line,
        decision_time: '2026-08-27T13:31:50Z',
    };
    const futureV2 = { ...v2, projection_available_at: '2026-08-28T13:31:49Z' };
    assert.equal(latestAsOf([v1, futureV2], query).odds_decimal, v1.odds_decimal, 'a later-known reprojection cannot alter the past as-of result');
    assert.throws(() => latestAsOf([v1, v2], query), /projection_version is required/);
    assert.equal(latestAsOf([v1, v2], { ...query, projection_version: '1' }).odds_decimal, v1.odds_decimal);
    assert.equal(latestAsOf([v1, v2], { ...query, projection_version: '2' }).odds_decimal, 9.99);
    const forgedSameVersion = { ...v1, observation_id: `${v1.observation_id}-forged`, odds_decimal: 9.99, identity_registry_sha256: 'f'.repeat(64) };
    assert.throws(() => latestAsOf([v1, forgedSameVersion], { ...query, projection_version: '1' }), /governance boundary is ambiguous/);
});

test('same raw acquisition preserves two independent immutable receipts', t => {
    const root = fs.mkdtempSync(path.join(os.tmpdir(), 'stage-c-two-receipts-'));
    t.after(() => fs.rmSync(root, { recursive: true, force: true }));
    const raw = writeImmutableRaw({ rootDir: root, rawText });
    const receiptBase = {
        ...capture,
        provider: 'the-odds-api',
        http_status: 200,
        sanitized_request_parameters: { regions: 'uk', markets: 'h2h' },
        response_size_bytes: Buffer.byteLength(rawText),
        raw_sha256: raw.raw_sha256,
        raw_evidence_reference: raw.raw_evidence_reference,
    };
    const first = createCaptureReceipt({ ...receiptBase, capture_id: 'acquisition-001' });
    const second = createCaptureReceipt({ ...receiptBase, capture_id: 'acquisition-002', request_started_at: '2026-08-27T13:32:20Z', response_received_at: '2026-08-27T13:32:49Z', ingested_at: '2026-08-27T13:32:49Z' });
    writeReceipt({ rootDir: root, receipt: first });
    writeReceipt({ rootDir: root, receipt: second });
    assert.equal(fs.readdirSync(path.join(root, 'raw')).length, 1);
    assert.deepEqual(fs.readdirSync(path.join(root, 'receipts')).sort(), ['acquisition-001.json', 'acquisition-002.json']);
});

test('live client is key-gated and bounded to three requests without logging secrets', async () => {
    const previous = process.env.THE_ODDS_API_KEY;
    try {
        // Keep the key absent for the key-gating assertion even when the test
        // process was launched with a real or otherwise pre-existing key.
        delete process.env.THE_ODDS_API_KEY;
        const { buildRequestUrl } = require('../../../src/infrastructure/market_evidence/theOddsApiClient');
        assert.throws(() => buildRequestUrl(), /required/);
        process.env.THE_ODDS_API_KEY = 'test-only-not-persisted';
        assert.throws(() => buildRequestUrl({ markets: 'totals' }), /only permits/);
        assert.throws(() => buildRequestUrl({ regions: 'credential-token' }), /unsupported region/);
        delete process.env.THE_ODDS_API_KEY;
        const client = createTheOddsApiClient({
            requestFn: () => {
                throw new Error('network should be stubbed in this test');
            },
        });
        assert.equal(client.request_count, 0);
        assert.throws(() => client.capture(), /required/);
        assert.equal(client.request_count, 0);
    } finally {
        if (previous !== undefined) process.env.THE_ODDS_API_KEY = previous;
        else delete process.env.THE_ODDS_API_KEY;
    }
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

test('The Odds API client defaults to native DIRECT HTTPS without proxy selection or proxy environment use', async t => {
    const previous = process.env.THE_ODDS_API_KEY;
    const previousProxy = process.env.ALL_PROXY;
    process.env.THE_ODDS_API_KEY = 'test-only-not-persisted';
    process.env.ALL_PROXY = 'socks5://proxy.invalid:1080';
    t.after(() => {
        if (previous === undefined) delete process.env.THE_ODDS_API_KEY;
        else process.env.THE_ODDS_API_KEY = previous;
        if (previousProxy === undefined) delete process.env.ALL_PROXY;
        else process.env.ALL_PROXY = previousProxy;
    });
    const requests = [];
    class NativeAgent {
        constructor(options) {
            this.options = options;
        }
    }
    const requestFn = createDirectRequestFn({
        httpsModule: {
            Agent: NativeAgent,
            request(options, callback) {
                requests.push(options);
                const response = new EventEmitter();
                response.statusCode = 200;
                response.headers = {};
                process.nextTick(() => {
                    callback(response);
                    response.emit('data', Buffer.from(rawText));
                    response.emit('end');
                });
                const request = new EventEmitter();
                request.setTimeout = () => {};
                return request;
            },
        },
    });
    const client = createTheOddsApiClient({ requestFn });
    const result = await client.capture();
    assert.equal(result.http_status, 200);
    assert.equal(requests.length, 1);
    assert.equal(requests[0].hostname, 'api.the-odds-api.com');
    assert.equal(requests[0].port, 443);
    assert.equal(requests[0].agent instanceof NativeAgent, true);
    assert.equal(requests[0].agent.options.keepAlive, false);
    assert.equal(Object.hasOwn(requests[0], 'proxy'), false);
    assert.doesNotMatch(require('node:fs').readFileSync(
        require.resolve('../../../src/infrastructure/market_evidence/theOddsApiClient'), 'utf8'
    ), /ProxyProvider|SocksProxyAgent|HTTPS_PROXY|ALL_PROXY/);
});

test('non-200 direct responses and network failures do not create live RAW payloads', async t => {
    const previous = process.env.THE_ODDS_API_KEY;
    process.env.THE_ODDS_API_KEY = 'test-only-not-persisted';
    t.after(() => {
        if (previous === undefined) delete process.env.THE_ODDS_API_KEY;
        else process.env.THE_ODDS_API_KEY = previous;
    });
    const non200Client = createTheOddsApiClient({
        requestFn: (_url, _options, callback) => {
            const response = new EventEmitter();
            response.statusCode = 503;
            response.headers = {};
            process.nextTick(() => {
                callback(response);
                response.emit('data', Buffer.from('{"error":"unavailable"}'));
                response.emit('end');
            });
            return new EventEmitter();
        },
    });
    await assert.rejects(non200Client.capture(), error => error.http_status === 503 && !Object.hasOwn(error, 'rawText'));
    const networkClient = createTheOddsApiClient({
        requestFn: () => {
            const request = new EventEmitter();
            process.nextTick(() => request.emit('error', Object.assign(new Error('secret-free failure'), { code: 'ECONNRESET' })));
            return request;
        },
    });
    await assert.rejects(networkClient.capture(), /ECONNRESET/);
});

test('stable_proxy uses only its configured fixed agent and fails closed without a proxy URL', async () => {
    const stableAgent = { stable: true };
    // The transport receives an injected configuration value.  This is a
    // non-routable documentation host, not a hard-coded localhost proxy.
    const proxyConfiguration = new URL('http://stable-proxy.invalid:7897');
    const requestFn = createStableProxyRequestFn({ proxyUrl: proxyConfiguration.toString(), agent: stableAgent });
    const originalRequest = require('node:https').request;
    let receivedOptions;
    require('node:https').request = (options, callback) => {
        receivedOptions = options;
        const response = new EventEmitter();
        response.statusCode = 204;
        response.headers = {};
        process.nextTick(() => callback(response));
        const request = new EventEmitter();
        request.setTimeout = () => {};
        return request;
    };
    try {
        requestFn('https://api.the-odds-api.com/', { headers: {} }, () => {});
    } finally {
        require('node:https').request = originalRequest;
    }
    assert.equal(receivedOptions.agent, stableAgent);
    assert.equal(receivedOptions.rejectUnauthorized, true);
    assert.equal(resolveTransportPolicy('stable_proxy'), 'STABLE_PROXY');
    assert.equal(resolveTransportPolicy('direct'), 'DIRECT');
    assert.throws(() => createStableProxyRequestFn({ proxyUrl: '' }), /must be an HTTP\(S\) proxy URL/);
    assert.throws(() => resolveTransportPolicy('rotating_proxy_pool'), /direct or stable_proxy/);
});
