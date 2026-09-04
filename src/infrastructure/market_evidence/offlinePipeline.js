'use strict';

// 真实采集后的离线重放与 live 处理共用这一条 canonical pipeline：
// immutable RAW/receipt -> verified allocation -> prospective builder ->
// atomic publisher -> fresh authority reader。
const fs = require('node:fs');
const path = require('node:path');
const { seedFotMobFixtureUniverse, validateAllocationSnapshot, RULESET_VERSION, RESOLVER_VERSION } = require('../fixture_universe/FixtureUniverse');
const { persistVerifiedAllocationAuthority, loadVerifiedAllocationAuthority } = require('../fixture_universe/AllocationAuthorityArtifact');
const { sha256Text, stableStringify } = require('./contracts');
const { readImmutableRaw, loadVerifiedCaptureReceipt } = require('./evidenceStore');
const { bootstrapMarketEvidenceTransactionStore, readStoreContract } = require('./transactionStore');
const { openMarketEvidenceAuthoritySnapshot, readPackage } = require('./authorityReader');
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
    const receiptEvidence = loadVerifiedCaptureReceipt({ receiptPath });
    const receipt = receiptEvidence.receipt;
    const oddsRawText = readImmutableRaw({ rawPath: oddsRawPath, expectedSha256: receipt.raw_sha256 });
    if (receipt.response_size_bytes !== Buffer.byteLength(oddsRawText, 'utf8')) throw new Error('capture receipt response_size_bytes does not match immutable RAW');
    const allocationSnapshot = canonicalizePersistedAllocation(readRegularJson(allocationPath, 'allocation snapshot'), fotmobRawSha256);
    validateAllocationSnapshot(allocationSnapshot, fotmobRawSha256);
    return Object.freeze({ fotmobRawText, fotmobRawSha256, oddsRawText, receiptEvidence, allocationSnapshot });
}

function verifyPublishedLogicalBatch({ storeRoot, candidate, published, freshAuthoritySnapshot }) {
    const packagePath = path.join(path.resolve(storeRoot), 'committed');
    const transaction = readPackage(packagePath, published.transaction_id);
    const sourceMatches = stableStringify(transaction.manifest.source) === stableStringify(candidate.manifest.source);
    if (transaction.manifest.logical_batch_key !== candidate.logical_batch_key || !sourceMatches) throw new Error('published transaction does not bind the requested logical batch and capture source');
    const captureKey = `${transaction.manifest.source.provider}\u0000${transaction.manifest.source.capture_id}`;
    const captureBinding = freshAuthoritySnapshot.capture_bindings.find(row => row.key === captureKey);
    if (!captureBinding) throw new Error('fresh authority reader did not retain the published capture binding');
    const captureSource = { ...captureBinding }; delete captureSource.key;
    if (stableStringify(captureSource) !== stableStringify(transaction.manifest.source)) throw new Error('fresh authority reader did not retain the published capture binding');
    // The publisher has already committed this exact transaction. Another
    // writer may legitimately advance the head after its lock is released, so
    // success is proven by the immutable package and its reopened lineage—not
    // by requiring this batch to remain the current head.
    return transaction.manifest.publication_metadata.knowledge_time;
}

function publishOfflineMarketEvidence({ fotmobRawText, fotmobRawSha256, oddsRawText, receiptEvidence, allocationArtifactPath, storeRoot, projectionVersion = '1', supportedMarketKeys = ['h2h', 'h2h_lay'], authorizedSupersessions = [] }) {
    const storePath = path.join(path.resolve(storeRoot), 'STORE.json');
    const artifactExists = fs.existsSync(allocationArtifactPath); const storeExists = fs.existsSync(storePath);
    if (artifactExists !== storeExists) throw new Error('allocation artifact and transaction STORE.json must be created and reopened as one trust root');
    let universe;
    if (storeExists) {
        // STORE.json supplies the independent immutable binding before replay
        // can interpret allocation bytes as canonical authority.
        readStoreContract({ storeRoot, allocationArtifactPath });
        const verified = loadVerifiedAllocationAuthority({ artifactPath: allocationArtifactPath });
        universe = seedFotMobFixtureUniverse({ rawHtml: fotmobRawText, rawSha256: fotmobRawSha256, allocation: verified.allocationSnapshot, allocationAuthority: verified.allocationAuthority, manifest: { raw_file_relative_path: 'fotmob-fixtures.html' }, mode: 'REPLAY' });
    } else {
        universe = seedFotMobFixtureUniverse({ rawHtml: fotmobRawText, rawSha256: fotmobRawSha256, manifest: { raw_file_relative_path: 'fotmob-fixtures.html' }, mode: 'INITIAL_SEED' });
        persistVerifiedAllocationAuthority({ artifactPath: allocationArtifactPath, allocationAuthority: universe.allocationAuthority });
        bootstrapMarketEvidenceTransactionStore({ storeRoot, allocationArtifactPath, bootstrapMetadata: { source: 'stage-c-offline-canonical-pipeline/v1' } });
    }
    const authoritySnapshot = openMarketEvidenceAuthoritySnapshot({ storeRoot, allocationArtifactPath });
    const candidate = buildProspectiveMarketEvidenceTransaction({ authoritySnapshot, universe, oddsRawText, captureReceipt: receiptEvidence, projectionVersion, supportedMarketKeys, authorizedSupersessions });
    const published = publishProspectiveMarketEvidenceTransaction({ storeRoot, allocationArtifactPath, candidate });
    const freshAuthoritySnapshot = openMarketEvidenceAuthoritySnapshot({ storeRoot, allocationArtifactPath });
    const publishedKnowledgeTime = verifyPublishedLogicalBatch({ storeRoot, candidate, published, freshAuthoritySnapshot });
    return Object.freeze({
        published,
        candidate,
        freshAuthoritySnapshot,
        matched_decision_count: candidate.identity_decisions.filter(row => row.decision === 'MATCHED').length,
        quarantined_decision_count: candidate.identity_decisions.filter(row => row.decision === 'QUARANTINED').length,
        observation_count: freshAuthoritySnapshot.observations.length,
        knowledge_time: publishedKnowledgeTime,
        authority_head_knowledge_time: freshAuthoritySnapshot.head_knowledge_time,
    });
}

module.exports = { loadOfflineEvidence, publishOfflineMarketEvidence, verifyPublishedLogicalBatch };
