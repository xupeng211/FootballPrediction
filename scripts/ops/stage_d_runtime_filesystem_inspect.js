#!/usr/bin/env node
'use strict';

// Stage D runtime filesystem permission audit / remediation planner (Blocker #2, Phase A).
//
// Lifecycle: permanent
// Owner: @xupeng211 (scripts/ops per .github/CODEOWNERS)
//
// READ-ONLY BY CONSTRUCTION.  This CLI has exactly two modes, `audit` and
// `plan`, and neither of them writes to the filesystem it inspects.  There is
// deliberately NO apply mode: the mutating half of Blocker #2 is a separate,
// separately authorized Phase B procedure, and an operator cannot reach it
// from this entrypoint by accident, by flag, or by environment variable.
//
// The audit itself opens nothing for writing, spawns no privileged command,
// and never escalates privilege.  When a governed path is unreadable it
// records that fact instead of trying to fix it.
//
// Content authority is delegated: with --cold-load the CLI calls the real
// transaction-v1 reader so STORE binding, allocation binding, manifest hashes,
// the exact committed file set and the authority state hash are verified by
// the existing implementation, never re-implemented here.

const fs = require('node:fs');
const path = require('node:path');
const { execFileSync } = require('node:child_process');
const contract = require('./stage_d_runtime_filesystem_permission_contract');
const planner = require('./stage_d_runtime_filesystem_remediation_plan');

const MODES = Object.freeze(['audit', 'plan']);
const FLAG_SPEC = Object.freeze({
    '--authority-root': 'value',
    '--allocation-authority': 'value',
    '--ledger-root': 'value',
    '--run-lock-trust-root': 'value',
    '--runtime-uid': 'value',
    '--runtime-gid': 'value',
    '--runtime-groups': 'value',
    '--mode': 'value',
    '--cold-load': 'boolean',
    '--json': 'boolean',
    '--help': 'boolean',
});

const EXIT = Object.freeze({ COMPLIANT: 0, USAGE: 1, BLOCKED: 2, VIOLATION: 3 });

// Accepts both `--flag value` and `--flag=value`; there is no positional form.
function splitToken(token) {
    const separator = token.indexOf('=');
    if (separator === -1) return Object.freeze({ flag: token, inline: undefined });
    return Object.freeze({ flag: token.slice(0, separator), inline: token.slice(separator + 1) });
}

function parseBooleanToken(flag, inline, values) {
    if (inline !== undefined) throw new Error(`${flag} does not take a value`);
    values[flag] = true;
    return 0;
}

function parseValueToken(flag, inline, argv, index, values) {
    const value = inline === undefined ? argv[index + 1] : inline;
    if (value === undefined || value === '' || (inline === undefined && value.startsWith('--'))) throw new Error(`${flag} requires a value`);
    values[flag] = value;
    return inline === undefined ? 1 : 0;
}

function parseArgs(argv) {
    const values = {};
    for (let index = 0; index < argv.length; index += 1) {
        const { flag, inline } = splitToken(argv[index]);
        const kind = FLAG_SPEC[flag];
        if (kind === undefined) throw new Error(`unknown or forbidden argument: ${argv[index]}`);
        if (Object.prototype.hasOwnProperty.call(values, flag)) throw new Error(`duplicate argument: ${flag}`);
        index += kind === 'boolean' ? parseBooleanToken(flag, inline, values) : parseValueToken(flag, inline, argv, index, values);
    }
    if (!values['--authority-root']) throw new Error('--authority-root is required');
    const mode = values['--mode'] || 'audit';
    if (!MODES.includes(mode)) throw new Error(`--mode must be one of: ${MODES.join(', ')}`);
    return Object.freeze({ ...values, '--mode': mode });
}

function parseNonNegativeInteger(raw, label) {
    if (raw === undefined) return undefined;
    if (!/^\d+$/.test(raw)) throw new Error(`${label} must be a non-negative integer`);
    return Number.parseInt(raw, 10);
}

function resolveRuntimeIdentity(args) {
    const identity = contract.processIdentity({ source: 'PROCESS' });
    const uid = parseNonNegativeInteger(args['--runtime-uid'], '--runtime-uid');
    const gid = parseNonNegativeInteger(args['--runtime-gid'], '--runtime-gid');
    const groups = args['--runtime-groups'] === undefined
        ? identity.groups
        : Object.freeze(args['--runtime-groups'].split(',').filter(Boolean).map(entry => parseNonNegativeInteger(entry.trim(), '--runtime-groups')));
    return Object.freeze({
        uid: uid === undefined ? identity.uid : uid,
        gid: gid === undefined ? identity.gid : gid,
        groups,
        source: uid === undefined && gid === undefined ? 'PROCESS' : 'EXPLICIT',
    });
}

