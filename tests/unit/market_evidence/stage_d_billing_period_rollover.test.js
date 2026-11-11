'use strict';

process.env.NODE_ENV = 'test';
const assert = require('node:assert/strict');
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const test = require('node:test');
const ops = require('../../../src/infrastructure/market_evidence/stageDOperations');
const { stableStringify, sha256Text } = require('../../../src/infrastructure/market_evidence/contracts');
const cli = require('../../../scripts/ops/stage_d_quota_adjudication');
const bytes = value => `${stableStringify(value)}\n`;
const hash = value => sha256Text(bytes(value));
const auth = ops.createStageDTestRuntimeAuthorization();
const source = ops.resolveStageDGitSourceBinding({ testRuntimeAuthorization: auth });
const ACCOUNT = 'a'.repeat(64);
const OCT_NOW = '2026-10-13T01:00:00Z';

function config(period) {
    const month = Number(period.slice(5));
    const end = month === 12 ? `${Number(period.slice(0, 4)) + 1}-01` : `${period.slice(0, 4)}-${String(month + 1).padStart(2, '0')}`;
    return { ...JSON.parse(fs.readFileSync(path.resolve(__dirname, '../../../config/stage_d_quota_budget.json'), 'utf8')), billing_period_id: period, period_start_at: `${period}-01T00:00:00Z`, period_end_at: `${end}-01T00:00:00Z`, quota_evidence_source: 'synthetic Owner approval; not production evidence' };
}

function attempt(ctx, id, time, quota = null) {
    ops.recordRequestIntent({ ledgerRoot: ctx.ledgerRoot, requestId: id, runId: `run-${id}`, createdAt: `${time}00Z` });
    ops.markTransmissionStarted({ ledgerRoot: ctx.ledgerRoot, requestId: id, transmittedAt: `${time}01Z` });
    ops.markRequestTerminal({ ledgerRoot: ctx.ledgerRoot, requestId: id, terminalState: quota ? 'RESPONSE_RECEIVED' : id === 'lost-quota' ? 'POST_RESPONSE_PROCESSING_FAILURE' : 'TRANSPORT_FAILURE_AFTER_POSSIBLE_TRANSMISSION', at: `${time}02Z`, providerQuota: quota, errorClassification: quota ? null : id === 'lost-quota' ? 'PROVIDER_QUOTA_RECONCILIATION_FAILED' : 'SYNTHETIC_TRANSPORT_FAILURE' });
}

function snapshot(ctx) {
    return new Map([path.join(ctx.ledgerRoot, 'REQUEST_ACCOUNTING_EPOCH.json'), ...fs.readdirSync(path.join(ctx.ledgerRoot, 'entries')).map(name => path.join(ctx.ledgerRoot, 'entries', name)), ...fs.readdirSync(ctx.trustRoot).map(name => path.join(ctx.trustRoot, name))].map(file => [file, fs.readFileSync(file)]));
}

function unchanged(before) {
    for (const [file, value] of before) assert.deepEqual(fs.readFileSync(file), value, file);
}

