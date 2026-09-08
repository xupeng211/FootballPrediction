'use strict';

process.env.NODE_ENV = 'test';

const assert = require('node:assert/strict');
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const test = require('node:test');
const { createGovernedFixtureTestContext, createVerifiedTestReceipt } = require('../../helpers/market_evidence_authority');
const { persistVerifiedAllocationAuthority } = require('../../../src/infrastructure/fixture_universe/AllocationAuthorityArtifact');
const { bootstrapMarketEvidenceTransactionStore } = require('../../../src/infrastructure/market_evidence/transactionStore');
const { openMarketEvidenceAuthoritySnapshot } = require('../../../src/infrastructure/market_evidence/authorityReader');
const { buildProspectiveMarketEvidenceTransaction } = require('../../../src/infrastructure/market_evidence/prospectiveBatch');
const { publishProspectiveMarketEvidenceTransaction } = require('../../../src/infrastructure/market_evidence/atomicPublisher');
const { createCaptureReceipt } = require('../../../src/infrastructure/market_evidence/evidenceStore');
const { sha256Text } = require('../../../src/infrastructure/market_evidence/contracts');
const {
    HISTORICAL_PRE_EPOCH_EXACT_TOTAL,
    HISTORICAL_PRE_EPOCH_REQUEST_TOTAL,
    RUN_LOCK_FILE,
    initializeRequestAccountingEpoch,
    readRequestLedger,
    recordRequestIntent,
    markTransmissionStarted,
    markRequestTerminal,
    ledgerUsageSummary,
    inspectStageDRunLock,
    acquireStageDRunLock,
    releaseStageDRunLock,
    assertRequestBudget,
    buildOfflineStageDRunPlan,
    executeStageDOneCycle,
    createStageDTestRuntimeAuthorization,
    createStageDTestQuotaConfiguration,
    createStageDEvidencePersistence,
    createStageDFakeTransport,
    createStageDOddsApiTransport,
    createStageDCandidateBuilder,
    createStageDProspectiveCandidateBuilder,
    createStageDFakePublisher,
} = require('../../../src/infrastructure/market_evidence/stageDOperations');

const START = '2026-09-08T00:00:00Z';
const AUTHORITY = Object.freeze({
    head_transaction_id: `tx_${'a'.repeat(64)}`,
    state_hash: 'b'.repeat(64),
    observations: Object.freeze(Array.from({ length: 903 }, () => Object.freeze({}))),
});

function setup(t) {
    const root = fs.mkdtempSync(path.join(os.tmpdir(), 'stage-d-operations-'));
    t.after(() => fs.rmSync(root, { recursive: true, force: true }));
    const ledgerRoot = path.join(root, 'ledger');
    const epoch = initializeRequestAccountingEpoch({
        ledgerRoot,
        authoritySnapshot: AUTHORITY,
        startedAt: START,
        epochId: `sde_${'c'.repeat(64)}`,
    });
    return { root, ledgerRoot, epoch };
}

function quotaConfig(overrides = {}) {
    return createStageDTestQuotaConfiguration({
        schema_version: 'footballprediction-stage-d-quota-budget/v1',
        quota_evidence_verified: true,
        quota_evidence_source: 'test-only verified owner record',
        billing_period_id: '2026-09',
        period_start_at: '2026-09-01T00:00:00Z',
        period_end_at: '2026-10-01T00:00:00Z',
        monthly_quota_limit: 20,
        reserved_safety_buffer: 2,
        max_requests_per_stage_d_run: 1,
        max_requests_per_day: 4,
        stop_before_quota_exhaustion_threshold: 1,
        ...overrides,
    });
}

function clockSequence(...timestamps) {
    let index = 0;
    return () => timestamps[Math.min(index++, timestamps.length - 1)];
}

function liveAuthoritySetup(t) {
    const rawText = fs.readFileSync(path.join(__dirname, '../../../tests/fixtures/market_evidence/the_odds_api_epl_h2h.minimal.json'), 'utf8');
    const fixture = createGovernedFixtureTestContext({ rawText });
    t.after(fixture.cleanup);
    const root = fs.mkdtempSync(path.join(os.tmpdir(), 'stage-d-live-adapter-'));
    t.after(() => fs.rmSync(root, { recursive: true, force: true }));
    const allocationArtifactPath = path.join(root, 'allocation.authority.json');
    const persisted = persistVerifiedAllocationAuthority({ artifactPath: allocationArtifactPath, allocationAuthority: fixture.universe.allocationAuthority });
    const authorityRoot = path.join(root, 'transactions');
    bootstrapMarketEvidenceTransactionStore({ storeRoot: authorityRoot, allocationArtifactPath, bootstrapMetadata: { test: 'stage-d-live-adapter' } });
    const initialSnapshot = openMarketEvidenceAuthoritySnapshot({ storeRoot: authorityRoot, allocationArtifactPath });
    const receiptEvidence = createVerifiedTestReceipt({ root: path.join(root, 'initial-receipt'), rawText, overrides: { capture_id: 'prior-capture' } });
    const initialCandidate = buildProspectiveMarketEvidenceTransaction({
        authoritySnapshot: initialSnapshot,
        universe: fixture.universe,
        oddsRawText: rawText,
        captureReceipt: receiptEvidence,
    });
    publishProspectiveMarketEvidenceTransaction({ storeRoot: authorityRoot, allocationArtifactPath, candidate: initialCandidate });
    const authoritySnapshot = openMarketEvidenceAuthoritySnapshot({ storeRoot: authorityRoot, allocationArtifactPath });
    const ledgerRoot = path.join(root, 'request-accounting');
    initializeRequestAccountingEpoch({ ledgerRoot, authoritySnapshot, startedAt: START, epochId: `sde_${'d'.repeat(64)}` });
    const evidenceRoot = path.join(root, 'evidence');
    fs.mkdirSync(evidenceRoot, { mode: 0o700 });
    return {
        root,
        rawText,
        fixture,
        authorityRoot,
        allocationArtifactPath,
        authoritySnapshot,
        ledgerRoot,
        evidenceRoot,
    };
}

