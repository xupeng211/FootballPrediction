'use strict';

/* eslint-disable max-lines -- one versioned input boundary must remain reviewable as one contract. */
/* eslint-disable complexity -- fail-closed temporal/state validation is intentionally explicit. */

// lifecycle: permanent
// 纯内存、确定性的 standings as-of engine input contract validator。
// 本模块不读取文件、数据库、环境、网络、Git 或墙钟，也不调用 standings engine。

const { sha256Text, stableStringify } = require('../canonical/StableValue');
const {
    assertStandingsContractBinding,
    STANDINGS_COMPETITION,
    STANDINGS_CONTRACT_ID,
    STANDINGS_CONTRACT_VERSION,
    STANDINGS_LEAGUE_ID,
    STANDINGS_SEASONS,
} = require('./StandingsContractBinding');

const STANDINGS_ASOF_ENGINE_INPUT_CONTRACT_ID = 'standings-asof-engine-input/v1';
const STANDINGS_ASOF_ENGINE_INPUT_CONTRACT_VERSION = 'v1';
const STANDINGS_ASOF_ENGINE_INPUT_CONTRACT_STATUS = 'FROZEN';
const STANDINGS_ENGINE_IMPLEMENTATION_FAMILY = 'PointInTimeStandingsEngine';

const MODEL_ASOF_CONTRACT_ID = 'canonical-model-asof/v1';
const MODEL_ASOF_CONTRACT_VERSION = 'v1';
const RUNTIME_CAPTURE_CONTRACT_ID = 'canonical-runtime-capture/v1';
const RUNTIME_CAPTURE_CONTRACT_VERSION = 'v1';

const FIXTURE_STATES = Object.freeze([
    'RESULT_AVAILABLE_AT_T',
    'NO_TABLE_RESULT_AT_T',
    'REQUIRED_EVIDENCE_MISSING_AT_T',
    'ASOF_STATE_AMBIGUOUS',
    'TARGET_FIXTURE_EXCLUDED',
]);
const NO_TABLE_RESULT_REASONS = Object.freeze([
    'SCHEDULE_NOT_YET_REACHED_AT_T',
    'PROVEN_POSTPONED_NOT_PLAYED_BY_T',
    'PROVEN_NOT_FINAL_BY_T',
    'PROVEN_NON_TABLE_ELIGIBLE_BY_T',
    'PROVEN_ABANDONED_NON_TABLE_ELIGIBLE_BY_T',
    'PROVEN_VOID_NON_TABLE_ELIGIBLE_BY_T',
    'PROVEN_REPLAY_ORIGINAL_NON_ELIGIBLE_BY_T',
]);
const ADJUSTMENT_STATES = Object.freeze([
    'EFFECTIVE_AND_AVAILABLE_AT_T',
    'KNOWN_NOT_EFFECTIVE_AT_T',
    'ASOF_ADJUSTMENT_AMBIGUOUS',
]);
const AVAILABILITY_PROOF_KINDS = Object.freeze([
    'EXACT_OBSERVATION_TIMESTAMP',
    'EXACT_EFFECTIVE_TIMESTAMP_WITH_SOURCE_OBSERVATION_PROOF',
    'BOUNDED_INTERVAL_ENTIRELY_BEFORE_T',
]);
const FAIL_CLOSED_REASON_CODES = Object.freeze([
    'STANDINGS_ASOF_INPUT_CONTRACT_MISMATCH',
    'MODEL_ASOF_BINDING_MISMATCH',
    'ASOF_DECISION_TIME_INVALID',
    'TARGET_KICKOFF_IDENTITY_CONFLICT',
    'FIXTURE_UNIVERSE_INCOMPLETE',
    'FIXTURE_ASOF_STATE_MISSING',
    'FIXTURE_ASOF_STATE_DUPLICATE',
    'FIXTURE_ASOF_STATE_UNKNOWN',
    'RESULT_AVAILABLE_AT_T_UNPROVEN',
    'REQUIRED_EVIDENCE_MISSING_AT_T',
    'ASOF_STATE_AMBIGUOUS',
    'POST_DECISION_STANDINGS_EVIDENCE',
    'STANDINGS_SOURCE_CLOSURE_UNPROVEN',
    'ADMIN_ADJUSTMENT_ASOF_AMBIGUOUS',
    'TARGET_FIXTURE_NOT_EXCLUDED',
]);

const UTC_TIMESTAMP = /^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d{3})?Z$/;
const SHA256 = /^[0-9a-f]{64}$/;

const BOUNDARY_FIELDS = new Set([
    'contract_id',
    'version',
    'status',
    'standings_contract',
    'model_as_of_contract',
    'runtime_capture_contract',
    'implementation_family',
    'evaluation_boundary',
    'fixture_universe',
    'source_stream_closure',
    'fixture_state_taxonomy',
    'no_table_result_reason_codes',
    'adjustment_state_taxonomy',
    'availability_proof',
    'trust_boundary',
    'readiness',
    'fail_closed_reason_codes',
    'digest',
]);
const REFERENCE_FIELDS = new Set(['referenceId', 'referenceVersion', 'referenceSha256', 'fixtureIds']);
const FIXTURE_FIELDS = new Set([
    'canonicalMatchId',
    'competition',
    'leagueId',
    'season',
    'homeTeamId',
    'awayTeamId',
    'scheduledKickoffUtc',
    'sourceLineage',
]);
const TARGET_FIELDS = new Set([
    'canonicalMatchId',
    'competition',
    'leagueId',
    'season',
    'homeTeamId',
    'awayTeamId',
    'targetKickoffUtc',
    'sourceLineage',
]);
const LINEAGE_FIELDS = new Set(['evidenceRefs', 'sourceRecordRef']);
const BASIS_FIELDS = new Set(['reasonCode', 'evidenceRefs', 'availabilityProofRef']);
const FIXTURE_STATE_FIELDS = new Set(['canonicalMatchId', 'state', 'basis', 'result']);
const RESULT_FIELDS = new Set([
    'canonicalMatchId',
    'competition',
    'leagueId',
    'season',
    'homeTeamId',
    'awayTeamId',
    'actualEligibleEventTimeUtc',
    'disposition',
    'tableEligibility',
    'finalityStatus',
    'homeScore',
    'awayScore',
    'sourceLineage',
    'availabilityProof',
    'replayOfMatchId',
]);
const AVAILABILITY_PROOF_FIELDS = new Set([
    'kind',
    'observedAtUtc',
    'effectiveAtUtc',
    'intervalStartUtc',
    'intervalEndUtc',
    'proofRef',
]);
const ADJUSTMENT_FIELDS = new Set([
    'adjustmentId',
    'competition',
    'leagueId',
    'season',
    'teamId',
    'delta',
    'state',
    'effectiveTime',
    'sourceLineage',
    'availabilityProof',
]);
const EFFECTIVE_TIME_FIELDS = new Set(['kind', 'atUtc', 'lowerBoundUtc', 'upperBoundUtc']);
const INPUT_FIELDS = new Set([
    'contractBoundary',
    'standingsContractBinding',
    'modelDecisionTimeUtc',
    'featureAsOfUtc',
    'target',
    'fixtureUniverse',
    'fixtureStates',
    'administrativeAdjustments',
]);

class StandingsAsOfEngineInputContractError extends Error {
    constructor(message, code = 'STANDINGS_ASOF_INPUT_CONTRACT_MISMATCH') {
        super(message);
        this.name = 'StandingsAsOfEngineInputContractError';
        this.code = code;
        this.reasonCode = code;
    }
}

function isPlainObject(value) {
    return value !== null && typeof value === 'object' && !Array.isArray(value);
}

function fail(message, code = 'STANDINGS_ASOF_INPUT_CONTRACT_MISMATCH') {
    throw new StandingsAsOfEngineInputContractError(message, code);
}

function assertPlainObject(value, label, code) {
    if (!isPlainObject(value)) fail(`${label} must be an object`, code);
    return value;
}

function assertKnownKeys(value, allowed, label, code) {
    for (const key of Object.keys(value)) {
        if (!allowed.has(key)) fail(`${label} contains unsupported field ${key}`, code);
    }
}

