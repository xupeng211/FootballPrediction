'use strict';

// Safety tests for the properties that make this tooling safe to have in the
// repository at all: it has no production default, it discovers no credential,
// it signs nothing itself, it cannot delete, and its CLIs cannot be pointed at
// a live target by accident or by a mistyped argument.
//
// Most of these read the sources rather than call them, because the property is
// "this code does not exist here".  A behavioural test can only show that the
// paths it exercises are safe; a source sweep shows that the dangerous paths
// were never written.

const assert = require('node:assert/strict');
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const test = require('node:test');
const { spawnSync } = require('node:child_process');

const { buildBackupFixture } = require('../../../helpers/backup_authority_fixture');
const { installNetworkTripwire } = require('../../../helpers/network_tripwire');

// Sealed for the whole file.  The per-test seals below stay where they assert
// something immediately after an operation; this one is what makes every other
// test in the file covered too.
//
// The tripwire self-test deliberately trips every entry point and then empties
// the module-level recorder, so this file-level check runs against a recorder
// the self-test has already put back the way it found it.
const tripwire = installNetworkTripwire();
test.after(() => {
    assert.deepEqual(tripwire.attempts, [], 'no test in this file may attempt outbound network access');
    tripwire.restore();
});
const backup = require('../../../../src/infrastructure/market_evidence/backup');
const { createLocalTransport, isGovernedProductionPath, PRODUCTION_MARKERS } = require('../../../../src/infrastructure/market_evidence/backup/localTransport');
const { FORBIDDEN_TRANSPORT_METHODS, SnapshotIntegrityError, TransportContractError, assertTransportContract } = require('../../../../src/infrastructure/market_evidence/backup/transport');
const { executeRestore } = require('../../../../src/infrastructure/market_evidence/backup/restoreExecutor');

const REPOSITORY_ROOT = path.resolve(__dirname, '..', '..', '..', '..');
const BACKUP_SOURCE_DIRECTORY = path.join(REPOSITORY_ROOT, 'src', 'infrastructure', 'market_evidence', 'backup');
const CLI_PATHS = Object.freeze([
    path.join(REPOSITORY_ROOT, 'scripts', 'ops', 'stage_d_backup_snapshot.js'),
    path.join(REPOSITORY_ROOT, 'scripts', 'ops', 'stage_d_restore_verify.js'),
]);

const PRODUCTION_AREA = path.join(REPOSITORY_ROOT, 'data', 'market_evidence', 'live');

let shared = null;
function fixture() {
    if (shared === null) shared = buildBackupFixture({ transactionCount: 1, includeLedgerEntries: 1 });
    return shared;
}
test.after(() => { if (shared) shared.cleanup(); });

