'use strict';

/* eslint-disable max-lines -- frozen evidence validation and normalization form one adapter boundary. */
/* eslint-disable complexity -- the adapter is deliberately fail-closed at every evidence seam. */

// lifecycle: permanent
// 离线 Premier League 历史证据适配器。调用方负责读取文件并计算 raw SHA-256；
// 本模块只接收已读取的对象和文件绑定，不执行文件、网络、数据库或时钟 I/O。
// 它证明完整赛程后，才构造 PointInTimeStandingsEngine 的 normalized input。

const {
    AWAY_FIXTURES_PER_TEAM,
    COMPETITION,
    FIXTURES_PER_SEASON,
    FIXTURES_PER_TEAM,
    HOME_FIXTURES_PER_TEAM,
    MASTER_COUNT,
    SEASONS,
    TEAMS_PER_SEASON,
    APPROVED_REAL_MASTER_V1_IDENTITY_PROJECTION_HASH,
} = require('../canonical/CanonicalInventoryContract');
const {
    STANDINGS_COMPETITION,
    STANDINGS_CONTRACT_ID,
    STANDINGS_CONTRACT_VERSION,
    STANDINGS_LEAGUE_ID,
    STANDINGS_SEASONS,
    bindFrozenStandingsContract,
} = require('./StandingsContractBinding');
const { sha256Text, stableStringify } = require('../canonical/StableValue');

const OFFICIAL_SCHEMA = 'standings-official-fixture-projection/v1';
const NORMALIZED_SCHEMA = 'standings-normalized-prior-result-ledger/v1';
const MISSING_SCHEMA = 'standings-missing-prior-fixture-ledger/v1';
const POSTPONED_SCHEMA = 'standings-postponed-rescheduled-audit/v1';
const EXCEPTION_SCHEMA = 'standings-exception-status-audit/v1';
const ADMIN_SCHEMA = 'standings-administrative-adjustment-ledger/v1';
const TARGET_CLOSURE_SCHEMA = 'standings-target-closure-audit/v1';
const UTC_TIMESTAMP = /^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d{3})?Z$/;
const SHA256 = /^[0-9a-f]{64}$/;

const OFFICIAL_FIELDS = new Set([
    'actual_event_time_proven',
    'actual_played_kickoff_utc',
    'away_canonical_team_id',
    'away_score',
    'canonical_away_team',
    'canonical_home_team',
    'canonical_match_id',
    'canonical_scheduled_kickoff_utc',
    'competition',
    'exception_classification',
    'home_canonical_team_id',
    'home_score',
    'league_id',
    'official_away_team_name',
    'official_fixture_id',
    'official_fixture_type',
    'official_home_team_name',
    'official_opta_fixture_id',
    'official_outcome',
    'official_phase',
    'official_provisional_kickoff_utc',
    'official_replay_flag',
    'official_status',
    'result_eligible_for_table',
    'result_finality_status',
    'season',
    'source_capture_id',
    'source_hash',
    'source_record_sha256',
]);

const NORMALIZED_FIELDS = new Set([
    'actual_kickoff_utc',
    'away_canonical_team_id',
    'away_score',
    'canonical_match_id',
    'canonical_schedule_kickoff_utc',
    'event_status',
    'evidence_confidence',
    'home_canonical_team_id',
    'home_score',
    'league_id',
    'linkage_proof',
    'newly_acquired_event_time_fact',
    'newly_acquired_result_fact',
    'original_scheduled_time',
    'provider_match_id',
    'reason_code',
    'result_eligible_for_table',
    'result_finality_status',
    'season',
    'source_hash',
    'source_identity',
    'source_record_sha256',
]);

const MISSING_FIELDS = new Set([
    'acquisition_status',
    'actual_played_kickoff_utc',
    'away_canonical_team_id',
    'away_team',
    'canonical_match_id',
    'canonical_scheduled_kickoff_utc',
    'home_canonical_team_id',
    'home_team',
    'league_id',
    'provider_match_id',
    'reason_code',
    'required_by_target_count',
    'required_by_target_ids_sha256',
    'required_under_actual_event_time_cutoff',
    'required_under_canonical_schedule_cutoff',
    'season',
]);

const TARGET_FIELDS = new Set([
    'administrative_adjustment_timing_blockers',
    'canonical_match_id',
    'competition_membership_closed',
    'exception_status_blocker_ids',
    'fabricated_position',
    'final_table_used',
    'future_result_used',
    'missing_prior_result_ids',
    'postponed_time_blocker_ids',
    'prior_fixture_count',
    'prior_fixture_ids_sha256',
    'provider_display_order_used',
    'reason_codes',
    'rule_version_proven',
    'same_kickoff_prior_result_used',
    'season',
    'status',
    'target_kickoff_utc',
    'target_match_result_used',
    'tie_representation_approved',
]);

const REQUIRED_SOURCE_BINDINGS = Object.freeze([
    'official_fixture_projection',
    'normalized_prior_result_ledger',
    'missing_prior_fixture_ledger',
    'postponed_rescheduled_audit',
    'exception_status_audit',
    'administrative_adjustment_ledger',
    'target_closure_audit',
    'season_rule_matrix',
]);

class FrozenEvidenceAdapterError extends Error {
    constructor(message, code = 'DEPENDENCY_UNAVAILABLE') {
        super(message);
        this.name = 'FrozenEvidenceAdapterError';
        this.code = code;
        this.reasonCode = code;
    }
}

function fail(message, code = 'DEPENDENCY_UNAVAILABLE') {
    throw new FrozenEvidenceAdapterError(message, code);
}

function isPlainObject(value) {
    return value !== null && typeof value === 'object' && !Array.isArray(value);
}

function assertObject(value, label, code = 'DEPENDENCY_UNAVAILABLE') {
    if (!isPlainObject(value)) fail(`${label} must be an object`, code);
    return value;
}

function assertArray(value, label, code = 'DEPENDENCY_UNAVAILABLE') {
    if (!Array.isArray(value)) fail(`${label} must be an array`, code);
    return value;
}

function assertText(value, label, code = 'DEPENDENCY_UNAVAILABLE') {
    if (typeof value !== 'string' || value.trim() === '') fail(`${label} must be non-empty text`, code);
    return value;
}

function assertBoolean(value, label, code = 'DEPENDENCY_UNAVAILABLE') {
    if (typeof value !== 'boolean') fail(`${label} must be boolean`, code);
    return value;
}

function assertInteger(value, label, code = 'DEPENDENCY_UNAVAILABLE') {
    if (!Number.isSafeInteger(value)) fail(`${label} must be a safe integer`, code);
    return value;
}

function assertSha(value, label, code = 'DEPENDENCY_UNAVAILABLE') {
    if (typeof value !== 'string' || !SHA256.test(value)) fail(`${label} must be a lowercase SHA-256`, code);
    return value;
}

