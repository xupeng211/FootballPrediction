'use strict';

// lifecycle: test-fixture
// 既有 standings engine 的 T-aware consumer 行为、边界策略和 fail-closed gate 测试。

const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const { test } = require('node:test');

const {
    bindFrozenStandingsContract,
    STANDINGS_COMPETITION,
    STANDINGS_CONTRACT_ID,
    STANDINGS_LEAGUE_ID,
} = require('../../src/infrastructure/standings/StandingsContractBinding');
const {
    computeStandingsAsOfSnapshot,
    computeStandingsSnapshot,
    computeStandingsSnapshots,
    PointInTimeStandingsEngine,
} = require('../../src/infrastructure/standings/PointInTimeStandingsEngine');

const REGISTRY_PATH = path.resolve(__dirname, '../../config/model_feature_contracts.json');
const ENGINE_PATH = path.resolve(__dirname, '../../src/infrastructure/standings/PointInTimeStandingsEngine.js');
const REGISTRY = JSON.parse(fs.readFileSync(REGISTRY_PATH, 'utf8'));
const INPUT_BOUNDARY = REGISTRY.decision_boundaries.standings_asof_engine_input;
const STANDINGS_BINDING = bindFrozenStandingsContract(REGISTRY);
const SEASON = '2022/2023';
const T = '2022-08-19T12:00:00.000Z';
const TARGET_KICKOFF = '2022-08-20T12:00:00.000Z';
const TEAMS = Array.from({ length: 20 }, (_, index) => `TEAM_${String(index + 1).padStart(2, '0')}`);

function clone(value) {
    return JSON.parse(JSON.stringify(value));
}

function cloneAsOfInput(value) {
    const copy = clone(value);
    copy.standingsContractBinding = STANDINGS_BINDING;
    return copy;
}

function lineage(id) {
    return {
        evidenceRefs: [`evidence:${id}`, `lineage:${id}`],
        sourceRecordRef: `record:${id}`,
    };
}

function fixture(canonicalMatchId, scheduledKickoffUtc, homeTeamId, awayTeamId) {
    return {
        canonicalMatchId,
        competition: STANDINGS_COMPETITION,
        leagueId: STANDINGS_LEAGUE_ID,
        season: SEASON,
        homeTeamId,
        awayTeamId,
        scheduledKickoffUtc,
        sourceLineage: lineage(`fixture:${canonicalMatchId}`),
    };
}

function observationProof(proofRef, observedAtUtc = '2022-08-19T10:00:00.000Z') {
    return {
        kind: 'EXACT_OBSERVATION_TIMESTAMP',
        observedAtUtc,
        effectiveAtUtc: null,
        intervalStartUtc: null,
        intervalEndUtc: null,
        proofRef,
    };
}

function asOfResult(sourceFixture, { actualEligibleEventTimeUtc, homeScore = 2, awayScore = 1 } = {}) {
    const eventTime = actualEligibleEventTimeUtc || sourceFixture.scheduledKickoffUtc;
    const proofRef = `proof:${sourceFixture.canonicalMatchId}`;
    return {
        canonicalMatchId: sourceFixture.canonicalMatchId,
        competition: sourceFixture.competition,
        leagueId: sourceFixture.leagueId,
        season: sourceFixture.season,
        homeTeamId: sourceFixture.homeTeamId,
        awayTeamId: sourceFixture.awayTeamId,
        actualEligibleEventTimeUtc: eventTime,
        disposition: 'COMPLETED',
        tableEligibility: 'ELIGIBLE',
        finalityStatus: 'FINAL',
        homeScore,
        awayScore,
        sourceLineage: lineage(`result:${sourceFixture.canonicalMatchId}`),
        availabilityProof: observationProof(proofRef),
        replayOfMatchId: null,
    };
}

function basis(reasonCode, id, availabilityProofRef = null) {
    return {
        reasonCode,
        evidenceRefs: [`basis:${id}`],
        availabilityProofRef,
    };
}

function availableState(sourceFixture, options = {}) {
    const proofRef = `proof:${sourceFixture.canonicalMatchId}`;
    return {
        canonicalMatchId: sourceFixture.canonicalMatchId,
        state: 'RESULT_AVAILABLE_AT_T',
        basis: basis('RESULT_AVAILABLE_AT_T', sourceFixture.canonicalMatchId, proofRef),
        result: asOfResult(sourceFixture, options),
    };
}

