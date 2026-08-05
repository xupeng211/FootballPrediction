/* eslint-disable complexity, max-lines */
// The contract module is a decision-table collection: L1-L9 validation layers
// and the L9 terminal-state classifier are intentionally branchy. File-level
// disable matches project precedent for such tables (GoldenFeatureExtractor,
// enhanced_stealth_config).
'use strict';

// lifecycle: permanent
//
// FotMob detail staging — offline contract module.
//
// Owns the validation and construction contract for the offline staging
// artifact `fotmob-detail-staging-artifact/v1`, produced from archived
// `fotmob-match-detail-capture-payload/v1` + `fotmob-match-detail-capture-
// manifest/v1` pairs via a repository-external source index.
//
// This module is a leaf: zero network, zero database, zero capture. It REUSES
// the capture pipeline's hashing helpers (computeStableCapturePayloadSha256,
// computeCaptureManifestSelfHash) — it never re-implements canonical JSON
// hashing (contract errata ERRATA_4). Hash portability: V8 enumerates
// numeric-string object keys (player_stats player ids) in dict-hash-bucket
// order, so a naive sorted encoder diverges from the pipeline hashes; the
// only correct source of stable_payload_sha256 is the real pipeline code.
//
// Contract source: fotmob-detail-staging-contract-b6f9f385-20260804T105736Z
// (staging-artifact-schema, provenance-contract, idempotency-versioning-
// policy, canonical-link-policy, validation-and-quarantine-contract,
// error-code-registry).

const crypto = require('node:crypto');

const {
    PAYLOAD_SCHEMA_VERSION,
    REQUIRED_SOURCE_PROVIDER,
    REQUIRED_COMPETITION,
    REQUIRED_LEAGUE_ID,
    VALID_SEASON_PATTERN,
    TRUSTED_OBSERVED_ID_SOURCES,
    computeStableCapturePayloadSha256,
    computeCaptureManifestSelfHash,
    validateCaptureManifest,
    canonicalJsonHash,
    normalizeTeamName,
    isPlainObject,
    sha256Hex,
} = require('./FotMobDetailCaptureContract');

// ─────────────────────────────────────────────────────────────
// Constants (contract package: schema names, states, codes, layers)
// ─────────────────────────────────────────────────────────────

const STAGING_ARTIFACT_SCHEMA_VERSION = 'fotmob-detail-staging-artifact/v1';
const SOURCE_INDEX_SCHEMA_VERSION = 'fotmob-detail-source-index/v1';
const PARSED_OUTPUT_CONTRACT_VERSION = 'fotmob-match-detail-parsed/v1';

// 11 terminal states — idempotency-versioning-policy.md (names MUST match
// the contract package; no renames).
const TERMINAL_STATES = Object.freeze({
    ACCEPTED_NEW: 'ACCEPTED_NEW',
    ACCEPTED_REPEAT_EXACT: 'ACCEPTED_REPEAT_EXACT',
    ACCEPTED_REPEAT_EQUIVALENT: 'ACCEPTED_REPEAT_EQUIVALENT',
    REJECTED_IDENTITY_INCONSISTENT: 'REJECTED_IDENTITY_INCONSISTENT',
    REJECTED_PROVENANCE_BROKEN: 'REJECTED_PROVENANCE_BROKEN',
    REJECTED_SCHEMA_UNKNOWN: 'REJECTED_SCHEMA_UNKNOWN',
    QUARANTINED_VALIDATION_FAIL: 'QUARANTINED_VALIDATION_FAIL',
    QUARANTINED_PROVENANCE_MISMATCH: 'QUARANTINED_PROVENANCE_MISMATCH',
    LINKED_CANONICAL: 'LINKED_CANONICAL',
    LINK_PENDING: 'LINK_PENDING',
    LINK_BLOCKED: 'LINK_BLOCKED',
});

// 6 link statuses — canonical-link-policy.md.
const LINK_STATUSES = Object.freeze({
    UNLINKED_NOT_ATTEMPTED: 'UNLINKED_NOT_ATTEMPTED',
    LINKED_EXACT_ID_MATCH: 'LINKED_EXACT_ID_MATCH',
    LINKED_IDENTITY_MATCH: 'LINKED_IDENTITY_MATCH',
    LINK_BLOCKED_CONFLICT: 'LINK_BLOCKED_CONFLICT',
    LINK_PENDING_UNAVAILABLE: 'LINK_PENDING_UNAVAILABLE',
    LINK_REJECTED_FOR_MANUAL_REVIEW: 'LINK_REJECTED_FOR_MANUAL_REVIEW',
});

// 9 validation layers — validation-and-quarantine-contract.md.
const VALIDATION_LAYERS = Object.freeze({
    L1_DOCUMENT_SHAPE: 'L1_DOCUMENT_SHAPE',
    L2_SCHEMA_IDENTITY: 'L2_SCHEMA_IDENTITY',
    L3_IDENTITY_BINDING: 'L3_IDENTITY_BINDING',
    L4_PROVENANCE_HASH_CHAIN: 'L4_PROVENANCE_HASH_CHAIN',
    L5_SECTION_PRESENCE: 'L5_SECTION_PRESENCE',
    L6_VALUE_SANITY: 'L6_VALUE_SANITY',
    L7_DRIFT_TOLERANCE: 'L7_DRIFT_TOLERANCE',
    L8_QUARANTINE_RULES: 'L8_QUARANTINE_RULES',
    L9_IMPORT_READINESS: 'L9_IMPORT_READINESS',
});

// 13 error codes — error-code-registry.json.
const ERROR_CODES = Object.freeze({
    E001: 'E001', // DOCUMENT_NOT_OBJECT (L1)
    E002: 'E002', // UNSUPPORTED_SCHEMA_VERSION (L2)
    E003: 'E003', // SOURCE_PROVIDER_MISMATCH (L2)
    E004: 'E004', // COMPETITION_MISMATCH (L2)
    E005: 'E005', // LEAGUE_ID_MISMATCH (L2)
    E006: 'E006', // SEASON_INVALID (L2)
    E007: 'E007', // IDENTITY_BINDING_CONFLICT (L3)
    E008: 'E008', // PROVENANCE_HASH_MISMATCH (L4)
    E009: 'E009', // MANIFEST_SELF_HASH_MISMATCH (L4)
    E010: 'E010', // OBSERVED_ID_NOT_RESPONSE_DERIVED (L4)
    E011: 'E011', // VALUE_SANITY_FAIL (L6)
    E012: 'E012', // CANONICAL_LINK_CONFLICT (L9/K)
    E013: 'E013', // INTERNAL_CONTRACT_VIOLATION (L1/L8/L9)
});

const SECTIONS = ['events', 'lineup', 'player_stats', 'shotmap', 'stats'];

// L1: event minute sanity bound (real matches never exceed 130 with added
// time; generous on purpose — L6 is a quarantine layer, not a rejection).
const MAX_EVENT_MINUTE = 130;
// L6: expectedGoals is a probability band 0..1.
const EXPECTED_GOALS_MAX = 1.0;
const EXPECTED_GOALS_MIN = 0.0;

// L8: prohibited retention markers. Key names that must never appear in an
// allowlisted payload document, and string-value signatures of raw HTML /
// headers. Field NAMES used inside this module's own errors are not
// sensitive; the check targets payload content only.
const PROHIBITED_KEY_NAMES = ['__NEXT_DATA__', 'pageProps', 'raw_data', 'translations', 'set-cookie', 'authorization'];
const PROHIBITED_VALUE_SIGNATURES = ['<html', '<body', '<script', '<div', 'text/html; charset', 'x-csrf-token'];