function assertExactKeys(value, allowed, label, code) {
    assertKnownKeys(value, allowed, label, code);
    if (Object.keys(value).length !== allowed.size) fail(`${label} is incomplete`, code);
}

function assertText(value, label, code) {
    if (typeof value !== 'string' || value.trim() === '') fail(`${label} must be non-empty text`, code);
    return value;
}

function assertInteger(value, label, code) {
    if (!Number.isSafeInteger(value)) fail(`${label} must be a safe integer`, code);
    return value;
}

function assertSha256(value, label, code) {
    if (typeof value !== 'string' || !SHA256.test(value)) fail(`${label} must be lowercase SHA-256`, code);
    return value;
}

function parseUtc(value, label, code = 'ASOF_DECISION_TIME_INVALID') {
    if (typeof value !== 'string' || !UTC_TIMESTAMP.test(value)) fail(`${label} is not absolute UTC`, code);
    const milliseconds = Date.parse(value);
    if (!Number.isFinite(milliseconds)) fail(`${label} is invalid UTC`, code);
    return milliseconds;
}

function assertTextList(value, label, { allowEmpty = false, code } = {}) {
    if (!Array.isArray(value) || (!allowEmpty && value.length === 0)) fail(`${label} is malformed`, code);
    if (value.some(item => typeof item !== 'string' || item.trim() === '')) {
        fail(`${label} contains malformed text`, code);
    }
    if (new Set(value).size !== value.length) fail(`${label} contains duplicates`, code);
    return value;
}

function sortedTextList(value) {
    return [...value].sort((left, right) => left.localeCompare(right));
}

function assertExactValue(actual, expected, label, code) {
    if (stableStringify(actual) !== stableStringify(expected)) fail(`${label} differs from frozen contract`, code);
}

function assertLineage(value, label) {
    assertPlainObject(value, label, 'STANDINGS_ASOF_INPUT_CONTRACT_MISMATCH');
    assertExactKeys(value, LINEAGE_FIELDS, label, 'STANDINGS_ASOF_INPUT_CONTRACT_MISMATCH');
    const evidenceRefs = assertTextList(value.evidenceRefs, `${label}.evidenceRefs`, {
        code: 'STANDINGS_ASOF_INPUT_CONTRACT_MISMATCH',
    });
    assertText(value.sourceRecordRef, `${label}.sourceRecordRef`, 'STANDINGS_ASOF_INPUT_CONTRACT_MISMATCH');
    return { evidenceRefs: sortedTextList(evidenceRefs), sourceRecordRef: value.sourceRecordRef };
}

function assertBoundaryReference(value, label, expectedId, expectedVersion) {
    assertPlainObject(value, label, 'STANDINGS_ASOF_INPUT_CONTRACT_MISMATCH');
    assertExactKeys(value, new Set(['contract_id', 'version']), label, 'STANDINGS_ASOF_INPUT_CONTRACT_MISMATCH');
    if (value.contract_id !== expectedId || value.version !== expectedVersion) {
        fail(`${label} does not match the frozen authority`, 'MODEL_ASOF_BINDING_MISMATCH');
    }
    return { contract_id: value.contract_id, version: value.version };
}