function setup(t, { oldHeaders = false } = {}) {
    const root = fs.mkdtempSync(path.join(os.tmpdir(), 'stage-d-rollover-synthetic-'));
    assert.ok(root.startsWith(`${os.tmpdir()}/stage-d-rollover-synthetic-`));
    const ctx = { root, ledgerRoot: path.join(root, 'ledger'), trustRoot: path.join(root, 'trust') };
    fs.mkdirSync(ctx.trustRoot, { mode: 0o700 });
    ops.initializeRequestAccountingEpoch({ ledgerRoot: ctx.ledgerRoot, authoritySnapshot: { head_transaction_id: `tx_${'c'.repeat(64)}`, state_hash: 'd'.repeat(64) }, epochId: 'sde_synthetic-rollover', startedAt: '2026-09-08T05:56:56Z' });
    t.after(() => fs.rmSync(root, { recursive: true, force: true }));
    for (let i = 0; i < 4; i++) attempt(ctx, i === 3 ? 'lost-quota' : `old-${i}`, `2026-09-08T06:0${i}:`);
    ctx.previousConfig = config('2026-09');
    if (oldHeaders) attempt(ctx, 'old-success', '2026-09-10T06:00:', ops.reconcileProviderQuotaHeaders({ headers: { 'x-requests-used': '20', 'x-requests-remaining': '480', 'x-requests-last': '1' }, quotaConfig: ctx.previousConfig, expectedRequestCostCredits: 1, localConsumedAfterRequest: 5 }));
    const ledger = ops.readRequestLedger(ctx);
    const v1 = { ...ops.createStageDQuotaAdjudication({ ledger, quotaConfig: ctx.previousConfig, quotaConfigSha256: hash(ctx.previousConfig), historicalRequestId: 'lost-quota', sourceMainSha: source.source_main_sha, sourceMainTreeSha: source.source_main_tree_sha, testRuntimeAuthorization: auth, adjudicatedAt: '2026-09-11T01:00:00Z', adjudicationId: 'sqa_synthetic-v1' }), source_main_sha: '1'.repeat(40), source_main_tree_sha: '2'.repeat(40) };
    ctx.v1 = v1;
    ctx.v1Hash = hash(v1);
    ctx.v1Path = path.join(ctx.trustRoot, 'stage-d-quota-adjudication-synthetic-v1.json');
    ops.persistStageDQuotaAdjudication({ artifactPath: ctx.v1Path, ledgerRoot: ctx.ledgerRoot, runLockTrustRoot: ctx.trustRoot, artifact: v1 });
    ctx.prior = ops.createStageDQuotaAdjudicationSuccessor({ ledger, quotaConfig: ctx.previousConfig, quotaConfigSha256: hash(ctx.previousConfig), predecessor: v1, predecessorSha256: ctx.v1Hash, sourceMainSha: source.source_main_sha, sourceMainTreeSha: source.source_main_tree_sha, testRuntimeAuthorization: auth, adjudicatedAt: '2026-09-11T02:00:00Z', adjudicationId: 'sqa_synthetic-v2' });
    ctx.priorHash = hash(ctx.prior);
    ctx.priorPath = path.join(ctx.trustRoot, `stage-d-quota-adjudication-successor-${ctx.v1Hash}.json`);
    ops.persistStageDQuotaAdjudication({ artifactPath: ctx.priorPath, ledgerRoot: ctx.ledgerRoot, runLockTrustRoot: ctx.trustRoot, artifact: ctx.prior });
    ctx.nextConfig = config('2026-10');
    ctx.now = OCT_NOW;
    return ctx;
}

function evidence(ctx) {
    return { schema_version: ops.QUOTA_ROLLOVER_EVIDENCE_SCHEMA_VERSION, approval_status: 'OWNER_APPROVED_BILLING_PERIOD_ROLLOVER', provider: 'the-odds-api', previous_billing_period_id: ctx.previousConfig.billing_period_id, billing_period_id: ctx.nextConfig.billing_period_id, previous_account_identity_sha256: ACCOUNT, account_identity_sha256: ACCOUNT, quota_config_sha256: hash(ctx.nextConfig), previous_adjudication_sha256: ctx.priorHash, reset_rule: 'MONTHLY_FIRST_DAY_00_UTC', provider_period_start_at: ctx.nextConfig.period_start_at, provider_period_end_at: ctx.nextConfig.period_end_at, observed_at: ctx.now, approved_at: ctx.now, reported_used: 0, reported_remaining: 500, account_evidence_reference: 'synthetic-owner-account-declaration', account_evidence_sha256: 'e'.repeat(64) };
}

function args(ctx, overrides = {}) {
    const ownerEvidence = evidence(ctx);
    return { ledger: ops.readRequestLedger(ctx), quotaConfig: ctx.nextConfig, quotaConfigSha256: hash(ctx.nextConfig), previousQuotaConfigBytes: bytes(ctx.previousConfig), predecessor: ctx.prior, predecessorSha256: ctx.priorHash, previousV1: ctx.v1, previousV1Sha256: ctx.v1Hash, ownerEvidence, ownerEvidenceSha256: hash(ownerEvidence), sourceMainSha: source.source_main_sha, sourceMainTreeSha: source.source_main_tree_sha, testRuntimeAuthorization: auth, adjudicatedAt: ctx.now, adjudicationId: `sqa_rollover-${ctx.nextConfig.billing_period_id}`, ...overrides };
}

function publish(ctx, artifact) {
    const owner = artifact.rollover.owner_evidence;
    const ownerPath = path.join(ctx.trustRoot, `stage-d-billing-period-evidence-${hash(owner)}.json`);
    if (!fs.existsSync(ownerPath)) fs.writeFileSync(ownerPath, bytes(owner), { flag: 'wx', mode: 0o400 });
    const artifactPath = path.join(ctx.trustRoot, ops.quotaRolloverFileName(artifact));
    const persisted = ops.persistStageDQuotaAdjudication({ artifactPath, ledgerRoot: ctx.ledgerRoot, runLockTrustRoot: ctx.trustRoot, artifact });
    return { artifactPath, ...persisted };
}

