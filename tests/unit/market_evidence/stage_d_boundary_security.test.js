'use strict';

process.env.NODE_ENV = 'test';

const assert = require('node:assert/strict');
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const test = require('node:test');
const {
    RUN_LOCK_FILE,
    runLockParentFile,
    runLockAncestorFile,
    acquireStageDRunLock,
    releaseStageDRunLock,
    inspectStageDRunLock,
    createStageDOddsApiTransport,
    createStageDFakeTransport,
} = require('../../../src/infrastructure/market_evidence/stageDOperations');

function removeRunLockArtifacts(root) {
    const resolved = path.resolve(root);
    for (const target of [
        path.join(resolved, RUN_LOCK_FILE),
        path.join(path.dirname(resolved), runLockParentFile(resolved)),
        path.join(path.dirname(path.dirname(resolved)), runLockAncestorFile(resolved)),
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

test('fake transport accepts only serialized data fixtures and never evaluates a getter', () => {
    let getterCalled = false;
    const response = {};
    Object.defineProperty(response, 'raw_text', { enumerable: true, get() { getterCalled = true; throw new Error('getter must not execute'); } });
    assert.throws(() => createStageDFakeTransport({ response }), error => error.code === 'INVALID_CONTRACT');
    assert.equal(getterCalled, false);
});
