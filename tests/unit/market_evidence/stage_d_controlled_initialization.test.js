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
const { sha256Text, stableStringify } = require('../../../src/infrastructure/market_evidence/contracts');
const { parseArgs: parseControlledCliArgs } = require('../../../scripts/ops/stage_d_controlled_initialization');
const {
    RUN_LOCK_FILE,
    runLockParentFile,
    runLockAncestorFile,
    runLockTrustFile,
    initializeRequestAccountingEpoch,
    readRequestLedger,
    createStageDEvidencePersistence,
    createStageDFakeTransport,
    createStageDProspectiveCandidateBuilder,
    createStageDFakePublisher,
    executeStageDControlledInitialization,
} = require('../../../src/infrastructure/market_evidence/stageDOperations');

const START = '2026-09-08T00:00:00Z';
const AUTHORIZATION_NOW = '2026-09-08T08:00:00Z';
const AUTHORIZATION_EXPIRES = '2026-09-09T07:00:00Z';
const ACCOUNTING_EPOCH_ID = 'sde_b10b6bd109a6c60498fbd9e8c9ec87894e79ca1091aedbdb229083199cd00406';

function quotaConfiguration(overrides = {}) {
    const config = {
        schema_version: 'footballprediction-stage-d-quota-budget/v2',
        provider: 'the-odds-api',
        subscription_tier: 'starter_free',
        quota_evidence_class: 'OWNER_DECLARATION_PLUS_PUBLIC_PLAN_EVIDENCE',
        quota_evidence_verified: true,
        quota_evidence_source: 'networkless controlled-initialization test fixture',
        billing_period_id: '2026-09',
        period_start_at: '2026-09-01T00:00:00Z',
        period_end_at: '2026-10-01T00:00:00Z',
        monthly_quota_limit: 20,
        reserved_safety_buffer: 2,
        automated_spend_limit: 17,
        max_requests_per_stage_d_run: 1,
        max_requests_per_day: 4,
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
        config.automated_spend_limit = config.monthly_quota_limit - config.reserved_safety_buffer - config.stop_before_quota_exhaustion_threshold;
    }
    return config;
}

function removeRunLockArtifacts({ ledgerRoot, trustRoot }) {
    const targets = [
        path.join(ledgerRoot, RUN_LOCK_FILE),
        path.join(path.dirname(path.resolve(ledgerRoot)), runLockParentFile(ledgerRoot)),
        path.join(path.dirname(path.dirname(path.resolve(ledgerRoot))), runLockAncestorFile(ledgerRoot)),
        path.join(trustRoot, runLockTrustFile(ledgerRoot)),
    ];
    for (const target of targets) {
        if (fs.existsSync(target)) fs.unlinkSync(target);
    }
}

function writeReadOnlyCanonicalJson(filePath, value) {
    if (fs.existsSync(filePath)) fs.chmodSync(filePath, 0o600);
    fs.writeFileSync(filePath, `${stableStringify(value)}\n`, { mode: 0o444 });
    fs.chmodSync(filePath, 0o444);
}

function overwriteReadOnlyFile(filePath, bytes) {
    fs.chmodSync(filePath, 0o600);
    fs.writeFileSync(filePath, bytes);
    fs.chmodSync(filePath, 0o444);
}

function makeAuthorization(ctx, overrides = {}) {
    const authorization = {
        schema_version: 'footballprediction-stage-d-controlled-initialization-authorization/v1',
        authorization_id: 'sda_networkless-test-authorization',
        authorization_status: 'OWNER_AND_CHIEF_ENGINEER_AUTHORIZED',
        mission: 'CONTROLLED_STAGE_D_SINGLE_CYCLE',
        provider: 'the-odds-api',
        configured_markets: ['h2h'],
        configured_regions: ['uk'],
        max_provider_requests: 1,
        expected_request_cost_credits: 1,
        accounting_epoch_id: ACCOUNTING_EPOCH_ID,
        authority_pre_head: ctx.authoritySnapshot.head_transaction_id,
        authority_pre_state_hash: ctx.authoritySnapshot.state_hash,
        authority_pre_observation_count: ctx.authoritySnapshot.observations.length,
        authority_pre_store_sha256: ctx.storeSha256,
        authority_pre_allocation_authority_sha256: ctx.allocationSha256,
        quota_config_sha256: ctx.quotaConfigSha256,
        fixture_universe_raw_sha256: ctx.rawSha256,
        run_id: 'stage-d-controlled-test-run',
        request_id: 'stage-d-controlled-test-request',
        issued_at: '2026-09-08T07:00:00Z',
        expires_at: AUTHORIZATION_EXPIRES,
        ...overrides,
    };
    writeReadOnlyCanonicalJson(ctx.authorizationPath, authorization);
    return authorization;
}

