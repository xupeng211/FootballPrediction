'use strict';

/* eslint-disable max-lines -- the Blocker #2 permission contract, its inert remediation planner and the kernel-enforced proof that binds them are one safety contract: the audit, the plan and the tests that falsify them have to be reviewed together, and splitting them would hide a mismatch between what is classified and what is planned. */
//
// Stage D Blocker #2 Phase A — runtime filesystem permission contract tests.
//
// These tests build REAL directory trees with REAL modes and REAL ownership on
// a real filesystem, then make REAL open() calls whose kernel verdicts are
// asserted.  No access check is mocked; the only injected input is the declared
// runtime identity, which is the contract's own parameter.
//
// One limit is stated honestly rather than papered over: a file owned by a
// foreign uid cannot be created without privilege, so the "root-owned 0400
// package" case declares a foreign runtime identity, and the kernel half of the
// same claim is independently proved against a real EACCES that this
// unprivileged process genuinely receives.  Group ownership, by contrast, CAN
// be varied without privilege, so the wrong-group case uses real chown metadata.

process.env.NODE_ENV = 'test';

const assert = require('node:assert/strict');
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const test = require('node:test');
const { spawnSync } = require('node:child_process');

// ---------------------------------------------------------------------------
// Runtime identity of the test process itself
// ---------------------------------------------------------------------------
//
// Everything below proves a property OF an unprivileged cold-loading identity:
// that a 0o000 artifact is unreadable, that a 0o000 directory is untraversable,
// that a foreign-owned 0o400 package is unreachable.  A uid 0 process bypasses
// every one of those checks, so a suite that quietly "passed" as root would be
// asserting nothing at all — the same failure mode that created Blocker #2.
//
// The canonical local profile (`make verify-targeted`) executes inside the dev
// container, which runs as uid 0.  Rather than weaken the assertions, skip them,
// or mock fs.access, the file re-executes itself once under an unprivileged
// identity and forwards the child's TAP stream and exit code verbatim.  The
// suite therefore proves the same kernel-enforced boundary on the host (already
// unprivileged: a no-op) and in the container (dropped to RUNTIME_UID).
//
// If the drop cannot be performed the run FAILS loudly.  It never falls back to
// running the assertions as root.
const RUNTIME_UID = 1000;
const RUNTIME_GID = 1000;
const IDENTITY_ENV = 'STAGE_D_PERMISSION_CONTRACT_TEST_IDENTITY';

if (process.getuid() === 0 && process.env[IDENTITY_ENV] !== 'unprivileged') {
    const child = spawnSync(process.execPath, [__filename, ...process.argv.slice(2)], {
        uid: RUNTIME_UID,
        gid: RUNTIME_GID,
        stdio: 'inherit',
        env: { ...process.env, [IDENTITY_ENV]: 'unprivileged' },
    });
    if (child.error) {
        console.error(`[permission-contract] cannot drop to uid ${RUNTIME_UID}: ${child.error.message}`);
        process.exit(1);
    }
    process.exit(child.status === null ? 1 : child.status);
}

const contract = require('../../../scripts/ops/stage_d_runtime_filesystem_permission_contract');
const planner = require('../../../scripts/ops/stage_d_runtime_filesystem_remediation_plan');

const OPS = path.join(__dirname, '..', '..', '..', 'scripts', 'ops');
const AUDIT_CLI = path.join(OPS, 'stage_d_runtime_filesystem_inspect.js');
const CONTRACT_MODULE = path.join(OPS, 'stage_d_runtime_filesystem_permission_contract.js');
const PLAN_MODULE = path.join(OPS, 'stage_d_runtime_filesystem_remediation_plan.js');

const RUNTIME = Object.freeze({ uid: process.getuid(), gid: process.getgid(), groups: Object.freeze([...process.getgroups()]), source: 'TEST' });
const FOREIGN = Object.freeze({ uid: RUNTIME.uid + 1, gid: RUNTIME.gid + 1, groups: Object.freeze([]), source: 'DECLARED' });
const PACKAGE_FILES = contract.describeContract().immutable_package_file_set;

function tempRoot(label) {
    // The tree must not sit directly under a world-writable non-sticky parent,
    // so it is created inside a private container directory.
    const container = fs.mkdtempSync(path.join(os.tmpdir(), `sd-perm-${label}-`));
    return fs.mkdtempSync(path.join(container, 'authority-'));
}

// Some cases deliberately strip a directory's traverse bit, which also blocks
// the recursive delete, so the tree is repaired in memory before removal.
function cleanup(target) {
    const container = path.dirname(target);
    const repair = entry => {
        let stat;
        try {
            stat = fs.lstatSync(entry);
        } catch {
            return;
        }
        if (!stat.isDirectory() || stat.isSymbolicLink()) return;
        try {
            fs.chmodSync(entry, 0o700);
        } catch {
            return;
        }
        for (const name of fs.readdirSync(entry)) repair(path.join(entry, name));
    };
    try {
        repair(container);
    } catch {
        // best effort: removal below still reports a real failure
    }
    fs.rmSync(container, { recursive: true, force: true, maxRetries: 3 });
}

// The accounting ledger is a separate governed root with its own write surface.
function buildLedger(parent, name = 'ledger') {
    const ledger = path.join(parent, name);
    makeDirectory(ledger, 0o700);
    makeDirectory(path.join(ledger, 'entries'), 0o700);
    makeFile(path.join(ledger, 'REQUEST_ACCOUNTING_EPOCH.json'), '{}', 0o400);
    makeFile(path.join(ledger, 'entries', '000000000001.json'), '{}', 0o400);
    return ledger;
}

function makeDirectory(target, mode) {
    fs.mkdirSync(target, { recursive: true, mode });
    fs.chmodSync(target, mode);
}

function makeFile(target, content, mode) {
    fs.writeFileSync(target, content);
    fs.chmodSync(target, mode);
}

// Access-ACL round-trip helpers.  These drive the real getfacl/setfacl: an ACL
// synthesised in memory would prove nothing about what setfacl actually
// restores, which is the only claim a rollback manifest is allowed to make.
function aclLines(target) {
    const result = spawnSync('getfacl', ['-n', '-p', '--absolute-names', target], { encoding: 'utf8' });
    assert.equal(result.status, 0, `getfacl failed: ${result.stderr}`);
    return result.stdout.split('\n').filter(line => line && !line.startsWith('#')).map(line => line.trim()).sort();
}

function setAcl(args, target) {
    const result = spawnSync('setfacl', [...args, target], { encoding: 'utf8' });
    assert.equal(result.status, 0, `setfacl ${args.join(' ')} failed: ${result.stderr}`);
}

// The same ACL as a structured record, shape-compatible with what the contract
// observes and what the plan has to replay.
function structuredAcl(target) {
    const parsed = { named_user_perms: {}, named_group_perms: {} };
    for (const line of aclLines(target)) {
        const [field, qualifier, permission] = line.split(':');
        if (permission === undefined) continue;
        if (field === 'mask') parsed.mask = permission;
        else if (field === 'other') parsed.other = permission;
        else if (field === 'user' && qualifier) parsed.named_user_perms[qualifier] = permission;
        else if (field === 'user') parsed.owner = permission;
        else if (field === 'group' && qualifier) parsed.named_group_perms[qualifier] = permission;
        else if (field === 'group') parsed.group = permission;
    }
    parsed.named_entries = Object.keys(parsed.named_user_perms).map(key => `user:${key}`);
    return parsed;
}

// A contract-compliant authority tree mirroring the real publisher's
// postconditions: 0o700 directories, 0o444 STORE, 0o400 package artifacts.
function buildCompliantAuthority(root, { transactionId = `tx_${'a'.repeat(64)}` } = {}) {
    makeDirectory(root, 0o700);
    makeDirectory(path.join(root, '.staging'), 0o700);
    makeDirectory(path.join(root, 'committed'), 0o700);
    makeFile(path.join(root, 'STORE.json'), '{}', 0o444);
    makeFile(path.join(root, 'allocation.authority.json'), '{}', 0o444);
    const txPath = path.join(root, 'committed', transactionId);
    makeDirectory(txPath, 0o700);
    for (const name of PACKAGE_FILES) makeFile(path.join(txPath, name), `${name}-bytes`, 0o400);
    return txPath;
}

