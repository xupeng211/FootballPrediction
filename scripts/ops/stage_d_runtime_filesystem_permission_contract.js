#!/usr/bin/env node
'use strict';

// Stage D runtime filesystem permission contract (Blocker #2, Phase A).
//
// Lifecycle: permanent
// Owner: @xupeng211 (scripts/ops per .github/CODEOWNERS)
//
// This module is INSPECT / CLASSIFY / PLAN only.  It never mutates the
// filesystem, never shells out, never escalates privilege and never starts
// Stage D.  Every classification is derived from real lstat/readdir
// observations of the governed paths, compared against the exact metadata
// postconditions that the existing Stage C/D publication code already
// produces.
//
// It deliberately does NOT verify authority content.  Content authority stays
// with transactionStore.js and authorityReader.js; a metadata repair can never
// substitute for authority verification.  The audit CLI reuses those modules
// for the content dimension and this module only ever reports metadata plus
// observed content hashes.
//
// Why owner identity equality is the required mechanism rather than an ACL:
// atomicPublisher.safeWrite() and transactionStore.writeExclusive() both call
// fchmod()/chmod() with an owner-only mode (0o400 / 0o444).  On POSIX, chmod
// re-derives the ACL mask from the group permission bits, so any named-user
// ACL entry is collapsed to "---" the moment a package is published.  A named
// ACL therefore cannot survive the publisher and is structurally unable to
// make a committed package cold-loadable.  The only mechanism that the
// publisher's own postconditions support is identity equality between the
// publishing identity, the authority owner and the cold-loading runtime user.

const fs = require('node:fs');
const path = require('node:path');
const crypto = require('node:crypto');
const { TRANSACTION_FILES } = require('../../src/infrastructure/market_evidence/transactionContract');

const CONTRACT_SCHEMA_VERSION = 'footballprediction-stage-d-runtime-filesystem-permission-contract/v1';
const REPORT_SCHEMA_VERSION = 'footballprediction-stage-d-runtime-filesystem-permission-audit/v1';
const CONTRACT_VERSION = 'stage-d-runtime-filesystem-permission/v1';

// Access classes are modelled separately because a single "read" notion cannot
// express directory traversal, the rename-into-committed transition, or fsync.
const ACCESS = Object.freeze(Object.fromEntries([
    'READ', 'DIRECTORY_TRAVERSE', 'CREATE', 'WRITE', 'RENAME', 'FSYNC', 'CHMOD', 'DELETE', 'NONE',
].map(name => [name, name])));

const SURFACE = Object.freeze(Object.fromEntries([
    'TRANSACTION_AUTHORITY_ROOT', 'STORE_ARTIFACT', 'COMMITTED_ROOT', 'STAGING_ROOT',
    'TRANSACTION_PACKAGE_DIRECTORY', 'IMMUTABLE_PACKAGE_FILE', 'ALLOCATION_AUTHORITY_ARTIFACT',
    'REQUEST_ACCOUNTING_ROOT', 'REQUEST_ACCOUNTING_ENTRIES', 'REQUEST_ACCOUNTING_EPOCH',
    'REQUEST_ACCOUNTING_ENTRY_FILE', 'RUN_LOCK_TRUST_ROOT', 'FUTURE_PUBLISHED_PACKAGE',
].map(name => [name, name])));

const GOVERNED_SURFACE = 'GOVERNED_SURFACE';
const IMMUTABLE_HISTORICAL_READ_SURFACE = 'IMMUTABLE_HISTORICAL_READ_SURFACE';
const ACTIVE_RUNTIME_WRITE_SURFACE = 'ACTIVE_RUNTIME_WRITE_SURFACE';
const FUTURE_PUBLICATION_SURFACE = 'FUTURE_PUBLICATION_SURFACE';

const SEVERITY = Object.freeze({ VIOLATION: 'VIOLATION', ADVISORY: 'ADVISORY' });

const STORE_FILE = 'STORE.json';
const EPOCH_FILE = 'REQUEST_ACCOUNTING_EPOCH.json';
const ENTRY_DIRECTORY = 'entries';
const STAGING_DIRECTORY = '.staging';
const COMMITTED_DIRECTORY = 'committed';
const TX_DIRECTORY = /^tx_[a-f0-9]{64}$/;
const LEDGER_ENTRY_FILE = /^\d{12}\.json$/;
// The exact shape of an access-ACL permission field, and therefore the only
// shape that may be emitted as a `setfacl --set` argument.
const ACL_PERMISSION = /^[r-][w-][x-]$/;

const orNull = value => (value === undefined ? null : value);

// One ACL scope is replayable only when every triad in it is exact.  The access
// scope and the default scope are checked by the same rule because a malformed
// `setfacl --set` argument is malformed the same way in both.
function aclScopeReplayable(base, named) {
    const exact = value => typeof value === 'string' && ACL_PERMISSION.test(value);
    return Object.values(base).every(exact) && Object.values(named).every(exact);
}

const RESERVED_NAMES = Object.freeze([STORE_FILE, STAGING_DIRECTORY, COMMITTED_DIRECTORY]);

function contractError(code, message) {
    const error = new Error(message);
    error.code = code;
    return error;
}

function assertRuntimeIdentity(runtimeIdentity) {
    if (runtimeIdentity === null || typeof runtimeIdentity !== 'object') {
        throw contractError('UNKNOWN_RUNTIME_IDENTITY', 'an explicit runtime identity is required');
    }
    const { uid, gid, groups } = runtimeIdentity;
    for (const [label, value] of [['uid', uid], ['gid', gid]]) {
        if (!Number.isInteger(value) || value < 0) throw contractError('UNKNOWN_RUNTIME_IDENTITY', `runtime identity ${label} must be a non-negative integer`);
    }
    if (groups !== undefined && (!Array.isArray(groups) || groups.some(group => !Number.isInteger(group) || group < 0))) {
        throw contractError('UNKNOWN_RUNTIME_IDENTITY', 'runtime identity groups must be non-negative integers');
    }
    return Object.freeze({ uid, gid, groups: Object.freeze([...(groups || [])]), source: runtimeIdentity.source || 'EXPLICIT' });
}

// ---------------------------------------------------------------------------
// Surface specification.  Exact modes are the postconditions the existing
// publisher already produces; they are not aspirational values.
// ---------------------------------------------------------------------------

function directorySpec({ surfaceId, label, classification, runtimeAccess, relative }) {
    return Object.freeze({
        surface_id: surfaceId, label, classification, object_type: 'directory',
        relative, exact_mode: 0o700, immutable_content: false,
        runtime_access: Object.freeze(runtimeAccess),
    });
}

function fileSpec({ surfaceId, label, classification, exactMode, relative, immutableContent = true, runtimeAccess = [ACCESS.READ] }) {
    return Object.freeze({
        surface_id: surfaceId, label, classification, object_type: 'regular_file',
        relative, exact_mode: exactMode, immutable_content: immutableContent,
        runtime_access: Object.freeze(runtimeAccess),
    });
}

