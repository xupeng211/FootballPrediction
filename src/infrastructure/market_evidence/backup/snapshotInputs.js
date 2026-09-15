'use strict';

// Enumerates the exact governed input set for a Stage D snapshot.
//
// The set is the contract's minimum: the immutable committed transaction
// packages, STORE.json, the allocation authority, the durable request
// accounting epoch and entries, any required run state, and the non-secret
// quota configuration needed to interpret accounting.  Nothing else is
// eligible.  There is no directory walk that picks up "whatever is there":
// every category is named, and a missing required category fails closed.
//
// This module resolves and measures.  It never copies bytes.

const fs = require('node:fs');
const path = require('node:path');

const { SnapshotIntegrityError } = require('./transport');
const { assertNotGovernedProductionPath } = require('./localTransport');

const SNAPSHOT_INPUTS_SCHEMA_VERSION = 'stage-d-independent-backup-snapshot-inputs/v1';

const STORE_FILE = 'STORE.json';
const ALLOCATION_FILE = 'allocation.authority.json';
const COMMITTED_DIRECTORY = 'committed';
const STAGING_DIRECTORY = '.staging';
const EPOCH_FILE = 'REQUEST_ACCOUNTING_EPOCH.json';
const ENTRY_DIRECTORY = 'entries';
const LEDGER_ENTRY_PATTERN = /^\d{12}\.json$/;
const TRANSACTION_PACKAGE_PATTERN = /^tx_[a-f0-9]{64}$/;

const CATEGORY = Object.freeze({
    TRANSACTION_PACKAGE: 'transaction_package',
    STORE: 'store',
    ALLOCATION_AUTHORITY: 'allocation_authority',
    REQUEST_ACCOUNTING_EPOCH: 'request_accounting_epoch',
    REQUEST_ACCOUNTING_ENTRY: 'request_accounting_entry',
    RUN_STATE: 'run_state',
    QUOTA_CONFIG: 'quota_config',
});

const REQUIRED_CATEGORIES = Object.freeze([
    CATEGORY.TRANSACTION_PACKAGE,
    CATEGORY.STORE,
    CATEGORY.ALLOCATION_AUTHORITY,
    CATEGORY.REQUEST_ACCOUNTING_EPOCH,
    CATEGORY.QUOTA_CONFIG,
]);

// Names that mean "a secret lives here".  A snapshot must never carry one, so a
// configured root that happens to contain one is rejected rather than silently
// skipped: silently skipping would hide a misconfiguration.
const FORBIDDEN_NAME_PATTERNS = Object.freeze([
    /^\.env/i,
    /(^|[._-])env($|[._-])/i,
    /credential/i,
    /secret/i,
    /(^|[._-])token/i,
    /\.pem$/i,
    /\.key$/i,
    /^id_[a-z]+$/i,
    /^\.npmrc$/i,
    /^\.netrc$/i,
    /password/i,
]);

// Every input root is refused if it denotes the governed production area.
//
// "Explicit" is not the same as "safe".  The restore side already refuses to
// write anywhere near production, and the local transport already refuses to
// stage onto it; without the same refusal here, an operator could point
// --authority-root straight at the governed authority and the tooling would
// read and copy it, which is the one thing a snapshot tool must not be able to
// do by accident today.  The refusal is deliberately fail-closed: reading
// production for a snapshot is a decision a future, explicitly authorized
// mission makes by changing this line, not something an argument can turn on.
function assertExplicitDirectory(target, label) {
    if (typeof target !== 'string' || !target.trim()) throw new SnapshotIntegrityError(`${label} must be supplied explicitly; there is no default and no production fallback`);
    const resolved = assertNotGovernedProductionPath(target, label);
    let stat;
    try {
        stat = fs.lstatSync(resolved);
    } catch (error) {
        if (error.code === 'ENOENT') throw new SnapshotIntegrityError(`${label} does not exist: ${resolved}`);
        throw error;
    }
    if (stat.isSymbolicLink()) throw new SnapshotIntegrityError(`${label} must not be a symbolic link: ${resolved}`);
    if (!stat.isDirectory()) throw new SnapshotIntegrityError(`${label} must be a directory: ${resolved}`);
    return resolved;
}

function assertExplicitRegularFile(target, label) {
    if (typeof target !== 'string' || !target.trim()) throw new SnapshotIntegrityError(`${label} must be supplied explicitly; there is no default and no production fallback`);
    const resolved = assertNotGovernedProductionPath(target, label);
    let stat;
    try {
        stat = fs.lstatSync(resolved);
    } catch (error) {
        if (error.code === 'ENOENT') throw new SnapshotIntegrityError(`${label} is missing: ${resolved}`);
        throw error;
    }
    if (stat.isSymbolicLink()) throw new SnapshotIntegrityError(`${label} must not be a symbolic link: ${resolved}`);
    if (!stat.isFile()) throw new SnapshotIntegrityError(`${label} must be a regular file: ${resolved}`);
    return { resolved, size: stat.size };
}