function evaluate(root, overrides = {}) {
    return contract.evaluateRuntimeFilesystemContract({
        runtimeIdentity: RUNTIME,
        authorityRoot: root,
        allocationArtifactPath: path.join(root, 'allocation.authority.json'),
        ...overrides,
    });
}

function codes(report) {
    return report.findings.filter(item => item.severity === 'VIOLATION').map(item => item.code);
}

// ---------------------------------------------------------------------------
// 0. the suite proves the boundary as an unprivileged identity
// ---------------------------------------------------------------------------

test('0. the kernel-enforced assertions run as an unprivileged identity', () => {
    // Guards the re-exec above: if the drop ever silently stops happening the
    // rest of this file would still "pass" as root while proving nothing.
    assert.notEqual(process.getuid(), 0, 'the permission contract must be proved by an unprivileged identity, never by root');
    assert.equal(RUNTIME.uid, process.getuid());
    assert.equal(RUNTIME.gid, process.getgid());
    assert.ok(RUNTIME.groups.length > 0, 'a governed tree cannot be owned by an identity that has no group at all');
});

// ---------------------------------------------------------------------------
// 1. valid runtime cold-load contract
// ---------------------------------------------------------------------------

test('1. a publisher-shaped authority tree satisfies the runtime permission contract', t => {
    const root = tempRoot('compliant');
    t.after(() => cleanup(root));
    buildCompliantAuthority(root);
    const report = evaluate(root);
    assert.equal(report.status, 'COMPLIANT');
    assert.equal(report.violation_count, 0);
    assert.equal(report.production_mutation_performed, false);
    assert.equal(report.mutating_capability_present, false);
    assert.ok(report.surfaces.length >= PACKAGE_FILES.length + 4);
    const separation = report.read_write_separation;
    assert.ok(separation.immutable_historical_read_surface.length > 0);
    assert.ok(separation.active_runtime_write_surface.length > 0);
    assert.ok(separation.immutable_historical_read_surface.every(entry => !entry.includes('.staging')));
});

test('1b. the contract document is machine-readable and separates the two surfaces', () => {
    const document = contract.describeContract();
    assert.equal(document.schema_version, contract.CONTRACT_SCHEMA_VERSION);
    assert.equal(document.identity_rule.mechanism, 'IDENTITY_EQUALITY');
    assert.deepEqual([...document.immutable_package_file_set], [...PACKAGE_FILES]);
    assert.ok(document.surfaces.every(entry => typeof entry.exact_mode === 'number'));
    assert.ok(document.surfaces.some(entry => entry.classification === 'IMMUTABLE_HISTORICAL_READ_SURFACE'));
    assert.ok(document.surfaces.some(entry => entry.classification === 'ACTIVE_RUNTIME_WRITE_SURFACE'));
    assert.ok(document.identity_rule.rejected_mechanisms.some(entry => entry.includes('ACL')));
});

// ---------------------------------------------------------------------------
// 2. root-owned 0400 historical package inaccessible to the runtime identity
// ---------------------------------------------------------------------------

test('2. a foreign-owned 0400 package is classified unreadable to the runtime identity', t => {
    const root = tempRoot('foreign-owner');
    t.after(() => cleanup(root));
    const txPath = buildCompliantAuthority(root);
    // The real Blocker #2 shape: owner-only modes owned by uid 0 while the
    // runtime identity is unprivileged.
    const report = evaluate(root, { runtimeIdentity: FOREIGN });
    assert.equal(report.status, 'NONCOMPLIANT_REPAIRABLE');
    assert.ok(codes(report).includes('UNEXPECTED_IDENTITY_RELATION'));
    assert.ok(codes(report).includes('UNREADABLE_BY_RUNTIME'));
    const packageFile = report.surfaces.find(entry => entry.spec.path === path.join(txPath, 'manifest.json'));
    assert.deepEqual([...packageFile.access.missing], ['READ']);
    assert.equal(packageFile.observation.mode, 0o400);
    assert.equal(packageFile.compliant, false);
    const packageDirectory = report.surfaces.find(entry => entry.spec.path === txPath);
    assert.ok(packageDirectory.access.missing.includes('DIRECTORY_TRAVERSE'));
});

test('2b. the kernel really denies the analogous owner-class read the model predicts', t => {
    const root = tempRoot('kernel-denial');
    t.after(() => cleanup(root));
    const target = path.join(root, 'owner-only.json');
    makeFile(target, 'governed-bytes', 0o000);
    // The process IS the owner and still cannot read its own 0o000 file: this
    // is real DAC enforcement, not a modelled prediction.
    let observed = null;
    try {
        fs.readFileSync(target);
    } catch (error) {
        observed = error.code;
    }
    assert.equal(observed, 'EACCES');
    const missing = contract.predictRuntimeAccess(contract.observeObject(target), RUNTIME, ['READ']).missing;
    assert.deepEqual([...missing], ['READ']);
});

// ---------------------------------------------------------------------------
// 3. repaired metadata allows read without content mutation
// 10. package bytes/hash unchanged across metadata-only remediation
// ---------------------------------------------------------------------------

test('3+10. a metadata-only repair restores readability and leaves bytes identical', t => {
    const root = tempRoot('repair');
    t.after(() => cleanup(root));
    const txPath = buildCompliantAuthority(root);
    const target = path.join(txPath, 'manifest.json');
    const bytesBefore = fs.readFileSync(target);
    const hashBefore = contract.sha256OfReadableFile(target);

    // Simulate the damaged metadata state, then repair ONLY the mode.  This is
    // the exact bounded operation Phase B is allowed to perform.
    fs.chmodSync(target, 0o000);
    assert.equal(contract.sha256OfReadableFile(target).status, 'NOT_READABLE');
    assert.ok(codes(evaluate(root)).includes('MODE_MISMATCH'));

    fs.chmodSync(target, 0o400); // owner-only repair of a file this identity owns
    const hashAfter = contract.sha256OfReadableFile(target);
    assert.equal(hashAfter.status, 'HASHED');
    assert.equal(hashAfter.sha256, hashBefore.sha256);
    assert.deepEqual(fs.readFileSync(target), bytesBefore);
    assert.equal(evaluate(root).status, 'COMPLIANT');
});

test('10b. the emitted plan is inert, forbids content writes and carries a rollback manifest', t => {
    const root = tempRoot('plan');
    t.after(() => cleanup(root));
    const txPath = buildCompliantAuthority(root);
    fs.chmodSync(path.join(txPath, 'COMMITTED'), 0o000);
    const report = evaluate(root);
    const plan = planner.buildRemediationPlan(report);
    assert.equal(plan.applies_content_writes, false);
    assert.equal(plan.mutating, false);
    assert.equal(plan.execution_authorized, false);
    assert.equal(plan.execution_requires, 'SEPARATE_OWNER_AUTHORIZED_PHASE_B');
    assert.ok(plan.operations.length > 0);
    assert.ok(plan.operations.every(operation => operation.metadata_only && operation.content_impact === 'NONE'));
    assert.ok(plan.operations.every(operation => operation.content_bytes_must_be_identical === true));
    assert.ok(plan.operations.every(operation => operation.owner_authorization_required));
    // Every CHMOD must name the contract's own postcondition mode.
    for (const operation of plan.operations.filter(item => item.operation === 'CHMOD')) {
        const spec = report.surfaces.find(item => item.spec.path === operation.path).spec;
        assert.equal(operation.post.mode, spec.exact_mode, `${operation.path} must be set to its contract postcondition`);
        assert.equal(operation.post.mode_source, 'CONTRACT_POSTCONDITION');
    }
    assert.equal(plan.rollback.length, plan.operations.length);
    assert.ok(plan.rollback.every(entry => entry.content_impact === 'NONE'));
    // chown must precede chmod, and extended-ACL removal must come last.
    const ranks = plan.operations.map(operation => ({ CHOWN: 0, CHMOD: 1, REMOVE_EXTENDED_ACL: 2 }[operation.operation]));
    assert.deepEqual(ranks, [...ranks].sort((left, right) => left - right));
});