function budget(ctx, artifact, overrides = {}) {
    return ops.assertRequestBudget({ ledger: ops.readRequestLedger(ctx), quotaConfig: ctx.nextConfig, quotaConfigSha256: hash(ctx.nextConfig), quotaAdjudication: artifact, quotaAdjudicationSha256: hash(artifact), expectedSourceMainSha: source.source_main_sha, expectedSourceMainTreeSha: source.source_main_tree_sha, testRuntimeAuthorization: auth, runId: 'new-period-single-cycle', now: ctx.now, ...overrides });
}

function coldRead(ctx, artifactPath) {
    return ops.readBoundQuotaAdjudication({ quotaAdjudicationPath: artifactPath, ledgerRoot: ctx.ledgerRoot, runLockTrustRoot: ctx.trustRoot, ledger: ops.readRequestLedger(ctx), quotaConfig: ctx.nextConfig, quotaConfigSha256: hash(ctx.nextConfig), expectedSourceMainSha: source.source_main_sha, expectedSourceMainTreeSha: source.source_main_tree_sha, testRuntimeAuthorization: auth, now: ctx.now });
}

test('September four consumed/UNKNOWN remain byte-identical; October admits exactly one credit offline', t => {
    const ctx = setup(t), before = snapshot(ctx);
    const artifact = ops.createStageDQuotaRollover(args(ctx));
    const saved = publish(ctx, artifact);
    const admitted = budget(ctx, coldRead(ctx, saved.artifactPath).value);
    assert.equal(admitted.monthly_used, 0);
    assert.equal(admitted.conservative_remaining_after_request, 449);
    assert.equal(artifact.local_consumed_requests, 4);
    assert.equal(artifact.local_consumed_quota_units, 0);
    assert.equal(artifact.provider_quota_actual_effect, 'UNKNOWN');
    assert.equal(artifact.rollover.previous_adjudication.conservative_effective_provider_usage, 4);
    const ledger = ops.readRequestLedger(ctx);
    assert.equal(ledger.epoch.historical_pre_epoch_request_total, 'AT_LEAST_2_CONFIRMED');
    assert.equal(ledger.epoch.historical_pre_epoch_exact_total, 'UNKNOWN');
    assert.equal(ops.ledgerUsageSummary(ledger).consumed_request_count, 4);
    assert.equal(coldRead(ctx, saved.artifactPath).sha256, saved.sha256);
    unchanged(before);
});

test('October to November inherits an appended consumed request; old monthly headers never become November quota', t => {
    const ctx = setup(t);
    const october = ops.createStageDQuotaRollover(args(ctx));
    publish(ctx, october);
    const historical = snapshot(ctx);
    const quota = ops.reconcileProviderQuotaHeaders({ headers: { 'x-requests-used': '1', 'x-requests-remaining': '499', 'x-requests-last': '1' }, quotaConfig: ctx.nextConfig, expectedRequestCostCredits: 1, localConsumedAfterRequest: 1 });
    attempt(ctx, 'october-success', '2026-10-13T02:00:', quota);
    ctx.previousConfig = ctx.nextConfig;
    ctx.nextConfig = config('2026-11');
    ctx.prior = october;
    ctx.priorHash = hash(october);
    ctx.v1 = null;
    ctx.v1Hash = null;
    ctx.now = '2026-11-01T01:00:00Z';
    const november = ops.createStageDQuotaRollover(args(ctx));
    const saved = publish(ctx, november);
    assert.equal(november.local_consumed_requests, 5);
    assert.equal(november.local_consumed_quota_units, 0);
    assert.equal(november.last_trusted_provider_quota_evidence, null);
    assert.equal(budget(ctx, coldRead(ctx, saved.artifactPath).value).monthly_used, 0);
    assert.equal(november.rollover.previous_adjudication.provider_quota_actual_effect, 'UNKNOWN');
    unchanged(historical);
});

test('old September trusted usage of 20 is retained historically without consuming October allowance', t => {
    const ctx = setup(t, { oldHeaders: true });
    const artifact = ops.createStageDQuotaRollover(args(ctx));
    assert.equal(artifact.rollover.previous_adjudication.conservative_effective_provider_usage, 20);
    assert.equal(artifact.last_trusted_provider_quota_evidence, null);
    assert.equal(budget(ctx, artifact).conservative_provider_usage, 0);
});

