'use strict';

const assert = require('node:assert/strict');
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const test = require('node:test');
const { seedFotMobFixtureUniverse, resolveOddsEvents } = require('../../../src/infrastructure/fixture_universe/FixtureUniverse');
const { createIdentityRegistry } = require('../../../src/infrastructure/market_evidence/identityRegistry');
const { createIdentityDecisionLedger } = require('../../../src/infrastructure/fixture_universe/IdentityDecisionLedger');
const { adaptTheOddsApiRaw } = require('../../../src/infrastructure/market_evidence/theOddsApiAdapter');
const { appendProjection, writeImmutableRaw } = require('../../../src/infrastructure/market_evidence/evidenceStore');
const { replayRaw } = require('../../../src/infrastructure/market_evidence/replay');
const { sha256Text } = require('../../../src/infrastructure/market_evidence/contracts');

function universe() {
    const allMatches = Array.from({ length: 380 }, (_, index) => ({ id: String(700000 + index), home: { name: index ? `Home ${index}` : 'Arsenal' }, away: { name: index ? `Away ${index}` : 'Chelsea' }, status: { utcTime: index ? `2026-10-${String((index % 28) + 1).padStart(2, '0')}T15:00:00Z` : '2026-09-12T15:00:00Z' } }));
    const raw = `<script id="__NEXT_DATA__" type="application/json">${JSON.stringify({ query: { season: '2026/2027' }, props: { pageProps: { details: { id: 47 }, fixtures: { allMatches } } } })}</script>`;
    let n = 0;
    return seedFotMobFixtureUniverse({ rawHtml: raw, rawSha256: sha256Text(raw), mode: 'INITIAL_SEED', allocate: prefix => `${prefix}_${String(++n).padStart(6, '0')}` });
}
function capture(raw) { return { capture_id: 'trust-root', provider: 'the-odds-api', acquisition_mode: 'HISTORICAL_FILE', request_started_at: '2026-08-27T13:31:20Z', response_received_at: '2026-08-27T13:31:49Z', ingested_at: '2026-08-27T13:31:49Z', raw_evidence_reference: 'raw/trust-root.json', raw_sha256: sha256Text(raw) }; }

test('canonical authority has no caller-controlled allocation or ledger path', t => {
    const root = fs.mkdtempSync(path.join(os.tmpdir(), 'stage-c-trust-')); t.after(() => fs.rmSync(root, { recursive: true, force: true }));
    const u = universe(); const event = { id: 'real-event', sport_key: 'soccer_epl', home_team: 'Arsenal', away_team: 'Chelsea', commence_time: '2026-09-12T15:00:00Z', bookmakers: [{ key: 'book', title: 'Book', markets: [{ key: 'h2h', outcomes: [{ name: 'Arsenal', price: 2 }, { name: 'Draw', price: 3 }, { name: 'Chelsea', price: 4 }] }] }] }; const raw = JSON.stringify([event]);
    const ledger = createIdentityDecisionLedger({ ledgerPath: path.join(root, 'identity.jsonl') });
    const resolution = resolveOddsEvents({ oddsRawText: raw, oddsRawSha256: sha256Text(raw), universe: u, decidedAt: capture(raw).ingested_at, decisionLedger: ledger });
    const admitted = adaptTheOddsApiRaw({ rawText: raw, capture: capture(raw), registry: resolution.registry, decisionLedger: ledger, projectionVersion: '1' });
    assert.ok(admitted.length > 0);
    assert.throws(() => createIdentityRegistry({ version: 'forged', governed_event_ids: ['evt_toaprovider123'], events: [] }), /unknown identity registry field/);
    assert.throws(() => createIdentityRegistry({ version: 'forged', allocation_hash: 'a'.repeat(64), events: [] }), /unknown identity registry field/);
    assert.throws(() => createIdentityRegistry({ version: 'forged', allocation_snapshot: { authority: 'FootballPrediction' }, events: [] }), /unknown identity registry field/);
    assert.deepEqual(adaptTheOddsApiRaw({ rawText: raw, capture: capture(raw), registry: resolution.registry, projectionVersion: '1' }), admitted);
    assert.equal(appendProjection({ ledgerPath: path.join(root, 'observations.jsonl'), projection: admitted[0], registry: resolution.registry }).observation_id, admitted[0].observation_id);
    const rawReceipt = writeImmutableRaw({ rootDir: root, captureId: 'trust-root', rawText: raw });
    const rawPath = path.join(root, rawReceipt.raw_evidence_reference);
    assert.deepEqual(replayRaw({ rawPath, capture: capture(raw), registry: resolution.registry, projectionAvailableAt: capture(raw).ingested_at }), admitted);
    assert.throws(() => ledger.append({ ...resolution.decisions[0] }), /not produced/);
    assert.throws(() => ledger.assertActiveMatched({ provider: 'wrong', providerEventId: event.id, canonicalEventId: resolution.aliases[0].canonical_event_id, decisionId: resolution.decisions[0].identity_decision_id, rulesetVersion: resolution.decisions[0].ruleset_version, resolverVersion: resolution.decisions[0].resolver_version }), /exact active/);
});
