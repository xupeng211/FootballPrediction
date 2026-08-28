'use strict';

const KICKOFF_TOLERANCE_SECONDS = 900;

function normalizeIdentityText(value) {
    return String(value || '').normalize('NFKC').trim().replace(/\s+/g, ' ').toLocaleLowerCase('en-US');
}

module.exports = { KICKOFF_TOLERANCE_SECONDS, normalizeIdentityText };