const HISTORICAL_READ_DIRECTORY = Object.freeze([ACCESS.DIRECTORY_TRAVERSE, ACCESS.READ]);
const LEDGER_DIRECTORY_ACCESS = Object.freeze([ACCESS.DIRECTORY_TRAVERSE, ACCESS.READ, ACCESS.WRITE, ACCESS.CREATE, ACCESS.FSYNC]);

const AUTHORITY_ROOT_DIRECTORY_SPEC = directorySpec({
    surfaceId: SURFACE.TRANSACTION_AUTHORITY_ROOT, label: 'transaction authority root', relative: '',
    classification: IMMUTABLE_HISTORICAL_READ_SURFACE, runtimeAccess: HISTORICAL_READ_DIRECTORY,
});
const STORE_ARTIFACT_SPEC = fileSpec({
    surfaceId: SURFACE.STORE_ARTIFACT, label: 'STORE.json', relative: STORE_FILE, exactMode: 0o444,
    classification: IMMUTABLE_HISTORICAL_READ_SURFACE,
});
const COMMITTED_ROOT_SPEC = directorySpec({
    surfaceId: SURFACE.COMMITTED_ROOT, label: 'committed root', relative: COMMITTED_DIRECTORY,
    classification: GOVERNED_SURFACE,
    runtimeAccess: [ACCESS.DIRECTORY_TRAVERSE, ACCESS.READ, ACCESS.WRITE, ACCESS.FSYNC],
});
const STAGING_ROOT_SPEC = directorySpec({
    surfaceId: SURFACE.STAGING_ROOT, label: 'transaction staging root', relative: STAGING_DIRECTORY,
    classification: ACTIVE_RUNTIME_WRITE_SURFACE,
    runtimeAccess: [ACCESS.DIRECTORY_TRAVERSE, ACCESS.READ, ACCESS.WRITE, ACCESS.CREATE, ACCESS.DELETE, ACCESS.RENAME, ACCESS.FSYNC],
});
const PACKAGE_DIRECTORY_SPEC = directorySpec({
    surfaceId: SURFACE.TRANSACTION_PACKAGE_DIRECTORY, label: 'committed transaction package directory',
    relative: `${COMMITTED_DIRECTORY}/<transaction_id>`,
    classification: IMMUTABLE_HISTORICAL_READ_SURFACE, runtimeAccess: HISTORICAL_READ_DIRECTORY,
});
const PACKAGE_FILE_SPEC = fileSpec({
    surfaceId: SURFACE.IMMUTABLE_PACKAGE_FILE, label: 'immutable package artifact',
    relative: `${COMMITTED_DIRECTORY}/<transaction_id>/<artifact>`, exactMode: 0o400,
    classification: IMMUTABLE_HISTORICAL_READ_SURFACE,
});
const ALLOCATION_ARTIFACT_SPEC = fileSpec({
    surfaceId: SURFACE.ALLOCATION_AUTHORITY_ARTIFACT, label: 'allocation authority artifact',
    relative: '<allocation-authority>', exactMode: 0o444,
    classification: IMMUTABLE_HISTORICAL_READ_SURFACE,
});
const LEDGER_ROOT_SPEC = directorySpec({
    surfaceId: SURFACE.REQUEST_ACCOUNTING_ROOT, label: 'request accounting ledger root',
    relative: '<ledger-root>', classification: ACTIVE_RUNTIME_WRITE_SURFACE, runtimeAccess: LEDGER_DIRECTORY_ACCESS,
});
const LEDGER_ENTRIES_SPEC = directorySpec({
    surfaceId: SURFACE.REQUEST_ACCOUNTING_ENTRIES, label: 'request accounting entries directory',
    relative: `<ledger-root>/${ENTRY_DIRECTORY}`, classification: ACTIVE_RUNTIME_WRITE_SURFACE,
    runtimeAccess: LEDGER_DIRECTORY_ACCESS,
});
const LEDGER_EPOCH_SPEC = fileSpec({
    surfaceId: SURFACE.REQUEST_ACCOUNTING_EPOCH, label: 'request accounting epoch anchor',
    relative: `<ledger-root>/${EPOCH_FILE}`, exactMode: 0o400,
    classification: IMMUTABLE_HISTORICAL_READ_SURFACE,
});
const LEDGER_ENTRY_FILE_SPEC = fileSpec({
    surfaceId: SURFACE.REQUEST_ACCOUNTING_ENTRY_FILE, label: 'request accounting ledger entry',
    relative: `<ledger-root>/${ENTRY_DIRECTORY}/<sequence>.json`, exactMode: 0o400,
    classification: IMMUTABLE_HISTORICAL_READ_SURFACE,
});
const TRUST_ROOT_SPEC = directorySpec({
    surfaceId: SURFACE.RUN_LOCK_TRUST_ROOT, label: 'run-lock runtime trust root',
    relative: '<run-lock-trust-root>', classification: ACTIVE_RUNTIME_WRITE_SURFACE,
    runtimeAccess: [ACCESS.DIRECTORY_TRAVERSE, ACCESS.READ, ACCESS.WRITE, ACCESS.CREATE, ACCESS.DELETE, ACCESS.RENAME, ACCESS.FSYNC],
});

function describeContract() {
    return Object.freeze({
        schema_version: CONTRACT_SCHEMA_VERSION,
        contract_version: CONTRACT_VERSION,
        authority: 'Stage D Blocker #2 Phase A — machine-readable runtime filesystem access contract',
        scope_note: 'Inspect, classify and plan only. No apply path exists in Phase A.',
        identity_rule: Object.freeze({
            owner_uid: 'must equal the cold-loading runtime uid',
            owner_gid: 'must equal the cold-loading runtime gid',
            mechanism: 'IDENTITY_EQUALITY',
            rejected_mechanisms: Object.freeze([
                'named POSIX ACL entries (collapsed to mask "---" by the publisher fchmod)',
                'group access to immutable package artifacts (publisher emits owner-only modes)',
                'making immutable historical surfaces writable',
            ]),
            privileged_runtime_uid_0: 'REJECTED — a uid 0 runtime bypasses DAC and makes this contract unverifiable',
        }),
        surfaces: Object.freeze([
            AUTHORITY_ROOT_DIRECTORY_SPEC, STORE_ARTIFACT_SPEC, COMMITTED_ROOT_SPEC, STAGING_ROOT_SPEC,
            PACKAGE_DIRECTORY_SPEC, PACKAGE_FILE_SPEC, ALLOCATION_ARTIFACT_SPEC,
            LEDGER_ROOT_SPEC, LEDGER_ENTRIES_SPEC, LEDGER_EPOCH_SPEC, LEDGER_ENTRY_FILE_SPEC,
            TRUST_ROOT_SPEC,
        ]),
        immutable_package_file_set: Object.freeze([...TRANSACTION_FILES].sort()),
        future_publication: Object.freeze({
            classification: FUTURE_PUBLICATION_SURFACE,
            directory_mode: 0o700,
            package_file_mode: 0o400,
            requirement: 'a newly published tx_<sha> directory and every package file must satisfy the same postconditions before the publication counts as contract-compliant',
            umask_rule: 'umask may only clear bits; a umask that intersects 0o700 will silently damage a published directory, and rename preserves the damage permanently',
        }),
        access_classes: Object.freeze(Object.values(ACCESS)),
        definitions: Object.freeze({
            IMMUTABLE_HISTORICAL_READ_SURFACE: 'read-only content the cold-loading runtime must be able to read; never writable by the runtime',
            ACTIVE_RUNTIME_WRITE_SURFACE: 'runtime-owned working surface that must stay writable for authorized publication and accounting',
            GOVERNED_SURFACE: 'directory whose contents become immutable once published; needs write access only to accept the publication rename',
            FUTURE_PUBLICATION_SURFACE: 'postconditions that a not-yet-published package must satisfy',
        }),
    });
}

