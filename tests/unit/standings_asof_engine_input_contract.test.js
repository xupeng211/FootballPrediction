'use strict';

// lifecycle: test-fixture
// 纯内存 standings as-of input contract 的行为、边界、信任隔离与篡改测试。

const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const { test } = require('node:test');

const { bindFrozenStandingsContract } = require('../../src/infrastructure/standings/StandingsContractBinding');
const {
    ADJUSTMENT_STATES,
    AVAILABILITY_PROOF_KINDS,
    FIXTURE_STATES,
    STANDINGS_ASOF_ENGINE_INPUT_CONTRACT_ID,
    STANDINGS_ASOF_ENGINE_INPUT_CONTRACT_VERSION,
    StandingsAsOfEngineInputContractError,
    validateStandingsAsOfEngineInput,
} = require('../../src/infrastructure/standings/StandingsAsOfEngineInputContract');

const REGISTRY = JSON.parse(
    fs.readFileSync(path.resolve(__dirname, '../../config/model_feature_contracts.json'), 'utf8')
);
const CONTRACT_BOUNDARY = REGISTRY.decision_boundaries.standings_asof_engine_input;
const STANDINGS_BINDING = bindFrozenStandingsContract(REGISTRY);
const SEASON = '2022/2023';
const T = '2022-08-19T12:00:00.000Z';
const TARGET_KICKOFF = '2022-08-20T12:00:00.000Z';
const TEAMS = ['TEAM_01', 'TEAM_02', 'TEAM_03', 'TEAM_04'];

function lineage(id) {
    return {
        evidenceRefs: [`evidence:${id}`, `lineage:${id}`],
        sourceRecordRef: `record:${id}`,
    };
}

function fixture(canonicalMatchId, scheduledKickoffUtc, homeTeamId, awayTeamId) {
    return {
        canonicalMatchId,
        competition: 'Premier League',
        leagueId: 47,
        season: SEASON,
        homeTeamId,
        awayTeamId,
        scheduledKickoffUtc,
        sourceLineage: lineage(`fixture:${canonicalMatchId}`),
    };
}

function observationProof(proofRef, observedAtUtc = '2022-08-18T18:00:00.000Z') {
    return {
        kind: 'EXACT_OBSERVATION_TIMESTAMP',
        observedAtUtc,
        effectiveAtUtc: null,
        intervalStartUtc: null,
        intervalEndUtc: null,
        proofRef,
    };
}

function resultFor(sourceFixture, proofRef = `proof:${sourceFixture.canonicalMatchId}`) {
    return {
        canonicalMatchId: sourceFixture.canonicalMatchId,
        competition: sourceFixture.competition,
        leagueId: sourceFixture.leagueId,
        season: sourceFixture.season,
        homeTeamId: sourceFixture.homeTeamId,
        awayTeamId: sourceFixture.awayTeamId,
        actualEligibleEventTimeUtc: sourceFixture.scheduledKickoffUtc,
        disposition: 'COMPLETED',
        tableEligibility: 'ELIGIBLE',
        finalityStatus: 'FINAL',
        homeScore: 2,
        awayScore: 1,
        sourceLineage: lineage(`result:${sourceFixture.canonicalMatchId}`),
        availabilityProof: observationProof(proofRef),
        replayOfMatchId: null,
    };
}

function basis(reasonCode, evidenceRefs, availabilityProofRef = null) {
    return { reasonCode, evidenceRefs, availabilityProofRef };
}

function availableState(sourceFixture) {
    const proofRef = `proof:${sourceFixture.canonicalMatchId}`;
    return {
        canonicalMatchId: sourceFixture.canonicalMatchId,
        state: 'RESULT_AVAILABLE_AT_T',
        basis: basis('RESULT_AVAILABLE_AT_T', [`result:${sourceFixture.canonicalMatchId}`], proofRef),
        result: resultFor(sourceFixture, proofRef),
    };
}

