'use strict';

process.env.NODE_ENV = 'test';

const assert = require('node:assert/strict');
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const test = require('node:test');
const { sha256Text, stableStringify } = require('../../../src/infrastructure/market_evidence/contracts');
const { resolveGitSourceBinding } = require('../../../scripts/ops/stage_d_quota_adjudication');
const {
    initializeRequestAccountingEpoch,
    readRequestLedger,
    recordRequestIntent,
    markTransmissionStarted,
    markRequestTerminal,
    ledgerUsageSummary,
    assertRequestBudget,
    createStageDTestQuotaConfiguration,
    createStageDQuotaAdjudication,
    readBoundQuotaAdjudication,
    persistStageDQuotaAdjudication,
    resolveStageDGitSourceBinding,
} = require('../../../src/infrastructure/market_evidence/stageDOperations');

const AUTHORITY = Object.freeze({
    head_transaction_id: `tx_${'a'.repeat(64)}`,
    state_hash: 'b'.repeat(64),
    observations: Object.freeze([]),
});
const START = '2026-09-08T05:56:56Z';
const NOW = '2026-09-08T08:00:00Z';
const SOURCE_BINDING = resolveStageDGitSourceBinding();
const SOURCE_MAIN_SHA = SOURCE_BINDING.source_main_sha;
const SOURCE_MAIN_TREE_SHA = SOURCE_BINDING.source_main_tree_sha;

function canonicalSha(value) {
    return sha256Text(`${stableStringify(value)}\n`);
}

function quotaConfig(overrides = {}) {
    const value = {
        schema_version: 'footballprediction-stage-d-quota-budget/v2',
        provider: 'the-odds-api',
        subscription_tier: 'starter_free',
        quota_evidence_class: 'OWNER_DECLARATION_PLUS_PUBLIC_PLAN_EVIDENCE',
        quota_evidence_verified: true,
        quota_evidence_source: 'networkless quota-adjudication test fixture',
        billing_period_id: '2026-09',
        period_start_at: '2026-09-01T00:00:00Z',
        period_end_at: '2026-10-01T00:00:00Z',
        monthly_quota_limit: 20,
        reserved_safety_buffer: 2,
        automated_spend_limit: 17,
        max_requests_per_stage_d_run: 1,
        max_requests_per_day: null,
        stop_before_quota_exhaustion_threshold: 1,
        configured_markets: ['h2h'],
        configured_regions: ['uk'],
        market_count: 1,
        region_count: 1,
        expected_request_cost_credits: 1,
        max_provider_requests_per_cycle: 1,
        quota_reset_rule: 'PROVIDER_RECONCILED__NO_UNVERIFIED_AUTOMATIC_RESET',
        automatic_zero_on_calendar_change: false,
        historical_pre_epoch_request_total: 'AT_LEAST_2_CONFIRMED',
        historical_pre_epoch_exact_total: 'UNKNOWN',
        post_epoch_usage_source: 'read_from_durable_request_ledger',
        ...overrides,
    };
    if (!Object.prototype.hasOwnProperty.call(overrides, 'automated_spend_limit')) {
        value.automated_spend_limit = value.monthly_quota_limit - value.reserved_safety_buffer - value.stop_before_quota_exhaustion_threshold;
    }
    return createStageDTestQuotaConfiguration(value, { now: NOW });
}

function setup(t) {
    const root = fs.mkdtempSync(path.join(os.tmpdir(), 'stage-d-quota-adjudication-'));
    const ledgerRoot = path.join(root, 'ledger');
    const trustRoot = path.join(root, 'trust');
    fs.mkdirSync(trustRoot, { mode: 0o700 });
    initializeRequestAccountingEpoch({
        ledgerRoot,
        authoritySnapshot: AUTHORITY,
        startedAt: START,
        epochId: `sde_${'e'.repeat(64)}`,
    });
    t.after(() => fs.rmSync(root, { recursive: true, force: true }));
    return { root, ledgerRoot, trustRoot };
}

