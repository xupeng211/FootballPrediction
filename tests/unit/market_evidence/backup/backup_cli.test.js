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
const { installNetworkTripwire, PRELOAD_ENV } = require('../../../helpers/network_tripwire');
const { createLocalTransport } = require('../../../../src/infrastructure/market_evidence/backup/localTransport');
const { payloadObjectKey } = require('../../../../src/infrastructure/market_evidence/backup/snapshotManifest');

// The file runs behind the tripwire, and so does every child process it spawns.
// Sealing only the parent would leave the end-to-end path -- which is the whole
// point of this file -- unproven: the CLI does its work in a child, so a child
// that reached an endpoint would never touch the parent's seals.
const TRIPWIRE_PRELOAD = require.resolve('../../../helpers/network_tripwire');
const tripwire = installNetworkTripwire();
test.after(() => {
    assert.deepEqual(tripwire.attempts, [], 'no test in this file may attempt outbound network access');
    tripwire.restore();
});

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
        // The child gets the tripwire as a preload, so the CLI's own process is
        // sealed too.  The sentinel is what makes the helper install itself on
        // load; a plain `--require` would be indistinguishable from an import
        // and would leave the preloaded copy inert.
        env: {
            PATH: process.env.PATH || '',
            [PRELOAD_ENV]: '1',
            NODE_OPTIONS: `--require ${TRIPWIRE_PRELOAD}`,
        },
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

// A denylist can only refuse the names someone thought to write down, and the
// names that matter most here are the ones that keep being invented.  Each of
// these matched no entry on the list, was ignored by the argument reader, and
// let the command run to completion -- a snapshot carrying an access key or an
// API token exited 0 and reported success.  The refusal must also never echo
// the value: a value in this position may be a secret.
for (const [name, cli, extra] of [
    ['the snapshot CLI', SNAPSHOT_CLI, []],
    ['the restore CLI', RESTORE_CLI, []],
]) {
    test(`${name} refuses a credential or remote flag it does not implement instead of ignoring it`, t => {
        const transportRoot = temporary(t, 'stage-d-cli-unknown-');
        const args = cli === SNAPSHOT_CLI
            ? ['--transport-root', transportRoot, ...extra]
            : ['--transport-root', transportRoot, '--snapshot-id', 'snap_20260913T000000000Z_0011223344556677', ...extra];

        for (const flag of [
            '--r2-access-key-id=AKIAIOSFODNN7EXAMPLE',
            '--r2-secret-access-key=SECRETVALUE',
            '--cloudflare-api-token=TOKENVALUE',
            '--storage-endpoint=https://example.invalid',
            '--region=auto',
        ]) {
            const result = runCli(cli, [...args, flag]);
            assert.equal(result.status, 1, `${flag} must not be accepted`);
            const payload = payloadOf(result);
            // Which of the two refusals catches it is not the property under
            // test -- `--region` is on the named list and the rest are not, and
            // both are correct.  The property is that it is refused rather than
            // ignored, that the refusal names the flag, and that the value never
            // appears: a value in this position may be a secret.
            assert.ok(
                /unknown flag is refused rather than ignored|live off-host target flags are rejected/.test(payload.error),
                `${flag}: ${payload.error}`
            );
            const reported = flag.slice(0, flag.indexOf('='));
            assert.ok(payload.error.includes(reported), `the refusal must name the flag: ${payload.error}`);
            const value = flag.slice(flag.indexOf('=') + 1);
            assert.equal(payload.error.includes(value), false, `the refusal must never echo the value: ${payload.error}`);
            assert.equal(result.stdout.includes(value), false, `the value must not reach stdout at all: ${result.stdout.slice(0, 200)}`);
            assert.equal(result.stderr.includes(value), false, `the value must not reach stderr at all`);
        }
    });
}