function assertUtc(value, label, allowNull = false, code = 'EVENT_TIME_CONFLICT') {
    if (allowNull && value === null) return null;
    if (typeof value !== 'string' || !UTC_TIMESTAMP.test(value) || !Number.isFinite(Date.parse(value))) {
        fail(`${label} must be an absolute UTC timestamp`, code);
    }
    return value;
}

function assertKnownKeys(value, allowed, label, code = 'DEPENDENCY_UNAVAILABLE') {
    for (const key of Object.keys(value)) {
        if (!allowed.has(key)) fail(`${label} contains unsupported field ${key}`, code);
    }
}

function assertRequiredKeys(value, required, label, code = 'DEPENDENCY_UNAVAILABLE') {
    for (const key of required) {
        if (!Object.hasOwn(value, key)) fail(`${label}.${key} is required`, code);
    }
}

function sortedTextValues(value, label, code = 'RULE_VERSION_UNPROVEN') {
    const values = assertArray(value, label, code);
    if (values.some(item => typeof item !== 'string' || item.trim() === '')) {
        fail(`${label} must contain non-empty text values`, code);
    }
    return [...values].sort((left, right) => left.localeCompare(right));
}

function assertSourceBindings(sourceBindings) {
    const bindings = assertObject(sourceBindings, 'frozen evidence source bindings');
    for (const name of REQUIRED_SOURCE_BINDINGS) {
        const binding = assertObject(bindings[name], `source binding ${name}`);
        assertSha(binding.sha256, `source binding ${name}.sha256`);
        assertSha(binding.content_sha256, `source binding ${name}.content_sha256`);
        assertText(binding.schema_version, `source binding ${name}.schema_version`);
        if (binding.upstream_cryptographic_binding !== undefined) {
            assertBoolean(
                binding.upstream_cryptographic_binding,
                `source binding ${name}.upstream_cryptographic_binding`
            );
        }
    }
    return bindings;
}

function verifyContentBinding(document, sourceBinding, label) {
    if (sourceBinding.content_sha256 === undefined) return;
    if (computeEvidenceContentDigest(document) !== sourceBinding.content_sha256) {
        fail(`${label} normalized content binding differs from the pinned input manifest`, 'DEPENDENCY_UNAVAILABLE');
    }
}

function canonicalEvidenceValue(value) {
    if (Array.isArray(value)) {
        return value
            .map(canonicalEvidenceValue)
            .sort((left, right) => stableStringify(left).localeCompare(stableStringify(right)));
    }
    if (isPlainObject(value)) {
        return Object.fromEntries(Object.entries(value).map(([key, child]) => [key, canonicalEvidenceValue(child)]));
    }
    return value;
}

function computeEvidenceContentDigest(document) {
    return sha256Text(stableStringify(canonicalEvidenceValue(document)));
}

function assertScope(document, schemaVersion, label) {
    const value = assertObject(document, label, 'RULE_VERSION_UNPROVEN');
    if (value.schema_version !== schemaVersion) fail(`${label} schema version is unsupported`, 'RULE_VERSION_UNPROVEN');
    const scope = assertObject(value.scope, `${label}.scope`, 'RULE_VERSION_UNPROVEN');
    if (scope.competition !== COMPETITION || scope.league_id !== String(STANDINGS_LEAGUE_ID)) {
        fail(`${label} competition scope is outside Premier League v1`, 'RULE_VERSION_UNPROVEN');
    }
    if (
        stableStringify(sortedTextValues(scope.seasons, `${label}.scope.seasons`)) !==
        stableStringify([...SEASONS].sort())
    ) {
        fail(`${label} season scope is outside frozen v1`, 'RULE_VERSION_UNPROVEN');
    }
    return value;
}

function assertScopePopulation(scope, label, expected) {
    if (scope[expected.field] !== expected.value) {
        fail(`${label}.${expected.field} is not ${expected.value}`, expected.code || 'DEPENDENCY_UNAVAILABLE');
    }
}

function validateOfficialRow(row, index) {
    const label = `official fixture projection row[${index}]`;
    assertObject(row, label, 'RESULT_IDENTITY_CONFLICT');
    assertKnownKeys(row, OFFICIAL_FIELDS, label, 'RESULT_IDENTITY_CONFLICT');
    assertRequiredKeys(row, OFFICIAL_FIELDS, label, 'RESULT_IDENTITY_CONFLICT');
    assertText(row.canonical_match_id, `${label}.canonical_match_id`, 'RESULT_IDENTITY_CONFLICT');
    assertText(row.season, `${label}.season`, 'RULE_VERSION_UNPROVEN');
    if (!SEASONS.includes(row.season)) fail(`${label}.season is outside frozen scope`, 'RULE_VERSION_UNPROVEN');
    if (!row.canonical_match_id.startsWith(`${STANDINGS_LEAGUE_ID}_${row.season.replace('/', '')}_`)) {
        fail(`${label}.canonical_match_id is not bound to its season`, 'RESULT_IDENTITY_CONFLICT');
    }
    if (row.competition !== COMPETITION || row.league_id !== String(STANDINGS_LEAGUE_ID)) {
        fail(`${label} competition identity conflicts`, 'RESULT_IDENTITY_CONFLICT');
    }
    for (const field of [
        'home_canonical_team_id',
        'away_canonical_team_id',
        'canonical_home_team',
        'canonical_away_team',
        'official_home_team_name',
        'official_away_team_name',
        'official_fixture_id',
        'official_opta_fixture_id',
        'source_capture_id',
        'source_hash',
        'source_record_sha256',
    ]) {
        assertText(row[field], `${label}.${field}`, 'RESULT_IDENTITY_CONFLICT');
    }
    if (row.home_canonical_team_id === row.away_canonical_team_id) {
        fail(`${label} has identical home and away teams`, 'RESULT_IDENTITY_CONFLICT');
    }
    assertUtc(row.canonical_scheduled_kickoff_utc, `${label}.canonical_scheduled_kickoff_utc`);
    assertUtc(row.official_provisional_kickoff_utc, `${label}.official_provisional_kickoff_utc`);
    assertBoolean(row.actual_event_time_proven, `${label}.actual_event_time_proven`, 'POSTPONED_EVENT_TIME_UNPROVEN');
    if (!row.actual_event_time_proven) {
        fail(`${label} actual event time is not proven`, 'POSTPONED_EVENT_TIME_UNPROVEN');
    }
    assertUtc(row.actual_played_kickoff_utc, `${label}.actual_played_kickoff_utc`);
    assertInteger(row.home_score, `${label}.home_score`, 'RESULT_SCORE_CONFLICT');
    assertInteger(row.away_score, `${label}.away_score`, 'RESULT_SCORE_CONFLICT');
    if (row.home_score < 0 || row.away_score < 0) fail(`${label} score is negative`, 'RESULT_SCORE_CONFLICT');
    if (
        row.official_status !== 'C' ||
        row.official_phase !== 'F' ||
        row.official_fixture_type !== 'REGULAR' ||
        row.official_replay_flag !== false ||
        row.result_eligible_for_table !== 'YES' ||
        row.result_finality_status !== 'OFFICIAL_STATUS_C_PHASE_F_FINAL'
    ) {
        fail(`${label} official final-table eligibility is not proven`, 'FIXTURE_STATUS_CONFLICT');
    }
    if (!['NONE_IN_OFFICIAL_FINAL_FIXTURE_RECORD', 'REPLAYED_REPLACEMENT'].includes(row.exception_classification)) {
        fail(`${label} exception classification is unknown`, 'EXCEPTION_STATUS_UNPROVEN');
    }
    assertSha(row.source_hash, `${label}.source_hash`, 'DEPENDENCY_UNAVAILABLE');
    assertSha(row.source_record_sha256, `${label}.source_record_sha256`, 'DEPENDENCY_UNAVAILABLE');
    const expectedCapture = `pl-fixtures-${row.season.replace('/', '-')}`;
    if (row.source_capture_id !== expectedCapture) {
        fail(`${label}.source_capture_id is not the frozen season capture`, 'DEPENDENCY_UNAVAILABLE');
    }
    return row;
}