test('10c. several findings on one path collapse into one operation each', t => {
    const root = tempRoot('dedupe');
    t.after(() => cleanup(root));
    const txPath = buildCompliantAuthority(root);
    const target = path.join(txPath, 'metadata.json');
    fs.chmodSync(target, 0o600); // wrong mode AND writable AND unreadable to a foreign identity
    const plan = planner.buildRemediationPlan(evaluate(root, { runtimeIdentity: FOREIGN }));
    const onTarget = plan.operations.filter(operation => operation.path === target);
    assert.equal(onTarget.filter(operation => operation.operation === 'CHOWN').length, 1);
    assert.equal(onTarget.filter(operation => operation.operation === 'CHMOD').length, 1);
    assert.equal(onTarget.length, 2);
});

// ---------------------------------------------------------------------------
// 16. an extended ACL is only removed when it can be put back exactly
// ---------------------------------------------------------------------------
//
// REMOVE_EXTENDED_ACL deletes named entries that no chmod can restore: chmod
// only ever re-derives the mask from the group bits.  So the operation is only
// plannable when the current ACL was observed completely, and the plan has to
// carry it — otherwise the "rollback" would silently restore a tree with the
// named entries gone.

// The ACL the production authority actually carries: owner rwx, a named user
// with r-x, no group or other access, mask r-x.
const EXTENDED_ACL = Object.freeze({
    named_entries: Object.freeze([`user:${RUNTIME.uid}`]), named_user_perms: Object.freeze({ [String(RUNTIME.uid)]: 'r-x' }),
    named_group_perms: Object.freeze({}), owner: 'rwx', group: '---', other: '---', mask: 'r-x',
});

test('16. a removable extended ACL requires complete, restorable evidence', t => {
    const root = tempRoot('acl-evidence');
    t.after(() => cleanup(root));
    const target = buildCompliantAuthority(root);
    fs.chmodSync(target, 0o710); // the group bits are the mask, and the mask is wrong
    const finding = 'EXTENDED_ACL_PRESENT';

    // Nothing observed and nothing claimed: no ACL finding, so no removal.
    assert.equal(codes(evaluate(root)).includes(finding), false);
    assert.equal(planner.buildRemediationPlan(evaluate(root)).operations.some(operation => operation.operation === 'REMOVE_EXTENDED_ACL'), false);

    // An observation that names entries but cannot be replayed in full is
    // refused: a chmod-only rollback would leave those entries gone for good.
    const partial = evaluate(root, { aclObservations: { [target]: { available: true, named_entries: [`user:${RUNTIME.uid}`] } } });
    assert.ok(codes(partial).includes(finding));
    assert.equal(partial.acl_state[target].restorable, false);
    const incomplete = planner.buildRemediationPlan(partial);
    assert.equal(incomplete.operations.some(operation => operation.operation === 'REMOVE_EXTENDED_ACL'), false);
    const block = incomplete.blocked_operations.find(entry => entry.reason_code === 'ACL_ROLLBACK_EVIDENCE_INCOMPLETE');
    assert.equal(block.operation, 'REMOVE_EXTENDED_ACL');
    assert.equal(block.path, target);
    // The repairs a mode restore does undo stay plannable on the same path.
    assert.ok(incomplete.operations.some(operation => operation.path === target && operation.operation === 'CHMOD'));

    // With complete evidence the removal is planned and carries its exact inverse.
    const report = evaluate(root, { aclObservations: { [target]: { available: true, ...EXTENDED_ACL } } });
    assert.equal(report.acl_state[target].restorable, true);
    const plan = planner.buildRemediationPlan(report);
    const removal = plan.operations.find(operation => operation.operation === 'REMOVE_EXTENDED_ACL');
    assert.equal(removal.path, target);
    assert.equal(plan.blocked_operations.some(entry => entry.operation === 'REMOVE_EXTENDED_ACL'), false);
    assert.equal(removal.restore_acl.entries, `u::rwx,g::---,o::---,m::r-x,u:${RUNTIME.uid}:r-x`);
    const rollback = plan.rollback.find(entry => entry.operation === 'REMOVE_EXTENDED_ACL');
    assert.deepEqual(rollback.restore.acl.named_user_perms, { [String(RUNTIME.uid)]: 'r-x' });
    assert.equal(rollback.restore.acl.mask, 'r-x');
    // Rollback undoes the apply order, so the ACL is restored before the mode
    // that setfacl --set would otherwise re-derive.
    assert.deepEqual(plan.rollback.map(entry => entry.sequence), [...plan.rollback.map(entry => entry.sequence)].sort((left, right) => right - left));
});

test('16b. the recorded ACL reproduces the original access ACL through setfacl', t => {
    const root = tempRoot('acl-roundtrip');
    t.after(() => cleanup(root));
    const target = buildCompliantAuthority(root);
    // The acl package is not installed everywhere — the dev container omits it,
    // so the canonical container profile lands here.  Neither branch is a skip:
    // where the tools exist the recorded payload has to reproduce the ACL
    // through the real setfacl, and where they do not the contract has to say so
    // and refuse to plan a deletion it cannot undo.
    if (spawnSync('getfacl', ['--version']).error) {
        const unavailable = { available: false, reason: 'getfacl-not-installed' };
        const report = evaluate(root, { aclObservations: { [target]: unavailable } });
        assert.ok(report.findings.some(item => item.code === 'ACL_PROBE_UNAVAILABLE'));
        assert.equal(report.acl_state[target].restorable, false);
        assert.equal(planner.buildRemediationPlan(report).operations.some(operation => operation.operation === 'REMOVE_EXTENDED_ACL'), false);
        return;
    }
    const before = aclLines(target);
    setAcl(['-m', `u:${RUNTIME.uid}:r-x`], target); // a real named entry, applied by setfacl
    const expected = [...before, `user:${RUNTIME.uid}:r-x`, 'mask::r-x'].sort();
    assert.deepEqual(aclLines(target), expected);
    const report = evaluate(root, { aclObservations: { [target]: { available: true, ...structuredAcl(target) } } });
    const payload = planner.buildRemediationPlan(report).rollback.map(entry => entry.restore.acl).find(entry => entry !== null);
    assert.ok(payload, 'the plan must carry the observed ACL');
    // Delete the ACL, then replay the recorded payload: the access ACL has to
    // come back exactly, which is the only claim a rollback manifest may make.
    setAcl(['-b'], target);
    assert.notDeepEqual(aclLines(target), expected);
    setAcl(['--set', payload.entries], target);
    assert.deepEqual(aclLines(target), expected);
});

test('12e. the publisher guard refuses a privileged identity on both sides, not only the mixed case', t => {
    const root = tempRoot('guard-both-root');
    t.after(() => cleanup(root));
    buildCompliantAuthority(root);
    const ROOT_IDENTITY = Object.freeze({ uid: 0, gid: 0, groups: Object.freeze([]) });
    // The mixed case is the obvious one: a root container publishing into a
    // runtime-user-owned tree.
    assert.throws(
        () => contract.assertPublicationIdentity({ publisherIdentity: ROOT_IDENTITY, runtimeIdentity: RUNTIME, authorityRoot: root }),
        error => error.code === 'PUBLICATION_AS_PRIVILEGED_IDENTITY',
    );
    // The dangerous one is the both-root case, and it is reachable through the
    // binder's own derivation rather than through a caller mistake: the runtime
    // identity is taken from the authority anchor's owner, so a root process
    // facing a root-owned anchor gets uid 0 on both sides and used to verify
    // itself.  `/` is a genuine root-owned, non-group-writable directory, so the
    // derivation is exercised on real metadata instead of a declared value.
    const derived = contract.deriveRuntimeIdentityFromAuthority('/');
    assert.equal(derived.uid, 0, 'the filesystem root must be owned by uid 0 for this assertion to mean anything');
    assert.throws(
        () => contract.assertPublicationIdentity({ publisherIdentity: ROOT_IDENTITY, runtimeIdentity: derived, authorityRoot: '/' }),
        error => error.code === 'PUBLICATION_AS_PRIVILEGED_IDENTITY',
    );
    // Declaring the privileged runtime identity by hand is refused the same way,
    // so the guard cannot be walked around by passing it in explicitly.
    assert.throws(
        () => contract.assertPublicationIdentity({ publisherIdentity: ROOT_IDENTITY, runtimeIdentity: ROOT_IDENTITY, authorityRoot: root }),
        error => error.code === 'PUBLICATION_AS_PRIVILEGED_IDENTITY',
    );
    // The legitimate shape still verifies, so the new checks did not simply turn
    // the guard permanently red.
    assert.equal(contract.assertPublicationIdentity({ publisherIdentity: RUNTIME, runtimeIdentity: RUNTIME, authorityRoot: root }).status, 'PUBLICATION_IDENTITY_VERIFIED');
});

