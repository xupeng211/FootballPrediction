'use strict';

const assert = require('node:assert/strict');
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const { spawn, spawnSync } = require('node:child_process');
const test = require('node:test');
const { seedFotMobFixtureUniverse } = require('../../../src/infrastructure/fixture_universe/FixtureUniverse');
const { persistVerifiedAllocationAuthority } = require('../../../src/infrastructure/fixture_universe/AllocationAuthorityArtifact');
const { sha256Text } = require('../../../src/infrastructure/market_evidence/contracts');
const { bootstrapMarketEvidenceTransactionStore } = require('../../../src/infrastructure/market_evidence/transactionStore');
const { openMarketEvidenceAuthoritySnapshot } = require('../../../src/infrastructure/market_evidence/authorityReader');
const { buildProspectiveMarketEvidenceTransaction } = require('../../../src/infrastructure/market_evidence/prospectiveBatch');
const { publishProspectiveMarketEvidenceTransaction } = require('../../../src/infrastructure/market_evidence/atomicPublisher');
const { createVerifiedTestReceipt } = require('../../helpers/market_evidence_authority');

function fixtures() {
    const allMatches = Array.from({ length: 380 }, (_, index) => ({ id: String(930000 + index), home: { name: index ? `H${index}` : 'Arsenal' }, away: { name: index ? `A${index}` : 'Chelsea' }, status: { utcTime: index ? `2026-10-${String((index % 28) + 1).padStart(2, '0')}T15:00:00Z` : '2026-09-12T15:00:00Z' } }));
    return `<script id="__NEXT_DATA__" type="application/json">${JSON.stringify({ query: { season: '2026/2027' }, props: { pageProps: { details: { id: 47 }, fixtures: { allMatches } } } })}</script>`;
}
function setup(t) {
    const root = fs.mkdtempSync(path.join(os.tmpdir(), 'atomic-publisher-')); t.after(() => fs.rmSync(root, { recursive: true, force: true }));
    const raw = fixtures(); const initial = seedFotMobFixtureUniverse({ rawHtml: raw, rawSha256: sha256Text(raw), manifest: { raw_file_relative_path: 'fixture.html' }, mode: 'INITIAL_SEED' });
    const allocationPath = path.join(root, 'allocation.json'); const persisted = persistVerifiedAllocationAuthority({ artifactPath: allocationPath, allocationAuthority: initial.allocationAuthority });
    const universe = seedFotMobFixtureUniverse({ rawHtml: raw, rawSha256: sha256Text(raw), allocation: persisted.allocationSnapshot, allocationAuthority: persisted.allocationAuthority, manifest: { raw_file_relative_path: 'fixture.html' }, mode: 'REPLAY' });
    const storeRoot = path.join(root, 'store'); bootstrapMarketEvidenceTransactionStore({ storeRoot, allocationArtifactPath: allocationPath, bootstrapMetadata: { test: 'atomic' } });
    const fixturePath = path.join(root, 'fixture.html'); fs.writeFileSync(fixturePath, raw);
    return { root, universe, storeRoot, allocationPath, fixturePath };
}
function candidate(ctx, id = 'e0', unknown = false, captureTag = '') {
    const home = unknown ? 'Unknown FC' : 'Arsenal';
    const event = { id, sport_key: 'soccer_epl', home_team: home, away_team: 'Chelsea', commence_time: '2026-09-12T15:00:00Z', bookmakers: [{ key: 'book', title: 'Book', markets: [{ key: 'h2h', outcomes: [{ name: home, price: 2 }, { name: 'Draw', price: 3 }, { name: 'Chelsea', price: 4 }] }] }] };
    const oddsRawText = JSON.stringify([event]); const captureId = `capture-${id}-${unknown ? 'q' : 'm'}${captureTag}`;
    const captureReceipt = createVerifiedTestReceipt({ root: path.join(ctx.root, 'receipt-sources', captureId), rawText: oddsRawText, overrides: { capture_id: captureId } });
    return buildProspectiveMarketEvidenceTransaction({ authoritySnapshot: openMarketEvidenceAuthoritySnapshot({ storeRoot: ctx.storeRoot, allocationArtifactPath: ctx.allocationPath }), universe: ctx.universe, oddsRawText, captureReceipt });
}
function publish(ctx, candidateValue, extra = {}) { return publishProspectiveMarketEvidenceTransaction({ storeRoot: ctx.storeRoot, allocationArtifactPath: ctx.allocationPath, candidate: candidateValue, ...extra }); }
function concurrentInput(ctx, captureId, eventId = 'e0', price = 2) {
    const event = { id: eventId, sport_key: 'soccer_epl', home_team: 'Arsenal', away_team: 'Chelsea', commence_time: '2026-09-12T15:00:00Z', bookmakers: [{ key: 'book', title: 'Book', markets: [{ key: 'h2h', outcomes: [{ name: 'Arsenal', price }, { name: 'Draw', price: 3 }, { name: 'Chelsea', price: 4 }] }] }] };
    const raw = JSON.stringify([event]); const sourceRoot = path.join(ctx.root, 'concurrent-inputs', captureId); createVerifiedTestReceipt({ root: sourceRoot, rawText: raw, overrides: { capture_id: captureId } });
    const rawPath = path.join(sourceRoot, `${captureId}.raw.json`); fs.writeFileSync(rawPath, raw); return { rawPath, receiptPath: path.join(sourceRoot, 'receipts', `${captureId}.json`) };
}
function runConcurrentPublisher(ctx, input, barrier, label) {
    const program = `const fs=require('node:fs');const path=require('node:path');const {loadVerifiedAllocationAuthority}=require('./src/infrastructure/fixture_universe/AllocationAuthorityArtifact');const {seedFotMobFixtureUniverse}=require('./src/infrastructure/fixture_universe/FixtureUniverse');const {sha256Text}=require('./src/infrastructure/market_evidence/contracts');const {loadVerifiedCaptureReceipt}=require('./src/infrastructure/market_evidence/evidenceStore');const {openMarketEvidenceAuthoritySnapshot}=require('./src/infrastructure/market_evidence/authorityReader');const {buildProspectiveMarketEvidenceTransaction}=require('./src/infrastructure/market_evidence/prospectiveBatch');const {publishProspectiveMarketEvidenceTransaction}=require('./src/infrastructure/market_evidence/atomicPublisher');const [storeRoot,allocationPath,fixturePath,receiptPath,rawPath,barrier,label]=process.argv.slice(1);try{const allocation=loadVerifiedAllocationAuthority({artifactPath:allocationPath});const rawHtml=fs.readFileSync(fixturePath,'utf8');const universe=seedFotMobFixtureUniverse({rawHtml,rawSha256:sha256Text(rawHtml),allocation:allocation.allocationSnapshot,allocationAuthority:allocation.allocationAuthority,mode:'REPLAY'});const oddsRawText=fs.readFileSync(rawPath,'utf8');const captureReceipt=loadVerifiedCaptureReceipt({receiptPath});const authoritySnapshot=openMarketEvidenceAuthoritySnapshot({storeRoot,allocationArtifactPath:allocationPath});const candidate=buildProspectiveMarketEvidenceTransaction({authoritySnapshot,universe,oddsRawText,captureReceipt});fs.writeFileSync(path.join(barrier,label),'ready');while(fs.readdirSync(barrier).length<2)Atomics.wait(new Int32Array(new SharedArrayBuffer(4)),0,0,10);const result=publishProspectiveMarketEvidenceTransaction({storeRoot,allocationArtifactPath:allocationPath,candidate});process.stdout.write(JSON.stringify({ok:true,id:result.transaction_id,reused:result.reused}));}catch(error){process.stdout.write(JSON.stringify({ok:false,message:error.message,code:error.code||null}));process.exitCode=2;}`;
    return new Promise(resolve => { const child = spawn(process.execPath, ['-e', program, ctx.storeRoot, ctx.allocationPath, ctx.fixturePath, input.receiptPath, input.rawPath, barrier, label], { cwd: path.resolve(__dirname, '../../..') }); let stdout = ''; let stderr = ''; child.stdout.on('data', chunk => { stdout += chunk; }); child.stderr.on('data', chunk => { stderr += chunk; }); child.on('close', status => resolve({ status, stdout, stderr })); });
}

