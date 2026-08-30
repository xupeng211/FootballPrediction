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
const { buildProspectiveMarketEvidenceTransaction, snapshotPlainData } = require('../../../src/infrastructure/market_evidence/prospectiveBatch');
const { publishProspectiveMarketEvidenceTransaction } = require('../../../src/infrastructure/market_evidence/atomicPublisher');
const { adaptTheOddsApiRaw } = require('../../../src/infrastructure/market_evidence/theOddsApiAdapter');
const { projectIdentityDecisionState } = require('../../../src/infrastructure/fixture_universe/IdentityDecisionLedger');

const hash = value => sha256Text(value);
function allocator() { let n = 0; return prefix => `${prefix}_${String(++n).padStart(4, '0')}`; }
function fotmobRaw() {
    const allMatches = Array.from({ length: 380 }, (_, i) => ({ id: String(810000 + i), home: { name: i ? `Home ${i}` : 'Arsenal' }, away: { name: i ? `Away ${i}` : 'Chelsea' }, status: { utcTime: i ? `2026-10-${String((i % 28) + 1).padStart(2, '0')}T15:00:00Z` : '2026-09-12T15:00:00Z' } }));
    return `<script id="__NEXT_DATA__" type="application/json">${JSON.stringify({ query: { season: '2026/2027' }, props: { pageProps: { details: { id: 47 }, fixtures: { allMatches } } } })}</script>`;
}
function setup(t) {
    const root = fs.mkdtempSync(path.join(os.tmpdir(), 'prospective-v1-')); t.after(() => fs.rmSync(root, { recursive: true, force: true }));
    const raw = fotmobRaw(); const universe = seedFotMobFixtureUniverse({ rawHtml: raw, rawSha256: hash(raw), manifest: { raw_file_relative_path: 'fixture.html' }, allocate: allocator(), mode: 'INITIAL_SEED' });
    const allocationPath = path.join(root, 'allocation.json'); persistVerifiedAllocationAuthority({ artifactPath: allocationPath, allocationAuthority: universe.allocationAuthority });
    const storeRoot = path.join(root, 'market_evidence_transactions'); bootstrapMarketEvidenceTransactionStore({ storeRoot, allocationArtifactPath: allocationPath, bootstrapMetadata: { fixture: 'prospective-v1' } });
    return { root, universe, allocationPath, storeRoot, snapshot: () => openMarketEvidenceAuthoritySnapshot({ storeRoot, allocationArtifactPath: allocationPath }) };
}
function rawEvent(index, id, { price = 2, home = null, away = null, kickoff = null } = {}) {
    const defaults = index ? { home: `Home ${index}`, away: `Away ${index}`, kickoff: `2026-10-${String((index % 28) + 1).padStart(2, '0')}T15:00:00Z` } : { home: 'Arsenal', away: 'Chelsea', kickoff: '2026-09-12T15:00:00Z' };
    return { id, sport_key: 'soccer_epl', home_team: home || defaults.home, away_team: away || defaults.away, commence_time: kickoff || defaults.kickoff, bookmakers: [{ key: 'fixture-bookmaker', title: 'Fixture Bookmaker', markets: [{ key: 'h2h', outcomes: [{ name: home || defaults.home, price }, { name: 'Draw', price: 3 }, { name: away || defaults.away, price: 4 }] }] }] };
}
function input(events) {
    const oddsRawText = JSON.stringify(events);
    return { oddsRawText, captureReceipt: { provider: 'the-odds-api', capture_id: 'capture-prospective-1', raw_sha256: hash(oddsRawText), request_started_at: '2026-08-27T13:31:20Z', response_received_at: '2026-08-27T13:31:49Z', ingested_at: '2026-08-27T13:31:49Z', acquisition_mode: 'HISTORICAL_FILE', raw_evidence_reference: 'raw/odds.json' } };
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
function build(ctx, events, extra = {}) { return buildProspectiveMarketEvidenceTransaction({ authoritySnapshot: ctx.snapshot(), universe: ctx.universe, ...input(events), ...extra }); }
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
function materializeRegistryConflictParent(ctx) {
    const candidate = build(ctx, [rawEvent(0, 'event-0')]);
    const entries = candidate.registry_delta.entries.map(entry => entry.kind === 'bookmaker' ? { ...entry, canonical_id: 'bookmaker:conflicting-parent' } : entry);
    const registry = new Map(entries.map(entry => [`${entry.kind}\u0000${entry.provider}\u0000${entry.provider_id}`, entry]));
    const delta = { ...candidate.registry_delta, entries, result_registry_state_sha256: hashCanonical([...registry.entries()].sort(([a], [b]) => a.localeCompare(b))) };
    const bytes = { ...candidate.artifact_bytes, 'registry_delta.json': canonicalBytes(delta) };
    const artifacts = { ...candidate.artifacts, 'registry_delta.json': descriptorForBytes('registry_delta.json', bytes['registry_delta.json'], entries.length) };
    const projected = projectIdentityDecisionState(candidate.identity_decisions, ctx.universe.allocationAuthority);
    const observations = new Map(candidate.observations.map(row => [row.observation_id, row]));
    const postState = computeAuthorityStateHash({ allocation: candidate.allocation, decisions: candidate.identity_decisions, latestDecisions: projected.latest, activeMatched: projected.active, registryState: registry, observationIndex: observations });
    const manifest = createManifest({ sequence: 1, parent_transaction_id: null, parent_transaction_content_hash: null, expected_parent_state_hash: ctx.snapshot().state_hash, post_state_hash: postState, allocation: candidate.allocation, source: candidate.metadata.source, versions: candidate.manifest.versions, artifacts, decision_count: candidate.decision_count, observation_count: candidate.observation_count, registry_delta_count: entries.length, quarantine_count: candidate.quarantine_count, publication_metadata: { ...candidate.manifest.publication_metadata, knowledge_time: '2026-08-27T13:31:49Z' } });
    materializeCandidate(ctx, { transaction_id: manifest.transaction_id, artifact_bytes: bytes, manifest });
}

test('PROSPECTIVE_VALID_BATCH_BUILDS_CANDIDATE with one coherent zero-write authority head', t => {
    const ctx = setup(t); const beforeTree = tree(ctx.root); const before = ctx.snapshot();
    const candidate = build(ctx, [rawEvent(0, 'event-0'), rawEvent(1, 'event-1')]); const after = ctx.snapshot();
    assert.equal(candidate.sequence, 1); assert.equal(candidate.identity_decisions.length, 2); assert.equal(candidate.observations.length, 6); assert.equal(candidate.decision_count, 2); assert.equal(candidate.observation_count, 6);
    assert.equal(candidate.parent_transaction_id, null); assert.equal(candidate.expected_parent_state_hash, before.state_hash); assert.equal(after.state_hash, before.state_hash);
    assert.deepEqual(tree(ctx.root), beforeTree, 'prospective build must not write STORE, committed, staging, legacy ledgers, or registry files');
    assert.equal(candidate.manifest.transaction_id, candidate.transaction_id); assert.equal(candidate.artifact_bytes['identity_decisions.jsonl'].includes('\n'), true);
});

test('IDENTICAL_PROSPECTIVE_REBUILD_DETERMINISTIC and caller input is snapshotted', t => {
    const ctx = setup(t); const events = [rawEvent(0, 'event-0'), rawEvent(1, 'event-1')]; const args = input(events);
    const first = buildProspectiveMarketEvidenceTransaction({ authoritySnapshot: ctx.snapshot(), universe: ctx.universe, ...args });
    args.captureReceipt.capture_id = 'mutated-after-build'; events[0].bookmakers[0].markets[0].outcomes[0].price = 999;
    const second = build(ctx, [rawEvent(0, 'event-0'), rawEvent(1, 'event-1')]);
    assert.equal(first.transaction_id, second.transaction_id); assert.equal(first.post_state_hash, second.post_state_hash); assert.deepEqual(first.artifact_bytes, second.artifact_bytes);
    const cyclic = {}; cyclic.self = cyclic; assert.throws(() => snapshotPlainData(cyclic), /cycle/);
    const getter = {}; Object.defineProperty(getter, 'x', { enumerable: true, get() { throw new Error('getter read'); } }); assert.throws(() => snapshotPlainData(getter), /accessor/);
});

test('late replay cannot backdate T2 and is visible only after publisher knowledge time', t => {
    const ctx = setup(t);
    const args = input([rawEvent(0, 'event-replay')]);
    const replayCapture = { ...args.captureReceipt, acquisition_mode: 'REPLAY' };
    assert.throws(() => buildProspectiveMarketEvidenceTransaction({ authoritySnapshot: ctx.snapshot(), universe: ctx.universe, oddsRawText: args.oddsRawText, captureReceipt: replayCapture, projectionAvailableAt: replayCapture.ingested_at }), /publisher-owned/);
    const candidate = buildProspectiveMarketEvidenceTransaction({ authoritySnapshot: ctx.snapshot(), universe: ctx.universe, oddsRawText: args.oddsRawText, captureReceipt: replayCapture });
    const result = publishProspectiveMarketEvidenceTransaction({ storeRoot: ctx.storeRoot, allocationArtifactPath: ctx.allocationPath, candidate });
    const row = result.snapshot.observations[0];
    assert.ok(Date.parse(row.projection_available_at) > Date.parse(replayCapture.ingested_at));
    const query = { canonical_event_id: row.canonical_event_id, canonical_bookmaker_id: row.canonical_bookmaker_id, canonical_selection_id: row.canonical_selection_id, period: row.period, market_type: row.market_type, line: row.line };
    assert.equal(latestAsOf([row], { ...query, decision_time: replayCapture.ingested_at }), null);
    assert.equal(latestAsOf([row], { ...query, decision_time: row.projection_available_at }).observation_id, row.observation_id);
});

test('PROSPECTIVE_QUARANTINE_NO_OBSERVATION and fake prospective context is rejected', t => {
    const ctx = setup(t); const candidate = build(ctx, [rawEvent(0, 'event-0'), rawEvent(1, 'unresolved-1', { home: 'Unknown FC' })]);
    assert.equal(candidate.identity_decisions.filter(row => row.decision === 'QUARANTINED').length, 1); assert.equal(candidate.observations.some(row => row.provider_event_id === 'unresolved-1'), false); assert.equal(candidate.registry_delta.entries.some(row => row.kind === 'event' && row.provider_id === 'unresolved-1'), false);
    const data = input([rawEvent(0, 'event-0')]); const resolved = resolveOddsEventsProspectively({ oddsRawText: data.oddsRawText, oddsRawSha256: data.captureReceipt.raw_sha256, universe: ctx.universe, decidedAt: data.captureReceipt.response_received_at });
    assert.throws(() => adaptTheOddsApiRaw({ rawText: data.oddsRawText, capture: data.captureReceipt, registry: resolved.registry, decisionLedger: { assertActiveMatched() { return true; } }, supportedMarketKeys: ['h2h'], allowedProviderEventIds: new Set(['event-0']), projectionVersion: '1' }), /unverified identity decision ledger/);
});

test('LAST_EVENT_ADAPTER_INVALID_ZERO_WRITES and LAST_EVENT_OBSERVATION_INVALID_ZERO_WRITES', t => {
    const ctx = setup(t); const beforeTree = tree(ctx.root); const before = ctx.snapshot(); const events = [rawEvent(0, 'event-0'), rawEvent(1, 'event-1', { price: 1 })];
    assert.throws(() => build(ctx, events), /odds_decimal/);
    const after = ctx.snapshot(); assert.equal(after.state_hash, before.state_hash); assert.deepEqual(tree(ctx.root), beforeTree);
});

test('LAST_EVENT_DECISION_INVALID_ZERO_WRITES processes a valid earlier event only in memory', t => {
    const ctx = setup(t); const beforeTree = tree(ctx.root); const before = ctx.snapshot();
    assert.throws(() => build(ctx, [rawEvent(0, 'event-0'), rawEvent(1, 'event-0')]), /duplicate or invalid provider event identity/);
    const after = ctx.snapshot(); assert.equal(after.state_hash, before.state_hash); assert.deepEqual(tree(ctx.root), beforeTree);
});

test('LAST_EVENT_REGISTRY_CONFLICT_ZERO_WRITES detects a late immutable mapping conflict', t => {
    const ctx = setup(t); materializeRegistryConflictParent(ctx); const beforeTree = tree(ctx.root); const before = ctx.snapshot();
    assert.throws(() => build(ctx, [rawEvent(1, 'event-1'), rawEvent(0, 'event-0')]), /registry conflict: bookmaker/);
    const after = ctx.snapshot(); assert.equal(after.state_hash, before.state_hash); assert.deepEqual(tree(ctx.root), beforeTree);
});

test('LAST_EVENT_SUPERSESSION_CONFLICT_ZERO_WRITES preserves the complete parent authority', t => {
    const ctx = setup(t); const first = build(ctx, [rawEvent(0, 'event-0')]); materializeCandidate(ctx, first); const beforeTree = tree(ctx.root); const before = ctx.snapshot();
    // The first event is a valid recapture; the second reaches identity/registry
    // resolution then attempts an unauthorized provider-id reassignment.
    assert.throws(() => build(ctx, [rawEvent(1, 'event-1'), rawEvent(1, 'event-0')]), /identity mapping conflict requires authorized supersession/);
    const after = ctx.snapshot(); assert.equal(after.state_hash, before.state_hash); assert.deepEqual(tree(ctx.root), beforeTree);
    const authorized = build(ctx, [rawEvent(1, 'event-1'), rawEvent(1, 'event-0')], { authorizedSupersessions: ['event-0'] });
    assert.equal(authorized.registry_delta.entries.some(entry => entry.kind === 'event' && entry.provider_id === 'event-0'), true);
    assert.deepEqual(tree(ctx.root), beforeTree, 'even a valid supersession remains only a prospective registry delta');
});

test('prospective candidate reopens through the single authority snapshot head', t => {
    const ctx = setup(t); const candidate = build(ctx, [rawEvent(0, 'event-0'), rawEvent(1, 'event-1')]); materializeCandidate(ctx, candidate);
    const snapshot = ctx.snapshot(); assert.equal(snapshot.head_transaction_id, candidate.transaction_id); assert.equal(snapshot.state_hash, candidate.post_state_hash); assert.equal(snapshot.decisions.length, 2); assert.equal(snapshot.observations.length, 6);
    assert.equal(snapshot.latestDecision('the-odds-api', 'event-1').identity_decision_id, candidate.identity_decisions.find(row => row.candidate_provider_event_id === 'event-1').identity_decision_id);
    assert.equal(snapshot.activeMatched('the-odds-api', 'event-0').decision, 'MATCHED');
});