function noTableState(sourceFixture, reasonCode = 'SCHEDULE_NOT_YET_REACHED_AT_T') {
    return {
        canonicalMatchId: sourceFixture.canonicalMatchId,
        state: 'NO_TABLE_RESULT_AT_T',
        basis: basis(reasonCode, [`status:${sourceFixture.canonicalMatchId}`]),
    };
}

function targetExcludedState(sourceFixture) {
    return {
        canonicalMatchId: sourceFixture.canonicalMatchId,
        state: 'TARGET_FIXTURE_EXCLUDED',
        basis: basis('TARGET_FIXTURE_EXCLUDED', [`target:${sourceFixture.canonicalMatchId}`]),
    };
}

function missingState(sourceFixture) {
    return {
        canonicalMatchId: sourceFixture.canonicalMatchId,
        state: 'REQUIRED_EVIDENCE_MISSING_AT_T',
        basis: basis('REQUIRED_EVIDENCE_MISSING_AT_T', [`obligation:${sourceFixture.canonicalMatchId}`]),
    };
}

function ambiguousState(sourceFixture) {
    return {
        canonicalMatchId: sourceFixture.canonicalMatchId,
        state: 'ASOF_STATE_AMBIGUOUS',
        basis: basis('ASOF_STATE_AMBIGUOUS', [`conflict:${sourceFixture.canonicalMatchId}`]),
    };
}

function exactAdjustment(adjustmentId, state = 'EFFECTIVE_AND_AVAILABLE_AT_T') {
    const effectiveAtUtc =
        state === 'EFFECTIVE_AND_AVAILABLE_AT_T' ? '2022-08-18T10:00:00.000Z' : '2022-08-20T10:00:00.000Z';
    return {
        adjustmentId,
        competition: 'Premier League',
        leagueId: 47,
        season: SEASON,
        teamId: 'TEAM_01',
        delta: -3,
        state,
        effectiveTime: {
            kind: 'EXACT',
            atUtc: effectiveAtUtc,
            lowerBoundUtc: null,
            upperBoundUtc: null,
        },
        sourceLineage: lineage(`adjustment:${adjustmentId}`),
        availabilityProof: observationProof(`proof:${adjustmentId}`),
    };
}

function intervalAdjustment(adjustmentId, state = 'ASOF_ADJUSTMENT_AMBIGUOUS') {
    return {
        adjustmentId,
        competition: 'Premier League',
        leagueId: 47,
        season: SEASON,
        teamId: 'TEAM_01',
        delta: -3,
        state,
        effectiveTime: {
            kind: 'INTERVAL',
            atUtc: null,
            lowerBoundUtc: '2022-08-19T00:00:00.000Z',
            upperBoundUtc: '2022-08-20T00:00:00.000Z',
        },
        sourceLineage: lineage(`adjustment:${adjustmentId}`),
        availabilityProof: observationProof(`proof:${adjustmentId}`),
    };
}

function clone(value) {
    return JSON.parse(JSON.stringify(value));
}

function baseInput() {
    const prior = fixture('prior', '2022-08-18T12:00:00.000Z', 'TEAM_03', 'TEAM_04');
    const future = fixture('future', '2022-08-21T12:00:00.000Z', 'TEAM_01', 'TEAM_02');
    const target = fixture('target', TARGET_KICKOFF, 'TEAM_01', 'TEAM_02');
    return {
        contractBoundary: clone(CONTRACT_BOUNDARY),
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
            sourceLineage: lineage('target:target'),
        },
        fixtureUniverse: {
            reference: {
                referenceId: 'canonical-fixture-universe-test-reference',
                referenceVersion: 'v1',
                referenceSha256: 'a'.repeat(64),
                fixtureIds: ['prior', 'future', 'target'],
            },
            fixtures: [prior, future, target],
        },
        fixtureStates: [availableState(prior), noTableState(future), targetExcludedState(target)],
        administrativeAdjustments: [],
    };
}

function expectReject(mutator, expectedCode) {
    const value = baseInput();
    mutator(value);
    assert.throws(
        () => validateStandingsAsOfEngineInput(value),
        error =>
            error instanceof StandingsAsOfEngineInputContractError && (!expectedCode || error.code === expectedCode)
    );
}