function validateContractBoundary(value) {
    const boundary = assertPlainObject(value, 'contractBoundary', 'STANDINGS_ASOF_INPUT_CONTRACT_MISMATCH');
    assertExactKeys(boundary, BOUNDARY_FIELDS, 'contractBoundary', 'STANDINGS_ASOF_INPUT_CONTRACT_MISMATCH');
    if (
        boundary.contract_id !== STANDINGS_ASOF_ENGINE_INPUT_CONTRACT_ID ||
        boundary.version !== STANDINGS_ASOF_ENGINE_INPUT_CONTRACT_VERSION ||
        boundary.status !== STANDINGS_ASOF_ENGINE_INPUT_CONTRACT_STATUS
    ) {
        fail('standings as-of input contract identity is not frozen', 'STANDINGS_ASOF_INPUT_CONTRACT_MISMATCH');
    }
    const standingsContract = assertBoundaryReference(
        boundary.standings_contract,
        'contractBoundary.standings_contract',
        STANDINGS_CONTRACT_ID,
        STANDINGS_CONTRACT_VERSION
    );
    const modelAsOfContract = assertBoundaryReference(
        boundary.model_as_of_contract,
        'contractBoundary.model_as_of_contract',
        MODEL_ASOF_CONTRACT_ID,
        MODEL_ASOF_CONTRACT_VERSION
    );
    const runtimeCaptureContract = assertBoundaryReference(
        boundary.runtime_capture_contract,
        'contractBoundary.runtime_capture_contract',
        RUNTIME_CAPTURE_CONTRACT_ID,
        RUNTIME_CAPTURE_CONTRACT_VERSION
    );
    assertText(boundary.implementation_family, 'contractBoundary.implementation_family');
    if (boundary.implementation_family !== STANDINGS_ENGINE_IMPLEMENTATION_FAMILY) {
        fail('contractBoundary implementation family is not the existing engine family');
    }

    const evaluationBoundary = assertPlainObject(
        boundary.evaluation_boundary,
        'contractBoundary.evaluation_boundary',
        'STANDINGS_ASOF_INPUT_CONTRACT_MISMATCH'
    );
    assertExactKeys(
        evaluationBoundary,
        new Set([
            'model_decision_time_field',
            'feature_as_of_field',
            'target_kickoff_field',
            'model_decision_time_is_asof_boundary',
            'target_kickoff_is_evaluation_boundary',
            'prematch_requires_t_lt_target_kickoff',
            'target_kickoff_relabeling_forbidden',
            'prefilter_only_proves_asof_compatibility',
        ]),
        'contractBoundary.evaluation_boundary',
        'STANDINGS_ASOF_INPUT_CONTRACT_MISMATCH'
    );
    assertExactValue(
        evaluationBoundary,
        {
            model_decision_time_field: 'MODEL_DECISION_TIME_UTC',
            feature_as_of_field: 'FEATURE_AS_OF_UTC',
            target_kickoff_field: 'TARGET_KICKOFF_UTC',
            model_decision_time_is_asof_boundary: 'YES',
            target_kickoff_is_evaluation_boundary: 'NO',
            prematch_requires_t_lt_target_kickoff: 'YES',
            target_kickoff_relabeling_forbidden: 'YES',
            prefilter_only_proves_asof_compatibility: 'NO',
        },
        'contractBoundary.evaluation_boundary',
        'STANDINGS_ASOF_INPUT_CONTRACT_MISMATCH'
    );

    const fixtureUniverse = assertPlainObject(
        boundary.fixture_universe,
        'contractBoundary.fixture_universe',
        'STANDINGS_ASOF_INPUT_CONTRACT_MISMATCH'
    );
    assertExactKeys(
        fixtureUniverse,
        new Set([
            'required',
            'reference_match_required',
            'full_state_coverage',
            'target_exclusion',
            'authority_proven_by_core',
            'status_authority_proven_by_core',
        ]),
        'contractBoundary.fixture_universe',
        'STANDINGS_ASOF_INPUT_CONTRACT_MISMATCH'
    );
    assertExactValue(
        fixtureUniverse,
        {
            required: 'YES',
            reference_match_required: 'YES',
            full_state_coverage: 'EXACTLY_ONE_STATE_PER_FIXTURE',
            target_exclusion: 'EXACTLY_ONE_TARGET_FIXTURE_EXCLUDED',
            authority_proven_by_core: 'NO',
            status_authority_proven_by_core: 'NO',
        },
        'contractBoundary.fixture_universe',
        'STANDINGS_ASOF_INPUT_CONTRACT_MISMATCH'
    );
    const sourceStreamClosure = assertPlainObject(
        boundary.source_stream_closure,
        'contractBoundary.source_stream_closure',
        'STANDINGS_ASOF_INPUT_CONTRACT_MISMATCH'
    );
    assertExactKeys(
        sourceStreamClosure,
        new Set([
            'fixture_universe_reference_match',
            'fixture_universe_closure',
            'fixture_status_evidence_closure',
            'result_evidence_closure',
            'admin_adjustment_stream_closure',
        ]),
        'contractBoundary.source_stream_closure',
        'STANDINGS_ASOF_INPUT_CONTRACT_MISMATCH'
    );
    assertExactValue(
        sourceStreamClosure,
        {
            fixture_universe_reference_match: 'STRUCTURALLY_VALID',
            fixture_universe_closure: 'NOT_PROVEN',
            fixture_status_evidence_closure: 'NOT_PROVEN',
            result_evidence_closure: 'NOT_PROVEN',
            admin_adjustment_stream_closure: 'NOT_PROVEN',
        },
        'contractBoundary.source_stream_closure',
        'STANDINGS_ASOF_INPUT_CONTRACT_MISMATCH'
    );
    assertExactValue(boundary.fixture_state_taxonomy, FIXTURE_STATES, 'contractBoundary.fixture_state_taxonomy');
    assertExactValue(
        boundary.no_table_result_reason_codes,
        NO_TABLE_RESULT_REASONS,
        'contractBoundary.no_table_result_reason_codes'
    );
    assertExactValue(
        boundary.adjustment_state_taxonomy,
        ADJUSTMENT_STATES,
        'contractBoundary.adjustment_state_taxonomy'
    );

    const availabilityProof = assertPlainObject(
        boundary.availability_proof,
        'contractBoundary.availability_proof',
        'STANDINGS_ASOF_INPUT_CONTRACT_MISMATCH'
    );
    assertExactKeys(
        availabilityProof,
        new Set([
            'allowed_forms',
            'event_time_alone_proves_availability',
            'captured_at_alone_proves_availability',
            'post_t_evidence_allowed',
            'ambiguous_interval_fails_closed',
        ]),
        'contractBoundary.availability_proof',
        'STANDINGS_ASOF_INPUT_CONTRACT_MISMATCH'
    );
    assertExactValue(
        availabilityProof,
        {
            allowed_forms: AVAILABILITY_PROOF_KINDS,
            event_time_alone_proves_availability: 'NO',
            captured_at_alone_proves_availability: 'NO',
            post_t_evidence_allowed: 'NO',
            ambiguous_interval_fails_closed: 'YES',
        },
        'contractBoundary.availability_proof',
        'STANDINGS_ASOF_INPUT_CONTRACT_MISMATCH'
    );

    const trustBoundary = assertPlainObject(
        boundary.trust_boundary,
        'contractBoundary.trust_boundary',
        'STANDINGS_ASOF_INPUT_CONTRACT_MISMATCH'
    );
    assertExactKeys(
        trustBoundary,
        new Set([
            'core_establishes_runtime_source_authority',
            'fixture_universe_authority_proven_by_core',
            'fixture_status_stream_authority_proven_by_core',
            'result_stream_authority_proven_by_core',
            'admin_adjustment_stream_authority_proven_by_core',
            'runtime_capture_to_js_proven',
            'source_normalization_replay_proven',
            'caller_source_closure_flags_accepted',
            'caller_source_commit_proves_provenance',
        ]),
        'contractBoundary.trust_boundary',
        'STANDINGS_ASOF_INPUT_CONTRACT_MISMATCH'
    );
    assertExactValue(
        trustBoundary,
        {
            core_establishes_runtime_source_authority: 'NO',
            fixture_universe_authority_proven_by_core: 'NO',
            fixture_status_stream_authority_proven_by_core: 'NO',
            result_stream_authority_proven_by_core: 'NO',
            admin_adjustment_stream_authority_proven_by_core: 'NO',
            runtime_capture_to_js_proven: 'NO',
            source_normalization_replay_proven: 'NO',
            caller_source_closure_flags_accepted: 'NO',
            caller_source_commit_proves_provenance: 'NO',
        },
        'contractBoundary.trust_boundary',
        'STANDINGS_ASOF_INPUT_CONTRACT_MISMATCH'
    );

    const readiness = assertPlainObject(
        boundary.readiness,
        'contractBoundary.readiness',
        'STANDINGS_ASOF_INPUT_CONTRACT_MISMATCH'
    );
    assertExactKeys(
        readiness,
        new Set([
            'engine_consumer_implemented',
            'runtime_source_to_standings_normalization_proven',
            'standings_source_closure_proven',
            'historical_asof_numeric_parity_proven',
            'runtime_eligible',
            'training_eligible',
        ]),
        'contractBoundary.readiness',
        'STANDINGS_ASOF_INPUT_CONTRACT_MISMATCH'
    );
    assertExactValue(
        readiness,
        {
            engine_consumer_implemented: 'NO',
            runtime_source_to_standings_normalization_proven: 'NO',
            standings_source_closure_proven: 'NO',
            historical_asof_numeric_parity_proven: 'NO',
            runtime_eligible: 'NO',
            training_eligible: 'NO',
        },
        'contractBoundary.readiness',
        'STANDINGS_ASOF_INPUT_CONTRACT_MISMATCH'
    );
    assertExactValue(
        boundary.fail_closed_reason_codes,
        FAIL_CLOSED_REASON_CODES,
        'contractBoundary.fail_closed_reason_codes'
    );

    const digest = assertPlainObject(boundary.digest, 'contractBoundary.digest');
    assertExactKeys(
        digest,
        new Set(['algorithm', 'canonical_serialization', 'fixture_state_ordering', 'adjustment_state_ordering']),
        'contractBoundary.digest'
    );
    assertExactValue(
        digest,
        {
            algorithm: 'SHA-256',
            canonical_serialization: 'STABLE_VALUE_SORTED_KEYS_COMPACT_UTF8_JSON',
            fixture_state_ordering: 'canonicalMatchId_ASCENDING',
            adjustment_state_ordering: 'adjustmentId_ASCENDING',
        },
        'contractBoundary.digest'
    );

    return {
        contract_id: boundary.contract_id,
        version: boundary.version,
        status: boundary.status,
        standings_contract: standingsContract,
        model_as_of_contract: modelAsOfContract,
        runtime_capture_contract: runtimeCaptureContract,
        implementation_family: boundary.implementation_family,
        evaluation_boundary: { ...evaluationBoundary },
        fixture_universe: { ...fixtureUniverse },
        source_stream_closure: { ...sourceStreamClosure },
        fixture_state_taxonomy: [...boundary.fixture_state_taxonomy],
        no_table_result_reason_codes: [...boundary.no_table_result_reason_codes],
        adjustment_state_taxonomy: [...boundary.adjustment_state_taxonomy],
        availability_proof: { ...availabilityProof, allowed_forms: [...availabilityProof.allowed_forms] },
        trust_boundary: { ...trustBoundary },
        readiness: { ...readiness },
        fail_closed_reason_codes: [...boundary.fail_closed_reason_codes],
        digest: { ...digest },
    };
}

function validateDecisionTimes(input) {
    const modelDecisionMilliseconds = parseUtc(
        input.modelDecisionTimeUtc,
        'modelDecisionTimeUtc',
        'ASOF_DECISION_TIME_INVALID'
    );
    const featureAsOfMilliseconds = parseUtc(input.featureAsOfUtc, 'featureAsOfUtc', 'ASOF_DECISION_TIME_INVALID');
    if (featureAsOfMilliseconds !== modelDecisionMilliseconds) {
        fail('featureAsOfUtc must equal modelDecisionTimeUtc', 'MODEL_ASOF_BINDING_MISMATCH');
    }
    return { modelDecisionMilliseconds, featureAsOfMilliseconds };
}

