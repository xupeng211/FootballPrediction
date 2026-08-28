'use strict';

const { adaptTheOddsApiRaw } = require('./theOddsApiAdapter');
const { appendProjection, readImmutableRaw } = require('./evidenceStore');
const { ledgerForRegistry } = require('../fixture_universe/VerifiedAllocationAuthority');

function replayRaw({ rawPath, capture, registry, decisionLedger, projectionVersion = '1', projectionAvailableAt, ledgerPath = null }) {
    if (!capture || typeof capture !== 'object') throw new Error('replay capture metadata is required');
    if (!/^[a-f0-9]{64}$/.test(capture.raw_sha256 || '')) {
        throw new Error('capture raw_sha256 is required for replay');
    }
    if (typeof projectionAvailableAt !== 'string' || !projectionAvailableAt.trim()) throw new Error('replay projectionAvailableAt is required');
    let rawText;
    try {
        rawText = readImmutableRaw({
            rawPath,
            expectedSha256: capture.raw_sha256,
        });
    } catch (error) {
        throw new Error(`replay raw input does not match replay input: ${error.message}`, { cause: error });
    }
    const verifiedLedger = decisionLedger || ledgerForRegistry(registry);
    if (!verifiedLedger) throw new Error('verified identity decision ledger is required for replay');
    const observations = adaptTheOddsApiRaw({ rawText, capture, registry, decisionLedger: verifiedLedger, projectionVersion, projectionAvailableAt });
    if (ledgerPath) observations.forEach(projection => appendProjection({ ledgerPath, projection, registry, decisionLedger: verifiedLedger }));
    return observations;
}

module.exports = { replayRaw };
