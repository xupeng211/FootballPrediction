'use strict';

const {
    isUtcTimestamp,
    normalizeUtcTimestamp,
    compareUtcTimestamps,
    compareCodeUnits,
    PRICE_SIDES,
} = require('./contracts');

function parseUtcTime(value, field) {
    if (!isUtcTimestamp(value)) throw new Error(`${field} must be UTC ISO-8601`);
    return normalizeUtcTimestamp(value);
}

function knowledgeTime(row) {
    const receivedAt = isUtcTimestamp(row?.response_received_at)
        ? normalizeUtcTimestamp(row.response_received_at)
        : null;
    const ingestedAt = isUtcTimestamp(row?.ingested_at) ? normalizeUtcTimestamp(row.ingested_at) : null;
    if (receivedAt === null || ingestedAt === null) return null;
    return compareUtcTimestamps(receivedAt, ingestedAt) >= 0 ? receivedAt : ingestedAt;
}

function isKnownBy(row, cutoff) {
    const receivedAt = knowledgeTime(row);
    return receivedAt !== null && compareUtcTimestamps(receivedAt, cutoff) <= 0;
}

function compareKnowledgeToCutoff(row, cutoff) {
    const receivedAt = knowledgeTime(row);
    return receivedAt === null ? null : compareUtcTimestamps(receivedAt, cutoff);
}

function compareKnowledgeTime(left, right) {
    return compareUtcTimestamps(knowledgeTime(left), knowledgeTime(right));
}

function parsePriceSide(value) {
    if (!PRICE_SIDES.has(value)) throw new Error('price_side must be BOOKMAKER, BACK or LAY');
    return value;
}

function governanceBoundary(row) {
    const fields = ['projection_version', 'adapter_name', 'adapter_version', 'identity_registry_version', 'identity_registry_sha256', 'identity_ruleset_version'];
    const values = fields.map(field => row?.[field]);
    if (values.some(value => typeof value !== 'string' || !value.trim())) throw new Error('projection governance boundary is incomplete');
    return values.join('\u001f');
}

// Version choice is an as-of concern: only observations actually visible at
// the requested decision time participate.  A later reprojection therefore
// cannot turn a historical query ambiguous.  Within a version, changing any
// governed adapter/registry/ruleset boundary is likewise ambiguous rather
// than being silently hidden by observation_id ordering.
function selectProjection(rows, projectionVersion) {
    const candidates = projectionVersion === undefined || projectionVersion === null
        ? rows
        : (() => {
            if (typeof projectionVersion !== 'string' || !projectionVersion.trim()) throw new Error('projection_version must be a non-empty string');
            return rows.filter(row => row.projection_version === projectionVersion);
        })();
    const boundaries = new Set(candidates.map(governanceBoundary));
    if (boundaries.size > 1) {
        if (projectionVersion === undefined || projectionVersion === null) throw new Error('projection_version is required when multiple projections are visible');
        throw new Error('projection governance boundary is ambiguous');
    }
    return candidates;
}

