'use strict';

/* eslint-disable complexity -- provider payload traversal is intentionally bounded to four schema levels. */
const {
    ACQUISITION_MODES,
    compareUtcTimestamps,
    createObservation,
    isUtcTimestamp,
    sha256Text,
} = require('./contracts');

const ADAPTER_NAME = 'the-odds-api';
const ADAPTER_VERSION = '1.0.0';

function resolvePriceSide(bookmaker, market, outcome, canonicalBookmaker) {
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

function adaptTheOddsApiRaw({ rawText, capture, registry, projectionVersion = '1' }) {
    assertCaptureMetadata({ rawText, capture, registry, projectionVersion });
    const payload = JSON.parse(rawText);
    if (!Array.isArray(payload)) throw new Error('The Odds API payload must be an array');
    const rawSha256 = sha256Text(rawText);
    if (capture.raw_sha256 !== rawSha256) throw new Error('capture raw_sha256 does not match provider payload');
    const observations = [];
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
        const canonicalEvent = registry.resolve('event', 'the-odds-api', event.id);
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
            const canonicalBookmaker = registry.resolve('bookmaker', 'the-odds-api', bookmaker.key);
            for (const rawMarket of requireNonEmptyArray(bookmaker.markets, `bookmaker ${bookmaker.key} markets`)) {
                const market = requireObject(rawMarket, 'provider market');
                if (typeof market.key !== 'string' || !market.key.trim()) {
                    throw new Error(`provider market identity is incomplete: ${bookmaker.key}`);
                }
                if (market.key !== 'h2h') {
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
                    const canonicalSelection = registry.resolve('selection', 'the-odds-api', outcome.name);
                    if (seenSelections.has(canonicalSelection.canonical_id)) {
                        throw new Error(`duplicate canonical selection: ${canonicalSelection.canonical_id}`);
                    }
                    seenSelections.add(canonicalSelection.canonical_id);
                    const idSeed = [
                        rawSha256,
                        projectionVersion,
                        capture.capture_id,
                        capture.response_received_at,
                        event.id,
                        bookmaker.key,
                        market.key,
                        outcome.name,
                        outcome.price,
                    ].join('|');
                    observations.push(
                        createObservation({
                            projection_version: projectionVersion,
                            observation_id: sha256Text(idSeed),
                            canonical_event_id: canonicalEvent.canonical_id,
                            provider: 'the-odds-api',
                            provider_event_id: event.id,
                            canonical_market_id: canonicalMarket.canonical_id,
                            provider_market_id: market.key,
                            canonical_bookmaker_id: canonicalBookmaker.canonical_id,
                            provider_bookmaker_id: bookmaker.key,
                            provider_bookmaker_name: bookmaker.title,
                            competition: 'English Premier League',
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
                        })
                    );
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
module.exports = { ADAPTER_NAME, ADAPTER_VERSION, adaptTheOddsApiRaw };