// Provenance double binding (Codex review 4863122944 P1-2).
//
// The ORIGINAL constant claimed a "20-field double binding" but several of
// those fields do not exist on both documents (parser_output_contract_version
// is payload-only; capture_run_id / authorization_id / collector_code_revision
// are manifest-only), so no equality check was ever possible for them — the
// claim overstated the implementation. The matrix below is the ACTUAL set of
// fields present on BOTH documents and compared for equality:
//
//   A. PAYLOAD_AND_MANIFEST_DOUBLE_BOUND (16 fields):
//      source_provider, source_match_id, candidate_id, competition,
//      league_id, season, parser_component, parser_version,
//      home_team, away_team, kickoff_at,
//      observed_match_id, observed_match_id_source,
//      observed_match_id_conflict, observed_match_id_is_response_derived,
//      stable_payload_sha256 (recomputed live by L4, compared on both).
//   B. PAYLOAD_ONLY (validated on the payload side, never claimed as
//      double-bound): schema_version, parser_output_contract_version,
//      expected_identity_sha256, observed_identity_sha256, normalized.
//   C. MANIFEST_ONLY (validated on the manifest side, never claimed as
//      double-bound): schema_version, capture_run_id, authorization_id,
//      collector_code_revision, source_plan_sha256, source_artifact_sha256,
//      request/response fields.
//   D. DERIVED_AND_RECOMPUTED (recomputed live and compared):
//      candidate_identity_sha256, expected_identity_sha256,
//      payload_file_sha256, capture_manifest_sha256, stable_payload_sha256.
//
// Each matrix row is [manifestPath, payloadPath]; '.'-separated payload
// paths index into expected_identity / observed_identity.
const DOUBLE_BOUND_FIELD_PAIRS = Object.freeze([
    ['source_provider', 'source_provider'],
    ['source_match_id', 'source_match_id'],
    ['candidate_id', 'candidate_id'],
    ['competition', 'competition'],
    ['league_id', 'league_id'],
    ['season', 'season'],
    ['parser_component', 'parser_component'],
    ['parser_version', 'parser_version'],
    ['home_team', 'expected_identity.home_team'],
    ['away_team', 'expected_identity.away_team'],
    ['kickoff_at', 'expected_identity.kickoff_at'],
    ['observed_match_id', 'observed_identity.observed_match_id'],
    ['observed_match_id_source', 'observed_identity.observed_match_id_source'],
    ['observed_match_id_conflict', 'observed_identity.observed_match_id_conflict'],
    ['observed_match_id_is_response_derived', 'observed_identity.observed_match_id_is_response_derived'],
    ['stable_payload_sha256', 'stable_payload_sha256'],
]);

// R1-P1-1: matrix rows whose values are booleans on BOTH documents. These
// are compared type-strict in the A-class loop (never String()-coerced).
const DOUBLE_BOUND_BOOLEAN_FIELDS = new Set([
    'observed_match_id_conflict',
    'observed_match_id_is_response_derived',
]);

// ACTUAL_DOUBLE_BOUND_FIELDS — authoritative count of the A-class matrix.
const ACTUAL_DOUBLE_BOUND_FIELDS = Object.freeze(
    DOUBLE_BOUND_FIELD_PAIRS.map(([manifestPath]) => manifestPath)
);

// Kept as an alias for compatibility: the A-class field names.
const DOUBLE_BINDING_FIELDS = ACTUAL_DOUBLE_BOUND_FIELDS;

// ─────────────────────────────────────────────────────────────
// Source index contract (fotmob-detail-source-index/v1)
// ─────────────────────────────────────────────────────────────

/**
 * Validate a repository-external source index document that binds archive
 * sha256s and lists the payload/manifest pairs to convert.
 *
 * @param {object} index - source index document
 * @returns {{ ok: boolean, errors: string[], entries: Array }}
 */
/* eslint-disable-next-line complexity */
function validateSourceIndex(index) {
    const errors = [];
    if (!isPlainObject(index)) {
        return {
            ok: false,
            errors: ['source index is not an object'],
            entries: [],
        };
    }
    if (index.schema_version !== SOURCE_INDEX_SCHEMA_VERSION) {
        errors.push(`schema_version must be ${SOURCE_INDEX_SCHEMA_VERSION}`);
    }
    if (index.source_provider !== REQUIRED_SOURCE_PROVIDER) {
        errors.push(`source_provider must be ${REQUIRED_SOURCE_PROVIDER}`);
    }
    if (!Array.isArray(index.entries) || index.entries.length === 0) {
        errors.push('entries must be a non-empty array');
    }
    const archives = index.archive_bindings;
    if (!isPlainObject(archives) || Object.keys(archives).length === 0) {
        errors.push('archive_bindings must be a non-empty object of {package: {sha256, path, receipt}}');
    } else {
        for (const [pkg, binding] of Object.entries(archives)) {
            if (!isPlainObject(binding)) {
                errors.push(`archive_bindings.${pkg} must be an object`);
                continue;
            }
            if (!/^[0-9a-f]{64}$/.test(String(binding.sha256 || ''))) {
                errors.push(`archive_bindings.${pkg}.sha256 must be 64 lowercase hex`);
            }
            if (typeof binding.path !== 'string' || binding.path === '') {
                errors.push(`archive_bindings.${pkg}.path must be a non-empty archive path`);
            }
            if (typeof binding.receipt !== 'string' || binding.receipt === '') {
                errors.push(`archive_bindings.${pkg}.receipt must be a non-empty receipt path`);
            }
        }
    }
    const entries = [];
    const seenIds = new Set();
    if (Array.isArray(index.entries)) {
        index.entries.forEach((entry, i) => {
            const label = `entries[${i}]`;
            if (!isPlainObject(entry)) {
                errors.push(`${label} is not an object`);
                return;
            }
            const sourceMatchId = String(entry.source_match_id ?? '');
            if (!/^\d+$/.test(sourceMatchId)) {
                errors.push(`${label}: source_match_id must be numeric`);
            } else if (seenIds.has(sourceMatchId)) {
                errors.push(`${label}: duplicate source_match_id ${sourceMatchId}`);
            } else {
                seenIds.add(sourceMatchId);
            }
            for (const f of ['payload_file', 'manifest_file']) {
                if (typeof entry[f] !== 'string' || entry[f] === '') {
                    errors.push(`${label}: ${f} must be a non-empty path string`);
                }
            }
            // P2-2 (Codex review 4863122944): both declared file hashes are
            // REQUIRED and are verified LIVE at build time against the actual
            // external file bytes (which themselves must equal the receipt
            // member hash and the live archive member hash).
            if (!/^[0-9a-f]{64}$/.test(String(entry.payload_file_sha256 || ''))) {
                errors.push(`${label}: payload_file_sha256 is required and must be 64 lowercase hex`);
            }
            if (!/^[0-9a-f]{64}$/.test(String(entry.manifest_file_sha256 || ''))) {
                errors.push(`${label}: manifest_file_sha256 is required and must be 64 lowercase hex`);
            }
            // PR1817 remediation (FINDING_3): every entry MUST be bound to exactly
            // one archive package; the package must exist in archive_bindings and
            // the same package must serve BOTH the payload and the manifest
            // (single-package rule — no mixing).
            const packageId = String(entry.package ?? '');
            if (!/^[A-Za-z0-9._-]+$/.test(packageId)) {
                errors.push(`${label}: package must be a plain identifier`);
            } else if (!isPlainObject(archives) || !Object.prototype.hasOwnProperty.call(archives || {}, packageId)) {
                errors.push(`${label}: package ${packageId} has no archive_binding (declared package must exist)`);
            }
            entries.push(entry);
        });
    }
    return { ok: errors.length === 0, errors, entries };
}

// ─────────────────────────────────────────────────────────────
// L2 — schema identity
// ─────────────────────────────────────────────────────────────

/**
 * L2_SCHEMA_IDENTITY: payload schema_version / provider / competition /
 * league_id / season must match the fixed contract scope.
 * Failure → REJECTED_SCHEMA_UNKNOWN with E002–E006.
 */
/* eslint-disable-next-line complexity */
function validateSchemaIdentity(payload) {
    const errors = [];
    if (payload.schema_version !== PAYLOAD_SCHEMA_VERSION) {
        errors.push({
            code: ERROR_CODES.E002,
            message: `schema_version must be ${PAYLOAD_SCHEMA_VERSION}`,
        });
    }
    if (payload.source_provider !== REQUIRED_SOURCE_PROVIDER) {
        errors.push({
            code: ERROR_CODES.E003,
            message: `source_provider must be ${REQUIRED_SOURCE_PROVIDER}`,
        });
    }
    if (payload.competition !== REQUIRED_COMPETITION) {
        errors.push({
            code: ERROR_CODES.E004,
            message: `competition must be ${REQUIRED_COMPETITION}`,
        });
    }
    if (String(payload.league_id ?? '') !== REQUIRED_LEAGUE_ID) {
        errors.push({
            code: ERROR_CODES.E005,
            message: `league_id must be ${REQUIRED_LEAGUE_ID}`,
        });
    }
    if (typeof payload.season !== 'string' || !VALID_SEASON_PATTERN.test(payload.season)) {
        errors.push({
            code: ERROR_CODES.E006,
            message: 'season must be YYYY/YYYY',
        });
    }
    // REQUIRED_STABLE_IDENTITY: the allowlisted normalized block is mandatory
    // (all 16 real payloads carry it); it is the ONLY payload content stored.
    if (!isPlainObject(payload.normalized)) {
        errors.push({
            code: ERROR_CODES.E002,
            message: 'normalized must be an object',
        });
    }
    return { ok: errors.length === 0, errors };
}

