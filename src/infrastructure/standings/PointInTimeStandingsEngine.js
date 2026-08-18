'use strict';

/* eslint-disable max-lines -- 一个纯语义引擎必须保持合同、校验、累计和投影的同一边界。 */
/* eslint-disable complexity -- 严格合同校验与 fail-closed 时间状态机必须保持在同一语义边界。 */

// lifecycle: permanent
// 纯内存、确定性的 Premier League v1 standings 语义引擎。
// 本文件不得读取文件、网络、数据库、环境变量或当前时间；历史与未来适配器
// 只能把已验证证据转换为下方的 normalized input。

const { sha256Text, stableStringify } = require('../canonical/StableValue');
const {
    assertStandingsContractBinding,
    STANDINGS_CONTRACT_ID,
    STANDINGS_CONTRACT_VERSION,
} = require('./StandingsContractBinding');
const {
    STANDINGS_ASOF_ENGINE_INPUT_CONTRACT_ID,
    STANDINGS_ASOF_ENGINE_INPUT_CONTRACT_VERSION,
    validateStandingsAsOfEngineInput,
} = require('./StandingsAsOfEngineInputContract');

const STANDINGS_ASOF_ENGINE_CONSUMER_CONTRACT_ID = 'standings-asof-engine-consumer/v1';
const STANDINGS_ASOF_ENGINE_CONSUMER_CONTRACT_VERSION = 'v1';
const STANDINGS_ASOF_ENGINE_CONSUMER_CONTRACT_STATUS = 'FROZEN';
const LEGACY_KICKOFF_EXCLUSIVE = Object.freeze({
    id: 'KICKOFF_EXCLUSIVE',
    resultBoundary: 'STRICT_LT_TARGET_KICKOFF',
    adjustmentBoundary: 'STRICT_LT_TARGET_KICKOFF',
});
const MODEL_DECISION_TIME_INCLUSIVE = Object.freeze({
    id: 'MODEL_DECISION_TIME_INCLUSIVE',
    resultBoundary: 'LTE_MODEL_DECISION_TIME',
    adjustmentBoundary: 'LTE_MODEL_DECISION_TIME',
});

// This is the in-process identity of the implementation that is actually
// imported and invoked. It intentionally contains no Git/source-commit claim;
// repository provenance is proven separately by the external audit boundary.
const STANDINGS_ENGINE_IMPLEMENTATION = Object.freeze({
    implementation_id: 'PointInTimeStandingsEngine',
    implementation_version: STANDINGS_CONTRACT_VERSION,
    contract_id: STANDINGS_CONTRACT_ID,
});
const STANDINGS_ENGINE_IMPLEMENTATION_IDENTITY_DIGEST = sha256Text(stableStringify(STANDINGS_ENGINE_IMPLEMENTATION));
const STANDINGS_ENGINE_IMPLEMENTATION_BINDING = Object.freeze({
    ...STANDINGS_ENGINE_IMPLEMENTATION,
    implementation_identity_digest: STANDINGS_ENGINE_IMPLEMENTATION_IDENTITY_DIGEST,
});

