'use strict';

/* eslint-disable max-lines -- the permanent facts contract keeps schema, hash and receipt invariants together. */

// lifecycle: permanent
// GD-A02 facts artifact/receipt contract.  This module owns only the
// file-first facts projection shape, hashes, population accounting and
// post-match timing boundary.  Parser, staging and linkage authorities stay
// in their existing modules.

const {
    GdA01ContractError,
    assertInteger,
    assertObject,
    assertSha,
    assertText,
    admittedIdSetHash,
    sha256Bytes,
    sha256Text,
    stableStringify,
    validateMatchLink,
} = require('./GdA01AssemblyContract');
const { canonicalJsonHash } = require('../fotmob/FotMobDetailCaptureContract');
const { isPlainJsonData, validateStagingArtifact, SECTIONS } = require('../fotmob/FotMobDetailStagingContract');

const FACTS_ASSEMBLY_SCHEMA_VERSION = 'golden-dataset-v1-gd-a02-facts-artifact/v2';
const LEGACY_FACTS_ASSEMBLY_SCHEMA_VERSION = 'golden-dataset-v1-gd-a02-facts-artifact/v1';
const FACTS_RECEIPT_SCHEMA_VERSION = 'gd-a02-facts-assembly-receipt/v2';
const LEGACY_FACTS_RECEIPT_SCHEMA_VERSION = 'gd-a02-facts-assembly-receipt/v1';
const FACTS_SOURCE_INDEX_SCHEMA_VERSION = 'gd-a02-facts-source-index/v1';
const STAGE = 'GD-A02';
const ARTIFACT_KIND = 'fotmob_facts_assembly';
const PARSED_OUTPUT_CONTRACT_VERSION = 'fotmob-match-detail-parsed/v1';
const GIT_REVISION_PATTERN = /^[0-9a-f]{40}$/;
const HEX_PATTERN = /^[0-9a-f]{64}$/;
const RESULT_VALUES = new Set(['home', 'draw', 'away']);
const RESULT_STATUS_VALUES = new Set(['AVAILABLE', 'UNAVAILABLE']);
const XG_STATUS_VALUES = new Set(['VALID', 'PARTIAL', 'UNAVAILABLE']);
const XG_SIDE_STATUS_VALUES = new Set(['COMPLETE', 'PARTIAL', 'UNAVAILABLE']);
const SHOTS_ON_TARGET_STATUS_VALUES = new Set(['VALID', 'PARTIAL', 'UNAVAILABLE']);
const SHOTS_ON_TARGET_SIDE_STATUS_VALUES = new Set(['COMPLETE', 'PARTIAL', 'UNAVAILABLE']);
const FACT_TIMING = Object.freeze({
    role: 'MATCH_FACT',
    timing_class: 'POSTMATCH_ONLY',
    prematch_available: false,
    decision_time_eligible: false,
});
const SCOPE = Object.freeze({
    facts_only: true,
    prematch_features: false,
    training: false,
    backtest: false,
    model_activation: false,
});

const SOURCE_BINDING_KEYS = new Set([
    'gd_a01_artifact',
    'gd_a01_receipt',
    'fotmob_freeze',
    'fotmob_manifest',
    'fotmob_facts_source_index',
]);
const FORBIDDEN_KEYS = new Set([
    'odds',
    'feature',
    'training',
    'prediction',
    'backtest',
    'model',
    'value_betting',
    'prematch_feature',
]);
const PROHIBITED_VALUE_SIGNATURES = [
    '<html',
    '<body',
    '<script',
    '<div',
    'pageprops',
    '__next_data__',
    'raw_data',
    'translations',
    'set-cookie',
    'authorization:',
];

class GdA02ContractError extends GdA01ContractError {
    constructor(message, code = 'GD_A02_CONTRACT_INVALID') {
        super(message, code);
        this.name = 'GdA02ContractError';
    }
}

function fail(message, code = 'GD_A02_CONTRACT_INVALID') {
    throw new GdA02ContractError(message, code);
}

function assertFactsObject(value, label) {
    if (!value || typeof value !== 'object' || Array.isArray(value)) {
        fail(`${label} must be an object`);
    }
}

function assertHex(value, label) {
    if (typeof value !== 'string' || !HEX_PATTERN.test(value)) {
        fail(`${label} must be a lowercase SHA-256`, 'HASH_MISMATCH');
    }
}

function assertRevision(value, label) {
    if (typeof value !== 'string' || !GIT_REVISION_PATTERN.test(value)) {
        fail(`${label} must be a 40-hex git revision`, 'PROVENANCE_INVALID');
    }
}

function assertAllowedKeys(value, allowed, label) {
    assertFactsObject(value, label);
    for (const key of Object.keys(value)) {
        if (!allowed.has(key)) fail(`${label} contains unsupported field ${key}`, 'SCHEMA_MISMATCH');
    }
}

function assertPlainJson(value, label) {
    if (!isPlainJsonData(value)) fail(`${label} must be strict plain JSON data`, 'SCHEMA_MISMATCH');
}

