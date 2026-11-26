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
    readBoundQuotaAdjudication,
    readRequestLedger,
    resolveStageDGitSourceBinding,
} = require('../../src/infrastructure/market_evidence/stageDOperations');
const { inspectForwardAccounting } = require('../../src/infrastructure/market_evidence/stageDForwardAccounting');
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

function readQuotaConfigSource(filePath) {
    if (!filePath) return null;
    const stat = fs.lstatSync(filePath);
    if (stat.isSymbolicLink() || !stat.isFile()) throw new Error('quota config must be a regular file');
    const bytes = fs.readFileSync(filePath, 'utf8');
    return Object.freeze({ value: JSON.parse(bytes), sha256: sha256Text(bytes) });
}

function authoritySnapshot(authorityRoot) {
    const root = path.resolve(authorityRoot || 'data/market_evidence/live/transactions');
    return openMarketEvidenceAuthoritySnapshot({
        storeRoot: root,
        allocationArtifactPath: path.join(root, 'allocation.authority.json'),
    });
}

const FORWARD_ONLY_FLAGS = Object.freeze({
    '--forward-opening': 'openingPath',
    '--expected-opening-sha256': 'openingSha256',
    '--account-record': 'accountPath',
    '--history-record': 'historyPath',
    '--prior-ledger-root': 'priorLedgerRoot',
    '--allocation-authority': 'allocationAuthorityPath',
    '--ledger-checkpoint': 'checkpointPath',
    '--expected-checkpoint-sha256': 'checkpointSha256',
});

const FORWARD_FLAGS = Object.freeze({
    ...FORWARD_ONLY_FLAGS,
    '--quota-config': 'quotaConfigPath',
    '--ledger-root': 'ledgerRoot',
    '--authority-root': 'authorityRoot',
    '--run-lock-trust-root': 'runLockTrustRoot',
});

function forwardPlan(argv) {
    const input = {};
    for (let index = 0; index < argv.length; index += 1) {
        const flag = argv[index];
        if (flag === '--dry-run') continue;
        const key = FORWARD_FLAGS[flag];
        const value = argv[index + 1];
        if (!Object.hasOwn(FORWARD_FLAGS, flag) || Object.hasOwn(input, key) || !value || value.startsWith('--')) {
            throw new Error('后续记账核验只接受一组明确的离线凭据路径');
        }
        input[key] = value;
        index += 1;
    }
    if (Object.keys(input).length !== Object.keys(FORWARD_FLAGS).length || argv.filter(arg => arg === '--dry-run').length !== 1) {
        throw new Error('后续记账核验需要 --dry-run 和完整凭据');
    }
    const result = inspectForwardAccounting({ ...input, now: new Date().toISOString() });
    process.stdout.write(`${JSON.stringify(result)}\n`);
}

function offlineAdjudicationOptions({ ledger, resolvedLedgerRoot, runLockTrustRoot, quotaConfigSource, now }) {
    const quotaAdjudicationPath = valueAfter('--quota-adjudication');
    if (!quotaAdjudicationPath) return {};
    const source = resolveStageDGitSourceBinding();
    const adjudication = readBoundQuotaAdjudication({
        quotaAdjudicationPath: path.resolve(quotaAdjudicationPath),
        ledgerRoot: resolvedLedgerRoot,
        runLockTrustRoot,
        // The descriptor-bound reader computes the observed hash from the
        // same immutable file descriptor that it validates.  Do not read
        // this untrusted path separately before that check.
        expectedSha256: null,
        ledger,
        quotaConfig: quotaConfigSource?.value || null,
        quotaConfigSha256: quotaConfigSource?.sha256 || null,
        expectedSourceMainSha: source.source_main_sha,
        expectedSourceMainTreeSha: source.source_main_tree_sha,
        now,
    });
    return {
        quotaAdjudication: adjudication.value,
        quotaAdjudicationSha256: adjudication.sha256,
        quotaAdjudicationPredecessor: adjudication.predecessor,
        quotaAdjudicationPredecessorSha256: adjudication.predecessorSha256,
        expectedSourceMainSha: source.source_main_sha,
        expectedSourceMainTreeSha: source.source_main_tree_sha,
    };
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
    const quotaConfigSource = readQuotaConfigSource(valueAfter('--quota-config'));
    const quotaConfig = quotaConfigSource?.value || null;
    const ledger = readRequestLedger({ ledgerRoot: resolvedLedgerRoot });
    const plan = buildOfflineStageDRunPlan({
        operationRoot: path.resolve(operationRoot),
        ledgerRoot: resolvedLedgerRoot,
        authoritySnapshot: snapshot,
        quotaConfig,
        quotaConfigSha256: quotaConfigSource?.sha256 || null,
        ...offlineAdjudicationOptions({ ledger, resolvedLedgerRoot, runLockTrustRoot, quotaConfigSource, now }),
        runId: valueAfter('--run-id') || `stage-d-dry-run-${Date.now()}`,
        now,
        runLockTrustRoot,
    });
    process.stdout.write(`${JSON.stringify(plan)}\n`);
}

if (require.main === module) {
    try {
        const args = process.argv.slice(2);
        if (args.some(arg => Object.hasOwn(FORWARD_ONLY_FLAGS, arg.split('=', 1)[0]))) forwardPlan(args);
        else main();
    } catch (error) {
        process.stderr.write(`STAGE_D_CYCLE_FAILED=${error.message.replace(/https?:\/\/\S+/g, '[redacted-url]')}\n`);
        process.exitCode = 1;
    }
}

module.exports = { valueAfter, readQuotaConfig, readQuotaConfigSource, authoritySnapshot, main };