function proveCanonicalScheduleClosure(document, sourceBinding) {
    const value = assertScope(document, OFFICIAL_SCHEMA, 'official fixture projection');
    verifyContentBinding(value, sourceBinding, 'official fixture projection');
    const rows = assertArray(value.rows, 'official fixture projection.rows', 'DEPENDENCY_UNAVAILABLE');
    assertScopePopulation(value.scope, 'official fixture projection.scope', {
        field: 'canonical_schedule_count',
        value: MASTER_COUNT,
    });
    if (rows.length !== MASTER_COUNT) {
        fail(`canonical schedule must contain ${MASTER_COUNT} fixtures`, 'DEPENDENCY_UNAVAILABLE');
    }
    const seenMatchIds = new Set();
    const seenOfficialIds = new Set();
    const seenOptaIds = new Set();
    const bySeason = new Map(SEASONS.map(season => [season, []]));
    for (const [index, row] of rows.entries()) {
        validateOfficialRow(row, index);
        if (seenMatchIds.has(row.canonical_match_id)) {
            fail(`duplicate canonical fixture ID ${row.canonical_match_id}`, 'RESULT_IDENTITY_CONFLICT');
        }
        if (seenOfficialIds.has(row.official_fixture_id) || seenOptaIds.has(row.official_opta_fixture_id)) {
            fail(`duplicate official fixture identity for ${row.canonical_match_id}`, 'RESULT_IDENTITY_CONFLICT');
        }
        seenMatchIds.add(row.canonical_match_id);
        seenOfficialIds.add(row.official_fixture_id);
        seenOptaIds.add(row.official_opta_fixture_id);
        bySeason.get(row.season).push(row);
    }
    const seasonTeamIds = {};
    const perSeason = {};
    for (const season of SEASONS) {
        const seasonRows = bySeason.get(season);
        if (seasonRows.length !== FIXTURES_PER_SEASON) {
            fail(`${season} canonical schedule is not ${FIXTURES_PER_SEASON} fixtures`, 'DEPENDENCY_UNAVAILABLE');
        }
        const teamCounts = new Map();
        for (const row of seasonRows) {
            const home = teamCounts.get(row.home_canonical_team_id) || { total: 0, home: 0, away: 0 };
            const away = teamCounts.get(row.away_canonical_team_id) || { total: 0, home: 0, away: 0 };
            home.total += 1;
            home.home += 1;
            away.total += 1;
            away.away += 1;
            teamCounts.set(row.home_canonical_team_id, home);
            teamCounts.set(row.away_canonical_team_id, away);
        }
        if (teamCounts.size !== TEAMS_PER_SEASON) {
            fail(`${season} canonical team universe is not ${TEAMS_PER_SEASON} clubs`, 'DEPENDENCY_UNAVAILABLE');
        }
        for (const [teamId, counts] of teamCounts) {
            if (
                counts.total !== FIXTURES_PER_TEAM ||
                counts.home !== HOME_FIXTURES_PER_TEAM ||
                counts.away !== AWAY_FIXTURES_PER_TEAM
            ) {
                fail(`${season} team ${teamId} has non-canonical home/away closure`, 'DEPENDENCY_UNAVAILABLE');
            }
        }
        seasonTeamIds[season] = [...teamCounts.keys()].sort((left, right) => left.localeCompare(right));
        perSeason[season] = {
            canonical_fixtures: seasonRows.length,
            team_count: teamCounts.size,
            fixtures_per_team: FIXTURES_PER_TEAM,
            home_fixtures_per_team: HOME_FIXTURES_PER_TEAM,
            away_fixtures_per_team: AWAY_FIXTURES_PER_TEAM,
        };
    }
    if (value.scope.canonical_schedule_business_sha256 !== APPROVED_REAL_MASTER_V1_IDENTITY_PROJECTION_HASH) {
        fail('canonical schedule business identity is not the approved frozen projection', 'DEPENDENCY_UNAVAILABLE');
    }
    assertSha(value.scope.canonical_schedule_sha256, 'official fixture projection.scope.canonical_schedule_sha256');
    assertSha(
        value.scope.canonical_required_set_sha256,
        'official fixture projection.scope.canonical_required_set_sha256'
    );
    return Object.freeze({
        status: 'PROVEN',
        authority: 'standings-official-fixture-projection/v1 + canonical inventory closure',
        schema_version: OFFICIAL_SCHEMA,
        source_binding: { ...sourceBinding },
        canonical_schedule_count: rows.length,
        canonical_schedule_sha256: value.scope.canonical_schedule_sha256,
        canonical_schedule_business_sha256: value.scope.canonical_schedule_business_sha256,
        canonical_required_set_sha256: value.scope.canonical_required_set_sha256,
        per_season: perSeason,
        season_team_ids: seasonTeamIds,
        rows,
    });
}

