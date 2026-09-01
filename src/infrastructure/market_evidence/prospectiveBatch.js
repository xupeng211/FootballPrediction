'use strict';
/* eslint-disable complexity -- this is the deliberate all-or-nothing business validation boundary. */

const util = require('node:util');
const { stableStringify, sha256Text, createObservation, isUtcTimestamp } = require('./contracts');
const { resolveOddsEventsProspectively } = require('../fixture_universe/FixtureUniverse');
const { allocationAuthorityFor, allocationDescriptor } = require('../fixture_universe/VerifiedAllocationAuthority');
const { projectIdentityDecisionState } = require('../fixture_universe/IdentityDecisionLedger');
const { createProspectiveGovernanceContext } = require('../fixture_universe/ProspectiveGovernanceContext');
const { isVerifiedMarketEvidenceAuthoritySnapshot } = require('./authorityReader');
const { adaptTheOddsApiRaw } = require('./theOddsApiAdapter');
const { verifiedCaptureReceipt } = require('./evidenceStore');
const { TRANSACTION_SCHEMA_VERSION, REGISTRY_DELTA_SCHEMA_VERSION, METADATA_SCHEMA_VERSION, canonicalBytes, canonicalJson, hashCanonical, descriptorForBytes, createManifest, computeAuthorityStateHash, assertPlainObject } = require('./transactionContract');
const authenticCandidates = new WeakSet();

