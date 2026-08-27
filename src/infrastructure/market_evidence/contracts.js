'use strict';
/* eslint-disable complexity -- contract construction validates each independent invariant explicitly. */

const crypto = require('node:crypto');

const SCHEMA_VERSION = 'footballprediction-market-observation/v1';
const ACQUISITION_MODES = new Set(['LIVE_CAPTURE', 'HISTORICAL_API', 'HISTORICAL_FILE', 'REPLAY']);
const PRICE_SIDES = new Set(['BOOKMAKER', 'BACK', 'LAY']);
const PERIODS = new Set(['MATCH', 'FIRST_HALF']);
const MARKET_TYPES = new Set(['1X2', 'ASIAN_HANDICAP', 'TOTAL']);
const SELECTIONS = new Set(['HOME', 'DRAW', 'AWAY']);
const ISO_UTC = /^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d{1,9})?Z$/;

function stableCanonicalize(value) {
    if (Array.isArray(value)) return value.map(stableCanonicalize);
    if (value && typeof value === 'object') {
        return Object.keys(value)
            .sort()
            .reduce((result, key) => {
                result[key] = stableCanonicalize(value[key]);
                return result;
            }, {});
    }
    return value;
}

function stableStringify(value) {
    return JSON.stringify(stableCanonicalize(value));
}

function sha256Text(value) {
    return crypto.createHash('sha256').update(String(value), 'utf8').digest('hex');
}

function requireText(value, field, errors) {
    if (value !== null && value !== undefined && typeof value !== 'string') {
        errors.push(`${field} must be a string`);
        return null;
    }
    const text = String(value ?? '').trim();
    if (!text) errors.push(`${field} is required`);
    return text || null;
}

function requireUtc(value, field, errors, nullable = false) {
    if (value === null || value === undefined || value === '') {
        if (!nullable) errors.push(`${field} is required`);
        return null;
    }
    const text = String(value);
    if (!ISO_UTC.test(text) || !Number.isFinite(Date.parse(text))) errors.push(`${field} must be UTC ISO-8601`);
    return text;
}

function isUtcTimestamp(value) {
    return ISO_UTC.test(String(value ?? '')) && Number.isFinite(Date.parse(String(value)));
}

function validateMarketIdentity({ period, market_type: marketType, line }, errors) {
    if (!PERIODS.has(period)) errors.push('invalid period');
    if (!MARKET_TYPES.has(marketType)) errors.push('invalid market_type');
    if (marketType === '1X2' && line !== null && line !== undefined) errors.push('1X2 line must be null');
    if (marketType !== '1X2' && !Number.isFinite(Number(line))) errors.push('non-1X2 line must be numeric');
}

function semanticProjection(observation) {
    const copy = { ...observation };
    delete copy.ingested_at;
    return stableCanonicalize(copy);
}

