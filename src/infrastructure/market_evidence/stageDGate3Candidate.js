'use strict';

// Offline-only preparation and validation of a future Gate 3 authorization
// candidate.  This module never imports a provider client or the live binder.
const crypto = require('node:crypto');
const { execFileSync } = require('node:child_process');
const fs = require('node:fs');
const path = require('node:path');
const { stableStringify } = require('./contracts');
const authorityReader = require('./authorityReader');
const stageD = require('./stageDOperations');

const CANDIDATE_SCHEMA_VERSION = 'footballprediction-stage-d-gate3-authorization-candidate/v2';
const CANDIDATE_STATUS = 'PREPARED_NOT_AUTHORIZED';
// This is an intentional candidate-layer allowlist, not a second source for
// emitted metadata.  Emission still derives from the binder getter below, but
// the future-authorization artifact must never be prepared from an unexpected
// (including legacy or future) binder metadata value.
const ACCEPTED_CONTROLLED_AUTHORIZATION_SCHEMA_VERSION =
    'footballprediction-stage-d-controlled-initialization-authorization/v2';
const FILE_PATTERN = /^sdc_stage_d_gate3_[a-f0-9]{32}\.json$/;
const SAFE_GIT = '/usr/bin/git';

function fail(code, message) {
    const error = new Error(message);
    error.code = code;
    throw error;
}
function hash(bytes) {
    return crypto.createHash('sha256').update(bytes).digest('hex');
}
function token(value, label) {
    if (typeof value !== 'string' || !/^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$/.test(value))
        {fail('INVALID_CANDIDATE', `${label} is invalid`);}
}
function sha(value, label) {
    if (typeof value !== 'string' || !/^[a-f0-9]{64}$/.test(value)) fail('INVALID_CANDIDATE', `${label} is invalid`);
}
function gitSha(value, label) {
    if (typeof value !== 'string' || !/^[a-f0-9]{40}$/.test(value)) fail('INVALID_CANDIDATE', `${label} is invalid`);
}
function utc(value, label) {
    if (typeof value !== 'string' || !/^\d{4}-\d\d-\d\dT/.test(value) || Number.isNaN(Date.parse(value)))
        {fail('INVALID_CANDIDATE', `${label} is invalid`);}
}
function exactKeys(value, keys, label) {
    if (
        !value ||
        typeof value !== 'object' ||
        Array.isArray(value) ||
        Object.keys(value).sort().join(',') !== [...keys].sort().join(',')
    )
        {fail('INVALID_CANDIDATE', `${label} keys are invalid`);}
}
function requiredContractString(value, label) {
    if (typeof value !== 'string' || !value)
        {fail('UNSUPPORTED_AUTHORIZATION_SCHEMA', `${label} is not valid controlled authorization metadata`);}
}
function requiredSingleContractValue(value, label) {
    if (!Array.isArray(value) || value.length !== 1 || typeof value[0] !== 'string' || !value[0])
        {fail('UNSUPPORTED_AUTHORIZATION_SCHEMA', `${label} is not valid controlled authorization metadata`);}
}
function requiredContractInteger(value, expected, label) {
    if (!Number.isSafeInteger(value) || value !== expected)
        {fail('UNSUPPORTED_AUTHORIZATION_SCHEMA', `${label} is not valid controlled authorization metadata`);}
}
function controlledAuthorizationContract() {
    const contract = stageD.getStageDControlledAuthorizationContract();
    exactKeys(
        contract,
        [
            'schema_version',
            'authorization_status',
            'mission',
            'max_lifetime_ms',
            'provider',
            'configured_markets',
            'configured_regions',
            'max_provider_requests',
            'expected_request_cost_credits',
        ],
        'controlled authorization contract'
    );
    if (contract.schema_version !== ACCEPTED_CONTROLLED_AUTHORIZATION_SCHEMA_VERSION)
        {fail('UNSUPPORTED_AUTHORIZATION_SCHEMA', 'controlled authorization metadata is not the canonical v2 contract');}
    requiredContractString(contract.authorization_status, 'authorization_status');
    requiredContractString(contract.mission, 'mission');
    if (!Number.isSafeInteger(contract.max_lifetime_ms) || contract.max_lifetime_ms <= 0)
        {fail('UNSUPPORTED_AUTHORIZATION_SCHEMA', 'max_lifetime_ms is not valid controlled authorization metadata');}
    requiredContractString(contract.provider, 'provider');
    requiredSingleContractValue(contract.configured_markets, 'configured_markets');
    requiredSingleContractValue(contract.configured_regions, 'configured_regions');
    requiredContractInteger(contract.max_provider_requests, 1, 'max_provider_requests');
    requiredContractInteger(contract.expected_request_cost_credits, 1, 'expected_request_cost_credits');
    return Object.freeze({
        schema_version: contract.schema_version,
        authorization_status: contract.authorization_status,
        mission: contract.mission,
        max_lifetime_ms: contract.max_lifetime_ms,
        provider: contract.provider,
        configured_markets: Object.freeze([...contract.configured_markets]),
        configured_regions: Object.freeze([...contract.configured_regions]),
        max_provider_requests: contract.max_provider_requests,
        expected_request_cost_credits: contract.expected_request_cost_credits,
    });
}
function readRegular(file, label, immutable = false) {
    const before = fs.lstatSync(file);
    if (!before.isFile() || before.isSymbolicLink()) fail('UNSAFE_PATH', `${label} must be a regular file`);
    if (immutable && (before.mode & 0o222) !== 0) fail('MUTABLE_EVIDENCE', `${label} must be read-only`);
    const fd = fs.openSync(file, fs.constants.O_RDONLY | (fs.constants.O_NOFOLLOW || 0));
    try {
        const opened = fs.fstatSync(fd);
        if (!opened.isFile() || opened.dev !== before.dev || opened.ino !== before.ino)
            {fail('UNSAFE_PATH', `${label} changed during open`);}
        const bytes = fs.readFileSync(fd);
        const after = fs.fstatSync(fd);
        if (after.dev !== opened.dev || after.ino !== opened.ino) fail('UNSAFE_PATH', `${label} changed during read`);
        return Object.freeze({ bytes, stat: after });
    } finally {
        fs.closeSync(fd);
    }
}
function json(source, label) {
    try {
        return JSON.parse(source.bytes.toString('utf8'));
    } catch {
        fail('INVALID_CANDIDATE', `${label} is invalid JSON`);
    }
}
function sourceDetails() {
    const source = stageD.resolveStageDGitSourceBinding();
    const sourcePath = path.join(__dirname, 'stageDOperations.js');
    const blob = execFileSync(
        SAFE_GIT,
        [
            '-C',
            path.resolve(__dirname, '../../..'),
            'rev-parse',
            'HEAD:src/infrastructure/market_evidence/stageDOperations.js',
        ],
        { encoding: 'utf8' }
    ).trim();
    return Object.freeze({
        ...source,
        implementation_source_sha256: hash(readRegular(sourcePath, 'Stage D operations source').bytes),
        implementation_git_blob_sha: blob,
    });
}
function candidateDirectory(directory) {
    const stat = fs.lstatSync(directory);
    if (!stat.isDirectory() || stat.isSymbolicLink() || (stat.mode & 0o077) !== 0)
        {fail('UNSAFE_PATH', 'candidate directory must be owner-only and non-symlink');}
    return Object.freeze({ path: fs.realpathSync.native(directory), stat });
}
function idsUnused({ ledger, candidateDirectory: directory, runId, requestId, ignoreCandidateId = null }) {
    if (ledger.requests.some(row => row.run_id === runId || row.request_id === requestId))
        {fail('CANDIDATE_ID_REUSED', 'run_id or request_id already exists in ledger');}
    for (const name of fs.readdirSync(directory)) {
        if (!FILE_PATTERN.test(name)) continue;
        try {
            const value = json(
                readRegular(path.join(directory, name), 'existing candidate', true),
                'existing candidate'
            );
            if (
                value.candidate_id !== ignoreCandidateId &&
                (value.future_authorization_ids?.run_id === runId ||
                    value.future_authorization_ids?.request_id === requestId)
            )
                {fail('CANDIDATE_ID_REUSED', 'run_id or request_id already exists in candidates');}
        } catch (error) {
            if (error.code === 'CANDIDATE_ID_REUSED') throw error;
            fail('INVALID_EXISTING_CANDIDATE', 'candidate directory contains unreadable or malformed evidence');
        }
    }
}
function runtimeState(input, now) {
    const ledgerRoot = path.resolve(input.ledgerRoot),
        trust = path.resolve(input.runLockTrustRoot);
    const ledger = stageD.readRequestLedger({ ledgerRoot });
    const quotaSource = readRegular(input.quotaConfigPath, 'quota configuration');
    const quotaConfig = stageD.validateQuotaConfiguration(JSON.parse(quotaSource.bytes), { now });
    const source = sourceDetails();
    const adjudicationSource = stageD.readBoundQuotaAdjudication({
        quotaAdjudicationPath: path.resolve(input.quotaAdjudicationPath),
        ledgerRoot,
        runLockTrustRoot: trust,
        expectedSha256: null,
        ledger,
        quotaConfig,
        quotaConfigSha256: hash(quotaSource.bytes),
        expectedSourceMainSha: source.source_main_sha,
        expectedSourceMainTreeSha: source.source_main_tree_sha,
        now,
    });
    const summary = stageD.ledgerUsageSummary(ledger);
    if (summary.ambiguous_consumed_request_ids.length)
        {fail('AMBIGUOUS_LEDGER', 'candidate preparation requires no ambiguous consumed request');}
    const lock = stageD.inspectStageDRunLock({ operationRoot: ledgerRoot, runLockTrustRoot: trust });
    if (lock.state !== 'ABSENT') fail('RUN_LOCK_NOT_CLEAR', 'candidate preparation requires no active run lock');
    const authority = authorityReader.openMarketEvidenceAuthoritySnapshot({
        storeRoot: path.resolve(input.authorityRoot),
        allocationArtifactPath: path.resolve(input.allocationArtifactPath),
    });
    const fixture = readRegular(input.fixtureUniverseRawPath, 'fixture universe');
    return Object.freeze({
        ledger,
        quotaConfig,
        quotaConfigSha256: hash(quotaSource.bytes),
        adjudication: adjudicationSource.value,
        quotaAdjudicationSha256: adjudicationSource.sha256,
        quotaAdjudicationPredecessor: adjudicationSource.predecessor,
        quotaAdjudicationPredecessorSha256: adjudicationSource.predecessorSha256,
        summary,
        authority,
        fixtureSha256: hash(fixture.bytes),
        source,
    });
}
function constructCandidate(input, state, now, id = crypto.randomBytes(16).toString('hex')) {
    if (typeof id !== 'string' || !/^[a-f0-9]{32}$/.test(id)) fail('INVALID_CANDIDATE', 'candidate identifier is invalid');
    const contract = controlledAuthorizationContract();
    const runId = `stage_d_gate3_run_${id}`,
        requestId = `stage_d_gate3_request_${id}`;
    stageD.assertRequestBudget({
        ledger: state.ledger,
        quotaConfig: state.quotaConfig,
        quotaConfigSha256: state.quotaConfigSha256,
        quotaAdjudication: state.adjudication,
        quotaAdjudicationSha256: state.quotaAdjudicationSha256,
        quotaAdjudicationPredecessor: state.quotaAdjudicationPredecessor,
        quotaAdjudicationPredecessorSha256: state.quotaAdjudicationPredecessorSha256,
        expectedSourceMainSha: state.source.source_main_sha,
        expectedSourceMainTreeSha: state.source.source_main_tree_sha,
        runId,
        now,
        requestedUnits: contract.expected_request_cost_credits,
    });
    return Object.freeze({
        schema_version: CANDIDATE_SCHEMA_VERSION,
        candidate_id: `sdc_stage_d_gate3_${id}`,
        candidate_status: CANDIDATE_STATUS,
        prepared_at: now,
        future_authorization_ids: { request_id: requestId, run_id: runId },
        provider_boundary: {
            authorization_consumed: false,
            live_provider_requests: 0,
            provider_contacted: false,
            provider_dns_lookup_performed: false,
            provider_reachability_proven: false,
            quota_units_charged_or_assumed: 0,
            request_intent_created: false,
            transmission_boundary_crossed: false,
        },
        request_scope: {
            provider: contract.provider,
            market: contract.configured_markets[0],
            region: contract.configured_regions[0],
            max_provider_requests: contract.max_provider_requests,
            expected_request_cost_credits: contract.expected_request_cost_credits,
        },
        required_authorization: {
            schema_version: contract.schema_version,
            authorization_status_required: contract.authorization_status,
            mission: contract.mission,
            authorization_validity_max_seconds: contract.max_lifetime_ms / 1000,
        },
        source_main_sha: state.source.source_main_sha,
        source_main_tree_sha: state.source.source_main_tree_sha,
        runtime_bindings: {
            accounting_epoch_id: state.ledger.epoch.epoch_id,
            ledger_entries: state.ledger.entries.length,
            ledger_last_entry_hash: state.ledger.last_entry_hash,
            consumed_requests: state.summary.consumed_request_count,
            ambiguous_consumed_request_ids: state.summary.ambiguous_consumed_request_ids,
            authority_pre_head: state.authority.head_transaction_id,
            authority_pre_state_hash: state.authority.state_hash,
            authority_pre_observation_count: state.authority.observations.length,
            authority_pre_store_sha256: hash(
                readRegular(path.join(input.authorityRoot, 'STORE.json'), 'authority store').bytes
            ),
            authority_pre_allocation_authority_sha256: hash(
                readRegular(input.allocationArtifactPath, 'allocation authority').bytes
            ),
            quota_config_sha256: state.quotaConfigSha256,
            quota_adjudication_sha256: state.quotaAdjudicationSha256,
            fixture_universe_raw_sha256: state.fixtureSha256,
            run_lock_state: 'ABSENT',
            post_response_semantics: {
                contract_version: 'stage-d-post-response-evidence-semantics/v1',
                implementation_source_sha256: state.source.implementation_source_sha256,
                implementation_git_blob_sha: state.source.implementation_git_blob_sha,
                response_evidence_order: [
                    'VALIDATE_COMPLETED_HTTP_RESPONSE',
                    'PERSIST_IMMUTABLE_RAW',
                    'RECONCILE_PROVIDER_QUOTA',
                ],
            },
        },
    });
}
function persistCandidate({ candidateDirectory: directory, candidate }) {
    const trustedDirectory = candidateDirectory(directory);
    const name = `${candidate.candidate_id}.json`;
    if (!FILE_PATTERN.test(name)) fail('INVALID_CANDIDATE', 'candidate filename is invalid');
    const output = path.join(trustedDirectory.path, name);
    const bytes = Buffer.from(`${stableStringify(candidate)}\n`);
    const fd = fs.openSync(
        output,
        fs.constants.O_WRONLY | fs.constants.O_CREAT | fs.constants.O_EXCL | (fs.constants.O_NOFOLLOW || 0),
        0o400
    );
    try {
        fs.writeFileSync(fd, bytes);
        fs.fsyncSync(fd);
    } finally {
        fs.closeSync(fd);
    }
    const directoryFd = fs.openSync(trustedDirectory.path, fs.constants.O_RDONLY | fs.constants.O_DIRECTORY);
    try {
        fs.fsyncSync(directoryFd);
    } finally {
        fs.closeSync(directoryFd);
    }
    const observed = readRegular(output, 'persisted candidate', true);
    if (!observed.bytes.equals(bytes) || hash(observed.bytes) !== hash(bytes))
        {fail('CANDIDATE_PERSISTENCE_FAILED', 'candidate changed after write');}
    return Object.freeze({ path: output, sha256: hash(bytes) });
}
function prepareGate3Candidate(input, { now = new Date().toISOString(), id } = {}) {
    utc(now, 'prepared_at');
    const trustedDirectory = candidateDirectory(input.candidateDirectory);
    const state = runtimeState(input, now);
    const candidate = constructCandidate(input, state, now, id);
    idsUnused({
        ledger: state.ledger,
        candidateDirectory: trustedDirectory.path,
        runId: candidate.future_authorization_ids.run_id,
        requestId: candidate.future_authorization_ids.request_id,
    });
    const persisted = persistCandidate({ candidateDirectory: trustedDirectory.path, candidate });
    return Object.freeze({
        candidate,
        ...persisted,
        budget: stageD.assertRequestBudget({
            ledger: state.ledger,
            quotaConfig: state.quotaConfig,
            quotaConfigSha256: state.quotaConfigSha256,
            quotaAdjudication: state.adjudication,
            quotaAdjudicationSha256: state.quotaAdjudicationSha256,
            quotaAdjudicationPredecessor: state.quotaAdjudicationPredecessor,
            quotaAdjudicationPredecessorSha256: state.quotaAdjudicationPredecessorSha256,
            expectedSourceMainSha: state.source.source_main_sha,
            expectedSourceMainTreeSha: state.source.source_main_tree_sha,
            runId: candidate.future_authorization_ids.run_id,
            now,
        }),
    });
}
function validateGate3Candidate({ candidatePath, input, expectedSha256 = null, now = new Date().toISOString() }) {
    const trustedDirectory = candidateDirectory(input.candidateDirectory);
    const resolvedCandidatePath = path.resolve(candidatePath);
    if (path.dirname(resolvedCandidatePath) !== trustedDirectory.path)
        {fail('UNSAFE_PATH', 'candidate must be a direct child of the trusted candidate directory');}
    const observed = readRegular(candidatePath, 'candidate', true);
    const actual = hash(observed.bytes);
    if (expectedSha256 !== null && actual !== expectedSha256)
        {fail('CANDIDATE_HASH_MISMATCH', 'candidate hash does not match');}
    const candidate = json(observed, 'candidate');
    if (!observed.bytes.equals(Buffer.from(`${stableStringify(candidate)}\n`)))
        {fail('NON_CANONICAL_CANDIDATE', 'candidate bytes must use canonical serialization');}
    exactKeys(
        candidate,
        [
            'schema_version',
            'candidate_id',
            'candidate_status',
            'prepared_at',
            'future_authorization_ids',
            'provider_boundary',
            'request_scope',
            'required_authorization',
            'source_main_sha',
            'source_main_tree_sha',
            'runtime_bindings',
        ],
        'candidate'
    );
    if (
        candidate.schema_version !== CANDIDATE_SCHEMA_VERSION ||
        candidate.candidate_status !== CANDIDATE_STATUS ||
        path.basename(resolvedCandidatePath) !== `${candidate.candidate_id}.json` ||
        !FILE_PATTERN.test(path.basename(resolvedCandidatePath))
    )
        {fail('INVALID_CANDIDATE', 'candidate identity or status is invalid');}
    token(candidate.candidate_id, 'candidate_id');
    utc(candidate.prepared_at, 'prepared_at');
    exactKeys(candidate.future_authorization_ids, ['request_id', 'run_id'], 'candidate ids');
    token(candidate.future_authorization_ids.run_id, 'run_id');
    token(candidate.future_authorization_ids.request_id, 'request_id');
    const state = runtimeState(input, now);
    const expected = constructCandidate(
        input,
        state,
        candidate.prepared_at,
        candidate.candidate_id.slice('sdc_stage_d_gate3_'.length)
    );
    if (stableStringify(candidate) !== stableStringify(expected))
        {fail('CANDIDATE_BINDING_MISMATCH', 'candidate does not match current governed state');}
    idsUnused({
        ledger: state.ledger,
        candidateDirectory: trustedDirectory.path,
        runId: candidate.future_authorization_ids.run_id,
        requestId: candidate.future_authorization_ids.request_id,
        ignoreCandidateId: candidate.candidate_id,
    });
    return Object.freeze({
        candidate,
        sha256: actual,
        authorization_schema: controlledAuthorizationContract().schema_version,
    });
}

module.exports = {
    CANDIDATE_SCHEMA_VERSION,
    CANDIDATE_STATUS,
    ACCEPTED_CONTROLLED_AUTHORIZATION_SCHEMA_VERSION,
    prepareGate3Candidate,
    validateGate3Candidate,
    constructCandidate,
    runtimeState,
};
