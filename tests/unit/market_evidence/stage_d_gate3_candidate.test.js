'use strict';

process.env.NODE_ENV = 'test';

const assert = require('node:assert/strict');
const crypto = require('node:crypto');
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const test = require('node:test');
const { stableStringify } = require('../../../src/infrastructure/market_evidence/contracts');
const stageD = require('../../../src/infrastructure/market_evidence/stageDOperations');
const authorityReader = require('../../../src/infrastructure/market_evidence/authorityReader');
const candidateModule = require('../../../src/infrastructure/market_evidence/stageDGate3Candidate');

const NOW = '2026-09-20T12:00:00.000Z';
const SOURCE_SHA = 'a'.repeat(40);
const SOURCE_TREE = 'b'.repeat(40);
const QUOTA_SHA = 'c'.repeat(64);
const ADJUDICATION_SHA = 'd'.repeat(64);
const FIXTURE_SHA = 'e'.repeat(64);

function writeImmutable(file, value) {
    fs.writeFileSync(file, typeof value === 'string' ? value : `${stableStringify(value)}\n`, { mode: 0o400 });
    fs.chmodSync(file, 0o400);
}

function state() {
    return {
        epoch: { epoch_id: 'epoch-test' },
        entries: [{ sequence: 1 }],
        last_entry_hash: 'f'.repeat(64),
        requests: [],
    };
}

function setup(t) {
    const root = fs.mkdtempSync(path.join(os.tmpdir(), 'stage-d-gate3-candidate-'));
    const candidateDirectory = path.join(root, 'candidates');
    fs.mkdirSync(candidateDirectory, { mode: 0o700 });
    const inputs = {
        candidateDirectory,
        authorityRoot: path.join(root, 'authority'),
        allocationArtifactPath: path.join(root, 'allocation.json'),
        ledgerRoot: path.join(root, 'ledger'),
        quotaConfigPath: path.join(root, 'quota.json'),
        quotaAdjudicationPath: path.join(root, 'adjudication.json'),
        fixtureUniverseRawPath: path.join(root, 'fixture.raw'),
        runLockTrustRoot: path.join(root, 'trust'),
    };
    fs.mkdirSync(inputs.authorityRoot, { recursive: true, mode: 0o700 });
    fs.mkdirSync(inputs.ledgerRoot, { recursive: true, mode: 0o700 });
    fs.mkdirSync(inputs.runLockTrustRoot, { recursive: true, mode: 0o700 });
    writeImmutable(inputs.quotaConfigPath, { quota: 'fixture' });
    writeImmutable(inputs.quotaAdjudicationPath, { adjudication: 'fixture' });
    writeImmutable(inputs.fixtureUniverseRawPath, 'fixture-universe');
    writeImmutable(path.join(inputs.authorityRoot, 'STORE.json'), 'store');
    writeImmutable(inputs.allocationArtifactPath, 'allocation');
    const originals = new Map();
    const replace = (object, key, value) => { originals.set(`${key}:${originals.size}`, [object, key, object[key]]); object[key] = value; };
    const ledger = state();
    replace(stageD, 'readRequestLedger', () => ledger);
    replace(stageD, 'validateQuotaConfiguration', value => value);
    replace(stageD, 'validateQuotaAdjudication', value => value);
    replace(stageD, 'ledgerUsageSummary', () => ({ consumed_request_count: 4, ambiguous_consumed_request_ids: [] }));
    replace(stageD, 'inspectStageDRunLock', () => ({ state: 'ABSENT' }));
    replace(stageD, 'resolveStageDGitSourceBinding', () => ({ source_main_sha: SOURCE_SHA, source_main_tree_sha: SOURCE_TREE }));
    replace(stageD, 'assertRequestBudget', () => ({ allowed: true, conservative_remaining_after_request: 445 }));
    replace(authorityReader, 'openMarketEvidenceAuthoritySnapshot', () => ({
        head_transaction_id: 'tx-1', state_hash: '1'.repeat(64), observations: [Object.freeze({})],
    }));
    t.after(() => {
        for (const [, [object, key, value]] of originals) object[key] = value;
        fs.rmSync(root, { recursive: true, force: true });
    });
    return inputs;
}