function validated(value = baseInput()) {
    return validateStandingsAsOfEngineInput(value);
}

test('valid T strictly before target kickoff is accepted structurally', () => {
    const result = validated();
    assert.equal(result.semanticStatus, 'STRUCTURALLY_VALID');
    assert.equal(result.normalizedInput.model_decision_time_utc, T);
    assert.equal(result.normalizedInput.target.targetKickoffUtc, TARGET_KICKOFF);
});

test('missing model decision time is rejected', () => {
    expectReject(value => delete value.modelDecisionTimeUtc, 'ASOF_DECISION_TIME_INVALID');
});

test('FEATURE_AS_OF different from T is rejected', () => {
    expectReject(value => {
        value.featureAsOfUtc = '2022-08-19T11:59:59.000Z';
    }, 'MODEL_ASOF_BINDING_MISMATCH');
});

test('T at or after target kickoff is rejected', () => {
    expectReject(value => {
        value.modelDecisionTimeUtc = TARGET_KICKOFF;
        value.featureAsOfUtc = TARGET_KICKOFF;
    }, 'ASOF_DECISION_TIME_INVALID');
});

test('replacing target kickoff with T is rejected', () => {
    expectReject(value => {
        value.target.targetKickoffUtc = T;
    }, 'ASOF_DECISION_TIME_INVALID');
});

test('exact fixture-universe reference is required', () => {
    expectReject(value => delete value.fixtureUniverse.reference, 'FIXTURE_UNIVERSE_INCOMPLETE');
});

test('duplicate fixture as-of state is rejected', () => {
    expectReject(value => value.fixtureStates.push(clone(value.fixtureStates[0])), 'FIXTURE_ASOF_STATE_DUPLICATE');
});

test('omitted required fixture state is rejected', () => {
    expectReject(value => value.fixtureStates.splice(1, 1), 'FIXTURE_ASOF_STATE_MISSING');
});

test('unknown fixture identity is rejected', () => {
    expectReject(value => {
        value.fixtureStates[0].canonicalMatchId = 'unknown-fixture';
    }, 'FIXTURE_ASOF_STATE_UNKNOWN');
});

test('exactly one target fixture is explicitly excluded', () => {
    const result = validated();
    assert.equal(result.stateCounts.targetFixtureExcluded, 1);
    assert.equal(
        result.normalizedInput.fixture_states.find(state => state.state === 'TARGET_FIXTURE_EXCLUDED').canonicalMatchId,
        'target'
    );
});

test('target fixture contributing a result is rejected', () => {
    expectReject(value => {
        const target = value.fixtureUniverse.fixtures.find(row => row.canonicalMatchId === 'target');
        value.fixtureStates[2] = availableState(target);
    }, 'TARGET_FIXTURE_NOT_EXCLUDED');
});

test('RESULT_AVAILABLE_AT_T with a normalized final result is accepted structurally', () => {
    const result = validated();
    assert.equal(result.stateCounts.resultAvailableAtT, 1);
    assert.equal(
        result.normalizedInput.fixture_states.find(state => state.canonicalMatchId === 'prior').state,
        'RESULT_AVAILABLE_AT_T'
    );
});

test('RESULT_AVAILABLE_AT_T without final score is rejected', () => {
    expectReject(value => {
        delete value.fixtureStates[0].result.homeScore;
    }, 'RESULT_AVAILABLE_AT_T_UNPROVEN');
});

test('RESULT_AVAILABLE_AT_T without table eligibility is rejected', () => {
    expectReject(value => {
        delete value.fixtureStates[0].result.tableEligibility;
    }, 'RESULT_AVAILABLE_AT_T_UNPROVEN');
});

test('event time alone cannot prove RESULT_AVAILABLE_AT_T', () => {
    expectReject(value => {
        value.fixtureStates[0].result.availabilityProof = null;
    }, 'RESULT_AVAILABLE_AT_T_UNPROVEN');
});

