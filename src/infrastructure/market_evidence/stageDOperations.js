'use strict';
/* eslint-disable max-lines -- the Stage D boundary keeps lock, ledger, adapter and failure ordering together for auditability. */

// Stage D operational controls deliberately live outside transaction-v1.  They
// govern whether an acquisition may happen; transaction-v1 remains the only
// canonical evidence publication authority.
const crypto = require('node:crypto');
const fs = require('node:fs');
const https = require('node:https');
const path = require('node:path');
const { HttpsProxyAgent } = require('https-proxy-agent');
const { SocksProxyAgent } = require('socks-proxy-agent');
const { getProxyProvider } = require('../network/ProxyProvider');
const { isUtcTimestamp, sha256Text, stableStringify } = require('./contracts');
const { createCaptureReceipt, loadVerifiedCaptureReceipt } = require('./evidenceStore');
const { openMarketEvidenceAuthoritySnapshot, isVerifiedMarketEvidenceAuthoritySnapshot } = require('./authorityReader');
const { publishProspectiveMarketEvidenceTransaction } = require('./atomicPublisher');
const { isVerifiedProspectiveTransactionCandidate, buildProspectiveMarketEvidenceTransaction } = require('./prospectiveBatch');

const EPOCH_SCHEMA_VERSION = 'footballprediction-stage-d-request-accounting-epoch/v1';
const LEDGER_SCHEMA_VERSION = 'footballprediction-stage-d-request-ledger/v1';
const RUN_LOCK_SCHEMA_VERSION = 'footballprediction-stage-d-run-lock/v1';
const RUN_LOCK_GENERATION_SCHEMA_VERSION = 'footballprediction-stage-d-ledger-generation/v1';
const QUOTA_SCHEMA_VERSION = 'footballprediction-stage-d-quota-budget/v2';
const EPOCH_FILE = 'REQUEST_ACCOUNTING_EPOCH.json';
const ENTRY_DIRECTORY = 'entries';
const RUN_LOCK_FILE = 'stage-d-run.lock.json';
const RUN_LOCK_PARENT_FILE_PREFIX = '.stage-d-run-';
const RUN_LOCK_ANCESTOR_FILE_PREFIX = '.stage-d-run-ancestor-';
const RUN_LOCK_TRUST_FILE_PREFIX = '.stage-d-runtime-fence-';
const RUN_LOCK_GENERATION_FILE_PREFIX = '.stage-d-ledger-generation-';
const PROVIDER = 'the-odds-api';
const MARKET_SCOPE = 'EPL_1X2_H2H';
const SUBSCRIPTION_TIER = 'starter_free';
const QUOTA_EVIDENCE_CLASS = 'OWNER_DECLARATION_PLUS_PUBLIC_PLAN_EVIDENCE';
const QUOTA_RESET_RULE = 'PROVIDER_RECONCILED__NO_UNVERIFIED_AUTOMATIC_RESET';
const LOCAL_LEDGER_AUTOMATIC_ZERO_ON_CALENDAR_CHANGE = false;
const CONFIGURED_MARKETS = Object.freeze(['h2h']);
const CONFIGURED_REGIONS = Object.freeze(['uk']);
const STAGE_D_MARKET_COUNT = CONFIGURED_MARKETS.length;
const STAGE_D_REGION_COUNT = CONFIGURED_REGIONS.length;
const EXPECTED_REQUEST_COST_CREDITS = STAGE_D_MARKET_COUNT * STAGE_D_REGION_COUNT;
const MAX_PROVIDER_REQUESTS_PER_CYCLE = 1;
const REQUIRED_QUOTA_HEADERS = Object.freeze(['x-requests-used', 'x-requests-remaining', 'x-requests-last']);
const PROVIDER_QUOTA_HEADER_PATTERN = /^(?:x-(?:requests|ratelimit|credits)-(?:remaining|used|last|limit|reset)|ratelimit-(?:remaining|used|limit|reset))$/i;
const HISTORICAL_PRE_EPOCH_REQUEST_TOTAL = 'AT_LEAST_2_CONFIRMED';
const HISTORICAL_PRE_EPOCH_EXACT_TOTAL = 'UNKNOWN';
const EVENT_TYPES = new Set([
    'REQUEST_INTENT',
    'TRANSMISSION_STARTED_OR_MAY_HAVE_STARTED',
    'RESPONSE_RECEIVED',
    'HTTP_FAILURE_AFTER_TRANSMISSION',
    'TRANSPORT_FAILURE_AFTER_POSSIBLE_TRANSMISSION',
    'CANCELLED_BEFORE_TRANSMISSION',
]);
const TERMINAL_STATES = new Set([
    'RESPONSE_RECEIVED',
    'HTTP_FAILURE_AFTER_TRANSMISSION',
    'TRANSPORT_FAILURE_AFTER_POSSIBLE_TRANSMISSION',
    'CANCELLED_BEFORE_TRANSMISSION',
]);
const activeLockTokens = new WeakSet();
const approvedTransports = new WeakSet();
const approvedPersistors = new WeakSet();
const approvedPublishers = new WeakSet();
const approvedCandidateBuilders = new WeakSet();
const approvedQuotaConfigs = new WeakSet();
// This capability is deliberately not exported.  A future owner-approved
// bootstrap must obtain/hold it in the same trusted process that supplies the
// verified quota configuration; a copied string must never arm live transport.
const STAGE_D_RUNTIME_AUTHORIZATION = Symbol('stage-d-runtime-authorization');
const STAGE_D_TEST_RUNTIME_AUTHORIZATION = Symbol('stage-d-test-runtime-authorization');
const STAGE_D_TRANSPORT_CALL_TOKEN = Object.freeze({ stage_d: 'transport-call' });
const CONTROLLED_AUTHORIZATION_SCHEMA_VERSION = 'footballprediction-stage-d-controlled-initialization-authorization/v1';
const CONTROLLED_AUTHORIZATION_STATUS = 'OWNER_AND_CHIEF_ENGINEER_AUTHORIZED';
const CONTROLLED_AUTHORIZATION_MISSION = 'CONTROLLED_STAGE_D_SINGLE_CYCLE';
const CONTROLLED_AUTHORIZATION_MAX_LIFETIME_MS = 24 * 60 * 60 * 1000;
const CONTROLLED_AUTHORIZATION_CONSUMPTION_FILE_PREFIX = '.stage-d-authorization-consumed-';
const DIRECTORY_FD_ROOT = '/proc/self/fd';

function fail(code, message) {
    const error = new Error(message);
    error.code = code;
    throw error;
}

function createStageDTestRuntimeAuthorization() {
    if (process.env.NODE_ENV !== 'test') fail('STAGE_D_NOT_AUTHORIZED', 'test runtime authorization is unavailable outside NODE_ENV=test');
    return STAGE_D_TEST_RUNTIME_AUTHORIZATION;
}

function createStageDProductionQuotaConfiguration(value, { now } = {}) {
    const normalized = validateQuotaConfiguration(value, { now });
    approvedQuotaConfigs.add(normalized);
    return normalized;
}

function assertPlainObject(value, label) {
    if (!value || typeof value !== 'object' || Array.isArray(value) || Object.getPrototypeOf(value) !== Object.prototype) {
        fail('INVALID_CONTRACT', `${label} must be a plain object`);
    }
}

function clonePlainData(value, label, seen = new Set()) {
    if (value === null || typeof value === 'string' || typeof value === 'number' || typeof value === 'boolean') return value;
    if (typeof value !== 'object') fail('INVALID_CONTRACT', `${label} contains executable or unsupported data`);
    if (seen.has(value)) fail('INVALID_CONTRACT', `${label} contains a cycle`);
    const prototype = Object.getPrototypeOf(value);
    if (prototype !== Object.prototype && prototype !== null && !Array.isArray(value)) fail('INVALID_CONTRACT', `${label} must contain plain data`);
    const nextSeen = new Set(seen);
    nextSeen.add(value);
    const output = Array.isArray(value) ? [] : {};
    for (const key of Object.keys(value)) {
        const descriptor = Object.getOwnPropertyDescriptor(value, key);
        if (!descriptor || !Object.prototype.hasOwnProperty.call(descriptor, 'value')) fail('INVALID_CONTRACT', `${label}.${key} must be a data property`);
        output[key] = clonePlainData(descriptor.value, `${label}.${key}`, nextSeen);
    }
    return output;
}

function assertExactKeys(value, keys, label) {
    assertPlainObject(value, label);
    const actual = Object.keys(value).sort();
    const expected = [...keys].sort();
    if (stableStringify(actual) !== stableStringify(expected)) fail('INVALID_CONTRACT', `${label} fields are invalid`);
}

function assertToken(value, label) {
    if (typeof value !== 'string' || !/^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$/.test(value)) {
        fail('INVALID_CONTRACT', `${label} is invalid`);
    }
    return value;
}

function assertUtc(value, label, nullable = false) {
    if (value === null && nullable) return null;
    if (!isUtcTimestamp(value)) fail('INVALID_CONTRACT', `${label} must be UTC ISO-8601`);
    return value;
}

function assertNonNegativeInteger(value, label) {
    if (!Number.isInteger(value) || value < 0) fail('INVALID_CONTRACT', `${label} must be a non-negative integer`);
    return value;
}

function canonicalBytes(value) {
    return `${stableStringify(value)}\n`;
}

function directoryIdentity(directory, label) {
    const stat = fs.lstatSync(directory);
    if (stat.isSymbolicLink() || !stat.isDirectory()) fail('UNSAFE_PATH', `${label} must be a non-symlink directory`);
    return directoryIdentityFromStat(stat);
}

function sameDirectoryIdentity(left, right) {
    return Boolean(left && right
        && left.dev === right.dev
        && left.ino === right.ino
        && left.mode === right.mode
        && left.uid === right.uid
        && left.gid === right.gid);
}

function directoryIdentityFromStat(stat) {
    return Object.freeze({ dev: stat.dev, ino: stat.ino, mode: stat.mode, uid: stat.uid, gid: stat.gid });
}

function trustedDirectoryIdentity(directory, label) {
    const descriptor = openTrustedDirectoryDescriptor(directory, label);
    try {
        return descriptor.identity;
    } finally {
        closeDirectoryDescriptor(descriptor);
    }
}

function assertDirectoryIdentity(directory, expected, label) {
    const observed = trustedDirectoryIdentity(directory, label);
    if (!sameDirectoryIdentity(observed, expected)) fail('DIRECTORY_IDENTITY_CHANGED', `${label} identity changed during the cycle`);
    return observed;
}

function openDirectoryDescriptor(directory, label, expected = null) {
    const resolved = path.resolve(directory);
    const observed = fs.lstatSync(resolved);
    if (observed.isSymbolicLink() || !observed.isDirectory()) fail('UNSAFE_PATH', `${label} must be a non-symlink directory`);
    const fd = fs.openSync(resolved, fs.constants.O_RDONLY | (fs.constants.O_DIRECTORY || 0) | (fs.constants.O_NOFOLLOW || 0));
    try {
        const stat = fs.fstatSync(fd);
        if (!stat.isDirectory()) fail('UNSAFE_PATH', `${label} descriptor is not a directory`);
        if (!sameDirectoryIdentity(stat, observed)) fail('DIRECTORY_IDENTITY_CHANGED', `${label} changed during open`);
        if (expected && !sameDirectoryIdentity(stat, expected)) fail('DIRECTORY_IDENTITY_CHANGED', `${label} changed during open`);
        return Object.freeze({ fd, path: resolved, identity: directoryIdentityFromStat(stat) });
    } catch (error) {
        fs.closeSync(fd);
        throw error;
    }
}

function openChildDirectoryDescriptor(parentFd, name, label, expected = null) {
    const childPath = scopedPath(parentFd, name);
    const observed = fs.lstatSync(childPath);
    if (observed.isSymbolicLink() || !observed.isDirectory()) fail('UNSAFE_PATH', `${label} must be a non-symlink directory`);
    const fd = fs.openSync(childPath, fs.constants.O_RDONLY | (fs.constants.O_DIRECTORY || 0) | (fs.constants.O_NOFOLLOW || 0));
    try {
        const stat = fs.fstatSync(fd);
        if (!stat.isDirectory()) fail('UNSAFE_PATH', `${label} descriptor is not a directory`);
        if (!sameDirectoryIdentity(stat, observed)) fail('DIRECTORY_IDENTITY_CHANGED', `${label} changed during open`);
        if (expected && !sameDirectoryIdentity(stat, expected)) fail('DIRECTORY_IDENTITY_CHANGED', `${label} changed during open`);
        return Object.freeze({ fd, path: childPath, identity: directoryIdentityFromStat(stat) });
    } catch (error) {
        fs.closeSync(fd);
        throw error;
    }
}

// Open a sensitive root through a descriptor for its parent, then compare the
// child identity before and after the child open.  This closes the common
// lstat(root) -> open(root) window in which a same-type directory could be
// swapped underneath the caller.  The returned descriptor is the authority;
// subsequent mutations resolve children through its fd.
function openTrustedDirectoryDescriptor(directory, label, expected = null) {
    const resolved = path.resolve(directory);
    const parentPath = path.dirname(resolved);
    const name = path.basename(resolved);
    if (!name || name === '.' || name === '..') fail('UNSAFE_PATH', `${label} path is invalid`);
    const parentDescriptor = openDirectoryDescriptor(parentPath, `${label} parent`);
    try {
        const observed = directoryIdentity(scopedPath(parentDescriptor.fd, name), label);
        const identity = expected || observed;
        if (expected && !sameDirectoryIdentity(observed, expected)) {
            fail('DIRECTORY_IDENTITY_CHANGED', `${label} changed before open`);
        }
        const child = openChildDirectoryDescriptor(parentDescriptor.fd, name, label, identity);
        return Object.freeze({ ...child, path: resolved });
    } finally {
        closeDirectoryDescriptor(parentDescriptor);
    }
}

function closeDirectoryDescriptor(descriptor) {
    if (descriptor && Number.isInteger(descriptor.fd)) fs.closeSync(descriptor.fd);
}

function runLockParentFile(operationRoot) {
    const resolved = path.resolve(operationRoot);
    return `${RUN_LOCK_PARENT_FILE_PREFIX}${sha256Text(resolved)}.parent.lock.json`;
}

function runLockAncestorFile(operationRoot) {
    const resolved = path.resolve(operationRoot);
    return `${RUN_LOCK_ANCESTOR_FILE_PREFIX}${sha256Text(resolved)}.parent.lock.json`;
}

function runLockTrustFile(operationRoot) {
    const resolved = path.resolve(operationRoot);
    return `${RUN_LOCK_TRUST_FILE_PREFIX}${sha256Text(resolved)}.lock.json`;
}

function runLockGenerationFile(operationRoot, entryCount) {
    assertNonNegativeInteger(entryCount, 'ledger generation entry_count');
    const resolved = path.resolve(operationRoot);
    return `${RUN_LOCK_GENERATION_FILE_PREFIX}${sha256Text(resolved)}-${String(entryCount).padStart(12, '0')}.json`;
}

function defaultRunLockTrustRoot(operationRoot) {
    const resolved = path.resolve(operationRoot);
    // The test-only fallback is deterministic per operation root and lives
    // outside the operation-root parent.  Production callers must supply an
    // owner-controlled path explicitly (see resolveRunLockTrustRoot).
    return path.join(
        path.dirname(path.dirname(resolved)),
        '.stage-d-runtime-trust',
        sha256Text(resolved),
    );
}

function resolveRunLockTrustRoot(operationRoot, supplied) {
    if (supplied !== undefined && (typeof supplied !== 'string' || !supplied.trim())) {
        fail('UNSAFE_TRUST_ROOT', 'runLockTrustRoot must be an explicit non-empty path');
    }
    const resolvedOperationRoot = path.resolve(operationRoot);
    const resolvedTrustRoot = typeof supplied === 'string' && supplied.trim()
        ? path.resolve(supplied)
        : defaultRunLockTrustRoot(resolvedOperationRoot);
    const trustContainsOperation = path.relative(resolvedTrustRoot, resolvedOperationRoot);
    const operationContainsTrust = path.relative(resolvedOperationRoot, resolvedTrustRoot);
    const isNested = relative => relative === '' || (relative !== '..' && !relative.startsWith(`..${path.sep}`) && !path.isAbsolute(relative));
    if (isNested(trustContainsOperation) || isNested(operationContainsTrust)) {
        fail('UNSAFE_TRUST_ROOT', 'runtime trust root must be a separate path domain from the Stage D operation root');
    }
    if (typeof supplied === 'string' && supplied.trim()) return resolvedTrustRoot;
    if (process.env.NODE_ENV !== 'test') fail('RUN_LOCK_TRUST_ROOT_REQUIRED', 'production Stage D runs require an explicit external runtime trust root');
    return resolvedTrustRoot;
}

function assertControlledTrustParentChain(directory) {
    let current = path.dirname(path.resolve(directory));
    let atFilesystemRoot = false;
    while (!atFilesystemRoot) {
        const stat = fs.lstatSync(current);
        if (stat.isSymbolicLink() || !stat.isDirectory()) fail('UNSAFE_TRUST_ROOT', 'runtime trust-root parent chain must contain real directories');
        const owner = typeof process.getuid === 'function' ? process.getuid() : stat.uid;
        if ((stat.uid !== owner && stat.uid !== 0) || (stat.mode & 0o022) !== 0) fail('UNSAFE_TRUST_ROOT', 'runtime trust-root parent chain must be runtime- or root-owned and not group/world writable');
        atFilesystemRoot = current === path.dirname(current);
        current = path.dirname(current);
    }
}

function openTrustedRuntimeRoot(operationRoot, trustRoot, expected = null) {
    const resolvedTrustRoot = resolveRunLockTrustRoot(operationRoot, trustRoot);
    if (!fs.existsSync(resolvedTrustRoot) && process.env.NODE_ENV === 'test') {
        fs.mkdirSync(resolvedTrustRoot, { recursive: true, mode: 0o700 });
    }
    const descriptor = openTrustedDirectoryDescriptor(resolvedTrustRoot, 'Stage D runtime trust root', expected);
    const stat = fs.fstatSync(descriptor.fd);
    const owner = typeof process.getuid === 'function' ? process.getuid() : stat.uid;
    if (stat.uid !== owner || (stat.mode & 0o022) !== 0) {
        closeDirectoryDescriptor(descriptor);
        fail('UNSAFE_TRUST_ROOT', 'Stage D runtime trust root must be owned by the runtime user and not group/world writable');
    }
    if (process.env.NODE_ENV !== 'test') {
        try {
            assertControlledTrustParentChain(resolvedTrustRoot);
        } catch (error) {
            closeDirectoryDescriptor(descriptor);
            throw error;
        }
    }
    return Object.freeze({ ...descriptor, path: resolvedTrustRoot });
}

// Keep the parent descriptor open for the complete lock lifetime.  The parent
// sentinel is deliberately outside the operation root: replacing the root
// directory therefore cannot make an active run invisible to the next run.
function openTrustedRootWithParent(directory, label, expected = null) {
    const resolved = path.resolve(directory);
    const parentPath = path.dirname(resolved);
    const name = path.basename(resolved);
    if (!name || name === '.' || name === '..') fail('UNSAFE_PATH', `${label} path is invalid`);
    const ancestorPath = path.dirname(parentPath);
    const ancestorName = path.basename(parentPath);
    const ancestorDescriptor = ancestorName && ancestorName !== '.' && ancestorName !== '..'
        ? openDirectoryDescriptor(ancestorPath, `${label} ancestor`)
        : null;
    let parentDescriptor;
    try {
        parentDescriptor = ancestorDescriptor
            ? openChildDirectoryDescriptor(ancestorDescriptor.fd, ancestorName, `${label} parent`)
            : openDirectoryDescriptor(parentPath, `${label} parent`);
        const observed = directoryIdentity(scopedPath(parentDescriptor.fd, name), label);
        if (expected && !sameDirectoryIdentity(observed, expected)) {
            fail('DIRECTORY_IDENTITY_CHANGED', `${label} changed before open`);
        }
        const rootDescriptor = openChildDirectoryDescriptor(parentDescriptor.fd, name, label, expected || observed);
        return Object.freeze({ ancestorDescriptor, parentDescriptor, rootDescriptor: Object.freeze({ ...rootDescriptor, path: resolved }) });
    } catch (error) {
        closeDirectoryDescriptor(parentDescriptor);
        closeDirectoryDescriptor(ancestorDescriptor);
        throw error;
    }
}

