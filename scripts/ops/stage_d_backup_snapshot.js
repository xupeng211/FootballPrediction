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

function assertNoLiveTargetFlags() {
    const offending = LIVE_TARGET_FLAGS.filter(flag => process.argv.includes(flag));
    if (offending.length) {
        throw new Error(`live off-host target flags are rejected by this CLI (LIVE_R2_CLI_WIRING=NOT_IMPLEMENTED): ${offending.join(', ')}`);
    }
}

function required(flag) {
    const value = valueAfter(flag);
    if (!value) throw new Error(`${flag} is required; this command has no production default`);
    return value;
}

async function main() {
    assertNoLiveTargetFlags();
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