function validateFixtureUniverse(value, target, competition, season) {
    const universe = assertPlainObject(value, 'fixtureUniverse', 'FIXTURE_UNIVERSE_INCOMPLETE');
    assertExactKeys(universe, new Set(['reference', 'fixtures']), 'fixtureUniverse', 'FIXTURE_UNIVERSE_INCOMPLETE');
    const reference = assertPlainObject(universe.reference, 'fixtureUniverse.reference', 'FIXTURE_UNIVERSE_INCOMPLETE');
    assertExactKeys(reference, REFERENCE_FIELDS, 'fixtureUniverse.reference', 'FIXTURE_UNIVERSE_INCOMPLETE');
    assertText(reference.referenceId, 'fixtureUniverse.reference.referenceId', 'FIXTURE_UNIVERSE_INCOMPLETE');
    assertText(reference.referenceVersion, 'fixtureUniverse.reference.referenceVersion', 'FIXTURE_UNIVERSE_INCOMPLETE');
    assertSha256(reference.referenceSha256, 'fixtureUniverse.reference.referenceSha256', 'FIXTURE_UNIVERSE_INCOMPLETE');
    const referenceIds = assertTextList(reference.fixtureIds, 'fixtureUniverse.reference.fixtureIds', {
        code: 'FIXTURE_UNIVERSE_INCOMPLETE',
    });
    const fixturesValue = universe.fixtures;
    if (!Array.isArray(fixturesValue) || fixturesValue.length === 0) {
        fail('fixtureUniverse.fixtures is required', 'FIXTURE_UNIVERSE_INCOMPLETE');
    }
    const fixtures = fixturesValue.map((row, index) => validateFixture(row, index, competition, season));
    const fixtureById = indexUnique(fixtures, 'canonicalMatchId', 'fixture universe', 'FIXTURE_UNIVERSE_INCOMPLETE');
    if (stableStringify(sortedTextList(referenceIds)) !== stableStringify([...fixtureById.keys()].sort())) {
        fail('fixture universe reference does not match supplied fixtures', 'FIXTURE_UNIVERSE_INCOMPLETE');
    }
    if (!fixtureById.has(target.canonicalMatchId)) {
        fail('target is outside the bound fixture universe', 'TARGET_KICKOFF_IDENTITY_CONFLICT');
    }
    return {
        reference: {
            referenceId: reference.referenceId,
            referenceVersion: reference.referenceVersion,
            referenceSha256: reference.referenceSha256,
            fixtureIds: sortedTextList(referenceIds),
        },
        fixtures: fixtures.sort(compareByCanonicalMatchId),
        fixtureById,
    };
}

function validateFixture(row, index, competition, season) {
    const fixture = assertPlainObject(row, `fixtureUniverse.fixtures[${index}]`, 'FIXTURE_UNIVERSE_INCOMPLETE');
    assertExactKeys(fixture, FIXTURE_FIELDS, `fixtureUniverse.fixtures[${index}]`, 'FIXTURE_UNIVERSE_INCOMPLETE');
    for (const field of ['canonicalMatchId', 'competition', 'season', 'homeTeamId', 'awayTeamId']) {
        assertText(fixture[field], `fixtureUniverse.fixtures[${index}].${field}`, 'FIXTURE_UNIVERSE_INCOMPLETE');
    }
    if (fixture.competition !== competition || fixture.season !== season || fixture.leagueId !== STANDINGS_LEAGUE_ID) {
        fail(
            `fixtureUniverse.fixtures[${index}] is outside the bound competition-season`,
            'FIXTURE_UNIVERSE_INCOMPLETE'
        );
    }
    if (fixture.homeTeamId === fixture.awayTeamId) {
        fail(`fixtureUniverse.fixtures[${index}] has identical teams`, 'FIXTURE_UNIVERSE_INCOMPLETE');
    }
    parseUtc(
        fixture.scheduledKickoffUtc,
        `fixtureUniverse.fixtures[${index}].scheduledKickoffUtc`,
        'FIXTURE_UNIVERSE_INCOMPLETE'
    );
    return {
        ...fixture,
        sourceLineage: assertLineage(fixture.sourceLineage, `fixtureUniverse.fixtures[${index}].sourceLineage`),
    };
}

function validateTarget(value, fixtureById, modelDecisionMilliseconds, competition, season) {
    const target = assertPlainObject(value, 'target', 'TARGET_KICKOFF_IDENTITY_CONFLICT');
    assertExactKeys(target, TARGET_FIELDS, 'target', 'TARGET_KICKOFF_IDENTITY_CONFLICT');
    for (const field of ['canonicalMatchId', 'competition', 'season', 'homeTeamId', 'awayTeamId']) {
        assertText(target[field], `target.${field}`, 'TARGET_KICKOFF_IDENTITY_CONFLICT');
    }
    if (target.competition !== competition || target.season !== season || target.leagueId !== STANDINGS_LEAGUE_ID) {
        fail('target competition-season binding is invalid', 'TARGET_KICKOFF_IDENTITY_CONFLICT');
    }
    const targetMilliseconds = parseUtc(
        target.targetKickoffUtc,
        'target.targetKickoffUtc',
        'TARGET_KICKOFF_IDENTITY_CONFLICT'
    );
    if (modelDecisionMilliseconds >= targetMilliseconds) {
        fail('model decision time must be strictly before target kickoff', 'ASOF_DECISION_TIME_INVALID');
    }
    const fixture = fixtureById.get(target.canonicalMatchId);
    if (!fixture) fail('target has no matching fixture', 'TARGET_KICKOFF_IDENTITY_CONFLICT');
    if (
        fixture.scheduledKickoffUtc !== target.targetKickoffUtc ||
        fixture.homeTeamId !== target.homeTeamId ||
        fixture.awayTeamId !== target.awayTeamId
    ) {
        fail('target kickoff or team identity conflicts with fixture universe', 'TARGET_KICKOFF_IDENTITY_CONFLICT');
    }
    return {
        ...target,
        sourceLineage: assertLineage(target.sourceLineage, 'target.sourceLineage'),
        targetMilliseconds,
    };
}

function validateAvailabilityProof(value, decisionMilliseconds, label) {
    const proof = assertPlainObject(value, `${label}.availabilityProof`, 'RESULT_AVAILABLE_AT_T_UNPROVEN');
    assertExactKeys(proof, AVAILABILITY_PROOF_FIELDS, `${label}.availabilityProof`, 'RESULT_AVAILABLE_AT_T_UNPROVEN');
    assertText(proof.kind, `${label}.availabilityProof.kind`, 'RESULT_AVAILABLE_AT_T_UNPROVEN');
    assertText(proof.proofRef, `${label}.availabilityProof.proofRef`, 'RESULT_AVAILABLE_AT_T_UNPROVEN');
    const fields = {
        observedAtUtc:
            proof.observedAtUtc === null
                ? null
                : parseUtc(proof.observedAtUtc, `${label}.observedAtUtc`, 'RESULT_AVAILABLE_AT_T_UNPROVEN'),
        effectiveAtUtc:
            proof.effectiveAtUtc === null
                ? null
                : parseUtc(proof.effectiveAtUtc, `${label}.effectiveAtUtc`, 'RESULT_AVAILABLE_AT_T_UNPROVEN'),
        intervalStartUtc:
            proof.intervalStartUtc === null
                ? null
                : parseUtc(proof.intervalStartUtc, `${label}.intervalStartUtc`, 'RESULT_AVAILABLE_AT_T_UNPROVEN'),
        intervalEndUtc:
            proof.intervalEndUtc === null
                ? null
                : parseUtc(proof.intervalEndUtc, `${label}.intervalEndUtc`, 'RESULT_AVAILABLE_AT_T_UNPROVEN'),
    };
    if (!AVAILABILITY_PROOF_KINDS.includes(proof.kind)) {
        fail(`${label}.availabilityProof.kind is unsupported`, 'RESULT_AVAILABLE_AT_T_UNPROVEN');
    }
    if (proof.kind === 'EXACT_OBSERVATION_TIMESTAMP') {
        if (
            fields.observedAtUtc === null ||
            fields.effectiveAtUtc !== null ||
            fields.intervalStartUtc !== null ||
            fields.intervalEndUtc !== null
        ) {
            fail(`${label} lacks exact observation availability proof`, 'RESULT_AVAILABLE_AT_T_UNPROVEN');
        }
        if (fields.observedAtUtc > decisionMilliseconds) {
            fail(`${label} was observed after T`, 'POST_DECISION_STANDINGS_EVIDENCE');
        }
    } else if (proof.kind === 'EXACT_EFFECTIVE_TIMESTAMP_WITH_SOURCE_OBSERVATION_PROOF') {
        if (
            fields.observedAtUtc === null ||
            fields.effectiveAtUtc === null ||
            fields.intervalStartUtc !== null ||
            fields.intervalEndUtc !== null
        ) {
            fail(`${label} lacks exact effective-time availability proof`, 'RESULT_AVAILABLE_AT_T_UNPROVEN');
        }
        if (fields.observedAtUtc > decisionMilliseconds || fields.effectiveAtUtc > decisionMilliseconds) {
            fail(`${label} contains post-T evidence`, 'POST_DECISION_STANDINGS_EVIDENCE');
        }
    } else {
        if (
            fields.intervalStartUtc === null ||
            fields.intervalEndUtc === null ||
            fields.observedAtUtc !== null ||
            fields.effectiveAtUtc !== null
        ) {
            fail(`${label} lacks bounded pre-T availability proof`, 'RESULT_AVAILABLE_AT_T_UNPROVEN');
        }
        if (fields.intervalStartUtc >= fields.intervalEndUtc) {
            fail(`${label} availability interval is inverted`, 'RESULT_AVAILABLE_AT_T_UNPROVEN');
        }
        if (fields.intervalEndUtc >= decisionMilliseconds) {
            fail(`${label} availability interval overlaps T`, 'ASOF_STATE_AMBIGUOUS');
        }
    }
    return {
        kind: proof.kind,
        observedAtUtc: proof.observedAtUtc,
        effectiveAtUtc: proof.effectiveAtUtc,
        intervalStartUtc: proof.intervalStartUtc,
        intervalEndUtc: proof.intervalEndUtc,
        proofRef: proof.proofRef,
    };
}

