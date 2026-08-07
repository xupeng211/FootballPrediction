'use strict';

// lifecycle: permanent
//
// FotMob bounded detail capture — TRANSPORT-PHASE OBSERVATION record.
//
// Component class: Internal — bounded, redacted, persistable transport-phase
// telemetry for the capture pipeline (FotMobDetailCapturePipeline). Not a
// capture entrypoint, not a business capability; diagnostics only.
//
// Purpose (owner: FOTMOB_DETAIL_TRANSPORT_PHASE_OBSERVABILITY_PR):
//   The real capture path (30 s per-request timeout, retry 0, redirect
//   manual, GET only, https://www.fotmob.com/match/<digits> only) can stall
//   in transport without any persistable evidence of WHERE it stalled. This
//   module records, for each real request attempt, which transport phase was
//   reliably reached before the terminal outcome — so a future timeout
//   evidence trail can answer: waiting for response headers vs headers
//   received vs body reading started vs body bytes read before timeout vs
//   which local timer fired vs last reliable phase vs post-failure counters.
//
//   It NEVER changes the safety contract: no request behavior change, no
//   retry, no redirect-follow, no timeout/delay/budget change, no new
//   network access, no payload/credential persistence.
//
// Safety properties enforced here:
//   - phases are set by actual code-execution boundaries in the fetch
//     adapter — never inferred from error message text;
//   - a request timeout is recognized by a LOCAL timer flag flipped inside
//     the timer callback before abort() — never by matching
//     error.message === 'This operation was aborted' (user / process aborts
//     therefore classify as ABORTED / EXTERNAL_ABORT, never as REQUEST
//     TIMEOUT);
//   - only allowlisted response metadata is persisted (content_type,
//     declared_content_length as a number, location_present boolean,
//     redirected boolean) — cookies, authorization headers, full request /
//     response headers, tokens, sessions, proxy credentials, URL query
//     strings, body fragments and HTML are NEVER persisted;
//   - error fields are name/code/cause-name/cause-code only, bounded to
//     MAX_SHORT_STRING_LEN; strings are max-length bounded everywhere;
//   - numbers are non-negative safe integers; unknown fields are null or
//     explicit enum members;
//   - the file is bounded by max_requests (one observation per attempt,
//     last attempt per ordinal wins), written atomically (temp + rename,
//     'wx' creation flag), symlink-safe (lstat rejects non-regular / link
//     targets), path-traversal-safe (fixed file name inside the run dir),
//     idempotent (identical bytes are not re-written), and NEVER overwrites
//     different content silently (an existing different-valid doc fails
//     closed; an existing invalid doc fails closed);
//   - every doc carries a self-hash (observations_sha256) recomputed and
//     verified on read; a doc that fails structure, schema, invariant or
//     hash validation is refused (fail closed) — never guessed at;
//   - the file is derived data only: it can never turn a failed pair into a
//     capture pair, and its writes never alter the business payload,
//     capture manifest, run state or run summary hashes;
//   - telemetry can affect the RUN only at start: an unreadable or foreign
//     pre-existing observations file fails closed before any request. After
//     the primary capture outcome is finalized, failure of the FINAL
//     telemetry persistence never changes that outcome — the run summary
//     then links telemetry only from the verified final on-disk document
//     (or omits the linkage entirely), never from the pending in-memory
//     doc. A later REPLAY fails closed on an invalid/foreign artifact.
//
// Phase vocabulary (last_reliable_phase values):
//   REQUEST_STARTED               — the request began (timer armed)
//   AWAITING_RESPONSE_HEADERS     — waiting for response headers (set
//                                   immediately before the native fetch)
//   RESPONSE_HEADERS_RECEIVED     — headers are in (fetch resolved)
//   READING_RESPONSE_BODY         — body stream read started
//   RESPONSE_BODY_COMPLETED       — body fully read
//   REQUEST_FAILED                — terminal marker: a non-timeout failure
//   REQUEST_ABORTED_BY_TIMEOUT    — terminal marker: the request was
//                                   aborted by the local timeout timer
//
//   The adapter emits the most specific PROGRESS phase as last_reliable_phase
//   (owner minimum-capability spec: a wait-headers timeout must record
//   AWAITING_RESPONSE_HEADERS with response_headers_received=false and
//   body_bytes_received=0; a body-read timeout must record
//   READING_RESPONSE_BODY with response_headers_received=true,
//   http_status=<real>, body_reading_started=true and body_bytes_received=
//   <actual accumulated safe integer>). REQUEST_FAILED /
//   REQUEST_ABORTED_BY_TIMEOUT are part of the valid vocabulary (accepted by
//   the validator); the terminal classification itself lives in
//   terminal_outcome + abort_source, so the specific progress phase is never
//   lost.
//
// Persistence: runs/<run-id>/transport-observations.json
//   schema fotmob-detail-transport-observations/v1, one final observation
//   per attempt (last attempt per ordinal wins on resume). Observations are
//   SETTLED IN MEMORY during the run and persisted exactly once, at run end,
//   as a bounded final run-local document (atomic temp + rename, 'wx'
//   creation) — there is no per-settle file write. The run summary links
//   the file and the observation count ONLY from the verified final
//   on-disk document (reconcilePersistedObservationsDoc), never from the
//   pending in-memory doc.

