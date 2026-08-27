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
    }
) {
    const time = parseUtcTime(decision_time, 'decision_time');
    const side = parsePriceSide(price_side);
    return (
        observations
            .filter(
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
            )
            .sort((a, b) => compareKnowledgeTime(b, a) || compareCodeUnits(b.observation_id, a.observation_id))[0] ||
        null
    );
}
function latestAsOfMarket(observations, query) {
    const decisionTime = parseUtcTime(query.decision_time, 'decision_time');
    const side = parsePriceSide(query.price_side ?? 'BOOKMAKER');
    const candidates = observations.filter(
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
    const preKickoff = visible.filter(row => compareKnowledgeToCutoff(row, kickoffTime) < 0);
    const bySelection = selection =>
        visible
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
        [...visible].sort(
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