function validateResult(value, fixture, index, decisionMilliseconds) {
    const label = `fixtureStates[${index}].result`;
    const result = assertPlainObject(value, label, 'RESULT_AVAILABLE_AT_T_UNPROVEN');
    assertExactKeys(result, RESULT_FIELDS, label, 'RESULT_AVAILABLE_AT_T_UNPROVEN');
    for (const field of [
        'canonicalMatchId',
        'competition',
        'season',
        'homeTeamId',
        'awayTeamId',
        'disposition',
        'tableEligibility',
        'finalityStatus',
    ]) {
        assertText(result[field], `${label}.${field}`, 'RESULT_AVAILABLE_AT_T_UNPROVEN');
    }
    if (
        result.canonicalMatchId !== fixture.canonicalMatchId ||
        result.competition !== fixture.competition ||
        result.leagueId !== fixture.leagueId ||
        result.season !== fixture.season ||
        result.homeTeamId !== fixture.homeTeamId ||
        result.awayTeamId !== fixture.awayTeamId
    ) {
        fail(`${label} identity conflicts with fixture`, 'TARGET_KICKOFF_IDENTITY_CONFLICT');
    }
    if (!['COMPLETED', 'REPLAYED', 'AWARDED'].includes(result.disposition)) {
        fail(`${label}.disposition is not final`, 'RESULT_AVAILABLE_AT_T_UNPROVEN');
    }
    if (result.tableEligibility !== 'ELIGIBLE' || result.finalityStatus !== 'FINAL') {
        fail(`${label} is not a final table-eligible result`, 'RESULT_AVAILABLE_AT_T_UNPROVEN');
    }
    const eventMilliseconds = parseUtc(
        result.actualEligibleEventTimeUtc,
        `${label}.actualEligibleEventTimeUtc`,
        'RESULT_AVAILABLE_AT_T_UNPROVEN'
    );
    if (eventMilliseconds > decisionMilliseconds) {
        fail(`${label} event is after T`, 'RESULT_AVAILABLE_AT_T_UNPROVEN');
    }
    assertInteger(result.homeScore, `${label}.homeScore`, 'RESULT_AVAILABLE_AT_T_UNPROVEN');
    assertInteger(result.awayScore, `${label}.awayScore`, 'RESULT_AVAILABLE_AT_T_UNPROVEN');
    if (result.homeScore < 0 || result.awayScore < 0) {
        fail(`${label} score cannot be negative`, 'RESULT_AVAILABLE_AT_T_UNPROVEN');
    }
    if (result.replayOfMatchId !== null && result.replayOfMatchId !== undefined) {
        assertText(result.replayOfMatchId, `${label}.replayOfMatchId`, 'RESULT_AVAILABLE_AT_T_UNPROVEN');
    }
    return {
        ...result,
        sourceLineage: assertLineage(result.sourceLineage, `${label}.sourceLineage`),
        availabilityProof: validateAvailabilityProof(result.availabilityProof, decisionMilliseconds, label),
    };
}

function validateBasis(value, state, index) {
    const label = `fixtureStates[${index}].basis`;
    const basis = assertPlainObject(value, label, 'STANDINGS_ASOF_INPUT_CONTRACT_MISMATCH');
    assertExactKeys(basis, BASIS_FIELDS, label, 'STANDINGS_ASOF_INPUT_CONTRACT_MISMATCH');
    assertText(basis.reasonCode, `${label}.reasonCode`, 'STANDINGS_ASOF_INPUT_CONTRACT_MISMATCH');
    const evidenceRefs = assertTextList(basis.evidenceRefs, `${label}.evidenceRefs`, {
        code: 'STANDINGS_ASOF_INPUT_CONTRACT_MISMATCH',
    });
    if (basis.availabilityProofRef !== null) {
        assertText(
            basis.availabilityProofRef,
            `${label}.availabilityProofRef`,
            'STANDINGS_ASOF_INPUT_CONTRACT_MISMATCH'
        );
    }
    if (state === 'RESULT_AVAILABLE_AT_T' && basis.reasonCode !== 'RESULT_AVAILABLE_AT_T') {
        fail(`${label}.reasonCode does not explain the result state`, 'STANDINGS_ASOF_INPUT_CONTRACT_MISMATCH');
    }
    if (state === 'NO_TABLE_RESULT_AT_T' && !NO_TABLE_RESULT_REASONS.includes(basis.reasonCode)) {
        fail(`${label}.reasonCode is not a supported no-table reason`, 'FIXTURE_ASOF_STATE_UNKNOWN');
    }
    if (state === 'REQUIRED_EVIDENCE_MISSING_AT_T' && basis.reasonCode !== 'REQUIRED_EVIDENCE_MISSING_AT_T') {
        fail(`${label}.reasonCode does not explain missing evidence`, 'STANDINGS_ASOF_INPUT_CONTRACT_MISMATCH');
    }
    if (state === 'ASOF_STATE_AMBIGUOUS' && basis.reasonCode !== 'ASOF_STATE_AMBIGUOUS') {
        fail(`${label}.reasonCode does not explain ambiguity`, 'STANDINGS_ASOF_INPUT_CONTRACT_MISMATCH');
    }
    if (state === 'TARGET_FIXTURE_EXCLUDED' && basis.reasonCode !== 'TARGET_FIXTURE_EXCLUDED') {
        fail(`${label}.reasonCode does not explain target exclusion`, 'TARGET_FIXTURE_NOT_EXCLUDED');
    }
    return {
        reasonCode: basis.reasonCode,
        evidenceRefs: sortedTextList(evidenceRefs),
        availabilityProofRef: basis.availabilityProofRef,
    };
}

