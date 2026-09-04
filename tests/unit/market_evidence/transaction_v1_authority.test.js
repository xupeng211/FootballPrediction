'use strict';

const assert = require('node:assert/strict');
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const { spawnSync } = require('node:child_process');
const test = require('node:test');
const { seedFotMobFixtureUniverse } = require('../../../src/infrastructure/fixture_universe/FixtureUniverse');
const { persistVerifiedAllocationAuthority } = require('../../../src/infrastructure/fixture_universe/AllocationAuthorityArtifact');
const { sha256Text, stableStringify } = require('../../../src/infrastructure/market_evidence/contracts');
const { bootstrapMarketEvidenceTransactionStore } = require('../../../src/infrastructure/market_evidence/transactionStore');
const { openMarketEvidenceAuthoritySnapshot } = require('../../../src/infrastructure/market_evidence/authorityReader');
const { buildProspectiveMarketEvidenceTransaction } = require('../../../src/infrastructure/market_evidence/prospectiveBatch');
const { publishProspectiveMarketEvidenceTransaction } = require('../../../src/infrastructure/market_evidence/atomicPublisher');
const { loadVerifiedCaptureReceipt } = require('../../../src/infrastructure/market_evidence/evidenceStore');
const { publishOfflineMarketEvidence, verifyPublishedLogicalBatch } = require('../../../src/infrastructure/market_evidence/offlinePipeline');
const { canonicalBytes, createCommittedMarker, createManifest, descriptorForBytes } = require('../../../src/infrastructure/market_evidence/transactionContract');
const { createVerifiedTestReceipt } = require('../../helpers/market_evidence_authority');

