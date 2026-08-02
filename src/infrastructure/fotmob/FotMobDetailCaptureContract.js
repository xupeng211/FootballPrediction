'use strict';

// lifecycle: permanent
//
// FotMob bounded detail capture — contract module.
//
// Owns the three schema contracts used by the PLAN / CAPTURE / REPLAY
// pipeline and the match-detail content-validity gate:
//
//   1. input artifact contract (candidate-match-identity/v1 and
//      canonical-inventory-artifact/v2) — fail-closed validation before
//      any plan is built;
//   2. match-detail content-validity contract — HTTP 200 alone is never
//      sufficient; an empty SSR shell must fail with EMPTY_SSR_SHELL;
//   3. capture manifest schema (fotmob-match-detail-capture-manifest/v1)
//      and structured artifact schema (fotmob-match-detail-artifact/v1).
//
// This module is a leaf: it must not import the pipeline or retention
// modules. It reuses hashing helpers from FotMobCandidateExporter and
// FotMobRawDetailFetcher rather than re-implementing them.

const crypto = require('node:crypto');
const path = require('node:path');
const fs = require('node:fs');

const {
    isNumericExternalId,
    isStrictAbsoluteTimestamp,
    computeBusinessContentHash,
    computeV1IdentityProjectionHash,
    computeV2BusinessHash,
} = require('./FotMobCandidateExporter');

const {
    validateCanonicalRawDataShape,
    sha256StableRawPayload,
    buildStableRawPayload,
    canonicalizeJson,
    sha256CanonicalJson,
    sha256Text,
} = require('../services/FotMobRawDetailFetcher');

const {
    IDENTITY_MATCH,
    REVERSE_FIXTURE_DETECTED,
    CROSS_SEASON_SLUG_REUSE,
    UNRESOLVED_LARGE_GAP,
    UNKNOWN_DATE_COMPATIBILITY,
} = require('../services/FotMobRouteIdentityReconciler');

// ─────────────────────────────────────────────────────────────
// Constants
// ─────────────────────────────────────────────────────────────

const PLAN_SCHEMA_VERSION = 'fotmob-detail-capture-plan/v1';
const MANIFEST_SCHEMA_VERSION = 'fotmob-match-detail-capture-manifest/v1';
const DETAIL_ARTIFACT_SCHEMA_VERSION = 'fotmob-match-detail-artifact/v1';
const GENERATOR_COMPONENT = 'FotMobDetailCapturePipeline';
const NETWORK_AUTHORIZATION_MODE = 'explicit_network_authorization';

const REQUIRED_SOURCE_PROVIDER = 'FotMob';
const REQUIRED_COMPETITION = 'Premier League';
const REQUIRED_LEAGUE_ID = '47';

const VALID_SEASON_PATTERN = /^(\d{4})\/(\d{4})$/;

// Allowed content types for the match detail page.
const ALLOWED_CONTENT_TYPES = [
    'text/html',
    'application/xhtml+xml',
];

// Maximum reasonable body size for a FotMob match detail SSR page.
const MAX_BODY_BYTES = 8 * 1024 * 1024; // 8 MiB
const MIN_BODY_BYTES = 100;

// Captcha / WAF challenge markers (looked at in the body text only, never stored).
const BLOCK_MARKERS = [
    'captcha',
    'cf-challenge',
    'cloudflare',
    'access denied',
    'access_denied',
    'challenge',
    'blocked',
];

// ─────────────────────────────────────────────────────────────
// Small helpers
// ─────────────────────────────────────────────────────────────

function sha256Hex(buf) {
    return crypto.createHash('sha256').update(buf).digest('hex');
}

// Canonical deep-sort + SHA-256 over a JSON value. Delegates to the shared
// fetcher helpers rather than re-implementing the canonicalization.
function canonicalJsonHash(value) {
    return sha256CanonicalJson(value);
}

function isPlainObject(value) {
    return value !== null && typeof value === 'object' && !Array.isArray(value);
}

/**
 * Walk every path component of an absolute path and reject any symlink
 * ancestor (the leaf lstat alone misses intermediate symlinked directories).
 */
