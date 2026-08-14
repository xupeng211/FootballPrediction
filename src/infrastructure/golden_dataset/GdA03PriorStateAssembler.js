'use strict';

/* eslint-disable max-lines -- one canonical in-memory feature assembler keeps all derivations together. */

// lifecycle: permanent
// GD-A03 纯内存 prior-state assembler。文件读取、上游 artifact 校验和输出写盘
// 位于 scripts/ops/gd_a03_assembler.js；本模块不联网、不连接 DB、不写 raw/L3，
// 也不读取 SchemaManager 的兼容 proxy/default 实现。

const {
    FEATURE_AVAILABILITY,
    FEATURE_CUTOFF_POLICY,
    FEATURE_CUTOFF_RELATION,
    FATIGUE_LOOKBACK_DAYS,
    GdA03ContractError,
    PRIOR_STATE_ARTIFACT_SCHEMA_VERSION,
    PRIOR_STATE_LINEAGE_CONTRACT_VERSION,
    PRIOR_STATE_RECEIPT_SCHEMA_VERSION,
    PRIOR_STATE_STAGE,
    REASON_CODES,
    REQUIRED_ROLLING_HISTORY_COUNT,
    SEMANTICS_STATUS,
    assertFiniteNumber,
    assertObject,
    assertSha,
    assertText,
    computeBusinessHash,
    computeProvenanceDigest,
    featureSemanticsInOrder,
    stableStringify,
    validateFeatureContract,
} = require('./GdA03PriorStateContract');
const { admittedIdSetHash, sha256Bytes } = require('./GdA01AssemblyContract');

const SCHEDULE_SCHEMA_VERSION = 'candidate-match-identity/v1';
const SCHEDULE_AUTHORITY_VERSION = 'canonical-schedule-history/v1';
const FACT_TIMING_CLASS = 'POSTMATCH_ONLY';
const TRAINING_LABEL_ROLE = 'TRAINING_LABEL_POSTMATCH';
const NUMERIC_PARITY = Object.freeze({
    canonical_20_name_order_parity: true,
    train_gd_a03_numeric_semantics_proven: 'PARTIAL',
    runtime_numeric_semantics_proven: 'NO',
    train_inference_numeric_parity: 'NOT_PROVEN',
});

function fail(message, code = 'GD_A03_CONTRACT_INVALID') {
    throw new GdA03ContractError(message, code);
}

function assertArray(value, label) {
    if (!Array.isArray(value)) fail(`${label} must be an array`, 'SCHEMA_MISMATCH');
    return value;
}

function parseTimestamp(value, label) {
    assertText(value, label);
    const milliseconds = Date.parse(value);
    if (!Number.isFinite(milliseconds)) fail(`${label} must be an absolute timestamp`, 'FACT_VALUE_INVALID');
    return milliseconds;
}

function dedupeSorted(values) {
    return [...new Set(values)].sort((left, right) => left.localeCompare(right));
}

function uniqueReasons(reasons) {
    return [...new Set(reasons.filter(Boolean))].sort((left, right) => left.localeCompare(right));
}

function normalizeScheduleCandidate(candidate, index) {
    assertObject(candidate, `schedule candidate[${index}]`);
    const fields = [
        'id',
        'source_provider',
        'source_match_id',
        'competition',
        'season',
        'home_team',
        'away_team',
        'kickoff_at',
    ];
    for (const field of fields) assertText(candidate[field], `schedule candidate[${index}].${field}`);
    if (candidate.source_provider !== 'FotMob') {
        fail(`schedule candidate[${index}] provider is unsupported`, 'IDENTITY_CONFLICT');
    }
    if (candidate.competition !== 'Premier League') {
        fail(`schedule candidate[${index}] competition is unsupported`, 'IDENTITY_CONFLICT');
    }
    if (candidate.home_team === candidate.away_team) {
        fail(`schedule candidate[${index}] home/away identity collision`, 'IDENTITY_CONFLICT');
    }
    const kickoffMs = parseTimestamp(candidate.kickoff_at, `schedule candidate[${index}].kickoff_at`);
    return {
        id: candidate.id,
        source_provider: candidate.source_provider,
        source_match_id: candidate.source_match_id,
        competition: candidate.competition,
        season: candidate.season,
        home_team: candidate.home_team,
        away_team: candidate.away_team,
        kickoff_at: candidate.kickoff_at,
        kickoff_ms: kickoffMs,
    };
}

function normalizeSchedule(scheduleCandidates) {
    const normalized = assertArray(scheduleCandidates, 'schedule candidates').map(normalizeScheduleCandidate);
    const seen = new Set();
    const sourceIds = new Set();
    for (const candidate of normalized) {
        if (seen.has(candidate.id)) fail(`duplicate schedule canonical ID ${candidate.id}`, 'POPULATION_MISMATCH');
        if (sourceIds.has(candidate.source_match_id)) {
            fail(`duplicate schedule source ID ${candidate.source_match_id}`, 'POPULATION_MISMATCH');
        }
        seen.add(candidate.id);
        sourceIds.add(candidate.source_match_id);
    }
    return normalized.sort(compareSchedule);
}

function compareSchedule(left, right) {
    return (
        left.season.localeCompare(right.season) ||
        left.kickoff_at.localeCompare(right.kickoff_at) ||
        left.id.localeCompare(right.id)
    );
}