function liveComponents(ctx, { response, error = null, publisher = async () => ({ status: 'FAKE_NOT_CALLED' }), build = () => { throw new Error('candidate builder must not be called'); }, candidateBuilder = null } = {}) {
    const transport = createStageDFakeTransport({ response: error ? null : (response || {
        raw_text: ctx.rawText,
        http_status: 200,
        response_received_at: '2026-09-08T08:00:03Z',
        provider_quota: null,
    }), error });
    return {
        transport,
        evidencePersistence: createStageDEvidencePersistence({ evidenceRoot: ctx.evidenceRoot }),
        candidateBuilder: candidateBuilder || createStageDCandidateBuilder(build),
        transactionPublisher: createStageDFakePublisher(publisher, { authorityRoot: ctx.authorityRoot, allocationArtifactPath: ctx.allocationArtifactPath }),
    };
}

async function executeLive(ctx, overrides = {}) {
    const components = overrides.components || liveComponents(ctx, overrides);
    return executeStageDOneCycle({
        authorityRoot: ctx.authorityRoot,
        allocationArtifactPath: ctx.allocationArtifactPath,
        ledgerRoot: ctx.ledgerRoot,
        quotaConfig: quotaConfig(),
        runId: overrides.runId || 'live-run',
        requestId: overrides.requestId || 'live-request',
        runtimeAuthorization: createStageDTestRuntimeAuthorization(),
        clock: overrides.clock || clockSequence(
            '2026-09-08T08:00:00Z',
            '2026-09-08T08:00:01Z',
            '2026-09-08T08:00:02Z',
            '2026-09-08T08:00:04Z',
            '2026-09-08T08:00:05Z'
        ),
        ...components,
        ...overrides,
    });
}

function intent(ctx, requestId = 'request-a', runId = 'run-a') {
    return recordRequestIntent({
        ledgerRoot: ctx.ledgerRoot,
        requestId,
        runId,
        createdAt: '2026-09-08T01:00:00Z',
    });
}

test('Stage D accounting epoch preserves the historical lower bound and unknown exact lifetime total', t => {
    const ctx = setup(t);
    assert.equal(ctx.epoch.historical_pre_epoch_request_total, HISTORICAL_PRE_EPOCH_REQUEST_TOTAL);
    assert.equal(ctx.epoch.historical_pre_epoch_exact_total, HISTORICAL_PRE_EPOCH_EXACT_TOTAL);
    const reloaded = readRequestLedger({ ledgerRoot: ctx.ledgerRoot });
    assert.equal(reloaded.epoch.epoch_id, ctx.epoch.epoch_id);
    assert.equal(reloaded.entries.length, 0);
});

test('cancelled-before-transmission request is not consumed', t => {
    const ctx = setup(t);
    intent(ctx);
    markRequestTerminal({
        ledgerRoot: ctx.ledgerRoot,
        requestId: 'request-a',
        terminalState: 'CANCELLED_BEFORE_TRANSMISSION',
        at: '2026-09-08T01:00:01Z',
        errorClassification: 'PRE_TRANSPORT_POLICY_ABORT',
    });
    const summary = ledgerUsageSummary(readRequestLedger({ ledgerRoot: ctx.ledgerRoot }));
    assert.deepEqual(summary, {
        request_count: 1,
        consumed_request_count: 0,
        cancelled_before_transmission_count: 1,
        ambiguous_consumed_request_ids: [],
    });
});

test('success, HTTP error and timeout after possible transmission are all durably consumed', t => {
    const ctx = setup(t);
    const cases = [
        ['request-success', 'run-success', 'RESPONSE_RECEIVED', null],
        ['request-http-error', 'run-http-error', 'TRANSPORT_FAILURE_AFTER_POSSIBLE_TRANSMISSION', 'HTTP_503'],
        ['request-timeout', 'run-timeout', 'TRANSPORT_FAILURE_AFTER_POSSIBLE_TRANSMISSION', 'TIMEOUT_NO_RESPONSE'],
    ];
    for (const [requestId, runId, terminalState, errorClassification] of cases) {
        intent(ctx, requestId, runId);
        markTransmissionStarted({ ledgerRoot: ctx.ledgerRoot, requestId, transmittedAt: '2026-09-08T02:00:00Z' });
        markRequestTerminal({
            ledgerRoot: ctx.ledgerRoot,
            requestId,
            terminalState,
            at: '2026-09-08T02:00:01Z',
            receiptEvidenceReference: terminalState === 'RESPONSE_RECEIVED' ? `receipts/${requestId}.json` : null,
            errorClassification,
        });
    }
    const ledger = readRequestLedger({ ledgerRoot: ctx.ledgerRoot });
    assert.equal(ledgerUsageSummary(ledger).consumed_request_count, 3);
    assert.equal(ledgerUsageSummary(ledger).ambiguous_consumed_request_ids.length, 0);
});

