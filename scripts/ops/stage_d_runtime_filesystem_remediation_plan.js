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

const { SEVERITY, observeObject, walkAncestry } = require('./stage_d_runtime_filesystem_permission_contract');

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

// ---------------------------------------------------------------------------
// Phase B identity model.  Three roles, deliberately separated, because the
// first authorized Phase B preflight proved that collapsing them into one
// identity produces a contract that cannot be executed at all.
//
//   TARGET_RUNTIME_IDENTITY      the ordinary identity that must own the
//                                repaired surfaces and cold-load the authority.
//                                It never gains a capability, and it is the
//                                ONLY identity whose cold-load counts as proof.
//   REPAIR_EXECUTOR_IDENTITY     a temporary bounded privileged host principal
//                                that applies exactly the emitted operations and
//                                then loses its privilege.  It is never the
//                                proof identity.
//   PRE_REPAIR_CONTENT_EVIDENCE_READER
//                                the identity allowed to collect the PRE
//                                content hash.  It prefers the ordinary runtime
//                                read and falls back to a privileged READ-ONLY
//                                read only for an artifact the target runtime
//                                genuinely cannot read.
//
// The canonical policy is an explicit bounded privileged executor, NOT a
// capability injected into the Stage D runtime identity.  Adding CAP_CHOWN or
// CAP_FOWNER to the identity that runs Stage D would make every future
// publication and cold-load run with a permanent capability the contract never
// described, which is a strictly worse defect than the one Phase B repairs.
const REPAIR_EXECUTOR_POLICY = 'BOUNDED_PRIVILEGED_HOST_EXECUTOR';
const RUNTIME_CAPABILITY_INJECTION_POLICY = 'FORBIDDEN';

// The only mutation classes a privileged executor may be handed.  This is the
// planner's own operation set, restated as policy so a reader does not have to
// infer the bound from the operations array.
const ALLOWED_PRIVILEGED_OPERATION_CLASSES = Object.freeze(['CHOWN', 'REMOVE_EXTENDED_ACL', 'CHMOD']);

// PRE content evidence provenance.  Every governed artifact needs a PRE hash,
// and the source of that hash is recorded so a privileged pre-read can never be
// mistaken for evidence that the ordinary runtime could read the artifact.
const PRE_CONTENT_EVIDENCE_SOURCE = Object.freeze({
    ORDINARY: 'ORDINARY_RUNTIME_READ',
    PRIVILEGED: 'PRIVILEGED_READ_ONLY_EVIDENCE',
});

// A PRE_CONTENT_SHA256 is a lowercase hex SHA-256 digest — the same shape the
// audit CLI publishes in its `content_hashes` manifest.  It is required: an
// evidence record without one is not content evidence, and a source without a
// digest would let the set pass as READY while proving nothing per artifact.
const PRE_CONTENT_SHA256_RE = /^[0-9a-f]{64}$/;

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