function noTableState(sourceFixture, reasonCode = 'SCHEDULE_NOT_YET_REACHED_AT_T') {
    return {
        canonicalMatchId: sourceFixture.canonicalMatchId,
        state: 'NO_TABLE_RESULT_AT_T',
        basis: basis(reasonCode, sourceFixture.canonicalMatchId),
    };
}

function targetExcludedState(sourceFixture) {
    return {
        canonicalMatchId: sourceFixture.canonicalMatchId,
        state: 'TARGET_FIXTURE_EXCLUDED',
        basis: basis('TARGET_FIXTURE_EXCLUDED', sourceFixture.canonicalMatchId),
    };
}

function missingState(sourceFixture) {
    return {
        canonicalMatchId: sourceFixture.canonicalMatchId,
        state: 'REQUIRED_EVIDENCE_MISSING_AT_T',
        basis: basis('REQUIRED_EVIDENCE_MISSING_AT_T', sourceFixture.canonicalMatchId),
    };
}

function ambiguousState(sourceFixture) {
    return {
        canonicalMatchId: sourceFixture.canonicalMatchId,
        state: 'ASOF_STATE_AMBIGUOUS',
        basis: basis('ASOF_STATE_AMBIGUOUS', sourceFixture.canonicalMatchId),
    };
}

function exactAdjustment(adjustmentId, atUtc, state) {
    return {
        adjustmentId,
        competition: STANDINGS_COMPETITION,
        leagueId: STANDINGS_LEAGUE_ID,
        season: SEASON,
        teamId: 'TEAM_03',
        delta: -3,
        state,
        effectiveTime: {
            kind: 'EXACT',
            atUtc,
            lowerBoundUtc: null,
            upperBoundUtc: null,
        },
        sourceLineage: lineage(`adjustment:${adjustmentId}`),
        availabilityProof: observationProof(`proof:${adjustmentId}`),
    };
}

function overlappingAdjustment(adjustmentId = 'adjustment-overlap') {
    return {
        adjustmentId,
        competition: STANDINGS_COMPETITION,
        leagueId: STANDINGS_LEAGUE_ID,
        season: SEASON,
        teamId: 'TEAM_03',
        delta: -3,
        state: 'ASOF_ADJUSTMENT_AMBIGUOUS',
        effectiveTime: {
            kind: 'INTERVAL',
            atUtc: null,
            lowerBoundUtc: '2022-08-19T11:00:00.000Z',
            upperBoundUtc: '2022-08-19T13:00:00.000Z',
        },
        sourceLineage: lineage(`adjustment:${adjustmentId}`),
        availabilityProof: observationProof(`proof:${adjustmentId}`),
    };
}

function asOfInput({
    modelDecisionTimeUtc = T,
    targetKickoffUtc = TARGET_KICKOFF,
    priorState = 'AVAILABLE',
    priorEventTimeUtc = '2022-08-19T11:00:00.000Z',
    priorHomeScore = 2,
    priorAwayScore = 1,
    administrativeAdjustments = [],
} = {}) {
    const fixtures = [
        fixture('target', targetKickoffUtc, 'TEAM_01', 'TEAM_02'),
        fixture('prior', '2022-08-18T12:00:00.000Z', 'TEAM_03', 'TEAM_04'),
    ];
    for (let index = 2; index < 10; index += 1) {
        const homeTeamId = TEAMS[index * 2];
        const awayTeamId = TEAMS[index * 2 + 1];
        fixtures.push(fixture(`future-${index}`, '2022-08-21T12:00:00.000Z', homeTeamId, awayTeamId));
    }
    const priorFixture = fixtures.find(row => row.canonicalMatchId === 'prior');
    const targetFixture = fixtures.find(row => row.canonicalMatchId === 'target');
    const states = [
        priorState === 'AVAILABLE'
            ? availableState(priorFixture, {
                  actualEligibleEventTimeUtc: priorEventTimeUtc,
                  homeScore: priorHomeScore,
                  awayScore: priorAwayScore,
              })
            : priorState === 'MISSING'
              ? missingState(priorFixture)
              : priorState === 'AMBIGUOUS'
                ? ambiguousState(priorFixture)
                : noTableState(priorFixture, priorState),
        targetExcludedState(targetFixture),
        ...fixtures.filter(row => row.canonicalMatchId.startsWith('future-')).map(row => noTableState(row)),
    ];
    return {
        contractBoundary: clone(INPUT_BOUNDARY),
        standingsContractBinding: STANDINGS_BINDING,
        modelDecisionTimeUtc,
        featureAsOfUtc: modelDecisionTimeUtc,
        target: {
            canonicalMatchId: targetFixture.canonicalMatchId,
            competition: targetFixture.competition,
            leagueId: targetFixture.leagueId,
            season: targetFixture.season,
            homeTeamId: targetFixture.homeTeamId,
            awayTeamId: targetFixture.awayTeamId,
            targetKickoffUtc: targetFixture.scheduledKickoffUtc,
            sourceLineage: lineage('target:target'),
        },
        fixtureUniverse: {
            reference: {
                referenceId: 'canonical-fixture-universe-consumer-test',
                referenceVersion: 'v1',
                referenceSha256: 'a'.repeat(64),
                fixtureIds: fixtures.map(row => row.canonicalMatchId),
            },
            fixtures,
        },
        fixtureStates: states,
        administrativeAdjustments,
    };
}