// ---------------------------------------------------------------------------
// Extended ACL probe.  Policy is applied from the group-class bits, which cap
// every named ACL entry, so this probe can only ever add information.  It has
// no effect on the least-privilege verdict.
// ---------------------------------------------------------------------------

// getfacl -n emits numeric qualifiers, which lets the access model apply the
// ACL to the declared runtime identity without a name lookup.
function probeAcl(target) {
    let output;
    try {
        output = execFileSync('getfacl', ['-n', '-p', '--absolute-names', target], { encoding: 'utf8', stdio: ['ignore', 'pipe', 'ignore'], timeout: 5000 });
    } catch (error) {
        return Object.freeze({ available: false, reason: error.code === 'ENOENT' ? 'getfacl-not-installed' : 'getfacl-failed' });
    }
    const named = [];
    const namedUserPerms = {};
    const namedGroupPerms = {};
    const defaultNamed = [];
    const defaultUserPerms = {};
    const defaultGroupPerms = {};
    const base = {};
    const defaultBase = {};
    // The access ACL describes this object; the default ACL describes every
    // object created below it.  They are recorded separately because they are
    // evidence about different things and only one of them can be replayed by
    // an access-ACL restore.
    const recordAccess = (field, qualifier, permission) => {
        if (qualifier && field === 'user') { named.push(`user:${qualifier}`); namedUserPerms[qualifier] = permission; return; }
        if (qualifier && field === 'group') { named.push(`group:${qualifier}`); namedGroupPerms[qualifier] = permission; return; }
        if (!qualifier) base[field] = permission;
    };
    const recordDefault = (field, qualifier, permission) => {
        if (qualifier) {
            defaultNamed.push(`${field}:${qualifier}`);
            (field === 'user' ? defaultUserPerms : defaultGroupPerms)[qualifier] = permission;
            return;
        }
        defaultBase[field] = permission;
    };
    for (const line of output.split('\n')) {
        // Anything from `#` on is annotation, not policy.  getfacl appends a
        // trailing `#effective:...` to every entry the mask limits — which is
        // exactly the state a publisher fchmod creates — and a parser that kept
        // it would record "r-x\t#effective:---" as the permission, mark the ACL
        // restorable and hand setfacl an argument it rejects.  The rollback
        // would then fail for the one repair that cannot be undone any other
        // way.  Leading `# file:`/`# owner:` lines fall out for free.
        const trimmed = line.split('#')[0].trim();
        if (!trimmed || !trimmed.includes(':')) continue;
        const fields = trimmed.split(':');
        // `default:user::rwx` carries one field more than `user::rwx`: the
        // leading `default` is a scope, not a field.  Splitting to exactly three
        // and indexing [2] would read the default scope as an unknown field name
        // and drop the entry entirely — silently, and in the one direction that
        // matters, because an inherited default ACL is what governs the
        // permissions of packages that have not been published yet.
        const scoped = fields[0] === 'default';
        const [field, qualifier, permission] = scoped ? fields.slice(1) : fields;
        if (permission !== undefined) (scoped ? recordDefault : recordAccess)(field, qualifier, permission);
    }
    return Object.freeze({
        available: true,
        named_entries: Object.freeze(named.sort()),
        named_user_perms: Object.freeze(namedUserPerms),
        named_group_perms: Object.freeze(namedGroupPerms),
        owner: base.user === undefined ? null : base.user,
        group: base.group === undefined ? null : base.group,
        other: base.other === undefined ? null : base.other,
        mask: base.mask === undefined ? null : base.mask,
        default_present: defaultNamed.length > 0 || Object.keys(defaultBase).length > 0,
        default_entries: Object.freeze(defaultNamed.sort()),
        default_user_perms: Object.freeze(defaultUserPerms),
        default_group_perms: Object.freeze(defaultGroupPerms),
        default_base: Object.freeze(defaultBase),
    });
}

function collectAclObservations(paths) {
    const observations = {};
    for (const target of paths) observations[target] = probeAcl(target);
    return Object.freeze(observations);
}