function schemaShape(value) {
    if (value === null) return { kind: 'null' };
    if (Array.isArray(value)) {
        const itemShapes = [...new Set(value.map(item => stableStringify(schemaShape(item))))]
            .sort()
            .map(shape => JSON.parse(shape));
        return { kind: 'array', items: itemShapes };
    }
    if (typeof value !== 'object') return { kind: typeof value };
    const keys = Object.keys(value).sort();
    if (keys.length > 0 && keys.every(key => /^\d+$/.test(key))) {
        const valueShapes = [...new Set(keys.map(key => stableStringify(schemaShape(value[key]))))]
            .sort()
            .map(shape => JSON.parse(shape));
        return { kind: 'numeric_key_map', values: valueShapes };
    }
    return {
        kind: 'object',
        fields: keys.map(key => [key, schemaShape(value[key])]),
    };
}

function computeSchemaFingerprint(value) {
    assertPlainJson(value, 'section JSON');
    return canonicalJsonHash(schemaShape(value));
}

function resultFromScores(homeScore, awayScore) {
    const normalizeScore = value => {
        if (Number.isSafeInteger(value) && value >= 0) return value;
        if (typeof value === 'string' && /^\d+$/.test(value)) {
            const parsed = Number(value);
            if (Number.isSafeInteger(parsed)) return parsed;
        }
        return null;
    };
    homeScore = normalizeScore(homeScore);
    awayScore = normalizeScore(awayScore);
    if (homeScore === null || awayScore === null) {
        return {
            status: 'UNAVAILABLE',
            home_score: null,
            away_score: null,
            outcome: null,
            source_path: 'normalized.home_team.score + normalized.away_team.score',
        };
    }
    const outcome = homeScore === awayScore ? 'draw' : homeScore > awayScore ? 'home' : 'away';
    return {
        status: 'AVAILABLE',
        home_score: homeScore,
        away_score: awayScore,
        outcome,
        source_path: 'normalized.home_team.score + normalized.away_team.score',
    };
}

function validateResult(value, label) {
    assertAllowedKeys(value, new Set(['status', 'home_score', 'away_score', 'outcome', 'source_path']), label);
    if (!RESULT_STATUS_VALUES.has(value.status)) fail(`${label}.status is invalid`, 'SCHEMA_MISMATCH');
    if (value.status === 'AVAILABLE') {
        if (!Number.isSafeInteger(value.home_score) || value.home_score < 0) {
            fail(`${label}.home_score is invalid`, 'FACT_VALUE_INVALID');
        }
        if (!Number.isSafeInteger(value.away_score) || value.away_score < 0) {
            fail(`${label}.away_score is invalid`, 'FACT_VALUE_INVALID');
        }
        if (!RESULT_VALUES.has(value.outcome)) fail(`${label}.outcome is invalid`, 'FACT_VALUE_INVALID');
        const expectedOutcome =
            value.home_score === value.away_score ? 'draw' : value.home_score > value.away_score ? 'home' : 'away';
        if (value.outcome !== expectedOutcome) {
            fail(`${label}.outcome is not derived from the scores`, 'FACT_VALUE_INVALID');
        }
    } else if (value.home_score !== null || value.away_score !== null || value.outcome !== null) {
        fail(`${label} unavailable result must not carry a value`, 'FACT_VALUE_INVALID');
    }
    assertText(value.source_path, `${label}.source_path`);
}

function emptyXgProjection(status = 'UNAVAILABLE') {
    return {
        status,
        source_path: 'normalized.shotmap.shots[*].expectedGoals',
        aggregation: 'sum_known_expectedGoals_by_team_id',
        total_shots: null,
        shots_with_xg: null,
        shots_without_xg: null,
        non_own_goal_shots: null,
        non_own_goal_shots_with_xg: null,
        home: { value: null, status: 'UNAVAILABLE', known_shots: 0, missing_shots: 0 },
        away: { value: null, status: 'UNAVAILABLE', known_shots: 0, missing_shots: 0 },
    };
}

function validateXgSide(value, label) {
    assertAllowedKeys(value, new Set(['value', 'status', 'known_shots', 'missing_shots']), label);
    if (!XG_SIDE_STATUS_VALUES.has(value.status)) fail(`${label}.status is invalid`, 'SCHEMA_MISMATCH');
    assertInteger(value.known_shots, `${label}.known_shots`);
    assertInteger(value.missing_shots, `${label}.missing_shots`);
    if (value.value !== null && (typeof value.value !== 'number' || !Number.isFinite(value.value) || value.value < 0)) {
        fail(`${label}.value is invalid`, 'FACT_VALUE_INVALID');
    }
    if (value.status === 'UNAVAILABLE' && value.value !== null) {
        fail(`${label}.unavailable side must not carry a value`, 'FACT_VALUE_INVALID');
    }
    if (value.status === 'COMPLETE' && value.missing_shots !== 0) {
        fail(`${label}.complete side cannot have missing shots`, 'FACT_VALUE_INVALID');
    }
}