function assertNameIsNotSecret(name, label) {
    for (const pattern of FORBIDDEN_NAME_PATTERNS) {
        if (pattern.test(name)) throw new SnapshotIntegrityError(`${label} looks like a credential and may never enter a snapshot: ${name}`);
    }
    return name;
}

function assertInsideRoot(root, target, label) {
    const relative = path.relative(root, target);
    if (relative === '' || relative.startsWith('..') || path.isAbsolute(relative)) throw new SnapshotIntegrityError(`${label} escapes its configured root: ${target}`);
    return relative.split(path.sep).join('/');
}

function assertPlainEntries(directory, label) {
    const names = fs.readdirSync(directory).sort();
    for (const name of names) {
        const absolute = path.join(directory, name);
        const stat = fs.lstatSync(absolute);
        if (stat.isSymbolicLink()) throw new SnapshotIntegrityError(`${label} contains a symbolic link: ${absolute}`);
    }
    return names;
}

function enumerateCommittedPackages(authorityRoot, requiredDirectories) {
    const committedRoot = path.join(authorityRoot, COMMITTED_DIRECTORY);
    const committedStat = fs.lstatSync(committedRoot);
    if (committedStat.isSymbolicLink() || !committedStat.isDirectory()) throw new SnapshotIntegrityError(`committed directory must be a plain directory: ${committedRoot}`);
    requiredDirectories.add(`transactions/${COMMITTED_DIRECTORY}`);
    const entries = [];
    for (const packageName of assertPlainEntries(committedRoot, 'committed directory')) {
        if (packageName === STAGING_DIRECTORY) throw new SnapshotIntegrityError('staging must never appear below committed/');
        if (!TRANSACTION_PACKAGE_PATTERN.test(packageName)) throw new SnapshotIntegrityError(`unexpected entry below committed/: ${packageName}`);
        const packagePath = path.join(committedRoot, packageName);
        const packageStat = fs.lstatSync(packagePath);
        if (packageStat.isSymbolicLink() || !packageStat.isDirectory()) throw new SnapshotIntegrityError(`committed package must be a plain directory: ${packagePath}`);
        requiredDirectories.add(`transactions/${COMMITTED_DIRECTORY}/${packageName}`);
        for (const fileName of assertPlainEntries(packagePath, `committed package ${packageName}`)) {
            const absolute = path.join(packagePath, fileName);
            const stat = fs.lstatSync(absolute);
            if (!stat.isFile()) throw new SnapshotIntegrityError(`committed package entry must be a regular file: ${absolute}`);
            entries.push({
                logical_path: `transactions/${COMMITTED_DIRECTORY}/${packageName}/${fileName}`,
                category: CATEGORY.TRANSACTION_PACKAGE,
                source_path: absolute,
                size: stat.size,
            });
        }
    }
    if (!entries.length) throw new SnapshotIntegrityError('no committed transaction packages were found');
    return entries;
}

function enumerateLedgerEntries(ledgerRoot, requiredDirectories) {
    const entriesRoot = path.join(ledgerRoot, ENTRY_DIRECTORY);
    const stat = fs.lstatSync(entriesRoot);
    if (stat.isSymbolicLink() || !stat.isDirectory()) throw new SnapshotIntegrityError(`request accounting entries directory must be a plain directory: ${entriesRoot}`);
    // Recorded whether or not the directory turns out to hold anything.  This
    // is the line that the whole defect turned on: the canonical ledger layout
    // requires this directory to exist, the enumeration has always asserted
    // that it does, and until now the assertion was thrown away -- so a
    // generation whose ledger happened to be empty described a tree that could
    // not be rebuilt from it.
    requiredDirectories.add(`request-accounting/${ENTRY_DIRECTORY}`);
    const collected = [];
    for (const name of assertPlainEntries(entriesRoot, 'request accounting entries directory')) {
        if (!LEDGER_ENTRY_PATTERN.test(name)) throw new SnapshotIntegrityError(`request accounting entry name is invalid: ${name}`);
        const absolute = path.join(entriesRoot, name);
        const entryStat = fs.lstatSync(absolute);
        if (!entryStat.isFile()) throw new SnapshotIntegrityError(`request accounting entry must be a regular file: ${absolute}`);
        collected.push({
            logical_path: `request-accounting/${ENTRY_DIRECTORY}/${name}`,
            category: CATEGORY.REQUEST_ACCOUNTING_ENTRY,
            source_path: absolute,
            size: entryStat.size,
        });
    }
    return collected;
}