test('16c. a blocked ACL removal is counted in the plan status, not hidden behind READY', t => {
    const root = tempRoot('acl-status');
    t.after(() => cleanup(root));
    const target = buildCompliantAuthority(root);
    // Named entries are visible but cannot be replayed, so the removal is
    // blocked.  Mode and identity are already correct, which makes the ACL the
    // ONLY thing this tree needs — a status of NOT_REQUIRED would tell a caller
    // the authority is fully repairable when it is not.
    const incompleteEvidence = { [target]: { available: true, named_entries: [`user:${RUNTIME.uid}`] } };
    const aclOnly = planner.buildRemediationPlan(evaluate(root, { aclObservations: incompleteEvidence }));
    assert.equal(aclOnly.operations.length, 0);
    assert.ok(aclOnly.blocked_operations.some(entry => entry.operation === 'REMOVE_EXTENDED_ACL'));
    assert.equal(aclOnly.status, 'BLOCKED');

    // With a mode defect as well, part of the path is repairable and the ACL
    // removal is not: READY would hide the half that needs an Owner decision.
    fs.chmodSync(target, 0o710);
    const mixed = planner.buildRemediationPlan(evaluate(root, { aclObservations: incompleteEvidence }));
    assert.ok(mixed.operations.some(operation => operation.operation === 'CHMOD'));
    assert.ok(mixed.blocked_operations.some(entry => entry.operation === 'REMOVE_EXTENDED_ACL'));
    assert.equal(mixed.status, 'PARTIAL_BLOCKED');

    // Complete evidence unblocks the removal, and the same tree then reads READY,
    // so the status is still driven by what the plan can actually do.
    const restorable = planner.buildRemediationPlan(evaluate(root, { aclObservations: { [target]: { available: true, ...EXTENDED_ACL } } }));
    assert.equal(restorable.blocked_operations.some(entry => entry.operation === 'REMOVE_EXTENDED_ACL'), false);
    assert.equal(restorable.status, 'READY');
});

// ---------------------------------------------------------------------------
// 4. committed package stays non-writable to the runtime
// ---------------------------------------------------------------------------

test('4. immutable historical surfaces are never granted write access', t => {
    const root = tempRoot('immutable');
    t.after(() => cleanup(root));
    const txPath = buildCompliantAuthority(root);
    const report = evaluate(root);
    for (const entry of report.surfaces) {
        if (entry.spec.classification !== 'IMMUTABLE_HISTORICAL_READ_SURFACE') continue;
        assert.ok(!entry.spec.runtime_access.includes('WRITE'), `${entry.spec.label} must not require WRITE`);
        assert.ok(!entry.spec.runtime_access.includes('CREATE'), `${entry.spec.label} must not require CREATE`);
        // A regular file must carry no write bit at all; a directory keeps its
        // owner write bit (the publisher needs it to accept the rename) but must
        // never let the group or any other identity write.
        const writeBits = entry.spec.object_type === 'regular_file' ? 0o222 : 0o022;
        assert.equal(entry.observation.mode & writeBits, 0, `${entry.spec.label} grants a non-owner write bit`);
    }
    assert.equal(contract.observeObject(path.join(root, 'committed')).mode & 0o022, 0, 'committed root must not be group or world writable');
    // A write attempt against a 0o400 package artifact is genuinely refused.
    let refused = null;
    try {
        fs.appendFileSync(path.join(txPath, 'observations.jsonl'), 'x');
    } catch (error) {
        refused = error.code;
    }
    assert.equal(refused, 'EACCES');
});

// ---------------------------------------------------------------------------
// 5. staging/write surface remains capable of authorized publication
// 12. future newly published package receives compliant metadata
// ---------------------------------------------------------------------------

test('5. the staging surface still permits a real authorized publication sequence', t => {
    const root = tempRoot('staging');
    t.after(() => cleanup(root));
    buildCompliantAuthority(root);
    const staging = path.join(root, '.staging');
    const stagingSurface = evaluate(root).surfaces.find(entry => entry.spec.path === staging);
    assert.equal(stagingSurface.compliant, true);
    assert.deepEqual([...stagingSurface.access.missing], []);

    // Prove it rather than assume it: stage a package, then rename it in.
    const transactionId = `tx_${'b'.repeat(64)}`;
    const staged = path.join(staging, transactionId);
    makeDirectory(staged, 0o700);
    for (const name of PACKAGE_FILES) makeFile(path.join(staged, name), `${name}-bytes`, 0o400);
    fs.renameSync(staged, path.join(root, 'committed', transactionId));
    assert.equal(evaluate(root).status, 'COMPLIANT');
});

test('12. a newly published package inherits compliant metadata through the rename', t => {
    const root = tempRoot('future-publication');
    t.after(() => cleanup(root));
    buildCompliantAuthority(root);
    const transactionId = `tx_${'c'.repeat(64)}`;
    const staged = path.join(root, '.staging', transactionId);
    makeDirectory(staged, 0o700);
    for (const name of PACKAGE_FILES) makeFile(path.join(staged, name), `${name}-bytes`, 0o400);
    fs.renameSync(staged, path.join(root, 'committed', transactionId));

    const report = evaluate(root);
    assert.equal(report.status, 'COMPLIANT');
    const published = report.surfaces.filter(entry => entry.spec.path.includes(transactionId));
    assert.ok(published.length >= PACKAGE_FILES.length + 1);
    assert.ok(published.every(entry => entry.compliant));
    const future = contract.describeContract().future_publication;
    assert.equal(future.directory_mode, 0o700);
    assert.equal(future.package_file_mode, 0o400);
    assert.ok(future.umask_rule.includes('umask'));
});

test('12b. the publisher guard refuses a privileged publisher for an unprivileged authority', t => {
    const root = tempRoot('guard');
    t.after(() => cleanup(root));
    buildCompliantAuthority(root);
    const runtime = contract.deriveRuntimeIdentityFromAuthority(root);
    assert.equal(runtime.uid, RUNTIME.uid);
    // The exact real-world recurrence: a root-running container process
    // publishing into a runtime-user-owned tree.
    assert.throws(
        () => contract.assertPublicationIdentity({
            publisherIdentity: Object.freeze({ uid: 0, gid: 0, groups: Object.freeze([]) }),
            runtimeIdentity: runtime,
            authorityRoot: root,
        }),
        error => error.code === 'PUBLICATION_AS_PRIVILEGED_IDENTITY',
    );
    assert.throws(
        () => contract.assertPublicationIdentity({ publisherIdentity: FOREIGN, runtimeIdentity: runtime, authorityRoot: root }),
        error => error.code === 'PUBLICATION_IDENTITY_MISMATCH',
    );
    // An unresolvable runtime identity fails closed rather than guessing.
    assert.throws(
        () => contract.assertPublicationIdentity({ publisherIdentity: RUNTIME, authorityRoot: root }),
        error => error.code === 'PUBLICATION_IDENTITY_UNSPECIFIED',
    );
    const verified = contract.assertPublicationIdentity({ publisherIdentity: RUNTIME, runtimeIdentity: runtime, authorityRoot: root });
    assert.equal(verified.status, 'PUBLICATION_IDENTITY_VERIFIED');
});

test('12c. the publisher guard rejects an unsafe authority anchor', t => {
    const root = tempRoot('unsafe-anchor');
    t.after(() => cleanup(root));
    const shared = path.join(root, 'shared');
    makeDirectory(shared, 0o770); // group-writable anchor: another identity could swap the tree
    assert.throws(
        () => contract.assertPublicationIdentity({ publisherIdentity: RUNTIME, runtimeIdentity: RUNTIME, authorityRoot: shared }),
        error => error.code === 'PUBLICATION_IDENTITY_UNSAFE_ROOT',
    );
});