function scopedPath(directoryFd, name) {
    if (!Number.isInteger(directoryFd) || directoryFd < 0 || typeof name !== 'string' || name.includes('/') || name === '' || name === '.' || name === '..') {
        fail('UNSAFE_PATH', 'directory-scoped path is invalid');
    }
    if (process.platform !== 'linux') fail('UNSUPPORTED_PLATFORM', 'directory-scoped Stage D mutation requires Linux /proc/self/fd');
    return path.join(DIRECTORY_FD_ROOT, String(directoryFd), name);
}

function directoryFdPath(directoryFd) {
    if (!Number.isInteger(directoryFd) || directoryFd < 0) fail('UNSAFE_PATH', 'directory descriptor is invalid');
    if (process.platform !== 'linux') fail('UNSUPPORTED_PLATFORM', 'descriptor-bound Stage D publication requires Linux /proc/self/fd');
    return path.join(DIRECTORY_FD_ROOT, String(directoryFd));
}

function fsyncDirectoryFd(directoryFd) {
    const fd = fs.openSync(path.join(DIRECTORY_FD_ROOT, String(directoryFd)), fs.constants.O_RDONLY | (fs.constants.O_DIRECTORY || 0));
    try {
        fs.fsyncSync(fd);
    } finally {
        fs.closeSync(fd);
    }
}

function ensureChildDirectoryDescriptor(parentDescriptor, name, label) {
    try {
        return openChildDirectoryDescriptor(parentDescriptor.fd, name, label);
    } catch (error) {
        if (error?.code !== 'ENOENT') throw error;
        fs.mkdirSync(scopedPath(parentDescriptor.fd, name), { mode: 0o700 });
        fsyncDirectoryFd(parentDescriptor.fd);
        return openChildDirectoryDescriptor(parentDescriptor.fd, name, label);
    }
}

function readRegularFileBytes(filePath, label, { immutable = true } = {}) {
    const before = fs.lstatSync(filePath);
    if (before.isSymbolicLink() || !before.isFile()) fail('UNSAFE_PATH', `${label} must be a regular file`);
    if (immutable && (before.mode & 0o222) !== 0) fail('MUTABLE_EVIDENCE', `${label} must be read-only`);
    let fd;
    try {
        fd = fs.openSync(filePath, fs.constants.O_RDONLY | (fs.constants.O_NOFOLLOW || 0));
        const opened = fs.fstatSync(fd);
        if (!opened.isFile() || opened.dev !== before.dev || opened.ino !== before.ino) fail('UNSAFE_PATH', `${label} changed during open`);
        const bytes = fs.readFileSync(fd, 'utf8');
        const after = fs.fstatSync(fd);
        if (after.dev !== opened.dev || after.ino !== opened.ino) fail('UNSAFE_PATH', `${label} changed during read`);
        return Object.freeze({ bytes, stat: opened });
    } finally {
        if (fd !== undefined) fs.closeSync(fd);
    }
}

function readCanonicalJson(filePath, label, options = {}) {
    const { bytes } = readRegularFileBytes(filePath, label, options);
    return parseCanonicalJsonBytes(bytes, label);
}

function parseCanonicalJsonBytes(bytes, label) {
    let parsed;
    try {
        parsed = JSON.parse(bytes);
    } catch (error) {
        fail('INVALID_JSON', `${label} is invalid JSON: ${error.message}`);
    }
    if (bytes !== canonicalBytes(parsed)) fail('NON_CANONICAL_EVIDENCE', `${label} must use canonical serialization`);
    return parsed;
}

function assertSha256(value, label) {
    if (typeof value !== 'string' || !/^[a-f0-9]{64}$/.test(value)) fail('INVALID_AUTHORIZATION', `${label} must be a lowercase SHA-256`);
    return value;
}

function isDirectChild(parent, child) {
    return path.dirname(path.resolve(child)) === path.resolve(parent);
}

function readStageDControlledAuthorization({ authorizationArtifactPath, ledgerRoot, runLockTrustRoot } = {}) {
    if (typeof authorizationArtifactPath !== 'string' || !authorizationArtifactPath.trim()) fail('INVALID_AUTHORIZATION', 'authorizationArtifactPath is required');
    if (typeof ledgerRoot !== 'string' || !ledgerRoot.trim()) fail('INVALID_AUTHORIZATION', 'ledgerRoot is required for authorization binding');
    const trustDescriptor = openTrustedRuntimeRoot(ledgerRoot, runLockTrustRoot);
    try {
        const resolvedPath = path.resolve(authorizationArtifactPath);
        if (!isDirectChild(trustDescriptor.path, resolvedPath)) fail('UNTRUSTED_AUTHORIZATION', 'authorization artifact must be a direct child of the external runtime trust root');
        const observed = readRegularFileBytes(resolvedPath, 'Stage D controlled authorization', { immutable: true });
        const authorization = parseCanonicalJsonBytes(observed.bytes, 'Stage D controlled authorization');
        if (observed.stat.uid !== process.getuid?.() && observed.stat.uid !== 0) fail('UNTRUSTED_AUTHORIZATION', 'authorization artifact owner is not the runtime user or root');
        return Object.freeze({
            path: resolvedPath,
            authorization: Object.freeze(authorization),
            authorization_sha256: sha256Text(observed.bytes),
        });
    } finally {
        closeDirectoryDescriptor(trustDescriptor);
    }
}

function sha256RegularFile(filePath, label) {
    return sha256Text(readRegularFileBytes(filePath, label, { immutable: true }).bytes);
}

function controlledAuthorizationScope(authorization) {
    return Object.freeze({
        mission: authorization.mission,
        provider: authorization.provider,
        configured_markets: [...authorization.configured_markets],
        configured_regions: [...authorization.configured_regions],
        max_provider_requests: authorization.max_provider_requests,
        expected_request_cost_credits: authorization.expected_request_cost_credits,
        accounting_epoch_id: authorization.accounting_epoch_id,
        authority_pre_head: authorization.authority_pre_head,
        authority_pre_state_hash: authorization.authority_pre_state_hash,
        authority_pre_observation_count: authorization.authority_pre_observation_count,
        authority_pre_store_sha256: authorization.authority_pre_store_sha256,
        authority_pre_allocation_authority_sha256: authorization.authority_pre_allocation_authority_sha256,
        quota_config_sha256: authorization.quota_config_sha256,
        fixture_universe_raw_sha256: authorization.fixture_universe_raw_sha256,
        run_id: authorization.run_id,
        request_id: authorization.request_id,
    });
}

// eslint-disable-next-line complexity -- controlled authorization validates each immutable scope field independently.
function validateStageDControlledAuthorization({ authorization, authoritySnapshot, authorityRoot, allocationArtifactPath, ledger, quotaConfig, quotaConfigSha256, fixtureUniverseRawSha256, now } = {}) {
    assertExactKeys(
        authorization,
        [
            'schema_version',
            'authorization_id',
            'authorization_status',
            'mission',
            'provider',
            'configured_markets',
            'configured_regions',
            'max_provider_requests',
            'expected_request_cost_credits',
            'accounting_epoch_id',
            'authority_pre_head',
            'authority_pre_state_hash',
            'authority_pre_observation_count',
            'authority_pre_store_sha256',
            'authority_pre_allocation_authority_sha256',
            'quota_config_sha256',
            'fixture_universe_raw_sha256',
            'run_id',
            'request_id',
            'issued_at',
            'expires_at',
        ],
        'Stage D controlled authorization'
    );
    if (authorization.schema_version !== CONTROLLED_AUTHORIZATION_SCHEMA_VERSION || authorization.authorization_status !== CONTROLLED_AUTHORIZATION_STATUS) fail('INVALID_AUTHORIZATION', 'controlled authorization schema or approval status is invalid');
    if (!/^sda_[A-Za-z0-9][A-Za-z0-9._-]{0,120}$/.test(authorization.authorization_id)) fail('INVALID_AUTHORIZATION', 'authorization_id is invalid');
    if (authorization.mission !== CONTROLLED_AUTHORIZATION_MISSION || authorization.provider !== PROVIDER) fail('INVALID_AUTHORIZATION', 'authorization mission or provider scope is invalid');
    if (stableStringify(authorization.configured_markets) !== stableStringify(CONFIGURED_MARKETS) || stableStringify(authorization.configured_regions) !== stableStringify(CONFIGURED_REGIONS)) fail('INVALID_AUTHORIZATION', 'authorization market or region scope is invalid');
    if (authorization.max_provider_requests !== MAX_PROVIDER_REQUESTS_PER_CYCLE || authorization.expected_request_cost_credits !== EXPECTED_REQUEST_COST_CREDITS) fail('INVALID_AUTHORIZATION', 'authorization request scope is not bounded to one expected credit');
    assertToken(authorization.accounting_epoch_id, 'authorization.accounting_epoch_id');
    if (!/^tx_[a-f0-9]{64}$/.test(authorization.authority_pre_head || '') || !/^[a-f0-9]{64}$/.test(authorization.authority_pre_state_hash || '')) fail('INVALID_AUTHORIZATION', 'authorization authority pre-state is invalid');
    assertNonNegativeInteger(authorization.authority_pre_observation_count, 'authorization.authority_pre_observation_count');
    assertSha256(authorization.authority_pre_store_sha256, 'authorization.authority_pre_store_sha256');
    assertSha256(authorization.authority_pre_allocation_authority_sha256, 'authorization.authority_pre_allocation_authority_sha256');
    assertSha256(authorization.quota_config_sha256, 'authorization.quota_config_sha256');
    assertSha256(authorization.fixture_universe_raw_sha256, 'authorization.fixture_universe_raw_sha256');
    assertToken(authorization.run_id, 'authorization.run_id');
    assertToken(authorization.request_id, 'authorization.request_id');
    assertUtc(authorization.issued_at, 'authorization.issued_at');
    assertUtc(authorization.expires_at, 'authorization.expires_at');
    assertUtc(now, 'authorization validation time');
    const issuedAt = Date.parse(authorization.issued_at);
    const expiresAt = Date.parse(authorization.expires_at);
    const currentAt = Date.parse(now);
    if (expiresAt <= issuedAt || expiresAt - issuedAt > CONTROLLED_AUTHORIZATION_MAX_LIFETIME_MS) fail('INVALID_AUTHORIZATION', 'authorization lifetime is invalid or unbounded');
    if (currentAt < issuedAt || currentAt >= expiresAt) fail('STAGE_D_AUTHORIZATION_EXPIRED', 'controlled authorization is not currently valid');
    if (authorization.accounting_epoch_id !== ledger?.epoch?.epoch_id) fail('AUTHORIZATION_EPOCH_MISMATCH', 'authorization accounting epoch does not match the durable ledger');
    if (authorization.authority_pre_head !== authoritySnapshot?.head_transaction_id || authorization.authority_pre_state_hash !== authoritySnapshot?.state_hash || authorization.authority_pre_observation_count !== authoritySnapshot?.observations?.length) fail('AUTHORIZATION_AUTHORITY_PRESTATE_MISMATCH', 'authorization authority pre-state does not match the fresh authority snapshot');
    const resolvedAuthorityRoot = path.resolve(authorityRoot);
    const resolvedAllocationPath = path.resolve(allocationArtifactPath);
    if (authorization.authority_pre_store_sha256 !== sha256RegularFile(path.join(resolvedAuthorityRoot, 'STORE.json'), 'Stage D authority STORE.json')) fail('AUTHORIZATION_AUTHORITY_PRESTATE_MISMATCH', 'authorization STORE hash does not match the authority root');
    if (authorization.authority_pre_allocation_authority_sha256 !== sha256RegularFile(resolvedAllocationPath, 'Stage D allocation authority')) fail('AUTHORIZATION_AUTHORITY_PRESTATE_MISMATCH', 'authorization allocation authority hash does not match the authority root');
    if (authorization.quota_config_sha256 !== quotaConfigSha256) fail('AUTHORIZATION_QUOTA_MISMATCH', 'authorization quota configuration hash does not match the supplied governed configuration');
    if (authorization.fixture_universe_raw_sha256 !== fixtureUniverseRawSha256) fail('AUTHORIZATION_FIXTURE_UNIVERSE_MISMATCH', 'authorization fixture-universe RAW hash does not match the supplied replay input');
    const validatedQuota = validateQuotaConfiguration(quotaConfig, { now });
    if (validatedQuota.provider !== authorization.provider || validatedQuota.expected_request_cost_credits !== authorization.expected_request_cost_credits || validatedQuota.max_provider_requests_per_cycle !== authorization.max_provider_requests || validatedQuota.max_requests_per_stage_d_run !== authorization.max_provider_requests) fail('AUTHORIZATION_QUOTA_MISMATCH', 'authorization does not bind the governed one-request quota configuration');
    return Object.freeze({
        authorization,
        scope: controlledAuthorizationScope(authorization),
        scope_sha256: sha256Text(stableStringify(controlledAuthorizationScope(authorization))),
    });
}

function consumeStageDControlledAuthorization({ authorizationRecord, ledgerRoot, runLockTrustRoot, consumedAt } = {}) {
    assertPlainObject(authorizationRecord, 'authorizationRecord');
    const { authorization, scope, scope_sha256, authorization_sha256 } = authorizationRecord;
    const trustDescriptor = openTrustedRuntimeRoot(ledgerRoot, runLockTrustRoot);
    const markerName = `${CONTROLLED_AUTHORIZATION_CONSUMPTION_FILE_PREFIX}${authorization.authorization_id}.json`;
    try {
        writeExclusiveImmutable(
            scopedPath(trustDescriptor.fd, markerName),
            {
                schema_version: 'footballprediction-stage-d-controlled-initialization-consumption/v1',
                authorization_id: authorization.authorization_id,
                authorization_sha256,
                scope_sha256,
                mission: scope.mission,
                provider: scope.provider,
                market: scope.configured_markets[0],
                region: scope.configured_regions[0],
                max_provider_requests: scope.max_provider_requests,
                expected_request_cost_credits: scope.expected_request_cost_credits,
                accounting_epoch_id: scope.accounting_epoch_id,
                authority_pre_head: scope.authority_pre_head,
                run_id: scope.run_id,
                request_id: scope.request_id,
                consumed_at: consumedAt,
            },
            'Stage D controlled authorization consumption marker',
            { directoryFd: trustDescriptor.fd },
        );
    } catch (error) {
        if (error?.code === 'EEXIST') fail('STAGE_D_AUTHORIZATION_REPLAY', 'controlled authorization has already been consumed');
        throw error;
    } finally {
        closeDirectoryDescriptor(trustDescriptor);
    }
    return Object.freeze({ marker_name: markerName, scope_sha256 });
}

function assertStageDAuthorityPreState({ authoritySnapshot, authorityRoot, allocationArtifactPath, expected } = {}) {
    assertExactKeys(expected, ['head_transaction_id', 'state_hash', 'observation_count', 'store_sha256', 'allocation_authority_sha256'], 'Stage D authority pre-state expectation');
    if (expected.head_transaction_id !== authoritySnapshot?.head_transaction_id || expected.state_hash !== authoritySnapshot?.state_hash || expected.observation_count !== authoritySnapshot?.observations?.length) fail('AUTHORIZATION_AUTHORITY_PRESTATE_MISMATCH', 'authority changed after controlled authorization validation');
    if (expected.store_sha256 !== sha256RegularFile(path.join(path.resolve(authorityRoot), 'STORE.json'), 'Stage D authority STORE.json') || expected.allocation_authority_sha256 !== sha256RegularFile(path.resolve(allocationArtifactPath), 'Stage D allocation authority')) fail('AUTHORIZATION_AUTHORITY_PRESTATE_MISMATCH', 'authority artifact hash changed after controlled authorization validation');
}

function fsyncDirectory(directory) {
    const fd = fs.openSync(directory, fs.constants.O_RDONLY | (fs.constants.O_DIRECTORY || 0));
    try {
        fs.fsyncSync(fd);
    } finally {
        fs.closeSync(fd);
    }
}

function writeExclusiveImmutable(filePath, value, label, { directoryFd = null } = {}) {
    return writeExclusiveBytes(filePath, canonicalBytes(value), label, { directoryFd });
}

function writeExclusiveBytes(filePath, bytes, label, { directoryFd = null, mode = 0o400 } = {}) {
    let fd;
    try {
        fd = fs.openSync(
            filePath,
            fs.constants.O_WRONLY | fs.constants.O_CREAT | fs.constants.O_EXCL | (fs.constants.O_NOFOLLOW || 0),
            mode
        );
        const data = Buffer.from(bytes, 'utf8');
        let offset = 0;
        while (offset < data.length) {
            const written = fs.writeSync(fd, data, offset, data.length - offset);
            if (!Number.isInteger(written) || written <= 0) fail('SHORT_WRITE', `${label} short write`);
            offset += written;
        }
        fs.fchmodSync(fd, mode);
        fs.fsyncSync(fd);
    } finally {
        if (fd !== undefined) fs.closeSync(fd);
    }
    if (directoryFd === null) fsyncDirectory(path.dirname(filePath));
    else fsyncDirectoryFd(directoryFd);
}

function createEpochId({ startedAt, authorityHead, authorityStateHash }) {
    return `sde_${sha256Text(`${EPOCH_SCHEMA_VERSION}\u0000${startedAt}\u0000${authorityHead}\u0000${authorityStateHash}`)}`;
}

function validateEpoch(value) {
    assertExactKeys(
        value,
        [
            'schema_version',
            'epoch_id',
            'started_at',
            'start_authority_head',
            'start_authority_state_hash',
            'historical_pre_epoch_request_total',
            'historical_pre_epoch_exact_total',
            'genesis_entry_hash',
        ],
        'request accounting epoch'
    );
    if (value.schema_version !== EPOCH_SCHEMA_VERSION) fail('INVALID_EPOCH', 'request accounting epoch schema is invalid');
    assertToken(value.epoch_id, 'epoch_id');
    assertUtc(value.started_at, 'epoch started_at');
    if (!/^tx_[a-f0-9]{64}$/.test(value.start_authority_head || '')) fail('INVALID_EPOCH', 'epoch authority head is invalid');
    if (!/^[a-f0-9]{64}$/.test(value.start_authority_state_hash || '')) fail('INVALID_EPOCH', 'epoch authority state hash is invalid');
    if (value.historical_pre_epoch_request_total !== HISTORICAL_PRE_EPOCH_REQUEST_TOTAL) {
        fail('INVALID_EPOCH', 'historical pre-epoch lower bound must be preserved');
    }
    if (value.historical_pre_epoch_exact_total !== HISTORICAL_PRE_EPOCH_EXACT_TOTAL) {
        fail('INVALID_EPOCH', 'historical pre-epoch uncertainty must be preserved');
    }
    const unsigned = { ...value };
    delete unsigned.genesis_entry_hash;
    if (value.genesis_entry_hash !== sha256Text(stableStringify(unsigned))) fail('INVALID_EPOCH', 'epoch genesis hash is invalid');
    return Object.freeze({ ...value });
}

