'use strict';

const assert = require('node:assert/strict');
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const test = require('node:test');

const { buildBackupFixture } = require('../../../helpers/backup_authority_fixture');
const { installNetworkTripwire } = require('../../../helpers/network_tripwire');
const {
    CATEGORY,
    REQUIRED_CATEGORIES,
    enumerateSnapshotInputs,
    assertNameIsNotSecret,
} = require('../../../../src/infrastructure/market_evidence/backup/snapshotInputs');
const { SnapshotIntegrityError } = require('../../../../src/infrastructure/market_evidence/backup/transport');
const { isGovernedProductionPath } = require('../../../../src/infrastructure/market_evidence/backup/localTransport');

// Enumerating the governed inputs walks a real authority tree, and the whole
// file is offline by construction.  Sealing the file rather than one chosen
// test is what makes "no test here reaches the network" a property of the file
// instead of a property of the test someone remembered to wrap.
const tripwire = installNetworkTripwire();
test.after(() => {
    assert.deepEqual(tripwire.attempts, [], 'no test in this file may attempt outbound network access');
    tripwire.restore();
});

let shared = null;
function fixture() {
    if (shared === null) shared = buildBackupFixture({ transactionCount: 2, includeLedgerEntries: 2 });
    return shared;
}
test.after(() => { if (shared) shared.cleanup(); });

function tempDir(t, prefix) {
    const root = fs.mkdtempSync(path.join(os.tmpdir(), prefix));
    t.after(() => fs.rmSync(root, { recursive: true, force: true }));
    return root;
}

function enumerate(overrides = {}) {
    const fx = fixture();
    return enumerateSnapshotInputs({
        authorityRoot: fx.authorityRoot,
        allocationArtifactPath: fx.allocationArtifactPath,
        ledgerRoot: fx.ledgerRoot,
        quotaConfigPath: fx.quotaConfigPath,
        ...overrides,
    });
}

test('the enumerated set carries every required category', () => {
    const inputs = enumerate();
    const categories = new Set(inputs.entries.map(entry => entry.category));
    for (const category of REQUIRED_CATEGORIES) assert.ok(categories.has(category), `${category} must be present`);
    assert.equal(inputs.schema_version, 'stage-d-independent-backup-snapshot-inputs/v1');
    assert.equal(inputs.staging_excluded, true);
});

test('the enumerated set is exactly the governed inputs, sorted and de-duplicated', () => {
    const inputs = enumerate();
    const logicalPaths = inputs.entries.map(entry => entry.logical_path);
    assert.deepEqual(logicalPaths, [...logicalPaths].sort());
    assert.equal(new Set(logicalPaths).size, logicalPaths.length);
    assert.ok(logicalPaths.includes('transactions/STORE.json'));
    assert.ok(logicalPaths.includes('transactions/allocation.authority.json'));
    assert.ok(logicalPaths.includes('request-accounting/REQUEST_ACCOUNTING_EPOCH.json'));
    assert.ok(logicalPaths.some(logicalPath => logicalPath.startsWith('transactions/committed/tx_')));
    assert.ok(logicalPaths.some(logicalPath => logicalPath.startsWith('config/')));
});

test('total_bytes is the sum of the enumerated sizes and matches the files on disk', () => {
    const inputs = enumerate();
    const measured = inputs.entries.reduce((sum, entry) => sum + fs.lstatSync(entry.source_path).size, 0);
    assert.equal(inputs.total_bytes, measured);
    assert.deepEqual(Object.keys(inputs.categories).sort(), [...new Set(inputs.entries.map(entry => entry.category))].sort());
});

test('the staging directory is never enumerated', () => {
    const inputs = enumerate();
    assert.ok(inputs.staging_present, 'the fixture bootstrap creates a staging directory');
    assert.equal(inputs.entries.some(entry => entry.logical_path.includes('.staging')), false);
    assert.equal(inputs.entries.some(entry => entry.source_path.includes('.staging')), false);
});

test('a missing required artifact fails closed rather than shrinking the set', t => {
    const fx = fixture();
    assert.throws(
        () => enumerate({ allocationArtifactPath: path.join(tempDir(t, 'stage-d-inputs-'), 'absent.json') }),
        error => error instanceof SnapshotIntegrityError && /allocation authority artifact is missing/.test(error.message)
    );
    assert.throws(
        () => enumerate({ quotaConfigPath: path.join(tempDir(t, 'stage-d-inputs-'), 'absent.json') }),
        error => error instanceof SnapshotIntegrityError && /quota configuration is missing/.test(error.message)
    );
    assert.throws(
        () => enumerate({ ledgerRoot: path.join(fx.root, 'no-such-ledger') }),
        error => error instanceof SnapshotIntegrityError && /ledgerRoot does not exist/.test(error.message)
    );
});