// ─────────────────────────────────────────────────────────────
// L3 — identity binding
// ─────────────────────────────────────────────────────────────

function isStrictAbsoluteTimestamp(value) {
    // Same discipline as the exporter: strict ISO-8601 with timezone.
    if (typeof value !== 'string' || value === '') return false;
    if (
        !/^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(\.\d{1,9})?Z$/.test(value) &&
        !/^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(\.\d{1,9})?[+-]\d{2}:\d{2}$/.test(value)
    ) {
        return false;
    }
    return !Number.isNaN(Date.parse(value));
}

function sameInstant(a, b) {
    // P2-3 (Codex review 4863122944): strict timestamp binding — the two
    // strings must be CANONICAL and BYTE-EQUAL. Date.parse() (millisecond
    // precision) is never used, so two distinct nanosecond timestamps can
    // never collapse to "equal". Contract decision: timezone-equivalent but
    // textually different strings are REJECTED (fail-closed) — the fixture
    // pipeline copies these values verbatim, so byte equality holds for
    // legitimate data.
    if (typeof a !== 'string' || typeof b !== 'string') {
        return false;
    }
    if (!isStrictAbsoluteTimestamp(a) || !isStrictAbsoluteTimestamp(b)) {
        return false;
    }
    return a === b;
}

/**
 * L3_IDENTITY_BINDING: expected vs observed identity consistency — teams
 * (exact normalizeTeamName fold, no fuzzy/synonyms), observed_match_id vs
 * source_match_id, match_external_id vs observed id, observed id conflict
 * flag. Failure → REJECTED_IDENTITY_INCONSISTENT with E007.
 */
/* eslint-disable-next-line complexity */
function validateIdentityBinding(payload) {
    const errors = [];
    const expected = payload.expected_identity || {};
    const observed = payload.observed_identity || {};
    const sourceMatchId = String(payload.source_match_id ?? '');
    const observedMatchId = String(observed.observed_match_id ?? '');
    const externalId = String((payload.normalized && payload.normalized.match_external_id) ?? '');

    if (
        typeof expected.home_team !== 'string' ||
        typeof expected.away_team !== 'string' ||
        typeof expected.kickoff_at !== 'string' ||
        expected.home_team.trim() === '' ||
        expected.away_team.trim() === '' ||
        expected.kickoff_at.trim() === ''
    ) {
        errors.push({
            code: ERROR_CODES.E007,
            message: 'expected_identity home_team/away_team/kickoff_at required',
        });
    }
    if (!/^\d+$/.test(observedMatchId)) {
        errors.push({
            code: ERROR_CODES.E007,
            message: 'observed_match_id must be numeric',
        });
    } else if (observedMatchId !== sourceMatchId) {
        errors.push({
            code: ERROR_CODES.E007,
            message: `observed_match_id ${observedMatchId} must equal source_match_id ${sourceMatchId}`,
        });
    }
    if (externalId === '') {
        // REQUIRED_STABLE_IDENTITY: normalized.match_external_id must be
        // present (16/16 real payloads) and equal the observed id.
        errors.push({
            code: ERROR_CODES.E007,
            message: 'match_external_id missing in normalized',
        });
    } else if (!/^\d+$/.test(externalId)) {
        errors.push({
            code: ERROR_CODES.E007,
            message: 'match_external_id must be numeric',
        });
    } else if (externalId !== observedMatchId) {
        errors.push({
            code: ERROR_CODES.E007,
            message: `match_external_id ${externalId} must equal observed_match_id ${observedMatchId}`,
        });
    }
    const expHome = String(expected.home_team ?? '').trim();
    const expAway = String(expected.away_team ?? '').trim();
    const obsHome = String(observed.home_team ?? '').trim();
    const obsAway = String(observed.away_team ?? '').trim();
    if (expHome && obsHome && normalizeTeamName(expHome) !== normalizeTeamName(obsHome)) {
        errors.push({
            code: ERROR_CODES.E007,
            message: `home_team conflict: expected ${expHome}, observed ${obsHome}`,
        });
    }
    if (expAway && obsAway && normalizeTeamName(expAway) !== normalizeTeamName(obsAway)) {
        errors.push({
            code: ERROR_CODES.E007,
            message: `away_team conflict: expected ${expAway}, observed ${obsAway}`,
        });
    }
    if (observed.observed_match_id_conflict === true) {
        errors.push({
            code: ERROR_CODES.E007,
            message: 'observed_match_id_conflict must be false',
        });
    }
    return { ok: errors.length === 0, errors };
}

// ─────────────────────────────────────────────────────────────
// L4 — provenance hash chain (direct pipeline-hash reuse)
// ─────────────────────────────────────────────────────────────

/**
 * L4_PROVENANCE_HASH_CHAIN. The stable payload hash is recomputed LIVE by the
 * real pipeline code (computeStableCapturePayloadSha256) over the actual
 * payload document — ERRATA_4: no copied or "equivalent" canonical-JSON hash
 * implementation exists anywhere in this module.
 *
 * @param {object} payload - parsed payload document
 * @param {object} manifest - parsed manifest document
 * @param {Buffer} payloadBytes - physical payload file bytes
 * @returns {{ ok: boolean, errors: Array, checks: object }}
 */
/* eslint-disable-next-line complexity */
function validateProvenanceHashChain(payload, manifest, payloadBytes) {
    const errors = [];
    const checks = {};

    // 1. payload file sha over the physical bytes.
    const fileSha = sha256Hex(payloadBytes);
    checks.payload_file_sha256 = fileSha;
    if (String(manifest.payload_file_sha256 ?? '') !== fileSha) {
        errors.push({
            code: ERROR_CODES.E008,
            message: 'payload_file_sha256 does not match SHA-256 of the physical payload bytes',
        });
    }

    // 2. stable payload sha recomputed by the REAL pipeline function.
    const stable = computeStableCapturePayloadSha256(payload);
    checks.stable_payload_sha256 = stable;
    if (String(payload.stable_payload_sha256 ?? '') !== stable) {
        errors.push({
            code: ERROR_CODES.E008,
            message: 'payload.stable_payload_sha256 does not match recomputed business projection hash',
        });
    }
    if (String(manifest.stable_payload_sha256 ?? '') !== stable) {
        errors.push({
            code: ERROR_CODES.E008,
            message: 'manifest.stable_payload_sha256 does not match recomputed business projection hash',
        });
    }

    // 3. manifest self-hash recomputed with the shared helper.
    if (computeCaptureManifestSelfHash(manifest) !== String(manifest.capture_manifest_sha256 ?? '')) {
        errors.push({
            code: ERROR_CODES.E009,
            message: 'capture_manifest_sha256 does not match recomputed manifest self-hash',
        });
    }

    // 4. observed-id provenance (E010).
    if (manifest.observed_match_id_is_response_derived !== true) {
        errors.push({
            code: ERROR_CODES.E010,
            message: 'observed_match_id_is_response_derived must be true',
        });
    }
    if (!TRUSTED_OBSERVED_ID_SOURCES.has(String(manifest.observed_match_id_source ?? ''))) {
        errors.push({
            code: ERROR_CODES.E010,
            message: `observed_match_id_source must be one of ${[...TRUSTED_OBSERVED_ID_SOURCES].join('/')}`,
        });
    }

    return { ok: errors.length === 0, errors, checks };
}

/**
 * Provenance double binding between payload and manifest — driven by the
 * ACTUAL DOUBLE_BOUND_FIELD_PAIRS matrix (16 fields that exist on BOTH
 * documents, compared for equality; Codex review 4863122944 P1-2).
 * Disagreement fails closed. Fields present on only ONE side are validated
 * on their own side below and are explicitly NOT claimed as double-bound.
 */
