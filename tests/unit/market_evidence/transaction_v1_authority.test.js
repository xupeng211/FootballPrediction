'use strict';

const assert = require('node:assert/strict');
const crypto = require('node:crypto');
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const { spawnSync } = require('node:child_process');
const test = require('node:test');
const { seedFotMobFixtureUniverse } = require('../../../src/infrastructure/fixture_universe/FixtureUniverse');
const { persistVerifiedAllocationAuthority } = require('../../../src/infrastructure/fixture_universe/AllocationAuthorityArtifact');
const { projectIdentityDecisionState } = require('../../../src/infrastructure/fixture_universe/IdentityDecisionLedger');
const { createObservation, sha256Text, stableStringify } = require('../../../src/infrastructure/market_evidence/contracts');
const { bootstrapMarketEvidenceTransactionStore, readStoreContract } = require('../../../src/infrastructure/market_evidence/transactionStore');
const { openMarketEvidenceAuthoritySnapshot } = require('../../../src/infrastructure/market_evidence/authorityReader');
const { REGISTRY_DELTA_SCHEMA_VERSION, METADATA_SCHEMA_VERSION, canonicalBytes, descriptorForBytes, createManifest, createCommittedMarker, computeAuthorityStateHash } = require('../../../src/infrastructure/market_evidence/transactionContract');