function validateFixtureState(value, index, fixtureById, target, decisionMilliseconds) {
    const label = `fixtureStates[${index}]`;
    const state = assertPlainObject(value, label, 'STANDINGS_ASOF_INPUT_CONTRACT_MISMATCH');
    assertKnownKeys(state, FIXTURE_STATE_FIELDS, label, 'STANDINGS_ASOF_INPUT_CONTRACT_MISMATCH');
    for (const field of ['canonicalMatchId', 'state', 'basis']) {
        if (state[field] === undefined) fail(`${label}.${field} is missing`, 'FIXTURE_ASOF_STATE_MISSING');
    }
    assertText(state.canonicalMatchId, `${label}.canonicalMatchId`, 'FIXTURE_ASOF_STATE_UNKNOWN');
    assertText(state.state, `${label}.state`, 'FIXTURE_ASOF_STATE_UNKNOWN');
    if (!FIXTURE_STATES.includes(state.state)) fail(`${label}.state is unknown`, 'FIXTURE_ASOF_STATE_UNKNOWN');
    const fixture = fixtureById.get(state.canonicalMatchId);
    if (!fixture) fail(`${label} references unknown fixture`, 'FIXTURE_ASOF_STATE_UNKNOWN');
    const basis = validateBasis(state.basis, state.state, index);
    const scheduledMilliseconds = parseUtc(
        fixture.scheduledKickoffUtc,
        `${label}.fixture kickoff`,
        'FIXTURE_ASOF_STATE_UNKNOWN'
    );
    if (state.state === 'TARGET_FIXTURE_EXCLUDED') {
        if (state.canonicalMatchId !== target.canonicalMatchId || state.result !== undefined) {
            fail('target fixture is not represented as exactly excluded', 'TARGET_FIXTURE_NOT_EXCLUDED');
        }
        return { canonicalMatchId: state.canonicalMatchId, state: state.state, basis };
    }
    if (state.canonicalMatchId === target.canonicalMatchId) {
        fail('target fixture must have TARGET_FIXTURE_EXCLUDED state', 'TARGET_FIXTURE_NOT_EXCLUDED');
    }
    if (state.state === 'RESULT_AVAILABLE_AT_T') {
        if (state.result === undefined) {
            fail(`${label} result is missing`, 'RESULT_AVAILABLE_AT_T_UNPROVEN');
        }
        const result = validateResult(state.result, fixture, index, decisionMilliseconds);
        if (basis.availabilityProofRef !== result.availabilityProof.proofRef) {
            fail(
                `${label} availability proof reference is not bound to result proof`,
                'RESULT_AVAILABLE_AT_T_UNPROVEN'
            );
        }
        return { canonicalMatchId: state.canonicalMatchId, state: state.state, basis, result };
    }
    if (state.result !== undefined) {
        fail(`${label} non-result state contains a result`, 'STANDINGS_ASOF_INPUT_CONTRACT_MISMATCH');
    }
    if (state.state === 'NO_TABLE_RESULT_AT_T') {
        if (basis.reasonCode === 'SCHEDULE_NOT_YET_REACHED_AT_T') {
            if (scheduledMilliseconds < decisionMilliseconds) {
                fail(`${label} schedule reason contradicts T`, 'STANDINGS_ASOF_INPUT_CONTRACT_MISMATCH');
            }
        } else if (scheduledMilliseconds >= decisionMilliseconds) {
            fail(`${label} no-table status hides a not-yet-reached schedule`, 'STANDINGS_ASOF_INPUT_CONTRACT_MISMATCH');
        }
        return { canonicalMatchId: state.canonicalMatchId, state: state.state, basis };
    }
    if (scheduledMilliseconds >= decisionMilliseconds) {
        fail(`${label} blocker is not a prior fixture obligation`, 'STANDINGS_ASOF_INPUT_CONTRACT_MISMATCH');
    }
    if (state.state === 'REQUIRED_EVIDENCE_MISSING_AT_T') {
        return { canonicalMatchId: state.canonicalMatchId, state: state.state, basis };
    }
    return { canonicalMatchId: state.canonicalMatchId, state: state.state, basis };
}

function validateEffectiveTime(value, label) {
    const effectiveTime = assertPlainObject(value, label, 'ADMIN_ADJUSTMENT_ASOF_AMBIGUOUS');
    assertExactKeys(effectiveTime, EFFECTIVE_TIME_FIELDS, label, 'ADMIN_ADJUSTMENT_ASOF_AMBIGUOUS');
    assertText(effectiveTime.kind, `${label}.kind`, 'ADMIN_ADJUSTMENT_ASOF_AMBIGUOUS');
    if (effectiveTime.kind === 'EXACT') {
        if (
            effectiveTime.atUtc === null ||
            effectiveTime.lowerBoundUtc !== null ||
            effectiveTime.upperBoundUtc !== null
        ) {
            fail(`${label} exact form is malformed`, 'ADMIN_ADJUSTMENT_ASOF_AMBIGUOUS');
        }
        return {
            kind: 'EXACT',
            atUtc: effectiveTime.atUtc,
            lowerBoundUtc: null,
            upperBoundUtc: null,
            atMilliseconds: parseUtc(effectiveTime.atUtc, `${label}.atUtc`, 'ADMIN_ADJUSTMENT_ASOF_AMBIGUOUS'),
        };
    }
    if (effectiveTime.kind === 'INTERVAL') {
        if (
            effectiveTime.atUtc !== null ||
            effectiveTime.lowerBoundUtc === null ||
            effectiveTime.upperBoundUtc === null
        ) {
            fail(`${label} interval form is malformed`, 'ADMIN_ADJUSTMENT_ASOF_AMBIGUOUS');
        }
        const lowerBoundMilliseconds = parseUtc(
            effectiveTime.lowerBoundUtc,
            `${label}.lowerBoundUtc`,
            'ADMIN_ADJUSTMENT_ASOF_AMBIGUOUS'
        );
        const upperBoundMilliseconds = parseUtc(
            effectiveTime.upperBoundUtc,
            `${label}.upperBoundUtc`,
            'ADMIN_ADJUSTMENT_ASOF_AMBIGUOUS'
        );
        if (lowerBoundMilliseconds >= upperBoundMilliseconds) {
            fail(`${label} interval is inverted`, 'ADMIN_ADJUSTMENT_ASOF_AMBIGUOUS');
        }
        return {
            kind: 'INTERVAL',
            atUtc: null,
            lowerBoundUtc: effectiveTime.lowerBoundUtc,
            upperBoundUtc: effectiveTime.upperBoundUtc,
            lowerBoundMilliseconds,
            upperBoundMilliseconds,
        };
    }
    fail(`${label}.kind is unknown`, 'ADMIN_ADJUSTMENT_ASOF_AMBIGUOUS');
}

function classifyAdjustmentState(adjustment, decisionMilliseconds, index) {
    const effectiveTime = adjustment.effectiveTime;
    if (effectiveTime.kind === 'EXACT') {
        const effective = effectiveTime.atMilliseconds <= decisionMilliseconds;
        if (adjustment.state === 'ASOF_ADJUSTMENT_AMBIGUOUS') {
            fail(
                `administrativeAdjustments[${index}] exact time cannot be ambiguous`,
                'ADMIN_ADJUSTMENT_ASOF_AMBIGUOUS'
            );
        }
        if (effective !== (adjustment.state === 'EFFECTIVE_AND_AVAILABLE_AT_T')) {
            fail(
                `administrativeAdjustments[${index}] state contradicts exact effective time`,
                'ADMIN_ADJUSTMENT_ASOF_AMBIGUOUS'
            );
        }
        return;
    }
    const overlaps =
        decisionMilliseconds >= effectiveTime.lowerBoundMilliseconds &&
        decisionMilliseconds < effectiveTime.upperBoundMilliseconds;
    if (adjustment.state === 'ASOF_ADJUSTMENT_AMBIGUOUS') {
        if (!overlaps) {
            fail(`administrativeAdjustments[${index}] is not ambiguous at T`, 'ADMIN_ADJUSTMENT_ASOF_AMBIGUOUS');
        }
        return;
    }
    if (overlaps) {
        fail(`administrativeAdjustments[${index}] interval overlaps T`, 'ADMIN_ADJUSTMENT_ASOF_AMBIGUOUS');
    }
    const effective = decisionMilliseconds >= effectiveTime.upperBoundMilliseconds;
    if (effective !== (adjustment.state === 'EFFECTIVE_AND_AVAILABLE_AT_T')) {
        fail(`administrativeAdjustments[${index}] state contradicts interval`, 'ADMIN_ADJUSTMENT_ASOF_AMBIGUOUS');
    }
}

