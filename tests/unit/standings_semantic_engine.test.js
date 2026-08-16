'use strict';

// lifecycle: permanent
// 纯 standings engine 的行为合同测试；不访问网络、数据库或生产 feature 路径。

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
const { computeStandingsSnapshot } = require('../../src/infrastructure/standings/PointInTimeStandingsEngine');

const REGISTRY_PATH = path.resolve(__dirname, '../../config/model_feature_contracts.json');
const SEASON = '2022/2023';
const TEAMS = Array.from({ length: 20 }, (_, index) => `TEAM_${String(index + 1).padStart(2, '0')}`);

function frozenBinding() {
    const registry = JSON.parse(fs.readFileSync(REGISTRY_PATH, 'utf8'));
    return bindFrozenStandingsContract(registry);
}

function lineage(value) {
    return { source: `synthetic:${value}` };
}

function fixture(id, kickoff, homeTeamId = 'TEAM_01', awayTeamId = 'TEAM_02') {
    return {
        canonicalMatchId: id,
        competition: STANDINGS_COMPETITION,
        leagueId: STANDINGS_LEAGUE_ID,
        season: SEASON,
        homeTeamId,
        awayTeamId,
        scheduledKickoffUtc: kickoff,
        sourceLineage: lineage(`fixture:${id}`),
    };
}

function result(
    sourceFixture,
    {
        actualEligibleEventTimeUtc = sourceFixture.scheduledKickoffUtc,
        disposition = 'COMPLETED',
        tableEligibility = 'ELIGIBLE',
        finalityStatus = 'FINAL',
        homeScore = 1,
        awayScore = 0,
        replayOfMatchId,
    } = {}
) {
    return {
        canonicalMatchId: sourceFixture.canonicalMatchId,
        competition: sourceFixture.competition,
        leagueId: sourceFixture.leagueId,
        season: sourceFixture.season,
        homeTeamId: sourceFixture.homeTeamId,
        awayTeamId: sourceFixture.awayTeamId,
        actualEligibleEventTimeUtc,
        disposition,
        tableEligibility,
        finalityStatus,
        homeScore,
        awayScore,
        sourceLineage: lineage(`result:${sourceFixture.canonicalMatchId}`),
        ...(replayOfMatchId === undefined ? {} : { replayOfMatchId }),
    };
}

function targetFrom(sourceFixture, kickoff = sourceFixture.scheduledKickoffUtc) {
    return {
        canonicalMatchId: sourceFixture.canonicalMatchId,
        competition: sourceFixture.competition,
        leagueId: sourceFixture.leagueId,
        season: sourceFixture.season,
        homeTeamId: sourceFixture.homeTeamId,
        awayTeamId: sourceFixture.awayTeamId,
        targetKickoffUtc: kickoff,
        sourceLineage: lineage(`target:${sourceFixture.canonicalMatchId}`),
    };
}

function input({
    targetKickoffUtc = '2022-08-20T12:00:00.000Z',
    targetHomeTeamId = 'TEAM_01',
    targetAwayTeamId = 'TEAM_02',
    targetId = 'target',
    priorFixtures = [],
    priorResults = [],
    extraFixtures = [],
    extraResults = [],
    administrativeAdjustments = [],
    teamUniverse = TEAMS,
} = {}) {
    const targetFixture = fixture(targetId, targetKickoffUtc, targetHomeTeamId, targetAwayTeamId);
    return {
        contractBinding: frozenBinding(),
        competition: STANDINGS_COMPETITION,
        leagueId: STANDINGS_LEAGUE_ID,
        season: SEASON,
        teamUniverse,
        fixtures: [...priorFixtures, ...extraFixtures, targetFixture],
        results: [...priorResults, ...extraResults],
        administrativeAdjustments,
        target: targetFrom(targetFixture, targetKickoffUtc),
    };
}