const H = value => sha256Text(value);
const HASH = char => char.repeat(64);
function allocator() { let n = 0; return prefix => `${prefix}_${String(++n).padStart(4, '0')}`; }
function fotmobRaw() {
    const allMatches = Array.from({ length: 380 }, (_, i) => ({ id: String(810000 + i), home: { name: i ? `Home ${i}` : 'Arsenal' }, away: { name: i ? `Away ${i}` : 'Chelsea' }, status: { utcTime: i ? `2026-10-${String((i % 28) + 1).padStart(2, '0')}T15:00:00Z` : '2026-09-12T15:00:00Z' } }));
    return `<script id="__NEXT_DATA__" type="application/json">${JSON.stringify({ query: { season: '2026/2027' }, props: { pageProps: { details: { id: 47 }, fixtures: { allMatches } } } })}</script>`;
}
function setup(t) {
    const root = fs.mkdtempSync(path.join(os.tmpdir(), 'transaction-v1-')); t.after(() => fs.rmSync(root, { recursive: true, force: true }));
    const raw = fotmobRaw(); const universe = seedFotMobFixtureUniverse({ rawHtml: raw, rawSha256: H(raw), manifest: { raw_file_relative_path: 'fixture.html' }, allocate: allocator(), mode: 'INITIAL_SEED' });
    const allocationPath = path.join(root, 'allocation.json'); persistVerifiedAllocationAuthority({ artifactPath: allocationPath, allocationAuthority: universe.allocationAuthority });
    const storeRoot = path.join(root, 'market_evidence_transactions'); bootstrapMarketEvidenceTransactionStore({ storeRoot, allocationArtifactPath: allocationPath, bootstrapMetadata: { fixture: 'transaction-v1' } });
    const store = readStoreContract({ storeRoot, allocationArtifactPath: allocationPath }).store;
    return { root, allocationPath, storeRoot, store, authority: universe.allocationAuthority, eventId: universe.snapshot.fixtures[0].canonical_event_id };
}
function decision({ eventId, id = 'idn_1', prior = null, decision = 'MATCHED', raw = 'a' }) {
    return { identity_decision_id: id, candidate_provider: 'the-odds-api', candidate_provider_event_id: 'provider-event', decision, canonical_event_id: decision === 'MATCHED' ? eventId : null, ruleset_version: 'fixture-identity-ruleset/v1', resolver_version: 'fixture-identity-resolver/v1', decided_at: '2026-08-27T13:31:49Z', raw_sha256: HASH(raw), ...(decision === 'QUARANTINED' ? { quarantine_reason: 'UNKNOWN_HOME_TEAM' } : {}), ...(prior ? { supersedes_decision_id: prior } : {}) };
}
function observation(eventId, decisionId, id = 'obs_1') {
    return createObservation({ projection_version: '1', projection_available_at: '2026-08-27T13:31:50Z', observation_id: id, canonical_event_id: eventId, identity_decision_id: decisionId, identity_ruleset_version: 'fixture-identity-ruleset/v1', identity_resolver_version: 'fixture-identity-resolver/v1', provider: 'the-odds-api', provider_event_id: 'provider-event', canonical_market_id: 'MATCH/1X2/NULL', provider_market_id: 'h2h', canonical_bookmaker_id: 'bookmaker:fixture', provider_bookmaker_id: 'fixture', provider_bookmaker_name: 'Fixture', competition: 'English Premier League', season: '2026/2027', home_team: 'Arsenal', away_team: 'Chelsea', kickoff_utc: '2026-09-12T15:00:00Z', period: 'MATCH', market_type: '1X2', line: null, canonical_selection_id: 'HOME', selection: 'HOME', price_side: 'BOOKMAKER', odds_decimal: 2, available_volume: null, bet_limit: null, bookmaker_last_update_at: null, source_snapshot_at: null, capture_started_at: '2026-08-27T13:31:20Z', response_received_at: '2026-08-27T13:31:49Z', ingested_at: '2026-08-27T13:31:49Z', acquisition_mode: 'HISTORICAL_FILE', capture_id: 'capture-1', raw_evidence_reference: 'raw/x.json', raw_sha256: HASH('b'), adapter_name: 'the-odds-api', adapter_version: '1.0.0', identity_registry_version: 'fixture/v1', identity_registry_sha256: HASH('c'), quality_flags: [] });
}
function jsonl(rows) { return rows.length ? `${rows.map(stableStringify).join('\n')}\n` : ''; }
function semanticObservationJsonl(rows) { return jsonl(rows.map(row => { const copy = { ...row }; delete copy.projection_available_at; return copy; })); }
function overwrite(target, bytes) { fs.chmodSync(target, 0o644); fs.writeFileSync(target, bytes); fs.chmodSync(target, 0o444); }
function writePackage(ctx, previous, { decisions = [], observations = [], entries = [], name = null, manifestPatch = null } = {}) {
    const metadata = { schema_version: METADATA_SCHEMA_VERSION, source: { provider: 'the-odds-api', capture_id: 'capture-1', raw_sha256: HASH('b'), receipt_sha256: HASH('d') } };
    const delta = { schema_version: REGISTRY_DELTA_SCHEMA_VERSION, entries };
    const bytes = { 'identity_decisions.jsonl': jsonl(decisions), 'observations.jsonl': jsonl(observations), 'registry_delta.json': canonicalBytes(delta), 'metadata.json': canonicalBytes(metadata) };
    const artifacts = Object.fromEntries(Object.entries(bytes).map(([file, value]) => [file, descriptorForBytes(file, value, file === 'identity_decisions.jsonl' ? decisions.length : file === 'observations.jsonl' ? observations.length : file === 'registry_delta.json' ? entries.length : 1, file === 'observations.jsonl' ? semanticObservationJsonl(observations) : value)]));
    const allDecisions = [...(previous?.decisions || []), ...decisions]; const projected = projectIdentityDecisionState(allDecisions, ctx.authority);
    const registry = new Map(previous?.registry || []); for (const entry of entries) registry.set(`${entry.kind}\u0000${entry.provider}\u0000${entry.provider_id}`, entry);
    const index = new Map(previous?.observations || []); for (const row of observations) index.set(row.observation_id, row);
    const postState = computeAuthorityStateHash({ allocation: ctx.store.allocation, decisions: allDecisions, latestDecisions: projected.latest, activeMatched: projected.active, registryState: registry, observationIndex: index });
    let manifestFields = { sequence: previous ? previous.sequence + 1 : 1, parent_transaction_id: previous ? previous.id : null, parent_transaction_content_hash: previous ? previous.hash : null, expected_parent_state_hash: previous ? previous.state : ctx.store.genesis_state_hash, post_state_hash: postState, allocation: ctx.store.allocation, source: metadata.source, versions: { resolver_version: 'fixture-identity-resolver/v1', ruleset_version: 'fixture-identity-ruleset/v1', adapter_version: '1.0.0', projection_version: '1', registry_schema_version: REGISTRY_DELTA_SCHEMA_VERSION, registry_version: 'fixture/v1', observation_schema_version: 'footballprediction-market-observation/v1' }, artifacts, decision_count: decisions.length, observation_count: observations.length, registry_delta_count: entries.length, quarantine_count: decisions.filter(row => row.decision === 'QUARANTINED').length, publication_metadata: { schema_version: 'transaction-publication/v1', knowledge_time: '2026-08-27T13:31:50Z' } };
    if (manifestPatch) manifestFields = manifestPatch({ ...manifestFields });
    const manifest = createManifest(manifestFields);
    const dirName = name || manifest.transaction_id; const dir = path.join(ctx.storeRoot, 'committed', dirName); fs.mkdirSync(dir, { recursive: true });
    for (const [file, value] of Object.entries(bytes)) fs.writeFileSync(path.join(dir, file), value, { mode: 0o444 });
    fs.writeFileSync(path.join(dir, 'manifest.json'), canonicalBytes(manifest), { mode: 0o444 }); fs.writeFileSync(path.join(dir, 'COMMITTED'), canonicalBytes(createCommittedMarker(manifest)), { mode: 0o444 });
    return { id: manifest.transaction_id, hash: manifest.transaction_content_hash, state: manifest.post_state_hash, sequence: manifest.sequence, decisions: allDecisions, registry, observations: index, dir };
}

