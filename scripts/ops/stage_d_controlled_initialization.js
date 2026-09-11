#!/usr/bin/env node
'use strict';

// This is the only production-facing Stage D single-cycle binder.  It accepts
// an owner-controlled bounded authorization artifact, never a runtime token,
// and delegates private capability creation to stageDOperations.js.
const fs = require('node:fs');
const path = require('node:path');
const { seedFotMobFixtureUniverse } = require('../../src/infrastructure/fixture_universe/FixtureUniverse');
const { loadVerifiedAllocationAuthority } = require('../../src/infrastructure/fixture_universe/AllocationAuthorityArtifact');
const { sha256Text } = require('../../src/infrastructure/market_evidence/contracts');
const {
    executeStageDControlledInitialization,
} = require('../../src/infrastructure/market_evidence/stageDOperations');

const REQUIRED_FLAGS = Object.freeze([
    '--authorization',
    '--authority-root',
    '--allocation-authority',
    '--ledger-root',
    '--quota-config',
    '--fixture-universe-raw',
    '--evidence-root',
    '--run-lock-trust-root',
]);

function readRegularFile(filePath, label) {
    if (typeof filePath !== 'string' || !filePath.trim()) throw new Error(`${label} is required`);
    const stat = fs.lstatSync(filePath);
    if (stat.isSymbolicLink() || !stat.isFile()) throw new Error(`${label} must be a regular file`);
    const bytes = fs.readFileSync(filePath);
    return Object.freeze({ bytes, text: bytes.toString('utf8') });
}

function readJsonFile(filePath, label) {
    const source = readRegularFile(filePath, label);
    let value;
    try {
        value = JSON.parse(source.text);
    } catch (error) {
        throw new Error(`${label} is invalid JSON: ${error.message}`, { cause: error });
    }
    return Object.freeze({ value, sha256: sha256Text(source.bytes) });
}

function loadReplayUniverse({ fixtureRawPath, allocationArtifactPath } = {}) {
    const raw = readRegularFile(fixtureRawPath, 'fixture-universe RAW');
    const allocation = loadVerifiedAllocationAuthority({ artifactPath: allocationArtifactPath });
    const universe = seedFotMobFixtureUniverse({
        rawHtml: raw.text,
        rawSha256: sha256Text(raw.bytes),
        allocation: allocation.allocationSnapshot,
        allocationAuthority: allocation.allocationAuthority,
        manifest: { raw_file_relative_path: path.basename(fixtureRawPath) },
        mode: 'REPLAY',
    });
    return Object.freeze({ universe, raw_sha256: sha256Text(raw.bytes) });
}

function parseArgs(argv = process.argv.slice(2)) {
    const values = {};
    const allowed = new Set(REQUIRED_FLAGS);
    allowed.add('--help');
    for (let index = 0; index < argv.length; index += 1) {
        const flag = argv[index];
        if (flag === '--help') return Object.freeze({ help: true });
        if (!allowed.has(flag)) throw new Error(`unknown or forbidden argument: ${flag}`);
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
        'Stage D controlled single-cycle binder (future separately authorized use only)',
        'node scripts/ops/stage_d_controlled_initialization.js',
        ...REQUIRED_FLAGS.map(flag => `  ${flag} <path>`),
        '',
        'The authorization artifact must be a read-only direct child of the supplied runtime trust root.',
        'The CLI does not accept run-time authorization tokens, live booleans, retries, or request counts.',
    ].join('\n');
}

function summarizeResult(result) {
    return Object.freeze({
        schema_version: 'footballprediction-stage-d-controlled-initialization-result/v1',
        status: result.status,
        run_id: result.run_id,
        request_id: result.request_id,
        authorization_audit: result.authorization_audit,
    });
}

async function main(argv = process.argv.slice(2)) {
    const args = parseArgs(argv);
    if (args.help) {
        process.stdout.write(`${helpText()}\n`);
        return;
    }
    const result = await executeStageDControlledInitialization({
        authorizationArtifactPath: args['--authorization'],
        authorityRoot: args['--authority-root'],
        allocationArtifactPath: args['--allocation-authority'],
        ledgerRoot: args['--ledger-root'],
        quotaConfigPath: args['--quota-config'],
        fixtureUniverseRawPath: args['--fixture-universe-raw'],
        evidenceRoot: args['--evidence-root'],
        runLockTrustRoot: args['--run-lock-trust-root'],
    });
    process.stdout.write(`${JSON.stringify(summarizeResult(result), null, 2)}\n`);
}

if (require.main === module) {
    main().catch(error => {
        process.stderr.write(`STAGE_D_CONTROLLED_INITIALIZATION_FAILED=${error.code || 'CONTROLLED_INITIALIZATION_FAILED'}\n`);
        process.exitCode = 1;
    });
}

module.exports = { REQUIRED_FLAGS, readRegularFile, readJsonFile, loadReplayUniverse, parseArgs, helpText, summarizeResult, main };