function cloneInput(value) {
    return {
        ...value,
        teamUniverse: [...value.teamUniverse],
        fixtures: value.fixtures.map(row => ({ ...row, sourceLineage: { ...row.sourceLineage } })),
        results: value.results.map(row => ({ ...row, sourceLineage: { ...row.sourceLineage } })),
        administrativeAdjustments: value.administrativeAdjustments.map(row => ({
            ...row,
            effectiveTime: { ...row.effectiveTime },
            sourceLineage: { ...row.sourceLineage },
        })),
        target: { ...value.target, sourceLineage: { ...value.target.sourceLineage } },
    };
}

function exactAdjustment(adjustmentId, teamId, effectiveTime, delta = -3, season = SEASON) {
    return {
        adjustmentId,
        competition: STANDINGS_COMPETITION,
        leagueId: STANDINGS_LEAGUE_ID,
        season,
        teamId,
        delta,
        effectiveTime,
        sourceLineage: lineage(`adjustment:${adjustmentId}`),
    };
}

function assertUnavailable(resultValue, reason) {
    assert.equal(resultValue.snapshot_status, 'UNAVAILABLE');
    assert.equal(resultValue.home_table_position, null);
    assert.equal(resultValue.away_table_position, null);
    assert.equal(resultValue.table_position_diff, null);
    assert.deepEqual(resultValue.unavailable_reason_codes, [reason]);
}

function assertEngineError(callback, code) {
    assert.throws(callback, error => error?.code === code);
}

test('A: season start is valid and all 20 clubs share position 1', () => {
    const output = computeStandingsSnapshot(input());
    assert.equal(output.snapshot_status, 'AVAILABLE');
    assert.equal(output.diagnostic_table_state.length, 20);
    assert.deepEqual(new Set(output.diagnostic_table_state.map(row => row.position)), new Set([1]));
    assert.equal(output.diagnostic_table_state[0].played, 0);
    assert.equal(output.diagnostic_table_state[0].official_table_points, 0);
});

test('B: one completed result contributes exact W/D/L and positions', () => {
    const prior = fixture('prior', '2022-08-19T12:00:00.000Z', 'TEAM_03', 'TEAM_04');
    const output = computeStandingsSnapshot(input({ priorFixtures: [prior], priorResults: [result(prior)] }));
    const states = new Map(output.diagnostic_table_state.map(row => [row.team_id, row]));
    assert.equal(states.get('TEAM_03').position, 1);
    assert.equal(states.get('TEAM_03').wins, 1);
    assert.equal(states.get('TEAM_04').position, 20);
    assert.equal(states.get('TEAM_04').losses, 1);
});

test('C: points precede goal difference', () => {
    const one = fixture('one', '2022-08-17T12:00:00.000Z', 'TEAM_03', 'TEAM_04');
    const two = fixture('two', '2022-08-18T12:00:00.000Z', 'TEAM_05', 'TEAM_06');
    const output = computeStandingsSnapshot(
        input({
            priorFixtures: [one, two],
            priorResults: [result(one, { homeScore: 1, awayScore: 0 }), result(two, { homeScore: 10, awayScore: 10 })],
        })
    );
    const states = new Map(output.diagnostic_table_state.map(row => [row.team_id, row]));
    assert.ok(states.get('TEAM_03').position < states.get('TEAM_05').position);
});

test('D: equal points use goal difference', () => {
    const one = fixture('one', '2022-08-17T12:00:00.000Z', 'TEAM_03', 'TEAM_04');
    const two = fixture('two', '2022-08-18T12:00:00.000Z', 'TEAM_05', 'TEAM_06');
    const output = computeStandingsSnapshot(
        input({
            priorFixtures: [one, two],
            priorResults: [result(one, { homeScore: 2, awayScore: 0 }), result(two, { homeScore: 1, awayScore: 0 })],
        })
    );
    const states = new Map(output.diagnostic_table_state.map(row => [row.team_id, row]));
    assert.ok(states.get('TEAM_03').position < states.get('TEAM_05').position);
});

