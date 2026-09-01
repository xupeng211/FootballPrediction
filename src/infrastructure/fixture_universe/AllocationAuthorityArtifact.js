'use strict';

// The disk artifact, not an in-memory capability, is the cross-process
// allocation trust root.  Capabilities are issued only after every byte has
// been parsed, canonically re-hashed and validated again.
const fs = require('node:fs');
const path = require('node:path');
const { stableStringify, sha256Text } = require('../market_evidence/contracts');
const { validateAllocationSnapshot } = require('./FixtureUniverse');
const { issueAllocationAuthority, bindAllocationEvents, allocationDescriptor } = require('./VerifiedAllocationAuthority');

const ARTIFACT_SCHEMA_VERSION = 'footballprediction-allocation-authority-artifact/v1';

function regularFile(filePath, label) {
    const stat = fs.lstatSync(filePath);
    if (stat.isSymbolicLink() || !stat.isFile()) throw new Error(`${label} must be a regular file`);
    return stat;
}
function canonicalEnvelope(allocation) {
    return { schema_version: ARTIFACT_SCHEMA_VERSION, authority_owner: 'FootballPrediction', allocation_hash: allocation.content_sha256, allocation_provenance_raw_sha256: allocation.provenance_raw_sha256, allocation };
}
function serializeEnvelope(envelope) {
    const unsigned = { schema_version: envelope.schema_version, authority_owner: envelope.authority_owner, allocation_hash: envelope.allocation_hash, allocation_provenance_raw_sha256: envelope.allocation_provenance_raw_sha256, allocation: envelope.allocation };
    return { ...unsigned, artifact_sha256: sha256Text(stableStringify(unsigned)) };
}
function verifyEnvelope(parsed) {
    if (!parsed || typeof parsed !== 'object' || Array.isArray(parsed)) throw new Error('allocation authority artifact must be an object');
    const allowed = new Set(['schema_version', 'authority_owner', 'allocation_hash', 'allocation_provenance_raw_sha256', 'allocation', 'artifact_sha256']);
    if (Object.keys(parsed).some(key => !allowed.has(key))) throw new Error('allocation authority artifact contains unknown field');
    if (parsed.schema_version !== ARTIFACT_SCHEMA_VERSION || parsed.authority_owner !== 'FootballPrediction') throw new Error('allocation authority artifact schema or owner is invalid');
    const expected = serializeEnvelope(canonicalEnvelope(parsed.allocation));
    if (parsed.artifact_sha256 !== expected.artifact_sha256 || parsed.allocation_hash !== parsed.allocation?.content_sha256 || parsed.allocation_provenance_raw_sha256 !== parsed.allocation?.provenance_raw_sha256) throw new Error('allocation authority artifact hash is invalid');
    validateAllocationSnapshot(parsed.allocation, parsed.allocation_provenance_raw_sha256);
    return expected;
}
function authorityFromEnvelope(envelope) {
    const freshRuntime = Object.freeze({});
    const authority = bindAllocationEvents(issueAllocationAuthority(freshRuntime, envelope.allocation), envelope.allocation, envelope.allocation.fixtures.map(row => row.canonical_event_id));
    return Object.freeze({ allocationAuthority: authority, allocationSnapshot: Object.freeze({ ...envelope.allocation }), allocationHash: envelope.allocation_hash, artifactHash: envelope.artifact_sha256, provenanceRawSha256: envelope.allocation_provenance_raw_sha256 });
}
function persistVerifiedAllocationAuthority({ artifactPath, allocationAuthority }) {
    if (typeof artifactPath !== 'string' || !artifactPath.trim()) throw new Error('allocation artifact path is required');
    const descriptor = allocationDescriptor(allocationAuthority);
    const envelope = serializeEnvelope(canonicalEnvelope(descriptor.allocationSnapshot));
    const bytes = `${stableStringify(envelope)}\n`;
    fs.mkdirSync(path.dirname(artifactPath), { recursive: true });
    if (fs.existsSync(artifactPath)) {
        regularFile(artifactPath, 'allocation authority artifact');
        if (fs.readFileSync(artifactPath, 'utf8') !== bytes) throw new Error('allocation authority artifact already exists with different content');
    } else {
        fs.writeFileSync(artifactPath, bytes, { flag: 'wx', mode: 0o444 });
        fs.chmodSync(artifactPath, 0o444);
    }
    return loadVerifiedAllocationAuthority({ artifactPath });
}
function loadVerifiedAllocationAuthority({ artifactPath }) {
    if (typeof artifactPath !== 'string' || !artifactPath.trim() || !fs.existsSync(artifactPath)) throw new Error('allocation authority artifact is missing');
    const stat = regularFile(artifactPath, 'allocation authority artifact');
    if ((stat.mode & 0o222) !== 0) throw new Error('allocation authority artifact must be read-only');
    let parsed;
    try { parsed = JSON.parse(fs.readFileSync(artifactPath, 'utf8')); } catch (error) { throw new Error(`allocation authority artifact is invalid: ${error.message}`, { cause: error }); }
    return authorityFromEnvelope(verifyEnvelope(parsed));
}

module.exports = { ARTIFACT_SCHEMA_VERSION, persistVerifiedAllocationAuthority, loadVerifiedAllocationAuthority };
