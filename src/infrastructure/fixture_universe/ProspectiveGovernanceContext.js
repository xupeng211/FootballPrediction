'use strict';

// The brand is intentionally private: adapters may consume a prospective
// overlay only when it was derived from an authoritative transaction snapshot.
const { stableStringify } = require('../market_evidence/contracts');
const { allocationDescriptor, assertAllocationAuthority } = require('./VerifiedAllocationAuthority');
const { projectIdentityDecisionState } = require('./IdentityDecisionLedger');
const { isVerifiedMarketEvidenceAuthoritySnapshot } = require('../market_evidence/authorityReader');

const contexts = new WeakMap();
function allocationEquals(left, right) { return stableStringify(left) === stableStringify(right); }
function createProspectiveGovernanceContext({ authoritySnapshot, allocationAuthority, candidateDecisions }) {
    if (!isVerifiedMarketEvidenceAuthoritySnapshot(authoritySnapshot)) throw new Error('verified MarketEvidenceAuthoritySnapshot is required');
    const descriptor = allocationDescriptor(allocationAuthority);
    if (!allocationEquals(authoritySnapshot.allocation, { allocation_schema_version: descriptor.schemaVersion, allocation_content_hash: descriptor.allocationSnapshotSha256, allocation_artifact_sha256: authoritySnapshot.allocation.allocation_artifact_sha256, allocation_provenance_raw_sha256: descriptor.provenanceRawSha256 })) throw new Error('authority snapshot is bound to a different allocation authority');
    if (!Array.isArray(candidateDecisions)) throw new Error('candidate decisions must be an array');
    const decisions = [...authoritySnapshot.decisions, ...candidateDecisions];
    const state = projectIdentityDecisionState(decisions, allocationAuthority);
    const context = Object.freeze({
        assertActiveMatched({ provider, providerEventId, canonicalEventId, decisionId, rulesetVersion, resolverVersion }) {
            const active = state.active.get(`${provider}\u0000${providerEventId}`);
            if (!active || active.decision !== 'MATCHED' || active.identity_decision_id !== decisionId || active.canonical_event_id !== canonicalEventId || active.ruleset_version !== rulesetVersion || active.resolver_version !== resolverVersion) throw new Error('identity decision is not the exact prospective active MATCHED mapping');
            return Object.freeze({ ...active });
        },
        latestDecision: (provider, providerEventId) => state.latest.get(`${provider}\u0000${providerEventId}`) || null,
        activeMatchedDecision: (provider, providerEventId) => state.active.get(`${provider}\u0000${providerEventId}`) || null,
    });
    contexts.set(context, { allocationAuthority, decisions: Object.freeze([...decisions]), latest: state.latest, active: state.active });
    return context;
}
function isVerifiedProspectiveGovernanceContext(value, authority) { const record = contexts.get(value); return Boolean(record && record.allocationAuthority === authority); }
function prospectiveGovernanceState(value, authority) { if (!isVerifiedProspectiveGovernanceContext(value, authority)) throw new Error('verified prospective governance context is required'); return contexts.get(value); }
module.exports = { createProspectiveGovernanceContext, isVerifiedProspectiveGovernanceContext, prospectiveGovernanceState };