const crypto = require('node:crypto');
const path = require('node:path');
const fs = require('node:fs');

// ─────────────────────────────────────────────────────────────
// Vocabulary and bounds
// ─────────────────────────────────────────────────────────────

const OBSERVATIONS_FILE_NAME = 'transport-observations.json';
const OBSERVATIONS_DOC_SCHEMA = 'fotmob-detail-transport-observations/v1';
const OBSERVATION_ENTRY_SCHEMA = 'fotmob-detail-transport-observation/v1';

const TRANSPORT_PHASES = [
    'REQUEST_STARTED',
    'AWAITING_RESPONSE_HEADERS',
    'RESPONSE_HEADERS_RECEIVED',
    'READING_RESPONSE_BODY',
    'RESPONSE_BODY_COMPLETED',
    'REQUEST_FAILED',
    'REQUEST_ABORTED_BY_TIMEOUT',
];

const TERMINAL_OUTCOMES = ['COMPLETED', 'TIMEOUT', 'ABORTED', 'FETCH_ERROR', 'BODY_READ_ERROR', 'SAFETY_ERROR'];

const ABORT_SOURCES = ['REQUEST_TIMEOUT', 'EXTERNAL_ABORT'];

// Max-length bounds for every persisted string. Nothing unbounded is ever
// written; anything longer is truncated (an explicit, documented lossy
// boundary — the diagnostic value of a 64-char error name is never zero).
const MAX_STRING_LEN = 200;
const MAX_SHORT_STRING_LEN = 64;
const MAX_MATCH_ID_LEN = 32;

// Allowlisted response metadata only. Header VALUES (cookies, auth, set-
// cookie, full content-type strings beyond a bounded length, raw headers)
// are never persisted.
const RESPONSE_METADATA_KEYS = ['content_type', 'declared_content_length', 'location_present', 'redirected'];

const HEX_RE = /^[0-9a-f]+$/;

// ─────────────────────────────────────────────────────────────
// Small local helpers (self-contained leaf module — no imports)
// ─────────────────────────────────────────────────────────────

function isPlainObject(value) {
    if (value === null || typeof value !== 'object') return false;
    const proto = Object.getPrototypeOf(value);
    return proto === Object.prototype || proto === null;
}

function boundString(value, maxLen) {
    if (value === null || value === undefined) return null;
    const s = String(value);
    return s.length > maxLen ? s.slice(0, maxLen) : s;
}

function isIsoTimestamp(value) {
    if (value === null || value === undefined) return false;
    if (typeof value !== 'string' || value.length === 0) return false;
    const parsed = Date.parse(value);
    return !Number.isNaN(parsed) && /^\d{4}-\d{2}-\d{2}T/.test(value);
}

function isNonNegativeSafeInt(value) {
    return Number.isSafeInteger(value) && value >= 0;
}

function isPositiveSafeInt(value) {
    return Number.isSafeInteger(value) && value > 0;
}

// Deterministic canonical JSON (sorted object keys, no whitespace) — the
// same pattern the raw-detail fetcher uses for stable payload hashing.
function canonicalize(value) {
    if (value === null || typeof value !== 'object') {
        if (typeof value === 'number' && !Number.isFinite(value)) {
            throw new Error('canonicalize: non-finite number');
        }
        return JSON.stringify(value);
    }
    if (Array.isArray(value)) {
        return `[${value.map(item => canonicalize(item)).join(',')}]`;
    }
    const keys = Object.keys(value).sort();
    const parts = keys.map(key => `${JSON.stringify(key)}:${canonicalize(value[key])}`);
    return `{${parts.join(',')}}`;
}

function sha256Hex(text) {
    return crypto.createHash('sha256').update(String(text), 'utf8').digest('hex');
}

// ─────────────────────────────────────────────────────────────
// Observation entry builder
// ─────────────────────────────────────────────────────────────

