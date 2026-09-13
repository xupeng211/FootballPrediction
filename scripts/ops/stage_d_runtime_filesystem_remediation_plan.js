#!/usr/bin/env node
'use strict';

// Stage D runtime filesystem remediation PLANNER (Blocker #2, Phase A).
//
// Lifecycle: permanent
// Owner: @xupeng211 (scripts/ops per .github/CODEOWNERS)
//
// This module reasons about metadata change and therefore lives in its own
// file: the audit/classify half of the contract must never be able to mutate
// anything, and keeping the only change-shaped code separate makes that
// property reviewable at a glance.
//
// The planner is INERT.  It emits a plan; it never applies one, has no
// filesystem write call at all, and cannot be reached from an ordinary CLI
// invocation as a mutating path.  Applying a plan is a separately authorized
// Phase B host procedure.  Every operation it can emit is metadata-only and
// must leave the governed bytes byte-identical.

const { SEVERITY, observeObject } = require('./stage_d_runtime_filesystem_permission_contract');

const PLAN_SCHEMA_VERSION = 'footballprediction-stage-d-runtime-filesystem-remediation-plan/v1';

// ---------------------------------------------------------------------------
// Finding classification
// ---------------------------------------------------------------------------

// The mode on disk is not the contract's postcondition.
const MODE_FINDING_CODES = Object.freeze(new Set(['MODE_MISMATCH', 'CONTENT_WRITE_BIT_ON_IMMUTABLE', 'GROUP_OR_WORLD_WRITABLE']));
// The object is owned by an identity that is not the cold-loading runtime.
const IDENTITY_FINDING_CODES = Object.freeze(new Set(['UNEXPECTED_IDENTITY_RELATION']));
// An extended ACL exists; the exact mode is meant to be the whole policy.
const ACL_FINDING_CODES = Object.freeze(new Set(['EXTENDED_ACL_PRESENT']));
// Both causes converge on the same missing postcondition: without an exact mode
// to aim at, neither a chmod nor an ACL removal is a bounded operation.
const MODE_OR_ACL_FINDING_CODES = Object.freeze(new Set([...MODE_FINDING_CODES, ...ACL_FINDING_CODES]));

// A default ACL governs objects that do not exist yet.  It is not a defect of
// any current object, so no bounded metadata operation on the governed tree can
// resolve it: removing it is an Owner decision about future publication.
const DEFAULT_ACL_FINDING_CODES = Object.freeze(new Set(['DEFAULT_ACL_PRESENT']));
// The runtime cannot perform an operation it needs.  These are consequences of
// one of the three causes above, never a cause in their own right.
const ACCESS_FINDING_CODES = Object.freeze(new Set([
    'UNREADABLE_BY_RUNTIME', 'UNTRAVERSABLE_DIRECTORY', 'MISSING_WRITE_ACCESS',
    'MISSING_CREATE_ACCESS', 'MISSING_DELETE_ACCESS', 'MISSING_RENAME_ACCESS',
]));

const METADATA_REPAIR_CODES = Object.freeze(new Set([
    ...MODE_FINDING_CODES, ...IDENTITY_FINDING_CODES, ...ACL_FINDING_CODES, ...ACCESS_FINDING_CODES,
]));

// Findings no bounded metadata operation on the governed tree can safely
// resolve.  They are reported as blocked and require an Owner decision.
//
// WORLD_WRITABLE_ANCESTOR and GROUP_WRITABLE_ANCESTOR are deliberately here
// rather than in the repairable set: an ancestor is outside the governed
// authority tree (it is frequently a shared directory such as the repository
// root or a home directory), so prescribing a mode change for it would exceed
// this contract's authority.
const BLOCKING_FINDING_CODES = Object.freeze(new Set([
    'SYMLINK_IN_GOVERNED_PATH', 'NON_REGULAR_ARTIFACT', 'UNEXPECTED_FILESYSTEM_OBJECT',
    'HARDLINK_DETECTED', 'AUTHORITY_GENERATION_REPLACED', 'MISSING_REQUIRED_PATH',
    'UNOBSERVABLE_GOVERNED_PATH', 'UNEXPECTED_COMMITTED_ENTRY', 'UNEXPECTED_PACKAGE_FILE_SET',
    'UNOBSERVABLE_ANCESTOR', 'PRIVILEGED_RUNTIME_IDENTITY',
    'WORLD_WRITABLE_ANCESTOR', 'GROUP_WRITABLE_ANCESTOR',
    // A directory that could not be listed hides an unknown number of governed
    // objects.  Repairing the directory's own metadata would not produce a
    // complete plan, so the whole plan is blocked until the tree is re-audited.
    'UNOBSERVABLE_DIRECTORY_LISTING',
    // A default ACL is invisible to every other check: the directory's own mode
    // and owner can be perfectly compliant while everything the publisher
    // creates below it inherits entries this contract never authorised.  The
    // path's other metadata repairs stay plannable — they are per-finding — but
    // this hazard is escalated instead of guessed away.
    ...DEFAULT_ACL_FINDING_CODES,
]));