function enumerateRunState(runStateInputs, requiredDirectories) {
    const entries = [];
    for (const input of runStateInputs) {
        if (typeof input !== 'string' || !input.trim()) throw new SnapshotIntegrityError('run state inputs must be explicit paths');
        const resolved = assertNotGovernedProductionPath(input, 'run state input');
        const stat = fs.lstatSync(resolved);
        if (stat.isSymbolicLink()) throw new SnapshotIntegrityError(`run state input must not be a symbolic link: ${resolved}`);
        const name = path.basename(resolved);
        assertNameIsNotSecret(name, 'run state input');
        if (stat.isFile()) entries.push({ logical_path: `run-state/${name}`, category: CATEGORY.RUN_STATE, source_path: resolved, size: stat.size });
        else if (stat.isDirectory()) {
            const root = assertExplicitDirectory(resolved, 'run state input');
            requiredDirectories.add('run-state');
            for (const child of assertPlainEntries(root, 'run state input')) {
                const absolute = path.join(root, child);
                const childStat = fs.lstatSync(absolute);
                if (!childStat.isFile()) throw new SnapshotIntegrityError(`run state input must contain only regular files: ${absolute}`);
                assertNameIsNotSecret(child, 'run state input');
                entries.push({ logical_path: `run-state/${child}`, category: CATEGORY.RUN_STATE, source_path: absolute, size: childStat.size });
            }
        } else throw new SnapshotIntegrityError(`run state input must be a file or directory: ${resolved}`);
    }
    return entries;
}

function enumerateSnapshotInputs({ authorityRoot, allocationArtifactPath, ledgerRoot, quotaConfigPath, runStateInputs = [] } = {}) {
    const resolvedAuthorityRoot = assertExplicitDirectory(authorityRoot, 'authorityRoot');
    const resolvedLedgerRoot = assertExplicitDirectory(ledgerRoot, 'ledgerRoot');
    if (!Array.isArray(runStateInputs)) throw new SnapshotIntegrityError('runStateInputs must be an array');

    // Staging is mutable by construction and must never be part of a snapshot.
    // Its presence is tolerated in the authority root but never enumerated.
    const stagingPath = path.join(resolvedAuthorityRoot, STAGING_DIRECTORY);

    const store = assertExplicitRegularFile(path.join(resolvedAuthorityRoot, STORE_FILE), 'STORE.json');
    assertNameIsNotSecret(STORE_FILE, 'STORE.json');
    const allocation = assertExplicitRegularFile(allocationArtifactPath, 'allocation authority artifact');
    assertNameIsNotSecret(path.basename(allocation.resolved), 'allocation authority artifact');
    const quota = assertExplicitRegularFile(quotaConfigPath, 'quota configuration');
    assertNameIsNotSecret(path.basename(quota.resolved), 'quota configuration');
    const epoch = assertExplicitRegularFile(path.join(resolvedLedgerRoot, EPOCH_FILE), 'request accounting epoch');
    assertNameIsNotSecret(EPOCH_FILE, 'request accounting epoch');

    // Directories the governed layout requires to exist, collected as the
    // enumeration asserts them.  A file manifest is not a description of a
    // tree: it is a description of the tree's *files*, and a directory with no
    // files in it leaves no trace in one.  The canonical ledger layout requires
    // `<ledger_root>/entries` to exist even when it is empty, so the generation
    // has to carry that requirement explicitly or the restored root is not the
    // tree the readers accept.
    const requiredDirectories = new Set();

    const entries = [
        { logical_path: `transactions/${STORE_FILE}`, category: CATEGORY.STORE, source_path: store.resolved, size: store.size },
        { logical_path: `transactions/${ALLOCATION_FILE}`, category: CATEGORY.ALLOCATION_AUTHORITY, source_path: allocation.resolved, size: allocation.size },
        ...enumerateCommittedPackages(resolvedAuthorityRoot, requiredDirectories),
        { logical_path: `request-accounting/${EPOCH_FILE}`, category: CATEGORY.REQUEST_ACCOUNTING_EPOCH, source_path: epoch.resolved, size: epoch.size },
        ...enumerateLedgerEntries(resolvedLedgerRoot, requiredDirectories),
        ...enumerateRunState(runStateInputs, requiredDirectories),
        { logical_path: `config/${path.basename(quota.resolved)}`, category: CATEGORY.QUOTA_CONFIG, source_path: quota.resolved, size: quota.size },
    ];

    const seen = new Set();
    for (const entry of entries) {
        if (seen.has(entry.logical_path)) throw new SnapshotIntegrityError(`duplicate logical path in the snapshot input set: ${entry.logical_path}`);
        seen.add(entry.logical_path);
        if (entry.logical_path.split('/').some(segment => segment === '.' || segment === '..')) throw new SnapshotIntegrityError(`snapshot logical path must not contain traversal segments: ${entry.logical_path}`);
        if (entry.logical_path.includes(STAGING_DIRECTORY)) throw new SnapshotIntegrityError(`staging must never enter a snapshot: ${entry.logical_path}`);
    }
    for (const category of REQUIRED_CATEGORIES) {
        if (!entries.some(entry => entry.category === category)) throw new SnapshotIntegrityError(`required snapshot category is missing: ${category}`);
    }
    // Code-unit ordering, not locale collation: the ordering feeds the input
    // set digest, and a digest that depends on the host's ICU data is not a
    // digest.  Uppercase sorts before lowercase here, deterministically, on
    // every machine.
    entries.sort((left, right) => (left.logical_path < right.logical_path ? -1 : left.logical_path > right.logical_path ? 1 : 0));

    // A path cannot be both a file and a directory.  The two sets are built
    // independently above, so the disagreement is checked rather than assumed
    // away: a required directory that an artifact already occupies would make
    // the restore fail at mkdir with a message about the wrong thing.
    const filePaths = new Set(entries.map(entry => entry.logical_path));
    for (const directory of requiredDirectories) {
        if (filePaths.has(directory)) throw new SnapshotIntegrityError(`a governed path is both a file and a required directory: ${directory}`);
    }

    return Object.freeze({
        schema_version: SNAPSHOT_INPUTS_SCHEMA_VERSION,
        authority_root: resolvedAuthorityRoot,
        allocation_artifact_path: allocation.resolved,
        ledger_root: resolvedLedgerRoot,
        quota_config_path: quota.resolved,
        staging_excluded: true,
        staging_present: fs.existsSync(stagingPath),
        entries: Object.freeze(entries.map(entry => Object.freeze({ ...entry }))),
        required_directories: Object.freeze([...requiredDirectories].sort()),
        total_bytes: entries.reduce((sum, entry) => sum + entry.size, 0),
        categories: Object.freeze(entries.reduce((accumulator, entry) => {
            accumulator[entry.category] = (accumulator[entry.category] || 0) + 1;
            return accumulator;
        }, {})),
    });
}

