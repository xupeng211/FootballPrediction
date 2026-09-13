'use strict';

// End-to-end tests for the two ops CLIs, driven as real child processes.
//
// The CLIs are the only way an operator reaches this tooling, so they are
// exercised the way an operator would: separate processes, explicit arguments,
// structured JSON on stdout, a meaningful exit code.  Nothing here reaches the
// network, and no test supplies a credential because no CLI accepts one.

const assert = require('node:assert/strict');
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const test = require('node:test');
const { spawnSync } = require('node:child_process');

const { buildBackupFixture } = require('../../../helpers/backup_authority_fixture');
const { createLocalTransport } = require('../../../../src/infrastructure/market_evidence/backup/localTransport');
const { payloadObjectKey } = require('../../../../src/infrastructure/market_evidence/backup/snapshotManifest');

const REPOSITORY_ROOT = path.resolve(__dirname, '..', '..', '..', '..');
const SNAPSHOT_CLI = path.join(REPOSITORY_ROOT, 'scripts', 'ops', 'stage_d_backup_snapshot.js');
const RESTORE_CLI = path.join(REPOSITORY_ROOT, 'scripts', 'ops', 'stage_d_restore_verify.js');

let shared = null;
function fixture() {
    if (shared === null) shared = buildBackupFixture({ transactionCount: 2, includeLedgerEntries: 1 });
    return shared;
}
test.after(() => { if (shared) shared.cleanup(); });

function temporary(t, prefix) {
    const root = fs.mkdtempSync(path.join(os.tmpdir(), prefix));
    t.after(() => fs.rmSync(root, { recursive: true, force: true }));
    return root;
}

function runCli(scriptPath, args, options = {}) {
    const result = spawnSync(process.execPath, [scriptPath, ...args], {
        cwd: options.cwd || REPOSITORY_ROOT,
        encoding: 'utf8',
        env: { PATH: process.env.PATH || '' },
    });
    return { status: result.status, stdout: result.stdout || '', stderr: result.stderr || '' };
}

function payloadOf(result) {
    const line = result.stdout.trim().split('\n').filter(Boolean).pop();
    assert.ok(line, `no JSON line on stdout (status ${result.status}, stderr: ${result.stderr.slice(0, 400)})`);
    return JSON.parse(line);
}

function snapshotArguments(transportRoot, overrides = {}) {
    const fx = fixture();
    return [
        '--transport-root', transportRoot,
        '--authority-root', fx.authorityRoot,
        '--allocation-artifact', fx.allocationArtifactPath,
        '--ledger-root', fx.ledgerRoot,
        '--quota-config', fx.quotaConfigPath,
        ...(overrides.extra || []),
    ];
}

function writeThroughCli(t, name, overrides = {}) {
    const transportRoot = temporary(t, `stage-d-cli-${name}-`);
    const result = runCli(SNAPSHOT_CLI, snapshotArguments(transportRoot, overrides));
    assert.equal(result.status, 0, `snapshot CLI failed: ${result.stdout}`);
    const payload = payloadOf(result);
    assert.equal(payload.action, 'SNAPSHOT_WRITTEN');
    return { transportRoot, report: payload.report };
}

test('a generation written by the CLI verifies and restores through the CLI', async t => {
    const { transportRoot, report } = writeThroughCli(t, 'roundtrip');

    const verified = runCli(RESTORE_CLI, ['--transport-root', transportRoot, '--snapshot-id', report.snapshot_id, '--verify-only']);
    assert.equal(verified.status, 0, verified.stdout);
    const verifiedPayload = payloadOf(verified);
    assert.equal(verifiedPayload.action, 'SNAPSHOT_VERIFIED');
    assert.equal(verifiedPayload.report.result, 'PASS');
    assert.deepEqual(verifiedPayload.report.failures, []);
    assert.equal(verifiedPayload.live_r2_cli_wiring, 'NOT_IMPLEMENTED');

    const destinationRoot = path.join(temporary(t, 'stage-d-cli-dest-'), 'restored');
    const restored = runCli(RESTORE_CLI, ['--transport-root', transportRoot, '--snapshot-id', report.snapshot_id, '--destination-root', destinationRoot, '--fresh-process']);
    assert.equal(restored.status, 0, restored.stdout);
    const restoredPayload = payloadOf(restored);
    assert.equal(restoredPayload.action, 'SNAPSHOT_RESTORED');
    assert.equal(restoredPayload.report.result, 'PASS');
    assert.equal(restoredPayload.report.fresh_process_proof.ok, true, restoredPayload.report.fresh_process_proof.error);
    assert.equal(restoredPayload.report.fresh_process_proof.identity.head_transaction_id, report.source_head_transaction_id);
    assert.equal(restoredPayload.report.restored_file_count, report.artifact_count);

    // The restored tree is a complete, readable, non-writable authority.
    assert.equal(fs.lstatSync(path.join(destinationRoot, 'transactions', 'STORE.json')).mode & 0o7777, 0o444);
    assert.ok(fs.readdirSync(path.join(destinationRoot, 'request-accounting', 'entries')).length >= 1);
});