function initializeRequestAccountingEpoch({ ledgerRoot, authoritySnapshot, startedAt, epochId } = {}) {
    if (typeof ledgerRoot !== 'string' || !ledgerRoot.trim()) fail('INVALID_EPOCH', 'ledgerRoot is required');
    assertPlainObject(authoritySnapshot, 'authoritySnapshot');
    if (!/^tx_[a-f0-9]{64}$/.test(authoritySnapshot.head_transaction_id || '')) {
        fail('INVALID_EPOCH', 'an existing canonical authority head is required');
    }
    if (!/^[a-f0-9]{64}$/.test(authoritySnapshot.state_hash || '')) fail('INVALID_EPOCH', 'canonical authority state hash is required');
    assertUtc(startedAt, 'epoch startedAt');
    const root = path.resolve(ledgerRoot);
    const parentDescriptor = openDirectoryDescriptor(path.dirname(root), 'request ledger parent');
    let rootDescriptor;
    let entriesDescriptor;
    try {
        rootDescriptor = ensureChildDirectoryDescriptor(parentDescriptor, path.basename(root), 'request ledger root');
        entriesDescriptor = ensureChildDirectoryDescriptor(rootDescriptor, ENTRY_DIRECTORY, 'request ledger entries directory');
    } catch (error) {
        closeDirectoryDescriptor(entriesDescriptor);
        closeDirectoryDescriptor(rootDescriptor);
        closeDirectoryDescriptor(parentDescriptor);
        throw error;
    }
    try {
        const epochPath = scopedPath(rootDescriptor.fd, EPOCH_FILE);
        const id = epochId || createEpochId({
            startedAt,
            authorityHead: authoritySnapshot.head_transaction_id,
            authorityStateHash: authoritySnapshot.state_hash,
        });
        assertToken(id, 'epoch_id');
        const unsigned = {
            schema_version: EPOCH_SCHEMA_VERSION,
            epoch_id: id,
            started_at: startedAt,
            start_authority_head: authoritySnapshot.head_transaction_id,
            start_authority_state_hash: authoritySnapshot.state_hash,
            historical_pre_epoch_request_total: HISTORICAL_PRE_EPOCH_REQUEST_TOTAL,
            historical_pre_epoch_exact_total: HISTORICAL_PRE_EPOCH_EXACT_TOTAL,
        };
        const epoch = { ...unsigned, genesis_entry_hash: sha256Text(stableStringify(unsigned)) };
        if (fs.existsSync(epochPath)) {
            const existing = validateEpoch(readCanonicalJson(epochPath, 'request accounting epoch'));
            if (stableStringify(existing) !== stableStringify(epoch)) fail('EPOCH_ALREADY_EXISTS', 'request accounting epoch already exists with different content');
            return existing;
        }
        writeExclusiveImmutable(epochPath, epoch, 'request accounting epoch', { directoryFd: rootDescriptor.fd });
        return validateEpoch(readCanonicalJson(epochPath, 'request accounting epoch'));
    } finally {
        closeDirectoryDescriptor(entriesDescriptor);
        closeDirectoryDescriptor(rootDescriptor);
        closeDirectoryDescriptor(parentDescriptor);
    }
}

function validateProviderQuotaRecord(value) {
    assertExactKeys(
        value,
        [
            'raw_headers',
            'reported_used',
            'reported_remaining',
            'reported_last_cost',
            'expected_request_cost_credits',
            'reconciliation_status',
        ],
        'provider quota reconciliation record'
    );
    assertPlainObject(value.raw_headers, 'provider quota raw_headers');
    for (const [key, rawValue] of Object.entries(value.raw_headers)) {
        if (!PROVIDER_QUOTA_HEADER_PATTERN.test(key) || typeof rawValue !== 'string' || rawValue.includes('\n') || rawValue.includes('\r')) {
            fail('INVALID_PROVIDER_QUOTA_HEADERS', 'provider quota raw header evidence is invalid');
        }
    }
    for (const header of REQUIRED_QUOTA_HEADERS) {
        if (!Object.prototype.hasOwnProperty.call(value.raw_headers, header)) {
            fail('INVALID_PROVIDER_QUOTA_HEADERS', `provider quota header ${header} is missing`);
        }
        if (!/^\d+$/.test(value.raw_headers[header])) {
            fail('INVALID_PROVIDER_QUOTA_HEADERS', `provider quota header ${header} must be a non-negative integer`);
        }
    }
    for (const field of ['reported_used', 'reported_remaining', 'reported_last_cost', 'expected_request_cost_credits']) {
        assertNonNegativeInteger(value[field], `provider quota ${field}`);
    }
    if (value.reported_used !== Number(value.raw_headers['x-requests-used'])) {
        fail('INVALID_PROVIDER_QUOTA_HEADERS', 'provider reported used value does not bind to raw header evidence');
    }
    if (value.reported_remaining !== Number(value.raw_headers['x-requests-remaining'])) {
        fail('INVALID_PROVIDER_QUOTA_HEADERS', 'provider reported remaining value does not bind to raw header evidence');
    }
    if (value.reported_last_cost !== Number(value.raw_headers['x-requests-last'])) {
        fail('INVALID_PROVIDER_QUOTA_HEADERS', 'provider reported last cost does not bind to raw header evidence');
    }
    if (value.reconciliation_status !== 'RECONCILED') fail('INVALID_PROVIDER_QUOTA_HEADERS', 'provider quota reconciliation status is invalid');
    return Object.freeze({
        ...value,
        raw_headers: Object.freeze({ ...value.raw_headers }),
    });
}

function validateRequestRecord(record) {
    assertExactKeys(
        record,
        [
            'request_id',
            'run_id',
            'provider',
            'market_scope',
            'created_at',
            'transmission_state',
            'transmitted_at',
            'response_received_at',
            'terminal_state',
            'quota_units_charged_or_assumed',
            'receipt_evidence_reference',
            'error_classification',
            'provider_quota',
        ],
        'request ledger record'
    );
    assertToken(record.request_id, 'request_id');
    assertToken(record.run_id, 'run_id');
    if (record.provider !== PROVIDER || record.market_scope !== MARKET_SCOPE) fail('INVALID_REQUEST', 'provider or market scope is invalid');
    assertUtc(record.created_at, 'request created_at');
    if (!['TRANSMISSION_NOT_STARTED', 'TRANSMISSION_STARTED_OR_MAY_HAVE_STARTED'].includes(record.transmission_state)) {
        fail('INVALID_REQUEST', 'transmission_state is invalid');
    }
    assertUtc(record.transmitted_at, 'transmitted_at', true);
    assertUtc(record.response_received_at, 'response_received_at', true);
    if (record.terminal_state !== null && !TERMINAL_STATES.has(record.terminal_state)) fail('INVALID_REQUEST', 'terminal_state is invalid');
    assertNonNegativeInteger(record.quota_units_charged_or_assumed, 'quota_units_charged_or_assumed');
    for (const field of ['receipt_evidence_reference', 'error_classification']) {
        if (record[field] !== null && (typeof record[field] !== 'string' || !record[field].trim())) {
            fail('INVALID_REQUEST', `${field} is invalid`);
        }
    }
    if (record.provider_quota !== null) validateProviderQuotaRecord(record.provider_quota);
    return Object.freeze({ ...record, provider_quota: record.provider_quota === null ? null : validateProviderQuotaRecord(record.provider_quota) });
}

function intentRecord({ requestId, runId, createdAt }) {
    return validateRequestRecord({
        request_id: requestId,
        run_id: runId,
        provider: PROVIDER,
        market_scope: MARKET_SCOPE,
        created_at: createdAt,
        transmission_state: 'TRANSMISSION_NOT_STARTED',
        transmitted_at: null,
        response_received_at: null,
        terminal_state: null,
        quota_units_charged_or_assumed: 0,
        receipt_evidence_reference: null,
        error_classification: null,
        provider_quota: null,
    });
}

// eslint-disable-next-line complexity -- every possible provider-spend state is intentionally enumerated.
function validateTransition(previous, eventType, record) {
    validateRequestRecord(record);
    if (!previous) {
        if (eventType !== 'REQUEST_INTENT' || record.transmission_state !== 'TRANSMISSION_NOT_STARTED' || record.terminal_state !== null) {
            fail('INVALID_LEDGER_TRANSITION', 'request ledger must begin with intent before transmission');
        }
        return;
    }
    if (previous.terminal_state !== null) fail('INVALID_LEDGER_TRANSITION', 'terminal request ledger record cannot transition');
    for (const field of ['request_id', 'run_id', 'provider', 'market_scope', 'created_at']) {
        if (previous[field] !== record[field]) fail('INVALID_LEDGER_TRANSITION', `${field} cannot change across ledger transitions`);
    }
    if (eventType === 'TRANSMISSION_STARTED_OR_MAY_HAVE_STARTED') {
        if (
            previous.transmission_state !== 'TRANSMISSION_NOT_STARTED' ||
            record.transmission_state !== 'TRANSMISSION_STARTED_OR_MAY_HAVE_STARTED' ||
            record.transmitted_at === null ||
            record.terminal_state !== null ||
            record.quota_units_charged_or_assumed < 1 ||
            record.provider_quota !== null
        ) fail('INVALID_LEDGER_TRANSITION', 'transmission start must durably consume quota before transport');
        if (Date.parse(record.transmitted_at) < Date.parse(previous.created_at)) {
            fail('INVALID_LEDGER_TRANSITION', 'transmission cannot precede request intent');
        }
        return;
    }
    if (!['RESPONSE_RECEIVED', 'HTTP_FAILURE_AFTER_TRANSMISSION', 'TRANSPORT_FAILURE_AFTER_POSSIBLE_TRANSMISSION'].includes(eventType)) {
        if (eventType === 'CANCELLED_BEFORE_TRANSMISSION' && previous.transmission_state === 'TRANSMISSION_NOT_STARTED' && record.transmission_state === 'TRANSMISSION_NOT_STARTED' && record.terminal_state === eventType && record.quota_units_charged_or_assumed === 0) return;
        fail('INVALID_LEDGER_TRANSITION', 'ledger event is not a permitted request transition');
    }
    if (
        previous.transmission_state !== 'TRANSMISSION_STARTED_OR_MAY_HAVE_STARTED' ||
        record.transmission_state !== 'TRANSMISSION_STARTED_OR_MAY_HAVE_STARTED' ||
        record.terminal_state !== eventType ||
        record.quota_units_charged_or_assumed < 1
    ) fail('INVALID_LEDGER_TRANSITION', 'post-transmission outcome must remain consumed');
    if (eventType === 'RESPONSE_RECEIVED' && record.response_received_at === null) {
        fail('INVALID_LEDGER_TRANSITION', 'response terminal state requires response_received_at');
    }
    if (eventType === 'RESPONSE_RECEIVED' && record.provider_quota === null) {
        fail('PROVIDER_QUOTA_RECONCILIATION_REQUIRED', 'successful provider responses require quota header reconciliation');
    }
    if (record.response_received_at !== null && Date.parse(record.response_received_at) < Date.parse(previous.transmitted_at)) {
        fail('INVALID_LEDGER_TRANSITION', 'response cannot precede transmission');
    }
}

function validateEntry(value, { expectedSequence, previousHash, requests }) {
    assertExactKeys(value, ['schema_version', 'sequence', 'event_id', 'recorded_at', 'previous_entry_hash', 'event_type', 'request', 'entry_hash'], 'request ledger entry');
    if (value.schema_version !== LEDGER_SCHEMA_VERSION) fail('INVALID_LEDGER', 'request ledger schema is invalid');
    if (value.sequence !== expectedSequence) fail('INVALID_LEDGER', 'request ledger sequence is invalid');
    assertToken(value.event_id, 'event_id');
    assertUtc(value.recorded_at, 'recorded_at');
    if (value.previous_entry_hash !== previousHash) fail('TAMPERED_LEDGER', 'request ledger hash chain is broken');
    if (!EVENT_TYPES.has(value.event_type)) fail('INVALID_LEDGER', 'request ledger event type is invalid');
    const previous = requests.get(value.request?.request_id);
    if (value.event_type === 'REQUEST_INTENT' && previous) fail('DUPLICATE_REQUEST_ID', 'duplicate request_id is rejected');
    if (value.event_type !== 'REQUEST_INTENT' && !previous) fail('INVALID_LEDGER_TRANSITION', 'request transition has no intent');
    validateTransition(previous, value.event_type, value.request);
    const unsigned = { ...value };
    delete unsigned.entry_hash;
    if (value.entry_hash !== sha256Text(stableStringify(unsigned))) fail('TAMPERED_LEDGER', 'request ledger entry hash is invalid');
    requests.set(value.request.request_id, validateRequestRecord(value.request));
    return Object.freeze({ ...value, request: Object.freeze({ ...value.request }) });
}

function readRequestLedger({ ledgerRoot, expectedRootIdentity = null } = {}) {
    if (typeof ledgerRoot !== 'string' || !ledgerRoot.trim()) fail('INVALID_LEDGER', 'ledgerRoot is required');
    const rootDescriptor = openTrustedDirectoryDescriptor(path.resolve(ledgerRoot), 'request ledger root', expectedRootIdentity);
    const root = rootDescriptor.path;
    let entriesDescriptor;
    try {
        entriesDescriptor = openChildDirectoryDescriptor(rootDescriptor.fd, ENTRY_DIRECTORY, 'request ledger entries directory');
        const epoch = validateEpoch(readCanonicalJson(scopedPath(rootDescriptor.fd, EPOCH_FILE), 'request accounting epoch'));
        const names = fs.readdirSync(path.join(DIRECTORY_FD_ROOT, String(entriesDescriptor.fd))).sort();
        if (names.some(name => !/^\d{12}\.json$/.test(name))) fail('INVALID_LEDGER', 'request ledger entry filename is invalid');
        const requests = new Map();
        const entries = [];
        let previousHash = epoch.genesis_entry_hash;
        for (const [index, name] of names.entries()) {
            const entry = validateEntry(readCanonicalJson(scopedPath(entriesDescriptor.fd, name), `request ledger entry ${name}`), {
                expectedSequence: index + 1,
                previousHash,
                requests,
            });
            if (name !== `${String(entry.sequence).padStart(12, '0')}.json`) fail('INVALID_LEDGER', 'request ledger filename does not bind sequence');
            previousHash = entry.entry_hash;
            entries.push(entry);
        }
        return Object.freeze({
            root,
            root_identity: rootDescriptor.identity,
            entries_root: path.join(root, ENTRY_DIRECTORY),
            entries_identity: entriesDescriptor.identity,
            epoch,
            entries: Object.freeze(entries),
            requests: Object.freeze([...requests.values()].sort((left, right) => left.request_id.localeCompare(right.request_id))),
            last_entry_hash: previousHash,
        });
    } finally {
        closeDirectoryDescriptor(entriesDescriptor);
        closeDirectoryDescriptor(rootDescriptor);
    }
}

function validateRunLockGeneration(value) {
    assertExactKeys(value, [
        'schema_version',
        'operation_root',
        'operation_identity',
        'ledger_root',
        'ledger_identity',
        'epoch_id',
        'epoch_genesis_hash',
        'entry_count',
        'last_entry_hash',
        'generation_hash',
    ], 'Stage D ledger generation anchor');
    if (value.schema_version !== RUN_LOCK_GENERATION_SCHEMA_VERSION) fail('INVALID_LEDGER_GENERATION', 'ledger generation schema is invalid');
    if (typeof value.operation_root !== 'string' || !path.isAbsolute(value.operation_root)) fail('INVALID_LEDGER_GENERATION', 'ledger generation operation_root is invalid');
    for (const identityField of ['operation_identity', 'ledger_identity']) {
        assertPlainObject(value[identityField], `ledger generation ${identityField}`);
        assertExactKeys(value[identityField], ['dev', 'ino', 'mode', 'uid', 'gid'], `ledger generation ${identityField}`);
        for (const field of ['dev', 'ino', 'mode', 'uid', 'gid']) assertNonNegativeInteger(value[identityField][field], `ledger generation ${identityField}.${field}`);
    }
    if (typeof value.ledger_root !== 'string' || !path.isAbsolute(value.ledger_root)) fail('INVALID_LEDGER_GENERATION', 'ledger generation ledger_root is invalid');
    assertToken(value.epoch_id, 'ledger generation epoch_id');
    if (!/^[a-f0-9]{64}$/.test(value.epoch_genesis_hash || '') || !/^[a-f0-9]{64}$/.test(value.last_entry_hash || '')) {
        fail('INVALID_LEDGER_GENERATION', 'ledger generation hashes are invalid');
    }
    assertNonNegativeInteger(value.entry_count, 'ledger generation entry_count');
    const unsigned = { ...value };
    delete unsigned.generation_hash;
    if (value.generation_hash !== sha256Text(stableStringify(unsigned))) fail('TAMPERED_LEDGER_GENERATION', 'ledger generation hash is invalid');
    return Object.freeze({
        ...value,
        operation_identity: Object.freeze({ ...value.operation_identity }),
        ledger_identity: Object.freeze({ ...value.ledger_identity }),
    });
}

function buildRunLockGeneration({ operationRoot, operationIdentity, ledgerRoot, ledgerIdentity, ledger } = {}) {
    const root = path.resolve(operationRoot);
    const resolvedLedgerRoot = path.resolve(ledgerRoot);
    assertPlainObject(operationIdentity, 'ledger generation operation identity');
    assertPlainObject(ledgerIdentity, 'ledger generation ledger identity');
    assertPlainObject(ledger, 'ledger generation ledger');
    const entryCount = ledger.entries.length;
    const lastEntryHash = entryCount === 0 ? ledger.epoch.genesis_entry_hash : ledger.last_entry_hash;
    const unsigned = {
        schema_version: RUN_LOCK_GENERATION_SCHEMA_VERSION,
        operation_root: root,
        operation_identity: { ...operationIdentity },
        ledger_root: resolvedLedgerRoot,
        ledger_identity: { ...ledgerIdentity },
        epoch_id: ledger.epoch.epoch_id,
        epoch_genesis_hash: ledger.epoch.genesis_entry_hash,
        entry_count: entryCount,
        last_entry_hash: lastEntryHash,
    };
    return validateRunLockGeneration({ ...unsigned, generation_hash: sha256Text(stableStringify(unsigned)) });
}

function readRunLockGenerations(token) {
    const prefix = `${RUN_LOCK_GENERATION_FILE_PREFIX}${sha256Text(token.root)}-`;
    const names = fs.readdirSync(directoryFdPath(token.trust_directory_fd)).filter(name => name.startsWith(prefix));
    const generations = [];
    for (const name of names) {
        if (!/^\d{12}\.json$/.test(name.slice(prefix.length))) {
            fail('INVALID_LEDGER_GENERATION', 'ledger generation anchor filename is invalid');
        }
        const generation = validateRunLockGeneration(readCanonicalJson(scopedPath(token.trust_directory_fd, name), 'Stage D ledger generation anchor'));
        if (name !== runLockGenerationFile(token.root, generation.entry_count)) fail('INVALID_LEDGER_GENERATION', 'ledger generation anchor filename does not bind entry_count');
        generations.push(generation);
    }
    return generations.sort((left, right) => left.entry_count - right.entry_count);
}

function assertRunLockGenerationMatchesLedger(generation, ledger, { operationRoot, operationIdentity, ledgerRoot, ledgerIdentity } = {}) {
    if (generation.operation_root !== path.resolve(operationRoot) || !sameDirectoryIdentity(generation.operation_identity, operationIdentity)) fail('LEDGER_GENERATION_CHANGED', 'Stage D operation root identity changed since the last cycle');
    if (generation.ledger_root !== path.resolve(ledgerRoot) || !sameDirectoryIdentity(generation.ledger_identity, ledgerIdentity)) fail('LEDGER_GENERATION_CHANGED', 'request ledger root identity changed since the last Stage D cycle');
    if (generation.epoch_id !== ledger.epoch.epoch_id || generation.epoch_genesis_hash !== ledger.epoch.genesis_entry_hash) {
        fail('LEDGER_GENERATION_CHANGED', 'request accounting epoch changed since the last Stage D cycle');
    }
    if (generation.entry_count > ledger.entries.length) fail('LEDGER_GENERATION_ROLLBACK', 'request ledger lost entries since the last Stage D cycle');
    const observed = generation.entry_count === 0
        ? ledger.epoch.genesis_entry_hash
        : ledger.entries[generation.entry_count - 1]?.entry_hash;
    if (observed !== generation.last_entry_hash) fail('LEDGER_GENERATION_ROLLBACK', 'request ledger history no longer contains the anchored last entry');
}

