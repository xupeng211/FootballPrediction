'use strict';

process.env.NODE_ENV = 'test';

const assert = require('node:assert/strict');
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const test = require('node:test');
const { sha256Text } = require('../../../src/infrastructure/market_evidence/contracts');
const {
    RUN_LOCK_FILE,
    runLockParentFile,
    runLockAncestorFile,
    runLockTrustFile,
    bindStageDRunLockGeneration,
    acquireStageDRunLock,
    releaseStageDRunLock,
    inspectStageDRunLock,
    initializeRequestAccountingEpoch,
    recordRequestIntent,
    markTransmissionStarted,
    markRequestTerminal,
    createStageDOddsApiTransport,
    createStageDFakeTransport,
} = require('../../../src/infrastructure/market_evidence/stageDOperations');

function removeRunLockArtifacts(root) {
    const resolved = path.resolve(root);
    for (const target of [
        path.join(resolved, RUN_LOCK_FILE),
        path.join(path.dirname(resolved), runLockParentFile(resolved)),
        path.join(path.dirname(path.dirname(resolved)), runLockAncestorFile(resolved)),
        path.join(path.dirname(path.dirname(resolved)), '.stage-d-runtime-trust', sha256Text(resolved), runLockTrustFile(resolved)),
    ]) {
        if (fs.existsSync(target)) fs.unlinkSync(target);
    }
}

test('provider credential preflight fails locally before the transmission boundary', () => {
    const transport = createStageDOddsApiTransport({ apiKey: '' });
    assert.throws(() => transport.preflight(), error => error.code === 'CREDENTIAL_INVALID');
});

test('run-lock parent-directory replacement cannot hide the ancestor reconciliation fence', t => {
    const container = fs.mkdtempSync(path.join(os.tmpdir(), 'stage-d-lock-parent-'));
    const parent = path.join(container, 'parent');
    const root = path.join(parent, 'ledger');
    fs.mkdirSync(root, { recursive: true, mode: 0o700 });
    t.after(() => { removeRunLockArtifacts(root); fs.rmSync(container, { recursive: true, force: true }); });
    const token = acquireStageDRunLock({ operationRoot: root, runId: 'parent-swap-run', acquiredAt: '2026-09-08T00:00:00Z' });
    const movedParent = `${parent}.moved`;
    fs.renameSync(parent, movedParent); fs.mkdirSync(root, { recursive: true, mode: 0o700 });
    assert.throws(() => releaseStageDRunLock(token), error => ['AMBIGUOUS_RUN_LOCK', 'DIRECTORY_IDENTITY_CHANGED'].includes(error.code));
    assert.equal(inspectStageDRunLock({ operationRoot: root }).state, 'ACTIVE_OR_STALE_REQUIRES_RECONCILIATION');
    assert.equal(inspectStageDRunLock({ operationRoot: path.join(movedParent, 'ledger') }).state, 'ACTIVE_OR_STALE_REQUIRES_RECONCILIATION');
    removeRunLockArtifacts(root); removeRunLockArtifacts(path.join(movedParent, 'ledger'));
    fs.rmSync(parent, { recursive: true, force: true }); fs.renameSync(movedParent, parent);
});

test('external runtime trust fence survives replacement of the operation parent', t => {
    const container = fs.mkdtempSync(path.join(os.tmpdir(), 'stage-d-lock-external-trust-'));
    const trustContainer = fs.mkdtempSync(path.join(os.tmpdir(), 'stage-d-lock-trust-domain-'));
    const parent = path.join(container, 'parent');
    const root = path.join(parent, 'ledger');
    const trustRoot = path.join(trustContainer, 'runtime-trust');
    fs.mkdirSync(root, { recursive: true, mode: 0o700 });
    fs.mkdirSync(trustRoot, { recursive: true, mode: 0o700 });
    t.after(() => {
        removeRunLockArtifacts(root);
        removeRunLockArtifacts(path.join(`${parent}.moved`, 'ledger'));
        fs.rmSync(container, { recursive: true, force: true });
        fs.rmSync(trustContainer, { recursive: true, force: true });
    });
    const token = acquireStageDRunLock({ operationRoot: root, runId: 'external-trust-run', acquiredAt: '2026-09-08T00:00:00Z', runLockTrustRoot: trustRoot });
    const movedParent = `${parent}.moved`;
    fs.renameSync(parent, movedParent);
    fs.mkdirSync(root, { recursive: true, mode: 0o700 });
    assert.equal(inspectStageDRunLock({ operationRoot: root, runLockTrustRoot: trustRoot }).state, 'ACTIVE_OR_STALE_REQUIRES_RECONCILIATION');
    assert.throws(() => releaseStageDRunLock(token), error => ['AMBIGUOUS_RUN_LOCK', 'DIRECTORY_IDENTITY_CHANGED'].includes(error.code));
});