function assertNoSymlinkAncestors(absPath, fsImpl = fs) {
    const abs = path.resolve(String(absPath));
    const segments = abs.split(path.sep).filter(Boolean);
    let current = path.parse(abs).root;
    for (const segment of segments) {
        current = path.join(current, segment);
        let stat = null;
        try {
            stat = fsImpl.lstatSync(current);
        } catch { /* component absent is fine */ }
        if (stat && stat.isSymbolicLink()) {
            throw Object.assign(
                new Error(`path component must not be a symlink: ${current}`),
                { code: 'SAFETY_ERROR' }
            );
        }
    }
    return abs;
}

function assertRegularInputFile(filePath, fsImpl = fs) {
    // Symlink rejection: lstat resolves the path itself, never the link target.
    let stat;
    try {
        stat = fsImpl.lstatSync(filePath);
    } catch (err) {
        throw Object.assign(
            new Error(`input file not readable: ${filePath}`),
            { code: 'INPUT_ERROR' }
        );
    }
    if (stat.isSymbolicLink() || !stat.isFile()) {
        throw Object.assign(
            new Error(`input must be a regular file, not a symlink or directory: ${filePath}`),
            { code: 'SAFETY_ERROR' }
        );
    }
    return stat;
}

function readInputFile(filePath, fsImpl = fs) {
    assertRegularInputFile(filePath, fsImpl);
    const bytes = fsImpl.readFileSync(filePath);
    let parsed;
    try {
        parsed = JSON.parse(bytes.toString('utf8'));
    } catch (err) {
        throw Object.assign(
            new Error(`input artifact is not valid JSON: ${filePath}`),
            { code: 'INPUT_ERROR' }
        );
    }
    return {
        bytes,
        parsed,
        sha256: sha256Hex(bytes),
    };
}

// ─────────────────────────────────────────────────────────────
// Input artifact contract
// ─────────────────────────────────────────────────────────────

function validateCandidateIdentityV1Document(doc) {
    const errors = [];
    if (!isPlainObject(doc)) return { ok: false, errors: ['document is not an object'] };
    if (doc.schema_version !== 'candidate-match-identity/v1' &&
        doc.schema_version !== 'candidate-match-identity.v1') {
        errors.push(`unsupported schema_version: ${doc.schema_version}`);
    }
    const sourceProvider = doc.source_provider ?? doc.snapshot?.source_provider;
    if (sourceProvider !== REQUIRED_SOURCE_PROVIDER) {
        errors.push(`source_provider must be ${REQUIRED_SOURCE_PROVIDER}`);
    }
    const leagueId = doc.league_id ?? doc.snapshot?.league_id;
    const competition = doc.competition ?? doc.snapshot?.competition;
    if (leagueId !== undefined && String(leagueId) !== REQUIRED_LEAGUE_ID) {
        errors.push(`league_id must be ${REQUIRED_LEAGUE_ID}`);
    }
    if (competition !== undefined && competition !== REQUIRED_COMPETITION) {
        errors.push(`competition must be ${REQUIRED_COMPETITION}`);
    }
    if (!Array.isArray(doc.candidates)) {
        errors.push('candidates must be an array');
        return { ok: errors.length === 0, errors };
    }
    return { ok: errors.length === 0, errors };
}