test('result observed after T is rejected', () => {
    expectReject(value => {
        value.fixtureStates[0].result.availabilityProof = observationProof('proof:prior', '2022-08-19T12:00:01.000Z');
    }, 'POST_DECISION_STANDINGS_EVIDENCE');
});

test('captured-at-only proof is rejected', () => {
    expectReject(value => {
        value.fixtureStates[0].result.availabilityProof = {
            kind: 'CAPTURED_AT_ONLY',
            capturedAtUtc: '2022-08-19T10:00:00.000Z',
            proofRef: 'proof:prior',
        };
    }, 'RESULT_AVAILABLE_AT_T_UNPROVEN');
});

test('supported NO_TABLE_RESULT_AT_T status is accepted with explicit reason and evidence', () => {
    const value = baseInput();
    const prior = value.fixtureUniverse.fixtures[0];
    value.fixtureStates[0] = noTableState(prior, 'PROVEN_POSTPONED_NOT_PLAYED_BY_T');
    const result = validated(value);
    assert.equal(result.semanticStatus, 'STRUCTURALLY_VALID');
    assert.equal(result.stateCounts.noTableResultAtT, 2);
});

test('naked not_required boolean is rejected', () => {
    expectReject(value => {
        value.fixtureStates[1].not_required = true;
    }, 'STANDINGS_ASOF_INPUT_CONTRACT_MISMATCH');
});

test('missing data cannot masquerade as schedule-not-yet-reached', () => {
    expectReject(value => {
        value.fixtureStates[0] = noTableState(value.fixtureUniverse.fixtures[0]);
    }, 'STANDINGS_ASOF_INPUT_CONTRACT_MISMATCH');
});

test('REQUIRED_EVIDENCE_MISSING_AT_T is returned as a blocking semantic status', () => {
    const value = baseInput();
    value.fixtureStates[0] = missingState(value.fixtureUniverse.fixtures[0]);
    const result = validated(value);
    assert.equal(result.semanticStatus, 'BLOCKED');
    assert.deepEqual(result.blockingReasonCodes, ['REQUIRED_EVIDENCE_MISSING_AT_T']);
    assert.equal(result.statuses.TEMPORAL_ELIGIBILITY_VALIDITY, 'NOT_PROVEN');
});

test('ASOF_STATE_AMBIGUOUS is returned as a blocking semantic status', () => {
    const value = baseInput();
    value.fixtureStates[0] = ambiguousState(value.fixtureUniverse.fixtures[0]);
    const result = validated(value);
    assert.equal(result.semanticStatus, 'BLOCKED');
    assert.deepEqual(result.blockingReasonCodes, ['ASOF_STATE_AMBIGUOUS']);
});

test('conflicting fixture-state identity is rejected', () => {
    expectReject(value => {
        value.fixtureUniverse.fixtures[0].homeTeamId = 'TEAM_01';
    }, 'TARGET_KICKOFF_IDENTITY_CONFLICT');
});

test('unknown fixture state is rejected', () => {
    expectReject(value => {
        value.fixtureStates[0].state = 'NOT_YET_ELIGIBLE_AT_T';
    }, 'FIXTURE_ASOF_STATE_UNKNOWN');
});

test('unknown no-table reason is rejected', () => {
    expectReject(value => {
        value.fixtureStates[1].basis.reasonCode = 'NOT_REQUIRED';
    }, 'FIXTURE_ASOF_STATE_UNKNOWN');
});

test('effective and available adjustment by T is accepted structurally', () => {
    const value = baseInput();
    value.administrativeAdjustments = [exactAdjustment('adj-effective')];
    const result = validated(value);
    assert.equal(result.semanticStatus, 'STRUCTURALLY_VALID');
    assert.equal(result.normalizedInput.administrative_adjustments[0].state, ADJUSTMENT_STATES[0]);
});

test('known-not-effective adjustment by T is accepted structurally', () => {
    const value = baseInput();
    value.administrativeAdjustments = [exactAdjustment('adj-future', 'KNOWN_NOT_EFFECTIVE_AT_T')];
    const result = validated(value);
    assert.equal(result.semanticStatus, 'STRUCTURALLY_VALID');
    assert.equal(result.normalizedInput.administrative_adjustments[0].state, 'KNOWN_NOT_EFFECTIVE_AT_T');
});

