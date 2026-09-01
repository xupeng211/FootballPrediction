'use strict';

// This module deliberately keeps the brands private.  A JSON snapshot is
// evidence, not authority: callers cannot manufacture either capability by
// supplying an event list, a digest, or a lookalike object.
const universeAuthorities = new WeakMap();
const decisionAuthorities = new WeakMap();
const registryLedgers = new WeakMap();

function issueAllocationAuthority(universe, allocationSnapshot, existingAuthority = null) {
    const authority = existingAuthority || Object.freeze({});
    if (existingAuthority) assertAllocationAuthority(existingAuthority, undefined);
    universeAuthorities.set(universe, { authority, allocationSnapshot });
    return authority;
}
function allocationAuthorityFor(universe) {
    const record = universeAuthorities.get(universe);
    if (!record) throw new Error('Fixture Universe is not a verified FootballPrediction allocation authority');
    return record.authority;
}
function assertAllocationAuthority(authority, canonicalEventId) {
    if (!allocationBrands.has(authority)) throw new Error('verified FootballPrediction allocation authority is required');
    const record = allocationBrands.get(authority);
    if (canonicalEventId !== undefined && !record.eventIds.has(canonicalEventId)) throw new Error('canonical event is absent from the verified allocation authority');
    return record;
}
const allocationBrands = new WeakMap();
function bindAllocationEvents(authority, allocationSnapshot, eventIds) {
    allocationBrands.set(authority, { allocationSnapshotSha256: allocationSnapshot.content_sha256, provenanceRawSha256: allocationSnapshot.provenance_raw_sha256, schemaVersion: allocationSnapshot.schema_version, allocationSnapshot, eventIds: new Set(eventIds) });
    return authority;
}
function markResolvedDecision(decision, authority) { decisionAuthorities.set(decision, authority); return decision; }
function assertResolvedDecision(decision, authority) {
    if (decisionAuthorities.get(decision) !== authority) throw new Error('identity decision was not produced by the verified Fixture Universe resolver');
}
function bindRegistryDecisionLedger(registry, ledger) { registryLedgers.set(registry, ledger); }
function ledgerForRegistry(registry) { return registryLedgers.get(registry) || null; }
function allocationDescriptor(authority) { return assertAllocationAuthority(authority, undefined); }
module.exports = { issueAllocationAuthority, allocationAuthorityFor, bindAllocationEvents, assertAllocationAuthority, allocationDescriptor, markResolvedDecision, assertResolvedDecision, bindRegistryDecisionLedger, ledgerForRegistry };