// eslint-disable-next-line complexity
function validateCanonicalV2Document(doc) {
    const errors = [];
    if (!isPlainObject(doc)) return { ok: false, errors: ['document is not an object'] };
    if (doc.schema_version !== 'canonical-inventory-artifact/v2' &&
        doc.schema_version !== 'canonical-inventory-artifact.v2') {
        errors.push(`unsupported schema_version: ${doc.schema_version}`);
    }
    // Real producer shape (FotMobCandidateExporter.buildV2OutputDocument):
    // { schema_version, extracted_at, artifact: { source_provider,
    //   competition, seasons, candidate_count, per_season_counts,
    //   identity_projection_hash, business_hash, ... }, candidates }.
    // Top-level / snapshot fallbacks are accepted for hand-authored inputs.
    const provider = doc.artifact?.source_provider ?? doc.source_provider ?? doc.snapshot?.source_provider;
    if (provider !== REQUIRED_SOURCE_PROVIDER) {
        errors.push(`source_provider must be ${REQUIRED_SOURCE_PROVIDER}`);
    }
    const leagueId = doc.league_id ?? doc.snapshot?.league_id;
    const competition = doc.artifact?.competition ?? doc.competition ?? doc.snapshot?.competition;
    if (leagueId !== undefined && String(leagueId) !== REQUIRED_LEAGUE_ID) {
        errors.push(`league_id must be ${REQUIRED_LEAGUE_ID}`);
    }
    if (competition !== undefined && competition !== REQUIRED_COMPETITION) {
        errors.push(`competition must be ${REQUIRED_COMPETITION}`);
    }
    const candidates = doc.candidates ?? doc.snapshot?.candidates;
    if (!Array.isArray(candidates)) {
        errors.push('candidates must be an array (top level or snapshot.candidates)');
        return { ok: errors.length === 0, errors };
    }
    return { ok: errors.length === 0, errors };
}

/**
 * Validate a candidate artifact (v1 or v2) as input for plan building.
 * Fails closed on: unknown schema, wrong provider, wrong league,
 * wrong competition, symlink input, malformed candidates, duplicate
 * candidate ids, duplicate source_match_ids, non-numeric source ids,
 * invalid kickoff timestamps, missing identity fields.
 *
 * @param {object} loaded - { parsed, sha256 } from readInputFile
 * @returns {{ ok: boolean, schema: string, candidates: Array, errors: string[],
 *             artifact_sha256: string, business_hash: string|null }}
 */