function normalizeIdentityRow(row, label) {
    assertObject(row, label);
    for (const field of ['canonical_match_id', 'competition', 'season', 'home_team', 'away_team', 'kickoff_at']) {
        assertText(row[field], `${label}.${field}`);
    }
    return {
        canonical_match_id: row.canonical_match_id,
        competition: row.competition,
        season: row.season,
        home_team: row.home_team,
        away_team: row.away_team,
        kickoff_at: row.kickoff_at,
        source_match_id: row.source_match_id || null,
        kickoff_ms: parseTimestamp(row.kickoff_at, `${label}.kickoff_at`),
    };
}

function normalizeTargetRows(targetRows) {
    const rows = assertArray(targetRows, 'GD-A01 target rows').map((row, index) =>
        normalizeIdentityRow(row, `GD-A01 row[${index}]`)
    );
    const seen = new Set();
    for (const row of rows) {
        if (seen.has(row.canonical_match_id)) {
            fail(`duplicate target ID ${row.canonical_match_id}`, 'POPULATION_MISMATCH');
        }
        seen.add(row.canonical_match_id);
    }
    return rows.sort((left, right) => left.canonical_match_id.localeCompare(right.canonical_match_id));
}

function normalizeFactRow(row, label) {
    const normalized = normalizeIdentityRow(row, label);
    assertObject(row.facts, `${label}.facts`);
    assertObject(row.facts.match_result, `${label}.facts.match_result`);
    assertObject(row.facts.xg, `${label}.facts.xg`);
    if (!row.provenance || typeof row.provenance !== 'object' || Array.isArray(row.provenance)) {
        fail(`${label}.provenance is required`, 'PROVENANCE_INVALID');
    }
    const result = row.facts.match_result;
    if (!['AVAILABLE', 'UNAVAILABLE'].includes(result.status)) {
        fail(`${label}.match_result.status is invalid`, 'FACT_VALUE_INVALID');
    }
    if (result.status === 'AVAILABLE') {
        if (!['home', 'draw', 'away'].includes(result.outcome)) {
            fail(`${label}.match_result.outcome is invalid`, 'FACT_VALUE_INVALID');
        }
        if (!Number.isSafeInteger(result.home_score) || result.home_score < 0) {
            fail(`${label}.match_result.home_score is invalid`, 'FACT_VALUE_INVALID');
        }
        if (!Number.isSafeInteger(result.away_score) || result.away_score < 0) {
            fail(`${label}.match_result.away_score is invalid`, 'FACT_VALUE_INVALID');
        }
    }
    return {
        ...normalized,
        facts: row.facts,
        provenance: row.provenance,
        source_linkage: row.source_linkage || null,
    };
}

function normalizeFactRows(factRows) {
    const rows = assertArray(factRows, 'GD-A02 fact rows').map((row, index) =>
        normalizeFactRow(row, `GD-A02 row[${index}]`)
    );
    const byId = new Map();
    for (const row of rows) {
        if (byId.has(row.canonical_match_id)) {
            fail(`duplicate fact ID ${row.canonical_match_id}`, 'POPULATION_MISMATCH');
        }
        byId.set(row.canonical_match_id, row);
    }
    return byId;
}

function validateScheduleClosure(schedule, closure) {
    assertObject(closure, 'schedule closure');
    if (closure.schema_version !== SCHEDULE_AUTHORITY_VERSION) {
        fail('schedule closure schema is unsupported', 'SCHEMA_MISMATCH');
    }
    if (closure.status !== 'PROVEN') fail('schedule closure must be PROVEN', 'HISTORY_CLOSURE_INVALID');
    assertText(closure.authority, 'schedule closure authority');
    assertObject(closure.per_season_expected_counts, 'schedule closure per_season_expected_counts');
    const actualCounts = {};
    for (const candidate of schedule) actualCounts[candidate.season] = (actualCounts[candidate.season] || 0) + 1;
    if (stableStringify(actualCounts) !== stableStringify(closure.per_season_expected_counts)) {
        fail('schedule closure counts do not match the canonical schedule', 'HISTORY_CLOSURE_INVALID');
    }
    return {
        schema_version: closure.schema_version,
        status: closure.status,
        authority: closure.authority,
        per_season_expected_counts: { ...closure.per_season_expected_counts },
    };
}

function validateSourceBindings(sourceBindings) {
    assertObject(sourceBindings, 'GD-A03 source_bindings');
    for (const [name, binding] of Object.entries(sourceBindings)) {
        assertObject(binding, `GD-A03 source_bindings.${name}`);
        if (binding.sha256 !== undefined) assertSha(binding.sha256, `GD-A03 source_bindings.${name}.sha256`);
        if (binding.business_hash !== undefined) {
            assertSha(binding.business_hash, `GD-A03 source_bindings.${name}.business_hash`);
        }
    }
    return sourceBindings;
}

function makeSourceIdentity(candidate) {
    return {
        canonical_match_id: candidate.id,
        source_match_id: candidate.source_match_id,
        season: candidate.season,
        home_team: candidate.home_team,
        away_team: candidate.away_team,
        kickoff_at: candidate.kickoff_at,
    };
}

function sourceKickoff(sourceMatches) {
    if (sourceMatches.length === 0) return null;
    return sourceMatches.reduce((latest, match) => (match.kickoff_ms > latest.kickoff_ms ? match : latest)).kickoff_at;
}