test('adjustment interval overlapping T becomes blocking ambiguity', () => {
    const value = baseInput();
    value.administrativeAdjustments = [intervalAdjustment('adj-ambiguous')];
    const result = validated(value);
    assert.equal(result.semanticStatus, 'BLOCKED');
    assert.deepEqual(result.blockingReasonCodes, ['ADMIN_ADJUSTMENT_ASOF_AMBIGUOUS']);
});

test('post-T observed adjustment is rejected', () => {
    const value = baseInput();
    const adjustment = exactAdjustment('adj-post-t');
    adjustment.availabilityProof = observationProof('proof:adj-post-t', '2022-08-19T12:00:01.000Z');
    value.administrativeAdjustments = [adjustment];
    assert.throws(
        () => validated(value),
        error => error.code === 'POST_DECISION_STANDINGS_EVIDENCE'
    );
});

test('caller adjustment_stream_complete cannot establish source completeness', () => {
    expectReject(value => {
        value.adjustment_stream_complete = true;
    }, 'STANDINGS_ASOF_INPUT_CONTRACT_MISMATCH');
});

test('duplicate adjustment ID is rejected', () => {
    const value = baseInput();
    value.administrativeAdjustments = [exactAdjustment('adj-duplicate'), exactAdjustment('adj-duplicate')];
    assert.throws(
        () => validated(value),
        error => error.code === 'ADMIN_ADJUSTMENT_ASOF_AMBIGUOUS'
    );
});

test('conflicting adjustment state is rejected', () => {
    const value = baseInput();
    const adjustment = exactAdjustment('adj-conflict');
    adjustment.state = 'KNOWN_NOT_EFFECTIVE_AT_T';
    value.administrativeAdjustments = [adjustment];
    assert.throws(
        () => validated(value),
        error => error.code === 'ADMIN_ADJUSTMENT_ASOF_AMBIGUOUS'
    );
});

test('caller source_authority_proven flag is rejected fail-closed', () => {
    expectReject(value => {
        value.source_authority_proven = true;
    }, 'STANDINGS_ASOF_INPUT_CONTRACT_MISMATCH');
});

test('caller fixture_status_authority_proven flag is rejected fail-closed', () => {
    expectReject(value => {
        value.fixture_status_authority_proven = true;
    }, 'STANDINGS_ASOF_INPUT_CONTRACT_MISMATCH');
});

test('caller result_stream_complete flag is rejected fail-closed', () => {
    expectReject(value => {
        value.result_stream_complete = true;
    }, 'STANDINGS_ASOF_INPUT_CONTRACT_MISMATCH');
});

test('arbitrary source authority text cannot promote source authority', () => {
    const value = baseInput();
    value.fixtureUniverse.reference.referenceId = 'arbitrary-source-authority-string';
    const result = validated(value);
    assert.equal(result.statuses.SOURCE_AUTHORITY_VALIDITY, 'NOT_PROVEN');
    assert.equal(result.trustBoundary.CANONICAL_FIXTURE_UNIVERSE_AUTHORITY_PROVEN, 'NOT_PROVEN');
});

test('arbitrary Git SHA cannot establish engine provenance', () => {
    expectReject(value => {
        value.sourceCommit = '0123456789abcdef0123456789abcdef01234567';
    }, 'STANDINGS_ASOF_INPUT_CONTRACT_MISMATCH');
});

test('validator cannot claim runtime source authority', () => {
    const result = validated();
    assert.equal(result.trustBoundary.ENGINE_INPUT_CORE_ESTABLISHES_RUNTIME_SOURCE_AUTHORITY, 'NO');
    assert.equal(result.statuses.SOURCE_STREAM_COMPLETENESS, 'NOT_PROVEN');
    assert.equal(result.readiness.STANDINGS_RUNTIME_ELIGIBLE, 'NO');
});