function legacyInput({ targetKickoffUtc = TARGET_KICKOFF, eventTimeUtc, adjustment } = {}) {
    const targetFixture = fixture('target', targetKickoffUtc, 'TEAM_01', 'TEAM_02');
    const priorFixture = fixture('prior', '2022-08-18T12:00:00.000Z', 'TEAM_03', 'TEAM_04');
    return {
        contractBinding: STANDINGS_BINDING,
        competition: STANDINGS_COMPETITION,
        leagueId: STANDINGS_LEAGUE_ID,
        season: SEASON,
        teamUniverse: TEAMS,
        fixtures: [targetFixture, priorFixture],
        results: [
            {
                ...asOfResult(priorFixture, { actualEligibleEventTimeUtc: eventTimeUtc }),
                availabilityProof: undefined,
            },
        ].map(result => {
            const { availabilityProof, ...legacyResult } = result;
            return legacyResult;
        }),
        administrativeAdjustments: adjustment ? [adjustment] : [],
        target: {
            canonicalMatchId: targetFixture.canonicalMatchId,
            competition: targetFixture.competition,
            leagueId: targetFixture.leagueId,
            season: SEASON,
            homeTeamId: targetFixture.homeTeamId,
            awayTeamId: targetFixture.awayTeamId,
            targetKickoffUtc,
            sourceLineage: lineage('target:target'),
        },
    };
}

function assertUnavailable(output, reason) {
    assert.equal(output.engine_computation_status, 'NOT_EXECUTED');
    assert.equal(output.home_table_position, null);
    assert.equal(output.away_table_position, null);
    assert.equal(output.table_position_diff, null);
    assert.deepEqual(output.unavailable_reason_codes, [reason]);
}

test('C01-C03 legacy result boundary remains strict kickoff-exclusive', () => {
    const before = computeStandingsSnapshot(legacyInput({ eventTimeUtc: '2022-08-20T11:59:59.000Z' }));
    const equal = computeStandingsSnapshot(legacyInput({ eventTimeUtc: TARGET_KICKOFF }));
    const after = computeStandingsSnapshot(legacyInput({ eventTimeUtc: '2022-08-20T12:00:01.000Z' }));
    assert.deepEqual(before.source_event_ids_used, ['prior']);
    assert.deepEqual(equal.source_event_ids_used, []);
    assert.deepEqual(equal.diagnostics.same_kickoff_excluded_event_ids, ['prior']);
    assert.deepEqual(after.source_event_ids_used, []);
    assert.deepEqual(after.diagnostics.future_event_ids_excluded, ['prior']);
});

test('C04-C06 as-of result boundary is inclusive at T and rejects post-T evidence', () => {
    const before = computeStandingsAsOfSnapshot(asOfInput({ priorEventTimeUtc: '2022-08-19T11:59:59.000Z' }));
    const equal = computeStandingsAsOfSnapshot(asOfInput({ priorEventTimeUtc: T }));
    assert.deepEqual(before.source_event_ids_used, ['prior']);
    assert.deepEqual(equal.source_event_ids_used, ['prior']);
    assert.equal(equal.engine_computation_status, 'EXECUTED');

    const postT = asOfInput({ priorEventTimeUtc: '2022-08-19T12:00:01.000Z' });
    assert.throws(
        () => computeStandingsAsOfSnapshot(postT),
        error => error.code === 'RESULT_AVAILABLE_AT_T_UNPROVEN'
    );
});

