'use strict';

// Live Stage D restore / verify CLI — the off-host target entrypoint.
//
// Lifecycle: permanent — the operator entrypoint for Stage D Blocker #3
//   generation verification and isolated restore proof against the live
//   off-host target.  It is explicit-invocation only and is deliberately not
//   called by the publisher, the cycle, the scheduler or any commit path.
// Owner: Stage D continuous-operations maintainers (see
//   docs/data/STAGE_D_BLOCKER_3_BACKUP_TOOLING_CONTRACT.md).
//
// Separate from the offline CLI for the same reason as the backup entrypoint:
// the offline CLI's inability to address a remote target is a property worth
// keeping, so the live path is a new file rather than new flags.
//
// Two actions, both against the target:
//
//   --verify-only              read the generation through the canonical
//                              verifier; writes nothing anywhere
//   --destination-root <dir>   restore the generation into a fresh isolated
//                              root and prove the restored root cold-loads
//
// The generation's only source is the target.  No local transport is built, no
// local source root is passed, and the executor's report carries
// `production_fallback_used: false` and `production_paths_read: []` as positive
// assertions -- there is no code path in this process that could read a
// production file, so those are structural rather than observed.
//
// A generation restored from the target has no filesystem source, which is why
// `sourceRoots` is empty here rather than carrying a path.  Passing a local path
// would claim the source is local, and the disjointness assertion that protects
// a local restore would then be checking the wrong thing.

const backup = require('../../src/infrastructure/market_evidence/backup');
const restoreExecutor = require('../../src/infrastructure/market_evidence/backup/restoreExecutor');

const INLINE_SECRET_FLAGS = Object.freeze([
    '--access-key-id',
    '--secret-access-key',
    '--session-token',
    '--access-key',
    '--secret-key',
    '--token',
    '--api-token',
    '--credentials',
    '--credential',
    '--profile',
    '--aws-access-key-id',
    '--aws-secret-access-key',
    '--aws-session-token',
    '--aws-profile',
    '--endpoint',
    '--endpoint-url',
    '--bucket',
    '--region',
    '--prefix',
    '--r2',
    '--s3',
]);

function assertNoInlineSecretFlags() {
    const offending = INLINE_SECRET_FLAGS.filter(flag =>
        process.argv.some(argument => argument === flag || argument.startsWith(`${flag}=`)));
    if (offending.length) {
        throw new Error(`credential and target values are refused on the command line; both come from explicit files: ${offending.join(', ')}`);
    }
}

const ACCEPTED_FLAGS = Object.freeze({
    '--target-identity-file': 1,
    '--credential-file': 1,
    '--snapshot-id': 1,
    '--destination-root': 1,
    '--verify-only': 0,
    '--fresh-process': 0,
    '--preflight-only': 0,
});

// No flag this CLI accepts is meaningful more than once: every one of them
// names something singular (a target, a credential, a snapshot, a destination).
// A repeat is therefore refused rather than resolved -- see
// `assertOnlyAcceptedFlags`.
const REPEATABLE_FLAGS = Object.freeze(new Set());

const repeatedFlagMessage = flag => `${flag} was given more than once; this CLI refuses a repeated flag rather than silently choosing one of the values`;

function assertOnlyAcceptedFlags() {
    const argv = process.argv.slice(2);
    const seen = new Set();
    for (let index = 0; index < argv.length; index += 1) {
        const argument = argv[index];
        // A positional argument is not echoed, because a stray token is as
        // likely to be a pasted secret as a mistyped path.
        if (!argument.startsWith('--')) throw new Error('this CLI accepts only named flags; an unexpected positional argument was given');
        const equals = argument.indexOf('=');
        const name = equals === -1 ? argument : argument.slice(0, equals);
        let arity = ACCEPTED_FLAGS[name];
        if (arity === undefined) throw new Error(`unknown flag is refused rather than ignored; this CLI addresses one target through one identity file and one credential file: ${name}`);
        if (equals !== -1) throw new Error(`${name} must be given as a separate argument; this CLI does not accept the --flag=value form`);
        // `valueAfter` reads the first occurrence, so without this check
        // `--target-identity-file A --target-identity-file B` would silently
        // aim the run at A while the operator believed they had said B.  On the
        // non-preflight path that is a write to, or a restore from, the wrong
        // real target, which is the failure this CLI exists to refuse.
        if (!REPEATABLE_FLAGS.has(name)) {
            if (seen.has(name)) throw new Error(repeatedFlagMessage(name));
            seen.add(name);
        }
        while (arity > 0 && typeof argv[index + 1] === 'string' && !argv[index + 1].startsWith('--')) {
            arity -= 1;
            index += 1;
        }
    }
}