function collectTargetPaths(targets) {
    const roots = [targets.authorityRoot, targets.ledgerRoot, targets.runLockTrustRoot].filter(Boolean);
    const paths = [];
    for (const root of roots) {
        paths.push(root, ...contract.walkAncestry(root).map(entry => entry.path));
        paths.push(path.join(root, 'committed'), path.join(root, 'STORE.json'), path.join(root, '.staging'));
        const committed = path.join(root, 'committed');
        const listing = safeReaddir(committed);
        for (const name of listing) {
            const txPath = path.join(committed, name);
            paths.push(txPath, ...safeReaddir(txPath).map(file => path.join(txPath, file)));
        }
    }
    // The ledger has a layout of its own — entries/, the epoch anchor and each
    // entry file — and the contract evaluates all of those as governed
    // surfaces.  They are enumerated by reusing the contract's own surface
    // collection rather than by re-deriving the layout here, so the probe set
    // cannot drift from the evaluated set: a ledger artifact whose mode is
    // compliant but which carries a named ACL is still observed, classified and
    // given rollback evidence.
    if (targets.ledgerRoot) {
        paths.push(...contract.collectLedgerSurfaces(targets.ledgerRoot).map(entry => entry.target));
    }
    // The allocation authority can sit outside the authority root, so its own
    // ancestry is governed too and its ACLs have to be observed to be classified.
    if (targets.allocationArtifactPath) {
        paths.push(targets.allocationArtifactPath, ...contract.walkAncestry(targets.allocationArtifactPath).map(entry => entry.path));
    }
    return Object.freeze([...new Set(paths)]);
}

function safeReaddir(target) {
    try {
        return fs.readdirSync(target).sort();
    } catch {
        return [];
    }
}

// ---------------------------------------------------------------------------
// Observed content manifest.  This records bytes; it never writes them.
//
// Coverage is exactly the immutable content the contract governs, so the
// manifest can be compared before and after a Phase B repair: STORE.json, the
// allocation authority, every committed package file, and the request
// accounting epoch anchor and entries.  Transient runtime state is deliberately
// excluded — `.staging` contents and the run-lock trust root change on their
// own, so hashing them would make the before/after comparison meaningless
// rather than stronger.
// ---------------------------------------------------------------------------

function collectContentHashes(targets) {
    const hashes = {};
    // sha256OfReadableFile preserves the unreadable state as a status rather
    // than dropping the entry, so an artifact the runtime cannot read is
    // visible in the manifest instead of absent from it.
    const record = target => { hashes[target] = contract.sha256OfReadableFile(target); };
    record(path.join(targets.authorityRoot, 'STORE.json'));
    if (targets.allocationArtifactPath) record(targets.allocationArtifactPath);
    const committed = path.join(targets.authorityRoot, 'committed');
    for (const name of safeReaddir(committed)) {
        const txPath = path.join(committed, name);
        for (const file of safeReaddir(txPath)) record(path.join(txPath, file));
    }
    // The ledger holds immutable content too, and enumerating it through the
    // contract's own surface collection keeps the manifest's coverage equal to
    // the evaluated surface set instead of drifting from it.
    if (targets.ledgerRoot) {
        for (const entry of contract.collectLedgerSurfaces(targets.ledgerRoot)) {
            if (entry.spec.object_type === 'regular_file') record(entry.target);
        }
    }
    return Object.freeze(hashes);
}

// ---------------------------------------------------------------------------
// Delegated content authority verification.
// ---------------------------------------------------------------------------