const badInputs = [
    ['missing Owner evidence', input => ({ ...input, ownerEvidence: null })],
    ['wrong predecessor SHA', input => ({ ...input, predecessorSha256: 'f'.repeat(64) })],
    ['missing v1 predecessor', input => ({ ...input, previousV1: null, previousV1Sha256: null })],
    ['wrong previous config bytes', input => ({ ...input, previousQuotaConfigBytes: bytes({ ...JSON.parse(input.previousQuotaConfigBytes), quota_evidence_source: 'changed' }) })],
    ['Owner config mismatch', input => { const ownerEvidence = { ...input.ownerEvidence, quota_config_sha256: 'f'.repeat(64) }; return { ...input, ownerEvidence, ownerEvidenceSha256: hash(ownerEvidence) }; }],
    ['Owner account mismatch', input => { const ownerEvidence = { ...input.ownerEvidence, account_identity_sha256: 'f'.repeat(64) }; return { ...input, ownerEvidence, ownerEvidenceSha256: hash(ownerEvidence) }; }],
    ['unapproved Owner evidence', input => { const ownerEvidence = { ...input.ownerEvidence, approval_status: 'NOT_AUTHORIZED' }; return { ...input, ownerEvidence, ownerEvidenceSha256: hash(ownerEvidence) }; }],
    ['wrong reset rule', input => { const ownerEvidence = { ...input.ownerEvidence, reset_rule: 'CALENDAR_AUTO_RESET' }; return { ...input, ownerEvidence, ownerEvidenceSha256: hash(ownerEvidence) }; }],
    ['stale account evidence', input => { const ownerEvidence = { ...input.ownerEvidence, observed_at: '2026-10-01T00:00:00Z' }; return { ...input, ownerEvidence, ownerEvidenceSha256: hash(ownerEvidence) }; }],
    ['old account evidence', input => { const ownerEvidence = { ...input.ownerEvidence, observed_at: '2026-09-30T23:59:59Z' }; return { ...input, ownerEvidence, ownerEvidenceSha256: hash(ownerEvidence) }; }],
    ['missing account evidence hash', input => { const ownerEvidence = { ...input.ownerEvidence, account_evidence_sha256: null }; return { ...input, ownerEvidence, ownerEvidenceSha256: hash(ownerEvidence) }; }],
    ['wrong source HEAD', input => ({ ...input, sourceMainSha: '9'.repeat(40) })],
    ['wrong source tree', input => ({ ...input, sourceMainTreeSha: '9'.repeat(40) })],
    ['empty replacement ledger', input => ({ ...input, ledger: { ...input.ledger, entries: [], requests: [], last_entry_hash: input.ledger.epoch.genesis_entry_hash } })],
    ['tampered old entry', input => { const ledger = structuredClone(input.ledger); ledger.entries[0].request.run_id = 'tampered'; return { ...input, ledger }; }],
    ['old v2 UNKNOWN removed', input => { const predecessor = { ...input.predecessor, provider_quota_actual_effect: 'ZERO' }; return { ...input, predecessor, predecessorSha256: hash(predecessor) }; }],
];
for (const [name, corrupt] of badInputs) {test(`rollover rejects ${name}`, t => {
    const ctx = setup(t), before = snapshot(ctx);
    assert.throws(() => ops.createStageDQuotaRollover(corrupt(args(ctx))));
    unchanged(before);
});}

for (const period of ['2026-09', '2026-08', '2026-11']) {test(`rollover rejects repeated/backward/skipped target ${period}`, t => {
    const ctx = setup(t);
    ctx.nextConfig = config(period);
    ctx.now = `${period}-13T01:00:00Z`;
    assert.throws(() => ops.createStageDQuotaRollover(args(ctx)), error => error.code === 'QUOTA_ROLLOVER_PERIOD_INVALID');
});}

const badArtifacts = [
    ['missing old tail', artifact => { artifact.rollover.previous_ledger_tail_sha256 = null; }],
    ['wrong old tail', artifact => { artifact.rollover.previous_ledger_tail_sha256 = 'f'.repeat(64); }],
    ['wrong epoch genesis', artifact => { artifact.rollover.epoch_genesis_hash = 'f'.repeat(64); }],
    ['historical count lowered', artifact => { artifact.rollover.historical_consumed_count = 0; }],
    ['historical UNKNOWN classification lowered', artifact => { artifact.rollover.historical_unknown_classification = 'NO_RISK'; }],
    ['UNKNOWN effect removed', artifact => { artifact.provider_quota_actual_effect = 'ZERO'; }],
    ['current config SHA mismatch', artifact => { artifact.quota_config_sha256 = 'f'.repeat(64); }],
    ['current source mismatch', artifact => { artifact.source_main_sha = 'f'.repeat(40); }],
];
for (const [name, corrupt] of badArtifacts) {test(`admission rejects ${name}`, t => {
    const ctx = setup(t), artifact = structuredClone(ops.createStageDQuotaRollover(args(ctx)));
    corrupt(artifact);
    assert.throws(() => budget(ctx, artifact));
});}