/* eslint-disable-next-line complexity */
function validateCandidateArtifact(loaded) {
    if (!isPlainObject(loaded) || !isPlainObject(loaded.parsed)) {
        return { ok: false, schema: null, candidates: [], errors: ['artifact payload missing'], artifact_sha256: null, business_hash: null };
    }
    const doc = loaded.parsed;
    const sha256 = loaded.sha256;

    const schema = String(doc.schema_version || doc.schema || '');
    let base;
    if (schema.startsWith('candidate-match-identity')) {
        base = validateCandidateIdentityV1Document(doc);
        base.schema = 'candidate-match-identity/v1';
    } else if (schema.startsWith('canonical-inventory-artifact')) {
        base = validateCanonicalV2Document(doc);
        base.schema = 'canonical-inventory-artifact/v2';
    } else {
        base = {
            ok: false,
            errors: [`unknown artifact schema: ${schema}`],
            schema: schema || 'unknown',
        };
    }
    if (!base.ok) {
        return { ok: false, ...base, candidates: [], artifact_sha256: sha256, business_hash: null };
    }

    const candidates = doc.candidates ?? doc.snapshot?.candidates ?? [];
    const errors = [];
    const seenCandidateIds = new Set();
    const seenSourceIds = new Set();

    for (let i = 0; i < candidates.length; i += 1) {
        const c = candidates[i];
        const label = `candidates[${i}]`;
        if (!isPlainObject(c)) {
            errors.push(`${label} is not an object`);
            continue;
        }
        const candidateId = c.candidate_id ?? c.id;
        const sourceId = c.source_match_id ?? c.external_id ?? c.id;
        const season = c.season;
        const homeTeam = c.home_team ?? c.homeTeam;
        const awayTeam = c.away_team ?? c.awayTeam;
        const kickoffAt = c.kickoff_at ?? c.kickoffAt ?? c.kickoff_time;

        if (candidateId === undefined || candidateId === null || String(candidateId).trim() === '') {
            errors.push(`${label}: candidate id missing`);
        } else if (seenCandidateIds.has(String(candidateId))) {
            errors.push(`${label}: duplicate candidate id ${candidateId}`);
        } else {
            seenCandidateIds.add(String(candidateId));
        }

        if (!isNumericExternalId(String(sourceId))) {
            errors.push(`${label}: source_match_id must be numeric, got ${JSON.stringify(sourceId)}`);
        } else if (seenSourceIds.has(String(sourceId))) {
            errors.push(`${label}: duplicate source_match_id ${sourceId}`);
        } else {
            seenSourceIds.add(String(sourceId));
        }

        if (typeof season !== 'string' || !VALID_SEASON_PATTERN.test(season)) {
            errors.push(`${label}: season must be YYYY/YYYY, got ${JSON.stringify(season)}`);
        }
        if (typeof homeTeam !== 'string' || homeTeam.trim() === '') {
            errors.push(`${label}: home_team missing`);
        }
        if (typeof awayTeam !== 'string' || awayTeam.trim() === '') {
            errors.push(`${label}: away_team missing`);
        }
        if (homeTeam === awayTeam) {
            errors.push(`${label}: home_team must differ from away_team`);
        }
        if (typeof kickoffAt !== 'string' || !isStrictAbsoluteTimestamp(kickoffAt)) {
            errors.push(`${label}: kickoff_at must be a strict ISO timestamp with timezone, got ${JSON.stringify(kickoffAt)}`);
        }
    }

    if (errors.length > 0) {
        return { ok: false, schema: base.schema, candidates: [], errors, artifact_sha256: sha256, business_hash: null };
    }

    // Business hash verification: v1 uses snapshot.business_content_sha256;
    // v2 (real producer shape) carries artifact.identity_projection_hash and
    // artifact.business_hash computed with the exporter's own dual hashes.
    let businessHash = null;
    const statedHash = doc.business_content_sha256 ?? doc.snapshot?.business_content_sha256;
    if (base.schema === 'canonical-inventory-artifact/v2') {
        const statedV2 = doc.artifact?.identity_projection_hash ?? doc.snapshot?.identity_projection_hash ?? null;
        const statedV2Business = doc.artifact?.business_hash ?? doc.snapshot?.business_hash ?? null;
        businessHash = statedV2 ?? statedV2Business;
        if (statedV2) {
            const computed = computeV1IdentityProjectionHash(candidates);
            if (computed !== statedV2) {
                errors.push(`v2 identity hash mismatch: stated ${statedV2}, computed ${computed}`);
            }
        }
        if (statedV2Business) {
            const computed = computeV2BusinessHash(candidates);
            if (computed !== statedV2Business) {
                errors.push(`v2 business hash mismatch: stated ${statedV2Business}, computed ${computed}`);
            }
        }
        const statedCount = doc.artifact?.candidate_count;
        if (statedCount !== undefined && Number(statedCount) !== candidates.length) {
            errors.push(`v2 candidate_count mismatch: stated ${statedCount}, actual ${candidates.length}`);
        }
    } else {
        businessHash = statedHash || null;
        if (statedHash) {
            const computed = computeBusinessContentHash(candidates);
            if (computed !== statedHash) {
                errors.push(`v1 business hash mismatch: stated ${statedHash}, computed ${computed}`);
            }
        }
    }

    if (errors.length > 0) {
        return { ok: false, schema: base.schema, candidates: [], errors, artifact_sha256: sha256, business_hash: businessHash };
    }

    return {
        ok: true,
        schema: base.schema,
        candidates,
        errors: [],
        artifact_sha256: sha256,
        business_hash: businessHash,
    };
}

/**
 * Convenience: read + validate an artifact file in one call.
 */
function readAndValidateCandidateArtifact(filePath, fsImpl = fs) {
    const loaded = readInputFile(filePath, fsImpl);
    const result = validateCandidateArtifact(loaded);
    result.artifact_sha256 = loaded.sha256;
    return result;
}

// ─────────────────────────────────────────────────────────────
// Match-detail content-validity contract
// ─────────────────────────────────────────────────────────────

/**
 * Evaluate the content-validity contract for one fetched match detail.
 *
 * HTTP 200 is NOT sufficient. A successful capture must pass every gate.
 * Empty SSR shells (pageProps.ssr=false, no match data, translations only)
 * must fail with CONTENT_VALIDITY_FAIL / EMPTY_SSR_SHELL.
 *
 * @param {object} args - {
 *   http_status, content_type, body (string), body_sha256,
 *   fetcherResult (raw result of fetchFotMobRawDetail)
 * }
 * @returns {{ ok: boolean, error_code: string|null, checks: object }}
 */
