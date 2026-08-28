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
    COMPETITION,
} = require('./contracts');
const { normalizeIdentityText } = require('../fixture_universe/identityRules');
/* eslint-disable complexity -- receipt validation enumerates independent safety invariants. */

function assertNoSecret(value) {
    const configuredApiKey = process.env.THE_ODDS_API_KEY;
    if (
        /api[-_]?key|authorization|secret|token|THE_ODDS_API_KEY/i.test(value) ||
        (configuredApiKey && String(value).includes(configuredApiKey))
    ) {
        throw new Error('secret-bearing value is prohibited');
    }
}

const REQUEST_PARAMETER_KEYS = Object.freeze(['regions', 'markets', 'oddsFormat']);
const ALLOWED_REGIONS = new Set(['au', 'eu', 'uk', 'us', 'us2']);
const PROVIDER_ENDPOINT_IDENTITIES = new Set(['api.the-odds-api.com/v4/sports/soccer_epl/odds']);
const QUOTA_HEADER_PATTERN =
    /^(?:x-(?:requests|ratelimit|credits)-(?:remaining|used|limit|reset)|ratelimit-(?:remaining|used|limit|reset))$/i;
const COVERAGE_STATUSES = new Set(['OBSERVED', 'PARTIAL', 'QUARANTINED']);
const LEDGER_MANIFEST_SCHEMA_VERSION = 'footballprediction-market-ledger-integrity/v1';

function isPlainRecord(value) {
    if (!value || typeof value !== 'object' || Array.isArray(value)) return false;
    const prototype = Object.getPrototypeOf(value);
    return prototype === Object.prototype || prototype === null;
}

function sanitizeRequestParameters(value) {
    if (!isPlainRecord(value)) throw new Error('sanitized request parameters must be an object');
    const unknownFields = Object.keys(value).filter(field => !REQUEST_PARAMETER_KEYS.includes(field));
    if (unknownFields.length) throw new Error(`unsupported request parameter: ${unknownFields[0]}`);
    const result = {};
    for (const field of REQUEST_PARAMETER_KEYS) {
        if (value[field] === undefined) continue;
        if (typeof value[field] !== 'string' || !value[field].trim()) {
            throw new Error(`request parameter ${field} must be a non-empty string`);
        }
        const normalized = value[field].trim();
        if (!/^[A-Za-z0-9][A-Za-z0-9,_-]{0,127}$/.test(normalized)) {
            throw new Error(`request parameter ${field} contains unsafe characters`);
        }
        if (field === 'regions') {
            const regions = normalized.split(',');
            if (
                regions.length === 0 ||
                regions.some(region => !ALLOWED_REGIONS.has(region)) ||
                new Set(regions).size !== regions.length
            ) {
                throw new Error('request parameter regions contains an unsupported region');
            }
            result[field] = regions.join(',');
            continue;
        }
        if (field === 'markets' && normalized !== 'h2h') {
            throw new Error('request parameter markets must be h2h');
        }
        if (field === 'oddsFormat' && normalized !== 'decimal') {
            throw new Error('request parameter oddsFormat must be decimal');
        }
        result[field] = normalized;
    }
    return result;
}

function sanitizeProviderQuota(value) {
    if (value === null || value === undefined) return null;
    if (!isPlainRecord(value)) throw new Error('provider quota must be an object or null');
    const result = {};
    for (const [rawKey, rawValue] of Object.entries(value)) {
        const key = String(rawKey).toLowerCase();
        if (!QUOTA_HEADER_PATTERN.test(key)) throw new Error(`unsupported provider quota field: ${rawKey}`);
        if (
            (typeof rawValue !== 'string' && typeof rawValue !== 'number') ||
            (typeof rawValue === 'number' && !Number.isFinite(rawValue))
        ) {
            throw new Error(`provider quota ${rawKey} must be scalar`);
        }
        const normalized = String(rawValue).trim();
        if (!/^-?\d+(?:\.\d+)?$/.test(normalized)) {
            throw new Error(`provider quota ${rawKey} must be numeric`);
        }
        result[key] = normalized;
    }
    return result;
}

