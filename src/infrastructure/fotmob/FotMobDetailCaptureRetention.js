'use strict';

/* eslint-disable max-lines */

// lifecycle: permanent
//
// FotMob bounded detail capture — retention and replay support.
//
// Owns:
//   - the atomic stable-payload + manifest paired writer (both-or-neither,
//     temp file + rename, readback verification, rollback, symlink rejection,
//     no overwrite of different content, idempotent on identical bytes). The
//     full HTML response body is NEVER persisted: only the allowlisted
//     stable payload and its manifest survive (P1-1);
//   - run-state management (plan SHA binding, per-candidate completion,
//     resume support without refetching);
//   - the run-bound immutable plan snapshot (run-dir/plan.json) that REPLAY
//     binds candidate identity to (P2-6);
//   - offline REPLAY that materializes deterministic detail artifacts from
//     the persisted stable payload (no HTML, no current-time drift).
//
// This module never touches the network and never touches the database.

const path = require('node:path');
const fs = require('node:fs');

const {
    MANIFEST_SCHEMA_VERSION,
    PAYLOAD_SCHEMA_VERSION,
    validateCaptureManifest,
    validateDetailArtifact,
    validateAndRecomputeCapturePlan,
    computeStableCapturePayloadSha256,
    sha256Hex,
    sha256Text,
    isPlainObject,
    ensureRealDirectoryTree,
} = require('./FotMobDetailCaptureContract');

// ─────────────────────────────────────────────────────────────
// Helpers
// ─────────────────────────────────────────────────────────────

function assertRegularFilePath(filePath, fileSystem, purpose) {
    let stat;
    try {
        stat = fileSystem.lstatSync(filePath);
    } catch {
        return null; // absent
    }
    if (stat.isSymbolicLink() || !stat.isFile()) {
        throw Object.assign(
            new Error(`${purpose} refused: not a regular file: ${filePath}`),
            { code: 'SAFETY_ERROR' }
        );
    }
    return stat;
}

function sha256Bytes(buf) {
    return sha256Hex(buf);
}

/**
 * Atomic paired write of stable payload + capture manifest.
 *
 * Both files are written via temp files and renamed. On any failure the
 * already-renamed file is rolled back so the pair remains both-or-neither.
 * Existing identical pair → idempotent success; partial pair or different
 * content → SAFETY_ERROR. The target directory is created/verified via
 * ensureRealDirectoryTree so pre-existing symlinked descendants are
 * rejected before any write.
 *
 * @param {object} args - {
 *   payloadBody (string — serialized stable payload document),
 *   manifest (object),
 *   payloadFileName, manifestFileName, pairDir (absolute),
 *   fsImpl?
 * }
 * @returns {{ payloadPath, manifestPath, payloadSha256, manifestSha256, idempotent }}
 */
/* eslint-disable-next-line complexity */
function writeCapturePair(args = {}) {
    const fileSystem = args.fsImpl || fs;
    const payloadBody = String(args.payloadBody ?? '');
    const manifest = args.manifest;
    const payloadFileName = String(args.payloadFileName || '');
    const manifestFileName = String(args.manifestFileName || '');
    const pairDir = path.resolve(String(args.pairDir || ''));

    if (!payloadFileName || !manifestFileName) {
        throw Object.assign(new Error('payloadFileName and manifestFileName are required'), { code: 'INPUT_ERROR' });
    }
    if (!isPlainObject(manifest)) {
        throw Object.assign(new Error('manifest must be an object'), { code: 'INPUT_ERROR' });
    }
    const manifestValidation = validateCaptureManifest(manifest);
    if (!manifestValidation.ok) {
        throw Object.assign(
            new Error(`manifest validation failed: ${manifestValidation.errors.join('; ')}`),
            { code: 'SAFETY_ERROR' }
        );
    }

    const payloadSha256 = sha256Bytes(Buffer.from(payloadBody, 'utf8'));
    if (payloadSha256 !== manifest.payload_file_sha256) {
        throw Object.assign(
            new Error('manifest payload_file_sha256 does not match payload body'),
            { code: 'SAFETY_ERROR' }
        );
    }
    // The persisted payload must be the same business document the manifest
    // binds: its own stable_payload_sha256 must equal the manifest's.
    let payloadParsed = null;
    try {
        payloadParsed = JSON.parse(payloadBody);
    } catch {
        throw Object.assign(new Error('payload body is not valid JSON'), { code: 'SAFETY_ERROR' });
    }
    if (!isPlainObject(payloadParsed) ||
        payloadParsed.schema_version !== PAYLOAD_SCHEMA_VERSION ||
        payloadParsed.stable_payload_sha256 !== manifest.stable_payload_sha256) {
        throw Object.assign(
            new Error('payload stable_payload_sha256 does not match manifest'),
            { code: 'SAFETY_ERROR' }
        );
    }

    // Create/verify the pair directory WITHOUT following symlinked
    // descendants (P2-3); ensureRealDirectoryTree is the single shared
    // symlink-safe walk (no local duplicate).
    ensureRealDirectoryTree(pairDir, fileSystem);

    const payloadPath = path.join(pairDir, payloadFileName);
    const manifestPath = path.join(pairDir, manifestFileName);

    // Both-or-neither + symlink rejection + overwrite protection.
    const payloadStat = assertRegularFilePath(payloadPath, fileSystem, 'payload retention');
    const manifestStat = assertRegularFilePath(manifestPath, fileSystem, 'manifest retention');
    const payloadExists = payloadStat !== null;
    const manifestExists = manifestStat !== null;

    if (payloadExists !== manifestExists) {
        throw Object.assign(
            new Error(
                `capture pair integrity violated: payload=${payloadExists ? 'present' : 'absent'}, ` +
                    `manifest=${manifestExists ? 'present' : 'absent'}`
            ),
            { code: 'SAFETY_ERROR' }
        );
    }

    if (payloadExists) {
        const existingPayloadSha = sha256Bytes(fileSystem.readFileSync(payloadPath));
        if (existingPayloadSha !== payloadSha256) {
            throw Object.assign(
                new Error(`capture pair refused: payload file exists with different content`),
                { code: 'SAFETY_ERROR' }
            );
        }
        // Idempotent success only when the existing manifest bytes are
        // byte-identical to what this write would produce.
        const existingManifestBytes = fileSystem.readFileSync(manifestPath);
        const existingManifestSha = sha256Bytes(existingManifestBytes);
        const freshManifestBytes = Buffer.from(JSON.stringify(manifest, null, 2) + '\n', 'utf8');
        if (existingManifestSha !== sha256Bytes(freshManifestBytes)) {
            throw Object.assign(
                new Error('capture pair refused: manifest exists with different content'),
                { code: 'SAFETY_ERROR' }
            );
        }
        return {
            payloadPath,
            manifestPath,
            payloadSha256,
            manifestSha256: existingManifestSha,
            idempotent: true,
        };
    }

    // Write both via temp files, rename, rollback on failure.
    const manifestBytes = Buffer.from(JSON.stringify(manifest, null, 2) + '\n', 'utf8');
    const manifestSha256 = sha256Bytes(manifestBytes);
    const payloadTmp = `${payloadPath}.tmp-${process.pid}-${Date.now()}`;
    const manifestTmp = `${manifestPath}.tmp-${process.pid}-${Date.now()}`;
    let payloadRenamed = false;

    try {
        fileSystem.writeFileSync(payloadTmp, Buffer.from(payloadBody, 'utf8'), { encoding: 'utf8', flag: 'wx' });
        fileSystem.writeFileSync(manifestTmp, manifestBytes, { encoding: 'utf8', flag: 'wx' });
        fileSystem.renameSync(payloadTmp, payloadPath);
        payloadRenamed = true;
        fileSystem.renameSync(manifestTmp, manifestPath);
    } catch (err) {
        // Rollback: if payload was renamed but manifest was not, remove payload.
        try { fileSystem.unlinkSync(payloadTmp); } catch { /* ignore */ }
        try { fileSystem.unlinkSync(manifestTmp); } catch { /* ignore */ }
        if (payloadRenamed) {
            try { fileSystem.unlinkSync(payloadPath); } catch { /* ignore */ }
        }
        throw Object.assign(
            new Error(`capture pair write failed: ${err.message}`),
            { code: 'SAFETY_ERROR' }
        );
    }

    // Final readback verification — both files must be readable, regular,
    // and byte-identical to what we wrote.
    const payloadReadback = fileSystem.readFileSync(payloadPath);
    if (sha256Bytes(payloadReadback) !== payloadSha256) {
        try { fileSystem.unlinkSync(payloadPath); } catch { /* ignore */ }
        try { fileSystem.unlinkSync(manifestPath); } catch { /* ignore */ }
        throw Object.assign(
            new Error('capture pair readback failed: payload hash mismatch'),
            { code: 'SAFETY_ERROR' }
        );
    }
    const manifestReadback = fileSystem.readFileSync(manifestPath, 'utf8');
    if (sha256Text(manifestReadback) !== manifestSha256) {
        try { fileSystem.unlinkSync(payloadPath); } catch { /* ignore */ }
        try { fileSystem.unlinkSync(manifestPath); } catch { /* ignore */ }
        throw Object.assign(
            new Error('capture pair readback failed: manifest hash mismatch'),
            { code: 'SAFETY_ERROR' }
        );
    }

    return {
        payloadPath,
        manifestPath,
        payloadSha256,
        manifestSha256,
        idempotent: false,
    };
}