test('create-only namespace refuses duplicate, conflicting sibling and source refresh of a rollover', t => {
    const ctx = setup(t), artifact = ops.createStageDQuotaRollover(args(ctx));
    const saved = publish(ctx, artifact);
    assert.throws(() => publish(ctx, artifact), error => error.code === 'QUOTA_ADJUDICATION_CONFLICT');
    const sibling = ops.createStageDQuotaRollover(args(ctx, { adjudicationId: 'sqa_conflicting-sibling' }));
    assert.throws(() => publish(ctx, sibling), error => error.code === 'QUOTA_ADJUDICATION_CONFLICT');
    assert.throws(() => ops.createStageDQuotaAdjudicationSuccessor({ ...args(ctx), predecessor: artifact, predecessorSha256: hash(artifact) }));
    assert.equal(coldRead(ctx, saved.artifactPath).sha256, hash(artifact));
});

test('cold admission requires retained v1/v2 and immutable Owner evidence originals', t => {
    const ctx = setup(t), artifact = ops.createStageDQuotaRollover(args(ctx));
    const saved = publish(ctx, artifact);
    fs.renameSync(ctx.priorPath, `${ctx.priorPath}.saved`);
    assert.throws(() => coldRead(ctx, saved.artifactPath), error => error.code === 'QUOTA_ROLLOVER_LINEAGE_INVALID');
    fs.renameSync(`${ctx.priorPath}.saved`, ctx.priorPath);
    const ownerPath = path.join(ctx.trustRoot, `stage-d-billing-period-evidence-${artifact.rollover.owner_evidence_sha256}.json`);
    fs.chmodSync(ownerPath, 0o600);
    assert.throws(() => coldRead(ctx, saved.artifactPath), error => error.code === 'MUTABLE_EVIDENCE');
});

test('budget exhaustion, request cap and monthly expiry fail closed without transmission', t => {
    const ctx = setup(t);
    const ownerEvidence = { ...evidence(ctx), reported_used: 450, reported_remaining: 50 };
    const exhausted = ops.createStageDQuotaRollover(args(ctx, { ownerEvidence, ownerEvidenceSha256: hash(ownerEvidence) }));
    assert.throws(() => budget(ctx, exhausted), error => error.code === 'REQUEST_BUDGET_DENIED');
    const artifact = ops.createStageDQuotaRollover(args(ctx));
    assert.throws(() => budget(ctx, artifact, { requestedUnits: 2 }), error => error.code === 'REQUEST_BUDGET_DENIED');
    assert.throws(() => budget(ctx, artifact, { now: '2026-11-01T00:00:00Z' }), error => error.code === 'INVALID_QUOTA_CONFIGURATION');
    assert.throws(() => budget(ctx, artifact, { now: '2026-09-30T23:59:59Z' }), error => error.code === 'INVALID_QUOTA_CONFIGURATION');
});

test('same-month provider headers keep exact one-credit monotonicity; wrong old-month counters rejected', () => {
    const current = config('2026-10');
    const quota = ops.reconcileProviderQuotaHeaders({ headers: { 'x-requests-used': '1', 'x-requests-remaining': '499', 'x-requests-last': '1' }, quotaConfig: current, expectedRequestCostCredits: 1, localConsumedAfterRequest: 1 });
    assert.equal(ops.reconcileProviderQuotaHeaders({ headers: { 'x-requests-used': '2', 'x-requests-remaining': '498', 'x-requests-last': '1' }, quotaConfig: current, expectedRequestCostCredits: 1, localConsumedAfterRequest: 2, previousProviderQuota: quota }).reported_used, 2);
    assert.throws(() => ops.reconcileProviderQuotaHeaders({ headers: { 'x-requests-used': '20', 'x-requests-remaining': '480', 'x-requests-last': '1' }, quotaConfig: current, expectedRequestCostCredits: 1, localConsumedAfterRequest: 2, previousProviderQuota: quota }), error => error.code === 'PROVIDER_QUOTA_RECONCILIATION_FAILED');
});