test('E: equal points and goal difference use goals scored', () => {
    const one = fixture('one', '2022-08-17T12:00:00.000Z', 'TEAM_03', 'TEAM_04');
    const two = fixture('two', '2022-08-18T12:00:00.000Z', 'TEAM_05', 'TEAM_06');
    const output = computeStandingsSnapshot(
        input({
            priorFixtures: [one, two],
            priorResults: [result(one, { homeScore: 2, awayScore: 0 }), result(two, { homeScore: 3, awayScore: 1 })],
        })
    );
    const states = new Map(output.diagnostic_table_state.map(row => [row.team_id, row]));
    assert.ok(states.get('TEAM_05').position < states.get('TEAM_03').position);
});

test('F: exact two-way tie uses 1,1,3 competition ranking with gaps', () => {
    const one = fixture('one', '2022-08-17T12:00:00.000Z', 'TEAM_03', 'TEAM_04');
    const two = fixture('two', '2022-08-18T12:00:00.000Z', 'TEAM_05', 'TEAM_06');
    const output = computeStandingsSnapshot(
        input({
            priorFixtures: [one, two],
            priorResults: [result(one), result(two)],
        })
    );
    const positions = output.diagnostic_table_state.map(row => row.position);
    assert.equal(positions.filter(position => position === 1).length, 2);
    assert.ok(positions.includes(3));
});

test('G: multi-way ties share position and leave rank gaps', () => {
    const fixtures = [
        fixture('one', '2022-08-15T12:00:00.000Z', 'TEAM_03', 'TEAM_04'),
        fixture('two', '2022-08-16T12:00:00.000Z', 'TEAM_05', 'TEAM_06'),
        fixture('three', '2022-08-17T12:00:00.000Z', 'TEAM_07', 'TEAM_08'),
    ];
    const output = computeStandingsSnapshot(
        input({ priorFixtures: fixtures, priorResults: fixtures.map(item => result(item)) })
    );
    const positions = output.diagnostic_table_state.map(row => row.position);
    assert.equal(positions.filter(position => position === 1).length, 3);
    assert.equal(positions.filter(position => position === 4).length, 14);
});

test('H: table position diff is home minus away', () => {
    const prior = fixture('prior', '2022-08-19T12:00:00.000Z', 'TEAM_03', 'TEAM_04');
    const output = computeStandingsSnapshot(
        input({
            targetHomeTeamId: 'TEAM_04',
            targetAwayTeamId: 'TEAM_03',
            priorFixtures: [prior],
            priorResults: [result(prior)],
        })
    );
    assert.equal(output.table_position_diff, output.home_table_position - output.away_table_position);
});

test('I: same-kickoff fixture is excluded', () => {
    const prior = fixture('same-time', '2022-08-19T11:00:00.000Z', 'TEAM_03', 'TEAM_04');
    const output = computeStandingsSnapshot(
        input({
            priorFixtures: [prior],
            priorResults: [result(prior, { actualEligibleEventTimeUtc: '2022-08-20T12:00:00.000Z' })],
        })
    );
    assert.deepEqual(output.source_event_ids_used, []);
    assert.deepEqual(output.diagnostics.same_kickoff_excluded_event_ids, ['same-time']);
});

test('J: future result is excluded', () => {
    const future = fixture('future', '2022-08-21T12:00:00.000Z', 'TEAM_03', 'TEAM_04');
    const output = computeStandingsSnapshot(input({ extraFixtures: [future], extraResults: [result(future)] }));
    assert.deepEqual(output.source_event_ids_used, []);
    assert.deepEqual(output.diagnostics.future_event_ids_excluded, ['future']);
});

test('K: target result is never consumed', () => {
    const base = input();
    const targetFixture = base.fixtures[0];
    base.results.push(result(targetFixture, { homeScore: 9, awayScore: 0 }));
    const output = computeStandingsSnapshot(base);
    assert.deepEqual(output.source_event_ids_used, []);
    assert.equal(output.diagnostics.target_match_result_excluded, true);
    assert.deepEqual(new Set(output.diagnostic_table_state.map(row => row.position)), new Set([1]));
});

