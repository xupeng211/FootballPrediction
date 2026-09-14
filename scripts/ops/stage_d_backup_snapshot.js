'use strict';

// Offline Stage D snapshot CLI.
//
// Lifecycle: permanent — the operator entrypoint for Stage D Blocker #3
//   snapshot generation.  It is explicit-invocation only and is deliberately
//   not called by the publisher, the cycle, the scheduler or any commit path.
// Owner: Stage D continuous-operations maintainers (see
//   docs/data/STAGE_D_BLOCKER_3_BACKUP_TOOLING_CONTRACT.md).
//
// This CLI stages an independent backup generation into a filesystem transport
// root.  It is deliberately not wired to the off-host target: there is no
// endpoint flag, no bucket flag, no credential flag and no region flag, and a
// command line that names any of them is rejected rather than ignored.  Live R2
// wiring is a separate, explicitly authorized change.
//
// Every root is explicit.  There is no default authority root, no default
// ledger root and no default transport root, so this command cannot be run
// against production by accident: an operator who forgets an argument gets an
// error, never a backup of whatever happened to be in the default location.
//
// Nothing here prints, logs or persists a credential.  It accepts none.

const backup = require('../../src/infrastructure/market_evidence/backup');

const LIVE_TARGET_FLAGS = Object.freeze([
    '--endpoint',
    '--bucket',
    '--region',
    '--access-key-id',
    '--secret-access-key',
    '--session-token',
    '--credentials',
    '--profile',
    '--r2',
    '--s3',
    '--live',
    '--remote',
]);

function valueAfter(flag) {
    const index = process.argv.indexOf(flag);
    if (index === -1) return null;
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

// Both spellings are rejected: `--endpoint https://…` and `--endpoint=…` mean
// the same thing to an operator, so a check that only matched the first would
// silently ignore the second.  Silently ignoring a live-target flag is worse
// than refusing it -- the operator believes they aimed the command at R2 and
// gets a local run instead.  Only the flag name is reported; the value is never
// echoed, because a value here may be a secret.
function assertNoLiveTargetFlags() {
    const offending = LIVE_TARGET_FLAGS.filter(flag =>
        process.argv.some(argument => argument === flag || argument.startsWith(`${flag}=`)));
    if (offending.length) {
        throw new Error(`live off-host target flags are rejected by this CLI (LIVE_R2_CLI_WIRING=NOT_IMPLEMENTED): ${offending.join(', ')}`);
    }
}

// The denylist above can only refuse the names someone thought to write down,
// and the names that matter most here -- credentials and remote targets -- are
// exactly the ones that keep being invented: `--r2-access-key-id=…` matches
// none of them (`--r2=` needs the `=` where this has a `-`) and `--endpoint`
// with any prefix does the same, so a command carrying an access key or an API
// token ran a local snapshot and exited 0.  Silently ignoring an argument is
// worse than refusing it, because the operator believes they aimed the command
// somewhere it never went.  So the CLI accepts only what it implements, and the
// refusal names the flag rather than its value -- a value here may be a secret.
const ACCEPTED_FLAGS = Object.freeze({
    '--transport-root': 1,
    '--authority-root': 1,
    '--allocation-artifact': 1,
    '--ledger-root': 1,
    '--quota-config': 1,
    '--run-state': 1,
    '--snapshot-id': 1,
    '--now': 1,
});

function assertOnlyAcceptedFlags() {
    const argv = process.argv.slice(2);
    for (let index = 0; index < argv.length; index += 1) {
        const argument = argv[index];
        // A positional argument is not echoed, because a stray token is as
        // likely to be a pasted secret as a mistyped path.
        if (!argument.startsWith('--')) throw new Error('this CLI accepts only named flags; an unexpected positional argument was given');
        const equals = argument.indexOf('=');
        const name = equals === -1 ? argument : argument.slice(0, equals);
        let arity = ACCEPTED_FLAGS[name];
        if (arity === undefined) throw new Error(`unknown flag is refused rather than ignored (this CLI implements no credential, endpoint, bucket, region or live-target option): ${name}`);
        if (equals !== -1) throw new Error(`${name} must be given as a separate argument; this CLI does not accept the --flag=value form`);
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

function required(flag) {
    const value = valueAfter(flag);
    if (!value) throw new Error(`${flag} is required; this command has no production default`);
    return value;
}

async function main() {
    assertNoLiveTargetFlags();
    assertOnlyAcceptedFlags();
    const transportRoot = required('--transport-root');
    const authorityRoot = required('--authority-root');
    const allocationArtifactPath = required('--allocation-artifact');
    const ledgerRoot = required('--ledger-root');
    const quotaConfigPath = required('--quota-config');
    const runStateInputs = valuesAfter('--run-state');

    const transport = backup.createLocalTransport({ root: transportRoot });
    const report = await backup.writeSnapshot({
        transport,
        authorityRoot,
        allocationArtifactPath,
        ledgerRoot,
        quotaConfigPath,
        runStateInputs,
        snapshotId: valueAfter('--snapshot-id'),
        ...(valueAfter('--now') ? { now: () => new Date(valueAfter('--now')) } : {}),
    });
    process.stdout.write(`${JSON.stringify({ action: 'SNAPSHOT_WRITTEN', live_r2_cli_wiring: 'NOT_IMPLEMENTED', report })}\n`);
}

main().catch(error => {
    process.stdout.write(`${JSON.stringify({ action: 'SNAPSHOT_FAILED', error: error.message, code: error.code || null })}\n`);
    process.exitCode = 1;
});