test('a bare positional argument is refused and never echoed', t => {
    const transportRoot = temporary(t, 'stage-d-cli-positional-');
    const result = runCli(SNAPSHOT_CLI, ['--transport-root', transportRoot, 'AKIAIOSFODNN7EXAMPLE']);
    assert.equal(result.status, 1);
    const payload = payloadOf(result);
    assert.ok(/unexpected positional argument/.test(payload.error), payload.error);
    assert.equal(result.stdout.includes('AKIAIOSFODNN7EXAMPLE'), false, 'a stray token may be a secret and must never be echoed');
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
    // The operator path refuses for the canonical verifier's reason, which is
    // the same reason `--verify-only` gives for this generation (the test above
    // asserts that code directly).  The restore used to discover the tamper
    // itself, with wording of its own; naming the verifier's code is what makes
    // the two entry points visibly agree rather than merely both fail.
    assert.ok(/ARTIFACT_HASH_MISMATCH: transactions\/STORE\.json content does not match the hash bound by the manifest/.test(payload.error), payload.error);
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

// The preload is a mechanism, and a mechanism that silently failed to install
// would make every child process in this file pass for the wrong reason -- they
// would look sealed while running wide open.  This drives the child-side seal
// directly: the probe asks the tripwire's own exported list for an entry point
// and calls it, so the test names no network verb itself.  It catches the
// refusal and clears its exit code on purpose, because that is exactly the case
// the exit check exists for: a child that swallows the throw must still fail.
test('a spawned child process is sealed by the tripwire preload', () => {
    const probe = [
        `const { SEALED_ENTRY_POINTS } = require(${JSON.stringify(TRIPWIRE_PRELOAD)});`,
        'const entry = SEALED_ENTRY_POINTS[0];',
        'try {',
        '    entry.target[entry.methods[0]]("127.0.0.1");',
        '} catch (error) {',
        '    console.error(`PROBE_REFUSED:${error.name}`);',
        '    process.exitCode = 0;',
        '}',
    ].join('\n');
    const result = spawnSync(process.execPath, ['-e', probe], {
        encoding: 'utf8',
        env: { PATH: process.env.PATH || '', [PRELOAD_ENV]: '1', NODE_OPTIONS: `--require ${TRIPWIRE_PRELOAD}` },
    });
    assert.equal(result.status, 1, 'a sealed child must exit non-zero even when it swallows the refusal');
    assert.ok(/NETWORK_TRIPWIRE_TRIPPED/.test(result.stderr), `the child must report the tripwire (stderr: ${result.stderr})`);
    assert.deepEqual(tripwire.attempts, [], 'the attempt happened in the child, so this process must have recorded none');
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

// ---------------------------------------------------------------------------
// The live entrypoints.
//
// A separate CLI, not a flag on the offline one.  The offline CLI's inability
// to address a remote target is a property that was proven, reviewed and merged;
// teaching it an endpoint flag would destroy it, so the live path is a new file
// and the offline files are unchanged.  These tests cover the live CLI's
// refusals and its offline preflight mode, which is the only mode any test may
// exercise: the sending path is proven at the library level against a stub SDK.
// ---------------------------------------------------------------------------

const LIVE_BACKUP_CLI = path.join(REPOSITORY_ROOT, 'scripts', 'ops', 'stage_d_r2_backup_live.js');
const LIVE_RESTORE_CLI = path.join(REPOSITORY_ROOT, 'scripts', 'ops', 'stage_d_r2_restore_live.js');

const LIVE_ACCESS_KEY_ID = 'synthetic-live-access-key-id-DO-NOT-USE';
const LIVE_SECRET_ACCESS_KEY = 'synthetic-live-secret-access-key-DO-NOT-USE';
const LIVE_SESSION_TOKEN = 'synthetic-live-session-token-DO-NOT-USE';
const LIVE_SECRETS = [LIVE_ACCESS_KEY_ID, LIVE_SECRET_ACCESS_KEY, LIVE_SESSION_TOKEN];

function liveIdentity(overrides = {}) {
    return {
        schema_version: 'stage-d-live-target-identity/v1',
        provider: 'cloudflare-r2',
        endpoint: 'https://0123456789abcdef0123456789abcdef.r2.cloudflarestorage.com',
        bucket: 'footballprediction-stage-d-backup-test',
        region: 'auto',
        prefix: 'footballprediction/stage-d/transaction-v1/snapshots',
        environment: 'test',
        project: 'footballprediction',
        purpose: 'stage-d-transaction-backup',
        ...overrides,
    };
}

function writeLiveConfig(t, { identity = {}, credentials = {}, credentialMode = 0o600 } = {}) {
    const dir = temporary(t, 'stage-d-cli-live-config-');
    const identityFile = path.join(dir, 'target-identity.json');
    fs.writeFileSync(identityFile, JSON.stringify(liveIdentity(identity), null, 2), { mode: 0o600 });
    const credentialFile = path.join(dir, 'credentials.json');
    fs.writeFileSync(credentialFile, JSON.stringify({
        accessKeyId: LIVE_ACCESS_KEY_ID,
        secretAccessKey: LIVE_SECRET_ACCESS_KEY,
        ...credentials,
    }), { mode: credentialMode });
    // Explicit: the creation mode is masked by the umask, and the mode is what
    // the loader checks.
    fs.chmodSync(credentialFile, credentialMode);
    return { identityFile, credentialFile };
}

function assertNoLiveSecretLeaked(result, label) {
    for (const secret of LIVE_SECRETS) {
        assert.equal(result.stdout.includes(secret), false, `${label}: a credential value must not reach stdout`);
        assert.equal(result.stderr.includes(secret), false, `${label}: a credential value must not reach stderr`);
    }
}

test('the live CLIs are not reachable from the offline CLIs, and the offline CLIs are unchanged', t => {
    const transportRoot = temporary(t, 'stage-d-cli-offline-unchanged-');

    // Every flag the live path introduces is refused by the offline path.  It
    // refuses them because its allowlist admits only what it implements, which
    // is what keeps "the offline CLI cannot address a remote target" true
    // without a second denylist to maintain.
    for (const scriptPath of [SNAPSHOT_CLI, RESTORE_CLI]) {
        for (const flag of ['--target-identity-file', '--credential-file', '--preflight-only', '--access-key', '--secret-key', '--aws-access-key-id', '--aws-session-token', '--endpoint-url', '--prefix', '--token', '--api-token']) {
            const result = runCli(scriptPath, [flag, 'synthetic-value-DO-NOT-USE', '--transport-root', transportRoot]);
            assert.notEqual(result.status, 0, `${path.basename(scriptPath)} must refuse ${flag}`);
            const payload = payloadOf(result);
            assert.ok(
                /unknown flag is refused rather than ignored|live off-host target flags are rejected/.test(payload.error),
                `${flag} must be refused by name: ${payload.error}`,
            );
            assert.equal(result.stdout.includes('synthetic-value-DO-NOT-USE'), false, `${flag} must not echo its value`);
        }
    }

    // The structural half: neither offline CLI gained a reference to the live
    // path.  A refusal test proves the flags are refused today; this proves the
    // code that would use them is not there at all.
    for (const scriptPath of [SNAPSHOT_CLI, RESTORE_CLI]) {
        const source = fs.readFileSync(scriptPath, 'utf8');
        assert.ok(/LIVE_R2_CLI_WIRING=NOT_IMPLEMENTED/.test(source), `${path.basename(scriptPath)} must still declare itself unwired`);
        for (const forbidden of ['loadLiveTargetIdentity', 'loadLiveCredentials', 'createR2Transport', 'loadR2Transport', '@aws-sdk']) {
            assert.equal(source.includes(forbidden), false, `${path.basename(scriptPath)} must not reference ${forbidden}`);
        }
    }
});

test('the live backup CLI preflights offline: no request, no secret, and the target is named', t => {
    const { identityFile, credentialFile } = writeLiveConfig(t, { credentials: { sessionToken: LIVE_SESSION_TOKEN } });
    const result = runCli(LIVE_BACKUP_CLI, ['--target-identity-file', identityFile, '--credential-file', credentialFile, '--preflight-only']);

    assert.equal(result.status, 0, `the preflight must succeed: ${result.stdout} ${result.stderr}`);
    assert.equal(/NETWORK_TRIPWIRE_TRIPPED/.test(result.stderr), false, 'the preflight is offline: it must make no request');
    const payload = payloadOf(result);
    assert.equal(payload.action, 'LIVE_PREFLIGHT_ONLY');
    assert.equal(payload.live_r2_cli_wiring, 'IMPLEMENTED');
    assert.equal(payload.preflight_class, 'OFFLINE_PREFLIGHT');
    assert.equal(payload.live_connectivity_preflight, 'NOT_PERFORMED', 'an offline preflight proves the wiring, not reachability');
    assert.equal(payload.network_calls_made, 0);
    assert.equal(payload.target.bucket, 'footballprediction-stage-d-backup-test');
    assert.equal(payload.target.prefix, 'footballprediction/stage-d/transaction-v1/snapshots');
    assert.equal(payload.target.create_only, true);
    assert.equal(payload.target.delete_exposed, false);
    assert.equal(payload.target.session_token_present, true, 'a temporary credential is reported as a class');
    assert.equal(payload.credentials.session_token_present, true);
    assert.equal(typeof payload.target.target_fingerprint, 'string');
    assert.equal(payload.live_connectivity_probe_key, 'preflight-probe/conditional-write/v1/PROBE.json');
    assertNoLiveSecretLeaked(result, 'the preflight report');
});

test('the live restore CLI preflights offline and declares that it has no local source', t => {
    const { identityFile, credentialFile } = writeLiveConfig(t);
    const result = runCli(LIVE_RESTORE_CLI, ['--target-identity-file', identityFile, '--credential-file', credentialFile, '--preflight-only']);

    assert.equal(result.status, 0, result.stdout);
    assert.equal(/NETWORK_TRIPWIRE_TRIPPED/.test(result.stderr), false);
    const payload = payloadOf(result);
    assert.equal(payload.action, 'LIVE_PREFLIGHT_ONLY');
    assert.equal(payload.network_calls_made, 0);
    assert.deepEqual(payload.local_source_roots, [], 'a restore from the target has no filesystem source');
    assert.equal(payload.target.kind, 'r2-s3');
    assertNoLiveSecretLeaked(result, 'the preflight report');
});

test('the live CLIs refuse a credential or a target on the command line, in both spellings', t => {
    const { identityFile, credentialFile } = writeLiveConfig(t);
    const secret = LIVE_SECRET_ACCESS_KEY;
    const flags = [
        ['--access-key-id', secret],
        ['--secret-access-key', secret],
        ['--session-token', secret],
        ['--access-key', secret],
        ['--secret-key', secret],
        ['--credentials', secret],
        ['--profile', 'default'],
        ['--aws-access-key-id', secret],
        ['--aws-secret-access-key', secret],
        ['--aws-session-token', secret],
        ['--aws-profile', 'default'],
        ['--endpoint', 'https://example.invalid'],
        ['--endpoint-url', 'https://example.invalid'],
        ['--bucket', 'stage-d-backup'],
        ['--region', 'auto'],
        ['--prefix', 'somewhere'],
    ];

    for (const cli of [LIVE_BACKUP_CLI, LIVE_RESTORE_CLI]) {
        const name = path.basename(cli);
        for (const [flag, value] of flags) {
            for (const args of [[flag, value], [`${flag}=${value}`]]) {
                const result = runCli(cli, [...args, '--target-identity-file', identityFile, '--credential-file', credentialFile, '--preflight-only']);
                assert.equal(result.status, 1, `${name} ${args[0]} must be refused rather than ignored`);
                const payload = payloadOf(result);
                assert.equal(payload.action, 'LIVE_BACKUP_FAILED'.replace('BACKUP', cli === LIVE_BACKUP_CLI ? 'BACKUP' : 'RESTORE_VERIFY'), payload.error);
                assert.ok(/come from explicit files/.test(payload.error), `${name} ${args[0]}: ${payload.error}`);
                assert.ok(payload.error.includes(flag), `the refusal must name the flag: ${payload.error}`);
                assert.equal(result.stdout.includes(value), false, `${name} ${args[0]} must never echo the value`);
                assert.equal(result.stderr.includes(value), false);
            }
        }
    }
});

test('the live CLIs refuse a repeated single-valued flag instead of silently choosing one', t => {
    const { identityFile, credentialFile } = writeLiveConfig(t);
    // The failure this refuses is not a typo: `valueAfter` reads the first
    // occurrence, so `--target-identity-file A --target-identity-file B` would
    // aim a non-preflight run at A while the operator believed it had said B.
    // Each CLI has its own flag set, so the table is per CLI: repeating a flag
    // the CLI does not implement would be refused as unknown, which is a
    // different refusal and must not be mistaken for this one.
    const shared = [
        ['--target-identity-file', identityFile, identityFile],
        ['--credential-file', credentialFile, credentialFile],
        ['--snapshot-id', 'snap_20260914T000000000Z_0123456789abcdef', 'snap_20260914T000000000Z_fedcba9876543210'],
    ];
    const perCli = new Map([
        [LIVE_BACKUP_CLI, [
            ...shared,
            ['--authority-root', '/tmp/a', '/tmp/b'],
            ['--allocation-artifact', '/tmp/a.json', '/tmp/b.json'],
            ['--ledger-root', '/tmp/a', '/tmp/b'],
            ['--quota-config', '/tmp/a.json', '/tmp/b.json'],
            ['--now', '2026-09-14T00:00:00.000Z', '2026-09-15T00:00:00.000Z'],
        ]],
        [LIVE_RESTORE_CLI, [
            ...shared,
            ['--destination-root', '/tmp/a', '/tmp/b'],
        ]],
    ]);

    for (const cli of [LIVE_BACKUP_CLI, LIVE_RESTORE_CLI]) {
        const name = path.basename(cli);
        for (const [flag, first, second] of perCli.get(cli)) {
            const result = runCli(cli, [
                '--target-identity-file', identityFile,
                '--credential-file', credentialFile,
                flag, first,
                flag, second,
                '--preflight-only',
            ]);
            assert.equal(result.status, 1, `${name} ${flag} twice must be refused`);
            const payload = payloadOf(result);
            assert.ok(
                /was given more than once/.test(payload.error),
                `${name} ${flag} twice: ${payload.error}`,
            );
            assert.ok(
                payload.error.includes(flag),
                `the refusal must name the flag rather than resolve it: ${payload.error}`,
            );
            // The refusal must not print either candidate, because the second
            // one is exactly the value the operator believed they had set.
            assert.equal(result.stdout.includes(second), false, `${name} ${flag}: the second value must not be echoed`);
            assert.equal(result.stderr.includes(second), false);
            assertNoLiveSecretLeaked(result, `${name} ${flag} twice`);
        }
    }
});

test('the backup CLI still accepts a repeated --run-state, so the refusal is per-flag', t => {
    const { identityFile, credentialFile } = writeLiveConfig(t);
    // `--run-state` is the one flag that is meaningful more than once: a
    // snapshot carries a list of run-state inputs.  A duplicate-flag refusal
    // that did not exempt it would be a regression in the other direction.
    const result = runCli(LIVE_BACKUP_CLI, [
        '--target-identity-file', identityFile,
        '--credential-file', credentialFile,
        '--run-state', 'first',
        '--run-state', 'second',
        '--preflight-only',
    ]);
    const payload = payloadOf(result);
    assert.notEqual(
        /was given more than once/.test(payload.error || ''),
        true,
        `--run-state must stay repeatable: ${payload.error}`,
    );
    // The preflight does not read run state, so a repeated --run-state is
    // accepted and the preflight still succeeds without a request.
    assert.equal(result.status, 0, `the preflight must still pass: ${JSON.stringify(payload)}`);
    assert.equal(payload.preflight_class, 'OFFLINE_PREFLIGHT');
    assert.equal(payload.network_calls_made, 0);
});

test('the live CLIs refuse an unknown flag rather than ignoring it', t => {
    const { identityFile, credentialFile } = writeLiveConfig(t);
    for (const cli of [LIVE_BACKUP_CLI, LIVE_RESTORE_CLI]) {
        for (const flag of ['--target-endpoint', '--r2-access-key-id=synthetic-value-DO-NOT-USE', '--storage-endpoint=https://example.invalid']) {
            const result = runCli(cli, [flag, '--target-identity-file', identityFile, '--credential-file', credentialFile, '--preflight-only']);
            assert.equal(result.status, 1, `${flag} must not be accepted`);
            const payload = payloadOf(result);
            assert.ok(/unknown flag is refused rather than ignored|come from explicit files/.test(payload.error), payload.error);
            assert.ok(payload.error.includes(flag.slice(0, flag.indexOf('=') === -1 ? flag.length : flag.indexOf('='))), `the refusal must name the flag: ${payload.error}`);
            assert.equal(result.stdout.includes('synthetic-value-DO-NOT-USE'), false);
        }
    }
});

test('the live CLIs fail closed when a file is missing, loose or invalid', t => {
    const { identityFile, credentialFile } = writeLiveConfig(t);
    const missing = path.join(temporary(t, 'stage-d-cli-live-missing-'), 'absent.json');

    for (const cli of [LIVE_BACKUP_CLI, LIVE_RESTORE_CLI]) {
        const name = path.basename(cli);
        const cases = [
            { args: ['--target-identity-file', missing, '--credential-file', credentialFile], match: /identity file could not be opened/ },
            { args: ['--target-identity-file', identityFile, '--credential-file', missing], match: /credential file could not be opened/ },
            { args: ['--credential-file', credentialFile], match: /--target-identity-file is required/ },
            { args: ['--target-identity-file', identityFile], match: /--credential-file is required/ },
        ];
        for (const { args, match } of cases) {
            const result = runCli(cli, [...args, '--preflight-only']);
            assert.equal(result.status, 1, `${name} ${args[0]} must fail closed`);
            const payload = payloadOf(result);
            assert.ok(match.test(payload.error), `${name} ${args.join(' ')}: ${payload.error}`);
        }
    }

    // A credential file anyone but its owner can read is refused, and the file
    // is not used even though its contents are perfectly well formed.
    const loose = writeLiveConfig(t, { credentialMode: 0o644 });
    const result = runCli(LIVE_BACKUP_CLI, ['--target-identity-file', loose.identityFile, '--credential-file', loose.credentialFile, '--preflight-only']);
    assert.equal(result.status, 1);
    assert.ok(/group or other/.test(payloadOf(result).error));
    assertNoLiveSecretLeaked(result, 'a refused loose credential');

    // A target identity with a credential-shaped field is refused before any
    // transport exists.
    const withSecret = writeLiveConfig(t, { identity: { prefix: `snapshots/${'a'.repeat(64)}` } });
    const secretive = runCli(LIVE_BACKUP_CLI, ['--target-identity-file', withSecret.identityFile, '--credential-file', withSecret.credentialFile, '--preflight-only']);
    assert.equal(secretive.status, 1);
    assert.ok(/shaped like a secret/.test(payloadOf(secretive).error));
});

test('a live CLI never runs its sending path without the roots a backup needs', t => {
    const { identityFile, credentialFile } = writeLiveConfig(t);
    // Without `--preflight-only` the CLI needs the authority roots, and it says
    // so rather than defaulting to one.  Nothing is sent: the argument check
    // happens before the transport is built.
    const result = runCli(LIVE_BACKUP_CLI, ['--target-identity-file', identityFile, '--credential-file', credentialFile]);
    assert.equal(result.status, 1);
    const payload = payloadOf(result);
    assert.ok(/--authority-root is required/.test(payload.error), payload.error);
    assert.equal(/NETWORK_TRIPWIRE_TRIPPED/.test(result.stderr), false);
});

test('the live restore CLI refuses a credential file inside the repository', t => {
    const inside = path.join(REPOSITORY_ROOT, 'credentials.json');
    assert.equal(fs.existsSync(inside), false, 'this test must not create a credential file in the tree');
    const { identityFile } = writeLiveConfig(t);
    const result = runCli(LIVE_RESTORE_CLI, ['--target-identity-file', identityFile, '--credential-file', inside, '--preflight-only']);
    assert.equal(result.status, 1);
    assert.ok(/must not live inside the repository/.test(payloadOf(result).error));
});