/**
 * Build one transport observation entry. Returns null when NO request
 * actually started (budget / URL-contract errors are raised before the
 * attempt anchor exists — they are never recorded as attempts, matching the
 * run-state contract where a failed pre-fetch is not an attempted request).
 *
 * All strings are bounded, all numbers are coerced to non-negative safe
 * integers, unknown fields are null; the caller (fetch adapter) supplies
 * values from actual code boundaries, never from error-text guessing.
 */
/* eslint-disable-next-line complexity */
function buildTransportObservation(inputs = {}) {
    const started = inputs.requestStartedAtIso;
    if (started === null || started === undefined || String(started).trim() === '') {
        return null;
    }

    const nonNegativeInt = v => (isNonNegativeSafeInt(v) ? v : 0);
    const metadata = inputs.responseMetadata;
    const boundedMetadata = isPlainObject(metadata)
        ? {
              content_type: boundString(metadata.content_type, MAX_STRING_LEN),
              declared_content_length: isNonNegativeSafeInt(metadata.declared_content_length)
                  ? metadata.declared_content_length
                  : null,
              location_present: metadata.location_present === true,
              redirected: metadata.redirected === true,
          }
        : null;

    return {
        schema_version: OBSERVATION_ENTRY_SCHEMA,
        ordinal: nonNegativeInt(inputs.ordinal),
        source_match_id: boundString(inputs.sourceMatchId, MAX_MATCH_ID_LEN),
        request_started_at: String(started),
        request_finished_at: boundString(inputs.requestFinishedAtIso, MAX_STRING_LEN),
        elapsed_ms: nonNegativeInt(inputs.elapsedMs),
        last_reliable_phase: inputs.lastReliablePhase || 'REQUEST_STARTED',
        terminal_outcome: inputs.terminalOutcome || 'FETCH_ERROR',
        response_headers_received: inputs.responseHeadersReceived === true,
        response_headers_received_at: inputs.responseHeadersReceivedAt || null,
        http_status:
            Number.isInteger(inputs.httpStatus) && inputs.httpStatus >= 100 && inputs.httpStatus <= 599
                ? inputs.httpStatus
                : null,
        body_reading_started: inputs.bodyReadingStarted === true,
        body_reading_started_at: inputs.bodyReadingStartedAt || null,
        body_bytes_received: nonNegativeInt(inputs.bodyBytesReceived),
        body_completed: inputs.bodyCompleted === true,
        body_completed_at: inputs.bodyCompletedAt || null,
        timeout_configured_ms: isPositiveSafeInt(inputs.timeoutConfiguredMs) ? inputs.timeoutConfiguredMs : 0,
        timeout_triggered: inputs.timeoutTriggered === true,
        abort_source: ABORT_SOURCES.includes(inputs.abortSource) ? inputs.abortSource : null,
        error_name: boundString(inputs.errorName, MAX_SHORT_STRING_LEN),
        error_code: boundString(inputs.errorCode, MAX_SHORT_STRING_LEN),
        error_cause_name: boundString(inputs.errorCauseName, MAX_SHORT_STRING_LEN),
        error_cause_code: boundString(inputs.errorCauseCode, MAX_SHORT_STRING_LEN),
        response_metadata: boundedMetadata,
    };
}

// ─────────────────────────────────────────────────────────────
// Fail-closed validation
// ─────────────────────────────────────────────────────────────

const HTTP_REDIRECT_STATUSES = new Set([301, 302, 303, 307, 308]);