test('12d. the Stage D binder verifies publication identity before doing any work', t => {
    const root = tempRoot('binder-guard');
    t.after(() => cleanup(root));
    buildCompliantAuthority(root);
    const binder = require('../../../scripts/ops/stage_d_controlled_initialization');
    const verified = binder.verifyPublicationIdentity({ '--authority-root': root });
    assert.equal(verified.status, 'PUBLICATION_IDENTITY_VERIFIED');
    assert.equal(verified.runtime_identity.uid, RUNTIME.uid);
    // An authority root that does not exist yet still resolves to the nearest
    // runtime-owned ancestor, so the guard cannot be skipped by bootstrapping.
    const notYetCreated = path.join(root, 'committed', `tx_${'d'.repeat(64)}`);
    assert.equal(binder.verifyPublicationIdentity({ '--authority-root': notYetCreated }).status, 'PUBLICATION_IDENTITY_VERIFIED');
    const shared = path.join(root, 'shared');
    makeDirectory(shared, 0o770);
    assert.throws(() => binder.verifyPublicationIdentity({ '--authority-root': shared }), error => error.code === 'PUBLICATION_IDENTITY_UNSAFE_ROOT');
});

// ---------------------------------------------------------------------------
// 6. wrong group fails
// ---------------------------------------------------------------------------

test('6. a group mismatch between the artifact and the runtime identity is a violation', t => {
    const root = tempRoot('wrong-group');
    t.after(() => cleanup(root));
    const txPath = buildCompliantAuthority(root);
    const target = path.join(txPath, 'registry_delta.json');
    // An unprivileged owner may only chgrp to a group it belongs to.  The host
    // identity belongs to several groups; an identity dropped by spawn belongs
    // to exactly one, because libuv forces the supplementary set to [gid] when
    // a child is started under another uid.  Where a second group exists the
    // mismatch is real chgrp metadata; where it does not, the artifact keeps the
    // real group and the declared runtime gid carries the mismatch instead.
    // Every assertion below runs either way: this case is never skipped.
    const alternate = RUNTIME.groups.find(group => group !== RUNTIME.gid);
    const identity = alternate === undefined ? Object.freeze({ ...RUNTIME, gid: RUNTIME.gid + 1 }) : RUNTIME;
    if (alternate !== undefined) fs.chownSync(target, RUNTIME.uid, alternate); // real metadata change, unprivileged
    const artifactGid = alternate === undefined ? RUNTIME.gid : alternate;
    const observed = contract.observeObject(target);
    assert.equal(observed.gid, artifactGid);
    assert.notEqual(observed.gid, identity.gid);
    const report = evaluate(root, { runtimeIdentity: identity });
    assert.ok(codes(report).includes('UNEXPECTED_IDENTITY_RELATION'));
    assert.equal(report.status, 'NONCOMPLIANT_REPAIRABLE');
    const fix = planner.buildRemediationPlan(report).operations.find(operation => operation.path === target && operation.operation === 'CHOWN');
    assert.equal(fix.pre.gid, artifactGid);
    assert.equal(fix.post.gid, identity.gid);
});

// ---------------------------------------------------------------------------
// 7. missing directory execute/traverse permission fails
// ---------------------------------------------------------------------------

test('7. a directory without the execute bit genuinely blocks traversal', t => {
    const root = tempRoot('traverse');
    t.after(() => cleanup(root));
    const txPath = buildCompliantAuthority(root);
    fs.chmodSync(txPath, 0o600); // owner read/write, no traverse
    let observed = null;
    try {
        fs.readFileSync(path.join(txPath, 'manifest.json'));
    } catch (error) {
        observed = error.code;
    }
    assert.equal(observed, 'EACCES'); // real kernel refusal, owner class
    const report = evaluate(root);
    const packageDirectory = report.surfaces.find(entry => entry.spec.path === txPath);
    assert.deepEqual([...packageDirectory.access.missing], ['DIRECTORY_TRAVERSE']);
    assert.ok(codes(report).includes('UNTRAVERSABLE_DIRECTORY'));
});

// ---------------------------------------------------------------------------
// 8. world-writable ancestor fails
// ---------------------------------------------------------------------------

test('8. a world-writable ancestor fails closed, and the sticky bit is what saves /tmp', t => {
    const container = fs.mkdtempSync(path.join(os.tmpdir(), 'sd-perm-ancestor-'));
    t.after(() => fs.rmSync(container, { recursive: true, force: true, maxRetries: 3 }));
    const root = path.join(container, 'authority');
    buildCompliantAuthority(root);
    fs.chmodSync(container, 0o777); // no sticky bit
    const report = evaluate(root);
    assert.ok(codes(report).includes('WORLD_WRITABLE_ANCESTOR'));
    assert.equal(report.findings.find(item => item.code === 'WORLD_WRITABLE_ANCESTOR').path, container);
    // An ancestor lies outside the governed tree, so the plan refuses to
    // prescribe a mode change for it and escalates to the Owner instead.
    const plan = planner.buildRemediationPlan(report);
    assert.ok(plan.blocked_operations.some(entry => entry.reason_code === 'WORLD_WRITABLE_ANCESTOR'));
    assert.ok(!plan.operations.some(operation => operation.path === container));

    fs.chmodSync(container, 0o1777); // sticky: exactly the protection /tmp relies on
    const sticky = evaluate(root);
    assert.ok(!codes(sticky).includes('WORLD_WRITABLE_ANCESTOR'));
    assert.ok(sticky.findings.some(item => item.code === 'STICKY_WORLD_WRITABLE_ANCESTOR' && item.severity === 'ADVISORY'));
    assert.equal(sticky.status, 'COMPLIANT');
});

// ---------------------------------------------------------------------------
// 9. symlink substitution fails
// ---------------------------------------------------------------------------

test('9. a symlinked governed path is rejected, never followed, and never repaired', t => {
    const root = tempRoot('symlink');
    t.after(() => cleanup(root));
    const txPath = buildCompliantAuthority(root);
    const target = path.join(txPath, 'metadata.json');
    const decoy = path.join(path.dirname(root), 'decoy-bytes');
    makeFile(decoy, 'decoy', 0o400);
    fs.unlinkSync(target);
    fs.symlinkSync(decoy, target);
    const report = evaluate(root);
    assert.ok(codes(report).includes('SYMLINK_IN_GOVERNED_PATH'));
    assert.equal(contract.sha256OfReadableFile(target).status, 'NOT_REGULAR_FILE');
    const plan = planner.buildRemediationPlan(report);
    assert.ok(plan.blocked_operations.some(entry => entry.reason_code === 'SYMLINK_IN_GOVERNED_PATH'));
    assert.ok(!plan.operations.some(operation => operation.path === target));
});

test('9b. a symlinked or non-directory authority root is rejected before any observation', t => {
    const root = tempRoot('symlink-root');
    t.after(() => cleanup(root));
    const real = path.join(root, 'real');
    makeDirectory(real, 0o700);
    const link = path.join(root, 'link');
    fs.symlinkSync(real, link);
    assert.throws(() => contract.openGovernedRoot(link, 'authority root'), error => error.code === 'GOVERNED_ROOT_NOT_DIRECTORY');
    const file = path.join(root, 'not-a-directory');
    makeFile(file, 'x', 0o400);
    assert.throws(() => contract.openGovernedRoot(file, 'authority root'), error => error.code === 'GOVERNED_ROOT_NOT_DIRECTORY');
    assert.throws(() => contract.openGovernedRoot(path.join(root, 'absent'), 'authority root'), error => error.code === 'GOVERNED_ROOT_UNOBSERVABLE');
    const generation = contract.openGovernedRoot(real, 'authority root');
    assert.equal(generation.identity.ino, contract.observeObject(real).ino);
    contract.closeGovernedRoot(generation);
});

test('9c. a non-regular package artifact is rejected', t => {
    const root = tempRoot('nonregular');
    t.after(() => cleanup(root));
    const txPath = buildCompliantAuthority(root);
    const target = path.join(txPath, 'COMMITTED');
    fs.unlinkSync(target);
    makeDirectory(target, 0o400);
    const report = evaluate(root);
    assert.ok(codes(report).includes('NON_REGULAR_ARTIFACT'));
    assert.ok(planner.buildRemediationPlan(report).blocked_operations.some(entry => entry.reason_code === 'NON_REGULAR_ARTIFACT'));
});