test('EMPTY_STORE_GENESIS_READER_PASS and immutable allocation binding', t => {
    const ctx = setup(t); const snapshot = openMarketEvidenceAuthoritySnapshot({ storeRoot: ctx.storeRoot, allocationArtifactPath: ctx.allocationPath });
    assert.equal(snapshot.head_transaction_id, null); assert.equal(snapshot.state_hash, ctx.store.genesis_state_hash); assert.equal(snapshot.decisions.length, 0); assert.equal(snapshot.observations.length, 0);
    assert.throws(() => bootstrapMarketEvidenceTransactionStore({ storeRoot: ctx.storeRoot, allocationArtifactPath: ctx.allocationPath, bootstrapMetadata: { fixture: 'different' } }), /different content/);
    const raw = fotmobRaw(); let n = 0; const other = seedFotMobFixtureUniverse({ rawHtml: raw, rawSha256: H(raw), manifest: { raw_file_relative_path: 'fixture.html' }, allocate: prefix => `${prefix}_other${String(++n).padStart(4, '0')}`, mode: 'INITIAL_SEED' }); const otherPath = path.join(ctx.root, 'other-allocation.json'); persistVerifiedAllocationAuthority({ artifactPath: otherPath, allocationAuthority: other.allocationAuthority }); assert.throws(() => openMarketEvidenceAuthoritySnapshot({ storeRoot: ctx.storeRoot, allocationArtifactPath: otherPath }), /different allocation authority/);
});

test('VALID_SINGLE_TRANSACTION_READER_PASS and NO_COMMIT_TRANSACTION_NOT_DISCOVERED', t => {
    const ctx = setup(t); const d = decision({ eventId: ctx.eventId }); const transaction = writePackage(ctx, null, { decisions: [d], observations: [observation(ctx.eventId, d.identity_decision_id)] });
    const snapshot = openMarketEvidenceAuthoritySnapshot({ storeRoot: ctx.storeRoot, allocationArtifactPath: ctx.allocationPath }); assert.equal(snapshot.head_transaction_id, transaction.id); assert.equal(snapshot.decisions.length, 1); assert.equal(snapshot.observations.length, 1);
    const uncommitted = path.join(ctx.storeRoot, '.staging', 'tx_' + 'f'.repeat(64)); fs.mkdirSync(uncommitted); fs.writeFileSync(path.join(uncommitted, 'manifest.json'), '{}\n'); assert.equal(openMarketEvidenceAuthoritySnapshot({ storeRoot: ctx.storeRoot, allocationArtifactPath: ctx.allocationPath }).head_transaction_id, transaction.id);
});

test('VALID_MULTI_TRANSACTION_PARENT_CHAIN_PASS reconstructs one combined snapshot', t => {
    const ctx = setup(t); const firstDecision = decision({ eventId: ctx.eventId }); const first = writePackage(ctx, null, { decisions: [firstDecision], observations: [observation(ctx.eventId, firstDecision.identity_decision_id)], entries: [{ kind: 'event', provider: 'the-odds-api', provider_id: 'provider-event', canonical_id: ctx.eventId }] });
    const secondDecision = decision({ eventId: ctx.eventId, id: 'idn_2', prior: firstDecision.identity_decision_id, decision: 'QUARANTINED', raw: 'e' }); const second = writePackage(ctx, first, { decisions: [secondDecision] });
    const thirdDecision = decision({ eventId: ctx.eventId, id: 'idn_3', prior: secondDecision.identity_decision_id, raw: 'f' }); writePackage(ctx, second, { decisions: [thirdDecision], observations: [observation(ctx.eventId, thirdDecision.identity_decision_id, 'obs_2')] });
    const snapshot = openMarketEvidenceAuthoritySnapshot({ storeRoot: ctx.storeRoot, allocationArtifactPath: ctx.allocationPath });
    assert.equal(snapshot.decisions.length, 3); assert.equal(snapshot.observations.length, 2); assert.equal(snapshot.latestDecision('the-odds-api', 'provider-event').identity_decision_id, 'idn_3'); assert.equal(snapshot.activeMatched('the-odds-api', 'provider-event').identity_decision_id, 'idn_3'); assert.equal(snapshot.aliases[0].identity_decision_id, 'idn_3'); assert.equal(snapshot.head_transaction_id.startsWith('tx_'), true);
});