// ---------------------------------------------------------------------------
// Observation
// ---------------------------------------------------------------------------

function observeObject(target) {
    let stat;
    try {
        stat = fs.lstatSync(target);
    } catch (error) {
        return Object.freeze({ path: target, observable: false, code: error.code || 'UNKNOWN', absent: error.code === 'ENOENT' });
    }
    const isSymbolicLink = stat.isSymbolicLink();
    return Object.freeze({
        path: target,
        observable: true,
        absent: false,
        is_symbolic_link: isSymbolicLink,
        is_directory: stat.isDirectory(),
        is_file: stat.isFile(),
        is_other: !isSymbolicLink && !stat.isDirectory() && !stat.isFile(),
        uid: stat.uid,
        gid: stat.gid,
        mode: stat.mode & 0o7777,
        dev: stat.dev,
        ino: stat.ino,
        nlink: stat.nlink,
        size: stat.size,
    });
}

function walkAncestry(target) {
    const resolved = path.resolve(target);
    const segments = resolved.split(path.sep).filter(Boolean);
    const chain = [];
    let current = path.sep;
    for (const segment of segments) {
        current = path.join(current, segment);
        if (current === resolved) break;
        chain.push(current);
    }
    return Object.freeze(chain.map(observeObject));
}

function sha256OfReadableFile(target) {
    const observation = observeObject(target);
    if (!observation.observable) return Object.freeze({ status: observation.absent ? 'ABSENT' : 'NOT_OBSERVABLE', code: observation.code });
    if (!observation.is_file) return Object.freeze({ status: 'NOT_REGULAR_FILE' });
    try {
        const bytes = fs.readFileSync(target);
        return Object.freeze({ status: 'HASHED', sha256: crypto.createHash('sha256').update(bytes).digest('hex'), size: bytes.length });
    } catch (error) {
        return Object.freeze({ status: 'NOT_READABLE', code: error.code || 'UNKNOWN' });
    }
}

// ---------------------------------------------------------------------------
// Access model.  Effective class follows POSIX DAC: owner, then group, then
// other; a privileged runtime identity (uid 0) bypasses every class.
// ---------------------------------------------------------------------------

function parseAclPermission(value) {
    if (typeof value !== 'string' || value.length !== 3) return null;
    let bits = 0;
    if (value[0] === 'r') bits |= 0o4;
    if (value[1] === 'w') bits |= 0o2;
    if ('xst'.includes(value[2])) bits |= 0o1;
    return bits;
}

function identityMatchesGroup(observation, runtimeIdentity) {
    return observation.gid === runtimeIdentity.gid || runtimeIdentity.groups.includes(observation.gid);
}

// POSIX ACL evaluation order: owner, then a matching named user, then the union
// of every matching group entry (owning group plus named groups) capped by the
// mask, then other.  The mask caps the group class and named entries only; it
// never widens them, which is why a clean mode cannot be loosened by an ACL.
function aclClassBits(observation, runtimeIdentity, acl) {
    const mask = parseAclPermission(acl.mask);
    const cap = bits => (mask === null ? bits : bits & mask);
    const namedUser = (acl.named_user_perms || {})[String(runtimeIdentity.uid)];
    if (namedUser !== undefined) return cap(parseAclPermission(namedUser) ?? 0);
    const groupEntries = [];
    if (identityMatchesGroup(observation, runtimeIdentity)) {
        groupEntries.push(parseAclPermission(acl.group) ?? ((observation.mode >> 3) & 0o7));
    }
    for (const [gid, perms] of Object.entries(acl.named_group_perms || {})) {
        if (Number(gid) === runtimeIdentity.gid || runtimeIdentity.groups.includes(Number(gid))) groupEntries.push(parseAclPermission(perms) ?? 0);
    }
    if (groupEntries.length > 0) return cap(groupEntries.reduce((acc, bits) => acc | bits, 0));
    return parseAclPermission(acl.other) ?? (observation.mode & 0o7);
}

function effectiveClassBits(observation, runtimeIdentity, acl) {
    const ownerBits = (observation.mode >> 6) & 0o7;
    if (observation.uid === runtimeIdentity.uid) {
        if (acl && acl.available) return parseAclPermission(acl.owner) ?? ownerBits;
        return ownerBits;
    }
    if (acl && acl.available) return aclClassBits(observation, runtimeIdentity, acl);
    if (identityMatchesGroup(observation, runtimeIdentity)) return (observation.mode >> 3) & 0o7;
    return observation.mode & 0o7;
}

const ACCESS_BIT = Object.freeze({
    [ACCESS.READ]: 0o4,
    [ACCESS.DIRECTORY_TRAVERSE]: 0o1,
    [ACCESS.WRITE]: 0o2,
    [ACCESS.CREATE]: 0o2,
    [ACCESS.DELETE]: 0o2,
    [ACCESS.RENAME]: 0o2,
    [ACCESS.FSYNC]: 0,
    [ACCESS.CHMOD]: 0,
    [ACCESS.NONE]: 0,
});

function predictRuntimeAccess(observation, runtimeIdentity, requiredAccess, acl = null) {
    if (runtimeIdentity.uid === 0) {
        return Object.freeze({ effective_bits: 0o7, granted: Object.freeze([...requiredAccess]), missing: Object.freeze([]), privileged_bypass: true, acl_applied: false });
    }
    const aclApplied = Boolean(acl && acl.available);
    const bits = effectiveClassBits(observation, runtimeIdentity, acl);
    const missing = requiredAccess.filter(access => (bits & ACCESS_BIT[access]) !== ACCESS_BIT[access]);
    return Object.freeze({
        effective_bits: bits,
        granted: Object.freeze(requiredAccess.filter(access => !missing.includes(access))),
        missing: Object.freeze(missing),
        privileged_bypass: false,
        acl_applied: aclApplied,
    });
}

const ACCESS_VIOLATION_CODE = Object.freeze({
    [ACCESS.READ]: 'UNREADABLE_BY_RUNTIME',
    [ACCESS.DIRECTORY_TRAVERSE]: 'UNTRAVERSABLE_DIRECTORY',
    [ACCESS.WRITE]: 'MISSING_WRITE_ACCESS',
    [ACCESS.CREATE]: 'MISSING_CREATE_ACCESS',
    [ACCESS.DELETE]: 'MISSING_DELETE_ACCESS',
    [ACCESS.RENAME]: 'MISSING_RENAME_ACCESS',
});

// ---------------------------------------------------------------------------
// Classification
// ---------------------------------------------------------------------------

