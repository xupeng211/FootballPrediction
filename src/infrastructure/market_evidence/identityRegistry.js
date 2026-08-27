'use strict';

const fs = require('node:fs');

function key(...parts) {
    return JSON.stringify(parts);
}

function createIdentityRegistry({ version, events = [], bookmakers = [], markets = [], selections = [] }) {
    if (typeof version !== 'string' || !version.trim()) throw new Error('identity registry version is required');
    const index = new Map();
    for (const mapping of [...events, ...bookmakers, ...markets, ...selections]) {
        if (
            !mapping.kind ||
            !mapping.provider ||
            !mapping.provider_id ||
            !mapping.canonical_id ||
            !mapping.provenance
        ) {
            throw new Error('identity mapping requires kind, provider, provider_id, canonical_id and provenance');
        }
        const mappingKey = key(mapping.kind, mapping.provider, mapping.provider_id);
        if (index.has(mappingKey)) throw new Error(`ambiguous identity mapping: ${mappingKey}`);
        index.set(mappingKey, Object.freeze({ ...mapping }));
    }
    function resolve(kind, provider, providerId) {
        const mapping = index.get(key(kind, provider, providerId));
        if (!mapping) throw new Error(`identity mapping unknown: ${kind}:${provider}:${providerId}`);
        return mapping;
    }
    return Object.freeze({ version, resolve });
}

function loadIdentityRegistry(filePath) {
    const parsed = JSON.parse(fs.readFileSync(filePath, 'utf8'));
    return createIdentityRegistry(parsed);
}

module.exports = { createIdentityRegistry, loadIdentityRegistry };