test('every root must be supplied explicitly', () => {
    const fx = fixture();
    for (const field of ['authorityRoot', 'ledgerRoot']) {
        assert.throws(() => enumerate({ [field]: undefined }), error => error instanceof SnapshotIntegrityError && /must be supplied explicitly/.test(error.message));
        assert.throws(() => enumerate({ [field]: '' }), error => error instanceof SnapshotIntegrityError && /must be supplied explicitly/.test(error.message));
    }
    assert.throws(() => enumerate({ allocationArtifactPath: null }), error => error instanceof SnapshotIntegrityError && /must be supplied explicitly/.test(error.message));
    assert.throws(() => enumerate({ quotaConfigPath: '   ' }), error => error instanceof SnapshotIntegrityError && /must be supplied explicitly/.test(error.message));
    assert.ok(fx);
});

test('a symlinked governed root or artifact is refused', t => {
    const fx = fixture();
    const linkRoot = path.join(tempDir(t, 'stage-d-inputs-'), 'linked-transactions');
    fs.symlinkSync(fx.authorityRoot, linkRoot);
    assert.throws(() => enumerate({ authorityRoot: linkRoot }), error => error instanceof SnapshotIntegrityError && /symbolic link/.test(error.message));

    const linkFile = path.join(tempDir(t, 'stage-d-inputs-'), 'linked-allocation.json');
    fs.symlinkSync(fx.allocationArtifactPath, linkFile);
    assert.throws(() => enumerate({ allocationArtifactPath: linkFile }), error => error instanceof SnapshotIntegrityError && /symbolic link/.test(error.message));
});

test('a symlink inside a governed package is refused', t => {
    const fx = fixture();
    const packageName = fs.readdirSync(path.join(fx.authorityRoot, 'committed')).find(name => name.startsWith('tx_'));
    const link = path.join(fx.authorityRoot, 'committed', packageName, 'linked.json');
    fs.symlinkSync(path.join(fx.root, 'stage_d_quota_budget.json'), link);
    t.after(() => fs.rmSync(link, { force: true }));
    assert.throws(() => enumerate(), error => error instanceof SnapshotIntegrityError && /symbolic link/.test(error.message));
});

test('credential-shaped names are refused rather than silently skipped', t => {
    for (const name of ['.env', '.env.local', 'credentials.json', 'my-secret.json', 'api_token.txt', 'server.pem', 'private.key', 'id_rsa', '.npmrc', '.netrc', 'db-password.txt']) {
        assert.throws(() => assertNameIsNotSecret(name, 'input'), error => error instanceof SnapshotIntegrityError && /credential/.test(error.message), `${name} must be refused`);
    }
    assert.equal(assertNameIsNotSecret('STORE.json', 'input'), 'STORE.json');
    assert.equal(assertNameIsNotSecret('REQUEST_ACCOUNTING_EPOCH.json', 'input'), 'REQUEST_ACCOUNTING_EPOCH.json');

    const fx = fixture();
    const secretPath = path.join(tempDir(t, 'stage-d-inputs-'), 'credentials.json');
    fs.writeFileSync(secretPath, '{}');
    assert.throws(() => enumerate({ runStateInputs: [secretPath] }), error => error instanceof SnapshotIntegrityError && /credential/.test(error.message));
    assert.ok(fx);
});

test('run state inputs are additive and land under run-state/', t => {
    const fx = fixture();
    const runStateRoot = tempDir(t, 'stage-d-run-state-');
    fs.writeFileSync(path.join(runStateRoot, 'turn.json'), '{"turn":1}');
    const inputs = enumerate({ runStateInputs: [runStateRoot] });
    const runState = inputs.entries.filter(entry => entry.category === CATEGORY.RUN_STATE);
    assert.deepEqual(runState.map(entry => entry.logical_path), ['run-state/turn.json']);
    assert.ok(inputs.entries.some(entry => entry.logical_path === 'transactions/STORE.json'));
    assert.ok(fx);

    assert.throws(() => enumerate({ runStateInputs: 'not-an-array' }), error => error instanceof SnapshotIntegrityError && /must be an array/.test(error.message));
});