function validateNormalizedRow(row, index, official) {
    const label = `normalized result row[${index}]`;
    assertObject(row, label, 'RESULT_IDENTITY_CONFLICT');
    assertKnownKeys(row, NORMALIZED_FIELDS, label, 'RESULT_IDENTITY_CONFLICT');
    assertRequiredKeys(row, NORMALIZED_FIELDS, label, 'RESULT_IDENTITY_CONFLICT');
    if (row.canonical_match_id !== official.canonical_match_id) {
        fail(`${label}.canonical_match_id is not bound to official schedule`, 'RESULT_IDENTITY_CONFLICT');
    }
    for (const field of ['season', 'home_canonical_team_id', 'away_canonical_team_id', 'event_status', 'reason_code']) {
        assertText(row[field], `${label}.${field}`, 'RESULT_IDENTITY_CONFLICT');
    }
    if (row.season !== official.season) fail(`${label}.season conflicts with schedule`, 'RESULT_IDENTITY_CONFLICT');
    if (row.league_id !== String(STANDINGS_LEAGUE_ID)) fail(`${label}.league_id conflicts`, 'RESULT_IDENTITY_CONFLICT');
    if (
        row.home_canonical_team_id !== official.home_canonical_team_id ||
        row.away_canonical_team_id !== official.away_canonical_team_id
    ) {
        fail(`${label} team identity conflicts with official schedule`, 'RESULT_IDENTITY_CONFLICT');
    }
    if (row.canonical_schedule_kickoff_utc !== official.canonical_scheduled_kickoff_utc) {
        fail(`${label} scheduled event time conflicts`, 'EVENT_TIME_CONFLICT');
    }
    if (row.actual_kickoff_utc !== official.actual_played_kickoff_utc) {
        fail(`${label} actual event time conflicts`, 'EVENT_TIME_CONFLICT');
    }
    if (
        row.result_eligible_for_table !== official.result_eligible_for_table ||
        row.result_finality_status !== official.result_finality_status
    ) {
        fail(`${label} final-table status conflicts`, 'FIXTURE_STATUS_CONFLICT');
    }
    if (row.home_score !== official.home_score || row.away_score !== official.away_score) {
        fail(`${label} score conflicts with official result`, 'RESULT_SCORE_CONFLICT');
    }
    if (row.source_hash !== official.source_hash || row.source_record_sha256 !== official.source_record_sha256) {
        fail(`${label} source lineage conflicts with official result`, 'DEPENDENCY_UNAVAILABLE');
    }
    assertUtc(row.actual_kickoff_utc, `${label}.actual_kickoff_utc`);
    assertInteger(row.home_score, `${label}.home_score`, 'RESULT_SCORE_CONFLICT');
    assertInteger(row.away_score, `${label}.away_score`, 'RESULT_SCORE_CONFLICT');
    if (row.home_score < 0 || row.away_score < 0) fail(`${label} score is negative`, 'RESULT_SCORE_CONFLICT');
    if (!['COMPLETED', 'REPLAYED_COMPLETED'].includes(row.event_status)) {
        fail(`${label}.event_status is unknown`, 'EXCEPTION_STATUS_UNPROVEN');
    }
    if (row.event_status === 'REPLAYED_COMPLETED' && official.exception_classification !== 'REPLAYED_REPLACEMENT') {
        fail(`${label} replay status is not bound to the replay replacement`, 'FIXTURE_STATUS_CONFLICT');
    }
    if (row.event_status === 'COMPLETED' && official.exception_classification === 'REPLAYED_REPLACEMENT') {
        fail(`${label} replay replacement status is missing`, 'FIXTURE_STATUS_CONFLICT');
    }
    assertBoolean(row.newly_acquired_event_time_fact, `${label}.newly_acquired_event_time_fact`);
    if (!row.newly_acquired_event_time_fact) {
        fail(`${label} actual event time evidence is not marked proven`, 'POSTPONED_EVENT_TIME_UNPROVEN');
    }
    assertBoolean(row.newly_acquired_result_fact, `${label}.newly_acquired_result_fact`);
    assertObject(row.linkage_proof, `${label}.linkage_proof`);
    assertObject(row.source_identity, `${label}.source_identity`);
    assertSha(row.source_hash, `${label}.source_hash`);
    assertSha(row.source_record_sha256, `${label}.source_record_sha256`);
    return row;
}

function reconcileNormalizedResults(document, scheduleClosure, sourceBinding) {
    const value = assertScope(document, NORMALIZED_SCHEMA, 'normalized prior-result ledger');
    verifyContentBinding(value, sourceBinding, 'normalized prior-result ledger');
    const rows = assertArray(value.rows, 'normalized prior-result ledger.rows');
    assertScopePopulation(value.scope, 'normalized prior-result ledger.scope', {
        field: 'canonical_schedule_count',
        value: MASTER_COUNT,
    });
    if (rows.length !== MASTER_COUNT) {
        fail('normalized result population is not the complete schedule', 'MISSING_PRIOR_RESULT_EVIDENCE');
    }
    const officialById = new Map(scheduleClosure.rows.map(row => [row.canonical_match_id, row]));
    const normalizedById = new Map();
    for (const [index, row] of rows.entries()) {
        const official = officialById.get(row.canonical_match_id);
        if (!official) {
            fail(`normalized result ${row.canonical_match_id} has no official fixture`, 'RESULT_IDENTITY_CONFLICT');
        }
        validateNormalizedRow(row, index, official);
        if (normalizedById.has(row.canonical_match_id)) {
            fail(`duplicate normalized result ${row.canonical_match_id}`, 'RESULT_IDENTITY_CONFLICT');
        }
        normalizedById.set(row.canonical_match_id, row);
    }
    if (normalizedById.size !== scheduleClosure.rows.length) {
        fail('normalized results do not close canonical schedule', 'MISSING_PRIOR_RESULT_EVIDENCE');
    }
    return { value, rows, byId: normalizedById, source_binding: { ...sourceBinding } };
}