function makeContext(t, authorizationOverrides = {}) {
    const rawText = fs.readFileSync(path.join(__dirname, '../../../tests/fixtures/market_evidence/the_odds_api_epl_h2h.minimal.json'), 'utf8');
    const fixture = createGovernedFixtureTestContext({ rawText });
    t.after(fixture.cleanup);
    const root = fs.mkdtempSync(path.join(os.tmpdir(), 'stage-d-controlled-binder-'));
    const allocationArtifactPath = path.join(root, 'allocation.authority.json');
    persistVerifiedAllocationAuthority({ artifactPath: allocationArtifactPath, allocationAuthority: fixture.universe.allocationAuthority });
    const authorityRoot = path.join(root, 'transactions');
    bootstrapMarketEvidenceTransactionStore({ storeRoot: authorityRoot, allocationArtifactPath, bootstrapMetadata: { test: 'stage-d-controlled-binder' } });
    const initialSnapshot = openMarketEvidenceAuthoritySnapshot({ storeRoot: authorityRoot, allocationArtifactPath });
    const initialReceipt = createVerifiedTestReceipt({ root: path.join(root, 'initial-receipt'), rawText, overrides: { capture_id: 'prior-capture' } });
    const initialCandidate = buildProspectiveMarketEvidenceTransaction({
        authoritySnapshot: initialSnapshot,
        universe: fixture.universe,
        oddsRawText: rawText,
        captureReceipt: initialReceipt,
    });
    publishProspectiveMarketEvidenceTransaction({ storeRoot: authorityRoot, allocationArtifactPath, candidate: initialCandidate });
    const authoritySnapshot = openMarketEvidenceAuthoritySnapshot({ storeRoot: authorityRoot, allocationArtifactPath });
    const ledgerRoot = path.join(root, 'request-accounting');
    initializeRequestAccountingEpoch({ ledgerRoot, authoritySnapshot, startedAt: START, epochId: ACCOUNTING_EPOCH_ID });
    const trustRoot = path.join(root, 'runtime-trust');
    const evidenceRoot = path.join(root, 'evidence');
    fs.mkdirSync(trustRoot, { recursive: true, mode: 0o700 });
    fs.mkdirSync(evidenceRoot, { recursive: true, mode: 0o700 });
    const quotaConfig = quotaConfiguration();
    const quotaConfigPath = path.join(root, 'quota-config.json');
    writeReadOnlyCanonicalJson(quotaConfigPath, quotaConfig);
    const fixtureUniverseRawPath = path.join(root, 'fixture-universe.raw.html');
    fs.writeFileSync(fixtureUniverseRawPath, rawText, { mode: 0o444 });
    fs.chmodSync(fixtureUniverseRawPath, 0o444);
    const quotaConfigSha256 = sha256Text(`${stableStringify(quotaConfig)}\n`);
    const storeSha256 = sha256Text(fs.readFileSync(path.join(authorityRoot, 'STORE.json'), 'utf8'));
    const allocationSha256 = sha256Text(fs.readFileSync(allocationArtifactPath, 'utf8'));
    const authorizationPath = path.join(trustRoot, 'controlled-authorization.json');
    const ctx = {
        root,
        rawText,
        rawSha256: sha256Text(rawText),
        fixture,
        authorityRoot,
        allocationArtifactPath,
        authoritySnapshot,
        ledgerRoot,
        trustRoot,
        evidenceRoot,
        quotaConfig,
        quotaConfigPath,
        fixtureUniverseRawPath,
        quotaConfigSha256,
        storeSha256,
        allocationSha256,
        authorizationPath,
    };
    makeAuthorization(ctx, authorizationOverrides);
    t.after(() => {
        removeRunLockArtifacts(ctx);
        fs.rmSync(root, { recursive: true, force: true });
    });
    return ctx;
}