/* eslint-disable-next-line complexity */
function evaluateContentValidity(args = {}) {
    const checks = {};
    const httpStatus = Number(args.http_status || 0);

    checks.http_status_ok = httpStatus === 200;
    const contentType = String(args.content_type || '');
    checks.content_type_allowed = ALLOWED_CONTENT_TYPES.some(
        t => contentType.toLowerCase().startsWith(t)
    );
    const body = typeof args.body === 'string' ? args.body : '';
    checks.body_non_empty = body.length > 0;
    checks.body_byte_range = body.length >= MIN_BODY_BYTES && body.length <= MAX_BODY_BYTES;
    checks.body_sha256_hex = /^[0-9a-f]{64}$/.test(String(args.body_sha256 || ''));

    // Block markers: any of these in the body (case-insensitive) means the
    // page is a challenge/block page, not a match detail page.
    const lowerBody = body.slice(0, 200000).toLowerCase();
    checks.no_block_marker = !BLOCK_MARKERS.some(m => lowerBody.includes(m));

    const fr = args.fetcherResult || {};
    checks.hydration_parse_ok = fr.hydration_parse_ok === true;
    checks.transformed_api_format = fr.transformed_api_format === true;
    checks.looks_like_valid_match_detail = fr.looks_like_valid_match_detail === true;

    const rawData = fr.raw_data || null;
    const rawDataShapeErrors = rawData ? validateCanonicalRawDataShape(rawData) : null;
    checks.raw_data_shape_valid = rawData
        ? Array.isArray(rawDataShapeErrors) && rawDataShapeErrors.length === 0
        : false;

    // observed inner match id
    const observedId = rawData && (rawData.matchId ?? null) !== null ? String(rawData.matchId) : null;
    checks.observed_match_id_present = observedId !== null;
    checks.observed_match_id_matches = observedId !== null && observedId === String(args.expected_match_id || '');

    // stable raw payload + stable hash format
    const stable = rawData ? buildStableRawPayload(rawData, {}, {}) : null;
    const stableHash = stable ? sha256StableRawPayload(stable) : null;
    checks.stable_raw_payload_present = stable !== null;
    checks.stable_hash_64hex = /^[0-9a-f]{64}$/.test(String(stableHash || ''));

    // route identity: no deterministic conflict
    // (reconcileRouteIdentity keys are spread at the top level of the
    // fetchFotMobRawDetail result, not nested under route_identity)
    const dateStatus = fr.date_compatibility_status || null;
    const identityStatus = fr.identity_reconciliation_status || null;
    // Values come from the reconciler's own exported constants (shared leaf
    // module) so the conflict set cannot drift from the reconciler's semantics.
    const CONFLICTING_DATE_STATUSES = [
        REVERSE_FIXTURE_DETECTED,
        CROSS_SEASON_SLUG_REUSE,
        UNKNOWN_DATE_COMPATIBILITY,
        UNRESOLVED_LARGE_GAP,
    ];
    checks.date_compatibility_not_conflicting =
        dateStatus === null || !CONFLICTING_DATE_STATUSES.includes(dateStatus);
    checks.identity_reconciliation_not_conflicting =
        identityStatus === null ||
        identityStatus === IDENTITY_MATCH ||
        identityStatus === 'accepted_schedule_detail_mapping';

    // home/away markers: team flags must not contradict expected teams
    const expectedHome = String(args.expected_home_team || '').trim();
    const expectedAway = String(args.expected_away_team || '').trim();
    checks.team_markers_not_conflicting = evaluateTeamMarkers(rawData, expectedHome, expectedAway);

    const allOk = Object.values(checks).every(v => v === true);

    // Empty-shell recognition: ssr=false, or a __NEXT_DATA__ page that
    // carries no match business fields at all (translations/fallback only),
    // or a page where parsing succeeded but no valid match detail emerged.
    let emptyShellDetected = false;
    const nextData = args.next_data || null;
    if (httpStatus === 200 && checks.hydration_parse_ok === true && !fr.looks_like_valid_match_detail) {
        emptyShellDetected = true;
    }
    if (nextData && nextData.props && nextData.props.pageProps) {
        const pp = nextData.props.pageProps;
        const hasBusinessFields = Boolean(pp.content || pp.general || pp.header || pp.matchId);
        if (pp.ssr === false || !hasBusinessFields) {
            emptyShellDetected = true;
        }
    }

    const ok = allOk && !emptyShellDetected;
    const errorCode = ok
        ? null
        : (emptyShellDetected ? 'EMPTY_SSR_SHELL' : 'CONTENT_VALIDITY_FAIL');

    return { ok, error_code: errorCode, checks, stable_raw_payload_sha256: stableHash || null };
}