// chown is applied first because changing ownership can clear set-user/set-group
// bits.  The ACL is removed second and the mode set last, and that order is not
// interchangeable: while an extended ACL exists the group permission bits in
// st_mode ARE the mask, so a chmod before the removal writes the mask and leaves
// `group::` untouched — and `setfacl -b` then re-normalises `group::` from the
// mask it deletes, so the mode chmod wrote does not survive the removal.  With
// the ACL gone there is no mask left, the closing chmod sets all three triads
// directly, and the postcondition is exact by construction.
const OPERATION_RANK = Object.freeze({ CHOWN: 0, REMOVE_EXTENDED_ACL: 1, CHMOD: 2 });

function planError(code, message) {
    const error = new Error(message);
    error.code = code;
    return error;
}

// The mode a repaired object must end up with: the contract's own postcondition
// for that surface, never a mode invented here.
function exactModeFor(spec) {
    if (spec === undefined || spec === null) return null;
    return typeof spec.exact_mode === 'number' ? spec.exact_mode : null;
}

function hasAny(codesOnPath, group) {
    for (const code of codesOnPath) if (group.has(code)) return true;
    return false;
}

// Which of the bounded causes, plus the access consequences, are present on
// this path.  `removesAcl` is an input rather than a derivation because whether
// an ACL is removed at all also depends on the rollback evidence, and it forces
// the CHMOD: removing the ACL can move the mode even on a path whose observed
// mode already matched the contract, so every removal is paired with an explicit
// chmod to the postcondition.  `mode` keeps the narrower meaning — the observed
// mode itself disagreed — for the rule that decides whether an access defect has
// any metadata repair behind it.
function classifyPathDefects(codesOnPath, identityMismatch, removesAcl) {
    const modeMismatch = hasAny(codesOnPath, MODE_FINDING_CODES);
    return Object.freeze({
        chown: identityMismatch && hasAny(codesOnPath, IDENTITY_FINDING_CODES),
        chmod: modeMismatch || removesAcl,
        mode: modeMismatch,
        acl: hasAny(codesOnPath, ACL_FINDING_CODES),
        removesAcl,
        access: hasAny(codesOnPath, ACCESS_FINDING_CODES),
    });
}

function blockedForPath(defects, findings, targetMode) {
    const blocked = [];
    // A mode repair with no contract postcondition to aim at is not a bounded
    // operation, so it is escalated instead of guessed.  When the chmod exists
    // only because an ACL is being removed, the ACL finding is the one that
    // carries the missing postcondition.
    if (defects.chmod && targetMode === null) {
        const codes = defects.removesAcl ? MODE_OR_ACL_FINDING_CODES : MODE_FINDING_CODES;
        blocked.push(...findings.filter(item => codes.has(item.code)).map(item => blockedEntry(item, 'CONTRACT_HAS_NO_EXACT_MODE_FOR_THIS_SURFACE')));
    }
    // An access defect with no identity or mode cause left to repair cannot be
    // fixed by metadata at all.
    if (defects.access && !defects.chown && !defects.chmod) {
        blocked.push(...findings.filter(item => ACCESS_FINDING_CODES.has(item.code)).map(item => blockedEntry(item, 'NO_BOUNDED_METADATA_CAUSE_IDENTIFIED')));
    }
    return blocked;
}

