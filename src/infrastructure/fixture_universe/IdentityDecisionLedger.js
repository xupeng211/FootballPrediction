'use strict';
/* eslint-disable complexity -- validation deliberately enumerates fail-closed ledger invariants. */

// File-first, append-only identity evidence.  Decisions are facts about a
// capture, never mutable aliases; active state is derived by replaying them.
const fs = require('node:fs');
const path = require('node:path');
const { sha256Text, stableStringify, isUtcTimestamp } = require('../market_evidence/contracts');
const { assertAllocationAuthority, assertResolvedDecision, allocationDescriptor } = require('./VerifiedAllocationAuthority');
const { loadVerifiedAllocationAuthority } = require('./AllocationAuthorityArtifact');

const MANIFEST_VERSION = 'footballprediction-identity-decision-ledger/v1';
const authenticLedgers = new WeakMap();
function manifestPath(ledgerPath) { return `${ledgerPath}.manifest.json`; }
function parse(content) { return content === '' ? [] : content.trimEnd().split('\n').map(line => JSON.parse(line)); }
function validate(row) {
    if (!row || typeof row !== 'object' || Array.isArray(row)) throw new Error('identity decision must be an object');
    for (const field of ['identity_decision_id', 'candidate_provider', 'candidate_provider_event_id', 'decision', 'ruleset_version', 'resolver_version', 'raw_sha256']) {
        if (typeof row[field] !== 'string' || !row[field].trim()) throw new Error(`identity decision requires ${field}`);
    }
    if (!['MATCHED', 'QUARANTINED'].includes(row.decision) || !isUtcTimestamp(row.decided_at) || !/^[a-f0-9]{64}$/.test(row.raw_sha256)) throw new Error('identity decision contract is invalid');
    if (row.decision === 'MATCHED' && !/^evt_[A-Za-z0-9]+$/.test(row.canonical_event_id || '')) throw new Error('matched identity decision requires governed canonical event');
    if (row.decision === 'QUARANTINED' && row.canonical_event_id !== null) throw new Error('quarantined identity decision cannot map an event');
    if (row.supersedes_decision_id !== undefined && row.supersedes_decision_id !== null && (typeof row.supersedes_decision_id !== 'string' || !row.supersedes_decision_id)) throw new Error('identity supersession reference is invalid');
}
function projectDecisionState(rows, allocationAuthority) {
    if (!Array.isArray(rows)) throw new Error('identity decision rows must be an array');
    const active = new Map(); const known = new Map(); const latest = new Map();
    for (const row of rows) {
        validate(row);
        if (!allocationAuthority) throw new Error('identity decision ledger has no verified allocation authority');
        if (row.decision === 'MATCHED') assertAllocationAuthority(allocationAuthority, row.canonical_event_id);
        const id = row.decision_id || row.identity_decision_id;
        if (known.has(id)) throw new Error(`duplicate identity decision: ${id}`);
        known.set(id, row);
        const key = `${row.candidate_provider}\u0000${row.candidate_provider_event_id}`;
        if (row.supersedes_decision_id) {
            const old = known.get(row.supersedes_decision_id);
            if (!old || latest.get(key) !== old || `${old.candidate_provider}\u0000${old.candidate_provider_event_id}` !== key) throw new Error('identity decision supersession chain is invalid');
            active.delete(key);
        } else if (latest.has(key)) {
            throw new Error(`identity decision must supersede latest decision: ${row.candidate_provider_event_id}`);
        }
        latest.set(key, row);
        if (row.decision === 'MATCHED') {
            if (active.has(key)) throw new Error(`conflicting active identity decisions: ${row.candidate_provider_event_id}`);
            active.set(key, row);
        }
    }
    return { latest, active };
}
function verify(ledgerPath) {
    const mp = manifestPath(ledgerPath);
    if (!fs.existsSync(ledgerPath)) {
        if (fs.existsSync(mp)) throw new Error('identity decision ledger manifest exists without ledger');
        return { content: '', rows: [] };
    }
    const stat = fs.lstatSync(ledgerPath);
    if (stat.isSymbolicLink() || !stat.isFile() || (stat.mode & 0o222) !== 0) throw new Error('identity decision ledger must be a read-only regular file');
    const content = fs.readFileSync(ledgerPath, 'utf8'); const rows = parse(content);
    if (!fs.existsSync(mp)) throw new Error('identity decision ledger manifest is missing');
    const manifestStat = fs.lstatSync(mp);
    if (manifestStat.isSymbolicLink() || !manifestStat.isFile() || (manifestStat.mode & 0o222) !== 0) throw new Error('identity decision ledger manifest must be a read-only regular file');
    const manifest = JSON.parse(fs.readFileSync(mp, 'utf8'));
    if (manifest.schema_version !== MANIFEST_VERSION || manifest.ledger_sha256 !== sha256Text(content) || manifest.line_count !== rows.length) throw new Error('identity decision ledger integrity check failed');
    rows.forEach(validate); return { content, rows, manifest };
}
function rewriteManifest(ledgerPath, content, lineCount, allocation) {
    const mp = manifestPath(ledgerPath);
    if (fs.existsSync(mp)) {
        const stat = fs.lstatSync(mp);
        if (stat.isSymbolicLink() || !stat.isFile()) throw new Error('identity decision ledger manifest must be a regular file');
        fs.chmodSync(mp, 0o644);
    }
    try { fs.writeFileSync(mp, `${stableStringify({ schema_version: MANIFEST_VERSION, ledger_sha256: sha256Text(content), line_count: lineCount, allocation_schema_version: allocation.schemaVersion, allocation_hash: allocation.allocationSnapshotSha256, allocation_provenance_raw_sha256: allocation.provenanceRawSha256, allocation_snapshot: allocation.allocationSnapshot })}\n`, { mode: 0o444 }); } finally { fs.chmodSync(mp, 0o444); }
}
function createIdentityDecisionLedger({ ledgerPath, allocationAuthority = null }) {
    if (typeof ledgerPath !== 'string' || !ledgerPath.trim()) throw new Error('identity decision ledger path is required');
    if (allocationAuthority !== null) assertAllocationAuthority(allocationAuthority, undefined);
    function bindAllocationAuthority(authority) {
        assertAllocationAuthority(authority, undefined);
        if (allocationAuthority !== null && allocationAuthority !== authority) throw new Error('identity decision ledger allocation authority cannot change');
        allocationAuthority = authority;
    }
    function decisionState() {
        const verified = verify(ledgerPath); const rows = verified.rows;
        if (rows.length) {
            const allocation = allocationDescriptor(allocationAuthority);
            if (verified.manifest.allocation_hash !== allocation.allocationSnapshotSha256 || verified.manifest.allocation_schema_version !== allocation.schemaVersion || verified.manifest.allocation_provenance_raw_sha256 !== allocation.provenanceRawSha256 || stableStringify(verified.manifest.allocation_snapshot) !== stableStringify(allocation.allocationSnapshot)) throw new Error('identity decision ledger is bound to a different allocation artifact');
        }
        return projectDecisionState(rows, allocationAuthority);
    }
    function activeMappings() { return decisionState().active; }
    function latestDecisions() { return decisionState().latest; }
    function append(row) {
        if (!allocationAuthority) throw new Error('identity decision ledger has no verified allocation authority');
        validate(row); assertResolvedDecision(row, allocationAuthority); if (row.decision === 'MATCHED') assertAllocationAuthority(allocationAuthority, row.canonical_event_id); const existing = verify(ledgerPath); const serialized = stableStringify(row);
        const sameId = existing.rows.find(item => item.identity_decision_id === row.identity_decision_id);
        if (sameId) { if (stableStringify(sameId) === serialized) return Object.freeze({ ...sameId }); throw new Error(`conflicting identity decision append: ${row.identity_decision_id}`); }
        const state = decisionState(); const key = `${row.candidate_provider}\u0000${row.candidate_provider_event_id}`; const latest = state.latest.get(key) || null;
        if (latest && !row.supersedes_decision_id) throw new Error(`identity decision must supersede latest decision: ${row.candidate_provider_event_id}`);
        if (row.supersedes_decision_id && (!latest || (latest.decision_id || latest.identity_decision_id) !== row.supersedes_decision_id)) throw new Error('identity decision supersedes non-latest decision');
        fs.mkdirSync(path.dirname(ledgerPath), { recursive: true }); if (fs.existsSync(ledgerPath)) fs.chmodSync(ledgerPath, 0o644);
        const line = `${serialized}\n`; try { fs.appendFileSync(ledgerPath, line, { mode: 0o444 }); rewriteManifest(ledgerPath, `${existing.content}${line}`, existing.rows.length + 1, allocationDescriptor(allocationAuthority)); } finally { fs.chmodSync(ledgerPath, 0o444); }
        return Object.freeze({ ...row });
    }
    function assertActiveMatched({ provider, providerEventId, canonicalEventId, decisionId, rulesetVersion, resolverVersion }) {
        const active = activeMappings().get(`${provider}\u0000${providerEventId}`);
        if (!active || active.decision !== 'MATCHED' || (active.decision_id || active.identity_decision_id) !== decisionId || active.canonical_event_id !== canonicalEventId || active.ruleset_version !== rulesetVersion || active.resolver_version !== resolverVersion) throw new Error('identity decision is not the exact active MATCHED ledger mapping');
        return Object.freeze({ ...active });
    }
    const ledger = Object.freeze({ append, bindAllocationAuthority, activeMappings, latestDecisions, latestDecision: (provider, providerEventId) => latestDecisions().get(`${provider}\u0000${providerEventId}`) || null, activeMatchedDecision: (provider, providerEventId) => activeMappings().get(`${provider}\u0000${providerEventId}`) || null, assertActiveMatched, isBoundTo: authority => allocationAuthority === authority, read: () => Object.freeze(verify(ledgerPath).rows.map(row => Object.freeze({ ...row }))), verify: () => verify(ledgerPath) });
    authenticLedgers.set(ledger, true);
    return ledger;
}
function openIdentityDecisionLedger({ ledgerPath, allocationArtifactPath }) {
    const allocation = loadVerifiedAllocationAuthority({ artifactPath: allocationArtifactPath });
    const ledger = createIdentityDecisionLedger({ ledgerPath, allocationAuthority: allocation.allocationAuthority });
    // Force all persisted manifest/allocation checks before a caller obtains
    // the reopened governance context.
    ledger.activeMappings();
    return Object.freeze({ ...allocation, ledger });
}
function isVerifiedIdentityDecisionLedger(value, authority) { return authenticLedgers.has(value) && value.isBoundTo(authority); }
module.exports = { createIdentityDecisionLedger, openIdentityDecisionLedger, verifyIdentityDecisionLedger: verify, identityDecisionLedgerManifestPath: manifestPath, isVerifiedIdentityDecisionLedger, validateIdentityDecision: validate, projectIdentityDecisionState: projectDecisionState };