function validateXg(value, label) {
    assertAllowedKeys(
        value,
        new Set([
            'status',
            'source_path',
            'aggregation',
            'total_shots',
            'shots_with_xg',
            'shots_without_xg',
            'non_own_goal_shots',
            'non_own_goal_shots_with_xg',
            'home',
            'away',
        ]),
        label
    );
    if (!XG_STATUS_VALUES.has(value.status)) fail(`${label}.status is invalid`, 'SCHEMA_MISMATCH');
    assertText(value.source_path, `${label}.source_path`);
    assertText(value.aggregation, `${label}.aggregation`);
    for (const field of [
        'total_shots',
        'shots_with_xg',
        'shots_without_xg',
        'non_own_goal_shots',
        'non_own_goal_shots_with_xg',
    ]) {
        if (value[field] !== null) assertInteger(value[field], `${label}.${field}`);
    }
    validateXgSide(value.home, `${label}.home`);
    validateXgSide(value.away, `${label}.away`);
    if (value.status === 'UNAVAILABLE' && value.total_shots !== null) {
        fail(`${label}.unavailable projection must not carry counts`, 'FACT_VALUE_INVALID');
    }
    if (
        value.status !== 'UNAVAILABLE' &&
        (value.total_shots === null || value.shots_with_xg === null || value.shots_without_xg === null)
    ) {
        fail(`${label} available projection must carry shot counts`, 'FACT_VALUE_INVALID');
    }
}

function emptyShotsOnTargetProjection(status = 'UNAVAILABLE', unavailableReasonCode = null) {
    return {
        status,
        source_path: 'normalized.shotmap.shots[*].isOnTarget',
        aggregation: 'count_true_isOnTarget_by_team_id',
        total_shots: null,
        shots_with_on_target: null,
        shots_without_on_target: null,
        home: { value: null, status: 'UNAVAILABLE', known_shots: 0, missing_shots: 0 },
        away: { value: null, status: 'UNAVAILABLE', known_shots: 0, missing_shots: 0 },
        ...(unavailableReasonCode ? { unavailable_reason_code: unavailableReasonCode } : {}),
    };
}

function validateShotsOnTargetSide(value, label) {
    assertAllowedKeys(value, new Set(['value', 'status', 'known_shots', 'missing_shots']), label);
    if (!SHOTS_ON_TARGET_SIDE_STATUS_VALUES.has(value.status)) {
        fail(`${label}.status is invalid`, 'SCHEMA_MISMATCH');
    }
    assertInteger(value.known_shots, `${label}.known_shots`);
    assertInteger(value.missing_shots, `${label}.missing_shots`);
    if (value.value !== null && (!Number.isSafeInteger(value.value) || value.value < 0)) {
        fail(`${label}.value is invalid`, 'FACT_VALUE_INVALID');
    }
    if (value.status === 'UNAVAILABLE' && value.value !== null) {
        fail(`${label}.unavailable side must not carry a value`, 'FACT_VALUE_INVALID');
    }
    if (value.status === 'COMPLETE' && value.missing_shots !== 0) {
        fail(`${label}.complete side cannot have missing shots`, 'FACT_VALUE_INVALID');
    }
}

function validateShotsOnTargetStatusConsistency(value, label) {
    const sides = [
        ['home', value.home],
        ['away', value.away],
    ];
    if (value.status === 'UNAVAILABLE') {
        for (const [sideName, side] of sides) {
            if (side.status !== 'UNAVAILABLE') {
                fail(`${label}.${sideName} must be unavailable with an unavailable projection`, 'FACT_VALUE_INVALID');
            }
            if (side.value !== null || side.known_shots !== 0 || side.missing_shots !== 0) {
                fail(`${label}.${sideName} unavailable side must not carry observations`, 'FACT_VALUE_INVALID');
            }
        }
        return;
    }
    if (value.status === 'VALID') {
        for (const [sideName, side] of sides) {
            if (side.status !== 'COMPLETE') {
                fail(`${label}.${sideName} must be complete with a valid projection`, 'FACT_VALUE_INVALID');
            }
        }
        return;
    }
    for (const [sideName, side] of sides) {
        if (side.status === 'UNAVAILABLE') {
            fail(`${label}.${sideName} cannot be unavailable with a partial projection`, 'FACT_VALUE_INVALID');
        }
    }
}

function validateShotsOnTarget(value, label) {
    assertAllowedKeys(
        value,
        new Set([
            'status',
            'source_path',
            'aggregation',
            'total_shots',
            'shots_with_on_target',
            'shots_without_on_target',
            'home',
            'away',
            'unavailable_reason_code',
        ]),
        label
    );
    if (!SHOTS_ON_TARGET_STATUS_VALUES.has(value.status)) {
        fail(`${label}.status is invalid`, 'SCHEMA_MISMATCH');
    }
    assertText(value.source_path, `${label}.source_path`);
    assertText(value.aggregation, `${label}.aggregation`);
    if (value.unavailable_reason_code !== undefined) {
        assertText(value.unavailable_reason_code, `${label}.unavailable_reason_code`);
        if (value.status !== 'UNAVAILABLE') {
            fail(`${label}.unavailable_reason_code requires an unavailable projection`, 'FACT_VALUE_INVALID');
        }
    }
    for (const field of ['total_shots', 'shots_with_on_target', 'shots_without_on_target']) {
        if (value[field] !== null) assertInteger(value[field], `${label}.${field}`);
    }
    validateShotsOnTargetSide(value.home, `${label}.home`);
    validateShotsOnTargetSide(value.away, `${label}.away`);
    validateShotsOnTargetStatusConsistency(value, label);
    if (value.status === 'UNAVAILABLE' && value.total_shots !== null) {
        fail(`${label}.unavailable projection must not carry counts`, 'FACT_VALUE_INVALID');
    }
    if (
        value.status !== 'UNAVAILABLE' &&
        (value.total_shots === null || value.shots_with_on_target === null || value.shots_without_on_target === null)
    ) {
        fail(`${label} available projection must carry shot counts`, 'FACT_VALUE_INVALID');
    }
}