test('fake transport accepts only serialized data fixtures and never evaluates a getter', () => {
    let getterCalled = false;
    const response = {};
    Object.defineProperty(response, 'raw_text', { enumerable: true, get() { getterCalled = true; throw new Error('getter must not execute'); } });
    assert.throws(() => createStageDFakeTransport({ response }), error => error.code === 'INVALID_CONTRACT');
    assert.equal(getterCalled, false);
});

test('clean release preserves a ledger-generation anchor and rejects a valid old ledger copy', t => {
    const container = fs.mkdtempSync(path.join(os.tmpdir(), 'stage-d-ledger-generation-'));
    const trustContainer = fs.mkdtempSync(path.join(os.tmpdir(), 'stage-d-ledger-generation-trust-'));
    const root = path.join(container, 'ledger');
    const trustRoot = path.join(trustContainer, 'runtime-trust');
    fs.mkdirSync(root, { recursive: true, mode: 0o700 });
    fs.mkdirSync(trustRoot, { recursive: true, mode: 0o700 });
    initializeRequestAccountingEpoch({
        ledgerRoot: root,
        authoritySnapshot: { head_transaction_id: `tx_${'a'.repeat(64)}`, state_hash: 'b'.repeat(64) },
        startedAt: '2026-09-08T00:00:00Z',
        epochId: `sde_${'c'.repeat(64)}`,
    });
    t.after(() => {
        removeRunLockArtifacts(root);
        fs.rmSync(container, { recursive: true, force: true });
        fs.rmSync(trustContainer, { recursive: true, force: true });
    });
    const token = acquireStageDRunLock({ operationRoot: root, runId: 'ledger-generation-run', acquiredAt: '2026-09-08T00:00:00Z', runLockTrustRoot: trustRoot });
    bindStageDRunLockGeneration(token, { ledgerRoot: root });
    releaseStageDRunLock(token);
    const oldCopy = `${root}.old`;
    fs.cpSync(root, oldCopy, { recursive: true });
    const consumedToken = acquireStageDRunLock({ operationRoot: root, runId: 'ledger-generation-consumed', acquiredAt: '2026-09-08T00:00:01Z', runLockTrustRoot: trustRoot });
    bindStageDRunLockGeneration(consumedToken, { ledgerRoot: root });
    recordRequestIntent({ ledgerRoot: root, requestId: 'generation-request', runId: 'ledger-generation-consumed', createdAt: '2026-09-08T00:00:02Z' });
    markTransmissionStarted({ ledgerRoot: root, requestId: 'generation-request', transmittedAt: '2026-09-08T00:00:03Z' });
    markRequestTerminal({ ledgerRoot: root, requestId: 'generation-request', terminalState: 'TRANSPORT_FAILURE_AFTER_POSSIBLE_TRANSMISSION', at: '2026-09-08T00:00:04Z', errorClassification: 'TEST_TIMEOUT' });
    bindStageDRunLockGeneration(consumedToken, { ledgerRoot: root });
    releaseStageDRunLock(consumedToken);
    const moved = `${root}.moved`;
    fs.renameSync(root, moved);
    fs.renameSync(oldCopy, root);
    const replacement = acquireStageDRunLock({ operationRoot: root, runId: 'ledger-generation-replacement', acquiredAt: '2026-09-08T00:00:01Z', runLockTrustRoot: trustRoot });
    assert.throws(() => bindStageDRunLockGeneration(replacement, { ledgerRoot: root }), error => ['LEDGER_GENERATION_CHANGED', 'LEDGER_GENERATION_ROLLBACK'].includes(error.code));
    releaseStageDRunLock(replacement);
});

test('runtime trust root contained by the operation root is rejected', t => {
    const root = fs.mkdtempSync(path.join(os.tmpdir(), 'stage-d-contained-trust-'));
    t.after(() => fs.rmSync(root, { recursive: true, force: true }));
    assert.throws(
        () => acquireStageDRunLock({ operationRoot: root, runId: 'contained-trust-run', acquiredAt: '2026-09-08T00:00:00Z', runLockTrustRoot: path.join(root, '.trust') }),
        error => error.code === 'UNSAFE_TRUST_ROOT',
    );
});
