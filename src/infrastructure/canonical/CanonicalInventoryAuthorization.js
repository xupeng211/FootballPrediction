'use strict';

// lifecycle: permanent
// M3 的数据库外授权与来源证明合同；receipt 永不写入候选 artifact，且本版本
// 只允许显式标记的 disposable synthetic proof。

const crypto = require('node:crypto');
const { SEASONS, sha256Text, stableStringify } = require('./CanonicalInventoryContract');

const DISPOSABLE_OPERATION = 'canonical_inventory_disposable_proof';
const DISPOSABLE_AUTHORITY_ISSUER = 'm3-canonical-disposable-proof-authority';
const DISPOSABLE_AUTHORITY_KEY_ID = 'm3-canonical-disposable-proof-v1';

class CanonicalInventoryAuthorizationError extends Error {
    constructor(message, code = 'CANONICAL_AUTHORIZATION_FAILURE') {
        super(message);
        this.name = 'CanonicalInventoryAuthorizationError';
        this.code = code;
    }
}

function assertReceiptText(value, field) {
    if (typeof value !== 'string' || value.trim() === '') {
        throw new CanonicalInventoryAuthorizationError(`receipt requires ${field}`);
    }
    return value;
}

function assertDate(value, field) {
    if (!value || !Number.isFinite(Date.parse(value))) {
        throw new CanonicalInventoryAuthorizationError(`receipt requires valid ${field}`);
    }
    return new Date(value).getTime();
}

function sameSeasons(value) {
    return (
        Array.isArray(value) &&
        value.length === SEASONS.length &&
        value.every((season, index) => season === SEASONS[index])
    );
}

function authorizationPayload(receipt) {
    const { signature, ...unsigned } = receipt || {};
    return stableStringify(unsigned);
}

function authorizationReceiptSha256(receipt) {
    return sha256Text(stableStringify(receipt));
}

function assertTrustedAuthority(authority) {
    if (!authority || typeof authority !== 'object') {
        throw new CanonicalInventoryAuthorizationError('trusted authorization authority is required');
    }
    if (
        authority.issuer !== DISPOSABLE_AUTHORITY_ISSUER ||
        authority.key_id !== DISPOSABLE_AUTHORITY_KEY_ID ||
        typeof authority.public_key !== 'string' ||
        authority.public_key.trim() === ''
    ) {
        throw new CanonicalInventoryAuthorizationError('trusted authorization authority is not accepted');
    }
    return authority;
}

function assertReceiptSignature(receipt, authority) {
    const signature = receipt.signature;
    if (
        !signature ||
        signature.algorithm !== 'ed25519' ||
        signature.issuer !== authority.issuer ||
        signature.key_id !== authority.key_id ||
        typeof signature.value !== 'string' ||
        signature.value.trim() === ''
    ) {
        throw new CanonicalInventoryAuthorizationError('runtime authorization signature is required');
    }
    let verified = false;
    try {
        verified = crypto.verify(
            null,
            Buffer.from(authorizationPayload(receipt)),
            authority.public_key,
            Buffer.from(signature.value, 'base64')
        );
    } catch {
        throw new CanonicalInventoryAuthorizationError('runtime authorization signature is invalid');
    }
    if (!verified) throw new CanonicalInventoryAuthorizationError('runtime authorization signature is invalid');
}

