'use strict';

const assert = require('node:assert/strict');
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const test = require('node:test');
const { seedFotMobFixtureUniverse, resolveOddsEventsProspectively } = require('../../../src/infrastructure/fixture_universe/FixtureUniverse');
const { persistVerifiedAllocationAuthority } = require('../../../src/infrastructure/fixture_universe/AllocationAuthorityArtifact');
const { sha256Text } = require('../../../src/infrastructure/market_evidence/contracts');
const { bootstrapMarketEvidenceTransactionStore } = require('../../../src/infrastructure/market_evidence/transactionStore');
const { openMarketEvidenceAuthoritySnapshot } = require('../../../src/infrastructure/market_evidence/authorityReader');
const { latestAsOf } = require('../../../src/infrastructure/market_evidence/asOfView');
const { createCommittedMarker, canonicalBytes, descriptorForBytes, createManifest, computeAuthorityStateHash, hashCanonical } = require('../../../src/infrastructure/market_evidence/transactionContract');
const { buildProspectiveMarketEvidenceTransaction, finalizeProspectiveMarketEvidenceTransactionForPublication, snapshotPlainData } = require('../../../src/infrastructure/market_evidence/prospectiveBatch');
const { publishProspectiveMarketEvidenceTransaction } = require('../../../src/infrastructure/market_evidence/atomicPublisher');
const { adaptTheOddsApiRaw } = require('../../../src/infrastructure/market_evidence/theOddsApiAdapter');
const { projectIdentityDecisionState } = require('../../../src/infrastructure/fixture_universe/IdentityDecisionLedger');
const { createVerifiedTestReceipt } = require('../../helpers/market_evidence_authority');

