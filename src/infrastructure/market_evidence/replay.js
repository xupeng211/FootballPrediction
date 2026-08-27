'use strict';

const fs = require('node:fs');
const { adaptTheOddsApiRaw } = require('./theOddsApiAdapter');
const { appendProjection } = require('./evidenceStore');
const { sha256Text } = require('./contracts');

function replayRaw({ rawPath, capture, registry, projectionVersion = '1', ledgerPath = null }) {
    if (!capture || typeof capture !== 'object') throw new Error('replay capture metadata is required');
    const rawStat = fs.lstatSync(rawPath);
    if (rawStat.isSymbolicLink() || !rawStat.isFile()) throw new Error('replay raw input must be a regular file');
    const rawText = fs.readFileSync(rawPath, 'utf8');
    const rawSha256 = sha256Text(rawText);
    if (!/^[a-f0-9]{64}$/.test(capture.raw_sha256 || '')) {
        throw new Error('capture raw_sha256 is required for replay');
    }
    if (capture.raw_sha256 !== rawSha256) {
        throw new Error('capture raw_sha256 does not match replay input');
    }
    const observations = adaptTheOddsApiRaw({ rawText, capture, registry, projectionVersion });
    if (ledgerPath) observations.forEach(projection => appendProjection({ ledgerPath, projection }));
    return observations;
}

module.exports = { replayRaw };