// The receipt is intentionally a single fail-closed boundary; splitting its
// field checks would obscure the authorization binding it protects.
// eslint-disable-next-line complexity
function validateRuntimeAuthorization(receipt, binding, authority, now = Date.now()) {
    if (!receipt || typeof receipt !== 'object' || Array.isArray(receipt)) {
        throw new CanonicalInventoryAuthorizationError('external runtime authorization receipt is required');
    }
    const trustedAuthority = assertTrustedAuthority(authority);
    assertReceiptSignature(receipt, trustedAuthority);
    assertReceiptText(receipt.execution_id, 'execution_id');
    if (receipt.operation_type !== DISPOSABLE_OPERATION) {
        throw new CanonicalInventoryAuthorizationError('operation type is not authorized');
    }
    if (receipt.target?.classification !== 'disposable') {
        throw new CanonicalInventoryAuthorizationError('persistent targets are not authorized');
    }
    if (binding.target_classification !== 'disposable') {
        throw new CanonicalInventoryAuthorizationError('writer target is not independently classified as disposable');
    }
    for (const field of ['service_identity', 'database_identity', 'schema_baseline']) {
        assertReceiptText(receipt.target?.[field], `target.${field}`);
    }
    const issuedAt = assertDate(receipt.issued_at, 'issued_at');
    const expiresAt = assertDate(receipt.expires_at, 'expires_at');
    if (issuedAt > now || expiresAt <= now) {
        throw new CanonicalInventoryAuthorizationError('runtime authorization is expired or not yet valid');
    }
    if (
        receipt.target.database_identity !== binding.database_identity ||
        receipt.target.service_identity !== binding.service_identity
    ) {
        throw new CanonicalInventoryAuthorizationError('runtime authorization target identity mismatch');
    }
    if (receipt.target.schema_baseline !== binding.schema_baseline) {
        throw new CanonicalInventoryAuthorizationError('runtime authorization schema baseline mismatch');
    }
    const expected = receipt.artifact;
    if (!expected || typeof expected !== 'object') {
        throw new CanonicalInventoryAuthorizationError('receipt artifact binding is required');
    }
    for (const field of ['sha256', 'business_hash', 'identity_projection_hash', 'kind']) {
        if (expected[field] !== binding.artifact[field]) {
            throw new CanonicalInventoryAuthorizationError(`runtime authorization artifact ${field} mismatch`);
        }
    }
    if (
        expected.candidate_count !== binding.artifact.candidate_count ||
        expected.competition !== binding.artifact.competition ||
        !sameSeasons(expected.seasons)
    ) {
        throw new CanonicalInventoryAuthorizationError('runtime authorization artifact scope mismatch');
    }
    return {
        execution_id: receipt.execution_id,
        operation_type: receipt.operation_type,
        expires_at: receipt.expires_at,
        receipt_sha256: authorizationReceiptSha256(receipt),
    };
}

function validateProvenanceReceipt(receipt, binding) {
    if (!receipt || typeof receipt !== 'object' || Array.isArray(receipt)) {
        throw new CanonicalInventoryAuthorizationError('missing provenance receipt', 'BLOCKED_PROVENANCE_POLICY');
    }
    if (receipt.artifact_sha256 !== binding.sha256) {
        throw new CanonicalInventoryAuthorizationError(
            'provenance artifact hash mismatch',
            'BLOCKED_PROVENANCE_POLICY'
        );
    }
    if (receipt.synthetic_test_only === true && binding.target_classification === 'disposable') {
        if (receipt.provenance_class !== 'synthetic-test-only' || receipt.non_production !== true) {
            throw new CanonicalInventoryAuthorizationError(
                'synthetic provenance receipt is incomplete',
                'BLOCKED_PROVENANCE_POLICY'
            );
        }
        return { kind: 'synthetic-test-only' };
    }
    for (const field of [
        'provider_endpoint_identity',
        'capture_timestamp',
        'capture_process_identity',
        'license_terms_evidence',
    ]) {
        try {
            assertReceiptText(receipt[field], field);
        } catch {
            throw new CanonicalInventoryAuthorizationError(
                `real provenance receipt requires ${field}`,
                'BLOCKED_PROVENANCE_POLICY'
            );
        }
    }
    throw new CanonicalInventoryAuthorizationError(
        'real canonical writes require separately authorized provenance review',
        'BLOCKED_PROVENANCE_POLICY'
    );
}

module.exports = {
    CanonicalInventoryAuthorizationError,
    DISPOSABLE_AUTHORITY_ISSUER,
    DISPOSABLE_AUTHORITY_KEY_ID,
    DISPOSABLE_OPERATION,
    authorizationPayload,
    authorizationReceiptSha256,
    validateProvenanceReceipt,
    validateRuntimeAuthorization,
};
