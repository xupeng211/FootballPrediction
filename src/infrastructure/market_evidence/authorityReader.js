'use strict';
/* eslint-disable complexity -- transaction replay deliberately rejects every invalid graph shape. */

// Read-only authority for transaction-v1.  A directory becomes eligible only
// after a future publisher renames it below committed/.  .staging is never
// inspected as authority.
const fs = require('node:fs');
const path = require('node:path');
const { loadVerifiedAllocationAuthority } = require('../fixture_universe/AllocationAuthorityArtifact');
const { projectIdentityDecisionState } = require('../fixture_universe/IdentityDecisionLedger');
const { createObservation, stableStringify, isUtcTimestamp } = require('./contracts');
const { readStoreContract } = require('./transactionStore');
const { ARTIFACT_FILES, TRANSACTION_FILES, REGISTRY_DELTA_SCHEMA_VERSION, METADATA_SCHEMA_VERSION, canonicalBytes, canonicalJson, hashCanonical, descriptorForBytes, validateManifest, validateCommittedMarker, computeAuthorityStateHash, assertPlainObject } = require('./transactionContract');

const TX_DIRECTORY = /^tx_[a-f0-9]{64}$/;
const authenticSnapshots = new WeakSet();
function statDirectory(target, label) { const stat = fs.lstatSync(target); if (stat.isSymbolicLink() || !stat.isDirectory()) throw new Error(`${label} must be a non-symlink directory`); return stat; }
function readRegularFile(target, label) {
    const before = fs.lstatSync(target); if (before.isSymbolicLink() || !before.isFile()) throw new Error(`${label} must be a regular file`);
    const flags = fs.constants.O_RDONLY | (fs.constants.O_NOFOLLOW || 0); let fd;
    try {
        fd = fs.openSync(target, flags); const opened = fs.fstatSync(fd); if (!opened.isFile() || opened.dev !== before.dev || opened.ino !== before.ino) throw new Error(`${label} changed during open`);
        const bytes = fs.readFileSync(fd, 'utf8'); const after = fs.fstatSync(fd); if (after.dev !== opened.dev || after.ino !== opened.ino) throw new Error(`${label} changed during read`);
        return bytes;
    } finally { if (fd !== undefined) fs.closeSync(fd); }
}
function parseCanonicalJson(bytes, label) {
    let parsed; try { parsed = JSON.parse(bytes); } catch (error) { throw new Error(`${label} is invalid JSON: ${error.message}`, { cause: error }); }
    if (bytes !== canonicalBytes(parsed)) throw new Error(`${label} must use canonical serialization`);
    return parsed;
}
function parseCanonicalJsonl(bytes, label) {
    if (bytes === '') return [];
    if (!bytes.endsWith('\n')) throw new Error(`${label} must end with a newline`);
    const lines = bytes.slice(0, -1).split('\n'); if (lines.some(line => !line)) throw new Error(`${label} contains a blank line`);
    return lines.map((line, index) => {
        let parsed; try { parsed = JSON.parse(line); } catch (error) { throw new Error(`${label} line ${index + 1} is invalid JSON: ${error.message}`, { cause: error }); }
        if (line !== stableStringify(parsed)) throw new Error(`${label} line ${index + 1} is not canonical`);
        return parsed;
    });
}
function registryKey(entry) {
    assertPlainObject(entry, 'registry delta entry');
    for (const key of ['kind', 'provider', 'provider_id']) if (typeof entry[key] !== 'string' || !entry[key]) throw new Error(`registry delta entry requires ${key}`);
    return `${entry.kind}\u0000${entry.provider}\u0000${entry.provider_id}`;
}
function validateRegistryDelta(value) {
    assertPlainObject(value, 'registry_delta');
    const keys = ['schema_version', 'entries', 'base_registry_state_sha256', 'result_registry_state_sha256']; if (Object.keys(value).some(key => !keys.includes(key)) || !Object.prototype.hasOwnProperty.call(value, 'schema_version') || !Object.prototype.hasOwnProperty.call(value, 'entries')) throw new Error('registry_delta fields are invalid');
    if (value.schema_version !== REGISTRY_DELTA_SCHEMA_VERSION || !Array.isArray(value.entries)) throw new Error('registry_delta contract is invalid');
    const seen = new Set(); const entries = value.entries.map(entry => { const key = registryKey(entry); if (seen.has(key)) throw new Error(`duplicate registry delta entry: ${key}`); seen.add(key); return Object.freeze(JSON.parse(canonicalJson(entry))); });
    for (const key of ['base_registry_state_sha256', 'result_registry_state_sha256']) if (value[key] !== undefined && !/^[a-f0-9]{64}$/.test(value[key])) throw new Error(`registry_delta ${key} is invalid`);
    return Object.freeze({ schema_version: value.schema_version, entries: Object.freeze(entries), ...(value.base_registry_state_sha256 === undefined ? {} : { base_registry_state_sha256: value.base_registry_state_sha256 }), ...(value.result_registry_state_sha256 === undefined ? {} : { result_registry_state_sha256: value.result_registry_state_sha256 }) });
}
function validateMetadata(value, manifest) {
    assertPlainObject(value, 'metadata');
    if (value.schema_version !== METADATA_SCHEMA_VERSION) throw new Error('metadata schema_version is invalid');
    if (canonicalJson(value.source || null) !== canonicalJson(manifest.source)) throw new Error('metadata source does not bind manifest source');
    return Object.freeze(JSON.parse(canonicalJson(value)));
}
function semanticObservationBytes(observations) {
    if (!observations.length) return '';
    return `${observations.map(row => { const copy = { ...row }; delete copy.projection_available_at; return stableStringify(copy); }).join('\n')}\n`;
}
function validatePublisherKnowledgeTime(manifest, observations) {
    const knowledgeTime = manifest.publication_metadata?.knowledge_time;
    if (typeof knowledgeTime !== 'string' || !isUtcTimestamp(knowledgeTime)) throw new Error('transaction publication knowledge_time is required and must be UTC ISO-8601');
    if (observations.some(row => row.projection_available_at !== knowledgeTime)) throw new Error('observation projection_available_at does not match publisher knowledge_time');
}
function entrySet(committedPath) {
    statDirectory(committedPath, 'committed directory');
    const entries = fs.readdirSync(committedPath).sort();
    for (const name of entries) if (!TX_DIRECTORY.test(name)) throw new Error(`unexpected committed entry: ${name}`);
    return entries;
}
function readPackage(committedPath, directoryName) {
    const txPath = path.join(committedPath, directoryName); statDirectory(txPath, 'transaction directory');
    const names = fs.readdirSync(txPath).sort();
    if (canonicalJson(names) !== canonicalJson([...TRANSACTION_FILES].sort())) throw new Error(`transaction ${directoryName} has an unexpected file set`);
    const bytes = {}; for (const name of TRANSACTION_FILES) bytes[name] = readRegularFile(path.join(txPath, name), `transaction artifact ${name}`);
    const manifest = validateManifest(parseCanonicalJson(bytes['manifest.json'], 'manifest.json'));
    if (directoryName !== manifest.transaction_id) throw new Error('transaction directory name does not match manifest transaction_id');
    validateCommittedMarker(parseCanonicalJson(bytes.COMMITTED, 'COMMITTED'), manifest);
    const metadata = validateMetadata(parseCanonicalJson(bytes['metadata.json'], 'metadata.json'), manifest);
    const registryDelta = validateRegistryDelta(parseCanonicalJson(bytes['registry_delta.json'], 'registry_delta.json'));
    const decisions = parseCanonicalJsonl(bytes['identity_decisions.jsonl'], 'identity_decisions.jsonl');
    const observations = parseCanonicalJsonl(bytes['observations.jsonl'], 'observations.jsonl').map(createObservation);
    validatePublisherKnowledgeTime(manifest, observations);
    const actual = {
        'identity_decisions.jsonl': descriptorForBytes('identity_decisions.jsonl', bytes['identity_decisions.jsonl'], decisions.length),
        'observations.jsonl': descriptorForBytes('observations.jsonl', bytes['observations.jsonl'], observations.length, semanticObservationBytes(observations)),
        'registry_delta.json': descriptorForBytes('registry_delta.json', bytes['registry_delta.json'], registryDelta.entries.length),
        'metadata.json': descriptorForBytes('metadata.json', bytes['metadata.json'], 1),
    };
    for (const artifact of ARTIFACT_FILES) if (canonicalJson(actual[artifact]) !== canonicalJson(manifest.artifacts[artifact])) throw new Error(`artifact descriptor does not match bytes: ${artifact}`);
    if (manifest.decision_count !== decisions.length || manifest.observation_count !== observations.length || manifest.registry_delta_count !== registryDelta.entries.length) throw new Error('transaction count does not match artifacts');
    const quarantines = decisions.filter(row => row.decision === 'QUARANTINED').length; if (manifest.quarantine_count !== quarantines) throw new Error('transaction quarantine count does not match decisions');
    return Object.freeze({ manifest, metadata, registryDelta, decisions: Object.freeze(decisions), observations: Object.freeze(observations) });
}
function reconstruct(packages, store, allocationAuthority) {
    if (!packages.length) return buildSnapshot({ store, allocationAuthority, head: null, decisions: [], registry: new Map(), observations: new Map() });
    const byId = new Map(packages.map(item => [item.manifest.transaction_id, item]));
    const children = new Map(); const roots = [];
    for (const item of packages) {
        const m = item.manifest;
        if (m.parent_transaction_id === null) roots.push(item);
        else {
            const parent = byId.get(m.parent_transaction_id); if (!parent) throw new Error(`orphan transaction: ${m.transaction_id}`);
            if (parent.manifest.transaction_content_hash !== m.parent_transaction_content_hash) throw new Error(`wrong parent content hash: ${m.transaction_id}`);
            const list = children.get(m.parent_transaction_id) || []; list.push(item); children.set(m.parent_transaction_id, list);
        }
    }
    if (roots.length !== 1) throw new Error('transaction chain must have exactly one root');
    let current = roots[0]; const ordered = [];
    while (current) { ordered.push(current); const next = children.get(current.manifest.transaction_id) || []; if (next.length > 1) throw new Error(`transaction fork at ${current.manifest.transaction_id}`); current = next[0] || null; }
    if (ordered.length !== packages.length) throw new Error('transaction chain contains an orphan or multiple head');
    const decisions = []; const registry = new Map(); const observations = new Map(); let stateHash = store.genesis_state_hash; let parent = null;
    for (const item of ordered) {
        const m = item.manifest;
        if (m.sequence !== ordered.indexOf(item) + 1) throw new Error(`transaction sequence gap at ${m.transaction_id}`);
        if (parent === null) { if (m.parent_transaction_id !== null || m.parent_transaction_content_hash !== null) throw new Error('root transaction has a parent'); }
        else if (m.parent_transaction_id !== parent.manifest.transaction_id || m.parent_transaction_content_hash !== parent.manifest.transaction_content_hash) throw new Error(`wrong parent transaction: ${m.transaction_id}`);
        if (m.expected_parent_state_hash !== stateHash) throw new Error(`wrong parent state hash: ${m.transaction_id}`);
        for (const row of item.decisions) { if (decisions.some(old => old.identity_decision_id === row.identity_decision_id)) throw new Error(`duplicate decision across transactions: ${row.identity_decision_id}`); decisions.push(row); }
        const projected = projectIdentityDecisionState(decisions, allocationAuthority);
        const baseRegistryHash = hashCanonical([...registry.entries()].sort(([a], [b]) => a.localeCompare(b)));
        if (item.registryDelta.base_registry_state_sha256 !== undefined && item.registryDelta.base_registry_state_sha256 !== baseRegistryHash) throw new Error(`registry delta base state hash is invalid: ${m.transaction_id}`);
        for (const entry of item.registryDelta.entries) {
            const key = registryKey(entry); const existing = registry.get(key);
            // Event aliases are an append-only governance projection: a later
            // MATCHED decision may replace only the active alias it explicitly
            // supersedes.  Other registry keys are immutable across the chain.
            const authorizedEventRefresh = existing && existing.kind === 'event' && entry.kind === 'event' && item.decisions.some(decision => decision.candidate_provider === entry.provider && decision.candidate_provider_event_id === entry.provider_id && decision.identity_decision_id === entry.identity_decision_id && decision.supersedes_decision_id);
            if (existing && canonicalJson(existing) !== canonicalJson(entry) && !authorizedEventRefresh) throw new Error(`registry conflict across transactions: ${key}`);
            registry.set(key, entry);
        }
        const resultRegistryHash = hashCanonical([...registry.entries()].sort(([a], [b]) => a.localeCompare(b)));
        if (item.registryDelta.result_registry_state_sha256 !== undefined && item.registryDelta.result_registry_state_sha256 !== resultRegistryHash) throw new Error(`registry delta result state hash is invalid: ${m.transaction_id}`);
        for (const row of item.observations) { const existing = observations.get(row.observation_id); if (existing) throw new Error(`duplicate observation across transactions: ${row.observation_id}`); observations.set(row.observation_id, row); }
        stateHash = computeAuthorityStateHash({ allocation: store.allocation, decisions, latestDecisions: projected.latest, activeMatched: projected.active, registryState: registry, observationIndex: observations });
        if (stateHash !== m.post_state_hash) throw new Error(`post_state_hash is invalid: ${m.transaction_id}`);
        parent = item;
    }
    return buildSnapshot({ store, allocationAuthority, head: parent, decisions, registry, observations });
}
function buildSnapshot({ store, allocationAuthority, head, decisions, registry, observations }) {
    const projected = projectIdentityDecisionState(decisions, allocationAuthority);
    const stateHash = computeAuthorityStateHash({ allocation: store.allocation, decisions, latestDecisions: projected.latest, activeMatched: projected.active, registryState: registry, observationIndex: observations });
    const freezeRows = rows => Object.freeze(rows.map(row => Object.freeze({ ...row })));
    const decisionRows = freezeRows(decisions); const observationRows = freezeRows([...observations.values()]); const registryRows = Object.freeze([...registry.entries()].sort(([a], [b]) => a.localeCompare(b)).map(([key, value]) => Object.freeze({ key, ...value })));
    const latest = new Map([...projected.latest].map(([key, value]) => [key, Object.freeze({ ...value })])); const active = new Map([...projected.active].map(([key, value]) => [key, Object.freeze({ ...value })]));
    const snapshot = Object.freeze({
        head_transaction_id: head ? head.manifest.transaction_id : null,
        head_transaction_content_hash: head ? head.manifest.transaction_content_hash : null,
        head_sequence: head ? head.manifest.sequence : 0,
        head_knowledge_time: head ? head.manifest.publication_metadata.knowledge_time : null,
        state_hash: stateHash,
        allocation: Object.freeze({ ...store.allocation }),
        decisions: decisionRows,
        observations: observationRows,
        registry_state: registryRows,
        latestDecision: (provider, providerEventId) => latest.get(`${provider}\u0000${providerEventId}`) || null,
        activeMatched: (provider, providerEventId) => active.get(`${provider}\u0000${providerEventId}`) || null,
        aliases: Object.freeze([...active.entries()].map(([key, row]) => Object.freeze({ key, provider: row.candidate_provider, provider_event_id: row.candidate_provider_event_id, canonical_event_id: row.canonical_event_id, identity_decision_id: row.identity_decision_id }))),
    });
    authenticSnapshots.add(snapshot);
    return snapshot;
}
function openMarketEvidenceAuthoritySnapshot({ storeRoot, allocationArtifactPath, maxRetries = 2 }) {
    if (!Number.isInteger(maxRetries) || maxRetries < 0 || maxRetries > 10) throw new Error('maxRetries is invalid');
    const contract = readStoreContract({ storeRoot, allocationArtifactPath }); const allocation = loadVerifiedAllocationAuthority({ artifactPath: allocationArtifactPath }); const committedPath = path.join(contract.root, 'committed');
    for (let attempt = 0; attempt <= maxRetries; attempt += 1) {
        const before = entrySet(committedPath); const packages = before.map(name => readPackage(committedPath, name)); const snapshot = reconstruct(packages, contract.store, allocation.allocationAuthority); const after = entrySet(committedPath);
        if (canonicalJson(before) === canonicalJson(after)) return snapshot;
    }
    throw new Error('committed transaction entries changed during authority read');
}

function isVerifiedMarketEvidenceAuthoritySnapshot(value) { return authenticSnapshots.has(value); }
module.exports = { openMarketEvidenceAuthoritySnapshot, isVerifiedMarketEvidenceAuthoritySnapshot, validateRegistryDelta, readPackage };
