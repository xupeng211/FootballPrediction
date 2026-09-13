'use strict';

// Offline Stage D restore / verify CLI.
//
// Lifecycle: permanent — the operator entrypoint for Stage D Blocker #3
//   generation verification and isolated restore proof.  It is
//   explicit-invocation only and is deliberately not called by the publisher,
//   the cycle, the scheduler or any commit path.
// Owner: Stage D continuous-operations maintainers (see
//   docs/data/STAGE_D_BLOCKER_3_BACKUP_TOOLING_CONTRACT.md).
//
// Two actions, both offline and both against a filesystem transport root:
//
//   --verify-only              read the generation and check it against the
//                              contract; writes nothing anywhere
//   --destination-root <dir>   restore the generation into a fresh isolated
//                              root and prove the restored root cold-loads
//
// The destination must not exist.  A restore never overwrites, and the command
// refuses a destination inside the governed production area or inside the
// transport root, so a mistyped argument cannot turn a proof into an incident.
//
// As with the snapshot CLI there is no endpoint, bucket, region or credential
// flag: live R2 wiring is a separate, explicitly authorized change.

const restoreExecutor = require('../../src/infrastructure/market_evidence/backup/restoreExecutor');
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
// with any prefix does the same, so a restore carrying an access key or an API
// token ran to completion and exited 0.  Silently ignoring an argument is worse
// than refusing it, because the operator believes they aimed the command
// somewhere it never went.  So the CLI accepts only what it implements, and the
// refusal names the flag rather than its value -- a value here may be a secret.
const ACCEPTED_FLAGS = Object.freeze({
    '--transport-root': 1,
    '--snapshot-id': 1,
    '--destination-root': 1,
    '--verify-only': 0,
    '--fresh-process': 0,
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

async function main() {
    assertNoLiveTargetFlags();
    assertOnlyAcceptedFlags();
    const transportRoot = valueAfter('--transport-root');
    const snapshotId = valueAfter('--snapshot-id');
    if (!transportRoot) throw new Error('--transport-root is required; this command has no production default');
    if (!snapshotId) throw new Error('--snapshot-id is required; a generation is always named explicitly');
    const destinationRoot = valueAfter('--destination-root');
    const verifyOnly = process.argv.includes('--verify-only');
    if (verifyOnly === Boolean(destinationRoot)) throw new Error('choose exactly one of --verify-only or --destination-root');

    const transport = backup.createLocalTransport({ root: transportRoot });
    if (verifyOnly) {
        const report = await backup.verifySnapshot({ transport, snapshotId });
        process.stdout.write(`${JSON.stringify({ action: 'SNAPSHOT_VERIFIED', live_r2_cli_wiring: 'NOT_IMPLEMENTED', report })}\n`);
        if (report.result !== 'PASS') process.exitCode = 1;
        return;
    }

    const report = await restoreExecutor.executeRestore({
        transport,
        snapshotId,
        destinationRoot,
        // The transport root holds the generation.  A restore beside it, or
        // under it, would sit in the same failure domain as the thing it is
        // supposed to survive, which is the one property a restore proof exists
        // to establish.  The executor refuses; this CLI has to tell it where the
        // source is, or the refusal would never fire.
        sourceRoots: [transportRoot],
        includeFreshProcess: process.argv.includes('--fresh-process'),
    });
    process.stdout.write(`${JSON.stringify({ action: 'SNAPSHOT_RESTORED', live_r2_cli_wiring: 'NOT_IMPLEMENTED', report })}\n`);
}

main().catch(error => {
    const report = error && error.report ? error.report : null;
    process.stdout.write(`${JSON.stringify({ action: 'RESTORE_VERIFY_FAILED', error: error.message, code: error.code || null, report })}\n`);
    process.exitCode = 1;
});