test('crash immediately after the transmission boundary remains ambiguous-consumed and blocks budget', t => {
    const ctx = setup(t);
    intent(ctx, 'request-crash', 'run-crash');
    markTransmissionStarted({ ledgerRoot: ctx.ledgerRoot, requestId: 'request-crash', transmittedAt: '2026-09-08T03:00:00Z' });
    const ledger = readRequestLedger({ ledgerRoot: ctx.ledgerRoot });
    assert.deepEqual(ledgerUsageSummary(ledger).ambiguous_consumed_request_ids, ['request-crash']);
    assert.throws(
        () => assertRequestBudget({ ledger, quotaConfig: quotaConfig({ monthly_quota_limit: 4, reserved_safety_buffer: 1, stop_before_quota_exhaustion_threshold: 1 }), runId: 'run-next', now: '2026-09-08T03:00:01Z', requestedUnits: 2 }),
        error => error.code === 'REQUEST_BUDGET_DENIED'
    );
});

test('duplicate request IDs and post-terminal transitions fail closed', t => {
    const ctx = setup(t);
    intent(ctx);
    assert.throws(() => intent(ctx), error => error.code === 'DUPLICATE_REQUEST_ID');
    markTransmissionStarted({ ledgerRoot: ctx.ledgerRoot, requestId: 'request-a', transmittedAt: '2026-09-08T04:00:00Z' });
    markRequestTerminal({ ledgerRoot: ctx.ledgerRoot, requestId: 'request-a', terminalState: 'RESPONSE_RECEIVED', at: '2026-09-08T04:00:01Z' });
    assert.throws(
        () => markRequestTerminal({ ledgerRoot: ctx.ledgerRoot, requestId: 'request-a', terminalState: 'RESPONSE_RECEIVED', at: '2026-09-08T04:00:02Z' }),
        error => error.code === 'INVALID_LEDGER_TRANSITION'
    );
});

test('same run ID cannot exceed its independently enforced request cap', t => {
    const ctx = setup(t);
    intent(ctx, 'request-first', 'run-one');
    markTransmissionStarted({ ledgerRoot: ctx.ledgerRoot, requestId: 'request-first', transmittedAt: '2026-09-08T05:00:00Z' });
    const ledger = readRequestLedger({ ledgerRoot: ctx.ledgerRoot });
    assert.throws(
        () => assertRequestBudget({ ledger, quotaConfig: quotaConfig(), runId: 'run-one', now: '2026-09-08T05:00:01Z' }),
        error => error.code === 'REQUEST_BUDGET_DENIED'
    );
});

test('cold load detects ledger tampering through canonical serialization and hash-chain validation', t => {
    const ctx = setup(t);
    intent(ctx);
    const entryPath = path.join(ctx.ledgerRoot, 'entries', '000000000001.json');
    fs.chmodSync(entryPath, 0o600);
    fs.appendFileSync(entryPath, ' ');
    fs.chmodSync(entryPath, 0o400);
    assert.throws(() => readRequestLedger({ ledgerRoot: ctx.ledgerRoot }), /canonical serialization/);
});

test('ledger and lock readers reject symlink or inode replacement instead of following a swapped path', t => {
    const ctx = setup(t);
    intent(ctx);
    const entryPath = path.join(ctx.ledgerRoot, 'entries', '000000000001.json');
    const replacement = path.join(ctx.root, 'replacement.json');
    fs.writeFileSync(replacement, fs.readFileSync(entryPath), { mode: 0o400 });
    fs.unlinkSync(entryPath);
    fs.symlinkSync(replacement, entryPath);
    assert.throws(() => readRequestLedger({ ledgerRoot: ctx.ledgerRoot }), error => error.code === 'UNSAFE_PATH');

    const lockRoot = path.join(ctx.root, 'lock');
    fs.mkdirSync(lockRoot, { mode: 0o700 });
    const token = acquireStageDRunLock({ operationRoot: lockRoot, runId: 'inode-lock', acquiredAt: START });
    fs.unlinkSync(token.lock_path);
    fs.writeFileSync(token.lock_path, '{"replacement":true}\n', { mode: 0o400 });
    assert.throws(() => releaseStageDRunLock(token), error => error.code === 'AMBIGUOUS_RUN_LOCK');
});

test('run-lock release rejects a byte-identical replacement inode before unlinking it', t => {
    const root = fs.mkdtempSync(path.join(os.tmpdir(), 'stage-d-lock-byte-identical-'));
    t.after(() => fs.rmSync(root, { recursive: true, force: true }));
    const token = acquireStageDRunLock({ operationRoot: root, runId: 'byte-identical-run', acquiredAt: START });
    const lockBytes = fs.readFileSync(token.lock_path);
    fs.renameSync(token.lock_path, `${token.lock_path}.replaced`);
    fs.writeFileSync(token.lock_path, lockBytes, { mode: 0o400 });
    assert.throws(
        () => releaseStageDRunLock(token),
        error => error.code === 'AMBIGUOUS_RUN_LOCK'
    );
    assert.equal(inspectStageDRunLock({ operationRoot: root }).state, 'ACTIVE_OR_STALE_REQUIRES_RECONCILIATION');
});