// Fail-closed validator: one explicit check per field and per cross-field
// invariant, by design (the repo pattern for such gates — see the fetch
// adapter's eslint-disable).
/* eslint-disable-next-line complexity */
function validateTransportObservation(entry) {
    const errors = [];
    if (!isPlainObject(entry)) {
        return { ok: false, errors: ['entry is not a plain object'] };
    }
    if (entry.schema_version !== OBSERVATION_ENTRY_SCHEMA) {
        errors.push(`schema_version must be ${OBSERVATION_ENTRY_SCHEMA}`);
    }
    if (!isPositiveSafeInt(entry.ordinal)) {
        errors.push('ordinal must be a positive safe integer');
    }
    if (typeof entry.source_match_id !== 'string' || entry.source_match_id.length === 0) {
        errors.push('source_match_id must be a non-empty string');
    }
    if (!isIsoTimestamp(entry.request_started_at)) {
        errors.push('request_started_at must be a valid ISO timestamp');
    }
    if (!isIsoTimestamp(entry.request_finished_at)) {
        errors.push('request_finished_at must be a valid ISO timestamp');
    }
    if (!isNonNegativeSafeInt(entry.elapsed_ms)) {
        errors.push('elapsed_ms must be a non-negative safe integer');
    }
    if (!TRANSPORT_PHASES.includes(entry.last_reliable_phase)) {
        errors.push(`last_reliable_phase must be one of ${TRANSPORT_PHASES.join(', ')}`);
    }
    if (!TERMINAL_OUTCOMES.includes(entry.terminal_outcome)) {
        errors.push(`terminal_outcome must be one of ${TERMINAL_OUTCOMES.join(', ')}`);
    }
    if (typeof entry.response_headers_received !== 'boolean') {
        errors.push('response_headers_received must be a boolean');
    }
    if (entry.response_headers_received) {
        if (!isIsoTimestamp(entry.response_headers_received_at)) {
            errors.push('response_headers_received_at must be a valid ISO timestamp when headers were received');
        }
        if (!Number.isInteger(entry.http_status) || entry.http_status < 100 || entry.http_status > 599) {
            errors.push('http_status must be an integer in 100..599 when headers were received');
        }
    } else {
        if (entry.response_headers_received_at !== null && entry.response_headers_received_at !== undefined) {
            errors.push('response_headers_received_at must be null when no headers were received');
        }
        if (entry.http_status !== null && entry.http_status !== undefined) {
            errors.push('http_status must be null when no headers were received');
        }
    }
    if (typeof entry.body_reading_started !== 'boolean') {
        errors.push('body_reading_started must be a boolean');
    }
    if (entry.body_reading_started) {
        if (!isIsoTimestamp(entry.body_reading_started_at)) {
            errors.push('body_reading_started_at must be a valid ISO timestamp when body reading started');
        }
        if (!entry.response_headers_received) {
            errors.push('body reading can only start after response headers are received');
        }
    } else if (entry.body_reading_started_at !== null && entry.body_reading_started_at !== undefined) {
        errors.push('body_reading_started_at must be null when body reading did not start');
    }
    if (!isNonNegativeSafeInt(entry.body_bytes_received)) {
        errors.push('body_bytes_received must be a non-negative safe integer');
    }
    if (!entry.body_reading_started && entry.body_bytes_received !== 0) {
        errors.push('body_bytes_received must be 0 when body reading did not start');
    }
    if (typeof entry.body_completed !== 'boolean') {
        errors.push('body_completed must be a boolean');
    }
    if (entry.body_completed) {
        if (!isIsoTimestamp(entry.body_completed_at)) {
            errors.push('body_completed_at must be a valid ISO timestamp when the body completed');
        }
        if (!entry.body_reading_started) {
            errors.push('the body can only complete after body reading started');
        }
    } else if (entry.body_completed_at !== null && entry.body_completed_at !== undefined) {
        errors.push('body_completed_at must be null when the body did not complete');
    }
    if (!isPositiveSafeInt(entry.timeout_configured_ms)) {
        errors.push('timeout_configured_ms must be a positive safe integer');
    }
    if (typeof entry.timeout_triggered !== 'boolean') {
        errors.push('timeout_triggered must be a boolean');
    }
    if (entry.abort_source !== null && !ABORT_SOURCES.includes(entry.abort_source)) {
        errors.push(`abort_source must be null or one of ${ABORT_SOURCES.join(', ')}`);
    }
    for (const key of ['error_name', 'error_code', 'error_cause_name', 'error_cause_code']) {
        if (entry[key] !== null && typeof entry[key] !== 'string') {
            errors.push(`${key} must be null or a string`);
        }
    }
    if (entry.response_metadata !== null && entry.response_metadata !== undefined) {
        if (!isPlainObject(entry.response_metadata)) {
            errors.push('response_metadata must be null or a plain object');
        } else {
            const keys = Object.keys(entry.response_metadata);
            const unknown = keys.filter(key => !RESPONSE_METADATA_KEYS.includes(key));
            if (unknown.length > 0) {
                errors.push(`response_metadata has disallowed keys: ${unknown.join(', ')}`);
            }
            const meta = entry.response_metadata;
            if (meta.content_type !== null && typeof meta.content_type !== 'string') {
                errors.push('response_metadata.content_type must be null or a string');
            }
            if (meta.declared_content_length !== null && !isNonNegativeSafeInt(meta.declared_content_length)) {
                errors.push('response_metadata.declared_content_length must be null or a non-negative safe integer');
            }
            if (typeof meta.location_present !== 'boolean') {
                errors.push('response_metadata.location_present must be a boolean');
            }
            if (typeof meta.redirected !== 'boolean') {
                errors.push('response_metadata.redirected must be a boolean');
            }
            if (meta.redirected !== (meta.location_present && HTTP_REDIRECT_STATUSES.has(entry.http_status))) {
                errors.push('response_metadata.redirected must match location_present and the http status');
            }
        }
    }

    // Logical invariants — fail closed on impossible states.
    if (entry.terminal_outcome === 'COMPLETED' && !entry.response_headers_received) {
        errors.push('COMPLETED requires response headers received');
    }
    if (entry.terminal_outcome === 'COMPLETED') {
        if (entry.timeout_triggered) {
            errors.push('COMPLETED cannot have timeout_triggered true');
        }
        if (entry.error_name !== null || entry.error_code !== null) {
            errors.push('COMPLETED cannot carry error fields');
        }
        const redirected = Boolean(entry.response_metadata && entry.response_metadata.redirected);
        if (!redirected && !entry.body_completed) {
            errors.push('COMPLETED non-redirect responses must have body_completed true');
        }
    }
    if (entry.terminal_outcome === 'TIMEOUT') {
        if (!entry.timeout_triggered) {
            errors.push('TIMEOUT requires timeout_triggered true');
        }
        if (entry.abort_source !== 'REQUEST_TIMEOUT') {
            errors.push('TIMEOUT requires abort_source REQUEST_TIMEOUT');
        }
        if (entry.body_completed) {
            errors.push('TIMEOUT cannot have the body completed');
        }
    }
    if (entry.abort_source === 'REQUEST_TIMEOUT' && !entry.timeout_triggered) {
        errors.push('abort_source REQUEST_TIMEOUT requires timeout_triggered true');
    }
    if (entry.abort_source === 'REQUEST_TIMEOUT' && entry.terminal_outcome !== 'TIMEOUT') {
        errors.push('abort_source REQUEST_TIMEOUT requires terminal_outcome TIMEOUT');
    }
    if (entry.abort_source === 'EXTERNAL_ABORT' && entry.terminal_outcome !== 'ABORTED') {
        errors.push('abort_source EXTERNAL_ABORT requires terminal_outcome ABORTED');
    }
    if (entry.terminal_outcome === 'ABORTED' && entry.timeout_triggered) {
        errors.push('ABORTED cannot have timeout_triggered true');
    }
    if (
        ['FETCH_ERROR', 'BODY_READ_ERROR', 'SAFETY_ERROR', 'ABORTED'].includes(entry.terminal_outcome) &&
        (typeof entry.error_name !== 'string' || entry.error_name.length === 0)
    ) {
        errors.push(`${entry.terminal_outcome} requires a non-empty error_name`);
    }
    if (entry.last_reliable_phase === 'AWAITING_RESPONSE_HEADERS') {
        if (entry.response_headers_received) {
            errors.push('AWAITING_RESPONSE_HEADERS cannot have response headers received');
        }
        if (entry.body_reading_started) {
            errors.push('AWAITING_RESPONSE_HEADERS cannot have body reading started');
        }
        if (entry.body_bytes_received !== 0) {
            errors.push('AWAITING_RESPONSE_HEADERS requires body_bytes_received 0');
        }
    }
    if (
        entry.last_reliable_phase === 'READING_RESPONSE_BODY' &&
        !(entry.response_headers_received && entry.body_reading_started)
    ) {
        errors.push('READING_RESPONSE_BODY requires headers received and body reading started');
    }
    if (entry.last_reliable_phase === 'RESPONSE_BODY_COMPLETED' && !entry.body_completed) {
        errors.push('RESPONSE_BODY_COMPLETED requires body_completed true');
    }
    return { ok: errors.length === 0, errors };
}

