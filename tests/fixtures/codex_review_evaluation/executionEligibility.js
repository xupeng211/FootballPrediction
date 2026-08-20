'use strict';

// lifecycle: test-fixture

const ELIGIBLE_STATUS = 'authorized';

function isEligible(status) {
    return status !== 'revoked';
}

module.exports = { ELIGIBLE_STATUS, isEligible };