const clone = value => JSON.parse(JSON.stringify(value));
function fixtureRaw() {
    const allMatches = Array.from({ length: 380 }, (_, index) => ({ id: String(940000 + index), home: { name: index ? `Home ${index}` : 'Arsenal' }, away: { name: index ? `Away ${index}` : 'Chelsea' }, status: { utcTime: index ? `2026-10-${String((index % 28) + 1).padStart(2, '0')}T15:00:00Z` : '2026-09-12T15:00:00Z' } }));
    return `<script id="__NEXT_DATA__" type="application/json">${JSON.stringify({ query: { season: '2026/2027' }, props: { pageProps: { details: { id: 47 }, fixtures: { allMatches } } } })}</script>`;
}
function oddsRaw(id = 'provider-event', price = 2) {
    return JSON.stringify([{ id, sport_key: 'soccer_epl', home_team: 'Arsenal', away_team: 'Chelsea', commence_time: '2026-09-12T15:00:00Z', bookmakers: [{ key: 'fixture', title: 'Fixture', markets: [{ key: 'h2h', outcomes: [{ name: 'Arsenal', price }, { name: 'Draw', price: 3 }, { name: 'Chelsea', price: 4 }] }] }] }]);
}
function setup(t) {
    const root = fs.mkdtempSync(path.join(os.tmpdir(), 'transaction-v1-production-'));
    t.after(() => fs.rmSync(root, { recursive: true, force: true }));
    const raw = fixtureRaw();
    const initial = seedFotMobFixtureUniverse({ rawHtml: raw, rawSha256: sha256Text(raw), mode: 'INITIAL_SEED' });
    const allocationPath = path.join(root, 'allocation.json');
    const persisted = persistVerifiedAllocationAuthority({ artifactPath: allocationPath, allocationAuthority: initial.allocationAuthority });
    const universe = seedFotMobFixtureUniverse({ rawHtml: raw, rawSha256: sha256Text(raw), allocation: persisted.allocationSnapshot, allocationAuthority: persisted.allocationAuthority, mode: 'REPLAY' });
    const storeRoot = path.join(root, 'store');
    bootstrapMarketEvidenceTransactionStore({ storeRoot, allocationArtifactPath: allocationPath, bootstrapMetadata: { test: 'transaction-v1-production' } });
    return { root, universe, allocationPath, storeRoot };
}
function candidate(ctx, { captureId = 'capture-1', eventId = 'provider-event', price = 2, rawText = null, receiptOverrides = {}, receiptRootTag = '' } = {}) {
    const oddsRawText = rawText || oddsRaw(eventId, price);
    const captureReceipt = createVerifiedTestReceipt({ root: path.join(ctx.root, 'receipts', `${captureId}-${sha256Text(oddsRawText).slice(0, 8)}${receiptRootTag}`), rawText: oddsRawText, overrides: { capture_id: captureId, ...receiptOverrides } });
    return buildProspectiveMarketEvidenceTransaction({ authoritySnapshot: openMarketEvidenceAuthoritySnapshot({ storeRoot: ctx.storeRoot, allocationArtifactPath: ctx.allocationPath }), universe: ctx.universe, oddsRawText, captureReceipt });
}
function publish(ctx, value) { return publishProspectiveMarketEvidenceTransaction({ storeRoot: ctx.storeRoot, allocationArtifactPath: ctx.allocationPath, candidate: value }); }
function jsonl(rows) { return rows.length ? `${rows.map(stableStringify).join('\n')}\n` : ''; }
function semanticObservationBytes(rows) { return jsonl(rows.map(row => { const copy = { ...row }; delete copy.projection_available_at; return copy; })); }
function makeWritable(file) { fs.chmodSync(file, 0o644); }
function rewritePackage(ctx, transactionId, mutation, { retainTransactionId = false } = {}) {
    const oldDir = path.join(ctx.storeRoot, 'committed', transactionId);
    const manifest = JSON.parse(fs.readFileSync(path.join(oldDir, 'manifest.json'), 'utf8'));
    const data = {
        decisions: fs.readFileSync(path.join(oldDir, 'identity_decisions.jsonl'), 'utf8').trim().split('\n').filter(Boolean).map(JSON.parse),
        observations: fs.readFileSync(path.join(oldDir, 'observations.jsonl'), 'utf8').trim().split('\n').filter(Boolean).map(JSON.parse),
        registry: JSON.parse(fs.readFileSync(path.join(oldDir, 'registry_delta.json'), 'utf8')),
        metadata: JSON.parse(fs.readFileSync(path.join(oldDir, 'metadata.json'), 'utf8')),
        publication: clone(manifest.publication_metadata),
    };
    mutation(data);
    const bytes = {
        'identity_decisions.jsonl': jsonl(data.decisions),
        'observations.jsonl': jsonl(data.observations),
        'registry_delta.json': canonicalBytes(data.registry),
        'metadata.json': canonicalBytes(data.metadata),
    };
    const artifacts = {
        'identity_decisions.jsonl': descriptorForBytes('identity_decisions.jsonl', bytes['identity_decisions.jsonl'], data.decisions.length),
        'observations.jsonl': descriptorForBytes('observations.jsonl', bytes['observations.jsonl'], data.observations.length, semanticObservationBytes(data.observations)),
        'registry_delta.json': descriptorForBytes('registry_delta.json', bytes['registry_delta.json'], data.registry.entries.length),
        'metadata.json': descriptorForBytes('metadata.json', bytes['metadata.json'], 1),
    };
    const fields = clone(manifest);
    for (const key of ['schema_version', 'transaction_id', 'logical_batch_key', 'logical_content_hash', 'batch_content_hash', 'transaction_content_hash', 'manifest_sha256']) delete fields[key];
    Object.assign(fields, { artifacts, source: data.metadata.source, publication_metadata: data.publication });
    const rebuilt = createManifest(fields);
    const finalManifest = retainTransactionId ? { ...rebuilt, transaction_id: transactionId } : rebuilt;
    if (retainTransactionId) { const unsigned = { ...finalManifest }; delete unsigned.manifest_sha256; finalManifest.manifest_sha256 = sha256Text(stableStringify(unsigned)); }
    for (const [name, content] of Object.entries(bytes)) { const file = path.join(oldDir, name); makeWritable(file); fs.writeFileSync(file, content); fs.chmodSync(file, 0o444); }
    for (const name of ['manifest.json', 'COMMITTED']) makeWritable(path.join(oldDir, name));
    fs.writeFileSync(path.join(oldDir, 'manifest.json'), canonicalBytes(finalManifest));
    fs.writeFileSync(path.join(oldDir, 'COMMITTED'), canonicalBytes(createCommittedMarker(rebuilt)));
    fs.chmodSync(path.join(oldDir, 'manifest.json'), 0o444); fs.chmodSync(path.join(oldDir, 'COMMITTED'), 0o444);
    if (!retainTransactionId && rebuilt.transaction_id !== transactionId) { const newDir = path.join(ctx.storeRoot, 'committed', rebuilt.transaction_id); fs.renameSync(oldDir, newDir); return rebuilt.transaction_id; }
    return transactionId;
}