// ---------------------------------------------------------------------------
// 15. an allocation authority outside the authority root is still governed
// ---------------------------------------------------------------------------

// The allocation authority is addressed by its own path and is allowed to live
// outside the authority root.  When it does, its parent chain is part of the
// governed path: a world-writable or symlinked ancestor lets the artifact be
// swapped wholesale, and no content hash computed afterwards can detect it.
// Each case below is a negative one — the tree is otherwise fully compliant, so
// a COMPLIANT verdict would mean the allocation path was never examined.
test('15. a standalone allocation authority outside the authority root is still ancestry-checked', t => {
    const root = tempRoot('standalone-allocation');
    t.after(() => cleanup(root));
    buildCompliantAuthority(root);
    // A second, private container — so the only offending ancestor is the one
    // this test creates, never the shared /tmp sticky directory.
    const elsewhere = tempRoot('allocation-home');
    t.after(() => cleanup(elsewhere));
    const allocation = path.join(elsewhere, 'allocation.authority.json');
    makeFile(allocation, '{}', 0o444);

    // Control: a private chain is compliant, so the cases below isolate ancestry.
    const control = evaluate(root, { allocationArtifactPath: allocation });
    assert.equal(codes(control).filter(code => code.endsWith('_ANCESTOR')).length, 0);
    assert.equal(control.status, 'COMPLIANT');

    // A non-sticky world-writable parent is a violation, not an advisory.
    fs.chmodSync(elsewhere, 0o777);
    const worldWritable = evaluate(root, { allocationArtifactPath: allocation });
    assert.ok(codes(worldWritable).includes('WORLD_WRITABLE_ANCESTOR'));
    assert.notEqual(worldWritable.status, 'COMPLIANT');

    // A symlinked ancestor is rejected outright and never followed.
    fs.chmodSync(elsewhere, 0o700);
    const realParent = path.join(elsewhere, 'real');
    makeDirectory(realParent, 0o700);
    makeFile(path.join(realParent, 'allocation.authority.json'), '{}', 0o444);
    fs.symlinkSync(realParent, path.join(elsewhere, 'linked'));
    const viaSymlink = evaluate(root, { allocationArtifactPath: path.join(elsewhere, 'linked', 'allocation.authority.json') });
    assert.ok(codes(viaSymlink).includes('SYMLINK_IN_GOVERNED_PATH'));
    assert.notEqual(viaSymlink.status, 'COMPLIANT');
});

test('15b. a shared ancestor is classified once and never downgraded by a laxer target', t => {
    const root = tempRoot('shared-ancestor');
    t.after(() => cleanup(root));
    buildCompliantAuthority(root);
    // The allocation artifact sits inside the authority root, so both targets
    // reach the same ancestors.  tempRoot's container is one of them: making it
    // group writable exercises the dedup and the strictest-policy rule on a real
    // directory instead of on an empty finding set.
    const container = path.dirname(root);
    fs.chmodSync(container, 0o770);
    const allocation = path.join(root, 'allocation.authority.json');
    const hit = (report, severity) => report.findings.filter(item => item.code === 'GROUP_WRITABLE_ANCESTOR' && item.path === container && item.severity === severity);
    // Reporting it twice would be noise; reporting it only as an advisory,
    // because the laxer authority-root policy reached it first, would be a
    // downgrade — the allocation artifact and the root reach it equally.
    const lax = evaluate(root, { allocationArtifactPath: allocation });
    assert.equal(hit(lax, 'ADVISORY').length, 1, 'a shared ancestor must be classified exactly once');
    assert.equal(hit(lax, 'VIOLATION').length, 0);
    // The run-lock trust root demands a non-group-writable chain, so the same
    // directory has to escalate to a violation rather than stay an advisory.
    const runLockRoot = path.join(root, 'run-lock');
    makeDirectory(runLockRoot, 0o700);
    const strict = evaluate(root, { allocationArtifactPath: allocation, runLockTrustRoot: runLockRoot });
    assert.equal(hit(strict, 'VIOLATION').length, 1, 'the strictest policy must win for a shared ancestor');
    assert.equal(hit(strict, 'ADVISORY').length, 0, 'a path must never be both an advisory and a violation');
});

test('15c. the inspect CLI collects ACLs for a standalone allocation authority chain', t => {
    const root = tempRoot('allocation-acl');
    t.after(() => cleanup(root));
    buildCompliantAuthority(root);
    const elsewhere = tempRoot('allocation-acl-home');
    t.after(() => cleanup(elsewhere));
    const allocation = path.join(elsewhere, 'allocation.authority.json');
    makeFile(allocation, '{}', 0o444);
    const argv = [AUDIT_CLI, '--authority-root', root, '--allocation-authority', allocation, '--mode', 'audit', '--json'];
    const result = spawnSync(process.execPath, argv, { encoding: 'utf8' });
    assert.equal(result.status, 0, result.stderr);
    const report = JSON.parse(result.stdout);
    // The artifact and every one of its ancestors must have been probed, or the
    // planner downstream has no restorable ACL for a path it may repair.
    assert.ok(Object.prototype.hasOwnProperty.call(report.acl_state, allocation));
    for (const ancestor of contract.walkAncestry(allocation)) {
        assert.ok(Object.prototype.hasOwnProperty.call(report.acl_state, ancestor.path), `${ancestor.path} was never probed`);
    }
});

test('15d. the inspect CLI probes the whole governed ledger layout, not just the ledger root', t => {
    const root = tempRoot('ledger-acl');
    t.after(() => cleanup(root));
    buildCompliantAuthority(root);
    const ledger = buildLedger(path.dirname(root));
    const epoch = path.join(ledger, 'REQUEST_ACCOUNTING_EPOCH.json');
    const entry = path.join(ledger, 'entries', '000000000001.json');
    // The contract evaluates the epoch anchor and every entry file, so the probe
    // set has to cover them too.  Otherwise a ledger artifact whose mode is
    // compliant but which carries a named ACL is classified CLEAN, and its
    // removal would be planned with no rollback evidence at all.
    const evaluated = contract.collectLedgerSurfaces(ledger).map(surface => surface.target);
    assert.ok(evaluated.includes(epoch) && evaluated.includes(entry), 'this test assumes the contract evaluates the ledger layout');
    const run = mode => JSON.parse(spawnSync(process.execPath, [AUDIT_CLI, '--authority-root', root, '--ledger-root', ledger, '--mode', mode, '--json'], { encoding: 'utf8' }).stdout);
    const report = run('audit');
    for (const target of evaluated) {
        assert.ok(Object.prototype.hasOwnProperty.call(report.acl_state, target), `${target} was never probed`);
    }
    // The acl package is absent from the dev container, so the canonical
    // container profile lands in the first branch.  Neither branch is a skip:
    // without the tools the contract has to say so, and with them the CLI has to
    // actually detect and plan the removal.
    if (spawnSync('getfacl', ['--version']).error) {
        assert.equal(report.acl_state[entry].available, false);
        assert.ok(report.findings.some(item => item.code === 'ACL_PROBE_UNAVAILABLE'));
        return;
    }
    setAcl(['-m', `u:${RUNTIME.uid}:r--`], entry);
    const damaged = spawnSync(process.execPath, [AUDIT_CLI, '--authority-root', root, '--ledger-root', ledger, '--mode', 'plan', '--json'], { encoding: 'utf8' });
    const withAcl = JSON.parse(damaged.stdout);
    assert.equal(damaged.status, 3, 'a named ACL on a governed ledger file is a violation');
    assert.ok(withAcl.findings.some(item => item.code === 'EXTENDED_ACL_PRESENT' && item.path === entry));
    assert.equal(withAcl.acl_state[entry].restorable, true);
    assert.ok(withAcl.plan.operations.some(operation => operation.path === entry && operation.operation === 'REMOVE_EXTENDED_ACL'));
});

// ---------------------------------------------------------------------------
// 11. authority generation replacement fails
// ---------------------------------------------------------------------------

