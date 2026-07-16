'use strict';

// lifecycle: permanent；canonical observation 的严格字段、语义与隔离规则。

const { ALLOWED_SNAPSHOT_TYPES, appendObservationSignals, nullableText } = require('./contracts');

const MARKET_SELECTIONS = Object.freeze({
    '1X2': ['home', 'draw', 'away'],
    asian_handicap: ['home', 'away'],
    over_under: ['over', 'under'],
    draw_no_bet: ['home', 'away'],
    both_teams_to_score: ['yes', 'no'],
});

function isIsoTimestamp(value) {
    const text = nullableText(value);
    return Boolean(text) && /^\d{4}-\d{2}-\d{2}T/.test(text) && Number.isFinite(Date.parse(text));
}

function requiresLine(market) {
    return market === 'asian_handicap' || market === 'over_under';
}

function hasSufficientIdentity(observation) {
    if (nullableText(observation.source_match_id)) {
        return true;
    }
    return Boolean(
        nullableText(observation.competition) &&
        nullableText(observation.kickoff_at) &&
        nullableText(observation.home_team) &&
        nullableText(observation.away_team)
    );
}

function validateSourceIdentity(observation) {
    const reasons = [];
    if (!nullableText(observation.source_provider)) {
        reasons.push('source_provider_missing');
    }
    if (!nullableText(observation.source_url)) {
        reasons.push('source_url_missing');
    }
    if (!hasSufficientIdentity(observation)) {
        reasons.push('source_match_identity_insufficient');
    }
    if (nullableText(observation.home_team) && observation.home_team === observation.away_team) {
        reasons.push('home_and_away_identical');
    }
    if (observation.kickoff_at && !isIsoTimestamp(observation.kickoff_at)) {
        reasons.push('kickoff_at_invalid');
    }
    return reasons;
}

function validateMarketOdds(observation) {
    const reasons = [];
    const market = nullableText(observation.market);
    const selection = nullableText(observation.selection);
    const decimalOdds = Number(observation.decimal_odds);
    if (!nullableText(observation.bookmaker)) {
        reasons.push('bookmaker_missing_or_ambiguous');
    }
    if (!market || !Object.prototype.hasOwnProperty.call(MARKET_SELECTIONS, market)) {
        reasons.push('market_missing_or_unsupported');
    }
    if (!selection || (MARKET_SELECTIONS[market] && !MARKET_SELECTIONS[market].includes(selection))) {
        reasons.push('selection_market_mismatch');
    }
    if (!Number.isFinite(decimalOdds) || decimalOdds <= 1) {
        reasons.push('decimal_odds_invalid');
    }

    const line = observation.line;
    if (requiresLine(market) && !Number.isFinite(Number(line))) {
        reasons.push('market_line_missing');
    }
    if (!requiresLine(market) && line !== null && line !== undefined) {
        reasons.push('line_not_applicable');
    }
    return reasons;
}

function validateTimeAndProvenance(observation) {
    const reasons = [];
    if (!ALLOWED_SNAPSHOT_TYPES.has(observation.snapshot_type)) {
        reasons.push('snapshot_type_invalid');
    }
    if (observation.source_observed_at && !isIsoTimestamp(observation.source_observed_at)) {
        reasons.push('source_observed_at_invalid');
    }
    if (!isIsoTimestamp(observation.captured_at)) {
        reasons.push('captured_at_invalid');
    }
    if (!nullableText(observation.source_timezone)) {
        reasons.push('source_timezone_missing');
    }
    if (!/^[a-f0-9]{64}$/i.test(String(observation.raw_sha256 || ''))) {
        reasons.push('raw_sha256_invalid');
    }
    if (!nullableText(observation.raw_record_locator)) {
        reasons.push('raw_record_locator_missing');
    }
    if (!nullableText(observation.adapter) || !nullableText(observation.adapter_version)) {
        reasons.push('adapter_provenance_missing');
    }
    if (!nullableText(observation.extraction_method)) {
        reasons.push('extraction_method_missing');
    }
    if (!nullableText(observation.provenance_status)) {
        reasons.push('provenance_status_missing');
    }
    return reasons;
}

function validateSnapshotSemantics(observation) {
    const reasons = [];
    const flags = [];
    if (
        observation.snapshot_type !== 'unknown' &&
        /(?:record[_ -]?order|first|last|sequence)/i.test(String(observation.extraction_method || ''))
    ) {
        reasons.push('snapshot_order_inference_prohibited');
    }
    if (observation.snapshot_type !== 'unknown' && !observation.source_observed_at) {
        flags.push('snapshot_source_time_unknown');
    }
    if (observation.provenance_status === 'fixture') {
        flags.push('fixture_provenance');
    }
    return { reasons, flags };
}

function validateObservation(observation) {
    const snapshotSignals = validateSnapshotSemantics(observation);
    const reasons = [
        ...validateSourceIdentity(observation),
        ...validateMarketOdds(observation),
        ...validateTimeAndProvenance(observation),
        ...snapshotSignals.reasons,
    ];
    return appendObservationSignals(observation, reasons, snapshotSignals.flags);
}

module.exports = {
    MARKET_SELECTIONS,
    hasSufficientIdentity,
    validateObservation,
};