function featureLine({
    featureName,
    target,
    sourceMatches,
    sourceEvidence = [],
    value = null,
    reasons = [],
    derivation,
    sourceFields = [],
    sourceProjections = [],
}) {
    const cutoff = target.kickoff_at;
    const maxSourceTime = sourceKickoff(sourceMatches);
    const cutoffPassed = maxSourceTime === null || Date.parse(maxSourceTime) < Date.parse(cutoff);
    if (!cutoffPassed) fail(`${featureName} has a non-strict source cutoff`, 'CUTOFF_VIOLATION');
    if (value !== null) assertFiniteNumber(value, `${featureName}.value`);
    const availabilityStatus = value === null ? FEATURE_AVAILABILITY.UNAVAILABLE : FEATURE_AVAILABILITY.AVAILABLE;
    const unavailableReasonCodes = availabilityStatus === FEATURE_AVAILABILITY.AVAILABLE ? [] : uniqueReasons(reasons);
    if (availabilityStatus === FEATURE_AVAILABILITY.UNAVAILABLE && unavailableReasonCodes.length === 0) {
        fail(`${featureName} unavailable line must carry a reason`, 'SCHEMA_MISMATCH');
    }
    const sourceIdentities = sourceMatches.map(makeSourceIdentity);
    const provenanceDigest = computeProvenanceDigest({
        lineage_contract_version: PRIOR_STATE_LINEAGE_CONTRACT_VERSION,
        feature_name: featureName,
        target_match_id: target.canonical_match_id,
        target_cutoff: cutoff,
        source_match_ids: sourceMatches.map(match => match.id),
        source_evidence_match_ids: sourceEvidence.map(match => match.id),
        source_fields: [...sourceFields],
        source_projections: sourceProjections,
        derivation,
        unavailable_reason_codes: unavailableReasonCodes,
    });
    return {
        value,
        availability_status: availabilityStatus,
        source_match_ids: sourceMatches.map(match => match.id),
        source_identities: sourceIdentities,
        source_evidence_match_ids: sourceEvidence.map(match => match.id),
        latest_source_kickoff: maxSourceTime,
        derivation_contract: `${PRIOR_STATE_LINEAGE_CONTRACT_VERSION}:${derivation}`,
        source_fields: [...sourceFields],
        provenance_inputs: sourceProjections,
        cutoff_proof: {
            source_time_basis: 'MATCH_KICKOFF',
            relation: FEATURE_CUTOFF_RELATION,
            target_cutoff: cutoff,
            max_source_time: maxSourceTime,
            passed: cutoffPassed,
        },
        provenance_digest: provenanceDigest,
        unavailable_reason_codes: unavailableReasonCodes,
    };
}

function indexById(values) {
    return new Map(values.map(value => [value.id, value]));
}

function buildIndexes(schedule) {
    const byId = indexById(schedule);
    const byTeamSeason = new Map();
    const add = (key, candidate) => {
        const list = byTeamSeason.get(key) || [];
        list.push(candidate);
        byTeamSeason.set(key, list);
    };
    for (const candidate of schedule) {
        add(`${candidate.season}\u0000${candidate.home_team}`, candidate);
        add(`${candidate.season}\u0000${candidate.away_team}`, candidate);
    }
    for (const list of byTeamSeason.values()) list.sort(compareSchedule);
    return { byId, byTeamSeason };
}

function priorTeamMatches(indexes, target, teamName) {
    return (indexes.byTeamSeason.get(`${target.season}\u0000${teamName}`) || []).filter(
        candidate => candidate.kickoff_ms < target.kickoff_ms
    );
}

function priorLeagueMatches(schedule, target) {
    return schedule.filter(candidate => candidate.season === target.season && candidate.kickoff_ms < target.kickoff_ms);
}

function previousWindow(matches, count) {
    return matches.slice(Math.max(0, matches.length - count));
}

function teamSide(candidate, teamName) {
    if (candidate.home_team === teamName) return 'home';
    if (candidate.away_team === teamName) return 'away';
    fail(`team ${teamName} is not present in source ${candidate.id}`, 'IDENTITY_CONFLICT');
}

function getFactForSource(factsById, candidate, target, featureName) {
    const fact = factsById.get(candidate.id);
    if (!fact) return null;
    if (
        fact.home_team !== candidate.home_team ||
        fact.away_team !== candidate.away_team ||
        fact.kickoff_at !== candidate.kickoff_at ||
        fact.competition !== candidate.competition ||
        fact.season !== candidate.season
    ) {
        fail(`${featureName} source identity mismatch for ${candidate.id}`, 'IDENTITY_CONFLICT');
    }
    if (candidate.id === target.canonical_match_id) {
        fail(`${featureName} attempted target-match dependency`, 'TARGET_MATCH_LEAK');
    }
    if (!(candidate.kickoff_ms < target.kickoff_ms)) {
        fail(`${featureName} attempted future/equal dependency`, 'CUTOFF_VIOLATION');
    }
    return fact;
}

function resultPointsForTeam(fact, candidate, teamName) {
    if (!fact || fact.facts.match_result.status !== 'AVAILABLE') return null;
    const outcome = fact.facts.match_result.outcome;
    const side = teamSide(candidate, teamName);
    if (outcome === 'draw') return 1;
    if (outcome === side) return 3;
    return 0;
}

function factProvenanceProjection(fact, field) {
    return {
        canonical_match_id: fact.canonical_match_id,
        field,
        provenance: fact.provenance,
    };
}

function xgForTeam(fact, candidate, teamName) {
    const side = teamSide(candidate, teamName);
    const projection = fact?.facts?.xg?.[side];
    if (
        !projection ||
        projection.status !== 'COMPLETE' ||
        typeof projection.value !== 'number' ||
        !Number.isFinite(projection.value)
    ) {
        return null;
    }
    return projection.value;
}