test('production transaction reader reopens exact committed authority in a fresh process', t => {
    const ctx = setup(t); const result = publish(ctx, candidate(ctx));
    const program = "const r=require('./src/infrastructure/market_evidence/authorityReader');const s=r.openMarketEvidenceAuthoritySnapshot({storeRoot:process.argv[1],allocationArtifactPath:process.argv[2]});process.stdout.write(JSON.stringify({id:s.head_transaction_id,d:s.decisions.length,o:s.observations.length}))";
    const child = spawnSync(process.execPath, ['-e', program, ctx.storeRoot, ctx.allocationPath], { cwd: path.resolve(__dirname, '../../..'), encoding: 'utf8' });
    assert.equal(child.status, 0, child.stderr); assert.deepEqual(JSON.parse(child.stdout), { id: result.transaction_id, d: 1, o: 3 });
});

test('LIVE/offline entrypoint bootstraps internal allocation and shares publisher-owned T2', t => {
    const root = fs.mkdtempSync(path.join(os.tmpdir(), 'live-offline-transaction-v1-')); t.after(() => fs.rmSync(root, { recursive: true, force: true })); const fotmobRawText = fixtureRaw(); const oddsRawText = oddsRaw('live-event');
    const receiptEvidence = createVerifiedTestReceipt({ root: path.join(root, 'receipt'), rawText: oddsRawText, overrides: { capture_id: 'live-offline-capture', acquisition_mode: 'LIVE_CAPTURE' } }); const allocationArtifactPath = path.join(root, 'authority', 'allocation.json'); const storeRoot = path.join(root, 'authority', 'store');
    const result = publishOfflineMarketEvidence({ fotmobRawText, fotmobRawSha256: sha256Text(fotmobRawText), oddsRawText, receiptEvidence, allocationArtifactPath, storeRoot, knowledge_time: '2026-08-27T13:31:49Z' });
    assert.equal(result.published.status, 'COMMITTED'); assert.equal(result.freshAuthoritySnapshot.head_transaction_id, result.published.transaction_id); assert.notEqual(result.knowledge_time, '2026-08-27T13:31:49Z');
    const store = JSON.parse(fs.readFileSync(path.join(storeRoot, 'STORE.json'), 'utf8')); assert.ok(Date.parse(result.knowledge_time) >= Date.parse(store.authority_created_at));
});