// ─────────────────────────────────────────────────────────────
// Run state
// ─────────────────────────────────────────────────────────────

function defaultRunState(plan, options = {}) {
    const startedAt = String(options.startedAt || '');
    return {
        schema_version: 'fotmob-detail-capture-run-state/v1',
        run_id: String(options.runId || ''),
        plan_sha256: String(plan.plan_business_sha256 || ''),
        source_artifact_sha256: String(plan.source_artifact_sha256 || ''),
        authorization_id: String(options.authorizationId || ''),
        max_requests: Number(options.maxRequests || 0),
        delay_ms: Number(options.delayMs || 0),
        collector_code_revision: String(options.collectorCodeRevision || ''),
        started_at: startedAt,
        created_at: startedAt,
        updated_at: startedAt,
        completed_ordinals: [],
        stopped_at_ordinal: null,
        stop_reason: null,
        status: 'in_progress',
        network_requests_attempted: 0,
        network_responses_received: 0,
        // R3-P2-4: cumulative pairs actually persisted (independent of
        // attempts / responses).
        captures_completed: 0,
        // R3-P2-5: ISO timestamp of the last request attempt, persisted
        // before the native fetch; absent while no attempt exists.
        last_network_request_attempted_at: null,
        // R20-P1: ISO next-allowed-request DEADLINE (last request start +
        // delay_ms) persisted alongside the attempt — the resume gate waits
        // until the deadline, covering the last pre-fetch write's duration.
        next_allowed_request_at: null,
        // R22-P1 (Codex re-review on 0bc69dad9): in-flight marker — TRUE from
        // the last pre-fetch write until the request settles (both
        // actualization writes clear it). A true marker on disk means the
        // prior process died with a request possibly in flight; resume then
        // executes the FULL delay from the recovery moment.
        fetch_in_flight: false,
    };
}

/**
 * Run-state contract validator (Codex re-review R3, spec section 十六).
 * Enforces the full run-state schema — non-negative counters, monotonic
 * response/capture totals, unique ordinals, and the request-timestamp
 * invariant (present whenever attempts exist). NEVER auto-fixes: every
 * violation fails closed on read.
 *
 * @param {object} runState
 * @returns {{ ok: boolean, errors: string[] }}
 */
/* eslint-disable-next-line complexity */
function validateRunState(runState) {
    const errors = [];
    if (!isPlainObject(runState)) {
        return { ok: false, errors: ['run state is not an object'] };
    }
    if (runState.schema_version !== 'fotmob-detail-capture-run-state/v1') {
        errors.push('run state schema_version must be fotmob-detail-capture-run-state/v1');
    }
    if (!/^[a-zA-Z0-9][a-zA-Z0-9._-]*$/.test(String(runState.run_id || ''))) {
        errors.push('run_id must be a valid identifier');
    }
    if (!/^[0-9a-f]{64}$/.test(String(runState.plan_sha256 || ''))) {
        errors.push('plan_sha256 must be 64 lowercase hex');
    }
    if (!/^[0-9a-f]{64}$/.test(String(runState.source_artifact_sha256 || ''))) {
        errors.push('source_artifact_sha256 must be 64 lowercase hex');
    }
    if (!/^[a-zA-Z0-9][a-zA-Z0-9._-]*$/.test(String(runState.authorization_id || ''))) {
        errors.push('authorization_id must be a valid identifier');
    }
    for (const numField of ['max_requests', 'delay_ms', 'network_requests_attempted',
        'network_responses_received', 'captures_completed']) {
        const n = Number(runState[numField]);
        if (!Number.isInteger(n) || n < 0) {
            errors.push(`${numField} must be a non-negative integer`);
        }
    }
    // Monotonicity: responses can never exceed attempts (a failed attempt
    // is not a response); captures can never exceed responses (a response
    // that fails validity is not a capture).
    if (Number(runState.network_responses_received) > Number(runState.network_requests_attempted)) {
        errors.push('network_responses_received cannot exceed network_requests_attempted');
    }
    if (Number(runState.captures_completed) > Number(runState.network_responses_received)) {
        errors.push('captures_completed cannot exceed network_responses_received');
    }
    const ordinals = Array.isArray(runState.completed_ordinals)
        ? runState.completed_ordinals.map(Number)
        : [];
    if (ordinals.some(o => !Number.isInteger(o) || o < 1)) {
        errors.push('completed_ordinals must contain positive integers');
    } else if (new Set(ordinals).size !== ordinals.length) {
        errors.push('completed_ordinals must be unique');
    } else if (Number(runState.captures_completed) !== ordinals.length) {
        errors.push('captures_completed must equal completed_ordinals length');
    }
    // Invariant: whenever an attempt exists, the request timestamp must be
    // present and parseable (R3-P2-5).
    if (Number(runState.network_requests_attempted) > 0) {
        const ts = String(runState.last_network_request_attempted_at || '');
        if (!ts) {
            errors.push('last_network_request_attempted_at required when network_requests_attempted > 0');
        } else if (Number.isNaN(Date.parse(ts))) {
            errors.push('last_network_request_attempted_at must be a parseable timestamp');
        }
    }
    // R20-P1 (Codex re-review on 0bfe90629): the persisted next-allowed-
    // request DEADLINE (last request start + delayMs) covers the last pre-
    // fetch run-state write's duration — the resume gate waits until the
    // deadline instead of a timestamp that was still pending write. Optional
    // for backward compatibility with legacy states (they fall back to the
    // timestamp formula on resume); when present it must be parseable.
    if (runState.next_allowed_request_at !== undefined && runState.next_allowed_request_at !== null
        && String(runState.next_allowed_request_at).trim() !== '') {
        if (Number.isNaN(Date.parse(String(runState.next_allowed_request_at)))) {
            errors.push('next_allowed_request_at must be a parseable timestamp');
        } else if (Number(runState.network_requests_attempted || 0) > 0
            && runState.last_network_request_attempted_at !== undefined
            && runState.last_network_request_attempted_at !== null
            && String(runState.last_network_request_attempted_at).trim() !== '') {
            // R21-P2 (Codex re-review on 05cd23c55): when both are present the
            // deadline is a fail-closed GATE — a syntactically valid but EARLY
            // deadline (tampered below last + delay_ms) would let a resume
            // issue the next request before the full delay. Every legit write
            // keeps deadline === last + delay_ms exactly; any deviation
            // (earlier OR later) fails closed.
            const lastMs = Date.parse(String(runState.last_network_request_attempted_at));
            const delayMs = Number(runState.delay_ms);
            if (!Number.isNaN(lastMs) && !Number.isNaN(delayMs)
                && Date.parse(String(runState.next_allowed_request_at)) !== lastMs + delayMs) {
                errors.push('next_allowed_request_at must equal last_network_request_attempted_at + delay_ms');
            }
        }
    }
    // R22-P1 (Codex re-review on 0bc69dad9): the in-flight marker is a
    // boolean when present. R23-P1 (Codex re-review on ab6aca8ca): only a
    // fully ABSENT property is legacy-tolerated — an explicit null is as
    // abnormal as any other non-boolean (the pipeline only ever writes true
    // or false; a null could only come from migration or tampering and must
    // fail closed instead of silently taking the fast path).
    if (runState.fetch_in_flight !== undefined && typeof runState.fetch_in_flight !== 'boolean') {
        errors.push('fetch_in_flight must be a boolean');
    }
    return { ok: errors.length === 0, errors };
}

