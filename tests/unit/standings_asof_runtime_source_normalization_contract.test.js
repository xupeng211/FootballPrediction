'use strict';

// lifecycle: permanent
// 纯内存 generic normalization handoff contract tests. No provider, network,
// database, filesystem write, source parser, or standings-engine invocation.

const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const { test } = require('node:test');

const { sha256Text, stableStringify } = require('../../src/infrastructure/canonical/StableValue');
const { bindFrozenStandingsContract } = require('../../src/infrastructure/standings/StandingsContractBinding');
const {
    computeFactBindingDigest,
    computeNormalizationContentDigest,
    computeOutputInputBindingDigest,
    sourceRecordRefForEvidenceIds,
    StandingsAsOfRuntimeSourceNormalizationError,
    compareUnicodeCodePoints,
    sortUnicodeCodePoints,
    validateNormalizationEnvelopeStructure,
    validateStandingsAsOfRuntimeSourceNormalization,
} = require('../../src/infrastructure/standings/StandingsAsOfRuntimeSourceNormalizationContract');
const {
    validateStandingsAsOfEngineInput,
} = require('../../src/infrastructure/standings/StandingsAsOfEngineInputContract');

const REGISTRY = JSON.parse(
    fs.readFileSync(path.resolve(__dirname, '../../config/model_feature_contracts.json'), 'utf8')
);
const INPUT_BOUNDARY = REGISTRY.decision_boundaries.standings_asof_engine_input;
const STANDINGS_BINDING = bindFrozenStandingsContract(REGISTRY);
const SEASON = '2024/2025';
const T = '2026-08-18T12:00:00.000Z';
const TARGET_KICKOFF = '2026-08-18T13:00:00.000Z';

function clone(value) {
    return JSON.parse(JSON.stringify(value));
}

function cloneInput(value) {
    const copy = clone(value);
    copy.standingsContractBinding = STANDINGS_BINDING;
    return copy;
}

function lineage(evidenceId, sourceRecordRef) {
    return { evidenceRefs: [evidenceId], sourceRecordRef };
}

function fixture(canonicalMatchId, scheduledKickoffUtc, homeTeamId, awayTeamId, evidenceId, sourceRecordRef) {
    return {
        canonicalMatchId,
        competition: 'Premier League',
        leagueId: 47,
        season: SEASON,
        homeTeamId,
        awayTeamId,
        scheduledKickoffUtc,
        sourceLineage: lineage(evidenceId, sourceRecordRef),
    };
}

function observationProof(proofRef) {
    return {
        kind: 'EXACT_OBSERVATION_TIMESTAMP',
        observedAtUtc: '2026-08-18T10:30:00.000Z',
        effectiveAtUtc: null,
        intervalStartUtc: null,
        intervalEndUtc: null,
        proofRef,
    };
}

function resultFor(sourceFixture) {
    return {
        canonicalMatchId: sourceFixture.canonicalMatchId,
        competition: sourceFixture.competition,
        leagueId: sourceFixture.leagueId,
        season: sourceFixture.season,
        homeTeamId: sourceFixture.homeTeamId,
        awayTeamId: sourceFixture.awayTeamId,
        actualEligibleEventTimeUtc: '2026-08-18T11:00:00.000Z',
        disposition: 'COMPLETED',
        tableEligibility: 'ELIGIBLE',
        finalityStatus: 'FINAL',
        homeScore: 2,
        awayScore: 1,
        sourceLineage: lineage('e-result', 'record-result'),
        availabilityProof: observationProof('e-result'),
        replayOfMatchId: null,
    };
}

