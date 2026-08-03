'use strict';

/* eslint-disable max-lines */

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
const PAYLOAD_SCHEMA_VERSION = 'fotmob-match-detail-capture-payload/v1';
const DETAIL_ARTIFACT_SCHEMA_VERSION = 'fotmob-match-detail-artifact/v1';
const GENERATOR_COMPONENT = 'FotMobDetailCapturePipeline';
const NETWORK_AUTHORIZATION_MODE = 'explicit_network_authorization';

// Trusted observed match-id sources — the observed ID must come from a real
// RESPONSE payload field, never from the request input / fallback / URL, and
// never from a transformer-injected field. R3-P1: payload.matchId is the
// NextData transformer's copy of the REQUEST-side id and is synthetic; only
// the raw-hydration allowlist paths extracted pre-transform qualify:
//   - 'general.matchId' → raw pageProps.general.matchId
//   - 'matchId' → raw top-level pageProps.matchId
// (Source names carry the raw field path without the pageProps container,
// so persisted provenance never leaks the raw-data marker itself.)
const TRUSTED_OBSERVED_ID_SOURCES = new Set(['general.matchId', 'matchId']);

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

// Captcha / WAF challenge markers (looked at in the body text only, never
// stored). Only STRUCTURED challenge markers are matched — generic
// natural-language substrings like 'challenge' or 'blocked' can appear in
// legitimate football content and must never stop a valid run (Codex
// re-review P2).
const BLOCK_MARKERS = [
    'captcha',
    'cf-challenge',
    'cf-chl-',
    'cf-error-details',
    'challenge-platform',
    'turnstile',
    'cloudflare-challenge',
    'managed-challenge',
    'just a moment',
    'attention required!',
    'access denied',
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

/**
 * Ensure an absolute directory path is a REAL directory tree: walk every
 * component from the root, reject any symlink component (a recursive
 * mkdirSync would silently follow pre-existing symlinked descendants),
 * create missing components one level at a time, and verify immediately
 * after creation. Rejects non-directory components and symlinks.
 *
 * @param {string} absDirPath - absolute target directory
 * @param {object} fsImpl? - injected filesystem (tests)
 * @returns {string} the resolved absolute path
 */
function ensureRealDirectoryTree(absDirPath, fsImpl = fs) {
    const abs = path.resolve(String(absDirPath));
    const segments = abs.split(path.sep).filter(Boolean);
    let current = path.parse(abs).root;
    for (const segment of segments) {
        current = path.join(current, segment);
        let stat = null;
        try {
            stat = fsImpl.lstatSync(current);
        } catch { /* absent */ }
        if (stat) {
            if (stat.isSymbolicLink()) {
                throw Object.assign(
                    new Error(`path component must not be a symlink: ${current}`),
                    { code: 'SAFETY_ERROR' }
                );
            }
            if (!stat.isDirectory()) {
                throw Object.assign(
                    new Error(`path component must be a directory: ${current}`),
                    { code: 'SAFETY_ERROR' }
                );
            }
        } else {
            // Create one level at a time — never a single recursive mkdir
            // that could cross a pre-existing symlink unchecked.
            fsImpl.mkdirSync(current);
            let created = null;
            try {
                created = fsImpl.lstatSync(current);
            } catch { /* treat as missing */ }
            if (!created || created.isSymbolicLink() || !created.isDirectory()) {
                throw Object.assign(
                    new Error(`failed to create real directory: ${current}`),
                    { code: 'SAFETY_ERROR' }
                );
            }
        }
    }
    const finalStat = fsImpl.lstatSync(abs);
    if (!finalStat || finalStat.isSymbolicLink() || !finalStat.isDirectory()) {
        throw Object.assign(
            new Error(`target must be a real directory: ${abs}`),
            { code: 'SAFETY_ERROR' }
        );
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
// Capture plan contract (fotmob-detail-capture-plan/v1)
// ─────────────────────────────────────────────────────────────

const PLAN_REQUIRED_FIELDS = [
    'schema_version',
    'source_provider',
    'source_artifact_schema',
    'source_artifact_sha256',
    'source_artifact_business_hash',
    'competition',
    'league_id',
    'selected_seasons',
    'selected_candidate_count',
    'candidates',
    'plan_business_sha256',
    'generated_at',
    'generator_component',
    'generator_code_revision',
];

/**
 * Rebuild the canonical business projection of a capture plan. The PLAN
 * builder and every CAPTURE-side validator must use this single function so
 * the hash logic cannot drift: the recomputed value is compared against the
 * plan's self-declared plan_business_sha256 and the operator-provided
 * --expected-plan-sha256.
 *
 * The projection is derived from the plan's actual business fields:
 *   - ordinal is derived as index+1 (must equal the stored ordinal);
 *   - expected_request_path is derived as /match/<source_match_id> (must
 *     equal the stored value);
 *   - candidate_identity_sha256 is recomputed over the identity projection;
 *   - all other candidate fields are copied verbatim so any tampering with
 *     teams, season, kickoff, ids or count changes the recomputed hash.
 *
 * @param {object} plan - plan document
 * @returns {object} the canonical business projection
 */
function computeCapturePlanBusinessProjection(plan) {
    const candidates = (Array.isArray(plan.candidates) ? plan.candidates : []).map((c, index) => {
        const ordinal = index + 1;
        const sourceMatchId = String(c.source_match_id ?? '');
        const identity = {
            source_match_id: sourceMatchId,
            competition: String(c.competition ?? ''),
            season: String(c.season ?? ''),
            home_team: String(c.home_team ?? ''),
            away_team: String(c.away_team ?? ''),
            kickoff_at: String(c.kickoff_at ?? ''),
        };
        return {
            ordinal,
            candidate_id: String(c.candidate_id ?? ''),
            source_match_id: sourceMatchId,
            competition: String(c.competition ?? ''),
            season: String(c.season ?? ''),
            home_team: String(c.home_team ?? ''),
            away_team: String(c.away_team ?? ''),
            kickoff_at: String(c.kickoff_at ?? ''),
            expected_request_path: `/match/${sourceMatchId}`,
            candidate_identity_sha256: canonicalJsonHash(identity),
        };
    });
    return {
        source_provider: String(plan.source_provider ?? ''),
        source_artifact_schema: String(plan.source_artifact_schema ?? ''),
        source_artifact_sha256: String(plan.source_artifact_sha256 ?? ''),
        source_artifact_business_hash: plan.source_artifact_business_hash === null
            ? null
            : String(plan.source_artifact_business_hash ?? ''),
        competition: String(plan.competition ?? ''),
        league_id: String(plan.league_id ?? ''),
        selected_seasons: Array.isArray(plan.selected_seasons) ? plan.selected_seasons.map(String).sort() : [],
        selected_candidate_count: candidates.length,
        candidates,
    };
}

/**
 * Validate a capture plan and recompute its business hash from the actual
 * business fields. Fails closed on any tampering — including the plan's own
 * self-declared plan_business_sha256 field.
 *
 * All validation happens BEFORE any mkdir, run-state write, fetch or
 * artifact write (callers must invoke this before creating anything).
 *
 * @param {object} plan - plan document
 * @returns {{ ok: boolean, errors: string[], recomputed_sha256: string|null, projection: object|null }}
 */
/* eslint-disable-next-line complexity */
function validateAndRecomputeCapturePlan(plan) {
    const errors = [];
    if (!isPlainObject(plan)) {
        return { ok: false, errors: ['plan is not an object'], recomputed_sha256: null, projection: null };
    }
    if (plan.schema_version !== PLAN_SCHEMA_VERSION) {
        errors.push(`schema_version must be ${PLAN_SCHEMA_VERSION}`);
    }
    for (const field of PLAN_REQUIRED_FIELDS) {
        if (!(field in plan) || plan[field] === undefined || plan[field] === null) {
            errors.push(`missing required field: ${field}`);
        }
    }
    if (errors.length > 0) {
        return { ok: false, errors, recomputed_sha256: null, projection: null };
    }

    if (plan.source_provider !== REQUIRED_SOURCE_PROVIDER) {
        errors.push(`source_provider must be ${REQUIRED_SOURCE_PROVIDER}`);
    }
    if (String(plan.league_id) !== REQUIRED_LEAGUE_ID) {
        errors.push(`league_id must be ${REQUIRED_LEAGUE_ID}`);
    }
    if (plan.competition !== REQUIRED_COMPETITION) {
        errors.push(`competition must be ${REQUIRED_COMPETITION}`);
    }
    if (!/^[0-9a-f]{64}$/.test(String(plan.source_artifact_sha256 || ''))) {
        errors.push('source_artifact_sha256 must be 64 lowercase hex');
    }
    const artifactBusinessHash = plan.source_artifact_business_hash;
    if (artifactBusinessHash !== null && !/^[0-9a-f]{64}$/.test(String(artifactBusinessHash || ''))) {
        errors.push('source_artifact_business_hash must be 64 lowercase hex or null');
    }
    if (!/^[0-9a-f]{40}$/.test(String(plan.generator_code_revision || ''))) {
        errors.push('generator_code_revision must be 40-hex');
    }
    if (!Array.isArray(plan.candidates)) {
        errors.push('candidates must be an array');
    } else {
        if (Number(plan.selected_candidate_count) !== plan.candidates.length) {
            errors.push(
                `selected_candidate_count mismatch: stated ${plan.selected_candidate_count}, actual ${plan.candidates.length}`
            );
        }
        const seenOrdinals = new Set();
        const seenSourceIds = new Set();
        const seenCandidateIds = new Set();
        for (let i = 0; i < plan.candidates.length; i += 1) {
            const c = plan.candidates[i];
            const label = `candidates[${i}]`;
            if (!isPlainObject(c)) {
                errors.push(`${label} is not an object`);
                continue;
            }
            const ordinal = Number(c.ordinal || 0);
            if (ordinal !== i + 1) {
                errors.push(`${label}: ordinal must be ${i + 1}, got ${c.ordinal}`);
            } else if (seenOrdinals.has(ordinal)) {
                errors.push(`${label}: duplicate ordinal ${ordinal}`);
            } else {
                seenOrdinals.add(ordinal);
            }
            const sourceMatchId = String(c.source_match_id || '');
            if (!/^\d+$/.test(sourceMatchId)) {
                errors.push(`${label}: source_match_id must be numeric, got ${JSON.stringify(c.source_match_id)}`);
            } else if (seenSourceIds.has(sourceMatchId)) {
                errors.push(`${label}: duplicate source_match_id ${sourceMatchId}`);
            } else {
                seenSourceIds.add(sourceMatchId);
            }
            const candidateId = String(c.candidate_id || '');
            if (candidateId === '') {
                errors.push(`${label}: candidate_id missing`);
            } else if (seenCandidateIds.has(candidateId)) {
                errors.push(`${label}: duplicate candidate_id ${candidateId}`);
            } else {
                seenCandidateIds.add(candidateId);
            }
            if (c.expected_request_path !== `/match/${sourceMatchId}`) {
                errors.push(
                    `${label}: expected_request_path must be derived as /match/<source_match_id>, got ${JSON.stringify(c.expected_request_path)}`
                );
            }
            if (typeof c.season !== 'string' || !VALID_SEASON_PATTERN.test(c.season)) {
                errors.push(`${label}: season must be YYYY/YYYY, got ${JSON.stringify(c.season)}`);
            }
            // P2 (Codex re-review on a5d63af60): per-candidate scope must
            // CROSS-CHECK the plan's declared authorization scope, not just
            // be hashed self-consistently. A plan declaring Premier League /
            // selected_seasons while its candidates carry a different
            // competition or a season outside the declared set is a
            // self-consistent but out-of-scope document: the recomputed plan
            // hash proves internal consistency, not authorization. The
            // candidate's competition must equal the plan's declared
            // competition and its season must be one of the declared
            // selected_seasons — otherwise the CAPTURE gate would authorize
            // requests for matches the plan never scoped.
            if (String(c.competition ?? '') !== String(plan.competition ?? '')) {
                errors.push(
                    `${label}: competition ${JSON.stringify(c.competition)} must equal the plan's declared competition ${JSON.stringify(plan.competition)}`
                );
            }
            const declaredSeasons = (Array.isArray(plan.selected_seasons) ? plan.selected_seasons : []).map(String);
            if (!declaredSeasons.includes(String(c.season ?? ''))) {
                errors.push(`${label}: season ${JSON.stringify(c.season)} must be one of the plan's selected_seasons`);
            }
            if (typeof c.home_team !== 'string' || c.home_team.trim() === '') {
                errors.push(`${label}: home_team missing`);
            }
            if (typeof c.away_team !== 'string' || c.away_team.trim() === '') {
                errors.push(`${label}: away_team missing`);
            }
            if (c.home_team === c.away_team) {
                errors.push(`${label}: home_team must differ from away_team`);
            }
            if (typeof c.kickoff_at !== 'string' || !isStrictAbsoluteTimestamp(c.kickoff_at)) {
                errors.push(`${label}: kickoff_at must be a strict ISO timestamp with timezone, got ${JSON.stringify(c.kickoff_at)}`);
            }
            const recomputedIdentity = canonicalJsonHash({
                source_match_id: sourceMatchId,
                competition: String(c.competition ?? ''),
                season: String(c.season ?? ''),
                home_team: String(c.home_team ?? ''),
                away_team: String(c.away_team ?? ''),
                kickoff_at: String(c.kickoff_at ?? ''),
            });
            if (c.candidate_identity_sha256 !== recomputedIdentity) {
                errors.push(`${label}: candidate_identity_sha256 mismatch (tampering)`);
            }
        }
    }
    if (errors.length > 0) {
        return { ok: false, errors, recomputed_sha256: null, projection: null };
    }

    const projection = computeCapturePlanBusinessProjection(plan);
    const recomputed = canonicalJsonHash(projection);
    if (recomputed !== String(plan.plan_business_sha256 || '')) {
        errors.push('plan_business_sha256 does not match recomputed business projection');
    }
    return {
        ok: errors.length === 0,
        errors,
        recomputed_sha256: recomputed,
        projection,
    };
}

/**
 * Compute the canonical self-hash of a capture manifest: SHA-256 over the
 * canonical JSON of every manifest field EXCEPT capture_manifest_sha256
 * itself. The builder and the validator must use this single helper.
 *
 * @param {object} manifest - capture manifest
 * @returns {string} 64-hex self-hash
 */
function computeCaptureManifestSelfHash(manifest) {
    const clone = Object.fromEntries(
        Object.entries(manifest || {}).filter(([k]) => k !== 'capture_manifest_sha256')
    );
    return canonicalJsonHash(clone);
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

    // Authorized-scope inheritance: when a candidate omits provider /
    // competition / league it deterministically inherits the validated
    // top-level values; a candidate that DECLARES a conflicting scope is
    // rejected rather than silently overridden (mixed artifacts fail).
    const topProvider = doc.artifact?.source_provider ?? doc.source_provider ?? doc.snapshot?.source_provider;
    const topCompetition = doc.artifact?.competition ?? doc.competition ?? doc.snapshot?.competition;
    const topLeagueId = doc.league_id ?? doc.snapshot?.league_id;

    for (let i = 0; i < candidates.length; i += 1) {
        const c = candidates[i];
        const label = `candidates[${i}]`;
        if (!isPlainObject(c)) {
            errors.push(`${label} is not an object`);
            continue;
        }
        const candidateProvider = c.source_provider ?? c.provider ?? topProvider;
        if (candidateProvider !== REQUIRED_SOURCE_PROVIDER) {
            errors.push(`${label}: source_provider must be ${REQUIRED_SOURCE_PROVIDER}, got ${JSON.stringify(candidateProvider)}`);
        }
        const candidateCompetition = c.competition ?? topCompetition;
        if (candidateCompetition !== REQUIRED_COMPETITION) {
            errors.push(`${label}: competition must be ${REQUIRED_COMPETITION}, got ${JSON.stringify(candidateCompetition)}`);
        }
        const candidateLeagueId = c.league_id ?? topLeagueId;
        if (candidateLeagueId !== undefined && candidateLeagueId !== null &&
            String(candidateLeagueId) !== REQUIRED_LEAGUE_ID) {
            errors.push(`${label}: league_id must be ${REQUIRED_LEAGUE_ID}, got ${JSON.stringify(candidateLeagueId)}`);
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

    // observed inner match id — must come from a TRUSTED raw-hydration
    // response field (general.matchId / matchId, i.e. raw
    // pageProps.general.matchId / pageProps.matchId extracted pre-transform),
    // never from the transformer-injected payload.matchId, input external id
    // fallback, request URL or any derivation. A page whose only "match id"
    // is the request id must fail closed (R3-P1).
    const observedId = rawData && (rawData.matchId ?? null) !== null ? String(rawData.matchId) : null;
    const matchIdSource = String(fr.match_id_source ||
        (rawData && rawData._meta ? rawData._meta.match_id_source : null) || '');
    checks.observed_match_id_present = observedId !== null;
    checks.observed_match_id_source_trusted = TRUSTED_OBSERVED_ID_SOURCES.has(matchIdSource);
    checks.observed_match_id_not_conflicting = fr.observed_match_id_conflict !== true;
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
    'candidate_id',
    'source_match_id',
    'competition',
    'league_id',
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
    'request_method',
    'request_url',
    'request_attempted_at',
    'response_received_at',
    'http_status',
    'content_type',
    'response_body_byte_size',
    'response_body_sha256',
    'observed_match_id',
    'observed_match_id_source',
    'observed_match_id_match',
    'observed_match_id_conflict',
    'hydration_parse_ok',
    'transformed_api_format',
    'looks_like_valid_match_detail',
    'has_stats',
    'has_lineup',
    'has_shotmap',
    'stable_raw_payload_sha256',
    'stable_payload_sha256',
    'payload_file_sha256',
    'payload_file_relative_path',
    'parser_component',
    'parser_version',
    'collector_component',
    'collector_code_revision',
    'network_authorization_mode',
    'capture_manifest_sha256',
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
    if (!/^\d+$/.test(String(manifest.observed_match_id || ''))) {
        errors.push('observed_match_id must be numeric');
    }
    if (!TRUSTED_OBSERVED_ID_SOURCES.has(String(manifest.observed_match_id_source || ''))) {
        errors.push(`observed_match_id_source must be one of ${[...TRUSTED_OBSERVED_ID_SOURCES].join('/')}`);
    }
    if (manifest.observed_match_id_match !== true) {
        errors.push('observed_match_id_match must be true');
    }
    // R3-P1: provenance flag must be present and boolean — a manifest whose
    // observed id came from any request-side / derived value fails closed.
    if (typeof manifest.observed_match_id_is_response_derived !== 'boolean') {
        errors.push('observed_match_id_is_response_derived must be a boolean');
    }
    for (const hexField of ['response_body_sha256', 'stable_raw_payload_sha256', 'stable_payload_sha256',
        'payload_file_sha256', 'candidate_identity_sha256', 'source_plan_sha256',
        'source_artifact_sha256']) {
        if (!/^[0-9a-f]{64}$/.test(String(manifest[hexField] || ''))) {
            errors.push(`${hexField} must be 64 lowercase hex`);
        }
    }
    if (!/^[0-9a-f]{40}$/.test(String(manifest.collector_code_revision || ''))) {
        errors.push('collector_code_revision must be 40-hex');
    }
    if (String(manifest.payload_file_relative_path || '').includes('..')) {
        errors.push('payload_file_relative_path must not traverse directories');
    }
    for (const field of MANIFEST_REQUIRED_FIELDS) {
        if (!(field in manifest) || manifest[field] === undefined || manifest[field] === null) {
            errors.push(`missing required field: ${field}`);
        }
    }
    // Manifest self-hash: REQUIRED, 64-hex, recomputed from the other fields
    // with the shared helper. Any tampered field fails closed. No lenient
    // "derive and accept when absent" fallback exists (P2-1).
    if (!/^[0-9a-f]{64}$/.test(String(manifest.capture_manifest_sha256 || ''))) {
        errors.push('capture_manifest_sha256 must be 64 lowercase hex');
    } else if (computeCaptureManifestSelfHash(manifest) !== manifest.capture_manifest_sha256) {
        errors.push('capture_manifest_sha256 does not match recomputed self-hash');
    }
    return { ok: errors.length === 0, errors };
}

// ─────────────────────────────────────────────────────────────
// Stable capture payload contract (fotmob-match-detail-capture-payload/v1)
// ─────────────────────────────────────────────────────────────

/**
 * Build the stable, allowlisted capture payload persisted after a
 * successful in-memory parse. The payload NEVER contains the full HTML
 * body, __NEXT_DATA__, pageProps, raw_data or translations — only the
 * deterministic parser-output fields needed downstream, plus the exact
 * identity binding (expected vs observed).
 *
 * stable_payload_sha256 is the canonical hash of the payload's business
 * projection (identity + normalized fields). The same value is bound by
 * the manifest (manifest.stable_payload_sha256) and reused by REPLAY as
 * structured_payload_sha256, so the persisted payload and the materialized
 * artifact are provably the same document.
 *
 * @param {object} args - {
 *   candidate (plan candidate), parsedData (FotMobRawParser output .data),
 *   observedIdentity: { home_team, away_team, observed_match_id,
 *                       observed_match_id_source, observed_match_id_conflict }
 * }
 * @returns {object} payload document (with stable_payload_sha256)
 */
/* eslint-disable-next-line complexity */
/**
 * Shared business projection of the stable capture payload (Codex
 * re-review P2-1). The SAME projection is used to build the hash at CAPTURE
 * time and to RECOMPUTE it at REPLAY time, so a tampered normalized /
 * identity field — even with a refreshed payload file hash and manifest
 * self-hash — fails closed at replay.
 *
 * Business fields: schema_version, source_provider, source_match_id,
 * candidate_id, competition, league_id, season, expected_identity,
 * observed_identity, normalized and the parser component / version /
 * output-contract-version fields. Self-hash (stable_payload_sha256), file
 * hash, manifest hash and non-contract timestamps are excluded by
 * construction — they are not part of the projection.
 */
function computeStableCapturePayloadBusinessProjection(payload = {}) {
    return {
        schema_version: payload.schema_version,
        source_provider: payload.source_provider,
        source_match_id: payload.source_match_id,
        candidate_id: payload.candidate_id,
        competition: payload.competition,
        league_id: payload.league_id,
        season: payload.season,
        expected_identity: payload.expected_identity,
        observed_identity: payload.observed_identity,
        normalized: payload.normalized,
        parser_component: payload.parser_component,
        parser_version: payload.parser_version,
        parser_output_contract_version: payload.parser_output_contract_version,
    };
}

/**
 * Recomputed business hash of the stable capture payload. Deterministic:
 * identical payload business fields always produce the identical hash,
 * independent of when or where it is recomputed.
 */
function computeStableCapturePayloadSha256(payload = {}) {
    return canonicalJsonHash(computeStableCapturePayloadBusinessProjection(payload));
}

/* eslint-disable-next-line complexity */
function buildCapturePayload(args = {}) {
    const candidate = args.candidate || {};
    const parsedData = args.parsedData || {};
    const observed = args.observedIdentity || {};
    const normalized = {
        match_external_id: parsedData.match && parsedData.match.externalId !== undefined
            ? String(parsedData.match.externalId)
            : String(candidate.source_match_id || ''),
        home_team: parsedData.homeTeam ?? null,
        away_team: parsedData.awayTeam ?? null,
        stats: parsedData.stats ?? null,
        lineup: parsedData.lineup ?? null,
        events: parsedData.events ?? null,
        shotmap: parsedData.shotmap ?? null,
        player_stats: parsedData.playerStats ?? null,
    };
    const expectedIdentity = {
        home_team: String(candidate.home_team || ''),
        away_team: String(candidate.away_team || ''),
        kickoff_at: String(candidate.kickoff_at || ''),
    };
    const observedIdentity = {
        home_team: String(observed.home_team || ''),
        away_team: String(observed.away_team || ''),
        observed_match_id: String(observed.observed_match_id || ''),
        observed_match_id_source: String(observed.observed_match_id_source || ''),
        observed_match_id_conflict: observed.observed_match_id_conflict === true,
        // R3-P1: provenance — true only when the observed id was extracted
        // from the raw hydration allowlist (pageProps.general.matchId /
        // pageProps.matchId) pre-transform; false for any request-side or
        // derived value.
        observed_match_id_is_response_derived: observed.observed_match_id_is_response_derived === true,
    };
    const payload = {
        schema_version: PAYLOAD_SCHEMA_VERSION,
        source_provider: REQUIRED_SOURCE_PROVIDER,
        source_match_id: String(candidate.source_match_id || ''),
        candidate_id: String(candidate.candidate_id || ''),
        competition: String(candidate.competition || ''),
        league_id: REQUIRED_LEAGUE_ID,
        season: String(candidate.season || ''),
        expected_identity: expectedIdentity,
        observed_identity: observedIdentity,
        normalized,
        parser_component: 'NextDataParser+FotMobRawParser',
        parser_version: 'V174.0.0',
        parser_output_contract_version: 'fotmob-match-detail-parsed/v1',
    };
    // Shared business projection: buildCapturePayload and REPLAY recompute
    // the same hash from the same fields (P2-1).
    payload.stable_payload_sha256 = computeStableCapturePayloadSha256(payload);
    return payload;
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
    'normalized',
    'payload_file_sha256',
    'capture_manifest_sha256',
    'stable_payload_sha256',
    'structured_payload_sha256',
    'parser_component',
    'parser_version',
    'parser_code_revision',
    'parsed_at',
    'matchId',
];

/* eslint-disable-next-line complexity */
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
    if (!/^[0-9a-f]{64}$/.test(String(artifact.payload_file_sha256 || ''))) {
        errors.push('payload_file_sha256 must be 64 lowercase hex');
    }
    if (!/^[0-9a-f]{64}$/.test(String(artifact.capture_manifest_sha256 || ''))) {
        errors.push('capture_manifest_sha256 must be 64 lowercase hex');
    }
    if (!/^[0-9a-f]{64}$/.test(String(artifact.stable_payload_sha256 || ''))) {
        errors.push('stable_payload_sha256 must be 64 lowercase hex');
    }
    if (!/^[0-9a-f]{64}$/.test(String(artifact.structured_payload_sha256 || ''))) {
        errors.push('structured_payload_sha256 must be 64 lowercase hex');
    }
    if (!/^\d+$/.test(String(artifact.matchId || ''))) {
        errors.push('matchId must be numeric');
    }
    // The parser code revision must be a verified 40-hex revision — an empty
    // or non-40-hex value would make the artifact provenance untraceable
    // (Codex re-review P2).
    if (!/^[0-9a-f]{40}$/.test(String(artifact.parser_code_revision || ''))) {
        errors.push('parser_code_revision must be 40 lowercase hex');
    }
    // Replay must never emit empty candidate identity (P2-6): the identity
    // comes from the run-bound plan snapshot, never from file names.
    const expected = artifact.expected_identity || {};
    if (typeof expected.home_team !== 'string' || expected.home_team.trim() === '' ||
        typeof expected.away_team !== 'string' || expected.away_team.trim() === '' ||
        typeof expected.kickoff_at !== 'string' || expected.kickoff_at.trim() === '') {
        errors.push('expected_identity home_team/away_team/kickoff_at must be non-empty');
    }
    if (typeof artifact.candidate_id !== 'string' || artifact.candidate_id.trim() === '') {
        errors.push('candidate_id must be non-empty');
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
    PAYLOAD_SCHEMA_VERSION,
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
    TRUSTED_OBSERVED_ID_SOURCES,
    MANIFEST_REQUIRED_FIELDS,
    DETAIL_ARTIFACT_REQUIRED_FIELDS,
    PLAN_REQUIRED_FIELDS,
    sha256Hex,
    sha256Text,
    canonicalJsonHash,
    isPlainObject,
    readInputFile,
    assertRegularInputFile,
    assertNoSymlinkAncestors,
    ensureRealDirectoryTree,
    computeCapturePlanBusinessProjection,
    validateAndRecomputeCapturePlan,
    computeCaptureManifestSelfHash,
    computeStableCapturePayloadBusinessProjection,
    computeStableCapturePayloadSha256,
    validateCandidateArtifact,
    readAndValidateCandidateArtifact,
    evaluateContentValidity,
    buildCapturePayload,
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
