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

function assertNoLiveTargetFlags() {
    const offending = LIVE_TARGET_FLAGS.filter(flag => process.argv.includes(flag));
    if (offending.length) {
        throw new Error(`live off-host target flags are rejected by this CLI (LIVE_R2_CLI_WIRING=NOT_IMPLEMENTED): ${offending.join(', ')}`);
    }
}

async function main() {
    assertNoLiveTargetFlags();
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