function validateSection(value, section, label) {
    assertAllowedKeys(value, new Set(['present', 'version', 'coverage', 'schema_fingerprint']), label);
    if (typeof value.present !== 'boolean') fail(`${label}.present must be boolean`, 'SCHEMA_MISMATCH');
    if (value.version !== null) assertText(value.version, `${label}.version`);
    assertPlainJson(value.coverage, `${label}.coverage`);
    if (typeof value.coverage.present !== 'boolean' || value.coverage.present !== value.present) {
        fail(`${label}.coverage.present does not match section presence`, 'PROVENANCE_INVALID');
    }
    if (value.present && value.coverage.version !== value.version) {
        fail(`${label}.coverage.version does not match section version`, 'PROVENANCE_INVALID');
    }
    if (value.present) {
        if (value.version !== PARSED_OUTPUT_CONTRACT_VERSION) {
            fail(`${label}.version is not ${PARSED_OUTPUT_CONTRACT_VERSION}`, 'SCHEMA_MISMATCH');
        }
        assertHex(value.schema_fingerprint, `${label}.schema_fingerprint`);
    } else if (value.version !== null || value.schema_fingerprint !== null) {
        fail(`${label} absent section must have null version/fingerprint`, 'FACT_VALUE_INVALID');
    }
    if (!SECTIONS.includes(section)) fail(`${label} is not an allowed fact section`, 'SCHEMA_MISMATCH');
}

function validateTemporal(value, label = 'temporal_semantics') {
    if (stableStringify(value) !== stableStringify(FACT_TIMING)) {
        fail(`${label} must remain MATCH_FACT/POSTMATCH_ONLY`, 'TEMPORAL_SEMANTICS_UNPROVEN');
    }
}

function validateScope(value) {
    if (stableStringify(value) !== stableStringify(SCOPE)) {
        fail('GD-A02 scope boundary was widened', 'SCOPE_VIOLATION');
    }
}

function validateProvenance(value, label) {
    assertAllowedKeys(value, new Set(['frozen', 'staging', 'capture']), label);
    const required = {
        frozen: {
            fields: [
                'snapshot_id',
                'target_population_hash',
                'manifest_sha256',
                'fotmob_match_id',
                'raw_payload_sha256',
                'source_artifact_class',
                'capture_origin',
            ],
            hashes: ['snapshot_id', 'target_population_hash', 'manifest_sha256', 'raw_payload_sha256'],
        },
        staging: {
            fields: [
                'artifact_schema_version',
                'observation_id',
                'business_hash',
                'artifact_integrity_sha256',
                'stable_payload_sha256',
                'payload_file_sha256',
                'capture_manifest_sha256',
            ],
            hashes: [
                'business_hash',
                'artifact_integrity_sha256',
                'stable_payload_sha256',
                'payload_file_sha256',
                'capture_manifest_sha256',
            ],
        },
        capture: {
            fields: [
                'source_provider',
                'parser_component',
                'parser_version',
                'parser_output_contract_version',
                'payload_file_sha256',
                'manifest_file_sha256',
                'stable_payload_sha256',
                'capture_manifest_sha256',
            ],
            hashes: ['payload_file_sha256', 'manifest_file_sha256', 'stable_payload_sha256', 'capture_manifest_sha256'],
        },
    };
    for (const [part, contract] of Object.entries(required)) {
        assertAllowedKeys(value[part], new Set(contract.fields), `${label}.${part}`);
        for (const field of contract.fields) {
            assertText(value[part][field], `${label}.${part}.${field}`);
        }
        for (const field of contract.hashes) assertHex(value[part][field], `${label}.${part}.${field}`);
    }
}

function validateFactsRow(row, index, { requireShotsOnTarget = false } = {}) {
    const label = `artifact.rows[${index}]`;
    assertAllowedKeys(
        row,
        new Set([
            'canonical_match_id',
            'competition',
            'season',
            'kickoff_at',
            'home_team',
            'away_team',
            'source_linkage',
            'provenance',
            'temporal_semantics',
            'facts',
            'admission',
        ]),
        label
    );
    for (const field of ['canonical_match_id', 'competition', 'season', 'kickoff_at', 'home_team', 'away_team']) {
        assertText(row[field], `${label}.${field}`);
    }
    validateMatchLink(row.source_linkage, label);
    if (row.source_linkage.authority !== 'src/infrastructure/odds_staging/matchLinker.js') {
        fail(`${label}.source_linkage does not use the canonical match linker`, 'IDENTITY_CONFLICT');
    }
    if (row.source_linkage.matched_id !== row.canonical_match_id) {
        fail(`${label}.source_linkage points to another canonical match`, 'IDENTITY_CONFLICT');
    }
    validateProvenance(row.provenance, `${label}.provenance`);
    validateTemporal(row.temporal_semantics, `${label}.temporal_semantics`);
    assertFactsObject(row.facts, `${label}.facts`);
    assertAllowedKeys(row.facts, new Set(['sections', 'match_result', 'xg', 'shots_on_target']), `${label}.facts`);
    assertFactsObject(row.facts.sections, `${label}.facts.sections`);
    assertAllowedKeys(row.facts.sections, new Set(SECTIONS), `${label}.facts.sections`);
    for (const section of SECTIONS) {
        validateSection(row.facts.sections[section], section, `${label}.facts.sections.${section}`);
    }
    validateResult(row.facts.match_result, `${label}.facts.match_result`);
    validateXg(row.facts.xg, `${label}.facts.xg`);
    if (requireShotsOnTarget && !row.facts.shots_on_target) {
        fail(`${label}.facts.shots_on_target is required by the v2 contract`, 'SCHEMA_MISMATCH');
    }
    if (row.facts.shots_on_target) {
        validateShotsOnTarget(row.facts.shots_on_target, `${label}.facts.shots_on_target`);
    }
    assertAllowedKeys(row.admission, new Set(['status', 'rejection_reason']), `${label}.admission`);
    if (row.admission.status !== 'ADMITTED' || row.admission.rejection_reason !== null) {
        fail(`${label}.admission is not admitted`, 'SCHEMA_MISMATCH');
    }
    return row;
}

