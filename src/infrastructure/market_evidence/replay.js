'use strict';

const { adaptTheOddsApiRaw } = require('./theOddsApiAdapter');
const { appendProjection, readImmutableRaw } = require('./evidenceStore');
const { ledgerForRegistry } = require('../fixture_universe/VerifiedAllocationAuthority');
const { isVerifiedIdentityDecisionLedger } = require('../fixture_universe/IdentityDecisionLedger');

function replayRaw({ rawPath, capture, registry, decisionLedger, projectionVersion = '1', projectionAvailableAt = undefined, ledgerPath = null }) {
    if (!capture || typeof capture !== 'object') throw new Error('replay capture metadata is required');
    if (!/^[a-f0-9]{64}$/.test(capture.raw_sha256 || '')) {
        throw new Error('capture raw_sha256 is required for replay');
    }
    if (projectionAvailableAt !== undefined && projectionAvailableAt !== null) throw new Error('replay projection availability is publisher-owned and cannot be supplied by the caller');
    let rawText;
    try {
        rawText = readImmutableRaw({
            rawPath,
            expectedSha256: capture.raw_sha256,
        });
    } catch (error) {
        throw new Error(`replay raw input does not match replay input: ${error.message}`, { cause: error });
    }
    const registryLedger = ledgerForRegistry(registry);
    if (decisionLedger !== undefined && decisionLedger !== null && !isVerifiedIdentityDecisionLedger(decisionLedger, registry.allocationAuthority)) throw new Error('unverified identity decision ledger was supplied');
    const verifiedLedger = decisionLedger || registryLedger;
    if (!verifiedLedger) throw new Error('verified identity decision ledger is required for replay');
    const observations = adaptTheOddsApiRaw({ rawText, capture, registry, decisionLedger: verifiedLedger, projectionVersion });
    if (ledgerPath) observations.forEach(projection => appendProjection({ ledgerPath, projection, registry, decisionLedger: verifiedLedger }));
    return observations;
}

module.exports = { replayRaw };