// Removing an extended ACL deletes named entries that no mode change can bring
// back: a chmod only ever re-derives the mask from the group bits, so restoring
// uid/gid/mode afterwards would leave the named entries gone for good.  The
// operation is therefore only plannable when the exact current ACL was observed
// and can be replayed with `setfacl --set`; without that evidence it is blocked
// rather than planned with an unrecoverable rollback.
function aclRemovalBlocked(present, findings, acl) {
    if (!present) return [];
    const blockedFor = reason => findings
        .filter(item => ACL_FINDING_CODES.has(item.code))
        .map(item => blockedOperationEntry(item, 'REMOVE_EXTENDED_ACL', reason));
    // A default ACL on the same directory cannot be captured by an access-ACL
    // replay, and setfacl's treatment of default entries varies by version, so
    // the removal is not bounded by the evidence the rollback would carry.
    if (acl && acl.default_present === true) return blockedFor('DEFAULT_ACL_GOVERNS_CHILDREN');
    if (acl && acl.restorable === true) return [];
    const reason = !acl || acl.available === false
        ? 'ACL_ROLLBACK_EVIDENCE_MISSING'
        : 'ACL_ROLLBACK_EVIDENCE_INCOMPLETE';
    return blockedFor(reason);
}

function blockedOperationEntry(item, operation, reasonCode) {
    return Object.freeze({
        surface_id: item.surface_id, path: item.path, operation, reason_code: reasonCode, message: item.message,
        auto_repairable: false, required_action: 'OWNER_DECISION_AND_MANUAL_EVIDENCE_REVIEW',
    });
}

// The rollback payload for one path.  `acl` is only attached when the observed
// ACL is complete, and its `entries` string is the exact `setfacl --set` form
// that reproduces the pre-repair access ACL byte for byte.
function restorableAclPayload(acl) {
    if (!acl || acl.restorable !== true) return null;
    const parts = [`u::${acl.user}`, `g::${acl.group}`, `o::${acl.other}`, `m::${acl.mask}`];
    for (const qualifier of Object.keys(acl.named_user_perms).sort()) parts.push(`u:${qualifier}:${acl.named_user_perms[qualifier]}`);
    for (const qualifier of Object.keys(acl.named_group_perms).sort()) parts.push(`g:${qualifier}:${acl.named_group_perms[qualifier]}`);
    return Object.freeze({
        entries: parts.join(','),
        user: acl.user, group: acl.group, other: acl.other, mask: acl.mask,
        named_user_perms: acl.named_user_perms, named_group_perms: acl.named_group_perms,
        restore_command: `setfacl --set '${parts.join(',')}' -- <path>`,
        mask_note: 'setfacl --set rewrites the mask, so the mode must be re-applied after the ACL is restored',
    });
}

function blockedEntry(item, requiredAction = 'OWNER_DECISION_AND_MANUAL_EVIDENCE_REVIEW') {
    return Object.freeze({
        surface_id: item.surface_id, path: item.path, reason_code: item.code, message: item.message,
        auto_repairable: false, required_action: requiredAction,
    });
}