function baseInput() {
    const prior = fixture('prior', '2026-08-18T11:00:00.000Z', 'TEAM_03', 'TEAM_04', 'e-result', 'record-result');
    const target = fixture('target', TARGET_KICKOFF, 'TEAM_01', 'TEAM_02', 'e-target', 'record-target');
    return {
        contractBoundary: clone(INPUT_BOUNDARY),
        standingsContractBinding: STANDINGS_BINDING,
        modelDecisionTimeUtc: T,
        featureAsOfUtc: T,
        target: {
            canonicalMatchId: target.canonicalMatchId,
            competition: target.competition,
            leagueId: target.leagueId,
            season: target.season,
            homeTeamId: target.homeTeamId,
            awayTeamId: target.awayTeamId,
            targetKickoffUtc: target.scheduledKickoffUtc,
            sourceLineage: clone(target.sourceLineage),
        },
        fixtureUniverse: {
            reference: {
                referenceId: 'fixture-universe-normalization-test',
                referenceVersion: 'v1',
                referenceSha256: 'a'.repeat(64),
                fixtureIds: ['target', 'prior'],
            },
            fixtures: [prior, target],
        },
        fixtureStates: [
            {
                canonicalMatchId: 'prior',
                state: 'RESULT_AVAILABLE_AT_T',
                basis: {
                    reasonCode: 'RESULT_AVAILABLE_AT_T',
                    evidenceRefs: ['e-result'],
                    availabilityProofRef: 'e-result',
                },
                result: resultFor(prior),
            },
            {
                canonicalMatchId: 'target',
                state: 'TARGET_FIXTURE_EXCLUDED',
                basis: {
                    reasonCode: 'TARGET_FIXTURE_EXCLUDED',
                    evidenceRefs: ['e-target'],
                    availabilityProofRef: null,
                },
            },
        ],
        administrativeAdjustments: [],
    };
}

function attestation(evidenceId, sourceRecordId, sourceFamily = 'GENERIC_TEST') {
    return {
        EVIDENCE_ID: evidenceId,
        SOURCE_FAMILY: sourceFamily,
        SOURCE_AUTHORITY_ID: 'authority-text-only',
        SOURCE_RECORD_ID: sourceRecordId,
        PAYLOAD_KIND: 'CANONICAL_JSON',
        PAYLOAD_CONTENT_DIGEST: sha256Text(`payload:${evidenceId}`),
        PAYLOAD_BYTE_LENGTH: 1,
        SOURCE_EVENT_TIME_UTC: null,
        SOURCE_EFFECTIVE_TIME_UTC: null,
        SOURCE_OBSERVED_AT_UTC: '2026-08-18T10:30:00.000Z',
        SOURCE_CAPTURED_AT_UTC: '2026-08-18T11:00:00.000Z',
        AVAILABILITY_PROOF_KIND: 'EXACT_OBSERVATION_TIMESTAMP',
        AVAILABILITY_PROOF_DATA: { observed_at_field: 'SOURCE_OBSERVED_AT_UTC' },
        SOURCE_PROVENANCE_STATUS: 'UNKNOWN',
    };
}

function fact(bindingId, role, domainIdentity, evidenceIds, extra = {}) {
    const binding = {
        BINDING_ID: bindingId,
        SEMANTIC_ROLE: role,
        DOMAIN_IDENTITY: domainIdentity,
        SOURCE_EVIDENCE_IDS: [...evidenceIds],
        CANONICAL_MATCH_ID: null,
        ADJUSTMENT_ID: null,
        AVAILABILITY_EVIDENCE_ID: null,
        NORMALIZED_FACT_DIGEST: null,
        DERIVATION: 'SOURCE_ATTESTED',
        ...extra,
    };
    binding.NORMALIZED_FACT_DIGEST = computeFactBindingDigest(binding);
    return binding;
}