function validateMissingPriorLedger(document, scheduleClosure, normalized, sourceBinding) {
    const value = assertScope(document, MISSING_SCHEMA, 'missing prior-fixture ledger');
    verifyContentBinding(value, sourceBinding, 'missing prior-fixture ledger');
    const rows = assertArray(value.rows, 'missing prior-fixture ledger.rows');
    assertScopePopulation(value.scope, 'missing prior-fixture ledger.scope', {
        field: 'missing_prior_fixture_count',
        value: rows.length,
    });
    if (rows.length !== 186) {
        fail('missing prior-fixture evidence population is not 186', 'MISSING_PRIOR_RESULT_EVIDENCE');
    }
    const officialById = new Map(scheduleClosure.rows.map(row => [row.canonical_match_id, row]));
    const seen = new Set();
    for (const [index, row] of rows.entries()) {
        const label = `missing prior-fixture row[${index}]`;
        assertObject(row, label, 'MISSING_PRIOR_RESULT_EVIDENCE');
        assertKnownKeys(row, MISSING_FIELDS, label, 'MISSING_PRIOR_RESULT_EVIDENCE');
        assertRequiredKeys(row, MISSING_FIELDS, label, 'MISSING_PRIOR_RESULT_EVIDENCE');
        if (seen.has(row.canonical_match_id)) {
            fail(`duplicate missing prior fixture ${row.canonical_match_id}`, 'RESULT_IDENTITY_CONFLICT');
        }
        seen.add(row.canonical_match_id);
        const official = officialById.get(row.canonical_match_id);
        const result = normalized.byId.get(row.canonical_match_id);
        if (!official || !result) fail(`${label} is not closed by complete evidence`, 'MISSING_PRIOR_RESULT_EVIDENCE');
        if (
            row.season !== official.season ||
            row.home_canonical_team_id !== official.home_canonical_team_id ||
            row.away_canonical_team_id !== official.away_canonical_team_id ||
            row.canonical_scheduled_kickoff_utc !== official.canonical_scheduled_kickoff_utc ||
            row.actual_played_kickoff_utc !== official.actual_played_kickoff_utc
        ) {
            fail(`${label} identity or event time conflicts`, 'RESULT_IDENTITY_CONFLICT');
        }
        if (
            row.acquisition_status !== 'NEW_OFFICIAL_PL_RESULT_AND_EVENT_TIME_EVIDENCE' ||
            row.reason_code !== 'MISSING_NON_TARGET_PRIOR_RESULT_CLOSED_BY_OFFICIAL_PL_FIXTURE_RECORD' ||
            row.required_under_actual_event_time_cutoff !== true ||
            row.required_under_canonical_schedule_cutoff !== true
        ) {
            fail(`${label} remediation lineage is not proven`, 'MISSING_PRIOR_RESULT_EVIDENCE');
        }
        if (!result.newly_acquired_result_fact) {
            fail(`${label} was not marked as a newly acquired result fact`, 'MISSING_PRIOR_RESULT_EVIDENCE');
        }
        assertInteger(row.required_by_target_count, `${label}.required_by_target_count`);
        assertSha(row.required_by_target_ids_sha256, `${label}.required_by_target_ids_sha256`);
        if (row.league_id !== String(STANDINGS_LEAGUE_ID)) {
            fail(`${label}.league_id conflicts`, 'RESULT_IDENTITY_CONFLICT');
        }
    }
    const sortedIds = [...seen].sort((left, right) => left.localeCompare(right));
    if (sha256Text(stableStringify(sortedIds)) !== value.scope.missing_prior_fixture_ids_sha256) {
        fail('missing prior-fixture ID closure hash differs', 'DEPENDENCY_UNAVAILABLE');
    }
    return { value, rows, ids: sortedIds, source_binding: { ...sourceBinding } };
}

function validatePostponedAudit(document, sourceBinding) {
    const value = assertScope(document, POSTPONED_SCHEMA, 'postponed/rescheduled audit');
    verifyContentBinding(value, sourceBinding, 'postponed/rescheduled audit');
    if (
        value.canonical_fixture_count !== MASTER_COUNT ||
        value.official_fixture_count !== MASTER_COUNT ||
        value.actual_event_time_complete_fixture_count !== MASTER_COUNT ||
        value.official_source_missing_actual_time_count !== 0 ||
        value.postponed_policy_proven !== true ||
        value.postponed_rescheduled_inventory_complete !== true
    ) {
        fail('postponed/rescheduled actual event-time closure is not proven', 'POSTPONED_EVENT_TIME_UNPROVEN');
    }
    assertObject(value.policy, 'postponed/rescheduled audit.policy', 'POSTPONED_EVENT_TIME_UNPROVEN');
    assertText(
        value.event_time_authority,
        'postponed/rescheduled audit.event_time_authority',
        'POSTPONED_EVENT_TIME_UNPROVEN'
    );
    assertArray(
        value.explicit_documented_postponed_or_rescheduled_event_inventory,
        'postponed/rescheduled audit.inventory'
    );
    return { value, source_binding: { ...sourceBinding } };
}

function validateExceptionAudit(document, scheduleClosure, sourceBinding) {
    const value = assertScope(document, EXCEPTION_SCHEMA, 'exception status audit');
    verifyContentBinding(value, sourceBinding, 'exception status audit');
    if (value.exception_policy_proven !== true) {
        fail('exception status policy is not proven', 'EXCEPTION_STATUS_UNPROVEN');
    }
    const control = assertObject(
        value.official_fixture_control,
        'exception status official fixture control',
        'EXCEPTION_STATUS_UNPROVEN'
    );
    if (
        control.all_records_phase_f !== true ||
        control.all_records_regular_or_replacement !== true ||
        control.all_records_status_c !== true ||
        control.source_conflict_count !== 0 ||
        stableStringify(control.season_fixture_counts) !==
            stableStringify(Object.fromEntries(SEASONS.map(season => [season, FIXTURES_PER_SEASON])))
    ) {
        fail('exception status official control is not closed', 'EXCEPTION_STATUS_UNPROVEN');
    }
    for (const name of ['abandoned', 'replayed', 'awarded', 'void']) {
        assertObject(value[name], `exception status audit.${name}`, 'EXCEPTION_STATUS_UNPROVEN');
        assertInteger(value[name].event_count, `exception status audit.${name}.event_count`);
        assertBoolean(
            value[name].inventory_complete,
            `exception status audit.${name}.inventory_complete`,
            'EXCEPTION_STATUS_UNPROVEN'
        );
        if (!value[name].inventory_complete) {
            fail(`exception ${name} inventory is incomplete`, 'EXCEPTION_STATUS_UNPROVEN');
        }
        assertArray(value[name].events, `exception status audit.${name}.events`, 'EXCEPTION_STATUS_UNPROVEN');
        if (value[name].events.length !== value[name].event_count) {
            fail(`exception ${name} count disagrees with events`, 'EXCEPTION_STATUS_UNPROVEN');
        }
    }
    if (
        value.abandoned.event_count !== 1 ||
        value.replayed.event_count !== 1 ||
        value.awarded.event_count !== 0 ||
        value.void.event_count !== 0
    ) {
        fail('frozen exception population differs', 'EXCEPTION_STATUS_UNPROVEN');
    }
    const abandoned = value.abandoned.events[0];
    if (
        abandoned.canonical_match_id !== null ||
        abandoned.result_eligible_for_table !== 'NO' ||
        typeof abandoned.replay_replacement_canonical_match_id !== 'string' ||
        abandoned.replay_replacement_canonical_match_id.trim() === ''
    ) {
        fail('abandoned original is not excluded and replaced by the proven replay', 'FIXTURE_STATUS_CONFLICT');
    }
    const replay = value.replayed.events[0];
    const replayFixture = scheduleClosure.rows.find(row => row.canonical_match_id === replay.canonical_match_id);
    if (
        !replayFixture ||
        replay.canonical_match_id !== abandoned.replay_replacement_canonical_match_id ||
        replay.result_eligible_for_table !== 'YES' ||
        stableStringify(replay.score) !== stableStringify([replayFixture.home_score, replayFixture.away_score])
    ) {
        fail('replay evidence is not bound to one eligible replacement fixture', 'FIXTURE_STATUS_CONFLICT');
    }
    assertUtc(replay.actual_played_kickoff_utc, 'replay.actual_played_kickoff_utc');
    return { value, source_binding: { ...sourceBinding } };
}