const hash = value => sha256Text(value);
function fotmobRaw() {
    const allMatches = Array.from({ length: 380 }, (_, i) => ({ id: String(810000 + i), home: { name: i ? `Home ${i}` : 'Arsenal' }, away: { name: i ? `Away ${i}` : 'Chelsea' }, status: { utcTime: i ? `2026-10-${String((i % 28) + 1).padStart(2, '0')}T15:00:00Z` : '2026-09-12T15:00:00Z' } }));
    return `<script id="__NEXT_DATA__" type="application/json">${JSON.stringify({ query: { season: '2026/2027' }, props: { pageProps: { details: { id: 47 }, fixtures: { allMatches } } } })}</script>`;
}
function setup(t) {
    const root = fs.mkdtempSync(path.join(os.tmpdir(), 'prospective-v1-')); t.after(() => fs.rmSync(root, { recursive: true, force: true }));
    const raw = fotmobRaw(); const initial = seedFotMobFixtureUniverse({ rawHtml: raw, rawSha256: hash(raw), manifest: { raw_file_relative_path: 'fixture.html' }, mode: 'INITIAL_SEED' });
    const allocationPath = path.join(root, 'allocation.json'); const persisted = persistVerifiedAllocationAuthority({ artifactPath: allocationPath, allocationAuthority: initial.allocationAuthority });
    const universe = seedFotMobFixtureUniverse({ rawHtml: raw, rawSha256: hash(raw), allocation: persisted.allocationSnapshot, allocationAuthority: persisted.allocationAuthority, manifest: { raw_file_relative_path: 'fixture.html' }, mode: 'REPLAY' });
    const storeRoot = path.join(root, 'market_evidence_transactions'); bootstrapMarketEvidenceTransactionStore({ storeRoot, allocationArtifactPath: allocationPath, bootstrapMetadata: { fixture: 'prospective-v1' } });
    return { root, universe, allocationPath, storeRoot, snapshot: () => openMarketEvidenceAuthoritySnapshot({ storeRoot, allocationArtifactPath: allocationPath }) };
}
function rawEvent(index, id, { price = 2, home = null, away = null, kickoff = null } = {}) {
    const defaults = index ? { home: `Home ${index}`, away: `Away ${index}`, kickoff: `2026-10-${String((index % 28) + 1).padStart(2, '0')}T15:00:00Z` } : { home: 'Arsenal', away: 'Chelsea', kickoff: '2026-09-12T15:00:00Z' };
    return { id, sport_key: 'soccer_epl', home_team: home || defaults.home, away_team: away || defaults.away, commence_time: kickoff || defaults.kickoff, bookmakers: [{ key: 'fixture-bookmaker', title: 'Fixture Bookmaker', markets: [{ key: 'h2h', outcomes: [{ name: home || defaults.home, price }, { name: 'Draw', price: 3 }, { name: away || defaults.away, price: 4 }] }] }] };
}
function input(ctx, events, receiptOverrides = {}) {
    const oddsRawText = JSON.stringify(events);
    const captureId = receiptOverrides.capture_id || 'capture-prospective-1';
    return { oddsRawText, captureReceipt: createVerifiedTestReceipt({ root: path.join(ctx.root, 'receipt-sources', `${captureId}-${hash(oddsRawText).slice(0, 8)}`), rawText: oddsRawText, overrides: { capture_id: captureId, ...receiptOverrides } }) };
}
function tree(root) {
    const rows = [];
    function visit(relative) {
        const target = path.join(root, relative); const stat = fs.lstatSync(target);
        if (stat.isDirectory()) { rows.push(`${relative || '.'}/`); for (const name of fs.readdirSync(target).sort()) visit(path.join(relative, name)); }
        else rows.push(`${relative}:${stat.isSymbolicLink() ? 'symlink' : hash(fs.readFileSync(target))}`);
    }
    visit(''); return rows;
}
function build(ctx, events, extra = {}) {
    const { receiptOverrides = {}, ...builderOptions } = extra;
    return buildProspectiveMarketEvidenceTransaction({ authoritySnapshot: ctx.snapshot(), universe: ctx.universe, ...input(ctx, events, receiptOverrides), ...builderOptions });
}
// Test-only fixture materialisation validates that a prospective candidate is
// consumable by the existing read-only authority contract. It is not a
// publisher and production code never calls it.
function materializeCandidate(ctx, candidate) {
    if (candidate.observations) {
        return publishProspectiveMarketEvidenceTransaction({ storeRoot: ctx.storeRoot, allocationArtifactPath: ctx.allocationPath, candidate });
    }
    const dir = path.join(ctx.storeRoot, 'committed', candidate.transaction_id); fs.mkdirSync(dir);
    for (const [file, bytes] of Object.entries(candidate.artifact_bytes)) fs.writeFileSync(path.join(dir, file), bytes);
    fs.writeFileSync(path.join(dir, 'manifest.json'), canonicalBytes(candidate.manifest));
    fs.writeFileSync(path.join(dir, 'COMMITTED'), canonicalBytes(createCommittedMarker(candidate.manifest)));
}
function materializeCandidateWithKnowledgeTime(ctx, candidate, knowledgeTime) {
    const manifest = createManifest({
        sequence: candidate.sequence,
        parent_transaction_id: candidate.parent_transaction_id,
        parent_transaction_content_hash: candidate.parent_transaction_content_hash,
        expected_parent_state_hash: candidate.expected_parent_state_hash,
        post_state_hash: candidate.post_state_hash,
        allocation: candidate.allocation,
        source: candidate.metadata.source,
        versions: candidate.manifest.versions,
        artifacts: candidate.artifacts,
        decision_count: candidate.decision_count,
        observation_count: candidate.observation_count,
        registry_delta_count: candidate.registry_delta_count,
        quarantine_count: candidate.quarantine_count,
        publication_metadata: { ...candidate.manifest.publication_metadata, knowledge_time: knowledgeTime },
    });
    const dir = path.join(ctx.storeRoot, 'committed', manifest.transaction_id); fs.mkdirSync(dir);
    for (const [file, bytes] of Object.entries(candidate.artifact_bytes)) fs.writeFileSync(path.join(dir, file), bytes);
    fs.writeFileSync(path.join(dir, 'manifest.json'), canonicalBytes(manifest));
    fs.writeFileSync(path.join(dir, 'COMMITTED'), canonicalBytes(createCommittedMarker(manifest)));
    return manifest;
}
test('PROSPECTIVE_VALID_BATCH_BUILDS_CANDIDATE with one coherent zero-write authority head', t => {
    const ctx = setup(t); const beforeTree = tree(ctx.storeRoot); const before = ctx.snapshot();
    const candidate = build(ctx, [rawEvent(0, 'event-0'), rawEvent(1, 'event-1')]); const after = ctx.snapshot();
    assert.equal(candidate.sequence, 1); assert.equal(candidate.identity_decisions.length, 2); assert.equal(candidate.observations.length, 6); assert.equal(candidate.decision_count, 2); assert.equal(candidate.observation_count, 6);
    assert.equal(candidate.parent_transaction_id, null); assert.equal(candidate.expected_parent_state_hash, before.state_hash); assert.equal(after.state_hash, before.state_hash);
    assert.deepEqual(tree(ctx.storeRoot), beforeTree, 'prospective build must not write STORE, committed, staging, legacy ledgers, or registry files');
    assert.equal(candidate.manifest.transaction_id, candidate.transaction_id); assert.equal(candidate.artifact_bytes['identity_decisions.jsonl'].includes('\n'), true);
});