function buildRollingXgLine({ featureName, target, teamName, matches, factsById }) {
    const sourceMatches = previousWindow(matches, REQUIRED_ROLLING_HISTORY_COUNT);
    const reasons = [];
    if (sourceMatches.length < REQUIRED_ROLLING_HISTORY_COUNT) reasons.push(REASON_CODES.INSUFFICIENT_HISTORY);
    const evidence = [];
    const values = [];
    const projections = [];
    for (const candidate of sourceMatches) {
        const fact = getFactForSource(factsById, candidate, target, featureName);
        const value = xgForTeam(fact, candidate, teamName);
        if (fact && value !== null) {
            evidence.push(candidate);
            values.push(value);
            projections.push(factProvenanceProjection(fact, `facts.xg.${teamSide(candidate, teamName)}.value`));
        } else {
            reasons.push(REASON_CODES.HISTORY_GAP, REASON_CODES.NO_PROVEN_SOURCE_FACT);
        }
    }
    if (sourceMatches.length === REQUIRED_ROLLING_HISTORY_COUNT && values.length === REQUIRED_ROLLING_HISTORY_COUNT) {
        return featureLine({
            featureName,
            target,
            sourceMatches,
            sourceEvidence: evidence,
            value: values.reduce((sum, item) => sum + item, 0) / values.length,
            derivation: 'mean_exact_previous_5_complete_team_xg',
            sourceFields: ['facts.xg.<team_side>.value'],
            sourceProjections: projections,
        });
    }
    return featureLine({
        featureName,
        target,
        sourceMatches,
        sourceEvidence: evidence,
        reasons,
        derivation: 'mean_exact_previous_5_complete_team_xg',
        sourceFields: ['facts.xg.<team_side>.value'],
        sourceProjections: projections,
    });
}

function buildNoNumericRollingLine({ featureName, target, matches, reason = REASON_CODES.NO_PROVEN_SOURCE_FACT }) {
    const sourceMatches = previousWindow(matches, REQUIRED_ROLLING_HISTORY_COUNT);
    const reasons = [reason];
    if (sourceMatches.length < REQUIRED_ROLLING_HISTORY_COUNT) reasons.push(REASON_CODES.INSUFFICIENT_HISTORY);
    return featureLine({
        featureName,
        target,
        sourceMatches,
        reasons,
        derivation: 'unavailable_no_proven_numeric_source',
        sourceFields: ['no_proven_numeric_source_field'],
    });
}

function buildUnprovenRatingLine({ featureName, target, matches }) {
    const sourceMatches = previousWindow(matches, REQUIRED_ROLLING_HISTORY_COUNT);
    const reasons = [REASON_CODES.SEMANTICS_UNPROVEN];
    if (sourceMatches.length < REQUIRED_ROLLING_HISTORY_COUNT) reasons.push(REASON_CODES.INSUFFICIENT_HISTORY);
    return featureLine({
        featureName,
        target,
        sourceMatches,
        reasons,
        derivation: 'unavailable_rating_semantics_unproven',
        sourceFields: ['no_frozen_rating_formula'],
    });
}

function buildTeamPointsLine({ featureName, target, teamName, matches, factsById }) {
    const sourceMatches = matches;
    const evidence = [];
    const projections = [];
    let value = 0;
    const reasons = [];
    for (const candidate of sourceMatches) {
        const fact = getFactForSource(factsById, candidate, target, featureName);
        const points = resultPointsForTeam(fact, candidate, teamName);
        if (points === null) {
            reasons.push(REASON_CODES.HISTORY_GAP, REASON_CODES.STANDINGS_HISTORY_GAP);
            continue;
        }
        value += points;
        evidence.push(candidate);
        projections.push(factProvenanceProjection(fact, 'facts.match_result.outcome'));
    }
    if (reasons.length > 0) {
        return featureLine({
            featureName,
            target,
            sourceMatches,
            sourceEvidence: evidence,
            reasons,
            derivation: 'sum_prior_result_points_3_1_0',
            sourceFields: ['facts.match_result.outcome'],
            sourceProjections: projections,
        });
    }
    return featureLine({
        featureName,
        target,
        sourceMatches,
        sourceEvidence: evidence,
        value,
        derivation: 'sum_prior_result_points_3_1_0',
        sourceFields: ['facts.match_result.outcome'],
        sourceProjections: projections,
    });
}

function buildRecentFormLine({ featureName, target, teamName, matches, factsById }) {
    const sourceMatches = previousWindow(matches, REQUIRED_ROLLING_HISTORY_COUNT);
    const reasons = [];
    const evidence = [];
    const projections = [];
    let value = 0;
    if (sourceMatches.length < REQUIRED_ROLLING_HISTORY_COUNT) reasons.push(REASON_CODES.INSUFFICIENT_HISTORY);
    for (const candidate of sourceMatches) {
        const fact = getFactForSource(factsById, candidate, target, featureName);
        const points = resultPointsForTeam(fact, candidate, teamName);
        if (points === null) {
            reasons.push(REASON_CODES.HISTORY_GAP);
            continue;
        }
        value += points;
        evidence.push(candidate);
        projections.push(factProvenanceProjection(fact, 'facts.match_result.outcome'));
    }
    if (sourceMatches.length !== REQUIRED_ROLLING_HISTORY_COUNT || reasons.length > 0) {
        return featureLine({
            featureName,
            target,
            sourceMatches,
            sourceEvidence: evidence,
            reasons,
            derivation: 'sum_exact_previous_5_result_points_3_1_0',
            sourceFields: ['facts.match_result.outcome'],
            sourceProjections: projections,
        });
    }
    return featureLine({
        featureName,
        target,
        sourceMatches,
        sourceEvidence: evidence,
        value,
        derivation: 'sum_exact_previous_5_result_points_3_1_0',
        sourceFields: ['facts.match_result.outcome'],
        sourceProjections: projections,
    });
}