// Plan one governed path as a unit.  The required end state depends on every
// finding on that path, not on one at a time, so `post` is identical across all
// operations emitted for the path and is a true postcondition rather than a
// restatement of a single finding.
function planPath(entry, runtimeIdentity) {
    const observation = observeObject(entry.path);
    const findings = entry.findings;
    if (entry.spec === undefined || !observation.observable || observation.is_symbolic_link) {
        // Without a contract surface there is no postcondition to repair toward,
        // and a re-observed symlink must never be followed to its target.
        const action = entry.spec === undefined ? 'NO_CONTRACT_SURFACE_SPEC_FOR_THIS_PATH' : 'OWNER_DECISION_AND_MANUAL_EVIDENCE_REVIEW';
        return { operations: [], blocked: findings.map(item => blockedEntry(item, action)) };
    }
    const codesOnPath = new Set(findings.map(item => item.code));
    const targetMode = exactModeFor(entry.spec);
    const identityMismatch = observation.uid !== runtimeIdentity.uid || observation.gid !== runtimeIdentity.gid;
    // An ACL removal without rollback evidence blocks that one operation only:
    // the identity and mode repairs on the same path stay plannable, because
    // restoring uid/gid/mode does fully undo them.  It also decides whether this
    // path is planned as removing an ACL at all, which is what forces the CHMOD.
    const blockedOperations = aclRemovalBlocked(hasAny(codesOnPath, ACL_FINDING_CODES), findings, entry.acl);
    const defects = classifyPathDefects(codesOnPath, identityMismatch, hasAny(codesOnPath, ACL_FINDING_CODES) && blockedOperations.length === 0);
    const blocked = blockedForPath(defects, findings, targetMode);
    if (blocked.length > 0) return { operations: [], blocked, blockedOperations: [] };

    const post = Object.freeze({
        uid: defects.chown ? runtimeIdentity.uid : observation.uid,
        gid: defects.chown ? runtimeIdentity.gid : observation.gid,
        mode: defects.chmod ? targetMode : observation.mode,
        mode_source: defects.chmod ? 'CONTRACT_POSTCONDITION' : 'PRESERVED',
        mode_applied_last: true,
        unchanged_content: true,
    });
    const common = Object.freeze({
        surface_id: entry.spec.surface_id,
        path: entry.path,
        reason_codes: Object.freeze([...codesOnPath].sort()),
        pre: Object.freeze({ uid: observation.uid, gid: observation.gid, mode: observation.mode, dev: observation.dev, ino: observation.ino, nlink: observation.nlink }),
        post,
        metadata_only: true,
        content_impact: 'NONE',
        content_bytes_must_be_identical: true,
        path_resolution_rule: 're-open with O_NOFOLLOW and verify dev/ino match `pre` before applying; abort on mismatch',
        acl_mask_caveat: 'while an extended ACL exists the mode group bits ARE the mask, and setfacl -b re-normalises `group::` from the mask it deletes; the ACL removal therefore runs before the closing CHMOD, which is what makes `post.mode` exact',
        elevated_privilege_required: observation.uid !== process.getuid() || observation.gid !== process.getgid(),
        owner_authorization_required: true,
    });
    const planned = [{ operation: 'CHOWN', rank: OPERATION_RANK.CHOWN, applies: defects.chown },
        // Removing an extended ACL can only ever take access away from the named
        // entries, which is the safe direction: the exact mode is meant to be the
        // whole policy.  The base `group::` entry is re-normalised by the removal
        // itself, which is why the mode is set afterwards.
        { operation: 'REMOVE_EXTENDED_ACL', rank: OPERATION_RANK.REMOVE_EXTENDED_ACL, applies: defects.removesAcl },
        { operation: 'CHMOD', rank: OPERATION_RANK.CHMOD, applies: defects.chmod }];
    const aclPayload = restorableAclPayload(entry.acl);
    const operations = planned.filter(item => item.applies).map(item => Object.freeze({
        ...common,
        operation: item.operation,
        rank: item.rank,
        // The ACL to put back travels with the operation that takes it away.
        // CHMOD does not carry it: in the apply direction there is no ACL left
        // by then, and in rollback the ACL is restored after the mode.
        restore_acl: item.operation === 'REMOVE_EXTENDED_ACL' ? aclPayload : null,
    }));
    return { operations, blocked: [], blockedOperations };
}

function orderOperations(entries) {
    return entries.sort((left, right) => {
        if (left.path !== right.path) return left.path.localeCompare(right.path);
        return left.rank - right.rank;
    });
}

function groupByPath(violations) {
    const groups = new Map();
    for (const item of violations) {
        if (!groups.has(item.path)) groups.set(item.path, { path: item.path, findings: [] });
        groups.get(item.path).findings.push(item);
    }
    return groups;
}

function surfaceSpecIndex(report) {
    const index = new Map();
    for (const evaluation of report.surfaces || []) {
        if (evaluation && evaluation.spec) index.set(evaluation.spec.path, evaluation.spec);
    }
    return index;
}

function planStatus(operations, blocked) {
    if (operations.length === 0 && blocked.length === 0) return 'NOT_REQUIRED';
    if (operations.length === 0) return 'BLOCKED';
    if (blocked.length > 0) return 'PARTIAL_BLOCKED';
    if (operations.some(operation => operation.elevated_privilege_required)) return 'READY_WITH_ELEVATED_PRIVILEGE';
    return 'READY';
}