test('fixture, result, status, and adjustment stream closure remain separate from structure', () => {
    const result = validated();
    assert.equal(result.statuses.FIXTURE_UNIVERSE_REFERENCE_MATCH, 'STRUCTURALLY_VALID');
    assert.equal(result.statuses.FIXTURE_UNIVERSE_CLOSURE, 'NOT_PROVEN');
    assert.equal(result.statuses.FIXTURE_STATUS_EVIDENCE_CLOSURE, 'NOT_PROVEN');
    assert.equal(result.statuses.RESULT_EVIDENCE_CLOSURE, 'NOT_PROVEN');
    assert.equal(result.statuses.ADMIN_ADJUSTMENT_STREAM_CLOSURE, 'NOT_PROVEN');
});

test('fixture-state permutation preserves canonical digest', () => {
    const first = validated();
    const value = baseInput();
    value.fixtureStates.reverse();
    const second = validated(value);
    assert.equal(first.canonicalDigest, second.canonicalDigest);
});

test('adjustment-state permutation preserves canonical digest', () => {
    const value = baseInput();
    value.administrativeAdjustments = [exactAdjustment('adj-a'), exactAdjustment('adj-b', 'KNOWN_NOT_EFFECTIVE_AT_T')];
    const first = validated(value);
    const permuted = clone(value);
    permuted.standingsContractBinding = STANDINGS_BINDING;
    permuted.administrativeAdjustments.reverse();
    const second = validated(permuted);
    assert.equal(first.canonicalDigest, second.canonicalDigest);
});

test('T substitution changes the canonical digest', () => {
    const first = validated();
    const value = baseInput();
    value.modelDecisionTimeUtc = '2022-08-19T11:00:00.000Z';
    value.featureAsOfUtc = value.modelDecisionTimeUtc;
    const second = validated(value);
    assert.notEqual(first.canonicalDigest, second.canonicalDigest);
});

test('target ID substitution is rejected because target exclusion no longer matches', () => {
    expectReject(value => {
        value.target.canonicalMatchId = 'future';
        value.target.targetKickoffUtc = '2022-08-21T12:00:00.000Z';
    }, 'TARGET_FIXTURE_NOT_EXCLUDED');
});

test('target kickoff substitution is rejected by identity binding', () => {
    expectReject(value => {
        value.target.targetKickoffUtc = '2022-08-20T13:00:00.000Z';
    }, 'TARGET_KICKOFF_IDENTITY_CONFLICT');
});

test('state-reason substitution is rejected when it violates temporal semantics', () => {
    expectReject(value => {
        value.fixtureStates[1].basis.reasonCode = 'PROVEN_POSTPONED_NOT_PLAYED_BY_T';
    }, 'STANDINGS_ASOF_INPUT_CONTRACT_MISMATCH');
});

test('evidence reference substitution changes the canonical digest', () => {
    const first = validated();
    const value = baseInput();
    value.fixtureStates[0].basis.evidenceRefs = ['result:tampered'];
    const second = validated(value);
    assert.notEqual(first.canonicalDigest, second.canonicalDigest);
});

test('result score tamper changes the canonical digest', () => {
    const first = validated();
    const value = baseInput();
    value.fixtureStates[0].result.homeScore = 3;
    const second = validated(value);
    assert.notEqual(first.canonicalDigest, second.canonicalDigest);
});

test('extra unknown input field is rejected', () => {
    expectReject(value => {
        value.unexpected = 'reject-me';
    }, 'STANDINGS_ASOF_INPUT_CONTRACT_MISMATCH');
});

test('contract-version tamper is rejected', () => {
    expectReject(value => {
        value.contractBoundary.version = 'v2';
    }, 'STANDINGS_ASOF_INPUT_CONTRACT_MISMATCH');
});

test('model-as-of version tamper is rejected', () => {
    expectReject(value => {
        value.contractBoundary.model_as_of_contract.version = 'v2';
    }, 'MODEL_ASOF_BINDING_MISMATCH');
});

