'use strict';

const assert = require('node:assert/strict');
const { createHash } = require('node:crypto');
const { execFileSync } = require('node:child_process');
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const { test } = require('node:test');

const { buildBackupFixture } = require('../../helpers/backup_authority_fixture');
const stage = require('../../../src/infrastructure/market_evidence/stageDOperations');
const backup = require('../../../src/infrastructure/market_evidence/backup');
const { executeRestore } = require('../../../src/infrastructure/market_evidence/backup/restoreExecutor');
const { inspectForwardAccounting } = require('../../../src/infrastructure/market_evidence/stageDForwardAccounting');
const cli = path.resolve(__dirname, '../../../scripts/ops/stage_d_cycle.js');

function write(root, name, value) {
    const filename = path.join(root, name);
    const bytes = Buffer.from(JSON.stringify(value));
    fs.writeFileSync(filename, bytes, { mode: 0o400, flag: 'wx' });
    return { filename, sha: createHash('sha256').update(bytes).digest('hex') };
}

function binding(ledgerRoot) {
    const ledger = stage.readRequestLedger({ ledgerRoot });
    return {
        epoch_id: ledger.epoch.epoch_id, genesis: ledger.epoch.genesis_entry_hash,
        entries: ledger.entries.length, tail: ledger.last_entry_hash,
        consumed: stage.ledgerUsageSummary(ledger).consumed_request_count,
    };
}

function fixture(t, { used = 120, changedAccount = false, unknownHistory = true } = {}) {
    const fx = buildBackupFixture({ transactionCount: 1, includeLedgerEntries: 1 });
    t.after(fx.cleanup);
    stage.markRequestTerminal({
        ledgerRoot: fx.ledgerRoot, requestId: 'fixture-request-0001',
        terminalState: 'HTTP_FAILURE_AFTER_TRANSMISSION', at: '2026-09-13T00:01:01Z',
        errorClassification: 'HTTP_503',
    });
    const current = new Date().toISOString();
    const month = current.slice(0, 7);
    const end = new Date(Date.UTC(Number(current.slice(0, 4)), Number(current.slice(5, 7)), 1)).toISOString();
    const start = month + '-01T00:00:00.000Z';
    const expires = new Date(Math.min(Date.parse(current) + 3600000, Date.parse(end))).toISOString();
    const config = {
        ...require('../../../config/stage_d_quota_budget.json'),
        billing_period_id: month, period_start_at: start, period_end_at: end,
    };
    const cfg = write(fx.root, 'active-quota.json', config);
    const ledgerRoot = path.join(fx.root, 'next-ledger');
    const epoch = stage.initializeRequestAccountingEpoch({
        ledgerRoot, authoritySnapshot: fx, startedAt: current, epochId: 'fixture-next-segment',
    });
    const retained = binding(fx.ledgerRoot);
    const reportedTail = 'd'.repeat(64);
    const accountId = 'e'.repeat(64);
    const record = write(fx.root, 'opening-account.json', {
        provider: 'the-odds-api', account_identity_sha256: changedAccount ? 'f'.repeat(64) : accountId,
        period_id: month, period_start_at: start, period_end_at: end, observed_at: current, used, remaining: 500 - used,
    });
    const history = write(fx.root, 'history.json', {
        candidate_status: 'PREPARED_NOT_AUTHORIZED', prepared_at: '2026-09-22T00:00:00Z',
        runtime_bindings: {
            accounting_epoch_id: retained.epoch_id, ledger_entries: 12,
            consumed_requests: 4, ledger_last_entry_hash: reportedTail,
        },
    });
    const opening = write(fx.root, 'opening.json', {
        schema_version: 'footballprediction-stage-d-forward-opening/v1',
        account_identity_sha256: accountId, account_sha256: record.sha, history_sha256: history.sha,
        quota_config_sha256: cfg.sha, approved_at: current, expires_at: expires,
        run_id: 'open-run', request_id: 'open-request', account_exclusive: true, account_prior_usage_reconciled: true,
        history: {
            retained, reported_entries: 12, reported_tail: reportedTail,
            reported_consumed: 4, provider_effect: unknownHistory ? 'UNKNOWN' : 'PROVEN', missing_entries: true,
        },
        segment: { epoch_id: epoch.epoch_id, genesis: epoch.genesis_entry_hash, head: epoch.start_authority_head, state_hash: epoch.start_authority_state_hash },
    });
    function checkpoint(name) {
        return write(fx.root, name, { opening_sha256: opening.sha, ledger: binding(ledgerRoot) });
    }
    const initial = checkpoint('checkpoint-initial.json');
    const trustParent = process.env.STAGE_D_FORWARD_TEST_TRUST_PARENT || os.homedir();
    const runLockTrustRoot = fs.mkdtempSync(path.join(trustParent, '.stage-d-forward-fixture-'));
    t.after(() => fs.rmSync(runLockTrustRoot, { recursive: true, force: true }));
    const input = {
        openingPath: opening.filename, openingSha256: opening.sha,
        accountPath: record.filename, historyPath: history.filename,
        quotaConfigPath: cfg.filename, priorLedgerRoot: fx.ledgerRoot, ledgerRoot,
        authorityRoot: fx.authorityRoot, allocationAuthorityPath: fx.allocationArtifactPath, runLockTrustRoot,
        checkpointPath: initial.filename, checkpointSha256: initial.sha, now: current,
    };
    return { fx, input, checkpoint, expires };
}