test('IDENTICAL_PROSPECTIVE_REBUILD_DETERMINISTIC and caller input is snapshotted', t => {
    const ctx = setup(t); const events = [rawEvent(0, 'event-0'), rawEvent(1, 'event-1')]; const args = input(ctx, events);
    const first = buildProspectiveMarketEvidenceTransaction({ authoritySnapshot: ctx.snapshot(), universe: ctx.universe, ...args });
    assert.throws(() => { args.captureReceipt.capture_id = 'mutated-after-build'; }, /read only|extensible|assign/i); events[0].bookmakers[0].markets[0].outcomes[0].price = 999;
    const second = build(ctx, [rawEvent(0, 'event-0'), rawEvent(1, 'event-1')]);
    assert.equal(first.transaction_id, second.transaction_id); assert.equal(first.post_state_hash, second.post_state_hash); assert.deepEqual(first.artifact_bytes, second.artifact_bytes);
    const cyclic = {}; cyclic.self = cyclic; assert.throws(() => snapshotPlainData(cyclic), /cycle/);
    const getter = {}; Object.defineProperty(getter, 'x', { enumerable: true, get() { throw new Error('getter read'); } }); assert.throws(() => snapshotPlainData(getter), /accessor/);
});

test('late replay cannot backdate T2 and is visible only after publisher knowledge time', t => {
    const ctx = setup(t);
    const args = input(ctx, [rawEvent(0, 'event-replay')], { capture_id: 'capture-replay', acquisition_mode: 'REPLAY' });
    const replayCapture = args.captureReceipt;
    assert.throws(() => buildProspectiveMarketEvidenceTransaction({ authoritySnapshot: ctx.snapshot(), universe: ctx.universe, oddsRawText: args.oddsRawText, captureReceipt: replayCapture, projectionAvailableAt: replayCapture.receipt.ingested_at }), /publisher-owned/);
    const candidate = buildProspectiveMarketEvidenceTransaction({ authoritySnapshot: ctx.snapshot(), universe: ctx.universe, oddsRawText: args.oddsRawText, captureReceipt: replayCapture });
    const result = publishProspectiveMarketEvidenceTransaction({ storeRoot: ctx.storeRoot, allocationArtifactPath: ctx.allocationPath, candidate });
    const row = result.snapshot.observations[0];
    assert.ok(Date.parse(row.projection_available_at) > Date.parse(replayCapture.receipt.ingested_at));
    const query = { canonical_event_id: row.canonical_event_id, canonical_bookmaker_id: row.canonical_bookmaker_id, canonical_selection_id: row.canonical_selection_id, period: row.period, market_type: row.market_type, line: row.line };
    assert.equal(latestAsOf([row], { ...query, decision_time: replayCapture.receipt.ingested_at }), null);
    assert.equal(latestAsOf([row], { ...query, decision_time: row.projection_available_at }).observation_id, row.observation_id);
});

