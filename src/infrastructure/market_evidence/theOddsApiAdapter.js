'use strict';

/* eslint-disable complexity -- provider payload traversal is intentionally bounded to four schema levels. */
const {
    ACQUISITION_MODES,
    COMPETITION,
    compareUtcTimestamps,
    createObservation,
    isUtcTimestamp,
    sha256Text,
    stableStringify,
} = require('./contracts');

const ADAPTER_NAME = 'the-odds-api';
const ADAPTER_VERSION = '1.0.0';

function resolvePriceSide(bookmaker, market, outcome, canonicalBookmaker) {
    if (market.key === 'h2h_lay') return 'LAY';
    const rawSides = [outcome.price_side, market.price_side, bookmaker.price_side].filter(
        side => typeof side === 'string' && side.trim()
    );
    const rawSideSet = new Set(rawSides);
    if (rawSideSet.size > 1) throw new Error('provider price_side fields conflict');
    const rawSide = rawSides[0] || null;
    const registrySide = canonicalBookmaker.price_side || null;
    if (!registrySide) throw new Error('bookmaker identity mapping must declare price_side');
    if (registrySide && rawSide && registrySide !== rawSide) {
        throw new Error('provider price_side conflicts with identity registry');
    }
    return registrySide;
}

function requireObject(value, label) {
    if (!value || typeof value !== 'object' || Array.isArray(value)) throw new Error(`${label} must be an object`);
    return value;
}

function requireNonEmptyArray(value, label) {
    if (!Array.isArray(value) || value.length === 0) throw new Error(`${label} must be a non-empty array`);
    return value;
}

function assertCaptureMetadata({ rawText, capture, registry, projectionVersion }) {
    if (typeof rawText !== 'string') throw new Error('provider raw payload must be text');
    if (!capture || typeof capture !== 'object' || Array.isArray(capture)) {
        throw new Error('capture metadata is required');
    }
    if (!registry || typeof registry.resolve !== 'function' || typeof registry.version !== 'string') {
        throw new Error('identity registry is required');
    }
    if (capture.provider !== 'the-odds-api') {
        throw new Error('capture provider must be the-odds-api');
    }
    if (!/^[a-f0-9]{64}$/.test(registry.content_sha256 || '')) {
        throw new Error('identity registry content_sha256 is required');
    }
    if (typeof projectionVersion !== 'string' || !projectionVersion.trim()) {
        throw new Error('projection version is required');
    }
    for (const field of [
        'capture_id',
        'request_started_at',
        'response_received_at',
        'ingested_at',
        'raw_evidence_reference',
    ]) {
        if (typeof capture[field] !== 'string' || !capture[field].trim()) {
            throw new Error(`capture ${field} is required`);
        }
    }
    if (!ACQUISITION_MODES.has(capture.acquisition_mode)) {
        throw new Error('capture acquisition_mode is invalid');
    }
    if (!/^[a-f0-9]{64}$/.test(capture.raw_sha256 || '')) {
        throw new Error('capture raw_sha256 is required');
    }
    for (const field of ['request_started_at', 'response_received_at', 'ingested_at']) {
        if (!isUtcTimestamp(capture[field])) throw new Error(`capture ${field} must be UTC ISO-8601`);
    }
    if (compareUtcTimestamps(capture.response_received_at, capture.request_started_at) < 0) {
        throw new Error('capture response precedes request');
    }
}

