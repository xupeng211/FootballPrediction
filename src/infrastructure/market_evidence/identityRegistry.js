'use strict';

const fs = require('node:fs');
const { sha256Text, stableStringify, isUtcTimestamp } = require('./contracts');

const KINDS = new Set(['event', 'bookmaker', 'market', 'selection']);
const PERIODS = new Set(['MATCH', 'FIRST_HALF']);
const MARKET_TYPES = new Set(['1X2', 'ASIAN_HANDICAP', 'TOTAL']);
const SELECTIONS = new Set(['HOME', 'DRAW', 'AWAY']);
const PRICE_SIDES = new Set(['BOOKMAKER', 'BACK', 'LAY']);
const COLLECTION_KINDS = Object.freeze({
    events: 'event',
    bookmakers: 'bookmaker',
    markets: 'market',
    selections: 'selection',
});
const MAPPING_FIELDS = Object.freeze({
    event: new Set([
        'kind',
        'provider',
        'provider_id',
        'canonical_id',
        'season',
        'home_team',
        'away_team',
        'kickoff_utc',
        'provider_observed_kickoff_utc',
        'identity_decision_id',
        'identity_decision_status',
        'identity_ruleset_version',
        'provenance',
    ]),
    bookmaker: new Set(['kind', 'provider', 'provider_id', 'canonical_id', 'price_side', 'provenance']),
    market: new Set(['kind', 'provider', 'provider_id', 'canonical_id', 'period', 'market_type', 'line', 'provenance']),
    selection: new Set(['kind', 'provider', 'provider_id', 'canonical_id', 'selection', 'provenance']),
});

function key(...parts) {
    return JSON.stringify(parts);
}

function assertCollectionArrays(collections) {
    for (const [collectionName, collection] of Object.entries(collections)) {
        if (!Array.isArray(collection)) throw new Error(`identity registry ${collectionName} must be an array`);
    }
}

function collectMappings(collections) {
    assertCollectionArrays(collections);
    return Object.entries(collections).flatMap(([collectionName, collection]) => {
        const expectedKind = COLLECTION_KINDS[collectionName];
        return collection.map(mapping => {
            if (mapping?.kind !== expectedKind) {
                throw new Error(`identity registry ${collectionName} contains an invalid mapping kind`);
            }
            return mapping;
        });
    });
}

function assertBaseMapping(mapping) {
    if (
        !mapping ||
        typeof mapping !== 'object' ||
        !KINDS.has(mapping.kind) ||
        typeof mapping.provider !== 'string' ||
        !mapping.provider.trim() ||
        typeof mapping.provider_id !== 'string' ||
        !mapping.provider_id.trim() ||
        typeof mapping.canonical_id !== 'string' ||
        !mapping.canonical_id.trim() ||
        typeof mapping.provenance !== 'string' ||
        !mapping.provenance.trim()
    ) {
        throw new Error('identity mapping requires kind, provider, provider_id, canonical_id and provenance');
    }
}

function assertBookmakerMapping(mapping) {
    if (!PRICE_SIDES.has(mapping.price_side)) {
        throw new Error(`invalid bookmaker price_side: ${mapping.provider_id}`);
    }
}

function assertEventMapping(mapping) {
    for (const field of ['home_team', 'away_team']) {
        if (typeof mapping[field] !== 'string' || !mapping[field].trim()) {
            throw new Error(`event mapping requires ${field}: ${mapping.provider_id}`);
        }
    }
    if (!isUtcTimestamp(mapping.kickoff_utc)) {
        throw new Error(`event mapping requires valid kickoff_utc: ${mapping.provider_id}`);
    }
    for (const field of ['identity_decision_id', 'identity_ruleset_version']) {
        if (typeof mapping[field] !== 'string' || !mapping[field].trim()) {
            throw new Error(`event mapping requires ${field}: ${mapping.provider_id}`);
        }
    }
    if (!isUtcTimestamp(mapping.provider_observed_kickoff_utc)) {
        throw new Error(`event mapping requires valid provider_observed_kickoff_utc: ${mapping.provider_id}`);
    }
    if (mapping.identity_decision_status !== 'MATCHED') throw new Error(`event mapping requires MATCHED identity decision: ${mapping.provider_id}`);
    if (Math.abs(Date.parse(mapping.kickoff_utc) - Date.parse(mapping.provider_observed_kickoff_utc)) / 1000 > 900) throw new Error(`event mapping kickoff exceeds identity tolerance: ${mapping.provider_id}`);
}

