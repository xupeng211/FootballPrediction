'use strict';

const fs = require('node:fs');
const { adaptTheOddsApiRaw } = require('./theOddsApiAdapter');
const { appendProjection } = require('./evidenceStore');

function replayRaw({ rawPath, capture, registry, projectionVersion = '1', ledgerPath = null }) {
    const rawText = fs.readFileSync(rawPath, 'utf8');
    const observations = adaptTheOddsApiRaw({ rawText, capture, registry, projectionVersion });
    if (ledgerPath) observations.forEach(projection => appendProjection({ ledgerPath, projection }));
    return observations;
}

module.exports = { replayRaw };
