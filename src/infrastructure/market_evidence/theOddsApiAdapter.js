'use strict';

/* eslint-disable complexity -- provider payload traversal is intentionally bounded to four schema levels. */
const { createObservation, sha256Text } = require('./contracts');

const ADAPTER_NAME = 'the-odds-api';
const ADAPTER_VERSION = '1.0.0';

function resolvePriceSide(bookmaker, market, outcome) {
    return outcome.price_side || market.price_side || bookmaker.price_side || 'BOOKMAKER';
}

function adaptTheOddsApiRaw({ rawText, capture, registry, projectionVersion = '1' }) {
    const payload = JSON.parse(rawText);
    if (!Array.isArray(payload)) throw new Error('The Odds API payload must be an array');
    const rawSha256 = sha256Text(rawText);
    const observations = [];
    for (const event of payload) {
        const canonicalEvent = registry.resolve('event', 'the-odds-api', event.id);
        if (event.sport_key !== 'soccer_epl') throw new Error(`unsupported competition: ${event.sport_key}`);
        for (const bookmaker of event.bookmakers || []) {
            const canonicalBookmaker = registry.resolve('bookmaker', 'the-odds-api', bookmaker.key);
            for (const market of bookmaker.markets || []) {
                const canonicalMarket = registry.resolve('market', 'the-odds-api', market.key);
                if (canonicalMarket.market_type !== '1X2') throw new Error(`unsupported market: ${market.key}`);
                if (!Array.isArray(market.outcomes) || market.outcomes.length === 0) {
                    throw new Error(`market outcomes missing: ${market.key}`);
                }
                for (const outcome of market.outcomes) {
                    const canonicalSelection = registry.resolve('selection', 'the-odds-api', outcome.name);
                    const idSeed = [
                        rawSha256,
                        projectionVersion,
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
                            price_side: resolvePriceSide(bookmaker, market, outcome),
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
                            quality_flags: [],
                        })
                    );
                }
            }
        }
    }
    return observations;
}
module.exports = { ADAPTER_NAME, ADAPTER_VERSION, adaptTheOddsApiRaw };