test('canonical Gate 3 candidate derives the v2 binder contract and validates offline', t => {
    const inputs = setup(t);
    const result = candidateModule.prepareGate3Candidate(inputs, { now: NOW, id: '0123456789abcdef0123456789abcdef' });
    assert.equal(result.candidate.required_authorization.schema_version, stageD.getStageDControlledAuthorizationContract().schema_version);
    assert.equal(result.candidate.candidate_status, candidateModule.CANDIDATE_STATUS);
    assert.equal(result.candidate.provider_boundary.provider_contacted, false);
    assert.equal(result.candidate.provider_boundary.live_provider_requests, 0);
    assert.equal(fs.statSync(result.path).mode & 0o777, 0o400);
    assert.equal(candidateModule.validateGate3Candidate({ candidatePath: result.path, input: inputs, expectedSha256: result.sha256, now: NOW }).sha256, result.sha256);
});

test('v1, unknown schema, byte tampering and source drift fail closed without rewrite', t => {
    const inputs = setup(t);
    const result = candidateModule.prepareGate3Candidate(inputs, { now: NOW, id: 'fedcba9876543210fedcba9876543210' });
    const original = fs.readFileSync(result.path);
    const mutate = callback => {
        const value = JSON.parse(original);
        callback(value);
        fs.chmodSync(result.path, 0o600);
        fs.writeFileSync(result.path, `${stableStringify(value)}\n`);
        fs.chmodSync(result.path, 0o400);
        assert.throws(() => candidateModule.validateGate3Candidate({ candidatePath: result.path, input: inputs, now: NOW }));
        fs.chmodSync(result.path, 0o600);
        fs.writeFileSync(result.path, original);
        fs.chmodSync(result.path, 0o400);
    };
    mutate(value => { value.required_authorization.schema_version = 'footballprediction-stage-d-controlled-initialization-authorization/v1'; });
    mutate(value => { value.required_authorization.schema_version = 'footballprediction-stage-d-controlled-initialization-authorization/v999'; });
    mutate(value => { value.source_main_sha = '0'.repeat(40); });
    fs.chmodSync(result.path, 0o600);
    fs.writeFileSync(result.path, `${original.toString('utf8').trim()} \n`);
    fs.chmodSync(result.path, 0o400);
    assert.throws(() => candidateModule.validateGate3Candidate({ candidatePath: result.path, input: inputs, now: NOW }), /canonical serialization/);
});

test('reuse, unsafe paths and overwrite are rejected', t => {
    const inputs = setup(t);
    const id = '00112233445566778899aabbccddeeff';
    const first = candidateModule.prepareGate3Candidate(inputs, { now: NOW, id });
    assert.throws(() => candidateModule.prepareGate3Candidate(inputs, { now: NOW, id }), /exists/);
    const alias = path.join(path.dirname(inputs.candidateDirectory), 'candidate-link.json');
    fs.symlinkSync(first.path, alias);
    assert.throws(() => candidateModule.validateGate3Candidate({ candidatePath: alias, input: inputs, now: NOW }), /direct child/);
    const wrongName = path.join(inputs.candidateDirectory, 'sdc_stage_d_gate3_11111111111111111111111111111111.json');
    fs.copyFileSync(first.path, wrongName);
    fs.chmodSync(wrongName, 0o400);
    assert.throws(() => candidateModule.validateGate3Candidate({ candidatePath: wrongName, input: inputs, now: NOW }), /identity or status/);
    assert.equal(crypto.createHash('sha256').update(fs.readFileSync(first.path)).digest('hex'), first.sha256);
});
