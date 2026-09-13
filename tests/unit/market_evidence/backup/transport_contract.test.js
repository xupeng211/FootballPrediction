'use strict';

const assert = require('node:assert/strict');
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const test = require('node:test');
const { spawnSync } = require('node:child_process');

const R2_TRANSPORT_PATH = require.resolve('../../../../src/infrastructure/market_evidence/backup/r2Transport');

const backup = require('../../../../src/infrastructure/market_evidence/backup');
const { installNetworkTripwire } = require('../../../helpers/network_tripwire');
const { createLocalTransport, canonicalizeKey, isGovernedProductionPath } = require('../../../../src/infrastructure/market_evidence/backup/localTransport');
const {
    REQUIRED_TRANSPORT_METHODS,
    FORBIDDEN_TRANSPORT_METHODS,
    TransportContractError,
    ObjectAlreadyExistsError,
    SnapshotIntegrityError,
    assertTransportContract,
} = require('../../../../src/infrastructure/market_evidence/backup/transport');

// The whole file runs behind the tripwire, not just the one test that touches
// the R2 transport.  Every test here is offline by construction, and a file
// that seals only its most obviously networked test would leave the rest
// unproven -- an outbound attempt from anywhere else in the file is the same
// breach whether or not the test looks like it could make one.
const tripwire = installNetworkTripwire();
test.after(() => {
    assert.deepEqual(tripwire.attempts, [], 'no test in this file may attempt outbound network access');
    tripwire.restore();
});

function tempRoot(t) {
    const root = fs.mkdtempSync(path.join(os.tmpdir(), 'stage-d-transport-'));
    t.after(() => fs.rmSync(root, { recursive: true, force: true }));
    return root;
}

test('the local transport satisfies the transport contract', t => {
    const transport = createLocalTransport({ root: tempRoot(t) });
    assert.equal(assertTransportContract(transport), transport);
    assert.deepEqual(REQUIRED_TRANSPORT_METHODS.filter(method => typeof transport[method] !== 'function'), []);
    assert.deepEqual(FORBIDDEN_TRANSPORT_METHODS.filter(method => typeof transport[method] === 'function'), []);
});

test('the local transport declares itself create-only and delete-free', t => {
    const described = createLocalTransport({ root: tempRoot(t) }).describe();
    assert.equal(described.create_only, true);
    assert.equal(described.delete_exposed, false);
    assert.equal(described.kind, 'local');
});

test('a transport exposing any delete capability is rejected', t => {
    const transport = createLocalTransport({ root: tempRoot(t) });
    for (const method of FORBIDDEN_TRANSPORT_METHODS) {
        const compromised = { ...transport, [method]: () => {} };
        assert.throws(() => assertTransportContract(compromised), error => error instanceof TransportContractError && /forbidden capability/.test(error.message), `${method} must be rejected`);
    }
});

test('a transport missing a required capability is rejected', t => {
    const transport = createLocalTransport({ root: tempRoot(t) });
    for (const method of REQUIRED_TRANSPORT_METHODS) {
        const incomplete = { ...transport };
        delete incomplete[method];
        assert.throws(() => assertTransportContract(incomplete), error => error instanceof TransportContractError && /missing required capability/.test(error.message), `${method} must be required`);
    }
});

test('a transport that does not declare create-only semantics is rejected', t => {
    const transport = createLocalTransport({ root: tempRoot(t) });
    assert.throws(
        () => assertTransportContract({ ...transport, describe: () => ({ kind: 'local', create_only: false, delete_exposed: false }) }),
        error => error instanceof TransportContractError && /create_only/.test(error.message)
    );
    assert.throws(
        () => assertTransportContract({ ...transport, describe: () => ({ kind: 'local', create_only: true, delete_exposed: true }) }),
        error => error instanceof TransportContractError && /delete_exposed/.test(error.message)
    );
});

test('a create-only write refuses to overwrite an existing object', t => {
    const transport = createLocalTransport({ root: tempRoot(t) });
    const first = transport.putObjectCreateOnly({ key: 'generation/MANIFEST.json', bytes: Buffer.from('first') });
    assert.equal(first.size, 5);
    assert.throws(
        () => transport.putObjectCreateOnly({ key: 'generation/MANIFEST.json', bytes: Buffer.from('second') }),
        error => error instanceof ObjectAlreadyExistsError && error.code === 'OBJECT_ALREADY_EXISTS'
    );
    assert.equal(transport.getObject({ key: 'generation/MANIFEST.json' }).toString('utf8'), 'first');
});