function buildCoverageEvidence({ rawText, expectedProviderBookmakerIds = [] } = {}) {
    if (
        !Array.isArray(expectedProviderBookmakerIds) ||
        expectedProviderBookmakerIds.some(id => typeof id !== 'string' || !id.trim())
    ) {
        throw new Error('expected provider bookmaker IDs must be a string array');
    }
    const evidence = {
        schema_version: 'footballprediction-market-coverage/v1',
        provider: 'the-odds-api',
        competition: COMPETITION,
        requested_market_keys: ['h2h'],
        expected_provider_bookmaker_ids: [...new Set(expectedProviderBookmakerIds)].sort(),
        observed_provider_bookmakers: [],
        observed_market_keys: [],
        missing_expected_provider_bookmaker_ids: [],
        missing_expected_provider_market_bookmaker_ids: [],
        status: 'QUARANTINED',
        reason: null,
    };
    let payload;
    try {
        payload = JSON.parse(String(rawText));
    } catch {
        evidence.reason = 'MALFORMED_JSON';
        evidence.missing_expected_provider_bookmaker_ids = [...evidence.expected_provider_bookmaker_ids];
        return { ...evidence, evidence_sha256: sha256Text(stableStringify(evidence)) };
    }
    if (!Array.isArray(payload)) {
        evidence.reason = 'PAYLOAD_NOT_ARRAY';
        evidence.missing_expected_provider_bookmaker_ids = [...evidence.expected_provider_bookmaker_ids];
        return { ...evidence, evidence_sha256: sha256Text(stableStringify(evidence)) };
    }
    const bookmakerById = new Map();
    const marketKeys = new Set();
    for (const event of payload) {
        if (
            !event ||
            typeof event !== 'object' ||
            event.sport_key !== 'soccer_epl' ||
            !Array.isArray(event.bookmakers)
        ) {
            continue;
        }
        for (const bookmaker of event.bookmakers) {
            if (!bookmaker || typeof bookmaker !== 'object' || typeof bookmaker.key !== 'string') continue;
            const entry = bookmakerById.get(bookmaker.key) || {
                provider_bookmaker_id: bookmaker.key,
                provider_bookmaker_names: new Set(),
                market_keys: new Set(),
            };
            if (typeof bookmaker.title === 'string' && bookmaker.title.trim()) {
                entry.provider_bookmaker_names.add(bookmaker.title.trim());
            }
            if (Array.isArray(bookmaker.markets)) {
                for (const market of bookmaker.markets) {
                    if (market && typeof market.key === 'string' && market.key.trim()) {
                        entry.market_keys.add(market.key.trim());
                        marketKeys.add(market.key.trim());
                    }
                }
            }
            bookmakerById.set(bookmaker.key, entry);
        }
    }
    evidence.observed_provider_bookmakers = [...bookmakerById.values()]
        .sort((left, right) => (left.provider_bookmaker_id < right.provider_bookmaker_id ? -1 : 1))
        .map(entry => ({
            provider_bookmaker_id: entry.provider_bookmaker_id,
            provider_bookmaker_names: [...entry.provider_bookmaker_names].sort(),
            market_keys: [...entry.market_keys].sort(),
        }));
    evidence.observed_market_keys = [...marketKeys].sort();
    evidence.missing_expected_provider_bookmaker_ids = evidence.expected_provider_bookmaker_ids.filter(
        providerId => !bookmakerById.has(providerId)
    );
    evidence.missing_expected_provider_market_bookmaker_ids = evidence.expected_provider_bookmaker_ids.filter(
        providerId => {
            const bookmaker = bookmakerById.get(providerId);
            return (
                bookmaker &&
                evidence.requested_market_keys.some(requestedKey => !bookmaker.market_keys.has(requestedKey))
            );
        }
    );
    const missingExpectedMarketKeys = evidence.requested_market_keys.filter(key => !marketKeys.has(key));
    if (
        evidence.missing_expected_provider_bookmaker_ids.length > 0 ||
        evidence.missing_expected_provider_market_bookmaker_ids.length > 0 ||
        missingExpectedMarketKeys.length > 0
    ) {
        evidence.status = 'PARTIAL';
        if (
            evidence.missing_expected_provider_bookmaker_ids.length > 0 &&
            (evidence.missing_expected_provider_market_bookmaker_ids.length > 0 || missingExpectedMarketKeys.length > 0)
        ) {
            evidence.reason = 'EXPECTED_BOOKMAKER_AND_MARKET_NOT_OBSERVED';
        } else if (evidence.missing_expected_provider_bookmaker_ids.length > 0) {
            evidence.reason = 'EXPECTED_BOOKMAKER_NOT_OBSERVED';
        } else if (missingExpectedMarketKeys.length > 0) {
            evidence.reason = 'EXPECTED_MARKET_NOT_OBSERVED';
        } else {
            evidence.reason = 'EXPECTED_BOOKMAKER_MARKET_NOT_OBSERVED';
        }
    } else {
        evidence.status = 'OBSERVED';
    }
    return { ...evidence, evidence_sha256: sha256Text(stableStringify(evidence)) };
}