function componentsFor(ctx, { error = null } = {}) {
    const response = {
        raw_text: ctx.rawText,
        http_status: 200,
        response_received_at: '2026-09-08T08:00:05Z',
        provider_quota: {
            'x-requests-used': '1',
            'x-requests-remaining': '19',
            'x-requests-last': '1',
        },
    };
    return {
        transport: createStageDFakeTransport({ response: error ? null : JSON.stringify(response), error }),
        evidencePersistence: createStageDEvidencePersistence({ evidenceRoot: ctx.evidenceRoot }),
        candidateBuilder: createStageDProspectiveCandidateBuilder({ universe: ctx.fixture.universe }),
        transactionPublisher: createStageDFakePublisher({
            authorityRoot: ctx.authorityRoot,
            allocationArtifactPath: ctx.allocationArtifactPath,
            status: 'unexpected-publish',
        }),
    };
}

function binderOptions(ctx, components, clock = () => AUTHORIZATION_NOW) {
    return {
        authorizationArtifactPath: ctx.authorizationPath,
        authorityRoot: ctx.authorityRoot,
        allocationArtifactPath: ctx.allocationArtifactPath,
        ledgerRoot: ctx.ledgerRoot,
        quotaConfigPath: ctx.quotaConfigPath,
        fixtureUniverseRawPath: ctx.fixtureUniverseRawPath,
        fixtureUniverse: ctx.fixture.universe,
        evidenceRoot: ctx.evidenceRoot,
        runLockTrustRoot: ctx.trustRoot,
        ...components,
        clock,
    };
}

function controlledClock() {
    const timestamps = [
        '2026-09-08T08:00:00Z',
        '2026-09-08T08:00:01Z',
        '2026-09-08T08:00:02Z',
        '2026-09-08T08:00:03Z',
        '2026-09-08T08:00:04Z',
        '2026-09-08T08:00:05Z',
        '2026-09-08T08:00:06Z',
        '2026-09-08T08:00:07Z',
    ];
    let index = 0;
    return () => timestamps[Math.min(index++, timestamps.length - 1)];
}

test('controlled binder rejects missing and malformed authorization before fake transport', async t => {
    const missing = makeContext(t);
    fs.unlinkSync(missing.authorizationPath);
    const missingComponents = componentsFor(missing);
    await assert.rejects(
        executeStageDControlledInitialization(binderOptions(missing, missingComponents)),
        error => error.code === 'ENOENT' || error.code === 'INVALID_AUTHORIZATION',
    );
    assert.equal(missingComponents.transport.call_count, 0);

    const malformed = makeContext(t);
    fs.chmodSync(malformed.authorizationPath, 0o600);
    fs.writeFileSync(malformed.authorizationPath, '{"authorization_id":"malformed"}');
    fs.chmodSync(malformed.authorizationPath, 0o444);
    const malformedComponents = componentsFor(malformed);
    await assert.rejects(
        executeStageDControlledInitialization(binderOptions(malformed, malformedComponents)),
        error => error.code === 'INVALID_CONTRACT' || error.code === 'NON_CANONICAL_EVIDENCE',
    );
    assert.equal(malformedComponents.transport.call_count, 0);
});