/* eslint-disable-next-line complexity */
function validateDoubleBinding(payload, manifest) {
    const errors = [];

    if (payload.schema_version !== PAYLOAD_SCHEMA_VERSION) {
        errors.push({
            code: ERROR_CODES.E009,
            message: 'payload schema_version not capture payload v1',
        });
    }
    if (manifest.schema_version !== 'fotmob-match-detail-capture-manifest/v1') {
        errors.push({
            code: ERROR_CODES.E009,
            message: 'manifest schema_version not capture manifest v1',
        });
    }

    /**
     * Resolve a '.'-separated payload path (expected_identity.x /
     * observed_identity.x / top-level) with a safe default.
     */
    const payloadAt = pPath => {
        const parts = String(pPath).split('.');
        let value = payload;
        for (const part of parts) {
            if (value === null || value === undefined || typeof value !== 'object') return undefined;
            value = value[part];
        }
        return value;
    };

    // A-class: every matrix row must exist on both documents and agree.
    // R1-P1-1: the two observed-identity provenance fields are BOOLEANS on
    // both documents. Stringifying them would accept `true` vs `"true"` as
    // equal (and later `=== true` artifact writes would silently invert the
    // value), so boolean fields are compared type-strict: both sides must be
    // the boolean type and agree exactly.
    for (const [mField, pField] of DOUBLE_BOUND_FIELD_PAIRS) {
        const mVal = manifest[mField];
        const pVal = payloadAt(pField);
        if (DOUBLE_BOUND_BOOLEAN_FIELDS.has(mField)) {
            if (typeof mVal !== 'boolean' || typeof pVal !== 'boolean') {
                errors.push({
                    code: ERROR_CODES.E009,
                    message: `double binding ${mField}: must be a boolean on both documents (manifest ${typeof mVal}, payload ${typeof pVal})`,
                });
                continue;
            }
            if (mVal !== pVal) {
                errors.push({
                    code: ERROR_CODES.E009,
                    message: `double binding ${mField} disagrees: manifest ${mVal} vs payload ${pVal}`,
                });
            }
            continue;
        }
        const mStr = mVal === null || mVal === undefined ? '' : String(mVal);
        const pStr = pVal === null || pVal === undefined ? '' : String(pVal);
        if (mStr === '' || pStr === '') {
            errors.push({
                code: ERROR_CODES.E009,
                message: `double binding ${mField}: missing in one document`,
            });
            continue;
        }
        const agrees = mField === 'kickoff_at' ? sameInstant(mStr, pStr) : mStr === pStr;
        if (!agrees) {
            errors.push({
                code: ERROR_CODES.E009,
                message: `double binding ${mField} disagrees: manifest ${mStr} vs payload ${pStr}`,
            });
        }
    }
    // source_provider is additionally pinned to the fixed contract constant
    // on BOTH sides (equality alone would accept two identical wrong values).
    if (
        String(manifest.source_provider ?? '') !== REQUIRED_SOURCE_PROVIDER ||
        String(payload.source_provider ?? '') !== REQUIRED_SOURCE_PROVIDER
    ) {
        errors.push({
            code: ERROR_CODES.E009,
            message: 'source_provider must be FotMob in both documents',
        });
    }

    // candidate identity sha (plan-side binding) recomputed and verified.
    const candidateIdentity = {
        source_match_id: String(manifest.source_match_id ?? ''),
        competition: String(manifest.competition ?? ''),
        season: String(manifest.season ?? ''),
        home_team: String(manifest.home_team ?? ''),
        away_team: String(manifest.away_team ?? ''),
        kickoff_at: String(manifest.kickoff_at ?? ''),
    };
    const recomputedCandidate = canonicalJsonHash(candidateIdentity);
    if (String(manifest.candidate_identity_sha256 ?? '') !== recomputedCandidate) {
        errors.push({
            code: ERROR_CODES.E009,
            message: 'candidate_identity_sha256 does not match recomputed projection',
        });
    }

    // stability hashes over the identity projections (D-class recomputed).
    const expected = payload.expected_identity || {};
    const observed = payload.observed_identity || {};
    const expectedHash = canonicalJsonHash(payload.expected_identity || {});
    const observedHash = canonicalJsonHash({
        home_team: String(observed.home_team ?? ''),
        away_team: String(observed.away_team ?? ''),
        observed_match_id: String(observed.observed_match_id ?? ''),
        observed_match_id_source: String(observed.observed_match_id_source ?? ''),
        observed_match_id_conflict: observed.observed_match_id_conflict === true,
        observed_match_id_is_response_derived: observed.observed_match_id_is_response_derived === true,
    });
    const expectedRecomputed = canonicalJsonHash({
        home_team: String(expected.home_team ?? ''),
        away_team: String(expected.away_team ?? ''),
        kickoff_at: String(expected.kickoff_at ?? ''),
    });
    if (expectedHash !== expectedRecomputed) {
        errors.push({
            code: ERROR_CODES.E013,
            message: 'expected_identity_sha256 recomputation unstable',
        });
    }

    // B-class (PAYLOAD_ONLY) and C-class (MANIFEST_ONLY) fields: validated on
    // their own side — presence, format, fixed contract values. These are
    // NOT double-bound (they do not exist on both documents).
    // parser_version / parser_component are A-class (matrix rows above).
    if (String(payload.parser_version ?? '') === '') {
        errors.push({ code: ERROR_CODES.E009, message: 'parser_version missing' });
    }
    if (String(payload.parser_output_contract_version ?? '') === '') {
        errors.push({
            code: ERROR_CODES.E009,
            message: 'parser_output_contract_version missing',
        });
    }
    if (String(manifest.capture_run_id ?? '') === '') {
        errors.push({ code: ERROR_CODES.E009, message: 'capture_run_id missing' });
    }
    if (String(manifest.authorization_id ?? '') === '') {
        errors.push({
            code: ERROR_CODES.E009,
            message: 'authorization_id missing',
        });
    }
    if (!/^[0-9a-f]{40}$/.test(String(manifest.collector_code_revision ?? ''))) {
        errors.push({
            code: ERROR_CODES.E009,
            message: 'collector_code_revision must be 40-hex',
        });
    }
    if (String(payload.parser_output_contract_version ?? '') !== PARSED_OUTPUT_CONTRACT_VERSION) {
        errors.push({
            code: ERROR_CODES.E009,
            message: `parser_output_contract_version must be ${PARSED_OUTPUT_CONTRACT_VERSION}`,
        });
    }

    return {
        ok: errors.length === 0,
        errors,
        hashes: {
            expected_identity_sha256: expectedHash,
            observed_identity_sha256: observedHash,
        },
    };
}

// ─────────────────────────────────────────────────────────────
// L5 — section presence / coverage
// ─────────────────────────────────────────────────────────────

/**
 * L5_SECTION_PRESENCE: build the per-observation coverage record. Section
 * absence is recorded, NEVER an error (optional section valid chain).
 */
function buildCoverageRecord(payload) {
    const normalized = payload.normalized || {};
    const record = {};
    const present = [];
    const absent = [];
    for (const section of SECTIONS) {
        const value = normalized[section];
        const isPresent = value !== undefined && value !== null;
        if (!isPresent) {
            absent.push(section);
            record[section] = {
                present: false,
                version: String(payload.parser_output_contract_version ?? ''),
            };
            continue;
        }
        present.push(section);
        const entry = {
            present: true,
            version: String(payload.parser_output_contract_version ?? ''),
        };
        if (section === 'events' && Array.isArray(value)) {
            entry.count = value.length;
        } else if (section === 'lineup' && isPlainObject(value)) {
            entry.sides = Object.keys(value).filter(side => isPlainObject(value[side]));
        } else if (section === 'player_stats' && isPlainObject(value)) {
            entry.count = Object.keys(value).length;
        } else if (section === 'shotmap' && isPlainObject(value) && Array.isArray(value.shots)) {
            entry.shots = value.shots.length;
        } else if (section === 'stats' && Array.isArray(value)) {
            entry.entries = value.length;
            const periods = [];
            for (const row of value) {
                if (isPlainObject(row) && typeof row.period === 'string' && !periods.includes(row.period)) {
                    periods.push(row.period);
                }
            }
            if (periods.length > 0) entry.periods = periods;
        }
        record[section] = entry;
    }
    return { record, present, absent };
}

// ─────────────────────────────────────────────────────────────
// L6 — value sanity (quarantine layer, E011)
// ─────────────────────────────────────────────────────────────

function isNonNegativeInteger(value) {
    return typeof value === 'number' && Number.isInteger(value) && value >= 0;
}