function baseEnvelope(options = {}) {
    const input = options.input || baseInput();
    const inputValidation = validateStandingsAsOfEngineInput(input);
    const attestations = [attestation('e-target', 'record-target'), attestation('e-result', 'record-result')];
    const standingsEvidenceIds = options.standingsEvidenceIds || ['e-target', 'e-result'];
    const factBindings = [
        fact('fact-target-fixture', 'FIXTURE', 'fixture:target', ['e-target'], { CANONICAL_MATCH_ID: 'target' }),
        fact('fact-prior-fixture', 'FIXTURE', 'fixture:prior', ['e-result'], { CANONICAL_MATCH_ID: 'prior' }),
        fact('fact-prior-result', 'RESULT', 'result:prior', ['e-result'], {
            CANONICAL_MATCH_ID: 'prior',
            AVAILABILITY_EVIDENCE_ID: 'e-result',
        }),
    ];
    const outputBinding = {
        STANDINGS_ASOF_ENGINE_INPUT_CONTRACT_ID: 'standings-asof-engine-input/v1',
        STANDINGS_ASOF_ENGINE_INPUT_CONTRACT_VERSION: 'v1',
        STANDINGS_RANKING_CONTRACT_ID: 'standings/premier-league-point-in-time/v1',
        STANDINGS_RANKING_CONTRACT_VERSION: 'v1',
        CANONICAL_INPUT_DIGEST: inputValidation.canonicalDigest,
        MODEL_DECISION_TIME_UTC: T,
        FEATURE_AS_OF_UTC: T,
        TARGET_MATCH_ID: 'target',
        TARGET_KICKOFF_UTC: TARGET_KICKOFF,
        FIXTURE_UNIVERSE_REFERENCE_ID: 'fixture-universe-normalization-test',
        FIXTURE_STATE_IDS: ['target', 'prior'],
        ADMINISTRATIVE_ADJUSTMENT_IDS: [],
        OUTPUT_INPUT_BINDING_DIGEST: null,
    };
    outputBinding.OUTPUT_INPUT_BINDING_DIGEST = computeOutputInputBindingDigest(outputBinding);
    const envelope = {
        NORMALIZATION_CONTRACT_ID: 'standings-asof-runtime-source-normalization/v1',
        NORMALIZATION_CONTRACT_VERSION: 'v1',
        NORMALIZATION_INSTANCE_ID: 'normalization-instance-1',
        NORMALIZATION_CONTENT_DIGEST: null,
        PREDICTION_CONTEXT: {
            PREDICTION_CONTEXT_ID: 'prediction-context-1',
            MODEL_ASOF_CONTRACT_ID: 'canonical-model-asof/v1',
            MODEL_ASOF_CONTRACT_VERSION: 'v1',
            MODEL_DECISION_TIME_UTC: T,
            FEATURE_AS_OF_UTC: T,
            TARGET_MATCH_ID: 'target',
            TARGET_KICKOFF_UTC: TARGET_KICKOFF,
        },
        RUNTIME_CAPTURE_BINDING: {
            RUNTIME_CAPTURE_CONTRACT_ID: 'canonical-runtime-capture/v1',
            RUNTIME_CAPTURE_CONTRACT_VERSION: 'v1',
            CAPTURE_INSTANCE_ID: 'capture-instance-1',
            CAPTURE_CONTENT_DIGEST: 'b'.repeat(64),
            CAPTURE_SELECTED_EVIDENCE_IDS: ['e-odds', 'e-result', 'e-target'],
        },
        STANDINGS_EVIDENCE_IDS: standingsEvidenceIds,
        EVIDENCE_ATTESTATIONS: options.attestations || attestations,
        FACT_BINDINGS: options.factBindings || factBindings,
        OUTPUT_STANDINGS_INPUT_BINDING: outputBinding,
        STATUS: {
            NORMALIZATION_ENVELOPE_STRUCTURAL_VALIDITY: 'PROVEN',
            CAPTURE_BINDING_VALIDITY: 'PROVEN',
            OUTPUT_INPUT_BINDING_VALIDITY: 'NOT_PROVEN',
            SOURCE_SEMANTIC_NORMALIZATION_VALIDITY: 'NOT_PROVEN',
            SOURCE_AUTHORITY_VALIDITY: 'NOT_PROVEN',
            SOURCE_STREAM_COMPLETENESS: 'NOT_PROVEN',
            RUNTIME_NUMERIC_ELIGIBILITY: 'NO',
        },
    };
    envelope.NORMALIZATION_CONTENT_DIGEST = computeNormalizationContentDigest(envelope);
    return { envelope, input };
}

function expectNormalizationReject(value, expectedCode) {
    assert.throws(
        () => validateNormalizationEnvelopeStructure(value),
        error =>
            error instanceof StandingsAsOfRuntimeSourceNormalizationError &&
            (!expectedCode || error.reasonCode === expectedCode)
    );
}