function createDivergence(ctx, requestId = 'historical-quota-request', runId = 'historical-quota-run') {
    recordRequestIntent({ ledgerRoot: ctx.ledgerRoot, requestId, runId, createdAt: '2026-09-08T06:00:00Z' });
    markTransmissionStarted({ ledgerRoot: ctx.ledgerRoot, requestId, transmittedAt: '2026-09-08T06:00:01Z' });
    markRequestTerminal({
        ledgerRoot: ctx.ledgerRoot,
        requestId,
        terminalState: 'POST_RESPONSE_PROCESSING_FAILURE',
        at: '2026-09-08T06:00:02Z',
        errorClassification: 'PROVIDER_QUOTA_RECONCILIATION_FAILED',
    });
    return readRequestLedger({ ledgerRoot: ctx.ledgerRoot });
}

function buildArtifact(ctx, config, ledger = readRequestLedger({ ledgerRoot: ctx.ledgerRoot })) {
    const artifact = createStageDQuotaAdjudication({
        ledger,
        quotaConfig: config,
        quotaConfigSha256: canonicalSha(config),
        historicalRequestId: 'historical-quota-request',
        sourceMainSha: SOURCE_MAIN_SHA,
        sourceMainTreeSha: SOURCE_MAIN_TREE_SHA,
        adjudicatedAt: NOW,
        adjudicationId: 'sqa_test-current-epoch',
    });
    return Object.freeze({
        artifact,
        quotaConfigSha256: canonicalSha(config),
        artifactSha256: canonicalSha(artifact),
    });
}

function budgetArgs(ctx, config, binding, overrides = {}) {
    return {
        ledger: readRequestLedger({ ledgerRoot: ctx.ledgerRoot }),
        quotaConfig: config,
        quotaConfigSha256: binding?.quotaConfigSha256 || canonicalSha(config),
        quotaAdjudication: binding?.artifact || null,
        quotaAdjudicationSha256: binding?.artifactSha256 || null,
        expectedSourceMainSha: SOURCE_MAIN_SHA,
        expectedSourceMainTreeSha: SOURCE_MAIN_TREE_SHA,
        runId: 'next-offline-run',
        now: NOW,
        ...overrides,
    };
}

test('runtime source binding resolves a real commit/tree pair and rejects unknown or unrelated objects', t => {
    const currentSource = resolveStageDGitSourceBinding();
    const runtimeSource = resolveGitSourceBinding({
        sourceMainSha: currentSource.source_main_sha,
        sourceMainTreeSha: currentSource.source_main_tree_sha,
    });
    assert.match(runtimeSource.source_main_sha, /^[a-f0-9]{40}$/);
    assert.match(runtimeSource.source_main_tree_sha, /^[a-f0-9]{40}$/);
    assert.throws(
        () => resolveGitSourceBinding({ sourceMainSha: 'f'.repeat(40), sourceMainTreeSha: runtimeSource.source_main_tree_sha }),
        error => error.code === 'INVALID_AUTHORIZATION',
    );
    assert.throws(
        () => resolveGitSourceBinding({ sourceMainSha: runtimeSource.source_main_sha, sourceMainTreeSha: 'f'.repeat(40) }),
        error => error.code === 'INVALID_AUTHORIZATION',
    );
    const ctx = setup(t);
    const config = quotaConfig();
    createDivergence(ctx);
    const binding = buildArtifact(ctx, config);
    assert.throws(
        () => assertRequestBudget(budgetArgs(ctx, config, binding, {
            expectedSourceMainSha: 'a'.repeat(40),
            expectedSourceMainTreeSha: 'b'.repeat(40),
        })),
        error => error.code === 'QUOTA_ADJUDICATION_SOURCE_MISMATCH',
    );
});

test('unresolved provider quota divergence remains a hard admission block without adjudication', t => {
    const ctx = setup(t);
    const config = quotaConfig();
    const ledger = createDivergence(ctx);
    assert.equal(ledgerUsageSummary(ledger).consumed_request_count, 1);
    assert.throws(
        () => assertRequestBudget({ ledger, quotaConfig: config, runId: 'next-offline-run', now: NOW }),
        error => error.code === 'PROVIDER_QUOTA_RECONCILIATION_REQUIRED',
    );
});

