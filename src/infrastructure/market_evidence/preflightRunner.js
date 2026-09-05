'use strict';

// A bounded, opt-in preflight runner.  It deliberately has no default
// transport: callers must prepare durable evidence storage before injecting
// the one authorised transport invocation.
const fs = require('node:fs');
const path = require('node:path');
const crypto = require('node:crypto');
const {
    createCaptureReceipt,
    loadVerifiedCaptureReceipt,
    readImmutableRaw,
    sanitizeRequestParameters,
} = require('./evidenceStore');
const { stableStringify } = require('./contracts');

const preparedRoots = new WeakSet();
const consumedPreparations = new WeakSet();
const MAX_PROVIDER_REQUESTS = 1;

function sha256(value) {
    return crypto.createHash('sha256').update(value, 'utf8').digest('hex');
}
function regularDirectory(target, label) {
    if (fs.existsSync(target)) {
        const stat = fs.lstatSync(target);
        if (stat.isSymbolicLink() || !stat.isDirectory()) throw new Error(`${label} must be a regular directory`);
        return;
    }
    fs.mkdirSync(target, { recursive: true, mode: 0o700 });
}
function fsyncDirectory(target) {
    const fd = fs.openSync(target, 'r');
    try {
        fs.fsyncSync(fd);
    } finally {
        fs.closeSync(fd);
    }
}
function atomicWrite(target, bytes, mode = 0o600) {
    const directory = path.dirname(target);
    regularDirectory(directory, 'evidence parent');
    const temporary = path.join(directory, `.${path.basename(target)}.${crypto.randomUUID()}.partial`);
    let fd;
    try {
        fd = fs.openSync(temporary, fs.constants.O_WRONLY | fs.constants.O_CREAT | fs.constants.O_EXCL, mode);
        fs.writeFileSync(fd, bytes, 'utf8');
        fs.fsyncSync(fd);
    } finally {
        if (fd !== undefined) fs.closeSync(fd);
    }
    fs.renameSync(temporary, target);
    fs.chmodSync(target, mode);
    fsyncDirectory(directory);
}
function writeProbe(root) {
    const probe = path.join(root, `.write-probe-${crypto.randomUUID()}`);
    atomicWrite(probe, 'probe\n');
    fs.unlinkSync(probe);
    fsyncDirectory(root);
}
function sanitizeHeaders(headers = {}) {
    const result = {};
    for (const [key, value] of Object.entries(headers)) {
        if (
            /^(?:x-(?:requests|ratelimit|credits)-(?:remaining|used|limit|reset)|ratelimit-(?:remaining|used|limit|reset))$/i.test(
                key
            )
        ) {
            result[String(key).toLowerCase()] = String(value);
        }
    }
    return result;
}
function assertPrepared(prepared) {
    if (!preparedRoots.has(prepared)) throw new Error('prepared preflight context is required');
}
function recordFailure(prepared, captureId, stage, error) {
    try {
        atomicWrite(
            path.join(prepared.root, 'attempts', `${captureId}.failure.json`),
            `${JSON.stringify({ capture_id: captureId, state: 'FAILED', stage, message: String(error.message || error).replace(/https?:\/\/\S+/g, '[redacted-url]') }, null, 2)}\n`
        );
    } catch {
        /* original error remains authoritative */
    }
}

function preparePreflight({ rootDir, requestMetadata, credentialPresent, downstreamAvailable = true }) {
    if (credentialPresent !== true) {
        throw new Error('The Odds API credential presence must be verified before transport');
    }
    if (downstreamAvailable !== true) throw new Error('canonical downstream runner must be available before transport');
    if (typeof rootDir !== 'string' || !rootDir.trim()) throw new Error('evidence root is required');
    const root = path.resolve(rootDir);
    regularDirectory(root, 'evidence root');
    for (const name of ['raw', 'receipts', 'headers', 'metadata', 'attempts', 'manifest-workspace']) {
        regularDirectory(path.join(root, name), `${name} directory`);
        writeProbe(path.join(root, name));
    }
    writeProbe(root);
    const sanitizedRequestMetadata = sanitizeRequestParameters(requestMetadata);
    const metadataPath = path.join(root, 'metadata', 'request.json');
    atomicWrite(
        metadataPath,
        `${JSON.stringify({ ...sanitizedRequestMetadata, credential_present: 'YES', max_provider_requests: MAX_PROVIDER_REQUESTS }, null, 2)}\n`
    );
    const prepared = Object.freeze({
        root,
        metadataPath,
        requestMetadata: Object.freeze({ ...sanitizedRequestMetadata }),
        max_provider_requests: MAX_PROVIDER_REQUESTS,
    });
    preparedRoots.add(prepared);
    return prepared;
}