test('rollover artifact grants no Gate 3 authorization and live cycle remains disabled', async t => {
    const ctx = setup(t), artifact = ops.createStageDQuotaRollover(args(ctx));
    const before = snapshot(ctx);
    await assert.rejects(ops.executeStageDOneCycle({ operationRoot: ctx.ledgerRoot, ledgerRoot: ctx.ledgerRoot, quotaConfig: ctx.nextConfig, quotaAdjudication: artifact, runId: 'unauthorized-live-run', requestId: 'unauthorized-live-request', clock: () => ctx.now }), error => error.code === 'STAGE_D_NOT_AUTHORIZED');
    unchanged(before);
});

test('CLI advertises bounded paired rollover evidence; no provider option is accepted', () => {
    assert.match(cli.helpText(), /--owner-rollover-evidence/);
    assert.throws(() => cli.parseArgs(['--provider', 'anything']));
    assert.equal(cli.parseArgs(['--help']).help, true);
});

test('existing offline CLI persists rollover and existing Candidate binds its exact hash (synthetic source/authority only)', t => {
    const ctx = setup(t), artifact = ops.createStageDQuotaRollover(args(ctx));
    const owner = artifact.rollover.owner_evidence;
    const ownerPath = path.join(ctx.trustRoot, `stage-d-billing-period-evidence-${hash(owner)}.json`);
    fs.writeFileSync(ownerPath, bytes(owner), { flag: 'wx', mode: 0o400 });
    const previousConfigPath = path.join(ctx.root, 'september-quota.json');
    const quotaConfigPath = path.join(ctx.root, 'october-quota.json');
    fs.writeFileSync(previousConfigPath, bytes(ctx.previousConfig));
    fs.writeFileSync(quotaConfigPath, bytes(ctx.nextConfig));
    const actualResolve = ops.resolveStageDGitSourceBinding;
    const actualCreate = ops.createStageDQuotaRollover;
    ops.createStageDQuotaRollover = input => actualCreate({ ...input, testRuntimeAuthorization: auth });
    t.after(() => { ops.resolveStageDGitSourceBinding = actualResolve; ops.createStageDQuotaRollover = actualCreate; });
    // 合成源码身份 stand-in：生产 resolver 的 clean/origin-main 校验由已有回归覆盖。
    ops.resolveStageDGitSourceBinding = () => source;
    delete require.cache[require.resolve('../../../scripts/ops/stage_d_quota_adjudication')];
    const isolatedCli = require('../../../scripts/ops/stage_d_quota_adjudication');
    const artifactPath = path.join(ctx.trustRoot, ops.quotaRolloverFileName(artifact));
    const flags = { '--ledger-root': ctx.ledgerRoot, '--quota-config': quotaConfigPath, '--run-lock-trust-root': ctx.trustRoot, '--output': artifactPath, '--historical-request-id': 'lost-quota', '--source-main-sha': source.source_main_sha, '--source-main-tree': source.source_main_tree_sha, '--adjudication-id': artifact.adjudication_id, '--adjudicated-at': ctx.now, '--predecessor': ctx.priorPath, '--predecessor-sha256': ctx.priorHash, '--previous-quota-config': previousConfigPath, '--owner-rollover-evidence': ownerPath, '--previous-v1': ctx.v1Path, '--previous-v1-sha256': ctx.v1Hash };
    const output = [];
    const write = process.stdout.write;
    process.stdout.write = value => { output.push(String(value)); return true; };
    try { isolatedCli.main(Object.entries(flags).flat()); } finally { process.stdout.write = write; }
    assert.equal(JSON.parse(output.join('')).artifact_sha256, hash(artifact));
    const authorityReader = require('../../../src/infrastructure/market_evidence/authorityReader');
    const candidate = require('../../../src/infrastructure/market_evidence/stageDGate3Candidate');
    const actualAuthority = authorityReader.openMarketEvidenceAuthoritySnapshot;
    const actualBudget = ops.assertRequestBudget;
    const actualRead = ops.readBoundQuotaAdjudication;
    authorityReader.openMarketEvidenceAuthoritySnapshot = () => ({ head_transaction_id: `tx_${'c'.repeat(64)}`, state_hash: 'd'.repeat(64), observations: [] });
    // 只向既有 API 传递模块私有 test capability，真实 quota/budget/lineage 校验不 mock。
    ops.assertRequestBudget = input => actualBudget({ ...input, testRuntimeAuthorization: auth });
    ops.readBoundQuotaAdjudication = input => actualRead({ ...input, testRuntimeAuthorization: auth });
    t.after(() => {
        ops.resolveStageDGitSourceBinding = actualResolve;
        ops.assertRequestBudget = actualBudget;
        ops.readBoundQuotaAdjudication = actualRead;
        authorityReader.openMarketEvidenceAuthoritySnapshot = actualAuthority;
        delete require.cache[require.resolve('../../../scripts/ops/stage_d_quota_adjudication')];
    });
    const authorityRoot = path.join(ctx.root, 'synthetic-authority');
    const candidateDirectory = path.join(ctx.root, 'synthetic-candidates');
    fs.mkdirSync(authorityRoot, { mode: 0o700 });
    fs.mkdirSync(candidateDirectory, { mode: 0o700 });
    const allocationArtifactPath = path.join(ctx.root, 'synthetic-allocation.json');
    const fixtureUniverseRawPath = path.join(ctx.root, 'synthetic-fixture.raw');
    fs.writeFileSync(path.join(authorityRoot, 'STORE.json'), 'synthetic authority');
    fs.writeFileSync(allocationArtifactPath, 'synthetic allocation');
    fs.writeFileSync(fixtureUniverseRawPath, 'synthetic fixture; no real RAW');
    const input = { authorityRoot, candidateDirectory, allocationArtifactPath, fixtureUniverseRawPath, ledgerRoot: ctx.ledgerRoot, quotaConfigPath, quotaAdjudicationPath: artifactPath, runLockTrustRoot: ctx.trustRoot };
    const result = candidate.prepareGate3Candidate(input, { now: ctx.now, id: 'a'.repeat(32) });
    assert.equal(result.candidate.runtime_bindings.quota_adjudication_sha256, hash(artifact));
    assert.equal(result.candidate.runtime_bindings.consumed_requests, 4);
    assert.equal(result.candidate.candidate_status, 'PREPARED_NOT_AUTHORIZED');
    assert.equal(result.candidate.provider_boundary.live_provider_requests, 0);
    assert.equal(candidate.validateGate3Candidate({ candidatePath: result.path, expectedSha256: result.sha256, input, now: ctx.now }).sha256, result.sha256);
});

