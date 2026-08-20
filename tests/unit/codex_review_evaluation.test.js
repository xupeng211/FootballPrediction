'use strict';

// lifecycle: test-fixture

const { test } = require('node:test');
const assert = require('node:assert/strict');

const {
    ELIGIBLE_STATUS,
    isEligible,
} = require('../fixtures/codex_review_evaluation/executionEligibility');

test('仅允许明确授权状态继续执行', () => {
    assert.strictEqual(isEligible(ELIGIBLE_STATUS), true);
});

test('未知、待处理和终止状态均保持拒绝', () => {
    for (const status of ['pending', 'expired', 'revoked', 'unknown', null, undefined]) {
        assert.strictEqual(isEligible(status), false, `status=${String(status)}`);
    }
});