function bindStageDRunLockGeneration(token, { ledgerRoot = token?.root } = {}) {
    if (!activeLockTokens.has(token)) fail('INVALID_LOCK_TOKEN', 'an active Stage D run lock token is required');
    if (typeof ledgerRoot !== 'string' || !ledgerRoot.trim()) fail('LEDGER_GENERATION_CHANGED', 'request ledger root is required');
    const resolvedLedgerRoot = path.resolve(ledgerRoot);
    const ledger = readRequestLedger({ ledgerRoot: resolvedLedgerRoot });
    const generations = readRunLockGenerations(token);
    const latest = generations.at(-1);
    if (latest) {
        assertRunLockGenerationMatchesLedger(latest, ledger, {
            operationRoot: token.root,
            operationIdentity: token.root_identity,
            ledgerRoot: resolvedLedgerRoot,
            ledgerIdentity: ledger.root_identity,
        });
    }
    const current = buildRunLockGeneration({
        operationRoot: token.root,
        operationIdentity: token.root_identity,
        ledgerRoot: resolvedLedgerRoot,
        ledgerIdentity: ledger.root_identity,
        ledger,
    });
    if (!latest || current.entry_count > latest.entry_count) {
        writeExclusiveImmutable(
            scopedPath(token.trust_directory_fd, runLockGenerationFile(token.root, current.entry_count)),
            current,
            'Stage D ledger generation anchor',
            { directoryFd: token.trust_directory_fd, mode: 0o400 },
        );
    } else if (current.last_entry_hash !== latest.last_entry_hash) {
        fail('LEDGER_GENERATION_CHANGED', 'request ledger generation hash changed without an append-only extension');
    }
    return current;
}

function appendRequestEvent({ ledgerRoot, expectedRootIdentity = null, eventType, request, recordedAt, eventId } = {}) {
    const ledger = readRequestLedger({ ledgerRoot, expectedRootIdentity });
    const rootDescriptor = openTrustedDirectoryDescriptor(ledger.root, 'request ledger root', expectedRootIdentity || ledger.root_identity);
    let entriesDescriptor;
    try {
        entriesDescriptor = openChildDirectoryDescriptor(rootDescriptor.fd, ENTRY_DIRECTORY, 'request ledger entries directory', ledger.entries_identity);
        const sequence = ledger.entries.length + 1;
        const entry = {
            schema_version: LEDGER_SCHEMA_VERSION,
            sequence,
            event_id: eventId || `rle_${crypto.randomUUID()}`,
            recorded_at: recordedAt,
            previous_entry_hash: ledger.last_entry_hash,
            event_type: eventType,
            request,
        };
        validateEntry({ ...entry, entry_hash: sha256Text(stableStringify(entry)) }, {
            expectedSequence: sequence,
            previousHash: ledger.last_entry_hash,
            requests: new Map(ledger.requests.map(row => [row.request_id, row])),
        });
        const name = `${String(sequence).padStart(12, '0')}.json`;
        writeExclusiveImmutable(scopedPath(entriesDescriptor.fd, name), { ...entry, entry_hash: sha256Text(stableStringify(entry)) }, 'request ledger entry', { directoryFd: entriesDescriptor.fd });
    } catch (error) {
        if (error?.code === 'EEXIST') fail('LEDGER_CONCURRENCY_AMBIGUOUS', 'request ledger changed concurrently; reconciliation is required');
        throw error;
    } finally {
        closeDirectoryDescriptor(entriesDescriptor);
        closeDirectoryDescriptor(rootDescriptor);
    }
    return readRequestLedger({ ledgerRoot, expectedRootIdentity: expectedRootIdentity || ledger.root_identity });
}

function latestRequest(ledger, requestId) {
    const request = ledger.requests.find(row => row.request_id === requestId);
    if (!request) fail('UNKNOWN_REQUEST_ID', 'request_id is absent from ledger');
    return request;
}

function recordRequestIntent({ ledgerRoot, expectedRootIdentity = null, requestId, runId, createdAt, recordedAt = createdAt }) {
    return appendRequestEvent({ ledgerRoot, expectedRootIdentity, eventType: 'REQUEST_INTENT', request: intentRecord({ requestId, runId, createdAt }), recordedAt });
}

function markTransmissionStarted({ ledgerRoot, expectedRootIdentity = null, requestId, transmittedAt, recordedAt = transmittedAt }) {
    const ledger = readRequestLedger({ ledgerRoot, expectedRootIdentity });
    const previous = latestRequest(ledger, requestId);
    return appendRequestEvent({
        ledgerRoot,
        expectedRootIdentity,
        eventType: 'TRANSMISSION_STARTED_OR_MAY_HAVE_STARTED',
        recordedAt,
        request: { ...previous, transmission_state: 'TRANSMISSION_STARTED_OR_MAY_HAVE_STARTED', transmitted_at: transmittedAt, quota_units_charged_or_assumed: 1 },
    });
}

function markRequestTerminal({ ledgerRoot, expectedRootIdentity = null, requestId, terminalState, at, receiptEvidenceReference = null, errorClassification = null, providerQuota = null, recordedAt = at }) {
    if (!TERMINAL_STATES.has(terminalState)) fail('INVALID_REQUEST', 'terminalState is invalid');
    const ledger = readRequestLedger({ ledgerRoot, expectedRootIdentity });
    const previous = latestRequest(ledger, requestId);
    const request = {
        ...previous,
        terminal_state: terminalState,
        ...(['RESPONSE_RECEIVED', 'HTTP_FAILURE_AFTER_TRANSMISSION'].includes(terminalState) ? { response_received_at: at } : {}),
        receipt_evidence_reference: receiptEvidenceReference,
        error_classification: errorClassification,
        provider_quota: providerQuota,
    };
    return appendRequestEvent({ ledgerRoot, expectedRootIdentity, eventType: terminalState, request, recordedAt });
}

function requestIsConsumed(request) {
    return request.transmission_state === 'TRANSMISSION_STARTED_OR_MAY_HAVE_STARTED';
}

function ledgerUsageSummary(ledger) {
    const consumed = ledger.requests.filter(requestIsConsumed);
    return Object.freeze({
        request_count: ledger.requests.length,
        consumed_request_count: consumed.length,
        cancelled_before_transmission_count: ledger.requests.filter(row => row.terminal_state === 'CANCELLED_BEFORE_TRANSMISSION').length,
        ambiguous_consumed_request_ids: consumed.filter(row => row.terminal_state === null).map(row => row.request_id).sort(),
    });
}

function validateRunLockFence(lock, label) {
    assertExactKeys(lock, ['schema_version', 'run_id', 'acquired_at', 'lock_hash'], label);
    if (lock.schema_version !== RUN_LOCK_SCHEMA_VERSION) fail('INVALID_LOCK', `${label} schema is invalid`);
    assertToken(lock.run_id, 'run_id');
    assertUtc(lock.acquired_at, `${label} acquired_at`);
    const unsigned = { ...lock };
    delete unsigned.lock_hash;
    if (lock.lock_hash !== sha256Text(stableStringify(unsigned))) fail('TAMPERED_LOCK', `${label} hash is invalid`);
    return Object.freeze(lock);
}

// eslint-disable-next-line complexity -- reconciliation checks the external trust fence, ancestor, parent and root independently.
function inspectStageDRunLock({ operationRoot, runLockTrustRoot } = {}) {
    const resolvedRoot = path.resolve(operationRoot);
    const trustRootPath = resolveRunLockTrustRoot(resolvedRoot, runLockTrustRoot);
    let trustDescriptor;
    let rootBundle;
    const lockPath = path.join(resolvedRoot, RUN_LOCK_FILE);
    const parentLockPath = path.join(path.dirname(resolvedRoot), runLockParentFile(resolvedRoot));
    const ancestorLockPath = path.join(path.dirname(path.dirname(resolvedRoot)), runLockAncestorFile(resolvedRoot));
    const trustLockPath = path.join(trustRootPath, runLockTrustFile(resolvedRoot));
    try {
        trustDescriptor = openTrustedRuntimeRoot(resolvedRoot, trustRootPath);
        rootBundle = openTrustedRootWithParent(resolvedRoot, 'Stage D operation root');
        const { ancestorDescriptor, parentDescriptor, rootDescriptor } = rootBundle;
        const root = rootDescriptor.path;
        const scopedTrustLockPath = scopedPath(trustDescriptor.fd, runLockTrustFile(resolvedRoot));
        // The external fence is checked first.  A replacement operation-root
        // parent cannot hide a run whose outcome is still unresolved.
        if (fs.existsSync(scopedTrustLockPath)) {
            try {
                const trustLock = validateRunLockFence(readCanonicalJson(scopedTrustLockPath, 'Stage D runtime trust lock'), 'Stage D runtime trust lock');
                return Object.freeze({ state: 'ACTIVE_OR_STALE_REQUIRES_RECONCILIATION', lock_path: path.join(root, RUN_LOCK_FILE), parent_lock_path: path.join(parentDescriptor.path, runLockParentFile(resolvedRoot)), ancestor_lock_path: ancestorDescriptor ? path.join(ancestorDescriptor.path, runLockAncestorFile(resolvedRoot)) : null, trust_lock_path: trustLockPath, lock: trustLock });
            } catch (error) {
                return Object.freeze({ state: 'AMBIGUOUS_REQUIRES_RECONCILIATION', lock_path: path.join(root, RUN_LOCK_FILE), parent_lock_path: path.join(parentDescriptor.path, runLockParentFile(resolvedRoot)), ancestor_lock_path: ancestorDescriptor ? path.join(ancestorDescriptor.path, runLockAncestorFile(resolvedRoot)) : null, trust_lock_path: trustLockPath, error_code: error.code || 'INVALID_LOCK' });
            }
        }
        if (ancestorDescriptor) {
            const scopedAncestorLockPath = scopedPath(ancestorDescriptor.fd, runLockAncestorFile(resolvedRoot));
            if (fs.existsSync(scopedAncestorLockPath)) {
                try {
                    const ancestorLock = validateRunLockFence(readCanonicalJson(scopedAncestorLockPath, 'Stage D ancestor run lock'), 'Stage D ancestor run lock');
                    return Object.freeze({ state: 'ACTIVE_OR_STALE_REQUIRES_RECONCILIATION', lock_path: path.join(root, RUN_LOCK_FILE), parent_lock_path: path.join(parentDescriptor.path, runLockParentFile(resolvedRoot)), ancestor_lock_path: ancestorDescriptor ? path.join(ancestorDescriptor.path, runLockAncestorFile(resolvedRoot)) : null, trust_lock_path: trustLockPath, lock: ancestorLock });
                } catch (error) {
                    return Object.freeze({ state: 'AMBIGUOUS_REQUIRES_RECONCILIATION', lock_path: lockPath, parent_lock_path: parentLockPath, ancestor_lock_path: ancestorLockPath, trust_lock_path: trustLockPath, error_code: error.code || 'INVALID_LOCK' });
                }
            }
        }
        const scopedParentLockPath = scopedPath(parentDescriptor.fd, runLockParentFile(resolvedRoot));
        if (fs.existsSync(scopedParentLockPath)) {
            try {
                const parentLock = validateRunLockFence(readCanonicalJson(scopedParentLockPath, 'Stage D parent run lock'), 'Stage D parent run lock');
                return Object.freeze({ state: 'ACTIVE_OR_STALE_REQUIRES_RECONCILIATION', lock_path: path.join(root, RUN_LOCK_FILE), parent_lock_path: path.join(parentDescriptor.path, runLockParentFile(resolvedRoot)), ancestor_lock_path: ancestorDescriptor ? path.join(ancestorDescriptor.path, runLockAncestorFile(resolvedRoot)) : null, trust_lock_path: trustLockPath, lock: parentLock });
            } catch (error) {
                return Object.freeze({ state: 'AMBIGUOUS_REQUIRES_RECONCILIATION', lock_path: lockPath, parent_lock_path: parentLockPath, ancestor_lock_path: ancestorLockPath, trust_lock_path: trustLockPath, error_code: error.code || 'INVALID_LOCK' });
            }
        }
        const scopedLockPath = scopedPath(rootDescriptor.fd, RUN_LOCK_FILE);
        if (!fs.existsSync(scopedLockPath)) return Object.freeze({ state: 'ABSENT', lock_path: path.join(root, RUN_LOCK_FILE), parent_lock_path: path.join(parentDescriptor.path, runLockParentFile(resolvedRoot)), ancestor_lock_path: ancestorDescriptor ? path.join(ancestorDescriptor.path, runLockAncestorFile(resolvedRoot)) : null, trust_lock_path: trustLockPath });
        const lock = validateRunLockFence(readCanonicalJson(scopedLockPath, 'Stage D run lock'), 'Stage D run lock');
        return Object.freeze({ state: 'ACTIVE_OR_STALE_REQUIRES_RECONCILIATION', lock_path: path.join(root, RUN_LOCK_FILE), parent_lock_path: path.join(parentDescriptor.path, runLockParentFile(resolvedRoot)), ancestor_lock_path: ancestorDescriptor ? path.join(ancestorDescriptor.path, runLockAncestorFile(resolvedRoot)) : null, trust_lock_path: trustLockPath, lock });
    } catch (error) {
        return Object.freeze({ state: 'AMBIGUOUS_REQUIRES_RECONCILIATION', lock_path: lockPath, parent_lock_path: parentLockPath, ancestor_lock_path: ancestorLockPath, trust_lock_path: trustLockPath, error_code: error.code || 'INVALID_LOCK' });
    } finally {
        closeDirectoryDescriptor(rootBundle?.rootDescriptor);
        closeDirectoryDescriptor(rootBundle?.parentDescriptor);
        closeDirectoryDescriptor(rootBundle?.ancestorDescriptor);
        closeDirectoryDescriptor(trustDescriptor);
    }
}

// eslint-disable-next-line complexity -- lock acquisition enumerates trust/ancestor/parent/root reconciliation states.
function acquireStageDRunLock({ operationRoot, runId, acquiredAt, runLockTrustRoot } = {}) {
    const root = path.resolve(operationRoot);
    assertToken(runId, 'run_id');
    assertUtc(acquiredAt, 'lock acquiredAt');
    const lockPath = path.join(root, RUN_LOCK_FILE);
    const parentLockPath = path.join(path.dirname(root), runLockParentFile(root));
    const ancestorLockPath = path.join(path.dirname(path.dirname(root)), runLockAncestorFile(root));
    const trustRootPath = resolveRunLockTrustRoot(root, runLockTrustRoot);
    const trustLockPath = path.join(trustRootPath, runLockTrustFile(root));
    const unsigned = { schema_version: RUN_LOCK_SCHEMA_VERSION, run_id: runId, acquired_at: acquiredAt };
    const lock = { ...unsigned, lock_hash: sha256Text(stableStringify(unsigned)) };
    const trustDescriptor = openTrustedRuntimeRoot(root, trustRootPath);
    let rootBundle;
    try {
        rootBundle = openTrustedRootWithParent(root, 'Stage D operation root');
    } catch (error) {
        closeDirectoryDescriptor(trustDescriptor);
        throw error;
    }
    const { ancestorDescriptor, parentDescriptor, rootDescriptor: directoryDescriptor } = rootBundle;
    if (!ancestorDescriptor) {
        closeDirectoryDescriptor(parentDescriptor);
        closeDirectoryDescriptor(directoryDescriptor);
        closeDirectoryDescriptor(trustDescriptor);
        fail('UNSAFE_PATH', 'Stage D operation root requires a non-root ancestor for reconciliation fencing');
    }
    let trustLockCreated = false;
    let ancestorLockCreated = false;
    let parentLockCreated = false;
    let lockCreated = false;
    try {
        try {
            writeExclusiveImmutable(scopedPath(trustDescriptor.fd, runLockTrustFile(root)), lock, 'Stage D runtime trust lock', { directoryFd: trustDescriptor.fd });
            trustLockCreated = true;
        } catch (error) {
            if (error?.code === 'EEXIST') {
                let current;
                try {
                    current = { state: 'ACTIVE_OR_STALE_REQUIRES_RECONCILIATION', lock: validateRunLockFence(readCanonicalJson(scopedPath(trustDescriptor.fd, runLockTrustFile(root)), 'Stage D runtime trust lock'), 'Stage D runtime trust lock') };
                } catch (readError) {
                    current = { state: 'AMBIGUOUS_REQUIRES_RECONCILIATION', error_code: readError.code || 'INVALID_LOCK' };
                }
                if (current.state === 'ACTIVE_OR_STALE_REQUIRES_RECONCILIATION') fail('STAGE_D_RUN_ACTIVE_OR_STALE', 'a prior Stage D runtime trust fence exists; reconciliation is required before another provider request');
                fail('AMBIGUOUS_RUN_LOCK', 'Stage D runtime trust fence is ambiguous; reconciliation is required before another provider request');
            }
            throw error;
        }
        try {
            writeExclusiveImmutable(scopedPath(ancestorDescriptor.fd, runLockAncestorFile(root)), lock, 'Stage D ancestor run lock', { directoryFd: ancestorDescriptor.fd });
            ancestorLockCreated = true;
        } catch (error) {
            if (error?.code === 'EEXIST') {
                let current;
                try {
                    const existing = readCanonicalJson(scopedPath(ancestorDescriptor.fd, runLockAncestorFile(root)), 'Stage D ancestor run lock');
                    assertExactKeys(existing, ['schema_version', 'run_id', 'acquired_at', 'lock_hash'], 'Stage D ancestor run lock');
                    const unsignedExisting = { ...existing };
                    delete unsignedExisting.lock_hash;
                    if (existing.lock_hash !== sha256Text(stableStringify(unsignedExisting))) fail('TAMPERED_LOCK', 'Stage D ancestor run lock hash is invalid');
                    current = { state: 'ACTIVE_OR_STALE_REQUIRES_RECONCILIATION' };
                } catch (readError) {
                    current = { state: 'AMBIGUOUS_REQUIRES_RECONCILIATION', error_code: readError.code || 'INVALID_LOCK' };
                }
                fs.unlinkSync(scopedPath(trustDescriptor.fd, runLockTrustFile(root)));
                fsyncDirectoryFd(trustDescriptor.fd);
                trustLockCreated = false;
                if (current.state === 'ACTIVE_OR_STALE_REQUIRES_RECONCILIATION') fail('STAGE_D_RUN_ACTIVE_OR_STALE', 'a prior Stage D run lock exists; reconciliation is required before another provider request');
                fail('AMBIGUOUS_RUN_LOCK', 'Stage D ancestor run lock is ambiguous; reconciliation is required before another provider request');
            }
            throw error;
        }
        try {
            writeExclusiveImmutable(scopedPath(parentDescriptor.fd, runLockParentFile(root)), lock, 'Stage D parent run lock', { directoryFd: parentDescriptor.fd });
            parentLockCreated = true;
        } catch (error) {
            if (error?.code === 'EEXIST') {
                let current;
                try {
                    const existing = readCanonicalJson(scopedPath(parentDescriptor.fd, runLockParentFile(root)), 'Stage D parent run lock');
                    assertExactKeys(existing, ['schema_version', 'run_id', 'acquired_at', 'lock_hash'], 'Stage D parent run lock');
                    const unsignedExisting = { ...existing };
                    delete unsignedExisting.lock_hash;
                    if (existing.lock_hash !== sha256Text(stableStringify(unsignedExisting))) fail('TAMPERED_LOCK', 'Stage D parent run lock hash is invalid');
                    current = { state: 'ACTIVE_OR_STALE_REQUIRES_RECONCILIATION' };
                } catch (readError) {
                    current = { state: 'AMBIGUOUS_REQUIRES_RECONCILIATION', error_code: readError.code || 'INVALID_LOCK' };
                }
                fs.unlinkSync(scopedPath(ancestorDescriptor.fd, runLockAncestorFile(root)));
                fsyncDirectoryFd(ancestorDescriptor.fd);
                ancestorLockCreated = false;
                fs.unlinkSync(scopedPath(trustDescriptor.fd, runLockTrustFile(root)));
                fsyncDirectoryFd(trustDescriptor.fd);
                trustLockCreated = false;
                if (current.state === 'ACTIVE_OR_STALE_REQUIRES_RECONCILIATION') fail('STAGE_D_RUN_ACTIVE_OR_STALE', 'a prior Stage D run lock exists; reconciliation is required before another provider request');
                fail('AMBIGUOUS_RUN_LOCK', 'Stage D parent run lock is ambiguous; reconciliation is required before another provider request');
            }
            throw error;
        }
        try {
            writeExclusiveImmutable(scopedPath(directoryDescriptor.fd, RUN_LOCK_FILE), lock, 'Stage D run lock', { directoryFd: directoryDescriptor.fd });
        } catch (error) {
            if (error?.code !== 'EEXIST') throw error;
            // We own the parent sentinel, so remove it before reporting the
            // existing child lock.  A failed cleanup remains fail-closed.
            fs.unlinkSync(scopedPath(parentDescriptor.fd, runLockParentFile(root)));
            fsyncDirectoryFd(parentDescriptor.fd);
            parentLockCreated = false;
            fs.unlinkSync(scopedPath(ancestorDescriptor.fd, runLockAncestorFile(root)));
            fsyncDirectoryFd(ancestorDescriptor.fd);
            ancestorLockCreated = false;
            fs.unlinkSync(scopedPath(trustDescriptor.fd, runLockTrustFile(root)));
            fsyncDirectoryFd(trustDescriptor.fd);
            trustLockCreated = false;
            let current;
            try {
                const existing = readCanonicalJson(scopedPath(directoryDescriptor.fd, RUN_LOCK_FILE), 'Stage D run lock');
                assertExactKeys(existing, ['schema_version', 'run_id', 'acquired_at', 'lock_hash'], 'Stage D run lock');
                const unsignedExisting = { ...existing };
                delete unsignedExisting.lock_hash;
                if (existing.lock_hash !== sha256Text(stableStringify(unsignedExisting))) fail('TAMPERED_LOCK', 'Stage D run lock hash is invalid');
                current = { state: 'ACTIVE_OR_STALE_REQUIRES_RECONCILIATION' };
            } catch (readError) {
                current = { state: 'AMBIGUOUS_REQUIRES_RECONCILIATION', error_code: readError.code || 'INVALID_LOCK' };
            }
            if (current.state === 'ACTIVE_OR_STALE_REQUIRES_RECONCILIATION') fail('STAGE_D_RUN_ACTIVE_OR_STALE', 'a prior Stage D run lock exists; reconciliation is required before another provider request');
            fail('AMBIGUOUS_RUN_LOCK', 'Stage D run lock is ambiguous; reconciliation is required before another provider request');
        }
        lockCreated = true;
    } finally {
        if (!lockCreated) {
            if (parentLockCreated) {
                try {
                    fs.unlinkSync(scopedPath(parentDescriptor.fd, runLockParentFile(root)));
                    fsyncDirectoryFd(parentDescriptor.fd);
                } catch {
                    // Preserve the sentinel when cleanup is ambiguous.
                }
            }
            if (ancestorLockCreated) {
                try {
                    fs.unlinkSync(scopedPath(ancestorDescriptor.fd, runLockAncestorFile(root)));
                    fsyncDirectoryFd(ancestorDescriptor.fd);
                } catch {
                    // Preserve the ancestor sentinel when cleanup is ambiguous.
                }
            }
            if (trustLockCreated) {
                try {
                    fs.unlinkSync(scopedPath(trustDescriptor.fd, runLockTrustFile(root)));
                    fsyncDirectoryFd(trustDescriptor.fd);
                } catch {
                    // Preserve the external trust fence when cleanup is ambiguous.
                }
            }
            closeDirectoryDescriptor(directoryDescriptor);
            closeDirectoryDescriptor(parentDescriptor);
            closeDirectoryDescriptor(ancestorDescriptor);
            closeDirectoryDescriptor(trustDescriptor);
        }
    }
    let stat;
    let parentStat;
    let ancestorStat;
    let trustStat;
    try {
        stat = fs.lstatSync(scopedPath(directoryDescriptor.fd, RUN_LOCK_FILE));
        if (stat.isSymbolicLink() || !stat.isFile()) fail('UNSAFE_PATH', 'new Stage D run lock is unsafe');
        parentStat = fs.lstatSync(scopedPath(parentDescriptor.fd, runLockParentFile(root)));
        if (parentStat.isSymbolicLink() || !parentStat.isFile()) fail('UNSAFE_PATH', 'new Stage D parent run lock is unsafe');
        ancestorStat = fs.lstatSync(scopedPath(ancestorDescriptor.fd, runLockAncestorFile(root)));
        if (ancestorStat.isSymbolicLink() || !ancestorStat.isFile()) fail('UNSAFE_PATH', 'new Stage D ancestor run lock is unsafe');
        trustStat = fs.lstatSync(scopedPath(trustDescriptor.fd, runLockTrustFile(root)));
        if (trustStat.isSymbolicLink() || !trustStat.isFile()) fail('UNSAFE_PATH', 'new Stage D runtime trust lock is unsafe');
    } catch (error) {
        // The lock is intentionally left in place for reconciliation, but no
        // descriptor may leak when post-create validation cannot complete.
        closeDirectoryDescriptor(directoryDescriptor);
        closeDirectoryDescriptor(parentDescriptor);
        closeDirectoryDescriptor(ancestorDescriptor);
        closeDirectoryDescriptor(trustDescriptor);
        throw error;
    }
    const token = Object.freeze({
        root,
        lock_path: lockPath,
        parent_lock_path: parentLockPath,
        ancestor_lock_path: ancestorLockPath,
        trust_root: trustRootPath,
        trust_lock_path: trustLockPath,
        lock_hash: lock.lock_hash,
        run_id: runId,
        dev: stat.dev,
        ino: stat.ino,
        parent_dev: parentStat.dev,
        parent_ino: parentStat.ino,
        ancestor_dev: ancestorStat.dev,
        ancestor_ino: ancestorStat.ino,
        trust_dev: trustStat.dev,
        trust_ino: trustStat.ino,
        directory_fd: directoryDescriptor.fd,
        parent_directory_fd: parentDescriptor.fd,
        ancestor_directory_fd: ancestorDescriptor.fd,
        trust_directory_fd: trustDescriptor.fd,
        root_identity: directoryDescriptor.identity,
        parent_identity: parentDescriptor.identity,
        ancestor_identity: ancestorDescriptor.identity,
        trust_identity: trustDescriptor.identity,
    });
    activeLockTokens.add(token);
    return token;
}