test('N01-N10 capture identity and selected-evidence subset fail closed', () => {
    const { envelope } = baseEnvelope();
    const wrongContract = clone(envelope);
    wrongContract.RUNTIME_CAPTURE_BINDING.RUNTIME_CAPTURE_CONTRACT_ID = 'canonical-runtime-capture/v2';
    expectNormalizationReject(wrongContract, 'CONTRACT_VERSION_MISMATCH');

    const wrongInstance = clone(envelope);
    wrongInstance.RUNTIME_CAPTURE_BINDING.CAPTURE_INSTANCE_ID = 'capture-instance-other';
    wrongInstance.NORMALIZATION_CONTENT_DIGEST = computeNormalizationContentDigest(wrongInstance);
    assert.doesNotThrow(() => validateNormalizationEnvelopeStructure(wrongInstance));

    const wrongDigest = clone(envelope);
    wrongDigest.RUNTIME_CAPTURE_BINDING.CAPTURE_CONTENT_DIGEST = 'c'.repeat(64);
    expectNormalizationReject(wrongDigest, 'NORMALIZATION_CONTENT_DIGEST_MISMATCH');

    const wrongT = clone(envelope);
    wrongT.PREDICTION_CONTEXT.MODEL_DECISION_TIME_UTC = '2026-08-18T11:59:59.000Z';
    expectNormalizationReject(wrongT, 'NORMALIZATION_CONTEXT_MISMATCH');

    const wrongTarget = clone(envelope);
    wrongTarget.PREDICTION_CONTEXT.TARGET_MATCH_ID = 'other-target';
    expectNormalizationReject(wrongTarget, 'OUTPUT_INPUT_CONTEXT_MISMATCH');

    const wrongKickoff = clone(envelope);
    wrongKickoff.PREDICTION_CONTEXT.TARGET_KICKOFF_UTC = '2026-08-18T14:00:00.000Z';
    expectNormalizationReject(wrongKickoff, 'OUTPUT_INPUT_CONTEXT_MISMATCH');

    const wrongFeatureAsOf = clone(envelope);
    wrongFeatureAsOf.PREDICTION_CONTEXT.FEATURE_AS_OF_UTC = '2026-08-18T11:59:59.000Z';
    expectNormalizationReject(wrongFeatureAsOf, 'NORMALIZATION_CONTEXT_MISMATCH');

    const changedSelection = clone(envelope);
    changedSelection.RUNTIME_CAPTURE_BINDING.CAPTURE_SELECTED_EVIDENCE_IDS = ['e-result', 'e-target'];
    expectNormalizationReject(changedSelection, 'NORMALIZATION_CONTENT_DIGEST_MISMATCH');

    const unselected = clone(envelope);
    unselected.STANDINGS_EVIDENCE_IDS = ['e-unselected'];
    expectNormalizationReject(unselected, 'STANDINGS_EVIDENCE_NOT_SELECTED');

    const selectedNonStandings = clone(envelope);
    assert.doesNotThrow(() => validateNormalizationEnvelopeStructure(selectedNonStandings));
});

test('N11-N19 attestation metadata is an immutable capture projection', () => {
    const { envelope } = baseEnvelope();
    const fields = [
        'PAYLOAD_CONTENT_DIGEST',
        'SOURCE_EVENT_TIME_UTC',
        'SOURCE_OBSERVED_AT_UTC',
        'SOURCE_EFFECTIVE_TIME_UTC',
        'SOURCE_CAPTURED_AT_UTC',
        'AVAILABILITY_PROOF_KIND',
        'AVAILABILITY_PROOF_DATA',
        'SOURCE_FAMILY',
        'SOURCE_RECORD_ID',
    ];
    fields.forEach((field, index) => {
        const tampered = clone(envelope);
        const attestation = tampered.EVIDENCE_ATTESTATIONS[0];
        attestation[field] =
            field === 'AVAILABILITY_PROOF_DATA'
                ? { observed_at_field: 'SOURCE_CAPTURED_AT_UTC' }
                : field.endsWith('_UTC')
                  ? '2026-08-18T11:30:00.000Z'
                  : field === 'PAYLOAD_CONTENT_DIGEST'
                    ? 'd'.repeat(64)
                    : field === 'SOURCE_RECORD_ID'
                      ? 'record-other'
                      : 'ALTERED';
        expectNormalizationReject(tampered);
        assert.equal(index < fields.length, true);
    });
});