function assertMarketMapping(mapping) {
    if (!PERIODS.has(mapping.period) || !MARKET_TYPES.has(mapping.market_type)) {
        throw new Error(`invalid market identity mapping: ${mapping.provider_id}`);
    }
    if (mapping.market_type === '1X2' && mapping.line !== null) {
        throw new Error(`1X2 market line must be null: ${mapping.provider_id}`);
    }
    if (mapping.market_type !== '1X2' && (typeof mapping.line !== 'number' || !Number.isFinite(mapping.line))) {
        throw new Error(`non-1X2 market line must be numeric: ${mapping.provider_id}`);
    }
    const expectedMarketId = `${mapping.period}/${mapping.market_type}/${mapping.line === null ? 'NULL' : mapping.line}`;
    if (mapping.canonical_id !== expectedMarketId) {
        throw new Error(`market canonical_id does not match identity fields: ${mapping.provider_id}`);
    }
}

function assertSelectionMapping(mapping) {
    if (!SELECTIONS.has(mapping.selection)) {
        throw new Error(`invalid selection identity mapping: ${mapping.provider_id}`);
    }
    if (mapping.canonical_id !== mapping.selection) {
        throw new Error(`selection canonical_id does not match selection: ${mapping.provider_id}`);
    }
}

function validateMapping(mapping) {
    assertBaseMapping(mapping);
    const unknownFields = Object.keys(mapping).filter(field => !MAPPING_FIELDS[mapping.kind].has(field));
    if (unknownFields.length) throw new Error(`unknown identity mapping field: ${unknownFields[0]}`);
    if (mapping.kind === 'event') assertEventMapping(mapping);
    if (mapping.kind === 'bookmaker') assertBookmakerMapping(mapping);
    if (mapping.kind === 'market') assertMarketMapping(mapping);
    if (mapping.kind === 'selection') assertSelectionMapping(mapping);
}

function buildIndex(mappings) {
    const index = new Map();
    for (const mapping of mappings) {
        validateMapping(mapping);
        const mappingKey = key(mapping.kind, mapping.provider, mapping.provider_id);
        if (index.has(mappingKey)) throw new Error(`ambiguous identity mapping: ${mappingKey}`);
        index.set(mappingKey, Object.freeze({ ...mapping }));
    }
    return index;
}

function hashMappings(version, mappings) {
    const sortedMappings = mappings
        .map(mapping => ({ ...mapping }))
        .sort((left, right) => {
            const leftKey = key(left.kind, left.provider, left.provider_id);
            const rightKey = key(right.kind, right.provider, right.provider_id);
            return leftKey === rightKey ? 0 : leftKey < rightKey ? -1 : 1;
        });
    return sha256Text(stableStringify({ version, mappings: sortedMappings }));
}

function createIdentityRegistry(options = {}) {
    if (!options || typeof options !== 'object' || Array.isArray(options)) {
        throw new Error('identity registry must be an object');
    }
    const allowedFields = new Set(['version', 'events', 'bookmakers', 'markets', 'selections', 'content_sha256']);
    const unknownFields = Object.keys(options).filter(field => !allowedFields.has(field));
    if (unknownFields.length) throw new Error(`unknown identity registry field: ${unknownFields[0]}`);
    const { version, events = [], bookmakers = [], markets = [], selections = [], content_sha256 } = options;
    if (typeof version !== 'string' || !version.trim()) throw new Error('identity registry version is required');
    const mappings = collectMappings({ events, bookmakers, markets, selections });
    const index = buildIndex(mappings);
    const contentSha256 = hashMappings(version, mappings);
    if (content_sha256 !== undefined && content_sha256 !== contentSha256) {
        throw new Error('identity registry content_sha256 does not match mappings');
    }
    function resolve(kind, provider, providerId) {
        const mapping = index.get(key(kind, provider, providerId));
        if (!mapping) throw new Error(`identity mapping unknown: ${kind}:${provider}:${providerId}`);
        return mapping;
    }
    const list = (kind, provider) =>
        Object.freeze(
            mappings
                .filter(mapping => mapping.kind === kind && (provider === undefined || mapping.provider === provider))
                .map(mapping => Object.freeze({ ...mapping }))
        );
    return Object.freeze({ version, content_sha256: contentSha256, resolve, list });
}

function loadIdentityRegistry(filePath) {
    const parsed = JSON.parse(fs.readFileSync(filePath, 'utf8'));
    if (!/^[a-f0-9]{64}$/.test(parsed.content_sha256 || '')) {
        throw new Error('identity registry content_sha256 is required');
    }
    return createIdentityRegistry(parsed);
}

module.exports = { createIdentityRegistry, loadIdentityRegistry };