function validateCoverageEvidence(value) {
    if (value === null || value === undefined) return null;
    if (!isPlainRecord(value)) throw new Error('coverage_evidence must be an object or null');
    const allowedFields = new Set([
        'schema_version',
        'provider',
        'competition',
        'requested_market_keys',
        'expected_provider_bookmaker_ids',
        'observed_provider_bookmakers',
        'observed_market_keys',
        'missing_expected_provider_bookmaker_ids',
        'missing_expected_provider_market_bookmaker_ids',
        'status',
        'reason',
        'evidence_sha256',
    ]);
    const unknownFields = Object.keys(value).filter(field => !allowedFields.has(field));
    if (unknownFields.length) throw new Error(`unknown coverage evidence field: ${unknownFields[0]}`);
    if (value.schema_version !== 'footballprediction-market-coverage/v1') {
        throw new Error('unsupported coverage evidence schema_version');
    }
    if (value.provider !== 'the-odds-api' || value.competition !== COMPETITION) {
        throw new Error('coverage evidence provider or competition is invalid');
    }
    if (!Array.isArray(value.requested_market_keys) || value.requested_market_keys.some(key => key !== 'h2h')) {
        throw new Error('coverage evidence requested markets are invalid');
    }
    if (
        !Array.isArray(value.expected_provider_bookmaker_ids) ||
        value.expected_provider_bookmaker_ids.some(id => typeof id !== 'string' || !id.trim())
    ) {
        throw new Error('coverage evidence expected bookmaker IDs are invalid');
    }
    if (!Array.isArray(value.observed_provider_bookmakers)) {
        throw new Error('coverage evidence observed bookmakers are invalid');
    }
    if (
        !value.observed_provider_bookmakers.every(
            entry =>
                isPlainRecord(entry) &&
                typeof entry.provider_bookmaker_id === 'string' &&
                Array.isArray(entry.provider_bookmaker_names) &&
                entry.provider_bookmaker_names.every(name => typeof name === 'string') &&
                Array.isArray(entry.market_keys) &&
                entry.market_keys.every(key => typeof key === 'string')
        )
    ) {
        throw new Error('coverage evidence bookmaker entries are invalid');
    }
    if (!Array.isArray(value.observed_market_keys) || value.observed_market_keys.some(key => typeof key !== 'string')) {
        throw new Error('coverage evidence observed markets are invalid');
    }
    if (
        !Array.isArray(value.missing_expected_provider_bookmaker_ids) ||
        value.missing_expected_provider_bookmaker_ids.some(id => typeof id !== 'string' || !id.trim())
    ) {
        throw new Error('coverage evidence missing bookmaker IDs are invalid');
    }
    if (
        !Array.isArray(value.missing_expected_provider_market_bookmaker_ids) ||
        value.missing_expected_provider_market_bookmaker_ids.some(id => typeof id !== 'string' || !id.trim())
    ) {
        throw new Error('coverage evidence missing market bookmaker IDs are invalid');
    }
    if (!COVERAGE_STATUSES.has(value.status)) throw new Error('coverage evidence status is invalid');
    if (value.reason !== null && (typeof value.reason !== 'string' || !value.reason.trim())) {
        throw new Error('coverage evidence reason is invalid');
    }
    if (!/^[a-f0-9]{64}$/.test(value.evidence_sha256 || '')) {
        throw new Error('coverage evidence hash is required');
    }
    const withoutHash = { ...value };
    delete withoutHash.evidence_sha256;
    if (sha256Text(stableStringify(withoutHash)) !== value.evidence_sha256) {
        throw new Error('coverage evidence hash does not match content');
    }
    return Object.freeze(JSON.parse(JSON.stringify(value)));
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
    if (!fs.existsSync(target)) fs.writeFileSync(target, rawText, { flag: 'wx', mode: 0o444 });
    fs.chmodSync(target, 0o444);
    return { raw_sha256: sha256, raw_evidence_reference: relativePath };
}

