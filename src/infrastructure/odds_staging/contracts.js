'use strict';

// lifecycle: permanent；离线赔率 staging 的稳定数据合同与确定性哈希工具。

const crypto = require('node:crypto');

const SOURCE_MANIFEST_SCHEMA_VERSION = 'odds-source-manifest/v1';
const OBSERVATION_SCHEMA_VERSION = 'odds-observation/v1';
const QUARANTINE_SCHEMA_VERSION = 'odds-quarantine/v1';
const ALLOWED_PROVENANCE_STATUSES = new Set(['verified', 'declared', 'unknown', 'fixture']);
const ALLOWED_SNAPSHOT_TYPES = new Set(['opening', 'current', 'closing', 'unknown']);
const STRICT_ABSOLUTE_TIMESTAMP_PATTERN =
    /^(\d{4})-(\d{2})-(\d{2})T(\d{2}):(\d{2}):(\d{2})(?:\.\d{1,9})?(Z|[+-]\d{2}:\d{2})$/;

const IDEMPOTENCY_FIELDS = Object.freeze([
    'schema_version',
    'source_provider',
    'source_url',
    'source_match_id',
    'competition',
    'season',
    'kickoff_at',
    'home_team',
    'away_team',
    'bookmaker',
    'bookmaker_source_id',
    'market',
    'selection',
    'line',
    'decimal_odds',
    'snapshot_type',
    'source_observed_at',
    'captured_at',
    'source_timezone',
    'raw_sha256',
    'raw_record_locator',
    'adapter',
    'adapter_version',
    'extraction_method',
    'provenance_status',
]);

const SEMANTIC_DUPLICATE_FIELDS = Object.freeze([
    'source_provider',
    'source_match_id',
    'bookmaker',
    'market',
    'selection',
    'line',
    'snapshot_type',
    'source_observed_at',
]);

function nullableText(value) {
    const text = String(value ?? '').trim();
    return text === '' ? null : text;
}

function nullableFiniteNumber(value) {
    if (value === null || value === undefined || value === '') {
        return null;
    }

    const parsed = Number(value);
    return Number.isFinite(parsed) ? parsed : value;
}

function isStrictAbsoluteTimestamp(value) {
    const text = nullableText(value);
    const matched = text && STRICT_ABSOLUTE_TIMESTAMP_PATTERN.exec(text);
    if (!matched) {
        return false;
    }

    const [, yearText, monthText, dayText, hourText, minuteText, secondText, timezone] = matched;
    const year = Number(yearText);
    const month = Number(monthText);
    const day = Number(dayText);
    const hour = Number(hourText);
    const minute = Number(minuteText);
    const second = Number(secondText);
    if (
        month < 1 ||
        month > 12 ||
        hour > 23 ||
        minute > 59 ||
        second > 59 ||
        day < 1 ||
        day > new Date(Date.UTC(year, month, 0)).getUTCDate()
    ) {
        return false;
    }

    if (timezone !== 'Z') {
        const [, offsetHourText, offsetMinuteText] = /^([+-]\d{2}):(\d{2})$/.exec(timezone) || [];
        if (!offsetHourText || Number(offsetHourText.slice(1)) > 23 || Number(offsetMinuteText) > 59) {
            return false;
        }
    }

    return Number.isFinite(Date.parse(text));
}