test('11. replacing the authority generation after inspection is detected', t => {
    const root = tempRoot('generation');
    t.after(() => cleanup(root));
    buildCompliantAuthority(root);
    const generation = contract.openGovernedRoot(root, 'authority root');
    try {
        assert.equal(evaluate(root, { generation }).status, 'COMPLIANT');
        // Real replacement: rename the pinned tree away and build a new one.
        const moved = `${root}.moved`;
        fs.renameSync(root, moved);
        buildCompliantAuthority(root);
        assert.notEqual(contract.observeObject(root).ino, generation.identity.ino);
        const report = evaluate(root, { generation });
        assert.ok(codes(report).includes('AUTHORITY_GENERATION_REPLACED'));
        const plan = planner.buildRemediationPlan(report);
        assert.ok(plan.blocked_operations.some(entry => entry.reason_code === 'AUTHORITY_GENERATION_REPLACED'));
        assert.equal(plan.status, 'BLOCKED');
        void moved;
    } finally {
        contract.closeGovernedRoot(generation);
    }
});

test('11b. an unexpected committed entry or a short file set is rejected', t => {
    const root = tempRoot('unexpected-entry');
    t.after(() => cleanup(root));
    const txPath = buildCompliantAuthority(root);
    makeDirectory(path.join(root, 'committed', 'not-a-transaction'), 0o700);
    assert.ok(codes(evaluate(root)).includes('UNEXPECTED_COMMITTED_ENTRY'));
    fs.unlinkSync(path.join(txPath, 'manifest.json'));
    const report = evaluate(root);
    assert.ok(codes(report).includes('UNEXPECTED_PACKAGE_FILE_SET'));
    const plan = planner.buildRemediationPlan(report);
    assert.ok(plan.blocked_operations.some(entry => entry.reason_code === 'UNEXPECTED_PACKAGE_FILE_SET'));
    assert.equal(plan.status, 'BLOCKED');
});

// ---------------------------------------------------------------------------
// 13. ordinary cold-load succeeds in a fresh process/identity boundary
// ---------------------------------------------------------------------------

function probe(reportExpression, root) {
    const script = `
        const contract = require(${JSON.stringify(CONTRACT_MODULE)});
        const path = require('node:path');
        const report = contract.evaluateRuntimeFilesystemContract({
            runtimeIdentity: ${reportExpression},
            authorityRoot: process.argv[1],
            allocationArtifactPath: path.join(process.argv[1], 'allocation.authority.json'),
        });
        process.stdout.write(JSON.stringify({
            status: report.status,
            violations: report.findings.filter(item => item.severity === 'VIOLATION').map(item => item.code),
        }));
    `;
    const result = spawnSync(process.execPath, ['-e', script, root], { encoding: 'utf8' });
    assert.equal(result.status, 0, result.stderr);
    return JSON.parse(result.stdout);
}

test('13. a fresh process boundary reproduces the verdict for both states', t => {
    const root = tempRoot('fresh-process');
    t.after(() => cleanup(root));
    buildCompliantAuthority(root);
    const clean = probe('{ uid: process.getuid(), gid: process.getgid(), groups: process.getgroups() }', root);
    assert.equal(clean.status, 'COMPLIANT');
    assert.deepEqual(clean.violations, []);
    // The Blocker #2 shape, in a fresh process with a fresh module registry.
    const blocked = probe('{ uid: process.getuid() + 1, gid: process.getgid() + 1, groups: [] }', root);
    assert.equal(blocked.status, 'NONCOMPLIANT_REPAIRABLE');
    assert.ok(blocked.violations.includes('UNREADABLE_BY_RUNTIME'));
});

// ---------------------------------------------------------------------------
// 14. no privileged command is executed by default
// ---------------------------------------------------------------------------

// Comments and string literals both legitimately name the privileged commands
// this contract refuses to run, so the scan reads executable code only: block
// comments, line comments and quoted literals are removed.  The length guard
// keeps a mis-stripped file from silently passing the scan.
function codeOf(target) {
    const raw = fs.readFileSync(target, 'utf8');
    let out = '';
    let index = 0;
    while (index < raw.length) {
        const character = raw[index];
        const following = raw[index + 1];
        if (character === '/' && following === '*') {
            const end = raw.indexOf('*/', index + 2);
            index = end === -1 ? raw.length : end + 2;
            out += ' ';
            continue;
        }
        if (character === '/' && following === '/') {
            const end = raw.indexOf('\n', index);
            index = end === -1 ? raw.length : end;
            out += ' ';
            continue;
        }
        if (character === "'" || character === '"' || character === '`') {
            index += 1;
            while (index < raw.length && raw[index] !== character) index += raw[index] === '\\' ? 2 : 1;
            index += 1;
            out += 'LITERAL';
            continue;
        }
        out += character;
        index += 1;
    }
    assert.ok(out.length > raw.length * 0.3, `${path.basename(target)}: stripping was implausible`);
    return out;
}

// Call-shaped patterns: a name such as `chownRequired` legitimately describes
// the operation this contract only ever plans, so only invocations are banned.
const MUTATING_CALLS = [
    'writeFileSync', 'appendFileSync', 'writeFile(', 'appendFile(', 'mkdirSync', 'mkdir(', 'unlinkSync', 'unlink(',
    'rmSync', 'rmdirSync', 'rmdir(', 'renameSync', 'rename(', 'truncate', 'cpSync', 'copyFileSync', 'copyFile(',
    'createWriteStream', 'writeSync', 'utimesSync', 'linkSync', 'symlinkSync',
    'chmod(', 'chown(', 'lchown(', 'fchmod(', 'fchown(', 'chmodSync', 'chownSync', 'lchownSync', 'fchmodSync', 'fchownSync',
];