function unionMatches(...lines) {
    const byId = new Map();
    for (const line of lines) {
        for (const identity of line.source_identities) {
            byId.set(identity.canonical_match_id, {
                id: identity.canonical_match_id,
                source_match_id: identity.source_match_id,
                competition: 'Premier League',
                season: identity.season,
                home_team: identity.home_team,
                away_team: identity.away_team,
                kickoff_at: identity.kickoff_at,
                kickoff_ms: Date.parse(identity.kickoff_at),
            });
        }
    }
    return [...byId.values()].sort(compareSchedule);
}

function deriveLine({ featureName, target, left, right, operation, derivation }) {
    const sourceMatches = unionMatches(left, right);
    const reasons = [...left.unavailable_reason_codes, ...right.unavailable_reason_codes];
    if (left.value === null || right.value === null) {
        reasons.push(REASON_CODES.DEPENDENCY_UNAVAILABLE);
        return featureLine({
            featureName,
            target,
            sourceMatches,
            reasons,
            derivation,
            sourceFields: [left.derivation_contract, right.derivation_contract],
            sourceProjections: [left.provenance_digest, right.provenance_digest],
        });
    }
    return featureLine({
        featureName,
        target,
        sourceMatches,
        value: operation(left.value, right.value),
        derivation,
        sourceFields: [left.derivation_contract, right.derivation_contract],
        sourceProjections: [left.provenance_digest, right.provenance_digest],
    });
}

function buildTablePositionLine({ featureName, target, schedule, factsById }) {
    const sourceMatches = priorLeagueMatches(schedule, target);
    const evidence = [];
    const projections = [];
    const reasons = [REASON_CODES.SEMANTICS_UNPROVEN, REASON_CODES.STANDINGS_TIEBREAK_UNPROVEN];
    for (const candidate of sourceMatches) {
        const fact = getFactForSource(factsById, candidate, target, featureName);
        if (!fact || fact.facts.match_result.status !== 'AVAILABLE') reasons.push(REASON_CODES.STANDINGS_HISTORY_GAP);
        else {
            evidence.push(candidate);
            projections.push(factProvenanceProjection(fact, 'facts.match_result.home_score/away_score'));
        }
    }
    return featureLine({
        featureName,
        target,
        sourceMatches,
        sourceEvidence: evidence,
        reasons,
        derivation: 'unavailable_exact_prior_table_position_tiebreak_unproven',
        sourceFields: ['facts.match_result.home_score', 'facts.match_result.away_score', 'frozen_tiebreak_contract'],
        sourceProjections: projections,
    });
}

function buildEloLine({ featureName, target, homeMatches, awayMatches, factsById }) {
    const sourceMatches = unionMatches(
        featureLine({
            featureName,
            target,
            sourceMatches: homeMatches,
            reasons: [REASON_CODES.ELO_INITIAL_STATE_UNPROVEN],
            derivation: 'unavailable_elo_semantics_unproven',
            sourceFields: ['prior_result_universe'],
        }),
        featureLine({
            featureName,
            target,
            sourceMatches: awayMatches,
            reasons: [REASON_CODES.ELO_INITIAL_STATE_UNPROVEN],
            derivation: 'unavailable_elo_semantics_unproven',
            sourceFields: ['prior_result_universe'],
        })
    );
    const evidence = [];
    const projections = [];
    const reasons = [REASON_CODES.ELO_INITIAL_STATE_UNPROVEN, REASON_CODES.SEMANTICS_UNPROVEN];
    for (const candidate of sourceMatches) {
        const fact = getFactForSource(factsById, candidate, target, featureName);
        if (!fact || fact.facts.match_result.status !== 'AVAILABLE') reasons.push(REASON_CODES.ELO_HISTORY_GAP);
        else {
            evidence.push(candidate);
            projections.push(factProvenanceProjection(fact, 'facts.match_result.outcome'));
        }
    }
    return featureLine({
        featureName,
        target,
        sourceMatches,
        sourceEvidence: evidence,
        reasons,
        derivation: 'unavailable_elo_initialization_and_history_unproven',
        sourceFields: ['complete_prior_result_universe', 'frozen_elo_initialization', 'frozen_elo_algorithm'],
        sourceProjections: projections,
    });
}

function buildFatigueLine({ featureName, target, teamName, matches, closure, sourceBinding }) {
    const cutoffMs = target.kickoff_ms;
    const startMs = cutoffMs - FATIGUE_LOOKBACK_DAYS * 24 * 60 * 60 * 1000;
    const sourceMatches = matches.filter(
        candidate => candidate.kickoff_ms >= startMs && candidate.kickoff_ms < cutoffMs
    );
    const value = Math.min(1, sourceMatches.length / FATIGUE_LOOKBACK_DAYS);
    return featureLine({
        featureName,
        target,
        sourceMatches,
        value,
        derivation: 'capped_prior_7_day_scheduled_match_count_divided_by_7',
        sourceFields: ['canonical_schedule.kickoff_at', 'canonical_schedule.team_identity'],
        sourceProjections: [
            {
                authority: closure.authority,
                closure_schema: closure.schema_version,
                schedule_sha256: sourceBinding?.sha256 || null,
                team_name: teamName,
                window_start_exclusive: new Date(startMs).toISOString(),
                window_end_exclusive: target.kickoff_at,
            },
        ],
    });
}