function cliArgs(input) {
    return [
        cli, '--dry-run', '--forward-opening', input.openingPath,
        '--expected-opening-sha256', input.openingSha256, '--account-record', input.accountPath,
        '--history-record', input.historyPath, '--quota-config', input.quotaConfigPath,
        '--prior-ledger-root', input.priorLedgerRoot, '--ledger-root', input.ledgerRoot,
        '--authority-root', input.authorityRoot, '--allocation-authority', input.allocationAuthorityPath, '--run-lock-trust-root', input.runLockTrustRoot,
        '--ledger-checkpoint', input.checkpointPath, '--expected-checkpoint-sha256', input.checkpointSha256,
    ];
}

function reopen(input) {
    return JSON.parse(execFileSync(process.execPath, cliArgs(input), { encoding: 'utf8' }));
}

function transmit(input, requestId = 'open-request') {
    const state = { ledgerRoot: input.ledgerRoot, requestId };
    stage.recordRequestIntent({ ...state, runId: 'open-run', createdAt: input.now });
    stage.markTransmissionStarted({ ...state, transmittedAt: input.now });
}

function complete(input, used) {
    const providerQuota = stage.validateProviderQuotaRecord({
        raw_headers: { 'x-requests-used': String(used), 'x-requests-remaining': String(500 - used), 'x-requests-last': '1' },
        reported_used: used, reported_remaining: 500 - used, reported_last_cost: 1,
        expected_request_cost_credits: 1, reconciliation_status: 'RECONCILED',
    });
    stage.markRequestTerminal({
        ledgerRoot: input.ledgerRoot, requestId: 'open-request', at: input.now,
        terminalState: 'RESPONSE_RECEIVED', providerQuota,
    });
}

test('normal dry-run reads both ledgers and can only propose one unit', t => {
    const { input, expires } = fixture(t);
    const plan = reopen(input);
    assert.equal(plan.would_reserve_one, true);
    assert.equal(plan.transmission_permitted, false);
    assert.equal(plan.provider_requests, 0);
    assert.equal(plan.starting_used, 120);
    assert.equal(inspectForwardAccounting({ ...input, now: expires }).would_reserve_one, false);
    assert.equal(binding(input.ledgerRoot).entries, 0);
    assert.equal(binding(input.priorLedgerRoot).entries, 3);
});

test('unknown historical effect, account identity and independent hashes are mandatory', t => {
    const wrong = fixture(t, { changedAccount: true });
    assert.throws(() => inspectForwardAccounting(wrong.input), /账户身份/);
    const lost = fixture(t, { unknownHistory: false });
    assert.throws(() => inspectForwardAccounting(lost.input), /未知扣费/);
    const { input } = fixture(t);
    assert.throws(() => inspectForwardAccounting({ ...input, openingSha256: '0'.repeat(64) }), /摘要不符/);
    assert.throws(() => inspectForwardAccounting({ ...input, priorLedgerRoot: input.ledgerRoot }), /旧账本/);
});

test('reservation preserves 50 credits', t => {
    assert.equal(inspectForwardAccounting(fixture(t, { used: 449 }).input).would_reserve_one, true);
    assert.throws(() => inspectForwardAccounting(fixture(t, { used: 450 }).input), /超过预算/);
});