test('run lock rejects duplicate, stale and ambiguous ownership instead of reclaiming it', t => {
    const root = fs.mkdtempSync(path.join(os.tmpdir(), 'stage-d-run-lock-'));
    t.after(() => fs.rmSync(root, { recursive: true, force: true }));
    const token = acquireStageDRunLock({ operationRoot: root, runId: 'run-a', acquiredAt: START });
    assert.throws(
        () => acquireStageDRunLock({ operationRoot: root, runId: 'run-b', acquiredAt: '2026-09-08T01:00:00Z' }),
        error => error.code === 'STAGE_D_RUN_ACTIVE_OR_STALE'
    );
    releaseStageDRunLock(token);
    assert.equal(inspectStageDRunLock({ operationRoot: root }).state, 'ABSENT');

    const stale = acquireStageDRunLock({ operationRoot: root, runId: 'run-stale', acquiredAt: '2020-01-01T00:00:00Z' });
    assert.throws(
        () => acquireStageDRunLock({ operationRoot: root, runId: 'run-next', acquiredAt: '2026-09-08T01:00:00Z' }),
        error => error.code === 'STAGE_D_RUN_ACTIVE_OR_STALE'
    );
    fs.unlinkSync(stale.lock_path); // explicit test-only reconciliation; production never auto-reclaims.
    const corruptPath = path.join(root, RUN_LOCK_FILE);
    fs.writeFileSync(corruptPath, '{}\n', { mode: 0o400 });
    assert.equal(inspectStageDRunLock({ operationRoot: root }).state, 'AMBIGUOUS_REQUIRES_RECONCILIATION');
    assert.throws(
        () => acquireStageDRunLock({ operationRoot: root, runId: 'run-next', acquiredAt: '2026-09-08T01:00:00Z' }),
        error => error.code === 'AMBIGUOUS_RUN_LOCK'
    );
});

test('crash before request and crash after request both prevent another provider transmission until reconciliation', t => {
    const ctx = setup(t);
    const before = acquireStageDRunLock({ operationRoot: ctx.root, runId: 'run-before', acquiredAt: START });
    assert.throws(
        () => acquireStageDRunLock({ operationRoot: ctx.root, runId: 'run-next', acquiredAt: '2026-09-08T01:00:00Z' }),
        error => error.code === 'STAGE_D_RUN_ACTIVE_OR_STALE'
    );
    fs.unlinkSync(before.lock_path); // explicit test-only recovery from a simulated crash.
    intent(ctx, 'request-after', 'run-after');
    markTransmissionStarted({ ledgerRoot: ctx.ledgerRoot, requestId: 'request-after', transmittedAt: '2026-09-08T06:00:00Z' });
    acquireStageDRunLock({ operationRoot: ctx.root, runId: 'run-after', acquiredAt: '2026-09-08T06:00:00Z' });
    assert.throws(
        () => acquireStageDRunLock({ operationRoot: ctx.root, runId: 'run-next', acquiredAt: '2026-09-08T06:00:01Z' }),
        error => error.code === 'STAGE_D_RUN_ACTIVE_OR_STALE'
    );
    assert.deepEqual(ledgerUsageSummary(readRequestLedger({ ledgerRoot: ctx.ledgerRoot })).ambiguous_consumed_request_ids, ['request-after']);
});

test('offline dry run acquires/releases a lock, loads authority and ledger, and cannot transmit or mutate canonical authority', t => {
    const ctx = setup(t);
    const operationRoot = path.join(ctx.root, 'operation');
    fs.mkdirSync(operationRoot, { mode: 0o700 });
    const beforeEntries = readRequestLedger({ ledgerRoot: ctx.ledgerRoot }).entries.length;
    const plan = buildOfflineStageDRunPlan({
        operationRoot,
        ledgerRoot: ctx.ledgerRoot,
        authoritySnapshot: AUTHORITY,
        quotaConfig: null,
        runId: 'offline-run',
        now: '2026-09-08T07:00:00Z',
    });
    assert.equal(plan.mode, 'OFFLINE_DRY_RUN');
    assert.equal(plan.run_lock, 'ACQUIRED_AND_CLEANLY_RELEASED');
    assert.equal(plan.request_budget.allowed, false);
    assert.equal(plan.request_budget.code, 'UNVERIFIED_QUOTA_CONFIGURATION');
    assert.equal(plan.provider_requests, 0);
    assert.equal(plan.canonical_authority_writes, 0);
    assert.equal(readRequestLedger({ ledgerRoot: ctx.ledgerRoot }).entries.length, beforeEntries);
    assert.equal(inspectStageDRunLock({ operationRoot }).state, 'ABSENT');
});

