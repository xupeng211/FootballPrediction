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
]));

// chown is applied first because changing ownership can clear set-user/set-group
// bits, chmod second because it re-derives the ACL mask from the group bits, and
// ACL removal last so the surviving group bits stay exactly as chmod set them.
const OPERATION_RANK = Object.freeze({ CHOWN: 0, CHMOD: 1, REMOVE_EXTENDED_ACL: 2 });

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

// Which of the three bounded causes, plus the access consequences, are present
// on this path.
function classifyPathDefects(codesOnPath, identityMismatch) {
    return Object.freeze({
        chown: identityMismatch && hasAny(codesOnPath, IDENTITY_FINDING_CODES),
        chmod: hasAny(codesOnPath, MODE_FINDING_CODES),
        acl: hasAny(codesOnPath, ACL_FINDING_CODES),
        access: hasAny(codesOnPath, ACCESS_FINDING_CODES),
    });
}

function blockedForPath(defects, findings, targetMode) {
    const blocked = [];
    // A mode repair with no contract postcondition to aim at is not a bounded
    // operation, so it is escalated instead of guessed.
    if (defects.chmod && targetMode === null) {
        blocked.push(...findings.filter(item => MODE_FINDING_CODES.has(item.code)).map(item => blockedEntry(item, 'CONTRACT_HAS_NO_EXACT_MODE_FOR_THIS_SURFACE')));
    }
    // An access defect with no identity or mode cause left to repair cannot be
    // fixed by metadata at all.
    if (defects.access && !defects.chown && !defects.chmod) {
        blocked.push(...findings.filter(item => ACCESS_FINDING_CODES.has(item.code)).map(item => blockedEntry(item, 'NO_BOUNDED_METADATA_CAUSE_IDENTIFIED')));
    }
    return blocked;
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
    const defects = classifyPathDefects(codesOnPath, identityMismatch);
    const blocked = blockedForPath(defects, findings, targetMode);
    if (blocked.length > 0) return { operations: [], blocked };

    const post = Object.freeze({
        uid: defects.chown ? runtimeIdentity.uid : observation.uid,
        gid: defects.chown ? runtimeIdentity.gid : observation.gid,
        mode: defects.chmod ? targetMode : observation.mode,
        mode_source: defects.chmod ? 'CONTRACT_POSTCONDITION' : 'PRESERVED',
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
        acl_mask_caveat: 'chmod re-derives the ACL mask from the group bits, so CHOWN and CHMOD must be applied before REMOVE_EXTENDED_ACL',
        elevated_privilege_required: observation.uid !== process.getuid() || observation.gid !== process.getgid(),
        owner_authorization_required: true,
    });
    const planned = [{ operation: 'CHOWN', rank: OPERATION_RANK.CHOWN, applies: defects.chown },
        { operation: 'CHMOD', rank: OPERATION_RANK.CHMOD, applies: defects.chmod },
        // Removing an extended ACL can only ever take access away, which is the
        // safe direction: the exact mode is meant to be the whole policy.
        { operation: 'REMOVE_EXTENDED_ACL', rank: OPERATION_RANK.REMOVE_EXTENDED_ACL, applies: defects.acl }];
    return { operations: planned.filter(item => item.applies).map(item => Object.freeze({ ...common, operation: item.operation, rank: item.rank })), blocked: [] };
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
    const candidates = [];
    for (const group of groupByPath(violations.filter(item => METADATA_REPAIR_CODES.has(item.code) && !BLOCKING_FINDING_CODES.has(item.code))).values()) {
        const planned = planPath({ ...group, spec: specs.get(group.path) }, report.runtime_identity);
        blocked.push(...planned.blocked);
        candidates.push(...planned.operations);
    }
    const operations = orderOperations(candidates).map((operation, index) => Object.freeze({ ...operation, sequence: index + 1 }));
    return Object.freeze({
        schema_version: PLAN_SCHEMA_VERSION,
        contract_version: report.contract_version,
        generated_at: generatedAt,
        report_status: report.status,
        status: planStatus(operations, blocked),
        runtime_identity: report.runtime_identity,
        targets: report.targets,
        applies_content_writes: false,
        mutating: false,
        execution_authorized: false,
        execution_requires: 'SEPARATE_OWNER_AUTHORIZED_PHASE_B',
        elevated_privilege_required: operations.some(operation => operation.elevated_privilege_required),
        operations: Object.freeze(operations),
        blocked_operations: Object.freeze(blocked),
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
        rollback: Object.freeze(operations.map(operation => Object.freeze({
            sequence: operation.sequence, path: operation.path, operation: operation.operation, content_impact: 'NONE',
            restore: Object.freeze({ uid: operation.pre.uid, gid: operation.pre.gid, mode: operation.pre.mode, dev: operation.pre.dev, ino: operation.pre.ino }),
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
    MODE_FINDING_CODES, IDENTITY_FINDING_CODES, ACL_FINDING_CODES, ACCESS_FINDING_CODES,
    buildRemediationPlan, planStatus,
};