test('C07-C08 legacy exact adjustment boundary remains strict kickoff-exclusive', () => {
    const before = computeStandingsSnapshot(
        legacyInput({
            eventTimeUtc: '2022-08-18T13:00:00.000Z',
            adjustment: {
                adjustmentId: 'legacy-before',
                competition: STANDINGS_COMPETITION,
                leagueId: STANDINGS_LEAGUE_ID,
                season: SEASON,
                teamId: 'TEAM_03',
                delta: -3,
                effectiveTime: { kind: 'EXACT', atUtc: '2022-08-20T11:59:59.000Z' },
                sourceLineage: lineage('adjustment:legacy-before'),
            },
        })
    );
    const equal = computeStandingsSnapshot(
        legacyInput({
            eventTimeUtc: '2022-08-18T13:00:00.000Z',
            adjustment: {
                adjustmentId: 'legacy-equal',
                competition: STANDINGS_COMPETITION,
                leagueId: STANDINGS_LEAGUE_ID,
                season: SEASON,
                teamId: 'TEAM_03',
                delta: -3,
                effectiveTime: { kind: 'EXACT', atUtc: TARGET_KICKOFF },
                sourceLineage: lineage('adjustment:legacy-equal'),
            },
        })
    );
    assert.deepEqual(before.administrative_adjustment_ids_applied, ['legacy-before']);
    assert.deepEqual(equal.administrative_adjustment_ids_applied, []);
});

test('C09-C11 as-of exact adjustment boundary is inclusive at T', () => {
    const before = computeStandingsAsOfSnapshot(
        asOfInput({
            administrativeAdjustments: [
                exactAdjustment('asof-before', '2022-08-19T11:59:59.000Z', 'EFFECTIVE_AND_AVAILABLE_AT_T'),
            ],
        })
    );
    const equal = computeStandingsAsOfSnapshot(
        asOfInput({
            administrativeAdjustments: [exactAdjustment('asof-equal', T, 'EFFECTIVE_AND_AVAILABLE_AT_T')],
        })
    );
    const after = computeStandingsAsOfSnapshot(
        asOfInput({
            administrativeAdjustments: [
                exactAdjustment('asof-after', '2022-08-19T12:00:01.000Z', 'KNOWN_NOT_EFFECTIVE_AT_T'),
            ],
        })
    );
    assert.deepEqual(before.administrative_adjustment_ids_applied, ['asof-before']);
    assert.deepEqual(equal.administrative_adjustment_ids_applied, ['asof-equal']);
    assert.deepEqual(after.administrative_adjustment_ids_applied, []);
});

test('C12 overlapping as-of adjustment interval is unavailable before ranking computation', () => {
    const output = computeStandingsAsOfSnapshot(asOfInput({ administrativeAdjustments: [overlappingAdjustment()] }));
    assertUnavailable(output, 'ADMIN_ADJUSTMENT_ASOF_AMBIGUOUS');
});

test('C13-C14 blocked semantic states return deterministic unavailable output', () => {
    const missing = computeStandingsAsOfSnapshot(asOfInput({ priorState: 'MISSING' }));
    const ambiguous = computeStandingsAsOfSnapshot(asOfInput({ priorState: 'AMBIGUOUS' }));
    assertUnavailable(missing, 'REQUIRED_EVIDENCE_MISSING_AT_T');
    assertUnavailable(ambiguous, 'ASOF_STATE_AMBIGUOUS');
});

test('C15-C17 all source-dependent NO_TABLE reasons cannot reach numeric computation', () => {
    const reasons = [
        'PROVEN_POSTPONED_NOT_PLAYED_BY_T',
        'PROVEN_NOT_FINAL_BY_T',
        'PROVEN_NON_TABLE_ELIGIBLE_BY_T',
        'PROVEN_ABANDONED_NON_TABLE_ELIGIBLE_BY_T',
        'PROVEN_VOID_NON_TABLE_ELIGIBLE_BY_T',
        'PROVEN_REPLAY_ORIGINAL_NON_ELIGIBLE_BY_T',
    ];
    for (const reason of reasons) {
        const output = computeStandingsAsOfSnapshot(asOfInput({ priorState: reason }));
        assertUnavailable(output, 'STANDINGS_SOURCE_CLOSURE_UNPROVEN');
        assert.equal(output.source_event_ids_used.length, 0);
    }
});