function evaluateTeamMarkers(rawData, expectedHome, expectedAway) {
    if (!rawData || !rawData.general) return true;
    const g = rawData.general;
    const observedHome = String(g.homeTeam?.name ?? g.home_team?.name ?? g.home_team ?? '').trim();
    const observedAway = String(g.awayTeam?.name ?? g.away_team?.name ?? g.away_team ?? '').trim();
    if (!observedHome || !observedAway) return true; // markers absent — not a deterministic conflict
    if (expectedHome && expectedAway) {
        const homeMatches = normalizeTeamName(observedHome) === normalizeTeamName(expectedHome);
        const awayMatches = normalizeTeamName(observedAway) === normalizeTeamName(expectedAway);
        if (!homeMatches || !awayMatches) {
            // swapped legs or wrong teams are a deterministic conflict
            return false;
        }
    }
    return true;
}

function normalizeTeamName(name) {
    return String(name || '').toLowerCase().replace(/\s+/g, ' ').trim();
}

// ─────────────────────────────────────────────────────────────
// Capture manifest contract (fotmob-match-detail-capture-manifest/v1)
// ─────────────────────────────────────────────────────────────

const MANIFEST_REQUIRED_FIELDS = [
    'schema_version',
    'source_provider',
    'source_kind',
    'request_method',
    'request_url',
    'candidate_id',
    'source_match_id',
    'competition',
    'season',
    'home_team',
    'away_team',
    'kickoff_at',
    'candidate_identity_sha256',
    'source_plan_sha256',
    'source_artifact_sha256',
    'capture_run_id',
    'authorization_id',
    'request_ordinal',
    'request_budget',
    'delay_ms',
    'capture_started_at',
    'capture_completed_at',
    'http_status',
    'content_type',
    'body_byte_size',
    'body_sha256',
    'observed_match_id',
    'observed_match_id_match',
    'hydration_parse_ok',
    'transformed_api_format',
    'looks_like_valid_match_detail',
    'has_stats',
    'has_lineup',
    'has_shotmap',
    'stable_raw_payload_sha256',
    'parser_component',
    'parser_version',
    'collector_component',
    'collector_code_revision',
    'raw_file_relative_path',
    'network_authorization_mode',
];

/* eslint-disable-next-line complexity */
function validateCaptureManifest(manifest) {
    const errors = [];
    if (!isPlainObject(manifest)) {
        return { ok: false, errors: ['manifest is not an object'] };
    }
    if (manifest.schema_version !== MANIFEST_SCHEMA_VERSION) {
        errors.push(`schema_version must be ${MANIFEST_SCHEMA_VERSION}`);
    }
    if (manifest.source_provider !== REQUIRED_SOURCE_PROVIDER) {
        errors.push('source_provider must be FotMob');
    }
    if (manifest.source_kind !== 'match_detail_page') {
        errors.push('source_kind must be match_detail_page');
    }
    if (manifest.request_method !== 'GET') {
        errors.push('request_method must be GET');
    }
    if (!/^https:\/\/www\.fotmob\.com\/match\/[0-9]+$/.test(String(manifest.request_url || ''))) {
        errors.push('request_url must match https://www.fotmob.com/match/<digits>');
    }
    if (!/^[0-9a-f]{64}$/.test(String(manifest.body_sha256 || ''))) {
        errors.push('body_sha256 must be 64 lowercase hex');
    }
    if (!/^[0-9a-f]{64}$/.test(String(manifest.stable_raw_payload_sha256 || ''))) {
        errors.push('stable_raw_payload_sha256 must be 64 lowercase hex');
    }
    if (!/^[0-9a-f]{40}$/.test(String(manifest.collector_code_revision || ''))) {
        errors.push('collector_code_revision must be 40-hex');
    }
    if (String(manifest.raw_file_relative_path || '').includes('..')) {
        errors.push('raw_file_relative_path must not traverse directories');
    }
    for (const field of MANIFEST_REQUIRED_FIELDS) {
        if (!(field in manifest) || manifest[field] === undefined || manifest[field] === null) {
            errors.push(`missing required field: ${field}`);
        }
    }
    return { ok: errors.length === 0, errors };
}

