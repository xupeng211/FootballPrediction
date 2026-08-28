'use strict';
/* eslint-disable complexity -- validation deliberately enumerates fail-closed ledger invariants. */

// File-first, append-only identity evidence.  Decisions are facts about a
// capture, never mutable aliases; active state is derived by replaying them.
const fs = require('node:fs');
const path = require('node:path');
const { sha256Text, stableStringify, isUtcTimestamp } = require('../market_evidence/contracts');

const MANIFEST_VERSION = 'footballprediction-identity-decision-ledger/v1';
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
function verify(ledgerPath) {
    if (!fs.existsSync(ledgerPath)) return { content: '', rows: [] };
    const content = fs.readFileSync(ledgerPath, 'utf8'); const rows = parse(content);
    const mp = manifestPath(ledgerPath);
    if (!fs.existsSync(mp)) throw new Error('identity decision ledger manifest is missing');
    const manifest = JSON.parse(fs.readFileSync(mp, 'utf8'));
    if (manifest.schema_version !== MANIFEST_VERSION || manifest.ledger_sha256 !== sha256Text(content) || manifest.line_count !== rows.length) throw new Error('identity decision ledger integrity check failed');
    rows.forEach(validate); return { content, rows };
}
function rewriteManifest(ledgerPath, content, lineCount) {
    const mp = manifestPath(ledgerPath); if (fs.existsSync(mp)) fs.chmodSync(mp, 0o644);
    try { fs.writeFileSync(mp, `${stableStringify({ schema_version: MANIFEST_VERSION, ledger_sha256: sha256Text(content), line_count: lineCount })}\n`, { mode: 0o444 }); } finally { fs.chmodSync(mp, 0o444); }
}
function createIdentityDecisionLedger({ ledgerPath }) {
    if (typeof ledgerPath !== 'string' || !ledgerPath.trim()) throw new Error('identity decision ledger path is required');
    function activeMappings() {
        const rows = verify(ledgerPath).rows; const active = new Map(); const known = new Map();
        for (const row of rows) {
            const id = row.decision_id || row.identity_decision_id; known.set(id, row);
            const key = `${row.candidate_provider}\u0000${row.candidate_provider_event_id}`;
            if (row.supersedes_decision_id) {
                const old = known.get(row.supersedes_decision_id);
                if (!old || `${old.candidate_provider}\u0000${old.candidate_provider_event_id}` !== key) throw new Error('identity decision supersession chain is invalid');
                active.delete(key);
            }
            if (row.decision === 'MATCHED') {
                if (active.has(key)) throw new Error(`conflicting active identity decisions: ${row.candidate_provider_event_id}`);
                active.set(key, row);
            }
        }
        return active;
    }
    function append(row) {
        validate(row); const existing = verify(ledgerPath); const serialized = stableStringify(row);
        const sameId = existing.rows.find(item => item.identity_decision_id === row.identity_decision_id);
        if (sameId) { if (stableStringify(sameId) === serialized) return Object.freeze({ ...sameId }); throw new Error(`conflicting identity decision append: ${row.identity_decision_id}`); }
        const active = activeMappings(); const key = `${row.candidate_provider}\u0000${row.candidate_provider_event_id}`;
        if (row.decision === 'MATCHED' && active.has(key) && !row.supersedes_decision_id) throw new Error(`conflicting active identity decisions: ${row.candidate_provider_event_id}`);
        if (row.supersedes_decision_id && (!active.has(key) || (active.get(key).decision_id || active.get(key).identity_decision_id) !== row.supersedes_decision_id)) throw new Error('identity decision supersedes non-active decision');
        fs.mkdirSync(path.dirname(ledgerPath), { recursive: true }); if (fs.existsSync(ledgerPath)) fs.chmodSync(ledgerPath, 0o644);
        const line = `${serialized}\n`; try { fs.appendFileSync(ledgerPath, line, { mode: 0o444 }); rewriteManifest(ledgerPath, `${existing.content}${line}`, existing.rows.length + 1); } finally { fs.chmodSync(ledgerPath, 0o444); }
        return Object.freeze({ ...row });
    }
    return Object.freeze({ append, activeMappings, read: () => Object.freeze(verify(ledgerPath).rows.map(row => Object.freeze({ ...row }))), verify: () => verify(ledgerPath) });
}
module.exports = { createIdentityDecisionLedger, verifyIdentityDecisionLedger: verify, identityDecisionLedgerManifestPath: manifestPath };