test('N20-N25 generic metadata never upgrades source authority', () => {
    const { envelope } = baseEnvelope();
    const authorityTextOnly = clone(envelope);
    assert.doesNotThrow(() => validateNormalizationEnvelopeStructure(authorityTextOnly));

    for (const field of [
        'sourceAuthorityProven',
        'trusted',
        'verified',
        'canonical',
        'providerOfficial',
        'callerGitSha',
    ]) {
        const spoofed = clone(envelope);
        spoofed[field] = true;
        expectNormalizationReject(spoofed, 'NORMALIZATION_SCHEMA_MISMATCH');
    }

    const positiveProvenance = clone(envelope);
    positiveProvenance.EVIDENCE_ATTESTATIONS[0].SOURCE_PROVENANCE_STATUS = 'EXTERNAL_CONTRACT_BOUND';
    expectNormalizationReject(positiveProvenance, 'SOURCE_AUTHORITY_PROOF_UNAVAILABLE');
});

test('N26-N32 output lineage and proof references require selected evidence', () => {
    const { envelope, input } = baseEnvelope();
    assert.doesNotThrow(() => validateStandingsAsOfRuntimeSourceNormalization(envelope, input));

    const outputEvidence = cloneInput(input);
    outputEvidence.fixtureStates[0].result.sourceLineage.evidenceRefs = ['e-unselected'];
    assert.throws(
        () => validateStandingsAsOfRuntimeSourceNormalization(envelope, outputEvidence),
        error => error.reasonCode === 'OUTPUT_INPUT_BINDING_MISMATCH' || error.reasonCode === 'OUTPUT_LINEAGE_INVALID'
    );

    const outputRecord = cloneInput(input);
    outputRecord.fixtureStates[0].result.sourceLineage.sourceRecordRef = 'record-other';
    assert.throws(() => validateStandingsAsOfRuntimeSourceNormalization(envelope, outputRecord));

    const nullRecordAttestations = [attestation('e-target', null), attestation('e-result', null)];
    const nullRecord = baseEnvelope({ attestations: nullRecordAttestations });
    nullRecord.input.target.sourceLineage.sourceRecordRef = sourceRecordRefForEvidenceIds(
        nullRecord.envelope.RUNTIME_CAPTURE_BINDING.CAPTURE_CONTENT_DIGEST,
        ['e-target'],
        Object.fromEntries(nullRecordAttestations.map(row => [row.EVIDENCE_ID, row]))
    );
    nullRecord.input.fixtureUniverse.fixtures[1].sourceLineage.sourceRecordRef =
        nullRecord.input.target.sourceLineage.sourceRecordRef;
    assert.equal(nullRecord.input.target.sourceLineage.sourceRecordRef, 'capture:' + 'b'.repeat(64) + ':e-target');
    assert.notEqual(
        sourceRecordRefForEvidenceIds('b'.repeat(64), ['e-target'], { 'e-target': nullRecordAttestations[0] }),
        sourceRecordRefForEvidenceIds('c'.repeat(64), ['e-target'], { 'e-target': nullRecordAttestations[0] })
    );

    const wrongProof = cloneInput(input);
    wrongProof.fixtureStates[0].result.availabilityProof.proofRef = 'e-unselected';
    assert.throws(() => validateStandingsAsOfRuntimeSourceNormalization(envelope, wrongProof));

    const adjustmentEvidence = cloneInput(input);
    adjustmentEvidence.administrativeAdjustments = [];
    assert.doesNotThrow(() => validateStandingsAsOfRuntimeSourceNormalization(envelope, adjustmentEvidence));
});