test('the CLI round trip is stable across a fixed snapshot id', async t => {
    const fixedId = 'snap_20260913T000000000Z_0011223344556677';
    const { report } = writeThroughCli(t, 'fixed', { extra: ['--snapshot-id', fixedId, '--now', '2026-09-13T00:00:00Z'] });
    assert.equal(report.snapshot_id, fixedId);
    assert.equal(report.manifest_object_key, `${fixedId}/MANIFEST.json`);
    assert.equal(report.completeness_object_key, `${fixedId}/COMPLETE`);
    assert.equal(report.source_head_transaction_id, fixture().head_transaction_id);
    assert.equal(report.source_state_hash, fixture().state_hash);
    assert.equal(report.observation_count, fixture().observation_count);
    assert.equal(report.source_identity_equal, true);
    assert.equal(report.staging_excluded, true);
});

test('a snapshot id that is already occupied is refused, not overwritten', async t => {
    const transportRoot = temporary(t, 'stage-d-cli-collision-');
    const args = snapshotArguments(transportRoot, { extra: ['--snapshot-id', 'snap_20260913T000000000Z_0011223344556677'] });
    assert.equal(runCli(SNAPSHOT_CLI, args).status, 0);

    const second = runCli(SNAPSHOT_CLI, args);
    assert.equal(second.status, 1);
    const payload = payloadOf(second);
    assert.equal(payload.action, 'SNAPSHOT_FAILED');
    assert.equal(payload.code, 'OBJECT_ALREADY_EXISTS');
    assert.ok(/already exists/.test(payload.error));
});

test('the CLI report describes the generation without carrying payload bytes', async t => {
    const { report } = writeThroughCli(t, 'reportshape');
    const serialized = JSON.stringify(report);
    assert.ok(serialized.length < 20000, `the report must be a description, not a copy (was ${serialized.length} bytes)`);
    assert.equal(serialized.includes('BEGIN'), false);
    assert.equal(/access[_-]?key|secret[_-]?access|session[_-]?token/i.test(serialized), false);
    assert.equal(report.transport.kind, 'local');
    assert.equal(report.transport.create_only, true);
    assert.equal(report.transport.delete_exposed, false);
    assert.equal(report.categories.transaction_package, 12, 'two committed packages of six files each');
    assert.equal(Object.values(report.categories).reduce((sum, count) => sum + count, 0), report.artifact_count);
    assert.equal(report.categories.store, 1);
    assert.equal(report.categories.allocation_authority, 1);
    assert.equal(report.categories.request_accounting_epoch, 1);
    assert.equal(report.categories.request_accounting_entry, 2, 'the epoch genesis entry plus one recorded request');
    assert.equal(report.categories.quota_config, 1);
    assert.equal(report.categories.run_state, undefined, 'run state is captured only when it is named');
});

test('the CLI captures run state only when a run state root is named', async t => {
    const runStateRoot = temporary(t, 'stage-d-cli-runstate-');
    fs.writeFileSync(path.join(runStateRoot, 'turn.json'), '{"turn":1}');
    const { report } = writeThroughCli(t, 'runstate', { extra: ['--run-state', runStateRoot] });
    assert.equal(report.categories.run_state, 1);
});