function writeRunState(runDir, runState, fsImpl = fs) {
    ensureRealDirectoryTree(runDir, fsImpl);
    const statePath = path.join(runDir, 'run-state.json');
    const bytes = Buffer.from(JSON.stringify(runState, null, 2) + '\n', 'utf8');
    const tmpPath = `${statePath}.tmp-${process.pid}-${Date.now()}`;
    try {
        fsImpl.writeFileSync(tmpPath, bytes, { encoding: 'utf8', flag: 'wx' });
        fsImpl.renameSync(tmpPath, statePath);
    } catch (err) {
        try { fsImpl.unlinkSync(tmpPath); } catch { /* ignore */ }
        throw Object.assign(
            new Error(`run state write failed: ${err.message}`),
            { code: 'SAFETY_ERROR' }
        );
    }
    return statePath;
}

function readRunState(runDir, fsImpl = fs) {
    const statePath = path.join(runDir, 'run-state.json');
    const stat = assertRegularFilePath(statePath, fsImpl, 'run state');
    if (!stat) return null;
    const parsed = JSON.parse(fsImpl.readFileSync(statePath, 'utf8'));
    if (!isPlainObject(parsed) || parsed.schema_version !== 'fotmob-detail-capture-run-state/v1') {
        throw Object.assign(new Error('run state has unknown schema'), { code: 'SAFETY_ERROR' });
    }
    // The full run-state contract is enforced on every read: a tampered or
    // internally inconsistent state fails closed, never auto-fixed (R3).
    const validation = validateRunState(parsed);
    if (!validation.ok) {
        throw Object.assign(
            new Error(`run state invalid: ${validation.errors.join('; ')}`),
            { code: 'SAFETY_ERROR' }
        );
    }
    return parsed;
}

// ─────────────────────────────────────────────────────────────
// Run-bound plan snapshot (P2-6)
// ─────────────────────────────────────────────────────────────

/**
 * Write the immutable, run-bound plan snapshot to <run-dir>/plan.json.
 * Atomic temp+rename, readback verified, symlink rejected, no overwrite of
 * different content, idempotent on identical bytes. Called BEFORE any real
 * network request so the run is self-contained for offline REPLAY.
 *
 * @param {object} args - { runDir, plan, fsImpl }
 * @returns {{ snapshotPath, snapshotSha256, idempotent }}
 */
function writePlanSnapshot(args = {}) {
    const fileSystem = args.fsImpl || fs;
    const runDir = path.resolve(String(args.runDir || ''));
    const plan = args.plan;

    if (!isPlainObject(plan)) {
        throw Object.assign(new Error('plan snapshot requires a plan object'), { code: 'INPUT_ERROR' });
    }
    const planCheck = validateAndRecomputeCapturePlan(plan);
    if (!planCheck.ok) {
        throw Object.assign(
            new Error(`plan snapshot refused: ${planCheck.errors.join('; ')}`),
            { code: 'SAFETY_ERROR' }
        );
    }

    ensureRealDirectoryTree(runDir, fileSystem);
    const snapshotPath = path.join(runDir, 'plan.json');
    const bytes = Buffer.from(JSON.stringify(plan, null, 2) + '\n', 'utf8');
    const snapshotSha256 = sha256Bytes(bytes);

    const existingStat = assertRegularFilePath(snapshotPath, fileSystem, 'plan snapshot');
    if (existingStat) {
        const existingBytes = fileSystem.readFileSync(snapshotPath);
        if (sha256Bytes(existingBytes) !== snapshotSha256) {
            throw Object.assign(
                new Error('plan snapshot refused: exists with different content'),
                { code: 'SAFETY_ERROR' }
            );
        }
        return { snapshotPath, snapshotSha256, idempotent: true };
    }

    const tmpPath = `${snapshotPath}.tmp-${process.pid}-${Date.now()}`;
    try {
        fileSystem.writeFileSync(tmpPath, bytes, { encoding: 'utf8', flag: 'wx' });
        fileSystem.renameSync(tmpPath, snapshotPath);
    } catch (err) {
        try { fileSystem.unlinkSync(tmpPath); } catch { /* ignore */ }
        throw Object.assign(
            new Error(`plan snapshot write failed: ${err.message}`),
            { code: 'SAFETY_ERROR' }
        );
    }
    const readback = fileSystem.readFileSync(snapshotPath);
    if (sha256Bytes(readback) !== snapshotSha256) {
        try { fileSystem.unlinkSync(snapshotPath); } catch { /* ignore */ }
        throw Object.assign(
            new Error('plan snapshot readback failed: hash mismatch'),
            { code: 'SAFETY_ERROR' }
        );
    }
    return { snapshotPath, snapshotSha256, idempotent: false };
}