/* eslint-disable-next-line complexity */
function validateValueSanity(payload) {
    const errors = [];
    const normalized = payload.normalized || {};

    const home = normalized.home_team || {};
    const away = normalized.away_team || {};
    for (const [label, team] of [
        ['home_team', home],
        ['away_team', away],
    ]) {
        if (
            isPlainObject(team) &&
            team.score !== undefined &&
            team.score !== null &&
            !isNonNegativeInteger(team.score)
        ) {
            errors.push({
                code: ERROR_CODES.E011,
                message: `${label}.score must be a non-negative integer`,
            });
        }
    }

    if (Array.isArray(normalized.events)) {
        for (let i = 0; i < normalized.events.length; i += 1) {
            const event = normalized.events[i];
            if (!isPlainObject(event)) {
                errors.push({
                    code: ERROR_CODES.E011,
                    message: `events[${i}] is not an object`,
                });
                continue;
            }
            if (
                event.minute !== undefined &&
                event.minute !== null &&
                (typeof event.minute !== 'number' ||
                    !Number.isInteger(event.minute) ||
                    event.minute < 0 ||
                    event.minute > MAX_EVENT_MINUTE)
            ) {
                errors.push({
                    code: ERROR_CODES.E011,
                    message: `events[${i}].minute out of range 0..${MAX_EVENT_MINUTE}`,
                });
            }
            // marker_event entries (AddedTime / Half minute markers) are
            // parser-injected and carry NO native id by design — every captured
            // match has exactly four (45' +45', 90' +90'). The id requirement
            // applies to id-bearing events only (real events and synthetic ones).
            const isMarkerEvent = event.event_kind === 'marker_event';
            if (!isMarkerEvent && (event.id === undefined || event.id === null)) {
                errors.push({
                    code: ERROR_CODES.E011,
                    message: `events[${i}].id missing`,
                });
            }
        }
    }

    if (isPlainObject(normalized.shotmap) && Array.isArray(normalized.shotmap.shots)) {
        for (let i = 0; i < normalized.shotmap.shots.length; i += 1) {
            const shot = normalized.shotmap.shots[i];
            if (!isPlainObject(shot)) {
                errors.push({
                    code: ERROR_CODES.E011,
                    message: `shotmap.shots[${i}] is not an object`,
                });
                continue;
            }
            if (
                shot.expectedGoals !== undefined &&
                shot.expectedGoals !== null &&
                (typeof shot.expectedGoals !== 'number' ||
                    shot.expectedGoals < EXPECTED_GOALS_MIN ||
                    shot.expectedGoals > EXPECTED_GOALS_MAX)
            ) {
                errors.push({
                    code: ERROR_CODES.E011,
                    message: `shotmap.shots[${i}].expectedGoals outside 0..1`,
                });
            }
            for (const coord of ['x', 'y', 'blockedX', 'blockedY', 'goalCrossedY', 'goalCrossedZ']) {
                if (shot[coord] !== undefined && shot[coord] !== null && typeof shot[coord] !== 'number') {
                    errors.push({
                        code: ERROR_CODES.E011,
                        message: `shotmap.shots[${i}].${coord} must be numeric`,
                    });
                }
            }
        }
    }

    if (isPlainObject(normalized.player_stats)) {
        for (const [playerId, entry] of Object.entries(normalized.player_stats)) {
            if (!isPlainObject(entry)) {
                errors.push({
                    code: ERROR_CODES.E011,
                    message: `player_stats.${playerId} is not an object`,
                });
                continue;
            }
            if (entry.id !== undefined && entry.id !== null && Number(entry.id) !== Number(playerId)) {
                errors.push({
                    code: ERROR_CODES.E011,
                    message: `player_stats.${playerId}.id disagrees with its key`,
                });
            }
        }
    }

    if (Array.isArray(normalized.stats)) {
        for (let i = 0; i < normalized.stats.length; i += 1) {
            const row = normalized.stats[i];
            if (!isPlainObject(row) || typeof row.key !== 'string' || row.key === '') {
                errors.push({
                    code: ERROR_CODES.E011,
                    message: `stats[${i}].key must be a non-empty string`,
                });
            }
        }
    }

    if (isPlainObject(normalized.lineup)) {
        for (const side of ['home', 'away']) {
            const team = normalized.lineup[side];
            if (!isPlainObject(team)) continue;
            for (const group of ['starters', 'subs']) {
                if (Array.isArray(team[group])) {
                    for (let i = 0; i < team[group].length; i += 1) {
                        const member = team[group][i];
                        if (!isPlainObject(member) || member.id === undefined || member.id === null) {
                            errors.push({
                                code: ERROR_CODES.E011,
                                message: `lineup.${side}.${group}[${i}].id missing`,
                            });
                        }
                    }
                }
            }
        }
    }

    return { ok: errors.length === 0, errors };
}

// ─────────────────────────────────────────────────────────────
// L7 — drift tolerance (variants accepted, recorded in coverage)
// ─────────────────────────────────────────────────────────────

/**
 * L7_DRIFT_TOLERANCE: variant shapes are accepted and recorded; there is no
 * failure by design. stats 7-vs-21 entries, player_stats positionId /
 * usualPosition / funFacts variants, event id number|string, unknown extra
 * fields — all preserved byte-faithfully in the JSONB sections.
 */
function assessDriftVariants(payload) {
    const normalized = payload.normalized || {};
    const variants = {};
    if (Array.isArray(normalized.stats)) {
        const periods = [];
        for (const row of normalized.stats) {
            if (isPlainObject(row) && typeof row.period === 'string' && !periods.includes(row.period)) {
                periods.push(row.period);
            }
        }
        variants.stats_periods = periods;
    }
    if (isPlainObject(normalized.player_stats)) {
        let positionAndUsual = 0;
        let usualOnly = 0;
        let neither = 0;
        let funFacts = 0;
        for (const entry of Object.values(normalized.player_stats)) {
            if (!isPlainObject(entry)) continue;
            const hasPosition = entry.positionId !== undefined && entry.positionId !== null;
            const hasUsual = entry.usualPosition !== undefined && entry.usualPosition !== null;
            if (hasPosition && hasUsual) positionAndUsual += 1;
            else if (hasUsual) usualOnly += 1;
            else neither += 1;
            if (entry.funFacts !== undefined && entry.funFacts !== null) {
                funFacts += 1;
            }
        }
        variants.player_stats = {
            positionId_and_usualPosition: positionAndUsual,
            usualPosition_only: usualOnly,
            neither,
            funFacts,
        };
    }
    return { ok: true, variants };
}

// ─────────────────────────────────────────────────────────────
// L8 — quarantine rules / prohibited retention
// ─────────────────────────────────────────────────────────────

/* eslint-disable-next-line complexity */
function scanProhibitedContent(value, path, errors) {
    if (value === null || value === undefined) return;
    if (typeof value === 'string') {
        const lower = value.toLowerCase();
        for (const sig of PROHIBITED_VALUE_SIGNATURES) {
            if (lower.includes(sig)) {
                errors.push({
                    code: ERROR_CODES.E013,
                    message: `prohibited raw content signature at ${path}`,
                });
                return;
            }
        }
        return;
    }
    if (Array.isArray(value)) {
        for (let i = 0; i < value.length; i += 1) {
            scanProhibitedContent(value[i], `${path}[${i}]`, errors);
        }
        return;
    }
    if (isPlainObject(value)) {
        for (const [key, child] of Object.entries(value)) {
            if (PROHIBITED_KEY_NAMES.includes(key)) {
                errors.push({
                    code: ERROR_CODES.E013,
                    message: `prohibited key name ${key} at ${path}`,
                });
            }
            scanProhibitedContent(child, `${path}.${key}`, errors);
        }
    }
}

/**
 * L8_QUARANTINE_RULES: optional field absence is never an error (L5 handles
 * recording); prohibited retention content (raw HTML, hydration data,
 * credential material) fails closed with E013.
 */
function validateQuarantineRules(payload) {
    const errors = [];
    scanProhibitedContent(payload, 'payload', errors);
    return { ok: errors.length === 0, errors };
}

// ─────────────────────────────────────────────────────────────
// Top-level validation driver
// ─────────────────────────────────────────────────────────────

/**
 * Run the L1–L8 layer stack over one payload+manifest pair.
 *
 * @param {object} args - { payload, manifest, payloadBytes }
 * @returns {object} { ok, layers: {L1..L9...}, errors: [{code,message}],
 *                     coverage: {...}, checks: {...}, hashes: {...} }
 */
