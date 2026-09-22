#!/usr/bin/env node
'use strict';

// Lifecycle: permanent — bounded offline Stage D quota-adjudication entrypoint.
// Owner: Stage D continuous-operations maintainers (see .github/CODEOWNERS).

// Offline-only Stage D quota adjudication.  This command reads the sealed local
// ledger and quota configuration, creates a conservative UNKNOWN-provider-effect
// artifact, and writes it create-only into the explicit runtime trust root.  It
// has no provider client, DNS path, proxy path, or live authorization path.
const fs = require('node:fs');
const path = require('node:path');
const { sha256Text } = require('../../src/infrastructure/market_evidence/contracts');
const {
    createStageDQuotaAdjudication,
    createStageDQuotaAdjudicationSuccessor,
    persistStageDQuotaAdjudication,
    readRequestLedger,
    resolveStageDGitSourceBinding,
} = require('../../src/infrastructure/market_evidence/stageDOperations');

const REQUIRED_FLAGS = Object.freeze([
    '--ledger-root',
    '--quota-config',
    '--run-lock-trust-root',
    '--output',
    '--historical-request-id',
    '--source-main-sha',
    '--source-main-tree',
    '--adjudication-id',
]);

function readRegularJsonFile(filePath, label) {
    if (typeof filePath !== 'string' || !filePath.trim()) throw new Error(`${label} is required`);
    const before = fs.lstatSync(filePath);
    if (before.isSymbolicLink() || !before.isFile()) throw new Error(`${label} must be a regular file`);
    const fd = fs.openSync(filePath, fs.constants.O_RDONLY | (fs.constants.O_NOFOLLOW || 0));
    try {
        const opened = fs.fstatSync(fd);
        if (!opened.isFile() || opened.dev !== before.dev || opened.ino !== before.ino) throw new Error(`${label} changed during open`);
        const bytes = fs.readFileSync(fd, 'utf8');
        const after = fs.fstatSync(fd);
        if (after.dev !== opened.dev || after.ino !== opened.ino) throw new Error(`${label} changed during read`);
        return Object.freeze({ bytes, value: JSON.parse(bytes) });
    } finally {
        fs.closeSync(fd);
    }
}

function readBoundPredecessor(filePath, claimedSha256) {
    const predecessor = readRegularJsonFile(filePath, '--predecessor');
    const observedSha256 = sha256Text(predecessor.bytes);
    if (claimedSha256 !== observedSha256) {
        const error = new Error('--predecessor-sha256 does not match the predecessor bytes read');
        error.code = 'QUOTA_ADJUDICATION_HASH_MISMATCH';
        throw error;
    }
    return Object.freeze({ ...predecessor, sha256: observedSha256 });
}

function parseArgs(argv = process.argv.slice(2)) {
    const values = {};
    const allowed = new Set([...REQUIRED_FLAGS, '--adjudicated-at', '--predecessor', '--predecessor-sha256', '--help']);
    for (let index = 0; index < argv.length; index += 1) {
        const flag = argv[index];
        if (flag === '--help') return Object.freeze({ help: true });
        if (!allowed.has(flag)) throw new Error(`unknown argument: ${flag}`);
        if (Object.prototype.hasOwnProperty.call(values, flag)) throw new Error(`duplicate argument: ${flag}`);
        const value = argv[index + 1];
        if (!value || value.startsWith('--')) throw new Error(`${flag} requires a value`);
        values[flag] = value;
        index += 1;
    }
    for (const flag of REQUIRED_FLAGS) if (!values[flag]) throw new Error(`${flag} is required`);
    return Object.freeze(values);
}

function helpText() {
    return [
        'Stage D offline quota adjudication (provider-free)',
        'node scripts/ops/stage_d_quota_adjudication.js',
        ...REQUIRED_FLAGS.map(flag => `  ${flag} <value>`),
        '  --adjudicated-at <UTC timestamp> (optional; defaults to current UTC time)',
        '  --predecessor <immutable v1 adjudication> --predecessor-sha256 <SHA256> (together, for a source successor)',
        '',
        'The output must be a new direct child of the explicit runtime trust root.',
        'The command never contacts or resolves The Odds API and never changes the request ledger.',
    ].join('\n');
}