test('PARTIAL_STAGING_IGNORED and STAGING_WITH_COMMITTED_MARKER_IGNORED', t => {
    const ctx = setup(t); const residue = path.join(ctx.storeRoot, '.staging', 'tx_deadbeef'); fs.mkdirSync(residue); fs.writeFileSync(path.join(residue, 'COMMITTED'), '{}\n'); fs.writeFileSync(path.join(residue, 'garbage'), 'x');
    const snapshot = openMarketEvidenceAuthoritySnapshot({ storeRoot: ctx.storeRoot, allocationArtifactPath: ctx.allocationPath }); assert.equal(snapshot.head_transaction_id, null);
});

test('committed package tampering and exact-file violations fail closed', t => {
    const ctx = setup(t); const d = decision({ eventId: ctx.eventId }); const tx = writePackage(ctx, null, { decisions: [d] });
    fs.writeFileSync(path.join(tx.dir, 'extra'), 'x'); assert.throws(() => openMarketEvidenceAuthoritySnapshot({ storeRoot: ctx.storeRoot, allocationArtifactPath: ctx.allocationPath }), /unexpected file set/);
});

test('MISSING_ARTIFACT_REJECTED, MANIFEST_PAYLOAD_HASH_MISMATCH_REJECTED and COMMITTED mismatch reject persisted bytes', t => {
    const ctx = setup(t); const d = decision({ eventId: ctx.eventId }); const tx = writePackage(ctx, null, { decisions: [d] });
    fs.unlinkSync(path.join(tx.dir, 'metadata.json')); assert.throws(() => openMarketEvidenceAuthoritySnapshot({ storeRoot: ctx.storeRoot, allocationArtifactPath: ctx.allocationPath }), /unexpected file set/);
    const ctx2 = setup(t); const tx2 = writePackage(ctx2, null, { decisions: [decision({ eventId: ctx2.eventId })] }); overwrite(path.join(tx2.dir, 'identity_decisions.jsonl'), 'x\n'); assert.throws(() => openMarketEvidenceAuthoritySnapshot({ storeRoot: ctx2.storeRoot, allocationArtifactPath: ctx2.allocationPath }), /invalid JSON/);
    const ctx3 = setup(t); const tx3 = writePackage(ctx3, null, { decisions: [decision({ eventId: ctx3.eventId })] }); overwrite(path.join(tx3.dir, 'COMMITTED'), canonicalBytes({ schema_version: 'footballprediction-market-evidence-transaction-commit/v1', transaction_id: tx3.id, transaction_content_hash: tx3.hash, manifest_sha256: HASH('0') })); assert.throws(() => openMarketEvidenceAuthoritySnapshot({ storeRoot: ctx3.storeRoot, allocationArtifactPath: ctx3.allocationPath }), /does not bind manifest/);
});