// Why a path cannot be planned at all, independent of which findings it
// carries.  Each of these is a refusal rather than a repair: there is no
// postcondition to repair toward, or the object the report described is no
// longer the object at the path.  The refusals are decided from the path's own
// spec and from the fresh observation of it, never from the finding list: a
// finding that blocks the whole path is a blocking code and is filtered out of
// the group reaching `planPath`, so a guard that read findings would miss the
// hazard precisely when the path also carries a repairable defect.
function pathGuard(entry, observation) {
    // Without a contract surface there is no required end state.
    if (entry.spec === undefined) return 'NO_CONTRACT_SURFACE_SPEC_FOR_THIS_PATH';
    // A re-observed symlink must never be followed to its target.
    if (!observation.observable || observation.is_symbolic_link) return 'OWNER_DECISION_AND_MANUAL_EVIDENCE_REVIEW';
    // A different device or inode means every conclusion drawn from the report —
    // the ACL to replay, the content hash, the mode — belongs to an object that
    // is no longer here.  The apply-time `pre` check cannot catch this: it
    // compares against a fresh observation of the same replaced object.
    if (entry.observed && entry.observed.observable && (observation.dev !== entry.observed.dev || observation.ino !== entry.observed.ino)) {
        return 'OBJECT_REPLACED_SINCE_OBSERVATION';
    }
    // A hardlinked object shares its inode with every other name it has, so a
    // chmod or chown applied through this governed path also changes metadata
    // reachable at names this contract has no authority over.  The report
    // records this as HARDLINK_DETECTED, but that finding is a blocking code and
    // is therefore filtered out of the group handed to `planPath` before this
    // runs — so a path carrying a hardlink *and* a MODE_MISMATCH would otherwise
    // still produce a CHMOD, and a CHOWN where the identity also disagreed.  The
    // refusal is read from the fresh observation rather than from the finding so
    // that it does not depend on which findings were selected for planning, and
    // so that it also covers a link created after the audit.  The condition is
    // the contract's own: a *file* with a link count other than one.  For a
    // directory a count above one is ordinary, not a hardlink.
    if (observation.is_file && observation.nlink !== 1) return 'HARDLINK_IN_GOVERNED_PATH_UNPLANNABLE';
    // A path is only as safe as the directories it is reached through.  The
    // contract reports an ancestor that is not a real directory as
    // SYMLINK_IN_GOVERNED_PATH, but that finding is a blocking code and is
    // filtered out of the group reaching this function, so a package file
    // *below* such an ancestor arrives here carrying nothing but a
    // MODE_MISMATCH — while its path actually resolves to an object outside the
    // governed tree.  Nothing else on this path can see that: the re-observation
    // above is an lstat of the leaf, the emitted `path_resolution_rule` opens
    // with O_NOFOLLOW, which protects the last component only, and the apply-time
    // `pre` dev/ino check would compare the external object against itself and
    // pass.  The ancestry is therefore re-walked from fresh observations, the
    // same walk the contract's own ancestor rule refuses on, and a component
    // that is not a real directory refuses every path beneath it.
    for (const ancestor of walkAncestry(observation.path)) {
        if (!ancestor.observable || ancestor.is_symbolic_link || !ancestor.is_directory) return 'SYMLINK_IN_GOVERNED_PATH_UNPLANNABLE';
    }
    return null;
}