// The transaction reader runs inside this process, so the identity that
// actually performs the cold-load is this process's identity, not the declared
// runtime identity.  A success observed under some other identity — an operator
// running the audit as root, say — is not evidence that the runtime identity
// can cold-load, and reporting the two side by side would let exactly the
// failure this contract exists to detect pass as a success.  The result is
// therefore bound to the identity it was actually observed under, and a
// mismatch is reported as such rather than compensated for by privilege.
function coldLoadAuthority(targets, declaredRuntimeIdentity) {
    const { openMarketEvidenceAuthoritySnapshot } = require('../../src/infrastructure/market_evidence/authorityReader');
    const observed = contract.processIdentity({ source: 'PROCESS' });
    const declared = declaredRuntimeIdentity || null;
    const binds = declared !== null && observed.uid === declared.uid && observed.gid === declared.gid;
    let read;
    try {
        const snapshot = openMarketEvidenceAuthoritySnapshot({
            storeRoot: targets.authorityRoot,
            allocationArtifactPath: targets.allocationArtifactPath,
        });
        read = Object.freeze({
            read_status: 'SUCCEEDED',
            head_transaction_id: snapshot.head_transaction_id || null,
            authority_state_hash: snapshot.state_hash || null,
            observation_count: Array.isArray(snapshot.observations) ? snapshot.observations.length : null,
        });
    } catch (error) {
        read = Object.freeze({ read_status: 'FAILED', error_code: error.code || 'AUTHORITY_READ_FAILED', message: error.message });
    }
    const succeeded = read.read_status === 'SUCCEEDED';
    return Object.freeze({
        ...read,
        status: succeeded ? (binds ? 'COLD_LOAD_SUCCEEDED' : 'COLD_LOAD_SUCCEEDED_UNDER_OTHER_IDENTITY') : 'COLD_LOAD_FAILED',
        observed_identity: Object.freeze({ uid: observed.uid, gid: observed.gid }),
        declared_runtime_identity: declared === null ? null : Object.freeze({ uid: declared.uid, gid: declared.gid }),
        binds_declared_runtime_identity: binds,
        // The single field a Phase B post-repair proof may rely on: the read
        // both succeeded and was performed as the identity that must cold-load
        // the authority in production.
        evidence_for_declared_runtime_identity: succeeded && binds,
        identity_note: binds
            ? 'the cold-load ran as the declared runtime identity'
            : `the cold-load ran as ${observed.uid}:${observed.gid}, which is not the declared runtime identity ${declared === null ? 'unknown' : `${declared.uid}:${declared.gid}`}; this result must not be used as proof that the declared identity can cold-load, and the fix is to run the audit as that identity, never to escalate`,
    });
}

function readStoreAndAllocationHashes(targets) {
    const store = contract.sha256OfReadableFile(path.join(targets.authorityRoot, 'STORE.json'));
    const allocation = targets.allocationArtifactPath ? contract.sha256OfReadableFile(targets.allocationArtifactPath) : Object.freeze({ status: 'NOT_PROVIDED' });
    return Object.freeze({ store_sha256: store, allocation_authority_sha256: allocation });
}

function summarize(report, plan, coldLoad, artifactHashes, generationRecheck = null) {
    return Object.freeze({
        schema_version: 'footballprediction-stage-d-runtime-filesystem-audit-result/v1',
        mode: plan ? 'plan' : 'audit',
        status: report.status,
        plan_status: plan ? plan.status : null,
        runtime_identity: report.runtime_identity,
        authority_root: report.targets.authorityRoot,
        violation_count: report.violation_count,
        advisory_count: report.advisory_count,
        ambiguous_finding_count: report.ambiguous_finding_count,
        findings: report.findings.map(item => Object.freeze({
            code: item.code, severity: item.severity, path: item.path, message: item.message,
            auto_repairable: item.auto_repairable, elevated_privilege_required: item.elevated_privilege_required,
        })),
        planned_operation_count: plan ? plan.operations.length : 0,
        blocked_operation_count: plan ? plan.blocked_operations.length : 0,
        artifact_hashes: artifactHashes,
        // The full governed content manifest, not just the two headline hashes:
        // a Phase B repair is only allowed to change metadata, and comparing
        // this manifest before and after is how CONTENT_BYTES_BEFORE ==
        // CONTENT_BYTES_AFTER is actually checked for every artifact rather
        // than asserted for the authority as a whole.
        content_hashes: report.content_hashes,
        cold_load: coldLoad,
        // The observed ACL of every probed path, in the exact form a Phase B
        // rollback has to replay.  Without it the report would record that an
        // extended ACL exists but not what it was, and a removal could never be
        // undone.
        acl_state: report.acl_state,
        read_write_separation: report.read_write_separation,
        production_mutation_performed: report.production_mutation_performed,
        mutating_capability_present: report.mutating_capability_present,
        // The pinned authority generation and the re-observation taken after the
        // plan was built.  A replacement detected here is reported instead of a
        // plan, because every conclusion in the report describes the object that
        // was pinned, not the one now sitting at the path.
        authority_generation: report.authority_generation,
        generation_recheck: generationRecheck,
        production_permission_mutated: false,
        stage_d_started: false,
        provider_request_made: false,
    });
}