test('live adapter with a local fake transport persists intent, consumes exactly one request, and records a duplicate no-op without publishing', async t => {
    const ctx = liveAuthoritySetup(t);
    let publisherCalls = 0;
    const components = liveComponents(ctx, {
        response: {
            raw_text: ctx.rawText,
            http_status: 200,
            response_received_at: '2026-09-08T08:00:03Z',
            provider_quota: null,
        },
        publisher: async () => {
            publisherCalls += 1;
            return { status: 'unexpected-publish' };
        },
    });
    const before = openMarketEvidenceAuthoritySnapshot({ storeRoot: ctx.authorityRoot, allocationArtifactPath: ctx.allocationArtifactPath });
    const result = await executeLive(ctx, { components, runId: 'live-success-run', requestId: 'live-success-request' });
    const after = openMarketEvidenceAuthoritySnapshot({ storeRoot: ctx.authorityRoot, allocationArtifactPath: ctx.allocationArtifactPath });
    const ledger = readRequestLedger({ ledgerRoot: ctx.ledgerRoot });
    assert.equal(result.status, 'NO_OP_DUPLICATE_RAW_HASH');
    assert.equal(components.transport.call_count, 1);
    assert.equal(publisherCalls, 0);
    assert.equal(after.head_transaction_id, before.head_transaction_id);
    assert.equal(after.state_hash, before.state_hash);
    assert.deepEqual(ledgerUsageSummary(ledger), {
        request_count: 1,
        consumed_request_count: 1,
        cancelled_before_transmission_count: 0,
        ambiguous_consumed_request_ids: [],
    });
    assert.equal(ledger.requests[0].terminal_state, 'RESPONSE_RECEIVED');
    assert.equal(inspectStageDRunLock({ operationRoot: ctx.ledgerRoot }).state, 'ABSENT');
});

test('unknown or exhausted quota and an existing run lock prevent any fake transport call', async t => {
    const unknown = liveAuthoritySetup(t);
    const unknownComponents = liveComponents(unknown);
    await assert.rejects(
        executeLive(unknown, { components: unknownComponents, quotaConfig: null, runId: 'unknown-quota-run', requestId: 'unknown-quota-request' }),
        error => error.code === 'UNVERIFIED_QUOTA_CONFIGURATION'
    );
    assert.equal(unknownComponents.transport.call_count, 0);
    assert.equal(readRequestLedger({ ledgerRoot: unknown.ledgerRoot }).entries.length, 0);

    const exhausted = liveAuthoritySetup(t);
    intent({ ledgerRoot: exhausted.ledgerRoot }, 'prior-request', 'prior-run');
    markTransmissionStarted({ ledgerRoot: exhausted.ledgerRoot, requestId: 'prior-request', transmittedAt: '2026-09-08T07:00:00Z' });
    const exhaustedComponents = liveComponents(exhausted);
    await assert.rejects(
        executeLive(exhausted, {
            components: exhaustedComponents,
            quotaConfig: quotaConfig({ monthly_quota_limit: 1, reserved_safety_buffer: 0, stop_before_quota_exhaustion_threshold: 0 }),
            runId: 'exhausted-run',
            requestId: 'exhausted-request',
        }),
        error => error.code === 'REQUEST_BUDGET_DENIED'
    );
    assert.equal(readRequestLedger({ ledgerRoot: exhausted.ledgerRoot }).requests.length, 1);

    const locked = liveAuthoritySetup(t);
    const lockToken = acquireStageDRunLock({ operationRoot: locked.ledgerRoot, runId: 'active-run', acquiredAt: START });
    const lockedComponents = liveComponents(locked);
    await assert.rejects(
        executeLive(locked, { components: lockedComponents, runId: 'blocked-run', requestId: 'blocked-request' }),
        error => error.code === 'STAGE_D_RUN_ACTIVE_OR_STALE'
    );
    assert.equal(lockedComponents.transport.call_count, 0);
    releaseStageDRunLock(lockToken);
});

test('HTTP failure and transport timeout are consumed and never retried', async t => {
    const http = liveAuthoritySetup(t);
    const httpComponents = liveComponents(http, {
        response: { http_status: 503, response_received_at: '2026-09-08T08:00:03Z' },
    });
    const httpResult = await executeLive(http, { components: httpComponents, runId: 'http-run', requestId: 'http-request' });
    assert.equal(httpResult.status, 'HTTP_FAILURE_AFTER_TRANSMISSION');
    assert.equal(httpComponents.transport.call_count, 1);
    const httpRequest = readRequestLedger({ ledgerRoot: http.ledgerRoot }).requests[0];
    assert.equal(httpRequest.terminal_state, 'HTTP_FAILURE_AFTER_TRANSMISSION');
    assert.equal(httpRequest.quota_units_charged_or_assumed, 1);

    const timeout = liveAuthoritySetup(t);
    const timeoutComponents = liveComponents(timeout, { error: Object.assign(new Error('timeout'), { code: 'ETIMEDOUT' }) });
    await assert.rejects(
        executeLive(timeout, { components: timeoutComponents, runId: 'timeout-run', requestId: 'timeout-request' }),
        error => error.code === 'ETIMEDOUT'
    );
    assert.equal(timeoutComponents.transport.call_count, 1);
    const timeoutRequest = readRequestLedger({ ledgerRoot: timeout.ledgerRoot }).requests[0];
    assert.equal(timeoutRequest.terminal_state, 'TRANSPORT_FAILURE_AFTER_POSSIBLE_TRANSMISSION');
    assert.equal(timeoutRequest.quota_units_charged_or_assumed, 1);
});