// The sweeps below ask "does this code do X", not "does this file mention X".
// The header comments deliberately name the things the module refuses to do, so
// comments are stripped before a forbidden pattern is searched for; leaving
// them in would make the suite fail on its own documentation.
function stripComments(text) {
    return text.replace(/\/\*[\s\S]*?\*\//g, '').split('\n').filter(line => !line.trim().startsWith('//')).join('\n');
}

function readSource(absolutePath) {
    const text = fs.readFileSync(absolutePath, 'utf8');
    return { text, code: stripComments(text) };
}

function sourceFiles() {
    return fs.readdirSync(BACKUP_SOURCE_DIRECTORY).filter(name => name.endsWith('.js')).sort().map(name => ({
        name,
        ...readSource(path.join(BACKUP_SOURCE_DIRECTORY, name)),
    }));
}

const PRODUCTION_AREA_MENTION = /path\.join\(\s*'data'\s*,\s*'market_evidence'\s*,\s*'live'\s*\)|['"`]data\/market_evidence\/live['"`]/;

function runCli(scriptPath, args, options = {}) {
    const result = spawnSync(process.execPath, [scriptPath, ...args], {
        cwd: REPOSITORY_ROOT,
        encoding: 'utf8',
        env: { PATH: process.env.PATH || '' },
        ...options,
    });
    return { status: result.status, stdout: result.stdout || '', stderr: result.stderr || '' };
}

function parseJsonLine(text) {
    const line = text.trim().split('\n').filter(Boolean).pop();
    assert.ok(line, `expected a JSON line, received: ${JSON.stringify(text)}`);
    return JSON.parse(line);
}

test('no backup source file names a production path except the denylist that refuses it', () => {
    const mentioning = sourceFiles().filter(file => PRODUCTION_AREA_MENTION.test(file.code));
    assert.deepEqual(mentioning.map(file => file.name), ['localTransport.js'], 'the production area may only be named by the module whose job is to refuse it');

    const occurrences = mentioning[0].code.split('\n').filter(line => PRODUCTION_AREA_MENTION.test(line));
    assert.equal(occurrences.length, 1, `the production area is named exactly once in executable code, found: ${occurrences.map(line => line.trim()).join(' | ')}`);

    const denylist = /const PRODUCTION_MARKERS = Object\.freeze\(\[([\s\S]*?)\]\)/.exec(mentioning[0].code);
    assert.ok(denylist, 'PRODUCTION_MARKERS must be a frozen array literal so its contents can be read here');
    assert.equal(denylist[1].split('\n').filter(line => PRODUCTION_AREA_MENTION.test(line)).length, 1, 'the only mention must be inside the denylist, never a fallback default');
    assert.deepEqual(PRODUCTION_MARKERS, [path.join('data', 'market_evidence', 'live')]);
});

test('no ops CLI names a production path, an endpoint, a bucket or a credential', () => {
    for (const cliPath of CLI_PATHS) {
        const text = fs.readFileSync(cliPath, 'utf8');
        assert.equal(text.includes(path.join('data', 'market_evidence', 'live')), false, `${path.basename(cliPath)} must not name the production area`);
        assert.equal(/require\(['"][^'"]*r2Transport/.test(text), false, `${path.basename(cliPath)} must not import the R2 transport`);
        assert.equal(text.includes('@aws-sdk'), false, `${path.basename(cliPath)} must not import the AWS SDK`);
        for (const capability of ['createR2Transport', 'S3Client', 'PutObjectCommand']) {
            assert.equal(text.includes(capability), false, `${path.basename(cliPath)} must not reach ${capability}`);
        }
    }
});

test('the governed production area is recognised and refused', async t => {
    assert.equal(isGovernedProductionPath(PRODUCTION_AREA), true);
    assert.equal(isGovernedProductionPath(path.join(PRODUCTION_AREA, 'transactions')), true);
    assert.equal(isGovernedProductionPath(path.join('/', 'data', 'market_evidence', 'live')), true);
    for (const unrelated of ['live-2', 'live_backup', 'livex']) {
        assert.equal(isGovernedProductionPath(path.join(REPOSITORY_ROOT, 'data', 'market_evidence', unrelated)), false, `${unrelated} is not the governed area and must not be condemned by a substring match`);
    }
    assert.equal(isGovernedProductionPath(path.join(REPOSITORY_ROOT, 'tmp', 'copy')), false);

    assert.throws(
        () => createLocalTransport({ root: path.join(PRODUCTION_AREA, 'staging') }),
        error => error instanceof SnapshotIntegrityError && /governed production area/.test(error.message)
    );

    const root = fs.mkdtempSync(path.join(os.tmpdir(), 'stage-d-nodefault-'));
    t.after(() => fs.rmSync(root, { recursive: true, force: true }));
    const transport = createLocalTransport({ root });
    const report = await backup.writeSnapshot({
        transport,
        authorityRoot: fixture().authorityRoot,
        allocationArtifactPath: fixture().allocationArtifactPath,
        ledgerRoot: fixture().ledgerRoot,
        quotaConfigPath: fixture().quotaConfigPath,
    });
    await assert.rejects(
        executeRestore({ transport, snapshotId: report.snapshot_id, destinationRoot: path.join(PRODUCTION_AREA, 'restored') }),
        error => error instanceof SnapshotIntegrityError && /governed production area/.test(error.message)
    );
});

test('every entry point that needs a root refuses to invent one', async t => {
    const fx = fixture();
    const complete = {
        authorityRoot: fx.authorityRoot,
        allocationArtifactPath: fx.allocationArtifactPath,
        ledgerRoot: fx.ledgerRoot,
        quotaConfigPath: fx.quotaConfigPath,
    };
    assert.equal(backup.enumerateSnapshotInputs(complete).entries.length > 0, true, 'the complete call is the control: everything else differs from it in exactly one argument');

    for (const field of ['authorityRoot', 'allocationArtifactPath', 'ledgerRoot', 'quotaConfigPath']) {
        for (const bad of [undefined, null, '', '   ']) {
            assert.throws(
                () => backup.enumerateSnapshotInputs({ ...complete, [field]: bad }),
                error => error instanceof SnapshotIntegrityError && /no default and no production fallback/.test(error.message),
                `${field}=${JSON.stringify(bad)} must be refused`
            );
        }
    }

    const root = fs.mkdtempSync(path.join(os.tmpdir(), 'stage-d-nodefault-roots-'));
    t.after(() => fs.rmSync(root, { recursive: true, force: true }));
    const transport = createLocalTransport({ root });
    await assert.rejects(backup.writeSnapshot({ transport, ...complete, authorityRoot: undefined }), error => error instanceof SnapshotIntegrityError && /no default and no production fallback/.test(error.message));
    await assert.rejects(backup.writeSnapshot({ transport, ...complete, quotaConfigPath: '' }), error => error instanceof SnapshotIntegrityError && /no default and no production fallback/.test(error.message));
    await assert.rejects(backup.writeSnapshot({ transport, ...complete, ledgerRoot: null }), error => error instanceof SnapshotIntegrityError && /no default and no production fallback/.test(error.message));
});

test('the transport contract refuses every deletion and administration verb', () => {
    const base = () => ({ putObjectCreateOnly: () => {}, getObject: () => null, headObject: () => null, listObjects: () => [], describe: () => ({ create_only: true, delete_exposed: false }) });
    assert.equal(assertTransportContract(base()).describe().create_only, true);
    for (const verb of FORBIDDEN_TRANSPORT_METHODS) {
        const tainted = { ...base(), [verb]: () => {} };
        assert.throws(() => assertTransportContract(tainted), error => error instanceof TransportContractError && new RegExp(`forbidden capability: ${verb}`).test(error.message), `${verb} must be refused`);
    }
    for (const missing of ['putObjectCreateOnly', 'getObject', 'headObject', 'listObjects', 'describe']) {
        const incomplete = base();
        delete incomplete[missing];
        assert.throws(() => assertTransportContract(incomplete), error => error instanceof TransportContractError && /missing required capability/.test(error.message));
    }
});

test('no transport exposes a delete or an administration verb', () => {
    const built = createLocalTransport({ root: os.tmpdir() });
    for (const verb of FORBIDDEN_TRANSPORT_METHODS) assert.equal(typeof built[verb], 'undefined', `local transport must not expose ${verb}`);
    assert.deepEqual(Object.keys(built).sort(), ['describe', 'getObject', 'headObject', 'listObjects', 'putObjectCreateOnly']);
    assert.equal(built.describe().delete_exposed, false);
    assert.equal(built.describe().create_only, true);
});

test('no signature logic is written in this repository', () => {
    const forbidden = [/AWS4-HMAC-SHA256/, /X-Amz-/, /StringToSign/, /signingKey/i, /credentialScope/i, /createHmac/, /getSignature/i, /deriveSigningKey/i, /hmac/i];
    for (const file of sourceFiles()) {
        for (const pattern of forbidden) {
            assert.equal(pattern.test(file.code), false, `${file.name} must not implement signing (${pattern}): SigV4 is the provider SDK's job`);
        }
    }
    for (const cliPath of CLI_PATHS) {
        const { code } = readSource(cliPath);
        for (const pattern of forbidden) assert.equal(pattern.test(code), false, `${path.basename(cliPath)} must not implement signing (${pattern})`);
    }
});

test('the R2 transport discovers no credential from the environment', () => {
    const { text, code } = readSource(path.join(BACKUP_SOURCE_DIRECTORY, 'r2Transport.js'));
    for (const pattern of [/fromEnv/i, /fromIni/i, /fromNodeProviderChain/i, /defaultProvider/i, /credentialProvider/i, /AWS_PROFILE/, /AWS_ACCESS_KEY_ID/, /AWS_SECRET/, /\.aws\//, /instance.?metadata/i, /process\.env/]) {
        assert.equal(pattern.test(code), false, `the R2 transport must not contain ${pattern}`);
    }
    assert.ok(/INJECTED_EXPLICIT/.test(code), 'the transport must state where credentials come from');
    assert.ok(/environment_fallback: false/.test(code), 'the transport must declare that there is no environment fallback');
    assert.ok(/assertExplicitCredentials/.test(code), 'the transport must require injected credentials');
    assert.ok(/IfNoneMatch: '\*'/.test(text), 'create-only must be the server-side condition, not a read-then-write');
});

test('the credential refusal is documented rather than merely absent', () => {
    const { text } = readSource(path.join(BACKUP_SOURCE_DIRECTORY, 'r2Transport.js'));
    for (const phrase of ['no environment fallback', 'no ~/.aws', 'no default provider chain']) {
        assert.ok(text.includes(phrase), `the transport must state "${phrase}" where a reader will find it`);
    }
});

test('the R2 transport refuses to construct without injected credentials, even when the environment offers some', () => {
    const { createR2Transport } = backup.loadR2Transport();
    const ambient = { AWS_ACCESS_KEY_ID: 'AKIAAMBIENT', AWS_SECRET_ACCESS_KEY: 'ambient-secret', AWS_PROFILE: 'default' };
    const saved = {};
    for (const [name, value] of Object.entries(ambient)) {
        saved[name] = process.env[name];
        process.env[name] = value;
    }
    try {
        assert.throws(() => createR2Transport({ endpoint: 'https://example.invalid', bucket: 'b', region: 'auto' }), error => error instanceof TransportContractError && /injected explicitly/.test(error.message));
        assert.throws(() => createR2Transport({ endpoint: 'https://example.invalid', bucket: 'b', region: 'auto', credentials: {} }), error => error instanceof TransportContractError && /accessKeyId/.test(error.message));
        assert.throws(
            () => createR2Transport({ endpoint: 'https://example.invalid', bucket: 'b', region: 'auto', credentials: { accessKeyId: 'k', secretAccessKey: 's', sessionToken: '' } }),
            error => error instanceof TransportContractError && /sessionToken/.test(error.message)
        );
        for (const [field, bad] of [['endpoint', ''], ['bucket', '  '], ['region', undefined]]) {
            assert.throws(
                () => createR2Transport({ endpoint: 'https://example.invalid', bucket: 'b', region: 'auto', credentials: { accessKeyId: 'k', secretAccessKey: 's' }, [field]: bad }),
                error => error instanceof TransportContractError && new RegExp(field).test(error.message)
            );
        }
        // The injected-client seam is a seam for the command mechanics, not a
        // way around the credential rule.  If supplying a client were enough to
        // construct, a caller could hand in one backed by the SDK's default
        // provider chain and the refusal above would be conditional rather than
        // a guarantee.
        const stubClient = { send: () => Promise.resolve({}) };
        assert.throws(
            () => createR2Transport({ endpoint: 'https://example.invalid', bucket: 'b', region: 'auto', client: stubClient }),
            error => error instanceof TransportContractError && /injected explicitly/.test(error.message)
        );
        assert.throws(
            () => createR2Transport({ endpoint: 'https://example.invalid', bucket: 'b', region: 'auto', credentials: {}, client: stubClient }),
            error => error instanceof TransportContractError && /accessKeyId/.test(error.message)
        );
    } finally {
        for (const [name, value] of Object.entries(saved)) {
            if (value === undefined) delete process.env[name];
            else process.env[name] = value;
        }
    }
});

test('the R2 transport reports only provider identifiers, never client configuration', () => {
    const { createR2Transport } = backup.loadR2Transport();
    const secret = 'SUPERSECRETACCESSKEYMATERIAL';
    const sent = [];
    const client = {
        send(command) {
            sent.push(command.input);
            const error = new Error(`failed with ${secret}`);
            error.name = 'AccessDenied';
            error.$metadata = { httpStatusCode: 403 };
            return Promise.reject(error);
        },
    };
    const transport = createR2Transport({
        endpoint: 'https://example.invalid',
        bucket: 'bucket',
        region: 'auto',
        credentials: { accessKeyId: 'AKIASTUB', secretAccessKey: 'stub-secret' },
        client,
    });
    return transport.putObjectCreateOnly({ key: 'a/b.json', bytes: Buffer.from('{}') }).then(
        () => assert.fail('the write should have failed'),
        error => {
            assert.equal(error.name, 'SnapshotIntegrityError');
            assert.equal(error.message, 'putObjectCreateOnly failed: AccessDenied status=403');
            assert.equal(error.message.includes(secret), false, 'a provider message must not be able to carry a secret into a report');
            assert.equal(sent[0].IfNoneMatch, '*', 'create-only must be a server-side condition, never a HEAD-then-PUT');
        }
    );
});

test('the R2 transport describe() carries no credential material', () => {
    const { createR2Transport } = backup.loadR2Transport();
    const accessKeyId = 'AKIAEXPLICITINJECTED';
    const secretAccessKey = 'explicit-injected-secret';
    const transport = createR2Transport({
        endpoint: 'https://example.invalid',
        bucket: 'stage-d-backup',
        region: 'auto',
        prefix: '/snapshots/',
        credentials: { accessKeyId, secretAccessKey },
    });
    const described = transport.describe();
    assert.equal(described.credentials_injected, true);
    assert.equal(described.credential_source, 'INJECTED_EXPLICIT');
    assert.equal(described.environment_fallback, false);
    assert.equal(described.delete_exposed, false);
    assert.equal(described.create_only, true);
    assert.equal(described.prefix, 'snapshots');
    const serialized = JSON.stringify(described);
    assert.equal(serialized.includes(accessKeyId), false);
    assert.equal(serialized.includes(secretAccessKey), false);
});

test('the barrel does not link the network client until a caller asks for it', () => {
    const awsBefore = Object.keys(require.cache).filter(id => id.includes('@aws-sdk'));
    const api = require('../../../../src/infrastructure/market_evidence/backup');
    assert.equal(typeof api.loadR2Transport, 'function');
    assert.equal(typeof api.createLocalTransport, 'function');
    assert.equal(typeof api.writeSnapshot, 'function');
    assert.equal(typeof api.verifySnapshot, 'function');
    assert.equal(api.createR2Transport, undefined, 'the R2 transport is not part of the eager surface');
    assert.deepEqual(Object.keys(require.cache).filter(id => id.includes('@aws-sdk')), awsBefore, 'importing the barrel must not link the AWS SDK');
});

test('the library performs no outbound network access across a whole write, verify and restore', async t => {
    const tripwire = installNetworkTripwire();
    t.after(() => tripwire.restore());
    const root = fs.mkdtempSync(path.join(os.tmpdir(), 'stage-d-nodefault-full-'));
    const destinationRoot = fs.mkdtempSync(path.join(os.tmpdir(), 'stage-d-nodefault-dest-'));
    t.after(() => { fs.rmSync(root, { recursive: true, force: true }); fs.rmSync(destinationRoot, { recursive: true, force: true }); });

    const transport = createLocalTransport({ root });
    const report = await backup.writeSnapshot({
        transport,
        authorityRoot: fixture().authorityRoot,
        allocationArtifactPath: fixture().allocationArtifactPath,
        ledgerRoot: fixture().ledgerRoot,
        quotaConfigPath: fixture().quotaConfigPath,
    });
    assert.equal((await backup.verifySnapshot({ transport, snapshotId: report.snapshot_id })).result, 'PASS');
    const restored = await executeRestore({
        transport,
        snapshotId: report.snapshot_id,
        destinationRoot: path.join(destinationRoot, 'restored'),
    });
    assert.equal(restored.result, 'PASS');
    assert.deepEqual(tripwire.attempts, []);
});

test('the tripwire actually seals every entry point it advertises', t => {
    const { SEALED_ENTRY_POINTS } = require('../../../helpers/network_tripwire');
    const originals = SEALED_ENTRY_POINTS.map(entry => ({
        entry,
        methods: entry.methods.map(method => entry.target[method]),
    }));
    const sealedCount = originals.reduce((total, o) => total + o.methods.length, 0);

    const tripwire = installNetworkTripwire();
    t.after(() => tripwire.restore());

    // A tripwire that is never exercised is an assumption, not a proof: the
    // offline claim rests on this helper, so every entry point it advertises is
    // driven here and must refuse.
    for (const { entry } of originals) {
        for (const method of entry.methods) {
            assert.throws(
                () => entry.target[method]('127.0.0.1'),
                { name: 'NetworkAccessError', code: 'NETWORK_ACCESS_FORBIDDEN_IN_TEST' },
                `${entry.label}.${method} must refuse`,
            );
        }
    }
    assert.equal(tripwire.attempts.length, sealedCount, 'every refused attempt is recorded');

    tripwire.restore();
    for (const { entry, methods } of originals) {
        entry.methods.forEach((method, index) => {
            assert.equal(entry.target[method], methods[index], `${entry.label}.${method} is restored`);
        });
    }
    assert.equal(tripwire.attempts.length, sealedCount, 'restore does not erase what was recorded');

    // The recorder is module-level and shared with the other tests in this file,
    // so leave it exactly as it was found.
    tripwire.attempts.length = 0;
});

test('the snapshot CLI refuses to run without every root', () => {
    const [cliPath] = CLI_PATHS;
    const result = runCli(cliPath, []);
    assert.equal(result.status, 1);
    const payload = parseJsonLine(result.stdout);
    assert.equal(payload.action, 'SNAPSHOT_FAILED');
    assert.ok(/--transport-root is required/.test(payload.error));
    assert.ok(/no production default/.test(payload.error));

    const partial = runCli(cliPath, ['--transport-root', os.tmpdir()]);
    assert.equal(partial.status, 1);
    assert.ok(/--authority-root is required/.test(parseJsonLine(partial.stdout).error));
});

test('the snapshot CLI refuses every live target flag, and echoes no credential value', () => {
    const [cliPath] = CLI_PATHS;
    for (const flag of ['--endpoint', '--bucket', '--region', '--access-key-id', '--secret-access-key', '--session-token', '--profile', '--r2', '--s3', '--live', '--remote']) {
        const result = runCli(cliPath, ['--transport-root', os.tmpdir(), flag, 'value']);
        assert.equal(result.status, 1, `${flag} must be rejected`);
        const payload = parseJsonLine(result.stdout);
        assert.equal(payload.action, 'SNAPSHOT_FAILED');
        assert.ok(/LIVE_R2_CLI_WIRING=NOT_IMPLEMENTED/.test(payload.error), `${flag} must be refused as unwired, received: ${payload.error}`);
        assert.equal(payload.error.includes('value'), false, 'the rejected value must never be echoed back');
    }

    const secret = 'SUPERSECRETMATERIAL123';
    const leaked = runCli(cliPath, ['--secret-access-key', secret, '--transport-root', os.tmpdir()]);
    assert.equal(leaked.status, 1);
    assert.equal(leaked.stdout.includes(secret), false, 'a credential passed on the command line must never appear in output');
    assert.equal(leaked.stderr.includes(secret), false);
});

test('the snapshot CLI writes a generation end to end with every root explicit', async t => {
    const [cliPath] = CLI_PATHS;
    const root = fs.mkdtempSync(path.join(os.tmpdir(), 'stage-d-cli-snapshot-'));
    t.after(() => fs.rmSync(root, { recursive: true, force: true }));
    const fx = fixture();
    const result = runCli(cliPath, [
        '--transport-root', root,
        '--authority-root', fx.authorityRoot,
        '--allocation-artifact', fx.allocationArtifactPath,
        '--ledger-root', fx.ledgerRoot,
        '--quota-config', fx.quotaConfigPath,
        '--snapshot-id', 'snap_20260913T000000000Z_0011223344556677',
        '--now', '2026-09-13T00:00:00Z',
    ]);
    assert.equal(result.status, 0, result.stdout);
    const payload = parseJsonLine(result.stdout);
    assert.equal(payload.action, 'SNAPSHOT_WRITTEN');
    assert.equal(payload.live_r2_cli_wiring, 'NOT_IMPLEMENTED');
    assert.equal(payload.report.snapshot_id, 'snap_20260913T000000000Z_0011223344556677');
    assert.equal(payload.report.source_head_transaction_id, fx.head_transaction_id);
    assert.ok(JSON.stringify(payload).length < 100000, 'the CLI report must not embed payload bytes');
});

test('the restore CLI requires exactly one action and never guesses', async t => {
    const [, cliPath] = CLI_PATHS;
    const root = fs.mkdtempSync(path.join(os.tmpdir(), 'stage-d-cli-verify-'));
    t.after(() => fs.rmSync(root, { recursive: true, force: true }));
    const transport = createLocalTransport({ root });
    const report = await backup.writeSnapshot({
        transport,
        authorityRoot: fixture().authorityRoot,
        allocationArtifactPath: fixture().allocationArtifactPath,
        ledgerRoot: fixture().ledgerRoot,
        quotaConfigPath: fixture().quotaConfigPath,
    });

    const noAction = runCli(cliPath, ['--transport-root', root, '--snapshot-id', report.snapshot_id]);
    assert.equal(noAction.status, 1);
    assert.ok(/choose exactly one of --verify-only or --destination-root/.test(parseJsonLine(noAction.stdout).error));

    const bothActions = runCli(cliPath, ['--transport-root', root, '--snapshot-id', report.snapshot_id, '--verify-only', '--destination-root', path.join(root, 'x')]);
    assert.equal(bothActions.status, 1);
    assert.ok(/choose exactly one/.test(parseJsonLine(bothActions.stdout).error));

    const noId = runCli(cliPath, ['--transport-root', root, '--verify-only']);
    assert.equal(noId.status, 1);
    assert.ok(/--snapshot-id is required/.test(parseJsonLine(noId.stdout).error));

    const noRoot = runCli(cliPath, ['--snapshot-id', report.snapshot_id, '--verify-only']);
    assert.equal(noRoot.status, 1);
    assert.ok(/--transport-root is required/.test(parseJsonLine(noRoot.stdout).error));

    for (const flag of ['--endpoint', '--bucket', '--live', '--secret-access-key']) {
        const tainted = runCli(cliPath, ['--transport-root', root, '--snapshot-id', report.snapshot_id, '--verify-only', flag, 'value']);
        assert.equal(tainted.status, 1);
        assert.ok(/LIVE_R2_CLI_WIRING=NOT_IMPLEMENTED/.test(parseJsonLine(tainted.stdout).error));
    }
});

test('the restore CLI verifies, then restores and proves the restored root', async t => {
    const [, cliPath] = CLI_PATHS;
    const root = fs.mkdtempSync(path.join(os.tmpdir(), 'stage-d-cli-restore-root-'));
    const elsewhere = fs.mkdtempSync(path.join(os.tmpdir(), 'stage-d-cli-restore-dest-'));
    t.after(() => { fs.rmSync(root, { recursive: true, force: true }); fs.rmSync(elsewhere, { recursive: true, force: true }); });
    const transport = createLocalTransport({ root });
    const report = await backup.writeSnapshot({
        transport,
        authorityRoot: fixture().authorityRoot,
        allocationArtifactPath: fixture().allocationArtifactPath,
        ledgerRoot: fixture().ledgerRoot,
        quotaConfigPath: fixture().quotaConfigPath,
    });

    const verified = runCli(cliPath, ['--transport-root', root, '--snapshot-id', report.snapshot_id, '--verify-only']);
    assert.equal(verified.status, 0, verified.stdout);
    const verifiedPayload = parseJsonLine(verified.stdout);
    assert.equal(verifiedPayload.action, 'SNAPSHOT_VERIFIED');
    assert.equal(verifiedPayload.report.result, 'PASS');

    const destinationRoot = path.join(elsewhere, 'restored');
    const restored = runCli(cliPath, ['--transport-root', root, '--snapshot-id', report.snapshot_id, '--destination-root', destinationRoot, '--fresh-process']);
    assert.equal(restored.status, 0, restored.stdout);
    const restoredPayload = parseJsonLine(restored.stdout);
    assert.equal(restoredPayload.action, 'SNAPSHOT_RESTORED');
    assert.equal(restoredPayload.report.result, 'PASS');
    assert.equal(restoredPayload.report.fresh_process_proof.ok, true);
    assert.equal(restoredPayload.report.production_fallback_used, false);
    assert.deepEqual(restoredPayload.report.production_paths_read, []);
    assert.equal(restoredPayload.live_r2_cli_wiring, 'NOT_IMPLEMENTED');
});
