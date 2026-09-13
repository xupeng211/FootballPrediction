#!/usr/bin/env node
'use strict';

// Stage D runtime filesystem publication audit (Blocker #2, Phase A).
//
// Lifecycle: permanent
// Owner: @xupeng211 (scripts/ops per .github/CODEOWNERS)
//
// This module is the recurrence-prevention primitive for Blocker #2.  It is a
// library, not a command: there is no CLI, no apply mode and no flag that
// relaxes it.  The Stage D binder calls it before any publication work begins
// and it fails closed by throwing the exact contract error that names the
// condition it found.
//
// It is separate from stage_d_runtime_filesystem_permission_contract.js because
// the two answer different questions.  The contract module states what the
// permission contract IS — the surfaces, their exact modes, the access model
// and the classification of an observed tree.  This module is the single
// precondition the binder applies to that contract *before* it publishes: five
// read-only observations (the publisher identity, the anchor metadata, the
// effective umask, the anchor's ACLs and what `.staging` would pass on to a
// package created inside it) and no mutation.  Keeping the precondition out of
// the classifier is also what lets it be proved on its own.
//
// Identity equality alone is not sufficient, which is what the remaining checks
// exist for.  A correctly owned 0700 anchor still reproduces Blocker #2 when
//   * a default ACL sits on the anchor or on `.staging`, because every
//     directory atomicPublisher.mkdirSync creates below it inherits those
//     entries, and an inherited mask caps the mode the publisher's own fchmod
//     can produce — the same mechanism that makes a named access ACL unable to
//     survive the publisher at all;
//   * the effective umask clears owner bits, because the mode the publisher
//     asks mkdir for is then silently reduced; or
//   * `.staging` carries set-group-ID, or a group that is not the runtime's,
//     because mkdir propagates both to the package directory it creates, and
//     nothing in the publisher clears them before the rename.
// None of these conditions leaves a trace in the anchor's own mode, none is
// repairable by this code, and all are refused here rather than discovered after
// a package has been published.

const path = require('node:path');
const {
    STAGING_DIRECTORY, assertRuntimeIdentity, contractError, observeObject, processIdentity,
} = require('./stage_d_runtime_filesystem_permission_contract');

// `.staging` is observed once and handed to both the ACL dimension and the
// inheritance dimension, so the two cannot disagree about which object they
// described.
function observeStaging(anchor) {
    const observation = observeObject(path.join(anchor, STAGING_DIRECTORY));
    return observation.observable ? observation : null;
}

function nearestExistingAncestor(target) {
    let current = path.resolve(target);
    for (;;) {
        const observation = observeObject(current);
        if (observation.observable) return Object.freeze({ path: current, observation });
        if (current === path.dirname(current)) throw contractError('PUBLICATION_IDENTITY_UNRESOLVABLE', 'no existing ancestor could be observed for the authority root');
        current = path.dirname(current);
    }
}

// Identity says *who* publishes; it says nothing about what that publisher will
// produce.  These conditions reproduce Blocker #2 even from a correctly owned
// 0700 anchor, so each is checked before the execution chain is entered and each
// fails closed.
function assertPublicationUmask(umask) {
    const effective = umask === null || umask === undefined
        ? (typeof process.umask === 'function' ? process.umask() : null) : umask;
    if (effective === null || (effective & 0o700) !== 0) {
        throw contractError('PUBLICATION_UMASK_UNSAFE', `effective umask ${effective === null ? 'is unknown' : `0o${effective.toString(8)}`} strips owner bits, so the directories atomicPublisher.mkdirSync creates for a package would not carry the mode this contract requires of a committed artifact`);
    }
    return effective;
}