test('the CLI fails closed and exits non-zero when a root does not exist', t => {
    const transportRoot = temporary(t, 'stage-d-cli-missing-');
    const args = snapshotArguments(transportRoot);
    const brokenIndex = args.indexOf('--authority-root') + 1;
    args[brokenIndex] = path.join(transportRoot, 'does-not-exist');
    const result = runCli(SNAPSHOT_CLI, args);
    assert.equal(result.status, 1);
    const payload = payloadOf(result);
    assert.equal(payload.action, 'SNAPSHOT_FAILED');
    assert.ok(/does not exist/.test(payload.error), payload.error);
    assert.equal(payload.code, 'SNAPSHOT_INTEGRITY_VIOLATION');
    // A failed snapshot leaves no sealed generation behind.
    assert.deepEqual(fs.readdirSync(transportRoot), []);
});

// Every live-target flag is refused in both spellings, and the refused value
// never reaches stdout or stderr.
//
// `--endpoint https://…` and `--endpoint=…` mean the same thing to whoever
// types them, so a check that only matched the first would silently ignore the
// second -- the operator would believe the command was aimed at R2 and get a
// local run instead.  And a value passed to one of these flags may be a
// credential, so echoing it back would turn a refusal into a leak.
test('both CLIs reject every live-target flag in both spellings without echoing the value', t => {
    const transportRoot = temporary(t, 'stage-d-backup-cli-live-');
    const secret = 'AKIALIVETARGETSECRETVALUE';
    const flags = [
        ['--endpoint', 'https://example.invalid'],
        ['--bucket', 'stage-d-backup'],
        ['--region', 'auto'],
        ['--access-key-id', secret],
        ['--secret-access-key', secret],
        ['--session-token', secret],
        ['--credentials', secret],
        ['--profile', 'default'],
        ['--r2', 'yes'],
        ['--s3', 'yes'],
        ['--live', 'yes'],
        ['--remote', 'yes'],
    ];

    for (const scriptPath of [SNAPSHOT_CLI, RESTORE_CLI]) {
        const name = path.basename(scriptPath);
        for (const [flag, value] of flags) {
            for (const args of [[flag, value], [`${flag}=${value}`]]) {
                const result = runCli(scriptPath, [...args, '--transport-root', transportRoot]);
                assert.notEqual(result.status, 0, `${name} ${args[0]} must fail rather than run`);
                assert.ok(
                    /LIVE_R2_CLI_WIRING=NOT_IMPLEMENTED/.test(result.stdout + result.stderr),
                    `${name} ${args[0]} must be refused by the live-target check, not by something downstream`,
                );
                assert.equal(
                    (result.stdout + result.stderr).includes(secret),
                    false,
                    `${name} ${args[0]} must not echo the value it refused`,
                );
            }
        }
    }
});

test('the CLI refuses a flag whose value is missing rather than consuming the next flag', t => {
    const transportRoot = temporary(t, 'stage-d-cli-novalue-');
    const result = runCli(SNAPSHOT_CLI, ['--transport-root', '--authority-root', transportRoot]);
    assert.equal(result.status, 1);
    const payload = payloadOf(result);
    assert.equal(payload.action, 'SNAPSHOT_FAILED');
    assert.ok(/--transport-root requires a value/.test(payload.error), payload.error);
});

test('the CLI refuses a destination inside its own transport root', async t => {
    const { transportRoot, report } = writeThroughCli(t, 'insidetransport');
    const inside = path.join(transportRoot, 'restored');
    const result = runCli(RESTORE_CLI, ['--transport-root', transportRoot, '--snapshot-id', report.snapshot_id, '--destination-root', inside]);
    assert.equal(result.status, 1, result.stdout);
    const payload = payloadOf(result);
    assert.equal(payload.action, 'RESTORE_VERIFY_FAILED');
    assert.equal(fs.existsSync(inside), false, 'a refused restore must not have created anything');
});

test('a restore never overwrites, so the second attempt fails and the first tree survives', async t => {
    const { transportRoot, report } = writeThroughCli(t, 'nooverwrite');
    const destinationRoot = path.join(temporary(t, 'stage-d-cli-occupied-'), 'restored');
    const args = ['--transport-root', transportRoot, '--snapshot-id', report.snapshot_id, '--destination-root', destinationRoot];
    assert.equal(runCli(RESTORE_CLI, args).status, 0);
    const before = fs.readFileSync(path.join(destinationRoot, 'transactions', 'STORE.json'));

    const second = runCli(RESTORE_CLI, args);
    assert.equal(second.status, 1);
    const payload = payloadOf(second);
    assert.equal(payload.action, 'RESTORE_VERIFY_FAILED');
    assert.ok(/already exists/.test(payload.error), payload.error);
    assert.deepEqual(fs.readFileSync(path.join(destinationRoot, 'transactions', 'STORE.json')), before);
});