test('source provenance binds Git commit and tree object IDs, not content SHA-256 values', t => {
    const ctx = setup(t);
    const config = quotaConfig();
    createDivergence(ctx);
    const binding = buildArtifact(ctx, config);
    assert.equal(binding.artifact.source_main_sha, SOURCE_MAIN_SHA);
    assert.equal(binding.artifact.source_main_tree_sha, SOURCE_MAIN_TREE_SHA);
    assert.throws(
        () => createStageDQuotaAdjudication({
            ledger: readRequestLedger({ ledgerRoot: ctx.ledgerRoot }),
            quotaConfig: config,
            quotaConfigSha256: canonicalSha(config),
            historicalRequestId: 'historical-quota-request',
            sourceMainSha: 'e'.repeat(64),
            sourceMainTreeSha: SOURCE_MAIN_TREE_SHA,
            adjudicatedAt: NOW,
            adjudicationId: 'sqa_test-invalid-source-sha',
        }),
        error => error.code === 'INVALID_AUTHORIZATION',
    );
});

test('artifact source binding is checked against the trusted runtime pair at admission', t => {
    const ctx = setup(t);
    const config = quotaConfig();
    createDivergence(ctx);
    const binding = buildArtifact(ctx, config);
    const forged = {
        ...binding.artifact,
        source_main_sha: 'a'.repeat(40),
        source_main_tree_sha: 'b'.repeat(40),
    };
    assert.throws(
        () => assertRequestBudget(budgetArgs(ctx, config, {
            ...binding,
            artifact: forged,
            artifactSha256: canonicalSha(forged),
        })),
        error => error.code === 'QUOTA_ADJUDICATION_SOURCE_MISMATCH',
    );
});

test('valid conservative adjudication permits one request while preserving UNKNOWN provider effect', t => {
    const ctx = setup(t);
    const config = quotaConfig();
    createDivergence(ctx);
    const binding = buildArtifact(ctx, config);
    const decision = assertRequestBudget(budgetArgs(ctx, config, binding));
    assert.equal(decision.allowed, true);
    assert.equal(decision.monthly_used, 1);
    assert.equal(decision.conservative_provider_usage, 1);
    assert.equal(decision.conservative_remaining_after_request, 15);
    assert.equal(binding.artifact.provider_quota_actual_effect, 'UNKNOWN');
    assert.equal(binding.artifact.provider_exact_effect_known, false);
});

test('budget admission requires a hash binding whenever an adjudication is supplied', t => {
    const ctx = setup(t);
    const config = quotaConfig();
    createDivergence(ctx);
    const binding = buildArtifact(ctx, config);
    assert.throws(
        () => assertRequestBudget({
            ...budgetArgs(ctx, config, binding),
            quotaAdjudicationSha256: null,
        }),
        error => error.code === 'QUOTA_ADJUDICATION_HASH_MISMATCH',
    );
});

test('adjudication never lowers local consumption and budget ceiling still protects the reserve', t => {
    const ctx = setup(t);
    const config = quotaConfig();
    createDivergence(ctx);
    const binding = buildArtifact(ctx, config);
    const lowered = {
        ...binding.artifact,
        local_consumed_quota_units: 0,
        conservative_effective_provider_usage: 0,
        conservative_remaining_automatic_budget: config.automated_spend_limit,
    };
    assert.throws(
        () => assertRequestBudget(budgetArgs(ctx, config, { ...binding, artifact: lowered, artifactSha256: canonicalSha(lowered) })),
        error => error.code === 'QUOTA_ADJUDICATION_LEDGER_MISMATCH',
    );

    const atCeiling = {
        ...binding.artifact,
        conservative_effective_provider_usage: config.automated_spend_limit,
        conservative_remaining_automatic_budget: 0,
    };
    assert.throws(
        () => assertRequestBudget(budgetArgs(ctx, config, { ...binding, artifact: atCeiling, artifactSha256: canonicalSha(atCeiling) })),
        error => error.code === 'REQUEST_BUDGET_DENIED',
    );
});