/**
 * Read the run-bound plan snapshot from <run-dir>/plan.json.
 * Returns null when absent; the snapshot is re-validated (schema + hash
 * recompute) on read — a tampered snapshot fails closed.
 *
 * @param {string} runDir
 * @param {object} fsImpl?
 * @returns {object|null} validated plan snapshot
 */
function readPlanSnapshot(runDir, fsImpl = fs) {
    const snapshotPath = path.join(runDir, 'plan.json');
    const stat = assertRegularFilePath(snapshotPath, fsImpl, 'plan snapshot');
    if (!stat) return null;
    const parsed = JSON.parse(fsImpl.readFileSync(snapshotPath, 'utf8'));
    const planCheck = validateAndRecomputeCapturePlan(parsed);
    if (!planCheck.ok) {
        throw Object.assign(
            new Error(`plan snapshot invalid: ${planCheck.errors.join('; ')}`),
            { code: 'SAFETY_ERROR' }
        );
    }
    return parsed;
}

// ─────────────────────────────────────────────────────────────
// Resume pair check (P1-5: exact run/plan/authorization binding)
// ─────────────────────────────────────────────────────────────

/**
 * Check whether a candidate ordinal already has a complete, matching
 * payload+manifest pair for the CURRENT run context. Used for resume:
 * completed candidates must never be fetched again.
 *
 * The pair is bound to the current run, plan, source artifact,
 * authorization, candidate and request URL — a pair copied from another run
 * or plan is NEVER treated as complete (RESUME_PAIR_CONTEXT_MISMATCH).
 *
 * @param {object} args - {
 *   runDir, ordinal, sourceMatchId,
 *   expectedRunId, expectedAuthorizationId, expectedPlanSha256,
 *   expectedSourceArtifactSha256, expectedCandidate (plan candidate),
 *   expectedRequestUrl, fsImpl?
 * }
 * @returns {{ completed: boolean, state: 'complete'|'partial'|'mismatch'|'absent'|'error', detail: string }}
 */