test('L: postponed original scheduled before target but actual after target is excluded', () => {
    const postponed = fixture('postponed', '2022-08-19T12:00:00.000Z', 'TEAM_03', 'TEAM_04');
    const output = computeStandingsSnapshot(
        input({
            priorFixtures: [postponed],
            priorResults: [result(postponed, { actualEligibleEventTimeUtc: '2022-08-21T12:00:00.000Z' })],
        })
    );
    assert.deepEqual(output.source_event_ids_used, []);
    assert.deepEqual(output.diagnostics.future_event_ids_excluded, ['postponed']);
});

test('M: postponed actual event before target is eligible', () => {
    const postponed = fixture('postponed', '2022-08-21T12:00:00.000Z', 'TEAM_03', 'TEAM_04');
    const output = computeStandingsSnapshot(
        input({
            priorFixtures: [postponed],
            priorResults: [result(postponed, { actualEligibleEventTimeUtc: '2022-08-19T12:00:00.000Z' })],
        })
    );
    assert.deepEqual(output.source_event_ids_used, ['postponed']);
});

test('N: abandoned original does not contribute', () => {
    const abandoned = fixture('abandoned', '2022-08-19T12:00:00.000Z', 'TEAM_03', 'TEAM_04');
    const output = computeStandingsSnapshot(
        input({
            priorFixtures: [abandoned],
            priorResults: [
                result(abandoned, {
                    actualEligibleEventTimeUtc: null,
                    disposition: 'ABANDONED',
                    tableEligibility: 'NOT_ELIGIBLE',
                    finalityStatus: 'ABANDONED',
                    homeScore: 1,
                    awayScore: 1,
                }),
            ],
        })
    );
    assert.deepEqual(output.source_event_ids_used, []);
    assert.equal(output.diagnostic_table_state.find(row => row.team_id === 'TEAM_03').played, 0);
});

test('O: replay contributes once and rejects an eligible original', () => {
    const original = fixture('original', '2022-08-18T12:00:00.000Z', 'TEAM_03', 'TEAM_04');
    const replay = fixture('replay', '2022-08-19T12:00:00.000Z', 'TEAM_03', 'TEAM_04');
    const output = computeStandingsSnapshot(
        input({
            priorFixtures: [original, replay],
            priorResults: [
                result(original, {
                    actualEligibleEventTimeUtc: null,
                    disposition: 'ABANDONED',
                    tableEligibility: 'NOT_ELIGIBLE',
                    finalityStatus: 'ABANDONED',
                    homeScore: 1,
                    awayScore: 1,
                }),
                result(replay, { homeScore: 4, awayScore: 3, disposition: 'REPLAYED', replayOfMatchId: 'original' }),
            ],
        })
    );
    assert.deepEqual(output.source_event_ids_used, ['replay']);
    assert.equal(output.diagnostic_table_state.find(row => row.team_id === 'TEAM_03').wins, 1);

    const invalid = input({
        priorFixtures: [original, replay],
        priorResults: [result(original), result(replay, { disposition: 'REPLAYED', replayOfMatchId: 'original' })],
    });
    assertEngineError(() => computeStandingsSnapshot(invalid), 'FIXTURE_STATUS_CONFLICT');
});

test('P: awarded result without official table eligibility fails closed', () => {
    const awarded = fixture('awarded', '2022-08-19T12:00:00.000Z', 'TEAM_03', 'TEAM_04');
    const output = computeStandingsSnapshot(
        input({
            priorFixtures: [awarded],
            priorResults: [result(awarded, { disposition: 'AWARDED', tableEligibility: 'UNKNOWN' })],
        })
    );
    assertUnavailable(output, 'EXCEPTION_STATUS_UNPROVEN');
});

