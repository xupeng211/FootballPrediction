'use strict';

// lifecycle: permanent；只读本地 raw 文件与来源 manifest 的安全边界。

const crypto = require('node:crypto');
const fs = require('node:fs');
const path = require('node:path');
const {
    ALLOWED_PROVENANCE_STATUSES,
    SOURCE_MANIFEST_SCHEMA_VERSION,
    isStrictAbsoluteTimestamp,
    nullableText,
    stableCanonicalize,
} = require('./contracts');

class OfflineStagingError extends Error {
    constructor(code, message) {
        super(message);
        this.name = 'OfflineStagingError';
        this.code = code;
    }
}

function isNetworkReference(value) {
    return /^[a-z][a-z0-9+.-]*:\/\//i.test(String(value || '').trim());
}

function assertAbsoluteLocalPath(value, fieldName) {
    const rawPath = String(value || '').trim();
    if (!rawPath) {
        throw new OfflineStagingError('INPUT_ERROR', `${fieldName} is required`);
    }
    if (isNetworkReference(rawPath)) {
        throw new OfflineStagingError('SAFETY_ERROR', `${fieldName} must be a local path, not a network URL`);
    }
    if (!path.isAbsolute(rawPath)) {
        throw new OfflineStagingError('SAFETY_ERROR', `${fieldName} must be an absolute local path`);
    }
    return path.resolve(rawPath);
}

function isSha256(value) {
    return /^[a-f0-9]{64}$/i.test(String(value || '').trim());
}

const REQUIRED_MANIFEST_TEXT_FIELDS = Object.freeze([
    'schema_version',
    'source_provider',
    'acquisition_mode',
    'source_url',
    'captured_at',
    'source_timezone',
    'raw_path',
    'raw_media_type',
    'raw_sha256',
    'adapter',
    'adapter_version',
    'provenance_status',
]);

function appendRequiredFieldErrors(manifest, errors) {
    for (const field of REQUIRED_MANIFEST_TEXT_FIELDS) {
        if (!nullableText(manifest[field])) {
            errors.push(`manifest missing required field: ${field}`);
        }
    }
    if (!Object.prototype.hasOwnProperty.call(manifest, 'source_match_id')) {
        errors.push('manifest missing required field: source_match_id');
    }
}

function appendManifestValueErrors(manifest, errors) {
    if (manifest.schema_version !== SOURCE_MANIFEST_SCHEMA_VERSION) {
        errors.push(`unsupported manifest schema_version: ${manifest.schema_version || ''}`);
    }
    if (!isStrictAbsoluteTimestamp(manifest.captured_at)) {
        errors.push('captured_at must be an ISO-8601 timestamp with Z or an explicit numeric offset');
    }
    if (!Number.isSafeInteger(manifest.raw_size_bytes) || manifest.raw_size_bytes < 0) {
        errors.push('raw_size_bytes must be a non-negative safe integer');
    }
    if (!isSha256(manifest.raw_sha256)) {
        errors.push('raw_sha256 must be a 64-character SHA-256 hex string');
    }
    if (!ALLOWED_PROVENANCE_STATUSES.has(manifest.provenance_status)) {
        errors.push(`unsupported provenance_status: ${manifest.provenance_status || ''}`);
    }
}

function appendManifestPathErrors(manifest, errors) {
    try {
        assertAbsoluteLocalPath(manifest.raw_path, 'manifest.raw_path');
    } catch (error) {
        errors.push(error.message);
    }
}

function validateSourceManifest(manifest) {
    if (!manifest || typeof manifest !== 'object' || Array.isArray(manifest)) {
        return { valid: false, errors: ['manifest must be a JSON object'] };
    }

    const errors = [];
    appendRequiredFieldErrors(manifest, errors);
    appendManifestValueErrors(manifest, errors);
    appendManifestPathErrors(manifest, errors);

    return {
        valid: errors.length === 0,
        errors,
    };
}