/* eslint-disable-next-line complexity */
function checkCompletedPair(args = {}) {
    const fileSystem = args.fsImpl || fs;
    const runDir = String(args.runDir || '');
    const ordinal = Number(args.ordinal || 0);
    const sourceMatchId = String(args.sourceMatchId || '');
    const payloadFileName = `${ordinal}-${sourceMatchId}.payload.json`;
    const manifestFileName = `${ordinal}-${sourceMatchId}.manifest.json`;
    const payloadPath = path.join(runDir, 'captures', payloadFileName);
    const manifestPath = path.join(runDir, 'captures', manifestFileName);

    const payloadStat = assertRegularFilePath(payloadPath, fileSystem, 'resume check');
    const manifestStat = assertRegularFilePath(manifestPath, fileSystem, 'resume check');

    if (payloadStat === null && manifestStat === null) return { completed: false, state: 'absent', detail: 'pair absent' };
    if (payloadStat === null !== (manifestStat === null)) {
        return {
            completed: false,
            state: 'partial',
            detail: `partial pair: payload=${payloadStat !== null}, manifest=${manifestStat !== null}`,
        };
    }

    // Both present: verify file binding, manifest contract (incl. self-hash),
    // then the exact run-context binding field by field.
    const payloadSha = sha256Bytes(fileSystem.readFileSync(payloadPath));
    let manifest;
    try {
        manifest = JSON.parse(fileSystem.readFileSync(manifestPath, 'utf8'));
    } catch {
        return { completed: false, state: 'mismatch', detail: 'manifest unparseable' };
    }
    const manifestValidation = validateCaptureManifest(manifest);
    if (!manifestValidation.ok) {
        return { completed: false, state: 'mismatch', detail: `manifest invalid: ${manifestValidation.errors.join('; ')}` };
    }
    if (manifest.payload_file_sha256 !== payloadSha) {
        return { completed: false, state: 'mismatch', detail: 'manifest payload_file_sha256 does not match payload file' };
    }
    let payload;
    try {
        payload = JSON.parse(fileSystem.readFileSync(payloadPath, 'utf8'));
    } catch {
        return { completed: false, state: 'mismatch', detail: 'payload unparseable' };
    }
    if (!isPlainObject(payload) || payload.stable_payload_sha256 !== manifest.stable_payload_sha256) {
        return { completed: false, state: 'mismatch', detail: 'payload stable_payload_sha256 does not match manifest' };
    }
    // P2 (Codex round-2 review on 85bc0ee43): two self-declared equal hashes
    // are not evidence — the business hash is RECOMPUTED from the payload's
    // actual business fields with the shared projection before the pair is
    // treated as completed. A tampered payload with refreshed file hash and
    // manifest self-hash (but the same old declared stable hash) would
    // otherwise be skipped by resume and only fail later at replay.
    if (!isPlainObject(payload) || payload.schema_version !== PAYLOAD_SCHEMA_VERSION) {
        return { completed: false, state: 'mismatch', detail: 'payload has unknown schema' };
    }
    const recomputedPayloadHash = computeStableCapturePayloadSha256(payload);
    if (recomputedPayloadHash !== String(payload.stable_payload_sha256 || '') ||
        recomputedPayloadHash !== String(manifest.stable_payload_sha256 || '')) {
        return {
            completed: false,
            state: 'mismatch',
            detail: 'RESUME_PAIR_BUSINESS_HASH_MISMATCH: recomputed payload business hash does not match declared stable_payload_sha256',
        };
    }
    // P2 (Codex re-review on 670504754): the payload's OWN identity must bind
    // to the verified manifest, field by field, before the pair can be
    // treated as completed. The business hash proves the business content is
    // self-consistent, but a tamperer who recomputes the business hash and
    // refreshes both file hashes could otherwise swap in a DIFFERENT
    // candidate / source / observed identity that the business projection
    // does not cover — resume would count the contaminated pair complete and
    // only a later replay would reject it. The observed identity must be
    // response-derived with no conflict, exactly like replay requires.
    const payloadObserved = isPlainObject(payload.observed_identity) ? payload.observed_identity : {};
    const payloadExpected = isPlainObject(payload.expected_identity) ? payload.expected_identity : {};
    const identityChecks = [
        ['payload.source_match_id', payload.source_match_id, manifest.source_match_id],
        ['payload.candidate_id', payload.candidate_id, manifest.candidate_id],
        // P2 (Codex re-review on 047f6afcb): the payload's complete PLAN
        // identity — competition, league_id, season and expected_identity
        // (home_team, away_team, kickoff_at) — must bind to the verified
        // manifest field by field before the pair can be treated as
        // completed. The business hash covers these fields, but a tamperer
        // who recomputes the business hash and refreshes the file/self
        // hashes could otherwise swap in a payload declaring a DIFFERENT
        // plan identity; resume would count it complete and a later replay
        // would emit the wrong plan identity under the run's real plan.
        ['payload.competition', payload.competition, manifest.competition],
        ['payload.league_id', payload.league_id, manifest.league_id],
        ['payload.season', payload.season, manifest.season],
        ['payload.expected_identity.home_team', payloadExpected.home_team, manifest.home_team],
        ['payload.expected_identity.away_team', payloadExpected.away_team, manifest.away_team],
        ['payload.expected_identity.kickoff_at', payloadExpected.kickoff_at, manifest.kickoff_at],
        ['payload.observed_identity.observed_match_id', payloadObserved.observed_match_id, manifest.observed_match_id],
        ['payload.observed_identity.observed_match_id_source', payloadObserved.observed_match_id_source, manifest.observed_match_id_source],
        ['payload.observed_identity.observed_match_id_conflict', payloadObserved.observed_match_id_conflict, manifest.observed_match_id_conflict],
        ['payload.observed_identity.observed_match_id_is_response_derived', payloadObserved.observed_match_id_is_response_derived, manifest.observed_match_id_is_response_derived],
    ];
    for (const [label, actual, expected] of identityChecks) {
        if (String(actual ?? '') !== String(expected ?? '')) {
            return {
                completed: false,
                state: 'mismatch',
                detail: `RESUME_PAIR_PAYLOAD_IDENTITY_MISMATCH:${label}`,
            };
        }
    }
    if (payloadObserved.observed_match_id_is_response_derived !== true ||
        payloadObserved.observed_match_id_conflict === true) {
        return {
            completed: false,
            state: 'mismatch',
            detail: 'RESUME_PAIR_PAYLOAD_IDENTITY_MISMATCH: observed identity must be response-derived with no conflict',
        };
    }

    // R11-P2-1 (Codex re-review on abf6fbc65): the plan identity must bind
    // to the CURRENT plan candidate, not only to the manifest. A tamperer
    // who swaps the SAME identity fields in BOTH payload and manifest
    // (recomputing business/file/self hashes and keeping the original
    // candidate_identity_sha256 — which nothing here recomputes from the
    // manifest's identity fields) would otherwise pass every
    // payload↔manifest check while the pair actually belongs to a DIFFERENT
    // plan candidate: resume would count it complete and only a later
    // replay would reject it. Bind manifest AND payload plan-identity
    // fields directly to expectedCandidate (and the league id to the
    // run's REQUIRED league id). Missing expected values fail closed.
    const expectedCandidate = args.expectedCandidate || {};
    const expectedLeagueId = args.expectedLeagueId;
    const planIdentityChecks = [
        ['manifest.competition vs plan candidate', manifest.competition, expectedCandidate.competition],
        ['manifest.league_id vs plan', manifest.league_id, expectedLeagueId],
        ['manifest.season vs plan candidate', manifest.season, expectedCandidate.season],
        ['manifest.home_team vs plan candidate', manifest.home_team, expectedCandidate.home_team],
        ['manifest.away_team vs plan candidate', manifest.away_team, expectedCandidate.away_team],
        ['manifest.kickoff_at vs plan candidate', manifest.kickoff_at, expectedCandidate.kickoff_at],
        ['payload.competition vs plan candidate', payload.competition, expectedCandidate.competition],
        ['payload.league_id vs plan', payload.league_id, expectedLeagueId],
        ['payload.season vs plan candidate', payload.season, expectedCandidate.season],
        ['payload.expected_identity.home_team vs plan candidate', payloadExpected.home_team, expectedCandidate.home_team],
        ['payload.expected_identity.away_team vs plan candidate', payloadExpected.away_team, expectedCandidate.away_team],
        ['payload.expected_identity.kickoff_at vs plan candidate', payloadExpected.kickoff_at, expectedCandidate.kickoff_at],
    ];
    for (const [label, actual, expected] of planIdentityChecks) {
        if (String(actual ?? '') !== String(expected ?? '')) {
            return {
                completed: false,
                state: 'mismatch',
                detail: `RESUME_PAIR_PAYLOAD_IDENTITY_MISMATCH:${label}`,
            };
        }
    }

    // Exact run-context binding — any field that does not match the current
    // run, plan, artifact, authorization or candidate is a mismatch that
    // stops the run; it is NEVER treated as completed.
    const checks = [
        ['manifest.source_match_id', manifest.source_match_id, sourceMatchId],
        ['manifest.request_ordinal', Number(manifest.request_ordinal), ordinal],
        ['manifest.observed_match_id', manifest.observed_match_id, sourceMatchId],
        ['manifest.capture_run_id', manifest.capture_run_id, args.expectedRunId],
        ['manifest.authorization_id', manifest.authorization_id, args.expectedAuthorizationId],
        ['manifest.source_plan_sha256', manifest.source_plan_sha256, args.expectedPlanSha256],
        ['manifest.source_artifact_sha256', manifest.source_artifact_sha256, args.expectedSourceArtifactSha256],
        ['manifest.candidate_id', manifest.candidate_id, expectedCandidate.candidate_id],
        ['manifest.candidate_identity_sha256', manifest.candidate_identity_sha256, expectedCandidate.candidate_identity_sha256],
        ['manifest.request_url', manifest.request_url, args.expectedRequestUrl],
        // P2 (Codex re-review on a5d63af60): the pair must also be bound to
        // the EXECUTION context the current run-state records — request
        // budget, inter-request delay and collector code revision. The plan
        // business hash deliberately excludes the generator revision, so two
        // runs with identical plan / run id / authorization / candidate but
        // different budgets, delays or revisions must never accept each
        // other's pairs: a complete pair copied from a prior run would
        // otherwise be counted complete here and later replayed under THIS
        // run's revision, declaring false parser provenance. Missing expected
        // values fail closed (never skip the check).
        ['manifest.request_budget', Number(manifest.request_budget), args.expectedRequestBudget],
        ['manifest.delay_ms', Number(manifest.delay_ms), args.expectedDelayMs],
        ['manifest.collector_code_revision', manifest.collector_code_revision, args.expectedCollectorCodeRevision],
    ];
    for (const [label, actual, expected] of checks) {
        if (String(actual ?? '') !== String(expected ?? '')) {
            return {
                completed: false,
                state: 'mismatch',
                detail: `RESUME_PAIR_CONTEXT_MISMATCH:${label}`,
            };
        }
    }

    return { completed: true, state: 'complete', detail: 'pair complete and bound to this run context' };
}

// ─────────────────────────────────────────────────────────────
// Replay (fully offline, deterministic, payload-based)
// ─────────────────────────────────────────────────────────────

/**
 * Replay one captured payload+manifest pair into a structured detail
 * artifact, fully offline. No HTML is involved: the stable payload file is
 * verified (file hash, business hash, manifest self-hash, observed id) and
 * then materialized deterministically. parsed_at is derived from the
 * manifest's response_received_at — never the current wall clock — so
 * repeated replays of the same run produce byte-identical artifacts.
 *
 * Candidate identity comes exclusively from the run-bound plan snapshot;
 * a missing snapshot, missing candidate, or a plan candidate whose identity
 * hash does not match the manifest fails closed (no empty identity output).
 *
 * @param {object} args - {
 *   runDir, ordinal, sourceMatchId,
 *   runPlan (validated run-bound plan snapshot — REQUIRED),
 *   parserCodeRevision (40-hex),
 *   expectedRunId (run-state run_id the pair must be bound to — REQUIRED),
 *   expectedAuthorizationId (run-state authorization_id the pair must be
 *     bound to — REQUIRED),
 *   fsImpl?
 * }
 * @returns {{ artifact: object, artifactSha256: string }}
 */