function validateRejectedRow(row, index) {
    const label = `artifact.rejected_rows[${index}]`;
    assertAllowedKeys(
        row,
        new Set(['canonical_match_id', 'source_match_id', 'admission', 'error_code', 'reason']),
        label
    );
    assertText(row.canonical_match_id, `${label}.canonical_match_id`);
    if (row.source_match_id !== null) assertText(row.source_match_id, `${label}.source_match_id`);
    assertAllowedKeys(row.admission, new Set(['status', 'rejection_reason']), `${label}.admission`);
    if (row.admission.status !== 'REJECTED' || typeof row.admission.rejection_reason !== 'string') {
        fail(`${label}.admission is incomplete`, 'SCHEMA_MISMATCH');
    }
    assertText(row.error_code, `${label}.error_code`);
    assertText(row.reason, `${label}.reason`);
    assertPlainJson(row, label);
    return row;
}

function validateSourceBindings(value) {
    assertFactsObject(value, 'artifact.source_bindings');
    for (const key of Object.keys(value)) {
        if (!SOURCE_BINDING_KEYS.has(key)) fail(`unsupported source binding ${key}`, 'SCHEMA_MISMATCH');
        assertPlainJson(value[key], `artifact.source_bindings.${key}`);
    }
    for (const key of SOURCE_BINDING_KEYS) {
        if (!value[key]) fail(`missing source binding ${key}`, 'PROVENANCE_INVALID');
    }
    const bindingFields = {
        gd_a01_artifact: ['sha256', 'business_hash'],
        gd_a01_receipt: ['sha256', 'output_business_hash'],
        fotmob_freeze: ['sha256', 'snapshot_id', 'target_population_hash', 'manifest_sha256', 'raw_payload_count'],
        fotmob_manifest: ['sha256', 'row_count'],
        fotmob_facts_source_index: [
            'sha256',
            'entry_count',
            'artifact_set_sha256',
            'payload_set_sha256',
            'manifest_set_sha256',
            'admitted_fact_count',
        ],
    };
    for (const [part, fields] of Object.entries(bindingFields)) {
        assertAllowedKeys(value[part], new Set(fields), `artifact.source_bindings.${part}`);
        for (const field of fields) {
            if (!(field in value[part])) fail(`missing source binding ${part}.${field}`, 'PROVENANCE_INVALID');
        }
    }
    const hashFields = [
        ['gd_a01_artifact', 'sha256'],
        ['gd_a01_artifact', 'business_hash'],
        ['gd_a01_receipt', 'sha256'],
        ['gd_a01_receipt', 'output_business_hash'],
        ['fotmob_freeze', 'sha256'],
        ['fotmob_freeze', 'manifest_sha256'],
        ['fotmob_manifest', 'sha256'],
        ['fotmob_facts_source_index', 'sha256'],
        ['fotmob_facts_source_index', 'artifact_set_sha256'],
        ['fotmob_facts_source_index', 'payload_set_sha256'],
        ['fotmob_facts_source_index', 'manifest_set_sha256'],
    ];
    for (const [part, field] of hashFields) assertHex(value[part][field], `artifact.source_bindings.${part}.${field}`);
    for (const [part, field] of [
        ['fotmob_freeze', 'snapshot_id'],
        ['fotmob_freeze', 'target_population_hash'],
        ['fotmob_freeze', 'raw_payload_count'],
        ['fotmob_manifest', 'row_count'],
        ['fotmob_facts_source_index', 'entry_count'],
        ['fotmob_facts_source_index', 'admitted_fact_count'],
    ]) {
        if (field.endsWith('_count') || field === 'row_count' || field === 'entry_count') {
            assertInteger(
                value[part][field],
                `artifact.source_bindings.${part}.${field}`,
                field === 'admitted_fact_count' ? 0 : 1
            );
        } else {
            assertText(value[part][field], `artifact.source_bindings.${part}.${field}`);
        }
    }
    return value;
}