test('object keys are canonicalized and traversal is refused', () => {
    assert.equal(canonicalizeKey('snap_20260913T000000000Z_abcdef0123456789/payload/transactions/STORE.json'), 'snap_20260913T000000000Z_abcdef0123456789/payload/transactions/STORE.json');
    for (const key of ['', '/absolute/path', 'trailing/slash/', 'double//segment', 'dot/./segment', 'dot/dot/../segment', 'back\\slash', 'a b', 'null\0byte']) {
        assert.throws(() => canonicalizeKey(key), error => error instanceof SnapshotIntegrityError, `${JSON.stringify(key)} must be refused`);
    }
});

test('the local transport refuses to target the governed production area', t => {
    const forbidden = path.join(os.tmpdir(), 'data', 'market_evidence', 'live', 'transactions');
    fs.mkdirSync(forbidden, { recursive: true });
    t.after(() => fs.rmSync(path.join(os.tmpdir(), 'data'), { recursive: true, force: true }));
    assert.throws(
        () => createLocalTransport({ root: forbidden }),
        error => error instanceof SnapshotIntegrityError && /governed production area/.test(error.message)
    );
});

// `path.resolve` never asks the filesystem, so a root reached through a
// symlinked ancestor spells none of the governed area while every read and
// write through it lands inside it.  The lexical denylist is real but is not
// the whole question, and the lstat of the final component cannot answer it
// either: the link is higher up, so the final component is an ordinary
// directory.  The assertion that the literal check does *not* refuse this path
// is what makes the test fail if the physical arm is ever removed, rather than
// passing for the reason the bug already satisfied.
test('a root reached through a symlinked ancestor is refused', t => {
    const base = tempRoot(t);
    const production = path.join(base, 'elsewhere', 'data', 'market_evidence', 'live', 'nested');
    fs.mkdirSync(production, { recursive: true });
    const link = path.join(base, 'link');
    fs.symlinkSync(path.dirname(production), link);
    const throughLink = path.join(link, 'nested');

    assert.equal(isGovernedProductionPath(throughLink), false, 'the lexical check must not be what refuses this path');
    assert.equal(fs.realpathSync(throughLink), fs.realpathSync(production), 'the path must really land in the governed area');
    assert.throws(
        () => createLocalTransport({ root: throughLink }),
        error => error instanceof SnapshotIntegrityError && /resolve into the governed production area/.test(error.message)
    );
});

test('a root whose own real location is benign is still accepted', t => {
    const real = tempRoot(t);
    fs.mkdirSync(path.join(real, 'generation'));
    const link = path.join(tempRoot(t), 'link');
    fs.symlinkSync(real, link);
    const transport = createLocalTransport({ root: path.join(link, 'generation') });
    assert.equal(assertTransportContract(transport), transport, 'the physical arm must refuse the governed area, not symlinks in general');
});

test('the local transport has no default root', () => {
    assert.throws(() => createLocalTransport({}), error => error instanceof SnapshotIntegrityError && /explicit root/.test(error.message));
    assert.throws(() => createLocalTransport(), error => error instanceof SnapshotIntegrityError && /explicit root/.test(error.message));
});

test('a symlinked object path is never followed', t => {
    const root = tempRoot(t);
    const transport = createLocalTransport({ root });
    const outside = path.join(tempRoot(t), 'outside.json');
    fs.writeFileSync(outside, 'outside');
    fs.symlinkSync(outside, path.join(root, 'link.json'));
    assert.throws(() => transport.getObject({ key: 'link.json' }), error => error instanceof SnapshotIntegrityError && /symbolic links/.test(error.message));
    assert.throws(() => transport.headObject({ key: 'link.json' }), error => error instanceof SnapshotIntegrityError && /symbolic links/.test(error.message));
});

test('a missing object reads as absent rather than as an error', t => {
    const transport = createLocalTransport({ root: tempRoot(t) });
    assert.equal(transport.getObject({ key: 'nowhere/at/all.json' }), null);
    assert.equal(transport.headObject({ key: 'nowhere/at/all.json' }), null);
});

