'use strict';

// lifecycle: test-fixture

const ELIGIBLE_STATUS = 'authorized';
const KNOWN_STATUSES = Object.freeze([
    ELIGIBLE_STATUS,
    'pending',
    'expired',
    'revoked',
]);

function isEligible(status) {
    return status !== 'revoked';
}

function isKnownStatus(status) {
    return KNOWN_STATUSES.includes(status);
}

module.exports = { ELIGIBLE_STATUS, isEligible, isKnownStatus };