const UTC_TIMESTAMP = /^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d{3})?Z$/;
const TOP_LEVEL_FIELDS = new Set([
    'contractBinding',
    'competition',
    'leagueId',
    'season',
    'teamUniverse',
    'fixtures',
    'results',
    'administrativeAdjustments',
    'target',
]);
const TEAM_FIELDS = new Set(['teamId']);
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
    'replayOfMatchId',
]);
const ADJUSTMENT_FIELDS = new Set([
    'adjustmentId',
    'competition',
    'leagueId',
    'season',
    'teamId',
    'delta',
    'effectiveTime',
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
const DISPOSITIONS = new Set(['COMPLETED', 'REPLAYED', 'ABANDONED', 'VOID', 'AWARDED', 'UNKNOWN']);
const TABLE_ELIGIBILITY = new Set(['ELIGIBLE', 'NOT_ELIGIBLE', 'UNKNOWN']);
const FINALITY_STATUSES = new Set(['FINAL', 'ABANDONED', 'VOID', 'UNKNOWN']);

class StandingsEngineError extends Error {
    constructor(message, code = 'DEPENDENCY_UNAVAILABLE') {
        super(message);
        this.name = 'StandingsEngineError';
        this.code = code;
        this.reasonCode = code;
    }
}

function isPlainObject(value) {
    return value !== null && typeof value === 'object' && !Array.isArray(value);
}

function fail(message, code) {
    throw new StandingsEngineError(message, code);
}

function assertPlainObject(value, label) {
    if (!isPlainObject(value)) fail(`${label} must be an object`, 'DEPENDENCY_UNAVAILABLE');
    return value;
}

function assertKnownKeys(value, allowed, label) {
    for (const key of Object.keys(value)) {
        if (!allowed.has(key)) fail(`${label} contains unsupported field ${key}`, 'DEPENDENCY_UNAVAILABLE');
    }
}

function assertText(value, label) {
    if (typeof value !== 'string' || value.trim() === '') {
        fail(`${label} must be non-empty text`, 'DEPENDENCY_UNAVAILABLE');
    }
    return value;
}

function assertInteger(value, label, minimum, allowNull = false) {
    if (allowNull && value === null) return null;
    if (!Number.isSafeInteger(value) || (minimum !== undefined && value < minimum)) {
        fail(`${label} must be a safe integer`, 'RESULT_SCORE_CONFLICT');
    }
    return value;
}

function parseUtc(value, label, allowNull = false) {
    if (allowNull && value === null) return null;
    if (typeof value !== 'string' || !UTC_TIMESTAMP.test(value)) {
        fail(`${label} must be an absolute UTC timestamp`, 'EVENT_TIME_CONFLICT');
    }
    const milliseconds = Date.parse(value);
    if (!Number.isFinite(milliseconds)) fail(`${label} is not a valid UTC timestamp`, 'EVENT_TIME_CONFLICT');
    return milliseconds;
}

function assertLineage(value, label) {
    assertPlainObject(value, label);
    if (Object.keys(value).length === 0) fail(`${label} must contain evidence identity`, 'DEPENDENCY_UNAVAILABLE');
    return value;
}

function assertCompetitionIdentity(row, input, label) {
    if (row.competition !== input.competition || row.leagueId !== input.leagueId || row.season !== input.season) {
        fail(`${label} is outside the bound competition-season`, 'DEPENDENCY_UNAVAILABLE');
    }
}

function validateTeamUniverse(value, binding) {
    if (!Array.isArray(value) || value.length !== binding.team_count) {
        fail('team universe is incomplete', 'DEPENDENCY_UNAVAILABLE');
    }
    const teamIds = [];
    for (const [index, entry] of value.entries()) {
        if (typeof entry === 'string') {
            assertText(entry, `teamUniverse[${index}]`);
            teamIds.push(entry);
            continue;
        }
        const team = assertPlainObject(entry, `teamUniverse[${index}]`);
        assertKnownKeys(team, TEAM_FIELDS, `teamUniverse[${index}]`);
        assertText(team.teamId, `teamUniverse[${index}].teamId`);
        teamIds.push(team.teamId);
    }
    if (new Set(teamIds).size !== teamIds.length) {
        fail('team universe contains duplicate identities', 'DEPENDENCY_UNAVAILABLE');
    }
    return new Set(teamIds);
}

function validateFixture(fixture, input, teamIds, index) {
    const row = assertPlainObject(fixture, `fixtures[${index}]`);
    assertKnownKeys(row, FIXTURE_FIELDS, `fixtures[${index}]`);
    for (const field of ['canonicalMatchId', 'competition', 'season', 'homeTeamId', 'awayTeamId']) {
        assertText(row[field], `fixtures[${index}].${field}`);
    }
    if (!Number.isSafeInteger(row.leagueId)) fail(`fixtures[${index}].leagueId is malformed`, 'DEPENDENCY_UNAVAILABLE');
    assertCompetitionIdentity(row, input, `fixtures[${index}]`);
    parseUtc(row.scheduledKickoffUtc, `fixtures[${index}].scheduledKickoffUtc`);
    assertLineage(row.sourceLineage, `fixtures[${index}].sourceLineage`);
    if (row.homeTeamId === row.awayTeamId || !teamIds.has(row.homeTeamId) || !teamIds.has(row.awayTeamId)) {
        fail(`fixtures[${index}] has invalid team identity`, 'RESULT_IDENTITY_CONFLICT');
    }
    return { ...row };
}

function validateScorePair(row, index) {
    const homeNull = row.homeScore === null;
    const awayNull = row.awayScore === null;
    if (homeNull !== awayNull) fail(`results[${index}] has a partial score`, 'RESULT_SCORE_CONFLICT');
    if (!homeNull) {
        assertInteger(row.homeScore, `results[${index}].homeScore`, 0);
        assertInteger(row.awayScore, `results[${index}].awayScore`, 0);
    }
}

function validateResult(result, input, teamIds, index) {
    const row = assertPlainObject(result, `results[${index}]`);
    assertKnownKeys(row, RESULT_FIELDS, `results[${index}]`);
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
        assertText(row[field], `results[${index}].${field}`);
    }
    if (!Number.isSafeInteger(row.leagueId)) fail(`results[${index}].leagueId is malformed`, 'DEPENDENCY_UNAVAILABLE');
    assertCompetitionIdentity(row, input, `results[${index}]`);
    if (!DISPOSITIONS.has(row.disposition)) {
        fail(`results[${index}].disposition is unknown`, 'EXCEPTION_STATUS_UNPROVEN');
    }
    if (!TABLE_ELIGIBILITY.has(row.tableEligibility)) {
        fail(`results[${index}].tableEligibility is unknown`, 'FIXTURE_STATUS_CONFLICT');
    }
    if (!FINALITY_STATUSES.has(row.finalityStatus)) {
        fail(`results[${index}].finalityStatus is unknown`, 'EXCEPTION_STATUS_UNPROVEN');
    }
    parseUtc(row.actualEligibleEventTimeUtc, `results[${index}].actualEligibleEventTimeUtc`, true);
    validateScorePair(row, index);
    assertLineage(row.sourceLineage, `results[${index}].sourceLineage`);
    if (row.replayOfMatchId !== undefined && row.replayOfMatchId !== null) {
        assertText(row.replayOfMatchId, `results[${index}].replayOfMatchId`);
    }
    if (row.homeTeamId === row.awayTeamId || !teamIds.has(row.homeTeamId) || !teamIds.has(row.awayTeamId)) {
        fail(`results[${index}] has invalid team identity`, 'RESULT_IDENTITY_CONFLICT');
    }
    if (row.disposition === 'COMPLETED' && row.tableEligibility !== 'ELIGIBLE') {
        fail(`results[${index}] completed status is not table eligible`, 'FIXTURE_STATUS_CONFLICT');
    }
    if (row.disposition === 'REPLAYED' && row.tableEligibility !== 'ELIGIBLE') {
        fail(`results[${index}] replay status is not table eligible`, 'FIXTURE_STATUS_CONFLICT');
    }
    if (row.disposition === 'ABANDONED' && row.tableEligibility !== 'NOT_ELIGIBLE') {
        fail(`results[${index}] abandoned status is table eligible`, 'FIXTURE_STATUS_CONFLICT');
    }
    if (row.disposition === 'VOID' && row.tableEligibility !== 'NOT_ELIGIBLE') {
        fail(`results[${index}] void status is table eligible`, 'FIXTURE_STATUS_CONFLICT');
    }
    return { ...row };
}

function validateEffectiveTime(value, index) {
    const effectiveTime = assertPlainObject(value, `administrativeAdjustments[${index}].effectiveTime`);
    if (effectiveTime.kind === 'EXACT') {
        if (Object.keys(effectiveTime).length !== 2 || !Object.hasOwn(effectiveTime, 'atUtc')) {
            fail(`administrativeAdjustments[${index}].effectiveTime is malformed`, 'ADMIN_ADJUSTMENT_CONFLICT');
        }
        const atMs = parseUtc(effectiveTime.atUtc, `administrativeAdjustments[${index}].effectiveTime.atUtc`);
        return { kind: effectiveTime.kind, atUtc: effectiveTime.atUtc, atMs };
    }
    if (effectiveTime.kind === 'INTERVAL') {
        if (
            Object.keys(effectiveTime).length !== 3 ||
            !Object.hasOwn(effectiveTime, 'lowerBoundUtc') ||
            !Object.hasOwn(effectiveTime, 'upperBoundUtc')
        ) {
            fail(`administrativeAdjustments[${index}].effectiveTime is malformed`, 'ADMIN_ADJUSTMENT_CONFLICT');
        }
        const lowerMs = parseUtc(
            effectiveTime.lowerBoundUtc,
            `administrativeAdjustments[${index}].effectiveTime.lowerBoundUtc`
        );
        const upperMs = parseUtc(
            effectiveTime.upperBoundUtc,
            `administrativeAdjustments[${index}].effectiveTime.upperBoundUtc`
        );
        if (lowerMs >= upperMs) {
            fail(`administrativeAdjustments[${index}].effectiveTime interval is inverted`, 'ADMIN_ADJUSTMENT_CONFLICT');
        }
        return {
            kind: effectiveTime.kind,
            lowerBoundUtc: effectiveTime.lowerBoundUtc,
            upperBoundUtc: effectiveTime.upperBoundUtc,
            lowerMs,
            upperMs,
        };
    }
    fail(`administrativeAdjustments[${index}].effectiveTime.kind is unknown`, 'ADMIN_ADJUSTMENT_CONFLICT');
}

function validateAdjustment(adjustment, input, teamIds, index) {
    const row = assertPlainObject(adjustment, `administrativeAdjustments[${index}]`);
    assertKnownKeys(row, ADJUSTMENT_FIELDS, `administrativeAdjustments[${index}]`);
    for (const field of ['adjustmentId', 'competition', 'season', 'teamId']) {
        assertText(row[field], `administrativeAdjustments[${index}].${field}`);
    }
    if (!Number.isSafeInteger(row.leagueId)) {
        fail(`administrativeAdjustments[${index}].leagueId is malformed`, 'ADMIN_ADJUSTMENT_CONFLICT');
    }
    assertCompetitionIdentity(row, input, `administrativeAdjustments[${index}]`);
    assertInteger(row.delta, `administrativeAdjustments[${index}].delta`);
    if (row.delta === 0) fail(`administrativeAdjustments[${index}].delta cannot be zero`, 'ADMIN_ADJUSTMENT_CONFLICT');
    assertLineage(row.sourceLineage, `administrativeAdjustments[${index}].sourceLineage`);
    if (!teamIds.has(row.teamId)) {
        fail(`administrativeAdjustments[${index}] references an unknown team`, 'ADMIN_ADJUSTMENT_CONFLICT');
    }
    return { ...row, effectiveTime: validateEffectiveTime(row.effectiveTime, index) };
}

function validateTarget(target, input, teamIds) {
    const row = assertPlainObject(target, 'target');
    assertKnownKeys(row, TARGET_FIELDS, 'target');
    for (const field of ['canonicalMatchId', 'competition', 'season', 'homeTeamId', 'awayTeamId']) {
        assertText(row[field], `target.${field}`);
    }
    if (!Number.isSafeInteger(row.leagueId)) fail('target.leagueId is malformed', 'DEPENDENCY_UNAVAILABLE');
    assertCompetitionIdentity(row, input, 'target');
    parseUtc(row.targetKickoffUtc, 'target.targetKickoffUtc');
    assertLineage(row.sourceLineage, 'target.sourceLineage');
    if (row.homeTeamId === row.awayTeamId || !teamIds.has(row.homeTeamId) || !teamIds.has(row.awayTeamId)) {
        fail('target has invalid team identity', 'RESULT_IDENTITY_CONFLICT');
    }
    return { ...row };
}

function duplicateConflict(existing, current, label) {
    if (existing.homeScore !== current.homeScore || existing.awayScore !== current.awayScore) {
        return { message: `${label} has conflicting scores`, code: 'RESULT_SCORE_CONFLICT' };
    }
    if (existing.actualEligibleEventTimeUtc !== current.actualEligibleEventTimeUtc) {
        return { message: `${label} has conflicting event times`, code: 'EVENT_TIME_CONFLICT' };
    }
    if (
        existing.homeTeamId !== current.homeTeamId ||
        existing.awayTeamId !== current.awayTeamId ||
        existing.competition !== current.competition ||
        existing.season !== current.season
    ) {
        return { message: `${label} has conflicting team identity`, code: 'RESULT_IDENTITY_CONFLICT' };
    }
    if (existing.disposition !== current.disposition || existing.tableEligibility !== current.tableEligibility) {
        return { message: `${label} has conflicting fixture status`, code: 'FIXTURE_STATUS_CONFLICT' };
    }
    return { message: `${label} is duplicated`, code: 'RESULT_IDENTITY_CONFLICT' };
}

function indexUnique(rows, key, label) {
    const indexed = new Map();
    for (const row of rows) {
        const value = row[key];
        if (indexed.has(value)) {
            if (key === 'adjustmentId') fail(`${label} ${value} is duplicated`, 'ADMIN_ADJUSTMENT_CONFLICT');
            const conflict = duplicateConflict(indexed.get(value), row, label);
            fail(conflict.message, conflict.code);
        }
        indexed.set(value, row);
    }
    return indexed;
}

function compareById(left, right, field) {
    return left[field].localeCompare(right[field]);
}

function canonicalInput(input, fixtures, results, adjustments, target, teamIds) {
    return {
        contract_id: input.contractBinding.contract_id,
        contract_version: input.contractBinding.version,
        competition: input.competition,
        league_id: input.leagueId,
        season: input.season,
        team_universe: [...teamIds].sort((left, right) => left.localeCompare(right)),
        fixtures: [...fixtures].sort((left, right) => compareById(left, right, 'canonicalMatchId')),
        results: [...results].sort((left, right) => compareById(left, right, 'canonicalMatchId')),
        administrative_adjustments: [...adjustments].sort((left, right) => compareById(left, right, 'adjustmentId')),
        target,
    };
}

function prepareInput(input, { modelDecisionMilliseconds = null } = {}) {
    const value = assertPlainObject(input, 'standings engine input');
    assertKnownKeys(value, TOP_LEVEL_FIELDS, 'standings engine input');
    const binding = assertStandingsContractBinding(value.contractBinding);
    for (const field of ['competition', 'season']) assertText(value[field], `input.${field}`);
    if (value.competition !== binding.competition || !binding.frozen_seasons.includes(value.season)) {
        fail('input competition or season is not bound to the frozen contract', 'RULE_VERSION_UNPROVEN');
    }
    if (value.leagueId !== binding.league_id) {
        fail('input league identity is not bound to the frozen contract', 'DEPENDENCY_UNAVAILABLE');
    }
    const teamIds = validateTeamUniverse(value.teamUniverse, binding);
    if (!Array.isArray(value.fixtures) || value.fixtures.length === 0) {
        fail('fixture schedule is required', 'DEPENDENCY_UNAVAILABLE');
    }
    if (!Array.isArray(value.results)) fail('result evidence array is required', 'DEPENDENCY_UNAVAILABLE');
    if (!Array.isArray(value.administrativeAdjustments)) {
        fail('administrative adjustment array is required', 'DEPENDENCY_UNAVAILABLE');
    }
    const fixtures = value.fixtures.map((row, index) => validateFixture(row, value, teamIds, index));
    const fixtureById = indexUnique(fixtures, 'canonicalMatchId', 'fixture schedule');
    const results = value.results.map((row, index) => validateResult(row, value, teamIds, index));
    const resultsById = indexUnique(results, 'canonicalMatchId', 'result evidence');
    for (const result of results) {
        const fixture = fixtureById.get(result.canonicalMatchId);
        if (!fixture) fail(`result ${result.canonicalMatchId} has no canonical fixture`, 'RESULT_IDENTITY_CONFLICT');
        if (fixture.homeTeamId !== result.homeTeamId || fixture.awayTeamId !== result.awayTeamId) {
            fail(`result ${result.canonicalMatchId} disagrees with fixture team identity`, 'RESULT_IDENTITY_CONFLICT');
        }
    }
    for (const result of results) {
        if (result.replayOfMatchId === undefined || result.replayOfMatchId === null) continue;
        const original = resultsById.get(result.replayOfMatchId);
        if (!original || !fixtureById.has(result.replayOfMatchId)) {
            fail(`replay ${result.canonicalMatchId} references an unknown original`, 'FIXTURE_STATUS_CONFLICT');
        }
        if (original.tableEligibility === 'ELIGIBLE') {
            fail(
                `replay ${result.canonicalMatchId} would double count an eligible original`,
                'FIXTURE_STATUS_CONFLICT'
            );
        }
    }
    const adjustments = value.administrativeAdjustments.map((row, index) =>
        validateAdjustment(row, value, teamIds, index)
    );
    const adjustmentsById = indexUnique(adjustments, 'adjustmentId', 'administrative adjustment evidence');
    const target = validateTarget(value.target, value, teamIds);
    const targetFixture = fixtureById.get(target.canonicalMatchId);
    if (!targetFixture) fail('target has no canonical fixture', 'RESULT_IDENTITY_CONFLICT');
    if (targetFixture.homeTeamId !== target.homeTeamId || targetFixture.awayTeamId !== target.awayTeamId) {
        fail('target disagrees with canonical fixture team identity', 'RESULT_IDENTITY_CONFLICT');
    }
    return {
        input: value,
        binding,
        teamIds,
        fixtures,
        fixtureById,
        results,
        resultsById,
        adjustments,
        adjustmentsById,
        target,
        targetMilliseconds: parseUtc(target.targetKickoffUtc, 'target.targetKickoffUtc'),
        modelDecisionMilliseconds,
        inputDigest: sha256Text(
            stableStringify(canonicalInput(value, fixtures, results, adjustments, target, teamIds))
        ),
    };
}

function initialTable(teamIds) {
    return new Map(
        [...teamIds].map(teamId => [
            teamId,
            {
                team_id: teamId,
                played: 0,
                wins: 0,
                draws: 0,
                losses: 0,
                goals_for: 0,
                goals_against: 0,
                goal_difference: 0,
                match_earned_points: 0,
                admin_adjustment_points: 0,
                official_table_points: 0,
            },
        ])
    );
}

function applyResult(table, result) {
    if (result.homeScore === null || result.awayScore === null) return false;
    const home = table.get(result.homeTeamId);
    const away = table.get(result.awayTeamId);
    home.played += 1;
    away.played += 1;
    home.goals_for += result.homeScore;
    home.goals_against += result.awayScore;
    away.goals_for += result.awayScore;
    away.goals_against += result.homeScore;
    if (result.homeScore > result.awayScore) {
        home.wins += 1;
        away.losses += 1;
        home.match_earned_points += 3;
    } else if (result.homeScore < result.awayScore) {
        away.wins += 1;
        home.losses += 1;
        away.match_earned_points += 3;
    } else {
        home.draws += 1;
        away.draws += 1;
        home.match_earned_points += 1;
        away.match_earned_points += 1;
    }
    return true;
}

function setDerivedState(table) {
    for (const state of table.values()) {
        state.goal_difference = state.goals_for - state.goals_against;
        state.official_table_points = state.match_earned_points + state.admin_adjustment_points;
    }
}

function strictlyAhead(left, right) {
    if (left.official_table_points !== right.official_table_points) {
        return left.official_table_points > right.official_table_points;
    }
    if (left.goal_difference !== right.goal_difference) return left.goal_difference > right.goal_difference;
    return left.goals_for > right.goals_for;
}

function assignPositions(table) {
    const states = [...table.values()];
    for (const state of states) {
        state.position = 1 + states.filter(other => strictlyAhead(other, state)).length;
    }
    return states;
}

function evaluateAdjustment(adjustment, evaluationMilliseconds, boundaryPolicy) {
    if (adjustment.effectiveTime.kind === 'EXACT') {
        const effective =
            boundaryPolicy.adjustmentBoundary === 'LTE_MODEL_DECISION_TIME'
                ? adjustment.effectiveTime.atMs <= evaluationMilliseconds
                : adjustment.effectiveTime.atMs < evaluationMilliseconds;
        return effective ? 'EFFECTIVE' : 'NOT_EFFECTIVE';
    }
    if (evaluationMilliseconds < adjustment.effectiveTime.lowerMs) return 'NOT_EFFECTIVE';
    if (evaluationMilliseconds >= adjustment.effectiveTime.upperMs) return 'EFFECTIVE';
    return 'AMBIGUOUS';
}

function makeProjectionDigest(prepared, sourceEventIds, appliedAdjustmentIds) {
    return sha256Text(
        stableStringify({
            input_digest: prepared.inputDigest,
            source_event_ids_used: [...sourceEventIds].sort((left, right) => left.localeCompare(right)),
            administrative_adjustment_ids_applied: [...appliedAdjustmentIds].sort((left, right) =>
                left.localeCompare(right)
            ),
        })
    );
}

function baseOutput(prepared, status, reasonCodes, sourceEventIds, consideredAdjustmentIds, appliedAdjustmentIds) {
    const { target, binding, inputDigest } = prepared;
    return {
        snapshot_status: status,
        target_match_id: target.canonicalMatchId,
        target_kickoff_utc: target.targetKickoffUtc,
        home_team_id: target.homeTeamId,
        away_team_id: target.awayTeamId,
        competition: binding.competition,
        league_id: binding.league_id,
        season: target.season,
        contract_id: binding.contract_id,
        contract_version: binding.version,
        home_table_position: null,
        away_table_position: null,
        table_position_diff: null,
        unavailable_reason_codes: [...new Set(reasonCodes)].sort((left, right) => left.localeCompare(right)),
        source_event_ids_used: [...sourceEventIds].sort((left, right) => left.localeCompare(right)),
        administrative_adjustment_ids_considered: [...consideredAdjustmentIds].sort((left, right) =>
            left.localeCompare(right)
        ),
        administrative_adjustment_ids_applied: [...appliedAdjustmentIds].sort((left, right) =>
            left.localeCompare(right)
        ),
        max_eligible_source_event_time_utc: null,
        provenance_digest: makeProjectionDigest(prepared, sourceEventIds, appliedAdjustmentIds),
        input_digest: inputDigest,
        diagnostic_table_state: null,
        diagnostics: {
            target_match_result_excluded: true,
            same_kickoff_excluded_event_ids: [],
            future_event_ids_excluded: [],
            replay_double_count: 0,
            original_scheduled_date_used_as_event_time_count: 0,
        },
    };
}

function computePreparedStandings(prepared, boundaryPolicy) {
    const evaluationMilliseconds =
        boundaryPolicy === LEGACY_KICKOFF_EXCLUSIVE ? prepared.targetMilliseconds : prepared.modelDecisionMilliseconds;
    if (!Number.isFinite(evaluationMilliseconds)) {
        fail('standings evaluation boundary is unavailable', 'DEPENDENCY_UNAVAILABLE');
    }
    const { binding, target, fixtures, resultsById, adjustments, teamIds, inputDigest } = prepared;
    const blockers = new Set();
    const sourceEventIds = new Set();
    const sameKickoffExcluded = [];
    const futureExcluded = [];
    const table = initialTable(teamIds);
    let maxEligibleMilliseconds = null;

    for (const fixture of fixtures) {
        if (fixture.canonicalMatchId === target.canonicalMatchId) continue;
        const scheduledMilliseconds = parseUtc(fixture.scheduledKickoffUtc, 'fixture scheduled kickoff');
        const result = resultsById.get(fixture.canonicalMatchId);
        if (!result) {
            if (scheduledMilliseconds < evaluationMilliseconds) blockers.add('MISSING_PRIOR_RESULT_EVIDENCE');
            continue;
        }

        if (result.disposition === 'ABANDONED' || result.disposition === 'VOID') continue;

        const actualMilliseconds = parseUtc(
            result.actualEligibleEventTimeUtc,
            `result ${result.canonicalMatchId}.actualEligibleEventTimeUtc`,
            true
        );
        if (result.disposition === 'UNKNOWN') {
            if (
                actualMilliseconds === null ||
                actualMilliseconds < evaluationMilliseconds ||
                scheduledMilliseconds < evaluationMilliseconds
            ) {
                blockers.add('EXCEPTION_STATUS_UNPROVEN');
            }
            continue;
        }
        if (result.disposition === 'AWARDED' && result.tableEligibility === 'UNKNOWN') {
            if (
                actualMilliseconds === null ||
                actualMilliseconds < evaluationMilliseconds ||
                scheduledMilliseconds < evaluationMilliseconds
            ) {
                blockers.add('EXCEPTION_STATUS_UNPROVEN');
            }
            continue;
        }
        if (result.disposition === 'AWARDED' && result.tableEligibility === 'NOT_ELIGIBLE') continue;
        if (result.tableEligibility !== 'ELIGIBLE') {
            blockers.add('EXCEPTION_STATUS_UNPROVEN');
            continue;
        }
        if (result.finalityStatus !== 'FINAL') {
            if (
                actualMilliseconds === null ||
                actualMilliseconds < evaluationMilliseconds ||
                scheduledMilliseconds < evaluationMilliseconds
            ) {
                blockers.add('EXCEPTION_STATUS_UNPROVEN');
            }
            continue;
        }
        if (actualMilliseconds === null) {
            blockers.add('POSTPONED_EVENT_TIME_UNPROVEN');
            continue;
        }
        if (
            actualMilliseconds === evaluationMilliseconds &&
            boundaryPolicy.resultBoundary === 'STRICT_LT_TARGET_KICKOFF'
        ) {
            sameKickoffExcluded.push(result.canonicalMatchId);
            continue;
        }
        if (actualMilliseconds > evaluationMilliseconds) {
            futureExcluded.push(result.canonicalMatchId);
            continue;
        }
        if (result.homeScore === null || result.awayScore === null) {
            blockers.add('MISSING_PRIOR_RESULT_EVIDENCE');
            continue;
        }
        if (applyResult(table, result)) {
            sourceEventIds.add(result.canonicalMatchId);
            if (maxEligibleMilliseconds === null || actualMilliseconds > maxEligibleMilliseconds) {
                maxEligibleMilliseconds = actualMilliseconds;
            }
        }
    }

    const consideredAdjustmentIds = adjustments.map(row => row.adjustmentId);
    const appliedAdjustmentIds = [];
    for (const adjustment of adjustments) {
        const status = evaluateAdjustment(adjustment, evaluationMilliseconds, boundaryPolicy);
        if (status === 'AMBIGUOUS') {
            blockers.add('ADMIN_ADJUSTMENT_EFFECTIVE_TIME_AMBIGUOUS');
            continue;
        }
        if (status === 'EFFECTIVE') {
            table.get(adjustment.teamId).admin_adjustment_points += adjustment.delta;
            appliedAdjustmentIds.push(adjustment.adjustmentId);
        }
    }

    const output = baseOutput(
        prepared,
        blockers.size === 0 ? 'AVAILABLE' : 'UNAVAILABLE',
        [...blockers],
        sourceEventIds,
        consideredAdjustmentIds,
        blockers.size === 0 ? appliedAdjustmentIds : []
    );
    output.diagnostics.same_kickoff_excluded_event_ids = sameKickoffExcluded.sort((left, right) =>
        left.localeCompare(right)
    );
    output.diagnostics.future_event_ids_excluded = futureExcluded.sort((left, right) => left.localeCompare(right));
    if (maxEligibleMilliseconds !== null) {
        output.max_eligible_source_event_time_utc = new Date(maxEligibleMilliseconds).toISOString();
    }
    output.provenance_digest = makeProjectionDigest(
        prepared,
        sourceEventIds,
        blockers.size === 0 ? appliedAdjustmentIds : []
    );
    if (blockers.size !== 0) return output;

    setDerivedState(table);
    const states = assignPositions(table);
    const homeState = table.get(target.homeTeamId);
    const awayState = table.get(target.awayTeamId);
    if (!homeState.position || !awayState.position) {
        output.snapshot_status = 'UNAVAILABLE';
        output.unavailable_reason_codes = ['STANDINGS_POSITION_UNAVAILABLE'];
        return output;
    }
    output.home_table_position = homeState.position;
    output.away_table_position = awayState.position;
    output.table_position_diff = homeState.position - awayState.position;
    output.diagnostic_table_state = states
        .sort((left, right) => left.team_id.localeCompare(right.team_id))
        .map(state => ({ ...state }));
    return output;
}

function computeStandingsSnapshot(input) {
    const prepared = prepareInput(input);
    return computePreparedStandings(prepared, LEGACY_KICKOFF_EXCLUSIVE);
}

function toAsOfEngineResult(result) {
    const engineResult = { ...result };
    delete engineResult.availabilityProof;
    return engineResult;
}

function toAsOfEngineAdjustment(adjustment) {
    const engineAdjustment = { ...adjustment };
    delete engineAdjustment.state;
    delete engineAdjustment.availabilityProof;
    const { effectiveTime } = adjustment;
    const engineEffectiveTime =
        effectiveTime.kind === 'EXACT'
            ? { kind: 'EXACT', atUtc: effectiveTime.atUtc }
            : {
                  kind: 'INTERVAL',
                  lowerBoundUtc: effectiveTime.lowerBoundUtc,
                  upperBoundUtc: effectiveTime.upperBoundUtc,
              };
    return { ...engineAdjustment, effectiveTime: engineEffectiveTime };
}

function transformValidatedAsOfInput(rawInput, validation) {
    const normalized = validation.normalizedInput;
    const fixtures = normalized.fixture_universe.fixtures.map(fixture => ({ ...fixture }));
    const fixtureStates = new Map(normalized.fixture_states.map(state => [state.canonicalMatchId, state]));
    const results = normalized.fixture_states
        .filter(state => state.state === 'RESULT_AVAILABLE_AT_T')
        .map(state => toAsOfEngineResult(fixtureStates.get(state.canonicalMatchId).result));
    const teamUniverse = [...new Set(fixtures.flatMap(fixture => [fixture.homeTeamId, fixture.awayTeamId]))].sort(
        (left, right) => left.localeCompare(right)
    );
    return {
        contractBinding: rawInput.standingsContractBinding,
        competition: normalized.target.competition,
        leagueId: normalized.target.leagueId,
        season: normalized.target.season,
        teamUniverse,
        fixtures,
        results,
        administrativeAdjustments: normalized.administrative_adjustments.map(toAsOfEngineAdjustment),
        target: { ...normalized.target },
    };
}

function asOfConsumerGateReasonCodes(validation) {
    if (validation.semanticStatus === 'BLOCKED') return [...validation.blockingReasonCodes];
    if (validation.statuses.TEMPORAL_ELIGIBILITY_VALIDITY !== 'PROVEN') {
        return ['STANDINGS_SOURCE_CLOSURE_UNPROVEN'];
    }
    return [];
}

function rankingProjectionDigest(engineOutput) {
    if (!engineOutput) return null;
    return sha256Text(
        stableStringify({
            snapshot_status: engineOutput.snapshot_status,
            home_table_position: engineOutput.home_table_position,
            away_table_position: engineOutput.away_table_position,
            table_position_diff: engineOutput.table_position_diff,
            diagnostic_table_state: engineOutput.diagnostic_table_state,
            unavailable_reason_codes: engineOutput.unavailable_reason_codes,
        })
    );
}

function makeAsOfConsumerProvenanceDigest({
    validation,
    targetKickoffUtc,
    sourceEventIds,
    appliedAdjustmentIds,
    consumerOutcomeStatus,
    numericProjectionDigest,
}) {
    return sha256Text(
        stableStringify({
            consumer_contract_id: STANDINGS_ASOF_ENGINE_CONSUMER_CONTRACT_ID,
            consumer_contract_version: STANDINGS_ASOF_ENGINE_CONSUMER_CONTRACT_VERSION,
            input_contract_id: STANDINGS_ASOF_ENGINE_INPUT_CONTRACT_ID,
            input_contract_version: STANDINGS_ASOF_ENGINE_INPUT_CONTRACT_VERSION,
            asof_input_digest: validation.canonicalDigest,
            model_decision_time_utc: validation.normalizedInput.model_decision_time_utc,
            feature_as_of_utc: validation.normalizedInput.feature_as_of_utc,
            target_kickoff_utc: targetKickoffUtc,
            ranking_contract_id: STANDINGS_CONTRACT_ID,
            ranking_contract_version: STANDINGS_CONTRACT_VERSION,
            evaluation_boundary_policy: MODEL_DECISION_TIME_INCLUSIVE.id,
            engine_implementation_id: STANDINGS_ENGINE_IMPLEMENTATION.implementation_id,
            engine_implementation_identity_digest: STANDINGS_ENGINE_IMPLEMENTATION_IDENTITY_DIGEST,
            numeric_projection_digest: numericProjectionDigest,
            source_event_ids_used: [...sourceEventIds].sort((left, right) => left.localeCompare(right)),
            administrative_adjustment_ids_applied: [...appliedAdjustmentIds].sort((left, right) =>
                left.localeCompare(right)
            ),
            consumer_outcome_status: consumerOutcomeStatus,
        })
    );
}

function buildAsOfConsumerOutput(validation, engineOutput, computationStatus, gateReasonCodes = []) {
    const normalized = validation.normalizedInput;
    const target = normalized.target;
    const sourceEventIds = engineOutput?.source_event_ids_used || [];
    const appliedAdjustmentIds = engineOutput?.administrative_adjustment_ids_applied || [];
    const consideredAdjustmentIds =
        engineOutput?.administrative_adjustment_ids_considered ||
        normalized.administrative_adjustments.map(adjustment => adjustment.adjustmentId);
    const unavailableReasonCodes = engineOutput
        ? engineOutput.unavailable_reason_codes
        : [...new Set(gateReasonCodes)].sort((left, right) => left.localeCompare(right));
    const projectionDigest = rankingProjectionDigest(engineOutput);
    const consumerOutcomeStatus = computationStatus === 'EXECUTED' ? 'EXECUTED' : 'NOT_EXECUTED';
    return {
        snapshot_status: engineOutput?.snapshot_status || 'UNAVAILABLE',
        target_match_id: target.canonicalMatchId,
        target_kickoff_utc: target.targetKickoffUtc,
        home_team_id: target.homeTeamId,
        away_team_id: target.awayTeamId,
        competition: target.competition,
        league_id: target.leagueId,
        season: target.season,
        contract_id: STANDINGS_CONTRACT_ID,
        contract_version: STANDINGS_CONTRACT_VERSION,
        home_table_position: engineOutput?.home_table_position ?? null,
        away_table_position: engineOutput?.away_table_position ?? null,
        table_position_diff: engineOutput?.table_position_diff ?? null,
        unavailable_reason_codes: [...new Set(unavailableReasonCodes)].sort((left, right) => left.localeCompare(right)),
        source_event_ids_used: [...sourceEventIds].sort((left, right) => left.localeCompare(right)),
        administrative_adjustment_ids_considered: [...consideredAdjustmentIds].sort((left, right) =>
            left.localeCompare(right)
        ),
        administrative_adjustment_ids_applied: [...appliedAdjustmentIds].sort((left, right) =>
            left.localeCompare(right)
        ),
        max_eligible_source_event_time_utc: engineOutput?.max_eligible_source_event_time_utc || null,
        diagnostic_table_state: engineOutput?.diagnostic_table_state || null,
        diagnostics: engineOutput?.diagnostics || {
            target_match_result_excluded: true,
            same_kickoff_excluded_event_ids: [],
            future_event_ids_excluded: [],
            replay_double_count: 0,
            original_scheduled_date_used_as_event_time_count: 0,
        },
        consumer_contract_id: STANDINGS_ASOF_ENGINE_CONSUMER_CONTRACT_ID,
        consumer_contract_version: STANDINGS_ASOF_ENGINE_CONSUMER_CONTRACT_VERSION,
        consumer_contract_status: STANDINGS_ASOF_ENGINE_CONSUMER_CONTRACT_STATUS,
        input_contract_id: STANDINGS_ASOF_ENGINE_INPUT_CONTRACT_ID,
        input_contract_version: STANDINGS_ASOF_ENGINE_INPUT_CONTRACT_VERSION,
        model_decision_time_utc: normalized.model_decision_time_utc,
        feature_as_of_utc: normalized.feature_as_of_utc,
        evaluation_boundary_policy: MODEL_DECISION_TIME_INCLUSIVE.id,
        asof_input_digest: validation.canonicalDigest,
        ranking_contract_id: STANDINGS_CONTRACT_ID,
        ranking_contract_version: STANDINGS_CONTRACT_VERSION,
        engine_implementation_id: STANDINGS_ENGINE_IMPLEMENTATION.implementation_id,
        engine_implementation_identity_digest: STANDINGS_ENGINE_IMPLEMENTATION_IDENTITY_DIGEST,
        ranking_projection_input_digest: engineOutput?.input_digest || null,
        ranking_projection_provenance_digest: engineOutput?.provenance_digest || null,
        consumer_provenance_digest: makeAsOfConsumerProvenanceDigest({
            validation,
            targetKickoffUtc: target.targetKickoffUtc,
            sourceEventIds,
            appliedAdjustmentIds,
            consumerOutcomeStatus,
            numericProjectionDigest: projectionDigest,
        }),
        engine_computation_status: computationStatus,
        runtime_numeric_eligibility: 'NO',
        source_authority_validity: 'NOT_PROVEN',
    };
}

function computeStandingsAsOfSnapshot(asOfInput) {
    const validation = validateStandingsAsOfEngineInput(asOfInput);
    const gateReasonCodes = asOfConsumerGateReasonCodes(validation);
    if (gateReasonCodes.length > 0) {
        return buildAsOfConsumerOutput(validation, null, 'NOT_EXECUTED', gateReasonCodes);
    }

    const transformedInput = transformValidatedAsOfInput(asOfInput, validation);
    const prepared = prepareInput(transformedInput, {
        modelDecisionMilliseconds: parseUtc(validation.normalizedInput.model_decision_time_utc, 'model decision time'),
    });
    const engineOutput = computePreparedStandings(prepared, MODEL_DECISION_TIME_INCLUSIVE);
    return buildAsOfConsumerOutput(validation, engineOutput, 'EXECUTED');
}

function computeStandingsSnapshots(inputs) {
    if (!Array.isArray(inputs)) fail('standings snapshot input list must be an array', 'DEPENDENCY_UNAVAILABLE');
    return inputs
        .map(computeStandingsSnapshot)
        .sort((left, right) => left.target_match_id.localeCompare(right.target_match_id));
}

module.exports = {
    PointInTimeStandingsEngine: Object.freeze({
        computeStandingsSnapshot,
        computeStandingsSnapshots,
        computeStandingsAsOfSnapshot,
    }),
    STANDINGS_ENGINE_IMPLEMENTATION,
    STANDINGS_ENGINE_IMPLEMENTATION_BINDING,
    STANDINGS_ENGINE_IMPLEMENTATION_IDENTITY_DIGEST,
    StandingsEngineError,
    computeStandingsSnapshot,
    computeStandingsSnapshots,
    computeStandingsAsOfSnapshot,
};