function readJsonFile(filePath, fileSystem = fs) {
    try {
        return JSON.parse(fileSystem.readFileSync(filePath, 'utf8'));
    } catch (error) {
        throw new OfflineStagingError('INPUT_ERROR', `unable to parse JSON input: ${error.message}`);
    }
}

function sha256Buffer(buffer) {
    return crypto.createHash('sha256').update(buffer).digest('hex');
}

function decodeUtf8(buffer) {
    try {
        return new TextDecoder('utf-8', { fatal: true }).decode(buffer);
    } catch {
        throw new OfflineStagingError('INPUT_ERROR', 'raw file is not valid UTF-8 text');
    }
}

function loadSourceBundle(options = {}, dependencies = {}) {
    const fileSystem = dependencies.fileSystem || fs;
    const manifestPath = assertAbsoluteLocalPath(options.manifestPath, 'manifest path');
    const sourcePath = assertAbsoluteLocalPath(options.sourcePath, 'source path');

    if (!fileSystem.existsSync(manifestPath)) {
        throw new OfflineStagingError('INPUT_ERROR', 'manifest file does not exist');
    }
    if (!fileSystem.existsSync(sourcePath)) {
        throw new OfflineStagingError('INPUT_ERROR', 'source file does not exist');
    }

    const manifest = readJsonFile(manifestPath, fileSystem);
    const validation = validateSourceManifest(manifest);
    if (!validation.valid) {
        throw new OfflineStagingError('INPUT_ERROR', validation.errors.join('; '));
    }

    const declaredRawPath = assertAbsoluteLocalPath(manifest.raw_path, 'manifest.raw_path');
    const actualRawPath = fileSystem.realpathSync(sourcePath);
    const actualDeclaredPath = fileSystem.realpathSync(declaredRawPath);
    if (actualRawPath !== actualDeclaredPath) {
        throw new OfflineStagingError('INPUT_ERROR', 'source path does not match manifest.raw_path');
    }

    const stat = fileSystem.statSync(actualRawPath);
    if (!stat.isFile()) {
        throw new OfflineStagingError('INPUT_ERROR', 'source path must reference a regular file');
    }

    const rawBuffer = fileSystem.readFileSync(actualRawPath);
    const actualSha256 = sha256Buffer(rawBuffer);
    if (rawBuffer.length !== manifest.raw_size_bytes) {
        throw new OfflineStagingError('INPUT_ERROR', 'raw_size_bytes does not match the source file');
    }
    if (actualSha256 !== String(manifest.raw_sha256).toLowerCase()) {
        throw new OfflineStagingError('INPUT_ERROR', 'raw_sha256 does not match the source file');
    }

    return {
        manifest: stableCanonicalize({
            ...manifest,
            raw_path: actualRawPath,
            raw_sha256: actualSha256,
            raw_size_bytes: rawBuffer.length,
            source_match_id: nullableText(manifest.source_match_id),
            source_observed_at: nullableText(manifest.source_observed_at),
        }),
        rawText: decodeUtf8(rawBuffer),
        sourcePath: actualRawPath,
    };
}

function loadCandidates(candidatePath, dependencies = {}) {
    const fileSystem = dependencies.fileSystem || fs;
    const absolutePath = assertAbsoluteLocalPath(candidatePath, 'candidates path');
    if (!fileSystem.existsSync(absolutePath)) {
        throw new OfflineStagingError('INPUT_ERROR', 'candidates file does not exist');
    }

    const payload = readJsonFile(absolutePath, fileSystem);
    const candidates = Array.isArray(payload) ? payload : payload?.candidates;
    if (!Array.isArray(candidates)) {
        throw new OfflineStagingError('INPUT_ERROR', 'candidates JSON must be an array or contain a candidates array');
    }
    return candidates;
}

module.exports = {
    OfflineStagingError,
    assertAbsoluteLocalPath,
    isNetworkReference,
    loadCandidates,
    loadSourceBundle,
    validateSourceManifest,
};