test('C18 schedule-not-yet state is consumable by the as-of kernel', () => {
    const output = computeStandingsAsOfSnapshot(asOfInput());
    assert.equal(output.engine_computation_status, 'EXECUTED');
    assert.equal(output.snapshot_status, 'AVAILABLE');
    assert.deepEqual(output.source_event_ids_used, ['prior']);
    assert.equal(output.runtime_numeric_eligibility, 'NO');
    assert.equal(output.source_authority_validity, 'NOT_PROVEN');
});

test('C19 prior fixture cannot masquerade as schedule-not-yet', () => {
    assert.throws(
        () => computeStandingsAsOfSnapshot(asOfInput({ priorState: 'SCHEDULE_NOT_YET_REACHED_AT_T' })),
        error => error.code === 'STANDINGS_ASOF_INPUT_CONTRACT_MISMATCH'
    );
});

test('C20 target fixture is always excluded and cannot carry a result', () => {
    const value = asOfInput();
    const target = value.fixtureUniverse.fixtures.find(row => row.canonicalMatchId === 'target');
    value.fixtureStates[1] = availableState(target, { actualEligibleEventTimeUtc: '2022-08-19T11:00:00.000Z' });
    assert.throws(
        () => computeStandingsAsOfSnapshot(value),
        error => error.code === 'TARGET_FIXTURE_NOT_EXCLUDED'
    );
});

test('C21-C24 caller assertions and prevalidated wrappers are rejected by the raw validator', () => {
    for (const field of ['consumerEligible', 'evaluationBoundaryUtc', 'validatedInput', 'sourceAuthorityProven']) {
        const value = asOfInput();
        value[field] = field === 'evaluationBoundaryUtc' ? T : true;
        assert.throws(
            () => computeStandingsAsOfSnapshot(value),
            error => error.code === 'STANDINGS_ASOF_INPUT_CONTRACT_MISMATCH'
        );
    }
});

test('C25-C27 legacy APIs and the as-of API belong to one PointInTimeStandingsEngine family', () => {
    assert.equal(typeof computeStandingsSnapshot, 'function');
    assert.equal(typeof computeStandingsSnapshots, 'function');
    assert.equal(typeof computeStandingsAsOfSnapshot, 'function');
    assert.equal(PointInTimeStandingsEngine.computeStandingsSnapshot, computeStandingsSnapshot);
    assert.equal(PointInTimeStandingsEngine.computeStandingsSnapshots, computeStandingsSnapshots);
    assert.equal(PointInTimeStandingsEngine.computeStandingsAsOfSnapshot, computeStandingsAsOfSnapshot);
    assert.equal(Object.keys(PointInTimeStandingsEngine).length, 3);
});