/* eslint-disable-next-line complexity */
function replayCapturePair(args = {}) {
    const fileSystem = args.fsImpl || fs;
    const runDir = String(args.runDir || '');
    const ordinal = Number(args.ordinal || 0);
    const sourceMatchId = String(args.sourceMatchId || '');
    const payloadFileName = `${ordinal}-${sourceMatchId}.payload.json`;
    const manifestFileName = `${ordinal}-${sourceMatchId}.manifest.json`;
    const payloadPath = path.join(runDir, 'captures', payloadFileName);
    const manifestPath = path.join(runDir, 'captures', manifestFileName);

    // Run-bound plan snapshot is REQUIRED for replay identity (P2-6).
    const runPlan = args.runPlan;
    if (!isPlainObject(runPlan)) {
        throw Object.assign(new Error('replay failed: run-bound plan snapshot required'), { code: 'SAFETY_ERROR' });
    }
    const planCandidate = (Array.isArray(runPlan.candidates) ? runPlan.candidates : [])
        .find(c => String(c.source_match_id) === sourceMatchId);
    if (!planCandidate) {
        throw Object.assign(
            new Error(`replay failed: plan snapshot has no candidate for source_match_id ${sourceMatchId}`),
            { code: 'SAFETY_ERROR' }
        );
    }
    // P2 (Codex re-review on 9568ea33e): the pair's ordinal must bind to the
    // snapshot candidate. Lookup by source id alone lets a COPIED pair — e.g.
    // candidate 2's pair renamed with an ordinal-1 prefix plus a refreshed
    // request_ordinal and manifest self-hash — replay as ordinal 1 while the
    // summary claims ordinal 1 completed. The snapshot candidate's ordinal is
    // the ground truth for the pair's position; any mismatch fails closed
    // before any artifact or summary write.
    if (Number(planCandidate.ordinal) !== ordinal) {
        throw Object.assign(
            new Error(
                `replay failed: plan snapshot candidate ordinal mismatch — ` +
                `candidate ${sourceMatchId} is ordinal ${planCandidate.ordinal}, pair claims ordinal ${ordinal}`
            ),
            { code: 'SAFETY_ERROR' }
        );
    }

    // Payload file hash must match manifest; manifest must be self-valid.
    const payloadBytes = fileSystem.readFileSync(payloadPath);
    const payloadFileSha256 = sha256Bytes(payloadBytes);
    let manifest;
    try {
        manifest = JSON.parse(fileSystem.readFileSync(manifestPath, 'utf8'));
    } catch (err) {
        throw Object.assign(new Error(`replay failed: manifest unparseable: ${err.message}`), { code: 'SAFETY_ERROR' });
    }
    const manifestValidation = validateCaptureManifest(manifest);
    if (!manifestValidation.ok) {
        throw Object.assign(
            new Error(`replay failed: manifest invalid: ${manifestValidation.errors.join('; ')}`),
            { code: 'SAFETY_ERROR' }
        );
    }
    // R3-P2-2 (Codex final-head review): the capture pair must be bound to
    // THIS run and THIS authorization — a pair captured under another
    // run/authorization is REPLAY_PAIR_CONTEXT_MISMATCH and must fail
    // closed before any artifact or summary write.
    const expectedRunId = String(args.expectedRunId || '');
    const expectedAuthorizationId = String(args.expectedAuthorizationId || '');
    if (!expectedRunId || !expectedAuthorizationId) {
        throw Object.assign(
            new Error('replay failed: expected run id and authorization id required'),
            { code: 'SAFETY_ERROR' }
        );
    }
    // P2 (Codex re-review on a5d63af60): replay binds the pair to the FULL
    // execution context recorded in the run state — request budget,
    // inter-request delay and collector code revision. The plan business hash
    // excludes the generator revision, so a complete pair copied from a prior
    // run (same plan/run/authorization, different budget/delay/revision) must
    // never be replayed under THIS run's context: the artifact would declare
    // parser provenance of the wrong revision. Missing expected values fail
    // closed.
    const expectedRequestBudget = Number(args.expectedRequestBudget);
    const expectedDelayMs = Number(args.expectedDelayMs);
    const expectedCollectorCodeRevision = String(args.expectedCollectorCodeRevision || '');
    if (!Number.isInteger(expectedRequestBudget) || !Number.isInteger(expectedDelayMs) ||
        !expectedCollectorCodeRevision) {
        throw Object.assign(
            new Error('replay failed: expected request budget, delay and collector code revision required'),
            { code: 'SAFETY_ERROR' }
        );
    }
    if (Number(manifest.request_budget) !== expectedRequestBudget ||
        Number(manifest.delay_ms) !== expectedDelayMs) {
        throw Object.assign(
            new Error(
                'REPLAY_PAIR_CONTEXT_MISMATCH: manifest request_budget/delay_ms do not match the run state'
            ),
            { code: 'SAFETY_ERROR' }
        );
    }
    if (String(manifest.collector_code_revision || '') !== expectedCollectorCodeRevision) {
        throw Object.assign(
            new Error(
                `REPLAY_PAIR_REVISION_MISMATCH: manifest collector_code_revision ` +
                `${String(manifest.collector_code_revision || '')} does not match run state ` +
                `collector_code_revision ${expectedCollectorCodeRevision}`
            ),
            { code: 'SAFETY_ERROR' }
        );
    }
    if (String(manifest.capture_run_id || '') !== expectedRunId) {
        throw Object.assign(
            new Error(
                `REPLAY_PAIR_CONTEXT_MISMATCH: manifest capture_run_id ${String(manifest.capture_run_id || '')} ` +
                `does not match run state run_id ${expectedRunId}`
            ),
            { code: 'SAFETY_ERROR' }
        );
    }
    if (String(manifest.authorization_id || '') !== expectedAuthorizationId) {
        throw Object.assign(
            new Error(
                `REPLAY_PAIR_CONTEXT_MISMATCH: manifest authorization_id ${String(manifest.authorization_id || '')} ` +
                `does not match run state authorization_id ${expectedAuthorizationId}`
            ),
            { code: 'SAFETY_ERROR' }
        );
    }
    if (manifest.payload_file_sha256 !== payloadFileSha256) {
        throw Object.assign(new Error('replay failed: payload file hash does not match manifest payload_file_sha256'), { code: 'SAFETY_ERROR' });
    }
    if (manifest.source_match_id !== sourceMatchId) {
        throw Object.assign(new Error('replay failed: manifest source_match_id mismatch'), { code: 'SAFETY_ERROR' });
    }
    if (manifest.observed_match_id !== sourceMatchId) {
        throw Object.assign(new Error('replay failed: observed_match_id does not match source_match_id'), { code: 'SAFETY_ERROR' });
    }
    if (manifest.request_ordinal !== ordinal) {
        throw Object.assign(new Error('replay failed: manifest request_ordinal mismatch'), { code: 'SAFETY_ERROR' });
    }
    // Bind the manifest to the run plan candidate: same candidate id and
    // same identity hash — a manifest from another plan fails closed.
    if (manifest.candidate_id !== String(planCandidate.candidate_id || '') ||
        manifest.candidate_identity_sha256 !== String(planCandidate.candidate_identity_sha256 || '')) {
        throw Object.assign(new Error('replay failed: manifest candidate does not match run plan snapshot'), { code: 'SAFETY_ERROR' });
    }
    // Bind the manifest to the FULL run plan (Codex re-review P2): two valid
    // plans may share a candidate with different siblings/ordering — the
    // manifest's source_plan_sha256 must equal the snapshot's recomputed
    // plan_business_sha256 or replay fails closed.
    if (manifest.source_plan_sha256 !== String(runPlan.plan_business_sha256 || '')) {
        throw Object.assign(
            new Error('replay failed: manifest source_plan_sha256 does not match the run plan snapshot'),
            { code: 'SAFETY_ERROR' }
        );
    }

    let payload;
    try {
        payload = JSON.parse(payloadBytes.toString('utf8'));
    } catch (err) {
        throw Object.assign(new Error(`replay failed: payload unparseable: ${err.message}`), { code: 'SAFETY_ERROR' });
    }
    if (!isPlainObject(payload) || payload.schema_version !== PAYLOAD_SCHEMA_VERSION) {
        throw Object.assign(new Error('replay failed: payload has unknown schema'), { code: 'SAFETY_ERROR' });
    }
    // R3-P2-1 (Codex final-head review): the payload's business hash is
    // RECOMPUTED at replay time with the same shared projection used by the
    // capture builder — a tampered business field (e.g. normalized nested
    // data) fails closed even when the payload file hash and the manifest
    // self-hash were refreshed to match.
    const recomputedPayloadHash = computeStableCapturePayloadSha256(payload);
    if (recomputedPayloadHash !== String(payload.stable_payload_sha256 || '')) {
        throw Object.assign(
            new Error('replay failed: recomputed payload business hash does not match payload stable_payload_sha256'),
            { code: 'SAFETY_ERROR' }
        );
    }
    if (recomputedPayloadHash !== String(manifest.stable_payload_sha256 || '')) {
        throw Object.assign(
            new Error('replay failed: recomputed payload business hash does not match manifest stable_payload_sha256'),
            { code: 'SAFETY_ERROR' }
        );
    }
    if (payload.source_match_id !== sourceMatchId) {
        throw Object.assign(new Error('replay failed: payload source_match_id mismatch'), { code: 'SAFETY_ERROR' });
    }
    if (payload.candidate_id !== String(planCandidate.candidate_id || '')) {
        throw Object.assign(new Error('replay failed: payload candidate_id does not match run plan snapshot'), { code: 'SAFETY_ERROR' });
    }
    // P2 (Codex re-review on cdcb7ae18): bind the payload's OBSERVED IDENTITY
    // to the verified manifest, field by field. Hash equality alone is not
    // enough — a tamperer who recomputes the business hash and refreshes the
    // manifest hashes could otherwise swap in a request-side or conflicting
    // observed identity. The observed identity must be response-derived with
    // no conflict, or replay fails closed before any artifact write.
    const payloadObserved = isPlainObject(payload.observed_identity) ? payload.observed_identity : {};
    const observedIdentityMismatch = (field) => {
        throw Object.assign(
            new Error(`REPLAY_PAYLOAD_OBSERVED_IDENTITY_MISMATCH: ${field}`),
            { code: 'SAFETY_ERROR' }
        );
    };
    if (String(payloadObserved.observed_match_id ?? '') !== String(manifest.observed_match_id ?? '')) {
        observedIdentityMismatch('observed_match_id does not match verified manifest');
    }
    if (String(payloadObserved.observed_match_id_source ?? '') !== String(manifest.observed_match_id_source ?? '')) {
        observedIdentityMismatch('observed_match_id_source does not match verified manifest');
    }
    if ((payloadObserved.observed_match_id_conflict === true) !== (manifest.observed_match_id_conflict === true)) {
        observedIdentityMismatch('observed_match_id_conflict does not match verified manifest');
    }
    if ((payloadObserved.observed_match_id_is_response_derived === true) !==
        (manifest.observed_match_id_is_response_derived === true)) {
        observedIdentityMismatch('observed_match_id_is_response_derived does not match verified manifest');
    }
    if (payloadObserved.observed_match_id_is_response_derived !== true ||
        payloadObserved.observed_match_id_conflict === true) {
        observedIdentityMismatch('observed identity must be response-derived with no conflict');
    }

    // R10-P2-2 (Codex re-review on 047f6afcb): bind the payload's complete
    // PLAN identity — competition, league_id, season and expected_identity
    // (home_team, away_team, kickoff_at) — to the verified manifest AND the
    // run plan snapshot, field by field, before any artifact is built. The
    // business hash covers these fields, but a tamperer who recomputes the
    // shared projection and refreshes the file/self hashes could otherwise
    // swap in a payload declaring a different plan identity; the artifact
    // would then emit the wrong plan identity while the summary claims the
    // run's real one. Fail closed on any field, including missing values.
    const payloadExpected = isPlainObject(payload.expected_identity) ? payload.expected_identity : {};
    const planIdentityMismatch = (field) => {
        throw Object.assign(
            new Error(`REPLAY_PAYLOAD_PLAN_IDENTITY_MISMATCH: ${field}`),
            { code: 'SAFETY_ERROR' }
        );
    };
    if (String(payload.competition ?? '') !== String(manifest.competition ?? '') ||
        String(payload.competition ?? '') !== String(planCandidate.competition ?? '')) {
        planIdentityMismatch('competition does not match verified manifest / run plan snapshot');
    }
    // R11-P2-2 (Codex re-review on abf6fbc65): league_id is a PLAN-level
    // field (it lives on the plan, not on each candidate) — a
    // payload↔manifest comparison alone lets a tamperer sync both files to
    // a different league id and have the artifact's structured hash bind to
    // the WRONG league. Bind BOTH files to the verified run plan's top-level
    // league id; a missing run plan league id fails closed.
    if (String(payload.league_id ?? '') !== String(manifest.league_id ?? '') ||
        String(payload.league_id ?? '') !== String(runPlan.league_id ?? '') ||
        String(manifest.league_id ?? '') !== String(runPlan.league_id ?? '')) {
        planIdentityMismatch('league_id does not match verified manifest / run plan league id');
    }
    if (String(payload.season ?? '') !== String(manifest.season ?? '') ||
        String(payload.season ?? '') !== String(planCandidate.season ?? '')) {
        planIdentityMismatch('season does not match verified manifest / run plan snapshot');
    }
    if (String(payloadExpected.home_team ?? '') !== String(manifest.home_team ?? '') ||
        String(payloadExpected.home_team ?? '') !== String(planCandidate.home_team ?? '')) {
        planIdentityMismatch('expected_identity.home_team does not match verified manifest / run plan snapshot');
    }
    if (String(payloadExpected.away_team ?? '') !== String(manifest.away_team ?? '') ||
        String(payloadExpected.away_team ?? '') !== String(planCandidate.away_team ?? '')) {
        planIdentityMismatch('expected_identity.away_team does not match verified manifest / run plan snapshot');
    }
    if (String(payloadExpected.kickoff_at ?? '') !== String(manifest.kickoff_at ?? '') ||
        String(payloadExpected.kickoff_at ?? '') !== String(planCandidate.kickoff_at ?? '')) {
        planIdentityMismatch('expected_identity.kickoff_at does not match verified manifest / run plan snapshot');
    }

    // Structured payload hash = the payload's own business projection hash
    // (deterministic — identical bytes on every replay).
    const structuredPayloadSha256 = payload.stable_payload_sha256;

    const artifact = {
        schema_version: 'fotmob-match-detail-artifact/v1',
        source_provider: 'FotMob',
        source_match_id: sourceMatchId,
        candidate_id: String(planCandidate.candidate_id),
        competition: String(planCandidate.competition || ''),
        season: String(planCandidate.season || ''),
        expected_identity: {
            home_team: String(planCandidate.home_team || ''),
            away_team: String(planCandidate.away_team || ''),
            kickoff_at: String(planCandidate.kickoff_at || ''),
        },
        observed_identity: payload.observed_identity || {},
        normalized: payload.normalized || {},
        payload_file_sha256: payloadFileSha256,
        capture_manifest_sha256: manifest.capture_manifest_sha256,
        stable_payload_sha256: payload.stable_payload_sha256,
        structured_payload_sha256: structuredPayloadSha256,
        parser_component: manifest.parser_component || 'NextDataParser+FotMobRawParser',
        parser_version: manifest.parser_version || null,
        parser_code_revision: String(args.parserCodeRevision || ''),
        // Deterministic: derived from the capture record, never the wall clock.
        parsed_at: String(manifest.response_received_at || ''),
        matchId: sourceMatchId,
    };

    const artifactValidation = validateDetailArtifact(artifact);
    if (!artifactValidation.ok) {
        throw Object.assign(
            new Error(`replay failed: artifact contract: ${artifactValidation.errors.join('; ')}`),
            { code: 'SAFETY_ERROR' }
        );
    }

    const artifactSha256 = sha256Text(JSON.stringify(artifact));
    return { artifact, artifactSha256 };
}