test('a tampered generation is reported as FAIL with the failing codes and exits non-zero', async t => {
    const { transportRoot, report } = writeThroughCli(t, 'tamperedverify');
    const target = path.join(transportRoot, ...payloadObjectKey(report.snapshot_id, 'transactions/STORE.json').split('/'));
    const bytes = Buffer.from(fs.readFileSync(target));
    bytes[0] ^= 0x01;
    fs.writeFileSync(target, bytes);

    const result = runCli(RESTORE_CLI, ['--transport-root', transportRoot, '--snapshot-id', report.snapshot_id, '--verify-only']);
    assert.equal(result.status, 1);
    const payload = payloadOf(result);
    assert.equal(payload.action, 'SNAPSHOT_VERIFIED');
    assert.equal(payload.report.result, 'FAIL');
    assert.deepEqual(payload.report.failures.map(item => item.code), ['ARTIFACT_HASH_MISMATCH']);
});

test('a restore of a tampered generation fails and reports the carried report', async t => {
    const { transportRoot, report } = writeThroughCli(t, 'tamperedrestore');
    const target = path.join(transportRoot, ...payloadObjectKey(report.snapshot_id, 'transactions/STORE.json').split('/'));
    const bytes = Buffer.from(fs.readFileSync(target));
    bytes[0] ^= 0x01;
    fs.writeFileSync(target, bytes);

    const destinationRoot = path.join(temporary(t, 'stage-d-cli-tainted-'), 'restored');
    const result = runCli(RESTORE_CLI, ['--transport-root', transportRoot, '--snapshot-id', report.snapshot_id, '--destination-root', destinationRoot]);
    assert.equal(result.status, 1);
    const payload = payloadOf(result);
    assert.equal(payload.action, 'RESTORE_VERIFY_FAILED');
    assert.ok(/content the manifest does not bind/.test(payload.error), payload.error);
    assert.equal(fs.existsSync(path.join(destinationRoot, 'transactions', 'STORE.json')), false);
});

test('verify-only writes nothing anywhere', async t => {
    const { transportRoot, report } = writeThroughCli(t, 'verifyreadonly');
    const inventory = () => fs.readdirSync(transportRoot, { recursive: true }).sort();
    const before = inventory();
    const result = runCli(RESTORE_CLI, ['--transport-root', transportRoot, '--snapshot-id', report.snapshot_id, '--verify-only']);
    assert.equal(result.status, 0);
    assert.deepEqual(inventory(), before);
});

test('both CLIs run from any working directory', async t => {
    const { transportRoot, report } = writeThroughCli(t, 'cwd');
    const elsewhere = temporary(t, 'stage-d-cli-cwd-');
    const verified = runCli(RESTORE_CLI, ['--transport-root', transportRoot, '--snapshot-id', report.snapshot_id, '--verify-only'], { cwd: elsewhere });
    assert.equal(verified.status, 0, verified.stdout);
    assert.equal(payloadOf(verified).report.result, 'PASS');

    const anotherRoot = temporary(t, 'stage-d-cli-cwd2-');
    const written = runCli(SNAPSHOT_CLI, snapshotArguments(anotherRoot), { cwd: '/' });
    assert.equal(written.status, 0, written.stdout);
    assert.equal(payloadOf(written).action, 'SNAPSHOT_WRITTEN');
});

test('the CLI produces a generation a library call can then verify', async t => {
    const { transportRoot, report } = writeThroughCli(t, 'clilibrary');
    const backup = require('../../../../src/infrastructure/market_evidence/backup');
    const transport = createLocalTransport({ root: transportRoot });
    const verified = await backup.verifySnapshot({ transport, snapshotId: report.snapshot_id });
    assert.equal(verified.result, 'PASS');
    const { manifest } = await backup.loadAcceptedManifest({ transport, snapshotId: report.snapshot_id });
    assert.equal(manifest.snapshot_id, report.snapshot_id);
    assert.equal(manifest.artifact_count, report.artifact_count);
    assert.equal(manifest.total_bytes, report.total_bytes);
    assert.equal(manifest.secrets_included, false);
});