test('wrong epoch, period, request, ledger generation, config hash and artifact hash fail closed', t => {
    const ctx = setup(t);
    const config = quotaConfig();
    createDivergence(ctx);
    const binding = buildArtifact(ctx, config);
    const cases = [
        ['epoch', { accounting_epoch_id: `sde_${'f'.repeat(64)}` }, 'QUOTA_ADJUDICATION_EPOCH_MISMATCH'],
        ['period', { billing_period_id: '2026-10' }, 'QUOTA_ADJUDICATION_PERIOD_MISMATCH'],
        ['request', { historical_request_id: 'other-request' }, 'QUOTA_ADJUDICATION_STALE'],
        ['ledger', { ledger_last_entry_hash: 'f'.repeat(64) }, 'QUOTA_ADJUDICATION_STALE'],
    ];
    for (const [label, changes, code] of cases) {
        const artifact = { ...binding.artifact, ...changes };
        assert.throws(
            () => assertRequestBudget(budgetArgs(ctx, config, { ...binding, artifact, artifactSha256: canonicalSha(artifact) })),
            error => error.code === code,
            label,
        );
    }
    assert.throws(
        () => assertRequestBudget(budgetArgs(ctx, config, binding, { quotaConfigSha256: 'f'.repeat(64) })),
        error => error.code === 'QUOTA_ADJUDICATION_CONFIG_MISMATCH',
    );
    assert.throws(
        () => assertRequestBudget(budgetArgs(ctx, config, { ...binding, artifactSha256: 'f'.repeat(64) })),
        error => error.code === 'QUOTA_ADJUDICATION_HASH_MISMATCH',
    );
});

test('malformed and stale adjudications fail after ledger changes', t => {
    const ctx = setup(t);
    const config = quotaConfig();
    createDivergence(ctx);
    const binding = buildArtifact(ctx, config);
    const malformed = { ...binding.artifact };
    delete malformed.provider_quota_actual_effect;
    assert.throws(
        () => assertRequestBudget(budgetArgs(ctx, config, { ...binding, artifact: malformed, artifactSha256: canonicalSha(malformed) })),
        error => error.code === 'INVALID_CONTRACT',
    );

    recordRequestIntent({ ledgerRoot: ctx.ledgerRoot, requestId: 'newer-http-failure', runId: 'newer-run', createdAt: '2026-09-08T07:00:00Z' });
    markTransmissionStarted({ ledgerRoot: ctx.ledgerRoot, requestId: 'newer-http-failure', transmittedAt: '2026-09-08T07:00:01Z' });
    markRequestTerminal({ ledgerRoot: ctx.ledgerRoot, requestId: 'newer-http-failure', terminalState: 'HTTP_FAILURE_AFTER_TRANSMISSION', at: '2026-09-08T07:00:02Z', errorClassification: 'HTTP_403' });
    assert.throws(
        () => assertRequestBudget(budgetArgs(ctx, config, binding)),
        error => error.code === 'QUOTA_ADJUDICATION_STALE',
    );
});

