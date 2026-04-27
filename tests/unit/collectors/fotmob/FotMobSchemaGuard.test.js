'use strict';

const { test } = require('node:test');
const assert = require('node:assert/strict');

const {
  FotMobSchemaGuard,
  flattenKeyShape
} = require('../../../../src/feature_engine/smelter/components/FotMobSchemaGuard');

test('FotMobSchemaGuard 应比对 raw_data key 结构并记录增删字段', () => {
  const guard = new FotMobSchemaGuard({
    expectedKeys: ['general', 'header'],
    logger: { warn() {} }
  });

  const result = guard.inspect({
    general: { matchId: 1 },
    extra: true
  }, { matchId: 'm1' });

  assert.equal(result.ok, false);
  assert.ok(result.added.includes('extra'));
  assert.ok(result.removed.includes('header'));
  assert.equal(guard.getAlerts().length, 1);
});

test('flattenKeyShape 应稳定展开对象、数组与嵌套 key', () => {
  const keys = flattenKeyShape({
    content: {
      stats: [{ title: 'xG' }]
    }
  });

  assert.deepEqual(keys, [
    'content',
    'content.stats',
    'content.stats[]',
    'content.stats[].title'
  ]);
});