function latestAsOf(
    observations,
    {
        canonical_event_id,
        canonical_bookmaker_id,
        canonical_selection_id = null,
        period,
        market_type,
        line = null,
        price_side = 'BOOKMAKER',
        decision_time,
        projection_version,
    }
) {
    const time = parseUtcTime(decision_time, 'decision_time');
    const side = parsePriceSide(price_side);
    const eligible = observations.filter(
        row =>
            row.canonical_event_id === canonical_event_id &&
            row.canonical_bookmaker_id === canonical_bookmaker_id &&
            row.period === period &&
            row.market_type === market_type &&
            row.line === line &&
            row.price_side === side &&
            (canonical_selection_id === null || row.canonical_selection_id === canonical_selection_id) &&
            Array.isArray(row.quality_flags) &&
            row.quality_flags.length === 0 &&
            isKnownBy(row, time)
    );
    const projected = selectProjection(eligible, projection_version);
    return (
        projected
            .sort((a, b) => compareKnowledgeTime(b, a) || compareCodeUnits(b.observation_id, a.observation_id))[0] ||
        null
    );
}
function latestAsOfMarket(observations, query) {
    const decisionTime = parseUtcTime(query.decision_time, 'decision_time');
    const side = parsePriceSide(query.price_side ?? 'BOOKMAKER');
    const eligible = observations.filter(
        row =>
            row.canonical_event_id === query.canonical_event_id &&
            row.canonical_bookmaker_id === query.canonical_bookmaker_id &&
            row.period === query.period &&
            row.market_type === query.market_type &&
            row.line === (query.line ?? null) &&
            row.price_side === side &&
            Array.isArray(row.quality_flags) &&
            row.quality_flags.length === 0 &&
            isKnownBy(row, decisionTime)
    );
    const candidates = selectProjection(eligible, query.projection_version);
    const bySelection = new Map();
    for (const row of candidates) {
        const current = bySelection.get(row.canonical_selection_id);
        if (
            !current ||
            compareKnowledgeTime(row, current) > 0 ||
            (compareKnowledgeTime(row, current) === 0 &&
                compareCodeUnits(row.observation_id, current.observation_id) > 0)
        ) {
            bySelection.set(row.canonical_selection_id, row);
        }
    }
    return [...bySelection.values()].sort((a, b) =>
        compareCodeUnits(a.canonical_selection_id, b.canonical_selection_id)
    );
}
function deriveTimeline(
    observations,
    {
        canonical_event_id,
        canonical_bookmaker_id,
        period = 'MATCH',
        market_type = '1X2',
        line = null,
        price_side = 'BOOKMAKER',
        kickoff_utc,
        decision_time,
        projection_version,
    }
) {
    const kickoffTime = parseUtcTime(kickoff_utc, 'kickoff_utc');
    const decisionTime = parseUtcTime(decision_time, 'decision_time');
    const side = parsePriceSide(price_side);
    const eligible = observations.filter(
        row =>
            row.canonical_event_id === canonical_event_id &&
            row.canonical_bookmaker_id === canonical_bookmaker_id &&
            row.period === period &&
            row.market_type === market_type &&
            row.line === line &&
            row.price_side === side &&
            Array.isArray(row.quality_flags) &&
            row.quality_flags.length === 0
    );
    const visible = eligible.filter(row => isKnownBy(row, decisionTime));
    const governed = selectProjection(visible, projection_version);
    const preKickoff = governed.filter(row => compareKnowledgeToCutoff(row, kickoffTime) < 0);
    const bySelection = selection =>
        governed
            .filter(row => row.canonical_selection_id === selection)
            .sort((a, b) => compareKnowledgeTime(a, b) || compareCodeUnits(a.observation_id, b.observation_id));
    const preKickoffBySelection = selection =>
        preKickoff
            .filter(row => row.canonical_selection_id === selection)
            .sort((a, b) => compareKnowledgeTime(a, b) || compareCodeUnits(a.observation_id, b.observation_id));
    const opening =
        [...preKickoff].sort(
            (a, b) => compareKnowledgeTime(a, b) || compareCodeUnits(a.observation_id, b.observation_id)
        )[0] || null;
    const current =
        [...governed].sort(
            (a, b) => compareKnowledgeTime(b, a) || compareCodeUnits(b.observation_id, a.observation_id)
        )[0] || null;
    const closing =
        [...preKickoff].sort(
            (a, b) => compareKnowledgeTime(b, a) || compareCodeUnits(b.observation_id, a.observation_id)
        )[0] || null;
    return {
        opening,
        current,
        closing,
        observations_by_selection: Object.fromEntries(
            ['HOME', 'DRAW', 'AWAY'].map(selection => [selection, bySelection(selection)])
        ),
        opening_by_selection: Object.fromEntries(
            ['HOME', 'DRAW', 'AWAY'].map(selection => [selection, preKickoffBySelection(selection)[0] || null])
        ),
        current_by_selection: Object.fromEntries(
            ['HOME', 'DRAW', 'AWAY'].map(selection => [selection, bySelection(selection).at(-1) || null])
        ),
        closing_by_selection: Object.fromEntries(
            ['HOME', 'DRAW', 'AWAY'].map(selection => [selection, preKickoffBySelection(selection).at(-1) || null])
        ),
    };
}
module.exports = { latestAsOf, latestAsOfMarket, deriveTimeline };
