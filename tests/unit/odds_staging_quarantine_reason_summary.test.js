'use strict';

// lifecycle: permanent；验证离线赔率 staging 隔离原因的统计口径。

const assert = require('node:assert/strict');
const test = require('node:test');
const { summarizeQuarantineReasons } = require('../../src/infrastructure/odds_staging/quarantineReasonSummary');

test('按记录去重原因并跨记录累加，只返回原因代码和计数', () => {
    const quarantine = Object.freeze([
        Object.freeze({
            reasons: Object.freeze(['source_observed_at_invalid', 'decimal_odds_invalid', 'decimal_odds_invalid']),
            raw_record_locator: 'fixture:1',
            evidence: Object.freeze({ parsed_fields: Object.freeze({ decimal_odds: 'invalid' }) }),
        }),
        Object.freeze({ reasons: Object.freeze(['decimal_odds_invalid']) }),
    ]);

    assert.deepEqual(summarizeQuarantineReasons(quarantine), {
        decimal_odds_invalid: 2,
        source_observed_at_invalid: 1,
    });
});

test('原因键始终按代码字典序输出', () => {
    const quarantine = [
        { reasons: ['source_observed_at_invalid', 'market_line_missing'] },
        { reasons: ['decimal_odds_invalid'] },
    ];
    const expectedKeys = ['decimal_odds_invalid', 'market_line_missing', 'source_observed_at_invalid'];

    assert.deepEqual(Object.keys(summarizeQuarantineReasons(quarantine)), expectedKeys);
    const reversed = [...quarantine].reverse().map(({ reasons }) => ({ reasons: [...reasons].reverse() }));
    assert.deepEqual(Object.keys(summarizeQuarantineReasons(reversed)), expectedKeys);
});

test('无隔离记录时返回空对象', () => {
    assert.deepEqual(summarizeQuarantineReasons([]), {});
});