// eslint-disable-next-line complexity -- release validates the external trust fence plus three immutable lock records.
function releaseStageDRunLock(token) {
    if (!activeLockTokens.has(token)) fail('INVALID_LOCK_TOKEN', 'an active Stage D run lock token is required');
    let released = false;
    let currentTrust;
    try {
        const trustStat = fs.fstatSync(token.trust_directory_fd);
        if (!trustStat.isDirectory() || !sameDirectoryIdentity(trustStat, token.trust_identity)) {
            fail('AMBIGUOUS_RUN_LOCK', 'Stage D runtime trust-root identity changed; manual reconciliation is required');
        }
        const rootStat = fs.fstatSync(token.directory_fd);
        if (!rootStat.isDirectory() || !sameDirectoryIdentity(rootStat, token.root_identity)) {
            fail('AMBIGUOUS_RUN_LOCK', 'Stage D run-lock directory identity changed; manual reconciliation is required');
        }
        const parentStat = fs.fstatSync(token.parent_directory_fd);
        if (!parentStat.isDirectory() || !sameDirectoryIdentity(parentStat, token.parent_identity)) {
            fail('AMBIGUOUS_RUN_LOCK', 'Stage D run-lock parent identity changed; manual reconciliation is required');
        }
        // A pinned descriptor alone is not enough for release: verify that the
        // public path still names the exact generation that acquired the lock.
        // Otherwise a post-transmission root swap could make us delete the
        // fence and let the replacement ledger re-enter.
        const currentAncestor = openDirectoryDescriptor(path.dirname(path.dirname(token.root)), 'Stage D operation ancestor', token.ancestor_identity);
        const currentParent = openChildDirectoryDescriptor(currentAncestor.fd, path.basename(path.dirname(token.root)), 'Stage D operation parent', token.parent_identity);
        try {
            const currentRoot = directoryIdentity(scopedPath(currentParent.fd, path.basename(token.root)), 'Stage D operation root');
            if (!sameDirectoryIdentity(currentRoot, token.root_identity)) fail('AMBIGUOUS_RUN_LOCK', 'Stage D operation root path generation changed; manual reconciliation is required');
        } finally {
            closeDirectoryDescriptor(currentParent);
            closeDirectoryDescriptor(currentAncestor);
        }
        currentTrust = openTrustedRuntimeRoot(token.root, token.trust_root, token.trust_identity);
        const lockPath = scopedPath(token.directory_fd, RUN_LOCK_FILE);
        const parentLockPath = scopedPath(token.parent_directory_fd, runLockParentFile(token.root));
        const ancestorLockPath = scopedPath(token.ancestor_directory_fd, runLockAncestorFile(token.root));
        const trustLockPath = scopedPath(token.trust_directory_fd, runLockTrustFile(token.root));
        const observed = readRegularFileBytes(lockPath, 'Stage D run lock');
        if (observed.stat.dev !== token.dev || observed.stat.ino !== token.ino) {
            fail('AMBIGUOUS_RUN_LOCK', 'Stage D run lock inode changed; manual reconciliation is required');
        }
        const lock = parseCanonicalJsonBytes(observed.bytes, 'Stage D run lock');
        if (lock.lock_hash !== token.lock_hash || lock.run_id !== token.run_id) {
            fail('AMBIGUOUS_RUN_LOCK', 'Stage D run lock ownership changed; manual reconciliation is required');
        }
        const observedParent = readRegularFileBytes(parentLockPath, 'Stage D parent run lock');
        if (observedParent.stat.dev !== token.parent_dev || observedParent.stat.ino !== token.parent_ino) {
            fail('AMBIGUOUS_RUN_LOCK', 'Stage D parent run lock inode changed; manual reconciliation is required');
        }
        const parentLock = parseCanonicalJsonBytes(observedParent.bytes, 'Stage D parent run lock');
        if (parentLock.lock_hash !== token.lock_hash || parentLock.run_id !== token.run_id) {
            fail('AMBIGUOUS_RUN_LOCK', 'Stage D parent run lock ownership changed; manual reconciliation is required');
        }
        const observedAncestor = readRegularFileBytes(ancestorLockPath, 'Stage D ancestor run lock');
        if (observedAncestor.stat.dev !== token.ancestor_dev || observedAncestor.stat.ino !== token.ancestor_ino) {
            fail('AMBIGUOUS_RUN_LOCK', 'Stage D ancestor run lock inode changed; manual reconciliation is required');
        }
        const ancestorLock = parseCanonicalJsonBytes(observedAncestor.bytes, 'Stage D ancestor run lock');
        if (ancestorLock.lock_hash !== token.lock_hash || ancestorLock.run_id !== token.run_id) {
            fail('AMBIGUOUS_RUN_LOCK', 'Stage D ancestor run lock ownership changed; manual reconciliation is required');
        }
        const observedTrust = readRegularFileBytes(trustLockPath, 'Stage D runtime trust lock');
        if (observedTrust.stat.dev !== token.trust_dev || observedTrust.stat.ino !== token.trust_ino) {
            fail('AMBIGUOUS_RUN_LOCK', 'Stage D runtime trust lock inode changed; manual reconciliation is required');
        }
        const trustLock = parseCanonicalJsonBytes(observedTrust.bytes, 'Stage D runtime trust lock');
        if (trustLock.lock_hash !== token.lock_hash || trustLock.run_id !== token.run_id) {
            fail('AMBIGUOUS_RUN_LOCK', 'Stage D runtime trust lock ownership changed; manual reconciliation is required');
        }
        // Re-open and revalidate immediately before the unlink.  The directory
        // descriptor keeps the operation scoped to the trusted root, while the
        // second identity check prevents a replacement lock from being removed
        // after the first check.  A mismatch leaves the lock for reconciliation.
        const finalObserved = readRegularFileBytes(lockPath, 'Stage D run lock');
        if (finalObserved.stat.dev !== token.dev || finalObserved.stat.ino !== token.ino || finalObserved.bytes !== observed.bytes) {
            fail('AMBIGUOUS_RUN_LOCK', 'Stage D run lock changed during release; manual reconciliation is required');
        }
        const finalParentObserved = readRegularFileBytes(parentLockPath, 'Stage D parent run lock');
        if (finalParentObserved.stat.dev !== token.parent_dev || finalParentObserved.stat.ino !== token.parent_ino || finalParentObserved.bytes !== observedParent.bytes) {
            fail('AMBIGUOUS_RUN_LOCK', 'Stage D parent run lock changed during release; manual reconciliation is required');
        }
        const finalAncestorObserved = readRegularFileBytes(ancestorLockPath, 'Stage D ancestor run lock');
        if (finalAncestorObserved.stat.dev !== token.ancestor_dev || finalAncestorObserved.stat.ino !== token.ancestor_ino || finalAncestorObserved.bytes !== observedAncestor.bytes) {
            fail('AMBIGUOUS_RUN_LOCK', 'Stage D ancestor run lock changed during release; manual reconciliation is required');
        }
        const finalTrustObserved = readRegularFileBytes(trustLockPath, 'Stage D runtime trust lock');
        if (finalTrustObserved.stat.dev !== token.trust_dev || finalTrustObserved.stat.ino !== token.trust_ino || finalTrustObserved.bytes !== observedTrust.bytes) {
            fail('AMBIGUOUS_RUN_LOCK', 'Stage D runtime trust lock changed during release; manual reconciliation is required');
        }
        fs.unlinkSync(lockPath);
        fsyncDirectoryFd(token.directory_fd);
        fs.unlinkSync(parentLockPath);
        fsyncDirectoryFd(token.parent_directory_fd);
        fs.unlinkSync(ancestorLockPath);
        fsyncDirectoryFd(token.ancestor_directory_fd);
        // The external fence is removed last.  If any earlier unlink fails,
        // it still prevents a replacement operation root from re-entering.
        fs.unlinkSync(trustLockPath);
        fsyncDirectoryFd(token.trust_directory_fd);
        // Do not inspect these paths after unlink. A next owner may create a
        // fresh generation immediately after the fence is removed; that is
        // not evidence that this release failed. The pinned directory
        // identities, pre-unlink record identities/content, successful
        // unlink and directory fsync define the release boundary. Any
        // unlink/fsync error remains ambiguous and leaves reconciliation
        // required.
        released = true;
        activeLockTokens.delete(token);
    } finally {
        if (!released) activeLockTokens.delete(token);
        fs.closeSync(token.directory_fd);
        fs.closeSync(token.parent_directory_fd);
        fs.closeSync(token.ancestor_directory_fd);
        fs.closeSync(token.trust_directory_fd);
        closeDirectoryDescriptor(currentTrust);
    }
}

// eslint-disable-next-line complexity -- quota config is deliberately fail-closed field by field.
function validateQuotaConfiguration(value, { now } = {}) {
    if (!value || typeof value !== 'object' || Array.isArray(value)) {
        fail('UNVERIFIED_QUOTA_CONFIGURATION', 'verified quota configuration is required before provider transmission');
    }
    assertExactKeys(
        value,
        [
            'schema_version',
            'provider',
            'subscription_tier',
            'quota_evidence_class',
            'quota_evidence_verified',
            'quota_evidence_source',
            'billing_period_id',
            'period_start_at',
            'period_end_at',
            'monthly_quota_limit',
            'reserved_safety_buffer',
            'automated_spend_limit',
            'max_requests_per_stage_d_run',
            'max_requests_per_day',
            'stop_before_quota_exhaustion_threshold',
            'configured_markets',
            'configured_regions',
            'market_count',
            'region_count',
            'expected_request_cost_credits',
            'max_provider_requests_per_cycle',
            'quota_reset_rule',
            'automatic_zero_on_calendar_change',
            'historical_pre_epoch_request_total',
            'historical_pre_epoch_exact_total',
            'post_epoch_usage_source',
        ],
        'Stage D quota configuration'
    );
    if (value.schema_version !== QUOTA_SCHEMA_VERSION || value.quota_evidence_verified !== true) {
        fail('UNVERIFIED_QUOTA_CONFIGURATION', 'verified quota configuration is required before provider transmission');
    }
    if (value.provider !== PROVIDER || value.subscription_tier !== SUBSCRIPTION_TIER) {
        fail('INVALID_QUOTA_CONFIGURATION', 'provider plan identity is invalid');
    }
    if (value.quota_evidence_class !== QUOTA_EVIDENCE_CLASS) fail('INVALID_QUOTA_CONFIGURATION', 'quota evidence class is invalid');
    if (typeof value.quota_evidence_source !== 'string' || !value.quota_evidence_source.trim()) fail('INVALID_QUOTA_CONFIGURATION', 'quota evidence source is required');
    if (!/^\d{4}-\d{2}$/.test(value.billing_period_id || '')) fail('INVALID_QUOTA_CONFIGURATION', 'billing period ID is invalid');
    assertUtc(value.period_start_at, 'period_start_at');
    assertUtc(value.period_end_at, 'period_end_at');
    if (Date.parse(value.period_start_at) >= Date.parse(value.period_end_at)) fail('INVALID_QUOTA_CONFIGURATION', 'quota period is invalid');
    for (const field of ['monthly_quota_limit', 'reserved_safety_buffer', 'automated_spend_limit', 'max_requests_per_stage_d_run', 'stop_before_quota_exhaustion_threshold', 'market_count', 'region_count', 'expected_request_cost_credits', 'max_provider_requests_per_cycle']) {
        assertNonNegativeInteger(value[field], field);
    }
    if (value.monthly_quota_limit < 1 || value.max_requests_per_stage_d_run < 1 || value.automated_spend_limit < 1) {
        fail('INVALID_QUOTA_CONFIGURATION', 'quota limit, automated spend limit and run cap must be positive');
    }
    if (value.max_requests_per_day !== null) {
        assertNonNegativeInteger(value.max_requests_per_day, 'max_requests_per_day');
        if (value.max_requests_per_day < 1) fail('INVALID_QUOTA_CONFIGURATION', 'daily request cap must be positive when configured');
    }
    if (value.automated_spend_limit > value.monthly_quota_limit - value.reserved_safety_buffer - value.stop_before_quota_exhaustion_threshold) {
        fail('INVALID_QUOTA_CONFIGURATION', 'automated spend limit would consume the configured safety reserve');
    }
    if (value.reserved_safety_buffer + value.stop_before_quota_exhaustion_threshold >= value.monthly_quota_limit) {
        fail('INVALID_QUOTA_CONFIGURATION', 'quota safety buffers exhaust the monthly quota');
    }
    if (!Array.isArray(value.configured_markets) || value.configured_markets.length !== STAGE_D_MARKET_COUNT || value.configured_markets.some((market, index) => market !== CONFIGURED_MARKETS[index])) {
        fail('INVALID_QUOTA_CONFIGURATION', 'configured markets do not bind to the Stage D request');
    }
    if (!Array.isArray(value.configured_regions) || value.configured_regions.length !== STAGE_D_REGION_COUNT || value.configured_regions.some((region, index) => region !== CONFIGURED_REGIONS[index])) {
        fail('INVALID_QUOTA_CONFIGURATION', 'configured regions do not bind to the Stage D request');
    }
    if (value.market_count !== STAGE_D_MARKET_COUNT || value.region_count !== STAGE_D_REGION_COUNT) {
        fail('INVALID_QUOTA_CONFIGURATION', 'configured market/region counts are invalid');
    }
    if (value.expected_request_cost_credits !== value.market_count * value.region_count) {
        fail('INVALID_QUOTA_CONFIGURATION', 'expected request cost does not equal market count times region count');
    }
    if (value.max_provider_requests_per_cycle !== MAX_PROVIDER_REQUESTS_PER_CYCLE || value.max_requests_per_stage_d_run !== MAX_PROVIDER_REQUESTS_PER_CYCLE) {
        fail('INVALID_QUOTA_CONFIGURATION', 'provider request cycle cap is invalid');
    }
    if (value.quota_reset_rule !== QUOTA_RESET_RULE || value.automatic_zero_on_calendar_change !== LOCAL_LEDGER_AUTOMATIC_ZERO_ON_CALENDAR_CHANGE) {
        fail('INVALID_QUOTA_CONFIGURATION', 'quota reset uncertainty policy is invalid');
    }
    if (value.historical_pre_epoch_request_total !== HISTORICAL_PRE_EPOCH_REQUEST_TOTAL || value.historical_pre_epoch_exact_total !== HISTORICAL_PRE_EPOCH_EXACT_TOTAL) {
        fail('INVALID_QUOTA_CONFIGURATION', 'historical pre-epoch uncertainty must be preserved');
    }
    if (value.post_epoch_usage_source !== 'read_from_durable_request_ledger') fail('INVALID_QUOTA_CONFIGURATION', 'post-epoch usage source is invalid');
    if (now && (Date.parse(now) < Date.parse(value.period_start_at) || Date.parse(now) >= Date.parse(value.period_end_at))) {
        fail('INVALID_QUOTA_CONFIGURATION', 'current time is outside the locally governed quota period');
    }
    return Object.freeze({
        ...value,
        configured_markets: Object.freeze([...value.configured_markets]),
        configured_regions: Object.freeze([...value.configured_regions]),
    });
}