function assertStrictInputObject(value, label) {
    if (util.types.isProxy(value)) throw new Error(`${label} must not be a Proxy`);
    assertPlainObject(value, label);
    if (Object.getOwnPropertySymbols(value).length) throw new Error(`${label} contains symbol keys`);
    for (const key of Object.keys(value)) {
        const descriptor = Object.getOwnPropertyDescriptor(value, key);
        if (!descriptor || !Object.prototype.hasOwnProperty.call(descriptor, 'value')) throw new Error(`${label}.${key} must not be an accessor`);
    }
}
function snapshotPlainData(value, label = 'input', depth = 0, seen = new WeakSet()) {
    if (depth > 64) throw new Error(`${label} exceeds maximum depth`);
    if (value === null || typeof value === 'string' || typeof value === 'boolean') return value;
    if (typeof value === 'number') { if (!Number.isFinite(value)) throw new Error(`${label} contains a non-finite number`); return value; }
    if (typeof value !== 'object' || typeof value === 'function' || typeof value === 'symbol' || util.types.isProxy(value)) throw new Error(`${label} must be strict plain JSON data`);
    if (seen.has(value)) throw new Error(`${label} must not contain a cycle or shared mutable reference`);
    seen.add(value);
    if (Object.getOwnPropertySymbols(value).length) throw new Error(`${label} contains symbol keys`);
    if (Array.isArray(value)) return Object.freeze(value.map((item, index) => snapshotPlainData(item, `${label}[${index}]`, depth + 1, seen)));
    if (Object.getPrototypeOf(value) !== Object.prototype) throw new Error(`${label} must not have a custom prototype`);
    const out = {};
    for (const key of Object.keys(value).sort()) {
        const descriptor = Object.getOwnPropertyDescriptor(value, key);
        if (!descriptor || !Object.prototype.hasOwnProperty.call(descriptor, 'value')) throw new Error(`${label}.${key} must not be an accessor`);
        out[key] = snapshotPlainData(descriptor.value, `${label}.${key}`, depth + 1, seen);
    }
    return Object.freeze(out);
}
function assertSnapshotAllocation(snapshot, authority) {
    const descriptor = allocationDescriptor(authority);
    if (snapshot.allocation.allocation_schema_version !== descriptor.schemaVersion || snapshot.allocation.allocation_content_hash !== descriptor.allocationSnapshotSha256 || snapshot.allocation.allocation_provenance_raw_sha256 !== descriptor.provenanceRawSha256) throw new Error('authoritySnapshot is bound to a different allocation authority');
}
function decisionKey(row) { return `${row.candidate_provider}\u0000${row.candidate_provider_event_id}`; }
function registryKey(row) { return `${row.kind}\u0000${row.provider}\u0000${row.provider_id}`; }
function registryStateHash(registry) { return hashCanonical([...registry.entries()].sort(([a], [b]) => a.localeCompare(b))); }
function sortedRows(rows, key) { return [...rows].sort((left, right) => key(left).localeCompare(key(right))); }
function jsonl(rows) { return rows.length ? `${rows.map(stableStringify).join('\n')}\n` : ''; }
function semanticObservation(row) {
    const copy = { ...row };
    delete copy.projection_available_at;
    return copy;
}
function semanticObservationJsonl(rows) { return jsonl(rows.map(semanticObservation)); }
function sourceForCapture(capture, receiptSha256) {
    if (!capture || typeof capture !== 'object') throw new Error('captureReceipt is required');
    if (typeof capture.provider !== 'string' || typeof capture.capture_id !== 'string' || !/^[a-f0-9]{64}$/.test(capture.raw_sha256 || '')) throw new Error('captureReceipt identity is invalid');
    return { provider: capture.provider, capture_id: capture.capture_id, raw_sha256: capture.raw_sha256, receipt_sha256: receiptSha256 };
}
function registryEntries(registry) { return ['event', 'bookmaker', 'market', 'selection'].flatMap(kind => registry.list(kind)).map(entry => snapshotPlainData(entry, 'registry entry')); }
function buildRegistryDelta({ authoritySnapshot, registry, candidateDecisions }) {
    const base = new Map((authoritySnapshot.registry_state || []).map(row => [row.key, snapshotPlainData(Object.fromEntries(Object.entries(row).filter(([key]) => key !== 'key')), 'parent registry entry')]));
    const baseHash = registryStateHash(base); const delta = [];
    for (const entry of sortedRows(registryEntries(registry), registryKey)) {
        const key = registryKey(entry); const old = base.get(key);
        if (!old) { base.set(key, entry); delta.push(entry); continue; }
        if (canonicalJson(old) === canonicalJson(entry)) continue;
        const allowedDecisionRefresh = entry.kind === 'event' && old.kind === 'event' && candidateDecisions.some(row => row.candidate_provider === entry.provider && row.candidate_provider_event_id === entry.provider_id && row.identity_decision_id === entry.identity_decision_id && row.supersedes_decision_id);
        if (!allowedDecisionRefresh) throw new Error(`registry conflict: ${key}`);
        base.set(key, entry); delta.push(entry);
    }
    return { registry: base, delta: Object.freeze(delta), base_registry_state_sha256: baseHash, result_registry_state_sha256: registryStateHash(base) };
}
function duplicateSafeObservations(parent, observations) {
    const index = new Map(parent.observations.map(row => [row.observation_id, row])); const accepted = [];
    for (const row of sortedRows(observations, row => row.observation_id)) {
        const prior = index.get(row.observation_id);
        if (prior) { if (canonicalJson(semanticObservation(prior)) !== canonicalJson(semanticObservation(row))) throw new Error(`conflicting MarketObservation identity: ${row.observation_id}`); continue; }
        index.set(row.observation_id, row); accepted.push(row);
    }
    return { index, accepted: Object.freeze(accepted) };
}
function buildProspectiveMarketEvidenceTransaction(options = {}) {
    assertStrictInputObject(options, 'prospective builder options');
    const { authoritySnapshot, universe, oddsRawText, captureReceipt, projectionVersion = '1', projectionAvailableAt = undefined, supportedMarketKeys = ['h2h'], authorizedSupersessions = [] } = options;
    if (projectionAvailableAt !== undefined && projectionAvailableAt !== null) throw new Error('projection_available_at is publisher-owned and cannot be supplied to the prospective builder');
    if (!isVerifiedMarketEvidenceAuthoritySnapshot(authoritySnapshot)) throw new Error('verified MarketEvidenceAuthoritySnapshot is required');
    const authority = allocationAuthorityFor(universe); assertSnapshotAllocation(authoritySnapshot, authority);
    if (typeof oddsRawText !== 'string') throw new Error('oddsRawText is required');
    const verifiedReceipt = verifiedCaptureReceipt(captureReceipt);
    const capture = snapshotPlainData(verifiedReceipt.receipt, 'captureReceipt'); const safeSupportedMarketKeys = snapshotPlainData(supportedMarketKeys, 'supportedMarketKeys'); const safeSupersessions = snapshotPlainData(authorizedSupersessions, 'authorizedSupersessions');
    if (!Array.isArray(safeSupportedMarketKeys) || safeSupportedMarketKeys.some(key => typeof key !== 'string') || !Array.isArray(safeSupersessions) || safeSupersessions.some(key => typeof key !== 'string')) throw new Error('prospective builder collection input is invalid');
    const rawSha256 = sha256Text(oddsRawText); if (capture.raw_sha256 !== rawSha256) throw new Error('captureReceipt raw_sha256 does not match oddsRawText');
    const source = sourceForCapture(capture, verifiedReceipt.receipt_sha256);
    const captureKey = `${source.provider}\u0000${source.capture_id}`; const priorCapture = (authoritySnapshot.capture_bindings || []).find(row => row.key === captureKey);
    if (priorCapture) { const { key, ...priorSource } = priorCapture; if (canonicalJson(priorSource) !== canonicalJson(source)) throw new Error(`capture identity is already bound to different receipt or RAW content: ${source.capture_id}`); }
    const resolved = resolveOddsEventsProspectively({ oddsRawText, oddsRawSha256: rawSha256, universe, decidedAt: capture.response_received_at, priorDecisions: authoritySnapshot.decisions, authorizedSupersessions: new Set(safeSupersessions) });
    const parentDecisionIds = new Set(authoritySnapshot.decisions.map(row => row.identity_decision_id));
    const decisions = Object.freeze(sortedRows(resolved.decisions.filter(row => !parentDecisionIds.has(row.identity_decision_id)).map(row => snapshotPlainData(row, 'identity decision')), decisionKey));
    const overlay = createProspectiveGovernanceContext({ authoritySnapshot, allocationAuthority: authority, candidateDecisions: decisions });
    const registry = buildRegistryDelta({ authoritySnapshot, registry: resolved.registry, candidateDecisions: decisions });
    const adapted = adaptTheOddsApiRaw({ rawText: oddsRawText, capture, registry: resolved.registry, decisionLedger: overlay, projectionVersion, allowedProviderEventIds: new Set(resolved.aliases.map(alias => alias.provider_event_id)), supportedMarketKeys: safeSupportedMarketKeys });
    const observationState = duplicateSafeObservations(authoritySnapshot, adapted.map(row => createObservation(row)));
    const allDecisions = [...authoritySnapshot.decisions, ...decisions]; const projected = projectIdentityDecisionState(allDecisions, authority);
    const binding = { ...authoritySnapshot.allocation }; const postStateHash = computeAuthorityStateHash({ allocation: binding, decisions: allDecisions, latestDecisions: projected.latest, activeMatched: projected.active, registryState: registry.registry, observationIndex: observationState.index });
    const metadata = Object.freeze({ schema_version: METADATA_SCHEMA_VERSION, source, capture_receipt: capture }); const registryDelta = Object.freeze({ schema_version: REGISTRY_DELTA_SCHEMA_VERSION, base_registry_state_sha256: registry.base_registry_state_sha256, result_registry_state_sha256: registry.result_registry_state_sha256, entries: registry.delta });
    const bytes = Object.freeze({ 'identity_decisions.jsonl': jsonl(decisions), 'observations.jsonl': jsonl(observationState.accepted), 'registry_delta.json': canonicalBytes(registryDelta), 'metadata.json': canonicalBytes(metadata) });
    const artifacts = Object.freeze({ 'identity_decisions.jsonl': descriptorForBytes('identity_decisions.jsonl', bytes['identity_decisions.jsonl'], decisions.length), 'observations.jsonl': descriptorForBytes('observations.jsonl', bytes['observations.jsonl'], observationState.accepted.length, semanticObservationJsonl(observationState.accepted)), 'registry_delta.json': descriptorForBytes('registry_delta.json', bytes['registry_delta.json'], registry.delta.length), 'metadata.json': descriptorForBytes('metadata.json', bytes['metadata.json'], 1) });
    const versions = { resolver_version: decisions[0]?.resolver_version || 'fixture-identity-resolver/v1', ruleset_version: decisions[0]?.ruleset_version || 'fixture-identity-ruleset/v1', adapter_version: '1.0.0', projection_version: String(projectionVersion), registry_schema_version: REGISTRY_DELTA_SCHEMA_VERSION, registry_version: resolved.registry.version, observation_schema_version: 'footballprediction-market-observation/v1' };
    const sequence = authoritySnapshot.head_sequence + 1;
    if (!Number.isInteger(authoritySnapshot.head_sequence) || authoritySnapshot.head_sequence < 0) throw new Error('authoritySnapshot head sequence is invalid');
    const manifest = createManifest({ sequence, parent_transaction_id: authoritySnapshot.head_transaction_id, parent_transaction_content_hash: authoritySnapshot.head_transaction_content_hash, expected_parent_state_hash: authoritySnapshot.state_hash, post_state_hash: postStateHash, allocation: binding, source, versions, artifacts, decision_count: decisions.length, observation_count: observationState.accepted.length, registry_delta_count: registry.delta.length, quarantine_count: decisions.filter(row => row.decision === 'QUARANTINED').length, publication_metadata: { schema_version: 'transaction-publication/v1' } });
    const candidate = Object.freeze({ transaction_schema_version: TRANSACTION_SCHEMA_VERSION, sequence: manifest.sequence, parent_transaction_id: manifest.parent_transaction_id, parent_transaction_content_hash: manifest.parent_transaction_content_hash, parent_knowledge_time: authoritySnapshot.head_knowledge_time, expected_parent_state_hash: manifest.expected_parent_state_hash, allocation: manifest.allocation, logical_batch_key: manifest.logical_batch_key, logical_content_hash: manifest.logical_content_hash, identity_decisions: decisions, registry_delta: registryDelta, observations: observationState.accepted, metadata, artifact_bytes: bytes, artifacts, decision_count: manifest.decision_count, quarantine_count: manifest.quarantine_count, registry_delta_count: manifest.registry_delta_count, observation_count: manifest.observation_count, batch_content_hash: manifest.batch_content_hash, post_state_hash: manifest.post_state_hash, transaction_content_hash: manifest.transaction_content_hash, transaction_id: manifest.transaction_id, manifest: Object.freeze({ ...manifest }) });
    authenticCandidates.add(candidate);
    return candidate;
}

