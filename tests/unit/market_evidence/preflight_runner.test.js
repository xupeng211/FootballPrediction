'use strict';

const assert = require('node:assert/strict');
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const test = require('node:test');
const { sha256Text } = require('../../../src/infrastructure/market_evidence/contracts');
const {
    MAX_PROVIDER_REQUESTS,
    preparePreflight,
    executePreparedPreflight,
} = require('../../../src/infrastructure/market_evidence/preflightRunner');
const { seedFotMobFixtureUniverse } = require('../../../src/infrastructure/fixture_universe/FixtureUniverse');
const {
    persistVerifiedAllocationAuthority,
} = require('../../../src/infrastructure/fixture_universe/AllocationAuthorityArtifact');
const {
    bootstrapMarketEvidenceTransactionStore,
} = require('../../../src/infrastructure/market_evidence/transactionStore');
const { openMarketEvidenceAuthoritySnapshot } = require('../../../src/infrastructure/market_evidence/authorityReader');
const {
    buildProspectiveMarketEvidenceTransaction,
} = require('../../../src/infrastructure/market_evidence/prospectiveBatch');
const {
    publishProspectiveMarketEvidenceTransaction,
} = require('../../../src/infrastructure/market_evidence/atomicPublisher');
const { loadVerifiedCaptureReceipt } = require('../../../src/infrastructure/market_evidence/evidenceStore');

const payload = JSON.stringify([
    {
        id: 'epl-fixture-001',
        sport_key: 'soccer_epl',
        commence_time: '2026-09-12T15:00:00Z',
        home_team: 'Arsenal',
        away_team: 'Chelsea',
        bookmakers: [
            {
                key: 'williamhill',
                title: 'William Hill',
                markets: [
                    {
                        key: 'h2h',
                        last_update: '2026-08-27T13:31:22Z',
                        outcomes: [
                            { name: 'Arsenal', price: 2.1 },
                            { name: 'Draw', price: 3.4 },
                            { name: 'Chelsea', price: 3.6 },
                        ],
                    },
                ],
            },
        ],
    },
]);
function root(t) {
    const target = fs.mkdtempSync(path.join(os.tmpdir(), 'preflight-runner-'));
    t.after(() => fs.rmSync(target, { recursive: true, force: true }));
    return target;
}
function prepare(t, extra = {}) {
    return preparePreflight({
        rootDir: path.join(root(t), 'missing-at-start'),
        requestMetadata: { regions: 'uk', markets: 'h2h', oddsFormat: 'decimal' },
        credentialPresent: true,
        ...extra,
    });
}
const response = status => ({
    status,
    headers: { 'x-requests-last': '1', 'x-requests-remaining': '499', authorization: 'discard' },
    body: payload,
    receivedAt: '2020-09-06T00:00:00Z',
});

