'use strict';
/* eslint-disable complexity -- contract construction validates each independent invariant explicitly. */

const crypto = require('node:crypto');

const SCHEMA_VERSION = 'footballprediction-market-observation/v1';
const COMPETITION = 'English Premier League';
const ACQUISITION_MODES = new Set(['LIVE_CAPTURE', 'HISTORICAL_API', 'HISTORICAL_FILE', 'REPLAY']);
const PRICE_SIDES = new Set(['BOOKMAKER', 'BACK', 'LAY']);
const PERIODS = new Set(['MATCH', 'FIRST_HALF']);
const MARKET_TYPES = new Set(['1X2', 'ASIAN_HANDICAP', 'TOTAL']);
const SELECTIONS = new Set(['HOME', 'DRAW', 'AWAY']);
const ISO_UTC = /^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d{1,9})?Z$/;
const OBSERVATION_FIELDS = new Set([
    'schema_version',
    'projection_version',
    'projection_available_at',
    'observation_id',
    'canonical_event_id',
    'identity_decision_id',
    'identity_ruleset_version',
    'identity_resolver_version',
    'provider',
    'provider_event_id',
    'canonical_market_id',
    'provider_market_id',
    'canonical_bookmaker_id',
    'provider_bookmaker_id',
    'provider_bookmaker_name',
    'competition',
    'season',
    'home_team',
    'away_team',
    'kickoff_utc',
    'period',
    'market_type',
    'line',
    'canonical_selection_id',
    'selection',
    'price_side',
    'odds_decimal',
    'available_volume',
    'bet_limit',
    'bookmaker_last_update_at',
    'source_snapshot_at',
    'capture_started_at',
    'response_received_at',
    'ingested_at',
    'acquisition_mode',
    'capture_id',
    'raw_evidence_reference',
    'raw_sha256',
    'adapter_name',
    'adapter_version',
    'identity_registry_version',
    'identity_registry_sha256',
    'quality_flags',
]);

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

function optionalText(value, field, errors) {
    if (value === null || value === undefined) return null;
    if (typeof value !== 'string') {
        errors.push(`${field} must be a string or null`);
        return null;
    }
    const text = value.trim();
    if (!text) errors.push(`${field} must not be empty`);
    return text || null;
}

function optionalNumber(value, field, errors) {
    if (value === null || value === undefined) return null;
    if (typeof value !== 'number') {
        errors.push(`${field} must be a number or null`);
        return Number.NaN;
    }
    return value;
}

function requireUtc(value, field, errors, nullable = false) {
    if (value === null || value === undefined || value === '') {
        if (!nullable) errors.push(`${field} is required`);
        return null;
    }
    const text = String(value);
    if (!isUtcTimestamp(text)) errors.push(`${field} must be UTC ISO-8601`);
    return text;
}

function isUtcTimestamp(value) {
    const text = String(value ?? '');
    if (!ISO_UTC.test(text)) return false;
    const year = Number(text.slice(0, 4));
    const month = Number(text.slice(5, 7));
    const day = Number(text.slice(8, 10));
    const hour = Number(text.slice(11, 13));
    const minute = Number(text.slice(14, 16));
    const second = Number(text.slice(17, 19));
    const leapYear = year % 4 === 0 && (year % 100 !== 0 || year % 400 === 0);
    const daysInMonth = [31, leapYear ? 29 : 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31][month - 1];
    return (
        month >= 1 &&
        month <= 12 &&
        day >= 1 &&
        day <= daysInMonth &&
        hour >= 0 &&
        hour <= 23 &&
        minute >= 0 &&
        minute <= 59 &&
        second >= 0 &&
        second <= 59
    );
}

function isSafeEvidenceReference(value) {
    return (
        typeof value === 'string' &&
        value.trim() === value &&
        value.length > 0 &&
        /^[A-Za-z0-9._/-]+$/.test(value) &&
        !value.startsWith('/') &&
        !value.split('/').includes('..')
    );
}

function validateMarketIdentity({ period, market_type: marketType, line }, errors) {
    if (!PERIODS.has(period)) errors.push('invalid period');
    if (!MARKET_TYPES.has(marketType)) errors.push('invalid market_type');
    if (marketType === '1X2' && line !== null && line !== undefined) errors.push('1X2 line must be null');
    if (marketType !== '1X2' && (line === null || line === undefined || !Number.isFinite(Number(line)))) {
        errors.push('non-1X2 line must be numeric');
    }
}

function compareCodeUnits(left, right) {
    return left === right ? 0 : left < right ? -1 : 1;
}

function normalizeUtcTimestamp(value) {
    const text = String(value);
    const fractionStart = text.indexOf('.');
    if (fractionStart === -1) return `${text.slice(0, -1)}.000000000Z`;
    const fractionEnd = text.length - 1;
    return `${text.slice(0, fractionStart)}.${text.slice(fractionStart + 1, fractionEnd).padEnd(9, '0')}Z`;
}

function compareUtcTimestamps(left, right) {
    return compareCodeUnits(normalizeUtcTimestamp(left), normalizeUtcTimestamp(right));
}

function semanticProjection(observation) {
    const copy = { ...observation };
    delete copy.ingested_at;
    // projection_available_at is publisher-owned knowledge time.  It is
    // intentionally excluded from the semantic replay identity so a replay
    // cannot turn a historical source timestamp into a deterministic
    // backdated authority fact.
    delete copy.projection_available_at;
    return stableCanonicalize(copy);
}