test('14. the Phase A implementation contains no mutating or privileged call', () => {
    for (const target of [CONTRACT_MODULE, PLAN_MODULE, AUDIT_CLI]) {
        const code = codeOf(target);
        const label = path.basename(target);
        for (const forbidden of MUTATING_CALLS) assert.ok(!code.includes(forbidden), `${label} must not call ${forbidden}`);
        assert.ok(!code.includes('setfacl'), `${label} must not reference setfacl`);
        assert.ok(!code.includes('fs.promises'), `${label} must not use the promise filesystem API`);
        // No computed member access: it would let a call evade the patterns above.
        assert.ok(!code.includes('fs['), `${label} must not use computed filesystem member access`);
    }
    // Neither the contract nor the planner may be able to spawn anything at all,
    // not even by loading the module (a require is a literal, so this reads raw).
    for (const target of [CONTRACT_MODULE, PLAN_MODULE]) {
        const raw = fs.readFileSync(target, 'utf8');
        assert.ok(!raw.includes('child_process'), `${path.basename(target)} must not load child_process`);
        assert.ok(!raw.includes('execFile'), `${path.basename(target)} must not exec`);
        assert.ok(!raw.includes('spawn'), `${path.basename(target)} must not spawn`);
    }
    // The one permitted exec is the read-only getfacl probe, and nothing else.
    const cliRaw = fs.readFileSync(AUDIT_CLI, 'utf8');
    assert.equal([...cliRaw.matchAll(/require\('node:child_process'\)/g)].length, 1, 'the CLI may load child_process exactly once');
    assert.deepEqual([...cliRaw.matchAll(/execFileSync\(\s*'([^']+)'/g)].map(match => match[1]), ['getfacl']);
});

// Instruments the real fs and child_process modules inside a fresh process,
// then runs the real CLI in plan mode with cold-load delegation.  Any attempted
// mutation or any exec other than the getfacl probe throws and is recorded.
test('14b. running the real CLI attempts no mutation and no privileged command', t => {
    const root = tempRoot('cli-instrumented');
    t.after(() => cleanup(root));
    buildCompliantAuthority(root);
    const instrumented = `
        const fs = require('node:fs');
        const cp = require('node:child_process');
        const calls = [];
        const WRITE = fs.constants.O_WRONLY | fs.constants.O_RDWR | fs.constants.O_CREAT | fs.constants.O_TRUNC | fs.constants.O_APPEND;
        const openSync = fs.openSync;
        fs.openSync = function (target, flags, ...rest) {
            const numeric = typeof flags === 'number' ? flags : (flags === 'r' ? 0 : -1);
            if (numeric >= 0 && (numeric & WRITE) === 0) return openSync.call(fs, target, flags, ...rest);
            calls.push('fs.openSync(write)');
            throw new Error('MUTATION_ATTEMPTED:openSync');
        };
        for (const name of ${JSON.stringify(MUTATING_CALLS.map(entry => entry.replace(/\($/, '')).concat(['renameSync', 'writeFile', 'openSync', 'createWriteStream']))}) {
            if (typeof fs[name] !== 'function' || name === 'openSync') continue;
            fs[name] = function () { calls.push('fs.' + name); throw new Error('MUTATION_ATTEMPTED:' + name); };
        }
        for (const name of ['execSync', 'execFileSync', 'spawnSync', 'exec', 'execFile', 'spawn', 'fork']) {
            if (typeof cp[name] !== 'function') continue;
            const original = cp[name];
            cp[name] = function (command, ...rest) {
                if (name === 'execFileSync' && String(command) === 'getfacl') return original.call(cp, command, ...rest);
                calls.push('child_process.' + name + ':' + String(command));
                throw new Error('PRIVILEGED_EXEC_ATTEMPTED:' + name);
            };
        }
        const cli = require(process.argv[1]);
        let payload;
        try {
            payload = { exitCode: cli.main(['--authority-root', process.argv[2], '--allocation-authority', process.argv[3], '--mode=plan', '--cold-load'], { stdout: { write() {} } }), calls };
        } catch (error) {
            payload = { error: String(error && error.message), calls };
        }
        process.stdout.write(JSON.stringify(payload));
    `;
    const result = spawnSync(process.execPath, ['-e', instrumented, AUDIT_CLI, root, path.join(root, 'allocation.authority.json')], { encoding: 'utf8' });
    assert.equal(result.status, 0, result.stderr);
    const payload = JSON.parse(result.stdout);
    assert.equal(payload.error, undefined, `the CLI attempted a forbidden operation: ${payload.error}`);
    assert.deepEqual(payload.calls, [], 'the CLI must attempt no mutation and no privileged command');
    assert.equal(payload.exitCode, 0, 'a compliant tree must exit COMPLIANT');
});

test('14c. the audit CLI mutates neither metadata nor content', t => {
    const root = tempRoot('cli-readonly');
    t.after(() => cleanup(root));
    buildCompliantAuthority(root);
    const snapshot = () => {
        const entries = {};
        const walk = target => {
            const stat = fs.lstatSync(target);
            entries[target] = {
                mode: stat.mode & 0o7777, uid: stat.uid, gid: stat.gid, ino: stat.ino, nlink: stat.nlink,
                sha256: stat.isFile() ? contract.sha256OfReadableFile(target).sha256 : null,
            };
            if (stat.isDirectory()) for (const name of fs.readdirSync(target).sort()) walk(path.join(target, name));
        };
        walk(root);
        return entries;
    };
    const ledger = buildLedger(path.dirname(root));
    const before = snapshot();
    const result = spawnSync(process.execPath, [
        AUDIT_CLI, '--authority-root', root, '--allocation-authority', path.join(root, 'allocation.authority.json'),
        '--ledger-root', ledger, '--mode=plan', '--cold-load', '--json',
    ], { encoding: 'utf8' });
    assert.equal(result.status, 0, result.stderr); // compliant tree
    const payload = JSON.parse(result.stdout);
    assert.equal(payload.production_mutation_performed, false);
    assert.equal(payload.mutating_capability_present, false);
    assert.equal(payload.production_permission_mutated, false);
    assert.equal(payload.stage_d_started, false);
    assert.equal(payload.provider_request_made, false);
    assert.equal(payload.plan.status, 'NOT_REQUIRED');
    assert.equal(payload.plan.execution_authorized, false);
    assert.deepEqual(snapshot(), before);
});

test('14d. the audit CLI rejects unknown flags, refuses an apply mode, and never mutates', t => {
    const root = tempRoot('cli-flags');
    t.after(() => cleanup(root));
    buildCompliantAuthority(root);
    const run = args => spawnSync(process.execPath, [AUDIT_CLI, ...args], { encoding: 'utf8' });
    assert.equal(run(['--authority-root', root, '--apply']).status, 1);
    assert.match(run(['--authority-root', root, '--apply']).stderr, /unknown or forbidden argument/);
    assert.equal(run(['--authority-root', root, '--mode=apply']).status, 1);
    assert.match(run(['--authority-root', root, '--mode=apply']).stderr, /--mode must be one of/);
    assert.equal(run(['--mode=audit']).status, 1);
    assert.match(run(['--mode=audit']).stderr, /--authority-root is required/);
    assert.equal(run(['--authority-root', root, '--runtime-uid', '-1']).status, 1);
    assert.match(run(['--authority-root', root, '--runtime-uid', '-1']).stderr, /non-negative integer/);
    // A damaged tree exits with the violation code and reports it, rather than repairing it.
    fs.chmodSync(path.join(root, 'STORE.json'), 0o600);
    const damaged = run(['--authority-root', root, '--json']);
    assert.equal(damaged.status, 3);
    assert.equal(JSON.parse(damaged.stdout).status, 'NONCOMPLIANT_REPAIRABLE');
    assert.equal(fs.lstatSync(path.join(root, 'STORE.json')).mode & 0o7777, 0o600);
});

// ---------------------------------------------------------------------------
// Fail-closed inputs
// ---------------------------------------------------------------------------

test('contract. an unknown or privileged runtime identity fails closed', () => {
    assert.throws(() => contract.evaluateRuntimeFilesystemContract({ runtimeIdentity: { uid: -1, gid: 0 }, authorityRoot: os.tmpdir() }), error => error.code === 'UNKNOWN_RUNTIME_IDENTITY');
    assert.throws(() => contract.evaluateRuntimeFilesystemContract({ runtimeIdentity: { uid: 'root', gid: 0 }, authorityRoot: os.tmpdir() }), error => error.code === 'UNKNOWN_RUNTIME_IDENTITY');
    assert.throws(() => contract.evaluateRuntimeFilesystemContract({ runtimeIdentity: { uid: 0, gid: 0, groups: [0, 'x'] }, authorityRoot: os.tmpdir() }), error => error.code === 'UNKNOWN_RUNTIME_IDENTITY');
    assert.throws(() => contract.evaluateRuntimeFilesystemContract({ runtimeIdentity: RUNTIME }), error => error.code === 'INVALID_AUDIT_INPUT');
    const root = tempRoot('privileged-runtime');
    try {
        buildCompliantAuthority(root);
        const report = contract.evaluateRuntimeFilesystemContract({ runtimeIdentity: { uid: 0, gid: 0, groups: [] }, authorityRoot: root });
        assert.ok(codes(report).includes('PRIVILEGED_RUNTIME_IDENTITY'));
        assert.equal(report.status, 'NONCOMPLIANT_BLOCKED');
        const plan = planner.buildRemediationPlan(report);
        assert.ok(plan.blocked_operations.some(entry => entry.reason_code === 'PRIVILEGED_RUNTIME_IDENTITY'));
        assert.equal(plan.status, 'PARTIAL_BLOCKED');
    } finally {
        cleanup(root);
    }
});

test('contract. an unrecognised violation is blocked rather than silently dropped', t => {
    const root = tempRoot('unknown-violation');
    t.after(() => cleanup(root));
    buildCompliantAuthority(root);
    const report = evaluate(root);
    const synthetic = Object.freeze({
        ...report,
        findings: Object.freeze([Object.freeze({
            code: 'SOME_FUTURE_CODE', severity: 'VIOLATION', surface_id: null, path: root,
            message: 'synthetic', auto_repairable: false, elevated_privilege_required: false, content_impact: 'NONE',
        })]),
    });
    const plan = planner.buildRemediationPlan(synthetic);
    assert.equal(plan.status, 'BLOCKED');
    assert.equal(plan.blocked_operations.length, 1);
    assert.equal(plan.blocked_operations[0].reason_code, 'SOME_FUTURE_CODE');
    assert.throws(() => planner.buildRemediationPlan(null), error => error.code === 'INVALID_PLAN_INPUT');
});