function validateAdministrativeAdjustments(document, scheduleClosure, sourceBinding) {
    const value = assertScope(document, ADMIN_SCHEMA, 'administrative adjustment ledger');
    verifyContentBinding(value, sourceBinding, 'administrative adjustment ledger');
    if (
        value.audit_complete !== true ||
        value.inventory_complete !== true ||
        value.events_found !== value.rows?.length
    ) {
        fail('administrative adjustment inventory is incomplete', 'ADMIN_ADJUSTMENT_CONFLICT');
    }
    const rows = assertArray(value.rows, 'administrative adjustment ledger.rows', 'ADMIN_ADJUSTMENT_CONFLICT');
    if (rows.length !== 4) {
        fail('administrative adjustment population differs from frozen scope', 'ADMIN_ADJUSTMENT_CONFLICT');
    }
    const ids = new Set();
    const normalized = rows.map((row, index) => {
        const label = `administrative adjustment row[${index}]`;
        assertObject(row, label, 'ADMIN_ADJUSTMENT_CONFLICT');
        for (const field of [
            'season',
            'team_id',
            'team_name',
            'evidence_date',
            'effective_time_lower_bound',
            'effective_time_upper_bound',
            'effective_time_precision',
            'decision_type',
            'source_hash',
            'source_title',
            'source_type',
            'source_url',
            'provenance',
            'source_conclusion',
        ]) {
            assertText(row[field], `${label}.${field}`, 'ADMIN_ADJUSTMENT_CONFLICT');
        }
        if (!STANDINGS_SEASONS.includes(row.season)) {
            fail(`${label}.season is outside frozen admin scope`, 'ADMIN_ADJUSTMENT_CONFLICT');
        }
        if (!scheduleClosure.season_team_ids[row.season].includes(row.team_id)) {
            fail(`${label}.team_id is not in season universe`, 'ADMIN_ADJUSTMENT_CONFLICT');
        }
        assertInteger(row.delta, `${label}.delta`, 'ADMIN_ADJUSTMENT_CONFLICT');
        if (row.delta === 0) fail(`${label}.delta cannot be zero`, 'ADMIN_ADJUSTMENT_CONFLICT');
        assertInteger(row.cumulative_effect, `${label}.cumulative_effect`, 'ADMIN_ADJUSTMENT_CONFLICT');
        assertBoolean(
            row.exact_effective_timestamp_proven,
            `${label}.exact_effective_timestamp_proven`,
            'ADMIN_ADJUSTMENT_CONFLICT'
        );
        if (
            row.exact_effective_timestamp_proven !== false ||
            row.effective_time_precision !== 'CALENDAR_DATE_INTERVAL_ONLY'
        ) {
            fail(`${label} fabricated an exact administrative timestamp`, 'ADMIN_ADJUSTMENT_CONFLICT');
        }
        assertUtc(row.effective_time_lower_bound, `${label}.effective_time_lower_bound`);
        assertUtc(row.effective_time_upper_bound, `${label}.effective_time_upper_bound`);
        if (Date.parse(row.effective_time_lower_bound) >= Date.parse(row.effective_time_upper_bound)) {
            fail(`${label} effective interval is inverted`, 'ADMIN_ADJUSTMENT_CONFLICT');
        }
        assertSha(row.source_hash, `${label}.source_hash`, 'ADMIN_ADJUSTMENT_CONFLICT');
        const adjustmentId = `${row.season}|${row.team_id}|${row.evidence_date}|${row.decision_type}`;
        if (ids.has(adjustmentId)) {
            fail(`duplicate administrative adjustment ${adjustmentId}`, 'ADMIN_ADJUSTMENT_CONFLICT');
        }
        ids.add(adjustmentId);
        return {
            adjustmentId,
            competition: STANDINGS_COMPETITION,
            leagueId: STANDINGS_LEAGUE_ID,
            season: row.season,
            teamId: row.team_id,
            delta: row.delta,
            effectiveTime: {
                kind: 'INTERVAL',
                lowerBoundUtc: row.effective_time_lower_bound,
                upperBoundUtc: row.effective_time_upper_bound,
            },
            sourceLineage: {
                evidence_file: 'administrative-adjustment-ledger.json',
                source_hash: row.source_hash,
                evidence_date: row.evidence_date,
                effective_time_precision: row.effective_time_precision,
                exact_effective_timestamp_proven: row.exact_effective_timestamp_proven,
                decision_type: row.decision_type,
            },
        };
    });
    return { value, rows, normalized, source_binding: { ...sourceBinding } };
}