test('Q: unknown exception status fails closed', () => {
    const unknown = fixture('unknown', '2022-08-19T12:00:00.000Z', 'TEAM_03', 'TEAM_04');
    const output = computeStandingsSnapshot(
        input({
            priorFixtures: [unknown],
            priorResults: [
                result(unknown, {
                    disposition: 'UNKNOWN',
                    tableEligibility: 'UNKNOWN',
                    finalityStatus: 'UNKNOWN',
                    actualEligibleEventTimeUtc: null,
                    homeScore: null,
                    awayScore: null,
                }),
            ],
        })
    );
    assertUnavailable(output, 'EXCEPTION_STATUS_UNPROVEN');
});

test('R: exact-timestamp administrative deduction before target is applied', () => {
    const adjustment = exactAdjustment('deduction', 'TEAM_03', { kind: 'EXACT', atUtc: '2022-08-19T12:00:00.000Z' });
    const output = computeStandingsSnapshot(input({ administrativeAdjustments: [adjustment] }));
    const state = output.diagnostic_table_state.find(row => row.team_id === 'TEAM_03');
    assert.equal(state.admin_adjustment_points, -3);
    assert.equal(state.official_table_points, -3);
    assert.equal(state.position, 20);
});

test('S: exact-timestamp administrative deduction after target is not applied', () => {
    const adjustment = exactAdjustment('deduction', 'TEAM_03', { kind: 'EXACT', atUtc: '2022-08-21T12:00:00.000Z' });
    const output = computeStandingsSnapshot(input({ administrativeAdjustments: [adjustment] }));
    const state = output.diagnostic_table_state.find(row => row.team_id === 'TEAM_03');
    assert.equal(state.admin_adjustment_points, 0);
    assert.equal(state.position, 1);
});

test('T: an interval wholly before target is applied', () => {
    const adjustment = exactAdjustment('deduction', 'TEAM_03', {
        kind: 'INTERVAL',
        lowerBoundUtc: '2022-08-17T00:00:00.000Z',
        upperBoundUtc: '2022-08-18T00:00:00.000Z',
    });
    const output = computeStandingsSnapshot(input({ administrativeAdjustments: [adjustment] }));
    assert.equal(output.diagnostic_table_state.find(row => row.team_id === 'TEAM_03').admin_adjustment_points, -3);
});

test('U: an interval overlapping target makes the global snapshot unavailable', () => {
    const adjustment = exactAdjustment('appeal', 'TEAM_03', {
        kind: 'INTERVAL',
        lowerBoundUtc: '2022-08-20T00:00:00.000Z',
        upperBoundUtc: '2022-08-21T00:00:00.000Z',
    });
    const output = computeStandingsSnapshot(input({ administrativeAdjustments: [adjustment] }));
    assertUnavailable(output, 'ADMIN_ADJUSTMENT_EFFECTIVE_TIME_AMBIGUOUS');
});

test('V: an adjustment is never applied retroactively before its interval', () => {
    const adjustment = exactAdjustment('future-deduction', 'TEAM_03', {
        kind: 'INTERVAL',
        lowerBoundUtc: '2022-08-21T00:00:00.000Z',
        upperBoundUtc: '2022-08-22T00:00:00.000Z',
    });
    const output = computeStandingsSnapshot(input({ administrativeAdjustments: [adjustment] }));
    assert.deepEqual(output.administrative_adjustment_ids_applied, []);
});

test('W: a missing unrelated league prior result blocks the global snapshot', () => {
    const unrelated = fixture('unrelated', '2022-08-19T12:00:00.000Z', 'TEAM_03', 'TEAM_04');
    const output = computeStandingsSnapshot(input({ priorFixtures: [unrelated], priorResults: [] }));
    assertUnavailable(output, 'MISSING_PRIOR_RESULT_EVIDENCE');
});

test('X: duplicate canonical match ID with team conflict fails closed', () => {
    const prior = fixture('duplicate', '2022-08-19T12:00:00.000Z', 'TEAM_03', 'TEAM_04');
    const conflicting = result(prior);
    conflicting.homeTeamId = 'TEAM_05';
    assertEngineError(
        () => computeStandingsSnapshot(input({ priorFixtures: [prior], priorResults: [result(prior), conflicting] })),
        'RESULT_IDENTITY_CONFLICT'
    );
});