function persistResponse({ prepared, captureId, response }) {
    assertPrepared(prepared);
    if (!response || !Number.isInteger(response.status) || typeof response.body !== 'string') {
        throw new Error('transport response is invalid');
    }
    const body = response.body;
    const rawSha = sha256(body);
    const rawRelative = path.join('raw', `${rawSha}.json`);
    const rawPath = path.join(prepared.root, rawRelative);
    const headerPath = path.join(prepared.root, 'headers', `${captureId}.json`);
    const attemptPath = path.join(prepared.root, 'attempts', `${captureId}.json`);
    // Headers and body are committed before JSON parsing or receipt construction.
    atomicWrite(
        headerPath,
        `${JSON.stringify({ http_status: response.status, response_headers: sanitizeHeaders(response.headers), response_received_at: response.receivedAt }, null, 2)}\n`
    );
    if (fs.existsSync(rawPath)) {
        const stat = fs.lstatSync(rawPath);
        if (
            stat.isSymbolicLink() ||
            !stat.isFile() ||
            (stat.mode & 0o222) !== 0 ||
            fs.readFileSync(rawPath, 'utf8') !== body
        ) {
            throw new Error('existing immutable RAW target is invalid');
        }
    } else atomicWrite(rawPath, body, 0o444);
    fs.chmodSync(rawPath, 0o444);
    atomicWrite(
        attemptPath,
        `${JSON.stringify({ capture_id: captureId, http_status: response.status, raw_evidence_reference: rawRelative, raw_sha256: rawSha, response_size_bytes: Buffer.byteLength(body, 'utf8'), state: 'RESPONSE_DURABLY_PERSISTED' }, null, 2)}\n`
    );
    return { rawSha, rawRelative, rawPath, headerPath, attemptPath };
}

async function executePreparedPreflight({
    prepared,
    transport,
    captureId = `preflight-${crypto.randomUUID()}`,
    now = () => new Date().toISOString(),
    downstream = null,
}) {
    assertPrepared(prepared);
    if (consumedPreparations.has(prepared)) throw new Error('provider request guard blocked a reused preparation');
    if (typeof transport !== 'function') throw new Error('an explicit transport is required');
    if (typeof captureId !== 'string' || !/^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$/.test(captureId)) {
        throw new Error('capture_id is invalid');
    }
    let calls = 0;
    consumedPreparations.add(prepared);
    const startedAt = now();
    let response;
    try {
        if (calls >= MAX_PROVIDER_REQUESTS) throw new Error('provider request guard blocked a second request');
        calls += 1;
        response = await transport(
            Object.freeze({ requestMetadata: prepared.requestMetadata, maxProviderRequests: MAX_PROVIDER_REQUESTS })
        );
    } catch (error) {
        recordFailure(prepared, captureId, 'TRANSPORT', error);
        throw error;
    }
    let persisted;
    try {
        persisted = persistResponse({ prepared, captureId, response });
    } catch (error) {
        recordFailure(prepared, captureId, 'RESPONSE_PERSISTENCE', error);
        throw error;
    }
    if (response.status !== 200) {
        throw Object.assign(new Error(`The Odds API returned HTTP ${response.status}`), {
            transport_calls: calls,
            persisted,
        });
    }
    const receivedAt = response.receivedAt || now();
    let receipt;
    try {
        receipt = createCaptureReceipt({
            capture_id: captureId,
            acquisition_mode: 'LIVE_CAPTURE',
            request_started_at: startedAt,
            response_received_at: receivedAt,
            ingested_at: now(),
            http_status: response.status,
            sanitized_request_parameters: prepared.requestMetadata,
            response_size_bytes: Buffer.byteLength(response.body, 'utf8'),
            raw_sha256: persisted.rawSha,
            raw_evidence_reference: persisted.rawRelative,
            provider_quota: sanitizeHeaders(response.headers),
        });
    } catch (error) {
        recordFailure(prepared, captureId, 'RECEIPT_CONSTRUCTION', error);
        throw error;
    }
    const receiptPath = path.join(prepared.root, 'receipts', `${captureId}.json`);
    try {
        atomicWrite(receiptPath, `${stableStringify(receipt)}\n`, 0o444);
    } catch (error) {
        recordFailure(prepared, captureId, 'RECEIPT_PERSISTENCE', error);
        throw error;
    }
    const verified = loadVerifiedCaptureReceipt({ receiptPath });
    readImmutableRaw({ rawPath: persisted.rawPath, expectedSha256: verified.receipt.raw_sha256 });
    const downstreamResult = downstream
        ? await downstream(
              Object.freeze({
                  rootDir: prepared.root,
                  rawPath: persisted.rawPath,
                  receiptPath,
                  receipt: verified.receipt,
              })
          )
        : null;
    return Object.freeze({
        transport_calls: calls,
        persisted,
        receiptPath,
        receipt: verified.receipt,
        downstreamResult,
    });
}

module.exports = {
    MAX_PROVIDER_REQUESTS,
    preparePreflight,
    executePreparedPreflight,
    persistResponse,
    sanitizeHeaders,
};