for (const [name, overrides, expectedCode] of [
    ['wrong provider', { provider: 'another-provider' }, 'INVALID_AUTHORIZATION'],
    ['wrong market', { configured_markets: ['totals'] }, 'INVALID_AUTHORIZATION'],
    ['wrong region', { configured_regions: ['us'] }, 'INVALID_AUTHORIZATION'],
    ['max requests greater than one', { max_provider_requests: 2 }, 'INVALID_AUTHORIZATION'],
    ['wrong accounting epoch', { accounting_epoch_id: `sde_${'e'.repeat(64)}` }, 'AUTHORIZATION_EPOCH_MISMATCH'],
]) {
    test(`controlled binder rejects ${name} before fake transport`, async t => {
        const ctx = makeContext(t, overrides);
        const components = componentsFor(ctx);
        await assert.rejects(
            executeStageDControlledInitialization(binderOptions(ctx, components)),
            error => error.code === expectedCode,
        );
        assert.equal(components.transport.call_count, 0);
        assert.equal(readRequestLedger({ ledgerRoot: ctx.ledgerRoot }).requests.length, 0);
    });
}

test('unknown quota state fails closed before fake transport', async t => {
    const ctx = makeContext(t);
    const components = componentsFor(ctx);
    const unknownQuota = quotaConfiguration({ quota_evidence_verified: false });
    const unknownQuotaSha256 = sha256Text(`${stableStringify(unknownQuota)}\n`);
    overwriteReadOnlyFile(ctx.quotaConfigPath, `${stableStringify(unknownQuota)}\n`);
    makeAuthorization(ctx, { quota_config_sha256: unknownQuotaSha256 });
    await assert.rejects(
        executeStageDControlledInitialization({
            ...binderOptions(ctx, components),
        }),
        error => error.code === 'UNVERIFIED_QUOTA_CONFIGURATION',
    );
    assert.equal(components.transport.call_count, 0);
    assert.equal(readRequestLedger({ ledgerRoot: ctx.ledgerRoot }).requests.length, 0);
});

test('controlled binder rejects a replaced quota input that retains the old authorization hash', async t => {
    const ctx = makeContext(t);
    const components = componentsFor(ctx);
    const replacedQuota = quotaConfiguration({
        monthly_quota_limit: 19,
        automated_spend_limit: 16,
    });
    overwriteReadOnlyFile(ctx.quotaConfigPath, `${stableStringify(replacedQuota)}\n`);
    await assert.rejects(
        executeStageDControlledInitialization(binderOptions(ctx, components)),
        error => error.code === 'AUTHORIZATION_QUOTA_MISMATCH',
    );
    assert.equal(components.transport.call_count, 0);
    assert.equal(readRequestLedger({ ledgerRoot: ctx.ledgerRoot }).requests.length, 0);
});

test('controlled binder rejects a replaced fixture RAW input that retains the old authorization hash', async t => {
    const ctx = makeContext(t);
    const components = componentsFor(ctx);
    overwriteReadOnlyFile(ctx.fixtureUniverseRawPath, `${ctx.rawText}\n`);
    await assert.rejects(
        executeStageDControlledInitialization(binderOptions(ctx, components)),
        error => error.code === 'AUTHORIZATION_FIXTURE_UNIVERSE_MISMATCH',
    );
    assert.equal(components.transport.call_count, 0);
    assert.equal(readRequestLedger({ ledgerRoot: ctx.ledgerRoot }).requests.length, 0);
});

test('authorization expiry after request intent is terminalized before fake transport', async t => {
    const ctx = makeContext(t, { expires_at: '2026-09-08T08:00:02Z' });
    const components = componentsFor(ctx);
    await assert.rejects(
        executeStageDControlledInitialization(binderOptions(ctx, components, controlledClock())),
        error => error.code === 'STAGE_D_AUTHORIZATION_EXPIRED',
    );
    assert.equal(components.transport.call_count, 0);
    const ledger = readRequestLedger({ ledgerRoot: ctx.ledgerRoot });
    assert.equal(ledger.requests.length, 1);
    assert.equal(ledger.requests[0].transmission_state, 'TRANSMISSION_NOT_STARTED');
    assert.equal(ledger.requests[0].terminal_state, 'CANCELLED_BEFORE_TRANSMISSION');
    assert.equal(ledger.requests[0].quota_units_charged_or_assumed, 0);
    assert.equal(ledger.requests[0].error_classification, 'STAGE_D_AUTHORIZATION_EXPIRED');
});