function buildRemediationPlan(report, { generatedAt = null } = {}) {
    if (report === null || typeof report !== 'object') throw planError('INVALID_PLAN_INPUT', 'a contract report is required');
    const violations = (report.findings || []).filter(item => item.severity === SEVERITY.VIOLATION);
    // Fail closed on the classification: a violation this module does not
    // recognise as a bounded metadata repair is blocked, never dropped.
    const blocked = violations
        .filter(item => BLOCKING_FINDING_CODES.has(item.code) || !METADATA_REPAIR_CODES.has(item.code))
        .map(item => blockedEntry(item));
    const specs = surfaceSpecIndex(report);
    const aclState = report.acl_state || {};
    const blockedOperations = [];
    const candidates = [];
    for (const group of groupByPath(violations.filter(item => METADATA_REPAIR_CODES.has(item.code) && !BLOCKING_FINDING_CODES.has(item.code))).values()) {
        const planned = planPath({ ...group, spec: specs.get(group.path), acl: aclState[group.path] || null }, report.runtime_identity);
        blocked.push(...planned.blocked);
        blockedOperations.push(...(planned.blockedOperations || []));
        candidates.push(...planned.operations);
    }
    const operations = orderOperations(candidates).map((operation, index) => Object.freeze({ ...operation, sequence: index + 1 }));
    return Object.freeze({
        schema_version: PLAN_SCHEMA_VERSION,
        contract_version: report.contract_version,
        generated_at: generatedAt,
        report_status: report.status,
        // Both kinds of blockage count toward the overall status.  A blocked
        // ACL removal is a repair this plan cannot complete, so reporting
        // READY — or NOT_REQUIRED when it was the only operation needed —
        // would let a caller driving off `status` believe the tree was fully
        // repairable when part of it needs an Owner decision.
        status: planStatus(operations, [...blocked, ...blockedOperations]),
        runtime_identity: report.runtime_identity,
        targets: report.targets,
        applies_content_writes: false,
        mutating: false,
        execution_authorized: false,
        execution_requires: 'SEPARATE_OWNER_AUTHORIZED_PHASE_B',
        elevated_privilege_required: operations.some(operation => operation.elevated_privilege_required),
        operations: Object.freeze(operations),
        blocked_operations: Object.freeze([...blocked, ...blockedOperations]),
        preconditions: Object.freeze([
            'the accepted authority identity is unchanged and the exact main revision matches the authorization',
            'the runtime uid/gid executing the repair equals the uid/gid that will cold-load the authority',
            'the governed roots are on the expected filesystem device',
            'no Stage D run is active (run lock absent or already reconciled) and no scheduler or provider request is enabled',
            'the pre-repair content SHA256 manifest and the full governed path metadata manifest have been captured outside the mutated tree',
        ]),
        postconditions: Object.freeze([
            'every governed surface satisfies its exact mode and identity postcondition',
            'CONTENT_BYTES_AFTER equals CONTENT_BYTES_BEFORE for every governed artifact',
            'an ordinary cold-load by the runtime identity reproduces the accepted head transaction, authority state hash, observation count, STORE SHA256 and allocation authority SHA256 exactly',
            'a fresh process boundary reproduces the same cold-load result',
        ]),
        // Rollback is the exact inverse of the apply order, so it is emitted in
        // reverse: the mode is restored first, the ACL second, and the owner
        // last, since chown can clear set-user/set-group bits.  Restoring the
        // ACL through `setfacl --set` rewrites the mask, and the recorded mask is
        // exactly the mode's group bits, so the mode is still the original one
        // once the ACL is back.  `sequence` still names the apply step each entry
        // undoes.
        rollback: Object.freeze(operations.slice().reverse().map(operation => Object.freeze({
            sequence: operation.sequence, path: operation.path, operation: operation.operation, content_impact: 'NONE',
            restore: Object.freeze({
                uid: operation.pre.uid, gid: operation.pre.gid, mode: operation.pre.mode, dev: operation.pre.dev, ino: operation.pre.ino,
                acl: operation.restore_acl || null,
                acl_note: operation.restore_acl
                    ? 'the recorded ACL is the exact pre-repair access ACL; a mode-only restore would leave removed named entries gone'
                    : 'no extended ACL was present on this path, so the mode and identity restore is complete',
            }),
        }))),
        forbidden_operations: Object.freeze([
            'any content write, rewrite, truncation or re-publication of a governed artifact',
            'recursive chmod -R or chown -R over the authority tree',
            'creating, deleting or relocating a transaction package, STORE.json or the allocation authority',
            'applying any operation whose pre-observation no longer matches at apply time',
        ]),
    });
}

module.exports = {
    PLAN_SCHEMA_VERSION, BLOCKING_FINDING_CODES, METADATA_REPAIR_CODES,
    MODE_FINDING_CODES, IDENTITY_FINDING_CODES, ACL_FINDING_CODES, DEFAULT_ACL_FINDING_CODES,
    ACCESS_FINDING_CODES, buildRemediationPlan, planStatus,
};