function scanForbiddenContent(value, pathLabel = 'artifact', seen = new WeakSet()) {
    if (value === null || value === undefined) return;
    if (typeof value === 'string') {
        const lower = value.toLowerCase();
        if (PROHIBITED_VALUE_SIGNATURES.some(signature => lower.includes(signature))) {
            fail(`${pathLabel} contains prohibited raw content`, 'SCOPE_VIOLATION');
        }
        return;
    }
    if (typeof value !== 'object') return;
    if (seen.has(value)) fail(`${pathLabel} contains a cycle`, 'SCHEMA_MISMATCH');
    seen.add(value);
    try {
        if (Array.isArray(value)) {
            value.forEach((item, index) => scanForbiddenContent(item, `${pathLabel}[${index}]`, seen));
        } else {
            const isScopeDeclaration = pathLabel === 'artifact.scope';
            for (const [key, child] of Object.entries(value)) {
                if (!isScopeDeclaration && FORBIDDEN_KEYS.has(key.toLowerCase())) {
                    fail(`${pathLabel}.${key} is outside GD-A02 scope`, 'SCOPE_VIOLATION');
                }
                scanForbiddenContent(child, `${pathLabel}.${key}`, seen);
            }
        }
    } finally {
        seen.delete(value);
    }
}

// eslint-disable-next-line complexity
function validateFactsArtifact(document, options = {}) {
    assertFactsObject(document, 'GD-A02 artifact');
    assertAllowedKeys(
        document,
        new Set([
            'schema_version',
            'stage',
            'artifact_kind',
            'source_bindings',
            'temporal_semantics',
            'scope',
            'population_accounting',
            'rows',
            'rejected_rows',
            'business_content_sha256',
        ]),
        'GD-A02 artifact'
    );
    const isCurrentSchema = document.schema_version === FACTS_ASSEMBLY_SCHEMA_VERSION;
    const isLegacySchema = document.schema_version === LEGACY_FACTS_ASSEMBLY_SCHEMA_VERSION;
    if (!isCurrentSchema && !isLegacySchema) {
        fail('GD-A02 artifact schema is unsupported', 'UNSUPPORTED_VERSION');
    }
    if (document.stage !== STAGE || document.artifact_kind !== ARTIFACT_KIND) {
        fail('GD-A02 artifact stage/kind mismatch', 'SCHEMA_MISMATCH');
    }
    assertSha(document.business_content_sha256, 'GD-A02 artifact business_content_sha256');
    validateSourceBindings(document.source_bindings);
    validateTemporal(document.temporal_semantics);
    validateScope(document.scope);
    assertFactsObject(document.population_accounting, 'artifact.population_accounting');
    assertAllowedKeys(
        document.population_accounting,
        new Set([
            'input_match_count',
            'admitted_count',
            'rejected_or_quarantined_count',
            'unaccounted_count',
            'duplicate_id_count',
            'extra_id_count',
        ]),
        'artifact.population_accounting'
    );
    for (const field of Object.keys(document.population_accounting)) {
        assertInteger(document.population_accounting[field], `artifact.population_accounting.${field}`);
    }
    if (
        document.population_accounting.unaccounted_count !== 0 ||
        document.population_accounting.duplicate_id_count !== 0 ||
        document.population_accounting.extra_id_count !== 0
    ) {
        fail('GD-A02 population accounting is not conserved', 'POPULATION_MISMATCH');
    }
    if (!Array.isArray(document.rows)) fail('GD-A02 artifact rows must be an array', 'SCHEMA_MISMATCH');
    if (!Array.isArray(document.rejected_rows)) fail('GD-A02 rejected_rows must be an array', 'SCHEMA_MISMATCH');
    if (document.rows.length === 0 && document.rejected_rows.length === 0) {
        fail('GD-A02 artifact must contain admitted or rejected rows', 'POPULATION_MISMATCH');
    }
    const rows = document.rows.map((row, index) =>
        validateFactsRow(row, index, { requireShotsOnTarget: isCurrentSchema })
    );
    const rejectedRows = document.rejected_rows.map(validateRejectedRow);
    const admittedIds = new Set();
    for (const row of rows) {
        if (admittedIds.has(row.canonical_match_id)) {
            fail(`duplicate admitted ID ${row.canonical_match_id}`, 'POPULATION_MISMATCH');
        }
        admittedIds.add(row.canonical_match_id);
    }
    const accountedIds = new Set(admittedIds);
    for (const row of rejectedRows) {
        if (accountedIds.has(row.canonical_match_id)) {
            fail(`duplicate accounted ID ${row.canonical_match_id}`, 'POPULATION_MISMATCH');
        }
        accountedIds.add(row.canonical_match_id);
    }
    const sortedRows = [...rows].sort((a, b) => a.canonical_match_id.localeCompare(b.canonical_match_id));
    const sortedRejected = [...rejectedRows].sort((a, b) => a.canonical_match_id.localeCompare(b.canonical_match_id));
    if (stableStringify(rows) !== stableStringify(sortedRows)) {
        fail('GD-A02 rows are not deterministically ordered', 'DETERMINISM_FAILURE');
    }
    if (stableStringify(rejectedRows) !== stableStringify(sortedRejected)) {
        fail('GD-A02 rejected rows are not ordered', 'DETERMINISM_FAILURE');
    }
    if (document.population_accounting.input_match_count !== accountedIds.size) {
        fail('GD-A02 input/accounted population mismatch', 'POPULATION_MISMATCH');
    }
    if (
        document.population_accounting.admitted_count !== rows.length ||
        document.population_accounting.rejected_or_quarantined_count !== rejectedRows.length
    ) {
        fail('GD-A02 accounting counts disagree with rows', 'POPULATION_MISMATCH');
    }
    const sourcePopulation = document.source_bindings.fotmob_freeze.raw_payload_count;
    if (
        sourcePopulation !== document.population_accounting.input_match_count ||
        document.source_bindings.fotmob_manifest.row_count !== document.population_accounting.input_match_count ||
        document.source_bindings.fotmob_facts_source_index.entry_count !==
            document.population_accounting.input_match_count ||
        document.source_bindings.fotmob_facts_source_index.admitted_fact_count !== rows.length
    ) {
        fail('GD-A02 source binding population disagrees with artifact accounting', 'POPULATION_MISMATCH');
    }
    if (
        document.population_accounting.unaccounted_count !==
        document.population_accounting.input_match_count - accountedIds.size
    ) {
        fail('GD-A02 unaccounted count is incorrect', 'POPULATION_MISMATCH');
    }
    if (options.expectedAdmittedRows !== undefined && rows.length !== Number(options.expectedAdmittedRows)) {
        fail('GD-A02 admitted count does not match upstream profile', 'POPULATION_MISMATCH');
    }
    scanForbiddenContent(document);
    const recomputed = computeArtifactBusinessHash(document);
    if (recomputed !== document.business_content_sha256) {
        fail('GD-A02 artifact business hash mismatch', 'BUSINESS_HASH_MISMATCH');
    }
    return { ...document, rows, rejected_rows: rejectedRows };
}