function finding({ code, severity, surfaceId, target, message, autoRepairable, elevatedPrivilegeRequired, contentImpact = 'NONE' }) {
    return Object.freeze({
        code, severity, surface_id: surfaceId, path: target, message,
        auto_repairable: autoRepairable, elevated_privilege_required: elevatedPrivilegeRequired,
        content_impact: contentImpact,
    });
}

function classifyObjectType(spec, observation, findings) {
    if (!observation.observable) {
        findings.push(finding({
            code: observation.absent ? 'MISSING_REQUIRED_PATH' : 'UNOBSERVABLE_GOVERNED_PATH', severity: SEVERITY.VIOLATION,
            surfaceId: spec.surface_id, target: observation.path,
            message: observation.absent ? `${spec.label} is absent` : `${spec.label} cannot be observed (${observation.code})`,
            autoRepairable: false, elevatedPrivilegeRequired: false,
        }));
        return false;
    }
    if (observation.is_symbolic_link) {
        findings.push(finding({
            code: 'SYMLINK_IN_GOVERNED_PATH', severity: SEVERITY.VIOLATION, surfaceId: spec.surface_id, target: observation.path,
            message: `${spec.label} must never be a symlink`, autoRepairable: false, elevatedPrivilegeRequired: false,
        }));
        return false;
    }
    if (spec.object_type === 'directory' && !observation.is_directory) {
        findings.push(finding({
            code: 'UNEXPECTED_FILESYSTEM_OBJECT', severity: SEVERITY.VIOLATION, surfaceId: spec.surface_id, target: observation.path,
            message: `${spec.label} must be a directory`, autoRepairable: false, elevatedPrivilegeRequired: false,
        }));
        return false;
    }
    if (spec.object_type === 'regular_file' && !observation.is_file) {
        findings.push(finding({
            code: 'NON_REGULAR_ARTIFACT', severity: SEVERITY.VIOLATION, surfaceId: spec.surface_id, target: observation.path,
            message: `${spec.label} must be a regular file`, autoRepairable: false, elevatedPrivilegeRequired: false,
        }));
        return false;
    }
    return true;
}

function classifyMetadata(spec, observation, findings) {
    if (observation.is_file && observation.nlink !== 1) {
        findings.push(finding({
            code: 'HARDLINK_DETECTED', severity: SEVERITY.VIOLATION, surfaceId: spec.surface_id, target: observation.path,
            message: `${spec.label} has ${observation.nlink} hard links; governed artifacts must be single-linked`,
            autoRepairable: false, elevatedPrivilegeRequired: false,
        }));
    }
    if ((observation.mode & 0o022) !== 0) {
        findings.push(finding({
            code: 'GROUP_OR_WORLD_WRITABLE', severity: SEVERITY.VIOLATION, surfaceId: spec.surface_id, target: observation.path,
            message: `${spec.label} is group/world writable (mode ${observation.mode.toString(8).padStart(4, '0')})`,
            autoRepairable: true, elevatedPrivilegeRequired: false,
        }));
    }
    if (spec.immutable_content && (observation.mode & 0o222) !== 0) {
        findings.push(finding({
            code: 'CONTENT_WRITE_BIT_ON_IMMUTABLE', severity: SEVERITY.VIOLATION, surfaceId: spec.surface_id, target: observation.path,
            message: `${spec.label} is an immutable artifact but carries a write bit`,
            autoRepairable: true, elevatedPrivilegeRequired: false,
        }));
    }
    if (observation.mode !== spec.exact_mode) {
        findings.push(finding({
            code: 'MODE_MISMATCH', severity: SEVERITY.VIOLATION, surfaceId: spec.surface_id, target: observation.path,
            message: `${spec.label} mode ${observation.mode.toString(8).padStart(4, '0')} does not match the contract postcondition ${spec.exact_mode.toString(8).padStart(4, '0')}`,
            autoRepairable: true, elevatedPrivilegeRequired: false,
        }));
    }
}

function classifyIdentity(spec, observation, runtimeIdentity, findings) {
    if (observation.uid !== runtimeIdentity.uid || observation.gid !== runtimeIdentity.gid) {
        findings.push(finding({
            code: 'UNEXPECTED_IDENTITY_RELATION', severity: SEVERITY.VIOLATION, surfaceId: spec.surface_id, target: observation.path,
            message: `${spec.label} is owned by ${observation.uid}:${observation.gid} but the cold-loading runtime identity is ${runtimeIdentity.uid}:${runtimeIdentity.gid}`,
            autoRepairable: true, elevatedPrivilegeRequired: observation.uid !== process.getuid(),
        }));
    }
}

function classifyAccess(spec, observation, runtimeIdentity, acl, findings) {
    const access = predictRuntimeAccess(observation, runtimeIdentity, spec.runtime_access, acl);
    const seen = new Set();
    for (const missing of access.missing) {
        const code = ACCESS_VIOLATION_CODE[missing] || 'MISSING_REQUIRED_ACCESS';
        if (seen.has(code)) continue;
        seen.add(code);
        findings.push(finding({
            code, severity: SEVERITY.VIOLATION, surfaceId: spec.surface_id, target: observation.path,
            message: `${spec.label} does not provide ${missing} to the runtime identity`,
            autoRepairable: true, elevatedPrivilegeRequired: observation.uid !== process.getuid(),
        }));
    }
    if (runtimeIdentity.uid === 0) {
        findings.push(finding({
            code: 'PRIVILEGED_RUNTIME_IDENTITY', severity: SEVERITY.VIOLATION, surfaceId: spec.surface_id, target: observation.path,
            message: `${spec.label} cannot be contract-verified because the declared runtime identity is uid 0`,
            autoRepairable: false, elevatedPrivilegeRequired: false,
        }));
    }
    return access;
}

function classifyAcl(spec, observation, aclObservations, findings) {
    if (!aclObservations || !Object.prototype.hasOwnProperty.call(aclObservations, observation.path)) return 'NOT_RUN';
    const acl = aclObservations[observation.path];
    if (!acl.available) {
        // An unobservable ACL is not the same thing as no ACL.  A default ACL
        // leaves no trace in the directory's own mode — that is the whole point
        // of the round-4 fix — so a mode-and-identity-clean directory whose ACL
        // could not be read is an evidence gap, not a clean surface.  Reporting
        // it as an advisory would let the CLI exit 0 and the plan report
        // NOT_REQUIRED for a tree whose future published packages may inherit
        // entries this contract never authorised.
        findings.push(finding({
            code: 'ACL_PROBE_UNAVAILABLE', severity: SEVERITY.VIOLATION, surfaceId: spec.surface_id, target: observation.path,
            message: `${spec.label} extended ACL could not be probed (${acl.reason || 'unavailable'}), so neither an access ACL nor an inherited default ACL can be ruled out from the mode alone`,
            autoRepairable: false, elevatedPrivilegeRequired: false,
        }));
        return 'UNAVAILABLE';
    }
    // A default ACL governs objects that do not exist yet.  Every directory the
    // publisher creates below this path inherits it, and an inherited mask caps
    // the mode its own fchmod can produce, so a clean mode on this directory no
    // longer means the next published package will be clean.  It is therefore
    // reported as an unrecognised future-publication hazard rather than folded
    // into the access-ACL verdict, and no bounded metadata operation on the
    // existing objects can resolve it.
    if (acl.default_present === true) {
        const inherited = acl.default_entries.length > 0 ? `named default entries: ${acl.default_entries.join(', ')}` : 'base default entries only';
        findings.push(finding({
            code: 'DEFAULT_ACL_PRESENT', severity: SEVERITY.VIOLATION, surfaceId: spec.surface_id, target: observation.path,
            message: `${spec.label} carries a default ACL (${inherited}), so every object created below it inherits those entries and an exact mode is no longer the whole policy for the next publication`,
            autoRepairable: false, elevatedPrivilegeRequired: true,
        }));
    }
    if (acl.named_entries && acl.named_entries.length > 0) {
        findings.push(finding({
            code: 'EXTENDED_ACL_PRESENT', severity: SEVERITY.VIOLATION, surfaceId: spec.surface_id, target: observation.path,
            message: `${spec.label} carries named access ACL entries: ${acl.named_entries.join(', ')}`,
            autoRepairable: true, elevatedPrivilegeRequired: false,
        }));
        return 'EXTENDED_ACL_PRESENT';
    }
    return acl.default_present === true ? 'DEFAULT_ACL_PRESENT' : 'CLEAN';
}

