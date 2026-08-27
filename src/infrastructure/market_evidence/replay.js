'use strict';

const fs = require('node:fs');
const { adaptTheOddsApiRaw } = require('./theOddsApiAdapter');
const { appendProjection } = require('./evidenceStore');
const { sha256Text } = require('./contracts');

function replayRaw({ rawPath, capture, registry, projectionVersion = '1', ledgerPath = null }) {
    const rawText = fs.readFileSync(rawPath, 'utf8');
    const rawSha256 = sha256Text(rawText);
    if (capture.raw_sha256 && capture.raw_sha256 !== rawSha256) {
        throw new Error('capture raw_sha256 does not match replay input');
    }
    const observations = adaptTheOddsApiRaw({ rawText, capture, registry, projectionVersion });
    if (ledgerPath) observations.forEach(projection => appendProjection({ ledgerPath, projection }));
    return observations;
}

module.exports = { replayRaw };