function computeArtifactBusinessProjection(artifact) {
    const { business_content_sha256: ignored, ...projection } = artifact;
    return projection;
}

function computeArtifactBusinessHash(artifact) {
    return sha256Text(stableStringify(computeArtifactBusinessProjection(artifact)));
}

function computeFactsSetHash(entries, field) {
    return sha256Text(
        stableStringify(
            entries
                .map(entry => ({ canonical_match_id: entry.canonical_match_id, value: entry[field] }))
                .sort((a, b) => a.canonical_match_id.localeCompare(b.canonical_match_id))
        )
    );
}

function validateFactsSourceIndex(document) {
    assertFactsObject(document, 'GD-A02 facts source index');
    if (document.schema_version !== FACTS_SOURCE_INDEX_SCHEMA_VERSION) {
        fail('GD-A02 source index schema is unsupported', 'UNSUPPORTED_VERSION');
    }
    if (document.source_provider !== 'FotMob') fail('GD-A02 source index provider must be FotMob', 'SCHEMA_MISMATCH');
    if (!Array.isArray(document.entries) || document.entries.length === 0) {
        fail('GD-A02 source index entries are required', 'POPULATION_MISMATCH');
    }
    const allowed = new Set([
        'canonical_match_id',
        'staging_artifact_path',
        'capture_payload_path',
        'capture_manifest_path',
        'staging_artifact_sha256',
        'capture_payload_sha256',
        'capture_manifest_file_sha256',
    ]);
    const seen = new Set();
    const entries = document.entries.map((entry, index) => {
        assertAllowedKeys(entry, allowed, `facts source index entries[${index}]`);
        assertText(entry.canonical_match_id, `facts source index entries[${index}].canonical_match_id`);
        if (seen.has(entry.canonical_match_id)) {
            fail(`duplicate source index canonical ID ${entry.canonical_match_id}`, 'POPULATION_MISMATCH');
        }
        seen.add(entry.canonical_match_id);
        for (const field of ['staging_artifact_path', 'capture_payload_path', 'capture_manifest_path']) {
            assertText(entry[field], `facts source index entries[${index}].${field}`);
            if (!entry[field].startsWith('/')) fail(`${field} must be absolute`, 'PATH_INVALID');
        }
        for (const field of ['staging_artifact_sha256', 'capture_payload_sha256', 'capture_manifest_file_sha256']) {
            assertHex(entry[field], `facts source index entries[${index}].${field}`);
        }
        return entry;
    });
    return entries;
}

function validateReceiptHeader(receipt) {
    if (
        receipt.schema_version !== FACTS_RECEIPT_SCHEMA_VERSION &&
        receipt.schema_version !== LEGACY_FACTS_RECEIPT_SCHEMA_VERSION
    ) {
        fail('GD-A02 receipt schema is unsupported', 'UNSUPPORTED_VERSION');
    }
    if (receipt.stage !== STAGE || receipt.build_mode !== 'file_first') {
        fail('GD-A02 receipt stage/build mode mismatch', 'SCHEMA_MISMATCH');
    }
    assertRevision(receipt.code_revision, 'GD-A02 receipt code_revision');
    if (!['COMPLETE', 'INCOMPLETE_REJECTED'].includes(receipt.status)) {
        fail('GD-A02 receipt status is invalid', 'SCHEMA_MISMATCH');
    }
    for (const field of [
        'artifact_sha256',
        'output_business_sha256',
        'admitted_id_set_sha256',
        'accounted_id_set_sha256',
    ]) {
        assertHex(receipt[field], `GD-A02 receipt ${field}`);
    }
    for (const field of ['input_match_count', 'admitted_row_count', 'rejected_row_count', 'unaccounted_row_count']) {
        assertInteger(receipt[field], `GD-A02 receipt ${field}`);
    }
    validateTemporal(receipt.temporal_semantics, 'GD-A02 receipt temporal_semantics');
    validateScope(receipt.scope);
}