test('valid controlled authorization reaches the shared cycle path and sends at most once', async t => {
    const ctx = makeContext(t);
    const components = componentsFor(ctx);
    const result = await executeStageDControlledInitialization(binderOptions(ctx, components, controlledClock()));
    assert.equal(result.status, 'NO_OP_DUPLICATE_RAW_HASH');
    assert.equal(components.transport.call_count, 1);
    assert.equal(components.transactionPublisher.call_count, 0);
    assert.equal(result.authorization_audit.max_provider_requests, 1);
    assert.equal(result.authorization_audit.provider_transmission_attempted, true);
    assert.equal(readRequestLedger({ ledgerRoot: ctx.ledgerRoot }).requests.length, 1);
});

test('authorization consumption is replay-safe and a second use cannot transmit', async t => {
    const ctx = makeContext(t);
    const firstComponents = componentsFor(ctx);
    await executeStageDControlledInitialization(binderOptions(ctx, firstComponents, controlledClock()));
    const secondComponents = componentsFor(ctx);
    await assert.rejects(
        executeStageDControlledInitialization(binderOptions(ctx, secondComponents)),
        error => error.code === 'STAGE_D_AUTHORIZATION_REPLAY',
    );
    assert.equal(firstComponents.transport.call_count, 1);
    assert.equal(secondComponents.transport.call_count, 0);
    assert.equal(readRequestLedger({ ledgerRoot: ctx.ledgerRoot }).requests.length, 1);
});

test('transport failure after the transmission boundary does not retry', async t => {
    const ctx = makeContext(t);
    const components = componentsFor(ctx, { error: Object.assign(new Error('networkless post-boundary failure'), { code: 'ETIMEDOUT' }) });
    await assert.rejects(
        executeStageDControlledInitialization(binderOptions(ctx, components)),
        error => error.code === 'ETIMEDOUT',
    );
    assert.equal(components.transport.call_count, 1);
    const ledger = readRequestLedger({ ledgerRoot: ctx.ledgerRoot });
    assert.equal(ledger.requests.length, 1);
    assert.equal(ledger.requests[0].terminal_state, 'TRANSPORT_FAILURE_AFTER_POSSIBLE_TRANSMISSION');
});

test('binder refuses caller-supplied private runtime authorization', async t => {
    const ctx = makeContext(t);
    const components = componentsFor(ctx);
    await assert.rejects(
        executeStageDControlledInitialization({
            ...binderOptions(ctx, components),
            runtimeAuthorization: 'caller-fabricated-token',
        }),
        error => error.code === 'STAGE_D_RUNTIME_AUTHORIZATION_INPUT_FORBIDDEN',
    );
    assert.equal(components.transport.call_count, 0);
});

test('production binder refuses caller-supplied clock injection before any provider component is created', async t => {
    const ctx = makeContext(t);
    const components = componentsFor(ctx);
    const previousNodeEnv = process.env.NODE_ENV;
    process.env.NODE_ENV = 'production';
    try {
        await assert.rejects(
            executeStageDControlledInitialization({
                ...binderOptions(ctx, components),
                clock: () => AUTHORIZATION_NOW,
            }),
            error => error.code === 'TRUSTED_CLOCK_REQUIRED',
        );
    } finally {
        process.env.NODE_ENV = previousNodeEnv;
    }
    assert.equal(components.transport.call_count, 0);
    assert.equal(readRequestLedger({ ledgerRoot: ctx.ledgerRoot }).requests.length, 0);
});

test('CLI parser exposes only bounded artifact paths and cannot accept a private runtime authorization token', () => {
    for (const forbidden of ['--authorized', '--runtime-authorized', '--bypass-auth', '--force-live', '--live=true']) {
        assert.throws(() => parseControlledCliArgs([forbidden, 'true']), /unknown or forbidden argument/);
    }
    assert.throws(() => parseControlledCliArgs(['--authorization', 'auth.json']), /is required/);
    assert.equal(typeof parseControlledCliArgs, 'function');
});