function valueAfter(flag) {
    const index = process.argv.indexOf(flag);
    if (index === -1) return null;
    // Re-checked here rather than only in `assertOnlyAcceptedFlags`, so that
    // "a single-valued flag is read at most once" does not depend on the order
    // of the checks in `main`.
    if (!REPEATABLE_FLAGS.has(flag) && process.argv.indexOf(flag, index + 1) !== -1) {
        throw new Error(repeatedFlagMessage(flag));
    }
    const value = process.argv[index + 1];
    if (!value || value.startsWith('--')) throw new Error(`${flag} requires a value`);
    return value;
}

function required(flag) {
    const value = valueAfter(flag);
    if (!value) throw new Error(`${flag} is required; this command has no production default`);
    return value;
}

// The credential values are known to this process, so they can be removed from
// any text on the way out -- including text from a dependency that chose to
// quote them.
function makeScrubber(credentials) {
    const secrets = credentials === null
        ? []
        : [credentials.accessKeyId, credentials.secretAccessKey, credentials.sessionToken]
            .filter(value => typeof value === 'string' && value.length > 0);
    return text => {
        let scrubbed = String(text);
        for (const secret of secrets) scrubbed = scrubbed.split(secret).join('[REDACTED]');
        return scrubbed;
    };
}

let credentials = null;
let targetFingerprint = null;

async function main() {
    assertNoInlineSecretFlags();
    assertOnlyAcceptedFlags();

    const identity = backup.loadLiveTargetIdentity({ targetIdentityFile: required('--target-identity-file') });
    targetFingerprint = identity.target_fingerprint;
    credentials = backup.loadLiveCredentials({ credentialFile: required('--credential-file') });

    const transport = backup.loadR2Transport().createR2Transport({
        endpoint: identity.endpoint,
        bucket: identity.bucket,
        region: identity.region,
        prefix: identity.prefix,
        credentials,
    });
    backup.assertTransportContract(transport);

    const target = Object.freeze({
        ...transport.describe(),
        environment: identity.environment,
        project: identity.project,
        purpose: identity.purpose,
        target_fingerprint: identity.target_fingerprint,
    });
    const credentialReport = backup.describeCredentialPresence(credentials);

    if (process.argv.includes('--preflight-only')) {
        process.stdout.write(`${JSON.stringify({
            action: 'LIVE_PREFLIGHT_ONLY',
            live_r2_cli_wiring: 'IMPLEMENTED',
            preflight_class: 'OFFLINE_PREFLIGHT',
            live_connectivity_preflight: 'NOT_PERFORMED',
            network_calls_made: 0,
            local_source_roots: [],
            target,
            credentials: credentialReport,
        })}\n`);
        return;
    }

    const snapshotId = required('--snapshot-id');
    const destinationRoot = valueAfter('--destination-root');
    const verifyOnly = process.argv.includes('--verify-only');
    if (verifyOnly === Boolean(destinationRoot)) throw new Error('choose exactly one of --verify-only or --destination-root');

    if (verifyOnly) {
        const report = await backup.verifySnapshot({ transport, snapshotId });
        process.stdout.write(`${JSON.stringify({
            action: 'LIVE_SNAPSHOT_VERIFIED',
            live_r2_cli_wiring: 'IMPLEMENTED',
            live_connectivity_preflight: 'NOT_PERFORMED',
            target,
            report,
        })}\n`);
        if (report.result !== 'PASS') process.exitCode = 1;
        return;
    }

    const report = await restoreExecutor.executeRestore({
        transport,
        snapshotId,
        destinationRoot,
        // Empty by construction: the generation lives on the target and has no
        // filesystem source in this process.
        sourceRoots: [],
        includeFreshProcess: process.argv.includes('--fresh-process'),
    });
    process.stdout.write(`${JSON.stringify({
        action: 'LIVE_SNAPSHOT_RESTORED',
        live_r2_cli_wiring: 'IMPLEMENTED',
        live_connectivity_preflight: 'NOT_PERFORMED',
        target,
        report,
    })}\n`);
}

main().catch(error => {
    const scrub = makeScrubber(credentials);
    const report = error && error.report ? error.report : null;
    process.stdout.write(`${JSON.stringify({
        action: 'LIVE_RESTORE_VERIFY_FAILED',
        live_r2_cli_wiring: 'IMPLEMENTED',
        error: scrub(error && error.message ? error.message : String(error)),
        code: (error && error.code) || null,
        target_fingerprint: targetFingerprint,
        report,
    })}\n`);
    process.exitCode = 1;
});