test('after October append, its exact-generation admission is stale and cannot double-use the same quota decision', t => {
    const ctx = setup(t), artifact = ops.createStageDQuotaRollover(args(ctx));
    publish(ctx, artifact);
    attempt(ctx, 'october-consumed', '2026-10-13T02:00:');
    assert.throws(() => budget(ctx, artifact), error => error.code === 'QUOTA_ADJUDICATION_STALE');
});

test('future adjacent periods cross year boundaries and keep the original September UNKNOWN chain', t => {
    const ctx = setup(t);
    for (const nextPeriod of ['2026-11', '2026-12', '2027-01']) {
        const artifact = ops.createStageDQuotaRollover(args(ctx));
        publish(ctx, artifact);
        ctx.previousConfig = ctx.nextConfig;
        ctx.nextConfig = config(nextPeriod);
        ctx.prior = artifact;
        ctx.priorHash = hash(artifact);
        ctx.v1 = null;
        ctx.v1Hash = null;
        ctx.now = `${nextPeriod}-01T01:00:00Z`;
    }
    const january = ops.createStageDQuotaRollover(args(ctx));
    const saved = publish(ctx, january);
    assert.equal(budget(ctx, coldRead(ctx, saved.artifactPath).value).monthly_used, 0);
    assert.equal(january.local_consumed_requests, 4);
    const ownerEvidence = { ...evidence(ctx), account_identity_sha256: 'f'.repeat(64), previous_account_identity_sha256: 'f'.repeat(64) };
    assert.throws(() => ops.createStageDQuotaRollover(args(ctx, { ownerEvidence, ownerEvidenceSha256: hash(ownerEvidence) })), error => error.code === 'QUOTA_ROLLOVER_EVIDENCE_MISMATCH');
});