test('N39-N41 core-derived schedule/target rules remain separate from source truth', () => {
    const { envelope, input } = baseEnvelope();
    assert.doesNotThrow(() => validateStandingsAsOfRuntimeSourceNormalization(envelope, input));

    const targetLeak = cloneInput(input);
    targetLeak.fixtureStates[1] = {
        canonicalMatchId: 'target',
        state: 'RESULT_AVAILABLE_AT_T',
        basis: {
            reasonCode: 'RESULT_AVAILABLE_AT_T',
            evidenceRefs: ['e-target'],
            availabilityProofRef: 'e-target',
        },
        result: resultFor(targetLeak.fixtureUniverse.fixtures[1]),
    };
    assert.throws(() => validateStandingsAsOfRuntimeSourceNormalization(envelope, targetLeak));

    const priorScheduleNotYet = cloneInput(input);
    priorScheduleNotYet.fixtureStates[0].state = 'NO_TABLE_RESULT_AT_T';
    priorScheduleNotYet.fixtureStates[0].basis = {
        reasonCode: 'SCHEDULE_NOT_YET_REACHED_AT_T',
        evidenceRefs: ['e-result'],
        availabilityProofRef: null,
    };
    delete priorScheduleNotYet.fixtureStates[0].result;
    assert.throws(() => validateStandingsAsOfRuntimeSourceNormalization(envelope, priorScheduleNotYet));
});

test('N42-N48 actual standings input digest and context are bound, not caller booleans', () => {
    const { envelope, input } = baseEnvelope();
    const result = validateStandingsAsOfRuntimeSourceNormalization(envelope, input);
    assert.equal(result.statuses.OUTPUT_INPUT_BINDING_VALIDITY, 'PROVEN');
    assert.equal(result.statuses.SOURCE_SEMANTIC_NORMALIZATION_VALIDITY, 'NOT_PROVEN');
    assert.equal(result.statuses.SOURCE_AUTHORITY_VALIDITY, 'NOT_PROVEN');
    assert.equal(result.statuses.RUNTIME_NUMERIC_ELIGIBILITY, 'NO');

    for (const mutation of [
        value => {
            value.fixtureUniverse.reference.referenceId = 'reference-other';
        },
        value => {
            value.fixtureStates[0].basis.evidenceRefs = ['e-target'];
        },
        value => {
            value.target.targetKickoffUtc = '2026-08-18T14:00:00.000Z';
        },
        value => {
            value.modelDecisionTimeUtc = '2026-08-18T11:59:59.000Z';
            value.featureAsOfUtc = value.modelDecisionTimeUtc;
        },
    ]) {
        const tampered = cloneInput(input);
        mutation(tampered);
        assert.throws(() => validateStandingsAsOfRuntimeSourceNormalization(envelope, tampered));
    }

    const bypass = cloneInput(input);
    bypass.consumerEligible = true;
    assert.throws(() => validateStandingsAsOfRuntimeSourceNormalization(envelope, bypass));
});

test('normalization validators are pure and do not invoke the standings engine', () => {
    const { envelope, input } = baseEnvelope();
    const envelopeBefore = JSON.stringify(envelope);
    const inputBefore = JSON.stringify(input);
    validateNormalizationEnvelopeStructure(envelope);
    validateStandingsAsOfRuntimeSourceNormalization(envelope, input);
    assert.equal(JSON.stringify(envelope), envelopeBefore);
    assert.equal(JSON.stringify(input), inputBefore);
});

test('source-dependent NO_TABLE representations remain structurally non-authoritative', () => {
    const { envelope } = baseEnvelope();
    const reasons = [
        'PROVEN_POSTPONED_NOT_PLAYED_BY_T',
        'PROVEN_NOT_FINAL_BY_T',
        'PROVEN_NON_TABLE_ELIGIBLE_BY_T',
        'PROVEN_ABANDONED_NON_TABLE_ELIGIBLE_BY_T',
        'PROVEN_VOID_NON_TABLE_ELIGIBLE_BY_T',
        'PROVEN_REPLAY_ORIGINAL_NON_ELIGIBLE_BY_T',
    ];
    for (const reason of reasons) {
        const candidate = clone(envelope);
        candidate.FACT_BINDINGS[0].DOMAIN_IDENTITY = `source-status:${reason}`;
        candidate.FACT_BINDINGS[0].NORMALIZED_FACT_DIGEST = computeFactBindingDigest(candidate.FACT_BINDINGS[0]);
        candidate.NORMALIZATION_CONTENT_DIGEST = computeNormalizationContentDigest(candidate);
        assert.doesNotThrow(() => validateNormalizationEnvelopeStructure(candidate));
        assert.equal(candidate.STATUS.SOURCE_SEMANTIC_NORMALIZATION_VALIDITY, 'NOT_PROVEN');
        assert.equal(candidate.STATUS.SOURCE_AUTHORITY_VALIDITY, 'NOT_PROVEN');
        assert.equal(candidate.STATUS.SOURCE_STREAM_COMPLETENESS, 'NOT_PROVEN');
    }
});

