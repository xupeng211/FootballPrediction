'use strict';

// lifecycle: test-fixture
// Deterministic, explicitly synthetic M3 canonical inventory populations. No
// real club names, FotMob payloads, endpoints, or provenance are represented.

const crypto = require('node:crypto');
const fs = require('node:fs');
const path = require('node:path');
const {
    COMPETITION,
    SCHEMA_VERSION,
    SEASONS,
    computeBusinessHash,
    computeV1IdentityProjectionHash,
    canonicalOrder,
} = require('../../src/infrastructure/canonical/CanonicalInventoryContract');
const { DISPOSABLE_OPERATION } = require('../../src/infrastructure/canonical/CanonicalInventoryAuthorization');
const { SCHEMA_BASELINE } = require('../../src/infrastructure/canonical/CanonicalInventoryWriter');

function sha256(value) {
    return crypto.createHash('sha256').update(value).digest('hex');
}

function syntheticCandidates() {
    const candidates = [];
    let sourceId = 9000000;
    for (const season of SEASONS) {
        const startYear = Number(season.slice(0, 4));
        for (let index = 0; index < 380; index += 1) {
            const kickoff = new Date(Date.UTC(startYear, 7, 1 + index, 12, 0, 0)).toISOString().replace('.000Z', 'Z');
            const id = String(sourceId++);
            candidates.push({
                id: `47_${season.replace('/', '')}_${id}`,
                source_provider: 'FotMob',
                source_match_id: id,
                competition: COMPETITION,
                season,
                home_team: `Synthetic ${season} Home ${String(index).padStart(3, '0')}`,
                away_team: `Synthetic ${season} Away ${String(index).padStart(3, '0')}`,
                kickoff_at: kickoff,
                status: index % 5 === 0 ? 'finished' : 'scheduled',
            });
        }
    }
    return candidates.sort(canonicalOrder);
}

function seasonCounts(candidates) {
    return candidates.reduce(
        (out, candidate) => ({ ...out, [candidate.season]: (out[candidate.season] || 0) + 1 }),
        {}
    );
}

function buildDocument(candidates, { kind = 'master', parentMaster = null } = {}) {
    const sorted = [...candidates].sort(canonicalOrder);
    const artifact = {
        kind,
        synthetic_test_only: true,
        business_hash: computeBusinessHash(sorted),
        identity_projection_hash: computeV1IdentityProjectionHash(sorted),
        candidate_count: sorted.length,
        competition: COMPETITION,
        seasons: [...SEASONS],
        per_season_counts: seasonCounts(sorted),
    };
    if (kind === 'canary') {
        artifact.parent_master = parentMaster;
        artifact.allowlist = sorted.map(candidate => candidate.id);
    }
    return { schema_version: SCHEMA_VERSION, artifact, candidates: sorted };
}

function writeDocument(directory, fileName, document) {
    const filePath = path.join(directory, fileName);
    const body = `${JSON.stringify(document)}\n`;
    fs.writeFileSync(filePath, body, { encoding: 'utf8', flag: 'wx' });
    return { path: filePath, sha256: sha256(body), byte_size: Buffer.byteLength(body) };
}

function parentMetadata(masterDocument, masterBinding) {
    return {
        sha256: masterBinding.sha256,
        byte_size: masterBinding.byte_size,
        business_hash: masterDocument.artifact.business_hash,
        identity_projection_hash: masterDocument.artifact.identity_projection_hash,
        candidate_count: masterDocument.artifact.candidate_count,
        per_season_counts: masterDocument.artifact.per_season_counts,
    };
}

function runtimeReceipt({
    artifact,
    sha256: artifactSha,
    databaseIdentity,
    serviceIdentity,
    executionId = crypto.randomUUID(),
    expiresAt = new Date(Date.now() + 60_000).toISOString(),
}) {
    return {
        execution_id: executionId,
        operation_type: DISPOSABLE_OPERATION,
        issued_at: new Date(Date.now() - 1_000).toISOString(),
        expires_at: expiresAt,
        target: {
            classification: 'disposable',
            database_identity: databaseIdentity,
            service_identity: serviceIdentity,
            schema_baseline: SCHEMA_BASELINE,
        },
        artifact: {
            sha256: artifactSha,
            business_hash: artifact.business_hash,
            identity_projection_hash: artifact.identity_projection_hash,
            kind: artifact.kind,
            candidate_count: artifact.candidate_count,
            competition: artifact.competition,
            seasons: artifact.seasons,
        },
    };
}

function syntheticProvenance(artifactSha) {
    return {
        artifact_sha256: artifactSha,
        synthetic_test_only: true,
        non_production: true,
        provenance_class: 'synthetic-test-only',
    };
}

module.exports = {
    buildDocument,
    parentMetadata,
    runtimeReceipt,
    sha256,
    syntheticCandidates,
    syntheticProvenance,
    writeDocument,
};