/* eslint-disable-next-line complexity */
/**
 * P2-4: human- and test-readable description of a received document value —
 * used in the L1 rejection message so structured garbage (null, array,
 * string, number, boolean) is reported by its ACTUAL type instead of a
 * generic phrase.
 */
function describeValueType(value) {
    if (value === null) return 'null';
    if (value === undefined) return 'undefined';
    if (Array.isArray(value)) return `array(${value.length})`;
    return typeof value;
}

function validateObservation(args = {}) {
    const payload = args.payload;
    const manifest = args.manifest;
    const payloadBytes = args.payloadBytes;

    const layers = {};
    const allErrors = [];

    // P2-4: structured garbage (null / [] / "string" / 123 / true / missing)
    // must be REJECTED_SCHEMA_UNKNOWN, never a crash. The shape check guards
    // every deeper layer: none of the internals are ever invoked with a
    // non-object, so a hostile document cannot throw its way out of
    // validation. The message names the ACTUAL received type of each side.
    const shapeOk = isPlainObject(payload) && isPlainObject(manifest);

    // L1 — document shape.
    layers.L1_DOCUMENT_SHAPE = { layer: VALIDATION_LAYERS.L1_DOCUMENT_SHAPE };
    if (!shapeOk) {
        allErrors.push({
            code: ERROR_CODES.E001,
            message: `payload/manifest must be JSON objects (payload=${describeValueType(payload)}, manifest=${describeValueType(manifest)})`,
        });
    }
    layers.L1_DOCUMENT_SHAPE.ok = shapeOk;
    layers.L1_DOCUMENT_SHAPE.errors = shapeOk ? [] : [allErrors[allErrors.length - 1]];

    // L2 — schema identity (payload only; manifest validated below).
    const l2 = shapeOk ? validateSchemaIdentity(payload) : { ok: false, errors: [] };
    layers.L2_SCHEMA_IDENTITY = {
        layer: VALIDATION_LAYERS.L2_SCHEMA_IDENTITY,
        ok: l2.ok,
        errors: l2.errors,
    };
    allErrors.push(...l2.errors);

    // L3 — identity binding.
    const l3 = shapeOk ? validateIdentityBinding(payload) : { ok: false, errors: [] };
    layers.L3_IDENTITY_BINDING = {
        layer: VALIDATION_LAYERS.L3_IDENTITY_BINDING,
        ok: l3.ok,
        errors: l3.errors,
    };
    allErrors.push(...l3.errors);

    // L4 — provenance hash chain + manifest schema + double binding.
    const manifestValidation = isPlainObject(manifest)
        ? validateCaptureManifest(manifest)
        : { ok: false, errors: ['manifest is not an object'] };
    const l4 = shapeOk
        ? validateProvenanceHashChain(payload, manifest, payloadBytes || Buffer.alloc(0))
        : { ok: false, errors: [] };
    // P2-4: the double-binding matrix and every later payload validator are
    // shape-guarded the same way — structured garbage yields a structured
    // rejection, never a TypeError escape.
    const binding = shapeOk ? validateDoubleBinding(payload, manifest) : { ok: false, errors: [] };
    const l4Errors = [
        ...(manifestValidation.ok
            ? []
            : manifestValidation.errors.map(e => ({
                  code: ERROR_CODES.E009,
                  message: `manifest: ${e}`,
              }))),
        ...l4.errors,
        ...binding.errors,
    ];
    layers.L4_PROVENANCE_HASH_CHAIN = {
        layer: VALIDATION_LAYERS.L4_PROVENANCE_HASH_CHAIN,
        ok: l4Errors.length === 0,
        errors: l4Errors,
        checks: l4.checks,
    };
    allErrors.push(...l4Errors);

    // L5 — section presence (never fails; records coverage).
    const coverage = shapeOk ? buildCoverageRecord(payload) : { record: {}, present: [], absent: [] };
    layers.L5_SECTION_PRESENCE = {
        layer: VALIDATION_LAYERS.L5_SECTION_PRESENCE,
        ok: true,
        coverage: coverage.record,
        present: coverage.present,
        absent: coverage.absent,
    };

    // L6 — value sanity (quarantine layer).
    const l6 = shapeOk ? validateValueSanity(payload) : { ok: false, errors: [] };
    layers.L6_VALUE_SANITY = {
        layer: VALIDATION_LAYERS.L6_VALUE_SANITY,
        ok: l6.ok,
        errors: l6.errors,
    };
    allErrors.push(...l6.errors);

    // L7 — drift tolerance (accepted by design).
    const l7 = shapeOk ? assessDriftVariants(payload) : { ok: true, variants: [] };
    layers.L7_DRIFT_TOLERANCE = {
        layer: VALIDATION_LAYERS.L7_DRIFT_TOLERANCE,
        ok: true,
        variants: l7.variants,
    };

    // L8 — quarantine rules.
    const l8 = shapeOk ? validateQuarantineRules(payload) : { ok: false, errors: [] };
    layers.L8_QUARANTINE_RULES = {
        layer: VALIDATION_LAYERS.L8_QUARANTINE_RULES,
        ok: l8.ok,
        errors: l8.errors,
    };
    allErrors.push(...l8.errors);

    const terminalState = classifyTerminalState(layers);
    layers.L9_IMPORT_READINESS = {
        layer: VALIDATION_LAYERS.L9_IMPORT_READINESS,
        ok: terminalState.ok,
        terminal_state: terminalState.state,
        error_code: terminalState.errorCode,
        quarantine_status: terminalState.quarantineStatus,
    };

    return {
        ok: terminalState.ok,
        terminal_state: terminalState.state,
        error_code: terminalState.errorCode,
        quarantine_status: terminalState.quarantineStatus,
        layers,
        errors: allErrors,
        coverage: coverage.record,
        checks: l4.checks,
        hashes: binding.hashes,
        variants: l7.variants,
    };
}

/**
 * L9 — assign the terminal state from the layer outcomes, per the contract:
 * L1/L2 → REJECTED_SCHEMA_UNKNOWN; L3 → REJECTED_IDENTITY_INCONSISTENT;
 * L4 → REJECTED_PROVENANCE_BROKEN; L6/L8 → QUARANTINED_VALIDATION_FAIL
 * (evidence preserved, quarantine coherence: quarantined ⇔ error code set).
 */
function classifyTerminalState(layers) {
    const firstError = [];
    for (const layerName of [
        VALIDATION_LAYERS.L1_DOCUMENT_SHAPE,
        VALIDATION_LAYERS.L2_SCHEMA_IDENTITY,
        VALIDATION_LAYERS.L3_IDENTITY_BINDING,
        VALIDATION_LAYERS.L4_PROVENANCE_HASH_CHAIN,
        VALIDATION_LAYERS.L6_VALUE_SANITY,
        VALIDATION_LAYERS.L8_QUARANTINE_RULES,
    ]) {
        const layer = layers[layerName];
        if (layer && layer.ok === false && Array.isArray(layer.errors)) {
            for (const e of layer.errors) firstError.push(e);
        }
    }
    const l6 = layers[VALIDATION_LAYERS.L6_VALUE_SANITY];
    const l8 = layers[VALIDATION_LAYERS.L8_QUARANTINE_RULES];

    if (firstError.length > 0) {
        const codes = firstError.map(e => e.code);
        // Priority follows the layer order: schema (L1/L2) → identity (L3) →
        // quarantine layers (L6/L8) → provenance (L4). A tampered schema
        // necessarily breaks the hash chain too, but the root cause is the
        // schema — REJECTED_SCHEMA_UNKNOWN must win (E002–E006).
        const isSchemaLayer = codes.some(c =>
            [
                ERROR_CODES.E001,
                ERROR_CODES.E002,
                ERROR_CODES.E003,
                ERROR_CODES.E004,
                ERROR_CODES.E005,
                ERROR_CODES.E006,
            ].includes(c)
        );
        const isIdentity = codes.some(c => c === ERROR_CODES.E007);
        const isProvenance = codes.some(c => [ERROR_CODES.E008, ERROR_CODES.E009, ERROR_CODES.E010].includes(c));
        const isQuarantine = (l6 && l6.ok === false) || (l8 && l8.ok === false);
        if (isSchemaLayer) {
            return {
                ok: false,
                state: TERMINAL_STATES.REJECTED_SCHEMA_UNKNOWN,
                errorCode: codes.find(c =>
                    [
                        ERROR_CODES.E001,
                        ERROR_CODES.E002,
                        ERROR_CODES.E003,
                        ERROR_CODES.E004,
                        ERROR_CODES.E005,
                        ERROR_CODES.E006,
                    ].includes(c)
                ),
                quarantineStatus: 'not_quarantined',
            };
        }
        if (isIdentity) {
            return {
                ok: false,
                state: TERMINAL_STATES.REJECTED_IDENTITY_INCONSISTENT,
                errorCode: ERROR_CODES.E007,
                quarantineStatus: 'not_quarantined',
            };
        }
        if (isQuarantine && !isProvenance) {
            // L6/L8 failures quarantine (evidence preserved); they never
            // mask an identity or provenance failure.
            return {
                ok: false,
                state: TERMINAL_STATES.QUARANTINED_VALIDATION_FAIL,
                errorCode: ERROR_CODES.E011,
                quarantineStatus: 'quarantined',
            };
        }
        return {
            ok: false,
            state: TERMINAL_STATES.REJECTED_PROVENANCE_BROKEN,
            // E010 (observed-id provenance) is the root cause when present;
            // E008 (hash mismatch) before E009 (cross-document disagreement).
            errorCode:
                codes.find(c => c === ERROR_CODES.E010) ||
                codes.find(c => c === ERROR_CODES.E008) ||
                codes.find(c => c === ERROR_CODES.E009) ||
                codes[0],
            quarantineStatus: 'not_quarantined',
        };
    }
    return {
        ok: true,
        state: null, // ACCEPTED_* decided by the retention store (duplicate fold)
        errorCode: null,
        quarantineStatus: 'not_quarantined',
    };
}