test('ALL_QUARANTINED zero-observation candidate cannot finalize before persisted receipt evidence', t => {
    const ctx = setup(t); const now = Date.now();
    const responseReceivedAt = new Date(now + 120_000).toISOString(); const ingestedAt = new Date(now + 180_000).toISOString();
    const candidate = build(ctx, [rawEvent(0, 'unresolved-future', { home: 'Unknown FC' })], {
        receiptOverrides: { capture_id: 'quarantine-future', response_received_at: responseReceivedAt, ingested_at: ingestedAt },
    });
    assert.equal(candidate.identity_decisions.length, 1); assert.equal(candidate.identity_decisions[0].decision, 'QUARANTINED'); assert.equal(candidate.observations.length, 0);
    assert.throws(() => finalizeProspectiveMarketEvidenceTransactionForPublication(candidate), /publisher clock precedes captured evidence/);
    assert.throws(() => publishProspectiveMarketEvidenceTransaction({ storeRoot: ctx.storeRoot, allocationArtifactPath: ctx.allocationPath, candidate }), /publisher clock precedes captured evidence/);
    assert.equal(ctx.snapshot().head_transaction_id, null);
});

test('authority reader rejects zero-observation transaction T2 before receipt and decision evidence', t => {
    const ctx = setup(t); const now = Date.now();
    const responseReceivedAt = new Date(now + 120_000).toISOString(); const ingestedAt = new Date(now + 180_000).toISOString();
    const candidate = build(ctx, [rawEvent(0, 'unresolved-reopen', { home: 'Unknown FC' })], {
        receiptOverrides: { capture_id: 'quarantine-reopen', response_received_at: responseReceivedAt, ingested_at: ingestedAt },
    });
    assert.equal(candidate.identity_decisions[0].decided_at, responseReceivedAt); assert.equal(candidate.observations.length, 0);
    const invalidKnowledgeTime = new Date(now + 60_000).toISOString(); materializeCandidateWithKnowledgeTime(ctx, candidate, invalidKnowledgeTime);
    assert.throws(() => ctx.snapshot(), /transaction knowledge time precedes capture receipt response evidence/);
});

test('authority reader rejects zero-observation transaction T2 before receipt ingestion evidence', t => {
    const ctx = setup(t); const now = Date.now();
    const responseReceivedAt = new Date(now + 120_000).toISOString(); const ingestedAt = new Date(now + 180_000).toISOString();
    const candidate = build(ctx, [rawEvent(0, 'unresolved-ingestion', { home: 'Unknown FC' })], {
        receiptOverrides: { capture_id: 'quarantine-ingestion', response_received_at: responseReceivedAt, ingested_at: ingestedAt },
    });
    const invalidKnowledgeTime = new Date(now + 150_000).toISOString(); materializeCandidateWithKnowledgeTime(ctx, candidate, invalidKnowledgeTime);
    assert.throws(() => ctx.snapshot(), /transaction knowledge time precedes capture receipt ingestion evidence/);
});

test('PROSPECTIVE_QUARANTINE_NO_OBSERVATION and fake prospective context is rejected', t => {
    const ctx = setup(t); const candidate = build(ctx, [rawEvent(0, 'event-0'), rawEvent(1, 'unresolved-1', { home: 'Unknown FC' })]);
    assert.equal(candidate.identity_decisions.filter(row => row.decision === 'QUARANTINED').length, 1); assert.equal(candidate.observations.some(row => row.provider_event_id === 'unresolved-1'), false); assert.equal(candidate.registry_delta.entries.some(row => row.kind === 'event' && row.provider_id === 'unresolved-1'), false);
    const data = input(ctx, [rawEvent(0, 'event-0')]); const receipt = data.captureReceipt.receipt; const resolved = resolveOddsEventsProspectively({ oddsRawText: data.oddsRawText, oddsRawSha256: receipt.raw_sha256, universe: ctx.universe, decidedAt: receipt.response_received_at });
    assert.throws(() => adaptTheOddsApiRaw({ rawText: data.oddsRawText, capture: receipt, registry: resolved.registry, decisionLedger: { assertActiveMatched() { return true; } }, supportedMarketKeys: ['h2h'], allowedProviderEventIds: new Set(['event-0']), projectionVersion: '1' }), /unverified identity decision ledger/);
});