// Plan one governed path as a unit.  The required end state depends on every
// finding on that path, not on one at a time, so `post` is identical across all
// operations emitted for the path and is a true postcondition rather than a
// restatement of a single finding.
function planPath(entry, runtimeIdentity) {
    const observation = observeObject(entry.path);
    const findings = entry.findings;
    const guard = pathGuard(entry, observation);
    if (guard !== null) return { operations: [], blocked: findings.map(item => blockedEntry(item, guard)) };
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
        // Measured against the TARGET runtime identity, never against whoever
        // happened to run the planner.  The gate this flag feeds — privileged
        // mutation is permitted only for an operation carrying it — is sound
        // only if the flag answers "can the identity that must own and
        // cold-load this object perform this operation itself?".  Comparing
        // against process.getuid() answers a different question: an operator who
        // ran the planner as root would see the flag cleared on every root-owned
        // object, and the plan would read as self-repairable precisely in the
        // state that must never be silently repairable.
        elevated_privilege_required: observation.uid !== runtimeIdentity.uid || observation.gid !== runtimeIdentity.gid,
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

// What the report observed for each governed path.  The plan re-observes every
// path it plans, and the identity of that second observation has to be the
// object the findings are about: a replacement between the audit and the plan
// would otherwise bind the old object's ACL and hashes to the new object's
// `pre`, and the apply-time `pre` check cannot see that it is comparing the
// wrong pair.
function surfaceObservationIndex(report) {
    const index = new Map();
    for (const evaluation of report.surfaces || []) {
        if (evaluation && evaluation.spec) index.set(evaluation.spec.path, { spec: evaluation.spec, observed: evaluation.observation });
    }
    return index;
}

// Which evidence source the PRE content hash for one governed artifact is
// allowed to come from.  Returns the source, or null to mean BLOCKED — never a
// silent omission and never a guess.
//
// The input is one entry of the evidence manifest a Phase B execution collects,
// and it reuses the vocabulary the audit CLI already emits rather than inventing
// a parallel one:
//
//   `sha256`
//        the PRE_CONTENT_SHA256 itself, and the reason this function exists: it
//        is required for EVERY artifact and for BOTH evidence sources.  A
//        permitted reader with no digest to show for it is not content evidence
//        at all, and accepting one — a `HASHED` status, or an EACCES artifact
//        whose preconditions hold — would leave the set READY while carrying no
//        per-artifact byte proof, which is precisely the hole the PRE/POST
//        invariant exists to close.
//   `status` and `code`
//        the same pair the CLI's `content_hashes` manifest carries for every
//        governed artifact: `{status: 'HASHED', sha256, size}` when the read
//        succeeded, and `{status: 'NOT_READABLE', code}` — plus `ABSENT`,
//        `NOT_OBSERVABLE` and `NOT_REGULAR_FILE` — when it did not, so an
//        artifact the audit could not read keeps its place in the manifest
//        instead of dropping out of it.
//   `path`, `dev`, `ino`
//        which artifact the record is about, and which object.  These are the
//        only artifact-side fields the privileged fallback trusts, and only to
//        look the artifact up in the plan: the authorization itself is the
//        plan's, never the record's.
//
// What is NOT an input is any assertion about the plan.  Whether the path is
// governed, whether this plan repairs it, whether it is symlink-free, whether
// its ancestors are real directories, and which object sits there are all read
// from `plan.governed_artifacts` — the planner's own statement, derived from the
// report's observations and the operations it emitted.  A caller-supplied
// `permission_defect_repaired_by_this_plan: true` would make the confinement a
// claim about the caller: the same record for an arbitrary path, with the same
// invented fields, would classify identically, and the fallback would authorize
// a privileged read of anything at all.
//
// The ordinary runtime read is tried first and is the only source that also
// demonstrates the runtime could read the artifact.  The privileged fallback
// exists because the artifact Phase B repairs is precisely the one the ordinary
// runtime cannot read: without it, an EACCES artifact could carry no PRE hash at
// all, and the contract's PRE/POST byte-equality proof would have a hole exactly
// where the defect is.  Every bound is therefore required before the fallback is
// allowed, and a failure this plan does not repair — a path outside the plan, a
// surface with no operation, a missing object, a symlink, a different dev/inode
// — is blocked rather than escalated.
function governedArtifactIndex(plan) {
    if (!plan || typeof plan !== 'object' || !Array.isArray(plan.governed_artifacts)) return null;
    const index = new Map();
    for (const entry of plan.governed_artifacts) {
        if (entry && typeof entry.path === 'string') index.set(entry.path, entry);
    }
    return index;
}

function preContentEvidenceSourceFor(artifact = {}, plan = null) {
    // The digest gates every artifact and both sources: without it there is no
    // PRE_CONTENT_SHA256 to compare against POST, so no source may be accepted.
    if (!PRE_CONTENT_SHA256_RE.test(artifact.sha256 || '')) return null;
    // And the plan gates every artifact too.  Everything the privileged fallback
    // is confined by — that the path is governed, that this plan repairs it, that
    // the object is the one the report observed and is not a symlink — is read
    // out of the plan, never out of the evidence record's own account of itself.
    // A record that asserted those facts about a path the plan never mentioned,
    // or about an object the plan did not observe, would otherwise be
    // indistinguishable from a real one, and "the privileged pre-read is
    // confined to the artifacts this plan repairs" would be a claim about the
    // caller rather than a property of the contract.
    const governed = governedArtifactIndex(plan);
    if (governed === null) return null;
    const entry = governed.get(artifact.path);
    if (entry === undefined || entry.symlink_free !== true) return null;
    if (artifact.status === 'HASHED') return PRE_CONTENT_EVIDENCE_SOURCE.ORDINARY;
    if (artifact.status !== 'NOT_READABLE') return null;
    if (artifact.code !== 'EACCES') return null;
    // Only a path this plan actually repairs may be read with elevated
    // privilege, and only for the object the plan observed: the record has to
    // name the same device and inode, so one about a different object at the
    // same path cannot inherit the authorization by landing on the name.
    if (entry.repaired_by.length === 0) return null;
    if (!Number.isInteger(entry.dev) || !Number.isInteger(entry.ino)) return null;
    if (artifact.dev !== entry.dev || artifact.ino !== entry.ino) return null;
    return PRE_CONTENT_EVIDENCE_SOURCE.PRIVILEGED;
}

// The whole-artifact-set verdict for PRE content evidence.  The contract's
// content proof is per artifact and universal — PRE_SHA256 == POST_SHA256 for
// every governed artifact — so one artifact with no permitted evidence source
// makes the set unproven rather than partially proven, and the verdict is
// BLOCKED.  Classification only: this function validates the digests a
// pre-repair manifest already carries and decides whether it is complete enough
// to authorize a repair.  It never reads a hash out of a file, opens a governed
// path or mutates anything, and a manifest entry without a well-formed digest is
// blocked rather than treated as evidence with an unstated value.
//
// The plan is a required argument for the same reason: the evidence manifest is
// checked against the plan that repairs it, so a manifest offered without one
// has nothing to be authorized against and is BLOCKED rather than vacuously
// READY.
function preContentEvidenceVerdict(artifacts = [], plan = null) {
    if (!Array.isArray(artifacts)) throw planError('INVALID_PRE_CONTENT_EVIDENCE_INPUT', 'governed artifacts must be an array');
    const governed = governedArtifactIndex(plan);
    if (governed === null) {
        return Object.freeze({
            status: 'BLOCKED',
            reason: 'a plan is required: an artifact is authorized by the plan that repairs it, never by the evidence record alone',
            governed_artifacts_required: 0,
            permitted: 0,
            classified: Object.freeze([]),
            blocked: Object.freeze([]),
            missing_pre_evidence_result: 'BLOCKED',
        });
    }
    const required = artifacts.length;
    const classified = artifacts.map(artifact => Object.freeze({
        path: artifact && artifact.path ? artifact.path : null,
        evidence_source: preContentEvidenceSourceFor(artifact || {}, plan),
        pre_content_sha256: PRE_CONTENT_SHA256_RE.test((artifact || {}).sha256 || '') ? artifact.sha256 : null,
    }));
    const blocked = classified.filter(entry => entry.evidence_source === null);
    return Object.freeze({
        status: blocked.length > 0 ? 'BLOCKED' : 'READY',
        reason: null,
        governed_artifacts_required: required,
        permitted: required - blocked.length,
        // Every artifact is reported, not only the refused ones, so a READY
        // verdict can be read as the per-artifact statement it is: each entry
        // names the source that was accepted and the PRE_CONTENT_SHA256 it was
        // accepted for.  A READY with an unreported digest would put the
        // invariant out of reach of the caller checking it.
        classified: Object.freeze(classified),
        blocked: Object.freeze(blocked),
        missing_pre_evidence_result: 'BLOCKED',
    });
}

function planStatus(operations, blocked) {
    if (operations.length === 0 && blocked.length === 0) return 'NOT_REQUIRED';
    if (operations.length === 0) return 'BLOCKED';
    if (blocked.length > 0) return 'PARTIAL_BLOCKED';
    if (operations.some(operation => operation.elevated_privilege_required)) return 'READY_WITH_ELEVATED_PRIVILEGE';
    return 'READY';
}

// The plan's own statement of what is governed, and what it repairs.  This is
// the authority the PRE content evidence is checked against: the evidence check
// must not be able to authorize itself, so every fact that confines the
// privileged fallback is derived here — from the report's per-surface
// observations and from the operations this plan actually emitted — rather than
// accepted from the evidence record.
function governedArtifactEntries(report, operations) {
    const repaired = new Map();
    for (const operation of operations) {
        if (!repaired.has(operation.path)) repaired.set(operation.path, new Set());
        repaired.get(operation.path).add(operation.operation);
    }
    return (report.surfaces || [])
        .filter(evaluation => evaluation && evaluation.spec && typeof evaluation.spec.path === 'string')
        .map(evaluation => {
            const observation = evaluation.observation || {};
            return Object.freeze({
                path: evaluation.spec.path,
                surface_id: evaluation.spec.surface_id,
                // The object the report observed at this path.  A privileged
                // read is authorized for this dev/inode or for nothing.
                dev: Number.isInteger(observation.dev) ? observation.dev : null,
                ino: Number.isInteger(observation.ino) ? observation.ino : null,
                // The planner refuses a symlinked governed path outright, so a
                // surface still listed here is one it re-observed as a real
                // object; the flag is restated for the evidence check to read.
                symlink_free: observation.observable === true && observation.is_symbolic_link !== true,
                repaired_by: Object.freeze([...repaired.get(evaluation.spec.path) || []].sort()),
            });
        });
}

function buildRemediationPlan(report, { generatedAt = null } = {}) {
    if (report === null || typeof report !== 'object') throw planError('INVALID_PLAN_INPUT', 'a contract report is required');
    const violations = (report.findings || []).filter(item => item.severity === SEVERITY.VIOLATION);
    // Fail closed on the classification: a violation this module does not
    // recognise as a bounded metadata repair is blocked, never dropped.
    const blocked = violations
        .filter(item => BLOCKING_FINDING_CODES.has(item.code) || !METADATA_REPAIR_CODES.has(item.code))
        .map(item => blockedEntry(item));
    const specs = surfaceObservationIndex(report);
    const aclState = report.acl_state || {};
    const blockedOperations = [];
    const candidates = [];
    for (const group of groupByPath(violations.filter(item => METADATA_REPAIR_CODES.has(item.code) && !BLOCKING_FINDING_CODES.has(item.code))).values()) {
        const known = specs.get(group.path) || {};
        const planned = planPath({ ...group, spec: known.spec, observed: known.observed, acl: aclState[group.path] || null }, report.runtime_identity);
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
        // The ordinary identity that must own the repaired surfaces and perform
        // the cold-load proof.  Named separately from the executor so no caller
        // can read the plan as "the repair runs as this identity".
        target_runtime_identity: report.runtime_identity,
        targets: report.targets,
        // Which artifacts this plan can speak for, and what it does to each.
        // The PRE content evidence is validated against this list, so the bound
        // on the privileged pre-read is a property of the plan rather than a
        // promise made by whoever assembled the evidence manifest.
        governed_artifacts: Object.freeze(governedArtifactEntries(report, operations)),
        // Which identity may apply this plan, and what it may not do with it.
        // `elevated_privilege_required` on an operation is the ONLY thing that
        // authorizes privilege for that operation; a caller may not widen this
        // to the whole plan.
        repair_executor_policy: Object.freeze({
            policy: REPAIR_EXECUTOR_POLICY,
            owner_authorization_required: true,
            exact_plan_only: true,
            elevated_privilege_authorized_by: 'SEPARATE_OWNER_AUTHORIZED_PHASE_B',
            allowed_operation_classes: ALLOWED_PRIVILEGED_OPERATION_CLASSES,
            privileged_permitted_only_for: 'operations carrying elevated_privilege_required=true',
            recursive_mutation_allowed: false,
            arbitrary_path_allowed: false,
            unrestricted_root_shell_allowed: false,
            privilege_persistence_allowed: false,
            runtime_capability_injection: RUNTIME_CAPABILITY_INJECTION_POLICY,
            executor_may_become_proof_identity: false,
        }),
        // How the PRE content hash for each governed artifact is allowed to be
        // obtained.  A privileged read is evidence about the bytes only; it is
        // never evidence about the ordinary runtime's access.
        pre_content_evidence_policy: Object.freeze({
            preferred_reader: 'TARGET_RUNTIME_IDENTITY',
            fallback_evidence_source: PRE_CONTENT_EVIDENCE_SOURCE.PRIVILEGED,
            ordinary_evidence_source: PRE_CONTENT_EVIDENCE_SOURCE.ORDINARY,
            eacces_fallback: PRE_CONTENT_EVIDENCE_SOURCE.PRIVILEGED,
            fallback_permitted_only_for: 'a governed artifact the target runtime identity cannot read, whose read failure is the permission defect this plan repairs',
            privileged_reader_may_mutate: false,
            privileged_read_may_satisfy_runtime_access_proof: false,
            every_governed_artifact_requires_pre_sha256: true,
            require_dev_inode_binding: true,
            missing_pre_evidence_result: 'BLOCKED',
            post_repair_hasher: 'TARGET_RUNTIME_IDENTITY',
            invariant: 'PRE_SHA256 == POST_SHA256 for every governed artifact',
        }),
        applies_content_writes: false,
        mutating: false,
        execution_authorized: false,
        execution_requires: 'SEPARATE_OWNER_AUTHORIZED_PHASE_B',
        elevated_privilege_required: operations.some(operation => operation.elevated_privilege_required),
        operations: Object.freeze(operations),
        blocked_operations: Object.freeze([...blocked, ...blockedOperations]),
        preconditions: Object.freeze([
            'the accepted authority identity is unchanged and the exact main revision matches the authorization',
            // The TARGET runtime identity is the ordinary uid/gid that must
            // cold-load the authority AFTER repair.  It is not required to be
            // the identity that executes the mutation: a root-owned governed
            // object cannot be repaired by the identity that cannot read it, so
            // requiring the two to be equal would forbid every operation this
            // planner emits and leave the defect unrepairable by construction.
            'the target runtime identity is the ordinary uid/gid that must cold-load the authority after repair, and it must not acquire a persistent capability in order to do so',
            'metadata mutation is performed by a separately bounded privileged host executor, only when the operation it is applying carries elevated_privilege_required=true, and only under a separate Owner-authorized Phase B authorization',
            'the repair executor does not become the proof identity: privileged success is never accepted as evidence that the target runtime identity can cold-load the authority',
            'the governed roots are on the expected filesystem device',
            'no Stage D run is active (run lock absent or already reconciled) and no scheduler or provider request is enabled',
            'the pre-repair content SHA256 manifest and the full governed path metadata manifest have been captured outside the mutated tree, with every governed artifact carrying a PRE hash whose evidence source is recorded',
            'the final operational access is proved only by the target runtime identity, by an ordinary cold-load and by a fresh-process cold-load',
        ]),
        postconditions: Object.freeze([
            'every governed surface satisfies its exact mode and identity postcondition',
            'PRE_SHA256 equals POST_SHA256 for every governed artifact, so CONTENT_BYTES_AFTER equals CONTENT_BYTES_BEFORE',
            'the POST manifest requires no privileged read: the target runtime identity can hash every governed artifact unaided after the repair',
            'an ordinary cold-load by the target runtime identity reproduces the accepted head transaction, authority state hash, observation count, STORE SHA256 and allocation authority SHA256 exactly',
            'a fresh process boundary reproduces the same cold-load result',
        ]),
        // Rollback is emitted in the SAME order as apply, not in reverse, and
        // that is deliberate.  The constraints that fix the apply order fix the
        // rollback order identically: a chown clears the set-user/set-group bits
        // of a non-directory on this kernel even when the caller is privileged,
        // so ownership has to be restored *before* the mode is written or the
        // restored mode loses exactly the bits the pre-repair observation
        // recorded; and restoring the ACL through `setfacl --set` rewrites the
        // mask, so the mode has to be written after it.  Reversing the apply
        // order put the chown last and silently produced a mode that was not
        // `pre.mode` for any path whose ownership and special bits both moved.
        // `sequence` still names the apply step each entry undoes; the array
        // order is the order the entries are to be applied in.
        rollback: Object.freeze(operations.slice().map(operation => Object.freeze({
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
    REPAIR_EXECUTOR_POLICY, RUNTIME_CAPABILITY_INJECTION_POLICY,
    ALLOWED_PRIVILEGED_OPERATION_CLASSES, PRE_CONTENT_EVIDENCE_SOURCE,
    preContentEvidenceSourceFor, preContentEvidenceVerdict,
};