// ─────────────────────────────────────────────────────────────
// Document (file) shape
// ─────────────────────────────────────────────────────────────

function defaultObservationsDoc({ runId, planSha256, authorizationId, maxRequests, collectorCodeRevision }) {
    const doc = {
        schema_version: OBSERVATIONS_DOC_SCHEMA,
        run_id: String(runId),
        plan_sha256: String(planSha256),
        authorization_id: String(authorizationId),
        max_requests: Number(maxRequests),
        collector_code_revision: String(collectorCodeRevision),
        observations_sha256: '',
        observations: [],
    };
    doc.observations_sha256 = computeObservationsSelfHash(doc);
    return doc;
}

// Self-hash covers every field EXCEPT observations_sha256 itself (standard
// self-referential-exclusion — the hash is verified on every read).
function computeObservationsSelfHash(doc) {
    const payload = {
        schema_version: doc.schema_version,
        run_id: doc.run_id,
        plan_sha256: doc.plan_sha256,
        authorization_id: doc.authorization_id,
        max_requests: Number(doc.max_requests),
        collector_code_revision: doc.collector_code_revision,
        observations: doc.observations,
    };
    return sha256Hex(canonicalize(payload));
}

// Settle one observation into a doc: the last attempt per ordinal wins
// (resume semantics — a resumed ordinal overwrites its earlier attempt), the
// array stays sorted by ordinal, and the self-hash is recomputed. The input
// doc is never mutated.
function settleObservationInDoc(doc, entry) {
    const check = validateTransportObservation(entry);
    if (!check.ok) {
        throw Object.assign(new Error(`SAFETY_ERROR:invalid transport observation: ${check.errors.join('; ')}`), {
            code: 'SAFETY_ERROR',
        });
    }
    const rest = (Array.isArray(doc.observations) ? doc.observations : []).filter(
        existing => existing.ordinal !== entry.ordinal
    );
    rest.push(entry);
    rest.sort((a, b) => a.ordinal - b.ordinal);
    const next = { ...doc, observations: rest };
    next.observations_sha256 = computeObservationsSelfHash(next);
    return next;
}