function evaluateSurface(spec, target, context) {
    const findings = [];
    const observation = observeObject(target);
    const effective = Object.freeze({ ...spec, path: target });
    if (!classifyObjectType(spec, observation, findings)) {
        return Object.freeze({ spec: effective, observation, access: null, acl: 'NOT_RUN', findings: Object.freeze(findings), compliant: false });
    }
    classifyMetadata(spec, observation, findings);
    classifyIdentity(spec, observation, context.runtimeIdentity, findings);
    const acl = classifyAcl(spec, observation, context.aclObservations, findings);
    const aclObservation = context.aclObservations ? context.aclObservations[target] : null;
    const access = classifyAccess(spec, observation, context.runtimeIdentity, aclObservation, findings);
    return Object.freeze({
        spec: effective, observation, access, acl,
        findings: Object.freeze(findings),
        compliant: !findings.some(item => item.severity === SEVERITY.VIOLATION),
    });
}

// ---------------------------------------------------------------------------
// Ancestry.  A world-writable ancestor fails closed unless it carries the
// sticky bit, which is exactly the protection that stops an unrelated user
// from renaming or deleting the governed subtree entry.  Group-writable
// ancestors are a hard violation only on the run-lock trust root chain, which
// is the rule the existing runtime already enforces; on the authority chain
// they are ADVISORY because the repository checkout itself is created
// group-writable under a umask of 0o002.
// ---------------------------------------------------------------------------

function classifyAncestorWriteBits(ancestor, surfaceId, failClosedOnGroupWritable, findings) {
    const mode = ancestor.mode.toString(8).padStart(4, '0');
    const elevated = ancestor.uid !== (typeof process.getuid === 'function' ? process.getuid() : ancestor.uid);
    if ((ancestor.mode & 0o002) !== 0 && (ancestor.mode & 0o1000) === 0) {
        findings.push(finding({
            code: 'WORLD_WRITABLE_ANCESTOR', severity: SEVERITY.VIOLATION, surfaceId, target: ancestor.path,
            message: `ancestor is world writable without the sticky bit (mode ${mode}); an unrelated user can replace the governed subtree`,
            autoRepairable: true, elevatedPrivilegeRequired: elevated,
        }));
        return;
    }
    if ((ancestor.mode & 0o002) !== 0) {
        findings.push(finding({
            code: 'STICKY_WORLD_WRITABLE_ANCESTOR', severity: SEVERITY.ADVISORY, surfaceId, target: ancestor.path,
            message: `ancestor is world writable but sticky (mode ${mode}); the sticky bit protects the governed subtree entry`,
            autoRepairable: false, elevatedPrivilegeRequired: false,
        }));
    }
    if ((ancestor.mode & 0o020) === 0) return;
    if (failClosedOnGroupWritable) {
        findings.push(finding({
            code: 'GROUP_WRITABLE_ANCESTOR', severity: SEVERITY.VIOLATION, surfaceId, target: ancestor.path,
            message: `ancestor is group writable (mode ${mode}); the run-lock trust root requires a non-group-writable parent chain`,
            autoRepairable: true, elevatedPrivilegeRequired: elevated,
        }));
        return;
    }
    findings.push(finding({
        code: 'GROUP_WRITABLE_ANCESTOR', severity: SEVERITY.ADVISORY, surfaceId, target: ancestor.path,
        message: `ancestor is group writable (mode ${mode}); any member of the owning group can replace the governed subtree`,
        autoRepairable: true, elevatedPrivilegeRequired: elevated,
    }));
}

function classifyAncestor(ancestor, { surfaceId, failClosedOnGroupWritable }, runtimeIdentity, aclObservations, findings) {
    if (!ancestor.observable) {
        findings.push(finding({
            code: 'UNOBSERVABLE_ANCESTOR', severity: SEVERITY.VIOLATION, surfaceId, target: ancestor.path,
            message: `ancestor cannot be observed (${ancestor.code})`, autoRepairable: false, elevatedPrivilegeRequired: false,
        }));
        return;
    }
    if (ancestor.is_symbolic_link || !ancestor.is_directory) {
        findings.push(finding({
            code: 'SYMLINK_IN_GOVERNED_PATH', severity: SEVERITY.VIOLATION, surfaceId, target: ancestor.path,
            message: 'governed ancestry must contain real directories', autoRepairable: false, elevatedPrivilegeRequired: false,
        }));
        return;
    }
    classifyAncestorWriteBits(ancestor, surfaceId, failClosedOnGroupWritable, findings);
    const acl = aclObservations ? aclObservations[ancestor.path] : null;
    if (acl && acl.available && acl.named_entries && acl.named_entries.length > 0) {
        findings.push(finding({
            code: 'EXTENDED_ACL_PRESENT', severity: SEVERITY.ADVISORY, surfaceId, target: ancestor.path,
            message: `ancestor carries named access ACL entries: ${acl.named_entries.join(', ')}`,
            autoRepairable: true, elevatedPrivilegeRequired: false,
        }));
    }
    if (predictRuntimeAccess(ancestor, runtimeIdentity, [ACCESS.DIRECTORY_TRAVERSE], acl).missing.length > 0) {
        findings.push(finding({
            code: 'UNTRAVERSABLE_DIRECTORY', severity: SEVERITY.VIOLATION, surfaceId, target: ancestor.path,
            message: 'ancestor does not provide directory traversal to the cold-loading runtime identity',
            autoRepairable: true, elevatedPrivilegeRequired: ancestor.uid !== runtimeIdentity.uid,
        }));
    }
}

function classifyAncestry(target, { surfaceId, failClosedOnGroupWritable, runtimeIdentity, aclObservations }) {
    const findings = [];
    for (const ancestor of walkAncestry(target)) {
        classifyAncestor(ancestor, { surfaceId, failClosedOnGroupWritable }, runtimeIdentity, aclObservations, findings);
    }
    return Object.freeze(findings);
}

