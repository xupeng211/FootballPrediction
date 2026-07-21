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
const { validateKickoffTimeInterpretation } = require('./footballDataIdentity');

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

// 唯一允许 captured_at 未知的采集模式：从 Git 历史恢复的 raw 没有可信原始下载时间，
// 必须显式声明 unknown 语义与恢复证据，而不是用 commit 时间/恢复时间/开球时间冒充。
const HISTORICAL_GIT_RECOVERY_ACQUISITION_MODE = 'historical_git_recovery';
const GIT_OBJECT_SHA_PATTERN = /^[a-f0-9]{40}$/i;
const REQUIRED_REPOSITORY_PROVENANCE_TEXT_FIELDS = Object.freeze(['repository', 'path']);
const REQUIRED_REPOSITORY_PROVENANCE_SHA_FIELDS = Object.freeze(['commit_sha', 'blob_sha']);

function isHistoricalGitRecoveryManifest(manifest) {
    return Boolean(manifest) && manifest.acquisition_mode === HISTORICAL_GIT_RECOVERY_ACQUISITION_MODE;
}

function appendRequiredFieldErrors(manifest, errors) {
    for (const field of REQUIRED_MANIFEST_TEXT_FIELDS) {
        if (field === 'captured_at' && isHistoricalGitRecoveryManifest(manifest)) {
            continue;
        }
        if (!nullableText(manifest[field])) {
            errors.push(`manifest missing required field: ${field}`);
        }
    }
    if (!Object.prototype.hasOwnProperty.call(manifest, 'source_match_id')) {
        errors.push('manifest missing required field: source_match_id');
    }
}

function appendRepositoryProvenanceErrors(manifest, errors) {
    const provenance = manifest.repository_provenance;
    if (!provenance || typeof provenance !== 'object' || Array.isArray(provenance)) {
        errors.push('historical_git_recovery requires a repository_provenance object');
        return;
    }
    for (const field of REQUIRED_REPOSITORY_PROVENANCE_TEXT_FIELDS) {
        if (!nullableText(provenance[field])) {
            errors.push(`repository_provenance missing required field: ${field}`);
        }
    }
    for (const field of REQUIRED_REPOSITORY_PROVENANCE_SHA_FIELDS) {
        if (!GIT_OBJECT_SHA_PATTERN.test(String(provenance[field] || '').trim())) {
            errors.push(`repository_provenance.${field} must be a full 40-character Git object SHA`);
        }
    }
    if (!isStrictAbsoluteTimestamp(provenance.commit_timestamp)) {
        errors.push('repository_provenance.commit_timestamp must be a strict ISO-8601 timestamp');
    }
}

function appendHistoricalRecoveryErrors(manifest, errors) {
    if (manifest.captured_at !== null) {
        errors.push(
            'historical_git_recovery requires captured_at to be explicitly null; commit time, recovery time, and kickoff time must not impersonate the original capture time'
        );
    }
    if (manifest.capture_time_status !== 'unknown') {
        errors.push('historical_git_recovery requires capture_time_status: unknown');
    }
    if (!isStrictAbsoluteTimestamp(manifest.recovered_at)) {
        errors.push('historical_git_recovery requires recovered_at as a strict ISO-8601 timestamp');
    }
    if (manifest.provenance_status !== 'declared') {
        errors.push('historical_git_recovery requires provenance_status: declared');
    }
    if (manifest.upstream_provenance_status !== 'unverified') {
        errors.push('historical_git_recovery requires upstream_provenance_status: unverified');
    }
    appendRepositoryProvenanceErrors(manifest, errors);
}

function appendCaptureTimeErrors(manifest, errors) {
    if (isHistoricalGitRecoveryManifest(manifest)) {
        appendHistoricalRecoveryErrors(manifest, errors);
        return;
    }
    if (!isStrictAbsoluteTimestamp(manifest.captured_at)) {
        errors.push('captured_at must be an ISO-8601 timestamp with Z or an explicit numeric offset');
    }
    if (Object.prototype.hasOwnProperty.call(manifest, 'capture_time_status')) {
        errors.push('capture_time_status is only allowed when acquisition_mode is historical_git_recovery');
    }
    if (Object.prototype.hasOwnProperty.call(manifest, 'recovered_at')) {
        errors.push('recovered_at is only allowed when acquisition_mode is historical_git_recovery');
    }
}

function appendManifestValueErrors(manifest, errors) {
    if (manifest.schema_version !== SOURCE_MANIFEST_SCHEMA_VERSION) {
        errors.push(`unsupported manifest schema_version: ${manifest.schema_version || ''}`);
    }
    appendCaptureTimeErrors(manifest, errors);
    if (!Number.isSafeInteger(manifest.raw_size_bytes) || manifest.raw_size_bytes < 0) {
        errors.push('raw_size_bytes must be a non-negative safe integer');
    }
    if (!isSha256(manifest.raw_sha256)) {
        errors.push('raw_sha256 must be a 64-character SHA-256 hex string');
    }
    if (!ALLOWED_PROVENANCE_STATUSES.has(manifest.provenance_status)) {
        errors.push(`unsupported provenance_status: ${manifest.provenance_status || ''}`);
    }

    // Validate kickoff_time_interpretation if present
    if (manifest.kickoff_time_interpretation) {
        const ktiValidation = validateKickoffTimeInterpretation(manifest.kickoff_time_interpretation);
        for (const error of ktiValidation.errors) {
            errors.push(error);
        }
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
    HISTORICAL_GIT_RECOVERY_ACQUISITION_MODE,
    OfflineStagingError,
    assertAbsoluteLocalPath,
    isHistoricalGitRecoveryManifest,
    isNetworkReference,
    loadCandidates,
    loadSourceBundle,
    validateSourceManifest,
};