function validateAdjustment(value, index, competition, season, teamIds, decisionMilliseconds) {
    const label = `administrativeAdjustments[${index}]`;
    const adjustment = assertPlainObject(value, label, 'ADMIN_ADJUSTMENT_ASOF_AMBIGUOUS');
    assertExactKeys(adjustment, ADJUSTMENT_FIELDS, label, 'ADMIN_ADJUSTMENT_ASOF_AMBIGUOUS');
    for (const field of ['adjustmentId', 'competition', 'season', 'teamId', 'state']) {
        assertText(adjustment[field], `${label}.${field}`, 'ADMIN_ADJUSTMENT_ASOF_AMBIGUOUS');
    }
    if (!ADJUSTMENT_STATES.includes(adjustment.state)) {
        fail(`${label}.state is unknown`, 'ADMIN_ADJUSTMENT_ASOF_AMBIGUOUS');
    }
    if (
        adjustment.competition !== competition ||
        adjustment.season !== season ||
        adjustment.leagueId !== STANDINGS_LEAGUE_ID
    ) {
        fail(`${label} is outside the bound competition-season`, 'ADMIN_ADJUSTMENT_ASOF_AMBIGUOUS');
    }
    if (!teamIds.has(adjustment.teamId)) {
        fail(`${label}.teamId is outside the fixture universe`, 'ADMIN_ADJUSTMENT_ASOF_AMBIGUOUS');
    }
    assertInteger(adjustment.delta, `${label}.delta`, 'ADMIN_ADJUSTMENT_ASOF_AMBIGUOUS');
    if (adjustment.delta === 0) fail(`${label}.delta cannot be zero`, 'ADMIN_ADJUSTMENT_ASOF_AMBIGUOUS');
    const effectiveTime = validateEffectiveTime(adjustment.effectiveTime, `${label}.effectiveTime`);
    const availabilityProof = validateAvailabilityProof(adjustment.availabilityProof, decisionMilliseconds, label);
    classifyAdjustmentState({ ...adjustment, effectiveTime }, decisionMilliseconds, index);
    return {
        adjustmentId: adjustment.adjustmentId,
        competition: adjustment.competition,
        leagueId: adjustment.leagueId,
        season: adjustment.season,
        teamId: adjustment.teamId,
        delta: adjustment.delta,
        state: adjustment.state,
        effectiveTime: {
            kind: effectiveTime.kind,
            atUtc: effectiveTime.atUtc,
            lowerBoundUtc: effectiveTime.lowerBoundUtc,
            upperBoundUtc: effectiveTime.upperBoundUtc,
        },
        sourceLineage: assertLineage(adjustment.sourceLineage, `${label}.sourceLineage`),
        availabilityProof,
    };
}

function indexUnique(rows, key, label, code) {
    const indexed = new Map();
    for (const row of rows) {
        if (indexed.has(row[key])) fail(`${label} ${row[key]} is duplicated`, code);
        indexed.set(row[key], row);
    }
    return indexed;
}

function compareByCanonicalMatchId(left, right) {
    return left.canonicalMatchId.localeCompare(right.canonicalMatchId);
}

function compareByAdjustmentId(left, right) {
    return left.adjustmentId.localeCompare(right.adjustmentId);
}

function canonicalizeInput({
    boundary,
    binding,
    modelDecisionTimeUtc,
    featureAsOfUtc,
    target,
    fixtureUniverse,
    fixtureStates,
    adjustments,
}) {
    const canonicalBinding = Object.fromEntries(
        Object.entries(binding)
            .filter(([key]) => key !== 'implementation_identity_digest')
            .map(([key, value]) => [key, Array.isArray(value) ? [...value] : value])
    );
    return {
        contract: {
            contract_id: boundary.contract_id,
            version: boundary.version,
            standings_contract_id: boundary.standings_contract.contract_id,
            standings_contract_version: boundary.standings_contract.version,
            model_as_of_contract_id: boundary.model_as_of_contract.contract_id,
            model_as_of_contract_version: boundary.model_as_of_contract.version,
            runtime_capture_contract_id: boundary.runtime_capture_contract.contract_id,
            runtime_capture_contract_version: boundary.runtime_capture_contract.version,
            implementation_family: boundary.implementation_family,
        },
        standings_contract_binding: canonicalBinding,
        model_decision_time_utc: modelDecisionTimeUtc,
        feature_as_of_utc: featureAsOfUtc,
        target: {
            ...target,
            targetMilliseconds: undefined,
        },
        fixture_universe: fixtureUniverse,
        fixture_states: fixtureStates.sort(compareByCanonicalMatchId),
        administrative_adjustments: adjustments.sort(compareByAdjustmentId),
    };
}

function removeUndefined(value) {
    if (Array.isArray(value)) return value.map(removeUndefined);
    if (isPlainObject(value)) {
        return Object.fromEntries(
            Object.entries(value)
                .filter(([, child]) => child !== undefined)
                .map(([key, child]) => [key, removeUndefined(child)])
        );
    }
    return value;
}