// ---------------------------------------------------------------------------
// Enumeration
// ---------------------------------------------------------------------------

function readEntryNames(target) {
    try {
        return Object.freeze({ status: 'OK', names: Object.freeze(fs.readdirSync(target).sort()) });
    } catch (error) {
        return Object.freeze({ status: 'UNREADABLE', code: error.code || 'UNKNOWN', names: Object.freeze([]) });
    }
}

// A listing that could not be read is not an empty listing.  Treating it as one
// would drop every governed object underneath it from the audit, so a
// complete-looking plan could be produced for a tree whose package files were
// never examined at all.  A directory that is simply absent is left to the
// surface evaluator, which already reports it as MISSING_REQUIRED_PATH; an
// existing directory that cannot be listed is an observation gap that no
// bounded metadata operation on the files themselves can resolve.
function recordListingGap(findings, { surfaceId, target, code, label }) {
    findings.push(finding({
        code: 'UNOBSERVABLE_DIRECTORY_LISTING', severity: SEVERITY.VIOLATION, surfaceId, target,
        message: `${label} exists but could not be listed (${code}), so the governed objects below it were never observed; the directory must be made readable and the tree re-audited before any file-level plan can be produced`,
        autoRepairable: false, elevatedPrivilegeRequired: false,
    }));
}

function listingGapOrNames(findings, { surfaceId, target, label }) {
    const listing = readEntryNames(target);
    if (listing.status !== 'OK' && listing.code !== 'ENOENT') recordListingGap(findings, { surfaceId, target, code: listing.code, label });
    return listing;
}

function collectPackageSurfaces(authorityRoot, findings) {
    const surfaces = [];
    const committed = path.join(authorityRoot, COMMITTED_DIRECTORY);
    const listing = listingGapOrNames(findings, { surfaceId: SURFACE.COMMITTED_ROOT, target: committed, label: 'the committed directory' });
    if (listing.status !== 'OK') return surfaces;
    for (const name of listing.names) {
        if (!TX_DIRECTORY.test(name)) {
            findings.push(finding({
                code: 'UNEXPECTED_COMMITTED_ENTRY', severity: SEVERITY.VIOLATION, surfaceId: SURFACE.COMMITTED_ROOT,
                target: path.join(committed, name), message: `unexpected committed entry: ${name}`,
                autoRepairable: false, elevatedPrivilegeRequired: false,
            }));
            continue;
        }
        const txPath = path.join(committed, name);
        surfaces.push({ spec: PACKAGE_DIRECTORY_SPEC, target: txPath });
        const names = listingGapOrNames(findings, { surfaceId: SURFACE.TRANSACTION_PACKAGE_DIRECTORY, target: txPath, label: 'a committed transaction package directory' });
        if (names.status !== 'OK') continue;
        if (JSON.stringify(names.names) !== JSON.stringify([...TRANSACTION_FILES].sort())) {
            findings.push(finding({
                code: 'UNEXPECTED_PACKAGE_FILE_SET', severity: SEVERITY.VIOLATION, surfaceId: SURFACE.TRANSACTION_PACKAGE_DIRECTORY,
                target: txPath, message: 'transaction package does not hold the exact committed file set',
                autoRepairable: false, elevatedPrivilegeRequired: false,
            }));
        }
        for (const file of names.names) surfaces.push({ spec: PACKAGE_FILE_SPEC, target: path.join(txPath, file) });
    }
    return surfaces;
}

function collectLedgerSurfaces(ledgerRoot, findings = []) {
    const surfaces = [{ spec: LEDGER_ROOT_SPEC, target: ledgerRoot }];
    surfaces.push({ spec: LEDGER_ENTRIES_SPEC, target: path.join(ledgerRoot, ENTRY_DIRECTORY) });
    surfaces.push({ spec: LEDGER_EPOCH_SPEC, target: path.join(ledgerRoot, EPOCH_FILE) });
    const listing = listingGapOrNames(findings, { surfaceId: SURFACE.REQUEST_ACCOUNTING_ENTRIES, target: path.join(ledgerRoot, ENTRY_DIRECTORY), label: 'the request-accounting entries directory' });
    if (listing.status === 'OK') {
        for (const name of listing.names) {
            if (LEDGER_ENTRY_FILE.test(name)) surfaces.push({ spec: LEDGER_ENTRY_FILE_SPEC, target: path.join(ledgerRoot, ENTRY_DIRECTORY, name) });
        }
    }
    return surfaces;
}

function collectSurfaces({ authorityRoot, allocationArtifactPath, ledgerRoot, runLockTrustRoot }, findings) {
    const planned = [
        { spec: AUTHORITY_ROOT_DIRECTORY_SPEC, target: authorityRoot },
        { spec: STORE_ARTIFACT_SPEC, target: path.join(authorityRoot, STORE_FILE) },
        { spec: COMMITTED_ROOT_SPEC, target: path.join(authorityRoot, COMMITTED_DIRECTORY) },
        { spec: STAGING_ROOT_SPEC, target: path.join(authorityRoot, STAGING_DIRECTORY) },
        ...collectPackageSurfaces(authorityRoot, findings),
    ];
    if (allocationArtifactPath) planned.push({ spec: ALLOCATION_ARTIFACT_SPEC, target: allocationArtifactPath });
    if (ledgerRoot) planned.push(...collectLedgerSurfaces(ledgerRoot, findings));
    if (runLockTrustRoot) planned.push({ spec: TRUST_ROOT_SPEC, target: runLockTrustRoot });
    return planned;
}

// ---------------------------------------------------------------------------
// Authority generation pinning (defeats TOCTOU / path replacement)
// ---------------------------------------------------------------------------

function openGovernedRoot(target, label) {
    let before;
    try {
        before = fs.lstatSync(target);
    } catch (error) {
        throw contractError('GOVERNED_ROOT_UNOBSERVABLE', `${label} cannot be observed: ${error.code || error.message}`);
    }
    if (before.isSymbolicLink() || !before.isDirectory()) throw contractError('GOVERNED_ROOT_NOT_DIRECTORY', `${label} must be a non-symlink directory`);
    const fd = fs.openSync(target, fs.constants.O_RDONLY | (fs.constants.O_DIRECTORY || 0) | (fs.constants.O_NOFOLLOW || 0));
    try {
        const opened = fs.fstatSync(fd);
        if (!opened.isDirectory() || opened.dev !== before.dev || opened.ino !== before.ino) {
            throw contractError('GOVERNED_ROOT_CHANGED_DURING_OPEN', `${label} changed during open`);
        }
        return Object.freeze({
            path: path.resolve(target), fd,
            identity: Object.freeze({ dev: opened.dev, ino: opened.ino, mode: opened.mode & 0o7777, uid: opened.uid, gid: opened.gid }),
        });
    } catch (error) {
        fs.closeSync(fd);
        throw error;
    }
}

function closeGovernedRoot(generation) {
    if (generation && Number.isInteger(generation.fd)) fs.closeSync(generation.fd);
}