test('transmission without terminal evidence prevents any new reservation', t => {
    const { input, checkpoint } = fixture(t);
    transmit(input);
    const fresh = checkpoint('after-transmission.json');
    assert.throws(() => inspectForwardAccounting(input), /独立锚点/);
    const plan = inspectForwardAccounting({ ...input, checkpointPath: fresh.filename, checkpointSha256: fresh.sha });
    assert.equal(plan.state, 'STOPPED');
    assert.equal(plan.would_reserve_one, false);
});

test('first response must exactly match one credit over the opening balance', t => {
    for (const used of [121, 122]) {
        const { input, checkpoint } = fixture(t);
        transmit(input);
        complete(input, used);
        const end = checkpoint('after-response.json');
        const review = () => inspectForwardAccounting({ ...input, checkpointPath: end.filename, checkpointSha256: end.sha });
        if (used === 121) {
            assert.equal(review().state, 'RECONCILED');
            assert.equal(review().would_reserve_one, false);
        } else {
            assert.throws(review, /diverge/);
        }
    }
});

test('restore can reopen both generations in a fresh process and a stale generation fails', async t => {
    const { input, fx, checkpoint } = fixture(t);
    const transport = backup.createLocalTransport({ root: fs.mkdtempSync(path.join(fx.root, 'snapshot-')) });
    const common = { transport, authorityRoot: fx.authorityRoot, allocationArtifactPath: fx.allocationArtifactPath };
    const priorSnapshot = await backup.writeSnapshot({
        ...common, ledgerRoot: input.priorLedgerRoot, quotaConfigPath: fx.quotaConfigPath,
    });
    const nextSnapshotInputs = {
        ...common, ledgerRoot: input.ledgerRoot, quotaConfigPath: input.quotaConfigPath,
        runStateInputs: [input.openingPath, input.accountPath, input.historyPath],
    };
    const stale = await backup.writeSnapshot(nextSnapshotInputs);
    transmit(input);
    complete(input, 121);
    const end = checkpoint('after-response.json');
    const next = await backup.writeSnapshot(nextSnapshotInputs);
    const prior = await executeRestore({
        transport, snapshotId: priorSnapshot.snapshot_id, destinationRoot: path.join(fx.root, 'restored-prior'), includeFreshProcess: true,
    });
    const restoredRoot = path.join(fx.root, 'restored-next');
    const restored = await executeRestore({ transport, snapshotId: next.snapshot_id, destinationRoot: restoredRoot, includeFreshProcess: true });
    assert.equal(prior.result, 'PASS');
    assert.equal(restored.result, 'PASS');
    const restoredInput = {
        ...input, authorityRoot: restored.authority_root, allocationAuthorityPath: restored.allocation_artifact_path, ledgerRoot: restored.ledger_root, priorLedgerRoot: prior.ledger_root,
        quotaConfigPath: restored.quota_config_path,
        openingPath: path.join(restoredRoot, 'run-state', 'opening.json'),
        accountPath: path.join(restoredRoot, 'run-state', 'opening-account.json'),
        historyPath: path.join(restoredRoot, 'run-state', 'history.json'),
        checkpointPath: end.filename, checkpointSha256: end.sha,
    };
    assert.equal(reopen(restoredInput).quota_receipt.reported_used, 121);
    const staleRestore = await executeRestore({
        transport, snapshotId: stale.snapshot_id, destinationRoot: path.join(fx.root, 'restored-stale'),
    });
    assert.throws(() => inspectForwardAccounting({ ...restoredInput, ledgerRoot: staleRestore.ledger_root }), /独立锚点/);
    assert.throws(() => inspectForwardAccounting({
        ...restoredInput, checkpointPath: input.checkpointPath, checkpointSha256: input.checkpointSha256,
    }), /独立锚点/);
    assert.throws(() => inspectForwardAccounting({
        ...restoredInput, openingPath: path.join(restoredRoot, 'run-state', 'absent.json'),
    }), /ENOENT/);
});

test('either ledger being locked blocks the offline plan', t => {
    const { input } = fixture(t);
    for (const operationRoot of [input.ledgerRoot, input.priorLedgerRoot]) {
        const token = stage.acquireStageDRunLock({
            operationRoot, runId: 'another-run', acquiredAt: input.now, runLockTrustRoot: input.runLockTrustRoot,
        });
        try {
            assert.throws(() => inspectForwardAccounting(input), /存在运行锁/);
        } finally {
            stage.releaseStageDRunLock(token);
        }
    }
});