/* eslint-disable-next-line complexity */
function validateObservationsDoc(doc) {
    const errors = [];
    if (!isPlainObject(doc)) {
        return { ok: false, errors: ['doc is not a plain object'] };
    }
    if (doc.schema_version !== OBSERVATIONS_DOC_SCHEMA) {
        errors.push(`schema_version must be ${OBSERVATIONS_DOC_SCHEMA}`);
    }
    if (typeof doc.run_id !== 'string' || doc.run_id.length === 0) {
        errors.push('run_id must be a non-empty string');
    }
    if (typeof doc.plan_sha256 !== 'string' || !HEX_RE.test(doc.plan_sha256) || doc.plan_sha256.length !== 64) {
        errors.push('plan_sha256 must be a 64-char hex string');
    }
    if (typeof doc.authorization_id !== 'string' || doc.authorization_id.length === 0) {
        errors.push('authorization_id must be a non-empty string');
    }
    if (!isPositiveSafeInt(doc.max_requests)) {
        errors.push('max_requests must be a positive safe integer');
    }
    if (
        typeof doc.collector_code_revision !== 'string' ||
        !HEX_RE.test(doc.collector_code_revision) ||
        doc.collector_code_revision.length !== 40
    ) {
        errors.push('collector_code_revision must be a 40-char hex string');
    }
    if (
        typeof doc.observations_sha256 !== 'string' ||
        !HEX_RE.test(doc.observations_sha256) ||
        doc.observations_sha256.length !== 64
    ) {
        errors.push('observations_sha256 must be a 64-char hex string');
    }
    if (!Array.isArray(doc.observations)) {
        errors.push('observations must be an array');
    } else {
        if (doc.observations.length > Number(doc.max_requests)) {
            errors.push(`observations length ${doc.observations.length} exceeds max_requests ${doc.max_requests}`);
        }
        const seenOrdinals = new Set();
        let previousOrdinal = 0;
        for (const entry of doc.observations) {
            const check = validateTransportObservation(entry);
            if (!check.ok) {
                errors.push(`observation invalid: ${check.errors.join('; ')}`);
                continue;
            }
            if (seenOrdinals.has(entry.ordinal)) {
                errors.push(`duplicate ordinal ${entry.ordinal}`);
            }
            seenOrdinals.add(entry.ordinal);
            if (entry.ordinal <= previousOrdinal) {
                errors.push(`ordinals must be strictly ascending (${previousOrdinal} then ${entry.ordinal})`);
            }
            previousOrdinal = entry.ordinal;
        }
        const recomputed = computeObservationsSelfHash(doc);
        if (recomputed !== doc.observations_sha256) {
            errors.push('observations_sha256 does not match the recomputed self-hash');
        }
    }
    return { ok: errors.length === 0, errors };
}

// ─────────────────────────────────────────────────────────────
// Atomic, symlink-safe, idempotent file persistence
// ─────────────────────────────────────────────────────────────

const toSafetyError = message => Object.assign(new Error(`SAFETY_ERROR:${message}`), { code: 'SAFETY_ERROR' });

/**
 * lstat the observations target. ONLY `ENOENT` means the target is absent
 * (returns null). Every other `lstatSync` failure (EACCES / EIO / EPERM /
 * ...) fails closed with SAFETY_ERROR — an un-inspectable pre-existing
 * artifact must never be treated as absent, on either the read or the
 * write path. Classification is by `err.code` only, never by message text;
 * the surfaced error stays bounded (error code + fixed target path, no
 * unbounded filesystem error text).
 */