test('wrong parent, gap, orphan, fork, noncanonical name and transaction identity all fail closed', t => {
    const ctx = setup(t); const d = decision({ eventId: ctx.eventId }); const first = writePackage(ctx, null, { decisions: [d] });
    writePackage(ctx, first, { name: 'tx_' + '0'.repeat(64) }); assert.throws(() => openMarketEvidenceAuthoritySnapshot({ storeRoot: ctx.storeRoot, allocationArtifactPath: ctx.allocationPath }), /directory name does not match/);
    const ctx2 = setup(t); const p = writePackage(ctx2, null, { decisions: [decision({ eventId: ctx2.eventId })] }); writePackage(ctx2, p, { observations: [observation(ctx2.eventId, 'idn_1', 'obs_a')] }); writePackage(ctx2, p, { observations: [observation(ctx2.eventId, 'idn_1', 'obs_b')] }); assert.throws(() => openMarketEvidenceAuthoritySnapshot({ storeRoot: ctx2.storeRoot, allocationArtifactPath: ctx2.allocationPath }), /fork|multiple head/);
    const ctx3 = setup(t); writePackage(ctx3, null, { decisions: [decision({ eventId: ctx3.eventId })], manifestPatch: fields => ({ ...fields, sequence: 2, parent_transaction_id: 'tx_' + 'a'.repeat(64), parent_transaction_content_hash: HASH('a') }) }); assert.throws(() => openMarketEvidenceAuthoritySnapshot({ storeRoot: ctx3.storeRoot, allocationArtifactPath: ctx3.allocationPath }), /orphan|root/);
    const ctx4 = setup(t); const first4 = writePackage(ctx4, null, { decisions: [decision({ eventId: ctx4.eventId })] }); writePackage(ctx4, first4, { manifestPatch: fields => ({ ...fields, parent_transaction_content_hash: HASH('b') }) }); assert.throws(() => openMarketEvidenceAuthoritySnapshot({ storeRoot: ctx4.storeRoot, allocationArtifactPath: ctx4.allocationPath }), /wrong parent content hash/);
    const ctx5 = setup(t); const first5 = writePackage(ctx5, null, { decisions: [decision({ eventId: ctx5.eventId })] }); writePackage(ctx5, first5, { manifestPatch: fields => ({ ...fields, expected_parent_state_hash: HASH('c') }) }); assert.throws(() => openMarketEvidenceAuthoritySnapshot({ storeRoot: ctx5.storeRoot, allocationArtifactPath: ctx5.allocationPath }), /wrong parent state hash/);
    const ctx6 = setup(t); const first6 = writePackage(ctx6, null, { decisions: [decision({ eventId: ctx6.eventId })] }); writePackage(ctx6, first6, { manifestPatch: fields => ({ ...fields, sequence: 3 }) }); assert.throws(() => openMarketEvidenceAuthoritySnapshot({ storeRoot: ctx6.storeRoot, allocationArtifactPath: ctx6.allocationPath }), /sequence gap/);
});

test('SYMLINK_TRANSACTION_REJECTED and SYMLINK_ARTIFACT_REJECTED', t => {
    const ctx = setup(t); const target = path.join(ctx.root, 'target'); fs.mkdirSync(target); fs.symlinkSync(target, path.join(ctx.storeRoot, 'committed', 'tx_' + '1'.repeat(64))); assert.throws(() => openMarketEvidenceAuthoritySnapshot({ storeRoot: ctx.storeRoot, allocationArtifactPath: ctx.allocationPath }), /transaction directory/);
    const ctx2 = setup(t); const tx = writePackage(ctx2, null, { decisions: [decision({ eventId: ctx2.eventId })] }); const targetFile = path.join(ctx2.root, 'target-file'); fs.writeFileSync(targetFile, 'safe'); fs.unlinkSync(path.join(tx.dir, 'metadata.json')); fs.symlinkSync(targetFile, path.join(tx.dir, 'metadata.json')); assert.throws(() => openMarketEvidenceAuthoritySnapshot({ storeRoot: ctx2.storeRoot, allocationArtifactPath: ctx2.allocationPath }), /regular file/);
});

test('STATE_HASH_DETERMINISTIC, TRANSACTION_ID_DETERMINISTIC and CROSS_PROCESS_REOPEN', t => {
    const ctx = setup(t); const d = decision({ eventId: ctx.eventId }); const a = writePackage(ctx, null, { decisions: [d], observations: [observation(ctx.eventId, d.identity_decision_id)] }); const one = openMarketEvidenceAuthoritySnapshot({ storeRoot: ctx.storeRoot, allocationArtifactPath: ctx.allocationPath }); const two = openMarketEvidenceAuthoritySnapshot({ storeRoot: ctx.storeRoot, allocationArtifactPath: ctx.allocationPath }); assert.equal(one.state_hash, two.state_hash);
    const identical = setup(t); const identicalDecision = decision({ eventId: identical.eventId }); const b = writePackage(identical, null, { decisions: [identicalDecision], observations: [observation(identical.eventId, identicalDecision.identity_decision_id)] }); const other = openMarketEvidenceAuthoritySnapshot({ storeRoot: identical.storeRoot, allocationArtifactPath: identical.allocationPath }); assert.equal(a.id, b.id); assert.equal(one.state_hash, other.state_hash);
    const program = "const r=require('./src/infrastructure/market_evidence/authorityReader');process.stdout.write(r.openMarketEvidenceAuthoritySnapshot({storeRoot:process.argv[1],allocationArtifactPath:process.argv[2]}).state_hash)";
    const child = spawnSync(process.execPath, ['-e', program, ctx.storeRoot, ctx.allocationPath], { cwd: path.resolve(__dirname, '../../..'), encoding: 'utf8' }); assert.equal(child.status, 0, child.stderr); assert.equal(child.stdout, one.state_hash);
});
