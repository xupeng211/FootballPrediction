'use strict';

const { describe, it } = require('node:test');
const assert = require('node:assert/strict');

const { buildStatusUpdateStatement } = require('../../src/infrastructure/shared/helpers/reconMappingSqlBuilders');
const { reconImmediateStore } = require('../../src/infrastructure/recon/services/ReconImmediateStore');

describe('Recon Persistence Consistency', () => {
  it('buildStatusUpdateStatement 应避免重复更新相同 pipeline_status', () => {
    const statement = buildStatusUpdateStatement('121_20252026_0001', 'RECON_LINKED');

    assert.match(statement.query, /pipeline_status IS DISTINCT FROM \$2/);
    assert.deepEqual(statement.params, ['121_20252026_0001', 'RECON_LINKED']);
  });

  it('_persistReconOutcomeImmediately 应只统计真实状态更新数', async () => {
    const store = {
      ...reconImmediateStore,
      async _persistReconBatches() {
        return {
          linkedStatusUpdated: 1,
          mismatchUpdated: 0
        };
      }
    };

    const result = await store._persistReconOutcomeImmediately({
      status: 'linked',
      mapping: { match_id: '121_20252026_0001' }
    });

    assert.deepEqual(result, {
      linked: 1,
      mismatched: 0
    });
  });
});