function adaptTheOddsApiRawInternal({
    rawText,
    capture,
    registry,
    projectionVersion = '1',
    allowedProviderEventIds = null,
    supportedMarketKeys = ['h2h'],
}) {
    assertCaptureMetadata({ rawText, capture, registry, projectionVersion });
    const payload = JSON.parse(rawText);
    if (!Array.isArray(payload)) throw new Error('The Odds API payload must be an array');
    const rawSha256 = sha256Text(rawText);
    if (capture.raw_sha256 !== rawSha256) throw new Error('capture raw_sha256 does not match provider payload');
    const observations = [];
    if (allowedProviderEventIds !== null && !(allowedProviderEventIds instanceof Set)) {
        throw new Error('allowedProviderEventIds must be a Set or null');
    }
    if (!Array.isArray(supportedMarketKeys) || supportedMarketKeys.some(key => typeof key !== 'string')) {
        throw new Error('supportedMarketKeys must be a string array');
    }
    const seenObservationIds = new Set();
    const seenProviderEventIds = new Set();
    for (const rawEvent of payload) {
        const event = requireObject(rawEvent, 'provider event');
        if (
            typeof event.id !== 'string' ||
            !event.id.trim() ||
            event.sport_key !== 'soccer_epl' ||
            typeof event.home_team !== 'string' ||
            !event.home_team.trim() ||
            typeof event.away_team !== 'string' ||
            !event.away_team.trim() ||
            typeof event.commence_time !== 'string' ||
            !event.commence_time.trim()
        ) {
            throw new Error('provider EPL event identity or kickoff is incomplete');
        }
        if (seenProviderEventIds.has(event.id)) {
            throw new Error(`duplicate provider event identity: ${event.id}`);
        }
        seenProviderEventIds.add(event.id);
        if (allowedProviderEventIds !== null && !allowedProviderEventIds.has(event.id)) continue;
        const canonicalEvent = registry.resolve('event', 'the-odds-api', event.id);
        if (
            event.home_team.trim() !== canonicalEvent.home_team.trim() ||
            event.away_team.trim() !== canonicalEvent.away_team.trim() ||
            !isUtcTimestamp(event.commence_time) ||
            compareUtcTimestamps(event.commence_time, canonicalEvent.kickoff_utc) !== 0
        ) {
            throw new Error(`provider event identity conflicts with registry: ${event.id}`);
        }
        const seenProviderBookmakerIds = new Set();
        for (const rawBookmaker of requireNonEmptyArray(event.bookmakers, `event ${event.id} bookmakers`)) {
            const bookmaker = requireObject(rawBookmaker, 'provider bookmaker');
            if (
                typeof bookmaker.key !== 'string' ||
                !bookmaker.key.trim() ||
                typeof bookmaker.title !== 'string' ||
                !bookmaker.title.trim()
            ) {
                throw new Error(`provider bookmaker identity is incomplete: ${event.id}`);
            }
            if (seenProviderBookmakerIds.has(bookmaker.key)) {
                throw new Error(`duplicate provider bookmaker identity: ${event.id}:${bookmaker.key}`);
            }
            seenProviderBookmakerIds.add(bookmaker.key);
            const canonicalBookmaker = registry.resolve('bookmaker', 'the-odds-api', bookmaker.key);
            const seenProviderMarketIds = new Set();
            for (const rawMarket of requireNonEmptyArray(bookmaker.markets, `bookmaker ${bookmaker.key} markets`)) {
                const market = requireObject(rawMarket, 'provider market');
                if (typeof market.key !== 'string' || !market.key.trim()) {
                    throw new Error(`provider market identity is incomplete: ${bookmaker.key}`);
                }
                if (seenProviderMarketIds.has(market.key)) {
                    throw new Error(`duplicate provider market identity: ${event.id}:${bookmaker.key}:${market.key}`);
                }
                seenProviderMarketIds.add(market.key);
                if (!supportedMarketKeys.includes(market.key)) {
                    throw new Error(`unsupported Stage C provider market: ${market.key}`);
                }
                const canonicalMarket = registry.resolve('market', 'the-odds-api', market.key);
                if (
                    canonicalMarket.period !== 'MATCH' ||
                    canonicalMarket.market_type !== '1X2' ||
                    canonicalMarket.line !== null
                ) {
                    throw new Error(`unsupported Stage C market: ${market.key}`);
                }
                const seenSelections = new Set();
                for (const rawOutcome of requireNonEmptyArray(market.outcomes, `market ${market.key} outcomes`)) {
                    const outcome = requireObject(rawOutcome, 'provider outcome');
                    if (typeof outcome.name !== 'string' || !outcome.name.trim()) {
                        throw new Error(`provider selection identity is incomplete: ${market.key}`);
                    }
                    // Provider team labels are event-contextual, so HOME/AWAY
                    // are resolved from the already governed event identity.
                    const canonicalSelection =
                        canonicalEvent.identity_decision_id && outcome.name.trim() === canonicalEvent.home_team.trim()
                            ? { canonical_id: 'HOME', selection: 'HOME' }
                            : canonicalEvent.identity_decision_id && outcome.name.trim() === canonicalEvent.away_team.trim()
                              ? { canonical_id: 'AWAY', selection: 'AWAY' }
                              : registry.resolve('selection', 'the-odds-api', outcome.name);
                    const expectedProviderTeam =
                        canonicalSelection.selection === 'HOME'
                            ? canonicalEvent.home_team
                            : canonicalSelection.selection === 'AWAY'
                              ? canonicalEvent.away_team
                              : null;
                    if (expectedProviderTeam !== null && outcome.name.trim() !== expectedProviderTeam.trim()) {
                        throw new Error(
                            `provider selection identity conflicts with event identity: ${event.id}:${outcome.name}`
                        );
                    }
                    if (seenSelections.has(canonicalSelection.canonical_id)) {
                        throw new Error(`duplicate canonical selection: ${canonicalSelection.canonical_id}`);
                    }
                    seenSelections.add(canonicalSelection.canonical_id);
                    const idSeed = [
                        rawSha256,
                        projectionVersion,
                        ADAPTER_VERSION,
                        registry.content_sha256,
                        capture.capture_id,
                        capture.response_received_at,
                        event.id,
                        bookmaker.key,
                        market.key,
                        outcome.name,
                        outcome.price,
                    ].join('|');
                    const observation = createObservation({
                        projection_version: projectionVersion,
                        observation_id: sha256Text(idSeed),
                        canonical_event_id: canonicalEvent.canonical_id,
                        identity_decision_id: canonicalEvent.identity_decision_id || null,
                        identity_ruleset_version: canonicalEvent.identity_ruleset_version || null,
                        provider: 'the-odds-api',
                        provider_event_id: event.id,
                        canonical_market_id: canonicalMarket.canonical_id,
                        provider_market_id: market.key,
                        canonical_bookmaker_id: canonicalBookmaker.canonical_id,
                        provider_bookmaker_id: bookmaker.key,
                        provider_bookmaker_name: bookmaker.title,
                        competition: COMPETITION,
                        season: canonicalEvent.season || null,
                        home_team: event.home_team,
                        away_team: event.away_team,
                        kickoff_utc: event.commence_time,
                        period: canonicalMarket.period,
                        market_type: canonicalMarket.market_type,
                        line: canonicalMarket.line ?? null,
                        canonical_selection_id: canonicalSelection.canonical_id,
                        selection: canonicalSelection.selection,
                        price_side: resolvePriceSide(bookmaker, market, outcome, canonicalBookmaker),
                        odds_decimal: outcome.price,
                        bookmaker_last_update_at: market.last_update || bookmaker.last_update || null,
                        source_snapshot_at: event.last_update || null,
                        capture_started_at: capture.request_started_at,
                        response_received_at: capture.response_received_at,
                        ingested_at: capture.ingested_at,
                        acquisition_mode: capture.acquisition_mode,
                        capture_id: capture.capture_id,
                        raw_evidence_reference: capture.raw_evidence_reference,
                        raw_sha256: rawSha256,
                        adapter_name: ADAPTER_NAME,
                        adapter_version: ADAPTER_VERSION,
                        identity_registry_version: registry.version,
                        identity_registry_sha256: registry.content_sha256,
                        quality_flags: [],
                    });
                    if (seenObservationIds.has(observation.observation_id)) {
                        throw new Error(`duplicate canonical observation identity: ${observation.observation_id}`);
                    }
                    seenObservationIds.add(observation.observation_id);
                    observations.push(observation);
                }
                for (const requiredSelection of ['HOME', 'DRAW', 'AWAY']) {
                    if (!seenSelections.has(requiredSelection)) {
                        throw new Error(`market ${market.key} is missing canonical selection: ${requiredSelection}`);
                    }
                }
            }
        }
    }
    return observations;
}

function coverageForArgs(args = {}) {
    const expectedProviderBookmakerIds =
        typeof args.registry?.list === 'function'
            ? args.registry.list('bookmaker', 'the-odds-api').map(mapping => mapping.provider_id)
            : [];
    return buildCoverageEvidence({ rawText: args.rawText, expectedProviderBookmakerIds });
}

function adaptTheOddsApiRaw(args = {}) {
    try {
        return adaptTheOddsApiRawInternal(args);
    } catch (error) {
        if (error && typeof error === 'object' && !error.coverage_evidence) {
            error.coverage_evidence = coverageForArgs(args);
        }
        throw error;
    }
}

function adaptTheOddsApiCapture(args = {}) {
    const observations = adaptTheOddsApiRaw(args);
    return Object.freeze({ observations, coverage_evidence: coverageForArgs(args) });
}

module.exports = {
    ADAPTER_NAME,
    ADAPTER_VERSION,
    adaptTheOddsApiRaw,
    adaptTheOddsApiCapture,
    buildCoverageEvidence,
};