function isVerifiedProspectiveTransactionCandidate(value) { return authenticCandidates.has(value); }
function finalizeProspectiveMarketEvidenceTransactionForPublication(candidate) {
    if (!isVerifiedProspectiveTransactionCandidate(candidate)) throw new Error('verified ProspectiveTransactionCandidate is required');
    const wallClockNow = Date.now();
    const governedEvidenceTimes = [
        candidate.metadata.capture_receipt.response_received_at,
        candidate.metadata.capture_receipt.ingested_at,
        ...candidate.identity_decisions.map(row => row.decided_at),
        ...candidate.observations.flatMap(row => [row.response_received_at, row.ingested_at]),
    ];
    if (governedEvidenceTimes.some(value => !isUtcTimestamp(value))) throw new Error('publisher governed evidence time is invalid');
    const latestEvidenceTime = Math.max(...governedEvidenceTimes.map(value => Date.parse(value)));
    if (!Number.isFinite(latestEvidenceTime) || wallClockNow < latestEvidenceTime) throw new Error('publisher clock precedes captured evidence');
    const parentTime = candidate.parent_knowledge_time === null ? Number.NEGATIVE_INFINITY : Date.parse(candidate.parent_knowledge_time);
    if (!Number.isFinite(parentTime) && candidate.parent_knowledge_time !== null) throw new Error('parent authority knowledge time is invalid');
    const now = Math.max(wallClockNow, parentTime + 1);
    const knowledgeTime = new Date(now).toISOString();
    const observations = Object.freeze(candidate.observations.map(row => createObservation({ ...row, projection_available_at: knowledgeTime })));
    const artifactBytes = Object.freeze({ ...candidate.artifact_bytes, 'observations.jsonl': jsonl(observations) });
    const artifacts = Object.freeze({
        'identity_decisions.jsonl': descriptorForBytes('identity_decisions.jsonl', artifactBytes['identity_decisions.jsonl'], candidate.decision_count),
        'observations.jsonl': descriptorForBytes('observations.jsonl', artifactBytes['observations.jsonl'], observations.length, semanticObservationJsonl(observations)),
        'registry_delta.json': descriptorForBytes('registry_delta.json', artifactBytes['registry_delta.json'], candidate.registry_delta_count),
        'metadata.json': descriptorForBytes('metadata.json', artifactBytes['metadata.json'], 1),
    });
    const publicationMetadata = { ...candidate.manifest.publication_metadata, knowledge_time: knowledgeTime };
    const manifest = createManifest({
        sequence: candidate.sequence,
        parent_transaction_id: candidate.parent_transaction_id,
        parent_transaction_content_hash: candidate.parent_transaction_content_hash,
        expected_parent_state_hash: candidate.expected_parent_state_hash,
        post_state_hash: candidate.post_state_hash,
        allocation: candidate.allocation,
        source: candidate.metadata.source,
        versions: candidate.manifest.versions,
        artifacts,
        decision_count: candidate.decision_count,
        observation_count: observations.length,
        registry_delta_count: candidate.registry_delta_count,
        quarantine_count: candidate.quarantine_count,
        publication_metadata: publicationMetadata,
    });
    const finalized = Object.freeze({
        transaction_schema_version: TRANSACTION_SCHEMA_VERSION,
        sequence: manifest.sequence,
        parent_transaction_id: manifest.parent_transaction_id,
        parent_transaction_content_hash: manifest.parent_transaction_content_hash,
        parent_knowledge_time: candidate.parent_knowledge_time,
        expected_parent_state_hash: manifest.expected_parent_state_hash,
        allocation: manifest.allocation,
        logical_batch_key: manifest.logical_batch_key,
        logical_content_hash: manifest.logical_content_hash,
        identity_decisions: candidate.identity_decisions,
        registry_delta: candidate.registry_delta,
        observations,
        metadata: candidate.metadata,
        artifact_bytes: artifactBytes,
        artifacts,
        decision_count: manifest.decision_count,
        quarantine_count: manifest.quarantine_count,
        registry_delta_count: manifest.registry_delta_count,
        observation_count: manifest.observation_count,
        batch_content_hash: manifest.batch_content_hash,
        post_state_hash: manifest.post_state_hash,
        transaction_content_hash: manifest.transaction_content_hash,
        transaction_id: manifest.transaction_id,
        manifest: Object.freeze({ ...manifest }),
    });
    authenticCandidates.add(finalized);
    return finalized;
}
module.exports = { snapshotPlainData, buildProspectiveMarketEvidenceTransaction, isVerifiedProspectiveTransactionCandidate, finalizeProspectiveMarketEvidenceTransactionForPublication };