function validateStandingsAsOfEngineInput(input) {
    const value = assertPlainObject(input, 'standings as-of engine input');
    assertKnownKeys(value, INPUT_FIELDS, 'standings as-of engine input', 'STANDINGS_ASOF_INPUT_CONTRACT_MISMATCH');
    const boundary = validateContractBoundary(value.contractBoundary);
    let binding;
    try {
        binding = assertStandingsContractBinding(value.standingsContractBinding);
    } catch (error) {
        fail(`standings contract binding is invalid: ${error.message}`, 'MODEL_ASOF_BINDING_MISMATCH');
    }
    if (
        binding.contract_id !== boundary.standings_contract.contract_id ||
        binding.version !== boundary.standings_contract.version ||
        binding.competition !== STANDINGS_COMPETITION ||
        binding.league_id !== STANDINGS_LEAGUE_ID ||
        stableStringify(binding.frozen_seasons) !== stableStringify(STANDINGS_SEASONS)
    ) {
        fail('standings contract binding does not match input contract', 'MODEL_ASOF_BINDING_MISMATCH');
    }
    const { modelDecisionMilliseconds } = validateDecisionTimes(value);
    const competition = binding.competition;
    const season = assertText(value.target?.season, 'target.season', 'TARGET_KICKOFF_IDENTITY_CONFLICT');
    if (!binding.frozen_seasons.includes(season)) {
        fail('target season is outside frozen standings scope', 'MODEL_ASOF_BINDING_MISMATCH');
    }
    const targetSeed = assertPlainObject(value.target, 'target', 'TARGET_KICKOFF_IDENTITY_CONFLICT');
    const targetId = assertText(
        targetSeed.canonicalMatchId,
        'target.canonicalMatchId',
        'TARGET_KICKOFF_IDENTITY_CONFLICT'
    );
    const reference = value.fixtureUniverse?.reference;
    if (!reference) fail('fixture universe reference is required', 'FIXTURE_UNIVERSE_INCOMPLETE');
    const provisionalFixtureIds = reference.fixtureIds;
    if (!Array.isArray(provisionalFixtureIds) || provisionalFixtureIds.length === 0) {
        fail('fixture universe reference fixture IDs are required', 'FIXTURE_UNIVERSE_INCOMPLETE');
    }
    const fixtureUniverse = validateFixtureUniverse(
        value.fixtureUniverse,
        { canonicalMatchId: targetId },
        competition,
        season
    );
    const target = validateTarget(
        value.target,
        fixtureUniverse.fixtureById,
        modelDecisionMilliseconds,
        competition,
        season
    );
    const teamIds = new Set();
    for (const fixture of fixtureUniverse.fixtures) {
        teamIds.add(fixture.homeTeamId);
        teamIds.add(fixture.awayTeamId);
    }
    const fixtureStatesValue = value.fixtureStates;
    if (!Array.isArray(fixtureStatesValue)) fail('fixtureStates array is required', 'FIXTURE_ASOF_STATE_MISSING');
    const fixtureStates = fixtureStatesValue.map((state, index) =>
        validateFixtureState(state, index, fixtureUniverse.fixtureById, target, modelDecisionMilliseconds)
    );
    const fixtureStateById = indexUnique(
        fixtureStates,
        'canonicalMatchId',
        'fixture as-of state',
        'FIXTURE_ASOF_STATE_DUPLICATE'
    );
    const expectedFixtureIds = [...fixtureUniverse.fixtureById.keys()].sort();
    if (fixtureStates.length !== expectedFixtureIds.length) {
        fail('fixture as-of state coverage is incomplete', 'FIXTURE_ASOF_STATE_MISSING');
    }
    if (stableStringify([...fixtureStateById.keys()].sort()) !== stableStringify(expectedFixtureIds)) {
        fail('fixture as-of state coverage does not match fixture universe', 'FIXTURE_ASOF_STATE_MISSING');
    }
    const targetStates = fixtureStates.filter(state => state.state === 'TARGET_FIXTURE_EXCLUDED');
    if (targetStates.length !== 1 || targetStates[0].canonicalMatchId !== target.canonicalMatchId) {
        fail('exactly one target fixture exclusion is required', 'TARGET_FIXTURE_NOT_EXCLUDED');
    }
    const adjustmentsValue = value.administrativeAdjustments;
    if (!Array.isArray(adjustmentsValue)) {
        fail('administrativeAdjustments array is required', 'STANDINGS_ASOF_INPUT_CONTRACT_MISMATCH');
    }
    const adjustments = adjustmentsValue.map((adjustment, index) =>
        validateAdjustment(adjustment, index, competition, season, teamIds, modelDecisionMilliseconds)
    );
    indexUnique(adjustments, 'adjustmentId', 'administrative adjustment', 'ADMIN_ADJUSTMENT_ASOF_AMBIGUOUS');

    const blockingReasonCodes = new Set();
    for (const state of fixtureStates) {
        if (state.state === 'REQUIRED_EVIDENCE_MISSING_AT_T') blockingReasonCodes.add('REQUIRED_EVIDENCE_MISSING_AT_T');
        if (state.state === 'ASOF_STATE_AMBIGUOUS') blockingReasonCodes.add('ASOF_STATE_AMBIGUOUS');
    }
    for (const adjustment of adjustments) {
        if (adjustment.state === 'ASOF_ADJUSTMENT_AMBIGUOUS') {
            blockingReasonCodes.add('ADMIN_ADJUSTMENT_ASOF_AMBIGUOUS');
        }
    }
    const normalizedInput = removeUndefined(
        canonicalizeInput({
            boundary,
            binding,
            modelDecisionTimeUtc: value.modelDecisionTimeUtc,
            featureAsOfUtc: value.featureAsOfUtc,
            target,
            fixtureUniverse: {
                reference: fixtureUniverse.reference,
                fixtures: fixtureUniverse.fixtures,
            },
            fixtureStates,
            adjustments,
        })
    );
    const canonicalDigest = sha256Text(stableStringify(normalizedInput));
    const blocking = [...blockingReasonCodes].sort((left, right) => left.localeCompare(right));
    const availableCount = fixtureStates.filter(state => state.state === 'RESULT_AVAILABLE_AT_T').length;
    const notYetEligibleCount = fixtureStates.filter(
        state => state.state === 'NO_TABLE_RESULT_AT_T' && state.basis.reasonCode === 'SCHEDULE_NOT_YET_REACHED_AT_T'
    ).length;
    const requiredEvidenceMissingCount = fixtureStates.filter(
        state => state.state === 'REQUIRED_EVIDENCE_MISSING_AT_T'
    ).length;
    return {
        normalizedInput,
        canonicalDigest,
        semanticStatus: blocking.length === 0 ? 'STRUCTURALLY_VALID' : 'BLOCKED',
        blockingReasonCodes: blocking,
        stateCounts: {
            resultAvailableAtT: availableCount,
            noTableResultAtT: fixtureStates.filter(state => state.state === 'NO_TABLE_RESULT_AT_T').length,
            notYetEligibleAtT: notYetEligibleCount,
            requiredEvidenceMissingAtT: requiredEvidenceMissingCount,
            asOfStateAmbiguous: fixtureStates.filter(state => state.state === 'ASOF_STATE_AMBIGUOUS').length,
            targetFixtureExcluded: targetStates.length,
        },
        statuses: {
            ENGINE_INPUT_STRUCTURAL_VALIDITY: 'PROVEN',
            FIXTURE_STATE_COVERAGE_VALIDITY: 'PROVEN',
            FIXTURE_UNIVERSE_REFERENCE_MATCH: 'STRUCTURALLY_VALID',
            TEMPORAL_ELIGIBILITY_VALIDITY:
                blocking.includes('REQUIRED_EVIDENCE_MISSING_AT_T') ||
                blocking.includes('ASOF_STATE_AMBIGUOUS') ||
                blocking.includes('ADMIN_ADJUSTMENT_ASOF_AMBIGUOUS')
                    ? 'NOT_PROVEN'
                    : 'PROVEN',
            FIXTURE_UNIVERSE_CLOSURE: 'NOT_PROVEN',
            FIXTURE_STATUS_EVIDENCE_CLOSURE: 'NOT_PROVEN',
            RESULT_EVIDENCE_CLOSURE: 'NOT_PROVEN',
            ADMIN_ADJUSTMENT_STREAM_CLOSURE: 'NOT_PROVEN',
            SOURCE_AUTHORITY_VALIDITY: 'NOT_PROVEN',
            SOURCE_STREAM_COMPLETENESS: 'NOT_PROVEN',
            RUNTIME_NUMERIC_ELIGIBILITY: 'NO',
        },
        trustBoundary: {
            ENGINE_INPUT_CORE_ESTABLISHES_RUNTIME_SOURCE_AUTHORITY: 'NO',
            CANONICAL_FIXTURE_UNIVERSE_AUTHORITY_PROVEN: 'NOT_PROVEN',
            FIXTURE_STATUS_STREAM_AUTHORITY_PROVEN: 'NOT_PROVEN',
            RESULT_STREAM_AUTHORITY_PROVEN: 'NOT_PROVEN',
            ADMIN_ADJUSTMENT_STREAM_AUTHORITY: 'NOT_PROVEN',
            RUNTIME_CAPTURE_TO_JS_PROVEN: 'NOT_PROVEN',
            RUNTIME_SOURCE_TO_STANDINGS_NORMALIZATION_PROVEN: 'NO',
        },
        readiness: {
            STANDINGS_ENGINE_ASOF_COMPATIBILITY: 'VERSIONED_ASOF_ENGINE_INPUT_CONTRACT_FROZEN_CONSUMER_NOT_IMPLEMENTED',
            POINT_IN_TIME_STANDINGS_ENGINE_ASOF_CONSUMER_IMPLEMENTED: 'NO',
            STANDINGS_RUNTIME_ELIGIBLE: 'NO',
            STANDINGS_TRAINING_ELIGIBLE: 'NO',
        },
    };
}

const canonicalizeStandingsAsOfEngineInput = validateStandingsAsOfEngineInput;

module.exports = {
    ADJUSTMENT_STATES,
    AVAILABILITY_PROOF_KINDS,
    FAIL_CLOSED_REASON_CODES,
    FIXTURE_STATES,
    MODEL_ASOF_CONTRACT_ID,
    MODEL_ASOF_CONTRACT_VERSION,
    NO_TABLE_RESULT_REASONS,
    RUNTIME_CAPTURE_CONTRACT_ID,
    RUNTIME_CAPTURE_CONTRACT_VERSION,
    STANDINGS_ASOF_ENGINE_INPUT_CONTRACT_ID,
    STANDINGS_ASOF_ENGINE_INPUT_CONTRACT_STATUS,
    STANDINGS_ASOF_ENGINE_INPUT_CONTRACT_VERSION,
    STANDINGS_ENGINE_IMPLEMENTATION_FAMILY,
    StandingsAsOfEngineInputContractError,
    canonicalizeStandingsAsOfEngineInput,
    validateStandingsAsOfEngineInput,
};