function validateTargetClosure(document, scheduleClosure, normalized, sourceBinding) {
    const value = assertScope(document, TARGET_CLOSURE_SCHEMA, 'target closure audit');
    verifyContentBinding(value, sourceBinding, 'target closure audit');
    if (value.same_kickoff_fixtures_included !== false) {
        fail('target closure audit is not bound to the frozen strict-cutoff evidence', 'RULE_VERSION_UNPROVEN');
    }
    if (value.standings_position_representation !== 'COMPETITION_RANKING_SHARED_POSITION_WITH_GAPS') {
        fail('target closure tie representation differs', 'RULE_VERSION_UNPROVEN');
    }
    if (
        value.strict_cutoff_rule !== 'SOURCE_EVENT_TIME_LT_TARGET_KICKOFF' ||
        value.table_position_diff_sign_convention !== 'HOME_POSITION_MINUS_AWAY_POSITION'
    ) {
        fail('target closure cutoff or diff convention differs', 'RULE_VERSION_UNPROVEN');
    }
    const rows = assertArray(value.rows, 'target closure audit.rows', 'MISSING_PRIOR_RESULT_EVIDENCE');
    if (rows.length !== 888) fail('target closure population is not 888', 'MISSING_PRIOR_RESULT_EVIDENCE');
    const expectedCoverage = `${rows.filter(row => row.status === 'EVIDENCE_READY').length}/${rows.length}`;
    if (value.target_row_coverage !== expectedCoverage) {
        fail('target closure readiness coverage disagrees with its rows', 'MISSING_PRIOR_RESULT_EVIDENCE');
    }
    const officialById = new Map(scheduleClosure.rows.map(row => [row.canonical_match_id, row]));
    const seen = new Set();
    for (const [index, row] of rows.entries()) {
        const label = `target closure row[${index}]`;
        assertObject(row, label, 'MISSING_PRIOR_RESULT_EVIDENCE');
        assertKnownKeys(row, TARGET_FIELDS, label, 'MISSING_PRIOR_RESULT_EVIDENCE');
        assertRequiredKeys(row, TARGET_FIELDS, label, 'MISSING_PRIOR_RESULT_EVIDENCE');
        if (seen.has(row.canonical_match_id)) {
            fail(`duplicate target ${row.canonical_match_id}`, 'RESULT_IDENTITY_CONFLICT');
        }
        seen.add(row.canonical_match_id);
        const fixture = officialById.get(row.canonical_match_id);
        const result = normalized.byId.get(row.canonical_match_id);
        if (!fixture || !result) fail(`${label} is not bound to complete schedule/results`, 'RESULT_IDENTITY_CONFLICT');
        assertUtc(row.target_kickoff_utc, `${label}.target_kickoff_utc`);
        if (
            row.season !== fixture.season ||
            row.target_kickoff_utc.replace('.000Z', 'Z') !== fixture.canonical_scheduled_kickoff_utc ||
            row.canonical_match_id !== result.canonical_match_id
        ) {
            fail(`${label} target identity or kickoff conflicts`, 'RESULT_IDENTITY_CONFLICT');
        }
        if (
            row.competition_membership_closed !== true ||
            row.rule_version_proven !== true ||
            row.tie_representation_approved !== true ||
            row.target_match_result_used !== false ||
            row.future_result_used !== false ||
            row.same_kickoff_prior_result_used !== false ||
            row.final_table_used !== false ||
            row.provider_display_order_used !== false ||
            row.fabricated_position !== false
        ) {
            fail(`${label} contains a frozen evidence leakage flag`, 'DEPENDENCY_UNAVAILABLE');
        }
        assertArray(row.reason_codes, `${label}.reason_codes`, 'RULE_VERSION_UNPROVEN');
        assertInteger(row.prior_fixture_count, `${label}.prior_fixture_count`);
        assertSha(row.prior_fixture_ids_sha256, `${label}.prior_fixture_ids_sha256`);
    }
    return {
        value,
        rows,
        byId: new Map(rows.map(row => [row.canonical_match_id, row])),
        source_binding: { ...sourceBinding },
    };
}

function validateSeasonRuleMatrix(document, sourceBinding) {
    const value = assertObject(document, 'season rule matrix', 'RULE_VERSION_UNPROVEN');
    verifyContentBinding(value, sourceBinding, 'season rule matrix');
    if (!Array.isArray(value.season_rule_bindings) || !isPlainObject(value.scope)) {
        fail('season rule matrix schema is incomplete', 'RULE_VERSION_UNPROVEN');
    }
    if (
        value.scope.competition !== COMPETITION ||
        value.scope.league_id !== String(STANDINGS_LEAGUE_ID) ||
        stableStringify(sortedTextValues(value.scope.frozen_seasons, 'season rule matrix.scope.frozen_seasons')) !==
            stableStringify([...SEASONS].sort())
    ) {
        fail('season rule matrix scope is outside frozen v1', 'RULE_VERSION_UNPROVEN');
    }
    if (value.lifecycle !== 'current-state') {
        fail('season rule matrix lifecycle is not current-state', 'RULE_VERSION_UNPROVEN');
    }
    assertObject(value.owner_decision, 'season rule matrix.owner_decision', 'RULE_VERSION_UNPROVEN');
    if (
        value.owner_decision.standings_position_representation !== 'COMPETITION_RANKING_SHARED_POSITION_WITH_GAPS' ||
        value.scope.target_population !== 888 ||
        value.scope.canonical_schedule_count !== MASTER_COUNT
    ) {
        fail('season rule matrix does not bind frozen standings semantics', 'RULE_VERSION_UNPROVEN');
    }
    return { value, source_binding: { ...sourceBinding } };
}

function makeFixture(row, scheduleBinding) {
    return {
        canonicalMatchId: row.canonical_match_id,
        competition: STANDINGS_COMPETITION,
        leagueId: STANDINGS_LEAGUE_ID,
        season: row.season,
        homeTeamId: row.home_canonical_team_id,
        awayTeamId: row.away_canonical_team_id,
        scheduledKickoffUtc: row.canonical_scheduled_kickoff_utc,
        sourceLineage: {
            evidence_file: 'derived/official-fixture-projection.json',
            evidence_schema: OFFICIAL_SCHEMA,
            evidence_sha256: scheduleBinding.sha256,
            canonical_match_id: row.canonical_match_id,
            official_fixture_id: row.official_fixture_id,
            official_opta_fixture_id: row.official_opta_fixture_id,
            source_capture_id: row.source_capture_id,
            source_hash: row.source_hash,
            source_record_sha256: row.source_record_sha256,
            actual_event_time_proven: row.actual_event_time_proven,
        },
    };
}

function makeResult(row, official, normalizedBinding) {
    return {
        canonicalMatchId: row.canonical_match_id,
        competition: STANDINGS_COMPETITION,
        leagueId: STANDINGS_LEAGUE_ID,
        season: row.season,
        homeTeamId: row.home_canonical_team_id,
        awayTeamId: row.away_canonical_team_id,
        actualEligibleEventTimeUtc: row.actual_kickoff_utc,
        disposition: row.event_status === 'REPLAYED_COMPLETED' ? 'REPLAYED' : 'COMPLETED',
        tableEligibility: row.result_eligible_for_table === 'YES' ? 'ELIGIBLE' : 'NOT_ELIGIBLE',
        finalityStatus: row.result_finality_status === 'OFFICIAL_STATUS_C_PHASE_F_FINAL' ? 'FINAL' : 'UNKNOWN',
        homeScore: row.home_score,
        awayScore: row.away_score,
        sourceLineage: {
            evidence_file: 'normalized-prior-result-ledger.json',
            evidence_schema: NORMALIZED_SCHEMA,
            evidence_sha256: normalizedBinding.sha256,
            canonical_match_id: row.canonical_match_id,
            source_hash: row.source_hash,
            source_record_sha256: row.source_record_sha256,
            source_identity: row.source_identity,
            linkage_proof: row.linkage_proof,
            newly_acquired_result_fact: row.newly_acquired_result_fact,
            newly_acquired_event_time_fact: row.newly_acquired_event_time_fact,
            reason_code: row.reason_code,
            actual_event_time_utc: row.actual_kickoff_utc,
            original_scheduled_time_not_used: true,
            official_schedule_source_record_sha256: official.source_record_sha256,
        },
        // The abandoned original has no canonical fixture ID in the frozen
        // official schedule. The exception audit proves the replay replaces it.
        replayOfMatchId: null,
    };
}