test('standings contract binding tamper is rejected', () => {
    expectReject(value => {
        value.contractBoundary.standings_contract.contract_id = 'standings/premier-league-point-in-time/v2';
    }, 'MODEL_ASOF_BINDING_MISMATCH');
});

test('runtime-capture contract reference tamper is rejected', () => {
    expectReject(value => {
        value.contractBoundary.runtime_capture_contract.contract_id = 'canonical-runtime-capture/v2';
    }, 'MODEL_ASOF_BINDING_MISMATCH');
});

test('contract identity constants remain versioned and separate from ranking contract', () => {
    assert.equal(STANDINGS_ASOF_ENGINE_INPUT_CONTRACT_ID, 'standings-asof-engine-input/v1');
    assert.equal(STANDINGS_ASOF_ENGINE_INPUT_CONTRACT_VERSION, 'v1');
    assert.notEqual(STANDINGS_ASOF_ENGINE_INPUT_CONTRACT_ID, 'standings/premier-league-point-in-time/v1');
});

test('frozen taxonomy is explicit and complete', () => {
    assert.deepEqual(FIXTURE_STATES, [
        'RESULT_AVAILABLE_AT_T',
        'NO_TABLE_RESULT_AT_T',
        'REQUIRED_EVIDENCE_MISSING_AT_T',
        'ASOF_STATE_AMBIGUOUS',
        'TARGET_FIXTURE_EXCLUDED',
    ]);
    assert.deepEqual(AVAILABILITY_PROOF_KINDS, [
        'EXACT_OBSERVATION_TIMESTAMP',
        'EXACT_EFFECTIVE_TIMESTAMP_WITH_SOURCE_OBSERVATION_PROOF',
        'BOUNDED_INTERVAL_ENTIRELY_BEFORE_T',
    ]);
    assert.deepEqual(ADJUSTMENT_STATES, [
        'EFFECTIVE_AND_AVAILABLE_AT_T',
        'KNOWN_NOT_EFFECTIVE_AT_T',
        'ASOF_ADJUSTMENT_AMBIGUOUS',
    ]);
});

test('future fixture is classified as not-yet-eligible rather than missing evidence', () => {
    const result = validated();
    assert.equal(result.stateCounts.notYetEligibleAtT, 1);
    assert.equal(result.stateCounts.requiredEvidenceMissingAtT, 0);
    assert.equal(result.semanticStatus, 'STRUCTURALLY_VALID');
});

test('availability proof reference is bound to the normalized result fact', () => {
    expectReject(value => {
        value.fixtureStates[0].basis.availabilityProofRef = 'proof:other';
    }, 'RESULT_AVAILABLE_AT_T_UNPROVEN');
});

test('partial final score is rejected', () => {
    expectReject(value => {
        value.fixtureStates[0].result.awayScore = null;
    }, 'RESULT_AVAILABLE_AT_T_UNPROVEN');
});

test('post-T bounded availability interval is rejected', () => {
    expectReject(value => {
        value.fixtureStates[0].result.availabilityProof = {
            kind: 'BOUNDED_INTERVAL_ENTIRELY_BEFORE_T',
            observedAtUtc: null,
            effectiveAtUtc: null,
            intervalStartUtc: '2022-08-19T11:00:00.000Z',
            intervalEndUtc: '2022-08-19T13:00:00.000Z',
            proofRef: 'proof:prior',
        };
    }, 'ASOF_STATE_AMBIGUOUS');
});

test('empty administrative adjustment stream is structurally valid but not complete by authority', () => {
    const result = validated();
    assert.deepEqual(result.normalizedInput.administrative_adjustments, []);
    assert.equal(result.trustBoundary.ADMIN_ADJUSTMENT_STREAM_AUTHORITY, 'NOT_PROVEN');
});

test('normalized input contains no source commit provenance field', () => {
    const result = validated();
    assert.equal(Object.hasOwn(result.normalizedInput, 'source_commit'), false);
    assert.equal(Object.hasOwn(result.normalizedInput.contract, 'source_commit'), false);
});