test('VALID_CANDIDATE_ATOMIC_PUBLISH_PASS and IDENTICAL_TRANSACTION_IDEMPOTENT', t => {
    const ctx = setup(t); const c = candidate(ctx); const one = publish(ctx, c);
    assert.equal(one.status, 'COMMITTED'); assert.equal(one.snapshot.head_transaction_id, one.transaction_id); assert.equal(one.snapshot.observations.length, 3);
    assert.notEqual(one.transaction_id, c.transaction_id, 'publisher-owned T2 must enter authoritative transaction identity');
    const originalT2 = one.snapshot.head_knowledge_time; const two = publish(ctx, c);
    assert.equal(two.reused, true); assert.equal(two.transaction_id, one.transaction_id); assert.equal(two.snapshot.head_knowledge_time, originalT2);
});
test('SECOND_STAGING_WRITE_FAILURE_ZERO_AUTHORITY', t => {
    const ctx = setup(t); const c = candidate(ctx); const before = openMarketEvidenceAuthoritySnapshot({ storeRoot: ctx.storeRoot, allocationArtifactPath: ctx.allocationPath });
    assert.throws(() => publish(ctx, c, { fault: 'observations.jsonl' }), /injected failure/);
    const after = openMarketEvidenceAuthoritySnapshot({ storeRoot: ctx.storeRoot, allocationArtifactPath: ctx.allocationPath });
    assert.equal(after.state_hash, before.state_hash); assert.equal(fs.readdirSync(path.join(ctx.storeRoot, 'committed')).length, 0); assert.equal(fs.readdirSync(path.join(ctx.storeRoot, '.staging')).length, 1);
});
test('STALE_PARENT_TRANSACTION_REJECTED and PRE_RENAME_FAILURE_ZERO_AUTHORITY', t => {
    const ctx = setup(t); const c = candidate(ctx); assert.throws(() => publish(ctx, c, { fault: 'before-rename' }), /injected failure/);
    assert.equal(openMarketEvidenceAuthoritySnapshot({ storeRoot: ctx.storeRoot, allocationArtifactPath: ctx.allocationPath }).head_transaction_id, null);
    const fresh = candidate(ctx, 'fresh'); publish(ctx, fresh); assert.throws(() => publish(ctx, c), /staging residue|authoritative head/);
});
test('all pre-rename write, fsync, staging-reopen and rename failures leave zero authority', t => {
    for (const fault of ['identity_decisions.jsonl', 'manifest.json', 'COMMITTED', 'identity_decisions.jsonl:fsync', 'manifest.json:fsync', 'COMMITTED:fsync', 'staging-directory-fsync', 'staging-tamper', 'before-rename', 'rename']) {
        const ctx = setup(t); const c = candidate(ctx); const before = openMarketEvidenceAuthoritySnapshot({ storeRoot: ctx.storeRoot, allocationArtifactPath: ctx.allocationPath });
        assert.throws(() => publish(ctx, c, { fault }));
        const after = openMarketEvidenceAuthoritySnapshot({ storeRoot: ctx.storeRoot, allocationArtifactPath: ctx.allocationPath });
        assert.equal(after.state_hash, before.state_hash, fault); assert.equal(after.head_transaction_id, null, fault); assert.equal(fs.readdirSync(path.join(ctx.storeRoot, 'committed')).length, 0, fault);
    }
});
test('post-rename parent fsync error is authoritatively resolved as full committed transaction', t => {
    const ctx = setup(t); const c = candidate(ctx); const result = publish(ctx, c, { fault: 'committed-directory-fsync' });
    assert.equal(result.status, 'COMMITTED'); assert.equal(result.snapshot.head_transaction_id, result.transaction_id); assert.equal(result.snapshot.observations.length, 3);
});
test('all final reader failures after rename produce COMMIT_OUTCOME_UNKNOWN without rollback', t => {
    for (const fault of ['final-reader-io', 'final-reader-tamper']) {
        const ctx = setup(t); const c = candidate(ctx); let error;
        try { publish(ctx, c, { fault }); } catch (caught) { error = caught; }
        assert.equal(error?.code, 'COMMIT_OUTCOME_UNKNOWN'); assert.match(error.transaction_id, /^tx_[a-f0-9]{64}$/); assert.equal(error.logical_batch_key, c.logical_batch_key); assert.ok(error.cause); assert.match(error.resolution, /reopen/i);
        assert.equal(fs.readdirSync(path.join(ctx.storeRoot, 'committed')).length, 1, 'post-rename authority must never be deleted');
        if (fault === 'final-reader-io') {
            const reopened = openMarketEvidenceAuthoritySnapshot({ storeRoot: ctx.storeRoot, allocationArtifactPath: ctx.allocationPath }); assert.equal(reopened.head_transaction_id, error.transaction_id);
            const retry = publish(ctx, c); assert.equal(retry.reused, true); assert.equal(retry.transaction_id, error.transaction_id);
        }
    }
});
test('MATCHED_QUARANTINED_MATCHED_ACROSS_TRANSACTIONS', t => {
    const ctx = setup(t); const one = candidate(ctx); publish(ctx, one); const two = candidate(ctx, 'e0', true); publish(ctx, two); const three = candidate(ctx, 'e0', false, '-recover'); const third = publish(ctx, three);
    const snapshot = openMarketEvidenceAuthoritySnapshot({ storeRoot: ctx.storeRoot, allocationArtifactPath: ctx.allocationPath });
    assert.equal(snapshot.decisions.length, 3); assert.equal(two.identity_decisions[0].supersedes_decision_id, one.identity_decisions[0].identity_decision_id); assert.equal(three.identity_decisions[0].supersedes_decision_id, two.identity_decisions[0].identity_decision_id);
    assert.equal(snapshot.latestDecision('the-odds-api', 'e0').decision, 'MATCHED'); assert.equal(snapshot.activeMatched('the-odds-api', 'e0').identity_decision_id, three.identity_decisions[0].identity_decision_id); assert.equal(snapshot.head_transaction_id, third.transaction_id); assert.equal(two.observations.length, 0);
});
test('CROSS_PROCESS_POST_COMMIT_REOPEN', t => {
    const ctx = setup(t); const result = publish(ctx, candidate(ctx));
    const program = "const r=require('./src/infrastructure/market_evidence/authorityReader');const s=r.openMarketEvidenceAuthoritySnapshot({storeRoot:process.argv[1],allocationArtifactPath:process.argv[2]});process.stdout.write(JSON.stringify({id:s.head_transaction_id,state:s.state_hash,decisions:s.decisions.length,observations:s.observations.length}))";
    const child = spawnSync(process.execPath, ['-e', program, ctx.storeRoot, ctx.allocationPath], { cwd: path.resolve(__dirname, '../../..'), encoding: 'utf8' });
    assert.equal(child.status, 0, child.stderr); assert.deepEqual(JSON.parse(child.stdout), { id: result.transaction_id, state: result.snapshot.state_hash, decisions: 1, observations: 3 });
});
test('real cross-process identical writers commit once and reuse one authoritative transaction', async t => {
    const ctx = setup(t); const input = concurrentInput(ctx, 'identical-capture'); const barrier = path.join(ctx.root, 'identical-barrier'); fs.mkdirSync(barrier);
    const results = await Promise.all([runConcurrentPublisher(ctx, input, barrier, 'a'), runConcurrentPublisher(ctx, input, barrier, 'b')]);
    assert.deepEqual(results.map(row => row.status), [0, 0], results.map(row => row.stderr).join('\n')); const payloads = results.map(row => JSON.parse(row.stdout)); assert.equal(new Set(payloads.map(row => row.id)).size, 1); assert.equal(payloads.some(row => row.reused), true);
    const snapshot = openMarketEvidenceAuthoritySnapshot({ storeRoot: ctx.storeRoot, allocationArtifactPath: ctx.allocationPath }); assert.equal(snapshot.head_sequence, 1); assert.equal(fs.readdirSync(path.join(ctx.storeRoot, 'committed')).length, 1);
});
test('real cross-process competing writers produce one head and one stale-parent rejection', async t => {
    const ctx = setup(t); const first = concurrentInput(ctx, 'competing-a', 'event-a', 2); const second = concurrentInput(ctx, 'competing-b', 'event-b', 2.5); const barrier = path.join(ctx.root, 'competing-barrier'); fs.mkdirSync(barrier);
    const results = await Promise.all([runConcurrentPublisher(ctx, first, barrier, 'a'), runConcurrentPublisher(ctx, second, barrier, 'b')]); const payloads = results.map(row => JSON.parse(row.stdout));
    assert.equal(payloads.filter(row => row.ok).length, 1); assert.equal(payloads.filter(row => !row.ok && /authoritative head/.test(row.message)).length, 1);
    const snapshot = openMarketEvidenceAuthoritySnapshot({ storeRoot: ctx.storeRoot, allocationArtifactPath: ctx.allocationPath }); assert.equal(snapshot.head_sequence, 1); assert.equal(fs.readdirSync(path.join(ctx.storeRoot, 'committed')).length, 1);
});