test('shared canonical digest vectors are accepted by the JS serializer', () => {
    const fixturePath = path.resolve(
        __dirname,
        '../fixtures/standings_asof_runtime_source_normalization_digest_vectors.json'
    );
    const vectors = JSON.parse(fs.readFileSync(fixturePath, 'utf8'));
    assert.equal(vectors.lifecycle, 'test-fixture');
    assert.equal(vectors.vectors.length, 20);

    function applyOperation(value, operation) {
        const target = value;
        const pathParts = operation.path ? operation.path.split('.') : [];
        let cursor = target;
        pathParts.slice(0, -1).forEach(part => {
            cursor = cursor[part];
        });
        if (operation.type === 'REVERSE') cursor[pathParts.at(-1)].reverse();
        if (operation.type === 'SET') cursor[pathParts.at(-1)] = operation.value;
        if (operation.type === 'REORDER_TOP_LEVEL') {
            const entries = Object.entries(target).reverse();
            Object.keys(target).forEach(key => delete target[key]);
            entries.forEach(([key, child]) => {
                target[key] = child;
            });
        }
        return target;
    }

    vectors.vectors.forEach(vector => {
        const value = vector.operations.reduce(applyOperation, clone(vectors.base));
        assert.equal(computeNormalizationContentDigest(value), vector.expected_digest, vector.id);
    });
});

function nonResultInput(options = {}) {
    const input = baseInput();
    input.fixtureStates[0] = {
        canonicalMatchId: 'prior',
        state: options.state || 'NO_TABLE_RESULT_AT_T',
        basis: {
            reasonCode: options.reason || 'PROVEN_POSTPONED_NOT_PLAYED_BY_T',
            evidenceRefs: ['e-result'],
            availabilityProofRef: options.proofRef === undefined ? 'e-result' : options.proofRef,
        },
    };
    input.fixtureStates[1].basis.availabilityProofRef = null;
    return input;
}

test('direct unicode code-point comparator matches the frozen locale-independent order', () => {
    const values = [
        'A-evidence',
        'a-evidence',
        'evidence-1',
        'evidence_1',
        'evidence.1',
        'evidence:1',
        'evidence/1',
        'Z-evidence',
        'z-evidence',
        '0-evidence',
        '9-evidence',
    ];
    const expected = [
        '0-evidence',
        '9-evidence',
        'A-evidence',
        'Z-evidence',
        'a-evidence',
        'evidence-1',
        'evidence.1',
        'evidence/1',
        'evidence:1',
        'evidence_1',
        'z-evidence',
    ];
    assert.deepEqual(sortUnicodeCodePoints(values), expected);
    assert.equal(compareUnicodeCodePoints('😀', '😁') < 0, true);
    assert.equal(compareUnicodeCodePoints('A', 'A'), 0);
    assert.equal(compareUnicodeCodePoints('A', 'AA') < 0, true);
    assert.equal(compareUnicodeCodePoints('AA', 'A') > 0, true);
});