function lstatObservationsTarget(filePath, fsImpl) {
    try {
        return fsImpl.lstatSync(filePath);
    } catch (err) {
        if (err && err.code === 'ENOENT') {
            return null;
        }
        throw toSafetyError(
            `cannot inspect transport observations target (${String((err && err.code) || 'UNKNOWN')}): ${filePath}`
        );
    }
}

/**
 * Read the observations file for a run dir. Absent (ENOENT) → null. Any
 * other lstat failure, symlink / non-regular target, unparseable JSON,
 * schema / invariant violations or a self-hash mismatch all fail closed
 * with SAFETY_ERROR — the file is never guessed at, and a tampered,
 * corrupted or un-inspectable file is a loud signal.
 */
function readTransportObservationsFile(runDir, fsImpl = fs) {
    const filePath = path.join(runDir, OBSERVATIONS_FILE_NAME);
    const stat = lstatObservationsTarget(filePath, fsImpl);
    if (!stat) return null;
    if (stat.isSymbolicLink() || !stat.isFile()) {
        throw toSafetyError(`transport observations target is not a regular file: ${filePath}`);
    }
    let parsed = null;
    try {
        parsed = JSON.parse(String(fsImpl.readFileSync(filePath, 'utf8')));
    } catch (err) {
        throw toSafetyError(
            `transport observations file is not valid JSON: ${String(err.message || err).slice(0, MAX_SHORT_STRING_LEN)}`
        );
    }
    const check = validateObservationsDoc(parsed);
    if (!check.ok) {
        throw toSafetyError(`transport observations file failed validation: ${check.errors.join('; ')}`);
    }
    return parsed;
}

const serializeDoc = doc => Buffer.from(JSON.stringify(doc, null, 2) + '\n', 'utf8');

/**
 * Write the observations doc atomically (temp + rename, 'wx' creation).
 * Idempotent: identical bytes are not re-written. Never silently overwrites
 * different content: an existing VALID doc that is neither byte-identical to
 * the new doc nor byte-identical to the caller-supplied base doc (the doc
 * this write evolves — read at run start, or the previous in-place version)
 * fails closed, because only the run's own earlier process can legitimately
 * own a different-but-valid doc under the same run lock; an existing
 * INVALID doc fails closed. A read-back hash verification confirms the
 * rename landed the exact bytes.
 *
 * @param {object} doc - the next doc version to persist
 * @param {object} [baseDoc] - the doc this write evolves (null when the
 *   file is absent / first write); must serialize to the existing bytes
 *   when the file exists but differs from `doc`
 * @returns {'written' | 'unchanged'}
 */
/* eslint-disable-next-line complexity */
function writeTransportObservationsFile(runDir, doc, fsImpl = fs, baseDoc = null) {
    const check = validateObservationsDoc(doc);
    if (!check.ok) {
        throw toSafetyError(`refusing to persist invalid transport observations: ${check.errors.join('; ')}`);
    }
    const filePath = path.join(runDir, OBSERVATIONS_FILE_NAME);
    const bytes = serializeDoc(doc);

    // Only ENOENT means the target is absent. Any other lstatSync failure
    // (EACCES / EIO / EPERM / ...) fails closed BEFORE the temp-file write
    // and rename below — the code must never proceed as if an
    // un-inspectable target did not exist.
    const existingStat = lstatObservationsTarget(filePath, fsImpl);
    if (existingStat) {
        if (existingStat.isSymbolicLink() || !existingStat.isFile()) {
            throw toSafetyError(`transport observations target is not a regular file: ${filePath}`);
        }
        const existingBytes = fsImpl.readFileSync(filePath);
        if (existingBytes.equals(bytes)) {
            return 'unchanged';
        }
        // This write evolves `baseDoc`: if the existing bytes ARE the base
        // doc, this is the run's own in-place evolution (first settle after
        // read/resume) — proceed. Anything else is a different valid doc
        // (tampering / concurrent writer — refused) or invalid content
        // (corruption — refused).
        if (baseDoc !== null && existingBytes.equals(serializeDoc(baseDoc))) {
            // falls through to the atomic write below
        } else {
            let existingParsed = null;
            try {
                existingParsed = JSON.parse(String(existingBytes, 'utf8'));
            } catch (err) {
                throw toSafetyError(
                    `transport observations target differs and is not valid JSON: ${String(err.message || err).slice(0, MAX_SHORT_STRING_LEN)}`
                );
            }
            const existingCheck = validateObservationsDoc(existingParsed);
            if (!existingCheck.ok) {
                throw toSafetyError(
                    `transport observations target differs and failed validation: ${existingCheck.errors.join('; ')}`
                );
            }
            throw toSafetyError(
                'transport observations target exists with different valid content — refusing to overwrite'
            );
        }
    }

    const tmpPath = `${filePath}.tmp-${process.pid}-${Date.now()}`;
    try {
        fsImpl.writeFileSync(tmpPath, bytes, { encoding: 'utf8', flag: 'wx' });
        fsImpl.renameSync(tmpPath, filePath);
    } catch (err) {
        try {
            fsImpl.unlinkSync(tmpPath);
        } catch {
            /* ignore */
        }
        throw toSafetyError(
            `transport observations write failed: ${String(err.message || err).slice(0, MAX_SHORT_STRING_LEN)}`
        );
    }
    // Read-back verification: the file on disk must re-validate and re-hash.
    try {
        const readBack = readTransportObservationsFile(runDir, fsImpl);
        if (!readBack || readBack.observations_sha256 !== doc.observations_sha256) {
            throw toSafetyError('transport observations read-back verification failed');
        }
    } catch (err) {
        throw toSafetyError(
            `transport observations read-back verification failed: ${String(err.message || err).slice(0, MAX_SHORT_STRING_LEN)}`
        );
    }
    return 'written';
}

