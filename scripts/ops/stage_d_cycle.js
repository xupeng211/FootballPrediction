'use strict';

// This is the one-cycle Stage D entrypoint.  It is intentionally offline-only
// until a later, explicitly authorized controlled-initialization change adds a
// transport implementation.  It never imports a provider client.
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const { openMarketEvidenceAuthoritySnapshot } = require('../../src/infrastructure/market_evidence/authorityReader');
const {
    buildOfflineStageDRunPlan,
    initializeRequestAccountingEpoch,
} = require('../../src/infrastructure/market_evidence/stageDOperations');
const { sha256Text } = require('../../src/infrastructure/market_evidence/contracts');

function valueAfter(flag) {
    const index = process.argv.indexOf(flag);
    if (index === -1) return null;
    const value = process.argv[index + 1];
    if (!value || value.startsWith('--')) throw new Error(`${flag} requires a value`);
    return value;
}

function readQuotaConfig(filePath) {
    if (!filePath) return null;
    const stat = fs.lstatSync(filePath);
    if (stat.isSymbolicLink() || !stat.isFile()) throw new Error('quota config must be a regular file');
    return JSON.parse(fs.readFileSync(filePath, 'utf8'));
}

function authoritySnapshot(authorityRoot) {
    const root = path.resolve(authorityRoot || 'data/market_evidence/live/transactions');
    return openMarketEvidenceAuthoritySnapshot({
        storeRoot: root,
        allocationArtifactPath: path.join(root, 'allocation.authority.json'),
    });
}

function main() {
    const initializeLedger = process.argv.includes('--initialize-request-accounting-epoch');
    const dryRun = process.argv.includes('--dry-run');
    if (initializeLedger === dryRun) {
        throw new Error('choose exactly one of --dry-run or --initialize-request-accounting-epoch; live execution is disabled');
    }
    const snapshot = authoritySnapshot(valueAfter('--authority-root'));
    const ledgerRoot = valueAfter('--ledger-root');
    if (!ledgerRoot) throw new Error('--ledger-root is required and must be an explicit repository-external or approved runtime path');
    const now = valueAfter('--now') || new Date().toISOString();
    if (initializeLedger) {
        const epoch = initializeRequestAccountingEpoch({
            ledgerRoot: path.resolve(ledgerRoot),
            authoritySnapshot: snapshot,
            startedAt: now,
            epochId: valueAfter('--epoch-id') || undefined,
        });
        process.stdout.write(`${JSON.stringify({ action: 'REQUEST_ACCOUNTING_EPOCH_INITIALIZED', epoch })}\n`);
        return;
    }
    const operationRoot = valueAfter('--operation-root') || fs.mkdtempSync(path.join(os.tmpdir(), 'stage-d-offline-plan-'));
    const resolvedLedgerRoot = path.resolve(ledgerRoot);
    const runLockTrustRoot = path.resolve(valueAfter('--run-lock-trust-root') || path.join(
        os.homedir(),
        '.stage-d-runtime-trust',
        sha256Text(resolvedLedgerRoot),
    ));
    if (!fs.existsSync(runLockTrustRoot)) fs.mkdirSync(runLockTrustRoot, { recursive: true, mode: 0o700 });
    const plan = buildOfflineStageDRunPlan({
        operationRoot: path.resolve(operationRoot),
        ledgerRoot: resolvedLedgerRoot,
        authoritySnapshot: snapshot,
        quotaConfig: readQuotaConfig(valueAfter('--quota-config')),
        runId: valueAfter('--run-id') || `stage-d-dry-run-${Date.now()}`,
        now,
        runLockTrustRoot,
    });
    process.stdout.write(`${JSON.stringify(plan)}\n`);
}

if (require.main === module) {
    try {
        main();
    } catch (error) {
        process.stderr.write(`STAGE_D_CYCLE_FAILED=${error.message.replace(/https?:\/\/\S+/g, '[redacted-url]')}\n`);
        process.exitCode = 1;
    }
}

module.exports = { valueAfter, readQuotaConfig, authoritySnapshot, main };
