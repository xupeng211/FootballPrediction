'use strict';

// 真实采集后的离线重放与 live 处理共用这一条 canonical pipeline：
// immutable RAW/receipt -> verified allocation -> prospective builder ->
// atomic publisher -> fresh authority reader。
const fs = require('node:fs');
const path = require('node:path');
const { seedFotMobFixtureUniverse, validateAllocationSnapshot, RULESET_VERSION, RESOLVER_VERSION } = require('../fixture_universe/FixtureUniverse');
const { persistVerifiedAllocationAuthority } = require('../fixture_universe/AllocationAuthorityArtifact');
const { sha256Text, stableStringify } = require('./contracts');
const { readImmutableRaw, createCaptureReceipt } = require('./evidenceStore');
const { bootstrapMarketEvidenceTransactionStore } = require('./transactionStore');
const { openMarketEvidenceAuthoritySnapshot } = require('./authorityReader');
const { buildProspectiveMarketEvidenceTransaction } = require('./prospectiveBatch');
const { publishProspectiveMarketEvidenceTransaction } = require('./atomicPublisher');

function readRegularJson(filePath, label) {
    const stat = fs.lstatSync(filePath);
    if (stat.isSymbolicLink() || !stat.isFile()) throw new Error(`${label} must be a regular file`);
    try {
        return JSON.parse(fs.readFileSync(filePath, 'utf8'));
    } catch (error) {
        throw new Error(`${label} is invalid JSON: ${error.message}`, { cause: error });
    }
}

function canonicalizePersistedAllocation(value, fotmobRawSha256) {
    if (!value || typeof value !== 'object' || Array.isArray(value)) throw new Error('persisted allocation snapshot is invalid');
    // The first Stage C evidence bundle predates the v1 provenance/hash
    // envelope.  Complete only those missing contract fields from the
    // immutable FotMob RAW used to validate the same 380-row allocation.
    if (value.provenance_raw_sha256 === undefined && value.content_sha256 === undefined) {
        const unsigned = {
            schema_version: value.schema_version,
            authority: value.authority,
            fixtures: value.fixtures,
            teams: value.teams,
            provenance_raw_sha256: fotmobRawSha256,
            identity_ruleset_version: RULESET_VERSION,
            resolver_version: RESOLVER_VERSION,
        };
        return { ...unsigned, content_sha256: sha256Text(stableStringify(unsigned)) };
    }
    return value;
}

function loadOfflineEvidence({ fotmobRawPath, oddsRawPath, receiptPath, allocationPath }) {
    for (const [value, label] of [[fotmobRawPath, 'FotMob RAW path'], [oddsRawPath, 'Odds RAW path'], [receiptPath, 'capture receipt path'], [allocationPath, 'allocation path']]) {
        if (typeof value !== 'string' || !value.trim()) throw new Error(`${label} is required`);
    }
    const fotmobRawText = fs.readFileSync(fotmobRawPath, 'utf8');
    const fotmobRawSha256 = sha256Text(fotmobRawText);
    const receipt = createCaptureReceipt(readRegularJson(receiptPath, 'capture receipt'));
    const oddsRawText = readImmutableRaw({ rawPath: oddsRawPath, expectedSha256: receipt.raw_sha256 });
    if (receipt.response_size_bytes !== Buffer.byteLength(oddsRawText, 'utf8')) throw new Error('capture receipt response_size_bytes does not match immutable RAW');
    const allocationSnapshot = canonicalizePersistedAllocation(readRegularJson(allocationPath, 'allocation snapshot'), fotmobRawSha256);
    validateAllocationSnapshot(allocationSnapshot, fotmobRawSha256);
    return Object.freeze({ fotmobRawText, fotmobRawSha256, oddsRawText, receipt, allocationSnapshot });
}

function publishOfflineMarketEvidence({ fotmobRawText, fotmobRawSha256, oddsRawText, receipt, allocationSnapshot, allocationArtifactPath, storeRoot, projectionVersion = '1', supportedMarketKeys = ['h2h', 'h2h_lay'], authorizedSupersessions = [] }) {
    const universe = seedFotMobFixtureUniverse({ rawHtml: fotmobRawText, rawSha256: fotmobRawSha256, allocation: allocationSnapshot, manifest: { raw_file_relative_path: 'fotmob-fixtures.html' }, mode: 'REPLAY' });
    persistVerifiedAllocationAuthority({ artifactPath: allocationArtifactPath, allocationAuthority: universe.allocationAuthority });
    bootstrapMarketEvidenceTransactionStore({ storeRoot, allocationArtifactPath, bootstrapMetadata: { source: 'stage-c-offline-canonical-pipeline/v1' } });
    const authoritySnapshot = openMarketEvidenceAuthoritySnapshot({ storeRoot, allocationArtifactPath });
    const candidate = buildProspectiveMarketEvidenceTransaction({ authoritySnapshot, universe, oddsRawText, captureReceipt: receipt, projectionVersion, supportedMarketKeys, authorizedSupersessions });
    const published = publishProspectiveMarketEvidenceTransaction({ storeRoot, allocationArtifactPath, candidate });
    const freshAuthoritySnapshot = openMarketEvidenceAuthoritySnapshot({ storeRoot, allocationArtifactPath });
    if (freshAuthoritySnapshot.head_transaction_id !== published.transaction_id) throw new Error('fresh authority reader did not reopen the published transaction');
    return Object.freeze({
        published,
        candidate,
        freshAuthoritySnapshot,
        matched_decision_count: candidate.identity_decisions.filter(row => row.decision === 'MATCHED').length,
        quarantined_decision_count: candidate.identity_decisions.filter(row => row.decision === 'QUARANTINED').length,
        observation_count: freshAuthoritySnapshot.observations.length,
        knowledge_time: freshAuthoritySnapshot.head_knowledge_time,
    });
}

module.exports = { loadOfflineEvidence, publishOfflineMarketEvidence };
