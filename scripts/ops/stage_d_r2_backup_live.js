'use strict';

// Live Stage D snapshot CLI — the off-host target entrypoint.
//
// Lifecycle: permanent — the operator entrypoint for Stage D Blocker #3
//   snapshot generation against the live off-host target.  It is
//   explicit-invocation only and is deliberately not called by the publisher,
//   the cycle, the scheduler or any commit path.
// Owner: Stage D continuous-operations maintainers (see
//   docs/data/STAGE_D_BLOCKER_3_BACKUP_TOOLING_CONTRACT.md).
//
// This is a separate entrypoint from the offline CLI on purpose.  The offline
// CLI is provably incapable of addressing a remote target: it builds a
// filesystem transport unconditionally and refuses every live-target flag by
// name, through a denylist *and* an allowlist.  Teaching it an endpoint flag
// would destroy that property, so the live path is a new file instead and the
// offline CLI is left exactly as it was.
//
// The target address and the credential are never command-line values here.
// Addressing comes from a non-secret identity file and the credential from a
// separate file that must be 0600 or stricter; both paths are explicit, and
// neither has a default.  A command line that carries a key, a token, an
// endpoint, a bucket, a region or a prefix is refused rather than ignored --
// because an operator who believes they aimed the command somewhere and had the
// value silently dropped learns the truth at the worst possible moment.
//
// Every failure path is fail-closed: there is no fallback to the local
// transport, no partial run, and no cleanup that deletes anything.
//
// Two modes:
//
//   --preflight-only   load and validate the identity and the credential,
//                      construct the transport, assert its contract, and report
//                      the addressing and the planned probe namespace.  Performs
//                      no transport call and therefore makes no network request.
//                      This is OFFLINE_PREFLIGHT, not a connectivity check: it
//                      proves the wiring and the files, and proves nothing about
//                      whether the target is reachable or the credential valid.
//
//   (default)          run one snapshot generation against the target through
//                      the same writer the offline path uses.

const backup = require('../../src/infrastructure/market_evidence/backup');

// Flag names that would put a credential value, or the target address, on a
// command line.  Both spellings are matched: `--endpoint https://…` and
// `--endpoint=…` mean the same thing to an operator, so a check that matched
// only one would silently ignore the other.  Only the flag name is reported --
// a value in one of these positions may be a secret.
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

// The denylist above can only refuse the names someone thought to write down,
// and the names that matter most here are exactly the ones that keep being
// invented: `--r2-access-key-id=…` matches none of them (`--r2=` needs the `=`
// where this has a `-`) and `--target-endpoint` does the same.  So this CLI
// accepts only what it implements, and the refusal names the flag rather than
// its value.
const ACCEPTED_FLAGS = Object.freeze({
    '--target-identity-file': 1,
    '--credential-file': 1,
    '--authority-root': 1,
    '--allocation-artifact': 1,
    '--ledger-root': 1,
    '--quota-config': 1,
    '--run-state': 1,
    '--snapshot-id': 1,
    '--now': 1,
    '--preflight-only': 0,
});

// The one flag that is meaningful more than once.  A snapshot carries a list of
// run-state inputs, so repeating this flag is how a caller gives more than one.
// Every other accepted flag is single-valued, and a repeat is refused rather
// than resolved -- see `assertOnlyAcceptedFlags`.
const REPEATABLE_FLAGS = Object.freeze(new Set(['--run-state']));

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
        // A value never begins with `--`, so a flag sitting in a value position
        // is a missing value rather than a value.  Consuming it would turn the
        // flag that follows into a stray positional and report the wrong
        // problem; leaving it lets the reader that needs the value name it.
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

function valuesAfter(flag) {
    const collected = [];
    for (let index = 0; index < process.argv.length; index += 1) {
        if (process.argv[index] !== flag) continue;
        const value = process.argv[index + 1];
        if (!value || value.startsWith('--')) throw new Error(`${flag} requires a value`);
        collected.push(value);
    }
    return collected;
}

function required(flag) {
    const value = valueAfter(flag);
    if (!value) throw new Error(`${flag} is required; this command has no production default`);
    return value;
}

// The namespace the live connectivity probe will use, frozen here at the point
// the wiring is written rather than invented during the first live contact.  It
// sits outside every generation prefix, so a probe object can never appear in a
// generation's exact object set: the verifier lists under `<snapshot_id>/` only.
//
// The second create of this key is the load-bearing live assertion -- it must
// fail with ObjectAlreadyExistsError, or the create-only guarantee this whole
// design rests on is false.  That assertion is a LIVE_CONNECTIVITY_PREFLIGHT
// concern and is not performed here.
const LIVE_CONNECTIVITY_PROBE_KEY = 'preflight-probe/conditional-write/v1/PROBE.json';

// The credential values are known to this process, so they can be removed from
// any text on the way out -- including text from a dependency that chose to
// quote them.  Nothing in the paths this CLI controls puts a secret in a
// message, but a guarantee that only covers the code you wrote is not the
// guarantee that is needed.  This runs over every line the CLI prints.
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
// Kept so a failure can still say which target it was addressing.  A fingerprint
// and not the endpoint: it identifies the target without republishing the
// account-bearing address into a log that may travel further than the identity
// file it came from.
let targetFingerprint = null;

async function main() {
    assertNoInlineSecretFlags();
    assertOnlyAcceptedFlags();

    const identity = backup.loadLiveTargetIdentity({ targetIdentityFile: required('--target-identity-file') });
    targetFingerprint = identity.target_fingerprint;
    credentials = backup.loadLiveCredentials({ credentialFile: required('--credential-file') });

    // The transport is built from the validated identity and the validated
    // credential, and from nothing else.  It constructs its own SDK client, so
    // there is no path here that could reach an ambient credential.
    const transport = backup.loadR2Transport().createR2Transport({
        endpoint: identity.endpoint,
        bucket: identity.bucket,
        region: identity.region,
        prefix: identity.prefix,
        credentials,
    });
    // Runs before a single byte is touched, and refuses a transport that can
    // delete rather than warning about one.
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
            live_connectivity_probe_key: LIVE_CONNECTIVITY_PROBE_KEY,
            target,
            credentials: credentialReport,
        })}\n`);
        return;
    }

    const report = await backup.writeSnapshot({
        transport,
        authorityRoot: required('--authority-root'),
        allocationArtifactPath: required('--allocation-artifact'),
        ledgerRoot: required('--ledger-root'),
        quotaConfigPath: required('--quota-config'),
        runStateInputs: valuesAfter('--run-state'),
        snapshotId: valueAfter('--snapshot-id'),
        ...(valueAfter('--now') ? { now: () => new Date(valueAfter('--now')) } : {}),
    });
    process.stdout.write(`${JSON.stringify({
        action: 'LIVE_SNAPSHOT_WRITTEN',
        live_r2_cli_wiring: 'IMPLEMENTED',
        live_connectivity_preflight: 'NOT_PERFORMED',
        target,
        credentials: credentialReport,
        report,
    })}\n`);
}

main().catch(error => {
    const scrub = makeScrubber(credentials);
    process.stdout.write(`${JSON.stringify({
        action: 'LIVE_BACKUP_FAILED',
        live_r2_cli_wiring: 'IMPLEMENTED',
        error: scrub(error && error.message ? error.message : String(error)),
        code: (error && error.code) || null,
        target_fingerprint: targetFingerprint,
    })}\n`);
    process.exitCode = 1;
});