/**
 * Reconcile the ACTUAL final on-disk observations state for run-summary
 * linkage (P2-1 remediation: RUN SUMMARY TELEMETRY LINKAGE MUST REFLECT
 * VERIFIED FINAL ON-DISK STATE, NOT THE PENDING IN-MEMORY OBSERVATIONS DOC).
 *
 * Returns the validated doc actually present on disk, or null when no usable
 * persisted doc exists — the ONLY doc buildRunSummary may receive for
 * telemetry linkage. Never throws: this runs after the primary run outcome
 * is finalized, and a telemetry reconciliation failure must not change that
 * outcome.
 *
 * Cases:
 *   A. No file on disk → null (fresh run whose final write failed, or no
 *      observations) — the summary must not claim telemetry it cannot
 *      verify.
 *   B. Resume: the valid base doc read at run start remains on disk (the
 *      evolved final write failed) → the ACTUAL base doc is returned (its
 *      bindings match), so the summary reflects what REPLAY will later read,
 *      not the newer in-memory doc.
 *   C. Final write returned 'unchanged' / the file equals the intended doc →
 *      the ACTUAL validated doc is returned.
 *   D. Write threw after the rename landed (read-back uncertainty) but the
 *      final file safely re-reads and validates → the ACTUAL validated doc
 *      is returned — verified by the production reader, never assumed.
 *   E. File unreadable / symlink / invalid / a foreign VALID doc (any
 *      binding mismatch) → null: the summary never lies, and the file is
 *      NEVER overwritten or deleted merely to make telemetry look
 *      consistent. A later REPLAY of this run fails closed on the
 *      invalid/foreign artifact (module contract above).
 *
 * @param {object} args - { runDir, expectedDoc, fsImpl? }
 * @param {object} args.expectedDoc - the run's pending doc (bindings to
 *   verify against the persisted file: run_id, plan_sha256,
 *   authorization_id, max_requests, collector_code_revision)
 * @returns {object|null} the verified persisted doc, or null
 */
function reconcilePersistedObservationsDoc({ runDir, expectedDoc, fsImpl = fs }) {
    let persisted = null;
    try {
        persisted = readTransportObservationsFile(runDir, fsImpl);
    } catch {
        return null; // E: unusable on-disk artifact — no linkage claim, file untouched
    }
    if (!persisted) {
        return null; // A: no persisted file
    }
    const bindingGetters = [
        doc => String(doc.run_id || ''),
        doc => String(doc.plan_sha256 || ''),
        doc => String(doc.authorization_id || ''),
        doc => Number(doc.max_requests),
        doc => String(doc.collector_code_revision || ''),
    ];
    const bindingsOk = bindingGetters.every((get, i) => get(persisted) === get(expectedDoc));
    if (!bindingsOk) {
        return null; // E: foreign valid doc — never claim it
    }
    return persisted;
}

module.exports = {
    OBSERVATIONS_FILE_NAME,
    OBSERVATIONS_DOC_SCHEMA,
    OBSERVATION_ENTRY_SCHEMA,
    TRANSPORT_PHASES,
    TERMINAL_OUTCOMES,
    ABORT_SOURCES,
    MAX_STRING_LEN,
    MAX_SHORT_STRING_LEN,
    buildTransportObservation,
    validateTransportObservation,
    validateObservationsDoc,
    defaultObservationsDoc,
    settleObservationInDoc,
    computeObservationsSelfHash,
    readTransportObservationsFile,
    writeTransportObservationsFile,
    reconcilePersistedObservationsDoc,
};
