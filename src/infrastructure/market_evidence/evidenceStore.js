'use strict';
const fs = require('node:fs');
const path = require('node:path');
const {
    sha256Text,
    stableStringify,
    isUtcTimestamp,
    isSafeEvidenceReference,
    compareUtcTimestamps,
    createObservation,
} = require('./contracts');
/* eslint-disable complexity -- receipt validation enumerates independent safety invariants. */

function assertNoSecret(value) {
    if (/api[-_]?key|authorization|secret|token|THE_ODDS_API_KEY/i.test(value)) {
        throw new Error('secret-bearing value is prohibited');
    }
}

function ensureDirectory(target, label) {
    if (fs.existsSync(target)) {
        const stat = fs.lstatSync(target);
        if (stat.isSymbolicLink() || !stat.isDirectory()) throw new Error(`${label} must be a regular directory`);
        return;
    }
    fs.mkdirSync(target, { recursive: true });
}
function writeImmutableRaw({ rootDir, rawText }) {
    if (typeof rawText !== 'string') throw new Error('immutable raw payload must be text');
    ensureDirectory(rootDir, 'evidence root');
    const sha256 = sha256Text(rawText);
    const relativePath = path.join('raw', `${sha256}.json`);
    ensureDirectory(path.join(rootDir, 'raw'), 'raw directory');
    const target = path.join(rootDir, relativePath);
    if (fs.existsSync(target)) {
        const stat = fs.lstatSync(target);
        if (!stat.isFile() || stat.isSymbolicLink()) throw new Error('immutable raw target must be a regular file');
        if (fs.readFileSync(target, 'utf8') !== rawText) throw new Error('immutable raw hash collision');
    }
    if (!fs.existsSync(target)) fs.writeFileSync(target, rawText, { flag: 'wx' });
    return { raw_sha256: sha256, raw_evidence_reference: relativePath };
}
function writeReceipt({ rootDir, receipt }) {
    assertNoSecret(stableStringify(receipt));
    const validated = createCaptureReceipt(receipt);
    ensureDirectory(rootDir, 'evidence root');
    const serialized = stableStringify(validated);
    assertNoSecret(serialized);
    if (!/^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$/.test(String(validated.capture_id || ''))) {
        throw new Error('capture_id must be a safe filename token');
    }
    const target = path.join(rootDir, 'receipts', `${validated.capture_id}.json`);
    ensureDirectory(path.join(rootDir, 'receipts'), 'receipt directory');
    if (fs.existsSync(target)) throw new Error('capture receipt is immutable');
    fs.writeFileSync(target, `${serialized}\n`, { flag: 'wx' });
    return target;
}
function createCaptureReceipt(options = {}) {
    const {
        capture_id,
        provider = 'the-odds-api',
        acquisition_mode,
        request_started_at,
        response_received_at,
        ingested_at,
        http_status,
        sanitized_request_parameters,
        provider_endpoint_identity = 'api.the-odds-api.com/v4/sports/soccer_epl/odds',
        response_size_bytes,
        raw_sha256,
        raw_evidence_reference,
        provider_quota = null,
        software_version = 'stage-c-market-evidence/1.0.0',
    } = options;
    assertNoSecret(stableStringify(options));
    const allowedFields = new Set([
        'capture_id',
        'provider',
        'acquisition_mode',
        'request_started_at',
        'response_received_at',
        'ingested_at',
        'http_status',
        'sanitized_request_parameters',
        'provider_endpoint_identity',
        'response_size_bytes',
        'raw_sha256',
        'raw_evidence_reference',
        'provider_quota',
        'software_version',
    ]);
    const unknownFields = Object.keys(options).filter(field => !allowedFields.has(field));
    if (unknownFields.length) throw new Error(`unknown capture receipt field: ${unknownFields[0]}`);
    const receipt = {
        capture_id,
        provider,
        acquisition_mode,
        request_started_at,
        response_received_at,
        http_status,
        sanitized_request_parameters,
        provider_endpoint_identity,
        response_size_bytes,
        raw_sha256,
        raw_evidence_reference,
        provider_quota,
        software_version,
    };
    receipt.ingested_at = ingested_at;
    assertNoSecret(stableStringify(receipt));
    if (
        !/^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$/.test(String(capture_id || '')) ||
        typeof provider !== 'string' ||
        !provider.trim() ||
        !['LIVE_CAPTURE', 'HISTORICAL_API', 'HISTORICAL_FILE', 'REPLAY'].includes(acquisition_mode)
    ) {
        throw new Error('invalid capture receipt identity or acquisition_mode');
    }
    if (!isUtcTimestamp(request_started_at) || !isUtcTimestamp(response_received_at)) {
        throw new Error('capture receipt times must be UTC ISO-8601');
    }
    if (!Number.isInteger(http_status) || http_status < 100 || http_status > 599) {
        throw new Error('capture receipt HTTP status is invalid');
    }
    if (!Number.isInteger(response_size_bytes) || response_size_bytes < 0 || !/^[a-f0-9]{64}$/.test(raw_sha256 || '')) {
        throw new Error('capture receipt payload metadata is invalid');
    }
    if (
        !isSafeEvidenceReference(raw_evidence_reference) ||
        typeof sanitized_request_parameters !== 'object' ||
        sanitized_request_parameters === null ||
        Array.isArray(sanitized_request_parameters)
    ) {
        throw new Error('capture receipt evidence reference or sanitized parameters is invalid');
    }
    if (
        typeof provider_endpoint_identity !== 'string' ||
        !provider_endpoint_identity.trim() ||
        typeof software_version !== 'string' ||
        !software_version.trim() ||
        (provider_quota !== null && (typeof provider_quota !== 'object' || Array.isArray(provider_quota)))
    ) {
        throw new Error('capture receipt endpoint or quota metadata is invalid');
    }
    if (compareUtcTimestamps(response_received_at, request_started_at) < 0) {
        throw new Error('capture receipt response precedes request');
    }
    if (!isUtcTimestamp(ingested_at)) {
        throw new Error('capture receipt ingestion time must be UTC ISO-8601');
    }
    if (compareUtcTimestamps(ingested_at, response_received_at) < 0) {
        throw new Error('capture receipt ingestion precedes response');
    }
    if (/\?|#|api[-_]?key|authorization|token|secret/i.test(provider_endpoint_identity)) {
        throw new Error('provider endpoint identity must be secret-free');
    }
    return Object.freeze(receipt);
}
function appendProjection({ ledgerPath, projection }) {
    const validated = createObservation(projection);
    const parentDir = path.dirname(ledgerPath);
    ensureDirectory(parentDir, 'ledger parent directory');
    if (fs.existsSync(ledgerPath)) {
        const stat = fs.lstatSync(ledgerPath);
        if (stat.isSymbolicLink() || !stat.isFile()) throw new Error('ledger must be a regular file');
    }
    fs.appendFileSync(ledgerPath, `${stableStringify(validated)}\n`);
}
module.exports = { writeImmutableRaw, createCaptureReceipt, writeReceipt, appendProjection };