function buildTargetFeatures({ target, schedule, factsById, indexes, closure, sourceBindings }) {
    const homeMatches = priorTeamMatches(indexes, target, target.home_team);
    const awayMatches = priorTeamMatches(indexes, target, target.away_team);
    const homeXg = buildRollingXgLine({
        featureName: 'rolling_xg_home',
        target,
        teamName: target.home_team,
        matches: homeMatches,
        factsById,
    });
    const awayXg = buildRollingXgLine({
        featureName: 'rolling_xg_away',
        target,
        teamName: target.away_team,
        matches: awayMatches,
        factsById,
    });
    const homePoints = buildTeamPointsLine({
        featureName: 'home_points',
        target,
        teamName: target.home_team,
        matches: homeMatches,
        factsById,
    });
    const awayPoints = buildTeamPointsLine({
        featureName: 'away_points',
        target,
        teamName: target.away_team,
        matches: awayMatches,
        factsById,
    });
    const featureByName = {
        rolling_xg_home: homeXg,
        rolling_xg_away: awayXg,
        rolling_shots_on_target_home: buildNoNumericRollingLine({
            featureName: 'rolling_shots_on_target_home',
            target,
            matches: homeMatches,
        }),
        rolling_shots_on_target_away: buildNoNumericRollingLine({
            featureName: 'rolling_shots_on_target_away',
            target,
            matches: awayMatches,
        }),
        rolling_possession_home: buildNoNumericRollingLine({
            featureName: 'rolling_possession_home',
            target,
            matches: homeMatches,
        }),
        rolling_possession_away: buildNoNumericRollingLine({
            featureName: 'rolling_possession_away',
            target,
            matches: awayMatches,
        }),
        rolling_team_rating_home: buildUnprovenRatingLine({
            featureName: 'rolling_team_rating_home',
            target,
            matches: homeMatches,
        }),
        rolling_team_rating_away: buildUnprovenRatingLine({
            featureName: 'rolling_team_rating_away',
            target,
            matches: awayMatches,
        }),
        home_table_position: buildTablePositionLine({
            featureName: 'home_table_position',
            target,
            schedule,
            factsById,
        }),
        away_table_position: buildTablePositionLine({
            featureName: 'away_table_position',
            target,
            schedule,
            factsById,
        }),
        home_points: homePoints,
        away_points: awayPoints,
        home_recent_form_points: buildRecentFormLine({
            featureName: 'home_recent_form_points',
            target,
            teamName: target.home_team,
            matches: homeMatches,
            factsById,
        }),
        raw_elo_gap: buildEloLine({
            featureName: 'raw_elo_gap',
            target,
            homeMatches,
            awayMatches,
            factsById,
        }),
        home_fatigue_index: buildFatigueLine({
            featureName: 'home_fatigue_index',
            target,
            teamName: target.home_team,
            matches: homeMatches,
            closure,
            sourceBinding: sourceBindings.canonical_schedule,
        }),
        away_fatigue_index: buildFatigueLine({
            featureName: 'away_fatigue_index',
            target,
            teamName: target.away_team,
            matches: awayMatches,
            closure,
            sourceBinding: sourceBindings.canonical_schedule,
        }),
    };
    featureByName.table_position_diff = deriveLine({
        featureName: 'table_position_diff',
        target,
        left: featureByName.home_table_position,
        right: featureByName.away_table_position,
        operation: (left, right) => left - right,
        derivation: 'home_table_position_minus_away_table_position',
    });
    featureByName.points_diff = deriveLine({
        featureName: 'points_diff',
        target,
        left: homePoints,
        right: awayPoints,
        operation: (left, right) => left - right,
        derivation: 'home_points_minus_away_points',
    });
    featureByName.adjusted_elo_gap = deriveLine({
        featureName: 'adjusted_elo_gap',
        target,
        left: featureByName.raw_elo_gap,
        right: featureLine({
            featureName: 'adjusted_elo_gap_factor',
            target,
            sourceMatches: [],
            value: null,
            reasons: [REASON_CODES.SEMANTICS_UNPROVEN],
            derivation: 'unavailable_adjustment_formula_unproven',
            sourceFields: ['no_frozen_elo_adjustment_formula'],
        }),
        operation: () => null,
        derivation: 'unavailable_adjusted_elo_dependency_unproven',
    });
    featureByName.fatigue_diff = deriveLine({
        featureName: 'fatigue_diff',
        target,
        left: featureByName.home_fatigue_index,
        right: featureByName.away_fatigue_index,
        operation: (left, right) => left - right,
        derivation: 'home_fatigue_minus_away_fatigue',
    });
    return featureByName;
}

function buildTargetLabel(target, fact) {
    const result = fact?.facts?.match_result;
    return {
        role: TRAINING_LABEL_ROLE,
        timing_class: FACT_TIMING_CLASS,
        status: result?.status || 'UNAVAILABLE',
        outcome: result?.outcome || null,
        source_match_id: target.canonical_match_id,
        provenance_digest: computeProvenanceDigest({
            role: TRAINING_LABEL_ROLE,
            target_match_id: target.canonical_match_id,
            result,
            source_provenance: fact?.provenance || null,
        }),
    };
}