function createStageDTestQuotaConfiguration(value, { now } = {}) {
    if (process.env.NODE_ENV !== 'test') fail('UNVERIFIED_QUOTA_CONFIGURATION', 'test quota configuration is unavailable outside NODE_ENV=test');
    const normalized = validateQuotaConfiguration(value, { now });
    approvedQuotaConfigs.add(normalized);
    return normalized;
}

function assertApprovedQuotaConfiguration(value, { now } = {}) {
    if (!approvedQuotaConfigs.has(value)) fail('UNVERIFIED_QUOTA_CONFIGURATION', 'verified quota configuration must come from the trusted Stage D bootstrap');
    return validateQuotaConfiguration(value, { now });
}

// eslint-disable-next-line complexity -- local budget admission enumerates every ambiguous ledger state.
function assertBudgetLedgerValid(ledger, config) {
    if (!ledger || !ledger.epoch || !Array.isArray(ledger.requests)) fail('REQUEST_ACCOUNTING_AMBIGUOUS', 'durable request ledger is unavailable');
    validateEpoch(ledger.epoch);
    const periodStart = Date.parse(config.period_start_at);
    const periodEnd = Date.parse(config.period_end_at);
    const epochStarted = Date.parse(ledger.epoch.started_at);
    if (epochStarted < periodStart || epochStarted >= periodEnd) fail('REQUEST_ACCOUNTING_AMBIGUOUS', 'request accounting epoch is outside the locally governed budget period');
    const summary = ledgerUsageSummary(ledger);
    if (summary.ambiguous_consumed_request_ids.length) fail('REQUEST_ACCOUNTING_AMBIGUOUS', 'ambiguous consumed request state requires reconciliation');
    for (const request of ledger.requests) {
        if (Date.parse(request.created_at) < epochStarted) fail('REQUEST_ACCOUNTING_AMBIGUOUS', 'request predates the sealed accounting epoch');
        if (request.transmitted_at !== null) {
            const transmittedAt = Date.parse(request.transmitted_at);
            if (transmittedAt < epochStarted || transmittedAt < periodStart || transmittedAt >= periodEnd) {
                fail('REQUEST_ACCOUNTING_AMBIGUOUS', 'request transmission is outside the sealed local accounting period');
            }
        }
        if (request.terminal_state === 'RESPONSE_RECEIVED' && request.provider_quota === null) {
            fail('PROVIDER_QUOTA_RECONCILIATION_REQUIRED', 'a successful response has no reconciled provider quota evidence');
        }
        if (request.error_classification?.startsWith('PROVIDER_QUOTA_')) {
            fail('PROVIDER_QUOTA_RECONCILIATION_REQUIRED', 'prior provider quota divergence requires explicit reconciliation');
        }
    }
    return summary;
}

function assertRequestBudget({ ledger, quotaConfig, runId, now, requestedUnits = 1 }) {
    const config = validateQuotaConfiguration(quotaConfig, { now });
    assertToken(runId, 'run_id');
    assertUtc(now, 'budget now');
    assertNonNegativeInteger(requestedUnits, 'requestedUnits');
    if (requestedUnits !== config.expected_request_cost_credits || requestedUnits > config.max_requests_per_stage_d_run) {
        fail('REQUEST_BUDGET_DENIED', 'expected provider request cost is not bounded by the cycle contract');
    }
    assertBudgetLedgerValid(ledger, config);
    const timestamped = ledger.requests.filter(request => requestIsConsumed(request) && request.transmitted_at !== null);
    const monthly = timestamped.filter(request => Date.parse(request.transmitted_at) >= Date.parse(config.period_start_at) && Date.parse(request.transmitted_at) < Date.parse(config.period_end_at));
    const day = now.slice(0, 10);
    const daily = timestamped.filter(request => request.transmitted_at.slice(0, 10) === day);
    const thisRun = monthly.filter(request => request.run_id === runId);
    const monthlyUsed = monthly.reduce((sum, request) => sum + request.quota_units_charged_or_assumed, 0);
    const dailyUsed = daily.reduce((sum, request) => sum + request.quota_units_charged_or_assumed, 0);
    const runUsed = thisRun.reduce((sum, request) => sum + request.quota_units_charged_or_assumed, 0);
    if (monthlyUsed + requestedUnits > config.automated_spend_limit) {
        fail('REQUEST_BUDGET_DENIED', 'monthly budget would cross the configured automated spend limit');
    }
    if (runUsed + requestedUnits > config.max_requests_per_stage_d_run) fail('REQUEST_BUDGET_DENIED', 'run request budget is exhausted');
    if (config.max_requests_per_day !== null && dailyUsed + requestedUnits > config.max_requests_per_day) {
        fail('REQUEST_BUDGET_DENIED', 'daily request budget is exhausted');
    }
    return Object.freeze({
        allowed: true,
        billing_period_id: config.billing_period_id,
        monthly_used: monthlyUsed,
        monthly_remaining_after_request: config.monthly_quota_limit - monthlyUsed - requestedUnits,
        automated_spend_limit: config.automated_spend_limit,
        expected_request_cost_credits: config.expected_request_cost_credits,
        daily_used: dailyUsed,
        run_used: runUsed,
    });
}

function latestReconciledProviderQuota(ledger) {
    return ledger.requests
        .filter(request => request.provider_quota?.reconciliation_status === 'RECONCILED')
        .sort((left, right) => Date.parse(left.response_received_at || left.transmitted_at) - Date.parse(right.response_received_at || right.transmitted_at))
        .at(-1)?.provider_quota || null;
}

function reconcileProviderQuotaHeaders({ headers, quotaConfig, expectedRequestCostCredits, localConsumedAfterRequest, previousProviderQuota = null } = {}) {
    const config = validateQuotaConfiguration(quotaConfig);
    assertNonNegativeInteger(expectedRequestCostCredits, 'expectedRequestCostCredits');
    assertNonNegativeInteger(localConsumedAfterRequest, 'localConsumedAfterRequest');
    if (expectedRequestCostCredits !== config.expected_request_cost_credits) fail('PROVIDER_QUOTA_RECONCILIATION_FAILED', 'provider request cost does not match the governed cost model');
    const rawHeaders = sanitizeProviderHeaders(headers);
    for (const header of REQUIRED_QUOTA_HEADERS) {
        if (!Object.prototype.hasOwnProperty.call(rawHeaders, header) || !/^\d+$/.test(rawHeaders[header])) {
            fail('PROVIDER_QUOTA_RECONCILIATION_FAILED', `provider quota header ${header} is missing or malformed`);
        }
    }
    const reportedUsed = Number(rawHeaders['x-requests-used']);
    const reportedRemaining = Number(rawHeaders['x-requests-remaining']);
    const reportedLastCost = Number(rawHeaders['x-requests-last']);
    if (reportedUsed + reportedRemaining !== config.monthly_quota_limit) {
        fail('PROVIDER_QUOTA_RECONCILIATION_FAILED', 'provider used and remaining headers do not reconcile to the configured plan limit');
    }
    if (reportedLastCost !== expectedRequestCostCredits) {
        fail('PROVIDER_QUOTA_RECONCILIATION_FAILED', 'provider x-requests-last does not match the expected request cost');
    }
    if (reportedUsed < localConsumedAfterRequest) {
        fail('PROVIDER_QUOTA_RECONCILIATION_FAILED', 'provider used balance is lower than local consumed accounting');
    }
    const localSafeRemaining = config.automated_spend_limit - localConsumedAfterRequest;
    if (reportedRemaining < localSafeRemaining) {
        fail('PROVIDER_QUOTA_RECONCILIATION_FAILED', 'provider remaining balance is below the local safe budget expectation');
    }
    if (previousProviderQuota) {
        if (reportedUsed !== previousProviderQuota.reported_used + expectedRequestCostCredits || reportedRemaining !== previousProviderQuota.reported_remaining - expectedRequestCostCredits) {
            fail('PROVIDER_QUOTA_RECONCILIATION_FAILED', 'provider quota headers diverge from the prior reconciled response');
        }
    }
    return validateProviderQuotaRecord({
        raw_headers: rawHeaders,
        reported_used: reportedUsed,
        reported_remaining: reportedRemaining,
        reported_last_cost: reportedLastCost,
        expected_request_cost_credits: expectedRequestCostCredits,
        reconciliation_status: 'RECONCILED',
    });
}

function ensureEvidenceChildDirectory(rootDescriptor, name, label) {
    try {
        return openChildDirectoryDescriptor(rootDescriptor.fd, name, label);
    } catch (error) {
        if (error?.code !== 'ENOENT') throw error;
        fs.mkdirSync(scopedPath(rootDescriptor.fd, name), { mode: 0o700 });
        fsyncDirectoryFd(rootDescriptor.fd);
        return openChildDirectoryDescriptor(rootDescriptor.fd, name, label);
    }
}

function withEvidenceDirectories(persistor, callback) {
    const rootDescriptor = openTrustedDirectoryDescriptor(persistor.root, 'Stage D evidence root', persistor.root_identity);
    let rawDescriptor;
    let receiptDescriptor;
    try {
        rawDescriptor = openChildDirectoryDescriptor(rootDescriptor.fd, 'raw', 'Stage D RAW root', persistor.raw_identity);
        receiptDescriptor = openChildDirectoryDescriptor(rootDescriptor.fd, 'receipts', 'Stage D receipt root', persistor.receipt_identity);
        return callback({ rootDescriptor, rawDescriptor, receiptDescriptor });
    } finally {
        closeDirectoryDescriptor(receiptDescriptor);
        closeDirectoryDescriptor(rawDescriptor);
        closeDirectoryDescriptor(rootDescriptor);
    }
}

function createStageDEvidencePersistence({ evidenceRoot, testHooks = null } = {}) {
    if (typeof evidenceRoot !== 'string' || !evidenceRoot.trim()) fail('INVALID_EVIDENCE_ROOT', 'evidenceRoot is required');
    if (testHooks !== null && process.env.NODE_ENV !== 'test') fail('INVALID_EVIDENCE_PERSISTENCE', 'test hooks are test-only');
    let testFault = null;
    let testFaultAuthorityRoot = null;
    if (testHooks !== null) {
        assertPlainObject(testHooks, 'testHooks');
        if (testHooks.fault === 'RAW_ROOT_SWAP') assertExactKeys(testHooks, ['fault'], 'testHooks');
        else if (testHooks.fault === 'AUTHORITY_ROOT_SWAP_BEFORE_RECEIPT') {
            assertExactKeys(testHooks, ['fault', 'authorityRoot'], 'testHooks');
            if (typeof testHooks.authorityRoot !== 'string' || !testHooks.authorityRoot.trim()) fail('INVALID_EVIDENCE_PERSISTENCE', 'authorityRoot is required for the declarative test fault');
            testFaultAuthorityRoot = path.resolve(testHooks.authorityRoot);
        } else {
            fail('INVALID_EVIDENCE_PERSISTENCE', 'testHooks.fault must be a supported declarative fault descriptor');
        }
        testFault = testHooks.fault;
    }
    const root = path.resolve(evidenceRoot);
    const rootDescriptor = openTrustedDirectoryDescriptor(root, 'Stage D evidence root');
    let rawDescriptor;
    let receiptDescriptor;
    let testFaultApplied = false;
    const applyTestFault = fault => {
        if (testFault !== fault || testFaultApplied) return;
        if (fault === 'RAW_ROOT_SWAP') {
            const moved = `${root}.moved`;
            if (fs.existsSync(moved)) fail('INVALID_EVIDENCE_PERSISTENCE', 'declarative RAW root swap target already exists');
            fs.renameSync(root, moved);
            fs.mkdirSync(root, { mode: 0o700 });
        } else if (fault === 'AUTHORITY_ROOT_SWAP_BEFORE_RECEIPT') {
            const moved = `${testFaultAuthorityRoot}.moved`;
            if (fs.existsSync(moved)) fail('INVALID_EVIDENCE_PERSISTENCE', 'declarative authority root swap target already exists');
            fs.renameSync(testFaultAuthorityRoot, moved);
            fs.mkdirSync(testFaultAuthorityRoot, { mode: 0o700 });
        }
        testFaultApplied = true;
    };
    try {
        rawDescriptor = ensureEvidenceChildDirectory(rootDescriptor, 'raw', 'Stage D RAW root');
        receiptDescriptor = ensureEvidenceChildDirectory(rootDescriptor, 'receipts', 'Stage D receipt root');
        const persistor = {
            schema_version: 'footballprediction-stage-d-evidence-persistence/v1',
            root,
            root_identity: rootDescriptor.identity,
            raw_identity: rawDescriptor.identity,
            receipt_identity: receiptDescriptor.identity,
            persistRaw({ rawText } = {}) {
                if (typeof rawText !== 'string') fail('RAW_PERSISTENCE_FAILED', 'rawText is required');
                applyTestFault('RAW_ROOT_SWAP');
                const rawSha256 = sha256Text(rawText);
                const name = `${rawSha256}.json`;
                return withEvidenceDirectories(this, ({ rawDescriptor: currentRaw }) => {
                    const target = scopedPath(currentRaw.fd, name);
                    try {
                        const existing = readRegularFileBytes(target, 'Stage D RAW');
                        if (existing.bytes !== rawText) fail('RAW_HASH_COLLISION', 'Stage D RAW hash collision');
                    } catch (error) {
                        if (error?.code !== 'ENOENT') throw error;
                        writeExclusiveBytes(target, rawText, 'Stage D RAW', { directoryFd: currentRaw.fd, mode: 0o400 });
                    }
                    return Object.freeze({ raw_sha256: rawSha256, raw_evidence_reference: `raw/${name}` });
                });
            },
            persistReceipt({ receipt } = {}) {
                let validated;
                try {
                    validated = createCaptureReceipt(receipt);
                } catch (error) {
                    fail('RECEIPT_PERSISTENCE_FAILED', error.message);
                }
                applyTestFault('AUTHORITY_ROOT_SWAP_BEFORE_RECEIPT');
                const name = `${validated.capture_id}.json`;
                const bytes = `${stableStringify(validated)}\n`;
                return withEvidenceDirectories(this, ({ receiptDescriptor: currentReceipts }) => {
                    const target = scopedPath(currentReceipts.fd, name);
                    try {
                        const existing = readRegularFileBytes(target, 'Stage D receipt');
                        if (existing.bytes !== bytes) fail('RECEIPT_CONFLICT', 'Stage D receipt already exists with different content');
                    } catch (error) {
                        if (error?.code !== 'ENOENT') throw error;
                        writeExclusiveBytes(target, bytes, 'Stage D receipt', { directoryFd: currentReceipts.fd, mode: 0o400 });
                    }
                    const stableReceipt = readRegularFileBytes(target, 'Stage D receipt');
                    const receiptEvidence = loadVerifiedCaptureReceipt({ receiptPath: target, receiptBytes: stableReceipt.bytes, expectedIdentity: stableReceipt.stat });
                    return Object.freeze({
                        receipt: validated,
                        receipt_sha256: receiptEvidence.receipt_sha256,
                        receipt_evidence_reference: `receipts/${name}`,
                        receipt_evidence: receiptEvidence,
                    });
                });
            },
        };
        Object.freeze(persistor);
        approvedPersistors.add(persistor);
        return persistor;
    } finally {
        closeDirectoryDescriptor(receiptDescriptor);
        closeDirectoryDescriptor(rawDescriptor);
        closeDirectoryDescriptor(rootDescriptor);
    }
}

function assertTransportCallToken(token) {
    if (token !== STAGE_D_TRANSPORT_CALL_TOKEN) fail('TRANSPORT_CALL_FORBIDDEN', 'transport may only be called by the Stage D adapter');
}

function createStageDFakeTransport({ response = null, error = null } = {}) {
    if (process.env.NODE_ENV !== 'test') fail('INVALID_TRANSPORT', 'fake transport is test-only');
    if ((response === null) === (error === null)) fail('INVALID_TRANSPORT', 'fake transport requires exactly one static response or error');
    if (response !== null) {
        if (typeof response !== 'string') fail('INVALID_CONTRACT', 'fake transport response must be a serialized JSON fixture');
        let parsed;
        try { parsed = JSON.parse(response); } catch (error) { fail('INVALID_CONTRACT', `fake transport response JSON is invalid: ${error.message}`); }
        assertPlainObject(parsed, 'fake transport response');
        response = Object.freeze(clonePlainData(parsed, 'fake transport response'));
    }
    if (error !== null && !(error instanceof Error)) fail('INVALID_TRANSPORT', 'fake transport error must be an Error');
    let callCount = 0;
    const transport = {
        schema_version: 'footballprediction-stage-d-transport/v1',
        provider: PROVIDER,
        market_scope: MARKET_SCOPE,
        network_capability: 'none',
        async send(request, token) {
            assertTransportCallToken(token);
            callCount += 1;
            if (error !== null) throw error;
            return Object.freeze({
                ...response,
                request_started_at: response.request_started_at || request.transmission_started_at,
                capture_id: response.capture_id || request.request_id,
            });
        },
    };
    Object.defineProperty(transport, 'call_count', { enumerable: true, get: () => callCount });
    Object.freeze(transport);
    approvedTransports.add(transport);
    return transport;
}

function sanitizeProviderHeaders(headers = {}) {
    const allowed = PROVIDER_QUOTA_HEADER_PATTERN;
    return Object.fromEntries(Object.entries(headers).filter(([key]) => allowed.test(key)).map(([key, value]) => [key.toLowerCase(), String(value)]));
}