/**
 * Write a structured detail artifact to the replay directory (atomic,
 * no overwrite of different content, symlink rejection, real directory
 * tree for the target directory).
 *
 * @param {object} args - { artifact, replayDir, ordinal, sourceMatchId, fsImpl }
 * @returns {{ artifactPath, artifactSha256 }}
 */
function writeDetailArtifact(args = {}) {
    const fileSystem = args.fsImpl || fs;
    const artifact = args.artifact;
    const replayDir = path.resolve(String(args.replayDir || ''));
    const ordinal = Number(args.ordinal || 0);
    const sourceMatchId = String(args.sourceMatchId || '');
    const fileName = `${ordinal}-${sourceMatchId}.detail.json`;
    const artifactPath = path.join(replayDir, fileName);

    const validation = validateDetailArtifact(artifact);
    if (!validation.ok) {
        throw Object.assign(
            new Error(`detail artifact validation failed: ${validation.errors.join('; ')}`),
            { code: 'SAFETY_ERROR' }
        );
    }

    ensureRealDirectoryTree(replayDir, fileSystem);

    const bytes = Buffer.from(JSON.stringify(artifact, null, 2) + '\n', 'utf8');
    const artifactSha256 = sha256Bytes(bytes);

    const existingStat = assertRegularFilePath(artifactPath, fileSystem, 'detail artifact write');
    if (existingStat) {
        const existingBytes = fileSystem.readFileSync(artifactPath);
        if (sha256Bytes(existingBytes) !== artifactSha256) {
            throw Object.assign(
                new Error('detail artifact refused: target exists with different content'),
                { code: 'SAFETY_ERROR' }
            );
        }
        return { artifactPath, artifactSha256, idempotent: true };
    }

    const tmpPath = `${artifactPath}.tmp-${process.pid}-${Date.now()}`;
    try {
        fileSystem.writeFileSync(tmpPath, bytes, { encoding: 'utf8', flag: 'wx' });
        fileSystem.renameSync(tmpPath, artifactPath);
    } catch (err) {
        try { fileSystem.unlinkSync(tmpPath); } catch { /* ignore */ }
        throw Object.assign(
            new Error(`detail artifact write failed: ${err.message}`),
            { code: 'SAFETY_ERROR' }
        );
    }
    const readback = fileSystem.readFileSync(artifactPath);
    if (sha256Bytes(readback) !== artifactSha256) {
        try { fileSystem.unlinkSync(artifactPath); } catch { /* ignore */ }
        throw Object.assign(
            new Error('detail artifact readback failed: hash mismatch'),
            { code: 'SAFETY_ERROR' }
        );
    }
    return { artifactPath, artifactSha256, idempotent: false };
}

