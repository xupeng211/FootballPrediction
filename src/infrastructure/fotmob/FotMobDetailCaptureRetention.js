'use strict';

// lifecycle: permanent
//
// FotMob bounded detail capture — retention and replay support.
//
// Owns:
//   - the atomic raw+manifest paired writer (both-or-neither, temp file +
//     rename, readback verification, rollback, symlink rejection, no
//     overwrite of different content, idempotent on identical bytes);
//   - run-state management (plan SHA binding, per-candidate completion,
//     resume support without refetching);
//   - offline REPLAY output of structured detail artifacts.
//
// This module never touches the network and never touches the database.

const path = require('node:path');
const fs = require('node:fs');
const crypto = require('node:crypto');

const {
    MANIFEST_SCHEMA_VERSION,
    validateCaptureManifest,
    validateDetailArtifact,
    sha256Hex,
    sha256Text,
    canonicalJsonHash,
    isPlainObject,
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
 * Atomic paired write of raw HTML + capture manifest.
 *
 * Both files are written via temp files and renamed. On any failure the
 * already-renamed file is rolled back so the pair remains both-or-neither.
 * Existing identical pair → idempotent success; partial pair or different
 * content → SAFETY_ERROR.
 *
 * @param {object} args - {
 *   rawBody (Buffer), manifest (object),
 *   rawFileName, manifestFileName, pairDir (absolute),
 *   fsImpl?
 * }
 * @returns {{ rawPath, manifestPath, rawSha256, manifestSha256, idempotent }}
 */
/* eslint-disable-next-line complexity */
function writeCapturePair(args = {}) {
    const fileSystem = args.fsImpl || fs;
    const rawBody = Buffer.isBuffer(args.rawBody) ? args.rawBody : Buffer.from(String(args.rawBody || ''), 'utf8');
    const manifest = args.manifest;
    const rawFileName = String(args.rawFileName || '');
    const manifestFileName = String(args.manifestFileName || '');
    const pairDir = path.resolve(String(args.pairDir || ''));

    if (!rawFileName || !manifestFileName) {
        throw Object.assign(new Error('rawFileName and manifestFileName are required'), { code: 'INPUT_ERROR' });
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

    const rawSha256 = sha256Bytes(rawBody);
    if (rawSha256 !== manifest.body_sha256) {
        throw Object.assign(
            new Error('manifest body_sha256 does not match raw body'),
            { code: 'SAFETY_ERROR' }
        );
    }

    const rawPath = path.join(pairDir, rawFileName);
    const manifestPath = path.join(pairDir, manifestFileName);

    // Both-or-neither + symlink rejection + overwrite protection.
    const rawStat = assertRegularFilePath(rawPath, fileSystem, 'raw retention');
    const manifestStat = assertRegularFilePath(manifestPath, fileSystem, 'manifest retention');
    const rawExists = rawStat !== null;
    const manifestExists = manifestStat !== null;

    if (rawExists !== manifestExists) {
        throw Object.assign(
            new Error(
                `capture pair integrity violated: raw=${rawExists ? 'present' : 'absent'}, ` +
                    `manifest=${manifestExists ? 'present' : 'absent'}`
            ),
            { code: 'SAFETY_ERROR' }
        );
    }

    if (rawExists) {
        const existingRawSha = sha256Bytes(fileSystem.readFileSync(rawPath));
        if (existingRawSha !== rawSha256) {
            throw Object.assign(
                new Error(`capture pair refused: raw file exists with different content`),
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
            rawPath,
            manifestPath,
            rawSha256,
            manifestSha256: existingManifestSha,
            idempotent: true,
        };
    }

    // Write both via temp files, rename, rollback on failure.
    const manifestBytes = Buffer.from(JSON.stringify(manifest, null, 2) + '\n', 'utf8');
    const manifestSha256 = sha256Bytes(manifestBytes);
    const rawTmp = `${rawPath}.tmp-${process.pid}-${Date.now()}`;
    const manifestTmp = `${manifestPath}.tmp-${process.pid}-${Date.now()}`;
    let rawRenamed = false;

    try {
        fileSystem.writeFileSync(rawTmp, rawBody, { encoding: 'utf8', flag: 'wx' });
        fileSystem.writeFileSync(manifestTmp, manifestBytes, { encoding: 'utf8', flag: 'wx' });
        fileSystem.renameSync(rawTmp, rawPath);
        rawRenamed = true;
        fileSystem.renameSync(manifestTmp, manifestPath);
    } catch (err) {
        // Rollback: if raw was renamed but manifest was not, remove raw.
        try { fileSystem.unlinkSync(rawTmp); } catch { /* ignore */ }
        try { fileSystem.unlinkSync(manifestTmp); } catch { /* ignore */ }
        if (rawRenamed) {
            try { fileSystem.unlinkSync(rawPath); } catch { /* ignore */ }
        }
        throw Object.assign(
            new Error(`capture pair write failed: ${err.message}`),
            { code: 'SAFETY_ERROR' }
        );
    }

    // Final readback verification — both files must be readable, regular,
    // and byte-identical to what we wrote.
    const rawReadback = fileSystem.readFileSync(rawPath);
    if (sha256Bytes(rawReadback) !== rawSha256) {
        try { fileSystem.unlinkSync(rawPath); } catch { /* ignore */ }
        try { fileSystem.unlinkSync(manifestPath); } catch { /* ignore */ }
        throw Object.assign(
            new Error('capture pair readback failed: raw hash mismatch'),
            { code: 'SAFETY_ERROR' }
        );
    }
    const manifestReadback = fileSystem.readFileSync(manifestPath, 'utf8');
    if (sha256Text(manifestReadback) !== manifestSha256) {
        try { fileSystem.unlinkSync(rawPath); } catch { /* ignore */ }
        try { fileSystem.unlinkSync(manifestPath); } catch { /* ignore */ }
        throw Object.assign(
            new Error('capture pair readback failed: manifest hash mismatch'),
            { code: 'SAFETY_ERROR' }
        );
    }

    return {
        rawPath,
        manifestPath,
        rawSha256,
        manifestSha256,
        idempotent: false,
    };
}

// ─────────────────────────────────────────────────────────────
// Run state
// ─────────────────────────────────────────────────────────────

function defaultRunState(plan, options = {}) {
    return {
        schema_version: 'fotmob-detail-capture-run-state/v1',
        run_id: String(options.runId || ''),
        plan_sha256: String(plan.plan_business_sha256 || ''),
        source_artifact_sha256: String(plan.source_artifact_sha256 || ''),
        authorization_id: String(options.authorizationId || ''),
        max_requests: Number(options.maxRequests || 0),
        delay_ms: Number(options.delayMs || 0),
        started_at: String(options.startedAt || ''),
        completed_ordinals: [],
        stopped_at_ordinal: null,
        stop_reason: null,
        status: 'in_progress',
    };
}

function writeRunState(runDir, runState, fsImpl = fs) {
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
    return parsed;
}

/**
 * Check whether a candidate ordinal already has a complete, matching pair.
 * Used for resume: completed candidates must never be fetched again.
 *
 * @param {object} args - { runDir, ordinal, sourceMatchId, expectedManifestSha256, fsImpl }
 * @returns {{ completed: boolean, state: 'complete'|'partial'|'mismatch'|'absent'|'error', detail: string }}
 */
function checkCompletedPair(args = {}) {
    const fileSystem = args.fsImpl || fs;
    const runDir = String(args.runDir || '');
    const ordinal = Number(args.ordinal || 0);
    const sourceMatchId = String(args.sourceMatchId || '');
    const rawFileName = `${ordinal}-${sourceMatchId}.html`;
    const manifestFileName = `${ordinal}-${sourceMatchId}.manifest.json`;
    const rawPath = path.join(runDir, 'captures', rawFileName);
    const manifestPath = path.join(runDir, 'captures', manifestFileName);

    const rawStat = assertRegularFilePath(rawPath, fileSystem, 'resume check');
    const manifestStat = assertRegularFilePath(manifestPath, fileSystem, 'resume check');

    if (rawStat === null && manifestStat === null) return { completed: false, state: 'absent', detail: 'pair absent' };
    if (rawStat === null !== (manifestStat === null)) {
        return {
            completed: false,
            state: 'partial',
            detail: `partial pair: raw=${rawStat !== null}, manifest=${manifestStat !== null}`,
        };
    }

    // Both present: verify hash binding.
    const rawSha = sha256Bytes(fileSystem.readFileSync(rawPath));
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
    if (manifest.body_sha256 !== rawSha) {
        return { completed: false, state: 'mismatch', detail: 'manifest body_sha256 does not match raw file' };
    }
    if (manifest.raw_file_relative_path !== rawFileName) {
        return { completed: false, state: 'mismatch', detail: 'manifest raw_file_relative_path mismatch' };
    }
    if (args.expectedManifestSha256 && manifest.capture_manifest_sha256 !== args.expectedManifestSha256) {
        return { completed: false, state: 'mismatch', detail: 'manifest content differs from expected' };
    }

    return { completed: true, state: 'complete', detail: 'pair complete and matching' };
}

// ─────────────────────────────────────────────────────────────
// Replay (fully offline)
// ─────────────────────────────────────────────────────────────

/**
 * Replay one captured pair into a structured detail artifact, fully offline.
 *
 * @param {object} args - {
 *   runDir, ordinal, sourceMatchId,
 *   plan (for identity expectations),
 *   parser: { extractFromHtml, transformToApiFormat, parseFotMobRaw },
 *   parsedAt (ISO string),
 *   parserCodeRevision (40-hex),
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
    const rawFileName = `${ordinal}-${sourceMatchId}.html`;
    const manifestFileName = `${ordinal}-${sourceMatchId}.manifest.json`;
    const rawPath = path.join(runDir, 'captures', rawFileName);
    const manifestPath = path.join(runDir, 'captures', manifestFileName);
    const parser = args.parser || {};
    const plan = args.plan || {};
    const planCandidates = Array.isArray(plan.candidates) ? plan.candidates : [];
    const planCandidate = planCandidates.find(c => String(c.source_match_id) === sourceMatchId) || {};

    // Raw hash must match manifest.
    const rawBytes = fileSystem.readFileSync(rawPath);
    const rawSha256 = sha256Bytes(rawBytes);
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
    if (manifest.body_sha256 !== rawSha256) {
        throw Object.assign(new Error('replay failed: raw hash does not match manifest body_sha256'), { code: 'SAFETY_ERROR' });
    }
    if (manifest.source_match_id !== sourceMatchId) {
        throw Object.assign(new Error('replay failed: manifest source_match_id mismatch'), { code: 'SAFETY_ERROR' });
    }
    if (manifest.observed_match_id !== sourceMatchId) {
        throw Object.assign(new Error('replay failed: observed_match_id does not match source_match_id'), { code: 'SAFETY_ERROR' });
    }

    if (typeof parser.extractFromHtml !== 'function' ||
        typeof parser.transformToApiFormat !== 'function' ||
        typeof parser.parseFotMobRaw !== 'function') {
        throw Object.assign(new Error('replay failed: parser dependencies missing'), { code: 'INPUT_ERROR' });
    }

    // Parse chain: HTML → __NEXT_DATA__ → API format (raw_data) → structured.
    let nextData;
    try {
        const extraction = parser.extractFromHtml(rawBytes.toString('utf8'));
        if (!extraction || extraction.success === false || !extraction.data) {
            throw Object.assign(new Error('replay failed: no __NEXT_DATA__ payload'), { code: 'REPLAY_PARSE_ERROR' });
        }
        nextData = extraction.data;
    } catch (err) {
        throw Object.assign(new Error(`replay failed: extraction error: ${err.message}`), { code: 'REPLAY_PARSE_ERROR' });
    }

    let transformed;
    try {
        transformed = parser.transformToApiFormat(nextData, sourceMatchId);
    } catch (err) {
        throw Object.assign(new Error(`replay failed: transform error: ${err.message}`), { code: 'REPLAY_PARSE_ERROR' });
    }
    if (!transformed || typeof transformed !== 'object') {
        throw Object.assign(new Error('replay failed: transform returned no structured match data'), { code: 'REPLAY_PARSE_ERROR' });
    }

    const parsed = parser.parseFotMobRaw(transformed, sourceMatchId);
    if (!parsed || parsed.ok !== true || !parsed.data) {
        const errMsg = parsed && parsed.error ? parsed.error : 'unknown parser error';
        throw Object.assign(new Error(`replay failed: parseFotMobRaw: ${errMsg}`), { code: 'REPLAY_PARSE_ERROR' });
    }

    // Structured payload hash over the deterministic business projection.
    const structuredProjection = {
        matchId: parsed.data.match?.externalId ?? sourceMatchId,
        homeTeam: parsed.data.homeTeam,
        awayTeam: parsed.data.awayTeam,
        stats: parsed.data.stats,
        lineup: parsed.data.lineup,
        events: parsed.data.events,
        shotmap: parsed.data.shotmap,
        playerStats: parsed.data.playerStats,
    };
    const structuredPayloadSha256 = canonicalJsonHash(structuredProjection);

    const artifact = {
        schema_version: 'fotmob-match-detail-artifact/v1',
        source_provider: 'FotMob',
        source_match_id: sourceMatchId,
        candidate_id: String(planCandidate.candidate_id || ''),
        competition: String(planCandidate.competition || manifest.competition || 'Premier League'),
        season: String(planCandidate.season || manifest.season || ''),
        expected_identity: {
            home_team: String(planCandidate.home_team || ''),
            away_team: String(planCandidate.away_team || ''),
            kickoff_at: String(planCandidate.kickoff_at || ''),
        },
        observed_identity: {
            home_team: manifest.home_team || '',
            away_team: manifest.away_team || '',
            observed_match_id: manifest.observed_match_id || '',
        },
        raw_file_sha256: rawSha256,
        capture_manifest_sha256: resolveManifestSelfHash(manifest, sha256Text),
        stable_raw_payload_sha256: manifest.stable_raw_payload_sha256 || null,
        structured_payload_sha256: structuredPayloadSha256,
        parser_component: manifest.parser_component || 'NextDataParser+FotMobRawParser',
        parser_version: manifest.parser_version || null,
        parser_code_revision: String(args.parserCodeRevision || ''),
        parsed_at: String(args.parsedAt || ''),
        content: parsed.data,
        general: transformed.general || {},
        header: transformed.header || {},
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
 * Resolve the manifest's self-hash for the detail artifact contract.
 * Prefers the manifest's own field; derives it deterministically when the
 * manifest was produced without one.
 */
function resolveManifestSelfHash(manifest, sha256TextFn) {
    if (manifest && /^[0-9a-f]{64}$/.test(String(manifest.capture_manifest_sha256 || ''))) {
        return manifest.capture_manifest_sha256;
    }
    const clone = { ...manifest };
    delete clone.capture_manifest_sha256;
    return sha256TextFn(JSON.stringify(clone));
}

/**
 * Write a structured detail artifact to the replay directory (atomic,
 * no overwrite of different content, symlink rejection).
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
        network_requests_made: runState.network_requests_made || 0,
        database_writes: 0,
        real_fotmob_network_requests: runState.real_fotmob_network_requests || 0,
    };
}

function writeRunSummary(runDir, summary, fsImpl = fs) {
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
    checkCompletedPair,
    replayCapturePair,
    writeDetailArtifact,
    buildRunSummary,
    writeRunSummary,
    sha256Bytes,
};