test('LAST_EVENT_ADAPTER_INVALID_ZERO_WRITES and LAST_EVENT_OBSERVATION_INVALID_ZERO_WRITES', t => {
    const ctx = setup(t); const beforeTree = tree(ctx.storeRoot); const before = ctx.snapshot(); const events = [rawEvent(0, 'event-0'), rawEvent(1, 'event-1', { price: 1 })];
    assert.throws(() => build(ctx, events), /odds_decimal/);
    const after = ctx.snapshot(); assert.equal(after.state_hash, before.state_hash); assert.deepEqual(tree(ctx.storeRoot), beforeTree);
});

test('LAST_EVENT_DECISION_INVALID_ZERO_WRITES processes a valid earlier event only in memory', t => {
    const ctx = setup(t); const beforeTree = tree(ctx.storeRoot); const before = ctx.snapshot();
    assert.throws(() => build(ctx, [rawEvent(0, 'event-0'), rawEvent(1, 'event-0')]), /duplicate or invalid provider event identity/);
    const after = ctx.snapshot(); assert.equal(after.state_hash, before.state_hash); assert.deepEqual(tree(ctx.storeRoot), beforeTree);
});

test('LAST_EVENT_SUPERSESSION_CONFLICT_ZERO_WRITES preserves the complete parent authority', t => {
    const ctx = setup(t); const first = build(ctx, [rawEvent(0, 'event-0')]); materializeCandidate(ctx, first); const beforeTree = tree(ctx.storeRoot); const before = ctx.snapshot();
    // The first event is a valid recapture; the second reaches identity/registry
    // resolution then attempts an unauthorized provider-id reassignment.
    assert.throws(() => build(ctx, [rawEvent(1, 'event-1'), rawEvent(1, 'event-0')], { receiptOverrides: { capture_id: 'capture-conflict' } }), /identity mapping conflict requires authorized supersession/);
    const after = ctx.snapshot(); assert.equal(after.state_hash, before.state_hash); assert.deepEqual(tree(ctx.storeRoot), beforeTree);
    const authorized = build(ctx, [rawEvent(1, 'event-1'), rawEvent(1, 'event-0')], { authorizedSupersessions: ['event-0'], receiptOverrides: { capture_id: 'capture-authorized' } });
    assert.equal(authorized.registry_delta.entries.some(entry => entry.kind === 'event' && entry.provider_id === 'event-0'), true);
    assert.deepEqual(tree(ctx.storeRoot), beforeTree, 'even a valid supersession remains only a prospective registry delta');
});

test('prospective candidate reopens through the single authority snapshot head', t => {
    const ctx = setup(t); const candidate = build(ctx, [rawEvent(0, 'event-0'), rawEvent(1, 'event-1')]); const published = materializeCandidate(ctx, candidate);
    const snapshot = ctx.snapshot(); assert.equal(snapshot.head_transaction_id, published.transaction_id); assert.equal(snapshot.state_hash, candidate.post_state_hash); assert.equal(snapshot.decisions.length, 2); assert.equal(snapshot.observations.length, 6);
    assert.equal(snapshot.latestDecision('the-odds-api', 'event-1').identity_decision_id, candidate.identity_decisions.find(row => row.candidate_provider_event_id === 'event-1').identity_decision_id);
    assert.equal(snapshot.activeMatched('the-odds-api', 'event-0').decision, 'MATCHED');
});