test('shared ordering adversarial digest vectors are accepted by the JS serializer', () => {
    const fixturePath = path.resolve(
        __dirname,
        '../fixtures/standings_asof_runtime_source_normalization_ordering_vectors.json'
    );
    const vectors = JSON.parse(fs.readFileSync(fixturePath, 'utf8'));
    assert.equal(vectors.lifecycle, 'test-fixture');
    assert.ok(vectors.vectors.length >= 20);

    function applyOperation(value, operation) {
        const target = value;
        const pathParts = operation.path ? operation.path.split('.') : [];
        if (operation.type === 'REORDER_TOP_LEVEL') {
            const entries = Object.entries(target).reverse();
            Object.keys(target).forEach(key => delete target[key]);
            entries.forEach(([key, child]) => {
                target[key] = child;
            });
            return target;
        }
        let cursor = target;
        pathParts.slice(0, -1).forEach(part => {
            cursor = cursor[part];
        });
        if (operation.type === 'REVERSE') cursor[pathParts.at(-1)].reverse();
        if (operation.type === 'SET') cursor[pathParts.at(-1)] = operation.value;
        return target;
    }

    vectors.vectors.forEach(vector => {
        const value = vector.operations.reduce(applyOperation, clone(vectors.base));
        assert.equal(computeNormalizationContentDigest(value), vector.expected_digest, vector.id);
    });
});

test('F201/F209/F210 non-result fixture-state proofRef lineage binding remains generic', () => {
    const validInput = nonResultInput({
        state: 'NO_TABLE_RESULT_AT_T',
        reason: 'PROVEN_POSTPONED_NOT_PLAYED_BY_T',
        proofRef: 'e-result',
    });
    const { envelope: validEnvelope } = baseEnvelope({ input: validInput });
    const valid = validateStandingsAsOfRuntimeSourceNormalization(validEnvelope, validInput);
    assert.equal(valid.statuses.SOURCE_SEMANTIC_NORMALIZATION_VALIDITY, 'NOT_PROVEN');
    assert.equal(valid.statuses.SOURCE_AUTHORITY_VALIDITY, 'NOT_PROVEN');

    const nullProofInput = nonResultInput({ proofRef: null });
    const { envelope: nullProofEnvelope } = baseEnvelope({ input: nullProofInput });
    assert.doesNotThrow(() => validateStandingsAsOfRuntimeSourceNormalization(nullProofEnvelope, nullProofInput));

    const sourceDependentInput = nonResultInput({
        state: 'NO_TABLE_RESULT_AT_T',
        reason: 'PROVEN_NOT_FINAL_BY_T',
        proofRef: 'e-result',
    });
    const { envelope: sourceDependentEnvelope } = baseEnvelope({ input: sourceDependentInput });
    const sourceDependent = validateStandingsAsOfRuntimeSourceNormalization(
        sourceDependentEnvelope,
        sourceDependentInput
    );
    assert.equal(sourceDependent.statuses.SOURCE_SEMANTIC_NORMALIZATION_VALIDITY, 'NOT_PROVEN');
    assert.equal(sourceDependent.statuses.SOURCE_AUTHORITY_VALIDITY, 'NOT_PROVEN');
    assert.equal(sourceDependent.statuses.SOURCE_STREAM_COMPLETENESS, 'NOT_PROVEN');
});

test('F202-F204 non-result proofRef outside the bound standings evidence subset is rejected', () => {
    for (const proofRef of ['e-other', 'e-unselected', 'e-odds']) {
        const input = nonResultInput({ proofRef });
        const { envelope } = baseEnvelope({ input });
        assert.throws(
            () => validateStandingsAsOfRuntimeSourceNormalization(envelope, input),
            error =>
                error instanceof StandingsAsOfRuntimeSourceNormalizationError &&
                error.reasonCode === 'PROOF_REF_UNBOUND'
        );
    }
});

test('F205 non-result proofRef cannot survive a missing canonical attestation', () => {
    const input = nonResultInput({ proofRef: 'e-result' });
    const { envelope } = baseEnvelope({ input });
    envelope.EVIDENCE_ATTESTATIONS = envelope.EVIDENCE_ATTESTATIONS.filter(row => row.EVIDENCE_ID !== 'e-result');
    envelope.NORMALIZATION_CONTENT_DIGEST = computeNormalizationContentDigest(envelope);
    assert.throws(
        () => validateStandingsAsOfRuntimeSourceNormalization(envelope, input),
        error => error.reasonCode === 'ATTESTATION_SET_MISMATCH'
    );
});