test('offline pipeline retries a prior logical batch without binding it to a newer authority head', t => {
    const root = fs.mkdtempSync(path.join(os.tmpdir(), 'offline-non-head-retry-')); t.after(() => fs.rmSync(root, { recursive: true, force: true }));
    const fotmobRawText = fixtureRaw(); const allocationArtifactPath = path.join(root, 'authority', 'allocation.json'); const storeRoot = path.join(root, 'authority', 'store');
    const rawA = oddsRaw('retry-event', 2); const receiptA = createVerifiedTestReceipt({ root: path.join(root, 'receipt-a'), rawText: rawA, overrides: { capture_id: 'capture-a' } });
    const first = publishOfflineMarketEvidence({ fotmobRawText, fotmobRawSha256: sha256Text(fotmobRawText), oddsRawText: rawA, receiptEvidence: receiptA, allocationArtifactPath, storeRoot });
    const immediateRetryA = publishOfflineMarketEvidence({ fotmobRawText, fotmobRawSha256: sha256Text(fotmobRawText), oddsRawText: rawA, receiptEvidence: receiptA, allocationArtifactPath, storeRoot });
    assert.equal(immediateRetryA.published.reused, true); assert.equal(immediateRetryA.published.transaction_id, first.published.transaction_id);
    const rawB = oddsRaw('retry-event', 2.5); const receiptB = createVerifiedTestReceipt({ root: path.join(root, 'receipt-b'), rawText: rawB, overrides: { capture_id: 'capture-b' } });
    const second = publishOfflineMarketEvidence({ fotmobRawText, fotmobRawSha256: sha256Text(fotmobRawText), oddsRawText: rawB, receiptEvidence: receiptB, allocationArtifactPath, storeRoot });

    const fixturePath = path.join(root, 'fotmob-fixtures.html'); const rawAPath = path.join(root, 'odds-a.json'); fs.writeFileSync(fixturePath, fotmobRawText); fs.writeFileSync(rawAPath, rawA);
    const retryProgram = "const fs=require('node:fs');const {sha256Text}=require('./src/infrastructure/market_evidence/contracts');const {loadVerifiedCaptureReceipt}=require('./src/infrastructure/market_evidence/evidenceStore');const {publishOfflineMarketEvidence}=require('./src/infrastructure/market_evidence/offlinePipeline');const [fixturePath,rawPath,receiptPath,allocationArtifactPath,storeRoot]=process.argv.slice(1);const fotmobRawText=fs.readFileSync(fixturePath,'utf8');const oddsRawText=fs.readFileSync(rawPath,'utf8');const result=publishOfflineMarketEvidence({fotmobRawText,fotmobRawSha256:sha256Text(fotmobRawText),oddsRawText,receiptEvidence:loadVerifiedCaptureReceipt({receiptPath}),allocationArtifactPath,storeRoot});process.stdout.write(JSON.stringify({transaction_id:result.published.transaction_id,reused:result.published.reused,head_transaction_id:result.freshAuthoritySnapshot.head_transaction_id,observation_count:result.observation_count,knowledge_time:result.knowledge_time,authority_head_knowledge_time:result.authority_head_knowledge_time}));";
    const child = spawnSync(process.execPath, ['-e', retryProgram, fixturePath, rawAPath, path.join(root, 'receipt-a', 'receipts', 'capture-a.json'), allocationArtifactPath, storeRoot], { cwd: path.resolve(__dirname, '../../..'), encoding: 'utf8' });
    assert.equal(child.status, 0, child.stderr); const retry = JSON.parse(child.stdout);

    assert.equal(retry.reused, true); assert.equal(retry.transaction_id, first.published.transaction_id);
    assert.equal(retry.head_transaction_id, second.published.transaction_id);
    assert.equal(retry.observation_count, second.observation_count);
    assert.equal(retry.knowledge_time, first.knowledge_time);
    assert.equal(retry.authority_head_knowledge_time, second.knowledge_time);
    const retryB = publishOfflineMarketEvidence({ fotmobRawText, fotmobRawSha256: sha256Text(fotmobRawText), oddsRawText: rawB, receiptEvidence: receiptB, allocationArtifactPath, storeRoot });
    const repeatedRetryA = publishOfflineMarketEvidence({ fotmobRawText, fotmobRawSha256: sha256Text(fotmobRawText), oddsRawText: rawA, receiptEvidence: receiptA, allocationArtifactPath, storeRoot });
    assert.equal(retryB.published.reused, true); assert.equal(retryB.published.transaction_id, second.published.transaction_id);
    assert.equal(repeatedRetryA.published.reused, true); assert.equal(repeatedRetryA.published.transaction_id, first.published.transaction_id);
    assert.equal(openMarketEvidenceAuthoritySnapshot({ storeRoot, allocationArtifactPath }).capture_bindings.length, 2);
});

test('published batch verification accepts A after B advances the authority head', t => {
    const ctx = setup(t); const firstCandidate = candidate(ctx, { captureId: 'interleave-a' }); const first = publish(ctx, firstCandidate);
    const secondCandidate = candidate(ctx, { captureId: 'interleave-b', rawText: oddsRaw('provider-event', 2.5) }); const second = publish(ctx, secondCandidate);
    const freshAuthoritySnapshot = openMarketEvidenceAuthoritySnapshot({ storeRoot: ctx.storeRoot, allocationArtifactPath: ctx.allocationPath });

    assert.equal(freshAuthoritySnapshot.head_transaction_id, second.transaction_id);
    assert.equal(verifyPublishedLogicalBatch({ storeRoot: ctx.storeRoot, candidate: firstCandidate, published: first, freshAuthoritySnapshot }), first.snapshot.head_knowledge_time);
    assert.equal(freshAuthoritySnapshot.observations.length, 6);
});