test('C28-C30 no generic cutoff API or second ranking implementation is exported', () => {
    assert.equal(PointInTimeStandingsEngine.computeStandingsAtTime, undefined);
    assert.equal(PointInTimeStandingsEngine.computeWithBoundary, undefined);
    const source = fs.readFileSync(ENGINE_PATH, 'utf8');
    assert.equal((source.match(/function applyResult\(/g) || []).length, 1);
    assert.equal((source.match(/function strictlyAhead\(/g) || []).length, 1);
    assert.equal((source.match(/function assignPositions\(/g) || []).length, 1);
    assert.match(source, /computePreparedStandings\(prepared, LEGACY_KICKOFF_EXCLUSIVE\)/);
    assert.match(source, /computePreparedStandings\(prepared, MODEL_DECISION_TIME_INCLUSIVE\)/);
    assert.equal(STANDINGS_CONTRACT_ID, 'standings/premier-league-point-in-time/v1');
});

test('C31-C33 as-of consumer provenance is invariant under fixture and adjustment permutations', () => {
    const adjustmentA = exactAdjustment('permutation-a', '2022-08-19T10:00:00.000Z', 'EFFECTIVE_AND_AVAILABLE_AT_T');
    const adjustmentB = exactAdjustment('permutation-b', '2022-08-19T09:00:00.000Z', 'EFFECTIVE_AND_AVAILABLE_AT_T');
    const firstInput = asOfInput({ administrativeAdjustments: [adjustmentA, adjustmentB] });
    const first = computeStandingsAsOfSnapshot(firstInput);
    const secondInput = cloneAsOfInput(firstInput);
    secondInput.fixtureUniverse.fixtures.reverse();
    secondInput.fixtureStates.reverse();
    secondInput.administrativeAdjustments.reverse();
    const second = computeStandingsAsOfSnapshot(secondInput);
    assert.equal(first.consumer_provenance_digest, second.consumer_provenance_digest);
    assert.deepEqual(first.diagnostic_table_state, second.diagnostic_table_state);
});

test('C34 same numeric positions at different T values still produce different provenance', () => {
    const first = computeStandingsAsOfSnapshot(asOfInput({ modelDecisionTimeUtc: '2022-08-19T11:00:00.000Z' }));
    const second = computeStandingsAsOfSnapshot(asOfInput({ modelDecisionTimeUtc: '2022-08-19T11:30:00.000Z' }));
    assert.deepEqual(
        [first.home_table_position, first.away_table_position, first.table_position_diff],
        [second.home_table_position, second.away_table_position, second.table_position_diff]
    );
    assert.notEqual(first.consumer_provenance_digest, second.consumer_provenance_digest);
});

test('C35 target kickoff remains distinct and bound in consumer provenance', () => {
    const first = computeStandingsAsOfSnapshot(asOfInput());
    const second = computeStandingsAsOfSnapshot(asOfInput({ targetKickoffUtc: '2022-08-20T13:00:00.000Z' }));
    assert.notEqual(first.target_kickoff_utc, second.target_kickoff_utc);
    assert.notEqual(first.consumer_provenance_digest, second.consumer_provenance_digest);
});

test('C36-C38 score, source-event-set, and applied-adjustment changes alter provenance', () => {
    const baseline = computeStandingsAsOfSnapshot(asOfInput());
    const scoreChanged = computeStandingsAsOfSnapshot(asOfInput({ priorHomeScore: 3 }));
    assert.notEqual(baseline.consumer_provenance_digest, scoreChanged.consumer_provenance_digest);

    const sourceChangedInput = asOfInput();
    const extraFixture = sourceChangedInput.fixtureUniverse.fixtures.find(row => row.canonicalMatchId === 'future-2');
    extraFixture.scheduledKickoffUtc = '2022-08-18T13:00:00.000Z';
    const extraStateIndex = sourceChangedInput.fixtureStates.findIndex(row => row.canonicalMatchId === 'future-2');
    sourceChangedInput.fixtureStates[extraStateIndex] = availableState(extraFixture, {
        actualEligibleEventTimeUtc: '2022-08-18T13:00:00.000Z',
    });
    const sourceChanged = computeStandingsAsOfSnapshot(sourceChangedInput);
    assert.notEqual(baseline.consumer_provenance_digest, sourceChanged.consumer_provenance_digest);

    const adjustmentChanged = computeStandingsAsOfSnapshot(
        asOfInput({
            administrativeAdjustments: [
                exactAdjustment('provenance-adjustment', '2022-08-19T10:00:00.000Z', 'EFFECTIVE_AND_AVAILABLE_AT_T'),
            ],
        })
    );
    assert.notEqual(baseline.consumer_provenance_digest, adjustmentChanged.consumer_provenance_digest);
});

test('C39-C40 contract version tampering cannot be consumed', () => {
    const consumerInputTampered = asOfInput();
    consumerInputTampered.contractBoundary.version = 'v2';
    assert.throws(
        () => computeStandingsAsOfSnapshot(consumerInputTampered),
        error => error.code === 'STANDINGS_ASOF_INPUT_CONTRACT_MISMATCH'
    );
    const inputReferenceTampered = asOfInput();
    inputReferenceTampered.contractBoundary.standings_contract.version = 'v2';
    assert.throws(
        () => computeStandingsAsOfSnapshot(inputReferenceTampered),
        error => error.code === 'MODEL_ASOF_BINDING_MISMATCH'
    );
});

test('consumer does not mutate the caller input and never upgrades runtime readiness', () => {
    const input = asOfInput();
    const before = cloneAsOfInput(input);
    const output = computeStandingsAsOfSnapshot(input);
    assert.deepEqual(input, before);
    assert.equal(output.consumer_contract_id, 'standings-asof-engine-consumer/v1');
    assert.equal(output.consumer_contract_version, 'v1');
    assert.equal(output.evaluation_boundary_policy, 'MODEL_DECISION_TIME_INCLUSIVE');
    assert.equal(output.runtime_numeric_eligibility, 'NO');
    assert.equal(output.source_authority_validity, 'NOT_PROVEN');
    assert.equal(output.ranking_contract_id, 'standings/premier-league-point-in-time/v1');
    assert.notEqual(output.consumer_provenance_digest, output.ranking_projection_provenance_digest);
});
