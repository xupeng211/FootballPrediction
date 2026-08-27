'use strict';
const fs = require('node:fs');
const path = require('node:path');
const { sha256Text, stableStringify, isUtcTimestamp } = require('./contracts');
/* eslint-disable complexity -- receipt validation enumerates independent safety invariants. */

function assertNoSecret(value) {
    if (/api[-_]?key|authorization|secret|token|THE_ODDS_API_KEY/i.test(value)) {
        throw new Error('secret-bearing value is prohibited');
    }
}
function writeImmutableRaw({ rootDir, rawText }) {
    const sha256 = sha256Text(rawText);
    const relativePath = path.join('raw', `${sha256}.json`);
    const target = path.join(rootDir, relativePath);
    fs.mkdirSync(path.dirname(target), { recursive: true });
    if (fs.existsSync(target) && fs.readFileSync(target, 'utf8') !== rawText) {
        throw new Error('immutable raw hash collision');
    }
    if (!fs.existsSync(target)) fs.writeFileSync(target, rawText, { flag: 'wx' });
    return { raw_sha256: sha256, raw_evidence_reference: relativePath };
}
function writeReceipt({ rootDir, receipt }) {
    const serialized = stableStringify(receipt);
    assertNoSecret(serialized);
    if (!/^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$/.test(String(receipt.capture_id || ''))) {
        throw new Error('capture_id must be a safe filename token');
    }
    const target = path.join(rootDir, 'receipts', `${receipt.capture_id}.json`);
    fs.mkdirSync(path.dirname(target), { recursive: true });
    if (fs.existsSync(target)) throw new Error('capture receipt is immutable');
    fs.writeFileSync(target, `${serialized}\n`, { flag: 'wx' });
    return target;
}
function createCaptureReceipt({
    capture_id,
    provider = 'the-odds-api',
    acquisition_mode,
    request_started_at,
    response_received_at,
    http_status,
    sanitized_request_parameters,
    provider_endpoint_identity = 'api.the-odds-api.com/v4/sports/soccer_epl/odds',
    response_size_bytes,
    raw_sha256,
    raw_evidence_reference,
    provider_quota = null,
    software_version = 'stage-c-market-evidence/1.0.0',
}) {
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
    assertNoSecret(stableStringify(receipt));
    if (
        !capture_id ||
        !provider ||
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
        !raw_evidence_reference ||
        typeof sanitized_request_parameters !== 'object' ||
        sanitized_request_parameters === null
    ) {
        throw new Error('capture receipt evidence reference or sanitized parameters is invalid');
    }
    if (Date.parse(response_received_at) < Date.parse(request_started_at)) {
        throw new Error('capture receipt response precedes request');
    }
    if (/\?|#|api[-_]?key|authorization|token|secret/i.test(provider_endpoint_identity)) {
        throw new Error('provider endpoint identity must be secret-free');
    }
    return Object.freeze(receipt);
}
function appendProjection({ ledgerPath, projection }) {
    fs.mkdirSync(path.dirname(ledgerPath), { recursive: true });
    fs.appendFileSync(ledgerPath, `${stableStringify(projection)}\n`);
}
module.exports = { writeImmutableRaw, createCaptureReceipt, writeReceipt, appendProjection };