test('RAW and receipt persistence failures retain consumed usage and do not retry', async t => {
    const rawFailure = liveAuthoritySetup(t);
    const originalEvidenceRoot = rawFailure.evidenceRoot;
    const movedEvidenceRoot = `${originalEvidenceRoot}.moved`;
    const rawComponents = liveComponents(rawFailure, {
        response: { raw_text: rawFailure.rawText, http_status: 200, response_received_at: '2026-09-08T08:00:03Z' },
    });
    rawComponents.evidencePersistence = createStageDEvidencePersistence({
        evidenceRoot: originalEvidenceRoot,
        testHooks: {
            beforePersistRaw() {
            fs.renameSync(originalEvidenceRoot, movedEvidenceRoot);
            fs.mkdirSync(originalEvidenceRoot, { mode: 0o700 });
            },
        },
    });
    await assert.rejects(
        executeLive(rawFailure, { components: rawComponents, runId: 'raw-failure-run', requestId: 'raw-failure-request' }),
        error => error.code === 'DIRECTORY_IDENTITY_CHANGED'
    );
    assert.equal(rawComponents.transport.call_count, 1);
    const rawRequest = readRequestLedger({ ledgerRoot: rawFailure.ledgerRoot }).requests[0];
    assert.equal(rawRequest.terminal_state, 'TRANSPORT_FAILURE_AFTER_POSSIBLE_TRANSMISSION');
    assert.equal(rawRequest.quota_units_charged_or_assumed, 1);

    const receiptFailure = liveAuthoritySetup(t);
    const receiptPersistence = createStageDEvidencePersistence({ evidenceRoot: receiptFailure.evidenceRoot });
    const conflictingReceipt = createCaptureReceipt({
        provider: 'the-odds-api',
        capture_id: 'receipt-failure-request',
        acquisition_mode: 'LIVE_CAPTURE',
        request_started_at: '2026-09-08T08:00:02Z',
        response_received_at: '2026-09-08T08:00:03Z',
        ingested_at: '2026-09-08T08:00:04Z',
        http_status: 200,
        sanitized_request_parameters: { regions: 'uk', markets: 'h2h', oddsFormat: 'decimal' },
        response_size_bytes: Buffer.byteLength(receiptFailure.rawText),
        raw_sha256: sha256Text(receiptFailure.rawText),
        raw_evidence_reference: 'raw/conflicting.json',
    });
    receiptPersistence.persistReceipt({ receipt: conflictingReceipt });
    const receiptComponents = liveComponents(receiptFailure, {
        response: { raw_text: receiptFailure.rawText, http_status: 200, response_received_at: '2026-09-08T08:00:03Z' },
    });
    await assert.rejects(
        executeLive(receiptFailure, { components: { ...receiptComponents, evidencePersistence: receiptPersistence }, runId: 'receipt-failure-run', requestId: 'receipt-failure-request' }),
        error => error.code === 'RECEIPT_CONFLICT'
    );
    const receiptRequest = readRequestLedger({ ledgerRoot: receiptFailure.ledgerRoot }).requests[0];
    assert.equal(receiptRequest.terminal_state, 'TRANSPORT_FAILURE_AFTER_POSSIBLE_TRANSMISSION');
    assert.equal(receiptRequest.quota_units_charged_or_assumed, 1);
});

test('candidate/parser failure releases the lock after consumed response, while publication failure leaves an explicit reconciliation lock', async t => {
    const parserFailure = liveAuthoritySetup(t);
    const parserRaw = parserFailure.rawText.replace('epl-fixture-001', 'epl-fixture-002');
    const parserComponents = liveComponents(parserFailure, {
        response: { raw_text: parserRaw, http_status: 200, response_received_at: '2026-09-08T08:00:03Z' },
        build: () => { throw Object.assign(new Error('parser failure'), { code: 'PARSER_FAILURE' }); },
    });
    await assert.rejects(
        executeLive(parserFailure, { components: parserComponents, runId: 'parser-failure-run', requestId: 'parser-failure-request' }),
        error => error.code === 'PARSER_FAILURE'
    );
    const parsedRequest = readRequestLedger({ ledgerRoot: parserFailure.ledgerRoot }).requests[0];
    assert.equal(parsedRequest.terminal_state, 'RESPONSE_RECEIVED');
    assert.equal(parsedRequest.quota_units_charged_or_assumed, 1);
    assert.equal(inspectStageDRunLock({ operationRoot: parserFailure.ledgerRoot }).state, 'ABSENT');

    const publicationFailure = liveAuthoritySetup(t);
    const changedRaw = publicationFailure.rawText.replace('epl-fixture-001', 'epl-fixture-002');
    const prospectiveBuilder = createStageDProspectiveCandidateBuilder({ universe: publicationFailure.fixture.universe });
    const publicationComponents = liveComponents(publicationFailure, {
        response: { raw_text: changedRaw, http_status: 200, response_received_at: '2026-09-08T08:00:03Z' },
        candidateBuilder: prospectiveBuilder,
        publisher: async () => { throw Object.assign(new Error('publisher failure'), { code: 'PUBLISH_FAILED' }); },
    });
    await assert.rejects(
        executeLive(publicationFailure, { components: publicationComponents, runId: 'publication-failure-run', requestId: 'publication-failure-request' }),
        error => error.code === 'PUBLISH_FAILED'
    );
    const publicationRequest = readRequestLedger({ ledgerRoot: publicationFailure.ledgerRoot }).requests[0];
    assert.equal(publicationRequest.terminal_state, 'RESPONSE_RECEIVED');
    assert.equal(publicationRequest.quota_units_charged_or_assumed, 1);
    assert.equal(inspectStageDRunLock({ operationRoot: publicationFailure.ledgerRoot }).state, 'ACTIVE_OR_STALE_REQUIRES_RECONCILIATION');
});