// eslint-disable-next-line complexity -- receipt/document binding is one fail-closed invariant.
function validateReceiptDocument(receipt, artifactBytes = null, artifact = null) {
    assertFactsObject(receipt, 'GD-A02 receipt');
    assertAllowedKeys(
        receipt,
        new Set([
            'schema_version',
            'stage',
            'build_mode',
            'code_revision',
            'source_bindings',
            'input_match_count',
            'admitted_row_count',
            'rejected_row_count',
            'unaccounted_row_count',
            'admitted_id_set_sha256',
            'accounted_id_set_sha256',
            'output_business_sha256',
            'artifact_sha256',
            'temporal_semantics',
            'scope',
            'status',
        ]),
        'GD-A02 receipt'
    );
    validateReceiptHeader(receipt);
    validateSourceBindings(receipt.source_bindings);
    if (artifactBytes && receipt.artifact_sha256 !== sha256Bytes(artifactBytes)) {
        fail('GD-A02 receipt artifact byte hash mismatch', 'ARTIFACT_HASH_MISMATCH');
    }
    if (artifact) {
        const normalizedArtifact = validateFactsArtifact(artifact);
        if (
            (normalizedArtifact.schema_version === FACTS_ASSEMBLY_SCHEMA_VERSION &&
                receipt.schema_version !== FACTS_RECEIPT_SCHEMA_VERSION) ||
            (normalizedArtifact.schema_version === LEGACY_FACTS_ASSEMBLY_SCHEMA_VERSION &&
                receipt.schema_version !== LEGACY_FACTS_RECEIPT_SCHEMA_VERSION)
        ) {
            fail('GD-A02 artifact/receipt schema versions do not match', 'UNSUPPORTED_VERSION');
        }
        if (receipt.output_business_sha256 !== normalizedArtifact.business_content_sha256) {
            fail('GD-A02 receipt business hash mismatch', 'BUSINESS_HASH_MISMATCH');
        }
        if (
            receipt.input_match_count !== normalizedArtifact.population_accounting.input_match_count ||
            receipt.admitted_row_count !== normalizedArtifact.rows.length ||
            receipt.rejected_row_count !== normalizedArtifact.rejected_rows.length
        ) {
            fail('GD-A02 receipt population mismatch', 'POPULATION_MISMATCH');
        }
        if (receipt.unaccounted_row_count !== normalizedArtifact.population_accounting.unaccounted_count) {
            fail('GD-A02 receipt unaccounted count mismatch', 'POPULATION_MISMATCH');
        }
        if (
            receipt.admitted_id_set_sha256 !==
            admittedIdSetHash(normalizedArtifact.rows.map(row => row.canonical_match_id))
        ) {
            fail('GD-A02 receipt admitted ID hash mismatch', 'BUSINESS_HASH_MISMATCH');
        }
        if (
            receipt.accounted_id_set_sha256 !==
            admittedIdSetHash(
                [...normalizedArtifact.rows, ...normalizedArtifact.rejected_rows].map(row => row.canonical_match_id)
            )
        ) {
            fail('GD-A02 receipt accounted ID hash mismatch', 'BUSINESS_HASH_MISMATCH');
        }
        if (stableStringify(receipt.source_bindings) !== stableStringify(normalizedArtifact.source_bindings)) {
            fail('GD-A02 receipt source bindings mismatch', 'BUSINESS_HASH_MISMATCH');
        }
    }
    return receipt;
}

function validateOutputFiles(artifactBytes, receiptBytes, options = {}) {
    let artifact;
    let receipt;
    try {
        artifact = JSON.parse(Buffer.from(artifactBytes).toString('utf8'));
        receipt = JSON.parse(Buffer.from(receiptBytes).toString('utf8'));
    } catch (error) {
        fail(`GD-A02 output is not valid JSON: ${error.message}`, 'SCHEMA_MISMATCH');
    }
    const normalizedArtifact = validateFactsArtifact(artifact, options);
    validateReceiptDocument(receipt, artifactBytes, normalizedArtifact);
    return { artifact: normalizedArtifact, receipt };
}

module.exports = {
    ARTIFACT_KIND,
    FACTS_ASSEMBLY_SCHEMA_VERSION,
    LEGACY_FACTS_ASSEMBLY_SCHEMA_VERSION,
    FACTS_RECEIPT_SCHEMA_VERSION,
    LEGACY_FACTS_RECEIPT_SCHEMA_VERSION,
    FACTS_SOURCE_INDEX_SCHEMA_VERSION,
    FACT_TIMING,
    GdA02ContractError,
    PARSED_OUTPUT_CONTRACT_VERSION,
    SCOPE,
    SECTIONS,
    admittedIdSetHash,
    computeArtifactBusinessHash,
    computeArtifactBusinessProjection,
    computeFactsSetHash,
    computeSchemaFingerprint,
    emptyXgProjection,
    emptyShotsOnTargetProjection,
    resultFromScores,
    sha256Bytes,
    stableStringify,
    validateFactsArtifact,
    validateFactsSourceIndex,
    validateOutputFiles,
    validateReceiptDocument,
    validateReceiptHeader,
    validateResult,
    validateScope,
    validateTemporal,
    validateXg,
    validateShotsOnTarget,
};