function resolveGitSourceBinding({ sourceMainSha, sourceMainTreeSha, testRuntimeAuthorization = null } = {}) {
    const runtimeSource = resolveStageDGitSourceBinding({ testRuntimeAuthorization });
    if (sourceMainSha !== runtimeSource.source_main_sha || sourceMainTreeSha !== runtimeSource.source_main_tree_sha) {
        const error = new Error('source main commit/tree must match the current trusted runtime Git checkout');
        error.code = 'INVALID_AUTHORIZATION';
        throw error;
    }
    return runtimeSource;
}

function main(argv = process.argv.slice(2)) {
    const args = parseArgs(argv);
    if (args.help) {
        process.stdout.write(`${helpText()}\n`);
        return;
    }
    const configSource = readRegularJsonFile(args['--quota-config'], '--quota-config');
    const ledger = readRequestLedger({ ledgerRoot: path.resolve(args['--ledger-root']) });
    const adjudicatedAt = args['--adjudicated-at'] || new Date().toISOString();
    const source = resolveGitSourceBinding({
        sourceMainSha: args['--source-main-sha'],
        sourceMainTreeSha: args['--source-main-tree'],
    });
    const hasPredecessor = Boolean(args['--predecessor']);
    if (hasPredecessor !== Boolean(args['--predecessor-sha256'])) throw new Error('--predecessor and --predecessor-sha256 must be supplied together');
    const predecessor = hasPredecessor ? readBoundPredecessor(args['--predecessor'], args['--predecessor-sha256']) : null;
    const create = predecessor === null ? createStageDQuotaAdjudication : createStageDQuotaAdjudicationSuccessor;
    const artifact = create({
        ledger,
        quotaConfig: configSource.value,
        quotaConfigSha256: sha256Text(configSource.bytes),
        historicalRequestId: args['--historical-request-id'],
        sourceMainSha: source.source_main_sha,
        sourceMainTreeSha: source.source_main_tree_sha,
        adjudicatedAt,
        adjudicationId: args['--adjudication-id'],
        ...(predecessor === null ? {} : { predecessor: predecessor.value, predecessorSha256: predecessor.sha256 }),
    });
    const persisted = persistStageDQuotaAdjudication({
        artifactPath: args['--output'],
        ledgerRoot: path.resolve(args['--ledger-root']),
        runLockTrustRoot: path.resolve(args['--run-lock-trust-root']),
        artifact,
    });
    process.stdout.write(`${JSON.stringify({
        schema_version: artifact.schema_version,
        artifact_path: persisted.path,
        artifact_sha256: persisted.sha256,
        adjudication_id: artifact.adjudication_id,
        local_consumed_requests: artifact.local_consumed_requests,
        local_consumed_quota_units: artifact.local_consumed_quota_units,
        provider_quota_actual_effect: artifact.provider_quota_actual_effect,
        conservative_effective_provider_usage: artifact.conservative_effective_provider_usage,
        conservative_remaining_automatic_budget: artifact.conservative_remaining_automatic_budget,
        predecessor_adjudication_id: artifact.predecessor_adjudication_id || null,
        predecessor_sha256: artifact.predecessor_sha256 || null,
    }, null, 2)}\n`);
}

if (require.main === module) {
    try {
        main();
    } catch (error) {
        process.stderr.write(`STAGE_D_QUOTA_ADJUDICATION_FAILED=${error.code || 'QUOTA_ADJUDICATION_FAILED'}\n`);
        process.exitCode = 1;
    }
}

module.exports = { REQUIRED_FLAGS, readRegularJsonFile, readBoundPredecessor, parseArgs, helpText, resolveGitSourceBinding, main };