test('listObjects walks the whole root and filters by prefix', t => {
    const transport = createLocalTransport({ root: tempRoot(t) });
    transport.putObjectCreateOnly({ key: 'snap_a/payload/one.json', bytes: Buffer.from('1') });
    transport.putObjectCreateOnly({ key: 'snap_a/payload/two.json', bytes: Buffer.from('22') });
    transport.putObjectCreateOnly({ key: 'snap_b/payload/three.json', bytes: Buffer.from('333') });
    const all = transport.listObjects({});
    assert.deepEqual(all.map(entry => entry.key), ['snap_a/payload/one.json', 'snap_a/payload/two.json', 'snap_b/payload/three.json']);
    assert.deepEqual(transport.listObjects({ prefix: 'snap_a/' }).map(entry => entry.key), ['snap_a/payload/one.json', 'snap_a/payload/two.json']);
    assert.deepEqual(transport.listObjects({ prefix: 'snap_a/payload/two.json' }).map(entry => entry.size), [2]);
});

// A transport speaks logical keys on both sides of its boundary.  Listing is
// the one method where the provider hands back a physical key, so it is the one
// place a configured prefix can leak into the manifest and the verifier -- and
// the verifier compares the listed set against the manifest's logical keys for
// exact equality, so a leak would report every object as unexpected *and* every
// expected object as missing.  A prefixed transport would then be unable to
// verify a generation it had just written.
// The on-demand boundary has to hold at the module, not only at the barrel.
// `require` is the thing that links a dependency, so a module that links the
// network client while being required has already broken the boundary no matter
// what the barrel around it does -- and a test file that requires it to reach
// the transport would be the first place that shows up.
//
// Both halves are asserted in fresh child processes: the second exists so the
// first cannot pass for a probe that observes nothing.
test('requiring the R2 transport does not link the network client', () => {
    const probe = action => [
        `const api = require(${JSON.stringify(R2_TRANSPORT_PATH)});`,
        `const linked = () => Object.keys(require.cache).filter(id => id.includes('@aws-sdk'));`,
        'const before = linked();',
        action,
        'console.log(JSON.stringify({ before, after: linked() }));',
    ].join('\n');

    const required = spawnSync(process.execPath, ['-e', probe('')], { encoding: 'utf8', env: { PATH: process.env.PATH || '' } });
    assert.equal(required.status, 0, required.stderr);
    const observed = JSON.parse(required.stdout.trim());
    assert.deepEqual(observed.before, [], 'the probe must start with no AWS SDK loaded');
    assert.deepEqual(observed.after, [], 'requiring the transport must not link @aws-sdk/client-s3');

    const constructed = spawnSync(process.execPath, ['-e', probe([
        'api.createR2Transport({',
        "    endpoint: 'https://example.invalid', bucket: 'stage-d-backup', region: 'auto',",
        "    credentials: { accessKeyId: 'AKIASTUB', secretAccessKey: 'stub-secret' },",
        '});',
    ].join('\n'))], { encoding: 'utf8', env: { PATH: process.env.PATH || '' } });
    const constructedObserved = JSON.parse(constructed.stdout.trim());
    assert.ok(
        constructedObserved.after.some(id => id.includes('@aws-sdk')),
        'constructing a transport must be what links the client, or the assertion above proves nothing',
    );
});

test('a prefixed R2 transport lists logical keys while asking the provider in physical ones', async () => {
    // Reached through the barrel's on-demand seam, which is the only sanctioned
    // way to it: requiring r2Transport directly would bypass the boundary the
    // barrel exists to hold, and would link the network client at file load.
    const { createR2Transport } = backup.loadR2Transport();
    const asked = [];
    const client = {
        send(command) {
            asked.push(command.input);
            return Promise.resolve({
                Contents: [
                    { Key: 'snapshots/snap-1/manifest.json', Size: 10 },
                    { Key: 'snapshots/snap-1/payload/aa.json', Size: 20 },
                    // Outside the configured scope: not evidence about this
                    // generation, so it must not appear as one of its objects.
                    { Key: 'somewhere-else/manifest.json', Size: 30 },
                ],
                IsTruncated: false,
            });
        },
    };
    const transport = createR2Transport({
        endpoint: 'https://example.invalid',
        bucket: 'stage-d-backup',
        region: 'auto',
        prefix: '/snapshots/',
        credentials: { accessKeyId: 'AKIASTUB', secretAccessKey: 'stub-secret' },
        client,
    });

    const objects = await transport.listObjects({ prefix: 'snap-1/' });
    assert.deepEqual(objects.map(entry => entry.key), ['snap-1/manifest.json', 'snap-1/payload/aa.json']);
    assert.deepEqual(objects.map(entry => entry.size), [10, 20]);
    assert.equal(asked[0].Prefix, 'snapshots/snap-1/', 'the provider is addressed in physical keys');
});