// ─────────────────────────────────────────────────────────────
// Artifact builder (fotmob-detail-staging-artifact/v1)
// ─────────────────────────────────────────────────────────────

/**
 * Deterministic UUID v5 over the observation key — no wall clock anywhere in
 * the business output (ERRATA_3 byte determinism).
 *
 * P2-3 (Codex review 4863122944): RFC 4122-compliant UUIDv5 — the SHA-1 name
 * input is the 16-byte NAMESPACE UUID (DNS) followed by the name bytes
 * (UTF-8), not the namespace text string. Verified against the official RFC
 * test vector (DNS namespace + "www.example.com" → 2ed6657d-e927-568b-95e1-
 * 2665a8aea6a2) in the contract tests.
 */
const DNS_NAMESPACE_HEX = '6ba7b8109dad11d180b400c04fd430c8';

/**
 * RFC 4122 UUIDv5 over a 16-byte namespace UUID + a UTF-8 name.
 * Exported for direct verification against the official RFC test vectors.
 *
 * @param {string} namespaceHex - 32-hex namespace UUID (no dashes)
 * @param {string} name - UTF-8 name
 * @returns {string} canonical UUID string
 */
function uuidV5(namespaceHex, name) {
    const namespaceBytes = Buffer.from(String(namespaceHex).replace(/-/g, ''), 'hex');
    if (namespaceBytes.length !== 16) {
        throw Object.assign(new Error('uuidv5 namespace must be a 16-byte UUID'), { code: 'INPUT_ERROR' });
    }
    const nameBytes = Buffer.from(String(name), 'utf8');
    const hash = crypto
        .createHash('sha1')
        .update(Buffer.concat([namespaceBytes, nameBytes]))
        .digest();
    const bytes = Buffer.from(hash.subarray(0, 16));
    bytes[6] = (bytes[6] & 0x0f) | 0x50; // version 5
    bytes[8] = (bytes[8] & 0x3f) | 0x80; // variant
    const hex = bytes.toString('hex');
    return `${hex.slice(0, 8)}-${hex.slice(8, 12)}-${hex.slice(12, 16)}-${hex.slice(16, 20)}-${hex.slice(20)}`;
}

function deterministicObservationId(sourceMatchId, stablePayloadSha256) {
    return uuidV5(DNS_NAMESPACE_HEX, `${String(sourceMatchId)}:${String(stablePayloadSha256)}`);
}

/**
 * Build the business projection of a staging artifact: every field EXCEPT
 * observation_id, generated_at, business_hash itself and
 * artifact_integrity_sha256 (identical exclusion discipline to the capture
 * pipeline's generated_at exclusion). The integrity hash is excluded too:
 * it covers business_hash, so including it in the business projection would
 * make the two hashes circularly dependent.
 */
/* eslint-disable-next-line complexity */
function computeStagingArtifactBusinessProjection(artifact) {
    const projection = {};
    for (const [key, value] of Object.entries(artifact)) {
        if (
            key === 'observation_id' ||
            key === 'generated_at' ||
            key === 'business_hash' ||
            key === 'artifact_integrity_sha256'
        ) {
            continue;
        }
        projection[key] = value;
    }
    return projection;
}

function computeStagingArtifactBusinessHash(artifact) {
    return canonicalJsonHash(computeStagingArtifactBusinessProjection(artifact));
}

/**
 * PR1817 remediation (FINDING_6, LAYER_B): full artifact integrity hash over
 * EVERY field except artifact_integrity_sha256 itself — including
 * observation_id, generated_at and business_hash which the BUSINESS
 * projection legitimately excludes. This is an integrity hash, NOT a digital
 * signature: any field change is detected by the validator recomputation.
 */
function computeStagingArtifactIntegrityHash(artifact) {
    const projection = {};
    for (const [key, value] of Object.entries(artifact)) {
        if (key === 'artifact_integrity_sha256') continue;
        projection[key] = value;
    }
    return canonicalJsonHash(projection);
}

/**
 * Build one staging artifact document from a validated observation.
 *
 * @param {object} args - { payload, manifest, validation, payloadFileSha256,
 *                         terminalState }
 * @returns {object} artifact document with business_hash
 */
/* eslint-disable-next-line complexity */
function buildStagingArtifact(args = {}) {
    const payload = args.payload;
    const manifest = args.manifest;
    const validation = args.validation || {};
    const payloadFileSha256 = args.payloadFileSha256 || '';
    const terminalState = args.terminalState || TERMINAL_STATES.ACCEPTED_NEW;

    const observed = payload.observed_identity || {};
    const expected = payload.expected_identity || {};
    const normalized = payload.normalized || {};
    const coverage = validation.coverage || {};

    const sections = {};
    for (const section of SECTIONS) {
        const value = normalized[section];
        const present = value !== undefined && value !== null;
        sections[section] = {
            version: present ? String(payload.parser_output_contract_version ?? PARSED_OUTPUT_CONTRACT_VERSION) : null,
            json: present ? value : null,
        };
    }

    const artifact = {
        schema_version: STAGING_ARTIFACT_SCHEMA_VERSION,
        observation_id: deterministicObservationId(
            String(payload.source_match_id ?? ''),
            String(payload.stable_payload_sha256 ?? '')
        ),
        generated_at: String(manifest.response_received_at ?? ''),
        // PR1817 remediation (FINDING_6, LAYER_A): the artifact records the
        // explicit source instant it derives generated_at from; the validator
        // requires generated_at to represent the SAME instant.
        source_response_received_at: String(manifest.response_received_at ?? ''),
        source_match_id: String(payload.source_match_id ?? ''),
        candidate_id: String(payload.candidate_id ?? ''),
        competition: String(payload.competition ?? ''),
        league_id: String(payload.league_id ?? ''),
        season: String(payload.season ?? ''),
        expected_identity: {
            home_team: String(expected.home_team ?? ''),
            away_team: String(expected.away_team ?? ''),
            kickoff_at: String(expected.kickoff_at ?? ''),
        },
        observed_identity: {
            home_team: String(observed.home_team ?? ''),
            away_team: String(observed.away_team ?? ''),
            observed_match_id: String(observed.observed_match_id ?? ''),
            observed_match_id_source: String(observed.observed_match_id_source ?? ''),
            observed_match_id_conflict: observed.observed_match_id_conflict === true,
            observed_match_id_is_response_derived: observed.observed_match_id_is_response_derived === true,
        },
        observed_match_id_source: String(observed.observed_match_id_source ?? ''),
        observed_match_id_conflict: observed.observed_match_id_conflict === true,
        observed_match_id_is_response_derived: observed.observed_match_id_is_response_derived === true,
        match_external_id: String(normalized.match_external_id ?? ''),
        stable_payload_sha256: String(payload.stable_payload_sha256 ?? ''),
        payload_file_sha256: String(payloadFileSha256 || manifest.payload_file_sha256 || ''),
        capture_manifest_sha256: String(manifest.capture_manifest_sha256 ?? ''),
        parser_component: String(payload.parser_component ?? ''),
        parser_version: String(payload.parser_version ?? ''),
        parser_output_contract_version: String(payload.parser_output_contract_version ?? ''),
        capture_run_id: String(manifest.capture_run_id ?? ''),
        authorization_id: String(manifest.authorization_id ?? ''),
        collector_code_revision: String(manifest.collector_code_revision ?? ''),
        canonical_match_id: null, // fail-closed: never guessed; no canonical DB in this task
        canonical_link_status: LINK_STATUSES.UNLINKED_NOT_ATTEMPTED,
        import_terminal_state: terminalState,
        validation_status: VALIDATION_LAYERS.L9_IMPORT_READINESS,
        quarantine_status: String(validation.quarantine_status || 'not_quarantined'),
        quarantine_error_code: validation.error_code || null,
        coverage_record: coverage,
        sections,
    };
    artifact.business_hash = computeStagingArtifactBusinessHash(artifact);
    // FINDING_6 LAYER_B: full-envelope integrity hash AFTER the business hash
    // (it covers business_hash, observation_id and generated_at).
    artifact.artifact_integrity_sha256 = computeStagingArtifactIntegrityHash(artifact);
    return artifact;
}