test('first failure regression: absent root is prepared and probed before transport', async t => {
    const prepared = prepare(t);
    let calls = 0;
    const result = await executePreparedPreflight({
        prepared,
        captureId: 'case-a',
        now: () => '2020-09-06T00:00:00Z',
        transport: async () => {
            calls += 1;
            assert.equal(fs.existsSync(prepared.root), true);
            assert.equal(fs.existsSync(path.join(prepared.root, 'raw')), true);
            return response(200);
        },
    });
    assert.equal(calls, 1);
    assert.equal(result.transport_calls, 1);
    assert.equal(fs.existsSync(result.persisted.rawPath), true);
    assert.equal(fs.statSync(result.persisted.rawPath).mode & 0o222, 0);
    assert.equal(sha256Text(fs.readFileSync(result.persisted.rawPath, 'utf8')), result.receipt.raw_sha256);
});
test('root preparation failure blocks transport', t => {
    let calls = 0;
    assert.throws(() =>
        preparePreflight({
            rootDir: '/dev/null/preflight',
            requestMetadata: { regions: 'uk', markets: 'h2h', oddsFormat: 'decimal' },
            credentialPresent: true,
        })
    );
    assert.equal(calls, 0);
});
test('prepared context is single-use and unsafe metadata is rejected before transport', async t => {
    const prepared = prepare(t);
    let calls = 0;
    await executePreparedPreflight({
        prepared,
        captureId: 'once',
        now: () => '2020-09-06T00:00:00Z',
        transport: async () => {
            calls += 1;
            return response(200);
        },
    });
    await assert.rejects(
        () =>
            executePreparedPreflight({
                prepared,
                captureId: 'twice',
                transport: async () => {
                    calls += 1;
                    return response(200);
                },
            }),
        /reused preparation/
    );
    assert.equal(calls, 1);
    assert.throws(
        () =>
            preparePreflight({
                rootDir: path.join(root(t), 'unsafe'),
                requestMetadata: { apiKey: 'forbidden' },
                credentialPresent: true,
            }),
        /unsupported request parameter/
    );
});
test('429, 500 and timeout use one transport call and never retry', async t => {
    for (const scenario of ['429', '500', 'timeout']) {
        const prepared = prepare(t);
        let calls = 0;
        const transport =
            scenario === 'timeout'
                ? async () => {
                      calls += 1;
                      throw new Error('timeout');
                  }
                : async () => {
                      calls += 1;
                      return response(Number(scenario));
                  };
        await assert.rejects(
            () => executePreparedPreflight({ prepared, captureId: `case-${scenario}`, transport }),
            /HTTP|timeout/
        );
        assert.equal(calls, MAX_PROVIDER_REQUESTS);
    }
});
test('durable raw and receipt precede downstream adapter callback', async t => {
    const prepared = prepare(t);
    const result = await executePreparedPreflight({
        prepared,
        captureId: 'case-d',
        now: () => '2020-09-06T00:00:00Z',
        transport: async () => response(200),
        downstream: ({ rawPath, receiptPath }) => {
            assert.equal(fs.existsSync(rawPath), true);
            assert.equal(fs.existsSync(receiptPath), true);
            return { adapter_reads_persisted_raw: JSON.parse(fs.readFileSync(rawPath, 'utf8')).length };
        },
    });
    assert.deepEqual(result.downstreamResult, { adapter_reads_persisted_raw: 1 });
});
test('malformed provider JSON remains durably captured when downstream parsing fails', async t => {
    const prepared = prepare(t);
    let rawPath = null;
    await assert.rejects(
        () =>
            executePreparedPreflight({
                prepared,
                captureId: 'case-malformed',
                now: () => '2020-09-06T00:00:00Z',
                transport: async () => ({ ...response(200), body: '{malformed' }),
                downstream: ({ rawPath: target }) => {
                    rawPath = target;
                    JSON.parse(fs.readFileSync(target, 'utf8'));
                },
            }),
        /JSON/
    );
    assert.equal(fs.existsSync(rawPath), true);
    assert.equal(fs.statSync(rawPath).mode & 0o222, 0);
});
test('offline dry run publishes the canonical transaction from persisted synthetic RAW', async t => {
    const prepared = prepare(t);
    const fixtureRoot = root(t);
    const matches = Array.from({ length: 380 }, (_, index) => ({
        id: String(800000 + index),
        home: { name: index ? `Home ${index}` : 'Arsenal' },
        away: { name: index ? `Away ${index}` : 'Chelsea' },
        status: {
            utcTime: index ? `2026-10-${String((index % 28) + 1).padStart(2, '0')}T15:00:00Z` : '2026-09-12T15:00:00Z',
        },
    }));
    const fixtureRaw = `<script id="__NEXT_DATA__" type="application/json">${JSON.stringify({ query: { season: '2026/2027' }, props: { pageProps: { details: { id: 47 }, fixtures: { allMatches: matches } } } })}</script>`;
    const initial = seedFotMobFixtureUniverse({
        rawHtml: fixtureRaw,
        rawSha256: sha256Text(fixtureRaw),
        mode: 'INITIAL_SEED',
    });
    const allocationPath = path.join(fixtureRoot, 'allocation.json');
    const persistedAllocation = persistVerifiedAllocationAuthority({
        artifactPath: allocationPath,
        allocationAuthority: initial.allocationAuthority,
    });
    const universe = seedFotMobFixtureUniverse({
        rawHtml: fixtureRaw,
        rawSha256: sha256Text(fixtureRaw),
        allocation: persistedAllocation.allocationSnapshot,
        allocationAuthority: persistedAllocation.allocationAuthority,
        mode: 'REPLAY',
    });
    const storeRoot = path.join(fixtureRoot, 'transactions');
    bootstrapMarketEvidenceTransactionStore({
        storeRoot,
        allocationArtifactPath: allocationPath,
        bootstrapMetadata: { test: 'offline-preflight' },
    });
    const result = await executePreparedPreflight({
        prepared,
        captureId: 'case-canonical',
        now: () => '2020-09-06T00:00:00Z',
        transport: async () => response(200),
        downstream: ({ rawPath, receiptPath }) => {
            const candidate = buildProspectiveMarketEvidenceTransaction({
                authoritySnapshot: openMarketEvidenceAuthoritySnapshot({
                    storeRoot,
                    allocationArtifactPath: allocationPath,
                }),
                universe,
                oddsRawText: fs.readFileSync(rawPath, 'utf8'),
                captureReceipt: loadVerifiedCaptureReceipt({ receiptPath }),
            });
            return publishProspectiveMarketEvidenceTransaction({
                storeRoot,
                allocationArtifactPath: allocationPath,
                candidate,
            });
        },
    });
    assert.equal(result.downstreamResult.snapshot.observations.length, 3);
});