function rowEligibility(featureNames, features) {
    const unavailable = featureNames.flatMap(name => features[name].unavailable_reason_codes);
    const eligible = featureNames.every(name => {
        const line = features[name];
        return line.availability_status === FEATURE_AVAILABILITY.AVAILABLE && Number.isFinite(line.value);
    });
    return {
        status: eligible ? 'YES' : 'NO',
        reason_codes: eligible ? [] : uniqueReasons(unavailable),
    };
}

function buildFeatureAvailability(rows, featureNames) {
    return featureNames.map(featureName => {
        const available = rows.filter(
            row => row.features[featureName].availability_status === FEATURE_AVAILABILITY.AVAILABLE
        ).length;
        return {
            feature_name: featureName,
            available_count: available,
            unavailable_count: rows.length - available,
        };
    });
}

// eslint-disable-next-line complexity -- counters intentionally enumerate each safety invariant.
function computeValidationCounters(rows, scheduleById) {
    let targetMatchFactDependencyCount = 0;
    let futureMatchDependencyCount = 0;
    let cutoffViolationCount = 0;
    let fabricatedValueCount = 0;
    let silentHistoryGapCount = 0;
    for (const row of rows) {
        for (const [featureName, line] of Object.entries(row.features)) {
            if (line.source_match_ids.includes(row.canonical_match_id)) targetMatchFactDependencyCount += 1;
            if (line.value !== null && !Number.isFinite(line.value)) fabricatedValueCount += 1;
            if (line.value !== null && line.unavailable_reason_codes.length > 0) fabricatedValueCount += 1;
            if (line.source_match_ids.length !== new Set(line.source_match_ids).size) silentHistoryGapCount += 1;
            for (const sourceId of line.source_match_ids) {
                const source = scheduleById.get(sourceId);
                if (!source) {
                    cutoffViolationCount += 1;
                    continue;
                }
                if (!(source.kickoff_ms < row.cutoff_time_ms)) {
                    cutoffViolationCount += 1;
                    futureMatchDependencyCount += 1;
                }
            }
            if (line.cutoff_proof.passed !== true) cutoffViolationCount += 1;
            if (featureName.startsWith('rolling_') && line.source_match_ids.length === REQUIRED_ROLLING_HISTORY_COUNT) {
                const evidenceCount = line.source_evidence_match_ids.length;
                if (line.value !== null && evidenceCount !== REQUIRED_ROLLING_HISTORY_COUNT) silentHistoryGapCount += 1;
            }
        }
    }
    return {
        target_match_fact_dependency_count: targetMatchFactDependencyCount,
        future_match_dependency_count: futureMatchDependencyCount,
        cutoff_violation_count: cutoffViolationCount,
        fabricated_value_count: fabricatedValueCount,
        silent_history_gap_count: silentHistoryGapCount,
    };
}

