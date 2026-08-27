'use strict';

const { isUtcTimestamp } = require('./contracts');

function parseUtcTime(value, field) {
    if (!isUtcTimestamp(value)) throw new Error(`${field} must be UTC ISO-8601`);
    return Date.parse(value);
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
        decision_time,
    }
) {
    const time = parseUtcTime(decision_time, 'decision_time');
    return (
        observations
            .filter(
                row =>
                    row.canonical_event_id === canonical_event_id &&
                    row.canonical_bookmaker_id === canonical_bookmaker_id &&
                    row.period === period &&
                    row.market_type === market_type &&
                    row.line === line &&
                    (canonical_selection_id === null || row.canonical_selection_id === canonical_selection_id) &&
                    Array.isArray(row.quality_flags) &&
                    row.quality_flags.length === 0 &&
                    Date.parse(row.response_received_at) <= time
            )
            .sort(
                (a, b) =>
                    Date.parse(b.response_received_at) - Date.parse(a.response_received_at) ||
                    b.observation_id.localeCompare(a.observation_id)
            )[0] || null
    );
}
function latestAsOfMarket(observations, query) {
    const decisionTime = parseUtcTime(query.decision_time, 'decision_time');
    const candidates = observations.filter(
        row =>
            row.canonical_event_id === query.canonical_event_id &&
            row.canonical_bookmaker_id === query.canonical_bookmaker_id &&
            row.period === query.period &&
            row.market_type === query.market_type &&
            row.line === (query.line ?? null) &&
            Array.isArray(row.quality_flags) &&
            row.quality_flags.length === 0 &&
            Date.parse(row.response_received_at) <= decisionTime
    );
    const bySelection = new Map();
    for (const row of candidates) {
        const current = bySelection.get(row.canonical_selection_id);
        if (
            !current ||
            Date.parse(row.response_received_at) > Date.parse(current.response_received_at) ||
            (Date.parse(row.response_received_at) === Date.parse(current.response_received_at) &&
                row.observation_id > current.observation_id)
        ) {
            bySelection.set(row.canonical_selection_id, row);
        }
    }
    return [...bySelection.values()].sort((a, b) => a.canonical_selection_id.localeCompare(b.canonical_selection_id));
}
function deriveTimeline(
    observations,
    { canonical_event_id, canonical_bookmaker_id, period = 'MATCH', market_type = '1X2', line = null, kickoff_utc }
) {
    const kickoffTime = parseUtcTime(kickoff_utc, 'kickoff_utc');
    const eligible = observations.filter(
        row =>
            row.canonical_event_id === canonical_event_id &&
            row.canonical_bookmaker_id === canonical_bookmaker_id &&
            row.period === period &&
            row.market_type === market_type &&
            row.line === line &&
            Array.isArray(row.quality_flags) &&
            row.quality_flags.length === 0
    );
    const preKickoff = eligible.filter(row => Date.parse(row.response_received_at) <= kickoffTime);
    const bySelection = selection =>
        eligible
            .filter(row => row.canonical_selection_id === selection)
            .sort(
                (a, b) =>
                    Date.parse(a.response_received_at) - Date.parse(b.response_received_at) ||
                    a.observation_id.localeCompare(b.observation_id)
            );
    const preKickoffBySelection = selection =>
        preKickoff
            .filter(row => row.canonical_selection_id === selection)
            .sort(
                (a, b) =>
                    Date.parse(a.response_received_at) - Date.parse(b.response_received_at) ||
                    a.observation_id.localeCompare(b.observation_id)
            );
    const opening =
        [...preKickoff].sort(
            (a, b) =>
                Date.parse(a.response_received_at) - Date.parse(b.response_received_at) ||
                a.observation_id.localeCompare(b.observation_id)
        )[0] || null;
    const current =
        [...eligible].sort(
            (a, b) =>
                Date.parse(b.response_received_at) - Date.parse(a.response_received_at) ||
                b.observation_id.localeCompare(a.observation_id)
        )[0] || null;
    const closing =
        [...preKickoff].sort(
            (a, b) =>
                Date.parse(b.response_received_at) - Date.parse(a.response_received_at) ||
                b.observation_id.localeCompare(a.observation_id)
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