function createStageDOddsApiTransport({ apiKey = process.env.THE_ODDS_API_KEY, timeoutMs = 15000, proxyProvider = null, proxyPoolName = 'default' } = {}) {
    if (!Number.isInteger(timeoutMs) || timeoutMs <= 0) fail('INVALID_TRANSPORT', 'provider transport timeout must be positive');
    if (proxyProvider !== null && (!proxyProvider || typeof proxyProvider.acquire !== 'function' || typeof proxyProvider.release !== 'function')) {
        fail('INVALID_TRANSPORT', 'proxyProvider must expose acquire/release');
    }
    const transport = {
        schema_version: 'footballprediction-stage-d-transport/v1',
        provider: PROVIDER,
        market_scope: MARKET_SCOPE,
        network_capability: 'provider',
        explicit_binding: 'the-odds-api-stage-d-controlled-adapter/v1',
        preflight() {
            if (typeof apiKey !== 'string' || !apiKey.trim()) fail('CREDENTIAL_INVALID', 'The Odds API credential is unavailable');
        },
        send(request, token) {
            assertTransportCallToken(token);
            transport.preflight();
            const url = new URL('https://api.the-odds-api.com/v4/sports/soccer_epl/odds');
            url.search = new URLSearchParams({ apiKey, regions: CONFIGURED_REGIONS.join(','), markets: CONFIGURED_MARKETS.join(','), oddsFormat: 'decimal' }).toString();
            const requestStartedAt = request.transmission_started_at;
            const provider = proxyProvider || getProxyProvider({ poolName: proxyPoolName, disableHealthChecks: true });
            const healthInterval = provider?.config?.healthCheckIntervalMs;
            const healthTimer = provider?.healthTimer;
            if (provider.stage_d_health_probe_disabled !== true || healthInterval !== 0 || healthTimer) {
                fail('PROXY_HEALTH_PROBE_UNSAFE', 'Stage D provider transport requires a proxy provider with health probes disabled');
            }
            return Promise.resolve(provider.acquire({ consumer: 'stage-d-controlled-adapter', sticky: false })).then(lease => {
                if (!lease?.proxy?.server) fail('PROXY_LEASE_INVALID', 'ProxyProvider returned an invalid lease');
                const proxyUrl = lease.proxy.server;
                const agent = proxyUrl.startsWith('socks')
                    ? new SocksProxyAgent(proxyUrl, { timeout: timeoutMs })
                    : new HttpsProxyAgent(proxyUrl, { keepAlive: false, timeout: timeoutMs });
                const releaseLease = () => Promise.resolve(provider.release(lease)).catch(() => undefined);
                return new Promise((resolve, reject) => {
                    const finishFailure = error => {
                        Promise.resolve(provider.reportFailure?.(lease, { reason: error.message, failureClass: 'provider_transport' }))
                            .catch(() => undefined)
                            .finally(() => { void releaseLease(); reject(error); });
                    };
                    const req = https.request({
                        protocol: 'https:',
                        hostname: 'api.the-odds-api.com',
                        port: 443,
                        method: 'GET',
                        path: `${url.pathname}${url.search}`,
                        headers: { 'User-Agent': 'FootballPrediction-stage-d-adapter/1.0' },
                        rejectUnauthorized: true,
                        agent,
                    }, response => {
                        const chunks = [];
                        response.on('data', chunk => chunks.push(Buffer.from(chunk)));
                        response.on('end', () => {
                            const result = {
                                raw_text: Buffer.concat(chunks).toString('utf8'),
                                http_status: response.statusCode,
                                request_started_at: requestStartedAt,
                                response_received_at: new Date().toISOString(),
                                provider_quota: sanitizeProviderHeaders(response.headers),
                                capture_id: request.request_id,
                            };
                            Promise.resolve(provider.reportSuccess?.(lease, { statusCode: response.statusCode }))
                                .catch(() => undefined)
                                .finally(() => { void releaseLease(); resolve(result); });
                        });
                        response.on('error', finishFailure);
                    });
                    req.setTimeout(timeoutMs, () => req.destroy(new Error('The Odds API request timed out')));
                    req.on('error', finishFailure);
                    req.end();
                });
            });
        },
    };
    Object.freeze(transport);
    approvedTransports.add(transport);
    return transport;
}

function createReviewedCandidateBuilder(build) {
    if (typeof build !== 'function') fail('INVALID_CANDIDATE_BUILDER', 'candidate builder function is required');
    const builder = Object.freeze({
        schema_version: 'footballprediction-stage-d-candidate-builder/v1',
        build(input) { return build(Object.freeze({ ...input })); },
    });
    approvedCandidateBuilders.add(builder);
    return builder;
}

function createStageDCandidateBuilder({ errorCode = 'CANDIDATE_BUILDER_NOT_CONFIGURED', errorMessage = 'test candidate builder was invoked unexpectedly' } = {}) {
    if (process.env.NODE_ENV !== 'test') fail('INVALID_CANDIDATE_BUILDER', 'generic candidate builders are test-only');
    if (typeof errorCode !== 'string' || !/^[A-Z][A-Z0-9_]{2,63}$/.test(errorCode) || typeof errorMessage !== 'string' || !errorMessage.trim()) {
        fail('INVALID_CANDIDATE_BUILDER', 'test candidate builder failure descriptor is invalid');
    }
    const builder = Object.freeze({
        schema_version: 'footballprediction-stage-d-candidate-builder/v1',
        build() { fail(errorCode, errorMessage); },
    });
    approvedCandidateBuilders.add(builder);
    return builder;
}

function createStageDProspectiveCandidateBuilder({ universe, projectionVersion = '1', supportedMarketKeys = ['h2h'], authorizedSupersessions = [] } = {}) {
    if (!universe || typeof universe !== 'object') fail('INVALID_CANDIDATE_BUILDER', 'verified fixture universe is required');
    return createReviewedCandidateBuilder(({ authoritySnapshot, evidence }) => buildProspectiveMarketEvidenceTransaction({
        authoritySnapshot,
        universe,
        oddsRawText: evidence.raw_text,
        captureReceipt: evidence.receipt_evidence,
        projectionVersion,
        supportedMarketKeys,
        authorizedSupersessions,
    }));
}

function createStageDFakePublisher({ mode = 'RETURN', status = 'FAKE_NOT_CALLED', errorCode = 'FAKE_PUBLISH_FAILURE', errorMessage = 'test publisher failure', authorityRoot, allocationArtifactPath } = {}) {
    if (process.env.NODE_ENV !== 'test') fail('INVALID_PUBLISHER', 'fake publisher is test-only');
    if (!['RETURN', 'ERROR'].includes(mode) || typeof status !== 'string' || !status.trim() || typeof errorCode !== 'string' || !/^[A-Z][A-Z0-9_]{2,63}$/.test(errorCode) || typeof errorMessage !== 'string' || !errorMessage.trim()) {
        fail('INVALID_PUBLISHER', 'fake publisher behavior descriptor is invalid');
    }
    if (typeof authorityRoot !== 'string' || typeof allocationArtifactPath !== 'string') fail('INVALID_PUBLISHER', 'fake publisher roots are required');
    const resolvedAuthorityRoot = path.resolve(authorityRoot);
    let callCount = 0;
    const publisher = Object.freeze({
        schema_version: 'footballprediction-stage-d-publisher/v1',
        binding: 'fake-transaction-v1-test-publisher',
        authority_root: resolvedAuthorityRoot,
        authority_root_identity: trustedDirectoryIdentity(resolvedAuthorityRoot, 'fake publisher authority root'),
        allocation_artifact_path: path.resolve(allocationArtifactPath),
        get call_count() { return callCount; },
        async publish() {
            callCount += 1;
            if (mode === 'ERROR') fail(errorCode, errorMessage);
            return Object.freeze({ status });
        },
    });
    approvedPublishers.add(publisher);
    return publisher;
}

function createStageDTransactionPublisher({ storeRoot, allocationArtifactPath } = {}) {
    if (typeof storeRoot !== 'string' || typeof allocationArtifactPath !== 'string') fail('INVALID_PUBLISHER', 'transaction-v1 publisher roots are required');
    const resolvedStoreRoot = path.resolve(storeRoot);
    const authorityDescriptor = openTrustedDirectoryDescriptor(resolvedStoreRoot, 'transaction authority root');
    let stagingDescriptor;
    let committedDescriptor;
    try {
        stagingDescriptor = openChildDirectoryDescriptor(authorityDescriptor.fd, '.staging', 'transaction staging directory');
        committedDescriptor = openChildDirectoryDescriptor(authorityDescriptor.fd, 'committed', 'transaction committed directory');
    } finally {
        closeDirectoryDescriptor(committedDescriptor);
        closeDirectoryDescriptor(stagingDescriptor);
        closeDirectoryDescriptor(authorityDescriptor);
    }
    const publisher = {
        schema_version: 'footballprediction-stage-d-publisher/v1',
        binding: 'transaction-v1-atomic-publisher',
        authority_root: resolvedStoreRoot,
        authority_root_identity: authorityDescriptor.identity,
        staging_identity: stagingDescriptor.identity,
        committed_identity: committedDescriptor.identity,
        allocation_artifact_path: path.resolve(allocationArtifactPath),
        publish(candidate) {
            if (!isVerifiedProspectiveTransactionCandidate(candidate)) fail('UNVERIFIED_CANDIDATE', 'verified transaction-v1 candidate is required');
            const rootDescriptor = openTrustedDirectoryDescriptor(resolvedStoreRoot, 'transaction authority root', publisher.authority_root_identity);
            const pinnedRoot = directoryFdPath(rootDescriptor.fd);
            try {
                // The transaction-v1 publisher receives a pinned descriptor
                // path for every read, lock, stage write, rename and reopen.
                // It never re-resolves the mutable authority path during the
                // publication window.
                const result = publishProspectiveMarketEvidenceTransaction({
                    storeRoot: pinnedRoot,
                    allocationArtifactPath,
                    candidate,
                    expectedStagingIdentity: publisher.staging_identity,
                    expectedCommittedIdentity: publisher.committed_identity,
                });
                const afterIdentity = trustedDirectoryIdentity(resolvedStoreRoot, 'transaction authority root');
                if (!sameDirectoryIdentity(afterIdentity, publisher.authority_root_identity)) fail('DIRECTORY_IDENTITY_CHANGED', 'transaction authority root identity changed after publication');
                const afterCommittedIdentity = trustedDirectoryIdentity(path.join(resolvedStoreRoot, 'committed'), 'transaction committed directory');
                if (!sameDirectoryIdentity(afterCommittedIdentity, publisher.committed_identity)) fail('DIRECTORY_IDENTITY_CHANGED', 'transaction committed directory identity changed after publication');
                const fresh = openMarketEvidenceAuthoritySnapshot({ storeRoot: pinnedRoot, allocationArtifactPath, expectedRootIdentity: publisher.authority_root_identity, expectedCommittedIdentity: publisher.committed_identity });
                if (!isVerifiedMarketEvidenceAuthoritySnapshot(fresh) || fresh.head_transaction_id !== result.transaction_id || fresh.state_hash !== candidate.post_state_hash) {
                    fail('AUTHORITY_REOPEN_FAILED', 'published transaction did not reopen as the expected authority head');
                }
                // Do not report success based solely on a check performed
                // before the final reopen: the public generation must still
                // be the one captured by this publisher session.
                const finalIdentity = trustedDirectoryIdentity(resolvedStoreRoot, 'transaction authority root');
                if (!sameDirectoryIdentity(finalIdentity, publisher.authority_root_identity)) fail('DIRECTORY_IDENTITY_CHANGED', 'transaction authority root identity changed before publication result');
                return Object.freeze({ ...result, fresh_authority_snapshot: fresh });
            } finally {
                closeDirectoryDescriptor(rootDescriptor);
            }
        },
    };
    Object.freeze(publisher);
    approvedPublishers.add(publisher);
    return publisher;
}

function systemClock() {
    return new Date().toISOString();
}

function abandonStageDRunLock(token) {
    if (!activeLockTokens.has(token)) return;
    activeLockTokens.delete(token);
    fs.closeSync(token.directory_fd);
    fs.closeSync(token.parent_directory_fd);
    fs.closeSync(token.ancestor_directory_fd);
    fs.closeSync(token.trust_directory_fd);
}

function createStageDProductionRuntimeAuthorization() {
    // This function is intentionally private.  The caller receives only the
    // cycle result; the Symbol never crosses the binder boundary.
    return STAGE_D_RUNTIME_AUTHORIZATION;
}

// eslint-disable-next-line complexity -- the binder deliberately orders validation, consumption and shared-cycle admission.
async function executeStageDControlledInitialization(options = {}) {
    assertPlainObject(options, 'Stage D controlled initialization options');
    if (Object.prototype.hasOwnProperty.call(options, 'runtimeAuthorization')) fail('STAGE_D_RUNTIME_AUTHORIZATION_INPUT_FORBIDDEN', 'runtimeAuthorization is private and cannot be supplied to the production binder');
    const {
        authorizationArtifactPath,
        authorityRoot,
        allocationArtifactPath,
        ledgerRoot,
        quotaConfig,
        quotaConfigSha256,
        fixtureUniverseRawSha256,
        fixtureUniverse,
        evidenceRoot,
        runLockTrustRoot,
        transport,
        evidencePersistence,
        candidateBuilder,
        transactionPublisher,
        clock = systemClock,
    } = options;
    if (typeof authorityRoot !== 'string' || !authorityRoot.trim() || typeof allocationArtifactPath !== 'string' || !allocationArtifactPath.trim() || typeof ledgerRoot !== 'string' || !ledgerRoot.trim()) fail('STAGE_D_INPUT_INVALID', 'authorityRoot, allocationArtifactPath and ledgerRoot are required');
    if (typeof quotaConfigSha256 !== 'string' || !/^[a-f0-9]{64}$/.test(quotaConfigSha256)) fail('STAGE_D_INPUT_INVALID', 'quotaConfigSha256 is required');
    if (typeof fixtureUniverseRawSha256 !== 'string' || !/^[a-f0-9]{64}$/.test(fixtureUniverseRawSha256)) fail('STAGE_D_INPUT_INVALID', 'fixtureUniverseRawSha256 is required');
    if (typeof clock !== 'function') fail('TRUSTED_CLOCK_REQUIRED', 'clock must be callable');
    const now = clock();
    assertUtc(now, 'controlled authorization validation time');
    const authorizationRecord = readStageDControlledAuthorization({ authorizationArtifactPath, ledgerRoot, runLockTrustRoot });
    const authoritySnapshot = openMarketEvidenceAuthoritySnapshot({
        storeRoot: path.resolve(authorityRoot),
        allocationArtifactPath: path.resolve(allocationArtifactPath),
    });
    const ledger = readRequestLedger({ ledgerRoot: path.resolve(ledgerRoot) });
    const normalizedQuotaConfig = createStageDProductionQuotaConfiguration(quotaConfig, { now });
    const validatedAuthorization = validateStageDControlledAuthorization({
        authorization: authorizationRecord.authorization,
        authoritySnapshot,
        authorityRoot,
        allocationArtifactPath,
        ledger,
        quotaConfig: normalizedQuotaConfig,
        quotaConfigSha256,
        fixtureUniverseRawSha256,
        now,
    });
    const componentKeys = ['transport', 'evidencePersistence', 'candidateBuilder', 'transactionPublisher'];
    const hasComponentOverride = componentKeys.some(key => Object.prototype.hasOwnProperty.call(options, key));
    let boundTransport;
    let boundEvidencePersistence;
    let boundCandidateBuilder;
    let boundTransactionPublisher;
    if (process.env.NODE_ENV === 'test') {
        if (!componentKeys.every(key => Object.prototype.hasOwnProperty.call(options, key))) fail('STAGE_D_TEST_COMPONENTS_REQUIRED', 'networkless tests must supply every reviewed fake component explicitly');
        boundTransport = transport;
        boundEvidencePersistence = evidencePersistence;
        boundCandidateBuilder = candidateBuilder;
        boundTransactionPublisher = transactionPublisher;
    } else {
        if (hasComponentOverride) fail('STAGE_D_COMPONENT_OVERRIDE_FORBIDDEN', 'production binder components are fixed to reviewed factories');
        if (!fixtureUniverse || typeof fixtureUniverse !== 'object') fail('STAGE_D_INPUT_INVALID', 'verified fixture universe replay input is required');
        if (typeof evidenceRoot !== 'string' || !evidenceRoot.trim() || typeof runLockTrustRoot !== 'string' || !runLockTrustRoot.trim()) fail('STAGE_D_INPUT_INVALID', 'production evidenceRoot and runLockTrustRoot are required');
        boundTransport = createStageDOddsApiTransport();
        boundEvidencePersistence = createStageDEvidencePersistence({ evidenceRoot });
        boundCandidateBuilder = createStageDProspectiveCandidateBuilder({ universe: fixtureUniverse, supportedMarketKeys: CONFIGURED_MARKETS });
        boundTransactionPublisher = createStageDTransactionPublisher({ storeRoot: authorityRoot, allocationArtifactPath });
    }
    const consumed = consumeStageDControlledAuthorization({
        authorizationRecord: { ...authorizationRecord, ...validatedAuthorization },
        ledgerRoot,
        runLockTrustRoot,
        consumedAt: now,
    });
    const cycleResult = await executeStageDOneCycle({
        authorityRoot,
        allocationArtifactPath,
        ledgerRoot,
        quotaConfig: normalizedQuotaConfig,
        runId: validatedAuthorization.authorization.run_id,
        requestId: validatedAuthorization.authorization.request_id,
        runtimeAuthorization: createStageDProductionRuntimeAuthorization(),
        transport: boundTransport,
        evidencePersistence: boundEvidencePersistence,
        candidateBuilder: boundCandidateBuilder,
        transactionPublisher: boundTransactionPublisher,
        runLockTrustRoot,
        clock,
        expectedAuthorityPreState: {
            head_transaction_id: validatedAuthorization.authorization.authority_pre_head,
            state_hash: validatedAuthorization.authorization.authority_pre_state_hash,
            observation_count: validatedAuthorization.authorization.authority_pre_observation_count,
            store_sha256: validatedAuthorization.authorization.authority_pre_store_sha256,
            allocation_authority_sha256: validatedAuthorization.authorization.authority_pre_allocation_authority_sha256,
        },
    });
    const providerTransmissionAttempted = cycleResult.status !== 'CANCELLED_BEFORE_TRANSMISSION';
    return Object.freeze({
        ...cycleResult,
        authorization_audit: Object.freeze({
            schema_version: 'footballprediction-stage-d-controlled-initialization-audit/v1',
            authorization_id: validatedAuthorization.authorization.authorization_id,
            authorization_sha256: authorizationRecord.authorization_sha256,
            scope_sha256: validatedAuthorization.scope_sha256,
            consumed_marker: consumed.marker_name,
            mission: CONTROLLED_AUTHORIZATION_MISSION,
            provider: PROVIDER,
            market: CONFIGURED_MARKETS[0],
            region: CONFIGURED_REGIONS[0],
            max_provider_requests: MAX_PROVIDER_REQUESTS_PER_CYCLE,
            expected_request_cost_credits: EXPECTED_REQUEST_COST_CREDITS,
            accounting_epoch_id: validatedAuthorization.authorization.accounting_epoch_id,
            run_id: validatedAuthorization.authorization.run_id,
            request_id: validatedAuthorization.authorization.request_id,
            provider_transmission_attempted: providerTransmissionAttempted,
            terminal_result: cycleResult.status,
        }),
    });
}