test('Y: duplicate canonical match ID with score conflict fails closed', () => {
    const prior = fixture('duplicate', '2022-08-19T12:00:00.000Z', 'TEAM_03', 'TEAM_04');
    assertEngineError(
        () =>
            computeStandingsSnapshot(
                input({ priorFixtures: [prior], priorResults: [result(prior), result(prior, { homeScore: 2 })] })
            ),
        'RESULT_SCORE_CONFLICT'
    );
});

test('Z: duplicate canonical match ID with event-time conflict fails closed', () => {
    const prior = fixture('duplicate', '2022-08-19T12:00:00.000Z', 'TEAM_03', 'TEAM_04');
    assertEngineError(
        () =>
            computeStandingsSnapshot(
                input({
                    priorFixtures: [prior],
                    priorResults: [
                        result(prior),
                        result(prior, { actualEligibleEventTimeUtc: '2022-08-19T13:00:00.000Z' }),
                    ],
                })
            ),
        'EVENT_TIME_CONFLICT'
    );
});

test('AA: result team identity conflict fails closed', () => {
    const prior = fixture('identity', '2022-08-19T12:00:00.000Z', 'TEAM_03', 'TEAM_04');
    const tampered = result(prior);
    tampered.awayTeamId = 'TEAM_05';
    assertEngineError(
        () => computeStandingsSnapshot(input({ priorFixtures: [prior], priorResults: [tampered] })),
        'RESULT_IDENTITY_CONFLICT'
    );
});

test('AB: incomplete team universe fails closed', () => {
    assertEngineError(
        () => computeStandingsSnapshot(input({ teamUniverse: TEAMS.slice(0, 19) })),
        'DEPENDENCY_UNAVAILABLE'
    );
});

test('AC: shuffled match and adjustment inputs produce identical output', () => {
    const fixtures = [
        fixture('one', '2022-08-17T12:00:00.000Z', 'TEAM_03', 'TEAM_04'),
        fixture('two', '2022-08-18T12:00:00.000Z', 'TEAM_05', 'TEAM_06'),
    ];
    const adjustments = [
        exactAdjustment('a', 'TEAM_03', { kind: 'EXACT', atUtc: '2022-08-16T12:00:00.000Z' }),
        exactAdjustment('b', 'TEAM_05', { kind: 'EXACT', atUtc: '2022-08-16T12:00:00.000Z' }),
    ];
    const baseline = computeStandingsSnapshot(
        input({
            priorFixtures: fixtures,
            priorResults: fixtures.map(item => result(item)),
            administrativeAdjustments: adjustments,
        })
    );
    const shuffled = computeStandingsSnapshot(
        input({
            priorFixtures: [...fixtures].reverse(),
            priorResults: fixtures.map(item => result(item)).reverse(),
            administrativeAdjustments: [...adjustments].reverse(),
        })
    );
    assert.deepEqual(shuffled, baseline);
});

test('AD: provider/display order cannot become a tie breaker', () => {
    const fixtures = [
        fixture('one', '2022-08-17T12:00:00.000Z', 'TEAM_03', 'TEAM_04'),
        fixture('two', '2022-08-18T12:00:00.000Z', 'TEAM_05', 'TEAM_06'),
    ];
    const baseline = computeStandingsSnapshot(
        input({ priorFixtures: fixtures, priorResults: fixtures.map(item => result(item)) })
    );
    const reordered = computeStandingsSnapshot(
        input({ priorFixtures: [...fixtures].reverse(), priorResults: fixtures.map(item => result(item)).reverse() })
    );
    assert.equal(baseline.table_position_diff, reordered.table_position_diff);
    assert.deepEqual(
        baseline.diagnostic_table_state.map(row => [row.team_id, row.position]),
        reordered.diagnostic_table_state.map(row => [row.team_id, row.position])
    );
});