// The publisher materialises each package with `mkdirSync(stagePath, { mode:
// 0o700 })` inside `.staging` and never chmods the result.  A new directory
// inherits exactly two things from the directory it is created in: the
// set-group-ID bit, and — with that bit set — the parent's group instead of the
// publisher's.  So a `.staging` carrying setgid hands every future package
// directory `02700`, and a `.staging` whose group is not the runtime's hands it
// a group the contract's identity rule does not allow.  Either way the package
// violates the contract the moment the rename into `committed/` lands, and a
// committed package directory is immutable from then on.  None of this is
// visible in the anchor's own metadata, which is why identity equality and the
// anchor checks above cannot see it.
//
// A `.staging` that could not be observed is deliberately not a refusal here.
// The publisher opens it through its own descriptor and fails closed when it is
// absent or unreadable, so such a tree cannot produce a package at all and there
// is no inheritance left to constrain.
function assertStagingInheritanceSafe(runtime, anchor, staging) {
    if (staging === null) return null;
    const risks = [];
    if (staging.is_symbolic_link || !staging.is_directory) {
        risks.push('is not a real directory, so the publisher\'s own open would follow a path this contract never described');
    }
    if ((staging.mode & 0o2000) !== 0) {
        risks.push('carries the set-group-ID bit, which mkdirSync propagates to every package directory created inside it and which nothing clears before the rename');
    }
    if (staging.uid !== runtime.uid || staging.gid !== runtime.gid) {
        risks.push(`is owned by ${staging.uid}:${staging.gid} rather than the declared runtime identity ${runtime.uid}:${runtime.gid}, so a package created inside it can inherit a group the contract does not allow`);
    }
    if (risks.length > 0) {
        throw contractError('PUBLICATION_STAGING_INHERITANCE_UNSAFE', `${path.join(anchor, STAGING_DIRECTORY)} ${risks.join('; ')}`);
    }
    return Object.freeze({ path: staging.path, uid: staging.uid, gid: staging.gid, mode: staging.mode });
}

function assertPublicationAcls(anchor, staging, aclProbe) {
    const targets = [anchor, ...(staging === null ? [] : [staging.path])];
    for (const target of targets) {
        const acl = typeof aclProbe === 'function' ? aclProbe(target) : null;
        if (!acl || !acl.available) {
            throw contractError('PUBLICATION_ACL_EVIDENCE_MISSING', `${target} extended ACL was not observed (${(acl && acl.reason) || 'no probe supplied'}), so an inheritable default ACL cannot be ruled out; an identity check alone does not constrain what the publisher creates next`);
        }
        if (acl.default_present === true) {
            const inherited = acl.default_entries && acl.default_entries.length > 0 ? `named default entries: ${acl.default_entries.join(', ')}` : 'base default entries only';
            throw contractError('PUBLICATION_DEFAULT_ACL_INHERITANCE', `${target} carries a default ACL (${inherited}), so every object the publisher creates below it — each new transaction package included — inherits those entries, which is exactly the recurrence this guard exists to stop`);
        }
    }
    return Object.freeze(targets);
}

// A privileged process is refused on either side of the check, not only on the
// mixed one.  The both-root case is the one that matters most here: the binder
// derives the runtime identity from the authority anchor's owner, so a root
// process facing a root-owned authority gets uid 0 on both sides and would
// otherwise verify itself — keep publishing owner-only packages that the
// ordinary runtime user cannot read, which is exactly how Blocker #2 arose.
// classifyAccess already treats a uid 0 runtime identity as a violation, so the
// audit must refuse it too.
function auditPublicationAnchor({ publisherIdentity, runtimeIdentity, authorityRoot, aclProbe = null, umask = null } = {}) {
    const publisher = assertRuntimeIdentity(publisherIdentity);
    const runtime = runtimeIdentity ? assertRuntimeIdentity(runtimeIdentity) : null;
    if (!runtime) throw contractError('PUBLICATION_IDENTITY_UNSPECIFIED', 'the expected cold-loading runtime identity must be declared explicitly');
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
    const staging = observeStaging(anchored.path);
    const publicationUmask = assertPublicationUmask(umask);
    const aclTargets = assertPublicationAcls(anchored.path, staging, aclProbe);
    const stagingInheritance = assertStagingInheritanceSafe(runtime, anchored.path, staging);
    return Object.freeze({
        status: 'PUBLICATION_IDENTITY_VERIFIED',
        publisher_identity: publisher,
        runtime_identity: runtime,
        anchor: anchored.path,
        anchor_identity: Object.freeze({ uid: observation.uid, gid: observation.gid, mode: observation.mode, dev: observation.dev, ino: observation.ino }),
        publication_umask: publicationUmask,
        acl_evidence_targets: aclTargets,
        staging_inheritance: stagingInheritance,
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

module.exports = {
    auditPublicationAnchor, deriveRuntimeIdentityFromAuthority, processIdentity,
};