// ─────────────────────────────────────────────────────────────
// Run summary
// ─────────────────────────────────────────────────────────────

function buildRunSummary(runState, plan, completedOrdinals) {
    return {
        schema_version: 'fotmob-detail-capture-run-summary/v1',
        run_id: runState.run_id,
        plan_sha256: runState.plan_sha256,
        source_artifact_sha256: runState.source_artifact_sha256,
        authorization_id: runState.authorization_id,
        status: runState.status,
        plan_candidate_count: Number(plan.selected_candidate_count || 0),
        completed_count: completedOrdinals.length,
        completed_ordinals: [...completedOrdinals].sort((a, b) => a - b),
        stopped_at_ordinal: runState.stopped_at_ordinal,
        stop_reason: runState.stop_reason,
        // Attempted counts persist BEFORE the fetch; failed requests are
        // never recorded as zero (P2-4).
        network_requests_attempted: Number(runState.network_requests_attempted || 0),
        network_responses_received: Number(runState.network_responses_received || 0),
        captures_completed: completedOrdinals.length,
        network_requests_made: Number(runState.network_requests_made || 0),
        real_fotmob_network_requests: Number(runState.real_fotmob_network_requests || 0),
        database_writes: 0,
    };
}

function writeRunSummary(runDir, summary, fsImpl = fs) {
    ensureRealDirectoryTree(runDir, fsImpl);
    const summaryPath = path.join(runDir, 'run-summary.json');
    const bytes = Buffer.from(JSON.stringify(summary, null, 2) + '\n', 'utf8');
    const tmpPath = `${summaryPath}.tmp-${process.pid}-${Date.now()}`;
    try {
        fsImpl.writeFileSync(tmpPath, bytes, { encoding: 'utf8', flag: 'wx' });
        fsImpl.renameSync(tmpPath, summaryPath);
    } catch (err) {
        try { fsImpl.unlinkSync(tmpPath); } catch { /* ignore */ }
        throw Object.assign(
            new Error(`run summary write failed: ${err.message}`),
            { code: 'SAFETY_ERROR' }
        );
    }
    return summaryPath;
}

module.exports = {
    writeCapturePair,
    defaultRunState,
    writeRunState,
    readRunState,
    validateRunState,
    writePlanSnapshot,
    readPlanSnapshot,
    checkCompletedPair,
    replayCapturePair,
    writeDetailArtifact,
    buildRunSummary,
    writeRunSummary,
    sha256Bytes,
};
