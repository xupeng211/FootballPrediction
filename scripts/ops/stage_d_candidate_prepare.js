#!/usr/bin/env node
'use strict';

// Lifecycle: permanent. Owner: market-evidence operations.
// Offline-only Gate 3 pre-authorization candidate entrypoint.  It has no
// live/authorize/execute mode and never imports the controlled live binder.
const {
    prepareGate3Candidate,
    validateGate3Candidate,
} = require('../../src/infrastructure/market_evidence/stageDGate3Candidate');

const FLAGS = Object.freeze([
    '--candidate-directory',
    '--authority-root',
    '--allocation-authority',
    '--ledger-root',
    '--quota-config',
    '--quota-adjudication',
    '--fixture-universe-raw',
    '--run-lock-trust-root',
]);
function parse(argv) {
    const values = {};
    for (let i = 0; i < argv.length; i += 1) {
        const key = argv[i];
        if (key === '--help') return { help: true };
        if (!FLAGS.includes(key) && key !== '--candidate' && key !== '--expected-sha256')
            {throw new Error(`unknown or forbidden argument: ${key}`);}
        if (values[key]) throw new Error(`duplicate argument: ${key}`);
        const value = argv[++i];
        if (!value || value.startsWith('--')) throw new Error(`${key} requires a value`);
        values[key] = value;
    }
    return values;
}
function input(values) {
    for (const key of FLAGS) if (!values[key]) throw new Error(`${key} is required`);
    return {
        candidateDirectory: values['--candidate-directory'],
        authorityRoot: values['--authority-root'],
        allocationArtifactPath: values['--allocation-authority'],
        ledgerRoot: values['--ledger-root'],
        quotaConfigPath: values['--quota-config'],
        quotaAdjudicationPath: values['--quota-adjudication'],
        fixtureUniverseRawPath: values['--fixture-universe-raw'],
        runLockTrustRoot: values['--run-lock-trust-root'],
    };
}
function help() {
    return [
        'Stage D canonical offline Gate 3 candidate preparation',
        'node scripts/ops/stage_d_candidate_prepare.js prepare|validate',
        ...FLAGS.map(flag => `  ${flag} <path>`),
        'validate also requires --candidate <path> [--expected-sha256 <sha256>]',
        '',
        'This command creates only an immutable PREPARED_NOT_AUTHORIZED candidate. It cannot authorize, execute, transmit, or contact a provider.',
    ].join('\n');
}
function main(argv = process.argv.slice(2)) {
    const [command, ...rest] = argv;
    const values = parse(rest);
    if (command === '--help' || values.help) {
        process.stdout.write(`${help()}\n`);
        return;
    }
    const governed = input(values);
    if (command === 'prepare') {
        const result = prepareGate3Candidate(governed);
        process.stdout.write(
            `${JSON.stringify({ candidate_path: result.path, candidate_sha256: result.sha256, candidate_status: result.candidate.candidate_status, run_id: result.candidate.future_authorization_ids.run_id, request_id: result.candidate.future_authorization_ids.request_id, required_authorization_schema: result.candidate.required_authorization.schema_version, provider_contacted: false, live_authorization_created: false }, null, 2)}\n`
        );
        return;
    }
    if (command === 'validate') {
        if (!values['--candidate']) throw new Error('--candidate is required');
        const result = validateGate3Candidate({
            candidatePath: values['--candidate'],
            input: governed,
            expectedSha256: values['--expected-sha256'] || null,
        });
        process.stdout.write(
            `${JSON.stringify({ candidate_sha256: result.sha256, candidate_status: result.candidate.candidate_status, authorization_schema: result.authorization_schema, validation: 'PASS' }, null, 2)}\n`
        );
        return;
    }
    throw new Error('command must be prepare or validate');
}
if (require.main === module) {
    try {
        main();
    } catch (error) {
        process.stderr.write(`STAGE_D_GATE3_CANDIDATE_FAILED=${error.code || 'CANDIDATE_FAILED'}\n`);
        process.exitCode = 1;
    }
}
module.exports = { FLAGS, parse, input, help, main };