test('fully rehashed invented decision identity cannot self-authorize observations', t => {
    const ctx = setup(t); const result = publish(ctx, candidate(ctx));
    rewritePackage(ctx, result.transaction_id, data => {
        data.decisions[0].identity_decision_id = `idn_${'f'.repeat(64)}`;
        for (const row of data.observations) row.identity_decision_id = data.decisions[0].identity_decision_id;
        for (const entry of data.registry.entries) if (entry.kind === 'event') entry.identity_decision_id = data.decisions[0].identity_decision_id;
    });
    assert.throws(() => openMarketEvidenceAuthoritySnapshot({ storeRoot: ctx.storeRoot, allocationArtifactPath: ctx.allocationPath }), /deterministic identity is invalid/);
});

test('fully rehashed decision governance forgeries fail closed independently', t => {
    const attacks = [
        data => { data.decisions[0].candidate_provider = 'evil-provider'; },
        data => { data.decisions[0].candidate_provider_event_id = 'wrong-event'; },
        data => { data.decisions[0].canonical_event_id = `evt_${'e'.repeat(32)}`; },
        data => { data.decisions[0].ruleset_version = 'evil-ruleset/v1'; },
        data => { data.decisions[0].resolver_version = 'evil-resolver/v1'; },
    ];
    for (const attack of attacks) {
        const ctx = setup(t); const result = publish(ctx, candidate(ctx)); rewritePackage(ctx, result.transaction_id, attack);
        assert.throws(() => openMarketEvidenceAuthoritySnapshot({ storeRoot: ctx.storeRoot, allocationArtifactPath: ctx.allocationPath }), /identity decision|canonical event|canonical_event_id|ruleset|resolver|provider/);
    }
});

test('observation must bind exact active MATCHED decision and registry governance', t => {
    for (const attack of [
        data => { data.observations[0].provider = 'evil-provider'; },
        data => { data.observations[0].provider_event_id = 'wrong-event'; },
        data => { data.observations[0].canonical_event_id = `evt_${'e'.repeat(32)}`; },
        data => { data.observations[0].identity_ruleset_version = 'evil-ruleset/v1'; },
    ]) {
        const ctx = setup(t); const result = publish(ctx, candidate(ctx)); rewritePackage(ctx, result.transaction_id, attack);
        assert.throws(() => openMarketEvidenceAuthoritySnapshot({ storeRoot: ctx.storeRoot, allocationArtifactPath: ctx.allocationPath }), /observation/);
    }
});

test('fully rehashed registry and receipt provenance forgeries fail semantic reopen', t => {
    const registryContext = setup(t); const registryResult = publish(registryContext, candidate(registryContext));
    rewritePackage(registryContext, registryResult.transaction_id, data => { const event = data.registry.entries.find(entry => entry.kind === 'event'); event.canonical_id = `evt_${'e'.repeat(32)}`; delete data.registry.result_registry_state_sha256; });
    assert.throws(() => openMarketEvidenceAuthoritySnapshot({ storeRoot: registryContext.storeRoot, allocationArtifactPath: registryContext.allocationPath }), /observation event registry governance is invalid/);
    const receiptContext = setup(t); const receiptResult = publish(receiptContext, candidate(receiptContext));
    rewritePackage(receiptContext, receiptResult.transaction_id, data => { data.metadata.capture_receipt.http_status = 201; });
    assert.throws(() => openMarketEvidenceAuthoritySnapshot({ storeRoot: receiptContext.storeRoot, allocationArtifactPath: receiptContext.allocationPath }), /capture receipt does not bind transaction source/);
});

test('transaction identity binds T2 and fully rehashed backdating predates STORE trust root', t => {
    const ctx = setup(t); const result = publish(ctx, candidate(ctx)); const oldT2 = '2026-08-27T13:31:49Z';
    rewritePackage(ctx, result.transaction_id, data => { data.publication.knowledge_time = oldT2; for (const row of data.observations) row.projection_available_at = oldT2; }, { retainTransactionId: true });
    assert.throws(() => openMarketEvidenceAuthoritySnapshot({ storeRoot: ctx.storeRoot, allocationArtifactPath: ctx.allocationPath }), /transaction content identity is invalid/);
    const second = setup(t); const committed = publish(second, candidate(second));
    rewritePackage(second, committed.transaction_id, data => { data.publication.knowledge_time = oldT2; for (const row of data.observations) row.projection_available_at = oldT2; });
    assert.throws(() => openMarketEvidenceAuthoritySnapshot({ storeRoot: second.storeRoot, allocationArtifactPath: second.allocationPath }), /predates its immutable STORE.json authority/);
});

