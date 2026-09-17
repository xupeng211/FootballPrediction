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
    createStageDOddsApiTransport,
    executeStageDControlledInitialization,
} = require('../../../src/infrastructure/market_evidence/stageDOperations');
const {
    STAGE_D_STABLE_PROXY_CONTRACT,
    STAGE_D_PROXY_ENDPOINT_ENV_VAR,
    STAGE_D_PROXY_PREFLIGHT_TARGET_ENV_VAR,
    STAGE_D_PROXY_PREFLIGHT_SECRET_ENV_VAR,
    PROXY_PREFLIGHT_PASS,
    PROXY_CONFIGURATION_MISSING,
    PROXY_URL_INVALID,
    PROXY_TCP_CONNECT_FAILED,
    PROXY_CONNECT_PROTOCOL_INVALID,
    PROXY_PREFLIGHT_TARGET_CONFIGURATION_MISSING,
    PREFLIGHT_ATTESTATION_SECRET_MISSING,
    resolveStageDStableProxyEndpoint,
    resolveStageDPreflightTarget,
    resolveStageDPreflightSecret,
    createStageDHttpConnectProxyPreflight,
} = require('../../../src/infrastructure/market_evidence/stageDStableProxy');

// The contract's own privileged, essentially never-bound loopback address.  Naming it as
// an explicitly configured probe target keeps the "definitely dead endpoint" claim tied to
// an address nothing is listening on, without relying on any implicit default.
const DEAD_ENDPOINT_URL = 'http://127.0.0.1:1';
const INERT_TARGET = resolveStageDPreflightTarget({ [STAGE_D_PROXY_PREFLIGHT_TARGET_ENV_VAR]: 'tcp://127.0.0.1:9' });

// An obvious fake attestation secret, used only to get the preflight past configuration
// resolution in the tests whose subject is a later failure.  It is never a production
// value and never leaves this file.
const TEST_PREFLIGHT_SECRET = resolveStageDPreflightSecret({
    [STAGE_D_PROXY_PREFLIGHT_SECRET_ENV_VAR]: Buffer.from('stage-d-test-secret-not-production-0123456789abcdef', 'utf8').toString('base64'),
});

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

// The binder proves the Stage D proxy contract before it spends the one-shot
// authorization.  Binder tests below exercise post-preflight behaviour, so they supply
// a preflight that resolves without touching the network.  The real HTTP CONNECT probe
// is covered by stage_d_stable_proxy_preflight.test.js.
function createStageDFakeProxyPreflight({ classification = PROXY_PREFLIGHT_PASS, onRun = null } = {}) {
    const result = Object.freeze({
        schema_version: 'footballprediction-stage-d-http-connect-proxy-preflight/v1',
        proxy_contract: STAGE_D_STABLE_PROXY_CONTRACT,
        classification,
        passed: classification === PROXY_PREFLIGHT_PASS,
        endpoint: 'http://proxy.invalid:3128',
        scheme: 'http',
        host: 'proxy.invalid',
        port: 3128,
        has_credentials: false,
        probe_destination: '127.0.0.1:1',
        provider_contacted: false,
        provider_dns_resolved: false,
        started_at: AUTHORIZATION_NOW,
        completed_at: AUTHORIZATION_NOW,
        detail: null,
    });
    let callCount = 0;
    return Object.freeze({
        schema_version: 'footballprediction-stage-d-http-connect-proxy-preflight/v1',
        proxy_contract: STAGE_D_STABLE_PROXY_CONTRACT,
        timeout_ms: 1,
        get call_count() { return callCount; },
        async run() {
            callCount += 1;
            // A seam for the clock race: a probe is bounded by its own socket budget, so
            // time genuinely passes inside it, and the only place a test can observe that
            // deterministically is between entering the probe and returning from it.
            if (onRun !== null) onRun();
            return result;
        },
    });
}

function consumptionMarkers(ctx) {
    return fs.readdirSync(ctx.trustRoot).filter(name => name.startsWith('.stage-d-authorization-consumed'));
}

function consumptionMarkerContents(ctx) {
    return consumptionMarkers(ctx).map(name => JSON.parse(fs.readFileSync(path.join(ctx.trustRoot, name), 'utf8')));
}