test('persisted adjudication is immutable, hash-bound, path-safe, and rejects a competing current-period artifact', t => {
    const ctx = setup(t);
    const config = quotaConfig();
    createDivergence(ctx);
    const binding = buildArtifact(ctx, config);
    const artifactPath = path.join(ctx.trustRoot, 'stage-d-quota-adjudication-sqa_test-current-epoch.json');
    const persisted = persistStageDQuotaAdjudication({
        artifactPath,
        ledgerRoot: ctx.ledgerRoot,
        runLockTrustRoot: ctx.trustRoot,
        artifact: binding.artifact,
    });
    assert.equal(persisted.sha256, binding.artifactSha256);
    assert.equal(fs.lstatSync(artifactPath).mode & 0o777, 0o400);
    const loaded = readBoundQuotaAdjudication({
        quotaAdjudicationPath: artifactPath,
        ledgerRoot: ctx.ledgerRoot,
        runLockTrustRoot: ctx.trustRoot,
        expectedSha256: binding.artifactSha256,
        ledger: readRequestLedger({ ledgerRoot: ctx.ledgerRoot }),
        quotaConfig: config,
        quotaConfigSha256: binding.quotaConfigSha256,
        expectedSourceMainSha: SOURCE_MAIN_SHA,
        expectedSourceMainTreeSha: SOURCE_MAIN_TREE_SHA,
        now: NOW,
    });
    assert.equal(loaded.sha256, binding.artifactSha256);
    assert.equal(loaded.value.provider_quota_actual_effect, 'UNKNOWN');

    const loadedWithoutCallerHash = readBoundQuotaAdjudication({
        quotaAdjudicationPath: artifactPath,
        ledgerRoot: ctx.ledgerRoot,
        runLockTrustRoot: ctx.trustRoot,
        expectedSha256: null,
        ledger: readRequestLedger({ ledgerRoot: ctx.ledgerRoot }),
        quotaConfig: config,
        quotaConfigSha256: binding.quotaConfigSha256,
        expectedSourceMainSha: SOURCE_MAIN_SHA,
        expectedSourceMainTreeSha: SOURCE_MAIN_TREE_SHA,
        now: NOW,
    });
    assert.equal(loadedWithoutCallerHash.sha256, binding.artifactSha256);

    const competingPath = path.join(ctx.trustRoot, 'stage-d-quota-adjudication-sqa_competing.json');
    fs.writeFileSync(competingPath, `${stableStringify({ ...binding.artifact, adjudication_id: 'sqa_competing' })}\n`, { mode: 0o400 });
    fs.chmodSync(competingPath, 0o400);
    assert.throws(
        () => readBoundQuotaAdjudication({
            quotaAdjudicationPath: artifactPath,
            ledgerRoot: ctx.ledgerRoot,
            runLockTrustRoot: ctx.trustRoot,
            expectedSha256: binding.artifactSha256,
            ledger: readRequestLedger({ ledgerRoot: ctx.ledgerRoot }),
            quotaConfig: config,
            quotaConfigSha256: binding.quotaConfigSha256,
            expectedSourceMainSha: SOURCE_MAIN_SHA,
            expectedSourceMainTreeSha: SOURCE_MAIN_TREE_SHA,
            now: NOW,
        }),
        error => error.code === 'QUOTA_ADJUDICATION_CONFLICT',
    );
});

test('writable and symlink adjudication paths are rejected before admission', t => {
    const ctx = setup(t);
    const config = quotaConfig();
    createDivergence(ctx);
    const binding = buildArtifact(ctx, config);
    const artifactPath = path.join(ctx.trustRoot, 'stage-d-quota-adjudication-sqa_safe.json');
    persistStageDQuotaAdjudication({ artifactPath, ledgerRoot: ctx.ledgerRoot, runLockTrustRoot: ctx.trustRoot, artifact: binding.artifact });
    fs.chmodSync(artifactPath, 0o600);
    assert.throws(
        () => readBoundQuotaAdjudication({
            quotaAdjudicationPath: artifactPath,
            ledgerRoot: ctx.ledgerRoot,
            runLockTrustRoot: ctx.trustRoot,
            expectedSha256: binding.artifactSha256,
            ledger: readRequestLedger({ ledgerRoot: ctx.ledgerRoot }),
            quotaConfig: config,
            quotaConfigSha256: binding.quotaConfigSha256,
            expectedSourceMainSha: SOURCE_MAIN_SHA,
            expectedSourceMainTreeSha: SOURCE_MAIN_TREE_SHA,
            now: NOW,
        }),
        error => error.code === 'MUTABLE_EVIDENCE',
    );
    fs.chmodSync(artifactPath, 0o400);
    const outsidePath = path.join(ctx.root, 'outside-adjudication.json');
    fs.renameSync(artifactPath, outsidePath);
    const symlinkPath = path.join(ctx.trustRoot, 'stage-d-quota-adjudication-sqa_link.json');
    fs.symlinkSync(outsidePath, symlinkPath);
    assert.throws(
        () => readBoundQuotaAdjudication({
            quotaAdjudicationPath: symlinkPath,
            ledgerRoot: ctx.ledgerRoot,
            runLockTrustRoot: ctx.trustRoot,
            expectedSha256: binding.artifactSha256,
            ledger: readRequestLedger({ ledgerRoot: ctx.ledgerRoot }),
            quotaConfig: config,
            quotaConfigSha256: binding.quotaConfigSha256,
            expectedSourceMainSha: SOURCE_MAIN_SHA,
            expectedSourceMainTreeSha: SOURCE_MAIN_TREE_SHA,
            now: NOW,
        }),
        error => error.code === 'UNSAFE_PATH',
    );
});