function helpText() {
    return [
        'Stage D runtime filesystem permission audit / remediation planner (read-only).',
        'node scripts/ops/stage_d_runtime_filesystem_inspect.js --authority-root <path> [options]',
        '',
        '  --authority-root <path>         transaction authority root (required)',
        '  --allocation-authority <path>   allocation authority artifact',
        '  --ledger-root <path>            request-accounting ledger root',
        '  --run-lock-trust-root <path>    run-lock runtime trust root',
        '  --runtime-uid <n>               declared cold-loading runtime uid',
        '  --runtime-gid <n>               declared cold-loading runtime gid',
        '  --runtime-groups <n,n>          declared supplementary groups',
        '  --mode <audit|plan>             default: audit',
        '  --cold-load                     delegate content authority to the transaction-v1 reader',
        '  --json                          emit the machine-readable report',
        '',
        '--cold-load records the identity the read actually ran under and only',
        'asserts evidence for the declared runtime identity when the two are equal,',
        'so run the audit as the runtime identity; privilege is never escalated.',
        '',
        'There is no apply mode.  This entrypoint never mutates ownership, mode, ACLs or content.',
    ].join('\n');
}

function exitCodeFor(report) {
    if (report.status === 'COMPLIANT') return EXIT.COMPLIANT;
    if (report.ambiguous_finding_count > 0) return EXIT.BLOCKED;
    return EXIT.VIOLATION;
}

function main(argv = process.argv.slice(2), { stdout = process.stdout } = {}) {
    const args = parseArgs(argv);
    if (args['--help']) {
        stdout.write(`${helpText()}\n`);
        return EXIT.COMPLIANT;
    }
    const targets = Object.freeze({
        authorityRoot: path.resolve(args['--authority-root']),
        allocationArtifactPath: args['--allocation-authority'] ? path.resolve(args['--allocation-authority']) : null,
        ledgerRoot: args['--ledger-root'] ? path.resolve(args['--ledger-root']) : null,
        runLockTrustRoot: args['--run-lock-trust-root'] ? path.resolve(args['--run-lock-trust-root']) : null,
    });
    // Pin the authority generation before anything is read.  The audit reads
    // ACLs, content hashes, metadata and the plan in separate phases, so without
    // a pinned identity a root replaced partway through would yield a report and
    // a plan that describe two different objects.
    const generation = contract.openGovernedRoot(targets.authorityRoot, 'the transaction authority root');
    try {
        const aclObservations = collectAclObservations(collectTargetPaths(targets));
        const runtimeIdentity = resolveRuntimeIdentity(args);
        const report = contract.evaluateRuntimeFilesystemContract({
            runtimeIdentity,
            authorityRoot: targets.authorityRoot,
            allocationArtifactPath: targets.allocationArtifactPath,
            ledgerRoot: targets.ledgerRoot,
            runLockTrustRoot: targets.runLockTrustRoot,
            generation,
            aclObservations,
            contentHashes: collectContentHashes(targets),
        });
        const plan = args['--mode'] === 'plan' ? planner.buildRemediationPlan(report) : null;
        // Re-verify the pinned generation after the last read and before anything
        // is emitted.  A replacement here invalidates the whole result, so the
        // audit fails closed instead of printing a plan built from a tree that is
        // no longer the one it inspected.
        const drift = contract.generationDrift(generation);
        if (drift) throw Object.assign(new Error(drift.message), { code: drift.code });
        // The plan is the point of plan mode, so it is always emitted there;
        // --json additionally returns the full per-surface observation detail.
        const result = summarize(report, plan, args['--cold-load'] ? coldLoadAuthority(targets, runtimeIdentity) : null,
            readStoreAndAllocationHashes(targets), Object.freeze({ replaced: false, pinned: report.authority_generation }));
        const detail = args['--json'] ? { surfaces: report.surfaces, authority_generation: report.authority_generation } : {};
        stdout.write(`${JSON.stringify({ ...result, ...detail, plan }, null, 2)}\n`);
        return exitCodeFor(report);
    } finally {
        contract.closeGovernedRoot(generation);
    }
}

if (require.main === module) {
    try {
        process.exitCode = main();
    } catch (error) {
        process.stderr.write(`STAGE_D_FILESYSTEM_AUDIT_FAILED=${error.code || 'AUDIT_FAILED'}\n${error.message}\n`);
        process.exitCode = EXIT.USAGE;
    }
}

module.exports = { parseArgs, resolveRuntimeIdentity, probeAcl, collectAclObservations, collectTargetPaths, collectContentHashes, coldLoadAuthority, summarize, exitCodeFor, helpText, main, EXIT };