test('authority reopen failure after a consumed response retains the reconciliation lock', async t => {
    const ctx = liveAuthoritySetup(t);
    const movedAuthorityRoot = `${ctx.authorityRoot}.moved`;
    const components = liveComponents(ctx);
    components.evidencePersistence = createStageDEvidencePersistence({
        evidenceRoot: ctx.evidenceRoot,
        testHooks: {
            beforePersistReceipt() {
                fs.renameSync(ctx.authorityRoot, movedAuthorityRoot);
                fs.mkdirSync(ctx.authorityRoot, { mode: 0o700 });
            },
        },
    });
    await assert.rejects(
        executeLive(ctx, { components, runId: 'authority-reopen-failure-run', requestId: 'authority-reopen-failure-request' }),
        error => ['ENOENT', 'INVALID_AUTHORITY', 'AUTHORITY_REOPEN_FAILED', 'DIRECTORY_IDENTITY_CHANGED'].includes(error.code)
    );
    const request = readRequestLedger({ ledgerRoot: ctx.ledgerRoot }).requests[0];
    assert.equal(request.terminal_state, 'RESPONSE_RECEIVED');
    assert.equal(inspectStageDRunLock({ operationRoot: ctx.ledgerRoot }).state, 'ACTIVE_OR_STALE_REQUIRES_RECONCILIATION');
    fs.unlinkSync(path.join(ctx.ledgerRoot, RUN_LOCK_FILE));
    fs.rmSync(ctx.authorityRoot, { recursive: true, force: true });
    fs.renameSync(movedAuthorityRoot, ctx.authorityRoot);
});

test('provider transport has an explicit binding and cannot be called without the adapter token', () => {
    const transport = createStageDOddsApiTransport({ apiKey: 'test-only-not-used' });
    assert.equal(transport.network_capability, 'provider');
    assert.throws(
        () => transport.send({ request_id: 'probe', transmission_started_at: '2026-09-08T08:00:00Z' }, {}),
        error => error.code === 'TRANSPORT_CALL_FORBIDDEN'
    );
});

test('provider transport is unavailable to test execution even with local fake authorization', async t => {
    const ctx = liveAuthoritySetup(t);
    const transport = createStageDOddsApiTransport({ apiKey: 'test-only-not-used' });
    await assert.rejects(
        executeStageDOneCycle({
            authorityRoot: ctx.authorityRoot,
            allocationArtifactPath: ctx.allocationArtifactPath,
            ledgerRoot: ctx.ledgerRoot,
            quotaConfig: quotaConfig(),
            runId: 'provider-disabled-test-run',
            requestId: 'provider-disabled-test-request',
            runtimeAuthorization: createStageDTestRuntimeAuthorization(),
            clock: () => '2026-09-08T08:00:00Z',
            transport,
            evidencePersistence: createStageDEvidencePersistence({ evidenceRoot: ctx.evidenceRoot }),
            candidateBuilder: createStageDCandidateBuilder(() => { throw new Error('must not build'); }),
            transactionPublisher: createStageDFakePublisher(async () => { throw new Error('must not publish'); }, {
                authorityRoot: ctx.authorityRoot,
                allocationArtifactPath: ctx.allocationArtifactPath,
            }),
        }),
        error => error.code === 'STAGE_D_PROVIDER_DISABLED_IN_TEST'
    );
    assert.equal(inspectStageDRunLock({ operationRoot: ctx.ledgerRoot }).state, 'ABSENT');
});

test('evidence persistence rejects parent-directory replacement and unsafe capture paths', t => {
    const ctx = liveAuthoritySetup(t);
    const persistence = createStageDEvidencePersistence({ evidenceRoot: ctx.evidenceRoot });
    const moved = `${ctx.evidenceRoot}.moved`;
    fs.renameSync(ctx.evidenceRoot, moved);
    fs.mkdirSync(ctx.evidenceRoot, { mode: 0o700 });
    assert.throws(
        () => persistence.persistRaw({ rawText: 'parent swap must fail closed' }),
        error => error.code === 'DIRECTORY_IDENTITY_CHANGED'
    );
    fs.rmSync(ctx.evidenceRoot, { recursive: true, force: true });
    fs.renameSync(moved, ctx.evidenceRoot);
    assert.throws(
        () => persistence.persistReceipt({ receipt: { capture_id: '../escape' } }),
        error => error.code === 'RECEIPT_PERSISTENCE_FAILED'
    );
});

test('run-lock directory replacement fails closed instead of unlinking a lock in another inode', t => {
    const root = fs.mkdtempSync(path.join(os.tmpdir(), 'stage-d-lock-identity-'));
    t.after(() => fs.rmSync(root, { recursive: true, force: true }));
    const token = acquireStageDRunLock({ operationRoot: root, runId: 'identity-run', acquiredAt: START });
    const moved = `${root}.moved`;
    fs.renameSync(root, moved);
    fs.mkdirSync(root, { mode: 0o700 });
    assert.doesNotThrow(() => releaseStageDRunLock(token));
    assert.equal(inspectStageDRunLock({ operationRoot: root }).state, 'ABSENT');
    assert.equal(inspectStageDRunLock({ operationRoot: moved }).state, 'ABSENT');
    fs.rmSync(root, { recursive: true, force: true });
    fs.renameSync(moved, root);
});