function readImmutableRaw({ rootDir, rawEvidenceReference, rawPath, expectedSha256 }) {
    if (!rawPath && (typeof rootDir !== 'string' || !rootDir.trim())) {
        throw new Error('evidence root is required when rawPath is not provided');
    }
    if (!rawPath && !isSafeEvidenceReference(rawEvidenceReference)) throw new Error('raw evidence reference is unsafe');
    if (!/^[a-f0-9]{64}$/.test(expectedSha256 || '')) throw new Error('raw SHA-256 is required');
    const target = rawPath ? path.resolve(rawPath) : path.resolve(rootDir, rawEvidenceReference);
    if (!rawPath) {
        const root = path.resolve(rootDir);
        if (target !== root && !target.startsWith(`${root}${path.sep}`)) {
            throw new Error('raw path escapes evidence root');
        }
    }
    const stat = fs.lstatSync(target);
    if (stat.isSymbolicLink() || !stat.isFile()) throw new Error('raw input must be a regular file');
    if ((stat.mode & 0o222) !== 0) throw new Error('raw input must be read-only');
    const rawText = fs.readFileSync(target, 'utf8');
    const actualSha256 = sha256Text(rawText);
    if (actualSha256 !== expectedSha256) throw new Error('raw SHA-256 does not match immutable content');
    return rawText;
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
    fs.writeFileSync(target, `${serialized}\n`, { flag: 'wx', mode: 0o444 });
    fs.chmodSync(target, 0o444);
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
        coverage_evidence = null,
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
        'coverage_evidence',
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
        sanitized_request_parameters: sanitizeRequestParameters(sanitized_request_parameters),
        provider_endpoint_identity,
        response_size_bytes,
        raw_sha256,
        raw_evidence_reference,
        provider_quota: sanitizeProviderQuota(provider_quota),
        coverage_evidence: validateCoverageEvidence(coverage_evidence),
        software_version,
    };
    receipt.ingested_at = ingested_at;
    assertNoSecret(stableStringify(receipt));
    if (
        !/^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$/.test(String(capture_id || '')) ||
        typeof provider !== 'string' ||
        provider !== 'the-odds-api' ||
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
    if (!isSafeEvidenceReference(raw_evidence_reference) || !isPlainRecord(receipt.sanitized_request_parameters)) {
        throw new Error('capture receipt evidence reference or sanitized parameters is invalid');
    }
    if (
        typeof provider_endpoint_identity !== 'string' ||
        !PROVIDER_ENDPOINT_IDENTITIES.has(provider_endpoint_identity) ||
        typeof software_version !== 'string' ||
        !/^[A-Za-z0-9][A-Za-z0-9._/-]{0,127}$/.test(software_version) ||
        (receipt.provider_quota !== null && !isPlainRecord(receipt.provider_quota))
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
    return Object.freeze(receipt);
}

function writeCoverageEvidence({ rootDir, captureId, evidence }) {
    if (!/^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$/.test(String(captureId || ''))) {
        throw new Error('capture_id must be a safe filename token');
    }
    const validated = validateCoverageEvidence(evidence);
    ensureDirectory(rootDir, 'evidence root');
    const coverageDir = path.join(rootDir, 'coverage');
    ensureDirectory(coverageDir, 'coverage directory');
    const target = path.join(coverageDir, `${captureId}.json`);
    if (fs.existsSync(target)) throw new Error('coverage evidence is immutable');
    fs.writeFileSync(target, `${stableStringify(validated)}\n`, { flag: 'wx', mode: 0o444 });
    fs.chmodSync(target, 0o444);
    return target;
}

function assertRegularFile(target, label) {
    const stat = fs.lstatSync(target);
    if (stat.isSymbolicLink() || !stat.isFile()) throw new Error(`${label} must be a regular file`);
    return stat;
}

function ledgerManifestPath(ledgerPath) {
    return `${ledgerPath}.manifest.json`;
}

function parseLedgerRows(content) {
    const lines = content.split('\n');
    if (lines.at(-1) === '') lines.pop();
    if (lines.some(line => !line.trim())) throw new Error('ledger integrity check failed: blank line');
    return lines.map(line => {
        let parsed;
        try {
            parsed = JSON.parse(line);
        } catch (error) {
            throw new Error(`ledger integrity check failed: invalid JSON: ${error.message}`, { cause: error });
        }
        return createObservation(parsed);
    });
}

function readLedgerManifest(ledgerPath) {
    const manifestPath = ledgerManifestPath(ledgerPath);
    if (!fs.existsSync(manifestPath)) throw new Error('ledger integrity manifest is missing');
    const manifestStat = assertRegularFile(manifestPath, 'ledger integrity manifest');
    if ((manifestStat.mode & 0o222) !== 0) throw new Error('ledger integrity manifest must be read-only');
    let manifest;
    try {
        manifest = JSON.parse(fs.readFileSync(manifestPath, 'utf8'));
    } catch (error) {
        throw new Error(`ledger integrity manifest is invalid: ${error.message}`, { cause: error });
    }
    if (
        !isPlainRecord(manifest) ||
        manifest.schema_version !== LEDGER_MANIFEST_SCHEMA_VERSION ||
        !/^[a-f0-9]{64}$/.test(manifest.ledger_sha256 || '') ||
        !Number.isInteger(manifest.line_count) ||
        manifest.line_count < 0
    ) {
        throw new Error('ledger integrity manifest is invalid');
    }
    return manifest;
}

function verifyLedgerIntegrity(ledgerPath) {
    if (!fs.existsSync(ledgerPath)) return { content: '', rows: [], manifest: null };
    const stat = assertRegularFile(ledgerPath, 'ledger');
    if ((stat.mode & 0o222) !== 0) throw new Error('ledger must be read-only');
    const content = fs.readFileSync(ledgerPath, 'utf8');
    const rows = parseLedgerRows(content);
    const manifest = readLedgerManifest(ledgerPath);
    if (manifest.line_count !== rows.length || manifest.ledger_sha256 !== sha256Text(content)) {
        throw new Error('ledger integrity check failed');
    }
    return { content, rows, manifest };
}

function writeLedgerManifest(ledgerPath, content, lineCount) {
    const manifestPath = ledgerManifestPath(ledgerPath);
    const serialized = `${stableStringify({
        schema_version: LEDGER_MANIFEST_SCHEMA_VERSION,
        ledger_sha256: sha256Text(content),
        line_count: lineCount,
    })}\n`;
    if (fs.existsSync(manifestPath)) {
        const existing = assertRegularFile(manifestPath, 'ledger integrity manifest');
        fs.chmodSync(manifestPath, existing.mode | 0o200);
    }
    try {
        fs.writeFileSync(manifestPath, serialized, { flag: 'w', mode: 0o444 });
    } finally {
        if (fs.existsSync(manifestPath)) fs.chmodSync(manifestPath, 0o444);
    }
}

function appendProjection({ ledgerPath, projection, registry }) {
    const validated = createObservation(projection);
    if (!registry || typeof registry.resolve !== 'function') throw new Error('identity registry is required for canonical ledger append');
    const event = registry.resolve('event', validated.provider, validated.provider_event_id);
    const bookmaker = registry.resolve('bookmaker', validated.provider, validated.provider_bookmaker_id);
    const market = registry.resolve('market', validated.provider, validated.provider_market_id);
    const selection = validated.selection === 'DRAW' ? registry.resolve('selection', validated.provider, 'Draw') : null;
    const eventMatches = event.canonical_id === validated.canonical_event_id && event.identity_decision_id === validated.identity_decision_id && event.identity_ruleset_version === validated.identity_ruleset_version && event.identity_decision_status === 'MATCHED' && event.season === validated.season && normalizeIdentityText(event.home_team) === normalizeIdentityText(validated.home_team) && normalizeIdentityText(event.away_team) === normalizeIdentityText(validated.away_team) && compareUtcTimestamps(event.provider_observed_kickoff_utc, validated.kickoff_utc) === 0;
    const marketMatches = bookmaker.canonical_id === validated.canonical_bookmaker_id && bookmaker.price_side === validated.price_side && market.canonical_id === validated.canonical_market_id && market.period === validated.period && market.market_type === validated.market_type && market.line === validated.line;
    const selectionMatches = validated.selection === 'HOME' || validated.selection === 'AWAY' ? validated.canonical_selection_id === validated.selection : selection.canonical_id === validated.canonical_selection_id && selection.selection === validated.selection;
    if (!eventMatches || !marketMatches || !selectionMatches || registry.version !== validated.identity_registry_version || registry.content_sha256 !== validated.identity_registry_sha256) throw new Error('canonical observation identity decision is not a valid MATCHED registry decision');
    if (typeof ledgerPath !== 'string' || !ledgerPath.trim()) throw new Error('ledger path is required');
    const parentDir = path.dirname(ledgerPath);
    ensureDirectory(parentDir, 'ledger parent directory');
    if (!fs.existsSync(ledgerPath) && fs.existsSync(ledgerManifestPath(ledgerPath))) {
        throw new Error('ledger integrity manifest exists without ledger');
    }
    const existing = fs.existsSync(ledgerPath) ? verifyLedgerIntegrity(ledgerPath) : { content: '', rows: [] };
    const line = `${stableStringify(validated)}\n`;
    if (fs.existsSync(ledgerPath)) {
        const stat = assertRegularFile(ledgerPath, 'ledger');
        fs.chmodSync(ledgerPath, stat.mode | 0o200);
    }
    try {
        fs.appendFileSync(ledgerPath, line, { mode: 0o444 });
        const content = `${existing.content}${line}`;
        writeLedgerManifest(ledgerPath, content, existing.rows.length + 1);
    } finally {
        if (fs.existsSync(ledgerPath)) {
            fs.chmodSync(ledgerPath, 0o444);
        }
    }
    return validated;
}

function readProjectionLedger({ ledgerPath }) {
    if (typeof ledgerPath !== 'string' || !ledgerPath.trim()) throw new Error('ledger path is required');
    return verifyLedgerIntegrity(ledgerPath).rows;
}
module.exports = {
    writeImmutableRaw,
    readImmutableRaw,
    createCaptureReceipt,
    writeReceipt,
    writeCoverageEvidence,
    appendProjection,
    readProjectionLedger,
    ledgerManifestPath,
    sanitizeRequestParameters,
    sanitizeProviderQuota,
    validateCoverageEvidence,
    ALLOWED_REGIONS,
    PROVIDER_ENDPOINT_IDENTITIES,
};