test('capture acquisition identity is unique while RAW content identity remains reusable', t => {
    const ctx = setup(t); const sameRaw = oddsRaw(); const firstCandidate = candidate(ctx, { captureId: 'same-capture', rawText: sameRaw }); const first = publish(ctx, firstCandidate);
    const retry = publish(ctx, candidate(ctx, { captureId: 'same-capture', rawText: sameRaw })); assert.equal(retry.reused, true); assert.equal(retry.transaction_id, first.transaction_id);
    assert.throws(() => candidate(ctx, { captureId: 'same-capture', rawText: oddsRaw('provider-event', 2.5) }), /capture identity is already bound/);
    assert.throws(() => candidate(ctx, { captureId: 'same-capture', rawText: sameRaw, receiptRootTag: '-conflict', receiptOverrides: { request_started_at: '2026-08-27T13:31:21Z' } }), /capture identity is already bound/);
    const second = publish(ctx, candidate(ctx, { captureId: 'different-capture', rawText: sameRaw })); assert.notEqual(second.transaction_id, first.transaction_id);
    assert.equal(openMarketEvidenceAuthoritySnapshot({ storeRoot: ctx.storeRoot, allocationArtifactPath: ctx.allocationPath }).capture_bindings.length, 2);
});

test('plain duck-typed receipt evidence and persisted receipt tamper are rejected', t => {
    const ctx = setup(t); const fake = { receipt: { capture_id: 'fake' }, receipt_sha256: 'a'.repeat(64) };
    assert.throws(() => buildProspectiveMarketEvidenceTransaction({ authoritySnapshot: openMarketEvidenceAuthoritySnapshot({ storeRoot: ctx.storeRoot, allocationArtifactPath: ctx.allocationPath }), universe: ctx.universe, oddsRawText: oddsRaw(), captureReceipt: fake }), /verified persisted capture receipt/);
    const receiptRoot = path.join(ctx.root, 'tampered-receipt'); createVerifiedTestReceipt({ root: receiptRoot, rawText: oddsRaw(), overrides: { capture_id: 'tampered' } }); const receiptPath = path.join(receiptRoot, 'receipts', 'tampered.json'); makeWritable(receiptPath); fs.appendFileSync(receiptPath, ' '); fs.chmodSync(receiptPath, 0o444);
    assert.throws(() => loadVerifiedCaptureReceipt({ receiptPath }), /invalid JSON|canonical serialization/);
});

test('committed whitelist, symlinks and staging residue fail closed', t => {
    const ctx = setup(t); const result = publish(ctx, candidate(ctx)); const txDir = path.join(ctx.storeRoot, 'committed', result.transaction_id);
    fs.writeFileSync(path.join(txDir, 'extra'), 'x'); assert.throws(() => openMarketEvidenceAuthoritySnapshot({ storeRoot: ctx.storeRoot, allocationArtifactPath: ctx.allocationPath }), /unexpected file set/);
    const ctx2 = setup(t); const staging = path.join(ctx2.storeRoot, '.staging', `tx_${'a'.repeat(64)}`); fs.mkdirSync(staging); fs.writeFileSync(path.join(staging, 'COMMITTED'), '{}\n'); assert.equal(openMarketEvidenceAuthoritySnapshot({ storeRoot: ctx2.storeRoot, allocationArtifactPath: ctx2.allocationPath }).head_transaction_id, null);
    const target = path.join(ctx2.root, 'target'); fs.mkdirSync(target); fs.symlinkSync(target, path.join(ctx2.storeRoot, 'committed', `tx_${'b'.repeat(64)}`)); assert.throws(() => openMarketEvidenceAuthoritySnapshot({ storeRoot: ctx2.storeRoot, allocationArtifactPath: ctx2.allocationPath }), /transaction directory/);
});