function stableCanonicalize(value) {
    if (value === undefined) {
        return null;
    }

    if (Array.isArray(value)) {
        return value.map(stableCanonicalize);
    }

    if (value && typeof value === 'object') {
        return Object.keys(value)
            .sort()
            .reduce((normalized, key) => {
                normalized[key] = stableCanonicalize(value[key]);
                return normalized;
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

function sortedUniqueStrings(values = []) {
    return [...new Set((values || []).map(value => String(value).trim()).filter(Boolean))].sort();
}

function normalizeMatchLink(matchLink = {}) {
    return {
        status: nullableText(matchLink.status) || 'unmatched',
        method: nullableText(matchLink.method) || 'not_evaluated',
        candidate_ids: sortedUniqueStrings(matchLink.candidate_ids),
        matched_id: nullableText(matchLink.matched_id),
        evidence: stableCanonicalize(matchLink.evidence || {}),
    };
}

function buildIdempotencyPayload(observation = {}) {
    return IDEMPOTENCY_FIELDS.reduce((payload, field) => {
        payload[field] = stableCanonicalize(observation[field] ?? null);
        return payload;
    }, {});
}

function buildIdempotencyKey(observation = {}) {
    return sha256Text(stableStringify(buildIdempotencyPayload(observation)));
}

function buildSemanticDuplicateKey(observation = {}) {
    const payload = SEMANTIC_DUPLICATE_FIELDS.reduce((result, field) => {
        result[field] = stableCanonicalize(observation[field] ?? null);
        return result;
    }, {});
    return stableStringify(payload);
}

function buildExactDuplicateKey(observation = {}) {
    return stableStringify({
        raw_sha256: observation.raw_sha256 ?? null,
        raw_record_locator: observation.raw_record_locator ?? null,
        idempotency_key: observation.idempotency_key ?? buildIdempotencyKey(observation),
    });
}

function createCanonicalObservation(fields = {}) {
    const observation = {
        schema_version: nullableText(fields.schema_version) || OBSERVATION_SCHEMA_VERSION,
        source_provider: nullableText(fields.source_provider),
        source_url: nullableText(fields.source_url),
        source_match_id: nullableText(fields.source_match_id),
        competition: nullableText(fields.competition),
        season: nullableText(fields.season),
        kickoff_at: nullableText(fields.kickoff_at),
        home_team: nullableText(fields.home_team),
        away_team: nullableText(fields.away_team),
        bookmaker: nullableText(fields.bookmaker),
        bookmaker_source_id: nullableText(fields.bookmaker_source_id),
        market: nullableText(fields.market),
        selection: nullableText(fields.selection),
        line: nullableFiniteNumber(fields.line),
        decimal_odds: nullableFiniteNumber(fields.decimal_odds),
        snapshot_type: nullableText(fields.snapshot_type) || 'unknown',
        source_observed_at: nullableText(fields.source_observed_at),
        captured_at: nullableText(fields.captured_at),
        source_timezone: nullableText(fields.source_timezone),
        raw_sha256: nullableText(fields.raw_sha256),
        raw_record_locator: nullableText(fields.raw_record_locator),
        adapter: nullableText(fields.adapter),
        adapter_version: nullableText(fields.adapter_version),
        extraction_method: nullableText(fields.extraction_method),
        provenance_status: nullableText(fields.provenance_status),
        match_link: normalizeMatchLink(fields.match_link),
        quality_flags: sortedUniqueStrings(fields.quality_flags),
        quarantine_reasons: sortedUniqueStrings(fields.quarantine_reasons),
        duplicate_evidence: stableCanonicalize(fields.duplicate_evidence || {}),
        ingested_at: nullableText(fields.ingested_at),
    };

    observation.idempotency_key = buildIdempotencyKey(observation);
    return observation;
}

function appendObservationSignals(observation, reasons = [], flags = []) {
    return {
        ...observation,
        quality_flags: sortedUniqueStrings([...(observation.quality_flags || []), ...flags]),
        quarantine_reasons: sortedUniqueStrings([...(observation.quarantine_reasons || []), ...reasons]),
    };
}

module.exports = {
    ALLOWED_PROVENANCE_STATUSES,
    ALLOWED_SNAPSHOT_TYPES,
    OBSERVATION_SCHEMA_VERSION,
    QUARANTINE_SCHEMA_VERSION,
    SOURCE_MANIFEST_SCHEMA_VERSION,
    appendObservationSignals,
    buildExactDuplicateKey,
    buildIdempotencyKey,
    buildIdempotencyPayload,
    buildSemanticDuplicateKey,
    createCanonicalObservation,
    isStrictAbsoluteTimestamp,
    nullableText,
    sha256Text,
    sortedUniqueStrings,
    stableCanonicalize,
    stableStringify,
};