test('ledger failure before the transmission boundary makes the run ambiguous without counting a provider attempt', async t => {
    const ctx = liveAuthoritySetup(t);
    const components = liveComponents(ctx);
    let ticks = 0;
    const originalLedgerRoot = ctx.ledgerRoot;
    const movedLedgerRoot = `${originalLedgerRoot}.moved`;
    const clock = () => {
        ticks += 1;
        if (ticks === 3) {
            fs.renameSync(originalLedgerRoot, movedLedgerRoot);
            fs.mkdirSync(originalLedgerRoot, { mode: 0o700 });
        }
        return ['2026-09-08T08:00:00Z', '2026-09-08T08:00:01Z', '2026-09-08T08:00:02Z'][Math.min(ticks - 1, 2)];
    };
    await assert.rejects(
        executeLive(ctx, { components, clock, runId: 'pre-boundary-failure-run', requestId: 'pre-boundary-failure-request' }),
        error => ['ENOENT', 'INVALID_LEDGER', 'DIRECTORY_IDENTITY_CHANGED'].includes(error.code)
    );
    assert.equal(components.transport.call_count, 0);
    assert.equal(readRequestLedger({ ledgerRoot: movedLedgerRoot }).requests[0].transmission_state, 'TRANSMISSION_NOT_STARTED');
    assert.equal(ledgerUsageSummary(readRequestLedger({ ledgerRoot: movedLedgerRoot })).consumed_request_count, 0);
    fs.rmSync(originalLedgerRoot, { recursive: true, force: true });
    fs.renameSync(movedLedgerRoot, originalLedgerRoot);
});

test('a valid ledger-copy swap after lock acquisition fails closed before any provider transmission', async t => {
    const ctx = liveAuthoritySetup(t);
    const components = liveComponents(ctx);
    const replacement = `${ctx.ledgerRoot}.replacement`;
    const moved = `${ctx.ledgerRoot}.moved`;
    let ticks = 0;
    const clock = () => {
        ticks += 1;
        if (ticks === 2) {
            fs.cpSync(ctx.ledgerRoot, replacement, { recursive: true });
            fs.rmSync(path.join(replacement, RUN_LOCK_FILE));
            fs.renameSync(ctx.ledgerRoot, moved);
            fs.renameSync(replacement, ctx.ledgerRoot);
        }
        return ['2026-09-08T08:00:00Z', '2026-09-08T08:00:01Z'][Math.min(ticks - 1, 1)];
    };
    await assert.rejects(
        executeLive(ctx, { components, clock, runId: 'ledger-copy-swap-run', requestId: 'ledger-copy-swap-request' }),
        error => error.code === 'REQUEST_INTENT_RECONCILIATION_REQUIRED'
    );
    assert.equal(components.transport.call_count, 0);
    assert.equal(inspectStageDRunLock({ operationRoot: ctx.ledgerRoot }).state, 'ABSENT');
    assert.equal(readRequestLedger({ ledgerRoot: moved }).requests.length, 0);
    assert.equal(inspectStageDRunLock({ operationRoot: moved }).state, 'ACTIVE_OR_STALE_REQUIRES_RECONCILIATION');
    fs.unlinkSync(path.join(moved, RUN_LOCK_FILE));
    fs.rmSync(ctx.ledgerRoot, { recursive: true, force: true });
    fs.renameSync(moved, ctx.ledgerRoot);
});

test('live one-cycle primitive is an explicit authorization firewall, not an injectable transport or publisher bypass', async () => {
    await assert.rejects(
        executeStageDOneCycle({
            acquireAndPersistEvidence: async () => { throw new Error('must not be called'); },
            publishCanonicalEvidence: async () => { throw new Error('must not be called'); },
        }),
        error => error.code === 'STAGE_D_NOT_AUTHORIZED'
    );
});

test('the retired Stage C entrypoint cannot send a provider request even with the old opt-in variable', async () => {
    const previous = process.env.STAGE_C_ALLOW_NETWORK;
    process.env.STAGE_C_ALLOW_NETWORK = 'yes';
    const modulePath = path.resolve(__dirname, '../../../scripts/ops/stage_c_the_odds_api_live_smoke.js');
    delete require.cache[modulePath];
    try {
        const stageC = require(modulePath);
        await assert.rejects(stageC.acquireOptInLiveEvidence(), /retired/);
    } finally {
        if (previous === undefined) delete process.env.STAGE_C_ALLOW_NETWORK;
        else process.env.STAGE_C_ALLOW_NETWORK = previous;
        delete require.cache[modulePath];
    }
});

test('one-cycle entrypoint cannot import a provider client or offer an execution mode', () => {
    const source = fs.readFileSync(path.join(__dirname, '../../../scripts/ops/stage_d_cycle.js'), 'utf8');
    assert.doesNotMatch(source, /theOddsApiClient|createTheOddsApiClient|https\.request/);
    assert.match(source, /--dry-run/);
    assert.match(source, /live execution is disabled/);
});