test('two competing create-only rollover writers yield one immutable winner', async t => {
    const ctx = setup(t);
    const artifacts = ['a', 'b'].map(id => ops.createStageDQuotaRollover(args(ctx, { adjudicationId: `sqa_competing-${id}` })));
    const owner = artifacts[0].rollover.owner_evidence;
    fs.writeFileSync(path.join(ctx.trustRoot, `stage-d-billing-period-evidence-${hash(owner)}.json`), bytes(owner), { flag: 'wx', mode: 0o400 });
    const artifactPath = path.join(ctx.trustRoot, ops.quotaRolloverFileName(artifacts[0]));
    const { spawn } = require('node:child_process');
    const operationPath = require.resolve('../../../src/infrastructure/market_evidence/stageDOperations');
    const script = `const fs=require('node:fs'); const ops=require(process.argv[1]); const input=JSON.parse(fs.readFileSync(process.argv[2], 'utf8')); process.stdout.write('READY\\n'); process.stdin.once('data',()=>{try { const result=ops.persistStageDQuotaAdjudication(input); process.stdout.write(JSON.stringify(result)); } catch(error) { process.stderr.write(error.code || error.message); process.exitCode=1; }});`;
    const writers = artifacts.map((artifact, index) => {
        const inputPath = path.join(ctx.root, `writer-${index}.json`);
        fs.writeFileSync(inputPath, JSON.stringify({ artifactPath, artifact, ledgerRoot: ctx.ledgerRoot, runLockTrustRoot: ctx.trustRoot }));
        const child = spawn(process.execPath, ['-e', script, operationPath, inputPath], { stdio: ['pipe', 'pipe', 'pipe'] });
        let stdout = '', stderr = '';
        const finished = new Promise((resolve, reject) => { child.once('error', reject); child.once('close', code => resolve({ code, stdout, stderr })); });
        const ready = new Promise((resolve, reject) => {
            child.stdout.on('data', data => { stdout += data.toString(); if (stdout.startsWith('READY\n')) resolve(); });
            child.stderr.on('data', data => { stderr += data.toString(); });
            child.once('error', reject);
            child.once('exit', code => { if (!stdout.startsWith('READY\n')) reject(new Error(`writer failed before barrier: ${code} ${stderr}`)); });
        });
        t.after(() => { if (child.exitCode === null) child.kill(); });
        return { child, ready, finished };
    });
    await Promise.all(writers.map(writer => writer.ready));
    for (const writer of writers) writer.child.stdin.end('GO');
    const results = await Promise.all(writers.map(writer => writer.finished));
    assert.deepEqual(results.map(result => result.code).sort(), [0, 1]);
    assert.match(results.find(result => result.code === 1).stderr, /QUOTA_ADJUDICATION_CONFLICT/);
    const winner = coldRead(ctx, artifactPath);
    assert.ok(artifacts.some(artifact => hash(artifact) === winner.sha256));
    assert.equal(fs.statSync(artifactPath).mode & 0o777, 0o400);
});

test('rollover rejects a pending historical intent and a second unresolved divergence', t => {
    const ctx = setup(t);
    ops.recordRequestIntent({ ledgerRoot: ctx.ledgerRoot, requestId: 'pending-september', runId: 'pending-run', createdAt: '2026-09-30T01:00:00Z' });
    assert.throws(() => ops.createStageDQuotaRollover(args(ctx)), error => error.code === 'QUOTA_ROLLOVER_LEDGER_MISMATCH');
    ops.markTransmissionStarted({ ledgerRoot: ctx.ledgerRoot, requestId: 'pending-september', transmittedAt: '2026-09-30T01:00:01Z' });
    ops.markRequestTerminal({ ledgerRoot: ctx.ledgerRoot, requestId: 'pending-september', terminalState: 'POST_RESPONSE_PROCESSING_FAILURE', at: '2026-09-30T01:00:02Z', errorClassification: 'PROVIDER_QUOTA_RECONCILIATION_FAILED' });
    assert.throws(() => ops.createStageDQuotaRollover(args(ctx)), error => error.code === 'QUOTA_ADJUDICATION_EVIDENCE_INVALID');
});

test('appended previous-period entries must have a valid hash chain and cannot backdate before the predecessor', t => {
    const ctx = setup(t);
    attempt(ctx, 'late-september', '2026-09-30T01:00:');
    const input = args(ctx);
    assert.equal(ops.createStageDQuotaRollover(input).local_consumed_requests, 5);
    const ledger = structuredClone(input.ledger);
    ledger.entries.at(-1).recorded_at = '2026-09-30T02:00:00Z';
    assert.throws(() => ops.createStageDQuotaRollover({ ...input, ledger }), error => error.code === 'TAMPERED_LEDGER');
    const another = setup(t);
    attempt(another, 'backdated-september', '2026-09-10T01:00:');
    assert.throws(() => ops.createStageDQuotaRollover(args(another)), error => error.code === 'QUOTA_ROLLOVER_LEDGER_MISMATCH');
});