// eslint-disable-next-line complexity -- the adapter deliberately enumerates each durable failure boundary.
async function executeStageDOneCycle({
    authorityRoot,
    allocationArtifactPath,
    ledgerRoot,
    quotaConfig,
    runId,
    requestId,
    runtimeAuthorization = null,
    transport,
    evidencePersistence,
    candidateBuilder,
    transactionPublisher,
    runLockTrustRoot,
    clock = systemClock,
    expectedAuthorityPreState = null,
} = {}) {
    if (runtimeAuthorization !== STAGE_D_RUNTIME_AUTHORIZATION
        && !(process.env.NODE_ENV === 'test' && runtimeAuthorization === STAGE_D_TEST_RUNTIME_AUTHORIZATION)) {
        fail('STAGE_D_NOT_AUTHORIZED', 'explicit Stage D runtime authorization is required');
    }
    if (!approvedTransports.has(transport) || !approvedPersistors.has(evidencePersistence) || !approvedCandidateBuilders.has(candidateBuilder) || !approvedPublishers.has(transactionPublisher)) {
        fail('STAGE_D_CONTROL_BOUNDARY_INVALID', 'transport, persistence, candidate builder and publisher must come from reviewed factories');
    }
    if (process.env.NODE_ENV === 'test' && transport.network_capability === 'provider') {
        fail('STAGE_D_PROVIDER_DISABLED_IN_TEST', 'provider transport is disabled in test processes; use the networkless fake transport');
    }
    if (transport.network_capability === 'provider' && transactionPublisher.binding !== 'transaction-v1-atomic-publisher') {
        fail('STAGE_D_CONTROL_BOUNDARY_INVALID', 'provider transport requires the transaction-v1 atomic publisher');
    }
    if (typeof ledgerRoot !== 'string' || !ledgerRoot.trim() || typeof authorityRoot !== 'string' || !authorityRoot.trim()) fail('STAGE_D_INPUT_INVALID', 'authorityRoot and ledgerRoot are required');
    assertToken(runId, 'run_id');
    assertToken(requestId, 'request_id');
    if (typeof clock !== 'function') fail('TRUSTED_CLOCK_REQUIRED', 'clock must be callable');
    const canonicalAuthorityRoot = path.resolve(authorityRoot);
    const canonicalAllocationArtifactPath = path.resolve(allocationArtifactPath || path.join(canonicalAuthorityRoot, 'allocation.authority.json'));
    const canonicalAuthorityRootIdentity = trustedDirectoryIdentity(canonicalAuthorityRoot, 'transaction authority root');
    if (transactionPublisher.authority_root !== canonicalAuthorityRoot || transactionPublisher.allocation_artifact_path !== canonicalAllocationArtifactPath) {
        fail('STAGE_D_CONTROL_BOUNDARY_INVALID', 'publisher authority root must bind to the cycle authority root');
    }
    if (!sameDirectoryIdentity(transactionPublisher.authority_root_identity, canonicalAuthorityRootIdentity)) {
        fail('STAGE_D_CONTROL_BOUNDARY_INVALID', 'publisher authority root identity must bind to the cycle authority root');
    }
    if (transport.network_capability === 'provider') assertApprovedQuotaConfiguration(quotaConfig);
    const trustedClock = transport.network_capability === 'provider' ? systemClock : clock;
    const acquiredAt = trustedClock();
    assertUtc(acquiredAt, 'run lock acquired_at');
    const token = acquireStageDRunLock({ operationRoot: ledgerRoot, runId, acquiredAt, runLockTrustRoot });
    let reconcileRequired = false;
    let intentPersisted = false;
    let authorityDescriptor;
    let finalizationError = null;
    let cycleResult;
    let cycleError = null;
    try {
        // eslint-disable-next-line complexity -- the inner cycle intentionally enumerates each durable boundary.
        cycleResult = await (async () => {
        try {
            bindStageDRunLockGeneration(token, { ledgerRoot });
        } catch (error) {
            reconcileRequired = true;
            throw error;
        }
        try {
            authorityDescriptor = openTrustedDirectoryDescriptor(canonicalAuthorityRoot, 'transaction authority root', canonicalAuthorityRootIdentity);
        } catch (error) {
            reconcileRequired = true;
            throw error;
        }
        const pinnedAuthorityRoot = directoryFdPath(authorityDescriptor.fd);
        const authoritySnapshotOptions = {
            storeRoot: pinnedAuthorityRoot,
            allocationArtifactPath: canonicalAllocationArtifactPath,
            expectedRootIdentity: authorityDescriptor.identity,
            ...(transactionPublisher.committed_identity ? { expectedCommittedIdentity: transactionPublisher.committed_identity } : {}),
        };
        const authoritySnapshot = openMarketEvidenceAuthoritySnapshot({
            ...authoritySnapshotOptions,
        });
        if (!isVerifiedMarketEvidenceAuthoritySnapshot(authoritySnapshot)) fail('AUTHORITY_NOT_READY', 'canonical Stage C authority is not verified');
        if (expectedAuthorityPreState !== null) {
            assertStageDAuthorityPreState({
                authoritySnapshot,
                authorityRoot: pinnedAuthorityRoot,
                allocationArtifactPath: canonicalAllocationArtifactPath,
                expected: expectedAuthorityPreState,
            });
        }
        const lockedLedgerRootIdentity = token.root_identity;
        let ledger;
        try {
            ledger = readRequestLedger({ ledgerRoot, expectedRootIdentity: lockedLedgerRootIdentity });
        } catch (error) {
            reconcileRequired = true;
            throw error;
        }
        if (ledger.requests.some(row => row.run_id === runId)) fail('DUPLICATE_RUN_ID', 'run_id has already been accounted and cannot be reused');
        const budgetNow = trustedClock();
        assertUtc(budgetNow, 'budget now');
        const budgetDecision = assertRequestBudget({ ledger, quotaConfig, runId, now: budgetNow, requestedUnits: EXPECTED_REQUEST_COST_CREDITS });
        try {
            // The descriptor pins the authority read, while this path check
            // prevents a replaced public root from becoming the authority
            // that a later publication or duplicate decision would claim.
            assertDirectoryIdentity(canonicalAuthorityRoot, canonicalAuthorityRootIdentity, 'transaction authority root');
        } catch (error) {
            reconcileRequired = true;
            throw error;
        }
        try {
            recordRequestIntent({ ledgerRoot, expectedRootIdentity: lockedLedgerRootIdentity, requestId, runId, createdAt: budgetNow, recordedAt: budgetNow });
            intentPersisted = true;
        } catch (error) {
            // The append may have committed before a subsequent read/identity
            // check failed.  Keep the run lock unreleased until reconciliation;
            // never assume a pre-transmission intent failure was clean.
            reconcileRequired = true;
            throw error;
        }
        if (transport.network_capability === 'provider' && typeof transport.preflight === 'function') {
            try {
                // Credential readiness is a local check and must precede the
                // transmission boundary; missing credentials cannot consume
                // provider quota.
                transport.preflight();
            } catch (error) {
                try {
                    markRequestTerminal({ ledgerRoot, expectedRootIdentity: lockedLedgerRootIdentity, requestId, terminalState: 'CANCELLED_BEFORE_TRANSMISSION', at: trustedClock(), errorClassification: error.code || 'CREDENTIAL_INVALID' });
                } catch (terminalError) {
                    reconcileRequired = true;
                    throw terminalError;
                }
                throw error;
            }
        }
        const transmissionStartedAt = trustedClock();
        assertUtc(transmissionStartedAt, 'transmission_started_at');
        try {
            markTransmissionStarted({ ledgerRoot, expectedRootIdentity: lockedLedgerRootIdentity, requestId, transmittedAt: transmissionStartedAt, recordedAt: transmissionStartedAt });
        } catch (error) {
            reconcileRequired = true;
            throw error;
        }
        let response;
        try {
            response = await transport.send(Object.freeze({ request_id: requestId, run_id: runId, provider: PROVIDER, market_scope: MARKET_SCOPE, transmission_started_at: transmissionStartedAt }), STAGE_D_TRANSPORT_CALL_TOKEN);
        } catch (error) {
            try {
                markRequestTerminal({ ledgerRoot, expectedRootIdentity: lockedLedgerRootIdentity, requestId, terminalState: 'TRANSPORT_FAILURE_AFTER_POSSIBLE_TRANSMISSION', at: trustedClock(), errorClassification: 'TRANSPORT_FAILURE_AFTER_POSSIBLE_TRANSMISSION' });
            } catch (terminalError) {
                reconcileRequired = true;
                throw terminalError;
            }
            throw error;
        }
        const terminalizePostBoundaryFailure = error => {
            try {
                markRequestTerminal({ ledgerRoot, expectedRootIdentity: lockedLedgerRootIdentity, requestId, terminalState: 'TRANSPORT_FAILURE_AFTER_POSSIBLE_TRANSMISSION', at: trustedClock(), errorClassification: error.code || 'POST_TRANSMISSION_FAILURE' });
            } catch (terminalError) {
                reconcileRequired = true;
                throw terminalError;
            }
            throw error;
        };
        let responseAt;
        try {
            assertPlainObject(response, 'provider transport response');
            if (!Number.isInteger(response.http_status) || response.http_status < 100 || response.http_status > 599) fail('TRANSPORT_RESPONSE_INVALID', 'provider HTTP status is invalid');
            responseAt = response.response_received_at || trustedClock();
            assertUtc(responseAt, 'response_received_at');
        } catch (error) {
            terminalizePostBoundaryFailure(error);
        }
        if (response.http_status < 200 || response.http_status >= 300) {
            try {
                markRequestTerminal({ ledgerRoot, expectedRootIdentity: lockedLedgerRootIdentity, requestId, terminalState: 'HTTP_FAILURE_AFTER_TRANSMISSION', at: responseAt, errorClassification: `HTTP_${response.http_status}` });
            } catch (error) {
                reconcileRequired = true;
                throw error;
            }
            return Object.freeze({ status: 'HTTP_FAILURE_AFTER_TRANSMISSION', request_id: requestId, run_id: runId });
        }
        if (typeof response.raw_text !== 'string') terminalizePostBoundaryFailure(Object.assign(new Error('successful response raw_text is required'), { code: 'RAW_PERSISTENCE_FAILED' }));
        let reconciledProviderQuota;
        try {
            reconciledProviderQuota = reconcileProviderQuotaHeaders({
                headers: response.provider_quota,
                quotaConfig,
                expectedRequestCostCredits: budgetDecision.expected_request_cost_credits,
                localConsumedAfterRequest: budgetDecision.monthly_used + budgetDecision.expected_request_cost_credits,
                previousProviderQuota: latestReconciledProviderQuota(ledger),
            });
        } catch (error) {
            terminalizePostBoundaryFailure(error);
        }
        let persistedRaw;
        let persistedReceipt;
        try {
            persistedRaw = evidencePersistence.persistRaw({ rawText: response.raw_text });
            const ingestedAt = trustedClock();
            const receipt = createCaptureReceipt({
                capture_id: response.capture_id || requestId,
                acquisition_mode: 'LIVE_CAPTURE',
                request_started_at: response.request_started_at || transmissionStartedAt,
                response_received_at: responseAt,
                ingested_at: ingestedAt,
                http_status: response.http_status,
                sanitized_request_parameters: { regions: 'uk', markets: 'h2h', oddsFormat: 'decimal' },
                response_size_bytes: Buffer.byteLength(response.raw_text),
                raw_sha256: persistedRaw.raw_sha256,
                raw_evidence_reference: persistedRaw.raw_evidence_reference,
                provider_quota: response.provider_quota || null,
                software_version: 'stage-d-live-adapter/1.0.0',
            });
            persistedReceipt = evidencePersistence.persistReceipt({ receipt });
        } catch (error) {
            try {
                markRequestTerminal({ ledgerRoot, expectedRootIdentity: lockedLedgerRootIdentity, requestId, terminalState: 'TRANSPORT_FAILURE_AFTER_POSSIBLE_TRANSMISSION', at: trustedClock(), errorClassification: 'RAW_OR_RECEIPT_PERSISTENCE_FAILURE_AFTER_TRANSMISSION' });
            } catch (terminalError) {
                reconcileRequired = true;
                throw terminalError;
            }
            throw error;
        }
        try {
            markRequestTerminal({ ledgerRoot, expectedRootIdentity: lockedLedgerRootIdentity, requestId, terminalState: 'RESPONSE_RECEIVED', at: responseAt, receiptEvidenceReference: persistedReceipt.receipt_evidence_reference, providerQuota: reconciledProviderQuota });
        } catch (error) {
            reconcileRequired = true;
            throw error;
        }
        const evidence = Object.freeze({ ...response, ...persistedRaw, ...persistedReceipt, raw_text: response.raw_text, response_received_at: responseAt });
        let freshAuthorityBeforePublication;
        try {
            freshAuthorityBeforePublication = openMarketEvidenceAuthoritySnapshot(authoritySnapshotOptions);
            assertDirectoryIdentity(canonicalAuthorityRoot, canonicalAuthorityRootIdentity, 'transaction authority root');
            if (!isVerifiedMarketEvidenceAuthoritySnapshot(freshAuthorityBeforePublication)) fail('AUTHORITY_REOPEN_FAILED', 'fresh authority reopen failed before duplicate classification');
        } catch (error) {
            reconcileRequired = true;
            throw error;
        }
        const duplicate = classifyDuplicateCapture({ authoritySnapshot: freshAuthorityBeforePublication, evidence });
        if (duplicate.duplicate) {
            let reopened;
            try {
                assertDirectoryIdentity(canonicalAuthorityRoot, canonicalAuthorityRootIdentity, 'transaction authority root');
                reopened = openMarketEvidenceAuthoritySnapshot(authoritySnapshotOptions);
                if (!isVerifiedMarketEvidenceAuthoritySnapshot(reopened)) fail('AUTHORITY_REOPEN_FAILED', 'duplicate capture authority reopen failed');
                // The descriptor held by the reopen pins the bytes, while this
                // final generation check prevents a replaced public path from
                // being reported as a successful no-op after the reopen.
                assertDirectoryIdentity(canonicalAuthorityRoot, canonicalAuthorityRootIdentity, 'transaction authority root');
            } catch (error) {
                reconcileRequired = true;
                throw error;
            }
            return Object.freeze({ status: duplicate.policy, request_id: requestId, run_id: runId, duplicate, fresh_authority_snapshot: reopened });
        }
        const candidate = await candidateBuilder.build({ authoritySnapshot: freshAuthorityBeforePublication, evidence });
        if (!isVerifiedProspectiveTransactionCandidate(candidate)) fail('UNVERIFIED_CANDIDATE', 'candidate builder did not return a verified transaction candidate');
        try {
            assertDirectoryIdentity(canonicalAuthorityRoot, canonicalAuthorityRootIdentity, 'transaction authority root');
            const publication = await transactionPublisher.publish(candidate);
            assertDirectoryIdentity(canonicalAuthorityRoot, canonicalAuthorityRootIdentity, 'transaction authority root');
            return Object.freeze({ status: 'PUBLISHED_TRANSACTION_V1', request_id: requestId, run_id: runId, publication });
        } catch (error) {
            reconcileRequired = true;
            throw error;
        }
        })();
    } catch (error) {
        cycleError = error;
    } finally {
        try {
            if (!reconcileRequired) {
                try {
                    bindStageDRunLockGeneration(token, { ledgerRoot });
                } catch (error) {
                    reconcileRequired = true;
                    finalizationError = error;
                }
            }
            if (reconcileRequired) abandonStageDRunLock(token);
            else releaseStageDRunLock(token);
        } finally {
            closeDirectoryDescriptor(authorityDescriptor);
        }
    }
    if (finalizationError) throw finalizationError;
    if (!intentPersisted && reconcileRequired) fail('REQUEST_INTENT_RECONCILIATION_REQUIRED', 'request intent outcome is ambiguous; manual reconciliation is required');
    if (cycleError) throw cycleError;
    return cycleResult;
}

function buildOfflineStageDRunPlan({ operationRoot, ledgerRoot, authoritySnapshot, quotaConfig = null, runId, now, runLockTrustRoot } = {}) {
    assertPlainObject(authoritySnapshot, 'authoritySnapshot');
    if (!/^tx_[a-f0-9]{64}$/.test(authoritySnapshot.head_transaction_id || '') || !/^[a-f0-9]{64}$/.test(authoritySnapshot.state_hash || '')) {
        fail('AUTHORITY_NOT_READY', 'canonical Stage C authority must reopen before a Stage D cycle is planned');
    }
    assertToken(runId, 'run_id');
    assertUtc(now, 'run now');
    const token = acquireStageDRunLock({ operationRoot, runId, acquiredAt: now, runLockTrustRoot });
    let reconcileRequired = false;
    try {
        try {
            bindStageDRunLockGeneration(token, { ledgerRoot });
        } catch (error) {
            reconcileRequired = true;
            throw error;
        }
        let ledger;
        let ledgerState;
        try {
            ledger = readRequestLedger({ ledgerRoot });
            ledgerState = { status: 'READY', epoch_id: ledger.epoch.epoch_id, usage: ledgerUsageSummary(ledger) };
        } catch (error) {
            ledgerState = { status: 'BLOCKED', code: error.code || 'REQUEST_LEDGER_UNAVAILABLE', message: error.message };
        }
        let budget;
        try {
            if (!ledger) fail('REQUEST_LEDGER_UNAVAILABLE', 'request ledger is unavailable');
            budget = assertRequestBudget({ ledger, quotaConfig, runId, now, requestedUnits: EXPECTED_REQUEST_COST_CREDITS });
        } catch (error) {
            budget = { allowed: false, code: error.code || 'REQUEST_BUDGET_DENIED', message: error.message };
        }
        return Object.freeze({
            schema_version: 'footballprediction-stage-d-offline-run-plan/v1',
            mode: 'OFFLINE_DRY_RUN',
            run_id: runId,
            scheduler_decision: 'EXTERNAL_SCHEDULER_DISABLED__ONE_CYCLE_ADMITTED_FOR_OFFLINE_PLANNING_ONLY',
            canonical_authority: {
                head_transaction_id: authoritySnapshot.head_transaction_id,
                state_hash: authoritySnapshot.state_hash,
                observation_count: authoritySnapshot.observations?.length ?? null,
            },
            run_lock: 'ACQUIRED_AND_CLEANLY_RELEASED',
            ledger: ledgerState,
            request_budget: budget,
            would_acquire: { provider: PROVIDER, market_scope: MARKET_SCOPE, transmission_permitted: false },
            would_publish: { authority: 'transaction-v1-only', canonical_authority_mutation_permitted: false },
            provider_requests: 0,
            canonical_authority_writes: 0,
        });
    } finally {
        if (reconcileRequired) abandonStageDRunLock(token);
        else releaseStageDRunLock(token);
    }
}

function classifyDuplicateCapture({ authoritySnapshot, evidence }) {
    assertPlainObject(authoritySnapshot, 'authoritySnapshot');
    assertPlainObject(evidence, 'acquisition evidence');
    if (!/^[a-f0-9]{64}$/.test(evidence.raw_sha256 || '')) fail('EVIDENCE_PERSISTENCE_REQUIRED', 'raw_sha256 is required for duplicate capture governance');
    const bindings = Array.isArray(authoritySnapshot.capture_bindings) ? authoritySnapshot.capture_bindings : [];
    const duplicate = bindings.find(binding => binding?.provider === PROVIDER && binding?.raw_sha256 === evidence.raw_sha256);
    return Object.freeze(duplicate
        ? { duplicate: true, policy: 'NO_OP_DUPLICATE_RAW_HASH', prior_capture_id: duplicate.capture_id }
        : { duplicate: false, policy: 'PUBLISH_TRANSACTION_V1' });
}

module.exports = {
    EPOCH_SCHEMA_VERSION,
    LEDGER_SCHEMA_VERSION,
    RUN_LOCK_SCHEMA_VERSION,
    RUN_LOCK_GENERATION_SCHEMA_VERSION,
    QUOTA_SCHEMA_VERSION,
    CONTROLLED_AUTHORIZATION_SCHEMA_VERSION,
    CONTROLLED_AUTHORIZATION_STATUS,
    CONTROLLED_AUTHORIZATION_MISSION,
    EPOCH_FILE,
    ENTRY_DIRECTORY,
    RUN_LOCK_FILE,
    runLockParentFile,
    runLockAncestorFile,
    runLockTrustFile,
    runLockGenerationFile,
    PROVIDER,
    SUBSCRIPTION_TIER,
    QUOTA_EVIDENCE_CLASS,
    QUOTA_RESET_RULE,
    LOCAL_LEDGER_AUTOMATIC_ZERO_ON_CALENDAR_CHANGE,
    CONFIGURED_MARKETS,
    CONFIGURED_REGIONS,
    STAGE_D_MARKET_COUNT,
    STAGE_D_REGION_COUNT,
    EXPECTED_REQUEST_COST_CREDITS,
    MAX_PROVIDER_REQUESTS_PER_CYCLE,
    REQUIRED_QUOTA_HEADERS,
    MARKET_SCOPE,
    HISTORICAL_PRE_EPOCH_REQUEST_TOTAL,
    HISTORICAL_PRE_EPOCH_EXACT_TOTAL,
    initializeRequestAccountingEpoch,
    readRequestLedger,
    recordRequestIntent,
    markTransmissionStarted,
    markRequestTerminal,
    ledgerUsageSummary,
    inspectStageDRunLock,
    acquireStageDRunLock,
    releaseStageDRunLock,
    bindStageDRunLockGeneration,
    validateQuotaConfiguration,
    validateProviderQuotaRecord,
    reconcileProviderQuotaHeaders,
    createStageDTestRuntimeAuthorization,
    createStageDTestQuotaConfiguration,
    assertRequestBudget,
    createStageDEvidencePersistence,
    createStageDFakeTransport,
    createStageDOddsApiTransport,
    createStageDCandidateBuilder,
    createStageDProspectiveCandidateBuilder,
    createStageDFakePublisher,
    createStageDTransactionPublisher,
    buildOfflineStageDRunPlan,
    executeStageDControlledInitialization,
    classifyDuplicateCapture,
    executeStageDOneCycle,
};