function componentsFor(ctx, { error = null, transmissionClock = null, proxyPreflight = null } = {}) {
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
        transport: createStageDFakeTransport({ response: error ? null : JSON.stringify(response), error, transmissionClock }),
        evidencePersistence: createStageDEvidencePersistence({ evidenceRoot: ctx.evidenceRoot }),
        candidateBuilder: createStageDProspectiveCandidateBuilder({ universe: ctx.fixture.universe }),
        transactionPublisher: createStageDFakePublisher({
            authorityRoot: ctx.authorityRoot,
            allocationArtifactPath: ctx.allocationArtifactPath,
            status: 'unexpected-publish',
        }),
        proxyPreflight: proxyPreflight || createStageDFakeProxyPreflight(),
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

test('authorization expiry immediately before fake transport transmission is rejected without a fake call', async t => {
    const ctx = makeContext(t, { expires_at: '2026-09-08T08:00:05Z' });
    const components = componentsFor(ctx, { transmissionClock: () => '2026-09-08T08:00:05Z' });
    await assert.rejects(
        executeStageDControlledInitialization(binderOptions(ctx, components, controlledClock())),
        error => error.code === 'STAGE_D_AUTHORIZATION_EXPIRED',
    );
    assert.equal(components.transport.call_count, 0);
    const ledger = readRequestLedger({ ledgerRoot: ctx.ledgerRoot });
    assert.equal(ledger.requests.length, 1);
    assert.equal(ledger.requests[0].transmission_state, 'TRANSMISSION_STARTED_OR_MAY_HAVE_STARTED');
    assert.equal(ledger.requests[0].terminal_state, 'TRANSPORT_FAILURE_AFTER_POSSIBLE_TRANSMISSION');
    assert.equal(ledger.requests[0].quota_units_charged_or_assumed, 1);
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

// ---------------------------------------------------------------------------
// Ordering invariant: the Stage D proxy contract is proven BEFORE the one-shot
// authorization is spent.  A proxy that is dead, missing, or not speaking HTTP
// CONNECT must leave AUTHORIZATION_CONSUMED=NO, PROVIDER_REQUEST_ATTEMPTED=NO and
// QUOTA_UNITS_CHARGED_OR_ASSUMED=0 -- the defect that spent the previous
// authorization was exactly a proxy failure discovered after consumption.
// ---------------------------------------------------------------------------

test('a preflight that does not pass fails closed before the authorization is consumed', async t => {
    for (const classification of [
        PROXY_TCP_CONNECT_FAILED,
        PROXY_CONNECT_PROTOCOL_INVALID,
        PROXY_CONFIGURATION_MISSING,
        PROXY_URL_INVALID,
    ]) {
        const ctx = makeContext(t);
        const proxyPreflight = createStageDFakeProxyPreflight({ classification });
        const components = componentsFor(ctx, { proxyPreflight });

        await assert.rejects(
            executeStageDControlledInitialization(binderOptions(ctx, components)),
            error => error.code === classification,
        );

        assert.equal(proxyPreflight.call_count, 1, `${classification}: the preflight must run exactly once`);
        assert.equal(consumptionMarkers(ctx).length, 0, `${classification}: the authorization must not be consumed`);
        assert.equal(readRequestLedger({ ledgerRoot: ctx.ledgerRoot }).requests.length, 0, `${classification}: no request may be accounted`);
        assert.equal(components.transport.call_count, 0, `${classification}: no transmission may be attempted`);
    }
});

test('a dead proxy endpoint fails closed before the authorization is consumed', async t => {
    // The strongest form of the regression: the real probe, against a real closed port.
    // Port 1 is privileged and never bound, so the refusal is deterministic.
    const ctx = makeContext(t);
    const proxyPreflight = createStageDHttpConnectProxyPreflight({
        endpoint: resolveStageDStableProxyEndpoint({ [STAGE_D_PROXY_ENDPOINT_ENV_VAR]: DEAD_ENDPOINT_URL }),
        target: INERT_TARGET,
        secret: TEST_PREFLIGHT_SECRET,
        timeoutMs: 2000,
    });
    const components = componentsFor(ctx, { proxyPreflight });

    await assert.rejects(
        executeStageDControlledInitialization(binderOptions(ctx, components)),
        error => error.code === PROXY_TCP_CONNECT_FAILED,
    );

    assert.equal(consumptionMarkers(ctx).length, 0);
    assert.equal(readRequestLedger({ ledgerRoot: ctx.ledgerRoot }).requests.length, 0);
    assert.equal(components.transport.call_count, 0);
});

// The authorization window and the preflight are two independent clocks.  The preflight
// is bounded by its own socket budget, not by the authorization's lifetime, so a probe
// can outlive an authorization that was valid when it started.  These three tests pin the
// resulting ordering: the authority is consumed against a reading taken AFTER the
// preflight, that same reading is the one recorded in the immutable marker, and a probe
// that outlives the window fails closed before the marker exists at all.
test('an authorization that expires during the preflight is not consumed', async t => {
    const ctx = makeContext(t);
    let currentTime = AUTHORIZATION_NOW;
    // Time advances only while the probe runs; the preflight itself still PASSES, so the
    // only thing standing between this cycle and a spent authorization is the re-read.
    const proxyPreflight = createStageDFakeProxyPreflight({
        onRun: () => { currentTime = '2026-09-09T07:00:01Z'; },
    });
    const components = componentsFor(ctx, { proxyPreflight });

    await assert.rejects(
        executeStageDControlledInitialization(binderOptions(ctx, components, () => currentTime)),
        error => error.code === 'STAGE_D_AUTHORIZATION_EXPIRED',
    );

    assert.equal(proxyPreflight.call_count, 1, 'the preflight must still have run');
    assert.equal(consumptionMarkers(ctx).length, 0, 'the immutable consumption marker must not exist');
    assert.equal(readRequestLedger({ ledgerRoot: ctx.ledgerRoot }).requests.length, 0, 'no request intent may be created');
    assert.equal(components.transport.call_count, 0, 'no transmission may be attempted');
});

test('an authorization expiring exactly at the post-preflight reading is not consumed', async t => {
    // The canonical boundary is inclusive-of-expiry: now >= expires_at is expired.  The
    // re-read must not quietly relax that into "still valid at the instant of expiry".
    const ctx = makeContext(t);
    let currentTime = AUTHORIZATION_NOW;
    const proxyPreflight = createStageDFakeProxyPreflight({
        onRun: () => { currentTime = AUTHORIZATION_EXPIRES; },
    });
    const components = componentsFor(ctx, { proxyPreflight });

    await assert.rejects(
        executeStageDControlledInitialization(binderOptions(ctx, components, () => currentTime)),
        error => error.code === 'STAGE_D_AUTHORIZATION_EXPIRED',
    );

    assert.equal(consumptionMarkers(ctx).length, 0, 'expiry at the exact boundary must not consume authority');
    assert.equal(readRequestLedger({ ledgerRoot: ctx.ledgerRoot }).requests.length, 0);
    assert.equal(components.transport.call_count, 0);
});

test('an authorization valid through the preflight is consumed at the post-preflight reading', async t => {
    // The positive control: the re-read must not refuse authorizations that are still
    // valid, and the timestamp recorded must be the post-preflight one rather than the
    // stale pre-preflight one.
    const ctx = makeContext(t);
    // AUTHORIZATION_NOW before the probe, then a distinct reading after it.  The value is
    // the instant the shared fixtures stamp their response at, so the cycle's receipt
    // ordering rules (request <= response <= ingestion) still hold; the point of the test
    // is only that the post-preflight reading differs from the pre-preflight one and is
    // the one recorded.
    const POST_PREFLIGHT_READING = '2026-09-08T08:00:05Z';
    let probeFinished = false;
    const advancingClock = () => (probeFinished ? POST_PREFLIGHT_READING : AUTHORIZATION_NOW);
    const proxyPreflight = createStageDFakeProxyPreflight({
        onRun: () => { probeFinished = true; },
    });
    const components = componentsFor(ctx, { proxyPreflight });

    const result = await executeStageDControlledInitialization(binderOptions(ctx, components, advancingClock));

    assert.equal(result.proxy_preflight.passed, true);
    const markers = consumptionMarkerContents(ctx);
    assert.equal(markers.length, 1, 'a still-valid authorization must still be consumed exactly once');
    assert.equal(markers[0].consumed_at, POST_PREFLIGHT_READING, 'the marker must record the post-preflight reading');
    assert.notEqual(markers[0].consumed_at, AUTHORIZATION_NOW, 'the marker must not record the pre-preflight reading');
    assert.equal(components.transport.call_count, 1, 'a valid authorization must still reach the transport');
});

test('a missing dedicated endpoint fails closed even while the rotating harvesting pool is configured', async t => {
    const previousEndpoint = process.env[STAGE_D_PROXY_ENDPOINT_ENV_VAR];
    delete process.env[STAGE_D_PROXY_ENDPOINT_ENV_VAR];
    t.after(() => {
        if (previousEndpoint === undefined) delete process.env[STAGE_D_PROXY_ENDPOINT_ENV_VAR];
        else process.env[STAGE_D_PROXY_ENDPOINT_ENV_VAR] = previousEndpoint;
    });

    const ctx = makeContext(t);
    // This is the production construction path: no endpoint argument, resolved from env.
    const components = componentsFor(ctx, { proxyPreflight: createStageDHttpConnectProxyPreflight() });

    await assert.rejects(
        executeStageDControlledInitialization(binderOptions(ctx, components)),
        error => error.code === PROXY_CONFIGURATION_MISSING,
    );

    assert.equal(consumptionMarkers(ctx).length, 0);
    assert.equal(readRequestLedger({ ledgerRoot: ctx.ledgerRoot }).requests.length, 0);
    assert.equal(components.transport.call_count, 0);
});

test('an unconfigured probe target fails closed before the authorization is consumed', async t => {
    // The probe target is a second, separate contract.  A Stage D cycle with an endpoint but
    // no configured target has nothing the proxy could be proven against, so it must stop
    // before authority is spent rather than probing something implicit.
    const ctx = makeContext(t);
    const proxyPreflight = createStageDHttpConnectProxyPreflight({
        endpoint: resolveStageDStableProxyEndpoint({ [STAGE_D_PROXY_ENDPOINT_ENV_VAR]: 'http://127.0.0.1:1' }),
        env: {},
    });
    const components = componentsFor(ctx, { proxyPreflight });

    await assert.rejects(
        executeStageDControlledInitialization(binderOptions(ctx, components)),
        error => error.code === PROXY_PREFLIGHT_TARGET_CONFIGURATION_MISSING,
    );

    assert.equal(consumptionMarkers(ctx).length, 0);
    assert.equal(readRequestLedger({ ledgerRoot: ctx.ledgerRoot }).requests.length, 0);
    assert.equal(components.transport.call_count, 0);
});

test('an unconfigured attestation secret fails closed before the authorization is consumed', async t => {
    // The third contract, and the one that carries the security property: without the
    // shared secret there is no way to tell a real tunnel from a reflector, so a Stage D
    // cycle that has an endpoint and a target but no secret has no sound preflight.  It
    // must stop before authority is spent rather than probe with a weaker proof.
    const ctx = makeContext(t);
    const proxyPreflight = createStageDHttpConnectProxyPreflight({
        endpoint: resolveStageDStableProxyEndpoint({ [STAGE_D_PROXY_ENDPOINT_ENV_VAR]: 'http://127.0.0.1:1' }),
        target: INERT_TARGET,
        env: {},
    });
    const components = componentsFor(ctx, { proxyPreflight });

    await assert.rejects(
        executeStageDControlledInitialization(binderOptions(ctx, components)),
        error => error.code === PREFLIGHT_ATTESTATION_SECRET_MISSING,
    );

    assert.equal(consumptionMarkers(ctx).length, 0);
    assert.equal(readRequestLedger({ ledgerRoot: ctx.ledgerRoot }).requests.length, 0);
    assert.equal(components.transport.call_count, 0);
});

test('a passing preflight is recorded and still consumes the authorization exactly once', async t => {
    const ctx = makeContext(t);
    const proxyPreflight = createStageDFakeProxyPreflight();
    const components = componentsFor(ctx, { proxyPreflight });
    const result = await executeStageDControlledInitialization(binderOptions(ctx, components, controlledClock()));

    assert.equal(proxyPreflight.call_count, 1);
    assert.equal(consumptionMarkers(ctx).length, 1);
    assert.equal(result.proxy_preflight.passed, true);
    assert.equal(result.proxy_preflight.classification, PROXY_PREFLIGHT_PASS);
    assert.equal(result.proxy_preflight.proxy_contract, STAGE_D_STABLE_PROXY_CONTRACT);
    assert.equal(result.proxy_preflight.provider_contacted, false);
    assert.equal(result.proxy_preflight.provider_dns_resolved, false);
});

test('the production Stage D transport exposes the stable proxy contract and no pool binding', () => {
    const transport = createStageDOddsApiTransport({ apiKey: 'not-a-real-key' });
    assert.equal(transport.network_capability, 'provider');
    assert.equal(transport.proxy_contract, STAGE_D_STABLE_PROXY_CONTRACT);
});

test('the proxy preflight is a mandatory binder component and cannot be omitted', async t => {
    // `componentKeys` drives both the test-mode presence check and the production
    // STAGE_D_COMPONENT_OVERRIDE_FORBIDDEN check, so proving membership here proves the
    // production binder cannot be handed a caller-supplied preflight.  The production
    // override path itself is unreachable from a temp-dir harness: the runtime trust
    // root's parent chain is world-writable under /tmp, and that gate fires first.
    const ctx = makeContext(t);
    const components = componentsFor(ctx);
    const options = binderOptions(ctx, components);
    delete options.proxyPreflight;

    await assert.rejects(
        executeStageDControlledInitialization(options),
        error => error.code === 'STAGE_D_TEST_COMPONENTS_REQUIRED',
    );

    assert.equal(consumptionMarkers(ctx).length, 0);
    assert.equal(readRequestLedger({ ledgerRoot: ctx.ledgerRoot }).requests.length, 0);
    assert.equal(components.transport.call_count, 0);
    assert.equal(components.proxyPreflight.call_count, 0);
});