// ─────────────────────────────────────────────────────────────
// Artifact validator
// ─────────────────────────────────────────────────────────────

const ARTIFACT_REQUIRED_FIELDS = [
    'schema_version',
    'observation_id',
    'generated_at',
    'source_response_received_at',
    'business_hash',
    'artifact_integrity_sha256',
    'source_match_id',
    'candidate_id',
    'competition',
    'league_id',
    'season',
    'expected_identity',
    'observed_identity',
    'match_external_id',
    'stable_payload_sha256',
    'payload_file_sha256',
    'capture_manifest_sha256',
    'parser_component',
    'parser_version',
    'parser_output_contract_version',
    'capture_run_id',
    'authorization_id',
    'collector_code_revision',
    // canonical_match_id is intentionally NOT in the required set: the
    // contract marks it required=false (null until a fail-closed link).
    'canonical_link_status',
    'import_terminal_state',
    'validation_status',
    'quarantine_status',
    'coverage_record',
    'sections',
];

/**
 * Validate a completed staging artifact document: schema, required fields,
 * hash formats, terminal state / link status membership, quarantine
 * coherence (quarantined ⇔ error code present), section shape, and the
 * business hash recomputation.
 */
/* eslint-disable-next-line complexity */
function validateStagingArtifact(artifact) {
    const errors = [];
    if (!isPlainObject(artifact)) {
        return { ok: false, errors: ['artifact is not an object'] };
    }
    if (artifact.schema_version !== STAGING_ARTIFACT_SCHEMA_VERSION) {
        errors.push(`schema_version must be ${STAGING_ARTIFACT_SCHEMA_VERSION}`);
    }
    for (const field of ARTIFACT_REQUIRED_FIELDS) {
        if (!(field in artifact) || artifact[field] === undefined || artifact[field] === null) {
            errors.push(`missing required field: ${field}`);
        }
    }
    for (const hexField of [
        'business_hash',
        'artifact_integrity_sha256',
        'stable_payload_sha256',
        'payload_file_sha256',
        'capture_manifest_sha256',
    ]) {
        if (!/^[0-9a-f]{64}$/.test(String(artifact[hexField] || ''))) {
            errors.push(`${hexField} must be 64 lowercase hex`);
        }
    }
    if (!/^[0-9a-f]{40}$/.test(String(artifact.collector_code_revision || ''))) {
        errors.push('collector_code_revision must be 40-hex');
    }
    const stateValues = Object.values(TERMINAL_STATES);
    if (!stateValues.includes(artifact.import_terminal_state)) {
        errors.push(`import_terminal_state must be one of ${stateValues.join('/')}`);
    }
    const linkValues = Object.values(LINK_STATUSES);
    if (!linkValues.includes(artifact.canonical_link_status)) {
        errors.push(`canonical_link_status must be one of ${linkValues.join('/')}`);
    }
    const quarantineCoherent =
        (artifact.quarantine_status === 'quarantined') === (artifact.quarantine_error_code !== null);
    if (!quarantineCoherent) {
        errors.push('quarantine coherence violated: quarantined ⇔ quarantine_error_code present');
    }
    if (artifact.canonical_match_id !== null && typeof artifact.canonical_match_id !== 'string') {
        errors.push('canonical_match_id must be null or a string');
    }
    if (!isPlainObject(artifact.sections)) {
        errors.push('sections must be an object');
    } else {
        for (const section of SECTIONS) {
            const entry = artifact.sections[section];
            if (!isPlainObject(entry) || !('json' in entry)) {
                errors.push(`sections.${section} must be an object with json`);
            }
        }
    }
    if (!isPlainObject(artifact.coverage_record)) {
        errors.push('coverage_record must be an object');
    }
    // Business hash recomputation — fails on any tampering.
    const recomputed = computeStagingArtifactBusinessHash(artifact);
    if (recomputed !== String(artifact.business_hash || '')) {
        errors.push('business_hash does not match recomputed business projection');
    }

    // PR1817 remediation (FINDING_6):
    // LAYER_A — semantic recomputation: observation_id is a deterministic
    // UUIDv5 over (source_match_id, stable_payload_sha256); generated_at must
    // be a strict absolute timestamp and represent the SAME instant as the
    // recorded source_response_received_at (which itself must be a strict
    // absolute timestamp — it derives from manifest.response_received_at).
    const recomputedObservationId = deterministicObservationId(
        String(artifact.source_match_id ?? ''),
        String(artifact.stable_payload_sha256 ?? '')
    );
    if (recomputedObservationId !== String(artifact.observation_id || '')) {
        errors.push('observation_id does not match recomputed UUIDv5 observation id');
    }
    if (!isStrictAbsoluteTimestamp(String(artifact.generated_at ?? ''))) {
        errors.push('generated_at must be a strict ISO-8601 absolute timestamp');
    }
    if (!isStrictAbsoluteTimestamp(String(artifact.source_response_received_at ?? ''))) {
        errors.push('source_response_received_at must be a strict ISO-8601 absolute timestamp');
    }
    if (!sameInstant(String(artifact.generated_at ?? ''), String(artifact.source_response_received_at ?? ''))) {
        errors.push('generated_at must represent the same instant as source_response_received_at');
    }

    // LAYER_B — full-envelope integrity hash: covers every field except the
    // hash itself, INCLUDING observation_id, generated_at and business_hash.
    const recomputedIntegrity = computeStagingArtifactIntegrityHash(artifact);
    if (recomputedIntegrity !== String(artifact.artifact_integrity_sha256 || '')) {
        errors.push('artifact_integrity_sha256 does not match recomputed full artifact hash');
    }

    return {
        ok: errors.length === 0,
        errors,
        recomputed_business_hash: recomputed,
        recomputed_integrity_hash: recomputedIntegrity,
        recomputed_observation_id: recomputedObservationId,
    };
}

module.exports = {
    STAGING_ARTIFACT_SCHEMA_VERSION,
    SOURCE_INDEX_SCHEMA_VERSION,
    PARSED_OUTPUT_CONTRACT_VERSION,
    TERMINAL_STATES,
    LINK_STATUSES,
    VALIDATION_LAYERS,
    ERROR_CODES,
    SECTIONS,
    DOUBLE_BINDING_FIELDS,
    DOUBLE_BOUND_FIELD_PAIRS,
    ACTUAL_DOUBLE_BOUND_FIELDS,
    ARTIFACT_REQUIRED_FIELDS,
    validateSourceIndex,
    validateSchemaIdentity,
    validateIdentityBinding,
    validateProvenanceHashChain,
    validateDoubleBinding,
    buildCoverageRecord,
    validateValueSanity,
    assessDriftVariants,
    validateQuarantineRules,
    validateObservation,
    classifyTerminalState,
    uuidV5,
    deterministicObservationId,
    computeStagingArtifactBusinessProjection,
    computeStagingArtifactBusinessHash,
    computeStagingArtifactIntegrityHash,
    buildStagingArtifact,
    validateStagingArtifact,
    isStrictAbsoluteTimestamp,
    sameInstant,
    canonicalJsonHash,
};