function createObservation(fields) {
    const errors = [];
    if (fields.decision_target_at !== undefined) errors.push('decision_target_at is not part of MarketObservation');
    if (fields.quality_flags !== undefined && !Array.isArray(fields.quality_flags)) {
        errors.push('quality_flags must be an array');
    }
    const schemaVersion = fields.schema_version === undefined ? SCHEMA_VERSION : fields.schema_version;
    if (schemaVersion !== SCHEMA_VERSION) errors.push('unsupported schema_version');
    const observation = {
        schema_version: schemaVersion,
        projection_version: requireText(fields.projection_version, 'projection_version', errors),
        observation_id: requireText(fields.observation_id, 'observation_id', errors),
        canonical_event_id: requireText(fields.canonical_event_id, 'canonical_event_id', errors),
        provider: requireText(fields.provider, 'provider', errors),
        provider_event_id: requireText(fields.provider_event_id, 'provider_event_id', errors),
        canonical_market_id: requireText(fields.canonical_market_id, 'canonical_market_id', errors),
        provider_market_id: requireText(fields.provider_market_id, 'provider_market_id', errors),
        canonical_bookmaker_id: requireText(fields.canonical_bookmaker_id, 'canonical_bookmaker_id', errors),
        provider_bookmaker_id: requireText(fields.provider_bookmaker_id, 'provider_bookmaker_id', errors),
        provider_bookmaker_name: requireText(fields.provider_bookmaker_name, 'provider_bookmaker_name', errors),
        competition: requireText(fields.competition, 'competition', errors),
        season: fields.season === null || fields.season === undefined ? null : String(fields.season),
        home_team: requireText(fields.home_team, 'home_team', errors),
        away_team: requireText(fields.away_team, 'away_team', errors),
        kickoff_utc: requireUtc(fields.kickoff_utc, 'kickoff_utc', errors),
        period: fields.period,
        market_type: fields.market_type,
        line: fields.line === null || fields.line === undefined ? null : Number(fields.line),
        canonical_selection_id: requireText(fields.canonical_selection_id, 'canonical_selection_id', errors),
        selection: fields.selection,
        price_side: fields.price_side,
        odds_decimal: Number(fields.odds_decimal),
        available_volume:
            fields.available_volume === null || fields.available_volume === undefined
                ? null
                : Number(fields.available_volume),
        bet_limit: fields.bet_limit === null || fields.bet_limit === undefined ? null : Number(fields.bet_limit),
        bookmaker_last_update_at: requireUtc(fields.bookmaker_last_update_at, 'bookmaker_last_update_at', errors, true),
        source_snapshot_at: requireUtc(fields.source_snapshot_at, 'source_snapshot_at', errors, true),
        capture_started_at: requireUtc(fields.capture_started_at, 'capture_started_at', errors),
        response_received_at: requireUtc(fields.response_received_at, 'response_received_at', errors),
        ingested_at: requireUtc(fields.ingested_at, 'ingested_at', errors),
        acquisition_mode: fields.acquisition_mode,
        capture_id: requireText(fields.capture_id, 'capture_id', errors),
        raw_evidence_reference: requireText(fields.raw_evidence_reference, 'raw_evidence_reference', errors),
        raw_sha256: requireText(fields.raw_sha256, 'raw_sha256', errors),
        adapter_name: requireText(fields.adapter_name, 'adapter_name', errors),
        adapter_version: requireText(fields.adapter_version, 'adapter_version', errors),
        identity_registry_version: requireText(fields.identity_registry_version, 'identity_registry_version', errors),
        quality_flags: Array.isArray(fields.quality_flags)
            ? Object.freeze([...fields.quality_flags].sort())
            : Object.freeze([]),
    };
    validateMarketIdentity(observation, errors);
    if (!SELECTIONS.has(observation.selection)) errors.push('invalid selection');
    if (observation.market_type === '1X2' && !['HOME', 'DRAW', 'AWAY'].includes(observation.selection)) {
        errors.push('1X2 selection must be HOME, DRAW or AWAY');
    }
    if (!PRICE_SIDES.has(observation.price_side)) errors.push('invalid price_side');
    if (!ACQUISITION_MODES.has(observation.acquisition_mode)) errors.push('invalid acquisition_mode');
    if (!Number.isFinite(observation.odds_decimal) || observation.odds_decimal <= 1) {
        errors.push('odds_decimal must be > 1');
    }
    if (
        observation.available_volume !== null &&
        (!Number.isFinite(observation.available_volume) || observation.available_volume < 0)
    ) {
        errors.push('available_volume must be >= 0');
    }
    if (observation.bet_limit !== null && (!Number.isFinite(observation.bet_limit) || observation.bet_limit < 0)) {
        errors.push('bet_limit must be >= 0');
    }
    if (!/^[a-f0-9]{64}$/.test(observation.raw_sha256 || '')) {
        errors.push('raw_sha256 must be lowercase SHA-256');
    }
    if (observation.quality_flags.some(flag => typeof flag !== 'string')) {
        errors.push('quality_flags must contain strings');
    }
    if (Date.parse(observation.response_received_at) < Date.parse(observation.capture_started_at)) {
        errors.push('response_received_at precedes capture_started_at');
    }
    if (Date.parse(observation.ingested_at) < Date.parse(observation.response_received_at)) {
        errors.push('ingested_at precedes response_received_at');
    }
    if (errors.length) throw new Error(`invalid MarketObservation: ${errors.join('; ')}`);
    return Object.freeze(observation);
}

module.exports = {
    SCHEMA_VERSION,
    ACQUISITION_MODES,
    PRICE_SIDES,
    stableCanonicalize,
    stableStringify,
    sha256Text,
    isUtcTimestamp,
    semanticProjection,
    createObservation,
};
