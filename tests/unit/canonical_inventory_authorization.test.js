'use strict';

// lifecycle: permanent

const assert = require('node:assert/strict');
const test = require('node:test');
const {
    CanonicalInventoryAuthorizationError,
    DISPOSABLE_OPERATION,
    validateProvenanceReceipt,
    validateRuntimeAuthorization,
} = require('../../src/infrastructure/canonical/CanonicalInventoryAuthorization');

const artifact = {
    sha256: 'a'.repeat(64),
    business_hash: 'b'.repeat(64),
    identity_projection_hash: 'c'.repeat(64),
    kind: 'master',
    candidate_count: 1140,
    competition: 'Premier League',
    seasons: ['2022/2023', '2023/2024', '2024/2025'],
};
const binding = {
    service_identity: 'disposable-service',
    database_identity: 'fp_m3_canonical_ephemeral_test',
    schema_baseline: 'm3-canonical-inventory-v26.10',
    artifact,
};
function receipt(overrides = {}) {
    return {
        execution_id: 'execution-1',
        operation_type: DISPOSABLE_OPERATION,
        issued_at: '2026-01-01T00:00:00Z',
        expires_at: '2026-01-01T01:00:00Z',
        target: {
            classification: 'disposable',
            service_identity: binding.service_identity,
            database_identity: binding.database_identity,
            schema_baseline: binding.schema_baseline,
        },
        artifact,
        ...overrides,
    };
}

test('runtime receipt is target/hash/scope/expiry bound and persistent operations fail closed', () => {
    assert.equal(
        validateRuntimeAuthorization(receipt(), binding, Date.parse('2026-01-01T00:30:00Z')).operation_type,
        DISPOSABLE_OPERATION
    );
    for (const altered of [
        receipt({ operation_type: 'persistent_master_write' }),
        receipt({ target: { ...receipt().target, classification: 'persistent' } }),
        receipt({ expires_at: '2025-12-31T23:59:59Z' }),
        receipt({ artifact: { ...artifact, sha256: 'd'.repeat(64) } }),
    ]) {
        assert.throws(
            () => validateRuntimeAuthorization(altered, binding, Date.parse('2026-01-01T00:30:00Z')),
            CanonicalInventoryAuthorizationError
        );
    }
});

test('only explicitly marked disposable synthetic provenance is accepted in this phase', () => {
    assert.equal(
        validateProvenanceReceipt(
            {
                artifact_sha256: artifact.sha256,
                synthetic_test_only: true,
                non_production: true,
                provenance_class: 'synthetic-test-only',
            },
            { sha256: artifact.sha256, target_classification: 'disposable' }
        ).kind,
        'synthetic-test-only'
    );
    assert.throws(
        () => validateProvenanceReceipt(null, { sha256: artifact.sha256, target_classification: 'disposable' }),
        error => error.code === 'BLOCKED_PROVENANCE_POLICY'
    );
    assert.throws(
        () =>
            validateProvenanceReceipt(
                { artifact_sha256: artifact.sha256 },
                { sha256: artifact.sha256, target_classification: 'persistent' }
            ),
        error => error.code === 'BLOCKED_PROVENANCE_POLICY'
    );
});