// ─────────────────────────────────────────────────────────────
// Structured detail artifact contract (fotmob-match-detail-artifact/v1)
// ─────────────────────────────────────────────────────────────

const DETAIL_ARTIFACT_REQUIRED_FIELDS = [
    'schema_version',
    'source_provider',
    'source_match_id',
    'candidate_id',
    'competition',
    'season',
    'expected_identity',
    'observed_identity',
    'raw_file_sha256',
    'capture_manifest_sha256',
    'stable_raw_payload_sha256',
    'structured_payload_sha256',
    'parser_component',
    'parser_version',
    'parser_code_revision',
    'parsed_at',
    'content',
    'general',
    'header',
    'matchId',
];

function validateDetailArtifact(artifact) {
    const errors = [];
    if (!isPlainObject(artifact)) {
        return { ok: false, errors: ['artifact is not an object'] };
    }
    if (artifact.schema_version !== DETAIL_ARTIFACT_SCHEMA_VERSION) {
        errors.push(`schema_version must be ${DETAIL_ARTIFACT_SCHEMA_VERSION}`);
    }
    if (artifact.source_provider !== REQUIRED_SOURCE_PROVIDER) {
        errors.push('source_provider must be FotMob');
    }
    if (!/^[0-9a-f]{64}$/.test(String(artifact.raw_file_sha256 || ''))) {
        errors.push('raw_file_sha256 must be 64 lowercase hex');
    }
    if (!/^[0-9a-f]{64}$/.test(String(artifact.capture_manifest_sha256 || ''))) {
        errors.push('capture_manifest_sha256 must be 64 lowercase hex');
    }
    if (!/^[0-9a-f]{64}$/.test(String(artifact.structured_payload_sha256 || ''))) {
        errors.push('structured_payload_sha256 must be 64 lowercase hex');
    }
    for (const field of DETAIL_ARTIFACT_REQUIRED_FIELDS) {
        if (!(field in artifact) || artifact[field] === undefined || artifact[field] === null) {
            errors.push(`missing required field: ${field}`);
        }
    }
    return { ok: errors.length === 0, errors };
}

module.exports = {
    PLAN_SCHEMA_VERSION,
    MANIFEST_SCHEMA_VERSION,
    DETAIL_ARTIFACT_SCHEMA_VERSION,
    GENERATOR_COMPONENT,
    NETWORK_AUTHORIZATION_MODE,
    REQUIRED_SOURCE_PROVIDER,
    REQUIRED_COMPETITION,
    REQUIRED_LEAGUE_ID,
    VALID_SEASON_PATTERN,
    ALLOWED_CONTENT_TYPES,
    MAX_BODY_BYTES,
    MIN_BODY_BYTES,
    BLOCK_MARKERS,
    MANIFEST_REQUIRED_FIELDS,
    DETAIL_ARTIFACT_REQUIRED_FIELDS,
    sha256Hex,
    sha256Text,
    canonicalJsonHash,
    isPlainObject,
    readInputFile,
    assertRegularInputFile,
    assertNoSymlinkAncestors,
    validateCandidateArtifact,
    readAndValidateCandidateArtifact,
    evaluateContentValidity,
    validateCaptureManifest,
    validateDetailArtifact,
    normalizeTeamName,
    canonicalizeJson,
    sha256CanonicalJson,
    // re-exported helpers (for hash consistency with the exporter)
    computeBusinessContentHash,
    computeV1IdentityProjectionHash,
    computeV2BusinessHash,
};