function makeTarget(row, fixture, normalized, targetBinding) {
    return {
        canonicalMatchId: row.canonical_match_id,
        competition: STANDINGS_COMPETITION,
        leagueId: STANDINGS_LEAGUE_ID,
        season: row.season,
        homeTeamId: fixture.home_canonical_team_id,
        awayTeamId: fixture.away_canonical_team_id,
        targetKickoffUtc: row.target_kickoff_utc,
        sourceLineage: {
            evidence_file: 'target-closure-audit.json',
            evidence_schema: TARGET_CLOSURE_SCHEMA,
            evidence_sha256: targetBinding.sha256,
            canonical_match_id: row.canonical_match_id,
            target_status: row.status,
            evidence_reason_codes: row.reason_codes,
            prior_fixture_count: row.prior_fixture_count,
            normalized_result_source_record_sha256: normalized.source_record_sha256,
            target_cutoff_rule: 'SOURCE_EVENT_TIME_LT_TARGET_KICKOFF',
        },
    };
}

function buildHistoricalStandingsEvidenceInputs({
    registry,
    officialFixtureProjection,
    normalizedPriorResultLedger,
    missingPriorFixtureLedger,
    postponedRescheduledAudit,
    exceptionStatusAudit,
    administrativeAdjustmentLedger,
    targetClosureAudit,
    seasonRuleMatrix,
    sourceBindings,
}) {
    const contractBinding = bindFrozenStandingsContract(registry);
    if (
        contractBinding.contract_id !== STANDINGS_CONTRACT_ID ||
        contractBinding.version !== STANDINGS_CONTRACT_VERSION ||
        contractBinding.competition !== STANDINGS_COMPETITION ||
        contractBinding.league_id !== STANDINGS_LEAGUE_ID ||
        stableStringify(contractBinding.frozen_seasons) !== stableStringify(STANDINGS_SEASONS)
    ) {
        fail('frozen standings contract binding is incompatible', 'RULE_VERSION_UNPROVEN');
    }
    const bindings = assertSourceBindings(sourceBindings);
    const schedule = proveCanonicalScheduleClosure(officialFixtureProjection, bindings.official_fixture_projection);
    const normalized = reconcileNormalizedResults(
        normalizedPriorResultLedger,
        schedule,
        bindings.normalized_prior_result_ledger
    );
    const missing = validateMissingPriorLedger(
        missingPriorFixtureLedger,
        schedule,
        normalized,
        bindings.missing_prior_fixture_ledger
    );
    const postponed = validatePostponedAudit(postponedRescheduledAudit, bindings.postponed_rescheduled_audit);
    const exceptions = validateExceptionAudit(exceptionStatusAudit, schedule, bindings.exception_status_audit);
    const adjustments = validateAdministrativeAdjustments(
        administrativeAdjustmentLedger,
        schedule,
        bindings.administrative_adjustment_ledger
    );
    const targets = validateTargetClosure(targetClosureAudit, schedule, normalized, bindings.target_closure_audit);
    const seasonRules = validateSeasonRuleMatrix(seasonRuleMatrix, bindings.season_rule_matrix);

    const fixturesBySeason = Object.fromEntries(
        SEASONS.map(season => [
            season,
            schedule.rows
                .filter(row => row.season === season)
                .map(row => makeFixture(row, bindings.official_fixture_projection)),
        ])
    );
    const resultsBySeason = Object.fromEntries(
        SEASONS.map(season => [
            season,
            normalized.rows
                .filter(row => row.season === season)
                .map(row =>
                    makeResult(
                        row,
                        schedule.rows.find(fixture => fixture.canonical_match_id === row.canonical_match_id),
                        bindings.normalized_prior_result_ledger
                    )
                ),
        ])
    );
    const adjustmentsBySeason = Object.fromEntries(
        SEASONS.map(season => [season, adjustments.normalized.filter(row => row.season === season)])
    );
    const targetInputs = targets.rows.map(row => {
        const fixture = schedule.rows.find(candidate => candidate.canonical_match_id === row.canonical_match_id);
        const result = normalized.byId.get(row.canonical_match_id);
        return {
            contractBinding,
            competition: STANDINGS_COMPETITION,
            leagueId: STANDINGS_LEAGUE_ID,
            season: row.season,
            teamUniverse: schedule.season_team_ids[row.season],
            fixtures: fixturesBySeason[row.season],
            results: resultsBySeason[row.season],
            administrativeAdjustments: adjustmentsBySeason[row.season],
            target: makeTarget(row, fixture, result, bindings.target_closure_audit),
        };
    });
    const resultLineageById = Object.fromEntries(
        normalized.rows.map(row => [
            row.canonical_match_id,
            {
                source_record_sha256: row.source_record_sha256,
                source_hash: row.source_hash,
                season: row.season,
                actual_event_time_utc: row.actual_kickoff_utc,
                evidence_file: 'normalized-prior-result-ledger.json',
                newly_acquired_result_fact: row.newly_acquired_result_fact,
                newly_acquired_event_time_fact: row.newly_acquired_event_time_fact,
                original_scheduled_time_not_used: true,
            },
        ])
    );
    const adjustmentLineageById = Object.fromEntries(
        adjustments.normalized.map(row => [row.adjustmentId, { ...row.sourceLineage }])
    );
    const targetLineageById = Object.fromEntries(
        targets.rows.map(row => [
            row.canonical_match_id,
            {
                evidence_file: 'target-closure-audit.json',
                target_status: row.status,
                target_reason_codes: [...row.reason_codes].sort((left, right) => left.localeCompare(right)),
                target_kickoff_utc: row.target_kickoff_utc,
            },
        ])
    );
    return Object.freeze({
        contractBinding,
        inputs: targetInputs,
        scheduleClosure: schedule,
        reconciliation: {
            canonical_fixture_count: schedule.rows.length,
            normalized_result_count: normalized.rows.length,
            remediation_result_count: missing.rows.length,
            target_count: targets.rows.length,
            postponed_actual_time_complete: postponed.value.actual_event_time_complete_fixture_count === MASTER_COUNT,
            exception_policy_proven: exceptions.value.exception_policy_proven,
            administrative_adjustment_count: adjustments.rows.length,
            season_rule_schema: 'season-rule-matrix/current-state',
        },
        sourceBindings: bindings,
        lineage: {
            resultByMatchId: resultLineageById,
            adjustmentById: adjustmentLineageById,
            targetByMatchId: targetLineageById,
        },
        evidence: {
            missingPrior: missing.rows,
            targetClosure: targets.rows,
        },
    });
}

module.exports = {
    ADMIN_SCHEMA,
    EXCEPTION_SCHEMA,
    FrozenEvidenceAdapterError,
    MISSING_SCHEMA,
    NORMALIZED_SCHEMA,
    OFFICIAL_SCHEMA,
    POSTPONED_SCHEMA,
    TARGET_CLOSURE_SCHEMA,
    buildHistoricalStandingsEvidenceInputs,
    computeEvidenceContentDigest,
    proveCanonicalScheduleClosure,
};