function buildPriorStateFeatureView(options) {
    assertObject(options, 'GD-A03 options');
    const featureContract = validateFeatureContract(options.featureContract);
    const featureNames = featureContract.ordered_features;
    const semantics = featureSemanticsInOrder(featureNames);
    const schedule = normalizeSchedule(options.scheduleCandidates);
    const closure = validateScheduleClosure(schedule, options.scheduleClosure);
    const targetRows = normalizeTargetRows(options.targetRows);
    const factsById = normalizeFactRows(options.factRows);
    const targetIds = new Set(targetRows.map(row => row.canonical_match_id));
    if (factsById.size !== targetIds.size || [...factsById.keys()].some(id => !targetIds.has(id))) {
        fail('GD-A02 facts must exactly cover the GD-A01 target population', 'POPULATION_MISMATCH');
    }
    const scheduleById = new Map(schedule.map(candidate => [candidate.id, candidate]));
    for (const target of targetRows) {
        const scheduleTarget = scheduleById.get(target.canonical_match_id);
        if (!scheduleTarget) {
            fail(`target ${target.canonical_match_id} is absent from canonical schedule`, 'IDENTITY_CONFLICT');
        }
        for (const field of ['competition', 'season', 'home_team', 'away_team', 'kickoff_at']) {
            if (target[field] !== scheduleTarget[field]) {
                fail(`target ${target.canonical_match_id} ${field} mismatch`, 'IDENTITY_CONFLICT');
            }
        }
        const fact = factsById.get(target.canonical_match_id);
        for (const field of ['competition', 'season', 'home_team', 'away_team', 'kickoff_at']) {
            if (fact[field] !== scheduleTarget[field]) {
                fail(`fact ${target.canonical_match_id} ${field} mismatch`, 'IDENTITY_CONFLICT');
            }
        }
    }
    const indexes = buildIndexes(schedule);
    const sourceBindings = validateSourceBindings(options.sourceBindings);
    const rows = targetRows.map(target => {
        const features = buildTargetFeatures({
            target,
            schedule,
            factsById,
            indexes,
            closure,
            sourceBindings,
        });
        const orderedFeatures = {};
        for (const featureName of featureNames) orderedFeatures[featureName] = features[featureName];
        return {
            canonical_match_id: target.canonical_match_id,
            target_kickoff: target.kickoff_at,
            home_team: target.home_team,
            away_team: target.away_team,
            feature_cutoff_policy: FEATURE_CUTOFF_POLICY,
            feature_cutoff_time: target.kickoff_at,
            features: orderedFeatures,
            feature_vector_eligibility: rowEligibility(featureNames, orderedFeatures),
            target_label: buildTargetLabel(target, factsById.get(target.canonical_match_id)),
            cutoff_time_ms: target.kickoff_ms,
        };
    });
    const eligibleRows = rows.filter(row => row.feature_vector_eligibility.status === 'YES');
    const unavailableRows = rows.filter(row => row.feature_vector_eligibility.status === 'NO');
    const validationCounters = computeValidationCounters(rows, scheduleById);
    if (validationCounters.target_match_fact_dependency_count !== 0) {
        fail('target-match facts reached feature computation', 'TARGET_MATCH_LEAK');
    }
    if (validationCounters.future_match_dependency_count !== 0 || validationCounters.cutoff_violation_count !== 0) {
        fail('future/equal source reached feature computation', 'CUTOFF_VIOLATION');
    }
    if (validationCounters.fabricated_value_count !== 0) {
        fail('fabricated/nonfinite feature value detected', 'FACT_VALUE_INVALID');
    }
    const accountedIds = new Set(rows.map(row => row.canonical_match_id));
    const artifactWithoutHash = {
        schema_version: PRIOR_STATE_ARTIFACT_SCHEMA_VERSION,
        stage: PRIOR_STATE_STAGE,
        artifact_kind: 'prior_state_feature_view',
        lineage_contract_version: PRIOR_STATE_LINEAGE_CONTRACT_VERSION,
        feature_cutoff_policy: FEATURE_CUTOFF_POLICY,
        feature_cutoff_relation: FEATURE_CUTOFF_RELATION,
        feature_contract: featureContract,
        feature_semantics: semantics,
        source_bindings: sourceBindings,
        schedule_authority: {
            schema_version: SCHEDULE_SCHEMA_VERSION,
            closure_schema_version: closure.schema_version,
            closure_status: closure.status,
            authority: closure.authority,
            per_season_counts: closure.per_season_expected_counts,
        },
        population_accounting: {
            target_population_count: rows.length,
            feature_eligible_count: eligibleRows.length,
            feature_unavailable_count: unavailableRows.length,
            rows_accounted: rows.length,
            unaccounted_count: targetIds.size - accountedIds.size,
            duplicate_id_count: rows.length - accountedIds.size,
            extra_id_count: 0,
            target_id_set_sha256: admittedIdSetHash([...targetIds]),
            accounted_id_set_sha256: admittedIdSetHash([...accountedIds]),
        },
        feature_availability: buildFeatureAvailability(rows, featureNames),
        validation_counters: validationCounters,
        numeric_parity: NUMERIC_PARITY,
        feature_frame_readiness: 'NOT_READY',
        real_training_readiness: 'NOT_READY',
        training_execution_authorized: false,
        strict_decision_time_value_evaluation: 'NOT_READY',
        golden_dataset_complete: false,
        rows: rows.map(({ cutoff_time_ms: ignored, ...row }) => row),
    };
    const artifact = {
        ...artifactWithoutHash,
        business_content_sha256: computeBusinessHash({ ...artifactWithoutHash, business_content_sha256: null }),
    };
    const artifactBytes = Buffer.from(`${stableStringify(artifact)}\n`, 'utf8');
    const receiptWithoutHash = {
        schema_version: PRIOR_STATE_RECEIPT_SCHEMA_VERSION,
        stage: PRIOR_STATE_STAGE,
        build_mode: 'file_first_offline',
        code_revision: options.codeRevision,
        source_bindings: sourceBindings,
        input_target_count: rows.length,
        rows_accounted: rows.length,
        feature_eligible_count: eligibleRows.length,
        feature_unavailable_count: unavailableRows.length,
        unaccounted_count: artifact.population_accounting.unaccounted_count,
        duplicate_id_count: artifact.population_accounting.duplicate_id_count,
        extra_id_count: artifact.population_accounting.extra_id_count,
        output_business_sha256: artifact.business_content_sha256,
        artifact_sha256: sha256Bytes(artifactBytes),
        feature_cutoff_policy: FEATURE_CUTOFF_POLICY,
        offline: true,
        file_first: true,
        live_network_requests: 0,
        db_writes: 0,
        db_migrations: 0,
        raw_mutations: 0,
        training_runs: 0,
        backtest_runs: 0,
        model_activations: 0,
        status: 'ACCOUNTED_FEATURE_AVAILABILITY_COMPLETE',
    };
    const receipt = receiptWithoutHash;
    validatePriorStateOutputFiles(artifactBytes, Buffer.from(`${stableStringify(receipt)}\n`, 'utf8'));
    return { artifact, receipt, artifactBytes, receiptBytes: Buffer.from(`${stableStringify(receipt)}\n`, 'utf8') };
}

function validatePriorStateOutputFiles(...args) {
    return require('./GdA03ArtifactContract').validatePriorStateOutputFiles(...args);
}

module.exports = {
    FACT_TIMING_CLASS,
    NUMERIC_PARITY,
    PRIOR_STATE_ARTIFACT_SCHEMA_VERSION,
    PRIOR_STATE_RECEIPT_SCHEMA_VERSION,
    SCHEDULE_AUTHORITY_VERSION,
    SCHEDULE_SCHEMA_VERSION,
    TRAINING_LABEL_ROLE,
    buildPriorStateFeatureView,
    computeValidationCounters,
    normalizeSchedule,
    validatePriorStateOutputFiles,
    validateScheduleClosure,
};