// Re-observe the pinned root and decide whether it is still the same object.
// The audit reads ACLs, content hashes, metadata and the plan in separate
// phases; without this, a root replaced while those phases ran would produce a
// report whose findings describe one object and whose plan binds another.
function generationDrift(generation) {
    if (!generation) return null;
    const observed = observeObject(generation.path);
    if (observed.observable && observed.dev === generation.identity.dev && observed.ino === generation.identity.ino) return null;
    return Object.freeze({
        code: 'AUTHORITY_GENERATION_REPLACED', path: generation.path,
        message: 'the authority root identity changed after inspection began; the observed authority generation is not the pinned generation',
        observed: Object.freeze({ dev: observed.observable ? observed.dev : null, ino: observed.observable ? observed.ino : null }),
        pinned: generation.identity,
    });
}

function classifyGeneration(generation, findings) {
    const { code, path: target, message } = generationDrift(generation) || {};
    if (code === undefined) return;
    findings.push(finding({ code, severity: SEVERITY.VIOLATION, surfaceId: SURFACE.TRANSACTION_AUTHORITY_ROOT, target, message, autoRepairable: false, elevatedPrivilegeRequired: false }));
}

// ---------------------------------------------------------------------------
// Evaluation
// ---------------------------------------------------------------------------

function evaluateAncestry(targets, runtimeIdentity, aclObservations, findings) {
    const configs = [
        { target: targets.authorityRoot, surfaceId: SURFACE.TRANSACTION_AUTHORITY_ROOT, failClosedOnGroupWritable: false },
        // The allocation authority may live outside the authority root.  Its
        // ancestry is part of the governed path: a symlinked or world-writable
        // ancestor lets the artifact be replaced wholesale, which no content
        // hash computed after the fact can detect.
        { target: targets.allocationArtifactPath, surfaceId: SURFACE.ALLOCATION_AUTHORITY_ARTIFACT, failClosedOnGroupWritable: false },
        { target: targets.ledgerRoot, surfaceId: SURFACE.REQUEST_ACCOUNTING_ROOT, failClosedOnGroupWritable: false },
        { target: targets.runLockTrustRoot, surfaceId: SURFACE.RUN_LOCK_TRUST_ROOT, failClosedOnGroupWritable: true },
    ];
    // One path can be an ancestor of several targets: the allocation artifact
    // normally sits inside the authority root, and a ledger root can share a
    // parent with either.  Each distinct ancestor is classified exactly once —
    // a shared directory must not be reported twice — but a path reached by any
    // target that demands a non-group-writable chain is classified under that
    // strictest policy, so a laxer target can never downgrade it.
    const reached = new Map();
    for (const config of configs) {
        if (!config.target) continue;
        for (const ancestor of walkAncestry(config.target)) {
            const prior = reached.get(ancestor.path);
            if (prior === undefined) {
                reached.set(ancestor.path, {
                    ancestor, surfaceId: config.surfaceId, failClosedOnGroupWritable: config.failClosedOnGroupWritable,
                });
                continue;
            }
            if (config.failClosedOnGroupWritable) prior.failClosedOnGroupWritable = true;
        }
    }
    for (const entry of reached.values()) {
        classifyAncestor(entry.ancestor, entry, runtimeIdentity, aclObservations, findings);
    }
}

// The ACL state a governed path is currently in, in a form a Phase B repair can
// put back with `setfacl --set`.  `restorable` is the only field the planner is
// allowed to act on: an unobservable or incomplete ACL is not evidence that no
// ACL exists, so it can never authorise deleting one.
function restorableAclState(acl) {
    if (!acl || acl.available !== true) {
        return Object.freeze({ available: false, restorable: false, reason: acl ? acl.reason : 'acl-not-observed' });
    }
    const namedUsers = acl.named_user_perms || {};
    const namedGroups = acl.named_group_perms || {};
    const defaultBase = acl.default_base || {};
    const defaultUsers = acl.default_user_perms || {};
    const defaultGroups = acl.default_group_perms || {};
    // A value is only replayable if it is exactly a POSIX permission triad.  A
    // type check is not enough: getfacl appends a `#effective:` annotation to
    // any entry the mask limits, and a parser that keeps it would record
    // "r-x  #effective:---" as the permission, mark the ACL restorable and hand
    // setfacl an argument it rejects — losing the very entries the rollback
    // exists to protect.
    //
    // Whether a default ACL exists has to have been *observed*, never inferred:
    // a `setfacl --set` replay covering only the access entries would silently
    // drop the entries every future child of this directory inherits, so an
    // observation that does not report one is incomplete rather than clean.
    const complete = typeof acl.default_present === 'boolean'
        && aclScopeReplayable({ user: acl.owner, group: acl.group, other: acl.other, mask: acl.mask }, { ...namedUsers, ...namedGroups })
        && (acl.default_present !== true || aclScopeReplayable(defaultBase, { ...defaultUsers, ...defaultGroups }));
    return Object.freeze({
        available: true,
        restorable: complete,
        reason: complete ? null : 'acl-observation-incomplete',
        named_entries: Object.freeze([...(acl.named_entries || [])]), default_entries: Object.freeze([...(acl.default_entries || [])]),
        named_user_perms: Object.freeze({ ...namedUsers }), named_group_perms: Object.freeze({ ...namedGroups }),
        default_user_perms: Object.freeze({ ...defaultUsers }), default_group_perms: Object.freeze({ ...defaultGroups }),
        user: orNull(acl.owner), group: orNull(acl.group), other: orNull(acl.other), mask: orNull(acl.mask),
        default_present: acl.default_present === true,
        default_user: orNull(defaultBase.user), default_group: orNull(defaultBase.group),
        default_other: orNull(defaultBase.other), default_mask: orNull(defaultBase.mask),
    });
}

function buildAclState(aclObservations) {
    if (!aclObservations || typeof aclObservations !== 'object') return Object.freeze({});
    const restorable = target => [target, restorableAclState(aclObservations[target])];
    return Object.freeze(Object.fromEntries(Object.keys(aclObservations).sort().map(restorable)));
}

function buildReport({ runtimeIdentity, targets, evaluations, findings, generation, contentHashes, aclState }) {
    const violations = findings.filter(item => item.severity === SEVERITY.VIOLATION);
    const ambiguous = violations.filter(item => !item.auto_repairable);
    let status = 'COMPLIANT';
    if (violations.length > 0) status = ambiguous.length > 0 ? 'NONCOMPLIANT_BLOCKED' : 'NONCOMPLIANT_REPAIRABLE';
    return Object.freeze({
        schema_version: REPORT_SCHEMA_VERSION,
        contract_version: CONTRACT_VERSION,
        status,
        runtime_identity: runtimeIdentity,
        targets: Object.freeze({ ...targets }),
        authority_generation: generation ? generation.identity : null,
        acl_state: aclState || Object.freeze({}),
        surfaces: Object.freeze(evaluations),
        findings: Object.freeze(findings),
        violation_count: violations.length,
        advisory_count: findings.length - violations.length,
        ambiguous_finding_count: ambiguous.length,
        content_hashes: contentHashes ? Object.freeze({ ...contentHashes }) : null,
        production_mutation_performed: false,
        mutating_capability_present: false,
        read_write_separation: Object.freeze({
            immutable_historical_read_surface: Object.freeze(evaluations.filter(item => item.spec.classification === IMMUTABLE_HISTORICAL_READ_SURFACE).map(item => item.spec.path)),
            active_runtime_write_surface: Object.freeze(evaluations.filter(item => item.spec.classification === ACTIVE_RUNTIME_WRITE_SURFACE).map(item => item.spec.path)),
        }),
    });
}