const REQUEST_ACCOUNTING_DIRECTORY = 'request-accounting';

// Required directories for a generation whose manifest predates
// `required_directories`.
//
// Generations written before the field existed do not describe their
// directories, and one of them -- the only one accepted against real hardware
// so far -- is already on the backup target.  Refusing to restore it would
// make an intact backup unreadable over a manifest omission, so the
// requirement is re-derived here instead.
//
// This is a statement of the canonical *layout*, not a fact about any
// particular generation: the request-ledger contract is that a ledger root
// contains an `entries` child directory, and the canonical reader requires it
// to exist whether or not it holds anything.  Any generation that carries a
// request-accounting artifact is therefore a generation whose ledger root must
// contain that directory.  The same rule is applied to every pre-field
// generation; nothing here reads a snapshot id, a timestamp or a machine path.
//
// It is version-bound by construction: the caller applies it only when the
// manifest carries no `required_directories` field, and the restore report
// records which of the two it used.
function deriveRequiredDirectoriesForLegacyManifest(artifacts) {
    if (!Array.isArray(artifacts)) throw new SnapshotIntegrityError('a legacy manifest must carry an artifact list to derive its required directories');
    const derived = new Set();
    const carriesLedger = artifacts.some(artifact => artifact && typeof artifact.logical_path === 'string'
        && artifact.logical_path.startsWith(`${REQUEST_ACCOUNTING_DIRECTORY}/`));
    if (carriesLedger) derived.add(`${REQUEST_ACCOUNTING_DIRECTORY}/${ENTRY_DIRECTORY}`);
    return Object.freeze([...derived].sort());
}

module.exports = {
    SNAPSHOT_INPUTS_SCHEMA_VERSION,
    CATEGORY,
    REQUIRED_CATEGORIES,
    STORE_FILE,
    ALLOCATION_FILE,
    COMMITTED_DIRECTORY,
    STAGING_DIRECTORY,
    EPOCH_FILE,
    ENTRY_DIRECTORY,
    LEDGER_ENTRY_PATTERN,
    enumerateSnapshotInputs,
    deriveRequiredDirectoriesForLegacyManifest,
    assertNameIsNotSecret,
};