test('an unexpected entry below committed/ is refused instead of being copied', t => {
    const fx = fixture();
    const stray = path.join(fx.authorityRoot, 'committed', 'not-a-transaction');
    fs.mkdirSync(stray);
    fs.writeFileSync(path.join(stray, 'file.json'), '{}');
    t.after(() => fs.rmSync(stray, { recursive: true, force: true }));
    assert.throws(() => enumerate(), error => error instanceof SnapshotIntegrityError && /unexpected entry below committed\//.test(error.message));
});

test('an invalid ledger entry filename is refused', t => {
    const fx = fixture();
    const stray = path.join(fx.ledgerRoot, 'entries', 'not-a-sequence.json');
    fs.writeFileSync(stray, '{}');
    t.after(() => fs.rmSync(stray, { force: true }));
    assert.throws(() => enumerate(), error => error instanceof SnapshotIntegrityError && /entry name is invalid/.test(error.message));
});

test('the enumerated set is frozen and never carries a resolved credential path', () => {
    const inputs = enumerate();
    assert.equal(Object.isFrozen(inputs), true);
    assert.equal(Object.isFrozen(inputs.entries), true);
    for (const entry of inputs.entries) {
        assert.equal(Object.isFrozen(entry), true);
        assert.equal(typeof entry.source_path, 'string');
        assert.equal(path.isAbsolute(entry.source_path), true);
    }
});

// "Explicit" is not the same as "safe".  A root that the caller names and that
// exists is still the wrong root when it is the governed production area, and
// without this refusal the tooling would read and copy the very authority it
// exists to protect.  Every input root is exercised, because a guard that only
// covers --authority-root would leave the same hole reachable through the
// ledger, the allocation artifact, the quota configuration or run state.
test('no snapshot input root may point into the governed production area', t => {
    const fx = fixture();
    const productionRoot = path.join(tempDir(t, 'stage-d-backup-prod-'), 'data', 'market_evidence', 'live');
    fs.mkdirSync(productionRoot, { recursive: true });
    const productionFile = path.join(productionRoot, 'STORE.json');
    fs.writeFileSync(productionFile, '{}');

    const attempts = [
        ['the authority root itself', { authorityRoot: productionRoot }],
        ['a directory below the authority root', { authorityRoot: path.join(productionRoot, 'committed') }],
        ['the ledger root', { ledgerRoot: productionRoot }],
        ['the allocation artifact', { allocationArtifactPath: productionFile }],
        ['the quota configuration', { quotaConfigPath: productionFile }],
        ['a run state file', { runStateInputs: [productionFile] }],
        ['a run state directory', { runStateInputs: [productionRoot] }],
    ];

    for (const [label, overrides] of attempts) {
        assert.throws(
            () => enumerate(overrides),
            error => error instanceof SnapshotIntegrityError && /governed production area/.test(error.message),
            `${label} must be refused`,
        );
    }

    // The refusal is by whole path segment, so a neighbour is not condemned by
    // a substring match and the denylist stays something a reader can reason
    // about.
    const neighbour = path.join(tempDir(t, 'stage-d-backup-neighbour-'), 'data', 'market_evidence', 'live-2');
    fs.mkdirSync(neighbour, { recursive: true });
    assert.throws(() => enumerate({ authorityRoot: neighbour }), error => error instanceof SnapshotIntegrityError && /STORE\.json is missing/.test(error.message));
});

// The refusal above answers "does this path spell the governed area", which
// `path.resolve` answers without touching the filesystem -- and that is exactly
// why it cannot see a symlinked ancestor.  A root reached through one spells
// the governed area nowhere while every read through it lands inside, so the
// real location has to be refused as well.  Each input kind is exercised here
// for the same reason each one is exercised above: a guard that covered only
// --authority-root would leave the hole open through the ledger, the allocation
// artifact, the quota configuration or run state.
test('no snapshot input root may reach the governed production area through a symlinked ancestor', t => {
    const base = tempDir(t, 'stage-d-backup-prod-link-');
    const production = path.join(base, 'elsewhere', 'data', 'market_evidence', 'live');
    fs.mkdirSync(production, { recursive: true });
    fs.writeFileSync(path.join(production, 'STORE.json'), '{}');
    const link = path.join(base, 'link');
    fs.symlinkSync(production, link);

    assert.equal(isGovernedProductionPath(link), false, 'the lexical check must not be what refuses these paths');
    assert.equal(fs.realpathSync(link), fs.realpathSync(production), 'these paths must really land in the governed area');

    const attempts = [
        ['the authority root', { authorityRoot: link }],
        ['a directory below the authority root', { authorityRoot: path.join(link, 'committed') }],
        ['the ledger root', { ledgerRoot: link }],
        ['the allocation artifact', { allocationArtifactPath: path.join(link, 'STORE.json') }],
        ['the quota configuration', { quotaConfigPath: path.join(link, 'STORE.json') }],
        ['a run state file', { runStateInputs: [path.join(link, 'STORE.json')] }],
        ['a run state directory', { runStateInputs: [link] }],
    ];

    for (const [label, overrides] of attempts) {
        assert.throws(
            () => enumerate(overrides),
            error => error instanceof SnapshotIntegrityError && /resolve into the governed production area|must never be the governed production area/.test(error.message),
            `${label} must be refused when it is reached through a symlinked ancestor`,
        );
    }
});