function evaluateRuntimeFilesystemContract({
    runtimeIdentity,
    authorityRoot,
    allocationArtifactPath = null,
    ledgerRoot = null,
    runLockTrustRoot = null,
    generation = null,
    aclObservations = null,
    contentHashes = null,
} = {}) {
    const identity = assertRuntimeIdentity(runtimeIdentity);
    if (typeof authorityRoot !== 'string' || !authorityRoot.trim()) throw contractError('INVALID_AUDIT_INPUT', 'authorityRoot is required');
    const targets = Object.freeze({
        authorityRoot: path.resolve(authorityRoot),
        allocationArtifactPath: allocationArtifactPath ? path.resolve(allocationArtifactPath) : null,
        ledgerRoot: ledgerRoot ? path.resolve(ledgerRoot) : null,
        runLockTrustRoot: runLockTrustRoot ? path.resolve(runLockTrustRoot) : null,
    });
    const findings = [];
    classifyGeneration(generation, findings);
    evaluateAncestry(targets, identity, aclObservations, findings);
    const evaluations = collectSurfaces(targets, findings)
        .map(planned => evaluateSurface(planned.spec, planned.target, { runtimeIdentity: identity, aclObservations }));
    for (const evaluation of evaluations) findings.push(...evaluation.findings);
    return buildReport({
        runtimeIdentity: identity, targets, evaluations, findings, generation, contentHashes,
        aclState: buildAclState(aclObservations),
    });
}

// ---------------------------------------------------------------------------
// Publication identity guard.  This is the recurrence-prevention primitive:
// it fails closed whenever the identity about to publish is not the identity
// that owns — and will cold-load — the accepted authority.
// ---------------------------------------------------------------------------

function nearestExistingAncestor(target) {
    let current = path.resolve(target);
    for (;;) {
        const observation = observeObject(current);
        if (observation.observable) return Object.freeze({ path: current, observation });
        if (current === path.dirname(current)) throw contractError('PUBLICATION_IDENTITY_UNRESOLVABLE', 'no existing ancestor could be observed for the authority root');
        current = path.dirname(current);
    }
}

function assertPublicationIdentity({ publisherIdentity, runtimeIdentity, authorityRoot } = {}) {
    const publisher = assertRuntimeIdentity(publisherIdentity);
    const runtime = runtimeIdentity ? assertRuntimeIdentity(runtimeIdentity) : null;
    if (!runtime) throw contractError('PUBLICATION_IDENTITY_UNSPECIFIED', 'the expected cold-loading runtime identity must be declared explicitly');
    // A privileged process is refused on either side of the check, not only on
    // the mixed one.  The both-root case is the one that matters most here:
    // the binder derives the runtime identity from the authority anchor's
    // owner, so a root process facing a root-owned authority gets uid 0 on both
    // sides and would otherwise verify itself — keep publishing owner-only
    // packages that the ordinary runtime user cannot read, which is exactly
    // how Blocker #2 arose.  classifyAccess already treats a uid 0 runtime
    // identity as a violation, so the guard must refuse it too.
    if (publisher.uid === 0) {
        throw contractError('PUBLICATION_AS_PRIVILEGED_IDENTITY', `publishing as uid 0 would create artifacts unreadable by runtime uid ${runtime.uid}; a privileged publisher is never accepted`);
    }
    if (runtime.uid === 0) {
        throw contractError('PUBLICATION_AS_PRIVILEGED_IDENTITY', 'a privileged cold-loading runtime identity (uid 0) can never be contract-verified, so it is never accepted as the publication target');
    }
    if (publisher.uid !== runtime.uid || publisher.gid !== runtime.gid) {
        throw contractError('PUBLICATION_IDENTITY_MISMATCH', `publisher ${publisher.uid}:${publisher.gid} is not the declared runtime identity ${runtime.uid}:${runtime.gid}`);
    }
    const anchored = nearestExistingAncestor(authorityRoot);
    const { observation } = anchored;
    if (observation.is_symbolic_link || !observation.is_directory) {
        throw contractError('PUBLICATION_IDENTITY_UNSAFE_ROOT', 'the authority root anchor must be a non-symlink directory');
    }
    if ((observation.mode & 0o022) !== 0) {
        throw contractError('PUBLICATION_IDENTITY_UNSAFE_ROOT', 'the authority root anchor must not be group or world writable');
    }
    if (observation.uid !== runtime.uid) {
        throw contractError('PUBLICATION_IDENTITY_UNRESOLVABLE', `the authority root anchor ${anchored.path} is owned by ${observation.uid}:${observation.gid}, not by the declared runtime identity ${runtime.uid}:${runtime.gid}`);
    }
    return Object.freeze({
        status: 'PUBLICATION_IDENTITY_VERIFIED',
        publisher_identity: publisher,
        runtime_identity: runtime,
        anchor: anchored.path,
        anchor_identity: Object.freeze({ uid: observation.uid, gid: observation.gid, mode: observation.mode, dev: observation.dev, ino: observation.ino }),
    });
}

function deriveRuntimeIdentityFromAuthority(authorityRoot, { source = 'AUTHORITY_ANCHOR_OWNER' } = {}) {
    const anchored = nearestExistingAncestor(authorityRoot);
    if (!anchored.observation.observable || anchored.observation.is_symbolic_link || !anchored.observation.is_directory) {
        throw contractError('PUBLICATION_IDENTITY_UNRESOLVABLE', 'the authority anchor could not be resolved to a real directory');
    }
    return Object.freeze({
        uid: anchored.observation.uid,
        gid: anchored.observation.gid,
        groups: Object.freeze([]),
        source,
        anchor: anchored.path,
    });
}

function processIdentity({ source = 'PROCESS' } = {}) {
    const uid = typeof process.getuid === 'function' ? process.getuid() : null;
    const gid = typeof process.getgid === 'function' ? process.getgid() : null;
    const groups = typeof process.getgroups === 'function' ? process.getgroups() : [];
    return Object.freeze({ uid, gid, groups: Object.freeze([...groups]), source });
}

module.exports = {
    CONTRACT_SCHEMA_VERSION, REPORT_SCHEMA_VERSION, CONTRACT_VERSION,
    ACCESS, SEVERITY, SURFACE, RESERVED_NAMES, STORE_FILE, EPOCH_FILE, ENTRY_DIRECTORY,
    STAGING_DIRECTORY, COMMITTED_DIRECTORY,
    describeContract, observeObject, walkAncestry, sha256OfReadableFile, predictRuntimeAccess,
    openGovernedRoot, closeGovernedRoot, generationDrift, evaluateRuntimeFilesystemContract, restorableAclState,
    collectLedgerSurfaces, LEDGER_ENTRY_FILE,
    assertPublicationIdentity, deriveRuntimeIdentityFromAuthority, processIdentity,
};