test('AE: null score is unavailable and never coerced to 0-0', () => {
    const prior = fixture('null-score', '2022-08-19T12:00:00.000Z', 'TEAM_03', 'TEAM_04');
    const output = computeStandingsSnapshot(
        input({ priorFixtures: [prior], priorResults: [result(prior, { homeScore: null, awayScore: null })] })
    );
    assertUnavailable(output, 'MISSING_PRIOR_RESULT_EVIDENCE');
});

test('AF: previous-season results cannot bleed into the frozen season', () => {
    const prior = fixture('previous', '2021-08-19T12:00:00.000Z', 'TEAM_03', 'TEAM_04');
    const previousResult = result(prior);
    previousResult.season = '2021/2022';
    assertEngineError(
        () => computeStandingsSnapshot(input({ priorFixtures: [prior], priorResults: [previousResult] })),
        'DEPENDENCY_UNAVAILABLE'
    );
});

test('AG: existing points feature semantics are not part of the standings projection', () => {
    const output = computeStandingsSnapshot(input());
    const registry = JSON.parse(fs.readFileSync(REGISTRY_PATH, 'utf8'));
    assert.deepEqual(registry.decision_boundaries.standings.contract.feature_bindings, [
        'home_table_position',
        'away_table_position',
        'table_position_diff',
    ]);
    assert.equal(Object.hasOwn(output, 'home_points'), false);
    assert.equal(Object.hasOwn(output, 'away_points'), false);
    assert.equal(Object.hasOwn(output, 'points_diff'), false);
});

test('contract binding rejects wrong contract ID', () => {
    const registry = JSON.parse(fs.readFileSync(REGISTRY_PATH, 'utf8'));
    registry.decision_boundaries.standings.contract.contract_id = 'standings/premier-league-point-in-time/v2';
    assertEngineError(() => bindFrozenStandingsContract(registry), 'SCHEMA_MISMATCH');
});

test('contract binding rejects wrong version', () => {
    const registry = JSON.parse(fs.readFileSync(REGISTRY_PATH, 'utf8'));
    registry.decision_boundaries.standings.contract.version = 'v2';
    assertEngineError(() => bindFrozenStandingsContract(registry), 'SCHEMA_MISMATCH');
});

test('contract binding rejects wrong ranking order', () => {
    const registry = JSON.parse(fs.readFileSync(REGISTRY_PATH, 'utf8'));
    registry.decision_boundaries.standings.contract.ordering_rules = ['goal_difference', 'points', 'goals_scored'];
    assertEngineError(() => bindFrozenStandingsContract(registry), 'SCHEMA_MISMATCH');
});

test('contract binding rejects wrong tie mode', () => {
    const registry = JSON.parse(fs.readFileSync(REGISTRY_PATH, 'utf8'));
    registry.decision_boundaries.standings.contract.tie_representation.mode = 'DENSE_RANK';
    assertEngineError(() => bindFrozenStandingsContract(registry), 'SCHEMA_MISMATCH');
});

test('contract binding rejects wrong cutoff', () => {
    const registry = JSON.parse(fs.readFileSync(REGISTRY_PATH, 'utf8'));
    registry.decision_boundaries.standings.contract.strict_cutoff_rule = 'source_kickoff <= target_kickoff';
    assertEngineError(() => bindFrozenStandingsContract(registry), 'SCHEMA_MISMATCH');
});

test('contract binding rejects wrong table position diff orientation', () => {
    const registry = JSON.parse(fs.readFileSync(REGISTRY_PATH, 'utf8'));
    registry.decision_boundaries.standings.contract.table_position_diff_rule.orientation =
        'AWAY_POSITION_MINUS_HOME_POSITION';
    assertEngineError(() => bindFrozenStandingsContract(registry), 'SCHEMA_MISMATCH');
});

test('contract binding rejects rule history closure being reopened', () => {
    const registry = JSON.parse(fs.readFileSync(REGISTRY_PATH, 'utf8'));
    registry.decision_boundaries.standings.rule_history_closure_required = 'YES';
    assertEngineError(() => bindFrozenStandingsContract(registry), 'SCHEMA_MISMATCH');
});