function createObservation(fields) {
    if (!fields || typeof fields !== 'object' || Array.isArray(fields)) {
        throw new Error('invalid MarketObservation: fields must be an object');
    }
    const errors = [];
    if (Object.prototype.hasOwnProperty.call(fields, 'decision_target_at')) {
        errors.push('decision_target_at is not part of MarketObservation');
    }
    for (const field of Object.keys(fields)) {
        if (!OBSERVATION_FIELDS.has(field) && field !== 'decision_target_at') {
            errors.push(`unknown MarketObservation field: ${field}`);
        }
    }
    if (fields.quality_flags !== undefined && !Array.isArray(fields.quality_flags)) {
        errors.push('quality_flags must be an array');
    }
    const schemaVersion = fields.schema_version === undefined ? SCHEMA_VERSION : fields.schema_version;
    if (schemaVersion !== SCHEMA_VERSION) errors.push('unsupported schema_version');
    const observation = {
        schema_version: schemaVersion,
        projection_version: requireText(fields.projection_version, 'projection_version', errors),
        projection_available_at: requireUtc(fields.projection_available_at, 'projection_available_at', errors),
        observation_id: requireText(fields.observation_id, 'observation_id', errors),
        canonical_event_id: requireText(fields.canonical_event_id, 'canonical_event_id', errors),
        identity_decision_id: requireText(fields.identity_decision_id, 'identity_decision_id', errors),
        identity_ruleset_version: requireText(fields.identity_ruleset_version, 'identity_ruleset_version', errors),
        identity_resolver_version: requireText(fields.identity_resolver_version, 'identity_resolver_version', errors),
        provider: requireText(fields.provider, 'provider', errors),
        provider_event_id: requireText(fields.provider_event_id, 'provider_event_id', errors),
        canonical_market_id: requireText(fields.canonical_market_id, 'canonical_market_id', errors),
        provider_market_id: requireText(fields.provider_market_id, 'provider_market_id', errors),
        canonical_bookmaker_id: requireText(fields.canonical_bookmaker_id, 'canonical_bookmaker_id', errors),
        provider_bookmaker_id: requireText(fields.provider_bookmaker_id, 'provider_bookmaker_id', errors),
        provider_bookmaker_name: requireText(fields.provider_bookmaker_name, 'provider_bookmaker_name', errors),
        competition: requireText(fields.competition, 'competition', errors),
        season: optionalText(fields.season, 'season', errors),
        home_team: requireText(fields.home_team, 'home_team', errors),
        away_team: requireText(fields.away_team, 'away_team', errors),
        kickoff_utc: requireUtc(fields.kickoff_utc, 'kickoff_utc', errors),
        period: fields.period,
        market_type: fields.market_type,
        line: optionalNumber(fields.line, 'line', errors),
        canonical_selection_id: requireText(fields.canonical_selection_id, 'canonical_selection_id', errors),
        selection: fields.selection,
        price_side: fields.price_side,
        odds_decimal: typeof fields.odds_decimal === 'number' ? fields.odds_decimal : Number.NaN,
        available_volume: optionalNumber(fields.available_volume, 'available_volume', errors),
        bet_limit: optionalNumber(fields.bet_limit, 'bet_limit', errors),
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
        identity_registry_sha256: requireText(fields.identity_registry_sha256, 'identity_registry_sha256', errors),
        quality_flags: Array.isArray(fields.quality_flags)
            ? Object.freeze([...fields.quality_flags].sort())
            : Object.freeze([]),
    };
    validateMarketIdentity(observation, errors);
    if (observation.competition !== COMPETITION) errors.push('competition must be English Premier League');
    if (!SELECTIONS.has(observation.selection)) errors.push('invalid selection');
    if (observation.market_type === '1X2' && !['HOME', 'DRAW', 'AWAY'].includes(observation.selection)) {
        errors.push('1X2 selection must be HOME, DRAW or AWAY');
    }
    if (PERIODS.has(observation.period) && MARKET_TYPES.has(observation.market_type)) {
        const expectedMarketId = `${observation.period}/${observation.market_type}/${
            observation.line === null ? 'NULL' : observation.line
        }`;
        if (observation.canonical_market_id !== expectedMarketId) {
            errors.push('canonical_market_id does not match market identity');
        }
    }
    if (SELECTIONS.has(observation.selection) && observation.canonical_selection_id !== observation.selection) {
        errors.push('canonical_selection_id does not match selection');
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
    if (!/^[a-f0-9]{64}$/.test(observation.identity_registry_sha256 || '')) {
        errors.push('identity_registry_sha256 must be lowercase SHA-256');
    }
    if (!isSafeEvidenceReference(observation.raw_evidence_reference)) {
        errors.push('raw_evidence_reference must be a safe relative reference');
    }
    if (observation.quality_flags.some(flag => typeof flag !== 'string')) {
        errors.push('quality_flags must contain strings');
    }
    if (new Set(observation.quality_flags).size !== observation.quality_flags.length) {
        errors.push('quality_flags must be unique');
    }
    if (compareUtcTimestamps(observation.response_received_at, observation.capture_started_at) < 0) {
        errors.push('response_received_at precedes capture_started_at');
    }
    if (compareUtcTimestamps(observation.ingested_at, observation.response_received_at) < 0) {
        errors.push('ingested_at precedes response_received_at');
    }
    if (compareUtcTimestamps(observation.projection_available_at, observation.ingested_at) < 0) {
        errors.push('projection_available_at precedes ingested_at');
    }
    if (errors.length) throw new Error(`invalid MarketObservation: ${errors.join('; ')}`);
    return Object.freeze(observation);
}

module.exports = {
    SCHEMA_VERSION,
    COMPETITION,
    ACQUISITION_MODES,
    PRICE_SIDES,
    stableCanonicalize,
    stableStringify,
    sha256Text,
    isUtcTimestamp,
    isSafeEvidenceReference,
    compareCodeUnits,
    normalizeUtcTimestamp,
    compareUtcTimestamps,
    semanticProjection,
    createObservation,
};
